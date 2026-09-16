"""
Implementation task 6, Part 3: runs A-F in the order later parts need
(D before E and F, which reuse D's saved pileup weights / E's saved
genEventSumw table). Part C is run separately (needs --lumi-csv / the
HGG_LUMI_CSV env var pointing at a locally-downloaded pp_2016lumibyls.csv
-- see part_c_run_stability.py's own module docstring) since it is the
only part needing an extra input beyond HGG_MERGED_DIR.

Usage:
    python -m studies.hgg_cms.validation.run_all
    python -m studies.hgg_cms.validation.run_all --with-part-c --lumi-csv <path>
"""
from __future__ import annotations

import argparse
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--with-part-c", action="store_true")
    p.add_argument("--lumi-csv", default=None)
    args = p.parse_args()

    from studies.hgg_cms.validation import (
        part_a_sidebands, part_b_turnon, part_d_pileup,
        part_e_expected_yields, part_f_category_composition,
    )

    print("=== Part A ===")
    part_a_sidebands.main()
    print("\n=== Part B ===")
    part_b_turnon.main()
    print("\n=== Part D ===")
    part_d_pileup.main()
    print("\n=== Part E ===")
    part_e_expected_yields.main()
    print("\n=== Part F ===")
    part_f_category_composition.main()

    if args.with_part_c:
        print("\n=== Part C ===")
        sys.argv = ["part_c_run_stability.py"]
        if args.lumi_csv:
            sys.argv += ["--lumi-csv", args.lumi_csv]
        from studies.hgg_cms.validation import part_c_run_stability
        part_c_run_stability.main()
    else:
        print("\n(skipped Part C -- pass --with-part-c --lumi-csv <path> to include it)")


if __name__ == "__main__":
    main()
