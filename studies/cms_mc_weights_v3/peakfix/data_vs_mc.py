#!/usr/bin/env python
"""
Peak fix steps 5 and 6 (18-19 Oct 2026): the new MC build vs the data
delivery, READ-ONLY on both.

Step 5, names: the histogram names in the data delivery (uncropped
*_bumpnet.root) vs the new summed-SM file -- in both / data-only / MC-only,
the data-only and MC-only lists grouped by final state, and for names in
both the first filled bin of data vs MC (agree / differ, by how many bins).

Step 6, data vs MC: the same 6 categories as the stacked plots (the MC
side's most-populated histogram of each), data points over the new MC
stack, linear and log, with a data/MC ratio panel; integrals printed.
Absolute normalisation; nothing tuned or rescaled.

Run (as a PBS job):
    python studies/cms_mc_weights_v3/peakfix/data_vs_mc.py \
        --data <delivery>/four_dataset_matched_vB_upstreamnames_w10p0_dr012_bumpnet.root \
        --new-dir <work>/build_combined --new-prefix peakfix --out-dir <work>/evidence/data_mc
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from studies.cms_mc_weights_v3.peakfix.common import (  # noqa: E402
    INK, INK2, LUMI, SURF, category_names, draw_stack, filled_range, group_parts,
    read_all, read_build, style,
)

CAT_RE = re.compile(r"_cat_(.+?)(?:_width_[0-9.]+)?$")


def final_state(name: str) -> str:
    m = CAT_RE.search(name)
    if not m:
        return "unparsed"
    return m.group(1).replace("x", "").replace("_", " ").strip().replace(" ", "_")


def names_section(data: dict, mc: dict) -> dict:
    dn, mn = set(data), set(mc)
    both, d_only, m_only = dn & mn, dn - mn, mn - dn
    group = lambda names: dict(sorted(Counter(final_state(n) for n in names).items(),  # noqa: E731
                                      key=lambda kv: -kv[1]))
    first = Counter()
    rows = []
    for n in sorted(both):
        rd, rm = filled_range(data[n]["values"][1:-1]), filled_range(mc[n]["values"][1:-1])
        if rd is None or rm is None:
            first["one_side_empty"] += 1
            continue
        d = rm[0] - rd[0]   # >0: MC starts later than data
        first["agree" if d == 0 else "differ"] += 1
        rows.append({"name": n, "data_first_gev": float(data[n]["edges"][rd[0]]),
                     "mc_first_gev": float(mc[n]["edges"][rm[0]]), "mc_minus_data_bins": int(d)})
    diffs = [r["mc_minus_data_bins"] for r in rows if r["mc_minus_data_bins"] != 0]
    bins = [(-10000, -10), (-10, -3), (-3, -1), (-1, 0), (1, 2), (2, 4), (4, 11), (11, 10000)]
    dist = {f"[{a},{b})": sum(1 for x in diffs if a <= x < b) for a, b in bins}
    edges_equal = all(np.array_equal(data[n]["edges"], mc[n]["edges"]) for n in both)
    return {
        "n_data": len(dn), "n_mc": len(mn), "n_both": len(both),
        "n_data_only": len(d_only), "n_mc_only": len(m_only),
        "data_only_by_final_state": group(d_only), "mc_only_by_final_state": group(m_only),
        "data_only_examples": sorted(d_only)[:30], "mc_only_examples": sorted(m_only)[:30],
        "first_filled_bin": dict(first),
        "first_bin_mc_minus_data_distribution_bins": dist,
        "n_mc_starts_later": sum(1 for x in diffs if x > 0),
        "n_mc_starts_earlier": sum(1 for x in diffs if x < 0),
        "same_bin_edges_for_all_common_names": edges_equal,
        "largest_first_bin_differences": sorted(rows, key=lambda r: -abs(r["mc_minus_data_bins"]))[:15],
        "rows": rows,
    }


def data_mc_plot(name, title, data_h, per, summed, out: Path, logy: bool) -> dict:
    h = summed[name]
    edges = h["edges"]
    parts = group_parts(name, per, len(edges) - 1)
    mc = h["values"][1:-1]
    mc_var = h["variances"][1:-1]
    d = data_h["values"][1:-1] if data_h is not None else np.zeros_like(mc)
    rm, rd = filled_range(mc), filled_range(d)
    lo = min(x[0] for x in (rm, rd) if x)
    hi = max(x[1] for x in (rm, rd) if x) + 1
    fig, (ax, axr) = plt.subplots(2, 1, figsize=(8, 6.2), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})
    draw_stack(ax, edges, parts, lo, hi, logy)
    e = edges[lo:hi + 1]
    c = 0.5 * (e[:-1] + e[1:])
    ax.stairs(mc[lo:hi], e, color=INK2, lw=0.8)
    ax.errorbar(c, d[lo:hi], yerr=np.sqrt(np.clip(d[lo:hi], 0, None)), fmt="o", ms=3, color=INK, lw=0.9,
                label=f"data 2016 G+H  ({d.sum():,.0f})")
    if logy:
        pos = np.concatenate([mc[lo:hi][mc[lo:hi] > 0], d[lo:hi][d[lo:hi] > 0]])
        if pos.size:
            ax.set_yscale("log")
            ax.set_ylim(bottom=max(pos.min() * 0.3, pos.max() * 1e-7))
    ax.set_ylabel("events / 10 GeV", color=INK)
    ax.set_title(f"Data vs MC (absolute, L = {LUMI} fb⁻¹, nothing rescaled) — {title}\n{name}",
                 fontsize=9, color=INK)
    hh, ll = ax.get_legend_handles_labels()
    ax.legend(hh[::-1], ll[::-1], fontsize=7, frameon=False, loc="upper right")
    style(ax)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(mc[lo:hi] > 0, d[lo:hi] / mc[lo:hi], np.nan)
        rerr = np.where(mc[lo:hi] > 0, np.sqrt(np.clip(d[lo:hi], 0, None)) / mc[lo:hi], np.nan)
        mc_band = np.where(mc[lo:hi] > 0, np.sqrt(mc_var[lo:hi]) / mc[lo:hi], np.nan)
    axr.fill_between(np.repeat(e, 2)[1:-1], np.repeat(1 - mc_band, 2), np.repeat(1 + mc_band, 2),
                     color="#c9c8c3", lw=0, label="MC stat.")
    axr.errorbar(c, ratio, yerr=rerr, fmt="o", ms=2.6, color=INK, lw=0.8)
    axr.axhline(1.0, color=INK2, ls="--", lw=0.8)
    axr.set_ylim(0, 2.5)
    axr.set_ylabel("data / MC", color=INK)
    axr.set_xlabel("mass [GeV]", color=INK)
    style(axr)
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    dt, mt = float(d.sum()), float(mc.sum())
    # the same ratio restricted to the bins where both are filled
    both = (d > 0) & (mc > 0)
    return {"png": out.name, "category": title, "histogram": name, "log": logy,
            "data_integral": dt, "mc_integral": mt, "mc_stat_error": float(np.sqrt(mc_var.sum())),
            "data_over_mc": dt / mt if mt else None,
            "data_over_mc_stat_error": (np.sqrt(dt) / mt) if mt else None,
            "data_first_gev": float(edges[rd[0]]) if rd else None,
            "mc_first_gev": float(edges[rm[0]]) if rm else None,
            "data_over_mc_common_filled_bins": (float(d[both].sum() / mc[both].sum()) if both.any() else None),
            "mc_by_group": {p[0]: float(p[2].sum()) for p in parts}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--new-dir", required=True)
    ap.add_argument("--new-prefix", default="peakfix")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    data = read_all(Path(args.data))
    print(f"data: {len(data)} histograms; e.g. {sorted(data)[:2]}", flush=True)
    per, summed = read_build(Path(args.new_dir), args.new_prefix)
    print(f"MC summed: {len(summed)} histograms", flush=True)

    names = names_section(data, summed)
    plots = []
    for i, title, name in category_names(summed):
        if name is None:
            continue
        for logy in (False, True):
            plots.append(data_mc_plot(name, title, data.get(name), per, summed,
                                      out / f"datamc_{i}_{'log' if logy else 'lin'}.png", logy))

    res = {"data_file": args.data, "mc_dir": args.new_dir, "names": names, "plots": plots}
    (out / "data_vs_mc.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in names.items() if k not in ("rows",)}, indent=1, default=str))
    for p in plots:
        if not p["log"]:
            print(f"{p['png']:<22} {p['category']:<40} data {p['data_integral']:>12,.0f}  MC {p['mc_integral']:>14,.1f}"
                  f"  data/MC {p['data_over_mc']:.4f}  first data {p['data_first_gev']} MC {p['mc_first_gev']}"
                  f"  common-bins ratio {p['data_over_mc_common_filled_bins']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
