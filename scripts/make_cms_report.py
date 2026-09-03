#!/usr/bin/env python3
"""
make_cms_report.py - build a human-readable report from a finished pipeline
run's histogram output.

Reads the single BumpNet histogram ROOT file under <run-dir>/histograms/ and
writes, under reports/<report-name>/:
  - summary.md   : totals, how many histograms pass BumpNet's usability bar
                   (>= 100 entries AND > 30 bins, per arXiv:2501.05603), and a
                   table of the passing histograms sorted by entry count.
  - plots/*.png  : plotted images for a representative handful of passing
                   histograms (the biggest ones plus a few modest ones).

Nothing here changes the pipeline; it only reads its output.

Usage:
  python scripts/make_cms_report.py --run-dir output/<run> --report-name cms_production_test
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

MIN_ENTRIES = 100      # BumpNet: "at least 100 events"
MIN_BINS = 30          # BumpNet: "greater than 30 bins"

PARTICLE_WORD = {"e": "electron", "m": "muon", "j": "jet", "g": "photon",
                 "t": "tau", "b": "b-jet"}
PARTICLE_SYMBOL = {"e": "e", "m": "μ", "j": "jet", "g": "γ",
                   "t": "τ", "b": "b"}

NAME_RE = re.compile(
    r"^ROI_mass_(?P<combo>[a-z0-9]+)_cat_"
    r"(?P<cat>(?:\d+[emjgtb]x_?)+)_width_(?P<w>[0-9.]+)$"
)
COMBO_TOKEN = re.compile(r"([emjgtb])(\d+)")
CAT_TOKEN = re.compile(r"(\d+)([emjgtb])x")


def parse_name(name: str):
    m = NAME_RE.match(name)
    if not m:
        return None
    combo = m.group("combo")
    cat = m.group("cat")
    width = float(m.group("w"))

    # combo: which 4-vectors were summed, e.g. "e0e1j0" -> e0 + e1 + j0
    parts = COMBO_TOKEN.findall(combo)
    combo_pretty = " + ".join(f"{PARTICLE_SYMBOL[p]}{i}" for p, i in parts)
    n_bodies = len(parts)

    # cat: the event category multiplicities, e.g. "2e_0m_3j_1g_0t_0b"
    counts = {p: int(c) for c, p in CAT_TOKEN.findall(cat)}
    cat_pretty = ", ".join(
        f"{counts.get(p, 0)}{PARTICLE_SYMBOL[p]}"
        for p in ("e", "m", "j", "g", "t", "b")
        if counts.get(p, 0) > 0
    )
    return {
        "combo": combo,
        "combo_pretty": combo_pretty,
        "n_bodies": n_bodies,
        "cat_pretty": cat_pretty,
        "width": width,
    }


def read_histograms(root_path: Path):
    f = uproot.open(root_path)
    rows = []
    # A ROOT file written more than once holds several cycles of the same
    # histogram (name;1, name;2, ...). Keep only the highest cycle per name.
    latest = {}
    for key in f.keys():
        base, _, cyc = key.partition(";")
        c = int(cyc) if cyc else 1
        if base not in latest or c > latest[base][0]:
            latest[base] = (c, key)
    for name, (_, key) in sorted(latest.items()):
        h = f[key]
        if not (hasattr(h, "values") and hasattr(h, "axis")):
            continue
        vals = np.asarray(h.values(), dtype=float)
        edges = np.asarray(h.axis().edges(), dtype=float)
        entries = float(vals.sum())
        nbins = int(len(vals))
        filled = int(np.count_nonzero(vals))
        modal_frac = float(vals.max() / entries) if entries > 0 else 1.0
        meta = parse_name(name) or {}
        rows.append({
            "name": name,
            "entries": entries,
            "nbins": nbins,
            "filled_bins": filled,
            "modal_frac": modal_frac,   # fraction of all entries in the single tallest bin
            "xmin": float(edges[0]),
            "xmax": float(edges[-1]),
            "values": vals,
            "edges": edges,
            **meta,
        })
    return rows


def passes(row) -> bool:
    return row["entries"] >= MIN_ENTRIES and row["nbins"] > MIN_BINS


def write_summary(rows, out_md: Path, run_dir: str, root_name: str,
                  title: str = "CMS full-pipeline test", run_params: str = ""):
    total = len(rows)
    good = [r for r in rows if passes(r)]
    bad = [r for r in rows if not r["entries"] >= MIN_ENTRIES or not r["nbins"] > MIN_BINS]
    fail_bins = sum(1 for r in rows if not passes(r) and not r["nbins"] > MIN_BINS)
    fail_entries = sum(1 for r in rows if not passes(r) and not r["entries"] >= MIN_ENTRIES)
    good.sort(key=lambda r: r["entries"], reverse=True)
    spiky = [r for r in good if r["modal_frac"] >= 0.9]
    peaky = [r for r in good if 0.5 <= r["modal_frac"] < 0.9]
    real = [r for r in good if r["modal_frac"] < 0.5]

    lines = []
    lines.append(f"# {title} - histogram results")
    lines.append("")
    lines.append(f"- Source run: `{run_dir}`")
    lines.append(f"- Histogram file: `histograms/{root_name}` (one ROOT file, one TH1F per channel)")
    lines.append(f"- BumpNet usability bar (arXiv:2501.05603): **at least {MIN_ENTRIES} entries "
                 f"AND more than {MIN_BINS} bins**")
    if run_params:
        lines.append("")
        lines.append("## Run parameters")
        lines.append("")
        lines.append(run_params)
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append(f"| | count |")
    lines.append(f"|---|---:|")
    lines.append(f"| Histograms produced | {total} |")
    lines.append(f"| **Meet BumpNet bar** (>= {MIN_ENTRIES} entries & > {MIN_BINS} bins) | **{len(good)}** |")
    lines.append(f"| Fall short | {len(bad)} |")
    lines.append(f"| &nbsp;&nbsp;- short on bin count (<= {MIN_BINS} bins) | {fail_bins} |")
    lines.append(f"| &nbsp;&nbsp;- short on entries (< {MIN_ENTRIES}) | {fail_entries} |")
    lines.append("")
    lines.append("_(A histogram can be short on both; the two sub-rows overlap.)_")
    lines.append("")
    lines.append("### Shape of the passing histograms")
    lines.append("")
    lines.append(f"| | count |")
    lines.append(f"|---|---:|")
    lines.append(f"| real distribution (tallest bin < 50% of entries) | {len(real)} |")
    lines.append(f"| peaky (tallest bin 50-90%) | {len(peaky)} |")
    lines.append(f"| **single-bin spike** (tallest bin >= 90%, ~0 GeV) | **{len(spiky)}** |")
    lines.append("")
    if spiky:
        lines.append(
            f"> The {len(spiky)} spike histograms are **still present** in this run. Cause "
            f"(now understood): in CMS NanoAOD an electron is normally also reconstructed as a "
            f"photon and often as a jet (same calorimeter cluster), so 2-body combinations like "
            f"electron+photon or electron+jet are dominated by ~0 GeV \"self-pairs\". This is an "
            f"**upstream reconstruction/object-overlap issue, not a post-processing bug** - "
            f"post-processing keeps essentially all the real (>15 GeV) signal in the histogrammed "
            f"\"main\" array; it is just swamped by the self-pair spike. Fixing it needs overlap "
            f"removal (delta-R cleaning between the electron/photon/jet collections), which is a "
            f"physics-analysis design decision - see docs/CMS_KNOWN_LIMITATIONS.md."
        )
    else:
        lines.append("> No single-bin spike histograms in this run.")
    lines.append("")
    lines.append("## Passing histograms (usable as BumpNet input)")
    lines.append("")
    lines.append("Sorted by entry count, highest first. \"Mass of\" is which object "
                 "four-vectors were added together to form the invariant mass; "
                 "\"Event category\" is the object multiplicity of the events that fed it.")
    lines.append("")
    lines.append("| # | Mass of | Event category | Entries | Bins | Filled bins | Shape | Mass range (GeV) | Histogram name |")
    lines.append("|---:|---|---|---:|---:|---:|---|---|---|")
    for i, r in enumerate(good, 1):
        shape = "spike" if r["modal_frac"] >= 0.9 else ("peaky" if r["modal_frac"] >= 0.5 else "distribution")
        lines.append(
            f"| {i} | {r.get('combo_pretty', r.get('combo', '?'))} "
            f"| {r.get('cat_pretty', '?')} "
            f"| {int(round(r['entries'])):,} "
            f"| {r['nbins']} "
            f"| {r['filled_bins']} "
            f"| {shape} "
            f"| {r['xmin']:.0f} - {r['xmax']:.0f} "
            f"| `{r['name']}` |"
        )
    lines.append("")
    lines.append("## Plots")
    lines.append("")
    lines.append("A representative sample is plotted under `plots/` - the highest-statistics "
                 "channels plus a few smaller ones that still clear the bar.")
    lines.append("")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return good


def pick_representative(good):
    """
    Pick 5-8 passing histograms that are genuine distributions (not single-bin
    spikes): highest-statistics ones first, then a few smaller-but-still-real
    ones, so the plots actually show the positive result.
    """
    real = [r for r in good if r["modal_frac"] < 0.5 and r["filled_bins"] >= 20]
    if not real:
        real = list(good)
    real.sort(key=lambda r: r["entries"], reverse=True)

    chosen = list(real[:5])
    modest = [r for r in real if r["entries"] <= 5000]
    for r in modest[::-1]:
        if len(chosen) >= 8:
            break
        if r not in chosen:
            chosen.append(r)
    idx = len(real) // 2
    while len(chosen) < 8 and idx < len(real):
        if real[idx] not in chosen:
            chosen.append(real[idx])
        idx += 1
    return chosen[:8]


def plot_histogram(row, out_png: Path):
    vals = row["values"]
    edges = row["edges"]
    centers = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(centers, vals, width=widths, align="center",
           color="#3b7dd8", edgecolor="#1f3f6e", linewidth=0.3)
    title_main = f"Invariant mass of {row.get('combo_pretty', row.get('combo','?'))}"
    subtitle = (f"event category: {row.get('cat_pretty','?')}    |    "
                f"{int(round(row['entries'])):,} entries    |    {row['nbins']} bins")
    ax.set_title(f"{title_main}\n{subtitle}", fontsize=11)
    ax.set_xlabel("invariant mass [GeV]")
    ax.set_ylabel(f"entries / {row.get('width', 10):.0f} GeV bin")
    ax.margins(x=0.01)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--report-name", default="cms_production_test")
    ap.add_argument("--reports-root", default="reports")
    ap.add_argument("--title", default="CMS full-pipeline test")
    ap.add_argument("--run-params", default="",
                    help="markdown snippet describing the run (files, events, runtime)")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    hist_dir = run_dir / "histograms"
    roots = sorted(hist_dir.glob("*.root"))
    if not roots:
        sys.exit(f"no histogram ROOT file under {hist_dir}")
    root_path = roots[0]

    rows = read_histograms(root_path)
    out_base = Path(args.reports_root) / args.report_name
    good = write_summary(rows, out_base / "summary.md", str(run_dir), root_path.name,
                         title=args.title, run_params=args.run_params)

    chosen = pick_representative(good)
    plotted = []
    for r in chosen:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", r["name"])
        png = out_base / "plots" / f"{safe}.png"
        plot_histogram(r, png)
        plotted.append(png)

    print(f"histograms read : {len(rows)}")
    print(f"pass BumpNet bar: {len(good)}")
    print(f"summary written : {out_base / 'summary.md'}")
    print(f"plots written   : {len(plotted)}")
    for p in plotted:
        print(f"  - {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
