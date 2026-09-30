"""
nonjet4 task, Step 4: identity checks on the full production run (209 jobs).

Runs entirely against already-written local (Lustre) sqlite shard files --
no xrootd re-reads. Read-only (mode=ro&immutable=1) against runs_matched/
(the top-4 task's own production baseline, listed read-only under Hard
Rule 3) and the new runs_matched_nonjet4/ outputs.
"""
import sqlite3
import json
import re
import os
import sys
import time
from collections import Counter

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/nonjet4_pilot_pinned/repo")
import numpy as np
from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

BASE_NEW = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_nonjet4"
BASE_OLD = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched"
DATASETS = [("DoubleMuon", 57, 94_148_416), ("SingleMuon", 152, 323_952_013)]
EXPECTED_COMMIT_PREFIX = "3c7c9c9"
FS_LABEL_RE = re.compile(r"^(\d+)e_(\d+)m_(\d+)j_(\d+)g_(\d+)t_(\d+)b$")


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


def read_final_state_counts(path):
    if not os.path.exists(path):
        return {}
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    cur = con.cursor()
    cur.execute("SELECT final_state, SUM(n_events) FROM final_state_counts GROUP BY final_state")
    d = dict(cur.fetchall())
    con.close()
    return d


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
check_c_incl_fail = []
check_d_rows = []
seen_files = set()
dup_files = []
missing_meta = []

SHARD_SET_IDENTITY = ["dataset_shard_inclusive.sqlite", "dataset_shard_exclusive.sqlite",
                       "dataset_shard_top4_inclusive.sqlite", "dataset_shard_top4_exclusive.sqlite"]
SHARD_SET_CAPPED = SHARD_SET_IDENTITY + ["dataset_shard_nonjet4_inclusive.sqlite",
                                          "dataset_shard_nonjet4_exclusive.sqlite"]

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

        top4_incl = read_all_arrays_np(f"{new_dir}/dataset_shard_top4_inclusive.sqlite")
        top4_excl = read_all_arrays_np(f"{new_dir}/dataset_shard_top4_exclusive.sqlite")
        nj4_incl = read_all_arrays_np(f"{new_dir}/dataset_shard_nonjet4_inclusive.sqlite")
        nj4_excl = read_all_arrays_np(f"{new_dir}/dataset_shard_nonjet4_exclusive.sqlite")
        for nj4_dict, t4_dict, which in [(nj4_incl, top4_incl, "incl"), (nj4_excl, top4_excl, "excl")]:
            for sig, vals in nj4_dict.items():
                if sig not in t4_dict:
                    submultiset_fail.append((label, i, which, sig, "missing in top4"))
                    continue
                c_nj4 = Counter(np.round(vals.astype(np.float64), 5).tolist())
                c_t4 = Counter(np.round(t4_dict[sig].astype(np.float64), 5).tolist())
                bad = any(v > c_t4.get(k, 0) for k, v in c_nj4.items())
                if bad:
                    submultiset_fail.append((label, i, which, sig, "exceeds top4 multiplicity"))

        nj4meta = meta_new["nonjet4_diagnostics"]
        t4meta = meta_new["top4_diagnostics"]
        t4_incl_sum = sum(t4meta["final_state_label_event_counts_inclusive"].values())
        nj4_incl_sum = sum(nj4meta["final_state_label_event_counts_inclusive"].values())
        n_rejected = nj4meta["n_rejected_gt4_lepton_bjet"]
        if nj4_incl_sum != t4_incl_sum - n_rejected:
            check_c_incl_fail.append((label, i, t4_incl_sum, n_rejected, nj4_incl_sum))

        fsc = read_final_state_counts(f"{new_dir}/dataset_shard_inclusive.sqlite")
        certain = 0
        ambiguous = 0
        for lbl, cnt in fsc.items():
            m = FS_LABEL_RE.match(lbl)
            if not m:
                continue
            e, mm, j, g, t, b = (int(x) for x in m.groups())
            s = e + mm + b
            nz = [x for x in (e, mm, b) if x > 0]
            if s > 4:
                certain += cnt
            elif s == 4 and len(nz) == 1 and nz[0] == 4:
                ambiguous += cnt
        check_d_rows.append((label, i, certain, ambiguous, n_rejected))

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
print("=== git commits across all 209 jobs ===", git_commits,
      "single_commit_matches_pinned:", git_commits == {"3c7c9c9add5c0436548ce18e41e9c61c898dd89b"} if len(git_commits) else False)
print()
print(f"=== normal+top4 shard identity vs runs_matched/ ({shards_compared} shard files compared) ===")
print("FAILURES:", len(identity_fail))
for x in identity_fail[:30]:
    print(" ", x)
print()
print(f"=== CAPPED:: entries found (should be zero, across {len(SHARD_SET_CAPPED)*sum(n for _,n,_ in DATASETS)} shard files) ===")
print("count:", len(capped_found))
for x in capped_found[:30]:
    print(" ", x)
print()
print("=== check (b): nonjet4 sub-multiset of top4, full dataset ===")
print("FAILURES:", len(submultiset_fail))
for x in submultiset_fail[:30]:
    print(" ", x)
print()
print("=== check (c) inclusive: nonjet4 == top4 - rejected, full dataset ===")
print("FAILURES:", len(check_c_incl_fail))
for x in check_c_incl_fail[:30]:
    print(" ", x)
print()
print("=== check (d): rejected count vs label-based bound, full dataset ===")
d_exact_pass = 0
d_bound_ok = 0
d_fail = []
sum_certain = sum_ambiguous = sum_rejected = 0
for label, i, certain, ambiguous, n_rejected in check_d_rows:
    sum_certain += certain
    sum_ambiguous += ambiguous
    sum_rejected += n_rejected
    if certain == n_rejected and ambiguous == 0:
        d_exact_pass += 1
    if certain <= n_rejected <= certain + ambiguous:
        d_bound_ok += 1
    else:
        d_fail.append((label, i, certain, ambiguous, n_rejected))
print(f"jobs with EXACT match (ambiguous=0): {d_exact_pass}/{len(check_d_rows)}")
print(f"jobs within bound [certain, certain+ambiguous]: {d_bound_ok}/{len(check_d_rows)}")
print(f"jobs OUTSIDE bound (real failures): {len(d_fail)}")
for x in d_fail[:30]:
    print(" ", x)
print(f"totals: sum_certain={sum_certain}, sum_ambiguous={sum_ambiguous}, sum_rejected={sum_rejected}")
print()
print(f"total elapsed: {time.time()-t0:.0f}s")

overall = (not missing_meta and not dup_files and n_read_all_pass and len(git_commits) == 1
           and not identity_fail and not capped_found and not submultiset_fail
           and not check_c_incl_fail and not d_fail)
print()
print(f"STEP 4 OVERALL: {'PASS' if overall else 'FAIL -- see failures above'}")

out = {
    "missing_meta": missing_meta, "dup_files": dup_files,
    "n_read_sums": total_n_read, "n_read_all_pass": n_read_all_pass,
    "git_commits": list(git_commits),
    "shards_compared": shards_compared, "identity_fail_count": len(identity_fail),
    "capped_found_count": len(capped_found),
    "submultiset_fail_count": len(submultiset_fail),
    "check_c_incl_fail_count": len(check_c_incl_fail),
    "check_d": {"exact_pass": d_exact_pass, "bound_ok": d_bound_ok, "fail_count": len(d_fail),
                "sum_certain": sum_certain, "sum_ambiguous": sum_ambiguous, "sum_rejected": sum_rejected},
    "overall_pass": overall,
}
with open("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_nonjet4/step4_identity_checks.json", "w") as f:
    json.dump(out, f, indent=2)
print("wrote step4_identity_checks.json")
sys.exit(0 if overall else 1)
