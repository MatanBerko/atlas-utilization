"""
Synthetic-event self-checks for studies/m0m1j0_cms/selection.py.

No ROOT, no network, no cluster -- pure awkward/numpy/vector on
hand-built events with known expected outcomes. Run directly:

    python studies/m0m1j0_cms/tests/test_selection_synthetic.py

This exists because selection.py cannot be exercised against a real CMS
file on this (Windows, no XRootD) dev machine -- see
studies/m0m1j0_cms/design_checks/common.py's own docstring. It is the one
piece of the Step-1 pipeline this session CAN verify without the cluster;
it does not substitute for running the real pilot on real files.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from studies.m0m1j0_cms import selection  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def make_events():
    """3 synthetic events, NanoAOD-shaped (jagged per-object branches):

    Event 0: 2 good muons + 1 good jet, well-isolated from muons -> should
             survive fully; hand-computed mass checked against
             vector.zip's own answer for a known back-to-back-ish config.
    Event 1: only 1 muon passing pt/eta/id/iso -> must be dropped
             (ge2mu fails) even though a raw second muon exists but fails
             the iso cut.
    Event 2: 2 good muons + 1 jet that sits ON TOP of the leading muon
             (same eta/phi) -> jet must be cleaned away by the deltaR<0.4
             lepton cleaning, leaving 0 selected jets (ge1jet fails).
    """
    events = ak.Array({
        "run": [1, 1, 1],
        "luminosityBlock": [1, 1, 1],
        "event": [1, 2, 3],
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ": [True, True, True],
        "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ": [False, False, False],
        "Muon_pt": [[60.0, 40.0], [60.0, 5.0], [60.0, 40.0]],
        "Muon_eta": [[0.1, -0.2], [0.1, -0.2], [0.1, -0.2]],
        "Muon_phi": [[0.0, 1.0], [0.0, 1.0], [0.0, 1.0]],
        "Muon_mass": [[0.105, 0.105], [0.105, 0.105], [0.105, 0.105]],
        "Muon_mediumId": [[True, True], [True, False], [True, True]],
        "Muon_pfRelIso04_all": [[0.05, 0.05], [0.05, 0.20], [0.05, 0.05]],
        "Electron_pt": [[], [], []],
        "Electron_eta": [[], [], []],
        "Electron_phi": [[], [], []],
        "Electron_mass": [[], [], []],
        "Electron_cutBased": [[], [], []],
        "Jet_pt": [[80.0], [80.0], [80.0]],
        "Jet_eta": [[1.5], [1.5], [0.1]],
        "Jet_phi": [[2.5], [2.5], [0.0]],
        "Jet_mass": [[8.0], [8.0], [8.0]],
        "Jet_jetId": [[6], [6], [6]],
        "Jet_btagDeepFlavB": [[0.01], [0.01], [0.01]],
    })
    return events


def main():
    events = make_events()

    triggered = selection.apply_trigger(events)
    check("trigger: all 3 events fire (event 0/1/2 all have the DZ path)", len(triggered) == 3)

    muons = selection.select_muons(triggered)
    check("muons: event0 has 2 selected", ak.to_list(ak.num(muons))[0] == 2)
    check("muons: event1 has 1 selected (2nd fails iso)", ak.to_list(ak.num(muons))[1] == 1)
    check("muons: event2 has 2 selected", ak.to_list(ak.num(muons))[2] == 2)

    electrons = selection.select_electrons(triggered)
    check("electrons: all events have 0 (none in synthetic data)", ak.sum(ak.num(electrons)) == 0)

    jets = selection.select_and_split_jets(triggered, muons, electrons)
    n_light = ak.to_list(ak.num(jets["Jets"]))
    n_b = ak.to_list(ak.num(jets["BJets"]))
    check("jets: event0 keeps 1 light jet (far from both muons)", n_light[0] == 1, f"got {n_light[0]}")
    check("jets: event2 jet is cleaned away (deltaR<0.4 from leading muon)", n_light[2] == 0, f"got {n_light[2]}")
    check("jets: no b-jets anywhere (btag 0.01 < 0.2598 WP)", sum(n_b) == 0)

    has_ge2mu = ak.num(muons) >= 2
    has_ge1jet = ak.num(jets["Jets"]) >= 1
    final_mask = ak.to_list(has_ge2mu & has_ge1jet)
    check("final selection: only event0 survives >=2mu & >=1jet", final_mask == [True, False, False], f"got {final_mask}")

    sel_muons = muons[has_ge2mu & has_ge1jet]
    sel_jets = jets["Jets"][has_ge2mu & has_ge1jet]
    mass = selection.compute_m0m1j0(sel_muons, sel_jets)
    mass_list = ak.to_list(mass)
    check("mass: exactly 1 surviving event", len(mass_list) == 1, f"got {len(mass_list)}")

    # Independent hand-check of event0's mass using the same vector library,
    # built completely separately from selection.py's own code path (no
    # shared helper functions), so this is a genuine cross-check rather
    # than the function checking itself.
    import vector as v
    v.register_awkward()
    p0 = v.obj(pt=60.0, eta=0.1, phi=0.0, mass=0.105)
    p1 = v.obj(pt=40.0, eta=-0.2, phi=1.0, mass=0.105)
    pj = v.obj(pt=80.0, eta=1.5, phi=2.5, mass=8.0)
    expected_mass = (p0 + p1 + pj).mass
    check(
        "mass: matches an independently-built vector.obj sum for event0",
        len(mass_list) == 1 and abs(mass_list[0] - expected_mass) < 1e-6,
        f"got {mass_list}, expected {expected_mass}",
    )

    # z_peak_cutoff / max_mass_cutoff behavior
    lo = selection.apply_z_peak_and_mass_cutoff(ak.Array([50.0, 200.0, 20000.0]))
    lo_list = ak.to_list(lo)
    check(
        "z_peak/max_mass cutoff: 50 GeV dropped (< 115), 200 GeV kept, 20000 GeV dropped (> 10000)",
        np.isnan(lo_list[0]) and lo_list[1] == 200.0 and np.isnan(lo_list[2]),
        f"got {lo_list}",
    )

    # missing trigger branch must raise, not silently pass through
    bad_events = ak.Array({"run": [1], "luminosityBlock": [1], "event": [1]})
    try:
        selection.apply_trigger(bad_events)
        check("missing trigger branch raises ValueError", False, "did not raise")
    except ValueError:
        check("missing trigger branch raises ValueError", True)

    # final-state string reuse of the shared group_by_final_state function
    from services.calculations.physics_calcs import group_by_final_state
    obj_record = selection.build_object_record(sel_muons, ak.Array([[]]), {"Jets": sel_jets, "BJets": ak.Array([[]])})
    fs_list = list(group_by_final_state(obj_record))
    check("final-state grouping yields exactly one final state for 1 event", len(fs_list) == 1, f"got {fs_list}")
    if fs_list:
        fs_name, fs_events = fs_list[0]
        check("final-state string has 2 muons, 1 jet", fs_name == "0e_2m_1j_0g_0t_0b", f"got {fs_name}")

    # services.pipelines.histograms_pipeline itself cannot be imported at
    # all in this project's actual cluster env (`import ROOT` fails there
    # too -- confirmed running the pilot, see histograms.py's module
    # docstring), so studies.m0m1j0_cms.histograms carries its own
    # verbatim, cited copy of _convert_to_bumpnet_name -- exercised here.
    from studies.m0m1j0_cms.histograms import _convert_to_bumpnet_name
    if fs_list:
        bumpnet_name = _convert_to_bumpnet_name(fs_name, "m0m1j0")
        check(
            "BumpNet name is mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx",
            bumpnet_name == "mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx",
            f"got {bumpnet_name}",
        )

    # Mixed b-jet scenario: event A has a b-tagged jet AND a light jet;
    # event B has only a light jet (0 b-jets) -- exercises the
    # per-event-mixed empty/non-empty case the earlier union-type bug
    # would have hit in a more realistic way than "all events empty".
    mixed = ak.Array({
        "run": [1, 1], "luminosityBlock": [1, 1], "event": [10, 11],
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ": [True, True],
        "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ": [False, False],
        "Muon_pt": [[60.0, 40.0], [60.0, 40.0]],
        "Muon_eta": [[0.1, -0.2], [0.1, -0.2]],
        "Muon_phi": [[0.0, 1.0], [0.0, 1.0]],
        "Muon_mass": [[0.105, 0.105], [0.105, 0.105]],
        "Muon_mediumId": [[True, True], [True, True]],
        "Muon_pfRelIso04_all": [[0.05, 0.05], [0.05, 0.05]],
        "Electron_pt": [[], []], "Electron_eta": [[], []], "Electron_phi": [[], []],
        "Electron_mass": [[], []], "Electron_cutBased": [[], []],
        "Jet_pt": [[80.0, 90.0], [80.0]],
        "Jet_eta": [[1.5, -1.0], [1.5]],
        "Jet_phi": [[2.5, -2.0], [2.5]],
        "Jet_mass": [[8.0, 9.0], [8.0]],
        "Jet_jetId": [[6, 6], [6]],
        "Jet_btagDeepFlavB": [[0.9, 0.01], [0.01]],  # event A: 1 b-jet + 1 light; event B: 1 light only
    })
    mixed_muons = selection.select_muons(mixed)
    mixed_electrons = selection.select_electrons(mixed)
    mixed_jets = selection.select_and_split_jets(mixed, mixed_muons, mixed_electrons)
    n_light_mixed = ak.to_list(ak.num(mixed_jets["Jets"]))
    n_b_mixed = ak.to_list(ak.num(mixed_jets["BJets"]))
    check("mixed b-jets: eventA has 1 bjet + 1 light jet", n_b_mixed[0] == 1 and n_light_mixed[0] == 1, f"got b={n_b_mixed} light={n_light_mixed}")
    check("mixed b-jets: eventB has 0 bjets + 1 light jet", n_b_mixed[1] == 0 and n_light_mixed[1] == 1, f"got b={n_b_mixed} light={n_light_mixed}")

    # Full cutflow function, end to end
    cutflow = selection.select_event_selection_cutflow(mixed)
    check("cutflow: n_after_golden_json == input size", cutflow["n_after_golden_json"] == 2)
    check("cutflow: n_after_trigger == 2", cutflow["n_after_trigger"] == 2)
    check("cutflow: n_after_ge2mu == 2", cutflow["n_after_ge2mu"] == 2)
    check("cutflow: n_after_ge1jet_after_cleaning == 2", cutflow["n_after_ge1jet_after_cleaning"] == 2)
    check("cutflow: obj_record has BJets/Jets/Muons/Electrons fields",
          set(["BJets", "Jets", "Muons", "Electrons"]).issubset(set(cutflow["obj_record"].fields)),
          f"got {cutflow['obj_record'].fields}")

    # Step 2 requirement B: low-mass dimuon diagnostic (extra_fields
    # threading + compute_dimuon_diagnostics), using a duplicate-like
    # pair (near-zero deltaR, pt ratio ~1, same charge) vs a normal pair.
    diag_events = ak.Array({
        "run": [1, 1], "luminosityBlock": [1, 1], "event": [20, 21],
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ": [True, True],
        "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ": [False, False],
        # event 0: near-duplicate pair (same eta/phi, pt ratio ~1, same charge)
        # event 1: normal back-to-back pair, opposite charge
        "Muon_pt": [[40.0, 39.9], [60.0, 40.0]],
        "Muon_eta": [[0.5, 0.5001], [0.1, -0.2]],
        "Muon_phi": [[1.0, 1.0001], [0.0, 3.0]],
        "Muon_mass": [[0.105, 0.105], [0.105, 0.105]],
        "Muon_mediumId": [[True, True], [True, True]],
        "Muon_pfRelIso04_all": [[0.05, 0.05], [0.05, 0.05]],
        "Muon_charge": [[1, 1], [1, -1]],
        "Electron_pt": [[], []], "Electron_eta": [[], []], "Electron_phi": [[], []],
        "Electron_mass": [[], []], "Electron_cutBased": [[], []],
        "Jet_pt": [[80.0], [80.0]], "Jet_eta": [[2.0], [2.0]], "Jet_phi": [[-1.5], [-1.5]],
        "Jet_mass": [[8.0], [8.0]], "Jet_jetId": [[6], [6]], "Jet_btagDeepFlavB": [[0.01], [0.01]],
    })
    muon_extra = {"charge": diag_events.Muon_charge}
    diag_result = selection.select_event_selection_cutflow(diag_events, muon_extra_fields=muon_extra)
    check("extra_fields threading: sel_muons carries 'charge' field", "charge" in diag_result["sel_muons"].fields, f"got {diag_result['sel_muons'].fields}")

    diagnostics = selection.compute_dimuon_diagnostics(diag_result["sel_muons"])
    dr_list = ak.to_list(diagnostics["dr"])
    cp_list = ak.to_list(diagnostics["charge_product"])
    ptr_list = ak.to_list(diagnostics["pt_ratio"])
    check("diagnostic: near-duplicate pair has deltaR ~0", dr_list[0] < 0.01, f"got {dr_list[0]}")
    check("diagnostic: near-duplicate pair has pt_ratio ~1", abs(ptr_list[0] - 1.0) < 0.01, f"got {ptr_list[0]}")
    check("diagnostic: near-duplicate pair is same-sign (charge_product=+1)", cp_list[0] == 1, f"got {cp_list[0]}")
    check("diagnostic: normal pair has larger deltaR", dr_list[1] > 1.0, f"got {dr_list[1]}")
    check("diagnostic: normal pair is opposite-sign (charge_product=-1)", cp_list[1] == -1, f"got {cp_list[1]}")
    check(
        "diagnostic: missing optional branches (isGlobal etc.) fill as NaN, not crash",
        all(np.isnan(x) for x in ak.to_list(diagnostics["isGlobal_mu0"])),
        f"got {diagnostics['isGlobal_mu0']}",
    )

    # Pilot sanity-plot helpers
    dimuon_mass = ak.to_list(selection.compute_dimuon_mass(mixed_muons))
    check("dimuon mass: 2 events computed, both finite", len(dimuon_mass) == 2 and all(not np.isnan(x) for x in dimuon_mass), f"got {dimuon_mass}")
    lead_pt = ak.to_list(selection.leading_jet_pt(mixed_jets["Jets"]))
    check("leading jet pT: eventA's light jet is 90 GeV (the non-b one)", lead_pt[0] == 90.0, f"got {lead_pt}")
    check("leading jet pT: eventB's light jet is 80 GeV", lead_pt[1] == 80.0, f"got {lead_pt}")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All synthetic self-checks passed.")


if __name__ == "__main__":
    main()
