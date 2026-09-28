#!/usr/bin/env python
"""
Part 2/4 supporting evidence -- uses a REAL ROOT (see REJECTION_REPORT.md
Part 2 for where one was found: CVMFS, no cluster env touched) to build a
TH1F exactly the way services/pipelines/histograms_pipeline.py does
(same constructor call, same fixed 0-10,000 GeV range, same real
hist.Fill() loop, same trim_empty_tail function copied verbatim from
that file), and reports its on-disk fingerprint -- to settle, with a
direct test rather than a read of the code alone, three open questions:

  1. Does a genuinely ROOT-Fill()'d histogram have non-zero fTsumwx/
     fTsumwx2 (our own studies/m0m1j0_cms/histograms.py's to_writable_th1f
     hardcodes these to 0.0 -- is that a real difference from what real
     ROOT itself produces)?
  2. Does a fresh, un-Sumw2()'d ROOT.TH1F have an empty fSumw2 array by
     ROOT's own default (matching what our files show), or does ROOT
     allocate one automatically?
  3. Does real ROOT's own trim_empty_tail (SetRangeUser) produce the same
     on-disk fFirst/fLast/kAxisRange encoding our uproot-based
     workaround (_set_trim_empty_tail_range) does -- previously flagged
     UNVERIFIED in histograms.py's own docstring because no real ROOT was
     reachable at the time that code was written?

Run with a real ROOT's own python3 (see REJECTION_REPORT.md Part 2).
Writes two tiny ROOT files (not committed -- scratch only) and reports
everything needed to answer the three questions above as JSON.

Usage:
    python3 root_fingerprint_test.py --out <path.json> --scratch-dir <dir>
"""
from __future__ import annotations

import argparse
import json
import os

import ROOT

KAXISRANGE_BIT = 1 << 11


def trim_empty_tail(hist: "ROOT.TH1F") -> None:
    """Copied verbatim from services/pipelines/histograms_pipeline.py:26-41."""
    last_filled = 0
    for b in range(hist.GetNbinsX(), 0, -1):
        if hist.GetBinContent(b) > 0:
            last_filled = b
            break
    if last_filled > 0:
        hist.GetXaxis().SetRangeUser(
            hist.GetXaxis().GetXmin(),
            hist.GetBinLowEdge(last_filled + 1),
        )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--scratch-dir", required=True)
    args = p.parse_args()
    os.makedirs(args.scratch_dir, exist_ok=True)

    result = {"root_version": ROOT.gROOT.GetVersion()}

    # ---- Test 1: fresh TH1F, real .Fill() calls, no trim, no Sumw2() ----
    values = [150.0, 155.0, 160.0, 160.0, 170.0]
    h1 = ROOT.TH1F("ROI_test_width_10", "ROI_test_width_10", 1000, 0.0, 10000.0)
    for v in values:
        h1.Fill(v)
    path1 = os.path.join(args.scratch_dir, "real_root_test.root")
    f1 = ROOT.TFile(path1, "RECREATE")
    h1.Write()
    f1.Close()
    result["test1_fresh_filled_histogram"] = {
        "input_values": values,
        "expected_sum_x": sum(values),
        "expected_sum_x2": sum(v * v for v in values),
        "class_version": h1.Class().GetClassVersion(),
        "GetSumw2N": h1.GetSumw2N(),
        "fTsumwx_via_getter": h1.GetMean() * h1.GetEntries(),  # cross-check only
        "written_path": path1,
    }

    # ---- Test 2: same histogram, but run the real trim_empty_tail ----
    h2 = ROOT.TH1F("ROI_realtrim_width_10", "ROI_realtrim_width_10", 1000, 0.0, 10000.0)
    for v in [142.0, 151.0, 151.0, 163.0]:
        h2.Fill(v)
    trim_empty_tail(h2)
    path2 = os.path.join(args.scratch_dir, "real_root_trimmed.root")
    f2 = ROOT.TFile(path2, "RECREATE")
    h2.Write()
    f2.Close()
    result["test2_trimmed_histogram"] = {
        "GetFirst": h2.GetXaxis().GetFirst(),
        "GetLast": h2.GetXaxis().GetLast(),
        "TestBit_kAxisRange": bool(h2.GetXaxis().TestBit(KAXISRANGE_BIT)),
        "written_path": path2,
    }

    with open(args.out, "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps(result, indent=2))
    print(f"wrote {args.out}")
    print("Now re-open both written files with uproot (a different environment -- "
          "see REJECTION_REPORT.md Part 2) to read back the raw on-disk fFirst/fLast/"
          "@fBits/fSumw2/fTsumwx members and compare against this test's own values.")


if __name__ == "__main__":
    main()
