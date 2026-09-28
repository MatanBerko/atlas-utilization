#!/usr/bin/env python
"""
Independent readback verification using REAL PyROOT (not uproot) --
intended to be run under a CVMFS LCG view providing ROOT 6.40.02 on
x86_64-el9-gcc13-opt (matching this cluster), e.g.:

    source /cvmfs/sft.cern.ch/lcg/views/LCG_110/x86_64-el9-gcc13-opt/setup.sh
    python3 verify_with_real_root.py --uncropped <path> --cropped <path>

Checks (real ROOT TH1F API, not uproot):
  - both files open and every key is a TH1F
  - histogram COUNT matches between uncropped and cropped files
  - every cropped histogram's bin 1 (GetBinContent(1)) is non-empty
  - every cropped histogram's contents equal the uncropped version's
    contents over the kept (non-empty) range exactly

No shared-repo imports -- deliberately standalone (this environment does
not have the atlas-pipeline conda env's packages).
"""
from __future__ import annotations

import argparse
import json
import sys


def main():
    import ROOT

    p = argparse.ArgumentParser()
    p.add_argument("--uncropped", required=True)
    p.add_argument("--cropped", required=True)
    p.add_argument("--out-json", required=True)
    args = p.parse_args()

    f_un = ROOT.TFile.Open(args.uncropped)
    f_cr = ROOT.TFile.Open(args.cropped)
    if not f_un or f_un.IsZombie():
        print(f"STOP: could not open {args.uncropped}", file=sys.stderr)
        sys.exit(1)
    if not f_cr or f_cr.IsZombie():
        print(f"STOP: could not open {args.cropped}", file=sys.stderr)
        sys.exit(1)

    keys_un = sorted(k.GetName() for k in f_un.GetListOfKeys())
    keys_cr = sorted(k.GetName() for k in f_cr.GetListOfKeys())

    problems = []
    if len(keys_un) != len(keys_cr):
        problems.append(f"histogram COUNT mismatch: uncropped={len(keys_un)} cropped={len(keys_cr)}")
    if set(keys_un) != set(keys_cr):
        problems.append("histogram NAME sets differ")

    n_checked = 0
    n_bin1_nonzero = 0
    for key in keys_cr:
        h_cr = f_cr.Get(key)
        h_un = f_un.Get(key)
        if not isinstance(h_cr, ROOT.TH1F) or not isinstance(h_un, ROOT.TH1F):
            problems.append(f"{key}: not a TH1F in one of the files")
            continue
        n_checked += 1

        bin1 = h_cr.GetBinContent(1)
        if bin1 > 0:
            n_bin1_nonzero += 1
        else:
            problems.append(f"{key}: cropped bin 1 is EMPTY")

        # Find the uncropped histogram's own first/last filled bin, and
        # verify the cropped histogram's contents equal that window exactly.
        n_un = h_un.GetNbinsX()
        first_un = next((b for b in range(1, n_un + 1) if h_un.GetBinContent(b) > 0), None)
        last_un = next((b for b in range(n_un, 0, -1) if h_un.GetBinContent(b) > 0), None)
        if first_un is None:
            problems.append(f"{key}: uncropped histogram is entirely empty")
            continue
        expected_n_bins = last_un - first_un + 1
        if h_cr.GetNbinsX() != expected_n_bins:
            problems.append(f"{key}: cropped n_bins={h_cr.GetNbinsX()} != expected {expected_n_bins}")
            continue
        mismatch = False
        for i, b in enumerate(range(first_un, last_un + 1), start=1):
            if h_cr.GetBinContent(i) != h_un.GetBinContent(b):
                mismatch = True
                break
        if mismatch:
            problems.append(f"{key}: cropped contents differ from uncropped's expected window")

        expected_low = h_un.GetXaxis().GetBinLowEdge(first_un)
        expected_high = h_un.GetXaxis().GetBinUpEdge(last_un)
        actual_low = h_cr.GetXaxis().GetBinLowEdge(1)
        actual_high = h_cr.GetXaxis().GetBinUpEdge(h_cr.GetNbinsX())
        if abs(actual_low - expected_low) > 1e-6 or abs(actual_high - expected_high) > 1e-6:
            problems.append(f"{key}: cropped edges [{actual_low},{actual_high}] != expected [{expected_low},{expected_high}]")

    result = {
        "uncropped_file": args.uncropped,
        "cropped_file": args.cropped,
        "root_version": ROOT.gROOT.GetVersion(),
        "n_histograms_uncropped": len(keys_un),
        "n_histograms_cropped": len(keys_cr),
        "n_checked": n_checked,
        "n_bin1_nonzero": n_bin1_nonzero,
        "n_problems": len(problems),
        "problems": problems[:50],
        "all_checks_passed": len(problems) == 0,
    }
    with open(args.out_json, "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != "problems"}, indent=2))
    if problems:
        print(f"STOP: {len(problems)} problem(s) found (see {args.out_json})", file=sys.stderr)
        for prob in problems[:20]:
            print(f"  - {prob}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: real ROOT {ROOT.gROOT.GetVersion()} confirms all {n_checked} cropped histograms "
          f"have non-empty bin 1 and match the uncropped version over the kept range exactly.")


if __name__ == "__main__":
    main()
