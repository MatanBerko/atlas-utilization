#!/usr/bin/env python
"""
Part 2 -- open our delivered ROOT file with a REAL ROOT/PyROOT (not
uproot) and report what ROOT itself says about each histogram. Run this
with a real ROOT's own python3 (see REJECTION_REPORT.md Part 2 for where
one was found and how it was set up) -- NOT the cluster's shared
atlas-pipeline conda env, which has no PyROOT (documented in
studies/m0m1j0_cms/histograms.py's own module docstring).

Usage (after sourcing a real ROOT's setup.sh):
    python3 root_probe.py --root-file <path> --out <path.json>
"""
from __future__ import annotations

import argparse
import json
import sys

import ROOT


def probe_one(key: str, hist) -> dict:
    n_bins = hist.GetNbinsX()
    # Peak bin -- the bin with the largest content, for GetBinError there.
    peak_bin = hist.GetMaximumBin()
    return {
        "root_key": key,
        "IsA": hist.IsA().GetName(),
        "GetNbinsX": n_bins,
        "GetBinContent_1": hist.GetBinContent(1),
        "GetEntries": hist.GetEntries(),
        "GetMean": hist.GetMean(),
        "GetRMS": hist.GetRMS(),
        "peak_bin_index": peak_bin,
        "peak_bin_content": hist.GetBinContent(peak_bin),
        "GetBinError_peak_bin": hist.GetBinError(peak_bin),
        "GetSumw2N": hist.GetSumw2N(),
        "GetXaxis_GetXmin": hist.GetXaxis().GetXmin(),
        "GetXaxis_GetXmax": hist.GetXaxis().GetXmax(),
        "GetXaxis_GetFirst": hist.GetXaxis().GetFirst(),
        "GetXaxis_GetLast": hist.GetXaxis().GetLast(),
        "Integral": hist.Integral(),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root-file", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    ROOT.gErrorIgnoreLevel = 0  # show every warning, don't suppress anything

    f = ROOT.TFile.Open(args.root_file, "READ")
    if not f or f.IsZombie():
        print(f"STOP: ROOT could not open {args.root_file} (IsZombie or null)", file=sys.stderr)
        sys.exit(1)

    keys = sorted(set(k.GetName() for k in f.GetListOfKeys()))
    print(f"ROOT opened {args.root_file} without error; {len(keys)} keys found.")

    entries = []
    n_load_warnings = 0
    for key in keys:
        obj = f.Get(key)
        if not obj:
            n_load_warnings += 1
            entries.append({"root_key": key, "LOAD_FAILED": True})
            continue
        entries.append(probe_one(key, obj))
    f.Close()

    summary = {
        "root_version": ROOT.gROOT.GetVersion(),
        "source_file": args.root_file,
        "n_keys": len(keys),
        "n_load_failures": n_load_warnings,
        "GetBinContent_1_all_zero": all(e.get("GetBinContent_1") == 0.0 for e in entries if "GetBinContent_1" in e),
        "GetSumw2N_unique_values": sorted(set(e.get("GetSumw2N") for e in entries if "GetSumw2N" in e)),
    }

    out = {"summary": summary, "histograms": entries}
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
