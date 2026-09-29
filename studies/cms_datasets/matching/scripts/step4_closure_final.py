"""
Step 4: exactly-once closure test, FINAL version -- run 280016 (Run2016G),
chosen because it has the smallest file-footprint among several candidate
common runs (run 279841, originally chosen by smallest combined pilot-file
event count, turned out to span 19 DoubleMuon files and 39 SingleMuon
files -- too large for a bounded "one closure run" check; see
step4_scan_footprint.py). Run 280016 spans 5 DoubleMuon_G files and 8
SingleMuon_G files (13 files total, ~693k raw events combined) -- reads
ALL of them (every DoubleMuon/SingleMuon file actually containing this
run, per the task's own instruction), not just the original 2 pilot files.

Reuses, unmodified, the exact functions from the pinned commit's
studies/cms_datasets/cluster/run_dataset_on_file.py (matched_acceptance_mask,
TRIGOBJ_BIT_*, DOUBLEMUON_MATCHED_*/SINGLEMUON_MATCHED_* thresholds,
TRIGGER_PATHS_BY_DATASET), services.parsing.validated_runs (golden JSON),
services.parsing.trigger_requirements.apply_trigger_requirement, and
studies.m0m1j0_cms.selection.select_muons.
"""
import sys
sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/matching_validation_pinned/repo")

import awkward as ak
import numpy as np
import uproot
import json

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter
from services.parsing.trigger_requirements import apply_trigger_requirement
from studies.m0m1j0_cms import selection
from studies.cms_datasets.cluster.run_dataset_on_file import (
    TRIGGER_PATHS_BY_DATASET,
    TRIGOBJ_BIT_TRKISOVVL, TRIGOBJ_BIT_ISO,
    DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV,
    SINGLEMUON_MATCHED_MIN_MUONS, SINGLEMUON_MATCHED_PT_MIN_GEV,
    SINGLEMUON_MATCHED_TRIGGER_PATHS,
    matched_acceptance_mask,
    DEFAULT_VALIDATED_RUNS_JSON,
)

TARGET_RUN = 280016

DM_URLS = [
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/05DD095C-F6C3-9A4F-9FB3-348A5A6403D5.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/78FA0801-28AF-3A45-A36A-AB7CC9A5506E.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/A3CE8422-11FF-5D4C-922D-B592FDD76682.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/ED3359B9-BF1E-044C-8418-ACDDE2B11FF0.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/EF0619CE-F699-5942-BA8B-206D2D434A33.root",
]
SM_URLS = [
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/0A4230E2-0C75-604D-890F-A4CE5E5C164E.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/1D280BA6-2EBB-A544-91EB-E821F3CF0B06.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/08BEF135-37C0-F145-88E9-63F7A10D3BC7.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/5BF83F4E-336D-1641-9576-53FC198765B5.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/95AF7A2E-F973-5642-96C6-B37EA7C96FF7.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/E801FC2F-0877-9F4C-978D-FE9C94B92CAF.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/16CB6056-D4D5-2046-9D30-82D8985F831F.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/20CCC9D4-0AD5-9E42-B642-DE86F25153ED.root",
]

BASE_BRANCHES = [
    "run", "luminosityBlock", "event",
    "nMuon", "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_mediumId", "Muon_pfRelIso04_all",
    "nTrigObj", "TrigObj_pt", "TrigObj_eta", "TrigObj_phi", "TrigObj_id", "TrigObj_filterBits",
]
DM_PATHS = TRIGGER_PATHS_BY_DATASET["DoubleMuon"]
SM_PATHS_MATCHED = list(SINGLEMUON_MATCHED_TRIGGER_PATHS)
ALL_TRIGGER_BRANCHES = sorted(set(DM_PATHS) | set(SM_PATHS_MATCHED))
ALL_BRANCHES = BASE_BRANCHES + ALL_TRIGGER_BRANCHES


def read_and_filter_to_run(urls, target_run, branches):
    chunks = []
    for url in urls:
        tree = uproot.open(url)["Events"]
        events = tree.arrays(branches, library="ak")
        mask = ak.to_numpy(events.run) == target_run
        filtered = events[mask]
        if len(filtered) > 0:
            chunks.append(filtered)
        print(f"  {url.rsplit('/', 1)[-1]}: {len(filtered)} events for run {target_run}")
    return ak.concatenate(chunks) if len(chunks) > 1 else chunks[0]


def make_trigobj(events):
    return ak.zip({
        "pt": events.TrigObj_pt, "eta": events.TrigObj_eta, "phi": events.TrigObj_phi,
        "id": events.TrigObj_id, "filterBits": events.TrigObj_filterBits,
    })


def rle_set(events):
    r = ak.to_numpy(events.run); l = ak.to_numpy(events.luminosityBlock); e = ak.to_numpy(events.event)
    return set(zip(r.tolist(), l.tolist(), e.tolist()))


validated_runs = ValidatedRunsFilter(DEFAULT_VALIDATED_RUNS_JSON)

print(f"=== Reading {len(DM_URLS)} DoubleMuon G files, filtering to run=={TARGET_RUN} ===")
dm_events_raw = read_and_filter_to_run(DM_URLS, TARGET_RUN, ALL_BRANCHES)
print(f"DoubleMuon TOTAL: {len(dm_events_raw)} raw events for run {TARGET_RUN}")

# Duplicate-event check across files (each (run,lumi,event) should appear
# exactly once across the whole dataset -- a basic sanity check before
# trusting the concatenated set).
dm_rle_all = list(zip(ak.to_numpy(dm_events_raw.run).tolist(), ak.to_numpy(dm_events_raw.luminosityBlock).tolist(), ak.to_numpy(dm_events_raw.event).tolist()))
n_dm_dupes = len(dm_rle_all) - len(set(dm_rle_all))
print(f"DoubleMuon duplicate (run,lumi,event) triples across its {len(DM_URLS)} files: {n_dm_dupes}")

dm_golden, dm_golden_stats = apply_validated_runs_filter(dm_events_raw, validated_runs)
print(f"DoubleMuon: golden-JSON {dm_golden_stats['n_before']} -> {dm_golden_stats['n_after']}")
dm_triggered, dm_trig_stats = apply_trigger_requirement(dm_golden, {"mode": "any", "paths": DM_PATHS})
print(f"DoubleMuon: own-trigger {dm_trig_stats['n_before']} -> {dm_trig_stats['n_after']}")
dm_muons = selection.select_muons(dm_triggered)
dm_trigobj = make_trigobj(dm_triggered)
dm_accept = matched_acceptance_mask(dm_muons, dm_trigobj, TRIGOBJ_BIT_TRKISOVVL,
                                      DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV)
dm_accepted_events = dm_triggered[dm_accept]
print(f"DoubleMuon: matched-accepted (INCLUSIVE == EXCLUSIVE) = {len(dm_accepted_events)}")
dm_inclusive_set = rle_set(dm_accepted_events)
dm_all_rle = rle_set(dm_golden)
dm_accept_by_rle = {}
_r = ak.to_numpy(dm_triggered.run); _l = ak.to_numpy(dm_triggered.luminosityBlock); _e = ak.to_numpy(dm_triggered.event)
_a = ak.to_numpy(dm_accept)
for i in range(len(dm_triggered)):
    dm_accept_by_rle[(int(_r[i]), int(_l[i]), int(_e[i]))] = bool(_a[i])

print()
print(f"=== Reading {len(SM_URLS)} SingleMuon G files, filtering to run=={TARGET_RUN} ===")
sm_events_raw = read_and_filter_to_run(SM_URLS, TARGET_RUN, ALL_BRANCHES)
print(f"SingleMuon TOTAL: {len(sm_events_raw)} raw events for run {TARGET_RUN}")
sm_rle_all = list(zip(ak.to_numpy(sm_events_raw.run).tolist(), ak.to_numpy(sm_events_raw.luminosityBlock).tolist(), ak.to_numpy(sm_events_raw.event).tolist()))
n_sm_dupes = len(sm_rle_all) - len(set(sm_rle_all))
print(f"SingleMuon duplicate (run,lumi,event) triples across its {len(SM_URLS)} files: {n_sm_dupes}")

sm_golden, sm_golden_stats = apply_validated_runs_filter(sm_events_raw, validated_runs)
print(f"SingleMuon: golden-JSON {sm_golden_stats['n_before']} -> {sm_golden_stats['n_after']}")
sm_triggered, sm_trig_stats = apply_trigger_requirement(sm_golden, {"mode": "any", "paths": SM_PATHS_MATCHED})
print(f"SingleMuon: own-trigger (matched mode, {SM_PATHS_MATCHED}) {sm_trig_stats['n_before']} -> {sm_trig_stats['n_after']}")
sm_muons = selection.select_muons(sm_triggered)
sm_trigobj = make_trigobj(sm_triggered)
sm_accept = matched_acceptance_mask(sm_muons, sm_trigobj, TRIGOBJ_BIT_ISO,
                                      SINGLEMUON_MATCHED_MIN_MUONS, SINGLEMUON_MATCHED_PT_MIN_GEV)
sm_inclusive_events = sm_triggered[sm_accept]
print(f"SingleMuon: matched-accepted (INCLUSIVE) = {len(sm_inclusive_events)}")
sm_inclusive_set = rle_set(sm_inclusive_events)

dm_fired_on_sm = np.zeros(len(sm_triggered), dtype=bool)
for path in DM_PATHS:
    dm_fired_on_sm |= ak.to_numpy(sm_triggered[path]).astype(bool)
dm_accepted_on_sm = matched_acceptance_mask(sm_muons, sm_trigobj, TRIGOBJ_BIT_TRKISOVVL,
                                              DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV)
vetoed_by_dm_on_sm = dm_fired_on_sm & dm_accepted_on_sm
sm_exclusive_mask = ~vetoed_by_dm_on_sm[sm_accept]
sm_exclusive_events = sm_inclusive_events[sm_exclusive_mask]
print(f"SingleMuon: matched-accepted AND vetoed-by-DoubleMuon-acceptance = {int(vetoed_by_dm_on_sm[sm_accept].sum())}")
print(f"SingleMuon: EXCLUSIVE = {len(sm_exclusive_events)}")
sm_exclusive_set = rle_set(sm_exclusive_events)
vetoed_rle_set = rle_set(sm_inclusive_events[~sm_exclusive_mask])

print()
print("=== Check (i): DoubleMuon set is disjoint from SingleMuon EXCLUSIVE set ===")
overlap_i = dm_inclusive_set & sm_exclusive_set
check_i_pass = (len(overlap_i) == 0)
print(f"  |DM_incl|={len(dm_inclusive_set)}  |SM_excl|={len(sm_exclusive_set)}  overlap={len(overlap_i)}  -> {'PASS' if check_i_pass else 'FAIL'}")
if overlap_i:
    print(f"  OVERLAPPING (up to 20): {sorted(overlap_i)[:20]}")

print()
print("=== Check (ii): every SingleMuon event vetoed because DoubleMuon accepts it ===")
print("    is actually present in the DoubleMuon file(s) and accepted there")
n_present_accepted = n_present_not_accepted = n_absent = 0
exceptions = []
for rle in vetoed_rle_set:
    if rle in dm_accept_by_rle:
        if dm_accept_by_rle[rle]:
            n_present_accepted += 1
        else:
            n_present_not_accepted += 1
            exceptions.append(("present_but_not_accepted_in_DM_own_copy", rle))
    else:
        n_absent += 1
        exceptions.append(("absent_from_DM_files_entirely", rle))
check_ii_pass = (n_present_accepted == len(vetoed_rle_set))
print(f"  n_vetoed={len(vetoed_rle_set)} present_and_accepted={n_present_accepted} "
      f"present_not_accepted={n_present_not_accepted} absent={n_absent} -> {'PASS' if check_ii_pass else 'FAIL'}")
if exceptions:
    print(f"  EXCEPTIONS (up to 20 shown): {exceptions[:20]}")

print()
print("=== Check (iii): union(DM_exclusive, SM_exclusive) == union(DM_inclusive, SM_inclusive) ===")
dm_exclusive_set = dm_inclusive_set
union_incl = dm_inclusive_set | sm_inclusive_set
union_excl = dm_exclusive_set | sm_exclusive_set
lost = union_incl - union_excl
gained = union_excl - union_incl
check_iii_pass = (len(lost) == 0 and len(gained) == 0)
print(f"  |union_incl|={len(union_incl)} |union_excl|={len(union_excl)} lost={len(lost)} gained={len(gained)} -> {'PASS' if check_iii_pass else 'FAIL'}")
if lost:
    print(f"  LOST (up to 20): {sorted(lost)[:20]}")
if gained:
    print(f"  GAINED (up to 20): {sorted(gained)[:20]}")

overall_pass = check_i_pass and check_ii_pass and check_iii_pass
print()
print(f"OVERALL Step 4 closure test (run {TARGET_RUN}, {len(DM_URLS)} DoubleMuon files + {len(SM_URLS)} SingleMuon files): {'PASS' if overall_pass else 'FAIL'}")

result = {
    "target_run": TARGET_RUN,
    "n_doublemuon_files": len(DM_URLS), "n_singlemuon_files": len(SM_URLS),
    "dm_urls": DM_URLS, "sm_urls": SM_URLS,
    "dm_n_raw_for_run": int(len(dm_events_raw)), "sm_n_raw_for_run": int(len(sm_events_raw)),
    "dm_n_duplicate_rle_across_files": n_dm_dupes, "sm_n_duplicate_rle_across_files": n_sm_dupes,
    "dm_n_after_golden": dm_golden_stats["n_after"], "sm_n_after_golden": sm_golden_stats["n_after"],
    "dm_n_after_trigger": dm_trig_stats["n_after"], "sm_n_after_trigger": sm_trig_stats["n_after"],
    "dm_n_inclusive_accepted": len(dm_inclusive_set), "sm_n_inclusive_accepted": len(sm_inclusive_set),
    "sm_n_vetoed_by_dm_acceptance": len(vetoed_rle_set), "sm_n_exclusive": len(sm_exclusive_set),
    "check_i_disjoint": {"pass": check_i_pass, "overlap_count": len(overlap_i)},
    "check_ii_vetoed_present_and_accepted_in_dm": {
        "pass": check_ii_pass, "n_checked": len(vetoed_rle_set),
        "n_present_and_accepted": n_present_accepted, "n_present_not_accepted": n_present_not_accepted,
        "n_absent": n_absent, "exceptions": exceptions[:50],
    },
    "check_iii_union_completeness": {
        "pass": check_iii_pass, "n_union_inclusive": len(union_incl), "n_union_exclusive": len(union_excl),
        "n_lost": len(lost), "n_gained": len(gained),
    },
    "overall_pass": overall_pass,
}
out_path = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/matching_validation/step4_closure_result_final.json"
json.dump(result, open(out_path, "w"), indent=2)
print("wrote", out_path)
