"""
nonjet4 task, Step 2 checks (b), (c), (e):
(b) HARD: for every signature, the nonjet4 array is a sub-multiset of the
    top-4 array (nonjet4 only removes the rejected events' contributions).
(c) HARD: nonjet4 accepted events == top-4 accepted events minus rejected
    events, for inclusive and exclusive separately.
(e) HARD: no nonjet4 category has electrons+muons+bjets > 4, or more than
    4 objects in total.
"""
import sqlite3
import sys
import json
import re
from collections import Counter

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/nonjet4_pilot_pinned/repo")
from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/nonjet4_pilot"
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


print("=== Check (c): nonjet4 accepted == top4 accepted - rejected (incl & excl) ===")
all_c_pass = True
for run in RUNS:
    meta = json.load(open(f"{BASE}/{run}/job_metadata.json"))
    t4 = meta["top4_diagnostics"]
    nj4 = meta["nonjet4_diagnostics"]

    t4_incl = sum(t4["final_state_label_event_counts_inclusive"].values())
    t4_excl = sum(t4["final_state_label_event_counts_exclusive"].values())
    nj4_incl = sum(nj4["final_state_label_event_counts_inclusive"].values())
    nj4_excl = sum(nj4["final_state_label_event_counts_exclusive"].values())
    n_rejected = nj4["n_rejected_gt4_lepton_bjet"]

    ok_incl = (nj4_incl == t4_incl - n_rejected == nj4["n_kept_le4_lepton_bjet"])
    print(f"  {run}: top4_incl={t4_incl} - rejected={n_rejected} = {t4_incl - n_rejected}, "
          f"nonjet4_incl(from FS sums)={nj4_incl}, nonjet4_incl(diag)={nj4['n_kept_le4_lepton_bjet']} "
          f"-> {'PASS' if ok_incl else 'FAIL'}")
    all_c_pass = all_c_pass and ok_incl

    # Exclusive identity (nonjet4_excl == top4_excl - rejected-and-exclusive
    # events) is checked with an INDEPENDENTLY-derived rejected-and-exclusive
    # count in nonjet4_check_d_f.py (that script re-reads the raw NanoAOD
    # data rather than trusting this run's own diagnostics) -- reported
    # here only as a sanity bound (nonjet4_excl must never exceed top4_excl).
    ok_excl_bound = (nj4_excl <= t4_excl)
    print(f"           top4_excl={t4_excl}, nonjet4_excl={nj4_excl} (<=top4_excl, sanity bound only; "
          f"exact exclusive identity verified independently in nonjet4_check_d_f.py) "
          f"-> {'PASS' if ok_excl_bound else 'FAIL'}")
    all_c_pass = all_c_pass and ok_excl_bound
print(f"Check (c) overall (inclusive identity HARD; exclusive bound here, exact identity in check_d_f): "
      f"{'PASS' if all_c_pass else 'FAIL'}")
print()

print("=== Check (b): nonjet4 array is a sub-multiset of top-4 array, per signature ===")
print("=== Check (e): no nonjet4 category has total objects > 4 ===")
all_b_pass = True
all_e_pass = True
for run in RUNS:
    top4_incl = read_all_arrays(f"{BASE}/{run}/dataset_shard_top4_inclusive.sqlite")
    top4_excl = read_all_arrays(f"{BASE}/{run}/dataset_shard_top4_exclusive.sqlite")
    nj4_incl = read_all_arrays(f"{BASE}/{run}/dataset_shard_nonjet4_inclusive.sqlite")
    nj4_excl = read_all_arrays(f"{BASE}/{run}/dataset_shard_nonjet4_exclusive.sqlite")

    # check (e): every nonjet4 signature must have total <= 4 (this is
    # automatically implied by it being a subset of top4's own signatures,
    # since top4 already enforces total<=4 -- verified directly anyway).
    over4 = []
    for sig in nj4_incl:
        m = FS_RE.search(sig)
        if not m:
            print(f"  {run}: UNPARSEABLE signature {sig!r}")
            all_e_pass = False
            continue
        e, mm, j, g, t, b = (int(x) for x in m.groups())
        total = e + mm + j + g + t + b
        if total > 4:
            over4.append((sig, total))
        if (e + mm + b) > 4:
            print(f"  {run}: FAIL nonjet4 signature {sig} has e+m+b={e+mm+b} > 4")
            all_e_pass = False
    if over4:
        print(f"  {run}: FAIL {len(over4)} nonjet4 signatures with total object count > 4: {over4[:5]}")
        all_e_pass = False
    else:
        print(f"  {run}: check (e) PASS -- all {len(nj4_incl)} nonjet4 signatures have total<=4 and e+m+b<=4")

    # check (b): nonjet4[sig] is a sub-multiset of top4[sig], for both incl/excl.
    def submultiset_check(nj4_dict, t4_dict, label):
        ok = True
        only_in_nj4 = set(nj4_dict) - set(t4_dict)
        if only_in_nj4:
            print(f"  {run} [{label}]: FAIL {len(only_in_nj4)} signatures present in nonjet4 but not top4")
            ok = False
        for sig, vals in nj4_dict.items():
            if sig not in t4_dict:
                continue
            c_nj4 = Counter(round(v, 5) for v in vals)
            c_t4 = Counter(round(v, 5) for v in t4_dict[sig])
            # sub-multiset: every value's count in nj4 <= its count in t4
            bad = {k: (v, c_t4.get(k, 0)) for k, v in c_nj4.items() if v > c_t4.get(k, 0)}
            if bad:
                print(f"  {run} [{label}]: FAIL signature {sig} not a sub-multiset (sample: {list(bad.items())[:3]})")
                ok = False
        return ok

    ok_incl = submultiset_check(nj4_incl, top4_incl, "inclusive")
    ok_excl = submultiset_check(nj4_excl, top4_excl, "exclusive")
    print(f"  {run}: check (b) inclusive={'PASS' if ok_incl else 'FAIL'}, exclusive={'PASS' if ok_excl else 'FAIL'}")
    all_b_pass = all_b_pass and ok_incl and ok_excl

print()
print(f"Check (b) overall: {'PASS' if all_b_pass else 'FAIL'}")
print(f"Check (e) overall: {'PASS' if all_e_pass else 'FAIL'}")

overall = all_b_pass and all_c_pass and all_e_pass
print()
print(f"OVERALL checks (b)(c)(e): {'PASS' if overall else 'FAIL'}")
sys.exit(0 if overall else 1)
