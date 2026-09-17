#!/usr/bin/env python
"""
Background-model task, Part 3: merge all per-job bias-study output JSONs
(from `run_bias_job.py` / the PBS array) into the final table, apply the
pre-set pass criteria, and select the chosen background function per
category.

OUTPUT LOCATION: writes to LUSTRE by default (under
`/storage/agrp/berkom/atlas-utilization/output/hgg_bias/merged/`), never
into the git checkout -- the checkout must stay clean for later preflight
checks (e.g. `studies/hgg_cms/cluster/submit_zee.sh`'s own
`preflight_git`, which refuses to submit against a dirty tree). `--out`
can still override this if a caller really wants somewhere else, but the
default is Lustre, not the repo.

PASS CRITERIA (pre-set, this project's own documented choice; see
BACKGROUND_MODEL_REPORT.md's "Fit-reliability eligibility rule" section
for the full dated writeup). A test function's FINAL verdict combines
TWO independent pre-set criteria -- both must hold in EVERY truth
variant (all truth families x all 3 leakage variations) AND at EVERY
scanned mass:

  (1) RELIABILITY (added 18 Sep 2026, before any bias-study result
      existed): fail_fraction <= 0.05 in every cell, AND (checked
      explicitly, not just inferred) at least 900/1000 successful toys
      at m_H=125 GeV or 270/300 elsewhere. A function violating this in
      ANY cell is INELIGIBLE for selection regardless of its spurious-
      signal size -- its numbers are still reported, for information,
      never hidden.
  (2) SPURIOUS SIGNAL (ATLAS-style; see G. Aad et al. (ATLAS),
      "Observation of a new particle...", Phys. Lett. B 716 (2012) 1,
      arXiv:1207.7214, and this project's own `studies/lr_toys/REPORT.md`
      T5, which used the same illustrative 20% threshold before this
      task -- Maryna's group has no prescribed convention, so this is
      OUR documented choice): |mean spurious S| < 0.20 x mean sigma_S.

BORDERLINE FLAG (added 18 Sep 2026): a cell is flagged "borderline" if
its ratio |mean_S|/mean_sigma_S is within 1 STANDARD ERROR of the 0.20
threshold, i.e. |ratio - 0.20| <= se_ratio, where
se_ratio = se_mean_S / mean_sigma_S -- se_mean_S (the toy-to-toy standard
error on the mean spurious signal, already computed by
`bias_study.summarize_toys`) is treated as the only fluctuating piece of
the ratio; mean_sigma_S (an average of per-toy FITTED uncertainties) is
treated as effectively fixed for this purpose -- a documented
approximation, not a full error propagation on both terms.

SELECTION (pre-set): per category, among ELIGIBLE, PASSING test
functions, the one with the FEWEST parameters; ties broken by the lower
sideband NLL (from `order_selection_<range>.json`). If NO function is
both eligible and passing, this script does NOT silently pick a
"least bad" option -- it reports the failure plainly, lists every
function's worst-case ratio AND its reliability verdict, and separately
lists which functions were excluded purely on reliability grounds
("ineligible: fit reliability") so a human can see whether reliability
or genuine bias is the blocker.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PASS_THRESHOLD = 0.20
MAX_FAIL_FRACTION = 0.05  # added 18 Sep 2026, before any real bias-study result existed
MIN_SUCCESSFUL_TOYS = {125: 900, "default": 270}  # 90% of 1000 / 90% of 300 -- see module docstring
DEFAULT_OUT_BASE = "/storage/agrp/berkom/atlas-utilization/output/hgg_bias"
DEFAULT_MERGED_SUBDIR = "merged"


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


def _min_required_toys(mass: float) -> int:
    return MIN_SUCCESSFUL_TOYS[125] if int(round(mass)) == 125 else MIN_SUCCESSFUL_TOYS["default"]


def evaluate_test_function(grid_cat: dict, test_function: str) -> dict:
    """Across every (truth_family, leakage_variant) key and every mass in
    grid_cat, find the worst (largest) |mean_S| / mean_sigma_S ratio for
    this one test function, its reliability verdict, and every
    individual per-cell value (for the report)."""
    worst_ratio = -1.0
    worst_detail = None
    worst_reliability_detail = None
    all_points = []
    any_missing = False
    any_reliability_violation = False
    borderline_points = []

    for key, by_mass in grid_cat.items():
        for mass, test_functions in by_mass.items():
            summary = test_functions.get(test_function)
            if summary is None or summary.get("mean_S") is None:
                any_missing = True
                continue

            n_total = summary.get("n_total", 0)
            n_failed = summary.get("n_failed", n_total)
            # n_used is read from the job's OWN reported field when present
            # (not silently recomputed as n_total-n_failed) so this check
            # is a genuine cross-check against that job's own bookkeeping,
            # not a tautological restatement of fail_fraction under a
            # different name -- falls back to the arithmetic only if the
            # field is absent (e.g. summarize_toys' all-failed branch,
            # which never emits "n_used").
            n_used = summary.get("n_used", n_total - n_failed)
            fail_fraction = (n_failed / n_total) if n_total else 1.0
            min_required = _min_required_toys(mass)
            # Two checks, kept SEPARATE on purpose (see comment above):
            # fail_fraction<=0.05 already implies n_used is comfortably
            # above these floors (95% >= 90%) IF the two numbers agree --
            # this explicit second check catches it if they don't.
            reliability_ok = (fail_fraction <= MAX_FAIL_FRACTION) and (n_used >= min_required)
            if not reliability_ok:
                any_reliability_violation = True

            mean_S = summary["mean_S"]
            mean_sigma_S = summary.get("mean_sigma_S")
            se_mean_S = summary.get("se_mean_S")
            ratio = abs(mean_S) / mean_sigma_S if mean_sigma_S else None
            se_ratio = (se_mean_S / mean_sigma_S) if (se_mean_S is not None and mean_sigma_S) else None
            borderline = bool(se_ratio is not None and ratio is not None
                               and abs(ratio - PASS_THRESHOLD) <= se_ratio)

            point = {
                "truth_family": key[0], "leakage_variant": key[1], "mass": mass,
                "mean_S": mean_S, "mean_sigma_S": mean_sigma_S, "se_mean_S": se_mean_S,
                "ratio": ratio, "se_ratio": se_ratio, "borderline": borderline,
                "fail_fraction": fail_fraction, "n_total": n_total, "n_used": n_used,
                "min_required_toys": min_required, "reliability_ok": reliability_ok,
            }
            all_points.append(point)
            if borderline:
                borderline_points.append(point)
            if ratio is not None and ratio > worst_ratio:
                worst_ratio = ratio
                worst_detail = point
            if not reliability_ok:
                if worst_reliability_detail is None or fail_fraction > worst_reliability_detail["fail_fraction"]:
                    worst_reliability_detail = point

    eligible = not any_reliability_violation
    ratio_passes = bool(worst_ratio >= 0 and worst_ratio < PASS_THRESHOLD)
    return {
        "worst_ratio": worst_ratio if worst_ratio >= 0 else None,
        "worst_detail": worst_detail,
        "ratio_passes": ratio_passes,
        "eligible": eligible,
        "worst_reliability_detail": worst_reliability_detail,
        "ineligibility_reason": (
            None if eligible else
            f"ineligible: fit reliability -- fail_fraction={worst_reliability_detail['fail_fraction']:.3f} "
            f"(max allowed {MAX_FAIL_FRACTION}) and/or n_used={worst_reliability_detail['n_used']} "
            f"< min_required={worst_reliability_detail['min_required_toys']} in "
            f"{worst_reliability_detail['truth_family']}/{worst_reliability_detail['leakage_variant']}/"
            f"m{worst_reliability_detail['mass']}"
        ),
        "passes": bool(eligible and ratio_passes),
        "any_missing_points": any_missing,
        "n_points": len(all_points),
        "n_borderline_points": len(borderline_points),
        "borderline_points": borderline_points,
        "all_points": all_points,
    }


def select_chosen_function(evaluations: dict, order_selection: dict, category: str) -> dict:
    passing = {tf: ev for tf, ev in evaluations.items() if ev["passes"]}
    ineligible = {tf: ev["ineligibility_reason"] for tf, ev in evaluations.items() if not ev["eligible"]}

    if not passing:
        worst_by_tf = {tf: ev["worst_ratio"] for tf, ev in evaluations.items()}
        return {
            "chosen": None,
            "reason": "NO TEST FUNCTION is both ELIGIBLE (fit reliability) and PASSING (spurious-signal "
                      "ratio) in every truth variant/mass. Per this task's own rule, neither criterion is "
                      "relaxed. Options to consider (a human decision, not made here): (1) if functions are "
                      "failing on RELIABILITY, investigate/improve the toy-fit convergence for those "
                      "specific (truth, mass) cells rather than accepting an unreliable bias estimate; "
                      "(2) if functions are failing on the spurious-signal RATIO, add higher-order "
                      "candidates beyond 'selected order + 1' for the families closest to passing, or "
                      "revisit whether the pre-set 20% threshold is appropriate; (3) inspect whether a "
                      "specific truth/leakage combination is driving the failures.",
            "worst_ratio_by_test_function": worst_by_tf,
            "ineligible_functions": ineligible,
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
        "ineligible_functions": ineligible,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fit-range", required=True)
    p.add_argument("--out-base", default=DEFAULT_OUT_BASE,
                    help="Where per-job output JSONs live (Lustre), NOT where the merged result is written.")
    p.add_argument("--order-selection-json", default=None)
    p.add_argument("--out", default=None,
                    help="Merged result path. Default: <out-base>/merged/bias_study_<fit-range>.json on "
                         "Lustre -- NEVER defaults into the git checkout.")
    args = p.parse_args()

    out_dir = Path(args.out_base) / args.fit_range
    order_selection_json = args.order_selection_json or (
        f"studies/hgg_cms/background_model/results/order_selection_{args.fit_range}.json"
    )
    order_selection = json.loads(Path(order_selection_json).read_text(encoding="utf-8"))

    out_path = Path(args.out) if args.out else (
        Path(args.out_base) / DEFAULT_MERGED_SUBDIR / f"bias_study_{args.fit_range}.json"
    )

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

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    for cat, r in result["per_category"].items():
        print(f"{cat}: chosen = {r['selection']['chosen']}")
        if r["selection"].get("ineligible_functions"):
            print(f"  ineligible (fit reliability): {list(r['selection']['ineligible_functions'].keys())}")


if __name__ == "__main__":
    main()
