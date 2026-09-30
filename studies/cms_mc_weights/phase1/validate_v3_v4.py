#!/usr/bin/env python
"""
Phase-1 MC weights task -- V3 (data vs MC) and V4 (leptoquark overlay).

Reads the delivered DoubleMuon histogram directly from the committed
delivery ROOT file (read-only, never modified) and the phase-1 MC ROOT
files (also read-only, produced by merge_full_v2_mc.py), for exactly
4 histogram names:

  V3(a) mass_m0m1_cat_0ex_2mx_1jx_0gx_0tx_0bx
        (2 muons, exactly 1 light jet, 0 b-jets, 0 electrons -- the
        lowest-jet-multiplicity, zero-b-tag m0m1 bin: the closest this
        baseline (>=1 light jet mandatory) gets to a clean dimuon
        selection, and the single largest-event-count m0m1 bin in the
        delivered manifest -- 28,496 data events)
  V3(b) mass_m0m1b0_cat_0ex_2mx_1jx_0gx_0tx_1bx,
        mass_m0m1b0_cat_0ex_2mx_2jx_0gx_0tx_1bx (given explicitly by the task)
  V4    mass_m0m1b0b1_cat_0ex_2mx_1jx_0gx_0tx_2bx (2 muons + 1 light jet +
        2 b-jets -- the best available match to the leptoquark pair's own
        b+mu, b+mu topology: both muons AND both b-jets in one mass,
        largest-event-count 2b-jet bin for this combination, 5,623 data
        events)

Produces one stacked (data vs MC, ratio panel, MC stat error band from
sumw2) PNG per histogram under studies/cms_mc_weights/phase1/plots/, plus
a JSON with every number quoted in the task (data/MC ratio overall and in
mass sub-ranges).

No interpretation. No tuning.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402
import matplotlib
matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

DATA_ROOT = "/storage/agrp/berkom/atlas-utilization/output/deliver_doublemuon_bumpnet/doublemuon_bumpnet_min26bins_cropped.root"

PLOTS_DIR = REPO_ROOT / "studies" / "cms_mc_weights" / "phase1" / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def read_hist(root_path: str, key_no_suffix: str):
    """Returns (values, edges, sumw2_or_None) for ROI_<name>_width_10, or
    None if the key doesn't exist in this file."""
    f = uproot.open(root_path)
    key = f"ROI_{key_no_suffix}_width_10"
    matches = [k for k in f.keys(cycle=False) if k == key]
    if not matches:
        return None
    h = f[key]
    values = h.values()
    edges = h.axis().edges()
    try:
        variances = h.variances()
    except Exception:  # noqa: BLE001
        variances = None
    return np.asarray(values, dtype=np.float64), np.asarray(edges, dtype=np.float64), (
        np.asarray(variances, dtype=np.float64) if variances is not None else None
    )


def rebin_to_common_edges(values, edges, sumw2, common_edges):
    """If `edges` is a superset-aligned or identical grid to
    `common_edges` (same bin width, integer multiple offset), returns
    values/sumw2 reindexed onto common_edges (zero-padded where a bin
    doesn't exist in the source). Assumes both grids share the same 10 GeV
    bin width and are aligned to the same absolute grid (both crops of the
    SAME underlying 0-10000 GeV / 10 GeV fixed grid -- true by
    construction for both the data delivery and this MC merge)."""
    bin_width = common_edges[1] - common_edges[0]
    n_common = len(common_edges) - 1
    out_values = np.zeros(n_common, dtype=np.float64)
    out_sumw2 = np.zeros(n_common, dtype=np.float64) if sumw2 is not None else None

    start_idx = int(round((edges[0] - common_edges[0]) / bin_width))
    for i, v in enumerate(values):
        j = start_idx + i
        if 0 <= j < n_common:
            out_values[j] = v
            if sumw2 is not None:
                out_sumw2[j] = sumw2[i]
    return out_values, out_sumw2


def build_common_grid(*edge_arrays):
    bin_width = edge_arrays[0][1] - edge_arrays[0][0]
    lo = min(e[0] for e in edge_arrays)
    hi = max(e[-1] for e in edge_arrays)
    n = int(round((hi - lo) / bin_width))
    return np.linspace(lo, hi, n + 1)


def sum_mc(mc_root_paths, key_no_suffix, common_edges):
    total_values = np.zeros(len(common_edges) - 1, dtype=np.float64)
    total_sumw2 = np.zeros(len(common_edges) - 1, dtype=np.float64)
    contributions = {}
    for label, path in mc_root_paths.items():
        h = read_hist(path, key_no_suffix)
        if h is None:
            contributions[label] = None
            continue
        values, edges, sumw2 = h
        v_re, s_re = rebin_to_common_edges(values, edges, sumw2, common_edges)
        total_values += v_re
        if s_re is not None:
            total_sumw2 += s_re
        contributions[label] = float(v_re.sum())
    return total_values, total_sumw2, contributions


def make_plot(name, data_values, data_edges, mc_values, mc_sumw2, out_path, mc_label="MC"):
    centers = 0.5 * (data_edges[:-1] + data_edges[1:])
    widths = np.diff(data_edges)
    mc_err = np.sqrt(mc_sumw2)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1]})
    ax1.bar(centers, mc_values, width=widths, color="#3b6fa0", alpha=0.6, label=mc_label)
    ax1.fill_between(centers, mc_values - mc_err, mc_values + mc_err, step="mid",
                      color="#3b6fa0", alpha=0.3, label="MC stat. unc. (sumw2)")
    ax1.errorbar(centers, data_values, yerr=np.sqrt(np.maximum(data_values, 0)),
                 fmt="ko", markersize=3, label="DoubleMuon data")
    ax1.set_ylabel("Events")
    ax1.set_title(name, fontsize=9)
    ax1.legend(fontsize=8)
    ax1.set_yscale("log")

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(mc_values > 0, data_values / mc_values, np.nan)
    ax2.axhline(1.0, color="gray", linewidth=1)
    ax2.plot(centers, ratio, "ko", markersize=3)
    ax2.set_ylim(0, 2)
    ax2.set_ylabel("Data / MC")
    ax2.set_xlabel("mass [GeV]")

    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def ratio_in_range(data_values, mc_values, edges, lo, hi):
    centers = 0.5 * (edges[:-1] + edges[1:])
    mask = (centers >= lo) & (centers < hi)
    d = data_values[mask].sum()
    m = mc_values[mask].sum()
    return {"range_gev": [lo, hi], "data": float(d), "mc": float(m),
            "ratio": float(d / m) if m > 0 else None}


def main():
    mc_paths = {
        "DYJetsToLL_M-50_madgraphMLM (35671)": str(REPO_ROOT / "studies/cms_mc_weights/phase1/35671/35671_mc.root"),
        "TTTo2L2Nu (67801)": str(REPO_ROOT / "studies/cms_mc_weights/phase1/67801/67801_mc.root"),
    }
    lq_path = str(REPO_ROOT / "studies/cms_mc_weights/phase1/42407/42407_mc.root")

    targets = [
        ("mass_m0m1_cat_0ex_2mx_1jx_0gx_0tx_0bx", "V3a_dimuon_1jet_0b"),
        ("mass_m0m1b0_cat_0ex_2mx_1jx_0gx_0tx_1bx", "V3b_m0m1b0_1jet_1b"),
        ("mass_m0m1b0_cat_0ex_2mx_2jx_0gx_0tx_1bx", "V3b_m0m1b0_2jet_1b"),
    ]

    results = {}
    for key, tag in targets:
        data_h = read_hist(DATA_ROOT, key)
        if data_h is None:
            results[key] = {"error": "not found in delivered data ROOT file"}
            continue
        data_values, data_edges, data_sumw2 = data_h

        mc_edge_candidates = [data_edges]
        per_sample_hists = {}
        for label, path in mc_paths.items():
            h = read_hist(path, key)
            per_sample_hists[label] = h
            if h is not None:
                mc_edge_candidates.append(h[1])
        common_edges = build_common_grid(*mc_edge_candidates)

        data_re, data_sumw2_re = rebin_to_common_edges(data_values, data_edges, data_sumw2, common_edges)
        mc_total, mc_sumw2, contributions = sum_mc(mc_paths, key, common_edges)

        out_png = PLOTS_DIR / f"genweight_v3_{tag}.png"
        make_plot(key, data_re, common_edges, mc_total, mc_sumw2, out_png, mc_label="DY+TTTo2L2Nu (weighted MC)")

        overall_data = float(data_re.sum())
        overall_mc = float(mc_total.sum())
        centers = 0.5 * (common_edges[:-1] + common_edges[1:])
        sub_ranges = []
        lo = common_edges[0]
        span = common_edges[-1] - common_edges[0]
        step = span / 3.0
        for i in range(3):
            sub_ranges.append(ratio_in_range(data_re, mc_total, common_edges, lo + i * step, lo + (i + 1) * step))

        results[key] = {
            "plot": str(out_png),
            "per_sample_mc_contribution_sum": contributions,
            "overall_data": overall_data,
            "overall_mc": overall_mc,
            "overall_data_over_mc": (overall_data / overall_mc) if overall_mc > 0 else None,
            "sub_range_ratios": sub_ranges,
        }
        print(f"{key}: data={overall_data:.1f} mc={overall_mc:.1f} "
              f"ratio={results[key]['overall_data_over_mc']}")

    # V4: leptoquark overlay
    v4_key = "mass_m0m1b0b1_cat_0ex_2mx_1jx_0gx_0tx_2bx"
    data_h = read_hist(DATA_ROOT, v4_key)
    lq_h = read_hist(lq_path, v4_key)
    if data_h is not None and lq_h is not None:
        data_values, data_edges, data_sumw2 = data_h
        lq_values, lq_edges, lq_sumw2 = lq_h
        common_edges = build_common_grid(data_edges, lq_edges)
        data_re, _ = rebin_to_common_edges(data_values, data_edges, data_sumw2, common_edges)
        lq_re, lq_sumw2_re = rebin_to_common_edges(lq_values, lq_edges, lq_sumw2, common_edges)

        centers = 0.5 * (common_edges[:-1] + common_edges[1:])
        widths = np.diff(common_edges)
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(centers, data_re, width=widths, color="black", alpha=0.15, label="DoubleMuon data")
        ax.errorbar(centers, data_re, yerr=np.sqrt(np.maximum(data_re, 0)), fmt="ko", markersize=3)
        ax.bar(centers, lq_re, width=widths, color="#c0392b", alpha=0.5,
               label="LQToBMu_M-400_pair (stop-pair proxy sigma_eff, flagged)")
        ax.set_yscale("log")
        ax.set_xlabel("mass [GeV]")
        ax.set_ylabel("Events")
        ax.set_title(v4_key, fontsize=9)
        ax.legend(fontsize=8)
        fig.tight_layout()
        out_png = PLOTS_DIR / "genweight_v4_leptoquark_overlay.png"
        fig.savefig(out_png, dpi=130)
        plt.close(fig)

        results[v4_key] = {
            "plot": str(out_png),
            "data_total": float(data_re.sum()),
            "lq_total_weighted": float(lq_re.sum()),
            "chosen_reason": (
                "2 muons + 1 light jet + 2 b-jets: best available match to "
                "the leptoquark pair's own b+mu, b+mu topology (both muons "
                "AND both b-jets used in one mass), and the largest-event-"
                "count 2-b-jet bin for the m0m1b0b1 combination in the "
                "delivered manifest (5,623 data events)."
            ),
        }
    else:
        results[v4_key] = {"error": f"missing (data found={data_h is not None}, LQ found={lq_h is not None})"}

    out_json = REPO_ROOT / "studies/cms_mc_weights/phase1/validate_v3_v4_result.json"
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {out_json}")


if __name__ == "__main__":
    main()
