#!/usr/bin/env python
"""
Step 4 pilot merge: reads each pilot job's job_metadata.json (wall time,
event counts at each stage, exclusive fraction, shard size -- all written
directly by run_dataset_on_file.py, nothing recomputed) and each pilot
job's own PBS log (/usr/bin/time -v output, for peak memory), then derives
a per-dataset cost estimate for the full run and produces the required
diagnostic PNGs straight from each job's own "diagnostics" histograms
(already computed once, at job run time, over real data -- not
regenerated here).

Usage:
    python merge_pilot.py --run-dir <.../output/cms_datasets/run> \
        --pbs-log-dir <.../logs/cms_datasets_run> \
        --file-lists <record_file_lists.json> \
        --out-json <pilot_summary.json> --out-plots-dir <plots dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import matplotlib
matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from studies.cms_datasets.cluster.gen_step4_pilot_mapping import PILOT_DATASET_LABELS, PILOT_FILE_INDEX  # noqa: E402
from studies.cms_datasets.cluster.datasets_records import DATASETS  # noqa: E402

MEM_RE = re.compile(r"Maximum resident set size \(kbytes\): (\d+)")
WALL_RE = re.compile(r"Elapsed \(wall clock\) time.*: (?:(\d+):)?(\d+):(\d+(?:\.\d+)?)")


def parse_time_v_log(log_path: Path) -> dict:
    if not log_path.exists():
        return {"peak_mem_mb": None, "wall_time_sec_from_log": None}
    text = log_path.read_text(errors="replace")
    mem_match = MEM_RE.search(text)
    wall_match = WALL_RE.search(text)
    peak_mem_mb = int(mem_match.group(1)) / 1024 if mem_match else None
    wall_sec = None
    if wall_match:
        hours = int(wall_match.group(1)) if wall_match.group(1) else 0
        minutes = int(wall_match.group(2))
        seconds = float(wall_match.group(3))
        wall_sec = hours * 3600 + minutes * 60 + seconds
    return {"peak_mem_mb": peak_mem_mb, "wall_time_sec_from_log": wall_sec}


def _hist_from_diag(diag_entry: dict):
    edges = np.array(diag_entry["bin_edges_gev"])
    counts = np.array(diag_entry["counts"])
    centers = (edges[:-1] + edges[1:]) / 2
    return centers, counts


def _weighted_peak(centers, counts):
    if counts.sum() == 0:
        return None
    return float(centers[np.argmax(counts)])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True)
    p.add_argument("--pbs-log-dir", required=True)
    p.add_argument("--file-lists", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-plots-dir", required=True)
    args = p.parse_args()

    run_dir = Path(args.run_dir)
    plots_dir = Path(args.out_plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)
    file_lists = json.loads(Path(args.file_lists).read_text())["records"]

    by_label = {d.label: d for d in DATASETS}
    pilot_jobs = []
    for label in PILOT_DATASET_LABELS:
        d = by_label[label]
        for era, record_id in (("G", d.record_g), ("H", d.record_h)):
            job_dir = run_dir / f"job_{label}_{record_id}_{PILOT_FILE_INDEX}_generic"
            meta_path = job_dir / "job_metadata.json"
            if not meta_path.exists():
                pilot_jobs.append({"dataset_label": label, "era": era, "record_id": record_id, "found": False})
                continue
            meta = json.loads(meta_path.read_text())
            log_path = Path(args.pbs_log_dir)
            # array index unknown here; find by scanning err logs for this job's file_url
            time_v = {"peak_mem_mb": None, "wall_time_sec_from_log": None}
            for err_file in sorted(log_path.glob("run_*.err")):
                text = err_file.read_text(errors="replace")
                if f"--record-id {record_id} --file-index {PILOT_FILE_INDEX}" in text and f"--dataset-label {label}" in text:
                    time_v = parse_time_v_log(err_file)
                    break
            pilot_jobs.append({
                "dataset_label": label, "era": era, "record_id": record_id, "found": True,
                "n_read": meta["n_read"], "n_after_golden_json": meta["n_after_golden_json"],
                "n_after_trigger": meta["n_after_trigger"], "n_after_gate": meta["n_after_gate"],
                "n_exclusive": meta["n_exclusive"],
                "exclusive_fraction": round(meta["n_exclusive"] / meta["n_after_gate"], 4) if meta["n_after_gate"] else None,
                "elapsed_sec_metadata": meta["elapsed_sec"],
                "peak_mem_mb": time_v["peak_mem_mb"],
                "wall_time_sec_from_log": time_v["wall_time_sec_from_log"],
                "inclusive_shard_size_mb": meta["inclusive_shard_size_mb"],
                "exclusive_shard_size_mb": meta["exclusive_shard_size_mb"],
                "diagnostics": meta["diagnostics"],
            })

    # Per-dataset cost estimate: mean per-file elapsed time (over both era
    # pilot files) x portal's own total file count for that dataset.
    cost_estimates = {}
    for label in PILOT_DATASET_LABELS:
        rows = [j for j in pilot_jobs if j["dataset_label"] == label and j["found"]]
        if not rows:
            cost_estimates[label] = {"n_pilot_files": 0}
            continue
        elapsed = [r["elapsed_sec_metadata"] for r in rows]
        d = by_label[label]
        n_total_files = file_lists[f"{label}_G"]["n_files_from_filepage_api"] + file_lists[f"{label}_H"]["n_files_from_filepage_api"]
        n_events_pilot = [r["n_read"] for r in rows]
        mean_sec_per_file = float(np.mean(elapsed))
        est_total_core_hours = mean_sec_per_file * n_total_files / 3600.0
        cost_estimates[label] = {
            "n_pilot_files": len(rows),
            "pilot_elapsed_sec": elapsed,
            "pilot_n_events": n_events_pilot,
            "mean_elapsed_sec_per_file": round(mean_sec_per_file, 1),
            "n_total_files_full_run": n_total_files,
            "estimated_total_core_hours_full_run": round(est_total_core_hours, 2),
            "peak_mem_mb_observed": [r["peak_mem_mb"] for r in rows],
        }

    # Required PNGs.
    def plot_mass(dataset_labels, key, title, out_name, xlim=(0, 200)):
        fig, ax = plt.subplots(figsize=(8, 5))
        for label in dataset_labels:
            for row in pilot_jobs:
                if row["dataset_label"] == label and row["found"]:
                    centers, counts = _hist_from_diag(row["diagnostics"][key])
                    ax.step(centers, counts, where="mid", label=f"{label} ({row['era']})")
        ax.set_xlabel("Mass [GeV]")
        ax.set_ylabel("Events / 1 GeV")
        ax.set_xlim(*xlim)
        ax.set_title(title)
        ax.legend()
        fig.tight_layout()
        fig.savefig(plots_dir / out_name, dpi=120)
        plt.close(fig)

    plot_mass(["SingleMuon", "DoubleMuon"], "raw_dimuon_mass_mu0mu1",
               "Raw m(mu0,mu1), pilot files", "pilot_raw_dimuon_mass.png")
    plot_mass(["DoubleEG", "SingleElectron"], "raw_dielectron_mass_e0e1",
               "Raw m(e0,e1), pilot files", "pilot_raw_dielectron_mass.png")

    z_peaks = {}
    for label in ["SingleMuon", "DoubleMuon"]:
        for row in pilot_jobs:
            if row["dataset_label"] == label and row["found"]:
                centers, counts = _hist_from_diag(row["diagnostics"]["raw_dimuon_mass_mu0mu1"])
                mask = (centers > 70) & (centers < 110)
                z_peaks[f"{label}_{row['era']}_dimuon"] = _weighted_peak(centers[mask], counts[mask])
    for label in ["DoubleEG", "SingleElectron"]:
        for row in pilot_jobs:
            if row["dataset_label"] == label and row["found"]:
                centers, counts = _hist_from_diag(row["diagnostics"]["raw_dielectron_mass_e0e1"])
                mask = (centers > 70) & (centers < 110)
                z_peaks[f"{label}_{row['era']}_dielectron"] = _weighted_peak(centers[mask], counts[mask])

    # Leading lepton pT plots with cut/trigger threshold markers.
    def plot_pt(label, key, cut_gev, trigger_gev, out_name, fraction_window):
        fig, ax = plt.subplots(figsize=(8, 5))
        fractions = {}
        for row in pilot_jobs:
            if row["dataset_label"] == label and row["found"]:
                centers, counts = _hist_from_diag(row["diagnostics"][key])
                ax.step(centers, counts, where="mid", label=f"{label} ({row['era']})")
                total = counts.sum()
                lo, hi = fraction_window
                in_window = counts[(centers >= lo) & (centers < hi)].sum()
                fractions[row["era"]] = round(float(in_window / total), 4) if total else None
        ax.axvline(cut_gev, color="red", linestyle="--", label=f"object cut ({cut_gev} GeV)")
        ax.axvline(trigger_gev, color="orange", linestyle=":", label=f"trigger threshold ({trigger_gev} GeV)")
        ax.set_xlabel("Leading lepton pT [GeV]")
        ax.set_ylabel("Events / 1 GeV")
        ax.set_xlim(0, 100)
        ax.set_title(f"Leading {label} lepton pT, pilot files")
        ax.legend()
        fig.tight_layout()
        fig.savefig(plots_dir / out_name, dpi=120)
        plt.close(fig)
        return fractions

    frac_muon = plot_pt("SingleMuon", "leading_muon_pt", 25, 24, "pilot_leading_muon_pt.png", (25, 28))
    frac_electron = plot_pt("SingleElectron", "leading_electron_pt", 25, 27, "pilot_leading_electron_pt.png", (25, 30))

    # Low-mass opposite-sign dimuon plots.
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    low_mass_below_2gev_fraction = {}
    for row in pilot_jobs:
        if row["dataset_label"] in ("DoubleMuon", "SingleMuon") and row["found"]:
            lm = row["diagnostics"]["low_mass_opposite_sign_dimuon"]
            masses = np.array(lm["mass_gev"])
            drs = np.array(lm["dr"])
            label_str = f"{row['dataset_label']} ({row['era']})"
            if masses.size:
                axes[0].hist(masses, bins=25, range=(0, 5), histtype="step", label=label_str)
                axes[1].hist(drs, bins=25, range=(0, 1), histtype="step", label=label_str)
                low_mass_below_2gev_fraction[label_str] = round(float((masses < 2.0).sum() / masses.size), 4)
            else:
                low_mass_below_2gev_fraction[label_str] = None
    axes[0].set_xlabel("m(mu,mu) [GeV] (opposite-sign, m<5 GeV)")
    axes[0].set_ylabel("Pairs")
    axes[0].legend()
    axes[1].set_xlabel("dR(mu,mu)")
    axes[1].set_ylabel("Pairs")
    axes[1].legend()
    fig.suptitle("Low-mass opposite-sign dimuon pairs, pilot files")
    fig.tight_layout()
    fig.savefig(plots_dir / "pilot_low_mass_dimuon.png", dpi=120)
    plt.close(fig)

    result = {
        "pilot_jobs": pilot_jobs,
        "cost_estimates": cost_estimates,
        "z_peak_positions_gev": z_peaks,
        "leading_muon_pt_fraction_25to28gev": frac_muon,
        "leading_electron_pt_fraction_25to30gev": frac_electron,
        "low_mass_dimuon_fraction_below_2gev": low_mass_below_2gev_fraction,
    }
    Path(args.out_json).write_text(json.dumps(result, indent=2))
    print(json.dumps({"z_peak_positions_gev": z_peaks, "cost_estimates": {k: v.get("estimated_total_core_hours_full_run") for k, v in cost_estimates.items()}}, indent=2))
    print(f"wrote {args.out_json}")
    print(f"plots written under {plots_dir}")


if __name__ == "__main__":
    main()
