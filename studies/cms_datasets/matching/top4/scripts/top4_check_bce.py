"""
Top-4 task, Step 2 checks (b), (c), (e):
(b) HARD: accepted-event counts (inclusive+exclusive) identical between
    normal and top-4.
(c) HARD: every top-4 category has total object count <=4; for every such
    category, normal's array is a sub-multiset of top-4's array.
(e) Count of top-4 categories with zero selected muons (report + explain).
"""
import sqlite3
import sys
import json
import re
from collections import Counter

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/top4_pilot_pinned/repo")
from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/top4_pilot"
RUNS = [
    "DoubleMuon_30522_0_matched",
    "DoubleMuon_30555_0_matched",
    "SingleMuon_30530_0_matched",
    "SingleMuon_30563_0_matched",
]
FS_RE = re.compile(r"_FS_(\d+)e_(\d+)m_(\d+)j_(\d+)g_(\d+)t_(\d+)b_IM_")


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


print("=== Check (b): accepted-event counts identical between normal and top-4 ===")
all_b_pass = True
for run in RUNS:
    meta = json.load(open(f"{BASE}/{run}/job_metadata.json"))
    t4 = meta["top4_diagnostics"]
    ok_incl = (t4["n_accepted_events"] == meta["n_after_gate"])
    ok_excl_consistent = True  # exclusive count comparison below via FS sums
    fs_incl_sum_normal = sum(meta["final_state_label_event_counts_inclusive"].values())
    fs_excl_sum_normal = sum(meta["final_state_label_event_counts_exclusive"].values())
    fs_incl_sum_top4 = sum(t4["final_state_label_event_counts_inclusive"].values())
    fs_excl_sum_top4 = sum(t4["final_state_label_event_counts_exclusive"].values())
    ok = (meta["n_after_gate"] == fs_incl_sum_normal == fs_incl_sum_top4 == t4["n_accepted_events"]) and \
         (meta["n_exclusive"] == fs_excl_sum_normal == fs_excl_sum_top4)
    print(f"  {run}: normal(incl={meta['n_after_gate']}, excl={meta['n_exclusive']}) "
          f"top4(incl={fs_incl_sum_top4}, excl={fs_excl_sum_top4}) -> {'PASS' if ok else 'FAIL'}")
    all_b_pass = all_b_pass and ok
print(f"Check (b) overall: {'PASS' if all_b_pass else 'FAIL'}")
print()

print("=== Check (c): every top-4 category has total <=4; normal subset of top-4 for those ===")
all_c_pass = True
c_details = {}
for run in RUNS:
    top4_incl = read_all_arrays(f"{BASE}/{run}/dataset_shard_top4_inclusive.sqlite")
    top4_excl = read_all_arrays(f"{BASE}/{run}/dataset_shard_top4_exclusive.sqlite")
    normal_incl = read_all_arrays(f"{BASE}/{run}/dataset_shard_inclusive.sqlite")
    normal_excl = read_all_arrays(f"{BASE}/{run}/dataset_shard_exclusive.sqlite")

    over4 = []
    for sig in top4_incl:
        m = FS_RE.search(sig)
        if not m:
            print(f"  {run}: UNPARSEABLE signature {sig!r}")
            all_c_pass = False
            continue
        e, mm, j, g, t, b = (int(x) for x in m.groups())
        total = e + mm + j + g + t + b
        if total > 4:
            over4.append((sig, total))
    if over4:
        print(f"  {run}: FAIL -- {len(over4)} top-4 signatures with total object count >4: {over4[:5]}")
        all_c_pass = False
    else:
        print(f"  {run}: PASS -- all {len(top4_incl)} top-4 inclusive signatures have total <=4")

    # normal subset of top4, restricted to categories with total<=4 (only
    # such categories can even exist in the top4 shard at all).
    n_checked = 0
    n_subset_fail = 0
    for sig, top4_arr in top4_incl.items():
        if sig not in normal_incl:
            continue  # signature only exists in top4 (e.g. from truncated events) -- fine, nothing to compare
        n_checked += 1
        c_top4 = Counter(round(v, 5) for v in top4_arr)
        c_normal = Counter(round(v, 5) for v in normal_incl[sig])
        for v, cnt in c_normal.items():
            if c_top4.get(v, 0) < cnt:
                n_subset_fail += 1
                break
    print(f"  {run}: inclusive subset check -- {n_checked} shared signatures checked, {n_subset_fail} failed")
    all_c_pass = all_c_pass and (n_subset_fail == 0)

    n_checked_e = 0
    n_subset_fail_e = 0
    for sig, top4_arr in top4_excl.items():
        if sig not in normal_excl:
            continue
        n_checked_e += 1
        c_top4 = Counter(round(v, 5) for v in top4_arr)
        c_normal = Counter(round(v, 5) for v in normal_excl[sig])
        for v, cnt in c_normal.items():
            if c_top4.get(v, 0) < cnt:
                n_subset_fail_e += 1
                break
    print(f"  {run}: exclusive subset check -- {n_checked_e} shared signatures checked, {n_subset_fail_e} failed")
    all_c_pass = all_c_pass and (n_subset_fail_e == 0)
print(f"Check (c) overall: {'PASS' if all_c_pass else 'FAIL'}")
print()

print("=== Check (e): top-4 categories with zero selected muons ===")
for run in RUNS:
    meta = json.load(open(f"{BASE}/{run}/job_metadata.json"))
    t4 = meta["top4_diagnostics"]
    fs_counts = t4["final_state_label_event_counts_inclusive"]
    zero_muon = {}
    for fs, n in fs_counts.items():
        m = re.match(r"(\d+)e_(\d+)m_(\d+)j_(\d+)g_(\d+)t_(\d+)b", fs)
        if m and int(m.group(2)) == 0:
            zero_muon[fs] = n
    total_zero_muon_events = sum(zero_muon.values())
    print(f"  {run}: {len(zero_muon)} zero-muon top-4 categories, {total_zero_muon_events} events total: {zero_muon}")

print()
sys.exit(0 if (all_b_pass and all_c_pass) else 1)
