#!/usr/bin/env python
"""
Background-model task, Part 4: generate the REDUCED bias-study job list
on the 110-180 GeV range -- nominal-leakage truths only (all 4 truth
families, since Part 2's 110-180 order selection dropped none), m_H=125
only, >= 500 toys, restricted to a specific set of test functions (the
chosen function from the main 105-180 study plus its two runners-up --
NOT knowable until that study's `merge_bias_results.py` output exists).

ELIGIBILITY RULE (added 18 Sep 2026, see merge_bias_results.py's module
docstring and BACKGROUND_MODEL_REPORT.md's "Fit-reliability eligibility
rule" section): "chosen function + 2 runners-up" MUST be read from the
merged 105-180 result's `per_category.<cat>.selection.passing_functions_ranked`
list -- that list already excludes any function marked ineligible on
fit-reliability grounds (fail_fraction > 0.05, or too few successful
toys, in ANY cell), not just functions failing the 0.20 spurious-signal
ratio. Do NOT pick runners-up from `worst_ratio_by_test_function` (that
dict lists EVERY test function, including ineligible ones, purely for
visibility) -- only `passing_functions_ranked` reflects both criteria.

Usage (fill in --test-functions from the merged 105-180 result's
`passing_functions_ranked` once available -- see BACKGROUND_MODEL_REPORT.md
Part 4):
    python studies/hgg_cms/background_model/cluster/make_job_list_part4.py \\
        --order-selection-json studies/hgg_cms/background_model/results/order_selection_110_180.json \\
        --out /tmp/job_list_110_180_part4.txt
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CATEGORIES = ["EBEB", "notEBEB"]
TRUTH_FAMILIES = ["bernstein", "expsum", "powersum", "laurent"]
N_TOYS = 500
MASS = 125
SEED_BASE = 20260918900


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--order-selection-json", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    config = json.loads(Path(args.order_selection_json).read_text(encoding="utf-8"))

    lines = []
    idx = 1
    for cat in CATEGORIES:
        for fam in TRUTH_FAMILIES:
            if config[cat][fam]["selection"]["final_selected_order"] is None:
                print(f"skipping {cat}/{fam} as a truth model: dropped (fails GOF everywhere)")
                continue
            seed = SEED_BASE + idx
            lines.append(f"{cat} {fam} nominal {MASS} {N_TOYS} {seed}")
            idx += 1

    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} jobs to {args.out}")
    print(f"qsub array range: -J 1-{len(lines)}")
    print("Remember to pass -v TEST_FUNCTIONS=<family:order,family:order,family:order> "
          "(the chosen function + 2 runners-up, taken from the merged 105-180 result's "
          "per_category.<cat>.selection.passing_functions_ranked -- NOT worst_ratio_by_test_function, "
          "which includes ineligible functions too) to qsub.")


if __name__ == "__main__":
    main()
