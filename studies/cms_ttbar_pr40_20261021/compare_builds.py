#!/usr/bin/env python
"""
Bit-for-bit comparison of two MC builder ROOT files (study step 5:
build_exact == build_base). Same key set; for every TH1D the bin contents
and the Sumw2 variances (flow bins included) equal byte for byte, and the
edges, title and entry count are identical.

Read-only. Writes one JSON. Run as a PBS job (cluster/pbs_post.sh WHAT=compare).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import uproot


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    fa, fb = uproot.open(args.a), uproot.open(args.b)
    ka = {k.split(";")[0] for k in fa.keys()}
    kb = {k.split(";")[0] for k in fb.keys()}
    diffs = []
    n_bins = 0
    for k in sorted(ka & kb):
        ha, hb = fa[k], fb[k]
        va, vb = ha.values(flow=True), hb.values(flow=True)
        sa, sb = ha.variances(flow=True), hb.variances(flow=True)
        n_bins += va.size
        same = (va.tobytes() == vb.tobytes() and sa.tobytes() == sb.tobytes()
                and np.array_equal(ha.axis().edges(), hb.axis().edges())
                and ha.member("fTitle") == hb.member("fTitle")
                and ha.member("fEntries") == hb.member("fEntries")
                and ha.classname == hb.classname)
        if not same:
            diffs.append(k)
    out = {"a": args.a, "b": args.b, "n_keys_a": len(ka), "n_keys_b": len(kb),
           "only_in_a": sorted(ka - kb)[:50], "only_in_b": sorted(kb - ka)[:50],
           "n_compared": len(ka & kb), "n_bins_compared_incl_flow": n_bins,
           "n_different": len(diffs), "different": diffs[:50]}
    out["identical"] = ka == kb and not diffs
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1))
    return 0 if out["identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
