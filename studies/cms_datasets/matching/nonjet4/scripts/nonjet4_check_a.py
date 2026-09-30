"""
nonjet4 task, Step 2 check (a) HARD: the NORMAL and TOP-4 matched
inclusive/exclusive shards and per-stage counts written by the new
nonjet4_pilot run (pinned commit 3a184b7) are identical to the
already-delivered production shards in runs_matched/ (commit 521c31e,
read-only per Hard Rule 3). This proves Step 1's addition changed
NOTHING about the normal/top-4 code paths (Hard Rule 5).
"""
import sqlite3
import sys
import json
from collections import Counter

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/nonjet4_pilot_pinned/repo")
from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

OLD_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched"
NEW_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/nonjet4_pilot"

# (nonjet4_pilot run dir name, runs_matched dataset dir, runs_matched job index)
RUNS = [
    ("DoubleMuon_30522_0_matched", "DoubleMuon", 0),
    ("DoubleMuon_30555_0_matched", "DoubleMuon", 29),
    ("SingleMuon_30530_0_matched", "SingleMuon", 0),
    ("SingleMuon_30563_0_matched", "SingleMuon", 70),
]

SHARD_PAIRS = [
    ("dataset_shard_inclusive.sqlite", "dataset_shard_inclusive.sqlite"),
    ("dataset_shard_exclusive.sqlite", "dataset_shard_exclusive.sqlite"),
    ("dataset_shard_top4_inclusive.sqlite", "dataset_shard_top4_inclusive.sqlite"),
    ("dataset_shard_top4_exclusive.sqlite", "dataset_shard_top4_exclusive.sqlite"),
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
for new_run, old_label, old_job in RUNS:
    old_dir = f"{OLD_BASE}/{old_label}/job_{old_job}"
    new_dir = f"{NEW_BASE}/{new_run}"
    for old_shard, new_shard in SHARD_PAIRS:
        ok = compare_identical(f"{old_dir}/{old_shard}", f"{new_dir}/{new_shard}", f"{new_run}/{new_shard}")
        all_pass = all_pass and ok

    old_meta = json.load(open(f"{old_dir}/job_metadata.json"))
    new_meta = json.load(open(f"{new_dir}/job_metadata.json"))
    keys_ok = True
    for key in ["n_read", "n_after_golden_json", "n_after_trigger", "n_after_gate", "n_exclusive",
                "n_signature_writes_inclusive", "n_signature_writes_exclusive",
                "n_values_written_inclusive", "n_values_written_exclusive"]:
        if old_meta[key] != new_meta[key]:
            print(f"[{new_run}] FAIL per-stage count {key}: old={old_meta[key]} new={new_meta[key]}")
            all_pass = False
            keys_ok = False
    for key in ["n_accepted_events", "n_accepted_events_gt4_objects",
                "n_signature_writes_inclusive", "n_signature_writes_exclusive",
                "n_values_written_inclusive", "n_values_written_exclusive"]:
        old_v = old_meta["top4_diagnostics"][key]
        new_v = new_meta["top4_diagnostics"][key]
        if old_v != new_v:
            print(f"[{new_run}] FAIL top4_diagnostics.{key}: old={old_v} new={new_v}")
            all_pass = False
            keys_ok = False
    print(f"[{new_run}] per-stage + top4_diagnostics counts: {'PASS (all match)' if keys_ok else 'FAIL (see above)'}")

print()
print(f"OVERALL check (a): {'PASS' if all_pass else 'FAIL'}")
sys.exit(0 if all_pass else 1)
