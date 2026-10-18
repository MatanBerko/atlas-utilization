#!/usr/bin/env python
"""
Peak fix step 4 (18-19 Oct 2026): the 17-18 Oct full-run build (per-sample
peak removal) vs the new build (--peak-scope combined). READ-ONLY on both.

Per histogram name of the summed-SM file: present in old / new, first and
last filled bin, total weight, and whether the histogram changed. Closure
of each build: sum of the per-sample histograms vs the summed-SM file, bin
by bin. Per-sample files: how many histograms changed. The 10 largest
changes (by |delta total| / old total, and by first-bin shift).

PNGs: the 6 stacked summed-SM plots redrawn from the new build
(new_stack_<i>.png), and stack 5 old vs new side by side.

Run (as a PBS job):
    python studies/cms_mc_weights_v3/peakfix/compare_old_new.py \
        --old-dir <fullrun>/build_default --old-prefix fullrun \
        --new-dir <work>/build_combined --new-prefix peakfix --out-dir <work>/evidence/compare
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from studies.cms_mc_weights_v3.peakfix.common import (  # noqa: E402
    INK, INK2, LUMI, RECORDS, SURF, category_names, draw_stack, filled_range,
    group_parts, read_build, style,
)


def closure(per: dict, summed: dict) -> dict:
    worst, worst_name = 0.0, None
    for name, h in summed.items():
        tot = np.zeros_like(h["values"])
        var = np.zeros_like(h["variances"])
        for rid in RECORDS:
            if name in per[rid]:
                tot += per[rid][name]["values"]
                var += per[rid][name]["variances"]
        scale = max(float(np.max(np.abs(h["values"]))), 1e-300)
        d = max(float(np.max(np.abs(tot - h["values"]))) / scale,
                float(np.max(np.abs(var - h["variances"]))) / max(float(np.max(np.abs(h["variances"]))), 1e-300))
        if d > worst:
            worst, worst_name = d, name
    return {"max_rel_diff_sum_per_sample_vs_summed": worst, "worst_histogram": worst_name}


def one_cut(per: dict, summed: dict) -> dict:
    """Every per-sample histogram's first filled bin must be >= the summed
    SM's first filled bin; with one cut per name, the summed SM's first filled
    bin is the common lower cut."""
    n_names, n_violations, n_samples_starting_later = 0, 0, 0
    for name, h in summed.items():
        r = filled_range(h["values"][1:-1])
        if r is None:
            continue
        n_names += 1
        for rid in RECORDS:
            if name in per[rid]:
                rr = filled_range(per[rid][name]["values"][1:-1])
                if rr is None:
                    continue
                if rr[0] < r[0]:
                    n_violations += 1
                if rr[0] > r[0]:
                    n_samples_starting_later += 1
    return {"n_names": n_names, "n_per_sample_starting_before_summed": n_violations,
            "n_per_sample_starting_after_summed_first_bin": n_samples_starting_later}


def side_by_side(name, title, old, new, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, (label, (per, summed)) in zip(axes, (("OLD: each sample cut at its own peak", old),
                                                  ("NEW: one cut on the combined spectrum", new))):
        if name not in summed:
            ax.set_title(f"{label}\n(histogram absent)", fontsize=9)
            continue
        h = summed[name]
        edges = h["edges"]
        parts = group_parts(name, per, len(edges) - 1)
        total = h["values"][1:-1]
        r = filled_range(total)
        lo, hi = (r[0], r[1] + 1) if r else (0, len(total))
        draw_stack(ax, edges, parts, lo, hi, True)
        ax.stairs(total[lo:hi], edges[lo:hi + 1], color=INK, lw=1.2, label=f"summed SM ({total.sum():,.4g})")
        c = 0.5 * (edges[lo:hi] + edges[lo + 1:hi + 1])
        ax.errorbar(c, total[lo:hi], yerr=np.sqrt(h["variances"][1:-1][lo:hi]), fmt="none", ecolor=INK2, lw=0.7)
        ax.set_yscale("log")
        ax.set_xlim(100, 1700)
        ax.set_xlabel("mass [GeV]", color=INK)
        ax.set_title(f"{label}\nfirst filled bin {edges[lo]:.0f} GeV", fontsize=9, color=INK)
        hh, ll = ax.get_legend_handles_labels()
        ax.legend(hh[::-1], ll[::-1], fontsize=7, frameon=False, loc="upper right")
        style(ax)
    axes[0].set_ylabel(f"weighted events / bin  (L = {LUMI} fb⁻¹)", color=INK)
    fig.suptitle(f"Summed SM, {title} — {name}", fontsize=10, color=INK)
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


def new_stack(name, title, per, summed, out: Path) -> dict:
    h = summed[name]
    edges = h["edges"]
    parts = group_parts(name, per, len(edges) - 1)
    total = h["values"][1:-1]
    r = filled_range(total)
    lo, hi = (r[0], r[1] + 1) if r else (0, len(total))
    fig, ax = plt.subplots(figsize=(8, 5))
    draw_stack(ax, edges, parts, lo, hi, True)
    ax.stairs(total[lo:hi], edges[lo:hi + 1], color=INK, lw=1.2, label=f"summed-SM file ({total.sum():,.4g})")
    c = 0.5 * (edges[lo:hi] + edges[lo + 1:hi + 1])
    ax.errorbar(c, total[lo:hi], yerr=np.sqrt(h["variances"][1:-1][lo:hi]), fmt="none", ecolor=INK2, lw=0.7)
    pos = total[lo:hi][total[lo:hi] > 0]
    if pos.size and pos.max() / pos.min() > 50:
        ax.set_yscale("log")
        ax.set_ylim(bottom=max(pos.min() * 0.3, pos.max() * 1e-6))
    ax.set_xlabel("mass [GeV]", color=INK)
    ax.set_ylabel(f"weighted events / bin  (L = {LUMI} fb⁻¹)", color=INK)
    ax.set_title(f"CMS MC, summed SM, peak removal on the combined spectrum — {title}\n{name}",
                 fontsize=9, color=INK)
    hh, ll = ax.get_legend_handles_labels()
    ax.legend(hh[::-1], ll[::-1], fontsize=7.5, frameon=False, loc="upper right")
    style(ax)
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    closure_groups = float(np.max(np.abs(sum(p[2] for p in parts) - total)) /
                           max(float(np.max(np.abs(total))), 1e-300))
    return {"png": out.name, "category": title, "histogram": name, "total_weighted": float(total.sum()),
            "first_filled_bin_gev": float(edges[lo]), "by_group": {p[0]: float(p[2].sum()) for p in parts},
            "max_rel_closure_groups_vs_summed_file": closure_groups}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-dir", required=True)
    ap.add_argument("--old-prefix", default="fullrun")
    ap.add_argument("--new-dir", required=True)
    ap.add_argument("--new-prefix", default="peakfix")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    old_per, old_sum = read_build(Path(args.old_dir), args.old_prefix)
    print(f"old: {len(old_sum)} summed histograms", flush=True)
    new_per, new_sum = read_build(Path(args.new_dir), args.new_prefix)
    print(f"new: {len(new_sum)} summed histograms", flush=True)

    names_old, names_new = set(old_sum), set(new_sum)
    rows = []
    for name in sorted(names_old & names_new):
        o, n = old_sum[name], new_sum[name]
        ro, rn = filled_range(o["values"][1:-1]), filled_range(n["values"][1:-1])
        to, tn = float(o["values"][1:-1].sum()), float(n["values"][1:-1].sum())
        changed = not (np.array_equal(o["values"], n["values"]) and np.array_equal(o["variances"], n["variances"]))
        rows.append({
            "name": name, "changed": changed,
            "old_first_gev": float(o["edges"][ro[0]]) if ro else None,
            "new_first_gev": float(n["edges"][rn[0]]) if rn else None,
            "old_last_gev": float(o["edges"][ro[1] + 1]) if ro else None,
            "new_last_gev": float(n["edges"][rn[1] + 1]) if rn else None,
            "old_total": to, "new_total": tn,
            "rel_change_total": (tn - to) / to if to else None,
            "first_bin_shift_bins": (int(rn[0] - ro[0]) if ro and rn else None),
            "last_bin_shift_bins": (int(rn[1] - ro[1]) if ro and rn else None),
        })
    changed = [r for r in rows if r["changed"]]
    rel = [abs(r["rel_change_total"]) for r in changed if r["rel_change_total"] is not None]
    shifts = [r["first_bin_shift_bins"] for r in changed if r["first_bin_shift_bins"] is not None]
    hist = lambda xs, edges: {f"{a}-{b}": int(sum(1 for x in xs if a <= x < b)) for a, b in zip(edges[:-1], edges[1:])}  # noqa: E731
    per_sample_changed = {}
    for rid in RECORDS:
        common = set(old_per[rid]) & set(new_per[rid])
        per_sample_changed[rid] = {
            "old": len(old_per[rid]), "new": len(new_per[rid]),
            "only_old": len(set(old_per[rid]) - set(new_per[rid])),
            "only_new": len(set(new_per[rid]) - set(old_per[rid])),
            "changed": sum(1 for k in common if not np.array_equal(old_per[rid][k]["values"], new_per[rid][k]["values"])),
        }

    summary = {
        "old_dir": args.old_dir, "new_dir": args.new_dir,
        "n_names_old": len(names_old), "n_names_new": len(names_new),
        "n_names_both": len(names_old & names_new),
        "names_only_old": sorted(names_old - names_new)[:50], "n_only_old": len(names_old - names_new),
        "names_only_new": sorted(names_new - names_old)[:50], "n_only_new": len(names_new - names_old),
        "n_summed_changed": len(changed), "n_summed_unchanged": len(rows) - len(changed),
        "rel_total_change_distribution": hist(rel, [0, 1e-6, 1e-3, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 1e9]),
        "first_bin_shift_distribution_bins": hist(shifts, [-1000, 0, 1, 2, 3, 6, 11, 21, 51, 1001]),
        "n_with_first_bin_moved_up": sum(1 for s in shifts if s > 0),
        "n_with_first_bin_moved_down": sum(1 for s in shifts if s < 0),
        "sum_total_old": sum(r["old_total"] for r in rows), "sum_total_new": sum(r["new_total"] for r in rows),
        "closure_old": closure(old_per, old_sum), "closure_new": closure(new_per, new_sum),
        "one_cut_old": one_cut(old_per, old_sum), "one_cut_new": one_cut(new_per, new_sum),
        "per_sample": per_sample_changed,
        "top10_by_rel_total_change": sorted(changed, key=lambda r: -abs(r["rel_change_total"] or 0))[:10],
        "top10_by_first_bin_shift": sorted(changed, key=lambda r: -abs(r["first_bin_shift_bins"] or 0))[:10],
        "top10_by_abs_total_change": sorted(changed, key=lambda r: -abs(r["new_total"] - r["old_total"]))[:10],
    }

    plots = []
    for i, title, name in category_names(new_sum):
        if name is None:
            plots.append({"category": title, "png": None})
            continue
        plots.append(new_stack(name, title, new_per, new_sum, out / f"new_stack_{i}.png"))
        if i == 5:
            # the same histogram as the old stack_5
            side_by_side(name, title, (old_per, old_sum), (new_per, new_sum), out / "stack_5_old_vs_new.png")
    summary["new_stacked_plots"] = plots
    summary["old_stack5_histogram"] = next((n for i, _t, n in category_names(old_sum) if i == 5), None)

    (out / "compare_old_new.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, default=str))
    print(json.dumps({k: v for k, v in summary.items() if not k.startswith("top10") and k != "new_stacked_plots"},
                     indent=1, default=str))
    for key in ("top10_by_rel_total_change", "top10_by_first_bin_shift"):
        print(f"\n{key}")
        for r in summary[key]:
            print(f"  {r['name']:<50} first {r['old_first_gev']}->{r['new_first_gev']}  "
                  f"total {r['old_total']:.6g}->{r['new_total']:.6g} ({100 * (r['rel_change_total'] or 0):+.2f}%)")
    for p in plots:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
