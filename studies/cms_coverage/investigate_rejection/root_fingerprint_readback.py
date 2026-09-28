#!/usr/bin/env python
"""
Companion to root_fingerprint_test.py: reads the two ROOT files that
script wrote (with a real ROOT) back using uproot instead (the cluster's
shared atlas-pipeline conda env -- no PyROOT there, see
studies/m0m1j0_cms/histograms.py's own docstring) and reports the raw
on-disk members, for direct comparison against root_fingerprint_test.py's
own JSON output (produced by the real-ROOT side of the same two files).

Usage (with the cluster's normal atlas-pipeline env, NOT a real-ROOT env):
    python root_fingerprint_readback.py --scratch-dir <same dir> --out <path.json>
"""
from __future__ import annotations

import argparse
import json
import os

import uproot

KAXISRANGE_BIT = 1 << 11


def read_one(path: str, key: str) -> dict:
    f = uproot.open(path)
    h = f[key]
    xaxis = h.member("fXaxis")
    fsumw2 = h.member("fSumw2")
    return {
        "classname": h.classname,
        "class_version": h.class_version,
        "fTsumwx": float(h.member("fTsumwx")),
        "fTsumwx2": float(h.member("fTsumwx2")),
        "fSumw2_length": len(fsumw2) if hasattr(fsumw2, "__len__") else None,
        "raw_fFirst": int(xaxis.member("fFirst")),
        "raw_fLast": int(xaxis.member("fLast")),
        "raw_fBits": int(xaxis.member("@fBits")),
        "kAxisRange_bit_set": bool(int(xaxis.member("@fBits")) & KAXISRANGE_BIT),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scratch-dir", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    result = {
        "test1_fresh_filled_histogram_via_uproot": read_one(
            os.path.join(args.scratch_dir, "real_root_test.root"), "ROI_test_width_10"
        ),
        "test2_trimmed_histogram_via_uproot": read_one(
            os.path.join(args.scratch_dir, "real_root_trimmed.root"), "ROI_realtrim_width_10"
        ),
    }
    with open(args.out, "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps(result, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
