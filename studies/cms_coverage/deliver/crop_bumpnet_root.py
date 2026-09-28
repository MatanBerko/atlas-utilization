#!/usr/bin/env python
"""
DoubleMuon BumpNet ROOT delivery -- CROPPED versions.

The shared pipeline builds every histogram on the fixed 0-10,000 GeV grid
(FIXED_MASS_MIN_GEV/FIXED_MASS_MAX_GEV, services/pipelines/
histograms_pipeline.py), so bin 1 (0-10 GeV) is necessarily empty once
post-processing's peak-removal step drops everything below the peak.
trim_empty_tail's own axis-range trim (already applied when the two
source files were written) only changes the DISPLAY range -- the bin
CONTENTS are untouched, and a reader that inspects bin contents directly
(as the supervisor's BumpNet loader does) still sees an empty bin 1. This
script actually removes the leading (and, if present, trailing) all-empty
region: a genuinely smaller TH1F, not a display-range restriction.

Reads the two ALREADY-DELIVERED ROOT files directly (read-only --
`uproot.open`, never `uproot.recreate`, on either of them) and writes two
NEW files. This is a re-windowing of already-written histograms, not a
recomputation from the coverage shards -- guarantees identical content by
construction (same source array, just a narrower slice of it), and keeps
the two existing files completely untouched.

Reuses, unmodified: studies.m0m1j0_cms.histograms.to_writable_th1f (the
same TH1F-construction/writing code the source files were built with) and
verify_written_th1f. For a properly cropped histogram (last bin always
non-empty by construction), to_writable_th1f's own trim_empty_tail-
equivalent logic naturally sets fFirst=1/fLast=n_bins with kAxisRange set
-- which, per TAxis::GetFirst()/GetLast()'s own documented behavior
(see histograms.py's own derivation), is observably IDENTICAL to no
restriction at all (both display the full histogram) -- so nothing
extra is needed to satisfy "no display range restriction" on the cropped
files.

Usage:
    python crop_bumpnet_root.py \
        --in-dir /storage/agrp/berkom/atlas-utilization/output/deliver_doublemuon_bumpnet \
        --out-dir /storage/agrp/berkom/atlas-utilization/output/deliver_doublemuon_bumpnet
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms.histograms import (  # noqa: E402
    to_writable_th1f,
    verify_written_th1f,
    BIN_WIDTH_GEV,
)

SOURCE_TO_CROPPED = {
    "doublemuon_bumpnet_min31bins.root": "doublemuon_bumpnet_min31bins_cropped.root",
    "doublemuon_bumpnet_min26bins.root": "doublemuon_bumpnet_min26bins_cropped.root",
}


def crop_arrays(values: np.ndarray, edges: np.ndarray):
    """(cropped_values, cropped_edges, first_idx, last_idx) spanning the
    first to last non-zero bin, inclusive -- any internal zero-content
    bins between them are kept unchanged; only the leading/trailing
    all-empty region on the fixed grid is removed."""
    nonzero = np.nonzero(values > 0)[0]
    if nonzero.size == 0:
        raise ValueError("all-empty histogram -- cannot crop")
    first, last = int(nonzero[0]), int(nonzero[-1])
    return values[first:last + 1].copy(), edges[first:last + 2].copy(), first, last


def process_file(in_path: Path, out_path: Path):
    fin = uproot.open(str(in_path))
    keys = sorted(set(k.split(";")[0] for k in fin.keys()))

    written = {}
    with uproot.recreate(str(out_path)) as fout:
        for key in keys:
            hist = fin[key]
            values = hist.values().astype(np.float64)
            edges = hist.axis().edges().astype(np.float64)
            title = hist.title

            cropped_values, cropped_edges, _first, _last = crop_arrays(values, edges)

            widths = np.diff(cropped_edges)
            if not np.allclose(widths, BIN_WIDTH_GEV, atol=1e-9):
                raise AssertionError(f"{key}: cropped bin widths are not exactly {BIN_WIDTH_GEV} GeV")

            fout[key] = to_writable_th1f(cropped_values, cropped_edges, title)
            written[key] = cropped_values

    verify_written_th1f(str(out_path), written)
    return keys


def verify_and_manifest(in_path: Path, out_path: Path, keys, out_name: str, out_dir: Path):
    """Re-opens BOTH files fresh from disk (not reusing anything held in
    memory from process_file) and runs every mandatory check against what
    was actually written."""
    f_src = uproot.open(str(in_path))
    f_out = uproot.open(str(out_path))
    out_keys = sorted(set(k.split(";")[0] for k in f_out.keys()))

    problems = []
    if len(out_keys) != len(keys):
        problems.append(f"histogram COUNT mismatch: source={len(keys)} cropped={len(out_keys)}")
    if set(out_keys) != set(keys):
        problems.append("histogram NAME set differs between source and cropped file "
                         f"(only-in-source={sorted(set(keys)-set(out_keys))}, "
                         f"only-in-cropped={sorted(set(out_keys)-set(keys))})")
    if problems:
        return problems, []

    manifest = []
    n_bin1_nonzero = 0
    for key in keys:
        src_hist = f_src[key]
        src_values = src_hist.values().astype(np.float64)
        src_edges = src_hist.axis().edges().astype(np.float64)

        out_hist = f_out[key]
        out_values = out_hist.values().astype(np.float64)
        out_edges = out_hist.axis().edges().astype(np.float64)

        src_nonzero_idx = np.nonzero(src_values > 0)[0]
        expected_first, expected_last = int(src_nonzero_idx[0]), int(src_nonzero_idx[-1])
        expected_cropped_values = src_values[expected_first:expected_last + 1]
        expected_first_edge = float(src_edges[expected_first])
        expected_last_edge = float(src_edges[expected_last + 1])

        if not np.isclose(out_values.sum(), src_values.sum()):
            problems.append(f"{key}: total event count mismatch "
                             f"(source={src_values.sum()}, cropped={out_values.sum()})")

        if out_values.size != expected_cropped_values.size or not np.array_equal(out_values, expected_cropped_values):
            problems.append(f"{key}: cropped bin contents differ from the source's expected crop window")

        widths = np.diff(out_edges)
        if not np.allclose(widths, BIN_WIDTH_GEV, atol=1e-9):
            problems.append(f"{key}: cropped bin width is not exactly {BIN_WIDTH_GEV} GeV "
                             f"(got {sorted(set(np.round(widths, 6)))})")

        if not np.isclose(out_edges[0], expected_first_edge) or not np.isclose(out_edges[-1], expected_last_edge):
            problems.append(f"{key}: cropped edges [{out_edges[0]}, {out_edges[-1]}] do not match "
                             f"the source's first/last FILLED bin edges "
                             f"[{expected_first_edge}, {expected_last_edge}]")

        if out_values[0] > 0:
            n_bin1_nonzero += 1
        else:
            problems.append(f"{key}: cropped bin 1 is EMPTY -- cropping failed for this histogram")

        name = key[len("ROI_"):].rsplit("_width_", 1)[0] if key.startswith("ROI_") else key
        manifest.append({
            "name": name,
            "root_key": key,
            "n_events": int(out_values.sum()),
            "n_bins_total": int(out_values.size),
            "n_filled_bins": int(np.count_nonzero(out_values)),
            "first_bin_low_edge_gev": float(out_edges[0]),
            "last_bin_high_edge_gev": float(out_edges[-1]),
            "source_n_bins_total": int(src_values.size),
        })

    if not problems:
        print(f"  bin 1 non-empty: {n_bin1_nonzero}/{len(keys)}")

    manifest_path = out_dir / f"manifest_{out_name.replace('.root', '')}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"  wrote {manifest_path} ({len(manifest)} entries)")

    return problems, manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in-dir", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    overall = {}
    for src_name, out_name in SOURCE_TO_CROPPED.items():
        print(f"\n=== {src_name} -> {out_name} ===")
        in_path = in_dir / src_name
        out_path = out_dir / out_name
        if not in_path.exists():
            print(f"STOP: source file missing: {in_path} -- refusing to proceed.", file=sys.stderr)
            sys.exit(1)

        keys = process_file(in_path, out_path)
        print(f"wrote {out_path}: {len(keys)} histograms, verified TH1F (in-memory check)")

        print("Re-opening both files from disk for the mandatory checks...")
        problems, manifest = verify_and_manifest(in_path, out_path, keys, out_name, out_dir)
        if problems:
            print(f"STOP: {len(problems)} problem(s) found for {out_name}:", file=sys.stderr)
            for prob in problems[:30]:
                print(f"  - {prob}", file=sys.stderr)
            sys.exit(1)

        print(f"PASS: all {len(keys)} histograms in {out_name} -- exact match to source "
              f"(events, bin contents, edges, width), all with non-empty bin 1.")

        overall[out_name] = {
            "source": src_name,
            "n_histograms": len(keys),
            "n_bin1_nonzero": len(keys),
            "all_checks_passed": True,
        }

    (out_dir / "crop_summary.json").write_text(json.dumps(overall, indent=2))
    print("\n" + json.dumps(overall, indent=2))
    print("\nAll mandatory checks PASSED for both cropped files.")


if __name__ == "__main__":
    main()
