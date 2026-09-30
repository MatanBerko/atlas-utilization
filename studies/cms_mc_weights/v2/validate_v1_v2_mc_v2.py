#!/usr/bin/env python
"""
CMS MC weights task v2 -- V1 (arithmetic closure) and V2 (per-file
Sigma genWeight vs Runs genEventSumw) validation, for every v2 sample.

No fresh ROOT reads: every number here comes from job_metadata.json's own
mc_runs_tree_sums_this_file / mc_sum_genweight_all_events_this_file,
already recorded per file during the --is-mc production run itself (the
full, pre-any-cut genWeight sum was computed once, in memory, at driver
time -- see run_dataset_on_file.py). Read from the DoubleMuon-labeled run
of each file (identical to the SingleMuon-labeled run's own numbers for
the same physical file -- asserted, not just assumed, exactly as
build_mc_muon_combined_delivery.py already does).

Reports, per sample: V2 across ALL discovered files (before the bad-file
policy excludes anything) and V2/V1 across the USED (good) files only --
directly showing whether/how the bad-file policy changes the result
(the v2 task's own explicit ask: "confirming that the bad-file policy
fixes ZZTo4L").

Usage:
    python validate_v1_v2_mc_v2.py --out studies/cms_mc_weights/v2/validate_v1_v2_result.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

BAD_FILE_REL_TOL = 1e-6
LUMI_FB = 16.393

WORK_BASE = "/storage/agrp/berkom/atlas-utilization/work/cms_mc_v2"

SAMPLES = {
    "42407": 12, "67801": 49, "35669": 41, "35671": 61,
    "64895": 11, "64839": 10, "72676": 7, "72752": 31,
    "75589": 99, "68187": 42, "68073": 12,
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--normalisation", default="studies/cms_mc_weights/cms_mc_normalisation.json")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    normalisation = json.loads(Path(args.normalisation).read_text(encoding="utf-8"))

    result = {}
    for record_id, n_files in SAMPLES.items():
        sigma_eff_pb = normalisation[record_id]["cross_section_pb"]
        target = sigma_eff_pb * 1000.0 * LUMI_FB

        per_file = []
        n_missing = []
        for i in range(n_files):
            meta_path = Path(WORK_BASE) / record_id / "DoubleMuon" / f"job_{i}" / "job_metadata.json"
            if not meta_path.exists():
                n_missing.append(i)
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            genEventSumw = meta["mc_runs_tree_sums_this_file"]["genEventSumw"]
            full_gw = meta["mc_sum_genweight_all_events_this_file"]
            rel_diff = abs(full_gw - genEventSumw) / abs(genEventSumw) if genEventSumw != 0 else float("nan")
            per_file.append({
                "file_index": i, "genEventSumw_runs_tree": genEventSumw,
                "sum_genWeight_all_events": full_gw, "relative_difference": rel_diff,
            })

        all_files_max_rel_diff = max((r["relative_difference"] for r in per_file), default=None)
        good = [r for r in per_file if r["relative_difference"] <= BAD_FILE_REL_TOL]
        bad = [r for r in per_file if r["relative_difference"] > BAD_FILE_REL_TOL]
        used_files_max_rel_diff = max((r["relative_difference"] for r in good), default=None)

        sum_genEventSumw_used = sum(r["genEventSumw_runs_tree"] for r in good)
        sum_full_gw_used = sum(r["sum_genWeight_all_events"] for r in good)
        v1_sum = target * (sum_full_gw_used / sum_genEventSumw_used) if sum_genEventSumw_used else None
        v1_rel_diff = abs(v1_sum - target) / abs(target) if v1_sum is not None else None

        result[record_id] = {
            "n_files_expected": n_files,
            "n_files_found": len(per_file),
            "n_files_missing": n_missing,
            "sigma_eff_pb": sigma_eff_pb,
            "target_sigma_eff_times_1000_times_L": target,
            "V2_all_files_max_relative_difference": all_files_max_rel_diff,
            "V2_n_bad_files_excluded": len(bad),
            "V2_bad_files": bad,
            "V2_used_files_max_relative_difference": used_files_max_rel_diff,
            "V2_used_files_all_pass_1e-6": (used_files_max_rel_diff is not None and used_files_max_rel_diff < BAD_FILE_REL_TOL),
            "V1_sum_genEventSumw_used": sum_genEventSumw_used,
            "V1_sum_weights_over_all_events_before_selection": v1_sum,
            "V1_target": target,
            "V1_relative_difference": v1_rel_diff,
            "V1_PASS_1e-6": (v1_rel_diff is not None and v1_rel_diff < BAD_FILE_REL_TOL),
        }
        print(f"{record_id}: n_files_found={len(per_file)} n_bad_excluded={len(bad)} "
              f"V2_used_max_reldiff={used_files_max_rel_diff} V1_reldiff={v1_rel_diff}", flush=True)

    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
