"""
Signal-model task, Part 2: fit the combined-signal (all six modes,
expected-yield-weighted) diphoton-mass shape per category, validate it,
check per-mode consistency, and provide the mass-shift / bin-integration
machinery for downstream (background-model / S+B) tasks.

Fit range for the UNBINNED shape fit itself: the full simulated range,
100-180 GeV (every event in `signal_*.root` already satisfies this --
selection.py's own mgg cut). This is deliberately NOT restricted to the
105-180 GeV background-model fit range: the signal model is fit once,
independently of that later choice, and using the full available MC
range gives the best-constrained tails (the DCB's whole reason for
existing). The GOODNESS-OF-FIT check (binned chi2) DOES use the
pre-set 105-180 GeV / 0.25 GeV binning, per this task's own instruction.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from studies.hgg_cms.signal_model.loader import (
    SIGNAL_LABELS, CATEGORIES, load_all_signal_events,
)
from studies.hgg_cms.signal_model.fit import (
    fit_signal_shape, sandwich_covariance, binned_chi2, decide_use_gauss2,
)
from studies.hgg_cms.stats.binning import bin_edges
from studies.hgg_cms.validation import common as vcommon
from studies.hgg_cms.physics_checks.common import effective_sigma_68, histogram_mode

GOF_LO, GOF_HI, GOF_BIN_WIDTH = 105.0, 180.0, 0.25
D3_GGH_REFERENCE_SIGMA_EFF68 = {"EBEB": 1.78, "notEBEB": 2.59}
VBF_SIGMA_EFF_FLAG_THRESHOLD_PCT = 10.0


def _combined_mgg_weight(all_signal: dict, cat: str, labels=None):
    labels = labels or SIGNAL_LABELS
    mgg_parts, w_parts = [], []
    for label in labels:
        sig = all_signal[label]
        m = sig.category_mask(cat)
        mgg_parts.append(sig.mgg[m])
        w_parts.append(sig.weight(use_pileup=True)[m])
    return np.concatenate(mgg_parts), np.concatenate(w_parts)


def fit_and_validate_category(all_signal: dict, cat: str) -> dict:
    mgg, w = _combined_mgg_weight(all_signal, cat)
    edges = bin_edges(GOF_LO, GOF_HI, int(round((GOF_HI - GOF_LO) / GOF_BIN_WIDTH)))

    fit_dcb = fit_signal_shape(mgg, w, use_gauss2=False)
    chi2_dcb = binned_chi2(mgg, w, fit_dcb.shape, edges, n_free_params=6)

    fit_dcb_gauss = fit_signal_shape(mgg, w, use_gauss2=True)
    chi2_dcb_gauss = binned_chi2(mgg, w, fit_dcb_gauss.shape, edges, n_free_params=9)

    decision = decide_use_gauss2(chi2_dcb, chi2_dcb_gauss)
    if decision["use_gauss2"]:
        chosen_fit, chosen_chi2, chosen_label = fit_dcb_gauss, chi2_dcb_gauss, "DCB+Gaussian"
    else:
        chosen_fit, chosen_chi2, chosen_label = fit_dcb, chi2_dcb, "DCB"

    cov = sandwich_covariance(mgg, w, chosen_fit.shape)
    chosen_fit.shape.covariance = cov

    model_sigma_eff = chosen_fit.shape.sigma_eff68()
    model_mode = chosen_fit.shape.mode()

    sample_mode, sample_sigma_eff = vcommon.weighted_mode_and_sigma68(
        mgg, w, bin_width=0.5, lo=GOF_LO if GOF_LO < 110 else 100.0, hi=150.0
    )

    ggh = all_signal["ggh"]
    ggh_mask = ggh.category_mask(cat)
    ggh_mgg_unweighted = ggh.mgg[ggh_mask]
    ggh_sigma_eff_unbinned = effective_sigma_68(ggh_mgg_unweighted)
    ggh_mode_unbinned = histogram_mode(ggh_mgg_unweighted, bin_width=0.5, lo=110.0, hi=140.0)
    d3_ref = D3_GGH_REFERENCE_SIGMA_EFF68[cat]
    rel_diff_vs_d3 = abs(model_sigma_eff - d3_ref) / d3_ref

    result = {
        "category": cat,
        "n_events_combined": int(len(mgg)),
        "sum_weights_combined": float(w.sum()),
        "fit_dcb": {
            "params": fit_dcb.shape.params, "nll": fit_dcb.nll, "valid": fit_dcb.valid,
            "chi2": chi2_dcb,
        },
        "fit_dcb_gauss": {
            "params": fit_dcb_gauss.shape.params, "nll": fit_dcb_gauss.nll, "valid": fit_dcb_gauss.valid,
            "chi2": chi2_dcb_gauss,
        },
        "gauss2_decision": decision,
        "chosen_model": chosen_label,
        "chosen_shape": chosen_fit.shape,
        "chosen_chi2": chosen_chi2,
        "model_sigma_eff68": model_sigma_eff,
        "model_mode": model_mode,
        "sample_sigma_eff68_weighted_binned": sample_sigma_eff,
        "sample_mode_weighted_binned": sample_mode,
        "ggh_unbinned_sigma_eff68": ggh_sigma_eff_unbinned,
        "ggh_unbinned_mode": ggh_mode_unbinned,
        "d3_reference_ggh_sigma_eff68": d3_ref,
        "model_vs_d3_rel_diff": rel_diff_vs_d3,
        "model_vs_d3_within_3pct": bool(rel_diff_vs_d3 < 0.03),
    }
    return result


def per_mode_check(all_signal: dict, cat: str, use_gauss2: bool, labels=("ggh", "vbf")) -> dict:
    out = {}
    for label in labels:
        sig = all_signal[label]
        m = sig.category_mask(cat)
        mgg = sig.mgg[m]
        w = sig.weight(use_pileup=True)[m]
        fit_res = fit_signal_shape(mgg, w, use_gauss2=use_gauss2)
        sigma_eff = fit_res.shape.sigma_eff68()
        mode = fit_res.shape.mode()
        out[label] = {
            "n_events": int(len(mgg)), "params": fit_res.shape.params, "valid": fit_res.valid,
            "sigma_eff68": sigma_eff, "mode": mode,
        }
    return out


def flag_vbf_difference(per_mode: dict, combined_sigma_eff: float) -> dict:
    vbf_sigma_eff = per_mode["vbf"]["sigma_eff68"]
    rel_diff_pct = 100.0 * abs(vbf_sigma_eff - combined_sigma_eff) / combined_sigma_eff
    return {
        "vbf_sigma_eff68": vbf_sigma_eff,
        "combined_sigma_eff68": combined_sigma_eff,
        "rel_diff_pct": rel_diff_pct,
        "flagged": bool(rel_diff_pct > VBF_SIGMA_EFF_FLAG_THRESHOLD_PCT),
    }


def run_part2(all_signal: dict) -> dict:
    out = {}
    for cat in CATEGORIES:
        cat_result = fit_and_validate_category(all_signal, cat)
        use_gauss2 = cat_result["gauss2_decision"]["use_gauss2"]
        per_mode = per_mode_check(all_signal, cat, use_gauss2=use_gauss2)
        vbf_flag = flag_vbf_difference(per_mode, cat_result["model_sigma_eff68"])
        cat_result["per_mode_check"] = per_mode
        cat_result["vbf_flag"] = vbf_flag
        out[cat] = cat_result
    return out
