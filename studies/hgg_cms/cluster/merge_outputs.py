#!/usr/bin/env python
"""
Implementation task 6, Part E: merge per-job H->gamma-gamma outputs.

Two modes, matching the two PBS job layouts:

  --mode data   : one job PER INPUT FILE (pbs_hgg_data_array.sh), numbered
                  job_1 .. job_<total-jobs> under --jobs-base. Verifies
                  every expected job directory produced a
                  selected/job_metadata.json, sums cutflow counts across
                  all present jobs, and collects the full list of
                  originally-failed input files (if any) across all jobs.

  --mode signal : one job PER RECORD (pbs_hgg_signal.sh), each with its
                  own run directory. Verifies, per record, that the
                  number of files the shared pipeline actually processed
                  (read from that run's own <run-dir>/logs/
                  parsing_stats*.json -- the implementation-task-5,
                  Part-A genEventSumw aggregation, NOT recomputed here)
                  matches the expected file count for that record (from
                  studies/hgg_cms/impl_checks/signal_sumw.json's
                  "n_files"). The per-record genEventSumw this script
                  reports is exactly that same aggregation's
                  "genEventSumw" value -- i.e. summed over EXACTLY the
                  files that record's job actually, successfully
                  processed, never the full-record table in
                  signal_sumw.json (which covers "all files in record ...
                  NOT necessarily the files a given pipeline run actually
                  processed" -- see that file's own "important_note").

Either mode REFUSES to mark the merge "COMPLETE" if anything is missing,
UNLESS --force is passed -- in which case the summary is written but
explicitly stamped "COMPLETE_FORCED_WITH_MISSING" (never silently
"COMPLETE"). Exit code is 1 whenever the merge is not COMPLETE and not
forced, so a calling script can detect this without parsing JSON.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

SIGNAL_SUMW_JSON = REPO_ROOT / "studies" / "hgg_cms" / "impl_checks" / "signal_sumw.json"

DATA_CUTFLOW_KEYS = [
    "n_input_events", "n_with_ge2_tm_photons", "n_selected",
    "n_written_normal", "n_written_blinded_signal_region",
]


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _latest_parsing_stats(run_dir: Path):
    candidates = sorted(glob.glob(str(run_dir / "logs" / "parsing_stats*.json")))
    if not candidates:
        return None
    return _load_json(Path(candidates[-1]))


def merge_data(jobs_base: Path, total_jobs: int, out_path: Path, force: bool) -> int:
    missing_jobs = []
    total_cutflow = {k: 0 for k in DATA_CUTFLOW_KEYS}
    all_failed_files = []
    n_processed_files_total = 0
    commit_hashes, config_hashes = set(), set()

    for i in range(1, total_jobs + 1):
        job_dir = jobs_base / f"job_{i}"
        meta = _load_json(job_dir / "selected" / "job_metadata.json")
        if meta is None:
            missing_jobs.append(i)
            continue
        cf = meta.get("cutflow", {})
        for k in DATA_CUTFLOW_KEYS:
            total_cutflow[k] += cf.get(k, 0)
        n_processed_files_total += len(meta.get("input_files_processed", []))
        all_failed_files.extend(meta.get("input_files_failed", []))
        if meta.get("git_commit"):
            commit_hashes.add(meta["git_commit"])
        if meta.get("config_sha256"):
            config_hashes.add(meta["config_sha256"])

    complete = not missing_jobs
    status = "COMPLETE" if complete else ("COMPLETE_FORCED_WITH_MISSING" if force else "INCOMPLETE")

    summary = {
        "mode": "data",
        "status": status,
        "total_jobs_expected": total_jobs,
        "n_jobs_present": total_jobs - len(missing_jobs),
        "n_jobs_missing": len(missing_jobs),
        "missing_job_indices": missing_jobs,
        "git_commits_seen": sorted(commit_hashes),
        "config_sha256_seen": sorted(config_hashes),
        "total_cutflow": total_cutflow,
        "n_input_files_processed_total": n_processed_files_total,
        "n_input_files_failed_total": len(all_failed_files),
        "input_files_failed": all_failed_files,
    }
    if len(commit_hashes) > 1:
        summary["WARNING_multiple_git_commits"] = (
            "Jobs ran against different git commits -- results may not be "
            "directly comparable/mergeable."
        )
    if len(config_hashes) > 1:
        summary["WARNING_multiple_configs"] = (
            "Jobs ran with different config file contents (sha256 differs) "
            "-- results may not be directly comparable/mergeable."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    _print_summary(summary, missing_label="job indices", missing_list=missing_jobs)
    return 0 if status != "INCOMPLETE" else 1


def merge_signal(records: dict, out_path: Path, force: bool) -> int:
    sumw_table = json.loads(SIGNAL_SUMW_JSON.read_text(encoding="utf-8"))["records"]

    missing_records = []
    incomplete_records = []
    per_record = {}

    for rid, job_dir_str in records.items():
        job_dir = Path(job_dir_str)
        parsing_stats = _latest_parsing_stats(job_dir)
        sel_meta = _load_json(job_dir / "selected" / "job_metadata.json")

        if parsing_stats is None or sel_meta is None:
            missing_records.append(rid)
            continue

        record_key = f"record_{rid}"
        sw = (parsing_stats.get("sumw_by_record") or {}).get(record_key)
        expected_n_files = sumw_table[rid]["n_files"]
        n_processed = sw["n_files_processed"] if sw else 0
        n_failed = sw["n_files_failed"] if sw else None
        genEventSumw = sw["genEventSumw"] if sw else None
        genEventCount = sw["genEventCount"] if sw else None

        if n_processed < expected_n_files:
            incomplete_records.append({
                "record": rid, "label": sumw_table[rid]["label"],
                "expected_n_files": expected_n_files, "n_files_processed": n_processed,
            })

        sel_cutflow = sel_meta.get("cutflow", {})
        cross_section_pb = sumw_table[rid]["cross_section_pb"]
        br = sumw_table[rid]["branching_ratio_Hgammagamma"]
        sum_gw_sel = sel_cutflow.get("sum_genWeight_selected")

        expected_yield_note = None
        if genEventSumw and sum_gw_sel is not None:
            expected_yield_note = (
                "Combine as: cross_section_pb * 1000 (pb->fb) * "
                "branching_ratio_Hgammagamma * L_fb * "
                "(selection_cutflow.sum_genWeight_selected / "
                "genEventSumw_over_processed_files) -- L_fb (16.393 for "
                "the Run2016 legacy dataset) is not hardcoded here."
            )

        per_record[rid] = {
            "label": sumw_table[rid]["label"],
            "expected_n_files": expected_n_files,
            "n_files_processed": n_processed,
            "n_files_failed": n_failed,
            "genEventSumw_over_processed_files": genEventSumw,
            "genEventCount_over_processed_files": genEventCount,
            "cross_section_pb": cross_section_pb,
            "branching_ratio_Hgammagamma": br,
            "selection_cutflow": sel_cutflow,
            "dedup_removed_simulation_events": sel_cutflow.get("dedup_removed_simulation_events"),
            "how_to_combine_into_expected_yield": expected_yield_note,
        }

    complete = not missing_records and not incomplete_records
    status = "COMPLETE" if complete else ("COMPLETE_FORCED_WITH_MISSING" if force else "INCOMPLETE")

    summary = {
        "mode": "signal",
        "status": status,
        "records_expected": sorted(records.keys()),
        "missing_records": missing_records,
        "incomplete_records": incomplete_records,
        "per_record": per_record,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    _print_summary(
        summary,
        missing_label="records",
        missing_list=missing_records + [r["record"] for r in incomplete_records],
    )
    return 0 if status != "INCOMPLETE" else 1


def _print_summary(summary: dict, missing_label: str, missing_list: list) -> None:
    print(json.dumps(summary, indent=2))
    if missing_list:
        print(
            f"\n{'!' * 70}\n"
            f"MISSING/INCOMPLETE {missing_label}: {missing_list}\n"
            f"status = {summary['status']}\n"
            f"{'!' * 70}"
        )
    else:
        print(f"\nAll expected outputs present. status = {summary['status']}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", required=True, choices=["data", "signal"])
    p.add_argument("--out", required=True)
    p.add_argument("--force", action="store_true",
                    help="Write status=COMPLETE_FORCED_WITH_MISSING instead of "
                         "refusing COMPLETE when something is missing.")
    # data mode
    p.add_argument("--jobs-base", default=None)
    p.add_argument("--total-jobs", type=int, default=None)
    # signal mode
    p.add_argument("--record", action="append", default=[],
                    metavar="RECORD_ID=RUN_DIR",
                    help="Repeatable. e.g. --record 37350=/storage/.../cms_hgg_signal_ggh")
    args = p.parse_args()

    out_path = Path(args.out)

    if args.mode == "data":
        if not args.jobs_base or not args.total_jobs:
            p.error("--mode data requires --jobs-base and --total-jobs")
        rc = merge_data(Path(args.jobs_base), args.total_jobs, out_path, args.force)
    else:
        if not args.record:
            p.error("--mode signal requires at least one --record RECORD_ID=RUN_DIR")
        records = {}
        for entry in args.record:
            rid, _, job_dir = entry.partition("=")
            if not rid or not job_dir:
                p.error(f"bad --record value: {entry!r} (expected RECORD_ID=RUN_DIR)")
            records[rid] = job_dir
        rc = merge_signal(records, out_path, args.force)

    sys.exit(rc)


if __name__ == "__main__":
    main()
