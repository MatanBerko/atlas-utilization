"""
Top-4 task, Step 2 check (d): human-readable table for 10 accepted events
that had more than 4 objects -- full object list (type, pT) and the 4
kept, so the priority rule (leptons by pT, then b-jets by pT, then light
jets by pT) can be checked by eye. Uses DoubleMuon record 30522 file 0
(the pinned commit's own pilot run) directly, re-deriving the exact same
accepted-event population the production job used (same functions,
same commit), then finds 10 such events and prints the table.
"""
import sys
sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/top4_pilot_pinned/repo")

import awkward as ak
import numpy as np

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter
from services.parsing.trigger_requirements import apply_trigger_requirement
from studies.m0m1j0_cms import selection
from studies.cms_datasets.cluster.run_dataset_on_file import (
    TRIGGER_PATHS_BY_DATASET, BASE_OBJECT_BRANCHES, MATCHED_MODE_EXTRA_BRANCHES,
    TRIGOBJ_BIT_TRKISOVVL, DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV,
    matched_acceptance_mask, build_top4_object_record, DEFAULT_VALIDATED_RUNS_JSON,
    resolve_file_url, read_events,
)

DATASET_LABEL = "DoubleMuon"
RECORD_ID = 30522
FILE_INDEX = 0

own_paths = TRIGGER_PATHS_BY_DATASET[DATASET_LABEL]
required_branches = list(BASE_OBJECT_BRANCHES) + sorted(set(own_paths)) + list(MATCHED_MODE_EXTRA_BRANCHES)

file_url = resolve_file_url(RECORD_ID, FILE_INDEX)
print(f"Reading {file_url}")
events = read_events(file_url, required_branches)

validated_runs = ValidatedRunsFilter(DEFAULT_VALIDATED_RUNS_JSON)
events_golden, _ = apply_validated_runs_filter(events, validated_runs)
events_triggered, _ = apply_trigger_requirement(events_golden, {"mode": "any", "paths": own_paths})

muons = selection.select_muons(events_triggered, extra_fields={"charge": events_triggered.Muon_charge})
electrons = selection.select_electrons(events_triggered)
jets = selection.select_and_split_jets(events_triggered, muons, electrons, apply_lepton_cleaning=True)

trigobj = ak.zip({
    "pt": events_triggered.TrigObj_pt, "eta": events_triggered.TrigObj_eta, "phi": events_triggered.TrigObj_phi,
    "id": events_triggered.TrigObj_id, "filterBits": events_triggered.TrigObj_filterBits,
})
keep = matched_acceptance_mask(muons, trigobj, TRIGOBJ_BIT_TRKISOVVL,
                                 DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV)

acc_muons = muons[keep]
acc_electrons = electrons[keep]
acc_light_jets = jets["Jets"][keep]
acc_bjets = jets["BJets"][keep]

top4_muons, top4_electrons, top4_light_jets, top4_bjets, n_original = build_top4_object_record(
    acc_muons, acc_electrons, acc_light_jets, acc_bjets
)

gt4_event_indices = np.where(n_original > 4)[0]
print(f"{len(gt4_event_indices)} accepted events have >4 selected objects; showing the first 10.\n")

lines = []
for i in gt4_event_indices[:10]:
    i = int(i)
    lines.append(f"=== Event index {i} (accepted-population row) -- {n_original[i]} original objects ===")
    full_list = []
    for pt in ak.to_list(acc_electrons.pt[i]):
        full_list.append(("Electron", pt))
    for pt in ak.to_list(acc_muons.pt[i]):
        full_list.append(("Muon", pt))
    for pt in ak.to_list(acc_bjets.pt[i]):
        full_list.append(("BJet", pt))
    for pt in ak.to_list(acc_light_jets.pt[i]):
        full_list.append(("Jet", pt))
    full_list_sorted_by_pt = sorted(full_list, key=lambda x: -x[1])
    lines.append("  Full object list (type, pT), sorted by pT for readability:")
    for typ, pt in full_list_sorted_by_pt:
        lines.append(f"    {typ:10s} pT={pt:8.3f}")

    kept_list = []
    for pt in ak.to_list(top4_electrons.pt[i]):
        kept_list.append(("Electron", pt))
    for pt in ak.to_list(top4_muons.pt[i]):
        kept_list.append(("Muon", pt))
    for pt in ak.to_list(top4_bjets.pt[i]):
        kept_list.append(("BJet", pt))
    for pt in ak.to_list(top4_light_jets.pt[i]):
        kept_list.append(("Jet", pt))
    lines.append(f"  KEPT (top-4, priority lepton>bjet>jet, by pT within each tier): {len(kept_list)} objects")
    for typ, pt in kept_list:
        lines.append(f"    {typ:10s} pT={pt:8.3f}  <-- KEPT")
    lines.append("")

table_text = "\n".join(lines)
print(table_text)

out_path = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/top4_pilot/step2d_top4_examples.txt"
with open(out_path, "w") as f:
    f.write(f"Top-4 task, Step 2 check (d): 10 accepted DoubleMuon events (record {RECORD_ID}, file {FILE_INDEX})\n")
    f.write(f"with more than 4 selected objects, full object list vs. the 4 kept by the priority rule\n")
    f.write(f"(leptons by pT, then b-jets by pT, then light jets by pT).\n\n")
    f.write(table_text)
print(f"\nwrote {out_path}")
