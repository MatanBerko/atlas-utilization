#!/usr/bin/env python
"""
Diagnosis round -- D4: redo the phase-1 V3 data-vs-MC comparisons with the
full background stack measured this round, for the 3 phase-1 histogram
names, under two stacks:
  (a) DY madgraphMLM (35671) + everything else
  (b) DY amcatnloFXFX (35669) REPLACING madgraphMLM, same everything else
"everything else" = TTTo2L2Nu(67801), ST_tW_top(64895), ST_tW_antitop(64839),
WW(72676), WZ(72752, k=1 flagged), ZZ4L(75589), TTZ(68187), TTW(68073).
TTToSemiLeptonic excluded per D4's own >250-file rule (see
d4_file_counts.json).

Reads the delivered data ROOT file and each sample's own phase-1/D4
_mc.root file (all read-only). Reports, per histogram: each process's
own fractional contribution to the stack, overall data/stack ratio, and
a stacked plot with a ratio panel.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DATA_ROOT = "/storage/agrp/berkom/atlas-utilization/output/deliver_doublemuon_bumpnet/doublemuon_bumpnet_min26bins_cropped.root"
PLOTS_DIR = REPO_ROOT / "studies/cms_mc_weights/phase1/plots/diagnosis"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

PHASE1_DIR = REPO_ROOT / "studies/cms_mc_weights/phase1"

COMMON_SAMPLES = {
    "TTTo2L2Nu (67801)": "67801",
    "ST_tW_top (64895)": "64895",
    "ST_tW_antitop (64839)": "64839",
    "WWTo2L2Nu (72676)": "72676",
    "WZTo3LNu_amcatnloFXFX (72752, k=1 flagged)": "72752",
    "ZZTo4L (75589)": "75589",
    "TTZToLLNuNu_M-10 (68187)": "68187",
    "TTWJetsToLNu (68073)": "68073",
}

STACK_A = {"DYJetsToLL_M-50_madgraphMLM (35671)": "35671", **COMMON_SAMPLES}
STACK_B = {"DYJetsToLL_M-50_amcatnloFXFX (35669) [ALT DY]": "35669", **COMMON_SAMPLES}

TARGETS = [
    ("mass_m0m1_cat_0ex_2mx_1jx_0gx_0tx_0bx", "V3a_dimuon_1jet_0b"),
    ("mass_m0m1b0_cat_0ex_2mx_1jx_0gx_0tx_1bx", "V3b_m0m1b0_1jet_1b"),
    ("mass_m0m1b0_cat_0ex_2mx_2jx_0gx_0tx_1bx", "V3b_m0m1b0_2jet_1b"),
]


def read_hist(root_path: str, key_no_suffix: str):
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
    return (np.asarray(values, dtype=np.float64), np.asarray(edges, dtype=np.float64),
            np.asarray(variances, dtype=np.float64) if variances is not None else None)


def build_common_grid(*edge_arrays):
    bin_width = edge_arrays[0][1] - edge_arrays[0][0]
    lo = min(e[0] for e in edge_arrays)
    hi = max(e[-1] for e in edge_arrays)
    n = int(round((hi - lo) / bin_width))
    return np.linspace(lo, hi, n + 1)


def rebin_to_common_edges(values, edges, sumw2, common_edges):
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


def sample_root_path(recid: str) -> str:
    return str(PHASE1_DIR / recid / f"{recid}_mc.root")


def sum_stack(stack: dict, key_no_suffix: str, common_edges):
    total_values = np.zeros(len(common_edges) - 1, dtype=np.float64)
    total_sumw2 = np.zeros(len(common_edges) - 1, dtype=np.float64)
    contributions = {}
    missing = []
    for label, recid in stack.items():
        path = sample_root_path(recid)
        h = read_hist(path, key_no_suffix)
        if h is None:
            contributions[label] = 0.0
            missing.append(label)
            continue
        values, edges, sumw2 = h
        v_re, s_re = rebin_to_common_edges(values, edges, sumw2, common_edges)
        total_values += v_re
        if s_re is not None:
            total_sumw2 += s_re
        contributions[label] = float(v_re.sum())
    return total_values, total_sumw2, contributions, missing


def make_plot(name, data_values, data_edges, mc_values, mc_sumw2, out_path, mc_label):
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
    ax1.legend(fontsize=7)
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


def main():
    results = {"stack_a_madgraphMLM_DY": {}, "stack_b_amcatnloFXFX_DY": {}}

    for stack_key, stack, tag in [
        ("stack_a_madgraphMLM_DY", STACK_A, "stackA_madgraphMLM"),
        ("stack_b_amcatnloFXFX_DY", STACK_B, "stackB_amcatnloFXFX"),
    ]:
        for hist_key, short_tag in TARGETS:
            data_h = read_hist(DATA_ROOT, hist_key)
            if data_h is None:
                results[stack_key][hist_key] = {"error": "not found in delivered data ROOT file"}
                continue
            data_values, data_edges, data_sumw2 = data_h

            edge_candidates = [data_edges]
            for recid in stack.values():
                h = read_hist(sample_root_path(recid), hist_key)
                if h is not None:
                    edge_candidates.append(h[1])
            common_edges = build_common_grid(*edge_candidates)

            data_re, _ = rebin_to_common_edges(data_values, data_edges, data_sumw2, common_edges)
            stack_values, stack_sumw2, contributions, missing = sum_stack(stack, hist_key, common_edges)

            overall_data = float(data_re.sum())
            overall_mc = float(stack_values.sum())
            fractions = {
                label: (v / overall_mc if overall_mc > 0 else None)
                for label, v in contributions.items()
            }

            out_png = PLOTS_DIR / f"d4_v3_{tag}_{short_tag}.png"
            make_plot(hist_key, data_re, common_edges, stack_values, stack_sumw2, out_png,
                      mc_label=f"Full stack ({len(stack)} processes)")

            results[stack_key][hist_key] = {
                "plot": str(out_png),
                "per_process_contribution_sum": contributions,
                "per_process_fraction_of_stack": fractions,
                "processes_missing_this_histogram": missing,
                "overall_data": overall_data,
                "overall_mc_stack": overall_mc,
                "overall_data_over_mc": (overall_data / overall_mc) if overall_mc > 0 else None,
            }
            print(f"[{stack_key}] {hist_key}: data={overall_data:.1f} mc_stack={overall_mc:.1f} "
                  f"ratio={results[stack_key][hist_key]['overall_data_over_mc']}")

    out_json = REPO_ROOT / "studies/cms_mc_weights/phase1/diagnosis/d4_v3_stack_result.json"
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {out_json}")


if __name__ == "__main__":
    main()
