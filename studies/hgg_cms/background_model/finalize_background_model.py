"""
Background-model task, Part 2: finalize the background model. Per
category, refits the chosen function (bernstein_6 in both categories --
see BACKGROUND_MODEL_REPORT.md's "Human decision after rerun 1" section)
ONE more time, warm-started exactly at the already-recorded best-fit
point from `order_selection_105_180.json`, to obtain a covariance
matrix (the original multi-start search never computed one -- see
`fit_background.refit_with_covariance`'s own docstring for why). The
refit's NLL is checked against the recorded value as an explicit
verification this reproduces the SAME minimum, not silently a different
one.

Writes `results/background_model_final.json`, sideband-fit validation
plots with a ±S_spur band, and updates the report's status section.

Run with:
    python -m studies.hgg_cms.background_model.finalize_background_model
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from studies.hgg_cms.background_model.common import load_category_histograms, CATEGORIES
from studies.hgg_cms.background_model.families import FAMILIES
from studies.hgg_cms.background_model.fit_background import refit_with_covariance, goodness_of_fit
from studies.hgg_cms.background_model.final_model import background_expectation
from studies.hgg_cms.background_model.plots_final import plot_chosen_fit, plot_spurious_signal_band
from studies.hgg_cms.signal_model.shapes import SignalShape

OUT_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = OUT_DIR / "plots"
FIT_RANGE = "105_180"

CHOSEN_FUNCTION = {"EBEB": ("bernstein", 6), "notEBEB": ("bernstein", 6)}
SPURIOUS_SIGNAL_SYSTEMATIC = {
    "EBEB": {
        "value_events": 32.1645570124977,
        "source_cell": {"truth_family": "expsum", "leakage_variant": "leakage_plus", "mass": 120.0},
        "signed_mean_S": 32.1645570124977,
    },
    "notEBEB": {
        "value_events": 109.26379513174238,
        "source_cell": {"truth_family": "powersum", "leakage_variant": "nominal", "mass": 120.0},
        "signed_mean_S": 109.26379513174238,
    },
}
EXPECTED_SIGNAL_YIELD = {"EBEB": 545.800396660376, "notEBEB": 266.12591585729473}
NLL_MATCH_TOL = 1e-3  # loose enough for float round-trip through JSON, tight enough to catch a real mismatch


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    order_selection = json.loads(
        (OUT_DIR / f"order_selection_{FIT_RANGE}.json").read_text(encoding="utf-8"))
    hist = load_category_histograms()

    per_category = {}
    for cat in CATEGORIES:
        family, order = CHOSEN_FUNCTION[cat]
        h = hist[cat]
        edges, counts, mask = h["edges"], h["counts"], h["sideband_mask"]

        recorded = order_selection[cat][family]["per_order"][str(order)]["fit"]
        recorded_nll = recorded["nll"]
        start_params = np.array(recorded["params"])

        refit = refit_with_covariance(family, order, edges, counts, mask, start_params,
                                       nll_match_tol=NLL_MATCH_TOL)
        nll_diff = abs(refit["nll"] - recorded_nll)
        if nll_diff > NLL_MATCH_TOL:
            raise SystemExit(
                f"{cat}: refit NLL ({refit['nll']}) does not match order_selection's recorded NLL "
                f"({recorded_nll}, diff={nll_diff}) within tolerance {NLL_MATCH_TOL} -- refit landed "
                f"at a DIFFERENT minimum than the recorded fit. Aborting rather than writing a "
                f"covariance for the wrong point."
            )
        print(f"{cat}: refit NLL={refit['nll']:.6f} matches recorded NLL={recorded_nll:.6f} "
              f"(diff={nll_diff:.2e} <= tol {NLL_MATCH_TOL}) -- verified same minimum.", flush=True)

        # Live sanity check (also covered by a standalone unit test):
        # the final_model module's own evaluator, restricted to sideband
        # bins, must reproduce exactly what this fit's own likelihood used.
        full_range_pred = background_expectation(cat, params=refit["params"], family=family, order=order, edges=edges)
        direct_pred = FAMILIES[family].bin_expectation(edges, order, refit["params"])
        if not np.allclose(full_range_pred[mask], direct_pred[mask]):
            raise SystemExit(f"{cat}: final_model.background_expectation does not reproduce the "
                              f"sideband-fit prediction in sideband bins -- aborting.")

        n_params = FAMILIES[family].n_params(order)
        syst = SPURIOUS_SIGNAL_SYSTEMATIC[cat]

        gof = goodness_of_fit(family, order, edges, counts, mask, refit["params"])
        plot_chosen_fit(cat, edges, counts, mask, family, order, refit["params"], gof,
                         PLOTS_DIR / f"{cat}_final_chosen_fit.png")

        signal_model_json = json.loads(
            (OUT_DIR.parent.parent / "signal_model" / "results" / "signal_model.json").read_text(encoding="utf-8"))
        sp = signal_model_json[cat]["shape_params"]
        signal_shape = SignalShape(params=sp["params"], use_gauss2=sp["use_gauss2"],
                                    param_names=tuple(sp["params"].keys()))
        plot_spurious_signal_band(cat, signal_shape, EXPECTED_SIGNAL_YIELD[cat], syst["value_events"],
                                   edges, PLOTS_DIR / f"{cat}_spurious_signal_band.png")

        per_category[cat] = {
            "chosen_function": {
                "family": family, "order": order, "n_params": n_params,
                "parameterization": (
                    "Bernstein polynomial, order 6 (7 non-negative coefficients c0..c6), "
                    "density(x) = sum_i c_i * C(6,i) * x^i * (1-x)^(6-i), "
                    "x = (m - 105) / 75 (normalized mass variable -- see families.py's own module docstring)."
                ),
                "normalized_variable": "x = (m_gg - 105.0) / 75.0",
            },
            "sideband_fit": {
                "fit_range_GeV": [105.0, 180.0], "bin_width_GeV": 0.25,
                "sideband_only": True,
                "param_names": refit["param_names"],
                "params": refit["params"].tolist(),
                "covariance": refit["covariance"].tolist() if refit["covariance"] is not None else None,
                "param_uncertainties": (
                    np.sqrt(np.clip(np.diag(refit["covariance"]), 0.0, None)).tolist()
                    if refit["covariance"] is not None else None
                ),
                "nll": refit["nll"], "valid": refit["valid"], "hesse_failed": refit["hesse_failed"],
                "verified_matches_order_selection_nll": nll_diff <= NLL_MATCH_TOL,
                "nll_diff_from_order_selection": nll_diff,
                "goodness_of_fit": gof,
            },
            "spurious_signal_systematic": {
                "value_events": syst["value_events"],
                "source_cell": syst["source_cell"],
                "signed_mean_S": syst["signed_mean_S"],
                "pct_of_expected_signal_yield": 100.0 * syst["value_events"] / EXPECTED_SIGNAL_YIELD[cat],
                "treatment": (
                    "Additional signal-yield term S_spur * theta_spur in the eventual S+B fit, "
                    "theta_spur a unit-Gaussian-constrained nuisance parameter, one per category, "
                    "uncorrelated between categories, independent of the hypothesized mass "
                    "(the maximum over the full mass scan is used at every mass point)."
                ),
            },
            "expected_signal_yield_events": EXPECTED_SIGNAL_YIELD[cat],
            "sources": {
                "order_selection": f"results/order_selection_{FIT_RANGE}.json",
                "bias_study_merged": "results/bias_study_105_180_with_rerun1.json",
                "signal_model": "../signal_model/results/signal_model.json",
            },
        }

    result = {
        "fit_range": FIT_RANGE,
        "decision_reference": "BACKGROUND_MODEL_REPORT.md, 'Human decision after rerun 1' section",
        "per_category": per_category,
    }
    out_path = OUT_DIR / "background_model_final.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    return result


if __name__ == "__main__":
    main()
