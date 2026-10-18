#!/usr/bin/env python
"""
Peak-fix step 0 (18 Oct 2026): verify the technical lead's finding on the
17-18 Oct full-run build, READ-ONLY.

Finding: build_mc_delivery.py runs postprocess_in_lockstep (Z cut -> max-mass
cut -> peak removal -> outlier split) separately per sample, and
sum_histograms adds the already-cut per-sample histograms, so each sample is
cut at its OWN peak and the summed SM is not "sum, then cut" as the data is.

Evidence collected here:
  1. From the build report: for every histogram name, the per-sample
     peak_mass values. Names whose kept samples do NOT share one peak mass
     are names where the summed SM is a mix of differently cut samples.
  2. From the ROOT files: for three histograms, each sample's first and last
     filled bin vs the summed-SM first and last filled bin.
  3. A memory estimate for a combined-scope build: the total number of
     entries after the Z and max-mass cuts, summed over samples and names.

Run (as a PBS job):
    python studies/cms_mc_weights_v3/peakfix/verify_finding.py \
        --build-dir <work>/fullrun_20261017/build_default --prefix fullrun --out <json>
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import uproot

NAMES = [
    "mass_e0e1m0m1_cat_2ex_2mx_0jx_0bx",   # stack_5: 2e2mu, 0 jets
    "mass_m0m1_cat_0ex_2mx_0jx_0bx",       # stack_1: mumu, 0 jets
    "mass_j0j1b0_cat_0ex_1mx_2jx_1bx",     # stack_6: mu + 2 jets + b
]
KEY_SUFFIX = "_width_10.0"


def filled_range(values: np.ndarray, edges: np.ndarray):
    nz = np.nonzero(values)[0]
    if nz.size == 0:
        return None
    return {"first_bin_low_edge": float(edges[nz[0]]),
            "last_bin_high_edge": float(edges[nz[-1] + 1]),
            "sum": float(values.sum())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-dir", required=True)
    ap.add_argument("--prefix", default="fullrun")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    bd = Path(args.build_dir)
    report = json.loads((bd / f"{args.prefix}_build_report.json").read_text())
    samples = report["samples"]

    # 1. per-name peak masses across samples
    peaks = {}
    n_entries_after_z = 0
    for rid, s in samples.items():
        for name, ph in s["histograms"]["per_histogram"].items():
            n_entries_after_z += int(ph.get("n_after_z_and_max_mass", 0))
            if ph.get("kept"):
                peaks.setdefault(name, {})[rid] = ph.get("peak_mass")
    multi = {n: p for n, p in peaks.items() if len(p) > 1}
    differing = {n: p for n, p in multi.items() if len(set(p.values())) > 1}
    spread = Counter()
    for n, p in differing.items():
        v = [x for x in p.values() if x is not None]
        spread[int(round((max(v) - min(v)) / 10.0))] += 1

    # 2. three histograms from the ROOT files
    files = {rid: bd / f"{args.prefix}_record{rid}_mc.root" for rid in samples}
    files["summedSM"] = bd / f"{args.prefix}_summedSM_mc.root"
    examples = {}
    for name in NAMES:
        key = f"ROI_{name}{KEY_SUFFIX}"
        row = {}
        for rid, path in files.items():
            with uproot.open(path) as f:
                if key not in f:
                    continue
                h = f[key]
                rng = filled_range(np.asarray(h.values(), float), np.asarray(h.axis().edges(), float))
                if rng is not None:
                    rng["peak_mass_in_report"] = (samples[rid]["histograms"]["per_histogram"]
                                                  .get(name, {}).get("peak_mass")
                                                  if rid != "summedSM" else None)
                    row[rid] = rng
        examples[name] = row

    out = {
        "build_dir": str(bd),
        "n_names_with_any_sample": len(peaks),
        "n_names_with_2plus_samples": len(multi),
        "n_names_where_sample_peaks_differ": len(differing),
        "spread_of_sample_peaks_in_bins_hist": dict(sorted(spread.items())),
        "examples": examples,
        "total_entries_after_z_and_max_mass_all_samples": n_entries_after_z,
        "memory_estimate_gb_masses_plus_weights_float64": n_entries_after_z * 16 / 1e9,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "examples"}, indent=1))
    for name, row in examples.items():
        print(f"\n{name}")
        s = row.get("summedSM")
        for rid, r in sorted(row.items(), key=lambda kv: (kv[0] == "summedSM", kv[1]["first_bin_low_edge"])):
            print(f"  {rid:>9}: first {r['first_bin_low_edge']:7.1f}  last {r['last_bin_high_edge']:7.1f}  "
                  f"peak(report) {r['peak_mass_in_report']}  sum {r['sum']:.6g}")
        if s:
            print(f"  summed-SM first filled bin {s['first_bin_low_edge']} = min over samples "
                  f"{min(r['first_bin_low_edge'] for k, r in row.items() if k != 'summedSM')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
