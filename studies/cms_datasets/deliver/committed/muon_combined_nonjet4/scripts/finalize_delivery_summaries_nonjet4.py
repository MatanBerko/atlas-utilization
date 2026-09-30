import json

BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_nonjet4"

verif = json.load(open(f"{BASE}/verification_summary.json"))
crop_summary = {}
name_map = {
    ("nonjet4", "min31bins"): ("muon_combined_matched_nonjet4_bumpnet_min31bins.root",
                                "muon_combined_matched_nonjet4_bumpnet_min31bins_cropped.root"),
    ("nonjet4", "min26bins"): ("muon_combined_matched_nonjet4_bumpnet_min26bins.root",
                                "muon_combined_matched_nonjet4_bumpnet_min26bins_cropped.root"),
}
for s in verif["summary"]:
    src, out = name_map[(s["version"], s["threshold"])]
    crop_summary[out] = {
        "source": src,
        "n_histograms": s["n_manifest"],
        "n_bin1_nonzero": s["n_manifest"] if s["all_checks_passed"] else None,
        "all_checks_passed": s["all_checks_passed"],
        "verified_with": ["uproot", "PyROOT 6.40.02 (LCG_110, x86_64-el9-gcc13-opt)"],
    }
json.dump(crop_summary, open(f"{BASE}/crop_summary.json", "w"), indent=2)
print("wrote crop_summary.json")
print(json.dumps(crop_summary, indent=2))

build_nonjet4 = json.load(open(f"{BASE}/build_summary_nonjet4.json"))
consolidated = {"nonjet4": build_nonjet4}
json.dump(consolidated, open(f"{BASE}/build_summary.json", "w"), indent=2)
print("\nwrote consolidated build_summary.json")
