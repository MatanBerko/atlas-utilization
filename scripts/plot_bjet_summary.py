#!/usr/bin/env python3
"""
plot_bjet_summary.py - two plots from a CMS b-tagging pipeline run:

  a) bjet_fraction.png   - bar chart of untagged Jets vs DeepJet-tagged BJets
                           (from parsed_data/*.root), with the tagging %.
  b) bjet_mass_<name>.png - one real invariant-mass histogram from a final state
                            that contains at least one BJet, picked as the
                            best-populated such histogram in the run's BumpNet
                            ROOT file.

Usage:
    python scripts/plot_bjet_summary.py --run-dir output/<run> --out-dir reports/<x>/plots
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import uproot
import awkward as ak
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def count_jets(parsed_dir: Path) -> tuple[int, int, int]:
    """Return (untagged_jets, btagged_jets, n_events) summed over parsed_data."""
    tot_j = tot_b = tot_ev = 0
    for rf in sorted(parsed_dir.glob("*.root")):
        f = uproot.open(rf)
        tname = "events" if "events" in f else f.keys()[0].split(";")[0]
        t = f[tname]
        keys = [k.split(";")[0] for k in t.keys()]

        def count(coll: str) -> int:
            if "n" + coll in keys:
                return int(ak.sum(t["n" + coll].array()))
            cand = sorted(k for k in keys if k.startswith(coll + "_"))
            if not cand:
                return 0
            arr = t[cand[0]].array()
            try:
                return int(ak.count(arr))
            except Exception:
                return int(ak.sum(ak.num(arr)))

        tot_j += count("Jets")
        tot_b += count("BJets")
        tot_ev += t.num_entries
    return tot_j, tot_b, tot_ev


def plot_fraction(untagged: int, tagged: int, n_ev: int, wp: str, out_png: Path) -> None:
    total = untagged + tagged
    frac = tagged / total if total else 0.0
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(["untagged jets\n(Jets)", "b-tagged jets\n(BJets)"],
                  [untagged, tagged],
                  color=["#6b7f99", "#4a9d5b"], edgecolor="#1f2d3d", linewidth=0.4)
    for b, v in zip(bars, [untagged, tagged]):
        ax.text(b.get_x() + b.get_width() / 2, v + total * 0.01,
                f"{v:,}\n({100*v/total:.1f}%)", ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("number of jets")
    ax.set_title(f"CMS DeepJet b-tagging  ({wp})\n"
                 f"{total:,} reconstructed jets in {n_ev:,} events  ->  "
                 f"{frac*100:.2f}% tagged as b", fontsize=11)
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, max(untagged, tagged) * 1.18)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    print(f"wrote {out_png}  (untagged={untagged:,} tagged={tagged:,} frac={frac*100:.2f}%)")


# BumpNet names look like: ROI_mass_<combo>_cat_<Xe>ex_<Xm>mx_<Xj>jx_<Xg>gx_<Xt>tx_<Xb>bx_width_10.0
_BCOUNT_RE = re.compile(r"_(\d+)bx_")
_COMBO_RE = re.compile(r"ROI_mass_([a-z0-9]+)_cat_")


def plot_bjet_hist(run_dir: Path, out_dir: Path) -> None:
    roots = sorted((run_dir / "histograms").glob("*.root"))
    if not roots:
        sys.exit(f"no histogram ROOT file under {run_dir}/histograms")
    f = uproot.open(roots[0])
    best_cyc: dict[str, int] = {}
    for key in f.keys():
        name = key.split(";")[0]
        cyc = int(key.split(";")[1]) if ";" in key else 1
        best_cyc[name] = max(best_cyc.get(name, 0), cyc)

    cands = []
    for name, cyc in best_cyc.items():
        m = _BCOUNT_RE.search(name)
        cm = _COMBO_RE.search(name)
        has_b_in_combo = cm and "b" in cm.group(1)
        nb = int(m.group(1)) if m else 0
        if nb == 0 and not has_b_in_combo:
            continue
        obj = f[f"{name};{cyc}"]
        if not hasattr(obj, "to_numpy"):
            continue
        vals, edges = obj.to_numpy()
        cands.append((name, vals, edges, float(vals.sum()), int((vals > 0).sum())))

    if not cands:
        print("  no b-jet-involving histogram found in the ROOT file")
        return
    # prefer histograms where the b-jet is actually IN the mass combination
    # (combo name contains 'b'), then best-populated, then a real distribution.
    def combo_has_b(name: str) -> bool:
        cm = _COMBO_RE.search(name)
        return bool(cm and "b" in cm.group(1))

    pool = [c for c in cands if combo_has_b(c[0])] or cands
    real = [c for c in pool if c[4] >= 30] or pool
    real.sort(key=lambda c: c[3], reverse=True)
    name, vals, edges, tot, nfilled = real[0]

    centers = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(centers, vals, width=widths, align="center",
           color="#4a9d5b", edgecolor="#1f3f2e", linewidth=0.3)
    ax.set_title(f"b-jet final-state invariant mass (real pipeline output)\n"
                 f"{name}\n{int(round(tot)):,} entries, {nfilled} filled bins",
                 fontsize=10)
    ax.set_xlabel("invariant mass [GeV]")
    ax.set_ylabel("entries / 10 GeV bin")
    ax.grid(axis="y", alpha=0.25)
    ax.margins(x=0.01)
    fig.tight_layout()
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    out_png = out_dir / f"bjet_mass_{safe}.png"
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    print(f"wrote {out_png}  ({int(round(tot)):,} entries, {nfilled} filled bins)")

    print("\n  other well-populated b-jet histograms available:")
    for n, _, _, t2, nf in real[1:6]:
        print(f"    {n}  ({int(round(t2)):,} entries, {nf} filled bins)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--wp", default="DeepJet Medium WP, Jet_btagDeepFlavB > 0.2598")
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    j, b, ev = count_jets(run_dir / "parsed_data")
    plot_fraction(j, b, ev, args.wp, out_dir / "bjet_fraction.png")
    plot_bjet_hist(run_dir, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
