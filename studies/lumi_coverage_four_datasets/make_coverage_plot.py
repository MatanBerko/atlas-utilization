"""
Luminosity-coverage check, four datasets: the one figure.

A bar chart of the fraction of the official Run2016G+H recorded luminosity
that sits in certified lumisections absent from each dataset's own files,
with the 0.1% decision threshold drawn in. Log y-axis, because the measured
fractions are orders of magnitude below the threshold and a linear axis
would show four invisible bars.

Usage:
    python make_coverage_plot.py --summary <summary.json> --out <png>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DATASETS = ["DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG"]
THRESHOLD_PCT = 0.1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    per = data["per_dataset"]
    pcts = [per[d]["missing_pct_of_official_total"] for d in DATASETS]
    n_missing = [per[d]["n_missing"] for d in DATASETS]
    n_files = [per[d]["n_files"] for d in DATASETS]

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    bars = ax.bar(DATASETS, pcts, color="#4C78A8", width=0.6, zorder=3)

    ax.axhline(THRESHOLD_PCT, color="#D62728", linestyle="--", linewidth=1.6,
               zorder=4,
               label=f"decision threshold, {THRESHOLD_PCT}%")

    ax.set_yscale("log")
    ax.set_ylabel("recorded luminosity in missing certified lumisections\n"
                  "(% of 16.393380531 fb$^{-1}$)")
    ax.set_title("CMS Open Data Run2016G+H: luminosity missing from each "
                 "dataset's files", fontsize=11)
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.set_axisbelow(True)

    lo = min([p for p in pcts if p > 0], default=1e-5)
    ax.set_ylim(lo / 20.0, THRESHOLD_PCT * 8.0)

    for bar, pct, nm, nf in zip(bars, pcts, n_missing, n_files):
        ax.annotate(f"{pct:.4f}%\n{nm} sections missing\n{nf} files",
                    xy=(bar.get_x() + bar.get_width() / 2.0, bar.get_height()),
                    xytext=(0, 6), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8.5)

    ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
    fig.tight_layout()
    fig.savefig(args.out, dpi=160)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
