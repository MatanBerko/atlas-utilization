#!/usr/bin/env python
"""
Step 3 regression check comparisons.

(i)   --population v0 output must be byte-for-byte identical (per
      signature, order-insensitive) to the existing delivered coverage
      run's own coverage_shard.sqlite (studies/cms_coverage/cluster/
      run_coverage_on_file.py), for the same 3 files. This also directly
      tests upstream master's commit b38f566 ("reordered sqlite_shards.py,
      claimed behaviour-preserving") -- see this study's own PREFLIGHT_REPORT.md.
(ii)  --population generic output, on the SAME 3 files: every final-state
      category the v0 run wrote (which, by construction, always has >=2
      muons and >=1 non-b jet -- that IS what "final state" encodes) must
      appear in generic's inclusive shard with an IDENTICAL array. Also
      reports how many additional signatures/categories generic contains
      beyond v0 (e.g. zero-jet categories the v0 gate excludes entirely).
(iii) DoubleMuon inclusive and exclusive shards must be identical (DoubleMuon
      is the top veto priority, so nothing should ever be vetoed out of it).

Signature names differ between the old script (job_tag =
"record{id}_file{idx}") and the new one (job_tag =
"{label}_record{id}_file{idx}") -- comparison therefore matches on the
"_FS_<final_state>_IM_<combo>" suffix (dataset/job-tag independent), not
the raw signature string.

Usage:
    python compare_regression.py --out <report.json>
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
from studies.cms_datasets.cluster.gen_step3_mapping import REGRESSION_FILES  # noqa: E402

SUFFIX_PATTERN = re.compile(r"(_FS_.*)$")
FS_LABEL_PATTERN = re.compile(r"_FS_(.*)_IM_[^_]+$")

OLD_COVERAGE_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_coverage_full"
NEW_RUN_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/run"


def normalize(sig: str) -> str:
    m = SUFFIX_PATTERN.search(sig)
    return m.group(1) if m else sig


def fs_label_of(normalized_sig: str) -> str:
    m = FS_LABEL_PATTERN.search(normalized_sig)
    return m.group(1) if m else "UNKNOWN"


def _list_signatures_ro(db_path: str) -> list:
    """Read-only equivalent of services.storage.sqlite_shards.list_signatures.

    CORRECTION: `mode=ro` alone is NOT sufficient to guarantee zero writes
    to the directory -- these shards are written with
    `PRAGMA journal_mode=WAL` (SqliteArrayShardWriter.__init__), and
    SQLite's WAL read path creates a `-shm` (and, if absent, a `-wal`)
    companion file next to the DB even for a read-only connection, to
    manage WAL-index consistency. Observed directly: a `mode=ro`-only
    version of this function left empty `-shm`/`-wal` files behind under
    the read-only cms_coverage_full directory (harmless -- the main .sqlite
    file's own bytes were unchanged, confirmed by checksum -- but still a
    write to a directory this task's hard rules mark read-only, and was
    cleaned up by hand). `immutable=1` tells SQLite the file will never
    change while this connection is open, which skips WAL-consistency
    file creation entirely -- the correct flag for this use case (a
    frozen, already-delivered shard that nothing else is writing to)."""
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


def _n_signature_writes_from_metadata(job_dir: str) -> int:
    """The old coverage run's own job_metadata.json 'n_signature_writes'
    field -- the number of writer.append_array(...) CALLS made during that
    job, which can exceed the number of DISTINCT signatures in the shard
    (list_signatures/_list_signatures_ro) when more than one raw
    final-state value collapses onto the same displayed/capped BumpNet
    label (physics_calcs.limit_particles_in_fs) -- both numbers are real,
    they just measure different things. Returns None if the file is
    missing (should not happen for the read-only coverage directory)."""
    meta_path = Path(job_dir) / "job_metadata.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text()).get("n_signature_writes")


def compare_shards(a: dict, b: dict, name_a: str, name_b: str) -> dict:
    keys_a, keys_b = set(a.keys()), set(b.keys())
    only_in_a = sorted(keys_a - keys_b)
    only_in_b = sorted(keys_b - keys_a)
    mismatched = []
    for k in sorted(keys_a & keys_b):
        va, vb = a[k], b[k]
        if va.shape != vb.shape or not np.array_equal(va, vb):
            mismatched.append({
                "signature_suffix": k,
                "n_a": int(va.size), "n_b": int(vb.size),
                "exact_equal": False,
                "allclose_1e-5": bool(va.shape == vb.shape and np.allclose(va, vb, rtol=1e-5, atol=1e-5)),
            })
    return {
        "name_a": name_a, "name_b": name_b,
        "n_signatures_a": len(keys_a), "n_signatures_b": len(keys_b),
        "n_only_in_a": len(only_in_a), "n_only_in_b": len(only_in_b),
        "only_in_a_sample": only_in_a[:10], "only_in_b_sample": only_in_b[:10],
        "n_mismatched_common": len(mismatched),
        "mismatched_sample": mismatched[:10],
        "identical": (len(only_in_a) == 0 and len(only_in_b) == 0 and len(mismatched) == 0),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()

    all_checks = []
    overall_pass = True

    for record_id, file_index, existing_job_dir in REGRESSION_FILES:
        old_path = f"{OLD_COVERAGE_BASE}/{existing_job_dir}/coverage_shard.sqlite"
        v0_incl = f"{NEW_RUN_BASE}/job_DoubleMuon_{record_id}_{file_index}_v0/dataset_shard_inclusive.sqlite"
        v0_excl = f"{NEW_RUN_BASE}/job_DoubleMuon_{record_id}_{file_index}_v0/dataset_shard_exclusive.sqlite"
        gen_incl = f"{NEW_RUN_BASE}/job_DoubleMuon_{record_id}_{file_index}_generic/dataset_shard_inclusive.sqlite"
        gen_excl = f"{NEW_RUN_BASE}/job_DoubleMuon_{record_id}_{file_index}_generic/dataset_shard_exclusive.sqlite"

        old = load_shard(old_path)
        v0i = load_shard(v0_incl)
        v0e = load_shard(v0_excl)
        geni = load_shard(gen_incl)
        gene = load_shard(gen_excl)

        old_job_dir = f"{OLD_COVERAGE_BASE}/{existing_job_dir}"
        old_meta = json.loads((Path(old_job_dir) / "job_metadata.json").read_text())
        new_v0_meta = json.loads(
            (Path(f"{NEW_RUN_BASE}/job_DoubleMuon_{record_id}_{file_index}_v0") / "job_metadata.json").read_text()
        )
        event_count_check = {
            "old_n_read": old_meta.get("n_read"),
            "new_v0_n_read": new_v0_meta.get("n_read"),
            "old_n_after_v0_selection": old_meta.get("n_after_v0_selection"),
            "new_v0_n_after_gate": new_v0_meta.get("n_after_gate"),
            "n_read_matches": old_meta.get("n_read") == new_v0_meta.get("n_read"),
            "n_selected_events_matches": old_meta.get("n_after_v0_selection") == new_v0_meta.get("n_after_gate"),
            "old_n_signature_writes": old_meta.get("n_signature_writes"),
            "old_n_distinct_signatures_in_shard": len(old),
            "new_v0_n_distinct_signatures_in_shard": len(v0i),
            "note": (
                "old_n_signature_writes counts every writer.append_array(...) call made "
                "during the old job (job_metadata.json's own field); it can exceed the "
                "number of DISTINCT signatures actually in the shard "
                "(old_n_distinct_signatures_in_shard) when more than one raw final-state "
                "value collapses onto the same capped/displayed BumpNet label "
                "(physics_calcs.limit_particles_in_fs) -- both are real numbers from the "
                "same job, they measure different things, and neither is 'wrong'."
            ),
        }

        check_i = compare_shards(old, v0i, "old_coverage_shard", "new_v0_inclusive")
        check_iii_v0 = compare_shards(v0i, v0e, "new_v0_inclusive", "new_v0_exclusive")
        check_iii_generic = compare_shards(geni, gene, "new_generic_inclusive", "new_generic_exclusive")

        # (ii): every v0 signature must appear identically in generic's inclusive shard.
        keys_v0 = set(v0i.keys())
        keys_gen = set(geni.keys())
        missing_from_generic = sorted(keys_v0 - keys_gen)
        mismatched_ii = []
        for k in sorted(keys_v0 & keys_gen):
            if v0i[k].shape != geni[k].shape or not np.array_equal(v0i[k], geni[k]):
                mismatched_ii.append(k)
        extra_in_generic = sorted(keys_gen - keys_v0)
        extra_fs_labels = sorted({fs_label_of(k) for k in extra_in_generic})
        v0_fs_labels = sorted({fs_label_of(k) for k in keys_v0})

        check_ii = {
            "n_v0_signatures": len(keys_v0),
            "n_generic_signatures": len(keys_gen),
            "n_v0_missing_from_generic": len(missing_from_generic),
            "missing_sample": missing_from_generic[:10],
            "n_mismatched": len(mismatched_ii),
            "mismatched_sample": mismatched_ii[:10],
            "n_extra_signatures_in_generic": len(extra_in_generic),
            "n_extra_final_state_labels_in_generic": len(extra_fs_labels),
            "extra_final_state_labels_sample": extra_fs_labels[:20],
            "n_v0_final_state_labels": len(v0_fs_labels),
            "passes": (len(missing_from_generic) == 0 and len(mismatched_ii) == 0),
        }

        file_result = {
            "record_id": record_id,
            "file_index": file_index,
            "event_count_check": event_count_check,
            "check_i_v0_matches_old_coverage": check_i,
            "check_ii_generic_superset_of_v0": check_ii,
            "check_iii_doublemuon_inclusive_eq_exclusive_v0": check_iii_v0,
            "check_iii_doublemuon_inclusive_eq_exclusive_generic": check_iii_generic,
        }
        this_pass = (
            check_i["identical"] and check_ii["passes"]
            and check_iii_v0["identical"] and check_iii_generic["identical"]
            and event_count_check["n_read_matches"] and event_count_check["n_selected_events_matches"]
        )
        file_result["all_checks_pass"] = this_pass
        overall_pass = overall_pass and this_pass
        all_checks.append(file_result)

        print(f"record {record_id} file {file_index}: "
              f"check_i={'PASS' if check_i['identical'] else 'FAIL'} "
              f"check_ii={'PASS' if check_ii['passes'] else 'FAIL'} "
              f"check_iii_v0={'PASS' if check_iii_v0['identical'] else 'FAIL'} "
              f"check_iii_generic={'PASS' if check_iii_generic['identical'] else 'FAIL'}",
              flush=True)

    result = {"overall_pass": overall_pass, "per_file": all_checks}
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")
    print(f"wrote {args.out}")
    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
