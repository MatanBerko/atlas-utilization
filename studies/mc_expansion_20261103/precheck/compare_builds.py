#!/usr/bin/env python
"""Compare two MC builds file by file and histogram by histogram (task A1 step 3). PBS job (reads ROOT).

  A vs B: the 13 delivered re-runs built with registry v3 (default) and with registry v4 -> must be
          identical (v4 carries the 13 v3 entries unchanged);
  C vs D: 54 new + the 13 delivered, once from the 3 Nov re-runs, once from the 25 Oct outputs
          (--extra-runs-dir, read only) -> identical iff the 25 Oct outputs can be reused as they are.
Exact comparison: same ROOT file names, same histogram keys, identical edges, contents, variances;
and in the build reports the same per-sample sigma_eff, Sigma-w, normalisation factor.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import uproot


def hists(path):
    out = {}
    with uproot.open(path) as f:
        for k in f.keys(cycle=False):
            h = f[k]
            if hasattr(h, "values"):
                out[k] = (np.asarray(h.values(flow=True)), np.asarray(h.variances(flow=True)), np.asarray(h.axis().edges()))
    return out


def compare(a: Path, b: Path) -> dict:
    fa = {p.name: p for p in a.glob("*.root")}
    fb = {p.name: p for p in b.glob("*.root")}
    res = {"files_only_in_a": sorted(set(fa) - set(fb)), "files_only_in_b": sorted(set(fb) - set(fa)), "files": {}}
    for n in sorted(set(fa) & set(fb)):
        ha, hb = hists(fa[n]), hists(fb[n])
        diff = [k for k in set(ha) & set(hb)
                if not all(np.array_equal(x, y) for x, y in zip(ha[k], hb[k]))]
        res["files"][n] = {"n_hist": len(ha), "keys_only_a": sorted(set(ha) - set(hb))[:10],
                           "keys_only_b": sorted(set(hb) - set(ha))[:10], "n_different": len(diff), "different": sorted(diff)[:10]}
    ra = json.loads(next(a.glob("*_build_report.json")).read_text())["samples"]
    rb = json.loads(next(b.glob("*_build_report.json")).read_text())["samples"]
    keys = ("cross_section_pb_sigma_eff", "sigma_w_over_surviving_files", "normalisation_factor", "n_files_included")
    res["report_differences"] = {r: {k: [ra[r].get(k), rb[r].get(k)] for k in keys if ra[r].get(k) != rb[r].get(k)}
                                 for r in set(ra) & set(rb)}
    res["report_differences"] = {r: v for r, v in res["report_differences"].items() if v}
    res["samples_only_in_a"] = sorted(set(ra) - set(rb))
    res["samples_only_in_b"] = sorted(set(rb) - set(ra))
    res["identical"] = (not res["files_only_in_a"] and not res["files_only_in_b"] and not res["report_differences"]
                        and not res["samples_only_in_a"] and not res["samples_only_in_b"]
                        and all(not v["keys_only_a"] and not v["keys_only_b"] and v["n_different"] == 0 for v in res["files"].values()))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", nargs=2, action="append", required=True, metavar=("A", "B"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {}
    for x, y in a.pair:
        r = compare(Path(x), Path(y))
        out[f"{Path(x).name}_vs_{Path(y).name}"] = r
        print(Path(x).name, "vs", Path(y).name, "IDENTICAL" if r["identical"] else "DIFFERENT",
              len(r["files"]), "common ROOT files", {k: v["n_different"] for k, v in r["files"].items() if v["n_different"]})
    Path(a.out).write_text(json.dumps(out, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
