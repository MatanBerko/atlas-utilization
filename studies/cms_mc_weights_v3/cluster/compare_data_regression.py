#!/usr/bin/env python
"""
Part B: prove the real-data output is unchanged by the v3 implementation.

Compares, per data file, the freshly re-run output (from the pinned v3 commit,
WITHOUT --is-mc) against the EXISTING delivered four-dataset production output,
which is opened READ-ONLY and never modified.

For every one of the eight shard files a job writes
(normal / top4 / nonjet4 / rare4, each inclusive and exclusive) it compares:

  * the set of signatures;
  * every signature's concatenated array -- exact dtype, exact length, exact
    values, bit-for-bit (`np.array_equal` on the raw arrays, no tolerance);
  * the `final_state_counts` table, as a multiset of (final_state, n_events);
  * every `shard_metadata` key and value.

and for `job_metadata.json`, every key except the ones that legitimately
differ between two runs of the same code (listed explicitly below).

Byte-identical FILES are reported when they occur but are not required:
SQLite page layout and WAL state can differ between two runs that store
identical content.

Any content difference is reported and makes the script exit non-zero.

Read-only with respect to everything under output/: it opens the delivered
shards with SQLite in immutable mode so it cannot write to them even by
accident.

Run:
    python studies/cms_mc_weights_v3/cluster/compare_data_regression.py \
        --old-runs-dir /storage/.../output/cms_datasets/runs_matched4_full_20261007 \
        --new-runs-dir /storage/.../work/cms_mc_v3_impl_<date>/data_regression \
        --out /storage/.../work/cms_mc_v3_impl_<date>/evidence/data_regression.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sqlite3
import sys
from collections import Counter

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

SHARD_FILES = (
    "dataset_shard_inclusive.sqlite",
    "dataset_shard_exclusive.sqlite",
    "dataset_shard_top4_inclusive.sqlite",
    "dataset_shard_top4_exclusive.sqlite",
    "dataset_shard_nonjet4_inclusive.sqlite",
    "dataset_shard_nonjet4_exclusive.sqlite",
    "dataset_shard_rare4_inclusive.sqlite",
    "dataset_shard_rare4_exclusive.sqlite",
)

# Keys in job_metadata.json that legitimately differ between two runs of the
# same code on the same input. Everything else must match exactly.
METADATA_KEYS_ALLOWED_TO_DIFFER = (
    "created_utc",              # wall-clock time of the run
    "git_commit",               # the point of the exercise: a different commit
    "elapsed_sec",              # wall-clock duration
    "inclusive_shard_size_mb",  # SQLite page layout, not content
    "exclusive_shard_size_mb",  # idem
)


def read_shard(path: pathlib.Path) -> dict:
    """Signatures, arrays, final-state counts and metadata of one shard.

    Opened `mode=ro` + `immutable=1`: the delivered production shards are
    read-only and this makes that a property of the connection, not a promise.
    """
    uri = f"file:{path.as_posix()}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = conn.execute(
            "SELECT signature, payload FROM array_chunks ORDER BY id").fetchall()
        arrays: dict[str, list] = {}
        for signature, payload in rows:
            arrays.setdefault(signature, []).append(_deserialize_array(payload))
        fs_counts = conn.execute(
            "SELECT final_state, n_events FROM final_state_counts").fetchall()
        meta = dict(conn.execute("SELECT key, value FROM shard_metadata").fetchall())
    finally:
        conn.close()
    return {
        "arrays": {s: (np.concatenate(cs) if len(cs) > 1 else cs[0])
                   for s, cs in arrays.items()},
        "n_chunks_by_signature": {s: len(cs) for s, cs in arrays.items()},
        "final_state_counts": Counter((str(fs), int(n)) for fs, n in fs_counts),
        "metadata": meta,
    }


def compare_shard(old_path: pathlib.Path, new_path: pathlib.Path) -> dict:
    old, new = read_shard(old_path), read_shard(new_path)
    diffs = []

    old_sigs, new_sigs = set(old["arrays"]), set(new["arrays"])
    if old_sigs != new_sigs:
        only_old, only_new = sorted(old_sigs - new_sigs), sorted(new_sigs - old_sigs)
        diffs.append({
            "kind": "signature_set",
            "n_only_in_old": len(only_old), "n_only_in_new": len(only_new),
            "only_in_old_sample": only_old[:10], "only_in_new_sample": only_new[:10],
        })

    n_arrays_equal = 0
    for sig in sorted(old_sigs & new_sigs):
        a, b = old["arrays"][sig], new["arrays"][sig]
        if a.dtype != b.dtype:
            diffs.append({"kind": "dtype", "signature": sig,
                          "old": str(a.dtype), "new": str(b.dtype)})
            continue
        if a.shape != b.shape:
            diffs.append({"kind": "length", "signature": sig,
                          "old": int(a.size), "new": int(b.size)})
            continue
        if not np.array_equal(a, b):
            n_diff = int(np.count_nonzero(a != b))
            diffs.append({"kind": "values", "signature": sig, "n_entries": int(a.size),
                          "n_differing_entries": n_diff,
                          "max_abs_diff": float(np.max(np.abs(
                              a.astype(np.float64) - b.astype(np.float64))))})
            continue
        n_arrays_equal += 1

    if old["final_state_counts"] != new["final_state_counts"]:
        only_old = old["final_state_counts"] - new["final_state_counts"]
        only_new = new["final_state_counts"] - old["final_state_counts"]
        diffs.append({"kind": "final_state_counts",
                      "only_in_old": sorted(only_old.elements())[:10],
                      "only_in_new": sorted(only_new.elements())[:10]})

    old_meta, new_meta = old["metadata"], new["metadata"]
    if set(old_meta) != set(new_meta):
        diffs.append({"kind": "metadata_keys",
                      "only_in_old": sorted(set(old_meta) - set(new_meta)),
                      "only_in_new": sorted(set(new_meta) - set(old_meta))})
    for key in sorted(set(old_meta) & set(new_meta)):
        if old_meta[key] != new_meta[key]:
            diffs.append({"kind": "metadata_value", "key": key,
                          "old": old_meta[key], "new": new_meta[key]})

    return {
        "shard": old_path.name,
        "n_signatures": len(old_sigs),
        "n_arrays_compared_equal": n_arrays_equal,
        "n_total_entries": int(sum(a.size for a in old["arrays"].values())),
        "n_final_state_count_rows": int(sum(old["final_state_counts"].values())),
        "n_metadata_keys": len(old_meta),
        "files_byte_identical": (
            hashlib.sha256(old_path.read_bytes()).hexdigest()
            == hashlib.sha256(new_path.read_bytes()).hexdigest()),
        "n_differences": len(diffs),
        "differences": diffs,
    }


def compare_job_metadata(old_path: pathlib.Path, new_path: pathlib.Path) -> dict:
    old = json.loads(old_path.read_text(encoding="utf-8"))
    new = json.loads(new_path.read_text(encoding="utf-8"))
    diffs = []
    if set(old) != set(new):
        diffs.append({"kind": "keys",
                      "only_in_old": sorted(set(old) - set(new)),
                      "only_in_new": sorted(set(new) - set(old))})
    compared = 0
    for key in sorted(set(old) & set(new)):
        if key in METADATA_KEYS_ALLOWED_TO_DIFFER:
            continue
        compared += 1
        if old[key] != new[key]:
            diffs.append({"kind": "value", "key": key,
                          "old": str(old[key])[:300], "new": str(new[key])[:300]})
    return {
        "n_keys_compared": compared,
        "keys_excluded": list(METADATA_KEYS_ALLOWED_TO_DIFFER),
        "excluded_values": {
            k: {"old": old.get(k), "new": new.get(k)}
            for k in METADATA_KEYS_ALLOWED_TO_DIFFER if k in old or k in new
        },
        "n_differences": len(diffs),
        "differences": diffs,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-runs-dir", required=True,
                    help="the DELIVERED production runs dir (read-only)")
    ap.add_argument("--new-runs-dir", required=True,
                    help="this round's re-run output")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    old_root = pathlib.Path(args.old_runs_dir)
    new_root = pathlib.Path(args.new_runs_dir)
    report = {
        "what": "Part B: data-path regression of the v3 implementation against "
                "the delivered four-dataset production",
        "old_runs_dir": str(old_root),
        "new_runs_dir": str(new_root),
        "old_opened": "SQLite mode=ro&immutable=1 -- the delivered shards cannot "
                      "be written to by this script",
        "shard_files_compared_per_job": list(SHARD_FILES),
        "metadata_keys_allowed_to_differ": list(METADATA_KEYS_ALLOWED_TO_DIFFER),
        "jobs": {},
    }

    total_diffs = 0
    totals = {"n_shards": 0, "n_signatures": 0, "n_entries": 0,
              "n_arrays_equal": 0, "n_byte_identical_files": 0}
    for new_meta_path in sorted(new_root.rglob("job_metadata.json")):
        new_job = new_meta_path.parent
        dataset = new_job.parent.name
        job_name = new_job.name
        old_job = old_root / dataset / job_name
        key = f"{dataset}/{job_name}"
        if not old_job.exists():
            report["jobs"][key] = {"error": f"no delivered counterpart at {old_job}"}
            total_diffs += 1
            continue

        entry = {"old_job_dir": str(old_job), "new_job_dir": str(new_job), "shards": {}}
        for shard_name in SHARD_FILES:
            o, n = old_job / shard_name, new_job / shard_name
            if not o.exists() or not n.exists():
                entry["shards"][shard_name] = {
                    "error": f"missing (old exists={o.exists()}, new exists={n.exists()})"}
                total_diffs += 1
                continue
            res = compare_shard(o, n)
            entry["shards"][shard_name] = res
            total_diffs += res["n_differences"]
            totals["n_shards"] += 1
            totals["n_signatures"] += res["n_signatures"]
            totals["n_entries"] += res["n_total_entries"]
            totals["n_arrays_equal"] += res["n_arrays_compared_equal"]
            totals["n_byte_identical_files"] += int(res["files_byte_identical"])
        entry["job_metadata"] = compare_job_metadata(
            old_job / "job_metadata.json", new_meta_path)
        total_diffs += entry["job_metadata"]["n_differences"]
        report["jobs"][key] = entry
        print(f"{key:28s} shards={len(SHARD_FILES)} "
              f"diffs={sum(s.get('n_differences', 1) for s in entry['shards'].values()) + entry['job_metadata']['n_differences']}",
              flush=True)

    report["totals"] = totals
    report["n_jobs_compared"] = len(report["jobs"])
    report["total_differences"] = total_diffs
    report["VERDICT"] = ("IDENTICAL -- the data path is unchanged"
                         if total_diffs == 0 else
                         f"DIFFERENT -- {total_diffs} difference(s); STOP")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"\njobs compared:         {report['n_jobs_compared']}")
    print(f"shards compared:       {totals['n_shards']}")
    print(f"signatures compared:   {totals['n_signatures']:,}")
    print(f"array entries compared:{totals['n_entries']:,}")
    print(f"arrays bit-identical:  {totals['n_arrays_equal']:,}")
    print(f"files byte-identical:  {totals['n_byte_identical_files']} of {totals['n_shards']}")
    print(f"\nVERDICT: {report['VERDICT']}")
    print(f"wrote {out}")
    return 0 if total_diffs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
