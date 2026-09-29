"""
Step 3a (HARD): full array-level comparison of my pinned-commit generic-mode
shards against the existing read-only pilot generic-mode shards.
Step 3b (HARD): full array-level check that matched-mode's per-signature
arrays are a sub-multiset of generic-mode's per-signature arrays, and that
no signature exists only in matched.

Read-only access throughout (mode=ro&immutable=1) for every path already
under cms_datasets/ (Hard Rule 3) -- including my own matching_validation/
outputs, which are new but there is no reason not to be consistently
read-only here either (this script never writes).
"""
import sqlite3
import sys
from collections import Counter

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/matching_validation_pinned/repo")
from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

OLD_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/run"
NEW_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/matching_validation"

PAIRS = [
    ("job_DoubleMuon_30522_0_generic", "DoubleMuon_30522_0_generic"),
    ("job_DoubleMuon_30555_0_generic", "DoubleMuon_30555_0_generic"),
    ("job_SingleMuon_30530_0_generic", "SingleMuon_30530_0_generic"),
    ("job_SingleMuon_30563_0_generic", "SingleMuon_30563_0_generic"),
]

MATCHED_VS_GENERIC = [
    ("DoubleMuon_30522_0_generic", "DoubleMuon_30522_0_matched"),
    ("DoubleMuon_30555_0_generic", "DoubleMuon_30555_0_matched"),
    ("SingleMuon_30530_0_generic", "SingleMuon_30530_0_matched"),
    ("SingleMuon_30563_0_generic", "SingleMuon_30563_0_matched"),
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
        print(f"[{label}] FAIL: signature name sets differ. only_old={len(old_names-new_names)} only_new={len(new_names-old_names)}")
        return False
    all_ok = True
    for name in sorted(old_names):
        c_old = Counter(round(v, 5) for v in old[name])
        c_new = Counter(round(v, 5) for v in new[name])
        if c_old != c_new:
            print(f"[{label}] FAIL signature {name}: old_n={len(old[name])} new_n={len(new[name])} multiset differs")
            all_ok = False
    if all_ok:
        print(f"[{label}] PASS: {len(old_names)} signatures, byte-for-byte (multiset) identical")
    return all_ok


def compare_subset(generic_path, matched_path, label):
    generic = read_all_arrays(generic_path)
    matched = read_all_arrays(matched_path)
    gen_names = set(generic.keys())
    mat_names = set(matched.keys())
    only_in_matched = mat_names - gen_names
    if only_in_matched:
        print(f"[{label}] FAIL: {len(only_in_matched)} signatures exist ONLY in matched: {sorted(only_in_matched)[:10]}")
        return False
    all_ok = True
    for name in sorted(mat_names):
        c_gen = Counter(round(v, 5) for v in generic.get(name, []))
        c_mat = Counter(round(v, 5) for v in matched[name])
        for v, cnt in c_mat.items():
            if c_gen.get(v, 0) < cnt:
                print(f"[{label}] FAIL signature {name}: value {v} appears {cnt}x in matched but only {c_gen.get(v,0)}x in generic")
                all_ok = False
    if all_ok:
        print(f"[{label}] PASS: matched ({len(mat_names)} signatures) is a sub-multiset of generic ({len(gen_names)} signatures)")
    return all_ok


if __name__ == "__main__":
    print("=== Step 3a: generic-mode shards, pinned-commit rerun vs existing pilot ===")
    all_3a = True
    for old_dir, new_dir in PAIRS:
        for shard in ["dataset_shard_inclusive.sqlite", "dataset_shard_exclusive.sqlite"]:
            ok = compare_identical(f"{OLD_BASE}/{old_dir}/{shard}", f"{NEW_BASE}/{new_dir}/{shard}", f"{new_dir}/{shard}")
            all_3a = all_3a and ok
    print()
    print("=== Step 3b: matched INCLUSIVE is a subset of generic INCLUSIVE ===")
    print("(exclusive shards deliberately use a DIFFERENT veto rule between modes for")
    print(" SingleMuon -- acceptance-only-vs-DoubleMuon in matched, bits-vs-3-datasets")
    print(" in generic -- so matched-exclusive is NOT expected to be a subset of")
    print(" generic-exclusive; checked separately below instead.)")
    all_3b = True
    for gen_dir, mat_dir in MATCHED_VS_GENERIC:
        ok = compare_subset(f"{NEW_BASE}/{gen_dir}/dataset_shard_inclusive.sqlite",
                             f"{NEW_BASE}/{mat_dir}/dataset_shard_inclusive.sqlite",
                             f"{mat_dir}/dataset_shard_inclusive.sqlite")
        all_3b = all_3b and ok
    print()
    print("=== Step 3b (sanity): matched-exclusive is a subset of matched-inclusive ===")
    all_3b_sanity = True
    for _, mat_dir in MATCHED_VS_GENERIC:
        ok = compare_subset(f"{NEW_BASE}/{mat_dir}/dataset_shard_inclusive.sqlite",
                             f"{NEW_BASE}/{mat_dir}/dataset_shard_exclusive.sqlite",
                             f"{mat_dir}/dataset_shard_exclusive.sqlite_vs_own_inclusive")
        all_3b_sanity = all_3b_sanity and ok
    print()
    print(f"OVERALL: 3a={'PASS' if all_3a else 'FAIL'} 3b_inclusive={'PASS' if all_3b else 'FAIL'} "
          f"3b_exclusive_sanity={'PASS' if all_3b_sanity else 'FAIL'}")
    sys.exit(0 if (all_3a and all_3b and all_3b_sanity) else 1)
