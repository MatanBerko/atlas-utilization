#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- Step 2 full run: job-index -> (record, file-index)
map generator.

Re-fetches BOTH records' (30522, 30555) CURRENT portal file lists AND
current portal-published total event/file counts, fresh, every time this
runs -- never cached or hardcoded, per this task's own instruction that
the portal's file list has changed within a single day before. Writes a
flat "<job_index> <record_id> <file_index>" map (1-based, matching
PBS_ARRAY_INDEX directly) that the PBS array script reads per-subjob, and
a JSON summary (per-record file/event counts, expected total) used to
size the array (-J 1-<total_jobs>) and as one input to the merge step's
completeness check (the merge step also independently re-fetches the
portal itself at merge time -- this summary is a submission-time
snapshot, not assumed still current hours later).

Usage:
    python generate_job_index_map.py \
        --out-map /storage/.../job_index_map.txt \
        --out-summary /storage/.../job_index_map_summary.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.m0m1j0_cms.design_checks.common import (  # noqa: E402
    fetch_file_list, fetch_record_number_events,
)

RECORDS = (30522, 30555)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-map", required=True)
    p.add_argument("--out-summary", required=True)
    args = p.parse_args()

    lines = []
    per_record = {}
    idx = 1
    for record_id in RECORDS:
        urls = fetch_file_list(record_id)
        portal_meta = fetch_record_number_events(record_id)
        if len(urls) != portal_meta["number_files"]:
            print(
                f"WARNING: record {record_id}: fetch_file_list returned {len(urls)} files but "
                f"the portal's own distribution.number_files says {portal_meta['number_files']} "
                f"-- using the actual fetched list ({len(urls)} files) for job assignment.",
                file=sys.stderr,
            )
        per_record[str(record_id)] = {
            "n_files_in_fetched_list": len(urls),
            "portal_number_files": portal_meta["number_files"],
            "portal_number_events": portal_meta["number_events"],
            "urls": urls,
        }
        for file_index in range(len(urls)):
            lines.append(f"{idx} {record_id} {file_index}")
            idx += 1

    total_jobs = idx - 1
    Path(args.out_map).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_map).write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary = {
        "total_jobs": total_jobs,
        "per_record": per_record,
        "total_expected_events_from_portal": sum(v["portal_number_events"] for v in per_record.values()),
    }
    Path(args.out_summary).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"wrote {args.out_map} ({total_jobs} jobs) and {args.out_summary}")
    print(f"per-record: " + ", ".join(f"{r}={d['n_files_in_fetched_list']} files" for r, d in per_record.items()))
    print(f"total expected events (portal): {summary['total_expected_events_from_portal']}")


if __name__ == "__main__":
    main()
