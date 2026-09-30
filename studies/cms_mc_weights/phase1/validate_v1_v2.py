#!/usr/bin/env python
"""
Phase-1 MC weights task -- V1 (arithmetic closure) and V2 (per-file
Sigma genWeight vs Runs genEventSumw) validation.

V2: for EVERY successfully processed file, reads the file's OWN Events-
tree genWeight branch in full (all events, not just selected -- a single,
cheap branch read) and compares its sum against that same file's own
Runs-tree genEventSumw (already cached in job_metadata.json's
runs_tree_sums_this_file, from A5's read_runs_tree_sums, never
re-derived here -- this script only re-reads the Events-tree side to
cross-check it).

V1: given V2 passes for every file (Sigma_events genWeight == genEventSumw,
per file, to float precision), summing across every processed file gives
Sigma_allfiles(genEventSumw) [[the aggregate_sumw_for_processed_files
denominator]] == Sigma_allfiles Sigma_events(genWeight) [[the numerator of
the full per-event weight formula, summed over ALL events, BEFORE
selection]] -- so
    Sigma(genWeight * sigma_eff*1000*L / Sigma_genWeight)
      = sigma_eff*1000*L * (Sigma_allfiles Sigma_events genWeight) / Sigma_genWeight
      = sigma_eff*1000*L
to the same floating-point precision V2 establishes, PROVIDED
Sigma_genWeight (the denominator actually used for the phase-1 weight,
from merge_full_v2_mc.py / aggregate_sumw_for_processed_files) equals the
same total this script independently sums here. Both are checked and
compared explicitly (not just asserted).

Usage:
    python validate_v1_v2.py \
        --record-id 67801 --jobs-base /storage/.../work/cms_mc_phase1/67801 \
        --merge-summary studies/cms_mc_weights/phase1/67801/merge_mc_summary.json \
        --out studies/cms_mc_weights/phase1/67801/validate_v1_v2_result.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record-id", required=True)
    p.add_argument("--jobs-base", required=True)
    p.add_argument("--merge-summary", required=True)
    p.add_argument("--lumi-fb", type=float, default=16.393)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    jobs_base = Path(args.jobs_base)
    merge_summary = json.loads(Path(args.merge_summary).read_text(encoding="utf-8"))
    sigma_eff_pb = merge_summary["cross_section_pb"]
    sigma_genweight_used = merge_summary["sum_genEventSumw"]
    per_file_norm = merge_summary["per_file_normalization_factor"]

    per_file_results = []
    total_events_read = 0
    total_sum_genweight_events_tree = 0.0
    total_genEventSumw_runs_tree = 0.0
    total_sum_l1_times_genweight_selected = 0.0
    total_n_selected = 0
    total_sum_l1_selected = 0.0

    n_files_present = 0
    for job_dir in sorted(jobs_base.glob("job_*"), key=lambda p: int(p.name.split("_")[1])):
        meta_path = job_dir / "job_metadata.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        file_url = meta["file_url"]
        n_read = meta["n_read"]
        genEventSumw = meta["runs_tree_sums_this_file"]["genEventSumw"]

        tree = uproot.open(file_url)["Events"]
        gw_all = tree["genWeight"].array(library="np")
        sum_gw_events_tree = float(gw_all.sum())

        rel_diff = abs(sum_gw_events_tree - genEventSumw) / abs(genEventSumw) if genEventSumw != 0 else float("nan")

        per_file_results.append({
            "file_url": file_url,
            "n_read": n_read,
            "sum_genWeight_events_tree_ALL_events": sum_gw_events_tree,
            "genEventSumw_runs_tree": genEventSumw,
            "relative_difference": rel_diff,
        })

        total_events_read += n_read
        total_sum_genweight_events_tree += sum_gw_events_tree
        total_genEventSumw_runs_tree += genEventSumw
        n_files_present += 1

        # For the prefiring-factor mean (V1's own separate report):
        # selected-event genWeight/L1 already cached per job.
        n_sel = meta["n_after_v0_selection"]
        mean_l1_sel = meta.get("mean_L1PreFiringWeight_Nom_selected_events_this_file")
        if n_sel > 0 and mean_l1_sel is not None:
            total_sum_l1_selected += mean_l1_sel * n_sel
            total_n_selected += n_sel

    # V1: Sigma over ALL events (before selection) of the full weight formula.
    # weight_i = genWeight_i * sigma_eff*1000*L / Sigma_genWeight_used
    # Sigma_i weight_i = sigma_eff*1000*L * total_sum_genweight_events_tree / Sigma_genWeight_used
    target = sigma_eff_pb * 1000.0 * args.lumi_fb
    v1_sum_weights_all_events = target * (total_sum_genweight_events_tree / sigma_genweight_used)
    v1_relative_diff = abs(v1_sum_weights_all_events - target) / abs(target)

    mean_l1_prefiring_overall = (total_sum_l1_selected / total_n_selected) if total_n_selected > 0 else None

    result = {
        "record_id": args.record_id,
        "n_files_checked": n_files_present,
        "sigma_eff_pb": sigma_eff_pb,
        "target_luminosity_fb": args.lumi_fb,
        "target_sigma_eff_times_1000_times_L": target,
        "V2_per_file": per_file_results,
        "V2_max_relative_difference": max((r["relative_difference"] for r in per_file_results), default=None),
        "V2_all_pass_1e-6": all(r["relative_difference"] < 1e-6 for r in per_file_results),
        "sum_genEventSumw_used_in_merge": sigma_genweight_used,
        "sum_genWeight_events_tree_independently_recomputed": total_sum_genweight_events_tree,
        "denominator_relative_difference": (
            abs(total_sum_genweight_events_tree - sigma_genweight_used) / abs(sigma_genweight_used)
        ),
        "V1_sum_weights_over_all_events_before_selection": v1_sum_weights_all_events,
        "V1_target_sigma_eff_times_1000_times_L": target,
        "V1_relative_difference": v1_relative_diff,
        "V1_PASS_1e-6": v1_relative_diff < 1e-6,
        "mean_L1PreFiringWeight_Nom_over_selected_events": mean_l1_prefiring_overall,
    }

    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "V2_per_file"}, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
