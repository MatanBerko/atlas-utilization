#!/usr/bin/env python
"""Plots for CHECKS.md from the evidence JSONs (reads only)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
EV, PL = HERE / "evidence", HERE / "plots"
PL.mkdir(exist_ok=True)
OLD, NEW = "#8a8f98", "#2a6fdb"

A = json.loads((EV / "A_data_old_vs_new.json").read_text())
D = json.loads((EV / "D_mc.json").read_text())
groups = ["0", "1", "2", "3+"]

# 1. n_b, data and MC, OLD vs NEW (relative change per group)
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=False)
for ax, (title, items) in zip(axes, [
        ("Data, file 0 of each dataset", {k: (v["jets_old"], v["jets_new"]) for k, v in A.items()}),
        ("MC, file 0", {f"MC {k}": (v["jets_old"], v["jets_new"]) for k, v in D["per_file"].items()})]):
    names = list(items)
    x = np.arange(len(groups))
    w = 0.8 / len(names)
    for i, n in enumerate(names):
        o, nw = items[n]
        rel = [100 * (nw["n_b_distribution"][g] / o["n_b_distribution"][g] - 1)
               if o["n_b_distribution"][g] else 0 for g in groups]
        ax.bar(x + (i - (len(names) - 1) / 2) * w, rel, w * 0.92, label=n)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x, [f"{g} b-jets" for g in groups])
    ax.set_ylabel("events, NEW / OLD - 1  [%]")
    ax.set_title(title)
    ax.legend(fontsize=8)
fig.suptitle("b-tag 0.2598 -> 0.2489: change in the number of events per b-jet group")
fig.tight_layout()
fig.savefig(PL / "nb_old_vs_new.png", dpi=130)
plt.close(fig)

# 2. b-tagged jet fraction, OLD vs NEW
fig, ax = plt.subplots(figsize=(7.5, 4))
rows = [(k, v["jets_old"], v["jets_new"]) for k, v in A.items()] + \
       [(f"MC {k}", v["jets_old"], v["jets_new"]) for k, v in D["per_file"].items()]
x = np.arange(len(rows))
ax.bar(x - 0.2, [100 * r[1]["b_tagged_jet_fraction"] for r in rows], 0.38, color=OLD, label="OLD 0.2598")
ax.bar(x + 0.2, [100 * r[2]["b_tagged_jet_fraction"] for r in rows], 0.38, color=NEW, label="NEW 0.2489")
for i, r in enumerate(rows):
    rel = 100 * (r[2]["b_tagged_jet_fraction"] / r[1]["b_tagged_jet_fraction"] - 1)
    ax.text(i, 100 * r[2]["b_tagged_jet_fraction"] + 0.8, f"+{rel:.1f}%", ha="center", fontsize=8)
ax.set_xticks(x, [r[0] for r in rows], rotation=20)
ax.set_ylabel("b-tagged share of selected jets [%]")
ax.set_title("Share of jets that are b-tagged, accepted events")
ax.legend()
fig.tight_layout()
fig.savefig(PL / "btag_fraction_old_vs_new.png", dpi=130)
plt.close(fig)

# 3. SingleElectron: leading qualifying electron pT, with the 32 GeV cut
H = json.loads((EV / "B_singleelectron_pt_histograms.json").read_text())
fig, ax = plt.subplots(figsize=(7.5, 4.2))
for name, h in H.items():
    edges = np.asarray(h.get("bin_edges_gev") or h.get("edges"))
    counts = np.asarray(h.get("counts"))
    ax.step(edges[:-1], counts, where="post", label=f"SingleElectron {name}")
ax.axvline(32, color="crimson", ls="--", lw=1.2, label="offline cut: pT > 32 GeV")
ax.set_yscale("log")
ax.set_xlim(20, 120)
ax.set_xlabel("offline pT of the leading electron matched online >= 27 GeV [GeV]")
ax.set_ylabel("events / 1 GeV")
ax.set_title("SingleElectron: Ele27 fired, >= 1 matched electron (accepted right of the line)")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(PL / "singleelectron_pt_cut32.png", dpi=130)
plt.close(fig)
print("plots written")
