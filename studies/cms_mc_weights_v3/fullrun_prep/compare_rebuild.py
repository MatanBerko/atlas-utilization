#!/usr/bin/env python
"""
Full-run preparation (17 Oct 2026), Part B2/B3: the pilot re-built with the
reviewed registry vs the 10 Oct pilot build 3a, histogram by histogram.

Expectation, from the registry alone (production does not read cross
sections, and the builder's sigma_eff enters only as one multiplicative
normalisation factor per sample):

  * 67801 ttbar (89.28 pb, unchanged)   -> IDENTICAL
  * 35669 DY    (5765.4 pb, unchanged)  -> IDENTICAL
  * 37728 ggH   0.013447 -> 0.013335 pb -> every bin x r, every variance
    (sum w^2) x r^2, with r = 0.013335 / 0.013447
  * summed SM -> differs from the old one ONLY by the ggH change, bin by bin:
    new_sum - old_sum == new_ggH - old_ggH (to float round-off)

Names, bin edges, entry counts and titles must be identical everywhere.
Anything else is reported as an UNEXPECTED difference.

Both sides are read with uproot from local copies; nothing is written next to
the inputs. Writes one JSON and the B3 PNGs into --out-dir.

Run:
    python studies/cms_mc_weights_v3/fullrun_prep/compare_rebuild.py \
        --old <copy of 10 Oct build_default> --new <copy of 17 Oct build_default> \
        --out-dir <dir>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

SIGMA_GGH_OLD = 0.013447
SIGMA_GGH_NEW = 0.013335
R_GGH = SIGMA_GGH_NEW / SIGMA_GGH_OLD
FILES = {
    "67801": ("pilot_record67801_mc.root", 1.0, "ttbar 67801 TTTo2L2Nu"),
    "35669": ("pilot_record35669_mc.root", 1.0, "DY 35669 DYJetsToLL_M-50 NLO"),
    "37728": ("pilot_record37728_mc.root", R_GGH, "ggH 37728 GluGluHToZZTo4L"),
}
SUMMED = "pilot_summedSM_mc.root"
OLD_COLOR, NEW_COLOR = "#2a78d6", "#eb6834"
INK, INK2 = "#0b0b0b", "#52514e"


def read_root(path: Path) -> dict:
    out = {}
    with uproot.open(path) as f:
        for key in f.keys(cycle=False):
            h = f[key]
            if not hasattr(h, "values"):
                continue
            out[key] = {
                "edges": np.asarray(h.axis().edges(flow=False), dtype=np.float64),
                "values": np.asarray(h.values(flow=True), dtype=np.float64),
                "variances": np.asarray(h.variances(flow=True), dtype=np.float64),
                "entries": float(h.member("fEntries")),
                "title": str(h.member("fTitle")),
            }
    return out


def _max_rel(new: np.ndarray, expect: np.ndarray) -> tuple[float, int]:
    """Largest |new/expect - 1| over bins where expect != 0, and the number
    of bins where expect == 0 but new != 0."""
    nz = expect != 0
    rel = float(np.max(np.abs(new[nz] / expect[nz] - 1.0))) if nz.any() else 0.0
    return rel, int(np.count_nonzero(new[~nz]))


def structure_diffs(old: dict, new: dict) -> list:
    diffs = []
    if set(old) != set(new):
        diffs.append({"what": "histogram names", "only_old": sorted(set(old) - set(new))[:50],
                      "only_new": sorted(set(new) - set(old))[:50]})
    for k in sorted(set(old) & set(new)):
        a, b = old[k], new[k]
        if a["edges"].shape != b["edges"].shape or a["edges"].tobytes() != b["edges"].tobytes():
            diffs.append({"what": "edges", "histogram": k})
        if a["entries"] != b["entries"]:
            diffs.append({"what": "entries", "histogram": k, "old": a["entries"], "new": b["entries"]})
        if a["title"] != b["title"]:
            diffs.append({"what": "title", "histogram": k})
    return diffs


def compare_sample(old: dict, new: dict, factor: float) -> dict:
    res = {"n_histograms_old": len(old), "n_histograms_new": len(new),
           "expected_factor": factor, "structure_differences": structure_diffs(old, new)}
    common = sorted(set(old) & set(new))
    n_bins = n_bitwise = 0
    max_rel_v = max_rel_var = 0.0
    zero_viol = 0
    worst = None
    for k in common:
        a, b = old[k], new[k]
        n_bins += a["values"].size
        bit = a["values"].tobytes() == b["values"].tobytes() and \
            a["variances"].tobytes() == b["variances"].tobytes()
        n_bitwise += bit
        rv, zv = _max_rel(b["values"], factor * a["values"])
        rw, zw = _max_rel(b["variances"], factor * factor * a["variances"])
        zero_viol += zv + zw
        if rv > max_rel_v:
            max_rel_v, worst = rv, k
        max_rel_var = max(max_rel_var, rw)
    sum_old = float(sum(old[k]["values"].sum() for k in common))
    sum_new = float(sum(new[k]["values"].sum() for k in common))
    res.update({
        "n_histograms_compared": len(common),
        "n_bins_compared_incl_flow": n_bins,
        "n_histograms_bitwise_identical": n_bitwise,
        "all_bitwise_identical": n_bitwise == len(common) and len(old) == len(new),
        "max_rel_deviation_values_from_expectation": max_rel_v,
        "max_rel_deviation_variances_from_expectation": max_rel_var,
        "histogram_with_max_values_deviation": worst,
        "bins_zero_in_expectation_but_nonzero_new": zero_viol,
        "sum_of_weights_old": sum_old, "sum_of_weights_new": sum_new,
        "ratio_of_sums_new_over_old": sum_new / sum_old if sum_old else None,
    })
    return res


def compare_summed(old_s: dict, new_s: dict, old_g: dict, new_g: dict) -> dict:
    res = {"n_histograms_old": len(old_s), "n_histograms_new": len(new_s),
           "structure_differences": structure_diffs(old_s, new_s)}
    common = sorted(set(old_s) & set(new_s))
    max_abs = max_rel_sum = max_rel_ggh = 0.0
    n_changed_without_ggh = n_unchanged = 0
    n_bins = 0
    for k in common:
        a, b = old_s[k]["values"], new_s[k]["values"]
        n_bins += a.size
        dg = (new_g[k]["values"] - old_g[k]["values"]) if k in old_g and k in new_g \
            else np.zeros_like(a)
        if k not in old_g:
            if a.tobytes() != b.tobytes():
                n_changed_without_ggh += 1
            else:
                n_unchanged += 1
            continue
        dev = np.abs((b - a) - dg)
        max_abs = max(max_abs, float(dev.max()))
        nz = a != 0
        if nz.any():
            max_rel_sum = max(max_rel_sum, float(np.max(dev[nz] / np.abs(a[nz]))))
        g = np.abs(dg) > 0
        if g.any():
            # how well (new - old) of the sum reproduces the ggH change itself;
            # limited by float round-off of the larger ttbar+DY sum
            max_rel_ggh = max(max_rel_ggh, float(np.max(dev[g] / np.abs(dg[g]))))
    res.update({
        "n_histograms_compared": len(common),
        "n_bins_compared_incl_flow": n_bins,
        "n_histograms_without_ggh_contribution": n_unchanged + n_changed_without_ggh,
        "n_histograms_without_ggh_that_CHANGED": n_changed_without_ggh,
        "max_abs_deviation_of_(new_sum-old_sum)_from_(new_ggH-old_ggH)": max_abs,
        "same_relative_to_the_old_summed_bin": max_rel_sum,
        "same_relative_to_the_ggH_change_itself": max_rel_ggh,
        "sum_of_weights_old": float(sum(old_s[k]["values"].sum() for k in common)),
        "sum_of_weights_new": float(sum(new_s[k]["values"].sum() for k in common)),
    })
    return res


def overlay(h_old: dict, h_new: dict, expect: float, title: str, path: Path) -> dict:
    o = h_old["values"][1:-1]
    n = h_new["values"][1:-1]
    e = h_old["edges"]
    nz = np.flatnonzero((o != 0) | (n != 0))
    lo, hi = (nz[0], nz[-1] + 1) if nz.size else (0, len(o))
    e, o, n = e[lo:hi + 1], o[lo:hi], n[lo:hi]
    fig, (ax, rx) = plt.subplots(2, 1, figsize=(7.5, 5.6), sharex=True,
                                 gridspec_kw={"height_ratios": [3, 1.3], "hspace": 0.06})
    ax.stairs(o, e, color=OLD_COLOR, lw=2, label="10 Oct build 3a (old registry)")
    ax.stairs(n, e, color=NEW_COLOR, lw=2, ls="--", label="17 Oct re-build (reviewed registry)")
    if (o > 0).sum() > 0.5 * len(o):
        ax.set_yscale("log")
    ax.set_ylabel("weighted events / bin", color=INK)
    ax.set_title(title, fontsize=8.5, color=INK)
    ax.legend(fontsize=8, frameon=False,
              title=f"sum: {o.sum():,.6g} (old)  {n.sum():,.6g} (new)", title_fontsize=8)
    ax.grid(axis="y", color="#e6e6e3", lw=0.6)
    ax.tick_params(colors=INK2)
    c = 0.5 * (e[:-1] + e[1:])
    m = o != 0
    ratio = np.divide(n, o, out=np.full_like(n, np.nan), where=m)
    rx.axhline(1.0, color="#9a9994", lw=0.8)
    if expect != 1.0:
        rx.axhline(expect, color=NEW_COLOR, lw=1, ls=":",
                   label=f"expected {expect:.6f}")
        rx.legend(fontsize=7, frameon=False, loc="lower right")
    rx.plot(c[m], ratio[m], "o", ms=3, color=INK)
    rx.set_ylim(0.985, 1.005)
    rx.set_ylabel("new / old", color=INK)
    rx.set_xlabel("mass [GeV]", color=INK)
    rx.grid(axis="y", color="#e6e6e3", lw=0.6)
    rx.tick_params(colors=INK2)
    fig.savefig(path, dpi=130, bbox_inches="tight", facecolor="#fcfcfb")
    plt.close(fig)
    rr = ratio[m]
    return {"png": path.name, "histogram": title, "n_nonzero_bins": int(m.sum()),
            "expected_ratio": expect,
            "ratio_min": float(np.min(rr)) if rr.size else None,
            "ratio_max": float(np.max(rr)) if rr.size else None,
            "max_abs_ratio_minus_expected": float(np.max(np.abs(rr - expect))) if rr.size else None}


def top(h: dict, k: int) -> list:
    return sorted(h, key=lambda x: -float(np.abs(h[x]["values"]).sum()))[:k]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    old_dir, new_dir, out = Path(args.old), Path(args.new), Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    hist = {}
    result = {"what": "pilot re-build (17 Oct, reviewed registry) vs 10 Oct build 3a",
              "r_ggH": R_GGH, "sigma_ggH_old_pb": SIGMA_GGH_OLD,
              "sigma_ggH_new_pb": SIGMA_GGH_NEW, "samples": {}}
    for rid, (fname, factor, _lab) in FILES.items():
        hist[rid] = (read_root(old_dir / fname), read_root(new_dir / fname))
        result["samples"][rid] = compare_sample(*hist[rid], factor)
        print(rid, json.dumps({k: v for k, v in result["samples"][rid].items()
                               if k != "structure_differences"}, default=str))
    so, sn = read_root(old_dir / SUMMED), read_root(new_dir / SUMMED)
    result["summed"] = compare_summed(so, sn, *hist["37728"])
    print("summed", json.dumps({k: v for k, v in result["summed"].items()
                                if k != "structure_differences"}, default=str))

    s = result["samples"]
    unexpected = []
    for rid in ("67801", "35669"):
        if not s[rid]["all_bitwise_identical"] or s[rid]["structure_differences"]:
            unexpected.append(f"{rid} is not bitwise identical")
    if s["37728"]["structure_differences"] or s["37728"]["bins_zero_in_expectation_but_nonzero_new"]:
        unexpected.append("37728 structure differs")
    if s["37728"]["max_rel_deviation_values_from_expectation"] > 1e-12:
        unexpected.append("37728 not scaled by r to 1e-12")
    if result["summed"]["structure_differences"] or result["summed"]["n_histograms_without_ggh_that_CHANGED"]:
        unexpected.append("summed differs beyond the ggH change")
    if result["summed"]["same_relative_to_the_old_summed_bin"] > 1e-12:
        unexpected.append("summed: (new-old) != ggH change to 1e-12 of the bin")
    result["unexpected_differences"] = unexpected
    result["verdict"] = "AS EXPECTED" if not unexpected else "UNEXPECTED DIFFERENCES"

    plots = []
    og, ng = hist["37728"]
    for i, k in enumerate(top(og, 2), 1):
        plots.append(overlay(og[k], ng[k], R_GGH, f"ggH 37728 (weighted): {k}",
                             out / f"B3_ggH_{i}.png"))
    for rid, tag in (("67801", "ttbar"), ("35669", "DY")):
        o, n = hist[rid]
        k = top(o, 1)[0]
        plots.append(overlay(o[k], n[k], 1.0, f"{FILES[rid][2]} (weighted): {k}",
                             out / f"B3_{tag}.png"))
    k = top(so, 1)[0]
    plots.append(overlay(so[k], sn[k], 1.0, f"summed SM (weighted): {k}", out / "B3_summedSM.png"))
    result["plots"] = plots
    (out / "pilot_rebuild_comparison.json").write_text(json.dumps(result, indent=2, default=str))
    print("VERDICT:", result["verdict"], unexpected)
    print(json.dumps(plots, indent=2))
    return 0 if not unexpected else 1


if __name__ == "__main__":
    raise SystemExit(main())
