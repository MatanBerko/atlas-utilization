#!/usr/bin/env python
"""
Step 7, finding (iv) (ttbar_count_vs_atlas): is upstream #27 -- the
outlier split aligned to the histogram bin edges -- present in PR #31?

Answered by RUNNING the function, not by reading it. The script is
side-agnostic (same pattern as step2_enumerate.py / step7_findings_check.py):
it is executed once per repo with that repo on PYTHONPATH, imports that
repo's own services.pipelines.post_processing_pipeline, and runs
_split_by_first_empty_bin on a fixed set of probe arrays. The three JSON
outputs -- ours, PR #31, upstream master -- are then compared.

Probe 2 below is the decisive one: 40 values at 205, 40 at 210 and 40 at
250 GeV. On the 10 GeV histogram grid the bin [220, 230) is empty and is
the first empty bin at index >= 2, so an aligned implementation splits
there and moves the 250 GeV cluster into the outlier array. An
implementation that derives its edges from min/max with linspace puts its
first empty bin at index 1, which the shared `<= 1` guard rejects, so it
does not split at all and keeps all 120 values in the main array.

Usage:
    PYTHONPATH=<repo> python step7_split_probe.py --side <name> --repo <repo> --out <json>
"""
from __future__ import annotations

import argparse
import json
import logging
import os

import numpy as np

LOGGER = logging.getLogger("step7_split_probe")
logging.basicConfig(level=logging.ERROR)

BIN_WIDTH = 10.0

PROBES = {
    "probe1_clean_gap": np.concatenate([
        np.full(40, 205.0), np.full(40, 215.0), np.full(40, 345.0)]),
    "probe2_decisive_gap_at_220": np.concatenate([
        np.full(40, 205.0), np.full(40, 210.0), np.full(40, 250.0)]),
    "probe3_no_gap": np.concatenate([
        np.full(40, 205.0), np.full(40, 212.0), np.full(40, 221.0)]),
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--side", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    import services.pipelines.post_processing_pipeline as pp
    resolved = os.path.realpath(pp.__file__)
    expected = os.path.realpath(
        os.path.join(args.repo, "services", "pipelines", "post_processing_pipeline.py"))
    if resolved != expected:
        raise SystemExit(f"WRONG REPO: imported {resolved}, expected {expected}")

    results = {}
    for name, arr in PROBES.items():
        main_arr, outliers = pp._split_by_first_empty_bin(arr.copy(), BIN_WIDTH, LOGGER)
        peak = pp._find_rightmost_highest_peak(arr.copy(), BIN_WIDTH, LOGGER)
        results[name] = {
            "n_input": int(arr.size),
            "n_main": int(main_arr.size),
            "n_outliers": int(outliers.size),
            "did_split": bool(outliers.size > 0),
            "max_of_main": float(main_arr.max()) if main_arr.size else None,
            "min_of_outliers": float(outliers.min()) if outliers.size else None,
            "peak_mass": None if peak is None else float(peak),
        }

    out = {
        "side": args.side,
        "repo": args.repo,
        "repo_head": os.environ.get("REPO_HEAD", ""),
        "imported_from": resolved,
        "has_aligned_bin_edges_helper": hasattr(pp, "_aligned_bin_edges"),
        "bin_width_gev": BIN_WIDTH,
        "probes": {k: [float(x) for x in np.unique(v)] for k, v in PROBES.items()},
        "results": results,
    }
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    print(f"[{args.side}] has _aligned_bin_edges: {out['has_aligned_bin_edges_helper']}")
    for name, r in results.items():
        print(f"[{args.side}] {name}: split={r['did_split']} "
              f"main={r['n_main']} outliers={r['n_outliers']}")
    print(f"[{args.side}] wrote {args.out}")


if __name__ == "__main__":
    main()
