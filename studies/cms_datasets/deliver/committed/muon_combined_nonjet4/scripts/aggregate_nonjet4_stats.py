import json
from collections import Counter

BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_nonjet4"
DATASETS = [("DoubleMuon", 57), ("SingleMuon", 152)]

total_accepted_before = 0
total_rejected = 0
total_light_jets_dropped = 0
n_dist = Counter()
e_dist = Counter()
m_dist = Counter()
b_dist = Counter()
per_dataset = {}

for label, n in DATASETS:
    ds_accepted = 0
    ds_rejected = 0
    ds_dropped = 0
    for i in range(n):
        meta = json.load(open(f"{BASE}/{label}/job_{i}/job_metadata.json"))
        nj4 = meta["nonjet4_diagnostics"]
        ds_accepted += nj4["n_accepted_events_before_nonjet4_rule"]
        ds_rejected += nj4["n_rejected_gt4_lepton_bjet"]
        ds_dropped += nj4["n_kept_events_with_light_jets_dropped"]
        for k, v in nj4["rejected_N_distribution"].items():
            n_dist[int(k)] += v
        for k, v in nj4["rejected_event_composition"]["electrons"].items():
            e_dist[int(k)] += v
        for k, v in nj4["rejected_event_composition"]["muons"].items():
            m_dist[int(k)] += v
        for k, v in nj4["rejected_event_composition"]["bjets"].items():
            b_dist[int(k)] += v
    per_dataset[label] = {"accepted_before": ds_accepted, "rejected": ds_rejected, "light_jets_dropped": ds_dropped}
    total_accepted_before += ds_accepted
    total_rejected += ds_rejected
    total_light_jets_dropped += ds_dropped

print("=== Per-dataset ===")
for label, d in per_dataset.items():
    print(f"{label}: accepted_before={d['accepted_before']}, rejected={d['rejected']} "
          f"({100*d['rejected']/d['accepted_before']:.5f}%), light_jets_dropped={d['light_jets_dropped']} "
          f"({100*d['light_jets_dropped']/(d['accepted_before']-d['rejected']):.4f}% of kept)")

print("\n=== Combined ===")
print(f"accepted_before={total_accepted_before}")
print(f"rejected={total_rejected} ({100*total_rejected/total_accepted_before:.5f}%)")
kept = total_accepted_before - total_rejected
print(f"kept={kept}")
print(f"light_jets_dropped={total_light_jets_dropped} ({100*total_light_jets_dropped/kept:.4f}% of kept)")

print("\n=== Rejected events: N (e+m+b) distribution ===")
for k in sorted(n_dist):
    print(f"  N={k}: {n_dist[k]}")
print("\n=== Rejected events: electron count distribution ===")
for k in sorted(e_dist):
    print(f"  e={k}: {e_dist[k]}")
print("=== Rejected events: muon count distribution ===")
for k in sorted(m_dist):
    print(f"  m={k}: {m_dist[k]}")
print("=== Rejected events: bjet count distribution ===")
for k in sorted(b_dist):
    print(f"  b={k}: {b_dist[k]}")

out = {
    "total_accepted_before": total_accepted_before,
    "total_rejected": total_rejected,
    "total_kept": kept,
    "total_light_jets_dropped": total_light_jets_dropped,
    "per_dataset": per_dataset,
    "rejected_N_distribution": dict(sorted(n_dist.items())),
    "rejected_electron_distribution": dict(sorted(e_dist.items())),
    "rejected_muon_distribution": dict(sorted(m_dist.items())),
    "rejected_bjet_distribution": dict(sorted(b_dist.items())),
}
with open(f"{BASE}/nonjet4_full_dataset_aggregate.json", "w") as f:
    json.dump(out, f, indent=2)
print("\nwrote nonjet4_full_dataset_aggregate.json")
