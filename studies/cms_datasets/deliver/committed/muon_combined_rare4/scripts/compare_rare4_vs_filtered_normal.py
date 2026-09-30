import json
import re

NORMAL_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined"
RARE4_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_rare4"
FS_RE = re.compile(r"^(\d+)ex_(\d+)mx_(\d+)jx_(\d+)gx_(\d+)tx_(\d+)bx$")

for threshold, normal_file, rare4_file in [
    ("min31bins", "manifest_muon_combined_matched_min31bins.json", "manifest_muon_combined_matched_rare4_min31bins.json"),
    ("min26bins", "manifest_muon_combined_matched_min26bins.json", "manifest_muon_combined_matched_rare4_min26bins.json"),
]:
    normal_manifest = json.load(open(f"{NORMAL_BASE}/{normal_file}"))
    rare4_manifest = json.load(open(f"{RARE4_BASE}/{rare4_file}"))

    filtered_normal_names = set()
    unparsed = []
    for e in normal_manifest:
        cat = e["final_state_category"]
        m = FS_RE.match(cat) if cat else None
        if not m:
            unparsed.append(e["name"])
            continue
        ee, mm, jj, gg, tt, bb = (int(x) for x in m.groups())
        if ee + mm + bb <= 4:
            filtered_normal_names.add(e["name"])

    rare4_names = set(e["name"] for e in rare4_manifest)

    only_filtered_normal = sorted(filtered_normal_names - rare4_names)
    only_rare4 = sorted(rare4_names - filtered_normal_names)

    print(f"=== {threshold} ===")
    print(f"  normal manifest total: {len(normal_manifest)}")
    print(f"  name-filtered normal (e+m+b<=4): {len(filtered_normal_names)}")
    print(f"  rare4 manifest total: {len(rare4_manifest)}")
    print(f"  unparsed normal categories: {unparsed}")
    print(f"  in filtered-normal but not rare4: {len(only_filtered_normal)} -> {only_filtered_normal}")
    print(f"  in rare4 but not filtered-normal: {len(only_rare4)} -> {only_rare4}")
    print()
