#!/usr/bin/env python
"""
The four plots of the overlap-convention study, from results/overlap_results.json only.

  1. dR(jet, nearest selected lepton), V0 jets, per channel, lines at 0.2 and 0.4
  2. light-jet multiplicity V0 / V1 / V2 overlaid, per channel
  3. leptons removed by V2's 0.4 step vs lepton pT (count and fraction), per flavour
  4. category yields V1 vs V2 (top 20 of the delivered four-dataset set) with a ratio panel

Run:  python studies/overlap_convention_20261015/make_plots.py [--results ...] [--out-dir ...]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
DATASETS = ["DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG"]
COL = {"V0": "#718096", "V1": "#2b6cb0", "V2": "#c05621", "V2u": "#2f855a"}


def step(ax, edges, counts, **kw):
    ax.stairs(counts, edges, **kw)


def plot1(r, out):
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), dpi=130, sharex=True)
    for ax, ds in zip(axes.flat, DATASETS):
        b = r["per_group"].get(ds, {}).get("b", {}).get("all")
        if not b:
            ax.set_visible(False)
            continue
        h = b["hist_dr_nearest_lepton"]
        hm = b["hist_dr_nearest_lepton_when_nearest_is_muon"]
        he = b["hist_dr_nearest_lepton_when_nearest_is_electron"]
        step(ax, h["edges"], np.maximum(h["counts"], 0.5), color="k", lw=1.6, label="all V0 jets")
        step(ax, hm["edges"], np.maximum(hm["counts"], 0.5), color="#2b6cb0", lw=1, label="nearest lepton is a muon")
        step(ax, he["edges"], np.maximum(he["counts"], 0.5), color="#c05621", lw=1, label="nearest lepton is an electron")
        for x, lab in ((0.2, "0.2 (#32 jet removal)"), (0.4, "0.4 (CMS cleaning; #32 lepton removal)")):
            ax.axvline(x, color="0.3", ls="--", lw=1)
        ax.set_yscale("log")
        ax.set_ylim(0.8, None)
        ax.set_title(f"{ds}: {b['n_below_0p2']:,} jets < 0.2,  {b['n_0p2_to_0p4']:,} in 0.2–0.4", fontsize=9)
        ax.set_xlabel("ΔR(jet, nearest selected lepton)")
        ax.set_ylabel("jets / 0.02")
    axes.flat[0].legend(fontsize=7, frameon=False)
    fig.suptitle("Plot 1 — V0 jets (no cleaning), accepted events: distance to the nearest selected lepton\n"
                 "dashed lines at ΔR = 0.2 and 0.4; overflow above 1.0 not drawn", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "plot1_dr_jet_nearest_lepton_V0.png")
    plt.close(fig)


def plot2(r, out):
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), dpi=130)
    for ax, ds in zip(axes.flat, DATASETS):
        jm = r["per_group"].get(ds, {}).get("jet_multiplicity")
        if not jm:
            ax.set_visible(False)
            continue
        x = np.arange(len(jm["V0"]["light"]))
        for i, vn in enumerate(("V0", "V1", "V2")):
            ax.bar(x + (i - 1) * 0.27, np.maximum(jm[vn]["light"], 0.5), width=0.27, color=COL[vn],
                   label={"V0": "V0 no cleaning", "V1": "V1 CMS one-step", "V2": "V2 #32 two-step"}[vn])
        ax.set_yscale("log")
        ax.set_ylim(0.8, None)
        ax.set_xticks(x)
        ax.set_xticklabels([str(i) for i in x[:-1]] + [f"≥{x[-1]}"])
        ax.set_xlabel("number of light jets")
        ax.set_ylabel("accepted events")
        ax.set_title(ds, fontsize=9)
    axes.flat[0].legend(fontsize=7, frameon=False)
    fig.suptitle("Plot 2 — light-jet multiplicity per accepted event, V0 / V1 / V2", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "plot2_jet_multiplicity_V0_V1_V2.png")
    plt.close(fig)


def plot3(r, out):
    c = r["per_group"]["combined"]["c"]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), dpi=130, sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    for fl, colour in (("muons", "#2b6cb0"), ("electrons", "#c05621")):
        ha, hr = c[f"hist_pt_all_selected_{fl}"], c[f"hist_pt_removed_{fl}"]
        e = np.asarray(ha["edges"])
        step(ax1, e, np.maximum(hr["counts"], 0.5), color=colour, lw=1.6,
             label=f"{fl} removed by the 0.4 step: {c[f'n_{fl}_removed_by_0p4_step']:,} "
                   f"of {c[f'n_{fl}_selected']:,}")
        step(ax1, e, np.maximum(ha["counts"], 0.5), color=colour, lw=0.8, ls=":",
             label=f"all selected {fl}")
        a = np.asarray(ha["counts"], float)
        rr = np.asarray(hr["counts"], float)
        fr = np.divide(rr, a, out=np.full_like(a, np.nan), where=a > 0)
        err = np.divide(np.sqrt(rr), a, out=np.full_like(a, np.nan), where=a > 0)
        ax2.errorbar(0.5 * (e[1:] + e[:-1]), fr, yerr=err, fmt="o", ms=3, color=colour, label=fl)
    ax1.set_yscale("log")
    ax1.set_ylim(0.8, None)
    ax1.set_ylabel("leptons / 5 GeV")
    ax1.legend(fontsize=7, frameon=False)
    ax2.set_ylabel("fraction removed")
    ax2.set_xlabel("lepton pT [GeV] (overflow above 300 not drawn)")
    ax2.set_yscale("symlog", linthresh=1e-4)
    fig.suptitle("Plot 3 — selected leptons removed by #32's 0.4 step (V2, all 8 files, accepted events)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "plot3_leptons_removed_vs_pt.png")
    plt.close(fig)


def plot4(r, out):
    top = r["delivered_four_dataset_categories"]["orderA"]["top20_by_V1"]
    cats = [t["category"] for t in top]
    v1 = np.array([t["V1"] for t in top], float)
    v2 = np.array([t["V2"] for t in top], float)
    v2u = np.array([t["V2u"] for t in top], float)
    x = np.arange(len(cats))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.5), dpi=130, sharex=True,
                                   gridspec_kw={"height_ratios": [2.2, 1]})
    ax1.bar(x - 0.27, v1, 0.27, color=COL["V1"], label="V1 CMS one-step (production)")
    ax1.bar(x, v2, 0.27, color=COL["V2"], label="V2 #32 two-step, b-jets CMS-cleaned")
    ax1.bar(x + 0.27, v2u, 0.27, color=COL["V2u"], label="V2u #32 two-step, b-jets uncleaned")
    ax1.set_yscale("log")
    ax1.set_ylabel("events")
    ax1.legend(fontsize=7, frameon=False)
    ax2.axhline(1, color="0.4", lw=1, ls="--")
    for arr, vn, off in ((v2, "V2", -0.12), (v2u, "V2u", 0.12)):
        ratio = np.divide(arr, v1, out=np.full_like(v1, np.nan), where=v1 > 0)
        err = ratio * np.sqrt(np.divide(1, np.maximum(arr, 1)) + np.divide(1, np.maximum(v1, 1)))
        ax2.errorbar(x + off, ratio, yerr=err, fmt="o", ms=3.5, color=COL[vn], label=f"{vn} / V1")
    ax2.set_ylabel("ratio to V1")
    ax2.legend(fontsize=7, frameon=False)
    ax2.set_xticks(x)
    ax2.set_xticklabels(cats, rotation=60, ha="right", fontsize=7)
    fig.suptitle("Plot 4 — the 20 most-populated categories of the delivered four-dataset set "
                 "(DoubleMuon inclusive + the other three exclusive), 8 files", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "plot4_category_yields_V1_vs_V2.png")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(HERE / "results" / "overlap_results.json"))
    ap.add_argument("--out-dir", default=str(HERE / "results" / "plots"))
    args = ap.parse_args()
    r = json.loads(pathlib.Path(args.results).read_text())
    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    plot1(r, out)
    plot2(r, out)
    plot3(r, out)
    plot4(r, out)
    print(f"wrote 4 plots to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
