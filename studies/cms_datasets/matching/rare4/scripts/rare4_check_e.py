"""
rare4 task, Step 2 check (e): human-readable table of 10 accepted events
with N>4 (rejected) and 10 accepted events with N<=4 but more than 4
light jets (kept, ALL objects retained -- showing the resulting capped
display label). Independently re-derives the accepted population from
raw NanoAOD data (re-reading via xrootd, re-applying golden JSON/own-
trigger/object-selection/matched-mode acceptance -- only PRE-EXISTING
shared functions, never the new rare4 code) across all 4 pilot files,
pooling examples until each quota (10+10) is filled.
"""
import sys

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/rare4_pilot_pinned/repo")

import awkward as ak
import numpy as np

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter
from services.parsing.trigger_requirements import apply_trigger_requirement
from services.calculations import physics_calcs
from studies.m0m1j0_cms import selection
from studies.cms_datasets.cluster.datasets_records import VETO_ORDER
from studies.cms_datasets.cluster.run_dataset_on_file import (
    TRIGGER_PATHS_BY_DATASET, BASE_OBJECT_BRANCHES, MATCHED_MODE_EXTRA_BRANCHES,
    TRIGOBJ_BIT_TRKISOVVL, TRIGOBJ_BIT_ISO,
    DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV,
    SINGLEMUON_MATCHED_MIN_MUONS, SINGLEMUON_MATCHED_PT_MIN_GEV,
    SINGLEMUON_MATCHED_TRIGGER_PATHS,
    matched_acceptance_mask, DEFAULT_VALIDATED_RUNS_JSON,
    resolve_file_url, read_events,
)

PILOT_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/rare4_pilot"
PILOT_FILES = [
    ("DoubleMuon", 30522, 0, "DoubleMuon_30522_0_matched"),
    ("DoubleMuon", 30555, 0, "DoubleMuon_30555_0_matched"),
    ("SingleMuon", 30530, 0, "SingleMuon_30530_0_matched"),
    ("SingleMuon", 30563, 0, "SingleMuon_30563_0_matched"),
]

rejected_examples = []   # N>4 -> up to 10
many_jets_examples = []  # N<=4 but >4 light jets -> up to 10

for dataset_label, record_id, file_index, run_dir in PILOT_FILES:
    print(f"\n=== {dataset_label} record {record_id} file {file_index} ===")
    if dataset_label == "SingleMuon":
        own_paths = SINGLEMUON_MATCHED_TRIGGER_PATHS
    else:
        own_paths = TRIGGER_PATHS_BY_DATASET[dataset_label]
    higher_priority = VETO_ORDER[:VETO_ORDER.index(dataset_label)]
    veto_paths_by_label = {h: TRIGGER_PATHS_BY_DATASET[h] for h in higher_priority}
    all_trigger_branches = list(own_paths)
    for paths in veto_paths_by_label.values():
        all_trigger_branches.extend(paths)
    required_branches = (list(BASE_OBJECT_BRANCHES) + sorted(set(all_trigger_branches))
                          + list(MATCHED_MODE_EXTRA_BRANCHES))

    file_url = resolve_file_url(record_id, file_index)
    print(f"Reading {file_url}")
    events = read_events(file_url, required_branches)

    validated_runs = ValidatedRunsFilter(DEFAULT_VALIDATED_RUNS_JSON)
    events_golden, _ = apply_validated_runs_filter(events, validated_runs)
    events_triggered, _ = apply_trigger_requirement(events_golden, {"mode": "any", "paths": own_paths})

    muons = selection.select_muons(events_triggered, extra_fields={"charge": events_triggered.Muon_charge})
    electrons = selection.select_electrons(events_triggered)
    jets = selection.select_and_split_jets(events_triggered, muons, electrons, apply_lepton_cleaning=True)

    trigobj = ak.zip({
        "pt": events_triggered.TrigObj_pt, "eta": events_triggered.TrigObj_eta,
        "phi": events_triggered.TrigObj_phi, "id": events_triggered.TrigObj_id,
        "filterBits": events_triggered.TrigObj_filterBits,
    })
    if dataset_label == "DoubleMuon":
        required_bit, min_matched, leading_pt_min = (
            TRIGOBJ_BIT_TRKISOVVL, DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV)
    else:
        required_bit, min_matched, leading_pt_min = (
            TRIGOBJ_BIT_ISO, SINGLEMUON_MATCHED_MIN_MUONS, SINGLEMUON_MATCHED_PT_MIN_GEV)
    keep = matched_acceptance_mask(muons, trigobj, required_bit, min_matched, leading_pt_min)

    acc_electrons = electrons[keep]
    acc_muons = muons[keep]
    acc_light_jets = jets["Jets"][keep]
    acc_bjets = jets["BJets"][keep]

    n_e = ak.to_numpy(ak.num(acc_electrons, axis=1))
    n_m = ak.to_numpy(ak.num(acc_muons, axis=1))
    n_b = ak.to_numpy(ak.num(acc_bjets, axis=1))
    n_j = ak.to_numpy(ak.num(acc_light_jets, axis=1))
    n_lepton_bjet = n_e + n_m + n_b

    def full_list_for(i):
        items = []
        for pt in ak.to_list(acc_electrons.pt[i]):
            items.append(("Electron", pt))
        for pt in ak.to_list(acc_muons.pt[i]):
            items.append(("Muon", pt))
        for pt in ak.to_list(acc_bjets.pt[i]):
            items.append(("BJet", pt))
        for pt in ak.to_list(acc_light_jets.pt[i]):
            items.append(("Jet", pt))
        return sorted(items, key=lambda x: -x[1])

    def capped_label_for(i):
        raw_fs = f"{n_e[i]}e_{n_m[i]}m_{n_j[i]}j_0g_0t_{n_b[i]}b"
        return physics_calcs.limit_particles_in_fs(raw_fs, 4)

    if len(rejected_examples) < 10:
        gt4_idx = np.where(n_lepton_bjet > 4)[0]
        for i in gt4_idx:
            if len(rejected_examples) >= 10:
                break
            i = int(i)
            rejected_examples.append({
                "dataset_label": dataset_label, "record_id": record_id, "file_index": file_index,
                "event_index": i, "N": int(n_lepton_bjet[i]),
                "e": int(n_e[i]), "m": int(n_m[i]), "b": int(n_b[i]), "j": int(n_j[i]),
                "full_list": full_list_for(i),
                "capped_label": capped_label_for(i),
            })

    if len(many_jets_examples) < 10:
        cand_idx = np.where((n_lepton_bjet <= 4) & (n_j > 4))[0]
        for i in cand_idx:
            if len(many_jets_examples) >= 10:
                break
            i = int(i)
            many_jets_examples.append({
                "dataset_label": dataset_label, "record_id": record_id, "file_index": file_index,
                "event_index": i, "N": int(n_lepton_bjet[i]),
                "e": int(n_e[i]), "m": int(n_m[i]), "b": int(n_b[i]), "j": int(n_j[i]),
                "full_list": full_list_for(i),
                "capped_label": capped_label_for(i),
            })

print()
print(f"Collected {len(rejected_examples)} rejected (N>4) examples, "
      f"{len(many_jets_examples)} kept-with->4-light-jets examples for check (e)")

lines = []
lines.append("rare4 task, Step 2 check (e): example events\n")
lines.append("=" * 70)
lines.append(f"\nPART 1: {len(rejected_examples)} accepted events with N (e+m+b) > 4 -- REJECTED from rare4\n")
for ex in rejected_examples:
    lines.append(f"--- {ex['dataset_label']} record {ex['record_id']} file {ex['file_index']} "
                  f"event_index {ex['event_index']}: N={ex['N']} (e={ex['e']},m={ex['m']},b={ex['b']}), "
                  f"{ex['j']} light jets -- true final state (uncapped)='{ex['e']}e_{ex['m']}m_{ex['j']}j_{ex['b']}b' "
                  f"-> REJECTED (capped display label would have been '{ex['capped_label']}') ---")
    for typ, pt in ex["full_list"]:
        lines.append(f"    {typ:10s} pT={pt:8.3f}")
    lines.append("")

lines.append("=" * 70)
lines.append(f"\nPART 2: {len(many_jets_examples)} accepted events with N<=4 but >4 light jets "
              f"-- KEPT, ALL objects retained (rare4 never truncates)\n")
for ex in many_jets_examples:
    lines.append(f"--- {ex['dataset_label']} record {ex['record_id']} file {ex['file_index']} "
                  f"event_index {ex['event_index']}: N={ex['N']} (e={ex['e']},m={ex['m']},b={ex['b']}), "
                  f"{ex['j']} light jets -> KEPT, all {len(ex['full_list'])} objects retained; "
                  f"display label = '{ex['capped_label']}' (light jets capped to '4j' in the name, "
                  f"but all {ex['j']} are still used in the mass combinations) ---")
    for typ, pt in ex["full_list"]:
        lines.append(f"    {typ:10s} pT={pt:8.3f}  <-- KEPT")
    lines.append("")

table_text = "\n".join(lines)
print("\n" + table_text)

out_path = f"{PILOT_BASE}/step2e_rare4_examples.txt"
with open(out_path, "w") as f:
    f.write(table_text)
print(f"\nwrote {out_path}")
