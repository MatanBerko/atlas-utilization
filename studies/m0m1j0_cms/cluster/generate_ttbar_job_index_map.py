#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- Part B: ttbar job-index -> file-index map
generator. Same technique as
studies/m0m1j0_cms/cluster/generate_job_index_map.py (fresh portal
fetch, never cached), kept as a separate small script rather than
parameterizing that one -- the data map generator is already validated
by the full data re-run and is not touched here.

Record: 67801 (RECIPE.md section 8) -- the ONE ttbar record this study
uses; --limit-files lets the pilot (first 2 files) reuse this same
script rather than needing a separate hand-written 2-line mapping file.

Usage:
    python generate_ttbar_job_index_map.py \
        --out-map /storage/.../job_index_map.txt \
        --out-summary /storage/.../job_index_map_summary.json \
        [--limit-files 2]
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

TTBAR_RECORD_ID = 67801


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-map", required=True)
    p.add_argument("--out-summary", required=True)
    p.add_argument("--limit-files", type=int, default=None,
                    help="If given, only the first N files of the portal's current "
                         "list are assigned job indices (pilot use).")
    args = p.parse_args()

    urls = fetch_file_list(TTBAR_RECORD_ID)
    portal_meta = fetch_record_number_events(TTBAR_RECORD_ID)
    if len(urls) != portal_meta["number_files"]:
        print(
            f"WARNING: record {TTBAR_RECORD_ID}: fetch_file_list returned {len(urls)} files but "
            f"the portal's own distribution.number_files says {portal_meta['number_files']} "
            f"-- using the actual fetched list ({len(urls)} files) for job assignment.",
            file=sys.stderr,
        )

    used_urls = urls if args.limit_files is None else urls[:args.limit_files]

    lines = [f"{idx} {TTBAR_RECORD_ID} {file_index}" for idx, file_index in enumerate(range(len(used_urls)), start=1)]
    total_jobs = len(lines)

    Path(args.out_map).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_map).write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary = {
        "total_jobs": total_jobs,
        "record_id": TTBAR_RECORD_ID,
        "n_files_in_fetched_list": len(urls),
        "n_files_used_this_submission": len(used_urls),
        "portal_number_files": portal_meta["number_files"],
        "portal_number_events": portal_meta["number_events"],
        "urls_used": used_urls,
    }
    Path(args.out_summary).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"wrote {args.out_map} ({total_jobs} jobs) and {args.out_summary}")
    print(f"record {TTBAR_RECORD_ID}: {len(urls)} files on the portal, using {len(used_urls)} this submission")


if __name__ == "__main__":
    main()
