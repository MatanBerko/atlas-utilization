#!/usr/bin/env python
"""
Step 3 regression check: builds the small, fixed PBS mapping file for the
3 DoubleMuon files also processed by the existing delivered coverage run
(studies/cms_coverage/cluster/run_coverage_on_file.py,
/storage/agrp/berkom/atlas-utilization/output/cms_coverage_full/, read-only).

The 3 files (found by reading that directory's own job_metadata.json files,
read-only, nothing written there) are record 30522 (Run2016G) file indices
0 and 1, and record 30555 (Run2016H) file index 0 -- i.e. at least one G
and one H file, per this task's own requirement. Their existing coverage
shards are at cms_coverage_full/job_1, job_2, job_30 respectively
(confirmed directly: job_1 -> record 30522 file 0, job_2 -> record 30522
file 1, job_30 -> record 30555 file 0).

Each file is run twice with the new generalized driver
(run_dataset_on_file.py): once with --population v0 (byte-for-byte
regression target: the existing coverage_shard.sqlite), once with
--population generic (superset check).

Usage:
    python gen_step3_mapping.py --out <mapping.txt>
"""
from __future__ import annotations

import argparse
from pathlib import Path

# (record_id, file_index, existing_coverage_job_dir_name) -- found by
# reading cms_coverage_full/job_*/job_metadata.json (read-only).
REGRESSION_FILES = [
    (30522, 0, "job_1"),   # Run2016G
    (30522, 1, "job_2"),   # Run2016G
    (30555, 0, "job_30"),  # Run2016H
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()

    lines = []
    idx = 1
    for record_id, file_index, _existing_job_dir in REGRESSION_FILES:
        for population in ("v0", "generic"):
            lines.append(f"{idx} DoubleMuon {record_id} {file_index} {population}")
            idx += 1

    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"wrote {len(lines)} job lines to {args.out}")
    for line in lines:
        print(" ", line)


if __name__ == "__main__":
    main()
