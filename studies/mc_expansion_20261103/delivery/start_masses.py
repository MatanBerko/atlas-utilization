#!/usr/bin/env python
"""Per-histogram start masses of the final MC delivery vs the delivered 25 Oct data (report only, reads only).

For every histogram of the MC file: the first filled bin of the data and of the MC (low edge in GeV; "filled" = content
!= 0, as post/checks_final.py), the common start = the later of the two, and the data and MC integrals from the common
start to the end of the axis, with data/MC there. Histograms that exist only in the MC are marked "mc_only".

    python start_masses.py --data-root <25 Oct data uncropped.root> --mc-root <final MC.root> \
        --out-csv <..._mc.start_masses.csv> --out-json <summary.json>
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

NAME = re.compile(r"^ROI_mass_([a-z0-9]+)_cat_(\d+)ex_(\d+)mx_(\d+)jx_(\d+)bx_width_10\.0$")


def read(path):
    import uproot
    out = {}
    with uproot.open(path) as f:
        for k in f.keys(cycle=False):
            if NAME.match(k):
                h = f[k]
                out[k] = (np.asarray(h.values(), float), np.asarray(h.variances(), float),
                          np.asarray(h.axis().edges(), float))
    return out


def first_last(v):
    nz = np.nonzero(v != 0)[0]
    return (int(nz[0]), int(nz[-1])) if nz.size else (None, None)


def main() -> int:
    ap = argparse.ArgumentParser()
    for a in ("--data-root", "--mc-root", "--out-csv", "--out-json"):
        ap.add_argument(a, required=True)
    a = ap.parse_args()
    for p in (a.out_csv, a.out_json):
        if Path(p).exists():
            raise SystemExit(f"refusing to overwrite {p}")
    data, mc = read(a.data_root), read(a.mc_root)
    rows, shifts, by_nlep = [], Counter(), Counter()
    for name in sorted(mc):
        m = NAME.match(name)
        e, mu, j, b = (int(x) for x in m.group(2, 3, 4, 5))
        fs = f"{e}e_{mu}m_{j}j_{b}b"
        mv, ms2, me = mc[name]
        mf, ml = first_last(mv)
        row = {"histogram": name, "final_state": fs, "status": "both" if name in data else "mc_only",
               "mc_first_filled_gev": me[mf] if mf is not None else "", "mc_last_filled_gev": me[ml + 1] if ml is not None else ""}
        if name in data:
            dv, _, de = data[name]
            assert np.array_equal(de, me), f"axis differs: {name}"
            df, dl = first_last(dv)
            c = max(df, mf)
            dsum, msum = float(dv[c:].sum()), float(mv[c:].sum())
            row.update({
                "data_first_filled_gev": de[df], "data_last_filled_gev": de[dl + 1],
                "shift_mc_minus_data_gev": me[mf] - de[df], "common_start_gev": me[c],
                "data_from_common_start": dsum, "mc_from_common_start": msum,
                "mc_stat_error_from_common_start": float(np.sqrt(ms2[c:].sum())),
                "data_over_mc_from_common_start": dsum / msum if msum else "",
                "data_own_range": float(dv.sum()), "mc_own_range": float(mv.sum()),
                "data_over_mc_own_range": float(dv.sum() / mv.sum()) if mv.sum() else ""})
            shifts[me[mf] - de[df]] += 1
            by_nlep[(e + mu, row["shift_mc_minus_data_gev"] != 0)] += 1
        rows.append(row)
    cols = ["histogram", "final_state", "status", "data_first_filled_gev", "mc_first_filled_gev",
            "shift_mc_minus_data_gev", "common_start_gev", "data_from_common_start", "mc_from_common_start",
            "mc_stat_error_from_common_start", "data_over_mc_from_common_start", "data_own_range", "mc_own_range",
            "data_over_mc_own_range", "data_last_filled_gev", "mc_last_filled_gev"]
    fmt = lambda v: f"{v:.6g}" if isinstance(v, float) else v
    with open(a.out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(r.get(k, "")) for k in cols})
    both = [r for r in rows if r["status"] == "both"]
    ex = {r["histogram"]: {k: r[k] for k in ("data_first_filled_gev", "mc_first_filled_gev", "common_start_gev",
                                             "data_over_mc_own_range", "data_over_mc_from_common_start")}
          for r in both if r["histogram"].startswith(("ROI_mass_m0j0_cat_0ex_1mx_1jx_0bx", "ROI_mass_e0j0_cat_1ex_0mx_1jx_0bx",
                                                      "ROI_mass_e0m0_cat_1ex_1mx_0jx_0bx", "ROI_mass_m0j0j1_cat_0ex_1mx_2jx_0bx"))}
    summary = {"what": "start masses, final MC vs 25 Oct data (report only)", "data_root": a.data_root, "mc_root": a.mc_root,
               "n_mc": len(mc), "n_data": len(data), "n_both": len(both),
               "mc_only": [r["histogram"] for r in rows if r["status"] == "mc_only"],
               "data_only": sorted(set(data) - set(mc)),
               "n_first_filled_same": shifts.get(0.0, 0),
               "shift_mc_minus_data_gev": {str(k): v for k, v in sorted(shifts.items())},
               "n_mismatch_by_n_leptons": {str(n): {"n_hist": by_nlep[(n, True)] + by_nlep[(n, False)], "n_mismatch": by_nlep[(n, True)]}
                                           for n in sorted({k[0] for k in by_nlep})},
               "examples": ex}
    Path(a.out_json).write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("mc_only",)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
