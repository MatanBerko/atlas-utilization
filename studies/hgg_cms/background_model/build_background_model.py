"""
Background-model task: top-level orchestrator for Parts 1, 2 and 4's
order selection (all run for real, locally). Part 3 (the full bias
study) and Part 4's reduced bias check are PENDING a cluster run -- see
BACKGROUND_MODEL_REPORT.md and the final chat message for the exact
commands. This script does not attempt them.

Run with:
    python -m studies.hgg_cms.background_model.build_background_model
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from studies.hgg_cms.background_model.common import load_category_histograms, CATEGORIES
from studies.hgg_cms.background_model.part2_order_selection import run_category_order_selection
from studies.hgg_cms.background_model.serialize import order_selection_to_json
from studies.hgg_cms.background_model.plots import plot_category_sideband_fits
from studies.hgg_cms.background_model.families import FAMILIES

OUT_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = OUT_DIR / "plots"

FIT_RANGES = {"105_180": (105.0, 180.0), "110_180": (110.0, 180.0)}


def run_range(range_tag: str, lo: float, hi: float) -> dict:
    print(f"--- fit range {range_tag} ({lo}-{hi} GeV) ---", flush=True)
    hist = load_category_histograms(lo=lo, hi=hi)
    part1 = {}
    part2_raw = {}
    for cat in CATEGORIES:
        h = hist[cat]
        part1[cat] = {
            "n_events_total_in_range": h["n_events_total_in_range"],
            "n_sideband_total": h["n_sideband_total"],
            "n_events_raw_selection": h["n_events_raw"],
            "n_bins_total": len(h["counts"]), "n_bins_sideband": int(h["sideband_mask"].sum()),
        }
        t0 = time.time()
        res = run_category_order_selection(h["edges"], h["counts"], h["sideband_mask"])
        print(f"  {cat}: order selection done in {time.time() - t0:.1f}s", flush=True)
        part2_raw[cat] = res

        selected = {}
        for fam_name, r in res.items():
            order = r["selection"]["final_selected_order"]
            if order is None:
                continue
            fit = r["per_order"][order]["fit"]
            gof = r["per_order"][order]["gof"]
            selected[fam_name] = {"order": order, "params": fit.params, "nll": fit.nll, "gof_p": gof["p_value"]}
        plot_category_sideband_fits(cat, h["edges"], h["counts"], h["sideband_mask"], selected,
                                     PLOTS_DIR / f"{cat}_{range_tag}_sideband_fits.png")

    order_selection_json = order_selection_to_json(part2_raw)
    (OUT_DIR / f"order_selection_{range_tag}.json").write_text(
        json.dumps(order_selection_json, indent=2, default=str), encoding="utf-8")

    part2_summary = {}
    for cat in CATEGORIES:
        part2_summary[cat] = {}
        for fam_name, r in part2_raw[cat].items():
            sel = r["selection"]
            part2_summary[cat][fam_name] = {
                "orders_tried": sel["orders_tried"],
                "ftest_selected_order": sel["ftest_selected_order"],
                "final_selected_order": sel["final_selected_order"],
                "gof_override_used": sel["gof_override_used"],
                "dropped_family_fails_gof_everywhere": sel["dropped_family_fails_gof_everywhere"],
                "gof_p_at_final_order": (
                    r["per_order"][sel["final_selected_order"]]["gof"]["p_value"]
                    if sel["final_selected_order"] is not None else None
                ),
                "nll_at_final_order": (
                    r["per_order"][sel["final_selected_order"]]["fit"].nll
                    if sel["final_selected_order"] is not None else None
                ),
                "n_params_at_final_order": (
                    r["per_order"][sel["final_selected_order"]]["n_params"]
                    if sel["final_selected_order"] is not None else None
                ),
                "cross_check_final_order": r["cross_check_final_order"],
            }
    return {"part1": part1, "part2_summary": part2_summary}


# Part 3 timing test (measured directly on this laptop, once, before
# committing to a local run of the full grid -- see BACKGROUND_MODEL_REPORT.md
# Part 3 for the full writeup): 100 toys x 8 test functions on one
# representative (category, truth family) combination took 39.9s
# (~0.050s/toy-pair, strategy=1); a smaller 4-combination cross-check
# gave the same 0.03-0.10s/toy-pair range. These numbers are recorded
# here, not re-measured by this function (re-running the full toy grid
# to re-time it would defeat the point of having stopped).
PART3_TIMING_TEST = {
    "method": "measured directly on this laptop before committing to a local run, per this task's own instruction",
    "strategy_used": ("iminuit MIGRAD strategy=1 for every toy fit (background-only and S+B), after a first "
                       "attempt at strategy=0 gave an unacceptable ~10-70% per-combination fit-invalidity rate "
                       "(is_above_max_edm) on this problem's mixed-scale parameters"),
    "measured_rate_sec_per_toy_pair": 0.050,
    "measurement_basis": ("100 toys x 8 test functions = 800 toy-pairs in 39.9s on one representative "
                           "(category, truth family) combination; a smaller 4-combination x 20-30 toy "
                           "cross-check gave per-toy-pair times in the same 0.03-0.10s range"),
    "full_grid_toy_pairs": {
        "mass_125_toys_per_combo": 1000, "other_4_masses_toys_per_combo": 300,
        "combos_per_category": ("12 truth variants (4 families x 3 leakage variants) x 8 test functions "
                                 "(4 families x [selected order, selected order + 1]) = 96"),
        "categories": 2,
        "total_toy_pairs": 2 * 96 * (1000 + 4 * 300),
    },
    "extrapolated_total_hours": round(2 * 96 * (1000 + 4 * 300) * 0.050 / 3600.0, 2),
    "budget_hours": 3,
    "decision": ("STOP local execution of the full Part 3 grid; prepare PBS cluster jobs instead "
                 "(not submitted -- see cluster/ scripts and the final chat message for exact commands)."),
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    fit_ranges = {}
    for range_tag, (lo, hi) in FIT_RANGES.items():
        fit_ranges[range_tag] = run_range(range_tag, lo, hi)

    result = {
        "fit_ranges": fit_ranges,
        "part3_bias_study_status": {
            "status": ("PENDING -- pipeline built, unit-tested (22 tests, tests/test_background_model.py), "
                       "and timed; NOT executed at full scale (see timing_test below)"),
            "timing_test": PART3_TIMING_TEST,
            "pipeline_validated_by": [
                "a 10-toy and a 100-toy end-to-end smoke run of cluster/run_bias_job.py against the real "
                "105-180 GeV EBEB sideband fit, all 8 test functions, producing sane (if noisy, given the "
                "tiny toy count) spurious-S numbers and 0-45% per-test-function fit-failure rates, all "
                "correctly counted rather than silently dropped",
                "the NLL invariant (NLL(S free) <= NLL(S=0) + 1e-6) held on every non-failed toy in that smoke run",
            ],
            "cluster_scripts": [
                "cluster/make_job_list.py", "cluster/run_bias_job.py", "cluster/pbs_hgg_bias_array.sh",
                "cluster/submit_bias_study.sh", "cluster/status_bias_study.sh", "cluster/merge_bias_results.py",
                "cluster/plot_bias_heatmap.py",
            ],
            "exact_commands": "See BACKGROUND_MODEL_REPORT.md Part 3 and the final chat message.",
        },
        "part4_robustness_status": {
            "order_selection_110_180": ("COMPLETE (see fit_ranges.110_180 above) -- no family dropped, orders "
                                         "selected for all 4 families in both categories"),
            "reduced_bias_check": {
                "status": ("PENDING -- depends on knowing the chosen function + 2 runners-up from the main "
                           "(105-180) bias study, which is itself pending"),
                "cluster_scripts": [
                    "cluster/make_job_list_part4.py (ready)",
                    "cluster/pbs_hgg_bias_array.sh (reused, with FIT_RANGE=110_180 and TEST_FUNCTIONS set)",
                ],
            },
        },
    }

    (OUT_DIR / "background_model.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"wrote {OUT_DIR / 'background_model.json'}")
    return result


if __name__ == "__main__":
    main()
