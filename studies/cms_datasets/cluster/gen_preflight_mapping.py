#!/usr/bin/env python
"""
Builds the PBS array mapping file for the Step 1 trigger pre-flight scan:
one line per job, each job covering a small contiguous range of files
from one dataset+era record (batching keeps the job count sensible --
732 total files across all 14 records would otherwise mean 732 single-file
jobs).

Reads the actual per-record file counts from record_file_lists.json
(produced by fetch_record_file_lists.py) rather than recomputing them, so
the mapping always matches the portal's real, just-verified file list.

Usage:
    python gen_preflight_mapping.py --file-lists <record_file_lists.json> \
        --batch-size 6 --out <mapping.txt>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file-lists", required=True)
    p.add_argument("--batch-size", type=int, default=6)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    data = json.loads(Path(args.file_lists).read_text())
    records = data["records"]

    lines = []
    idx = 1
    for key in sorted(records.keys()):
        rec = records[key]
        label = rec["dataset_label"]
        era = rec["era"]
        record_id = rec["record_id"]
        n_files = rec["n_files_from_filepage_api"]
        for start in range(0, n_files, args.batch_size):
            end = min(start + args.batch_size, n_files)
            lines.append(f"{idx} {label} {era} {record_id} {start} {end}")
            idx += 1

    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"wrote {len(lines)} job lines to {args.out}")


if __name__ == "__main__":
    main()
