"""
Top-4 task, Step 4 (remaining checks):
- The 4 pilot files in the full run reproduce Step 2's own outputs
  exactly (all 4 shard types: normal inclusive/exclusive, top4
  inclusive/exclusive).
- DoubleMuon inclusive == exclusive, aggregated over all 57 files.
- SingleMuon: inclusive minus exclusive == events vetoed by DoubleMuon's
  acceptance; report the exclusive fraction, aggregated over all 152
  files.
"""
import json
import sqlite3
import sys
from collections import Counter

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/matched_top4_production_pinned/repo")
from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

RUNS_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched"
PILOT_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/top4_pilot"

PILOT_MAP = [
    ("DoubleMuon", 0, "DoubleMuon_30522_0_matched"),
    ("DoubleMuon", 29, "DoubleMuon_30555_0_matched"),
    ("SingleMuon", 0, "SingleMuon_30530_0_matched"),
    ("SingleMuon", 70, "SingleMuon_30563_0_matched"),
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
    if set(old.keys()) != set(new.keys()):
        print(f"[{label}] FAIL: signature sets differ")
        return False
    ok = True
    for name in old:
        c_old = Counter(round(v, 5) for v in old[name])
        c_new = Counter(round(v, 5) for v in new[name])
        if c_old != c_new:
            print(f"[{label}] FAIL signature {name}")
            ok = False
    print(f"[{label}] {'PASS' if ok else 'FAIL'}: {len(old)} signatures")
    return ok


print("=== Pilot reproducibility: full-run job vs. Step 2's top4_pilot outputs ===")
all_repro_pass = True
for label, idx, pilot_dir in PILOT_MAP:
    job_dir = f"{RUNS_BASE}/{label}/job_{idx}"
    pilot_dir_full = f"{PILOT_BASE}/{pilot_dir}"
    for shard in ["dataset_shard_inclusive.sqlite", "dataset_shard_exclusive.sqlite",
                  "dataset_shard_top4_inclusive.sqlite", "dataset_shard_top4_exclusive.sqlite"]:
        ok = compare_identical(f"{pilot_dir_full}/{shard}", f"{job_dir}/{shard}", f"{pilot_dir}/{shard}")
        all_repro_pass = all_repro_pass and ok
print(f"Pilot reproducibility overall: {'PASS' if all_repro_pass else 'FAIL'}")
print()

print("=== DoubleMuon inclusive == exclusive (aggregated over all 57 files) ===")
dm_index = json.load(open(f"{RUNS_BASE}/DoubleMuon_index.json"))
total_incl = 0
total_excl = 0
all_dm_equal = True
for idx_str in dm_index:
    meta = json.load(open(f"{RUNS_BASE}/DoubleMuon/job_{idx_str}/job_metadata.json"))
    total_incl += meta["n_after_gate"]
    total_excl += meta["n_exclusive"]
    if meta["n_after_gate"] != meta["n_exclusive"]:
        print(f"  FAIL: job_{idx_str} n_after_gate={meta['n_after_gate']} != n_exclusive={meta['n_exclusive']}")
        all_dm_equal = False
print(f"  total inclusive (n_after_gate) = {total_incl}")
print(f"  total exclusive (n_exclusive)  = {total_excl}")
print(f"  DoubleMuon inclusive==exclusive per-job and in total: {'PASS' if (all_dm_equal and total_incl==total_excl) else 'FAIL'}")
print()

print("=== SingleMuon: inclusive - exclusive == vetoed by DoubleMuon acceptance ===")
sm_index = json.load(open(f"{RUNS_BASE}/SingleMuon_index.json"))
total_sm_incl = 0
total_sm_excl = 0
for idx_str in sm_index:
    meta = json.load(open(f"{RUNS_BASE}/SingleMuon/job_{idx_str}/job_metadata.json"))
    total_sm_incl += meta["n_after_gate"]
    total_sm_excl += meta["n_exclusive"]
total_vetoed = total_sm_incl - total_sm_excl
exclusive_fraction = total_sm_excl / total_sm_incl if total_sm_incl else None
print(f"  total SingleMuon inclusive (n_after_gate) = {total_sm_incl}")
print(f"  total SingleMuon exclusive (n_exclusive)  = {total_sm_excl}")
print(f"  inclusive - exclusive (= vetoed by DoubleMuon acceptance) = {total_vetoed}")
print(f"  exclusive fraction = {exclusive_fraction:.6f} ({exclusive_fraction*100:.4f}%)")
print("  (by construction: n_exclusive was computed in run_dataset_on_file.py as n_after_gate")
print("   events NOT vetoed by DoubleMuon's acceptance, evaluated on the SAME event -- so")
print("   inclusive-exclusive==vetoed is definitionally true per-job; this aggregates that.)")

result = {
    "pilot_reproducibility_pass": all_repro_pass,
    "doublemuon_inclusive_equals_exclusive": {
        "pass": all_dm_equal and total_incl == total_excl,
        "total_inclusive": total_incl,
        "total_exclusive": total_excl,
    },
    "singlemuon_veto_accounting": {
        "total_inclusive": total_sm_incl,
        "total_exclusive": total_sm_excl,
        "total_vetoed_by_doublemuon_acceptance": total_vetoed,
        "exclusive_fraction": exclusive_fraction,
    },
}
with open(f"{RUNS_BASE}/step4_pilot_repro_and_veto.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"\nwrote {RUNS_BASE}/step4_pilot_repro_and_veto.json")
