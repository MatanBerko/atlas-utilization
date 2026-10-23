#!/usr/bin/env python
"""
Sync with upstream #39 #40 #42, step 4: compare two DATA per-file trees with
the UNCHANGED studies/mcport_validation_20261014/compare.py.

Same wrapper as studies/sync_35_20261019/cluster/compare_data_runs.py, with
the dataset list as an argument: compare.py's `runs` command loops over its
own DATASETS x N_FILES_PER_DATASET (4 datasets x 2 files); this proof runs
file 0 of two (master) or five (data branch) datasets, so the wrapper sets
those two module constants and calls compare.cmd_runs itself -- the
comparison code is not touched.

Usage:
    python compare_data_runs.py --compare-dir <dir holding compare.py> \
        --datasets DoubleMuon,DoubleEG --a <old runs dir> --b <new runs dir> --out <json>
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare-dir", required=True)
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sys.path.insert(0, args.compare_dir)
    import compare
    compare.DATASETS = tuple(args.datasets.split(","))
    compare.N_FILES_PER_DATASET = 1
    compare.cmd_runs(argparse.Namespace(a=args.a, b=args.b, out=args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
