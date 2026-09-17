#!/usr/bin/env python
"""
Background-model task, bias-study rerun 1: generate the job list for
testing exactly ONE new candidate per category (EBEB bernstein_6,
notEBEB bernstein_7) against the SAME 60 cells (4 truth families x 3
leakage variants x 5 masses) and the SAME per-cell seeds as the first
run -- see BACKGROUND_MODEL_REPORT.md's "Pre-declared selection
procedure" section for why exactly these two candidates.

SEED IDENTITY BY CONSTRUCTION: this script imports `make_job_list.py`'s
own CATEGORIES / TRUTH_FAMILIES / LEAKAGE_VARIANTS / MASS_TOYS /
SEED_BASE constants and walks the identical nested loop in the identical
order, so `idx` (and therefore `seed = SEED_BASE + idx`) is guaranteed
byte-for-byte identical to the first run's job list for every
(category, truth_family, leakage_variant, mass) cell -- not
re-derived/copied by hand, which could silently drift. See
`tests/test_bias_rerun_seed_identity.py` for the proof that reusing
this seed reproduces the exact same pseudo-datasets `run_bias_job.py`'s
own toy loop generates.

Output format (7 fields, one more than the first run's job list):
`category truth_family leakage_variant mass n_toys seed test_function`

Usage:
    python studies/hgg_cms/background_model/cluster/make_job_list_rerun1.py \\
        --order-selection-json studies/hgg_cms/background_model/results/order_selection_105_180.json \\
        --out /tmp/job_list_105_180_rerun1.txt
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.background_model.cluster.make_job_list import (  # noqa: E402
    CATEGORIES, TRUTH_FAMILIES, LEAKAGE_VARIANTS, MASS_TOYS, SEED_BASE,
)

# The ONE new candidate per category -- see BACKGROUND_MODEL_REPORT.md's
# "Pre-declared selection procedure" section, point 1.
NEW_TEST_FUNCTION = {"EBEB": "bernstein:6", "notEBEB": "bernstein:7"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--order-selection-json", required=True,
                    help="Same file as the first run's make_job_list.py -- used only to "
                         "skip a dropped truth family, identically to that script.")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    config = json.loads(Path(args.order_selection_json).read_text(encoding="utf-8"))

    lines = []
    idx = 1
    for cat in CATEGORIES:
        for fam in TRUTH_FAMILIES:
            if config[cat][fam]["selection"]["final_selected_order"] is None:
                # NOTE: matches make_job_list.py's own behavior exactly --
                # `idx` is NOT advanced here (the original script doesn't
                # either; a dropped family leaves no gap in the seed
                # sequence, it just isn't skipped over). Currently moot
                # for the 105-180 range (no family is dropped in either
                # category), but kept identical to the source it must
                # match rather than "fixed" to something the original
                # doesn't actually do.
                print(f"skipping {cat}/{fam} as a truth model: dropped (fails GOF everywhere)")
                continue
            for variant in LEAKAGE_VARIANTS:
                for mass, n_toys in MASS_TOYS.items():
                    seed = SEED_BASE + idx  # IDENTICAL formula/position to the first run
                    lines.append(f"{cat} {fam} {variant} {mass} {n_toys} {seed} {NEW_TEST_FUNCTION[cat]}")
                    idx += 1

    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} jobs to {args.out}")
    print(f"qsub array range: -J 1-{len(lines)}")


if __name__ == "__main__":
    main()
