"""
rare4 task, Step 2 checks (b), (c), (d):
(b) HARD: for every signature, the rare4 array is a sub-multiset of the
    NORMAL array.
(c) HARD: for every signature whose (capped display) label has
    e+mu+b > 4, rare4 has NO entries; for every other signature, rare4
    equals normal exactly UNLESS that signature received contributions
    from "hidden" cases in this job (n_hidden_cases > 0 in
    rare4_diagnostics) -- in which case the difference is reported (not
    asserted to a precise per-signature value, since attributing it
    exactly requires re-deriving from raw data, done separately in
    rare4_check_d_f.py only for jobs where hidden cases actually occur).
(d) HARD: rare4 rejected events per file == nonjet4 rejected events per
    file (from job_metadata.json directly -- both should be literally the
    same number by construction, verified here from the actual written
    output, not just trusted from the code).
"""
import sqlite3
import sys
import json
import re
from collections import Counter

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/rare4_pilot_pinned/repo")
from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/rare4_pilot"
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


print("=== Check (d): rare4 rejected == nonjet4 rejected, per file ===")
all_d_pass = True
for run in RUNS:
    meta = json.load(open(f"{BASE}/{run}/job_metadata.json"))
    nj4_rej = meta["nonjet4_diagnostics"]["n_rejected_gt4_lepton_bjet"]
    r4_rej = meta["rare4_diagnostics"]["n_rejected_gt4_lepton_bjet"]
    n_hidden = meta["rare4_diagnostics"]["n_hidden_cases"]
    ok = (nj4_rej == r4_rej)
    print(f"  {run}: nonjet4_rejected={nj4_rej}, rare4_rejected={r4_rej}, hidden_cases={n_hidden} "
          f"-> {'PASS' if ok else 'FAIL'}")
    all_d_pass = all_d_pass and ok
print(f"Check (d) overall: {'PASS' if all_d_pass else 'FAIL'}")
print()

print("=== Checks (b) and (c) ===")
all_b_pass = True
all_c_pass = True
for run in RUNS:
    meta = json.load(open(f"{BASE}/{run}/job_metadata.json"))
    n_hidden = meta["rare4_diagnostics"]["n_hidden_cases"]

    normal_incl = read_all_arrays(f"{BASE}/{run}/dataset_shard_inclusive.sqlite")
    normal_excl = read_all_arrays(f"{BASE}/{run}/dataset_shard_exclusive.sqlite")
    rare4_incl = read_all_arrays(f"{BASE}/{run}/dataset_shard_rare4_inclusive.sqlite")
    rare4_excl = read_all_arrays(f"{BASE}/{run}/dataset_shard_rare4_exclusive.sqlite")

    def submultiset_check(r4_dict, normal_dict, label):
        ok = True
        only_in_r4 = set(r4_dict) - set(normal_dict)
        if only_in_r4:
            print(f"  {run} [{label}]: check(b) FAIL {len(only_in_r4)} signatures present in rare4 but not normal")
            ok = False
        for sig, vals in r4_dict.items():
            if sig not in normal_dict:
                continue
            c_r4 = Counter(round(v, 5) for v in vals)
            c_n = Counter(round(v, 5) for v in normal_dict[sig])
            bad = {k: (v, c_n.get(k, 0)) for k, v in c_r4.items() if v > c_n.get(k, 0)}
            if bad:
                print(f"  {run} [{label}]: check(b) FAIL signature {sig} not a sub-multiset (sample: {list(bad.items())[:3]})")
                ok = False
        return ok

    ok_b_incl = submultiset_check(rare4_incl, normal_incl, "inclusive")
    ok_b_excl = submultiset_check(rare4_excl, normal_excl, "exclusive")
    all_b_pass = all_b_pass and ok_b_incl and ok_b_excl
    print(f"  {run}: check (b) inclusive={'PASS' if ok_b_incl else 'FAIL'}, exclusive={'PASS' if ok_b_excl else 'FAIL'}")

    # check (c), inclusive shard only (exclusive follows structurally from
    # the same construction, and is itself already a sub-multiset of
    # inclusive per check (b))
    c_ok = True
    n_label_gt4_with_entries = 0
    n_label_le4_exact = 0
    n_label_le4_diff = 0
    diffs = []
    for sig, normal_vals in normal_incl.items():
        m = FS_RE.search(sig)
        if not m:
            print(f"  {run}: UNPARSEABLE signature {sig!r}")
            c_ok = False
            continue
        e, mm, j, g, t, b = (int(x) for x in m.groups())
        label_sum = e + mm + b
        r4_vals = rare4_incl.get(sig, [])
        if label_sum > 4:
            if len(r4_vals) > 0:
                print(f"  {run}: check(c) FAIL signature {sig} (label sum {label_sum}>4) has {len(r4_vals)} rare4 entries")
                c_ok = False
                n_label_gt4_with_entries += 1
        else:
            c_n = Counter(round(v, 5) for v in normal_vals)
            c_r4 = Counter(round(v, 5) for v in r4_vals)
            if c_n == c_r4:
                n_label_le4_exact += 1
            else:
                n_label_le4_diff += 1
                diffs.append((sig, len(normal_vals), len(r4_vals)))
    if n_hidden == 0 and n_label_le4_diff > 0:
        print(f"  {run}: check(c) FAIL -- n_hidden_cases=0 but {n_label_le4_diff} label<=4 signatures "
              f"differ between normal and rare4 (sample: {diffs[:5]})")
        c_ok = False
    print(f"  {run}: check (c): label>4 signatures with stray rare4 entries={n_label_gt4_with_entries}, "
          f"label<=4 exact-match={n_label_le4_exact}, label<=4 differing={n_label_le4_diff} "
          f"(n_hidden_cases this job={n_hidden}) -> {'PASS' if c_ok else 'FAIL'}")
    if n_label_le4_diff:
        print(f"    differing signatures (sig, normal_n, rare4_n): {diffs}")
    all_c_pass = all_c_pass and c_ok

print()
print(f"Check (b) overall: {'PASS' if all_b_pass else 'FAIL'}")
print(f"Check (c) overall: {'PASS' if all_c_pass else 'FAIL'}")

overall = all_b_pass and all_c_pass and all_d_pass
print()
print(f"OVERALL checks (b)(c)(d): {'PASS' if overall else 'FAIL'}")
sys.exit(0 if overall else 1)
