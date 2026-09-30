#!/usr/bin/env python
"""
Diagnosis round 2 -- E2 analysis: reads every zpeak_reader.py per-job
output (diagnosis_zpeak/{record}/job_*/) and builds the truly-inclusive
(0-jet events included) Z-peak comparison, for both DY generators.

MC weight per event: genWeight * L1PreFiringWeight_Nom * sigma_eff[pb] *
1000 * 16.393 / Sigma_genWeight, sigma_eff read from
studies/cms_mc_weights/cms_mc_normalisation.json (never recomputed),
Sigma_genWeight from aggregate_sumw_for_processed_files (fork master's
existing, unmodified function) via an INJECTED reader returning each
job's own already-read runs_tree_sums_this_file from job_metadata.json --
no fresh ROOT reads, same pattern as merge_full_v2_mc.py / A5.

No selection, weighting formula, or shared code is touched. This script
only reads existing diagnosis_zpeak outputs and combines them.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from services.parsing.mc_weights import aggregate_sumw_for_processed_files  # noqa: E402

ZPEAK_BASE = "/storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1/diagnosis_zpeak"
NORM_JSON = REPO_ROOT / "studies/cms_mc_weights/cms_mc_normalisation.json"
PLOTS_DIR = REPO_ROOT / "studies/cms_mc_weights/phase1/plots/diagnosis2"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

DATA_RECORDS = ["30522", "30555"]
LUMI_FB = 16.393

Z_LO, Z_HI = 60.0, 120.0
NARROW_LO, NARROW_HI = 76.0, 106.0

STACKS = {
    "LO_madgraphMLM": ["35671", "67801"],
    "NLO_amcatnloFXFX": ["35669", "67801"],
}


def load_record_jobs(record_id: str, is_mc: bool):
    """Returns list of per-job dicts: {npz, meta}."""
    job_dirs = sorted(
        glob.glob(f"{ZPEAK_BASE}/{record_id}/job_*/"),
        key=lambda p: int(p.rstrip("/").rsplit("_", 1)[1]),
    )
    jobs = []
    for jd in job_dirs:
        npz_path = Path(jd, "zpeak_data.npz")
        meta_path = Path(jd, "job_metadata.json")
        if not npz_path.is_file() or not meta_path.is_file():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        jobs.append({"npz_path": npz_path, "meta": meta})
    return jobs


def load_data_arrays():
    """Concatenate every field across both data records, unweighted."""
    fields = {"mass": [], "is_os": [], "n_jets_pt30": [], "n_jets_pt50": [],
              "n_bjets": [], "leading_jet_pt": [], "pv_npvsgood": []}
    n_jobs = 0
    for rid in DATA_RECORDS:
        jobs = load_record_jobs(rid, is_mc=False)
        n_jobs += len(jobs)
        for job in jobs:
            with np.load(job["npz_path"]) as npz:
                for k in fields:
                    fields[k].append(npz[k])
    out = {k: (np.concatenate(v) if v else np.array([])) for k, v in fields.items()}
    return out, n_jobs


def load_mc_stack_arrays(record_ids: list[str]):
    """For each record in the stack: load per-job arrays, compute that
    sample's own per-event weight (genWeight*L1*norm), concatenate across
    all jobs of all records in the stack. Returns arrays dict + per-sample
    info (sigma_eff, sum_genweight, n_files)."""
    normalisation = json.loads(NORM_JSON.read_text(encoding="utf-8"))

    fields = {"mass": [], "weight": [], "is_os": [], "n_jets_pt30": [], "n_jets_pt50": [],
              "n_bjets": [], "leading_jet_pt": [], "pv_npvsgood": [], "pileup_ntrueint": []}
    per_sample_info = {}

    for rid in record_ids:
        jobs = load_record_jobs(rid, is_mc=True)
        if not jobs:
            raise RuntimeError(f"no jobs found for MC record {rid} under {ZPEAK_BASE}")

        job_dirs_by_url = {}
        for job in jobs:
            job_dirs_by_url[job["meta"]["file_url"]] = job
        processed_urls = list(job_dirs_by_url.keys())

        def reader(file_url, _job_dirs_by_url=job_dirs_by_url):
            return _job_dirs_by_url[file_url]["meta"]["runs_tree_sums_this_file"]

        agg = aggregate_sumw_for_processed_files(processed_urls, reader=reader)
        sum_gen_weight = agg["genEventSumw"]

        entry = normalisation[rid]
        sigma_eff = entry["cross_section_pb"]
        per_file_norm = sigma_eff * 1000.0 * LUMI_FB / sum_gen_weight

        per_sample_info[rid] = {
            "physics_short": entry.get("physics_short"),
            "sigma_eff_pb": sigma_eff,
            "n_files_processed": len(jobs),
            "sum_genEventSumw": sum_gen_weight,
            "per_file_normalization_factor": per_file_norm,
        }

        for job in jobs:
            with np.load(job["npz_path"]) as npz:
                gw = npz["gen_weight"]
                l1 = npz["l1_prefiring"]
                w = gw * l1 * per_file_norm
                fields["weight"].append(w)
                for k in ("mass", "is_os", "n_jets_pt30", "n_jets_pt50", "n_bjets",
                          "leading_jet_pt", "pv_npvsgood", "pileup_ntrueint"):
                    fields[k].append(npz[k])

    out = {k: (np.concatenate(v) if v else np.array([])) for k, v in fields.items()}
    return out, per_sample_info


def ratio_with_stat(n_data, mc_w):
    n_mc = float(mc_w.sum())
    mc_stat = float(np.sqrt((mc_w ** 2).sum()))
    if n_mc <= 0:
        return {"n_data": int(n_data), "n_mc_weighted": n_mc, "n_mc_stat_err": mc_stat,
                "ratio": None, "ratio_stat_err": None}
    ratio = n_data / n_mc
    rel = (1.0 / np.sqrt(n_data) if n_data > 0 else 0.0) + (mc_stat / n_mc)
    return {"n_data": int(n_data), "n_mc_weighted": n_mc, "n_mc_stat_err": mc_stat,
            "ratio": ratio, "ratio_stat_err": ratio * rel}


def mass_window_mask(mass, lo, hi):
    return (mass >= lo) & (mass < hi)


def main():
    data, n_data_jobs = load_data_arrays()
    print(f"data: {n_data_jobs} jobs, {len(data['mass'])} events in [50,150] GeV window")

    result = {"generators": {}}

    for stack_name, record_ids in STACKS.items():
        print(f"=== {stack_name} ({record_ids}) ===")
        mc, per_sample_info = load_mc_stack_arrays(record_ids)
        gen_result = {"per_sample": per_sample_info}

        # (a) truly inclusive (all jet counts, including 0)
        incl = {}
        for lo, hi, tag in [(Z_LO, Z_HI, "60_120"), (NARROW_LO, NARROW_HI, "76_106")]:
            dmask = mass_window_mask(data["mass"], lo, hi)
            mmask = mass_window_mask(mc["mass"], lo, hi)
            incl[tag] = ratio_with_stat(dmask.sum(), mc["weight"][mmask])
        gen_result["inclusive_all_jets"] = incl
        print("  (a) truly inclusive:", json.dumps(incl, indent=2))

        # (b) vs jet count, at pT>30 and pT>50
        jet_cat = {
            "0": lambda n: n == 0, "1": lambda n: n == 1, "2": lambda n: n == 2,
            "ge3": lambda n: n >= 3,
        }
        vs_jetcount = {}
        for thresh_key in ("n_jets_pt30", "n_jets_pt50"):
            vs_jetcount[thresh_key] = {}
            for cat_name, pred in jet_cat.items():
                dmask = mass_window_mask(data["mass"], Z_LO, Z_HI) & pred(data[thresh_key])
                mmask = mass_window_mask(mc["mass"], Z_LO, Z_HI) & pred(mc[thresh_key])
                vs_jetcount[thresh_key][cat_name] = ratio_with_stat(dmask.sum(), mc["weight"][mmask])
        gen_result["vs_jet_count"] = vs_jetcount
        print("  (b) vs jet count:", json.dumps(vs_jetcount, indent=2))

        # (c) vs jet count (pT>30) in 3 pileup slices + PV_npvsGood shapes
        pu_slices = {"le15": lambda pv: pv <= 15, "16_25": lambda pv: (pv >= 16) & (pv <= 25),
                     "gt25": lambda pv: pv > 25}
        vs_pileup = {}
        for slice_name, pu_pred in pu_slices.items():
            vs_pileup[slice_name] = {}
            for cat_name, pred in jet_cat.items():
                dmask = (mass_window_mask(data["mass"], Z_LO, Z_HI) & pred(data["n_jets_pt30"])
                         & pu_pred(data["pv_npvsgood"]))
                mmask = (mass_window_mask(mc["mass"], Z_LO, Z_HI) & pred(mc["n_jets_pt30"])
                         & pu_pred(mc["pv_npvsgood"]))
                vs_pileup[slice_name][cat_name] = ratio_with_stat(dmask.sum(), mc["weight"][mmask])
        gen_result["vs_jet_count_by_pileup_slice"] = vs_pileup
        print("  (c) vs pileup slice:", json.dumps(vs_pileup, indent=2))

        # PV_npvsGood shape comparison (unit-area normalized), in the Z window
        dmask_z = mass_window_mask(data["mass"], Z_LO, Z_HI)
        mmask_z = mass_window_mask(mc["mass"], Z_LO, Z_HI)
        pv_edges = np.arange(0, 61, 1)
        d_pv_hist, _ = np.histogram(data["pv_npvsgood"][dmask_z], bins=pv_edges)
        m_pv_hist, _ = np.histogram(mc["pv_npvsgood"][mmask_z], bins=pv_edges, weights=mc["weight"][mmask_z])
        d_pv_norm = d_pv_hist / d_pv_hist.sum() if d_pv_hist.sum() > 0 else d_pv_hist
        m_pv_norm = m_pv_hist / m_pv_hist.sum() if m_pv_hist.sum() > 0 else m_pv_hist
        d_pv_mean = float(np.average(data["pv_npvsgood"][dmask_z])) if dmask_z.sum() > 0 else None
        m_pv_mean = (float(np.average(mc["pv_npvsgood"][mmask_z], weights=mc["weight"][mmask_z]))
                     if mmask_z.sum() > 0 else None)
        gen_result["pv_npvsgood_shape"] = {
            "data_mean": d_pv_mean, "mc_mean": m_pv_mean,
            "edges": pv_edges.tolist(),
            "data_shape_normalized": d_pv_norm.tolist(),
            "mc_shape_normalized": m_pv_norm.tolist(),
        }

        fig, ax = plt.subplots(figsize=(7, 5))
        centers = 0.5 * (pv_edges[:-1] + pv_edges[1:])
        ax.step(centers, d_pv_norm, where="mid", color="black", label=f"Data (mean={d_pv_mean:.1f})")
        ax.step(centers, m_pv_norm, where="mid", color="tab:blue",
                label=f"MC {stack_name} (mean={m_pv_mean:.1f})")
        ax.set_xlabel("PV_npvsGood")
        ax.set_ylabel("Shape-normalized fraction / bin")
        ax.set_title(f"PV_npvsGood shape, Z window, {stack_name}")
        ax.legend()
        fig.tight_layout()
        fig.savefig(PLOTS_DIR / f"e2_pv_npvsgood_shape_{stack_name}.png", dpi=130)
        plt.close(fig)

        # (d) leading-jet pT in Z + >=1 jet (pT>30)
        jetpt_edges = np.array([30, 40, 50, 60, 80, 100, 130, 170, 220, 300, 500])
        dmask_j1 = dmask_z & (data["n_jets_pt30"] >= 1)
        mmask_j1 = mmask_z & (mc["n_jets_pt30"] >= 1)
        d_pt_hist, _ = np.histogram(data["leading_jet_pt"][dmask_j1], bins=jetpt_edges)
        m_pt_hist, _ = np.histogram(mc["leading_jet_pt"][mmask_j1], bins=jetpt_edges, weights=mc["weight"][mmask_j1])
        m_pt_sumw2, _ = np.histogram(mc["leading_jet_pt"][mmask_j1], bins=jetpt_edges,
                                      weights=mc["weight"][mmask_j1] ** 2)
        with np.errstate(divide="ignore", invalid="ignore"):
            pt_ratio = np.where(m_pt_hist > 0, d_pt_hist / m_pt_hist, np.nan)
        gen_result["leading_jet_pt_ge1jet"] = {
            "edges": jetpt_edges.tolist(),
            "data_counts": d_pt_hist.tolist(),
            "mc_weighted_counts": m_pt_hist.tolist(),
            "mc_stat_err": np.sqrt(m_pt_sumw2).tolist(),
            "ratio": [None if np.isnan(x) else float(x) for x in pt_ratio],
        }

        # cross-check vs round-1: this pass's own >=1-jet(pT>30) Z-peak
        # ratio, computed directly here (this stack is DY+TTTo2L2Nu only,
        # 2 samples -- matching D1's/E1's 2-sample composition, NOT E1's
        # full 9-sample stack).
        ge1jet_60_120 = ratio_with_stat(dmask_j1.sum(), mc["weight"][mmask_j1])
        dmask_j1_narrow = mass_window_mask(data["mass"], NARROW_LO, NARROW_HI) & (data["n_jets_pt30"] >= 1)
        mmask_j1_narrow = mass_window_mask(mc["mass"], NARROW_LO, NARROW_HI) & (mc["n_jets_pt30"] >= 1)
        ge1jet_76_106 = ratio_with_stat(dmask_j1_narrow.sum(), mc["weight"][mmask_j1_narrow])
        gen_result["ge1jet_pt30_crosscheck_vs_round1"] = {
            "this_pass_60_120": ge1jet_60_120,
            "this_pass_76_106": ge1jet_76_106,
        }

        centers_pt = 0.5 * (jetpt_edges[:-1] + jetpt_edges[1:])
        widths_pt = np.diff(jetpt_edges)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True,
                                        gridspec_kw={"height_ratios": [3, 1]})
        ax1.bar(centers_pt, m_pt_hist, width=widths_pt, color="#3b6fa0", alpha=0.6,
                label=f"MC {stack_name}")
        ax1.fill_between(centers_pt, m_pt_hist - np.sqrt(m_pt_sumw2), m_pt_hist + np.sqrt(m_pt_sumw2),
                          step="mid", color="#3b6fa0", alpha=0.3)
        ax1.errorbar(centers_pt, d_pt_hist, yerr=np.sqrt(np.maximum(d_pt_hist, 0)),
                     fmt="ko", markersize=3, label="Data")
        ax1.set_ylabel("Events"); ax1.set_yscale("log"); ax1.legend()
        ax1.set_title(f"Leading jet pT, Z + >=1 jet(pT>30), {stack_name}")
        ax2.axhline(1.0, color="gray", linewidth=1)
        ax2.plot(centers_pt, pt_ratio, "ko", markersize=3)
        ax2.set_ylim(0, 2); ax2.set_ylabel("Data/MC"); ax2.set_xlabel("leading jet pT [GeV]")
        fig.tight_layout()
        fig.savefig(PLOTS_DIR / f"e2_leading_jet_pt_{stack_name}.png", dpi=130)
        plt.close(fig)

        result["generators"][stack_name] = gen_result

    # --- ratio-panel plots for (a) inclusive and (b) vs jet count ---
    fig, ax = plt.subplots(figsize=(7, 5))
    x = np.arange(4)
    labels = ["0", "1", "2", ">=3"]
    for stack_name, style in [("LO_madgraphMLM", "o-"), ("NLO_amcatnloFXFX", "s--")]:
        vals = [result["generators"][stack_name]["vs_jet_count"]["n_jets_pt30"][c]["ratio"] for c in ("0", "1", "2", "ge3")]
        errs = [result["generators"][stack_name]["vs_jet_count"]["n_jets_pt30"][c]["ratio_stat_err"] for c in ("0", "1", "2", "ge3")]
        ax.errorbar(x, vals, yerr=errs, fmt=style, label=stack_name)
    ax.axhline(1.0, color="gray", linewidth=1)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel("n jets (pT>30 GeV)"); ax.set_ylabel("Data/MC (60-120 GeV)")
    ax.set_title("E2(b): Data/MC vs jet count, both DY generators")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "e2_ratio_vs_jetcount_pt30.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    for stack_name, style in [("LO_madgraphMLM", "o-"), ("NLO_amcatnloFXFX", "s--")]:
        vals = [result["generators"][stack_name]["vs_jet_count"]["n_jets_pt50"][c]["ratio"] for c in ("0", "1", "2", "ge3")]
        errs = [result["generators"][stack_name]["vs_jet_count"]["n_jets_pt50"][c]["ratio_stat_err"] for c in ("0", "1", "2", "ge3")]
        ax.errorbar(x, vals, yerr=errs, fmt=style, label=stack_name)
    ax.axhline(1.0, color="gray", linewidth=1)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel("n jets (pT>50 GeV)"); ax.set_ylabel("Data/MC (60-120 GeV)")
    ax.set_title("E2(b): Data/MC vs jet count, pT>50 threshold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "e2_ratio_vs_jetcount_pt50.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    x2 = np.arange(3)
    labels2 = ["<=15", "16-25", ">25"]
    for stack_name, style in [("LO_madgraphMLM", "o-"), ("NLO_amcatnloFXFX", "s--")]:
        for cat_name, marker_off in [("0", 0), ("1", 0.06), ("ge3", -0.06)]:
            vals = [result["generators"][stack_name]["vs_jet_count_by_pileup_slice"][s][cat_name]["ratio"]
                    for s in ("le15", "16_25", "gt25")]
            ax.plot(x2 + marker_off, vals, style, label=f"{stack_name} njet={cat_name}", alpha=0.8)
    ax.axhline(1.0, color="gray", linewidth=1)
    ax.set_xticks(x2); ax.set_xticklabels(labels2)
    ax.set_xlabel("PV_npvsGood slice"); ax.set_ylabel("Data/MC (60-120 GeV)")
    ax.set_title("E2(c): Data/MC vs pileup slice, by jet count (pT>30)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "e2_ratio_vs_pileup_slice.png", dpi=130)
    plt.close(fig)

    # --- cross-check vs round 1 (D1 for LO DY+ttbar; E1's full 9-sample
    # stack for NLO DY+ttbar+7-more, noted as an approximate check since
    # the sample composition differs) ---
    d1_path = REPO_ROOT / "studies/cms_mc_weights/phase1/diagnosis/d1_zpeak_result.json"
    e1_path = REPO_ROOT / "studies/cms_mc_weights/phase1/diagnosis/e1_zpeak_full_stack_result.json"
    d1 = json.loads(d1_path.read_text(encoding="utf-8"))
    e1 = json.loads(e1_path.read_text(encoding="utf-8"))

    def sum_jet123(d):
        n_data = sum(d[c]["n_data_events_60_120"] for c in ("jet_1", "jet_2", "jet_ge3"))
        n_mc = sum(d[c]["n_mc_weighted_60_120"] for c in ("jet_1", "jet_2", "jet_ge3"))
        return {"n_data": n_data, "n_mc_weighted": n_mc, "ratio": (n_data / n_mc if n_mc > 0 else None)}

    result["crosscheck_vs_round1"] = {
        "LO_madgraphMLM": {
            "this_pass_ge1jet_pt30_60_120": result["generators"]["LO_madgraphMLM"]["ge1jet_pt30_crosscheck_vs_round1"]["this_pass_60_120"],
            "D1_2sample_jet1+jet2+jetge3_60_120": sum_jet123(d1["categories"]),
            "composition_note": "D1 used the identical 2-sample stack (DY madgraphMLM + TTTo2L2Nu) -- direct apples-to-apples comparison.",
        },
        "NLO_amcatnloFXFX": {
            "this_pass_ge1jet_pt30_60_120": result["generators"]["NLO_amcatnloFXFX"]["ge1jet_pt30_crosscheck_vs_round1"]["this_pass_60_120"],
            "E1_9sample_stack_b_jet1+jet2+jetge3_60_120": sum_jet123(e1["stacks"]["stack_b_amcatnloFXFX_DY"]["categories"]),
            "composition_note": "E1's stack (b) additionally includes 7 small backgrounds beyond DY+ttbar (~2-4% of the stack per D4) -- NOT a clean 2-sample match; a small residual difference from this is expected and is not evidence of a discrepancy in either pass.",
        },
    }

    out_path = REPO_ROOT / "studies/cms_mc_weights/phase1/diagnosis/e2_zpeak_analysis_result.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
