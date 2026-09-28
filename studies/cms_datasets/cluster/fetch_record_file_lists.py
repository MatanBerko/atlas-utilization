#!/usr/bin/env python
"""
Step 0 prep for the trigger pre-flight scan: fetch the CERN Open Data
portal's own file list and published event/file totals for all 14
dataset x era records (7 datasets, Run2016 G+H, Tau excluded), using the
SAME portal API calls already used elsewhere in this repo
(studies.m0m1j0_cms.design_checks.common.fetch_file_list /
fetch_record_number_events -- imported, not reimplemented).

Verifies the portal's OWN file count against the task brief's expected
(G+H combined) file counts, and reports any mismatch prominently rather
than silently trusting either number. Every number in the output is
either read directly from the portal's own API response (this script's
entire job) or a straight arithmetic combination of two such numbers.

Usage:
    python fetch_record_file_lists.py --out <path.json>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.m0m1j0_cms.design_checks.common import fetch_file_list, fetch_record_number_events  # noqa: E402
from studies.cms_datasets.cluster.datasets_records import DATASETS  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()

    per_record = {}
    for d in DATASETS:
        for era, record_id in (("G", d.record_g), ("H", d.record_h)):
            print(f"fetching {d.label} {era} (record {record_id})...", flush=True)
            for attempt in range(3):
                try:
                    files = fetch_file_list(record_id)
                    meta = fetch_record_number_events(record_id)
                    break
                except Exception as e:  # noqa: BLE001
                    print(f"  attempt {attempt + 1}/3 failed: {type(e).__name__}: {e}", flush=True)
                    if attempt == 2:
                        raise
                    time.sleep(5)
            per_record[f"{d.label}_{era}"] = {
                "dataset_label": d.label,
                "era": era,
                "record_id": record_id,
                "n_files_from_filepage_api": len(files),
                "file_urls": files,
                "portal_number_events": meta["number_events"],
                "portal_number_files": meta["number_files"],
            }
            print(f"  {d.label} {era}: {len(files)} files (filepage API), "
                  f"portal says number_files={meta['number_files']}, "
                  f"number_events={meta['number_events']}", flush=True)

    mismatches = []
    for d in DATASETS:
        g = per_record[f"{d.label}_G"]
        h = per_record[f"{d.label}_H"]
        actual_total = g["n_files_from_filepage_api"] + h["n_files_from_filepage_api"]
        portal_total = g["portal_number_files"] + h["portal_number_files"]
        row = {
            "dataset_label": d.label,
            "expected_g_plus_h_from_task_brief": d.expected_files_g_plus_h,
            "actual_g_plus_h_from_filepage_api": actual_total,
            "portal_number_files_g_plus_h": portal_total,
            "matches_task_brief": actual_total == d.expected_files_g_plus_h,
            "filepage_api_matches_portal_number_files": actual_total == portal_total,
        }
        if not row["matches_task_brief"] or not row["filepage_api_matches_portal_number_files"]:
            mismatches.append(row)
        per_record[f"{d.label}_G"]["_cross_check"] = row
        per_record[f"{d.label}_H"]["_cross_check"] = row

    result = {
        "source": "https://opendata.cern.ch (filepage + records API), fetched live",
        "records": per_record,
        "n_mismatches": len(mismatches),
        "mismatches": mismatches,
    }
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps({"n_mismatches": len(mismatches), "mismatches": mismatches}, indent=2))
    print(f"wrote {args.out}")
    if mismatches:
        print(f"WARNING: {len(mismatches)} dataset(s) have a file-count mismatch -- see output above", file=sys.stderr)


if __name__ == "__main__":
    main()
