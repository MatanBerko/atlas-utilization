#!/usr/bin/env python
"""
Step 4 (quality-gate report): aggregates cutflow, portal identity check,
and resonance/diagnostic histograms across every job of a full dataset
run -- straight from each job's own job_metadata.json (written by
run_dataset_on_file.py), nothing re-read from the raw NanoAOD files or
recomputed from the shards. Produces the required PNGs (Z peak + J/psi,
leading/subleading muon pT with cut/trigger-leg markers, low-mass
opposite-sign dimuon mass+dR) and a JSON summary with every number
VERIFIED BY RUNNING (i.e. read directly from the per-job metadata this
task's own full run already produced and committed as evidence).

Usage:
    python aggregate_cutflow_and_resonances.py --dataset-label DoubleMuon \
        --runs-dir /storage/.../output/cms_datasets/runs/DoubleMuon \
        --file-lists studies/cms_datasets/evidence/record_file_lists.json \
        --trigger-leg-gev 17,8 --muon-pt-cut-gev 25 \
        --out-json <summary.json> --out-plots-dir <plots dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import matplotlib
matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

try:
    from scipy.optimize import curve_fit
    _HAVE_SCIPY = True
except ImportError:
    _HAVE_SCIPY = False


def _gaussian(x, amp, mu, sigma, offset):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2) + offset


def fit_peak(centers: np.ndarray, counts: np.ndarray, window: tuple, p0_sigma: float):
    lo, hi = window
    mask = (centers >= lo) & (centers <= hi)
    x, y = centers[mask], counts[mask].astype(np.float64)
    if x.size < 5 or y.sum() == 0:
        return {"method": "insufficient_data", "position_gev": None}
    argmax_pos = float(x[np.argmax(y)])
    if not _HAVE_SCIPY:
        return {"method": "argmax (scipy unavailable)", "position_gev": argmax_pos}
    p0 = [float(y.max() - y.min()), argmax_pos, p0_sigma, float(y.min())]
    try:
        popt, pcov = curve_fit(_gaussian, x, y, p0=p0, maxfev=10000)
        perr = np.sqrt(np.diag(pcov))
        return {
            "method": "gaussian_fit",
            "position_gev": float(popt[1]),
            "position_err_gev": float(perr[1]),
            "sigma_gev": float(popt[2]),
            "amplitude": float(popt[0]),
            "offset": float(popt[3]),
            "argmax_fallback_gev": argmax_pos,
        }
    except Exception as e:  # noqa: BLE001
        return {"method": f"gaussian_fit_failed ({type(e).__name__}: {e})", "position_gev": argmax_pos,
                "argmax_fallback_gev": argmax_pos}


def sum_histograms(jobs: list, key: str):
    edges = None
    total_counts = None
    total_n_entries = 0
    total_n_nan = 0
    for meta in jobs:
        h = meta["diagnostics"][key]
        if edges is None:
            edges = np.array(h["bin_edges_gev"])
            total_counts = np.zeros(len(h["counts"]), dtype=np.int64)
        total_counts += np.array(h["counts"], dtype=np.int64)
        total_n_entries += h["n_entries"]
        total_n_nan += h["n_nan_or_missing"]
    return edges, total_counts, total_n_entries, total_n_nan


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-label", required=True)
    p.add_argument("--runs-dir", required=True)
    p.add_argument("--file-lists", required=True)
    p.add_argument("--trigger-leg-gev", required=True, help="comma-separated, e.g. 17,8")
    p.add_argument("--muon-pt-cut-gev", type=float, default=25.0)
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-plots-dir", required=True)
    args = p.parse_args()

    runs_dir = Path(args.runs_dir)
    plots_dir = Path(args.out_plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)
    trigger_legs = [float(x) for x in args.trigger_leg_gev.split(",")]
    file_lists = json.loads(Path(args.file_lists).read_text())["records"]

    job_dirs = sorted(runs_dir.glob("job_*"), key=lambda d: int(d.name.split("_")[1]))
    jobs = []
    for jd in job_dirs:
        meta_path = jd / "job_metadata.json"
        if not meta_path.exists():
            raise RuntimeError(f"{jd}: missing job_metadata.json")
        jobs.append(json.loads(meta_path.read_text()))

    n_jobs = len(jobs)
    print(f"loaded {n_jobs} job metadata files")

    # ---- Cutflow ----
    total_n_read = sum(j["n_read"] for j in jobs)
    total_n_after_golden = sum(j["n_after_golden_json"] for j in jobs)
    total_n_after_trigger = sum(j["n_after_trigger"] for j in jobs)
    total_n_after_gate = sum(j["n_after_gate"] for j in jobs)
    total_n_exclusive = sum(j["n_exclusive"] for j in jobs)

    per_path_totals = defaultdict(int)
    for j in jobs:
        for path, count in j["trigger_per_path"].items():
            per_path_totals[path] += count

    g_key, h_key = f"{args.dataset_label}_G", f"{args.dataset_label}_H"
    portal_total_events = file_lists[g_key]["portal_number_events"] + file_lists[h_key]["portal_number_events"]

    cutflow = {
        "n_jobs": n_jobs,
        "read": total_n_read,
        "after_golden_json": total_n_after_golden,
        "after_trigger_OR": total_n_after_trigger,
        "trigger_per_path_totals": dict(per_path_totals),
        "after_population_gate": total_n_after_gate,
        "n_exclusive": total_n_exclusive,
        "inclusive_equals_exclusive": total_n_exclusive == total_n_after_gate,
        "portal_identity_check": {
            "sum_n_read": total_n_read,
            "portal_number_events_both_eras": portal_total_events,
            "matches": total_n_read == portal_total_events,
        },
    }
    print(json.dumps(cutflow, indent=2))

    # ---- Resonances: raw dimuon mass, coarse (Z) and fine (J/psi) ----
    edges_coarse, counts_coarse, n_entries_coarse, n_nan_coarse = sum_histograms(jobs, "raw_dimuon_mass_mu0mu1")
    centers_coarse = (edges_coarse[:-1] + edges_coarse[1:]) / 2
    z_fit = fit_peak(centers_coarse, counts_coarse, window=(75, 107), p0_sigma=3.0)

    edges_fine, counts_fine, n_entries_fine, n_nan_fine = sum_histograms(jobs, "raw_dimuon_mass_mu0mu1_lowmass_finebins")
    centers_fine = (edges_fine[:-1] + edges_fine[1:]) / 2
    jpsi_fit = fit_peak(centers_fine, counts_fine, window=(2.8, 3.4), p0_sigma=0.05)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.stairs(counts_coarse, edges_coarse, fill=False)
    ax.set_yscale("log")
    ax.set_xlabel("m(mu0,mu1) [GeV] (raw, pre-post-processing)")
    ax.set_ylabel("Pairs / 1 GeV")
    ax.set_title(f"{args.dataset_label}: raw dimuon mass, full dataset ({n_jobs} files)")
    if z_fit["position_gev"]:
        ax.axvline(z_fit["position_gev"], color="red", linestyle="--",
                     label=f"Z fit: {z_fit['position_gev']:.2f} GeV")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "raw_dimuon_mass_full_range.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.stairs(counts_fine, edges_fine, fill=False)
    ax.set_yscale("log")
    ax.set_xlabel("m(mu0,mu1) [GeV] (raw, pre-post-processing)")
    ax.set_ylabel("Pairs / 20 MeV")
    ax.set_title(f"{args.dataset_label}: raw dimuon mass, low-mass region ({n_jobs} files)")
    if jpsi_fit["position_gev"]:
        ax.axvline(jpsi_fit["position_gev"], color="darkorange", linestyle="--",
                     label=f"J/psi fit: {jpsi_fit['position_gev']:.3f} GeV")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "raw_dimuon_mass_lowmass_region.png", dpi=130)
    plt.close(fig)

    # ---- Leading/subleading muon pT ----
    edges_lead, counts_lead, n_lead, _ = sum_histograms(jobs, "leading_muon_pt")
    edges_sub, counts_sub, n_sub, _ = sum_histograms(jobs, "subleading_muon_pt")
    centers_lead = (edges_lead[:-1] + edges_lead[1:]) / 2

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.stairs(counts_lead, edges_lead, fill=False, label="leading muon")
    ax.stairs(counts_sub, edges_sub, fill=False, label="subleading muon")
    ax.axvline(args.muon_pt_cut_gev, color="red", linestyle="--", label=f"object cut ({args.muon_pt_cut_gev:.0f} GeV)")
    for leg in trigger_legs:
        ax.axvline(leg, color="orange", linestyle=":", label=f"trigger leg ({leg:.0f} GeV)")
    ax.set_xlabel("Muon pT [GeV]")
    ax.set_ylabel("Events / 1 GeV")
    ax.set_xlim(0, 100)
    ax.set_title(f"{args.dataset_label}: leading/subleading selected muon pT, full dataset")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "leading_subleading_muon_pt.png", dpi=130)
    plt.close(fig)

    # ---- Low-mass opposite-sign dimuon population ----
    total_pairs_lt5 = 0
    total_mass_below_2 = 0
    all_dr_below_2 = []
    total_n_ge2mu = sum(j["diagnostics"]["n_events_ge2_selected_muons"] for j in jobs)
    for j in jobs:
        lm = j["diagnostics"]["low_mass_opposite_sign_dimuon"]
        masses = np.array(lm["mass_gev"])
        drs = np.array(lm["dr"])
        total_pairs_lt5 += lm["n_pairs"]
        below2 = masses < 2.0
        total_mass_below_2 += int(below2.sum())
        all_dr_below_2.extend(drs[below2].tolist())

    low_mass_summary = {
        "n_opposite_sign_pairs_m_lt_5gev": total_pairs_lt5,
        "n_opposite_sign_pairs_m_lt_2gev": total_mass_below_2,
        "n_all_gated_events": total_n_after_gate,
        "n_events_ge2_selected_muons": total_n_ge2mu,
        "fraction_of_all_gated_events": round(total_mass_below_2 / total_n_after_gate, 6) if total_n_after_gate else None,
        "fraction_of_events_with_ge2_muons": round(total_mass_below_2 / total_n_ge2mu, 6) if total_n_ge2mu else None,
    }
    print(json.dumps(low_mass_summary, indent=2))

    if all_dr_below_2:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        masses_all = []
        for j in jobs:
            lm = j["diagnostics"]["low_mass_opposite_sign_dimuon"]
            masses_all.extend(lm["mass_gev"])
        ax1.hist(masses_all, bins=50, range=(0, 5), histtype="step")
        ax1.set_xlabel("m(mu,mu) [GeV] (opposite-sign, m<5 GeV)")
        ax1.set_ylabel("Pairs")
        ax2.hist(all_dr_below_2, bins=50, range=(0, 1), histtype="step")
        ax2.set_xlabel("dR(mu,mu) (pairs with m<2 GeV)")
        ax2.set_ylabel("Pairs")
        fig.suptitle(f"{args.dataset_label}: low-mass opposite-sign dimuon population, full dataset")
        fig.tight_layout()
        fig.savefig(plots_dir / "low_mass_dimuon_population.png", dpi=130)
        plt.close(fig)

    result = {
        "dataset_label": args.dataset_label,
        "n_jobs": n_jobs,
        "cutflow": cutflow,
        "z_peak_fit": z_fit,
        "jpsi_peak_fit": jpsi_fit,
        "low_mass_population": low_mass_summary,
        "scipy_available_for_fits": _HAVE_SCIPY,
    }
    Path(args.out_json).write_text(json.dumps(result, indent=2))
    print(f"wrote {args.out_json}")
    print(f"plots written under {plots_dir}")


if __name__ == "__main__":
    main()
