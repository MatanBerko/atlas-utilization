#!/usr/bin/env python
"""
Part 1 analysis: reads the structural dump already produced for the ATLAS
reference file (dump_histogram_structure.py's output) and answers, with
counts rather than assertions, the specific questions this task's Part 1
asks: how many pass/fail bin-1-empty; the distinct (nbins, xmin, xmax)
combinations and how many histograms have each; whether the passing ones
have genuine content in the true first bin; and whether pass/fail
correlates with object-content category (jet-only / b-jet-containing /
lepton-only / lepton+jet), imported unmodified from
studies.cms_coverage.cluster.merge_and_count (the same classifier already
used throughout this whole survey for our own CMS histograms).

Usage:
    python analyze_atlas_reference.py --dump <dump_atlas_reference.json path> --out <path.json>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_coverage.cluster.merge_and_count import object_content_category, object_count  # noqa: E402

NAME_PATTERN = re.compile(r"^ROI_mass_([a-z0-9]+)_cat_")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dump", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    d = json.loads(Path(args.dump).read_text())
    hists = d["histograms"]

    passing = [h for h in hists if (h.get("bin1_content") or 0) > 0]
    failing = [h for h in hists if not (h.get("bin1_content") or 0) > 0]

    grid_combos = Counter((h["n_bins"], h["fXmin"], h["fXmax"]) for h in hists)

    pass_by_cat = Counter()
    fail_by_cat = Counter()
    unmatched = []
    for h in hists:
        m = NAME_PATTERN.match(h["fName"])
        if not m:
            unmatched.append(h["fName"])
            continue
        cat = object_content_category(m.group(1))
        if (h.get("bin1_content") or 0) > 0:
            pass_by_cat[cat] += 1
        else:
            fail_by_cat[cat] += 1

    all_cats = sorted(set(pass_by_cat) | set(fail_by_cat))
    rate_by_cat = {}
    for cat in all_cats:
        n_pass = pass_by_cat.get(cat, 0)
        n_fail = fail_by_cat.get(cat, 0)
        total = n_pass + n_fail
        rate_by_cat[cat] = {
            "n_pass": n_pass, "n_fail": n_fail, "n_total": total,
            "pass_rate_pct": round(100.0 * n_pass / total, 1) if total else None,
        }

    # Passing histograms: confirm genuine content in bin index 1 specifically
    # (not merely "first_nonempty_bin_index_1based == 1" by coincidence of a
    # different grid -- already ruled out by grid_combos having one entry).
    passing_bin_index_check = Counter(h["first_nonempty_bin_index_1based"] for h in passing)

    result = {
        "source_dump": args.dump,
        "n_total": len(hists),
        "n_passing_bin1_gt0": len(passing),
        "n_failing_bin1_eq0": len(failing),
        "distinct_grid_nbins_xmin_xmax": [
            {"n_bins": k[0], "fXmin": k[1], "fXmax": k[2], "count": v}
            for k, v in grid_combos.items()
        ],
        "passing_first_nonempty_bin_index_distribution": dict(passing_bin_index_check),
        "pass_fail_by_object_content_category": rate_by_cat,
        "n_unmatched_names": len(unmatched),
        "unmatched_names_sample": unmatched[:10],
    }
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
