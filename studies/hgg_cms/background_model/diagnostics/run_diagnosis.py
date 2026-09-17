"""
Bias-study diagnosis: top-level orchestrator. Reads the already-merged
`results/bias_study_105_180.json` (produced on the cluster,
`merge_bias_results.py` at commit 9683a1f, copied here for
reproducibility) and this task's own already-committed
`order_selection_105_180.json` / `signal_model.json`. Runs Parts 1-4 and
writes plots + a consolidated summary JSON. Part 5 (the small local toy
reruns) is run separately (see `part5_failure_diagnosis.py`'s own
module docstring) since it needs the DY leakage-template JSON path,
which lives outside the repo (`HGG_LEAKAGE_TEMPLATE_JSON` env var /
`leakage.py`'s own default).

DIAGNOSIS ONLY: this script never changes any pre-set criterion, never
selects a background function, and never submits or reruns anything on
the cluster.

Run with:
    python -m studies.hgg_cms.background_model.diagnostics.run_diagnosis
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from studies.hgg_cms.background_model.diagnostics.load import (
    load_merged, load_order_selection, load_signal_model, test_functions, points_table,
    CATEGORIES,
)
from studies.hgg_cms.background_model.diagnostics.part1_drivers import (
    worst_cells, dominant_driver, plot_heatmap,
)
from studies.hgg_cms.background_model.diagnostics.part2_significance import p_value_for_function
from studies.hgg_cms.background_model.diagnostics.part4_truth_spread import (
    build_truth_curves, signal_density, plot_truth_spread, spread_vs_signal_summary,
)
from studies.hgg_cms.background_model.common import bin_edges

OUT_DIR = Path(__file__).resolve().parents[1] / "results"
PLOTS_DIR = OUT_DIR / "plots" / "bias_diagnosis"

LEAKAGE_JSON_PATH = os.environ.get(
    "HGG_LEAKAGE_TEMPLATE_JSON", r"C:\Users\matan\hgg_zee_merged\hgg_leakage_mass_template_results.json"
)

EXPECTED_SIGNAL_YIELD = {"EBEB": 545.8, "notEBEB": 266.1}


def part1_and_2(merged: dict) -> dict:
    out = {}
    for cat in CATEGORIES:
        out[cat] = {}
        for tf in test_functions(merged, cat):
            pts = points_table(merged, cat, tf)
            ev = merged["per_category"][cat]["evaluations"][tf]

            w = worst_cells(pts, 5)
            dd = dominant_driver(pts)
            sig = p_value_for_function(pts, ev["worst_ratio"])

            plot_heatmap(cat, tf, pts, PLOTS_DIR / f"{cat}_{tf}_heatmap.png")

            out[cat][tf] = {
                "eligible": ev["eligible"], "ratio_passes": ev["ratio_passes"],
                "worst_ratio": ev["worst_ratio"],
                "worst_reliable_cells": [
                    {k: v for k, v in p.items()} for p in w
                ],
                "drivers": dd,
                "significance_vs_noise": sig,
            }
    return out


def part3_events(merged: dict) -> dict:
    best_fn = {"EBEB": "bernstein_5", "notEBEB": "bernstein_6"}
    out = {}
    for cat, tf in best_fn.items():
        pts = points_table(merged, cat, tf)
        pts_sorted = sorted(pts, key=lambda p: -abs(p["mean_S"]))
        out[cat] = {
            "test_function": tf, "expected_signal_yield": EXPECTED_SIGNAL_YIELD[cat],
            "top_cells_by_abs_mean_S": [
                {
                    "truth_family": p["truth_family"], "leakage_variant": p["leakage_variant"],
                    "mass": p["mass"], "mean_S": p["mean_S"], "mean_sigma_S": p["mean_sigma_S"],
                    "ratio": p["ratio"],
                    "frac_of_expected_yield_pct": 100.0 * p["mean_S"] / EXPECTED_SIGNAL_YIELD[cat],
                }
                for p in pts_sorted[:8]
            ],
        }
    return out


def part4(order_selection: dict, signal_model: dict) -> dict:
    edges = bin_edges(105.0, 180.0, 0.25)
    out = {}
    for cat in CATEGORIES:
        curves = build_truth_curves(cat, order_selection, LEAKAGE_JSON_PATH)
        sig_dens = signal_density(cat, signal_model, edges)
        plot_truth_spread(cat, curves, sig_dens, edges, PLOTS_DIR / f"{cat}_truth_spread.png")
        out[cat] = spread_vs_signal_summary(cat, curves, sig_dens, edges)
    return out


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    merged = load_merged()
    order_selection = load_order_selection()
    signal_model = load_signal_model()

    result = {
        "part1_and_2": part1_and_2(merged),
        "part3_events": part3_events(merged),
        "part4_truth_spread": part4(order_selection, signal_model),
    }

    out_path = OUT_DIR / "bias_diagnosis_summary.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out_path}")
    return result


if __name__ == "__main__":
    main()
