#!/usr/bin/env python
"""
Phase-1 MC weights task, amendment A4: prove the default-preserving
`make_fixed_grid_histogram`/`to_writable_th1f` extension in
studies/m0m1j0_cms/histograms.py changes NOTHING for the data path.

Two checks, both must pass:
  1. SYNTHETIC: a small array with NaNs, values at/near the grid edges,
     and an out-of-range value, run through make_fixed_grid_histogram with
     no weights argument at all (old call style) vs weights=None (new
     call style, the only style the function now supports beyond the old
     one) -- bin contents and edges must be bit-identical, and the return
     must still be a 2-tuple (not the 3-tuple sumw2 path).
  2. REAL DATA: a real, already-produced DoubleMuon data job's
     mass_by_category.npz (already on the cluster, NOT reprocessed or
     re-selected -- this script only re-runs the histogram-FILL step on
     its already-saved raw mass arrays) is fed through the OLD signature
     (no second argument) and the NEW signature (weights=None) for every
     category present, and the two outputs are compared bin-for-bin.

Usage:
    python prove_default_preserving.py \
        --real-npz /storage/agrp/berkom/atlas-utilization/output/m0m1j0_full_v2/job_5/mass_by_category.npz \
        --out studies/cms_mc_weights/phase1/prove_default_preserving_result.json

If --real-npz is omitted, only the synthetic check runs (still useful,
e.g. on a machine with no cluster access) -- the result JSON records
which checks actually ran.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.m0m1j0_cms.histograms import make_fixed_grid_histogram  # noqa: E402


def _old_make_fixed_grid_histogram(values):
    """A frozen copy of the function's PRE-A4 body (git history,
    studies/m0m1j0_cms/histograms.py, commit 3930d88 -- the design-branch
    tip this phase-1 branch was built from), kept here ONLY as the "old"
    reference implementation for this proof script, never imported or
    used anywhere else. This is the one deliberate, narrowly-scoped
    exception to "no copies of shared logic" in this phase-1 task -- its
    entire purpose is to BE the pre-change baseline to diff against."""
    import math
    from studies.m0m1j0_cms.histograms import (
        FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV, BIN_WIDTH_GEV, _n_bins,
    )
    import awkward as ak

    n_bins = _n_bins()
    counts = np.zeros(n_bins, dtype=np.float64)
    edges = np.linspace(FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV, n_bins + 1)

    values_np = ak.to_numpy(values) if not isinstance(values, np.ndarray) else values
    finite = values_np[~np.isnan(values_np)]
    nudged = np.where(finite == FIXED_MASS_MAX_GEV, math.nextafter(FIXED_MASS_MAX_GEV, FIXED_MASS_MIN_GEV), finite)
    in_range = (nudged >= FIXED_MASS_MIN_GEV) & (nudged < FIXED_MASS_MAX_GEV)
    bin_idx = np.floor((nudged[in_range] - FIXED_MASS_MIN_GEV) / BIN_WIDTH_GEV).astype(np.int64)
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)
    np.add.at(counts, bin_idx, 1.0)
    return counts, edges


def run_synthetic_check() -> dict:
    values = np.array([
        np.nan, 0.0, 5.0, 9999.999, 10000.0, 10000.0000001, -5.0, 5000.123, np.nan, 250.0,
    ])
    old_counts, old_edges = _old_make_fixed_grid_histogram(values)
    new_counts, new_edges = make_fixed_grid_histogram(values)  # weights=None default
    new_counts_explicit, new_edges_explicit = make_fixed_grid_histogram(values, weights=None)

    ok_vs_default = np.array_equal(old_counts, new_counts) and np.array_equal(old_edges, new_edges)
    ok_vs_explicit_none = np.array_equal(old_counts, new_counts_explicit) and np.array_equal(old_edges, new_edges_explicit)
    return {
        "n_input_values": int(len(values)),
        "old_total_entries": float(old_counts.sum()),
        "new_total_entries_default": float(new_counts.sum()),
        "new_total_entries_explicit_none": float(new_counts_explicit.sum()),
        "bin_contents_identical_vs_default_call": bool(ok_vs_default),
        "bin_contents_identical_vs_explicit_weights_none": bool(ok_vs_explicit_none),
        "return_is_still_2_tuple": True,  # would have raised on unpack above if not
        "PASS": bool(ok_vs_default and ok_vs_explicit_none),
    }


def run_real_data_check(npz_path: Path) -> dict:
    with np.load(npz_path, allow_pickle=True) as npz:
        categories = npz["category"]
        masses = npz["m0m1j0_raw_gev"]

    per_category = {}
    all_ok = True
    for cat in np.unique(categories):
        mask = categories == cat
        cat_mass = masses[mask]
        old_counts, old_edges = _old_make_fixed_grid_histogram(cat_mass)
        new_counts, new_edges = make_fixed_grid_histogram(cat_mass)
        ok = np.array_equal(old_counts, new_counts) and np.array_equal(old_edges, new_edges)
        all_ok = all_ok and ok
        per_category[str(cat)] = {
            "n_raw_events": int(mask.sum()),
            "old_total_entries": float(old_counts.sum()),
            "new_total_entries": float(new_counts.sum()),
            "bin_contents_identical": bool(ok),
        }

    return {
        "npz_path": str(npz_path),
        "n_categories": len(per_category),
        "per_category": per_category,
        "PASS": bool(all_ok),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--real-npz", default=None)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    result = {"synthetic_check": run_synthetic_check()}
    if args.real_npz:
        result["real_data_check"] = run_real_data_check(Path(args.real_npz))
    else:
        result["real_data_check"] = {"skipped": True, "reason": "--real-npz not given"}

    overall_pass = result["synthetic_check"]["PASS"] and result["real_data_check"].get(
        "PASS", True if result["real_data_check"].get("skipped") else False
    )
    result["OVERALL_PASS"] = bool(overall_pass)

    print(json.dumps(result, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")

    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
