#!/usr/bin/env python3
"""
plot_channels.py - plot specific invariant-mass histograms from a run's BumpNet
ROOT file to PNG.

Unlike scripts/make_cms_report.py (which auto-picks "representative" histograms),
this plots exactly the channels you name, so a report can be guaranteed to show
e.g. the dimuon histogram.

Usage:
    python scripts/plot_channels.py --run-dir output/<run> --out-dir reports/x/plots \
        --match m0m1 e0e1 e0j0 --top-per-match 1
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--match", nargs="+", required=True,
                    help="substrings to match against histogram names (e.g. m0m1)")
    ap.add_argument("--top-per-match", type=int, default=1,
                    help="plot the N highest-entry histograms per match string")
    args = ap.parse_args()

    hist_dir = Path(args.run_dir) / "histograms"
    roots = sorted(hist_dir.glob("*.root"))
    if not roots:
        sys.exit(f"no histogram ROOT file under {hist_dir}")
    f = uproot.open(roots[0])

    # highest cycle per name
    best = {}
    for key in f.keys():
        name = key.split(";")[0]
        cyc = int(key.split(";")[1]) if ";" in key else 1
        if name not in best or cyc > best[name]:
            best[name] = cyc

    hists = []
    for name, cyc in best.items():
        obj = f[f"{name};{cyc}"]
        if not hasattr(obj, "to_numpy"):
            continue
        vals, edges = obj.to_numpy()
        hists.append((name, vals, edges, float(vals.sum())))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for m in args.match:
        cand = sorted([h for h in hists if m in h[0]], key=lambda h: h[3], reverse=True)
        if not cand:
            print(f"  (no histogram matching '{m}')")
            continue
        for name, vals, edges, tot in cand[:args.top_per_match]:
            centers = 0.5 * (edges[:-1] + edges[1:])
            widths = np.diff(edges)
            nz = np.nonzero(vals)[0]
            fig, ax = plt.subplots(figsize=(9, 5))
            ax.bar(centers, vals, width=widths, align="center",
                   color="#3b7dd8", edgecolor="#1f3f6e", linewidth=0.3)
            if m in ("m0m1", "e0e1"):
                ax.axvline(91.1876, color="#d1495b", ls="--", lw=1.3, label="Z 91.2 GeV")
                ax.legend(loc="upper right", fontsize=9)
            ax.set_title(f"{name}\n{int(round(tot)):,} entries, "
                         f"{len(nz)} filled bins", fontsize=10)
            ax.set_xlabel("invariant mass [GeV]")
            ax.set_ylabel("entries / 10 GeV bin")
            ax.grid(axis="y", alpha=0.25)
            ax.margins(x=0.01)
            fig.tight_layout()
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
            png = out_dir / f"{safe}.png"
            fig.savefig(png, dpi=120)
            plt.close(fig)
            made.append(png)
            print(f"  wrote {png}  ({int(round(tot)):,} entries, {len(nz)} filled bins)")

    print(f"\n{len(made)} PNG(s) in {out_dir}")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
