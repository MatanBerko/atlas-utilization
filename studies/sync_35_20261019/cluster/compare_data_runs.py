#!/usr/bin/env python
"""
Sync with upstream #35, step B: compare two DATA per-file trees with the
UNCHANGED studies/mcport_validation_20261014/compare.py.

compare.py's `runs` command loops over its own DATASETS x N_FILES_PER_DATASET
(4 datasets x 2 files). This proof runs only DoubleMuon job 0 and DoubleEG
job 0, so this wrapper narrows those two module constants and then calls
compare.cmd_runs itself -- the comparison code is not touched.

Usage:
    python compare_data_runs.py --compare-dir <dir holding compare.py> \
        --a <old runs dir> --b <new runs dir> --out <json>
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare-dir", required=True)
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sys.path.insert(0, args.compare_dir)
    import compare
    compare.DATASETS = ("DoubleMuon", "DoubleEG")
    compare.N_FILES_PER_DATASET = 1
    compare.cmd_runs(argparse.Namespace(a=args.a, b=args.b, out=args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
