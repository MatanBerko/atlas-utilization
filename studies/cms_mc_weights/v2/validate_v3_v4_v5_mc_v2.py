#!/usr/bin/env python
"""
CMS MC weights task v2 -- V3 (Z-peak check in the new population), V4
(per-histogram data/MC table + 4 representative plots, nominal vs
alternative DY), V5 (leptoquark overlay on the best 2mu+2b+0jet match).

Data: read directly from the already-committed, read-only
muon_combined_matched_nonjet4_bumpnet_min26bins.root (UNCROPPED -- so a
60-120 GeV lookup is always valid regardless of any individual
histogram's own cropped window) and the delivered manifest (per-
histogram n_events/window). Data is never reprocessed here.

MC: reuses build_mc_muon_combined_delivery's own pooling (DoubleMuon
inclusive + SingleMuon exclusive), bad-file policy, and per-sample
normalisation -- imported, not reimplemented -- for every sample in each
stack.

Nominal stack: TTTo2L2Nu(67801) + DY amcatnloFXFX(35669, nominal) +
ST_tW top(64895) + ST_tW antitop(64839) + WW(72676) + WZ(72752, k=1
flagged) + ZZ4L(75589) + TTZ(68187) + TTW(68073).
Alternative stack: identical, DY madgraphMLM(35671) replacing 35669.
LQToBMu (42407) is in NEITHER stack -- signal only, used in V5 alone.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import uproot  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from build_mc_muon_combined_delivery import (  # noqa: E402
    load_job, load_shard_pooled, merge_pooled, BAD_FILE_REL_TOL,
)
from studies.m0m1j0_cms.histograms import make_fixed_grid_histogram, BIN_WIDTH_GEV  # noqa: E402

WORK_BASE = "/storage/agrp/berkom/atlas-utilization/work/cms_mc_v2"
MANIFEST_PATH = REPO_ROOT / "studies/cms_datasets/deliver/committed/muon_combined_nonjet4/manifest_muon_combined_matched_nonjet4_min26bins.json"
DATA_ROOT_UNCROPPED = REPO_ROOT / "studies/cms_datasets/deliver/committed/muon_combined_nonjet4/muon_combined_matched_nonjet4_bumpnet_min26bins.root"
PLOTS_DIR = REPO_ROOT / "studies/cms_mc_weights/v2/plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

LUMI_FB = 16.393
Z_LO, Z_HI = 60.0, 120.0

NOMINAL_DY = "35669"
ALT_DY = "35671"
COMMON_SAMPLES = ["67801", "64895", "64839", "72676", "72752", "75589", "68187", "68073"]
STACK_NOMINAL = [NOMINAL_DY] + COMMON_SAMPLES
STACK_ALT = [ALT_DY] + COMMON_SAMPLES
LQ_SAMPLE = "42407"

N_FILES = {
    "42407": 12, "67801": 49, "35669": 41, "35671": 61,
    "64895": 11, "64839": 10, "72676": 7, "72752": 31,
    "75589": 99, "68187": 42, "68073": 12,
}

NM_RE = re.compile(r"_(\d+)mx_")
NJ_RE = re.compile(r"_(\d+)jx_")
NB_RE = re.compile(r"_(\d+)bx")


def muon_count(name: str):
    m = NM_RE.search(name)
    return int(m.group(1)) if m else None


def jet_count(name: str):
    m = NJ_RE.search(name)
    return int(m.group(1)) if m else None


def bjet_count(name: str):
    m = NB_RE.search(name)
    return int(m.group(1)) if m else None


def load_manifest():
    entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {e["name"]: e for e in entries}


def read_data_hist(name: str):
    f = uproot.open(str(DATA_ROOT_UNCROPPED))
    key = f"ROI_{name}_width_{int(BIN_WIDTH_GEV)}"
    h = f[key]
    return np.asarray(h.values(), dtype=np.float64), np.asarray(h.axis().edges(), dtype=np.float64)


def load_sample_pooled_and_norm(record_id: str, normalisation: dict):
    """Reuses build_mc_muon_combined_delivery's own bad-file policy +
    normalisation to return (pooled_dict, per_file_norm, bad_files)."""
    n_files = N_FILES[record_id]
    jobs_base = Path(WORK_BASE) / record_id
    entry = normalisation[record_id]
    sigma_eff_pb = entry["cross_section_pb"]

    good_files = []
    total_genEventSumw = 0.0
    bad_files = []
    for i in range(n_files):
        dm = load_job(jobs_base, "DoubleMuon", i)
        sm = load_job(jobs_base, "SingleMuon", i)
        if dm is None or sm is None:
            continue
        dm_sums = dm["meta"]["mc_runs_tree_sums_this_file"]
        sm_sums = sm["meta"]["mc_runs_tree_sums_this_file"]
        dm_full_gw = dm["meta"]["mc_sum_genweight_all_events_this_file"]
        sm_full_gw = sm["meta"]["mc_sum_genweight_all_events_this_file"]
        assert dm_sums["genEventSumw"] == sm_sums["genEventSumw"] and dm_full_gw == sm_full_gw
        genEventSumw_this_file = dm_sums["genEventSumw"]
        rel_diff = abs(dm_full_gw - genEventSumw_this_file) / abs(genEventSumw_this_file) if genEventSumw_this_file else float("nan")
        if rel_diff > BAD_FILE_REL_TOL:
            bad_files.append(i)
            continue
        good_files.append(i)
        total_genEventSumw += genEventSumw_this_file

    per_file_norm = sigma_eff_pb * 1000.0 * LUMI_FB / total_genEventSumw

    pooled = {}
    for i in good_files:
        dm_dir = jobs_base / "DoubleMuon" / f"job_{i}"
        sm_dir = jobs_base / "SingleMuon" / f"job_{i}"
        dm_pooled = load_shard_pooled(
            dm_dir / "dataset_shard_nonjet4_inclusive.sqlite",
            dm_dir / "dataset_shard_nonjet4_weights_inclusive.sqlite",
        )
        sm_pooled = load_shard_pooled(
            sm_dir / "dataset_shard_nonjet4_exclusive.sqlite",
            sm_dir / "dataset_shard_nonjet4_weights_exclusive.sqlite",
        )
        pooled = merge_pooled(pooled, dm_pooled)
        pooled = merge_pooled(pooled, sm_pooled)

    return pooled, per_file_norm, bad_files


def stack_weighted_mass(stack_pooled: dict, bumpnet_name: str):
    """stack_pooled: {record_id: (pooled_dict, per_file_norm)}. Returns
    (mass_concat, weight_concat) across every sample in the stack that has
    this bumpnet_name, weight = genWeight*L1*per_file_norm."""
    masses, weights = [], []
    for record_id, (pooled, per_file_norm) in stack_pooled.items():
        d = pooled.get(bumpnet_name)
        if d is None:
            continue
        w = d["weight_raw"][:, 0] * d["weight_raw"][:, 1] * per_file_norm
        masses.append(d["mass"])
        weights.append(w)
    if not masses:
        return np.array([]), np.array([])
    return np.concatenate(masses), np.concatenate(weights)


def ratio_with_stat(n_data, mc_w):
    n_mc = float(mc_w.sum())
    mc_stat = float(np.sqrt((mc_w ** 2).sum()))
    if n_mc <= 0:
        return {"n_data": int(n_data), "n_mc_weighted": n_mc, "n_mc_stat_err": mc_stat, "ratio": None, "ratio_stat_err": None}
    ratio = n_data / n_mc
    rel = (1.0 / np.sqrt(n_data) if n_data > 0 else 0.0) + (mc_stat / n_mc)
    return {"n_data": int(n_data), "n_mc_weighted": n_mc, "n_mc_stat_err": mc_stat, "ratio": ratio, "ratio_stat_err": ratio * rel}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--normalisation", default=str(REPO_ROOT / "studies/cms_mc_weights/cms_mc_normalisation.json"))
    p.add_argument("--out", required=True)
    args = p.parse_args()

    normalisation = json.loads(Path(args.normalisation).read_text(encoding="utf-8"))
    manifest = load_manifest()

    print("=== Loading MC samples (nominal + alt stack + LQ) ===", flush=True)
    all_needed = sorted(set(STACK_NOMINAL) | set(STACK_ALT) | {LQ_SAMPLE})
    sample_data = {}
    for rid in all_needed:
        pooled, per_file_norm, bad_files = load_sample_pooled_and_norm(rid, normalisation)
        sample_data[rid] = (pooled, per_file_norm)
        print(f"  {rid}: {len(pooled)} bumpnet names pooled, per_file_norm={per_file_norm}, "
              f"bad_files_excluded={bad_files}", flush=True)

    stack_nominal_data = {rid: sample_data[rid] for rid in STACK_NOMINAL}
    stack_alt_data = {rid: sample_data[rid] for rid in STACK_ALT}

    result = {}

    # === V3: inclusive raw m(mu0,mu1), 60-120 GeV, ALL jet counts ===
    print("\n=== V3: truly inclusive m0m1 Z-peak, new (nonjet4/matched) population ===", flush=True)
    m0m1_names = [n for n, e in manifest.items() if e["combination"] == "m0m1"]
    data_n_60_120 = 0
    for name in m0m1_names:
        values, edges = read_data_hist(name)
        centers = 0.5 * (edges[:-1] + edges[1:])
        mask = (centers >= Z_LO) & (centers < Z_HI)
        data_n_60_120 += float(values[mask].sum())

    v3 = {}
    for stack_name, stack_data in [("nominal_DY_amcatnloFXFX", stack_nominal_data), ("alt_DY_madgraphMLM", stack_alt_data)]:
        mc_w_total = np.array([])
        for name in m0m1_names:
            mass, weight = stack_weighted_mass(stack_data, name)
            in_window = (mass >= Z_LO) & (mass < Z_HI)
            mc_w_total = np.concatenate([mc_w_total, weight[in_window]])
        v3[stack_name] = ratio_with_stat(data_n_60_120, mc_w_total)
        print(f"  [{stack_name}] data={data_n_60_120} mc={v3[stack_name]['n_mc_weighted']:.1f} "
              f"ratio={v3[stack_name]['ratio']}", flush=True)
    result["V3_inclusive_zpeak_new_population"] = v3

    # === V4: per-histogram table, >=2 muons only ===
    print("\n=== V4: per-histogram data/MC table (>=2 muons) ===", flush=True)
    ge2mu_names = sorted(n for n in manifest if muon_count(n) is not None and muon_count(n) >= 2)
    one_mu_names = sorted(n for n in manifest if muon_count(n) == 1)

    v4_table = {}
    for name in ge2mu_names:
        entry = manifest[name]
        low, high = entry["first_filled_bin_low_edge_gev"], entry["last_filled_bin_high_edge_gev"]
        values, edges = read_data_hist(name)
        centers = 0.5 * (edges[:-1] + edges[1:])
        mask = (centers >= low) & (centers < high)
        data_n = float(values[mask].sum())

        row = {"data_n_events": data_n, "manifest_n_events": entry["n_events"]}
        for stack_name, stack_data in [("nominal", stack_nominal_data), ("alt_DY", stack_alt_data)]:
            mass, weight = stack_weighted_mass(stack_data, name)
            in_window = (mass >= low) & (mass < high)
            row[stack_name] = ratio_with_stat(data_n, weight[in_window])
        v4_table[name] = row

    result["V4_table_ge2mu"] = v4_table
    result["V4_one_muon_histograms_not_yet_modelled"] = {
        "count": len(one_mu_names), "names": one_mu_names,
        "reason": (
            "Backgrounds for a single-muon final state (W+jets, single-lepton ttbar, QCD) "
            "are not included in either MC stack -- out of scope for this round. Listed, "
            "not compared."
        ),
    }

    # === V4 representative plots ===
    print("\n=== V4: 4 representative plots ===", flush=True)
    largest_overall = max(ge2mu_names, key=lambda n: manifest[n]["n_events"])
    dimuon0j_candidates = [n for n in ge2mu_names if manifest[n]["combination"] == "m0m1" and jet_count(n) == 0]
    largest_dimuon0j = max(dimuon0j_candidates, key=lambda n: manifest[n]["n_events"])
    withb_candidates = [n for n in ge2mu_names if (bjet_count(n) or 0) >= 1]
    largest_withb = max(withb_candidates, key=lambda n: manifest[n]["n_events"])
    j3_candidates = [n for n in ge2mu_names if jet_count(n) is not None and jet_count(n) >= 3]
    if j3_candidates:
        largest_j3 = max(j3_candidates, key=lambda n: manifest[n]["n_events"])
        j3_note = None
    else:
        j2_candidates = [n for n in ge2mu_names if jet_count(n) == 2]
        largest_j3 = max(j2_candidates, key=lambda n: manifest[n]["n_events"])
        j3_note = (
            "No histogram with >=2 muons AND >=3 jets exists in this delivery -- a "
            "structural consequence of the top-4/nonjet4 object cap (N<=4 kept objects: "
            "2 muons already use 2 of 4 slots, so at most 2 more jets/b-jets can ever be "
            "kept alongside them). Substituting the largest available >=2-muon, "
            "2-jet histogram instead."
        )
        print(f"  NOTE: {j3_note}", flush=True)

    plot_targets = [
        ("largest_ge2mu", largest_overall),
        ("largest_dimuon_0jet", largest_dimuon0j),
        ("largest_ge2mu_with_bjet", largest_withb),
        ("largest_j3_or_substitute", largest_j3),
    ]
    result["V4_plot_targets"] = {tag: name for tag, name in plot_targets}
    if j3_note:
        result["V4_plot_targets_note"] = j3_note

    for tag, name in plot_targets:
        entry = manifest[name]
        low, high = entry["first_filled_bin_low_edge_gev"], entry["last_filled_bin_high_edge_gev"]
        data_values, data_edges = read_data_hist(name)
        centers_full = 0.5 * (data_edges[:-1] + data_edges[1:])
        win_mask = (centers_full >= low) & (centers_full < high)
        data_win = data_values[win_mask]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
        for stack_name, stack_data, color, style in [
            ("nominal (amcatnloFXFX DY)", stack_nominal_data, "#3b6fa0", "-"),
            ("alt (madgraphMLM DY)", stack_alt_data, "#c0392b", "--"),
        ]:
            mass, weight = stack_weighted_mass(stack_data, name)
            in_window = (mass >= low) & (mass < high)
            mc_values, mc_edges_full, mc_sumw2 = make_fixed_grid_histogram(mass[in_window], weights=weight[in_window])
            assert np.array_equal(mc_edges_full, data_edges), f"{name}: MC and data fixed-grid edges must match"
            mc_win = mc_values[win_mask]
            mc_err_win = np.sqrt(mc_sumw2[win_mask])
            centers_win = centers_full[win_mask]
            ax1.step(centers_win, mc_win, where="mid", color=color, linestyle=style, label=stack_name)
            ax1.fill_between(centers_win, mc_win - mc_err_win, mc_win + mc_err_win, step="mid", color=color, alpha=0.2)
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.where(mc_win > 0, data_win / mc_win, np.nan)
            ax2.plot(centers_win, ratio, "o", color=color, markersize=3, label=stack_name)

        ax1.errorbar(centers_full[win_mask], data_win, yerr=np.sqrt(np.maximum(data_win, 0)),
                     fmt="ko", markersize=3, label="Data (DoubleMuon-incl + SingleMuon-excl)")
        ax1.set_ylabel("Events"); ax1.set_yscale("log")
        ax1.set_title(name, fontsize=9)
        ax1.legend(fontsize=7)
        ax2.axhline(1.0, color="gray", linewidth=1)
        ax2.set_ylim(0, 2); ax2.set_ylabel("Data/MC"); ax2.set_xlabel("mass [GeV]")
        fig.tight_layout()
        out_png = PLOTS_DIR / f"v4_{tag}.png"
        fig.savefig(out_png, dpi=130)
        plt.close(fig)
        print(f"  wrote {out_png}", flush=True)

    # === V5: leptoquark overlay ===
    print("\n=== V5: leptoquark overlay ===", flush=True)
    v5_candidates = [n for n in manifest if n.startswith("mass_m0m1b0b1_cat_") and jet_count(n) == 0 and (bjet_count(n) or 0) == 2]
    assert len(v5_candidates) == 1, f"expected exactly one 2mu+2b+0jet m0m1b0b1 histogram, found {v5_candidates}"
    v5_name = v5_candidates[0]
    entry = manifest[v5_name]
    low, high = entry["first_filled_bin_low_edge_gev"], entry["last_filled_bin_high_edge_gev"]
    data_values, data_edges = read_data_hist(v5_name)
    centers_full = 0.5 * (data_edges[:-1] + data_edges[1:])
    win_mask = (centers_full >= low) & (centers_full < high)
    data_win = data_values[win_mask]

    lq_pooled, lq_norm = sample_data[LQ_SAMPLE]
    d = lq_pooled.get(v5_name)
    if d is not None:
        lq_weight = d["weight_raw"][:, 0] * d["weight_raw"][:, 1] * lq_norm
        lq_mass = d["mass"]
        in_window = (lq_mass >= low) & (lq_mass < high)
        lq_values, _, lq_sumw2 = make_fixed_grid_histogram(lq_mass[in_window], weights=lq_weight[in_window])
        lq_win = lq_values[win_mask]
    else:
        lq_win = np.zeros_like(data_win)

    fig, ax = plt.subplots(figsize=(8, 5))
    centers_win = centers_full[win_mask]
    widths_win = np.diff(data_edges)[win_mask]
    ax.bar(centers_win, data_win, width=widths_win, color="black", alpha=0.15, label="Data (DoubleMuon-incl + SingleMuon-excl)")
    ax.errorbar(centers_win, data_win, yerr=np.sqrt(np.maximum(data_win, 0)), fmt="ko", markersize=3)
    ax.bar(centers_win, lq_win, width=widths_win, color="#c0392b", alpha=0.5, label="LQToBMu_M-400_pair (weighted)")
    ax.set_yscale("log"); ax.set_xlabel("mass [GeV]"); ax.set_ylabel("Events")
    ax.set_title(v5_name, fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    out_png = PLOTS_DIR / "v5_leptoquark_overlay.png"
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    print(f"  wrote {out_png}", flush=True)

    result["V5"] = {
        "name": v5_name,
        "chosen_reason": "2 muons + 2 b-jets + 0 light jets (m0m1b0b1 combination) -- best match to the LQ pair's own b+mu, b+mu topology; the only such histogram in the delivery.",
        "data_total": float(data_win.sum()),
        "lq_total_weighted": float(lq_win.sum()),
        "plot": str(out_png),
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
