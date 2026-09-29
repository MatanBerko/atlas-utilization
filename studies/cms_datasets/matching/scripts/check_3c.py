"""
Step 3c (HARD): for each matched-mode pilot run, using
final_state_label_event_counts_inclusive (already computed by the driver,
capped at 4 particles per type per limit_particles_in_fs -- so "4m" means
">=4 muons", not exactly 4):
  - zero categories with zero selected muons (m==0) in matched mode, for
    BOTH DoubleMuon and SingleMuon
  - every DoubleMuon matched category has >=2 selected muons
  - every SingleMuon matched category has >=1 selected muon
  - full lepton-content breakdown (all distinct (e,m,j,g,t,b) groups and
    their event counts)
"""
import json
import re

BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/matching_validation"
RUNS = [
    ("DoubleMuon", "DoubleMuon_30522_0_matched", 2),
    ("DoubleMuon", "DoubleMuon_30555_0_matched", 2),
    ("SingleMuon", "SingleMuon_30530_0_matched", 1),
    ("SingleMuon", "SingleMuon_30563_0_matched", 1),
]

FS_RE = re.compile(r"(\d+)e_(\d+)m_(\d+)j_(\d+)g_(\d+)t_(\d+)b")

all_ok = True
for label, run_dir, min_muons in RUNS:
    d = json.load(open(f"{BASE}/{run_dir}/job_metadata.json"))
    fs_counts = d["final_state_label_event_counts_inclusive"]
    print(f"=== {run_dir} (dataset={label}, min_muons_required={min_muons}) ===")
    print(f"n_after_gate={d['n_after_gate']}  n_final_state_groups={len(fs_counts)}")
    zero_muon_groups = []
    below_min_groups = []
    total_events = 0
    for fs, n in sorted(fs_counts.items(), key=lambda kv: -kv[1]):
        m = FS_RE.match(fs)
        if not m:
            print(f"  UNPARSEABLE final-state label: {fs!r} n={n}")
            all_ok = False
            continue
        e, mu, j, g, t, b = (int(x) for x in m.groups())
        total_events += n
        if mu == 0:
            zero_muon_groups.append((fs, n))
        if mu < min_muons:
            below_min_groups.append((fs, n))
        print(f"  {fs:30s} n_events={n}")
    print(f"  TOTAL events across all groups: {total_events} (n_after_gate={d['n_after_gate']})")
    assert total_events == d["n_after_gate"], "group event counts do not sum to n_after_gate"
    if zero_muon_groups:
        print(f"  FAIL: {len(zero_muon_groups)} zero-selected-muon categories: {zero_muon_groups}")
        all_ok = False
    else:
        print("  PASS: zero categories with 0 selected muons")
    if below_min_groups:
        print(f"  FAIL: {len(below_min_groups)} categories below min_muons={min_muons}: {below_min_groups}")
        all_ok = False
    else:
        print(f"  PASS: every category has >= {min_muons} selected muon(s)")
    print()

print(f"OVERALL Step 3c: {'PASS' if all_ok else 'FAIL'}")
import sys
sys.exit(0 if all_ok else 1)
