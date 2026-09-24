"""
Synthetic-event self-checks for studies/m0m1j0_cms/variants.py.

No ROOT, no network, no cluster -- pure awkward/numpy/vector on hand-built
events, run directly:

    python studies/m0m1j0_cms/tests/test_variants_synthetic.py

Checks:
  1. V0_baseline reproduces select_event_selection_cutflow's own bare
     defaults exactly, on real synthetic events (not just spec equality --
     variants._self_check already checks the spec dict at import time;
     this test additionally checks the RESULT is identical).
  2. V1 (no muon iso) selects a muon V0 rejects for failing isolation.
  3. V2 (no jet-lepton cleaning) keeps a jet V0's cleaning removes, and
     the leading jet -- and therefore the mass -- can differ from V0.
  4. V3 (single-muon trigger) fires on an event whose only fired path is
     HLT_IsoMu24, which V0 would reject (V0 requires a double-muon path).
  5. Every non-V0 variant changes exactly one flag relative to V0 (also
     checked at import time by variants._self_check; re-asserted here for
     visibility in this test's own output).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402
import vector  # noqa: E402

vector.register_awkward()

from studies.m0m1j0_cms import selection, variants  # noqa: E402


def _mk_events(rows):
    """rows: list of dicts with muon/electron/jet lists + trigger flags."""
    return ak.Array(rows)


def check(cond, msg):
    if not cond:
        raise AssertionError(f"FAILED: {msg}")
    print(f"[PASS] {msg}")


def main():
    # One event: 2 muons (mu0 passes iso, mu1 FAILS iso: pfRelIso=0.30),
    # 2 light jets (jetA far from both muons pt=60; jetB close to mu1,
    # dR~0.05, pt=50 -- V0's cleaning removes jetB, V2 keeps it and it
    # becomes the new leading jet since 50<60... wait need jetB > jetA to
    # actually change the LEADING jet -- set jetB pt=90 (highest) so V2's
    # leading jet becomes jetB, changing the mass), only the DZ trigger set.
    row = {
        "run": 1, "luminosityBlock": 1, "event": 1,
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ": True,
        "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ": False,
        "HLT_IsoMu24": False,
        "HLT_IsoTkMu24": False,
        "Muon_pt": [40.0, 30.0], "Muon_eta": [0.5, -0.5], "Muon_phi": [0.0, 3.0],
        "Muon_mass": [0.105, 0.105], "Muon_mediumId": [True, True],
        "Muon_pfRelIso04_all": [0.05, 0.30],  # mu1 fails V0's iso cut
        "Muon_charge": [1, -1],
        "Electron_pt": [], "Electron_eta": [], "Electron_phi": [], "Electron_mass": [], "Electron_cutBased": [],
        "Jet_pt": [60.0, 90.0], "Jet_eta": [2.0, -0.5], "Jet_phi": [-2.0, 3.05],
        "Jet_mass": [8.0, 10.0], "Jet_jetId": [6, 6], "Jet_btagDeepFlavB": [0.01, 0.01],
    }
    events = _mk_events([row])

    # --- 1. V0 result matches bare-default call exactly ---
    v0_via_module = variants.run_variant("V0_baseline", events)
    v0_bare = selection.select_event_selection_cutflow(events)
    check(
        ak.to_numpy(v0_via_module["mass"]).tolist() == ak.to_numpy(v0_bare["mass"]).tolist(),
        "V0_baseline reproduces select_event_selection_cutflow's bare defaults exactly (mass)",
    )
    check(
        v0_via_module["n_after_ge1jet_after_cleaning"] == v0_bare["n_after_ge1jet_after_cleaning"],
        "V0_baseline reproduces bare defaults exactly (n_after_ge1jet_after_cleaning)",
    )
    # Under V0 (iso applied), mu1 fails -> only 1 muon selected -> event fails >=2mu
    check(v0_via_module["n_after_ge2mu"] == 0, "V0: only 1 muon passes iso, event fails >=2mu")
    check(v0_via_module["n_after_ge1jet_after_cleaning"] == 0, "V0: event fails overall (needs >=2mu)")

    # --- 2. V1: no iso -> both muons selected -> event now has >=2 muons ---
    v1 = variants.run_variant("V1_no_muon_iso", events)
    check(v1["n_after_ge2mu"] == 1, "V1: both muons pass (iso not required) -> event has >=2 muons")

    # --- 3. V2: no jet-lepton cleaning -> jetB (close to mu1) is NOT cleaned away ---
    # Under V0's cleaning, jetB (pt=90, close to mu1 dR~0.05<0.4) is removed,
    # leaving only jetA (pt=60) as the (sole, hence leading) light jet.
    # Under V2, both jets survive; jetB (pt=90) is now the leading jet.
    v0_full = selection.select_event_selection_cutflow(_mk_events([{**row, "Muon_pfRelIso04_all": [0.05, 0.05]}]))
    v2_full = variants.run_variant(
        "V2_no_jet_lepton_cleaning", _mk_events([{**row, "Muon_pfRelIso04_all": [0.05, 0.05]}])
    )
    v0_lead_jet_pt = ak.to_numpy(selection.leading_jet_pt(v0_full["obj_record"]["Jets"]))[0]
    v2_lead_jet_pt = ak.to_numpy(selection.leading_jet_pt(v2_full["obj_record"]["Jets"]))[0]
    check(v0_lead_jet_pt == 60.0, f"V0 (iso relaxed for this check only): leading jet is jetA (60 GeV, jetB cleaned away), got {v0_lead_jet_pt}")
    check(v2_lead_jet_pt == 90.0, f"V2: leading jet is jetB (90 GeV, not cleaned), got {v2_lead_jet_pt}")
    check(
        ak.to_numpy(v0_full["mass"])[0] != ak.to_numpy(v2_full["mass"])[0],
        "V2's mass differs from V0's for this event (different leading jet -> recomputed, not reweighted)",
    )

    # --- 4. V3: single-muon trigger fires on HLT_IsoMu24 only ---
    row_v3 = {**row, "Muon_pfRelIso04_all": [0.05, 0.05],
              "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ": False, "HLT_IsoMu24": True}
    events_v3 = _mk_events([row_v3])
    v0_on_v3event = selection.select_event_selection_cutflow(events_v3)
    v3_on_v3event = variants.run_variant("V3_single_muon_trigger", events_v3)
    check(v0_on_v3event["n_after_trigger"] == 0, "V0 rejects an event with only HLT_IsoMu24 fired (no DZ path)")
    check(v3_on_v3event["n_after_trigger"] == 1, "V3 accepts the same event via HLT_IsoMu24")

    # --- 5. exactly-one-flag-changed invariant (re-asserted here) ---
    v0_spec = variants.VARIANT_SPECS["V0_baseline"]
    for key, spec in variants.VARIANT_SPECS.items():
        if key == "V0_baseline":
            continue
        diffs = [k for k in spec if spec[k] != v0_spec[k]]
        check(len(diffs) == 1, f"{key} differs from V0 in exactly one flag ({diffs})")

    print("\nAll variants self-checks passed.")


if __name__ == "__main__":
    main()
