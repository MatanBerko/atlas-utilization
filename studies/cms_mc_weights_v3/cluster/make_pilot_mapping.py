#!/usr/bin/env python
"""
Pilot: write the PBS mapping file for one sample (or for a named subset of its
files, which is what a resubmit of failed files needs).

Mapping format, 3 space-separated columns:
    <array_index> <record_id> <file_index>

`array_index` is 1-based and contiguous, because PBS array indices are, and
the job script asserts the line it reads carries its own index.

Run:
    # the full file set of one record
    python studies/cms_mc_weights_v3/cluster/make_pilot_mapping.py \
        --record 35669 --out <work>/mapping_35669.txt

    # just the largest file, for the Part 1b timing job
    python ... --record 35669 --file-indices 12 --out <work>/mapping_timing.txt

    # a resubmit of the files that failed
    python ... --record 67801 --file-indices 3,17,40 --out <work>/mapping_67801_retry.txt
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_mc_weights_v3.cluster.measure_pilot_inputs import PILOT_RECORDS  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--file-indices", default=None,
                    help="comma-separated file indices (default: every file of "
                         "the record)")
    ap.add_argument("--inputs-json", default=None,
                    help="measure_pilot_inputs.py output; when given, the file "
                         "count is checked against it instead of re-querying "
                         "the portal")
    args = ap.parse_args()

    rid = str(args.record)
    if rid not in PILOT_RECORDS:
        raise SystemExit(
            f"record {rid} is not a pilot record; the pilot is "
            f"{sorted(PILOT_RECORDS)} only.")

    if args.inputs_json:
        inputs = json.loads(pathlib.Path(args.inputs_json).read_text(encoding="utf-8"))
        n_files = inputs["records"][rid]["n_files"]
    else:
        n_files = len(fetch_file_list(int(rid)))
    expected = PILOT_RECORDS[rid]["expected_files"]
    if n_files != expected:
        raise SystemExit(
            f"STOP: record {rid} has {n_files} files, the pilot expects {expected}.")

    if args.file_indices:
        indices = [int(x) for x in args.file_indices.split(",") if x.strip()]
        bad = [i for i in indices if i < 0 or i >= n_files]
        if bad:
            raise SystemExit(
                f"file index/indices {bad} out of range for record {rid} "
                f"({n_files} files)")
    else:
        indices = list(range(n_files))

    rows = [f"{i + 1} {rid} {fi}" for i, fi in enumerate(indices)]
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")

    print(f"record {rid} ({PILOT_RECORDS[rid]['physics_short']}): "
          f"{len(rows)} job(s) of {n_files} file(s)")
    print(f"  array range: 1-{len(rows)}")
    print(f"  file indices: {indices if len(indices) <= 20 else str(indices[:20]) + ' ...'}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
