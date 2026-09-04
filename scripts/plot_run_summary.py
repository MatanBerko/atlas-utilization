#!/usr/bin/env python3
"""
plot_run_summary.py - two summary bar charts from a completed pipeline run:

  a) retention.png       - % of events surviving selection + de-dup, per record,
                           labelled with record id + trigger stream.
  b) bin_threshold.png   - how the produced histograms split across BOTH of
                           BumpNet's usability requirements together
                           (> 30 bins AND >= 100 entries), not just one of them.

Retention numbers are read from the pipeline log's "Retention record_<id>: K / R
(P%)" lines (pass --run-log). The histogram breakdown normally comes from the
run's BumpNet ROOT file (pass --run-dir); when that file is no longer available
(pipeline output is gitignored and not kept long-term) the same 4 counts can be
supplied directly with --bumpnet-counts, derived from whatever aggregate
pass/fail numbers were already computed for that run - see categorize_bumpnet()
for the exact definitions and the inclusion-exclusion identity that recovers
the 4-way split from just the "total", "pass both", "fail on bins" and "fail on
entries" counts a report may already state.

Usage:
    python scripts/plot_run_summary.py --run-dir output/<run> --run-log run.log \
        --out-dir reports/<x>/plots
    python scripts/plot_run_summary.py --bumpnet-counts 2161,387,18,220 \
        --out-dir reports/<x>/plots   # pass_both,fail_bins_only,fail_entries_only,fail_both
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

# BumpNet usability bar (arXiv:2501.05603): at least 100 entries AND more than
# 30 bins - the two conditions apply together, not separately.
MIN_ENTRIES = 100
MIN_BINS = 30

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


def hist_entries_and_bins(run_dir: Path):
    """Per-histogram (entries, nbins) arrays from the run's BumpNet ROOT file -
    the same underlying data make_cms_report.py uses for its pass/fail counts."""
    roots = sorted((run_dir / "histograms").glob("*.root"))
    if not roots:
        sys.exit(f"no histogram ROOT file under {run_dir}/histograms")
    f = uproot.open(roots[0])
    best: dict[str, int] = {}
    for key in f.keys():
        name = key.split(";")[0]
        cyc = int(key.split(";")[1]) if ";" in key else 1
        best[name] = max(best.get(name, 0), cyc)
    entries, nbins = [], []
    for name, cyc in best.items():
        obj = f[f"{name};{cyc}"]
        if not hasattr(obj, "to_numpy"):
            continue
        vals, _ = obj.to_numpy()
        entries.append(float(np.asarray(vals).sum()))
        nbins.append(len(vals))
    return np.array(entries), np.array(nbins)


def categorize_bumpnet(entries: np.ndarray, nbins: np.ndarray) -> dict[str, int]:
    """Split histograms into the 4 combinations of BumpNet's two requirements.

    Equivalently recoverable from just the totals a report already states -
    total, pass_both, and the two "fails on X regardless of Y" counts
    (fail_bins_regardless = count with nbins<=30; fail_entries_regardless =
    count with entries<100) - via inclusion-exclusion:
        fail_both        = fail_bins_regardless + fail_entries_regardless
                            - (total - pass_both)
        fail_bins_only    = fail_bins_regardless - fail_both
        fail_entries_only = fail_entries_regardless - fail_both
    """
    entries_ok = entries >= MIN_ENTRIES
    bins_ok = nbins > MIN_BINS
    return {
        "pass_both": int((entries_ok & bins_ok).sum()),
        "fail_bins_only": int((entries_ok & ~bins_ok).sum()),
        "fail_entries_only": int((~entries_ok & bins_ok).sum()),
        "fail_both": int((~entries_ok & ~bins_ok).sum()),
    }


def plot_bin_threshold(counts: dict[str, int], out_png: Path) -> None:
    total = sum(counts.values())
    order = ["pass_both", "fail_bins_only", "fail_entries_only", "fail_both"]
    labels = [
        f">30 bins AND >=100 entries\n(BumpNet-usable)",
        f">=100 entries, <=30 bins\n(fails on bins only)",
        f">30 bins, <100 entries\n(fails on entries only)",
        f"<=30 bins AND <100 entries\n(fails both)",
    ]
    values = [counts[k] for k in order]
    colors = ["#4a9d5b", "#c98a2c", "#b0562f", "#8a3b3b"]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor="#1f2d3d", linewidth=0.4, width=0.65)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + total * 0.01,
                f"{v:,}\n({100*v/total:.1f}%)", ha="center", va="bottom", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("number of histograms")
    ax.set_title("BumpNet usability: >30 bins AND >=100 entries required\n"
                 f"({total:,} histograms produced in total)", fontsize=11)
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, max(values) * 1.22)
    ax.set_xlim(-0.6, len(labels) - 0.4)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    print(f"wrote {out_png}  " + "  ".join(f"{k}={counts[k]}" for k in order) +
          f"  total={total}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", help="run dir with histograms/*.root (for bin_threshold + retention context)")
    ap.add_argument("--run-log", help="pipeline log with 'Retention record_...' lines")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--bumpnet-counts",
                    help="pass_both,fail_bins_only,fail_entries_only,fail_both - use instead of "
                         "--run-dir when the run's ROOT file is no longer on disk")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)

    if args.run_log:
        ret = parse_retention(Path(args.run_log))
        if not ret:
            print("WARNING: no 'Retention record_...' lines found in the log", file=sys.stderr)
        else:
            plot_retention(ret, out_dir / "retention.png")

    if args.bumpnet_counts:
        vals = [int(x) for x in args.bumpnet_counts.split(",")]
        if len(vals) != 4:
            sys.exit("--bumpnet-counts needs exactly 4 comma-separated integers: "
                     "pass_both,fail_bins_only,fail_entries_only,fail_both")
        counts = dict(zip(
            ["pass_both", "fail_bins_only", "fail_entries_only", "fail_both"], vals))
        plot_bin_threshold(counts, out_dir / "bin_threshold.png")
    elif args.run_dir:
        entries, nbins = hist_entries_and_bins(Path(args.run_dir))
        counts = categorize_bumpnet(entries, nbins)
        plot_bin_threshold(counts, out_dir / "bin_threshold.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
