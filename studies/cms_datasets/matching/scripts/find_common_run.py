"""
Step 4 prep: find a run number present in BOTH a DoubleMuon pilot file and
a SingleMuon pilot file (same era, since primary datasets share the same
run-number range within an era but split into differently-sized files),
with a "modest" (not tiny, not huge) event count in each, for the
exactly-once closure test.
"""
import uproot
import numpy as np
from collections import Counter

FILES = {
    "DoubleMuon_G": "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/05DD095C-F6C3-9A4F-9FB3-348A5A6403D5.root",
    "SingleMuon_G": "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/0A4230E2-0C75-604D-890F-A4CE5E5C164E.root",
    "DoubleMuon_H": "root://eospublic.cern.ch//eos/opendata/cms/Run2016H/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/2510000/127C2975-1B1C-A046-AABF-62B77E757A86.root",
    "SingleMuon_H": "root://eospublic.cern.ch//eos/opendata/cms/Run2016H/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/120000/61FC1E38-F75C-6B44-AD19-A9894155874E.root",
}

run_counts = {}
for label, url in FILES.items():
    tree = uproot.open(url)["Events"]
    runs = tree["run"].array(library="np")
    c = Counter(runs.tolist())
    run_counts[label] = c
    print(f"{label}: {len(c)} distinct runs, {runs.size} events total, "
          f"min_run={min(c)} max_run={max(c)}")

for era, dm_key, sm_key in [("G", "DoubleMuon_G", "SingleMuon_G"), ("H", "DoubleMuon_H", "SingleMuon_H")]:
    common = set(run_counts[dm_key].keys()) & set(run_counts[sm_key].keys())
    print(f"\nEra {era}: {len(common)} runs common to both DoubleMuon and SingleMuon pilot files")
    candidates = sorted(common, key=lambda r: run_counts[dm_key][r] + run_counts[sm_key][r])
    # Pick a "modest size" run: not the smallest, not the largest -- median of candidates.
    if candidates:
        median_run = candidates[len(candidates) // 2]
        print(f"  median-size common run: {median_run} "
              f"(DoubleMuon events={run_counts[dm_key][median_run]}, "
              f"SingleMuon events={run_counts[sm_key][median_run]})")
        # Show a few options around the median for picking.
        for r in candidates[max(0, len(candidates)//2 - 2): len(candidates)//2 + 3]:
            print(f"    run={r}: DoubleMuon={run_counts[dm_key][r]} SingleMuon={run_counts[sm_key][r]}")
