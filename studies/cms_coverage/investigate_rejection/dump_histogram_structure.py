#!/usr/bin/env python
"""
Part 1 -- complete structural dump of every histogram in a ROOT file, via
uproot (read-only; no ROOT/PyROOT needed for this part -- see Part 2 for
whether a real ROOT is reachable at all). Every field read here is a
literal member of the on-disk TH1/TAxis object as uproot decoded it from
the ROOT streamer info -- nothing computed or assumed beyond direct
arithmetic on those members (non-empty-bin search, negative/NaN check).

Usage:
    python dump_histogram_structure.py --root-file <path> --out <path.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import uproot

KAXISRANGE_BIT = 1 << 11  # TAxis.h:65, kAxisRange = BIT(11) -- same citation as
                          # studies/m0m1j0_cms/histograms.py's own _KAXISRANGE_BIT


def dump_one(key: str, hist) -> dict:
    xaxis = hist.member("fXaxis")
    values_flow = hist.values(flow=True).astype(np.float64)  # [underflow, bin1..binN, overflow]
    values = values_flow[1:-1]
    underflow = float(values_flow[0])
    overflow = float(values_flow[-1])

    nonzero_idx = np.nonzero(values > 0)[0]
    edges = hist.axis().edges().astype(np.float64)

    fsumw2 = hist.member("fSumw2")
    fsumw2_len = len(fsumw2) if hasattr(fsumw2, "__len__") else None

    has_negative = bool(np.any(values < 0) or underflow < 0 or overflow < 0)
    has_nan = bool(np.any(np.isnan(values)) or np.isnan(underflow) or np.isnan(overflow))

    entry = {
        "root_key": key,
        "classname": hist.classname,
        "class_version": hist.class_version,
        "fName": hist.member("fName"),
        "fTitle": hist.member("fTitle"),
        "n_bins": int(xaxis.member("fNbins")),
        "fXmin": float(xaxis.member("fXmin")),
        "fXmax": float(xaxis.member("fXmax")),
        "axis_fFirst": int(xaxis.member("fFirst")),
        "axis_fLast": int(xaxis.member("fLast")),
        "axis_fBits": int(xaxis.member("@fBits")),
        "axis_kAxisRange_set": bool(int(xaxis.member("@fBits")) & KAXISRANGE_BIT),
        "fEntries": float(hist.member("fEntries")),
        "fTsumw": float(hist.member("fTsumw")),
        "fTsumw2": float(hist.member("fTsumw2")),
        "fTsumwx": float(hist.member("fTsumwx")),
        "fTsumwx2": float(hist.member("fTsumwx2")),
        "fSumw2_present_nonempty": bool(fsumw2_len is not None and fsumw2_len > 0),
        "fSumw2_length": fsumw2_len,
        "bin1_content": float(values[0]) if values.size > 0 else None,
        "first_nonempty_bin_index_1based": int(nonzero_idx[0]) + 1 if nonzero_idx.size > 0 else None,
        "first_nonempty_bin_low_edge_gev": float(edges[nonzero_idx[0]]) if nonzero_idx.size > 0 else None,
        "last_nonempty_bin_index_1based": int(nonzero_idx[-1]) + 1 if nonzero_idx.size > 0 else None,
        "last_nonempty_bin_high_edge_gev": float(edges[nonzero_idx[-1] + 1]) if nonzero_idx.size > 0 else None,
        "n_nonempty_bins": int(nonzero_idx.size),
        "total_content": float(values.sum()),
        "has_negative_bin": has_negative,
        "has_nan_bin": has_nan,
        "underflow_content": underflow,
        "overflow_content": overflow,
    }
    return entry


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root-file", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    f = uproot.open(args.root_file)
    keys = sorted(set(k.split(";")[0] for k in f.keys()))

    entries = []
    for key in keys:
        hist = f[key]
        entries.append(dump_one(key, hist))

    # ---- Summary across all histograms ----
    def field_summary(fname):
        vals = [e[fname] for e in entries]
        uniq = sorted(set(vals), key=lambda x: (x is None, x))
        return {"unique_values": uniq, "n_unique": len(uniq)}

    summary = {
        "source_file": str(args.root_file),
        "n_histograms": len(entries),
        "classname": field_summary("classname"),
        "class_version": field_summary("class_version"),
        "n_bins": field_summary("n_bins"),
        "fXmin": field_summary("fXmin"),
        "fXmax": field_summary("fXmax"),
        "axis_fFirst": field_summary("axis_fFirst"),
        "axis_fLast_range": [min(e["axis_fLast"] for e in entries), max(e["axis_fLast"] for e in entries)] if entries else None,
        "axis_kAxisRange_set": field_summary("axis_kAxisRange_set"),
        "fSumw2_present_nonempty": field_summary("fSumw2_present_nonempty"),
        "bin1_content": field_summary("bin1_content"),
        "n_histograms_with_bin1_nonzero": sum(1 for e in entries if (e["bin1_content"] or 0) > 0),
        "n_histograms_with_negative_bin": sum(1 for e in entries if e["has_negative_bin"]),
        "n_histograms_with_nan_bin": sum(1 for e in entries if e["has_nan_bin"]),
        "underflow_content": field_summary("underflow_content"),
        "overflow_content": field_summary("overflow_content"),
        "n_nonempty_bins_range": [min(e["n_nonempty_bins"] for e in entries), max(e["n_nonempty_bins"] for e in entries)] if entries else None,
    }

    out = {"summary": summary, "histograms": entries}
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"wrote {args.out} ({len(entries)} histograms)")


if __name__ == "__main__":
    main()
