"""
Signal-model task: top-level orchestrator. Runs Parts 1-4 end to end and
writes:
  studies/hgg_cms/signal_model/results/signal_model.json
  studies/hgg_cms/signal_model/results/plots/<category>_fit.png
  studies/hgg_cms/signal_model/SIGNAL_MODEL_REPORT.md

Run with:
    python -m studies.hgg_cms.signal_model.build_signal_model
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from studies.hgg_cms.signal_model.loader import (
    CATEGORIES, SIGNAL_LABELS, load_all_signal_events, reproduce_part_e, effective_mc_counts,
    LUMI_FB, BR_HGG,
)
from studies.hgg_cms.signal_model.part2_shape import run_part2, _combined_mgg_weight
from studies.hgg_cms.signal_model.part3_yields import category_yields, FIT_LO, FIT_HI
from studies.hgg_cms.signal_model.part4_systematics import build_systematics_table
from studies.hgg_cms.signal_model.plots import plot_category_fit

OUT_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = OUT_DIR / "plots"
MASS_SHIFT_DEMO_POINTS = [110.0, 115.0, 120.0, 125.0, 130.0, 135.0, 140.0]


def main():
    t0 = time.time()
    print("loading signal events ...", flush=True)
    all_signal = load_all_signal_events()
    print(f"  loaded in {time.time() - t0:.1f}s", flush=True)

    print("Part 1: reproducing VALIDATION_REPORT_1 Part E ...", flush=True)
    part1_reproduction = reproduce_part_e(all_signal)
    part1_effective = effective_mc_counts(all_signal)

    print("Part 2: fitting signal shapes per category (this takes several minutes) ...", flush=True)
    t1 = time.time()
    part2 = run_part2(all_signal)
    print(f"  Part 2 done in {time.time() - t1:.1f}s", flush=True)

    print("Part 3: expected yields with corrections ...", flush=True)
    part3 = category_yields(all_signal)

    print("Part 4: systematics table ...", flush=True)
    part4 = build_systematics_table(all_signal, part3)

    print("Plots + mass-shift demo + bin-integration checks ...", flush=True)
    mass_shift_by_cat = {}
    bin_integration_check = {}
    for cat in CATEGORIES:
        r = part2[cat]
        shape = r["chosen_shape"]
        mgg, w = _combined_mgg_weight(all_signal, cat)

        plot_category_fit(cat, mgg, w, shape, PLOTS_DIR / f"{cat}_fit.png",
                           r["chosen_chi2"], r["chosen_model"])

        delta = shape.params["mu"] - 125.0
        shifts = {}
        for mH in MASS_SHIFT_DEMO_POINTS:
            shifted = shape.shifted_to_mass(mH)
            shifts[str(mH)] = {"mean_used": shifted.params["mu"], "mode": shifted.mode()}
        mass_shift_by_cat[cat] = {"delta_GeV": delta, "shifted_shapes": shifts}

        edges_full = np.array([FIT_LO, FIT_HI])
        bin_edges_fine = np.arange(FIT_LO, FIT_HI + 0.25, 0.25)
        sum_bins = float(np.sum(shape.bin_probabilities(bin_edges_fine)))
        in_range_frac = shape.in_range_fraction(FIT_LO, FIT_HI)
        bin_integration_check[cat] = {
            "sum_of_fine_bin_probabilities": sum_bins,
            "in_range_fraction_105_180": in_range_frac,
            "rel_diff": abs(sum_bins - in_range_frac) / in_range_frac if in_range_frac else None,
        }

    print("Assembling results JSON ...", flush=True)
    signal_model_json = {}
    for cat in CATEGORIES:
        r = part2[cat]
        shape = r["chosen_shape"]
        shape_json = shape.to_json()
        if shape.covariance is not None:
            diag = np.clip(np.diagonal(shape.covariance), 0.0, None)
            shape_json["param_uncertainties"] = dict(zip(shape.param_names, np.sqrt(diag).tolist()))
        signal_model_json[cat] = {
            "shape_function": r["chosen_model"],
            "shape_params": shape_json,
            "delta_GeV_mass_shift": mass_shift_by_cat[cat]["delta_GeV"],
            "sigma_eff68_GeV": r["model_sigma_eff68"],
            "mode_GeV": r["model_mode"],
            "goodness_of_fit": r["chosen_chi2"],
            "validation": {
                "d3_reference_ggh_sigma_eff68": r["d3_reference_ggh_sigma_eff68"],
                "model_vs_d3_rel_diff": r["model_vs_d3_rel_diff"],
                "model_vs_d3_within_3pct": r["model_vs_d3_within_3pct"],
                "sample_sigma_eff68_weighted_binned": r["sample_sigma_eff68_weighted_binned"],
                "sample_mode_weighted_binned": r["sample_mode_weighted_binned"],
            },
            "gauss2_decision": r["gauss2_decision"],
            "fit_dcb_alone": {"params": r["fit_dcb"]["params"], "chi2": r["fit_dcb"]["chi2"]},
            "fit_dcb_gauss_alone": {"params": r["fit_dcb_gauss"]["params"], "chi2": r["fit_dcb_gauss"]["chi2"]},
            "per_mode_check": r["per_mode_check"],
            "vbf_flag": r["vbf_flag"],
            "mass_shift_demo": mass_shift_by_cat[cat],
            "bin_integration_check": bin_integration_check[cat],
            "yields": part3[cat],
            "systematics": part4[cat],
        }

    signal_model_json["_meta"] = {
        "luminosity_fb": LUMI_FB,
        "branching_ratio_Hgammagamma": BR_HGG,
        "fit_range_GeV": [FIT_LO, FIT_HI],
        "part1_reproduction_of_validation_report_1_part_e": part1_reproduction.get("comparison_to_part_e"),
        "part1_effective_mc_events": part1_effective,
        "grand_total_signal_yield_105_180": part3["_grand_total_with_pileup"],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "signal_model.json"
    out_path.write_text(json.dumps(signal_model_json, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out_path}", flush=True)
    print(f"total build time: {time.time() - t0:.1f}s", flush=True)
    return signal_model_json, part2


if __name__ == "__main__":
    main()
