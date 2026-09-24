#!/usr/bin/env python
"""
Background-model task, Part 4: applies the pre-set 110-180 GeV
robustness interpretation rule (stated BEFORE any Part 4 result exists
-- see submit_bias_study_part4.sh's own header and
BACKGROUND_MODEL_REPORT.md's "Human decision after rerun 1" section for
the 105-180 numbers this compares against):

For the CHOSEN function (bernstein_6) in each category, the 110-180 GeV
run is "robust" if BOTH:
  (a) its worst ratio at 110-180 <= its worst ratio at 105-180 + 0.10, AND
  (b) its fit-reliability fail_fraction stays <= 5% in every cell.
If EITHER fails: STOP -- this script reports the finding and does NOT
automatically change the fit range or the chosen function. That
decision, like the Fallback C decision, is for a human.

NOT RUN as part of this task -- the Part 4 cluster job hasn't been
submitted. Ready to run once
output/hgg_bias/merged/bias_study_110_180_part4.json exists (see
status_bias_study_part4.sh's own printed merge command).

Usage:
    python studies/hgg_cms/background_model/cluster/check_part4_robustness.py \\
        --part4-merged studies/hgg_cms/background_model/results/bias_study_110_180_part4.json \\
        --primary-merged studies/hgg_cms/background_model/results/bias_study_105_180_with_rerun1.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CHOSEN_FUNCTION = "bernstein_6"
RATIO_MARGIN = 0.10
MAX_FAIL_FRACTION = 0.05


def check_category(cat: str, part4: dict, primary: dict) -> dict:
    part4_ev = part4["per_category"].get(cat, {}).get("evaluations", {}).get(CHOSEN_FUNCTION)
    primary_ev = primary["per_category"].get(cat, {}).get("evaluations", {}).get(CHOSEN_FUNCTION)
    if part4_ev is None or primary_ev is None:
        return {"category": cat, "verdict": "STOP", "reason": f"{CHOSEN_FUNCTION} missing from one of the two merged results"}

    ratio_105_180 = primary_ev["worst_ratio"]
    ratio_110_180 = part4_ev["worst_ratio"]
    ratio_ok = ratio_110_180 <= ratio_105_180 + RATIO_MARGIN

    reliability_ok = part4_ev["eligible"]
    max_fail_fraction_110_180 = max((p["fail_fraction"] for p in part4_ev["all_points"]), default=None)

    robust = bool(ratio_ok and reliability_ok)
    return {
        "category": cat,
        "chosen_function": CHOSEN_FUNCTION,
        "worst_ratio_105_180": ratio_105_180,
        "worst_ratio_110_180": ratio_110_180,
        "ratio_margin_allowed": RATIO_MARGIN,
        "ratio_criterion_met": ratio_ok,
        "reliability_criterion_met": reliability_ok,
        "max_fail_fraction_110_180": max_fail_fraction_110_180,
        "verdict": "robust" if robust else "STOP -- human decision required",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--part4-merged", required=True)
    p.add_argument("--primary-merged", required=True)
    args = p.parse_args()

    part4 = json.loads(Path(args.part4_merged).read_text(encoding="utf-8"))
    primary = json.loads(Path(args.primary_merged).read_text(encoding="utf-8"))

    for cat in ("EBEB", "notEBEB"):
        result = check_category(cat, part4, primary)
        print(json.dumps(result, indent=2))
        if result["verdict"] != "robust":
            print(f"*** {cat}: NOT robust by the pre-set rule -- STOP, this needs a human decision, "
                  f"not an automatic change of fit range or function. ***")


if __name__ == "__main__":
    main()
