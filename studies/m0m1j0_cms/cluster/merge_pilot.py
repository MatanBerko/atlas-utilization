#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- Step 1 PILOT merge.

Merges the 4 pilot jobs' outputs (studies/m0m1j0_cms/cluster/
run_m0m1j0_on_file.py: job_1..job_4 under --jobs-base), with:

  - Portal identity verification: re-fetches each pilot record's CURRENT
    file list (studies.m0m1j0_cms.design_checks.common.fetch_file_list)
    and compares it against what each job's own job_metadata.json
    recorded actually reading -- the task's own instructions note this
    list has changed within a single day before, so "the job ran and
    exited 0" is not by itself proof it read the file a human would
    expect from a fixed index today.
  - Histogram merging: sums same-named histograms (by their ROOT-internal
    ROI_..._width_10 name) across every present job's all_histograms.root,
    read/written via uproot -- this cluster account's own atlas-pipeline
    conda env has no PyROOT installed at all (see
    studies/m0m1j0_cms/histograms.py's module docstring for the full
    finding, discovered running this pilot), so histogram I/O throughout
    this study goes through uproot instead of PyROOT's TFile/TH1.
  - The merge-time-only min_events_per_fs prune (>=100 events per exact
    final state, GLOBAL across all merged jobs -- RECIPE.md section
    5/6.5; never applied per-job, and never applied to the inclusive
    histogram) -- using each job's own recorded per-category event count
    (job_metadata.json's "per_category"."<name>"."n_events_in_histogram",
    already an exact count) summed across jobs, rather than re-deriving a
    count from summed bin contents.
  - Cutflow, per-category counts, and outlier-event-list concatenation.
  - The 4 required sanity-check PNGs (dimuon mass, leading-jet pT,
    inclusive m0m1j0 log-y, top-5 categories overlaid).

This script does NOT decide whether the merge is "complete" in the sense
of covering the full 57-file dataset -- it is scoped to exactly the 4
pilot jobs and reports plainly on those 4, including any that are
missing or that read a file other than the portal's current one.

Usage:
    python merge_pilot.py \
        --jobs-base /storage/agrp/berkom/atlas-utilization/output/m0m1j0_pilot \
        --out-dir studies/m0m1j0_cms/pilot
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402
from studies.m0m1j0_cms.histograms import INCLUSIVE_HIST_NAME  # noqa: E402
from studies.m0m1j0_cms.selection import MIN_EVENTS_PER_FINAL_STATE, Z_PEAK_CUTOFF_GEV  # noqa: E402

JOB_INDEX_TO_RECORD_FILE = {1: (30522, 0), 2: (30522, 1), 3: (30555, 0), 4: (30555, 1)}
CUTFLOW_KEYS = [
    "n_read", "n_after_golden_json", "n_after_trigger", "n_after_ge2mu",
    "n_after_ge1jet_after_cleaning", "n_after_z_peak_and_mass_cutoff", "n_outliers_gt_1tev",
]


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def check_portal_identity(jobs_base: Path) -> dict:
    portal_first_two = {record_id: fetch_file_list(record_id)[:2] for record_id, _ in JOB_INDEX_TO_RECORD_FILE.values()}
    per_job = {}
    problems = []
    for idx, (record_id, file_index) in JOB_INDEX_TO_RECORD_FILE.items():
        meta = _load_json(jobs_base / f"job_{idx}" / "job_metadata.json")
        if meta is None:
            per_job[idx] = {"status": "MISSING_METADATA", "record_id": record_id, "file_index": file_index}
            problems.append(f"job_{idx}: missing job_metadata.json")
            continue
        recorded_url = meta["file_url"]
        current_urls = portal_first_two.get(record_id, [])
        current_url_at_index = current_urls[file_index] if file_index < len(current_urls) else None
        matches = recorded_url == current_url_at_index
        if not matches:
            problems.append(
                f"job_{idx} (record {record_id}, file-index {file_index}): recorded URL "
                f"{recorded_url!r} != portal's CURRENT file at that index "
                f"({current_url_at_index!r}) -- portal file list may have changed since this job ran."
            )
        per_job[idx] = {
            "status": "OK",
            "record_id": record_id,
            "file_index": file_index,
            "recorded_url": recorded_url,
            "current_portal_url_at_this_index": current_url_at_index,
            "matches_current_portal": matches,
            "n_read": meta["cutflow"]["n_read"],
            "git_commit": meta.get("git_commit"),
        }
    return {"per_job": per_job, "problems": problems}


def _bumpnet_name_from_root_name(root_name: str) -> str:
    """Strips the ROI_/_width_N ROOT-internal decoration back to the
    grouping name histograms.py used (see its own docstring on the
    known, documented ROI_ mismatch -- not fixed here, just undone for
    display/grouping purposes in this merge script)."""
    name = root_name[len("ROI_"):] if root_name.startswith("ROI_") else root_name
    return re.sub(r"_width_\d+$", "", name)


def merge_histograms(jobs_base: Path, present_indices: list) -> dict:
    """Sums same-named (values, edges) histograms across every present
    job's all_histograms.root, read via uproot (see this module's own
    docstring for why not PyROOT). Edges are asserted identical across
    jobs -- every job builds on the same FIXED_MASS_MIN_GEV/MAX_GEV grid
    (studies/m0m1j0_cms/histograms.py), so a mismatch would mean a job
    ran against different code, not a legitimate binning choice."""
    merged: dict = {}
    for idx in present_indices:
        root_path = jobs_base / f"job_{idx}" / "all_histograms.root"
        if not root_path.exists():
            continue
        f = uproot.open(str(root_path))
        for key in f.keys(cycle=False):
            hist = f[key]
            values = hist.values()
            edges = hist.axis().edges()
            if key not in merged:
                merged[key] = (values.copy(), edges)
            else:
                prev_values, prev_edges = merged[key]
                if not np.array_equal(prev_edges, edges):
                    raise ValueError(
                        f"job_{idx}'s histogram {key!r} has different bin edges than an "
                        f"earlier job -- jobs ran against inconsistent code/config."
                    )
                merged[key] = (prev_values + values, prev_edges)
    return merged


def sum_per_category_counts(jobs_base: Path, present_indices: list) -> dict:
    """Sums each job's own recorded per-category event count
    (job_metadata.json's "per_category"."<name>"."n_events_in_histogram")
    across present jobs -- an exact count already computed per job, used
    for the merge-time min_events_per_fs check instead of re-deriving a
    count from summed bin contents."""
    totals: dict = {}
    for idx in present_indices:
        meta = _load_json(jobs_base / f"job_{idx}" / "job_metadata.json")
        if meta is None:
            continue
        for name, cat_meta in meta.get("per_category", {}).items():
            if name.startswith("_"):  # "_dropped_categories_below_min_events_per_fs"
                continue
            totals[name] = totals.get(name, 0) + cat_meta.get("n_events_in_histogram", 0)
    return totals


def apply_merge_time_min_events_prune(merged_hists: dict, per_category_counts: dict) -> tuple:
    """The real min_events_per_fs check (RECIPE.md section 5/6.5):
    GLOBAL population per exact final state, taken AFTER summing every
    job -- never applied per job, never applied to the inclusive
    histogram."""
    kept, dropped = {}, []
    for root_name, hist in merged_hists.items():
        grouping_name = _bumpnet_name_from_root_name(root_name)
        if grouping_name == INCLUSIVE_HIST_NAME:
            kept[root_name] = hist
            continue
        n_entries = int(per_category_counts.get(grouping_name, 0))
        if n_entries < MIN_EVENTS_PER_FINAL_STATE:
            dropped.append({"name": grouping_name, "n_entries": n_entries})
            continue
        kept[root_name] = hist
    return kept, dropped


def sum_cutflow(jobs_base: Path, present_indices: list) -> dict:
    total = {k: 0 for k in CUTFLOW_KEYS}
    for idx in present_indices:
        meta = _load_json(jobs_base / f"job_{idx}" / "job_metadata.json")
        if meta is None:
            continue
        cf = meta.get("cutflow", {})
        for k in CUTFLOW_KEYS:
            total[k] += cf.get(k, 0)
    return total


def merge_outliers(jobs_base: Path, present_indices: list) -> list:
    merged = []
    for idx in present_indices:
        data = _load_json(jobs_base / f"job_{idx}" / "outliers_gt_1tev.json")
        if data:
            merged.extend(data)
    return merged


def merge_sanity_arrays(jobs_base: Path, present_indices: list) -> dict:
    dimuon, jet_pt = [], []
    for idx in present_indices:
        data = _load_json(jobs_base / f"job_{idx}" / "sanity_arrays.json")
        if data:
            dimuon.extend(data.get("dimuon_mass_gev", []))
            jet_pt.extend(data.get("leading_jet_pt_gev", []))
    return {"dimuon_mass_gev": dimuon, "leading_jet_pt_gev": jet_pt}


def plot_dimuon_mass(dimuon_mass_gev: list, out_path: Path):
    arr = np.array([x for x in dimuon_mass_gev if x == x])  # drop NaN
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(arr, bins=100, range=(0, 200), histtype="stepfilled", color="#4c72b0", alpha=0.8)
    ax.axvline(91.19, color="red", linestyle="--", label="Z pole (91.19 GeV)")
    ax.set_xlabel("Dimuon mass [GeV] (leading + subleading selected muon)")
    ax.set_ylabel("Events / 2 GeV")
    ax.set_title("m0m1j0 pilot: dimuon mass of the selected pair")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_leading_jet_pt(jet_pt_gev: list, out_path: Path):
    arr = np.array([x for x in jet_pt_gev if x == x])
    fig, ax = plt.subplots(figsize=(7, 5))
    hi = max(200.0, float(np.percentile(arr, 99)) if len(arr) else 200.0)
    ax.hist(arr, bins=60, range=(0, hi), histtype="stepfilled", color="#55a868", alpha=0.8)
    ax.axvline(30.0, color="red", linestyle="--", label="30 GeV jet pT cut")
    ax.set_xlabel("Leading (light) jet pT [GeV]")
    ax.set_ylabel(f"Events / {hi/60:.1f} GeV")
    ax.set_title("m0m1j0 pilot: leading light-jet pT")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_inclusive_m0m1j0(hist: tuple, out_path: Path):
    contents, edges = hist
    nonzero = np.nonzero(contents)[0]
    last_bin = int(nonzero.max()) + 1 if len(nonzero) else 10
    centers = (edges[:-1] + edges[1:]) / 2
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.step(centers[:last_bin], contents[:last_bin], where="mid", color="#c44e52")
    ax.set_yscale("log")
    ax.axvline(Z_PEAK_CUTOFF_GEV, color="gray", linestyle=":", label=f"z_peak_cutoff ({Z_PEAK_CUTOFF_GEV:.0f} GeV)")
    ax.set_xlabel("m0m1j0 [GeV]")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_title(f"m0m1j0 pilot: inclusive ({INCLUSIVE_HIST_NAME})")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_top_categories(kept_hists: dict, per_category_counts: dict, out_path: Path, top_n: int = 5):
    scored = []
    for root_name, hist in kept_hists.items():
        grouping_name = _bumpnet_name_from_root_name(root_name)
        if grouping_name == INCLUSIVE_HIST_NAME:
            continue
        n_entries = int(per_category_counts.get(grouping_name, 0))
        scored.append((n_entries, grouping_name, hist))
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:top_n]

    fig, ax = plt.subplots(figsize=(8, 5))
    for n_entries, grouping_name, hist in top:
        contents, edges = hist
        nonzero = np.nonzero(contents)[0]
        last_bin = int(nonzero.max()) + 1 if len(nonzero) else 10
        centers = (edges[:-1] + edges[1:]) / 2
        ax.step(centers[:last_bin], contents[:last_bin], where="mid", label=f"{grouping_name} (n={n_entries})")
    ax.set_yscale("log")
    ax.set_xlabel("m0m1j0 [GeV]")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_title(f"m0m1j0 pilot: top {top_n} categories by event count")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return [{"category": name, "n_entries": n} for n, name, _ in top]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-base", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    jobs_base = Path(args.jobs_base)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    present_indices = [i for i in JOB_INDEX_TO_RECORD_FILE if (jobs_base / f"job_{i}" / "job_metadata.json").exists()]
    missing_indices = [i for i in JOB_INDEX_TO_RECORD_FILE if i not in present_indices]

    identity = check_portal_identity(jobs_base)
    merged_hists = merge_histograms(jobs_base, present_indices)
    per_category_counts = sum_per_category_counts(jobs_base, present_indices)
    kept_hists, dropped_categories = apply_merge_time_min_events_prune(merged_hists, per_category_counts)
    cutflow = sum_cutflow(jobs_base, present_indices)
    outliers = merge_outliers(jobs_base, present_indices)
    sanity = merge_sanity_arrays(jobs_base, present_indices)

    merged_root_path = out_dir / "m0m1j0_pilot_merged.root"
    with uproot.recreate(str(merged_root_path)) as f:
        for root_name, (values, edges) in kept_hists.items():
            f[root_name] = (values, edges)

    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_dimuon_mass(sanity["dimuon_mass_gev"], plots_dir / "dimuon_mass.png")
    plot_leading_jet_pt(sanity["leading_jet_pt_gev"], plots_dir / "leading_jet_pt.png")

    inclusive_root_name = next(
        (n for n in kept_hists if _bumpnet_name_from_root_name(n) == INCLUSIVE_HIST_NAME), None
    )
    top_categories = []
    if inclusive_root_name is not None:
        plot_inclusive_m0m1j0(kept_hists[inclusive_root_name], plots_dir / "inclusive_m0m1j0.png")
        top_categories = plot_top_categories(kept_hists, per_category_counts, plots_dir / "top5_categories.png")

    summary = {
        "jobs_base": str(jobs_base),
        "present_job_indices": present_indices,
        "missing_job_indices": missing_indices,
        "n_jobs_expected": len(JOB_INDEX_TO_RECORD_FILE),
        "portal_identity": identity,
        "cutflow_summed_over_present_jobs": cutflow,
        "n_histograms_before_merge_prune": len(merged_hists),
        "n_histograms_after_merge_prune": len(kept_hists),
        "dropped_categories_below_min_events_per_fs": dropped_categories,
        "top_categories_by_event_count": top_categories,
        "n_outlier_events_gt_1tev": len(outliers),
        "complete": (
            not missing_indices
            and not identity["problems"]
        ),
    }
    (out_dir / "pilot_merge_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "outliers_gt_1tev_merged.json").write_text(json.dumps(outliers, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    if summary["complete"]:
        print("\nMerge status: COMPLETE (all 4 jobs present, no portal-identity problems).")
    else:
        print("\nMerge status: INCOMPLETE -- see missing_job_indices / portal_identity.problems above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
