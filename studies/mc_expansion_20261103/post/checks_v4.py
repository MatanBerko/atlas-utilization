#!/usr/bin/env python
"""Checks of the v4 MC build (MC expansion; written in A1, to be run by the B step after A2's build).

Runs in a PBS job (reads ROOT). Inputs: the v4 build directory (per-record files + summed file +
build report), the production run directory of the new samples (W+jets job metadata, for
max|genWeight| of the stored events), and the data delivery (uncropped).

  1. every histogram of every MC file: no NaN/inf in contents or variances, no negative variance;
  2. data/MC names: the set of MC summed-SM histogram names vs the data delivery's names
     (same format; lists names only in MC / only in data);
  3. Z peaks: the delivered histograms have the Z region removed (the builder's Z cut), so the Z
     peaks are made BEFORE peak removal, from the data run outputs and the MC build's kept scratch
     shards, with the 25 Oct analysis function (studies/fullrun_20261025/analysis/analyze_fullrun.py
     zpeak(); it sums every MC record found; only its colour groups are replaced by the v4 groups):
     data/MC in 76-106 and 60-120 GeV, 0 jets, ee and mumu, + plots (given --data-runs, --mc-scratch);
  4. stacked plots of mumu 0j, emu 0j, ee+1j, ee+2j, 3l, mumu near 125 GeV, with data;
  5. D3 (Matan): count the histograms where ONE W+jets event makes up > 50 % of a bin's MC
     content; list the worst 20 and plot 5. The single-event weight is not stored per bin, so an
     UPPER BOUND is used: w1(bin) = min( sqrt(sum w^2 of that W+jets sample in the bin),
     normalisation x max|genWeight| x max cap scale of the sample ). A bin is flagged when
     w1(bin) / (total MC content of the bin) > 0.5 (bins with total MC <= 0 are listed apart).
Writes checks_v4.json + PNGs into --out; exit 1 if check 1 fails.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "studies" / "mc_expansion_20261103" / "precheck"))
from precheck_report import GROUPS, INK, SURF, style  # noqa: E402

NAME = re.compile(r"(mass_[a-z0-9]+_cat_\d+ex_\d+mx_\d+jx_\d+bx)")
WJETS = (69715, 69717, 69719)
PLOTS = [("mumu_0j", "mass_m0m1_cat_0ex_2mx_0jx_0bx", None), ("emu_0j", "mass_e0m0_cat_1ex_1mx_0jx_0bx", None),
         ("ee_1j", "mass_e0e1_cat_2ex_0mx_1jx_0bx", None), ("ee_2j", "mass_e0e1_cat_2ex_0mx_2jx_0bx", None),
         ("3l_eem", "mass_e0e1_cat_2ex_1mx_0jx_0bx", None), ("mumu_0j_125", "mass_m0m1_cat_0ex_2mx_0jx_0bx", (100, 150))]


def read(path):
    out = {}
    with uproot.open(path) as f:
        for k in f.keys(cycle=False):
            h = f[k]
            if not hasattr(h, "values"):
                continue
            m = NAME.search(k)
            if m:
                out[m.group(1)] = {"key": k, "v": np.asarray(h.values(), float), "s2": np.asarray(h.variances(), float),
                                   "e": np.asarray(h.axis().edges(), float)}
    return out


def stack(ax, per, name, data, xr):
    edges = next(per[r][name]["e"] for r in per if name in per[r])
    bottom = np.zeros(len(edges) - 1)
    for lab, recs, col in GROUPS:
        v = sum((per[r][name]["v"] for r in recs if r in per and name in per[r] and len(per[r][name]["v"]) == len(bottom)),
                np.zeros(len(bottom)))
        if np.any(v):
            ax.bar(edges[:-1], v, width=np.diff(edges), bottom=bottom, align="edge", color=col, edgecolor=SURF, lw=0.4,
                   label=f"{lab} ({v.sum():.4g})")
            bottom = bottom + v
    if data is not None and name in data:
        d = data[name]
        c = 0.5 * (d["e"][1:] + d["e"][:-1])
        ax.errorbar(c, d["v"], yerr=np.sqrt(np.maximum(d["s2"], 0)), fmt="o", ms=3, color=INK, label=f"data ({d['v'].sum():.4g})")
    ax.set_yscale("log")
    if xr:
        ax.set_xlim(*xr)
    ax.legend(fontsize=7, frameon=False)
    return bottom, edges


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-dir", required=True)
    ap.add_argument("--prefix", default="mcexp")
    ap.add_argument("--runs", required=True, help="production runs dir holding record<W+jets>/job_*/job_metadata.json")
    ap.add_argument("--data-root", required=True, help="data delivery, uncropped")
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-runs", default=None, help="data run outputs (for the Z peaks)")
    ap.add_argument("--mc-scratch", default=None, help="the v4 build's kept scratch (for the Z peaks)")
    a = ap.parse_args()
    out = Path(a.out)
    (out / "plots").mkdir(parents=True, exist_ok=True)
    bd = Path(a.build_dir)
    report = json.loads((bd / f"{a.prefix}_build_report.json").read_text())
    per = {int(re.search(r"_record(\d+)_mc", p.name).group(1)): read(p) for p in bd.glob(f"{a.prefix}_record*_mc.root")}
    summed = read(bd / f"{a.prefix}_summedSM_mc.root")
    data = read(a.data_root)
    res = {"n_records": len(per), "n_summed_histograms": len(summed)}
    # 1
    bad = []
    for label, hs in [("summed", summed)] + [(str(r), h) for r, h in per.items()]:
        for n, h in hs.items():
            if not (np.all(np.isfinite(h["v"])) and np.all(np.isfinite(h["s2"]))) or np.any(h["s2"] < 0):
                bad.append(f"{label}:{n}")
    res["check1_nan_inf_negvar"] = {"n_bad": len(bad), "bad": bad[:50]}
    # 2
    res["check2_names"] = {"mc_only": sorted(set(summed) - set(data)), "data_only_count": len(set(data) - set(summed)),
                           "n_mc": len(summed), "n_data": len(data),
                           "key_format_example": {"mc": next(iter(summed.values()))["key"], "data": next(iter(data.values()))["key"]}}
    # 3 + 4
    res["plots"] = {}
    for key, name, xr in PLOTS:
        if not any(name in per[r] for r in per):
            res["plots"][key] = "absent"
            continue
        fig, ax = plt.subplots(figsize=(7.5, 4.4), facecolor=SURF)
        style(ax)
        mc, edges = stack(ax, per, name, data, xr)
        ax.set_title(f"{key}: {name} (v4 build)", fontsize=9, loc="left")
        fig.tight_layout()
        fig.savefig(out / "plots" / f"{key}.png", dpi=120, facecolor=SURF)
        plt.close(fig)
        res["plots"][key] = {"mc_total": float(mc.sum())}
    if a.data_runs and a.mc_scratch:
        sys.path.insert(0, str(REPO))
        sys.path.insert(0, str(REPO / "studies" / "fullrun_20261025" / "analysis"))
        import analyze_fullrun as AF
        AF.GROUPS = GROUPS
        AF.MISSING_MC = ("Not in the MC: QCD multijet, photon samples, the on-hold rare top "
                         "(tZq, tWll, ttZ->qq, tt+ll 1-10 GeV)")
        res["check3_zpeak"] = AF.zpeak(Path(a.data_runs), Path(a.mc_scratch), out / "plots")
    else:
        res["check3_zpeak"] = "not run (needs --data-runs and --mc-scratch)"
    # 5  D3
    w1 = {}
    for rid in WJETS:
        s = report["samples"].get(str(rid))
        if not s:
            continue
        gmax = 0.0
        for mp in (Path(a.runs) / f"record{rid}").glob("job_*/job_metadata.json"):
            g = json.loads(mp.read_text())["mc_diagnostics"]["genweight_stored_events"]
            gmax = max(gmax, abs(g.get("max") or 0.0), abs(g.get("min") or 0.0))
        caps = [c.get("weight_scale", 1.0) for ws in s["weight_write_stats"] for c in ws["capped_signatures"].values()] or [1.0]
        w1[rid] = {"norm": s["normalisation_factor"], "max_cap_scale": max(1.0, max(caps)), "max_abs_genweight": gmax}
    flagged, nonpos = [], []
    for name, h in summed.items():
        tot = h["v"]
        best = np.zeros(len(tot))
        for rid in WJETS:
            if rid not in per or name not in per[rid] or rid not in w1:
                continue
            bound = np.sqrt(np.maximum(per[rid][name]["s2"], 0))
            if w1[rid]["max_abs_genweight"]:
                bound = np.minimum(bound, w1[rid]["norm"] * w1[rid]["max_abs_genweight"] * w1[rid]["max_cap_scale"])
            best = np.maximum(best, bound)
        has = best > 0
        if not np.any(has):
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            frac = np.where(tot > 0, best / tot, np.inf)
        for i in np.where(has & (tot <= 0))[0]:
            nonpos.append({"name": name, "bin": int(i), "mc": float(tot[i])})
        worst = np.where(has & (tot > 0))[0]
        if len(worst) and np.max(frac[worst]) > 0.5:
            i = worst[np.argmax(frac[worst])]
            flagged.append({"name": name, "n_bins_over_50pct": int(np.sum(frac[worst] > 0.5)), "worst_bin": int(i),
                            "worst_bin_low_edge": float(h["e"][i]), "worst_fraction_upper_bound": float(frac[i]),
                            "mc_in_bin": float(tot[i])})
    flagged.sort(key=lambda d: -d["n_bins_over_50pct"])
    res["check5_D3_wjets"] = {"method": "upper bound, see the module docstring", "w1_inputs": w1,
                              "n_histograms": len(summed), "n_histograms_flagged": len(flagged),
                              "worst20": flagged[:20], "n_bins_wjets_present_mc_nonpositive": len(nonpos)}
    for d in flagged[:5]:
        n = d["name"]
        fig, ax = plt.subplots(figsize=(7.5, 4.4), facecolor=SURF)
        style(ax)
        stack(ax, per, n, data, None)
        ax.axvline(d["worst_bin_low_edge"], color=INK, ls="--", lw=0.8)
        ax.set_title(f"D3: {n}\n{d['n_bins_over_50pct']} bins where one W+jets event may be > 50 % of the MC", fontsize=9, loc="left")
        fig.tight_layout()
        fig.savefig(out / "plots" / f"d3_{n}.png", dpi=120, facecolor=SURF)
        plt.close(fig)
    (out / "checks_v4.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps({k: (v if k != "plots" else list(v)) for k, v in res.items() if k != "check5_D3_wjets"}, default=str)[:2000])
    print("D3 flagged:", len(flagged))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
