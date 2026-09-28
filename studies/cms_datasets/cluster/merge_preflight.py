#!/usr/bin/env python
"""
Step 1 merge: aggregates every trigger_preflight_on_file.py job's
preflight_result.json into the four deliverables this task's Part 1 asks
for -- (a) path presence, (b) menu gaps (incl. the MuonEG DZ/non-DZ
activity question), (c) prescale verdicts, (d) overlap matrix -- plus the
required PNGs.

Every number here is a direct read or a straightforward sum/ratio of
numbers written by trigger_preflight_on_file.py's own per-file, per-run
counts (themselves read directly off real NanoAOD branches) -- nothing is
estimated or guessed.

Usage:
    python merge_preflight.py --preflight-dir <.../output/cms_datasets/preflight> \
        --out-json <preflight_summary.json> --out-plots-dir <plots dir>
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

from studies.cms_datasets.cluster.datasets_records import (  # noqa: E402
    DATASETS, VETO_ORDER, NESTED_REFERENCE_PAIRS, MUONEG_NONDZ_PATHS,
    MET_HIGHER_THRESHOLD_CANDIDATES,
)

TRIGGER_PATHS_BY_DATASET = {d.label: d.trigger_paths for d in DATASETS}

# Which dataset's own stored events are used to evaluate each nested pair
# (the dataset whose own trigger set is expected to contain essentially
# every event firing these paths -- see module docstring reasoning in
# datasets_records.py).
NESTED_PAIR_SOURCE_DATASET = {
    "HLT_PFJet450__vs__HLT_PFJet500": "JetHT",
    "HLT_IsoMu24__vs__HLT_IsoMu27": "SingleMuon",
    "HLT_IsoTkMu24__vs__HLT_IsoTkMu27": "SingleMuon",
    "HLT_Ele27_WPTight_Gsf__vs__HLT_Ele32_eta2p1_WPTight_Gsf": "SingleElectron",
    "HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL__vs__HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ": "MuonEG",
    "HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL__vs__HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ": "MuonEG",
    "HLT_PFMET170_HBHECleaned__vs__HLT_PFMET300": "MET",
    "HLT_PFMET170_NotCleaned__vs__HLT_PFMET300": "MET",
}

# Fallback (no valid nested reference) ratio checks: (dataset, path, reference_path).
# Reference is a DIFFERENT path's own marginal count within the SAME dataset's
# own stored events -- weaker (cannot prove absence of a constant-across-runs
# prescale), per this task's own instruction.
FALLBACK_RATIO_CHECKS = [
    ("JetHT", "HLT_PFHT900", "HLT_PFJet450"),
    ("DoubleMuon", "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ", "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ"),
    ("DoubleEG", "HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ", "HLT_Ele27_WPTight_Gsf"),
]

PRESCALE_MIN_STRICTER_COUNT = 20  # below this, a run's ratio is too noisy to judge
PRESCALE_UNPRESCALED_RATIO_MIN = 0.95


def load_all_jobs(preflight_dir: Path):
    jobs = []
    for f in sorted(preflight_dir.glob("job_*/preflight_result.json")):
        jobs.append(json.loads(f.read_text()))
    return jobs


def part_a_path_presence(jobs):
    missing_by_path = defaultdict(list)
    n_files = 0
    for job in jobs:
        for pf in job["per_file"]:
            n_files += 1
            for path in pf["missing_hlt_branches"]:
                missing_by_path[path].append({
                    "dataset_label": job["dataset_label"], "era": job["era"],
                    "record_id": job["record_id"], "file_index": pf["file_index"],
                })
    return {
        "n_files_checked": n_files,
        "n_paths_with_any_missing_occurrence": len(missing_by_path),
        "missing_occurrences_by_path": dict(missing_by_path),
        "all_paths_present_everywhere": len(missing_by_path) == 0,
    }


def part_b_menu_gaps(jobs):
    # per dataset -> per run -> {n_golden, per_path_fires, era}
    per_dataset_run = defaultdict(lambda: defaultdict(lambda: {"n_golden": 0, "per_path_fires": defaultdict(int), "era": None}))
    for job in jobs:
        label, era = job["dataset_label"], job["era"]
        for pf in job["per_file"]:
            for run_str, run_data in pf["runs"].items():
                bucket = per_dataset_run[label][run_str]
                bucket["n_golden"] += run_data["n_golden"]
                bucket["era"] = era
                for path, count in run_data["per_path_fires"].items():
                    bucket["per_path_fires"][path] += count

    menu_gap_flags = []
    per_dataset_summary = {}
    for label, runs in per_dataset_run.items():
        own_paths = TRIGGER_PATHS_BY_DATASET[label]
        zero_fire_runs = []
        for run_str, bucket in runs.items():
            if bucket["n_golden"] <= 0:
                continue
            for path in own_paths:
                fires = bucket["per_path_fires"].get(path, 0)
                if fires == 0:
                    zero_fire_runs.append({"run": run_str, "era": bucket["era"], "path": path, "n_golden": bucket["n_golden"]})
        per_dataset_summary[label] = {
            "n_runs": len(runs),
            "n_runs_with_a_zero_fire_own_path": len({z["run"] for z in zero_fire_runs}),
            "zero_fire_flags": zero_fire_runs,
        }
        menu_gap_flags.extend(zero_fire_runs)

    # MuonEG DZ (G) / non-DZ (H) activity question.
    muoneg_runs = per_dataset_run.get("MuonEG", {})
    dz_paths = TRIGGER_PATHS_BY_DATASET["MuonEG"]
    g_runs = {r: b for r, b in muoneg_runs.items() if b["era"] == "G"}
    h_runs = {r: b for r, b in muoneg_runs.items() if b["era"] == "H"}

    def _active_every_run(runs_dict, paths):
        details = {}
        all_active = True
        for run, bucket in runs_dict.items():
            per_path = {p: bucket["per_path_fires"].get(p, 0) for p in paths}
            any_active = any(v > 0 for v in per_path.values())
            details[run] = {"n_golden": bucket["n_golden"], "per_path_fires": per_path, "any_path_active": any_active}
            if not any_active and bucket["n_golden"] > 0:
                all_active = False
        return all_active, details

    dz_active_every_run_g, dz_detail_g = _active_every_run(g_runs, dz_paths)
    nondz_active_every_run_h, nondz_detail_h = _active_every_run(h_runs, MUONEG_NONDZ_PATHS)

    return {
        "per_dataset_summary": per_dataset_summary,
        "n_total_zero_fire_flags": len(menu_gap_flags),
        "muoneg_dz_active_every_run_of_g": dz_active_every_run_g,
        "muoneg_dz_detail_by_run_g": dz_detail_g,
        "muoneg_nondz_active_every_run_of_h": nondz_active_every_run_h,
        "muoneg_nondz_detail_by_run_h": nondz_detail_h,
    }


def _collect_nested_per_run(jobs, source_dataset, pair_key):
    """Per-run {n_stricter, n_looser_and_stricter} summed across all files
    of source_dataset (both eras -- run numbers already disambiguate era)."""
    per_run = defaultdict(lambda: {"n_stricter": 0, "n_looser_and_stricter": 0})
    for job in jobs:
        if job["dataset_label"] != source_dataset:
            continue
        for pf in job["per_file"]:
            for run_str, run_data in pf["runs"].items():
                entry = run_data["nested_reference_pairs"].get(pair_key)
                if entry is None:
                    continue
                per_run[run_str]["n_stricter"] += entry["n_stricter"]
                per_run[run_str]["n_looser_and_stricter"] += entry["n_looser_and_stricter"]
    return per_run


def part_c_prescale_tests(jobs, plots_dir: Path):
    results = {}
    plot_paths = []

    for looser, stricter in NESTED_REFERENCE_PAIRS:
        pair_key = f"{looser}__vs__{stricter}"
        source_dataset = NESTED_PAIR_SOURCE_DATASET[pair_key]
        per_run = _collect_nested_per_run(jobs, source_dataset, pair_key)

        runs_sorted = sorted(per_run.keys(), key=lambda r: int(r))
        ratios, usable_runs, low_count_runs = [], [], []
        for run in runs_sorted:
            n_s = per_run[run]["n_stricter"]
            n_ls = per_run[run]["n_looser_and_stricter"]
            if n_s < PRESCALE_MIN_STRICTER_COUNT:
                low_count_runs.append(run)
                continue
            ratios.append(n_ls / n_s)
            usable_runs.append(run)

        if not ratios:
            verdict = "cannot be determined (insufficient statistics in every run)"
            prescaled_runs = []
        else:
            prescaled_runs = [r for r, ratio in zip(usable_runs, ratios) if ratio < PRESCALE_UNPRESCALED_RATIO_MIN]
            verdict = "unprescaled (tested)" if not prescaled_runs else f"prescaled in runs {prescaled_runs}"

        results[pair_key] = {
            "looser": looser, "stricter": stricter, "source_dataset": source_dataset,
            "method": "nested (stricter implies looser)",
            "n_runs_total": len(runs_sorted), "n_runs_usable": len(usable_runs),
            "n_runs_too_low_stricter_count": len(low_count_runs),
            "ratio_min": round(min(ratios), 4) if ratios else None,
            "ratio_median": round(float(np.median(ratios)), 4) if ratios else None,
            "ratio_max": round(max(ratios), 4) if ratios else None,
            "verdict": verdict,
        }

        needs_plot = (source_dataset in ("JetHT", "MET")) or bool(prescaled_runs)
        if needs_plot and usable_runs:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot([int(r) for r in usable_runs], ratios, marker="o", linestyle="-", markersize=3)
            ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
            ax.set_xlabel("Run number")
            ax.set_ylabel(f"N({looser} AND {stricter}) / N({stricter})")
            ax.set_title(f"Nested-reference prescale test: {looser} vs {stricter} ({source_dataset})")
            ax.set_ylim(0, 1.1)
            fig.tight_layout()
            out_path = plots_dir / f"nested_ratio_{pair_key}.png"
            fig.savefig(out_path, dpi=120)
            plt.close(fig)
            plot_paths.append(str(out_path))

    # Fallback (no valid nested reference) checks.
    fallback_results = {}
    for dataset_label, path, reference_path in FALLBACK_RATIO_CHECKS:
        per_run = defaultdict(lambda: {"n_path": 0, "n_ref": 0})
        for job in jobs:
            if job["dataset_label"] != dataset_label:
                continue
            for pf in job["per_file"]:
                for run_str, run_data in pf["runs"].items():
                    fires = run_data["per_path_fires"]
                    per_run[run_str]["n_path"] += fires.get(path, 0)
                    per_run[run_str]["n_ref"] += fires.get(reference_path, 0)
        runs_sorted = sorted(per_run.keys(), key=lambda r: int(r))
        ratios = []
        for run in runs_sorted:
            n_ref = per_run[run]["n_ref"]
            if n_ref >= PRESCALE_MIN_STRICTER_COUNT:
                ratios.append(per_run[run]["n_path"] / n_ref)
        fallback_results[f"{path}__ratio_to__{reference_path}"] = {
            "dataset": dataset_label, "path": path, "reference_path": reference_path,
            "method": "fallback (same-dataset ratio to an unrelated path, NOT a nested test -- "
                      "cannot prove absence of a prescale constant across all runs)",
            "n_runs_usable": len(ratios),
            "ratio_min": round(min(ratios), 4) if ratios else None,
            "ratio_median": round(float(np.median(ratios)), 4) if ratios else None,
            "ratio_max": round(max(ratios), 4) if ratios else None,
            "verdict": "cannot be determined (fallback method only)",
        }

    return {"nested_pair_results": results, "fallback_results": fallback_results, "plots_written": plot_paths}


def part_d_overlap_matrix(jobs, plots_dir: Path):
    labels = VETO_ORDER
    totals = {label: defaultdict(int) for label in labels}  # totals[X][Y] = n_own_trigger(X) events also passing Y
    n_own_total = defaultdict(int)
    n_exclusive_total = defaultdict(int)

    for job in jobs:
        label = job["dataset_label"]
        for pf in job["per_file"]:
            for run_data in pf["runs"].values():
                own = run_data.get("own_dataset")
                if own is None:
                    continue
                n_own_total[label] += own["n_own_trigger"]
                if own["n_exclusive"] is not None:
                    n_exclusive_total[label] += own["n_exclusive"]
                for other_label, n_also in own["n_also_passing"].items():
                    totals[label][other_label] += n_also

    matrix = []
    for x in labels:
        row = []
        for y in labels:
            if x == y:
                row.append(1.0)
            else:
                denom = n_own_total[x]
                row.append(round(totals[x][y] / denom, 4) if denom else None)
        matrix.append(row)

    exclusive_fraction = {
        x: (round(n_exclusive_total[x] / n_own_total[x], 4) if n_own_total[x] else None)
        for x in labels
    }

    fig, ax = plt.subplots(figsize=(8, 7))
    display_matrix = np.array([[v if v is not None else np.nan for v in row] for row in matrix])
    im = ax.imshow(display_matrix, cmap="viridis", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    ax.set_xlabel("also passing dataset Y's trigger")
    ax.set_ylabel("dataset X (golden events passing X's own trigger)")
    ax.set_title("Trigger overlap matrix (fraction of X's events also passing Y's trigger)")
    for i in range(len(labels)):
        for j in range(len(labels)):
            v = matrix[i][j]
            txt = f"{v:.3f}" if v is not None else "N/A"
            ax.text(j, i, txt, ha="center", va="center",
                     color="white" if (v is None or v < 0.6) else "black", fontsize=8)
    fig.colorbar(im, ax=ax, label="fraction")
    fig.tight_layout()
    out_path = plots_dir / "overlap_matrix_heatmap.png"
    fig.savefig(out_path, dpi=120)
    plt.close(fig)

    return {
        "labels": labels,
        "matrix_row_is_X_col_is_Y": matrix,
        "n_own_trigger_total": dict(n_own_total),
        "exclusive_fraction_by_dataset": exclusive_fraction,
        "plot_written": str(out_path),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--preflight-dir", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-plots-dir", required=True)
    args = p.parse_args()

    preflight_dir = Path(args.preflight_dir)
    plots_dir = Path(args.out_plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)

    jobs = load_all_jobs(preflight_dir)
    print(f"loaded {len(jobs)} job result files")

    result = {
        "n_job_files_loaded": len(jobs),
        "part_a_path_presence": part_a_path_presence(jobs),
        "part_b_menu_gaps": part_b_menu_gaps(jobs),
        "part_c_prescale_tests": part_c_prescale_tests(jobs, plots_dir),
        "part_d_overlap_matrix": part_d_overlap_matrix(jobs, plots_dir),
    }
    Path(args.out_json).write_text(json.dumps(result, indent=2))
    print(f"wrote {args.out_json}")
    print(f"plots written under {plots_dir}")


if __name__ == "__main__":
    main()
