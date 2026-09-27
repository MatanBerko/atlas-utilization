#!/usr/bin/env python
"""
Three quick-look PNGs for the DoubleMuon BumpNet delivery, from the
manifest + ROOT files build_bumpnet_root.py already wrote (no new
analysis, no shard access -- reads only what that script already
produced and verified).

  1. largest.png  -- the histogram with the most events, from the
     >30-bin file.
  2. median.png   -- the histogram whose event count is the median of
     the >30-bin file's 316.
  3. near_25bin_boundary.png -- a histogram from the >25-bin file whose
     bin count is close to 26 (as near the boundary as the data allows),
     to show what the looser cut actually adds.

Usage:
    python make_check_plots.py --out-dir /storage/.../deliver_doublemuon_bumpnet
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

BIN_WIDTH_GEV = 10.0


def plot_one(root_path: Path, entry: dict, out_png: Path, title_suffix: str):
    f = uproot.open(str(root_path))
    hist = f[entry["root_key"]]
    values = hist.values()
    edges = hist.axis().edges()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.stairs(values, edges, fill=False, linewidth=1.2)
    ax.set_yscale("log")
    ax.set_xlabel("Invariant mass [GeV]")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_title(f"{entry['name']}\n{title_suffix}", fontsize=9)
    nonzero = values[values > 0]
    if nonzero.size:
        ax.set_ylim(bottom=max(0.5, nonzero.min() * 0.5))
    first = entry["first_filled_bin_low_edge_gev"]
    last = entry["last_filled_bin_high_edge_gev"]
    if first is not None and last is not None:
        ax.set_xlim(max(0, first - 5 * BIN_WIDTH_GEV), last + 5 * BIN_WIDTH_GEV)
    ax.text(
        0.98, 0.95,
        f"events={entry['n_events']}\nfilled bins={entry['n_filled_bins']}",
        transform=ax.transAxes, ha="right", va="top", fontsize=8,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"wrote {out_png}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    out_dir = Path(args.out_dir)

    manifest_a = json.loads((out_dir / "manifest_min31bins.json").read_text())
    manifest_b = json.loads((out_dir / "manifest_min26bins.json").read_text())
    root_a = out_dir / "doublemuon_bumpnet_min31bins.root"
    root_b = out_dir / "doublemuon_bumpnet_min26bins.root"

    by_events_a = sorted(manifest_a, key=lambda e: e["n_events"])
    largest = by_events_a[-1]
    median_idx = len(by_events_a) // 2
    median_entry = by_events_a[median_idx]

    names_a = set(e["name"] for e in manifest_a)
    extra_b = [e for e in manifest_b if e["name"] not in names_a]
    if extra_b:
        near_boundary = min(extra_b, key=lambda e: abs(e["n_filled_bins"] - 26))
        near_boundary_root = root_b
    else:
        # No extra histograms at all (unexpected but not impossible) --
        # fall back to the >30-bin file's own histogram closest to 30
        # bins, clearly labeled as such rather than silently picking
        # something misleading.
        near_boundary = min(manifest_a, key=lambda e: abs(e["n_filled_bins"] - 31))
        near_boundary_root = root_a
        print("NOTE: no histograms are unique to the >25-bin file; falling back to the "
              ">30-bin file's own histogram closest to the boundary.")

    plot_one(root_a, largest, out_dir / "plot_1_largest.png",
              f"Largest by event count ({root_a.name})")
    plot_one(root_a, median_entry, out_dir / "plot_2_median.png",
              f"Median by event count, position {median_idx+1}/{len(by_events_a)} ({root_a.name})")
    plot_one(near_boundary_root, near_boundary, out_dir / "plot_3_near_25bin_boundary.png",
              f"Near the 25-bin boundary ({near_boundary_root.name})")

    print(json.dumps({
        "largest": {"name": largest["name"], "n_events": largest["n_events"], "n_filled_bins": largest["n_filled_bins"]},
        "median": {"name": median_entry["name"], "n_events": median_entry["n_events"], "n_filled_bins": median_entry["n_filled_bins"]},
        "near_25bin_boundary": {"name": near_boundary["name"], "n_events": near_boundary["n_events"], "n_filled_bins": near_boundary["n_filled_bins"], "file": near_boundary_root.name},
    }, indent=2))


if __name__ == "__main__":
    main()
