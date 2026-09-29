"""
Step 4 (corrected): the task brief explicitly allows reading, for the ONE
chosen closure run, from ALL DoubleMuon and SingleMuon files that contain
it -- not just the 4 pilot files ("4 existing pilot files ... PLUS ONE
closure run"). step4_lumi_overlap.py showed the two pilot files (record
30522 file 0, record 30530 file 0) cover ZERO overlapping luminosityBlocks
for run 279841 -- each dataset splits a run's data across multiple files
independently, so a meaningful closure test needs every file of BOTH
datasets (G-era only, since run 279841 is a G-era run) that actually
contains this run.

This script does ONLY a cheap single-branch ('run') scan over every
DoubleMuon_G and SingleMuon_G file (from the pre-existing, read-only
record_file_lists.json) to find which files contain run 279841 -- NOT a
full-dataset pipeline run (no selection, no combinatorics, no shard
writing) -- consistent with "use pre-flight per-file/per-run data to find
which files contain it" when no such per-run index already exists.
"""
import json
import uproot
import awkward as ak

TARGET_RUN = 279841
FILE_LISTS = json.load(open("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/record_file_lists.json"))["records"]

for key in ["DoubleMuon_G", "SingleMuon_G"]:
    urls = FILE_LISTS[key]["file_urls"]
    print(f"=== {key}: scanning {len(urls)} files for run {TARGET_RUN} ===")
    matches = []
    for i, url in enumerate(urls):
        try:
            t = uproot.open(url)["Events"]
            runs = t["run"].array(library="np")
        except Exception as e:
            print(f"  file {i}: ERROR reading ({e})")
            continue
        if (runs == TARGET_RUN).any():
            n = int((runs == TARGET_RUN).sum())
            matches.append((i, url, n))
            print(f"  file {i}: CONTAINS run {TARGET_RUN} ({n} events)")
    print(f"  -> {len(matches)} file(s) contain run {TARGET_RUN}: {[m[0] for m in matches]}")
    json.dump({"key": key, "target_run": TARGET_RUN,
               "matching_files": [{"index": i, "url": u, "n_events": n} for i, u, n in matches]},
              open(f"/storage/agrp/berkom/atlas-utilization/output/cms_datasets/matching_validation/step4_files_{key}.json", "w"),
              indent=2)
    print()
