#!/usr/bin/env python
"""
Study plots (step 7) from the rule-check evidence JSON -- no ROOT reading.

  1_histograms_per_final_state.png  histograms per pr40 final state: pr40 vs
                                    the exact build's histograms of its members
  2_raw_events_per_final_state.png  raw events per pr40 final state: pr40 vs
                                    the members that survive in the exact build
  3_merged_<i>.png                  pr40 histograms where merging happened, the
                                    contributing exact-label histograms stacked
  4_unchanged.png                   one histogram the rule does not change,
                                    exact vs pr40 overlaid

Run (Mac):  python make_plots.py --rule-check evidence/rule_check.json --out-dir plots
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
EXACT, PR40 = SERIES[0], SERIES[1]
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 9, "legend.frameon": False,
})


def grouped_bars(rows, key_a, key_b, label_a, label_b, ylabel, title, path, log=False):
    names = [r["final_state"] for r in rows]
    x = np.arange(len(names))
    w = 0.4
    fig, ax = plt.subplots(figsize=(max(8, 0.32 * len(names) + 2), 4.8))
    ax.bar(x - w / 2 - 0.01, [r[key_a] for r in rows], w, color=EXACT, label=label_a)
    ax.bar(x + w / 2 + 0.01, [r[key_b] for r in rows], w, color=PR40, label=label_b)
    ax.set_xticks(x, names, rotation=90, fontsize=7)
    ax.set_ylabel(ylabel)
    if log:
        ax.set_yscale("log")
    ax.set_title(title, loc="left")
    ax.legend(loc="upper right")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def hist_xy(h):
    edges = h["lo_edge"] + h["width"] * np.arange(len(h["values"]) + 1)
    return edges, np.asarray(h["values"])


def on_grid(h, lo, n, width):
    out = np.zeros(n)
    i0 = int(round((h["lo_edge"] - lo) / width))
    out[i0:i0 + len(h["values"])] = h["values"]
    return out


def merged_plot(ex, path):
    hs = [ex["pr40"]] + list(ex["contributors"].values())
    width = ex["pr40"]["width"]
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
    ax.stairs(on_grid(ex["pr40"], lo, n, width), edges, color=INK, linewidth=1.6,
              label=f"pr40 ({int(ex['pr40']['entries'])} entries)")
    name = ex["pr40_name"].replace("ROI_", "").replace("_width_10.0", "")
    ax.set_title(f"{name}: PR #40 histogram vs its exact-label histograms (stacked)",
                 loc="left", fontsize=9)
    ax.set_xlabel("invariant mass [GeV]")
    ax.set_ylabel("weighted events / 10 GeV")
    ax.set_xlim(lo, min(hi, lo + 2500))
    missing = ex.get("members_not_in_exact_build") or []
    note = ("Each exact histogram has its own peak cut, so the stack need not equal the PR #40 line."
            + (f"\nMembers with no exact histogram (below 100 events or empty after cuts): "
               f"{', '.join(missing)}" if missing else ""))
    ax.text(0.0, -0.2, note, transform=ax.transAxes, fontsize=7, color=MUTED, va="top", wrap=True)
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def unchanged_plot(ex, path):
    fig, ax = plt.subplots(figsize=(8, 4.4))
    e1, v1 = hist_xy(ex["exact"])
    e2, v2 = hist_xy(ex["pr40"])
    ax.stairs(v1, e1, color=EXACT, linewidth=3.0, label=f"exact ({int(ex['exact']['entries'])} entries)")
    ax.stairs(v2, e2, color=PR40, linewidth=1.2, linestyle="--",
              label=f"pr40 ({int(ex['pr40']['entries'])} entries)")
    same = ex["exact"]["values"] == ex["pr40"]["values"]
    name = ex["name"].replace("ROI_", "").replace("_width_10.0", "")
    ax.set_title(f"{name}: unchanged by the rule ({'identical' if same else 'DIFFERENT'})",
                 loc="left", fontsize=9)
    ax.set_xlabel("invariant mass [GeV]")
    ax.set_ylabel("weighted events / 10 GeV")
    ax.set_xlim(e1[0], min(e1[-1], e1[0] + 2500))
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule-check", required=True, type=pathlib.Path)
    ap.add_argument("--out-dir", required=True, type=pathlib.Path)
    args = ap.parse_args()
    rc = json.loads(args.rule_check.read_text())
    pd = rc["plot_data"]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = sorted(pd["per_pr40_final_state"], key=lambda r: -r["raw_events_pr40"])
    grouped_bars(rows, "n_histograms_exact_members", "n_histograms_pr40",
                 "exact build (sum over merged exact labels)", "PR #40 build",
                 "histograms", f"Histograms per final state: exact {rc['counts']['n_histograms_exact']}"
                 f" vs PR #40 {rc['counts']['n_histograms_pr40']} (ttbar 67801)",
                 args.out_dir / "1_histograms_per_final_state.png")
    grouped_bars(rows, "raw_events_exact_members_surviving", "raw_events_pr40",
                 "exact build (merged labels with >= 100 events)", "PR #40 build",
                 "raw MC events (log)", "Raw MC events per final state (ttbar 67801)",
                 args.out_dir / "2_raw_events_per_final_state.png", log=True)
    for i, ex in enumerate(pd["merged_examples"], 1):
        merged_plot(ex, args.out_dir / f"3_merged_{i}.png")
    if pd["unchanged_example"]:
        unchanged_plot(pd["unchanged_example"], args.out_dir / "4_unchanged.png")
    print("wrote", sorted(p.name for p in args.out_dir.glob("*.png")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
