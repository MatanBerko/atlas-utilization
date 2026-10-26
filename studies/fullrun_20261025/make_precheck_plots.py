#!/usr/bin/env python
"""Full run 25 Oct 2026, step 3: the PRECHECK plots, OLD (medium IDs) vs NEW
(loose IDs), from the JSONs the precheck PBS jobs wrote (no ROOT reading):

  evidence/objects/<name>.json  (cluster/object_compare.py, one per file)
  evidence/build_compare.json   (cluster/build_compare.py)

Writes into --out-dir:
  multiplicity_muons.png, multiplicity_electrons.png   per dataset / MC sample
  electron_pt_abseta.png                               DoubleEG and SingleElectron
  example_histograms.png                               an ee and a mumu histogram

    python studies/fullrun_20261025/make_precheck_plots.py \
        --evidence studies/fullrun_20261025/evidence --out-dir studies/fullrun_20261025/precheck_plots
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

NAMES = ("DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG", "SingleElectron", "MC_67801", "MC_72752")
TITLES = {"MC_67801": "MC 67801 (TTTo2L2Nu)", "MC_72752": "MC 72752 (WZTo3LNu)"}
# Reference palette, categorical slots 1 and 2 (light mode); OLD also dashed.
OLD = dict(color="#2a78d6", linestyle="--", label="OLD (medium ID)")
NEW = dict(color="#eb6834", linestyle="-", label="NEW (loose ID)")
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3dd"


def style(ax):
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)


def multiplicity(objs, kind, out):
    fig, axes = plt.subplots(2, 4, figsize=(14, 6.5))
    for ax, name in zip(axes.flat, NAMES):
        pop = objs[name]["populations"]["triggered"][kind]
        x = np.arange(len(pop["mult_old"]))
        w = 0.38
        ax.bar(x - w / 2 - 0.01, np.maximum(pop["mult_old"], 0.5), w, color=OLD["color"],
               label=OLD["label"], hatch="//", edgecolor="white", linewidth=0)
        ax.bar(x + w / 2 + 0.01, np.maximum(pop["mult_new"], 0.5), w, color=NEW["color"],
               label=NEW["label"])
        ax.set_yscale("log")
        ax.set_xticks(x, [str(i) for i in x[:-1]] + [f">={x[-1]}"])
        ratio = pop["new"] / pop["old"] if pop["old"] else float("nan")
        ax.set_title(f"{TITLES.get(name, name)}\n{pop['old']:,} -> {pop['new']:,} {kind} (x{ratio:.3f})",
                     fontsize=9, color=INK)
        ax.set_xlabel(f"selected {kind} per event", fontsize=8, color=MUTED)
        style(ax)
    axes.flat[-1].axis("off")
    h, lab = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].legend(h, lab, loc="center", frameon=False, fontsize=10)
    fig.suptitle(f"Selected {kind} per event, OLD vs NEW — file 0 of each, events passing the "
                 f"dataset trigger (MC: any of the five triggers)", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)


def electron_kinematics(objs, out):
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for row, name in enumerate(("DoubleEG", "SingleElectron")):
        e = objs[name]["populations"]["triggered"]["electrons"]
        pt_edges = np.array([float(x) for x in objs[name]["pt_edges_gev"][:-1]] + [205.0])
        ae_edges = np.array(objs[name]["abseta_edges"])
        for ax, edges, ko, kn, xl in ((axes[row, 0], pt_edges, "pt_old", "pt_new", "electron pT [GeV] (last bin: > 200)"),
                                      (axes[row, 1], ae_edges, "abseta_old", "abseta_new", "electron |eta|")):
            ax.stairs(e[ko], edges, linewidth=2, **OLD)
            ax.stairs(e[kn], edges, linewidth=2, **NEW)
            ax.set_xlabel(xl, fontsize=8, color=MUTED)
            ax.set_ylabel("selected electrons / bin", fontsize=8, color=MUTED)
            if ko == "pt_old":
                ax.set_yscale("log")
            ax.set_title(f"{name}: {e['old']:,} -> {e['new']:,} electrons", fontsize=9, color=INK)
            style(ax)
    axes[0, 0].legend(frameon=False, fontsize=9)
    fig.suptitle("Selected electrons, OLD (cutBased >= 3) vs NEW (cutBased >= 2) — file 0, "
                 "triggered events, before e-mu overlap removal", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)


def examples(bc, out):
    ex = bc["builds"]["data_examples"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, tag in zip(axes, ("ee", "mumu")):
        d = ex[tag]
        lo, hi = None, None
        for side, st in (("old", OLD), ("new", NEW)):
            if not d.get(side):
                continue
            v = np.array(d[side]["values"])
            edges = np.array(d[side]["edges"])
            nz = np.nonzero(v)[0]
            if len(nz):
                lo = nz[0] if lo is None else min(lo, nz[0])
                hi = nz[-1] if hi is None else max(hi, nz[-1])
            ax.stairs(v, edges, linewidth=2, label=f"{st['label']}: {int(v.sum()):,} entries",
                      color=st["color"], linestyle=st["linestyle"])
        if lo is not None:
            ax.set_xlim(edges[lo], edges[min(hi + 1, len(edges) - 1)])
        ax.set_yscale("log")
        ax.set_xlabel("mass [GeV] (10 GeV bins)", fontsize=8, color=MUTED)
        ax.set_ylabel("events / bin", fontsize=8, color=MUTED)
        ax.set_title(d["root_key"], fontsize=9, color=INK)
        ax.legend(frameon=False, fontsize=8)
        style(ax)
    fig.suptitle("Two delivered data histograms (matched5 build of the five file-0 outputs), OLD vs NEW",
                 fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--evidence", required=True)
    p.add_argument("--out-dir", required=True)
    a = p.parse_args()
    ev = Path(a.evidence)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    objs = {n: json.loads((ev / "objects" / f"{n}.json").read_text()) for n in NAMES}
    multiplicity(objs, "muons", out / "multiplicity_muons.png")
    multiplicity(objs, "electrons", out / "multiplicity_electrons.png")
    electron_kinematics(objs, out / "electron_pt_abseta.png")
    examples(json.loads((ev / "build_compare.json").read_text()), out / "example_histograms.png")
    print("wrote", sorted(x.name for x in out.glob("*.png")))


if __name__ == "__main__":
    main()
