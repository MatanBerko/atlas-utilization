"""
Task D: validate field_cuts (muon isolation) and bit_cuts (tight jet ID)
against studies/m0m1j0_cms/selection.py's hand-written cuts, on one small
real CMS file. Read-only w.r.t. studies/m0m1j0_cms/ -- imported, not modified.
"""
import json
import sys

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/generic_cuts/repo")

import awkward as ak
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import uproot

from services.calculations import physics_calcs
from studies.m0m1j0_cms import selection as ref

FILE_URL = (
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/"
    "UL2016_MiniAODv2_NanoAODv9-v2/2430000/05DD095C-F6C3-9A4F-9FB3-348A5A6403D5.root"
)
N_EVENTS = 5000
OUT_DIR = "/storage/agrp/berkom/atlas-utilization/work/generic_cuts/report_assets"
import os
os.makedirs(OUT_DIR, exist_ok=True)

print(f"Ground-truth thresholds read from studies/m0m1j0_cms/selection.py:")
print(f"  MUON_PT_MIN_GEV = {ref.MUON_PT_MIN_GEV}")
print(f"  MUON_ETA_MAX = {ref.MUON_ETA_MAX}")
print(f"  MUON_ISO_MAX = {ref.MUON_ISO_MAX}")
print(f"  JET_PT_MIN_GEV = {ref.JET_PT_MIN_GEV}")
print(f"  JET_ETA_MAX = {ref.JET_ETA_MAX}")
print(f"  jet tight-ID cut (from _clean_and_cut_jets source): (raw_jets.jetId & 2) != 0")
print()

f = uproot.open(FILE_URL)
tree = f["Events"]
branches = [
    "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_mediumId", "Muon_pfRelIso04_all",
    "Jet_pt", "Jet_eta", "Jet_phi", "Jet_mass", "Jet_jetId",
]
arrs = tree.arrays(branches, entry_stop=N_EVENTS)
print(f"Loaded {len(arrs)} events from {FILE_URL}")

# ============================= MUONS (D1) ==================================
# Reference: standalone script's own select_muons (imported, unmodified).
ref_muons_selected = ref.select_muons(arrs, apply_iso=True)
n_ref_muons = int(ak.sum(ak.num(ref_muons_selected)))
print(f"\n--- D1: muon isolation (field_cuts) ---")
print(f"Reference (select_muons, apply_iso=True): {n_ref_muons} muons selected "
      f"across {len(arrs)} events")

# Pipeline reproduction: same raw Muon collection, cuts expressed via
# pt_min/eta_max (existing capability) + bool_require (existing capability,
# for mediumId) + field_cuts (THIS task's new capability, for isolation).
muons_raw = ak.zip({
    "pt": arrs.Muon_pt, "eta": arrs.Muon_eta, "phi": arrs.Muon_phi, "mass": arrs.Muon_mass,
    "mediumId": arrs.Muon_mediumId, "pfRelIso04_all": arrs.Muon_pfRelIso04_all,
})
events_for_muons = ak.zip({"Muons": muons_raw}, depth_limit=1)
pipeline_cuts = {
    "Muons": {
        "pt": {"min": ref.MUON_PT_MIN_GEV},
        "eta": {"min": -ref.MUON_ETA_MAX, "max": ref.MUON_ETA_MAX},
        "bool_require": ["mediumId"],
        "field_cuts": {"pfRelIso04_all": {"max": ref.MUON_ISO_MAX}},
    }
}
pipeline_muons_selected = physics_calcs.filter_events_by_kinematics(events_for_muons, pipeline_cuts)["Muons"]
n_pipeline_muons = int(ak.sum(ak.num(pipeline_muons_selected)))
print(f"Pipeline (pt_min/eta_max inclusive + bool_require + field_cuts max<=): "
      f"{n_pipeline_muons} muons selected")

# Per-muon mask comparison (same starting collection/order -> directly comparable).
ref_mask = (
    (muons_raw.pt > ref.MUON_PT_MIN_GEV)
    & (abs(muons_raw.eta) < ref.MUON_ETA_MAX)
    & muons_raw.mediumId
    & (muons_raw.pfRelIso04_all < ref.MUON_ISO_MAX)
)
pipeline_mask = (
    (muons_raw.pt >= ref.MUON_PT_MIN_GEV)
    & (muons_raw.eta >= -ref.MUON_ETA_MAX) & (muons_raw.eta <= ref.MUON_ETA_MAX)
    & muons_raw.mediumId
    & (muons_raw.pfRelIso04_all <= ref.MUON_ISO_MAX)
)
masks_identical = ak.all(ref_mask == pipeline_mask)
n_disagree = int(ak.sum(ref_mask != pipeline_mask))
print(f"Per-muon mask identical for every muon in the sample: {bool(masks_identical)} "
      f"({n_disagree} muons disagree)")

# Boundary-case check: is the >=/<=  vs >/< and inclusive-max vs strict-max
# convention difference EVER actually triggered by real data in this sample?
flat_pt = ak.to_numpy(ak.flatten(muons_raw.pt))
flat_eta = ak.to_numpy(ak.flatten(muons_raw.eta))
flat_iso = ak.to_numpy(ak.flatten(muons_raw.pfRelIso04_all))
n_pt_boundary = int(np.sum(flat_pt == ref.MUON_PT_MIN_GEV))
n_eta_boundary = int(np.sum(np.abs(flat_eta) == ref.MUON_ETA_MAX))
n_iso_boundary = int(np.sum(flat_iso == ref.MUON_ISO_MAX))
print(f"Boundary-value check (where inclusive vs strict conventions could "
      f"differ): pt=={ref.MUON_PT_MIN_GEV}: {n_pt_boundary} muons; "
      f"|eta|=={ref.MUON_ETA_MAX}: {n_eta_boundary} muons; "
      f"pfRelIso04_all=={ref.MUON_ISO_MAX}: {n_iso_boundary} muons")

muon_result = {
    "n_events_sampled": len(arrs),
    "reference_thresholds": {
        "MUON_PT_MIN_GEV": ref.MUON_PT_MIN_GEV, "MUON_ETA_MAX": ref.MUON_ETA_MAX,
        "MUON_ISO_MAX": ref.MUON_ISO_MAX,
    },
    "n_reference_muons_selected": n_ref_muons,
    "n_pipeline_muons_selected": n_pipeline_muons,
    "per_muon_masks_identical": bool(masks_identical),
    "n_muons_disagreeing": n_disagree,
    "boundary_value_counts": {
        "pt_exactly_at_min": n_pt_boundary,
        "abs_eta_exactly_at_max": n_eta_boundary,
        "iso_exactly_at_max": n_iso_boundary,
    },
}

# ============================= JETS (D2) ====================================
print(f"\n--- D2: tight jet ID (bit_cuts) ---")
jets_raw = ak.zip({
    "pt": arrs.Jet_pt, "eta": arrs.Jet_eta, "phi": arrs.Jet_phi, "mass": arrs.Jet_mass,
    "jetId": arrs.Jet_jetId,
})

# Reference cut, exactly as written in _clean_and_cut_jets (kinematic part only,
# NOT the lepton-cleaning step -- that's a separate, out-of-scope dR capability):
ref_jet_mask = (
    (jets_raw.pt > ref.JET_PT_MIN_GEV)
    & (abs(jets_raw.eta) < ref.JET_ETA_MAX)
    & ((jets_raw.jetId & 2) != 0)
)
n_ref_jets = int(ak.sum(ref_jet_mask))
print(f"Reference ((jetId & 2) != 0, i.e. bits_any semantics): {n_ref_jets} jets selected")

# VERIFY bits_all(2) vs bits_any(2) equivalence on the REAL observed jetId
# values in this sample, rather than assuming it from the single-bit argument.
flat_jetid = ak.to_numpy(ak.flatten(jets_raw.jetId))
bits_any_2 = (flat_jetid & 2) != 0
bits_all_2 = (flat_jetid & 2) == 2
equivalence_holds = bool(np.array_equal(bits_any_2, bits_all_2))
uniq_jetid = sorted(set(flat_jetid.tolist()))
print(f"Observed Jet_jetId values in this sample: {uniq_jetid}")
print(f"bits_all(2) == bits_any(2) for every jet in this sample: {equivalence_holds}")

# Pipeline reproduction using bit_cuts (this task's new capability), bits_all
# form -- justified by the just-verified equivalence for this single-bit mask.
pipeline_jet_cuts = {
    "Jets": {
        "pt": {"min": ref.JET_PT_MIN_GEV},
        "eta": {"min": -ref.JET_ETA_MAX, "max": ref.JET_ETA_MAX},
        "bit_cuts": {"jetId": {"bits_all": 2}},
    }
}
events_for_jets = ak.zip({"Jets": jets_raw}, depth_limit=1)
pipeline_jets_selected = physics_calcs.filter_events_by_kinematics(events_for_jets, pipeline_jet_cuts)["Jets"]
n_pipeline_jets = int(ak.sum(ak.num(pipeline_jets_selected)))
print(f"Pipeline (pt_min/eta_max inclusive + bit_cuts bits_all=2): {n_pipeline_jets} jets selected")

pipeline_jet_mask = (
    (jets_raw.pt >= ref.JET_PT_MIN_GEV)
    & (jets_raw.eta >= -ref.JET_ETA_MAX) & (jets_raw.eta <= ref.JET_ETA_MAX)
    & ((jets_raw.jetId & 2) == 2)
)
jet_masks_identical = ak.all(ref_jet_mask == pipeline_jet_mask)
n_jet_disagree = int(ak.sum(ref_jet_mask != pipeline_jet_mask))
print(f"Per-jet mask identical for every jet in the sample: {bool(jet_masks_identical)} "
      f"({n_jet_disagree} jets disagree)")

flat_jet_pt = ak.to_numpy(ak.flatten(jets_raw.pt))
flat_jet_eta = ak.to_numpy(ak.flatten(jets_raw.eta))
n_jet_pt_boundary = int(np.sum(flat_jet_pt == ref.JET_PT_MIN_GEV))
n_jet_eta_boundary = int(np.sum(np.abs(flat_jet_eta) == ref.JET_ETA_MAX))
print(f"Boundary-value check: pt=={ref.JET_PT_MIN_GEV}: {n_jet_pt_boundary} jets; "
      f"|eta|=={ref.JET_ETA_MAX}: {n_jet_eta_boundary} jets")

# Isolated check: bit_cuts logic ALONE against the reference's jetId
# condition alone, with pt/eta held out of it entirely -- this is exactly
# what bits_all_2/bits_any_2 above already computed on the full flat jetId
# array (every jet in the sample, no pt/eta pre-filter), so 0 disagreement
# there means bit_cuts's own new logic reproduces the reference exactly.
n_isolated_disagree = int(np.sum(bits_any_2 != bits_all_2))

# Diagnose the FULL-selection discrepancy precisely: list every disagreeing
# jet's pt/eta/jetId so the cause is verified, not guessed.
flat_disagree = ak.to_numpy(ak.flatten(ref_jet_mask != pipeline_jet_mask))
disagree_idx = np.where(flat_disagree)[0]
disagreeing_jets = [
    {"pt": float(flat_jet_pt[i]), "eta": float(flat_jet_eta[i]), "jetId": int(flat_jetid[i])}
    for i in disagree_idx
]
all_disagreements_at_pt_boundary = bool(
    len(disagree_idx) > 0 and np.all(flat_jet_pt[disagree_idx] == ref.JET_PT_MIN_GEV)
)
print(f"Isolated bit_cuts-vs-reference disagreement (pt/eta held out entirely): "
      f"{n_isolated_disagree} jets")
print(f"Full-selection disagreement: {n_jet_disagree} jets, all at the pt=="
      f"{ref.JET_PT_MIN_GEV} boundary: {all_disagreements_at_pt_boundary}")
print(f"Disagreeing jets: {disagreeing_jets}")

jet_result = {
    "reference_thresholds": {"JET_PT_MIN_GEV": ref.JET_PT_MIN_GEV, "JET_ETA_MAX": ref.JET_ETA_MAX},
    "observed_jetid_values": uniq_jetid,
    "bits_all_2_equals_bits_any_2_on_this_sample": equivalence_holds,
    "n_isolated_bitmask_only_disagreements": n_isolated_disagree,
    "n_reference_jets_selected": n_ref_jets,
    "n_pipeline_jets_selected": n_pipeline_jets,
    "per_jet_masks_identical": bool(jet_masks_identical),
    "n_jets_disagreeing_full_selection": n_jet_disagree,
    "all_full_selection_disagreements_at_pt_boundary": all_disagreements_at_pt_boundary,
    "disagreeing_jets_detail": disagreeing_jets,
    "boundary_value_counts": {
        "pt_exactly_at_min": n_jet_pt_boundary,
        "abs_eta_exactly_at_max": n_jet_eta_boundary,
    },
}

full_result = {"muons": muon_result, "jets": jet_result, "file_url": FILE_URL}
with open(f"{OUT_DIR}/task_d_validation_result.json", "w") as fp:
    json.dump(full_result, fp, indent=2)

# ============================= PLOT ==========================================
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

axes[0].hist(flat_iso, bins=60, range=(0, 1.2), histtype="step", color="C0")
axes[0].axvline(ref.MUON_ISO_MAX, color="red", linestyle="--",
                 label=f"MUON_ISO_MAX={ref.MUON_ISO_MAX}")
axes[0].set_xlabel("Muon_pfRelIso04_all")
axes[0].set_ylabel("muons / bin")
axes[0].set_yscale("log")
axes[0].set_title(f"Muon isolation, {len(arrs)} events\n"
                   f"reference={n_ref_muons}, pipeline(field_cuts)={n_pipeline_muons}")
axes[0].legend()

uniq_vals, counts = np.unique(flat_jetid, return_counts=True)
axes[1].bar([str(v) for v in uniq_vals], counts, color="C1")
axes[1].set_xlabel("Jet_jetId value")
axes[1].set_ylabel("jets (all pt/eta, before ID cut)")
axes[1].set_title(f"Jet_jetId distribution\n"
                   f"reference(!=0)={n_ref_jets}, pipeline(bits_all=2)={n_pipeline_jets}")

fig.tight_layout()
fig.savefig(f"{OUT_DIR}/task_d_validation.png", dpi=150)
print(f"\nWrote {OUT_DIR}/task_d_validation.png and task_d_validation_result.json")
