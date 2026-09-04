#!/usr/bin/env python3
"""
plot_run_summary.py - two summary bar charts from a completed pipeline run:

  a) retention.png       - % of events surviving selection + de-dup, per record,
                           labelled with record id + trigger stream.
  b) bin_threshold.png   - how many produced histograms clear BumpNet's
                           ">30 bins" minimum vs how many fall short.

Retention numbers are read from the pipeline log's "Retention record_<id>: K / R
(P%)" lines (pass --run-log). Histogram bin counts are read from the run's
BumpNet ROOT file (pass --run-dir).

Usage:
    python scripts/plot_run_summary.py --run-dir output/<run> --run-log run.log \
        --out-dir reports/<x>/plots
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import uproot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# record id -> (short label, trigger stream)
RECORD_LABELS = {
    "30529": ("30529", "SingleElectron-G"),
    "30562": ("30562", "SingleElectron-H"),
    "30530": ("30530", "SingleMuon-G"),
    "30563": ("30563", "SingleMuon-H"),
}
RECORD_ORDER = ["30529", "30562", "30530", "30563"]

RETENTION_RE = re.compile(
    r"Retention\s+record_(\d+):\s*([\d,]+)\s*/\s*([\d,]+)\s*events kept\s*\(([\d.]+)%\)"
)


def parse_retention(log_path: Path) -> dict[str, tuple[int, int, float]]:
    out: dict[str, tuple[int, int, float]] = {}
    for line in log_path.read_text(errors="replace").splitlines():
        m = RETENTION_RE.search(line)
        if m:
            rid = m.group(1)
            kept = int(m.group(2).replace(",", ""))
            raw = int(m.group(3).replace(",", ""))
            pct = float(m.group(4))
            out[rid] = (kept, raw, pct)
    return out


def plot_retention(ret: dict, out_png: Path) -> None:
    rids = [r for r in RECORD_ORDER if r in ret] + [r for r in ret if r not in RECORD_ORDER]
    labels = [f"{RECORD_LABELS.get(r, (r, '?'))[0]}\n{RECORD_LABELS.get(r, (r, '?'))[1]}"
              for r in rids]
    pcts = [ret[r][2] for r in rids]
    kept = [ret[r][0] for r in rids]
    raw = [ret[r][1] for r in rids]
    colors = ["#c0504d" if "Electron" in RECORD_LABELS.get(r, (r, ""))[1] else "#3b7dd8"
              for r in rids]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, pcts, color=colors, edgecolor="#1f2d3d", linewidth=0.4)
    for b, k, rw, p in zip(bars, kept, raw, pcts):
        ax.text(b.get_x() + b.get_width() / 2, p + 1.2,
                f"{p:.1f}%\n{k/1e6:.2f}M / {rw/1e6:.2f}M",
                ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("events kept after selection + de-dup  [%]")
    ax.set_ylim(0, 100)
    ax.set_title("Per-record event retention (medium-scale 4-record run, 3 files/record)",
                 fontsize=11)
    ax.grid(axis="y", alpha=0.25)
    ax.axhline(0, color="k", lw=0.6)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    print(f"wrote {out_png}")


def hist_bin_counts(run_dir: Path):
    roots = sorted((run_dir / "histograms").glob("*.root"))
    if not roots:
        sys.exit(f"no histogram ROOT file under {run_dir}/histograms")
    f = uproot.open(roots[0])
    best: dict[str, int] = {}
    for key in f.keys():
        name = key.split(";")[0]
        cyc = int(key.split(";")[1]) if ";" in key else 1
        best[name] = max(best.get(name, 0), cyc)
    nbins = []
    for name, cyc in best.items():
        obj = f[f"{name};{cyc}"]
        if not hasattr(obj, "to_numpy"):
            continue
        vals, _ = obj.to_numpy()
        nbins.append(len(vals))
    return np.array(nbins)


def plot_bin_threshold(nbins: np.ndarray, out_png: Path) -> None:
    total = len(nbins)
    passing = int((nbins > 30).sum())
    failing = total - passing

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(["> 30 bins\n(BumpNet-usable width)", "≤ 30 bins\n(too few bins)"],
                  [passing, failing],
                  color=["#4a9d5b", "#b0562f"], edgecolor="#1f2d3d", linewidth=0.4)
    for b, v in zip(bars, [passing, failing]):
        ax.text(b.get_x() + b.get_width() / 2, v + total * 0.01,
                f"{v:,}\n({100*v/total:.0f}%)", ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("number of histograms")
    ax.set_title(f"Histograms vs BumpNet >30-bin threshold  "
                 f"({total:,} produced in total)", fontsize=11)
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, max(passing, failing) * 1.18)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    print(f"wrote {out_png}  ({passing} pass / {failing} fail / {total} total)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--run-log", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    ret = parse_retention(Path(args.run_log))
    if not ret:
        print("WARNING: no 'Retention record_...' lines found in the log", file=sys.stderr)
    else:
        plot_retention(ret, out_dir / "retention.png")

    nbins = hist_bin_counts(Path(args.run_dir))
    plot_bin_threshold(nbins, out_dir / "bin_threshold.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
