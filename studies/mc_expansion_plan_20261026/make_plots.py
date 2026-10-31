"""Plots of the MC expansion plan (26 Oct 2026), into plots/.

- mc_lumi_vs_data.png: simulated luminosity of each planned sample divided by the data's
  16.393 fb^-1 (from evidence/stats_cost.json; ESTIMATE where no probe result exists);
- genweight_<recid>.png: the genWeight distribution (sign and magnitude) of file 0, one per
  probed sample, from evidence/probe/probe_<recid>.json (only when the probe has run).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "plots"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def lumi_plot():
    d = json.loads((HERE / "evidence" / "stats_cost.json").read_text())
    rows = [s for s in d["samples"] if s["mc_lumi_over_data"]]
    rows.sort(key=lambda s: (s["tier"], s["role"] != "recommended"))
    names = [f"T{s['tier']} {s['recid']} {s['name'][:34]}{' (alt.)' if s['role'] == 'alternative' else ''}" for s in rows]
    vals = np.array([s["mc_lumi_over_data"] for s in rows])
    fig, ax = plt.subplots(figsize=(8.5, 0.24 * len(rows) + 1.4), facecolor=SURFACE)
    style(ax)
    y = np.arange(len(rows))[::-1]
    below = vals < 1
    ax.barh(y[~below], vals[~below] - 1, left=1, height=0.62, color=BLUE, label="MC luminosity ≥ data")
    ax.barh(y[below], vals[below] - 1, left=1, height=0.62, color=ORANGE, label="MC luminosity < data")
    for yi, v in zip(y[below], vals[below]):
        ax.text(1.2, yi, f"{v:.2f}× data", va="center", ha="left", fontsize=7.5, color=INK)
    ax.axvline(1, color=INK, linewidth=1.2)
    ax.text(1.1, y[0] + 0.9, "data = 16.393 fb⁻¹", fontsize=8, color=INK)
    ax.set_xscale("log")
    ax.set_yticks(y, names, fontsize=7.5, color=INK)
    ax.set_xlabel("simulated luminosity ÷ data luminosity (log scale)", color=INK, fontsize=9)
    ax.set_title("Simulated luminosity of each planned sample ÷ data luminosity\n"
                 "N_eff / σ_eff, PROPOSED σ_eff, N_eff ESTIMATED from the portal",
                 fontsize=9.5, color=INK, loc="left")
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    fig.tight_layout()
    ax.set_xlim(2e-3, 3e5)
    fig.savefig(OUT / "mc_lumi_vs_data.png", dpi=130, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def genweight_plots(probe_dir=HERE / "evidence" / "probe"):
    files = sorted(Path(probe_dir).glob("probe_*.json"))
    for f in files:
        p = json.loads(f.read_text())
        h = p["genweight_hist"]
        e = np.array(h["log10_abs_edges"])
        c = 0.5 * (e[1:] + e[:-1])
        w = e[1] - e[0]
        fig, ax = plt.subplots(figsize=(6.4, 3.6), facecolor=SURFACE)
        style(ax)
        ax.bar(c, h["pos_counts"], width=w * 0.92, color=BLUE, label=f"genWeight > 0 ({p['events_in_file'] - p['n_negative']:,})")
        ax.bar(c, -np.array(h["neg_counts"]), width=w * 0.92, color=ORANGE, label=f"genWeight < 0 ({p['n_negative']:,})")
        ax.axhline(0, color=INK, linewidth=0.8)
        ax.set_xlabel("log10 |genWeight|", color=INK, fontsize=9)
        ax.set_ylabel("events (negative weights drawn downward)", color=INK, fontsize=8)
        ax.set_title(f"{p['recid']} {p['name']} — file 0, {p['events_in_file']:,} events\n"
                     f"negative fraction {p['frac_negative']:.3f}, N_eff/N = {p['n_eff_file'] / p['events_in_file']:.3f}",
                     fontsize=9, color=INK, loc="left")
        ax.legend(fontsize=8, frameon=False)
        fig.tight_layout()
        fig.savefig(OUT / f"genweight_{p['recid']}.png", dpi=120, facecolor=SURFACE)
        plt.close(fig)
    return len(files)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    lumi_plot()
    print("genweight plots:", genweight_plots())
