#!/usr/bin/env python
"""
Background-model task, Part 3 (+ bias-study rerun 1): merge all per-job
bias-study output JSONs (from `run_bias_job.py` / the PBS array(s)) into
the final table, apply the pre-set pass criteria, and select the chosen
background function per category -- or STOP and report if none
qualifies.

MULTI-SOURCE MERGE (added for rerun 1): `--jobs-dir` (the primary
source, defaults to `<out-base>/<fit-range>`) can be combined with any
number of `--extra-jobs-dir` directories -- each a directory containing
per-job output JSONs DIRECTLY (no fit-range subdirectory appended,
unlike the primary source), e.g. the rerun's own
`.../hgg_bias/105_180_rerun1/`. All job outputs from every source are
pooled into ONE grid per category before evaluation, so a test function
introduced only in a later rerun (e.g. `bernstein_6`) is evaluated
side-by-side with the first run's own candidates.

OUTPUT LOCATION: writes to LUSTRE by default (under
`/storage/agrp/berkom/atlas-utilization/output/hgg_bias/merged/`), never
into the git checkout -- the checkout must stay clean for later preflight
checks (e.g. `studies/hgg_cms/cluster/submit_zee.sh`'s own
`preflight_git`, which refuses to submit against a dirty tree). `--out`
can still override this if a caller really wants somewhere else, but the
default is Lustre, not the repo.

PASS CRITERIA (pre-set, this project's own documented choice; see
BACKGROUND_MODEL_REPORT.md's "Fit-reliability eligibility rule" and
"Pre-declared selection procedure after the first bias study" sections
for the full dated writeups). A test function's FINAL verdict combines
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

SELECTION (pre-set, REVISED 18 Sep 2026 -- see BACKGROUND_MODEL_REPORT.md's
"Pre-declared selection procedure" section for the full, dated writeup;
an earlier version of that section briefly auto-applied fallback C here,
superseded before any rerun result existed):
  (i) If one or more candidates are ELIGIBLE and PASSING (both criteria
      above, in every cell): choose the one with the FEWEST parameters;
      ties broken by the lower sideband NLL.
  (ii) Otherwise: STOP. This script does NOT auto-select a function. It
      reports, per category: every candidate's eligibility, worst
      ratio, worst |S_spur| in events and as a percentage of the
      expected signal yield; and, separately, which candidate FALLBACK
      C (an ATLAS-style spurious-signal systematic: among ELIGIBLE
      candidates only, the smallest worst ratio, ties broken by fewer
      parameters) WOULD choose and what its systematic would be --
      clearly marked "not applied, human decision required". Neither
      fallback C nor the CMS discrete-profiling/envelope method
      (arXiv:1408.6865) is applied automatically.
  (iii) For a function chosen under (i): the category's spurious-signal
      systematic = the maximum over all 60 cells (or however many the
      merged sources cover) of |mean spurious S| in events, for that
      function -- a unit-Gaussian-constrained nuisance parameter, one
      per category, uncorrelated between categories, added to the
      eventual S+B fit's signal yield.
  (iv) If NO candidate in a category is eligible at all: STOP and
      report (same as (ii), but there is then no fallback-C candidate
      to compute either, since fallback C itself requires at least one
      eligible candidate).
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
REPO_ROOT = Path(__file__).resolve().parents[4]
SIGNAL_MODEL_JSON = REPO_ROOT / "studies" / "hgg_cms" / "signal_model" / "results" / "signal_model.json"


def load_expected_signal_yields(signal_model_json: Path = SIGNAL_MODEL_JSON) -> dict:
    d = json.loads(signal_model_json.read_text(encoding="utf-8"))
    return {cat: float(d[cat]["yields"]["N_with_trigger_sf_central"]) for cat in ("EBEB", "notEBEB")}


def load_all_job_outputs(*jobs_dirs: Path) -> list:
    """Pools per-job output JSONs from one or more directories (each
    read directly, non-recursively -- no fit-range subdirectory is
    appended here; callers pass the exact directory each source's jobs
    were written into)."""
    out = []
    for jobs_dir in jobs_dirs:
        out.extend(json.loads(p.read_text(encoding="utf-8")) for p in sorted(jobs_dir.glob("*.json")))
    return out


def build_grid(job_outputs: list) -> dict:
    """{category: {(truth_family, leakage_variant): {mass: {test_function: summary}}}}
    If the SAME (category, truth, leakage, mass, test_function) cell
    appears in more than one source, the LAST one loaded wins (sources
    should never genuinely overlap in practice -- each covers disjoint
    test functions for the same cells -- but this is documented rather
    than silently ambiguous)."""
    grid = {}
    for job in job_outputs:
        cat = job["category"]
        key = (job["truth_family"], job["leakage_variant"])
        mass = job["mass"]
        cell = grid.setdefault(cat, {}).setdefault(key, {}).setdefault(mass, {})
        cell.update(job["test_function_results"])
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
    worst_abs_mean_S = -1.0
    worst_abs_mean_S_detail = None
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
            if abs(mean_S) > worst_abs_mean_S:
                worst_abs_mean_S = abs(mean_S)
                worst_abs_mean_S_detail = point
            if not reliability_ok:
                if worst_reliability_detail is None or fail_fraction > worst_reliability_detail["fail_fraction"]:
                    worst_reliability_detail = point

    eligible = not any_reliability_violation
    ratio_passes = bool(worst_ratio >= 0 and worst_ratio < PASS_THRESHOLD)
    return {
        "worst_ratio": worst_ratio if worst_ratio >= 0 else None,
        "worst_detail": worst_detail,
        "worst_abs_mean_S_events": worst_abs_mean_S if worst_abs_mean_S >= 0 else None,
        "worst_abs_mean_S_detail": worst_abs_mean_S_detail,
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


def _n_params(order_selection: dict, category: str, tf: str) -> int:
    fam, order = tf.rsplit("_", 1)
    return order_selection[category][fam]["per_order"][order]["n_params"]


def _nll(order_selection: dict, category: str, tf: str) -> float:
    fam, order = tf.rsplit("_", 1)
    return order_selection[category][fam]["per_order"][order]["fit"]["nll"]


def compute_fallback_c_choice(evaluations: dict, order_selection: dict, category: str) -> dict | None:
    """What FALLBACK C (see module docstring) WOULD choose: among
    ELIGIBLE candidates only, the smallest worst ratio, ties broken by
    fewer parameters. Returns None if no candidate is eligible at all
    (fallback C itself has nothing to choose from then). NEVER called to
    make the actual selection -- see select_chosen_function's (ii)/(iv):
    this is computed for the report only, always marked "not applied"."""
    eligible = {tf: ev for tf, ev in evaluations.items() if ev["eligible"]}
    if not eligible:
        return None
    ranked = sorted(eligible.keys(), key=lambda tf: (eligible[tf]["worst_ratio"], _n_params(order_selection, category, tf)))
    chosen = ranked[0]
    ev = eligible[chosen]
    expected_yield = load_expected_signal_yields().get(category)
    worst_s_events = ev["worst_abs_mean_S_events"]
    return {
        "would_choose": chosen,
        "worst_ratio": ev["worst_ratio"],
        "n_params": _n_params(order_selection, category, chosen),
        "worst_abs_mean_S_events": worst_s_events,
        "worst_abs_mean_S_pct_of_expected_yield": (
            100.0 * worst_s_events / expected_yield if (worst_s_events is not None and expected_yield) else None
        ),
        "ranked_eligible_by_worst_ratio": ranked,
        "status": "NOT APPLIED -- human decision required (see BACKGROUND_MODEL_REPORT.md "
                  "'Pre-declared selection procedure', point 2(ii))",
    }


def select_chosen_function(evaluations: dict, order_selection: dict, category: str) -> dict:
    """Implements ONLY step (i) (pass-and-eligible -> fewest params,
    tie -> lower NLL) and the STOP-and-report path (ii)/(iv). Never
    auto-applies fallback C -- see compute_fallback_c_choice, called
    separately by main() and attached to the STOP report for visibility
    only."""
    passing = {tf: ev for tf, ev in evaluations.items() if ev["passes"]}
    ineligible = {tf: ev["ineligibility_reason"] for tf, ev in evaluations.items() if not ev["eligible"]}

    if not passing:
        expected_yield = load_expected_signal_yields().get(category)
        candidate_summary = {}
        for tf, ev in evaluations.items():
            worst_s = ev["worst_abs_mean_S_events"]
            candidate_summary[tf] = {
                "eligible": ev["eligible"],
                "worst_ratio": ev["worst_ratio"],
                "worst_abs_mean_S_events": worst_s,
                "worst_abs_mean_S_pct_of_expected_yield": (
                    100.0 * worst_s / expected_yield if (worst_s is not None and expected_yield) else None
                ),
            }
        fallback_c = compute_fallback_c_choice(evaluations, order_selection, category)
        return {
            "chosen": None,
            "reason": "NO TEST FUNCTION is both ELIGIBLE (fit reliability) and PASSING (spurious-signal "
                      "ratio) in every truth variant/mass. Per BACKGROUND_MODEL_REPORT.md's pre-declared "
                      "procedure, this is a STOP: no function is auto-selected. See "
                      "'fallback_c_if_applied' below for what an ATLAS-style spurious-signal-systematic "
                      "choice would be (NOT applied here -- a human decision) and "
                      "BACKGROUND_MODEL_REPORT.md's 'Pre-declared selection procedure' section point 4 "
                      "for the CMS discrete-profiling/envelope alternative.",
            "candidate_summary": candidate_summary,
            "ineligible_functions": ineligible,
            "fallback_c_if_applied": fallback_c,
        }

    ranked = sorted(passing.keys(), key=lambda tf: (_n_params(order_selection, category, tf), _nll(order_selection, category, tf)))
    chosen = ranked[0]
    return {
        "chosen": chosen, "n_params": _n_params(order_selection, category, chosen),
        "sideband_nll": _nll(order_selection, category, chosen),
        "passing_functions_ranked": ranked,
        "ineligible_functions": ineligible,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fit-range", required=True)
    p.add_argument("--out-base", default=DEFAULT_OUT_BASE,
                    help="Where the PRIMARY source's per-job output JSONs live, under "
                         "<out-base>/<fit-range>/ (Lustre); NOT where the merged result is written.")
    p.add_argument("--extra-jobs-dir", action="append", default=[],
                    help="Additional directory (repeatable) containing per-job output JSONs "
                         "DIRECTLY -- no fit-range subdirectory appended, e.g. a rerun's own "
                         ".../hgg_bias/105_180_rerun1/. Merged into the same grid as the primary source.")
    p.add_argument("--order-selection-json", default=None)
    p.add_argument("--out", default=None,
                    help="Merged result path. Default: <out-base>/merged/bias_study_<fit-range>.json on "
                         "Lustre -- NEVER defaults into the git checkout.")
    args = p.parse_args()

    primary_dir = Path(args.out_base) / args.fit_range
    extra_dirs = [Path(d) for d in args.extra_jobs_dir]
    order_selection_json = args.order_selection_json or (
        f"studies/hgg_cms/background_model/results/order_selection_{args.fit_range}.json"
    )
    order_selection = json.loads(Path(order_selection_json).read_text(encoding="utf-8"))

    out_path = Path(args.out) if args.out else (
        Path(args.out_base) / DEFAULT_MERGED_SUBDIR / f"bias_study_{args.fit_range}.json"
    )

    job_outputs = load_all_job_outputs(primary_dir, *extra_dirs)
    if not job_outputs:
        raise SystemExit(f"no job output JSONs found under {primary_dir} or any --extra-jobs-dir")

    grid = build_grid(job_outputs)

    result = {
        "fit_range": args.fit_range, "n_jobs_merged": len(job_outputs),
        "sources": [str(primary_dir)] + [str(d) for d in extra_dirs],
        "per_category": {},
    }
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
        fc = r["selection"].get("fallback_c_if_applied")
        if fc:
            print(f"  fallback C would choose (NOT applied): {fc['would_choose']} "
                  f"(worst_ratio={fc['worst_ratio']:.3f}, worst S_spur={fc['worst_abs_mean_S_events']:.1f} "
                  f"events = {fc['worst_abs_mean_S_pct_of_expected_yield']:.1f}% of expected yield)")


if __name__ == "__main__":
    main()
