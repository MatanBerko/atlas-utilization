#!/usr/bin/env python3
"""
Synthetic (no real data) test for the Part B impact-parameter masking in
scripts/higgs_4lepton_partB_report.py::build_selected_leptons. Run BEFORE
touching real data.

3 synthetic events, all otherwise-identical 4-muon events differing only in
sip3d/dxy/dz:
  evt0: fully prompt (sip3d~1, dxy~0.01, dz~0.05) -- all 4 muons pass every
        IP-cut combination.
  evt1: one muon has sip3d=10 (displaced) -- sip3d cut alone should drop
        exactly that one muon; dxy/dz cuts alone should not.
  evt2: one muon has dxy=0.8 (fails |dxy|<0.5) and a DIFFERENT muon has
        dz=2.0 (fails |dz|<1.0) -- dxy-only and dz-only cuts should each
        drop exactly one (different) muon; combining all three should drop
        both, leaving only 2 selected muons.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import awkward as ak

from higgs_4lepton_partB_report import build_selected_leptons


def make_events():
    return ak.Array({
        "Electrons_pt": [[], [], []], "Electrons_eta": [[], [], []], "Electrons_phi": [[], [], []],
        "Electrons_mass": [[], [], []], "Electrons_charge": [[], [], []],
        "Electrons_pfRelIso03_all": [[], [], []], "Electrons_cutBased": [[], [], []],
        "Electrons_sip3d": [[], [], []], "Electrons_dxy": [[], [], []], "Electrons_dz": [[], [], []],
        "Muons_pt": [[30, 25, 20, 15]] * 3,
        "Muons_eta": [[0, 0, 0, 0]] * 3, "Muons_phi": [[0, 1, 2, 3]] * 3, "Muons_mass": [[0.105658] * 4] * 3,
        "Muons_charge": [[1, -1, 1, -1]] * 3,
        "Muons_pfRelIso04_all": [[0.1, 0.1, 0.1, 0.1]] * 3,
        "Muons_looseId": [[True, True, True, True]] * 3,
        "Muons_sip3d": [[1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 10.0], [1.0, 1.0, 1.0, 1.0]],
        "Muons_dxy": [[0.01, 0.01, 0.01, 0.01], [0.01, 0.01, 0.01, 0.01], [0.01, 0.01, 0.01, 0.8]],
        "Muons_dz": [[0.05, 0.05, 0.05, 0.05], [0.05, 0.05, 0.05, 0.05], [0.05, 0.05, 2.0, 0.05]],
        "source_record": [30521, 30521, 30521], "run": [1, 1, 1],
        "luminosityBlock": [1, 1, 1], "event": [1, 2, 3],
    })


def test_ip_cuts_isolate_correctly():
    events = make_events()

    n_none = ak.num(build_selected_leptons(events, use_sip3d=False, use_dxy=False, use_dz=False)).tolist()
    assert n_none == [4, 4, 4]

    n_sip3d = ak.num(build_selected_leptons(events, use_sip3d=True, use_dxy=False, use_dz=False)).tolist()
    assert n_sip3d == [4, 3, 4], "evt1's displaced muon (sip3d=10) should be the only one dropped"

    n_dxy = ak.num(build_selected_leptons(events, use_sip3d=False, use_dxy=True, use_dz=False)).tolist()
    assert n_dxy == [4, 4, 3], "evt2's dxy=0.8 muon should be the only one dropped"

    n_dz = ak.num(build_selected_leptons(events, use_sip3d=False, use_dxy=False, use_dz=True)).tolist()
    assert n_dz == [4, 4, 3], "evt2's dz=2.0 muon should be the only one dropped"

    n_all = ak.num(build_selected_leptons(events, use_sip3d=True, use_dxy=True, use_dz=True)).tolist()
    assert n_all == [4, 3, 2], "evt2 should lose BOTH muons (dxy and dz fail on different muons)"

    print("test_ip_cuts_isolate_correctly: PASS (sip3d/dxy/dz each isolate exactly the intended muon)")


if __name__ == "__main__":
    test_ip_cuts_isolate_correctly()
    print("ALL PART B SYNTHETIC TESTS PASS")
