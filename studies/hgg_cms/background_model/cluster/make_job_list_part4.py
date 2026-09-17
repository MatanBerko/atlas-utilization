#!/usr/bin/env python
"""
Background-model task, Part 4: generate the REDUCED robustness bias-
study job list on the 110-180 GeV range -- nominal-leakage truths only
(all 4 truth families, since Part 2's 110-180 order selection dropped
none), m_H=125 only, >= 500 toys, one job per (category, truth family)
cell, each job evaluating the category's own set of test functions
(chosen function + runner-up(s)).

TEST FUNCTIONS PER CATEGORY (fixed here, read directly from the merged
105-180-with-rerun1 result's `per_category.<cat>.selection`
`fallback_c_if_applied.ranked_eligible_by_worst_ratio` -- the ranking
that already reflects BOTH the fit-reliability eligibility rule and the
0.20xsigma_S criterion, NOT `worst_ratio_by_test_function`/
`candidate_summary`, which list every candidate including ineligible
ones; see `BACKGROUND_MODEL_REPORT.md`'s "Human decision after rerun 1"
section for the underlying numbers):

  EBEB ranked-eligible:    bernstein_6, bernstein_5, expsum_3, bernstein_4, laurent_2, powersum_1
    -> chosen + 2 runners-up = bernstein_6, bernstein_5, expsum_3
  notEBEB ranked-eligible: bernstein_6, bernstein_5   (only 2 eligible candidates total)
    -> chosen + runner-up(s) = bernstein_6, bernstein_5 -- ONLY ONE runner-up
       exists for notEBEB (bernstein_7 and everything else is ineligible
       there -- see the same decision section); this is NOT an error,
       just fewer candidates than the "2 runners-up" plan assumed when
       more than 2 candidates are eligible. Recorded explicitly, not
       silently padded with something arbitrary.

Usage:
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

# Fixed from the real merged 105-180-with-rerun1 result -- see module docstring.
TEST_FUNCTIONS_PER_CATEGORY = {
    "EBEB": "bernstein:6,bernstein:5,expsum:3",
    "notEBEB": "bernstein:6,bernstein:5",
}


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
            tfs = TEST_FUNCTIONS_PER_CATEGORY[cat]
            lines.append(f"{cat} {fam} nominal {MASS} {N_TOYS} {seed} {tfs}")
            idx += 1

    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} jobs to {args.out}")
    print(f"qsub array range: -J 1-{len(lines)}")
    for cat, tfs in TEST_FUNCTIONS_PER_CATEGORY.items():
        n = len(tfs.split(","))
        print(f"  {cat}: {n} test function(s) per job -- {tfs}"
              + ("" if n >= 3 else "  (fewer than chosen+2 runners-up: only this many eligible candidates exist)"))


if __name__ == "__main__":
    main()
