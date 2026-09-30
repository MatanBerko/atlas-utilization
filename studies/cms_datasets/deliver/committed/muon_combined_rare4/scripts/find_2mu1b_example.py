import json

NJ4_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_nonjet4"
R4_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_rare4"

nj4_manifest = json.load(open(f"{NJ4_BASE}/manifest_muon_combined_matched_nonjet4_min26bins.json"))
r4_manifest = json.load(open(f"{R4_BASE}/manifest_muon_combined_matched_rare4_min26bins.json"))

target_nj4_cat = "0ex_2mx_1jx_0gx_0tx_1bx"
target_r4_cat = "0ex_2mx_4jx_0gx_0tx_1bx"

nj4_matches = [e for e in nj4_manifest if e["final_state_category"] == target_nj4_cat]
r4_matches = [e for e in r4_manifest if e["final_state_category"] == target_r4_cat]

print(f"nonjet4 entries with category {target_nj4_cat}: {len(nj4_matches)}")
for e in sorted(nj4_matches, key=lambda x: -x["n_events"])[:10]:
    print(f"  {e['name']}: n_events={e['n_events']}, n_filled_bins={e['n_filled_bins']}, combination={e['combination']}")

print(f"\nrare4 entries with category {target_r4_cat}: {len(r4_matches)}")
for e in sorted(r4_matches, key=lambda x: -x["n_events"])[:10]:
    print(f"  {e['name']}: n_events={e['n_events']}, n_filled_bins={e['n_filled_bins']}, combination={e['combination']}")
