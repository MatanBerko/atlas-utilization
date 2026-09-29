"""
Top-4 task, Step 2 check (a) HARD: the normal matched inclusive/exclusive
shards and per-stage counts from the new pinned commit (db2f5c0) are
identical to those already validated in matching_validation/ (commit
cbd1abb). Read-only (mode=ro&immutable=1) against matching_validation/,
per this task's own Hard Rule 3 (it is explicitly listed as read-only now).
"""
import sqlite3
import sys
import json
from collections import Counter

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/top4_pilot_pinned/repo")
from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

OLD_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/matching_validation"
NEW_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/top4_pilot"

RUNS = [
    "DoubleMuon_30522_0_matched",
    "DoubleMuon_30555_0_matched",
    "SingleMuon_30530_0_matched",
    "SingleMuon_30563_0_matched",
]


def read_all_arrays(sqlite_path):
    con = sqlite3.connect(f"file:{sqlite_path}?mode=ro&immutable=1", uri=True)
    cur = con.cursor()
    cur.execute("SELECT signature, payload FROM array_chunks")
    result = {}
    for signature, payload in cur.fetchall():
        if signature.startswith("CAPPED::"):
            continue
        arr = _deserialize_array(payload)
        result.setdefault(signature, []).extend(arr.tolist())
    con.close()
    return result


def compare_identical(old_path, new_path, label):
    old = read_all_arrays(old_path)
    new = read_all_arrays(new_path)
    old_names, new_names = set(old.keys()), set(new.keys())
    if old_names != new_names:
        print(f"[{label}] FAIL: signature sets differ. only_old={len(old_names-new_names)} only_new={len(new_names-old_names)}")
        return False
    all_ok = True
    for name in sorted(old_names):
        c_old = Counter(round(v, 5) for v in old[name])
        c_new = Counter(round(v, 5) for v in new[name])
        if c_old != c_new:
            print(f"[{label}] FAIL signature {name}: old_n={len(old[name])} new_n={len(new[name])} differs")
            all_ok = False
    if all_ok:
        print(f"[{label}] PASS: {len(old_names)} signatures byte-for-byte identical")
    return all_ok


all_pass = True
for run in RUNS:
    for shard in ["dataset_shard_inclusive.sqlite", "dataset_shard_exclusive.sqlite"]:
        ok = compare_identical(f"{OLD_BASE}/{run}/{shard}", f"{NEW_BASE}/{run}/{shard}", f"{run}/{shard}")
        all_pass = all_pass and ok

    old_meta = json.load(open(f"{OLD_BASE}/{run}/job_metadata.json"))
    new_meta = json.load(open(f"{NEW_BASE}/{run}/job_metadata.json"))
    for key in ["n_read", "n_after_golden_json", "n_after_trigger", "n_after_gate", "n_exclusive",
                "n_signature_writes_inclusive", "n_signature_writes_exclusive",
                "n_values_written_inclusive", "n_values_written_exclusive"]:
        if old_meta[key] != new_meta[key]:
            print(f"[{run}] FAIL per-stage count {key}: old={old_meta[key]} new={new_meta[key]}")
            all_pass = False
    print(f"[{run}] per-stage counts: {'PASS (all match)' if old_meta['n_read']==new_meta['n_read'] else '...'}")

print()
print(f"OVERALL check (a): {'PASS' if all_pass else 'FAIL'}")
sys.exit(0 if all_pass else 1)
