"""
nonjet4 task, Step 2 checks (d) and (f), plus the exclusive half of check (c).

Independently re-derives, straight from the raw NanoAOD files (re-reading
via xrootd, re-applying golden JSON / own-trigger / object selection /
matched-mode acceptance -- i.e. everything needed to reconstruct "the
accepted events" -- but NONE of the new nonjet4 shard-writing/rejection
code added in Step 1), the per-event N = electrons+muons+b-jets count for
every accepted event in all 4 pilot files. Only shared/pre-existing
functions are imported from run_dataset_on_file.py (matched_acceptance_mask,
TRIGGER_PATHS_BY_DATASET, etc.) -- never the new nonjet4-specific code.

check (d) HARD: independent count of accepted events with N>4 must equal
job_metadata.json's nonjet4_diagnostics.n_rejected_gt4_lepton_bjet.

check (c, exclusive half) HARD: independent count of EXCLUSIVE accepted
events with N>4 must equal (n_exclusive - nonjet4's exclusive accepted
count), i.e. nonjet4 exclusive accepted == top4/normal exclusive accepted
minus exclusive-and-rejected events.

check (f): prints + saves a human-readable table of 10 accepted events
with N>4 (full object list, shown as rejected) and 10 accepted events with
N<=4 but >4 objects in total (full list and the 4 kept, light jets
dropped), pooled across the 4 pilot files.
"""
import sys
import json

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/nonjet4_pilot_pinned/repo")

import awkward as ak
import numpy as np

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter
from services.parsing.trigger_requirements import apply_trigger_requirement
from studies.m0m1j0_cms import selection
from studies.cms_datasets.cluster.datasets_records import VETO_ORDER
from studies.cms_datasets.cluster.run_dataset_on_file import (
    TRIGGER_PATHS_BY_DATASET, BASE_OBJECT_BRANCHES, MATCHED_MODE_EXTRA_BRANCHES,
    TRIGOBJ_BIT_TRKISOVVL, TRIGOBJ_BIT_ISO,
    DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV,
    SINGLEMUON_MATCHED_MIN_MUONS, SINGLEMUON_MATCHED_PT_MIN_GEV,
    SINGLEMUON_MATCHED_TRIGGER_PATHS,
    matched_acceptance_mask, build_top4_object_record, DEFAULT_VALIDATED_RUNS_JSON,
    resolve_file_url, read_events,
)

PILOT_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/nonjet4_pilot"
PILOT_FILES = [
    ("DoubleMuon", 30522, 0, "DoubleMuon_30522_0_matched"),
    ("DoubleMuon", 30555, 0, "DoubleMuon_30555_0_matched"),
    ("SingleMuon", 30530, 0, "SingleMuon_30530_0_matched"),
    ("SingleMuon", 30563, 0, "SingleMuon_30563_0_matched"),
]

check_d_all_pass = True
check_c_excl_all_pass = True
rejected_examples = []   # N>4 -> up to 10
truncated_examples = []  # N<=4 but total>4 -> up to 10

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
    n_events_triggered = len(events_triggered)

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

    # is_exclusive_pretrigger, aligned to events_triggered -- same logic as
    # run_dataset_on_file.py's main() (independently re-derived here).
    is_exclusive_pretrigger = np.ones(n_events_triggered, dtype=bool)
    if dataset_label == "SingleMuon":
        doublemuon_fired = np.zeros(n_events_triggered, dtype=bool)
        for path in TRIGGER_PATHS_BY_DATASET["DoubleMuon"]:
            doublemuon_fired |= ak.to_numpy(events_triggered[path]).astype(bool)
        doublemuon_accepted = matched_acceptance_mask(
            muons, trigobj, TRIGOBJ_BIT_TRKISOVVL,
            DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV,
        )
        is_exclusive_pretrigger = ~(doublemuon_fired & doublemuon_accepted)
    is_exclusive_selected = is_exclusive_pretrigger[keep]

    acc_electrons = electrons[keep]
    acc_muons = muons[keep]
    acc_light_jets = jets["Jets"][keep]
    acc_bjets = jets["BJets"][keep]

    n_e = ak.to_numpy(ak.num(acc_electrons, axis=1))
    n_m = ak.to_numpy(ak.num(acc_muons, axis=1))
    n_b = ak.to_numpy(ak.num(acc_bjets, axis=1))
    n_j = ak.to_numpy(ak.num(acc_light_jets, axis=1))
    n_lepton_bjet = n_e + n_m + n_b
    n_total = n_lepton_bjet + n_j

    n_accepted = len(acc_electrons)
    indep_n_rejected = int((n_lepton_bjet > 4).sum())
    indep_n_rejected_excl = int(((n_lepton_bjet > 4) & is_exclusive_selected).sum())
    n_exclusive_accepted = int(is_exclusive_selected.sum())

    meta = json.load(open(f"{PILOT_BASE}/{run_dir}/job_metadata.json"))
    nj4 = meta["nonjet4_diagnostics"]
    meta_n_rejected = nj4["n_rejected_gt4_lepton_bjet"]
    meta_n_exclusive = meta["n_exclusive"]
    nj4_excl_accepted = sum(nj4["final_state_label_event_counts_exclusive"].values())

    print(f"  n_accepted={n_accepted} (meta n_after_gate={meta['n_after_gate']})")
    ok_d = (indep_n_rejected == meta_n_rejected)
    print(f"  check (d): independent N>4 count={indep_n_rejected} vs meta n_rejected={meta_n_rejected} "
          f"-> {'PASS' if ok_d else 'FAIL'}")
    check_d_all_pass = check_d_all_pass and ok_d

    expected_nj4_excl = n_exclusive_accepted - indep_n_rejected_excl
    ok_c_excl = (nj4_excl_accepted == expected_nj4_excl == meta_n_exclusive - indep_n_rejected_excl)
    print(f"  check (c, exclusive): exclusive accepted={n_exclusive_accepted} (meta n_exclusive={meta_n_exclusive}), "
          f"independent exclusive-and-N>4={indep_n_rejected_excl}, expected nonjet4 exclusive accepted="
          f"{expected_nj4_excl}, actual nonjet4 exclusive accepted (from shard FS sums)={nj4_excl_accepted} "
          f"-> {'PASS' if ok_c_excl else 'FAIL'}")
    check_c_excl_all_pass = check_c_excl_all_pass and ok_c_excl

    # ---- check (f): collect example events ----
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

    if len(rejected_examples) < 10:
        gt4_idx = np.where(n_lepton_bjet > 4)[0]
        for i in gt4_idx:
            if len(rejected_examples) >= 10:
                break
            i = int(i)
            rejected_examples.append({
                "dataset_label": dataset_label, "record_id": record_id, "file_index": file_index,
                "event_index": i, "N": int(n_lepton_bjet[i]), "n_total_objects": int(n_total[i]),
                "full_list": full_list_for(i),
            })

    if len(truncated_examples) < 10:
        t4m, t4e, t4j, t4b, _ = build_top4_object_record(acc_muons, acc_electrons, acc_light_jets, acc_bjets)
        cand_idx = np.where((n_lepton_bjet <= 4) & (n_total > 4))[0]
        for i in cand_idx:
            if len(truncated_examples) >= 10:
                break
            i = int(i)
            kept = []
            for pt in ak.to_list(t4e.pt[i]):
                kept.append(("Electron", pt))
            for pt in ak.to_list(t4m.pt[i]):
                kept.append(("Muon", pt))
            for pt in ak.to_list(t4b.pt[i]):
                kept.append(("BJet", pt))
            for pt in ak.to_list(t4j.pt[i]):
                kept.append(("Jet", pt))
            truncated_examples.append({
                "dataset_label": dataset_label, "record_id": record_id, "file_index": file_index,
                "event_index": i, "N": int(n_lepton_bjet[i]), "n_total_objects": int(n_total[i]),
                "full_list": full_list_for(i), "kept_list": kept,
            })

print()
print(f"Check (d) overall: {'PASS' if check_d_all_pass else 'FAIL'}")
print(f"Check (c, exclusive half) overall: {'PASS' if check_c_excl_all_pass else 'FAIL'}")
print(f"Collected {len(rejected_examples)} rejected (N>4) examples, {len(truncated_examples)} "
      f"kept-but-truncated (N<=4, total>4) examples for check (f)")

lines = []
lines.append("nonjet4 task, Step 2 check (f): example events\n")
lines.append("=" * 70)
lines.append(f"\nPART 1: {len(rejected_examples)} accepted events with N (e+m+b) > 4 -- REJECTED from nonjet4\n")
for ex in rejected_examples:
    lines.append(f"--- {ex['dataset_label']} record {ex['record_id']} file {ex['file_index']} "
                  f"event_index {ex['event_index']}: N={ex['N']}, total_objects={ex['n_total_objects']} "
                  f"-> REJECTED ---")
    for typ, pt in ex["full_list"]:
        lines.append(f"    {typ:10s} pT={pt:8.3f}")
    lines.append("")

lines.append("=" * 70)
lines.append(f"\nPART 2: {len(truncated_examples)} accepted events with N<=4 but >4 total objects "
              f"-- KEPT, light jets dropped\n")
for ex in truncated_examples:
    lines.append(f"--- {ex['dataset_label']} record {ex['record_id']} file {ex['file_index']} "
                  f"event_index {ex['event_index']}: N={ex['N']}, total_objects={ex['n_total_objects']} "
                  f"-> KEPT (padded to 4) ---")
    lines.append("  Full object list:")
    for typ, pt in ex["full_list"]:
        lines.append(f"    {typ:10s} pT={pt:8.3f}")
    lines.append(f"  KEPT ({len(ex['kept_list'])} objects):")
    for typ, pt in ex["kept_list"]:
        lines.append(f"    {typ:10s} pT={pt:8.3f}  <-- KEPT")
    lines.append("")

table_text = "\n".join(lines)
print("\n" + table_text)

out_path = f"{PILOT_BASE}/step2f_nonjet4_examples.txt"
with open(out_path, "w") as f:
    f.write(table_text)
print(f"\nwrote {out_path}")

overall = check_d_all_pass and check_c_excl_all_pass
sys.exit(0 if overall else 1)
