#!/usr/bin/env python
"""
Background-model task, Part 3: generate the bias-study job grid as a
plain-text list (one line per PBS array index) --
`category truth_family leakage_variant mass n_toys seed`.

MAIN STUDY (--stage main): fit-range 105-180, all 4 truth families x 3
leakage variants x 5 masses x 2 categories = 120 jobs. 1000 toys at
125 GeV, 300 toys at the other 4 masses (per this task's own toy-count
requirement).

Seeds: deterministic, `20260918000 + array_index` (documented, not
random-per-run) -- so a resubmission of a specific failed index
reproduces exactly the same toys.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CATEGORIES = ["EBEB", "notEBEB"]
TRUTH_FAMILIES = ["bernstein", "expsum", "powersum", "laurent"]
LEAKAGE_VARIANTS = ["nominal", "leakage_plus", "leakage_minus"]
MASS_TOYS = {125: 1000, 115: 300, 120: 300, 130: 300, 135: 300}
SEED_BASE = 20260918000


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--order-selection-json", required=True,
                    help="Used only to drop any truth family that was found to fail GOF "
                         "everywhere (dropped_family_fails_gof_everywhere) -- such a family "
                         "cannot be used as a truth-generator.")
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
            for variant in LEAKAGE_VARIANTS:
                for mass, n_toys in MASS_TOYS.items():
                    seed = SEED_BASE + idx
                    lines.append(f"{cat} {fam} {variant} {mass} {n_toys} {seed}")
                    idx += 1

    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} jobs to {args.out}")
    print(f"qsub array range: -J 1-{len(lines)}")


if __name__ == "__main__":
    main()
