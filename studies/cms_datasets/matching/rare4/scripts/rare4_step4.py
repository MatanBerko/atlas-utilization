"""
rare4 task, Step 4: identity checks on the full production run (209 jobs).

Runs entirely against already-written local sqlite shard files on
Lustre -- no xrootd re-reads. Read-only (mode=ro&immutable=1) against
runs_matched_nonjet4/ (the nonjet4 task's own production baseline,
listed read-only under Hard Rule 3) and the new runs_matched_rare4/
outputs.
"""
import sqlite3
import json
import re
import os
import sys
import time
from collections import Counter

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/rare4_pilot_pinned/repo")
import numpy as np
from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

BASE_NEW = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_rare4"
BASE_OLD = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_nonjet4"
DATASETS = [("DoubleMuon", 57, 94_148_416), ("SingleMuon", 152, 323_952_013)]
FS_LABEL_RE = re.compile(r"^(\d+)e_(\d+)m_(\d+)j_(\d+)g_(\d+)t_(\d+)b$")
FS_SIG_RE = re.compile(r"_FS_(\d+)e_(\d+)m_(\d+)j_(\d+)g_(\d+)t_(\d+)b_IM_")


def read_all_arrays_np(path):
    if not os.path.exists(path):
        return {}
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    cur = con.cursor()
    cur.execute("SELECT signature, payload FROM array_chunks ORDER BY signature, id")
    result = {}
    for sig, payload in cur.fetchall():
        arr = _deserialize_array(payload)
        result.setdefault(sig, []).append(arr)
    con.close()
    return {sig: np.concatenate(chunks) for sig, chunks in result.items()}


def read_capped_keys(path):
    if not os.path.exists(path):
        return []
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    cur = con.cursor()
    cur.execute("SELECT key FROM shard_metadata WHERE key LIKE 'CAPPED::%'")
    rows = [r[0] for r in cur.fetchall()]
    con.close()
    return rows


def arrays_identical(a: np.ndarray, b: np.ndarray) -> bool:
    if a.size != b.size:
        return False
    return np.array_equal(np.sort(np.round(a.astype(np.float64), 5)),
                            np.sort(np.round(b.astype(np.float64), 5)))


t0 = time.time()
total_n_read = {}
git_commits = set()
capped_found = []
identity_fail = []
shards_compared = 0
submultiset_fail = []
check_c_label_gt4_fail = []
check_c_label_le4_diff = []
seen_files = set()
dup_files = []
missing_meta = []
total_rare4_rejected = 0
total_hidden_cases = 0

SHARD_SET_IDENTITY = ["dataset_shard_inclusive.sqlite", "dataset_shard_exclusive.sqlite",
                       "dataset_shard_top4_inclusive.sqlite", "dataset_shard_top4_exclusive.sqlite",
                       "dataset_shard_nonjet4_inclusive.sqlite", "dataset_shard_nonjet4_exclusive.sqlite"]
SHARD_SET_CAPPED = SHARD_SET_IDENTITY + ["dataset_shard_rare4_inclusive.sqlite",
                                          "dataset_shard_rare4_exclusive.sqlite"]

for label, n, expected_n_read_sum in DATASETS:
    n_read_sum = 0
    for i in range(n):
        new_dir = f"{BASE_NEW}/{label}/job_{i}"
        old_dir = f"{BASE_OLD}/{label}/job_{i}"
        new_meta_path = f"{new_dir}/job_metadata.json"
        old_meta_path = f"{old_dir}/job_metadata.json"
        if not os.path.exists(new_meta_path) or not os.path.exists(old_meta_path):
            missing_meta.append((label, i))
            continue
        meta_new = json.load(open(new_meta_path))
        meta_old = json.load(open(old_meta_path))

        key = (meta_new["record_id"], meta_new["file_index"])
        if key in seen_files:
            dup_files.append((label, i, key))
        seen_files.add(key)

        n_read_sum += meta_new["n_read"]
        git_commits.add(meta_new["git_commit"])

        for k in ["record_id", "file_index", "n_read", "n_after_golden_json",
                  "n_after_trigger", "n_after_gate", "n_exclusive"]:
            if meta_new[k] != meta_old[k]:
                identity_fail.append((label, i, f"meta.{k}", meta_old[k], meta_new[k]))
        for k in ["n_accepted_events", "n_accepted_events_gt4_objects",
                  "n_signature_writes_inclusive", "n_signature_writes_exclusive"]:
            if meta_new["top4_diagnostics"][k] != meta_old["top4_diagnostics"][k]:
                identity_fail.append((label, i, f"top4_diagnostics.{k}",
                                       meta_old["top4_diagnostics"][k], meta_new["top4_diagnostics"][k]))
        for k in ["n_accepted_events_before_nonjet4_rule", "n_rejected_gt4_lepton_bjet",
                  "n_kept_le4_lepton_bjet", "n_kept_events_with_light_jets_dropped",
                  "n_signature_writes_inclusive", "n_signature_writes_exclusive"]:
            if meta_new["nonjet4_diagnostics"][k] != meta_old["nonjet4_diagnostics"][k]:
                identity_fail.append((label, i, f"nonjet4_diagnostics.{k}",
                                       meta_old["nonjet4_diagnostics"][k], meta_new["nonjet4_diagnostics"][k]))

        total_rare4_rejected += meta_new["rare4_diagnostics"]["n_rejected_gt4_lepton_bjet"]
        total_hidden_cases += meta_new["rare4_diagnostics"]["n_hidden_cases"]

        for shard in SHARD_SET_IDENTITY:
            old_arr = read_all_arrays_np(f"{old_dir}/{shard}")
            new_arr = read_all_arrays_np(f"{new_dir}/{shard}")
            shards_compared += 1
            if set(old_arr) != set(new_arr):
                identity_fail.append((label, i, shard, "signature set mismatch",
                                       len(set(old_arr) - set(new_arr)), len(set(new_arr) - set(old_arr))))
                continue
            for sig in old_arr:
                if not arrays_identical(old_arr[sig], new_arr[sig]):
                    identity_fail.append((label, i, shard, sig))

        for shard in SHARD_SET_CAPPED:
            keys = read_capped_keys(f"{new_dir}/{shard}")
            if keys:
                capped_found.append((label, i, shard, keys))

        # check (b): rare4 sub-multiset of normal
        normal_incl = read_all_arrays_np(f"{new_dir}/dataset_shard_inclusive.sqlite")
        normal_excl = read_all_arrays_np(f"{new_dir}/dataset_shard_exclusive.sqlite")
        rare4_incl = read_all_arrays_np(f"{new_dir}/dataset_shard_rare4_inclusive.sqlite")
        rare4_excl = read_all_arrays_np(f"{new_dir}/dataset_shard_rare4_exclusive.sqlite")
        for r4_dict, n_dict, which in [(rare4_incl, normal_incl, "incl"), (rare4_excl, normal_excl, "excl")]:
            for sig, vals in r4_dict.items():
                if sig not in n_dict:
                    submultiset_fail.append((label, i, which, sig, "missing in normal"))
                    continue
                c_r4 = Counter(np.round(vals.astype(np.float64), 5).tolist())
                c_n = Counter(np.round(n_dict[sig].astype(np.float64), 5).tolist())
                bad = any(v > c_n.get(k, 0) for k, v in c_r4.items())
                if bad:
                    submultiset_fail.append((label, i, which, sig, "exceeds normal multiplicity"))

        # check (c): label>4 signatures empty in rare4; label<=4 match normal
        # (inclusive shard only; exclusive follows structurally, and is
        # already covered by the sub-multiset check above)
        n_hidden_this_job = meta_new["rare4_diagnostics"]["n_hidden_cases"]
        for sig, normal_vals in normal_incl.items():
            m = FS_SIG_RE.search(sig)
            if not m:
                continue
            e, mm, j, g, t, b = (int(x) for x in m.groups())
            label_sum = e + mm + b
            r4_vals = rare4_incl.get(sig, np.array([]))
            if label_sum > 4:
                if r4_vals.size > 0:
                    check_c_label_gt4_fail.append((label, i, sig, int(r4_vals.size)))
            else:
                c_n = Counter(np.round(normal_vals.astype(np.float64), 5).tolist())
                c_r4 = Counter(np.round(r4_vals.astype(np.float64), 5).tolist())
                if c_n != c_r4 and n_hidden_this_job == 0:
                    check_c_label_le4_diff.append((label, i, sig, len(normal_vals), int(r4_vals.size)))

        if i % 20 == 0:
            print(f"[{time.time()-t0:.0f}s] {label} job_{i} done", flush=True)

    total_n_read[label] = n_read_sum

print()
print("=== missing job_metadata.json ===", missing_meta)
print("=== duplicate files ===", dup_files)
print()
print("=== n_read sums ===")
n_read_all_pass = True
for label, n, expected in DATASETS:
    actual = total_n_read[label]
    ok = (actual == expected)
    n_read_all_pass = n_read_all_pass and ok
    print(f"{label}: sum={actual}, expected={expected}, match={ok}")
print()
expected_commit_full = None
print("=== git commits across all 209 jobs ===", git_commits, "single_commit:", len(git_commits) == 1)
print()
print(f"=== normal+top4+nonjet4 shard identity vs runs_matched_nonjet4/ ({shards_compared} shard files compared) ===")
print("FAILURES:", len(identity_fail))
for x in identity_fail[:30]:
    print(" ", x)
print()
print(f"=== CAPPED:: entries found (should be zero, across {len(SHARD_SET_CAPPED)*sum(n for _,n,_ in DATASETS)} shard files) ===")
print("count:", len(capped_found))
for x in capped_found[:30]:
    print(" ", x)
print()
print("=== check (b): rare4 sub-multiset of normal, full dataset ===")
print("FAILURES:", len(submultiset_fail))
for x in submultiset_fail[:30]:
    print(" ", x)
print()
print("=== check (c): label>4 signatures empty in rare4 ===")
print("FAILURES:", len(check_c_label_gt4_fail))
for x in check_c_label_gt4_fail[:30]:
    print(" ", x)
print()
print("=== check (c): label<=4 signatures differ from normal despite n_hidden_cases=0 in that job ===")
print("FAILURES:", len(check_c_label_le4_diff))
for x in check_c_label_le4_diff[:30]:
    print(" ", x)
print()
print(f"=== Total rare4 rejected events (full dataset): {total_rare4_rejected} (expected 5738, nonjet4's total) "
      f"-> {'PASS' if total_rare4_rejected == 5738 else 'FAIL'} ===")
print(f"=== Total hidden cases (full dataset): {total_hidden_cases} ===")
print()
print(f"total elapsed: {time.time()-t0:.0f}s")

overall = (not missing_meta and not dup_files and n_read_all_pass and len(git_commits) == 1
           and not identity_fail and not capped_found and not submultiset_fail
           and not check_c_label_gt4_fail and not check_c_label_le4_diff
           and total_rare4_rejected == 5738)
print()
print(f"STEP 4 OVERALL: {'PASS' if overall else 'FAIL -- see failures above'}")

out = {
    "missing_meta": missing_meta, "dup_files": dup_files,
    "n_read_sums": total_n_read, "n_read_all_pass": n_read_all_pass,
    "git_commits": list(git_commits),
    "shards_compared": shards_compared, "identity_fail_count": len(identity_fail),
    "capped_found_count": len(capped_found),
    "submultiset_fail_count": len(submultiset_fail),
    "check_c_label_gt4_fail_count": len(check_c_label_gt4_fail),
    "check_c_label_le4_diff_count": len(check_c_label_le4_diff),
    "total_rare4_rejected": total_rare4_rejected,
    "expected_rare4_rejected": 5738,
    "total_hidden_cases": total_hidden_cases,
    "overall_pass": overall,
}
with open(f"{BASE_NEW}/step4_identity_checks.json", "w") as f:
    json.dump(out, f, indent=2)
print("wrote step4_identity_checks.json")
sys.exit(0 if overall else 1)
