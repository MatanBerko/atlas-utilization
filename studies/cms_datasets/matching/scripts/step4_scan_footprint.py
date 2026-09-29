"""
Single pass over every DoubleMuon_G and SingleMuon_G file, checking
membership for several CANDIDATE runs at once (to pick the one with the
smallest file-footprint for a tractable Step-4 closure test -- run 279841
turned out to span 19 DoubleMuon files and 39 SingleMuon files, too large
for a bounded 'one closure run' check).
"""
import json
import uproot
import numpy as np

CANDIDATES = [280024, 280016, 279029, 280018, 279841]
FILE_LISTS = json.load(open("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/record_file_lists.json"))["records"]

footprint = {c: {"DoubleMuon_G": [], "SingleMuon_G": []} for c in CANDIDATES}
for key in ["DoubleMuon_G", "SingleMuon_G"]:
    urls = FILE_LISTS[key]["file_urls"]
    for i, url in enumerate(urls):
        try:
            t = uproot.open(url)["Events"]
            runs = t["run"].array(library="np")
        except Exception as e:
            print(f"{key} file {i}: ERROR {e}")
            continue
        present = set(np.unique(runs).tolist())
        for c in CANDIDATES:
            if c in present:
                n = int((runs == c).sum())
                footprint[c][key].append((i, n))
    print(f"done scanning {key}")

for c in CANDIDATES:
    dm_files = footprint[c]["DoubleMuon_G"]
    sm_files = footprint[c]["SingleMuon_G"]
    print(f"run {c}: DoubleMuon in {len(dm_files)} file(s) {dm_files}, SingleMuon in {len(sm_files)} file(s) {sm_files}")

json.dump(footprint, open("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/matching_validation/step4_footprint_candidates.json", "w"), indent=2)
