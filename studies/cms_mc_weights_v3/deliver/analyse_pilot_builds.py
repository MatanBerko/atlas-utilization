#!/usr/bin/env python
"""
Pilot Part 3b + 3c: analyse the two pilot builds.

3b -- weighted vs unweighted peak finding.
  PR #35 locates the removed peak on the WEIGHTED spectrum; this design
  follows it. The question is whether that choice is harmless. Compares the
  default build against one that differs ONLY in `--peak-on unweighted`:
  how many histograms exist in both, for how many the peak-removal cut lands
  at a different mass, the distribution of that difference in GeV, and the ten
  largest differences by name. The default is NOT changed.

3c -- negative / empty bin inventory, for the summed file and each per-sample
  file. Every histogram with at least one bin <= 0 inside its filled range is
  counted, split into
     * "empty"      -- the bin received no entries at all (a statistics
                       problem: more MC, or wider bins)
     * "cancelling" -- the bin WAS filled and still came out <= 0, which only
                       negative generator weights can do
  with totals, the worst ten, and a PNG of two or three typical cases.

Reads the build reports and the ROOT files; writes a JSON and a PNG into
--out-dir and touches nothing else.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))


def peak_by_name(report: dict) -> dict:
    """{histogram name: peak_mass} over every kept histogram of every sample."""
    out = {}
    for rid, sample in report["samples"].items():
        for name, rec in sample["histograms"]["per_histogram"].items():
            if rec.get("kept"):
                out[(rid, name)] = rec.get("peak_mass")
    return out


def compare_peak_modes(weighted: dict, unweighted: dict) -> dict:
    pw, pu = peak_by_name(weighted), peak_by_name(unweighted)
    common = sorted(set(pw) & set(pu))
    diffs = []
    n_both_none = 0
    n_one_none = 0
    for key in common:
        a, b = pw[key], pu[key]
        if a is None and b is None:
            n_both_none += 1
            continue
        if a is None or b is None:
            n_one_none += 1
            diffs.append((key, a, b, None))
            continue
        if a != b:
            diffs.append((key, a, b, float(a - b)))
    numeric = [d[3] for d in diffs if d[3] is not None]
    arr = np.array(numeric) if numeric else np.array([])
    largest = sorted([d for d in diffs if d[3] is not None],
                     key=lambda d: -abs(d[3]))[:10]
    return {
        "n_histograms_weighted_build": len(pw),
        "n_histograms_unweighted_build": len(pu),
        "n_in_both": len(common),
        "n_only_in_weighted": len(set(pw) - set(pu)),
        "n_only_in_unweighted": len(set(pu) - set(pw)),
        "n_same_peak": len(common) - len(diffs) - 0,
        "n_different_peak": len(diffs),
        "fraction_different": (len(diffs) / len(common)) if common else None,
        "n_peak_none_in_both": n_both_none,
        "n_peak_none_in_exactly_one": n_one_none,
        "difference_gev": {
            "n": int(arr.size),
            "mean": float(arr.mean()) if arr.size else None,
            "median": float(np.median(arr)) if arr.size else None,
            "min": float(arr.min()) if arr.size else None,
            "max": float(arr.max()) if arr.size else None,
            "abs_median": float(np.median(np.abs(arr))) if arr.size else None,
            "abs_max": float(np.abs(arr).max()) if arr.size else None,
            "histogram_of_differences": (
                {str(int(b)): int(c) for b, c in zip(
                    *[a.tolist() for a in np.histogram(
                        arr, bins=np.arange(arr.min() - 5, arr.max() + 15, 10.0))[::-1]])}
                if arr.size else {}),
        },
        "ten_largest_differences": [
            {"record": k[0], "histogram": k[1],
             "peak_weighted_gev": a, "peak_unweighted_gev": b,
             "difference_gev": d}
            for (k, a, b, d) in largest
        ],
    }


def inventory_from_report(report: dict) -> dict:
    """3c for the per-sample files, from the build report's own inventory."""
    out = {}
    for rid, sample in report["samples"].items():
        kept = {n: r for n, r in sample["histograms"]["per_histogram"].items()
                if r.get("kept")}
        rows = []
        for name, rec in kept.items():
            inv = rec["negative_bin_inventory"]
            n_le0 = inv["n_bins_le_zero_in_filled_range"]
            if n_le0 == 0:
                continue
            rows.append({
                "histogram": name,
                "n_bins_in_filled_range": inv["n_bins_in_filled_range"],
                "n_bins_le_zero": n_le0,
                "n_empty_bins": inv["n_bins_never_filled_in_range"],
                "n_filled_bins_le_zero": inv["n_filled_bins_le_zero"],
                "n_filled_bins_lt_zero": inv["n_filled_bins_lt_zero"],
                "most_negative_content": inv["most_negative_content"],
            })
        rows.sort(key=lambda r: (-r["n_filled_bins_lt_zero"], -r["n_bins_le_zero"]))
        out[rid] = {
            "n_histograms": len(kept),
            "n_histograms_with_any_bin_le_zero": len(rows),
            "totals": {
                "bins_le_zero_in_filled_range": sum(r["n_bins_le_zero"] for r in rows),
                "empty_bins_in_filled_range": sum(r["n_empty_bins"] for r in rows),
                "filled_bins_le_zero_CANCELLING": sum(
                    r["n_filled_bins_le_zero"] for r in rows),
                "filled_bins_lt_zero_CANCELLING": sum(
                    r["n_filled_bins_lt_zero"] for r in rows),
            },
            "worst_ten": rows[:10],
        }
    return out


def inventory_from_root(root_path: pathlib.Path) -> dict:
    """3c for the summed file, recomputed from the ROOT file itself (the build
    report's summed inventory is keyed differently)."""
    sys.path.insert(0, str(REPO_ROOT))
    from studies.cms_mc_weights_v3.deliver.weighted_histograms import (
        negative_or_empty_bin_inventory,
    )
    rows = []
    n_hists = 0
    with uproot.open(str(root_path)) as f:
        for key in sorted({k.split(";")[0] for k in f.keys()}):
            h = f[key]
            if h.classname != "TH1D":
                continue
            n_hists += 1
            values = h.values(flow=False)
            errors = h.errors(flow=False)
            inv = negative_or_empty_bin_inventory(values, errors ** 2)
            if inv["n_bins_le_zero_in_filled_range"] == 0:
                continue
            rows.append({
                "histogram": key,
                "n_bins_in_filled_range": inv["n_bins_in_filled_range"],
                "n_bins_le_zero": inv["n_bins_le_zero_in_filled_range"],
                "n_empty_bins": inv["n_bins_never_filled_in_range"],
                "n_filled_bins_le_zero": inv["n_filled_bins_le_zero"],
                "n_filled_bins_lt_zero": inv["n_filled_bins_lt_zero"],
                "most_negative_content": inv["most_negative_content"],
            })
    rows.sort(key=lambda r: (-r["n_filled_bins_lt_zero"], -r["n_bins_le_zero"]))
    return {
        "root_file": str(root_path),
        "n_histograms": n_hists,
        "n_histograms_with_any_bin_le_zero": len(rows),
        "totals": {
            "bins_le_zero_in_filled_range": sum(r["n_bins_le_zero"] for r in rows),
            "empty_bins_in_filled_range": sum(r["n_empty_bins"] for r in rows),
            "filled_bins_le_zero_CANCELLING": sum(r["n_filled_bins_le_zero"] for r in rows),
            "filled_bins_lt_zero_CANCELLING": sum(r["n_filled_bins_lt_zero"] for r in rows),
        },
        "worst_ten": rows[:10],
        "_rows": rows,
    }


def plot_affected(root_path: pathlib.Path, rows: list, out_path: pathlib.Path) -> list:
    """A PNG of up to three typical affected histograms."""
    picks = [r for r in rows if r["n_filled_bins_lt_zero"] > 0][:2]
    picks += [r for r in rows if r["n_filled_bins_lt_zero"] == 0][:3 - len(picks)]
    picks = picks[:3]
    if not picks:
        return []
    fig, axes = plt.subplots(1, len(picks), figsize=(5.6 * len(picks), 4.3),
                             squeeze=False)
    axes = axes[0]
    shown = []
    with uproot.open(str(root_path)) as f:
        for ax, row in zip(axes, picks):
            h = f[row["histogram"]]
            v = h.values(flow=False)
            e = h.errors(flow=False)
            edges = h.axis().edges()
            c = 0.5 * (edges[:-1] + edges[1:])
            filled = np.nonzero(e > 0)[0]
            lo, hi = int(filled[0]), int(filled[-1])
            sl = slice(max(0, lo - 2), hi + 3)
            ax.errorbar(c[sl], v[sl], yerr=e[sl], fmt="o", ms=3.2, lw=1,
                        capsize=1.5, color="#2b6cb0")
            ax.axhline(0.0, color="#c05621", ls="--", lw=1)
            neg = [i for i in range(lo, hi + 1) if v[i] < 0 and e[i] > 0]
            if neg:
                ax.plot(c[neg], v[neg], "x", ms=9, mew=2, color="#c53030",
                        label="filled, still negative")
                ax.legend(fontsize=7.5)
            ax.set_title(row["histogram"].replace("ROI_mass_", ""), fontsize=7)
            ax.set_xlabel("invariant mass [GeV]")
            ax.set_ylabel("weighted events / 10 GeV")
            ax.grid(alpha=0.2, lw=0.5)
            shown.append(row["histogram"])
    fig.suptitle("CMS MC pilot -- typical histograms with non-positive bins "
                 "inside the filled range.\nRed crosses: bins that received "
                 "entries and still came out negative (negative generator "
                 "weights).", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"wrote {out_path}")
    return shown


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weighted-report", required=True)
    ap.add_argument("--unweighted-report", required=True)
    ap.add_argument("--summed-root", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    w = json.loads(pathlib.Path(args.weighted_report).read_text(encoding="utf-8"))
    u = json.loads(pathlib.Path(args.unweighted_report).read_text(encoding="utf-8"))

    peak = compare_peak_modes(w, u)
    per_sample = inventory_from_report(w)
    summed = inventory_from_root(pathlib.Path(args.summed_root))
    rows = summed.pop("_rows")
    shown = plot_affected(pathlib.Path(args.summed_root), rows,
                          out_dir / "P3c_negative_bins.png")

    report = {
        "what": "CMS MC pilot Part 3b/3c",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "3b_peak_mode_comparison": peak,
        "3b_note": "The default (weighted, PR #35's own choice) is NOT changed. "
                   "This is evidence about whether following it is harmless.",
        "3c_per_sample": per_sample,
        "3c_summed": summed,
        "3c_png": str(out_dir / "P3c_negative_bins.png"),
        "3c_histograms_shown": shown,
        "3c_definitions": {
            "empty": "a bin inside the filled range that received no entries "
                     "at all -- a statistics problem",
            "cancelling": "a bin that WAS filled and still came out <= 0 -- "
                          "only negative generator weights can do this",
        },
    }
    path = out_dir / "pilot_build_analysis.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("\n=== 3b: weighted vs unweighted peak finding ===")
    print(f"  histograms in both builds : {peak['n_in_both']:,}")
    print(f"  peak cut at a DIFFERENT mass: {peak['n_different_peak']:,}"
          f"  ({100 * (peak['fraction_different'] or 0):.3f}%)")
    d = peak["difference_gev"]
    if d["n"]:
        print(f"  difference (weighted - unweighted) GeV: median {d['median']}, "
              f"|median| {d['abs_median']}, range [{d['min']}, {d['max']}]")
    print("\n=== 3c: non-positive bins ===")
    t = summed["totals"]
    print(f"  summed file: {summed['n_histograms']:,} histograms, "
          f"{summed['n_histograms_with_any_bin_le_zero']:,} with >=1 bin <= 0")
    print(f"    bins <= 0 in filled range : {t['bins_le_zero_in_filled_range']:,}")
    print(f"      of which EMPTY          : {t['empty_bins_in_filled_range']:,}")
    print(f"      of which CANCELLING     : {t['filled_bins_le_zero_CANCELLING']:,}"
          f" (strictly negative: {t['filled_bins_lt_zero_CANCELLING']:,})")
    for rid, inv in sorted(per_sample.items()):
        tt = inv["totals"]
        print(f"  record {rid}: {inv['n_histograms']:,} histograms, "
              f"{inv['n_histograms_with_any_bin_le_zero']:,} affected; "
              f"cancelling bins {tt['filled_bins_le_zero_CANCELLING']:,}")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
