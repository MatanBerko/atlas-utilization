"""
Top-4 task, Step 4: identity checks (hard stops) on the full production
run (57 DoubleMuon + 152 SingleMuon jobs).
"""
import json
import sqlite3
from pathlib import Path

BASE = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched")
EXPECTED_N_READ = {"DoubleMuon": 94_148_416, "SingleMuon": 323_952_013}
EXPECTED_N_FILES = {"DoubleMuon": 57, "SingleMuon": 152}
PINNED_COMMIT = "521c31ec0085aef300cb0aa1844799f916610316"

all_pass = True
git_commits_seen = set()
result = {}

for label in ["DoubleMuon", "SingleMuon"]:
    index = json.load(open(BASE / f"{label}_index.json"))
    n_expected = EXPECTED_N_FILES[label]
    seen_pairs = set()
    total_n_read = 0
    n_capped_normal = 0
    n_capped_top4 = 0
    capped_details = []
    commits_this_dataset = set()
    job_dirs_found = 0

    for idx_str in index:
        idx = int(idx_str)
        job_dir = BASE / label / f"job_{idx}"
        meta_path = job_dir / "job_metadata.json"
        if not meta_path.exists():
            print(f"[{label}] FAIL: missing job_metadata.json for index {idx}")
            all_pass = False
            continue
        job_dirs_found += 1
        meta = json.loads(meta_path.read_text())
        commits_this_dataset.add(meta["git_commit"])
        git_commits_seen.add(meta["git_commit"])

        rec_file = (meta["record_id"], meta["file_index"])
        if rec_file in seen_pairs:
            print(f"[{label}] FAIL: duplicate (record,file) {rec_file} at index {idx}")
            all_pass = False
        seen_pairs.add(rec_file)

        expected_rec_file = (index[idx_str]["record_id"], index[idx_str]["file_index"])
        if rec_file != expected_rec_file:
            print(f"[{label}] FAIL: index {idx} processed {rec_file}, expected {expected_rec_file}")
            all_pass = False

        total_n_read += meta["n_read"]

        for shard_name, counter_name in [
            ("dataset_shard_inclusive.sqlite", "normal"),
            ("dataset_shard_exclusive.sqlite", "normal"),
            ("dataset_shard_top4_inclusive.sqlite", "top4"),
            ("dataset_shard_top4_exclusive.sqlite", "top4"),
        ]:
            shard_path = job_dir / shard_name
            con = sqlite3.connect(f"file:{shard_path}?mode=ro&immutable=1", uri=True)
            cur = con.cursor()
            cur.execute("SELECT key, value FROM shard_metadata WHERE key LIKE 'CAPPED::%'")
            rows = cur.fetchall()
            con.close()
            if rows:
                for k, v in rows:
                    capped_details.append({"index": idx, "shard": shard_name, "key": k, "value": v})
                if counter_name == "normal":
                    n_capped_normal += len(rows)
                else:
                    n_capped_top4 += len(rows)

    # Coverage check: every index in the index file has a job dir; every
    # (record,file) pair the index file expects was seen exactly once.
    all_expected_pairs = {(v["record_id"], v["file_index"]) for v in index.values()}
    missing_pairs = all_expected_pairs - seen_pairs
    extra_pairs = seen_pairs - all_expected_pairs

    print(f"=== {label} ===")
    print(f"  job dirs found: {job_dirs_found} / {n_expected} expected")
    print(f"  distinct (record,file) pairs covered: {len(seen_pairs)} / {len(all_expected_pairs)} expected")
    print(f"  missing pairs: {missing_pairs}")
    print(f"  extra/duplicate pairs beyond expected: {extra_pairs}")
    print(f"  sum(n_read) = {total_n_read}  (expected {EXPECTED_N_READ[label]})")
    print(f"  git commits used: {commits_this_dataset}")
    print(f"  CAPPED:: entries -- normal: {n_capped_normal}, top4: {n_capped_top4}")

    ok = (
        job_dirs_found == n_expected
        and not missing_pairs
        and not extra_pairs
        and total_n_read == EXPECTED_N_READ[label]
        and commits_this_dataset == {PINNED_COMMIT}
        and n_capped_normal == 0
        and n_capped_top4 == 0
    )
    print(f"  {label} identity checks: {'PASS' if ok else 'FAIL'}")
    all_pass = all_pass and ok

    result[label] = {
        "job_dirs_found": job_dirs_found,
        "n_expected_files": n_expected,
        "n_pairs_covered": len(seen_pairs),
        "n_pairs_expected": len(all_expected_pairs),
        "missing_pairs": list(missing_pairs),
        "extra_pairs": list(extra_pairs),
        "sum_n_read": total_n_read,
        "expected_n_read": EXPECTED_N_READ[label],
        "git_commits_used": list(commits_this_dataset),
        "n_capped_normal": n_capped_normal,
        "n_capped_top4": n_capped_top4,
        "capped_details": capped_details,
    }

print()
print(f"Single git commit across BOTH datasets: {git_commits_seen} -> "
      f"{'PASS' if git_commits_seen == {PINNED_COMMIT} else 'FAIL'}")
all_pass = all_pass and (git_commits_seen == {PINNED_COMMIT})

print()
print(f"OVERALL Step 4 identity checks (coverage/counts/commit/cap): {'PASS' if all_pass else 'FAIL'}")

with open(BASE / "step4_identity_checks.json", "w") as f:
    json.dump({"overall_pass": all_pass, "single_commit": list(git_commits_seen), **result}, f, indent=2)
print(f"wrote {BASE / 'step4_identity_checks.json'}")
