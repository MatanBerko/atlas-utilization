#!/usr/bin/env python
"""Check that the per-sample MC files add up to the summed MC file, histogram by histogram (report only, reads only).

For every histogram name: the bin contents and the Sumw2 of the summed file vs the sum over all per-sample files that
contain that name. Reports the largest absolute and relative differences (relative = |diff| / max|summed bin| of that
histogram), and the name sets (every per-sample name is in the summed file and vice versa).

    python per_sample_sumcheck.py --summed <summed.root> --per-sample-dir <dir with the 71 files> --out <check.json>
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

NAME = re.compile(r"^ROI_mass_.+_width_10\.0$")
REC = re.compile(r"-rec(\d+)_")


def read(path):
    import uproot
    out = {}
    with uproot.open(path) as f:
        for k in f.keys(cycle=False):
            if NAME.match(k):
                h = f[k]
                out[k] = (np.asarray(h.values(flow=True), float), np.asarray(h.variances(flow=True), float),
                          np.asarray(h.axis().edges(), float))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    for a in ("--summed", "--per-sample-dir", "--out"):
        ap.add_argument(a, required=True)
    a = ap.parse_args()
    if Path(a.out).exists():
        raise SystemExit(f"refusing to overwrite {a.out}")
    summed = read(a.summed)
    files = sorted(Path(a.per_sample_dir).glob("*_mc.root"))
    acc, n_per_file, extra = {}, {}, set()
    for p in files:
        rid = REC.search(p.name).group(1)
        h = read(p)
        n_per_file[rid] = len(h)
        for k, (v, s2, e) in h.items():
            if k not in summed:
                extra.add(k)
                continue
            assert np.array_equal(e, summed[k][2]), f"axis differs: {p.name} {k}"
            av, as2 = acc.get(k, (np.zeros_like(v), np.zeros_like(s2)))
            acc[k] = (av + v, as2 + s2)
    worst = {"value_rel": (0.0, None), "value_abs": (0.0, None), "sumw2_rel": (0.0, None)}
    per_hist = {}
    for k, (sv, ss2, _) in summed.items():
        if k not in acc:
            per_hist[k] = {"missing_in_per_sample": True}
            continue
        av, as2 = acc[k]
        dv, ds2 = np.abs(av - sv), np.abs(as2 - ss2)
        rv = float(dv.max() / np.abs(sv).max()) if np.abs(sv).max() > 0 else float(dv.max())
        rs = float(ds2.max() / np.abs(ss2).max()) if np.abs(ss2).max() > 0 else float(ds2.max())
        per_hist[k] = {"max_abs_diff": float(dv.max()), "max_rel_diff": rv, "sumw2_max_rel_diff": rs}
        for key, val in (("value_rel", rv), ("value_abs", float(dv.max())), ("sumw2_rel", rs)):
            if val > worst[key][0]:
                worst[key] = (val, k)
    res = {"what": "per-sample files vs summed file, per histogram (report only)", "summed": a.summed,
           "per_sample_dir": a.per_sample_dir, "n_per_sample_files": len(files),
           "n_histograms_summed": len(summed), "n_histograms_per_file": n_per_file,
           "n_histogram_entries_per_sample_total": sum(n_per_file.values()),
           "summed_names_missing_from_per_sample": sorted(k for k, v in per_hist.items() if v.get("missing_in_per_sample")),
           "per_sample_names_missing_from_summed": sorted(extra),
           "largest_relative_difference": {"value": worst["value_rel"][0], "histogram": worst["value_rel"][1]},
           "largest_absolute_difference": {"value": worst["value_abs"][0], "histogram": worst["value_abs"][1]},
           "largest_relative_difference_sumw2": {"value": worst["sumw2_rel"][0], "histogram": worst["sumw2_rel"][1]},
           "per_histogram": per_hist}
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k not in ("per_histogram", "n_histograms_per_file")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
