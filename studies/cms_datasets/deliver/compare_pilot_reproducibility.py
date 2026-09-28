#!/usr/bin/env python
"""
Step 2(b) pilot-reproducibility check, dataset-parameterized (built on the
same normalize/compare_shards approach as
studies/cms_datasets/cluster/compare_regression.py, reimplemented here
rather than imported since that script is hardcoded to the DoubleMuon
regression-file list).

For each given (record_id, file_index) pair that the pilot task also
processed, compares the FULL RUN's own inclusive and exclusive shards
against the PILOT's own shards (both are this study's own outputs, but
the pilot's are read-only per this task's hard rules) -- same
signatures, identical arrays -- and cross-checks the per-stage event
counts (n_after_gate, n_exclusive) from each side's own job_metadata.json.

The pilot ran an earlier commit that (per this task's own brief) differed
from the full run's commit ONLY in diagnostics fields -- any shard-level
difference found here is therefore a real problem to report, not
something to silently reconcile.

All SQLite reads use `mode=ro&immutable=1` (both the pilot's shards and
this run's own full-run shards, for consistency), per this task's
hard-rule update on read-only cluster paths.

Usage:
    python compare_pilot_reproducibility.py --dataset-label DoubleEG \
        --pilot-dir /storage/.../output/cms_datasets/run \
        --full-run-dir /storage/.../output/cms_datasets/runs/DoubleEG \
        --pilot-pairs 30521:0,30554:0 \
        --out <report.json>
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

SUFFIX_PATTERN = re.compile(r"(_FS_.*)$")


def normalize(sig: str) -> str:
    m = SUFFIX_PATTERN.search(sig)
    return m.group(1) if m else sig


def _list_signatures_ro(db_path: str) -> list:
    uri = f"file:{db_path}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute("SELECT DISTINCT signature FROM array_chunks ORDER BY signature").fetchall()
    return [r[0] for r in rows]


def _iter_arrays_for_signature_ro(db_path: str, signature: str):
    uri = f"file:{db_path}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute(
            "SELECT payload FROM array_chunks WHERE signature = ?", (signature,)
        ).fetchall()
    for (payload,) in rows:
        yield _deserialize_array(payload)


def load_shard(path: str) -> dict:
    if not Path(path).exists():
        raise FileNotFoundError(path)
    out = {}
    for sig in _list_signatures_ro(path):
        arrs = list(_iter_arrays_for_signature_ro(path, sig))
        combined = np.concatenate(arrs) if arrs else np.array([], dtype=np.float32)
        out[normalize(sig)] = np.sort(combined)
    return out


def compare_shards(a: dict, b: dict, name_a: str, name_b: str) -> dict:
    keys_a, keys_b = set(a.keys()), set(b.keys())
    only_in_a = sorted(keys_a - keys_b)
    only_in_b = sorted(keys_b - keys_a)
    mismatched = []
    for k in sorted(keys_a & keys_b):
        va, vb = a[k], b[k]
        if va.shape != vb.shape or not np.array_equal(va, vb):
            mismatched.append({"signature_suffix": k, "n_a": int(va.size), "n_b": int(vb.size)})
    return {
        "name_a": name_a, "name_b": name_b,
        "n_signatures_a": len(keys_a), "n_signatures_b": len(keys_b),
        "n_only_in_a": len(only_in_a), "n_only_in_b": len(only_in_b),
        "only_in_a_sample": only_in_a[:10], "only_in_b_sample": only_in_b[:10],
        "n_mismatched_common": len(mismatched),
        "mismatched_sample": mismatched[:10],
        "identical": (len(only_in_a) == 0 and len(only_in_b) == 0 and len(mismatched) == 0),
    }


def find_full_run_job_dir(full_run_dir: Path, record_id: int, file_index: int) -> Path:
    for job_dir in sorted(full_run_dir.glob("job_*"), key=lambda p: int(p.name.split("_")[1])):
        meta_path = job_dir / "job_metadata.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        if meta["record_id"] == record_id and meta["file_index"] == file_index:
            return job_dir
    raise RuntimeError(f"no full-run job found for record={record_id} file_index={file_index}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-label", required=True)
    p.add_argument("--pilot-dir", required=True)
    p.add_argument("--full-run-dir", required=True)
    p.add_argument("--pilot-pairs", required=True, help="comma-separated record:file_index, e.g. 30521:0,30554:0")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    pilot_dir = Path(args.pilot_dir)
    full_run_dir = Path(args.full_run_dir)
    pairs = []
    for token in args.pilot_pairs.split(","):
        record_str, idx_str = token.split(":")
        pairs.append((int(record_str), int(idx_str)))

    all_results = []
    overall_pass = True
    for record_id, file_index in pairs:
        pilot_job_dir = pilot_dir / f"job_{args.dataset_label}_{record_id}_{file_index}_generic"
        full_job_dir = find_full_run_job_dir(full_run_dir, record_id, file_index)

        pilot_meta = json.loads((pilot_job_dir / "job_metadata.json").read_text())
        full_meta = json.loads((full_job_dir / "job_metadata.json").read_text())

        event_count_check = {
            "pilot_n_read": pilot_meta["n_read"], "full_n_read": full_meta["n_read"],
            "pilot_n_after_gate": pilot_meta["n_after_gate"], "full_n_after_gate": full_meta["n_after_gate"],
            "pilot_n_exclusive": pilot_meta["n_exclusive"], "full_n_exclusive": full_meta["n_exclusive"],
            "n_read_matches": pilot_meta["n_read"] == full_meta["n_read"],
            "n_after_gate_matches": pilot_meta["n_after_gate"] == full_meta["n_after_gate"],
            "n_exclusive_matches": pilot_meta["n_exclusive"] == full_meta["n_exclusive"],
            "pilot_git_commit": pilot_meta["git_commit"], "full_git_commit": full_meta["git_commit"],
        }

        incl_check = compare_shards(
            load_shard(str(pilot_job_dir / "dataset_shard_inclusive.sqlite")),
            load_shard(str(full_job_dir / "dataset_shard_inclusive.sqlite")),
            "pilot_inclusive", "full_run_inclusive",
        )
        excl_check = compare_shards(
            load_shard(str(pilot_job_dir / "dataset_shard_exclusive.sqlite")),
            load_shard(str(full_job_dir / "dataset_shard_exclusive.sqlite")),
            "pilot_exclusive", "full_run_exclusive",
        )

        this_pass = (
            event_count_check["n_read_matches"] and event_count_check["n_after_gate_matches"]
            and event_count_check["n_exclusive_matches"] and incl_check["identical"] and excl_check["identical"]
        )
        overall_pass = overall_pass and this_pass
        result = {
            "record_id": record_id, "file_index": file_index,
            "full_run_job_dir": full_job_dir.name,
            "event_count_check": event_count_check,
            "inclusive_shard_check": incl_check,
            "exclusive_shard_check": excl_check,
            "all_checks_pass": this_pass,
        }
        all_results.append(result)
        print(f"record {record_id} file {file_index} ({full_job_dir.name}): "
              f"events={'PASS' if event_count_check['n_after_gate_matches'] and event_count_check['n_exclusive_matches'] else 'FAIL'} "
              f"inclusive_shard={'PASS' if incl_check['identical'] else 'FAIL'} "
              f"exclusive_shard={'PASS' if excl_check['identical'] else 'FAIL'}")

    out = {"dataset_label": args.dataset_label, "overall_pass": overall_pass, "per_file": all_results}
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")
    print(f"wrote {args.out}")
    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
