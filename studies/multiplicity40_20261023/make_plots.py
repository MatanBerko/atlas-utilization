#!/usr/bin/env python
"""
Plots (step 4) from the rule-check evidence JSONs -- no ROOT reading.
Adapted from studies/cms_ttbar_pr40_20261021/make_plots.py (study branch 0f90fe5).

Per kind (data = the five-file smoke test, mc = ttbar 67801):
  <kind>_histograms_per_final_state.png  histograms per upstream40 final state:
                                         upstream40 vs the exact build's histograms
                                         of the exact labels merged into it
  <kind>_merged_example.png              one upstream40 histogram where merging
                                         happened, the contributing exact-label
                                         histograms stacked

Run (Mac):  python make_plots.py --data evidence/rule_check_data.json \
                --mc evidence/rule_check_mc.json --out-dir plots
"""
from __future__ import annotations

import argparse
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# Categorical slots in fixed order (dataviz reference palette, light mode).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
EXACT, UP40 = SERIES[0], SERIES[1]
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 9, "legend.frameon": False,
})

WHAT = {"data": ("data, five-file smoke test (not physics)", "events / 10 GeV"),
        "mc": ("ttbar 67801, 49 files", "weighted events / 10 GeV")}


def grouped_bars(rows, counts, sample, path):
    names = [r["final_state"] for r in rows]
    x = np.arange(len(names))
    w = 0.4
    fig, ax = plt.subplots(figsize=(max(8, 0.32 * len(names) + 2), 4.8))
    ax.bar(x - w / 2 - 0.01, [r["n_histograms_exact_members"] for r in rows], w, color=EXACT,
           label="exact (sum over the merged exact labels)")
    ax.bar(x + w / 2 + 0.01, [r["n_histograms_upstream40"] for r in rows], w, color=UP40,
           label="upstream40 (#40 rule, the new default)")
    ax.set_xticks(x, names, rotation=90, fontsize=7)
    ax.set_ylabel("histograms")
    ax.set_title(f"Histograms per final state: exact {counts['n_histograms_exact']} vs "
                 f"upstream40 {counts['n_histograms_upstream40']} ({sample})", loc="left")
    ax.legend(loc="upper right")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def on_grid(h, lo, n, width):
    out = np.zeros(n)
    i0 = int(round((h["lo_edge"] - lo) / width))
    out[i0:i0 + len(h["values"])] = h["values"]
    return out


def merged_plot(ex, sample, ylabel, path):
    hs = [ex["upstream40"]] + list(ex["contributors"].values())
    width = ex["upstream40"]["width"]
    lo = min(h["lo_edge"] for h in hs)
    hi = max(h["lo_edge"] + width * len(h["values"]) for h in hs)
    n = int(round((hi - lo) / width))
    edges = lo + width * np.arange(n + 1)
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bottom = np.zeros(n)
    for i, (lab, h) in enumerate(ex["contributors"].items()):
        v = on_grid(h, lo, n, width)
        ax.bar(edges[:-1], v, width=width, bottom=bottom, align="edge",
               color=SERIES[i] if i < len(SERIES) else MUTED, edgecolor=SURFACE, linewidth=0.3,
               label=f"exact {lab} ({int(h['entries'])} entries)")
        bottom += v
    ax.stairs(on_grid(ex["upstream40"], lo, n, width), edges, color=INK, linewidth=1.6,
              label=f"upstream40 ({int(ex['upstream40']['entries'])} entries)")
    name = ex["upstream40_name"].replace("ROI_", "").replace("_width_10.0", "")
    ax.set_title(f"{name}: #40 histogram vs its exact-label histograms (stacked)\n{sample}",
                 loc="left", fontsize=9)
    ax.set_xlabel("invariant mass [GeV]")
    ax.set_ylabel(ylabel)
    ax.set_xlim(lo, min(hi, lo + 2500))
    missing = ex.get("members_not_in_exact_build") or []
    note = ("Each exact histogram has its own peak cut, so the stack need not equal the #40 line."
            + (f"\nMerged labels with no exact histogram (below 100 events or empty after cuts): "
               f"{', '.join(missing)}" if missing else ""))
    ax.text(0.0, -0.2, note, transform=ax.transAxes, fontsize=7, color=MUTED, va="top", wrap=True)
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=pathlib.Path)
    ap.add_argument("--mc", required=True, type=pathlib.Path)
    ap.add_argument("--out-dir", required=True, type=pathlib.Path)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for kind, path in (("data", args.data), ("mc", args.mc)):
        rc = json.loads(path.read_text())
        pd = rc["plot_data"]
        sample, ylabel = WHAT[kind]
        rows = sorted(pd["per_upstream40_final_state"], key=lambda r: -r["events_upstream40"])
        grouped_bars(rows, rc["counts"], sample, args.out_dir / f"{kind}_histograms_per_final_state.png")
        if pd["merged_examples"]:
            merged_plot(pd["merged_examples"][0], sample, ylabel,
                        args.out_dir / f"{kind}_merged_example.png")
    print("wrote", sorted(p.name for p in args.out_dir.glob("*.png")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
