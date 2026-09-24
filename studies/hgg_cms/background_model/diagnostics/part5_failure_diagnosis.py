"""Bias-study diagnosis, Part 5: characterize WHY specific (truth, test-
function) cells have an elevated fit-failure rate. Reruns a SMALL local
sample (<=50 toys, fixed seed) per targeted cell -- diagnosis only, does
not touch bias_study.py, does not change any pre-set criterion, does not
resubmit anything to the cluster.
"""
from __future__ import annotations

import numpy as np

from studies.hgg_cms.background_model.families import FAMILIES
from studies.hgg_cms.background_model.common import bin_edges
from studies.hgg_cms.background_model.leakage import leakage_template_fine
from studies.hgg_cms.background_model.bias_study import (
    build_truth_variants, generate_toy, fit_toy_bkg_only, fit_toy_splus_b, NLL_INVARIANT_TOL,
)
from studies.hgg_cms.background_model.signal_shape import load_signal_shape
from studies.hgg_cms.background_model.diagnostics.load import load_order_selection


def diagnose_cell(category: str, truth_family: str, leakage_variant: str, mass: float,
                   test_function: str, leakage_json_path: str, n_toys: int = 50,
                   seed: int = 20260918800) -> dict:
    order_selection = load_order_selection()
    edges = bin_edges(105.0, 180.0, 0.25)

    truth_order = order_selection[category][truth_family]["selection"]["final_selected_order"]
    truth_params = np.array(order_selection[category][truth_family]["per_order"][str(truth_order)]["fit"]["params"])
    leak = leakage_template_fine(category, edges, path=leakage_json_path)
    variants = build_truth_variants(truth_family, truth_order, truth_params, edges, leak)
    truth = variants[leakage_variant]

    test_fam_name, test_order_str = test_function.rsplit("_", 1)
    test_order = int(test_order_str)
    fam = FAMILIES[test_fam_name]
    warm_start = np.array(order_selection[category][test_fam_name]["per_order"][str(test_order)]["fit"]["params"])
    bounds = fam.bounds(test_order, float(truth.sum()))

    sig_shape = load_signal_shape(category).shifted_to_mass(mass)
    sig_probs = sig_shape.bin_probabilities(edges)

    rng = np.random.default_rng(seed)

    records = []
    for i in range(n_toys):
        data = generate_toy(rng, truth)
        m_bkg = fit_toy_bkg_only(test_fam_name, test_order, edges, data, warm_start, bounds)
        bkg_params = np.array([m_bkg.values[n] for n in m_bkg.parameters])

        m_sb = fit_toy_splus_b(test_fam_name, test_order, edges, data, bkg_params, bounds, sig_probs,
                                s_start=0.0, s_bound=20.0 * max(float(truth.sum()), 1.0))

        nll_bkg = float(m_bkg.fval)
        nll_sb = float(m_sb.fval)
        invariant_violated = nll_sb > nll_bkg + NLL_INVARIANT_TOL

        rec = {
            "toy": i,
            "bkg_valid": bool(m_bkg.valid),
            "bkg_is_above_max_edm": bool(m_bkg.fmin.is_above_max_edm),
            "bkg_has_parameters_at_limit": bool(m_bkg.fmin.has_parameters_at_limit),
            "bkg_hesse_failed": bool(m_bkg.fmin.hesse_failed),
            "sb_valid": bool(m_sb.valid),
            "sb_is_above_max_edm": bool(m_sb.fmin.is_above_max_edm),
            "sb_has_parameters_at_limit": bool(m_sb.fmin.has_parameters_at_limit),
            "sb_hesse_failed": bool(m_sb.fmin.hesse_failed),
            "sb_has_accurate_covar": bool(m_sb.fmin.has_accurate_covar) if hasattr(m_sb.fmin, "has_accurate_covar") else None,
            "invariant_violated": bool(invariant_violated),
            "nll_bkg": nll_bkg, "nll_sb": nll_sb,
            "S": float(m_sb.values["S"]),
        }
        # correlation matrix for the S+B fit's covariance, if available --
        # to check whether test-function parameters (esp. power-law
        # exponents) are strongly correlated with each other or with S.
        try:
            corr = np.array(m_sb.covariance.correlation())
            names = list(m_sb.parameters)
            # largest off-diagonal |correlation| among the BACKGROUND
            # parameters only (excluding S itself)
            bkg_idx = [i for i, n in enumerate(names) if n != "S"]
            sub = corr[np.ix_(bkg_idx, bkg_idx)]
            np.fill_diagonal(sub, 0.0)
            rec["max_abs_bkg_param_correlation"] = float(np.max(np.abs(sub))) if sub.size else None
            s_idx = names.index("S")
            rec["max_abs_S_correlation_with_bkg"] = float(np.max(np.abs(corr[s_idx, bkg_idx]))) if bkg_idx else None
        except Exception:
            rec["max_abs_bkg_param_correlation"] = None
            rec["max_abs_S_correlation_with_bkg"] = None

        records.append(rec)

    failed = [r for r in records if not (r["bkg_valid"] and r["sb_valid"]) or r["invariant_violated"]]
    reason_counts = {
        "bkg_is_above_max_edm": sum(1 for r in failed if r["bkg_is_above_max_edm"]),
        "sb_is_above_max_edm": sum(1 for r in failed if r["sb_is_above_max_edm"]),
        "bkg_has_parameters_at_limit": sum(1 for r in failed if r["bkg_has_parameters_at_limit"]),
        "sb_has_parameters_at_limit": sum(1 for r in failed if r["sb_has_parameters_at_limit"]),
        "bkg_hesse_failed": sum(1 for r in failed if r["bkg_hesse_failed"]),
        "sb_hesse_failed": sum(1 for r in failed if r["sb_hesse_failed"]),
        "invariant_violated": sum(1 for r in failed if r["invariant_violated"]),
    }
    corr_vals = [r["max_abs_bkg_param_correlation"] for r in records if r["max_abs_bkg_param_correlation"] is not None]

    return {
        "category": category, "truth_family": truth_family, "leakage_variant": leakage_variant, "mass": mass,
        "test_function": test_function, "n_toys": n_toys, "seed": seed,
        "n_failed": len(failed), "fail_fraction_local": len(failed) / n_toys,
        "failure_reason_counts": reason_counts,
        "mean_max_abs_bkg_param_correlation": float(np.mean(corr_vals)) if corr_vals else None,
        "max_max_abs_bkg_param_correlation": float(np.max(corr_vals)) if corr_vals else None,
        "records": records,
    }
