#!/usr/bin/env python
"""
Background-model task, Part 3: merge all per-job bias-study output JSONs
(from `run_bias_job.py` / the PBS array) into the final table, apply the
pre-set pass criterion, and select the chosen background function per
category.

PASS CRITERION (pre-set, this project's own documented choice; ATLAS-
style spurious-signal test -- see G. Aad et al. (ATLAS), "Observation of
a new particle in the search for the Standard Model Higgs boson with the
ATLAS detector at the LHC", Phys. Lett. B 716 (2012) 1, arXiv:1207.7214,
and later ATLAS H->gamma-gamma differential/coupling papers which use
the same "spurious signal < some fraction of the statistical
uncertainty" convention for background-function selection; this
project's own `studies/lr_toys/REPORT.md` T5 used the identical
illustrative 20% threshold before this task, flagged there as "not yet
the group's agreed convention" -- Maryna's group has NO prescribed
threshold (see this task's own "group conventions" note), so 20% is
adopted here as OUR documented choice, following that precedent):

    A test function PASSES if, for EVERY truth variant (all truth
    families x all 3 leakage variations) AND at EVERY scanned mass,
    |mean spurious S| < 0.20 x mean sigma_S.

SELECTION (pre-set): per category, the PASSING test function with the
FEWEST parameters; ties broken by the lower sideband NLL (from
`order_selection_<range>.json`). If NO function passes, this script
does NOT silently pick a "least bad" option -- it reports the failure
plainly and lists every function's worst-case ratio, for a human
decision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PASS_THRESHOLD = 0.20


def load_all_job_outputs(out_dir: Path) -> list:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(out_dir.glob("*.json"))]


def build_grid(job_outputs: list) -> dict:
    """{category: {(truth_family, leakage_variant): {mass: {test_function: summary}}}}"""
    grid = {}
    for job in job_outputs:
        cat = job["category"]
        key = (job["truth_family"], job["leakage_variant"])
        mass = job["mass"]
        grid.setdefault(cat, {}).setdefault(key, {})[mass] = job["test_function_results"]
    return grid


def evaluate_test_function(grid_cat: dict, test_function: str) -> dict:
    """Across every (truth_family, leakage_variant) key and every mass in
    grid_cat, find the worst (largest) |mean_S| / mean_sigma_S ratio for
    this one test function, plus every individual value (for the report)."""
    worst_ratio = -1.0
    worst_detail = None
    all_points = []
    any_missing = False
    for key, by_mass in grid_cat.items():
        for mass, test_functions in by_mass.items():
            summary = test_functions.get(test_function)
            if summary is None or summary.get("mean_S") is None:
                any_missing = True
                continue
            ratio = abs(summary["mean_S"]) / summary["mean_sigma_S"] if summary["mean_sigma_S"] else None
            point = {
                "truth_family": key[0], "leakage_variant": key[1], "mass": mass,
                "mean_S": summary["mean_S"], "mean_sigma_S": summary["mean_sigma_S"],
                "ratio": ratio, "fail_fraction": summary.get("fail_fraction"),
            }
            all_points.append(point)
            if ratio is not None and ratio > worst_ratio:
                worst_ratio = ratio
                worst_detail = point
    return {
        "worst_ratio": worst_ratio if worst_ratio >= 0 else None,
        "worst_detail": worst_detail,
        "passes": bool(worst_ratio >= 0 and worst_ratio < PASS_THRESHOLD),
        "any_missing_points": any_missing,
        "n_points": len(all_points),
        "all_points": all_points,
    }


def select_chosen_function(evaluations: dict, order_selection: dict, category: str) -> dict:
    passing = {tf: ev for tf, ev in evaluations.items() if ev["passes"]}
    if not passing:
        worst_by_tf = {tf: ev["worst_ratio"] for tf, ev in evaluations.items()}
        return {
            "chosen": None,
            "reason": "NO TEST FUNCTION PASSES the pre-set criterion in every truth variant/mass. "
                      "Per this task's own rule, the criterion is NOT relaxed. Options to consider "
                      "(a human decision, not made here): (1) add higher-order candidates beyond "
                      "'selected order + 1' for the families closest to passing; (2) revisit whether "
                      "the pre-set 20% threshold is appropriate for this analysis; (3) inspect "
                      "whether a specific truth/leakage combination is driving the failures.",
            "worst_ratio_by_test_function": worst_by_tf,
        }

    def n_params(tf: str) -> int:
        fam, order = tf.rsplit("_", 1)
        return order_selection[category][fam]["per_order"][order]["n_params"]

    def nll(tf: str) -> float:
        fam, order = tf.rsplit("_", 1)
        return order_selection[category][fam]["per_order"][order]["fit"]["nll"]

    ranked = sorted(passing.keys(), key=lambda tf: (n_params(tf), nll(tf)))
    chosen = ranked[0]
    return {
        "chosen": chosen, "n_params": n_params(chosen), "sideband_nll": nll(chosen),
        "passing_functions_ranked": ranked,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fit-range", required=True)
    p.add_argument("--out-base", default="/storage/agrp/berkom/atlas-utilization/output/hgg_bias")
    p.add_argument("--order-selection-json", default=None)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    out_dir = Path(args.out_base) / args.fit_range
    order_selection_json = args.order_selection_json or (
        f"studies/hgg_cms/background_model/results/order_selection_{args.fit_range}.json"
    )
    order_selection = json.loads(Path(order_selection_json).read_text(encoding="utf-8"))

    job_outputs = load_all_job_outputs(out_dir)
    if not job_outputs:
        raise SystemExit(f"no job output JSONs found under {out_dir}")

    grid = build_grid(job_outputs)

    result = {"fit_range": args.fit_range, "n_jobs_merged": len(job_outputs), "per_category": {}}
    for cat, grid_cat in grid.items():
        test_functions = sorted({tf for by_mass in grid_cat.values() for tfs in by_mass.values() for tf in tfs})
        evaluations = {tf: evaluate_test_function(grid_cat, tf) for tf in test_functions}
        selection = select_chosen_function(evaluations, order_selection, cat)
        result["per_category"][cat] = {
            "evaluations": evaluations, "selection": selection,
        }
        if selection["chosen"] is not None:
            chosen_ev = evaluations[selection["chosen"]]
            result["per_category"][cat]["spurious_signal_systematic"] = {
                "value": abs(chosen_ev["worst_detail"]["mean_S"]),
                "source": chosen_ev["worst_detail"],
                "description": "Largest |mean spurious S| over all truth variants/masses for the "
                                "chosen function -- a nuisance-parameter-sized systematic on the "
                                "signal yield for the later S+B fit.",
            }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")
    for cat, r in result["per_category"].items():
        print(f"{cat}: chosen = {r['selection']['chosen']}")


if __name__ == "__main__":
    main()
