#!/usr/bin/env python3
"""
Synthetic (no real data) tests for scripts/higgs_4lepton_zz_report.py, run
BEFORE the validation pass on real data. Two layers:

  1. find_z1_z2() alone, against hand-constructed leptons with known,
     back-to-back kinematics chosen so the pair masses are exactly
     computable by hand (m = 2*pt for two massless-ish back-to-back
     leptons at eta=0) -- covers: a clean 2e2mu candidate, a clean 4mu
     candidate, an all-same-charge reject, a Z2-mass-out-of-window reject,
     and a structurally-impossible 3e1mu reject.

  2. The full build_selected_leptons() + run_selection() pipeline on a
     small synthetic "events" awkward array shaped like real parsed output,
     covering: per-lepton ID/iso cuts dropping specific leptons (so an event
     that started with 4 raw leptons ends with only 3 selected), the
     exactly-4 filter, the charge-sum-zero filter, and end-to-end Z1/Z2
     candidate production with the correct per-record cut-flow breakdown.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import awkward as ak

from higgs_4lepton_zz_report import build_selected_leptons, find_z1_z2, run_selection


def lep(pt, eta, phi, mass, charge, flavor):
    return {"pt": pt, "eta": eta, "phi": phi, "mass": mass, "charge": charge, "flavor": flavor}


def back_to_back_pair(m_lep, target_mass, flavor):
    """Two leptons at eta=0, dphi=pi -> m = 2*pt for pt1=pt2=pt (exact in the
    massless limit, and to << 1 MeV precision here given real lepton masses)."""
    pt = target_mass / 2.0
    return [lep(pt, 0.0, 0.0, m_lep, +1, flavor), lep(pt, 0.0, math.pi, m_lep, -1, flavor)]


def test_find_z1_z2():
    e_pair = back_to_back_pair(0.000511, 91.0, 0)
    mu_pair = back_to_back_pair(0.105658, 30.0, 1)
    r = find_z1_z2(e_pair + mu_pair)
    assert r is not None and r["channel"] == "2e2mu"
    assert abs(r["m_z1"] - 91.0) < 0.5 and abs(r["m_z2"] - 30.0) < 0.5

    mu1, mu2 = back_to_back_pair(0.105658, 91.0, 1), back_to_back_pair(0.105658, 20.0, 1)
    r2 = find_z1_z2(mu1 + mu2)
    assert r2 is not None and r2["channel"] == "4mu"
    assert abs(r2["m_z1"] - 91.0) < 0.5 and abs(r2["m_z2"] - 20.0) < 0.5

    same_charge = [lep(30, 0, 0, 0.000511, +1, 0), lep(25, 0, 1, 0.000511, +1, 0),
                   lep(20, 0, 2, 0.000511, +1, 0), lep(15, 0, 3, 0.000511, +1, 0)]
    assert find_z1_z2(same_charge) is None

    e_ok = back_to_back_pair(0.000511, 91.0, 0)
    mu_low = back_to_back_pair(0.105658, 5.0, 1)  # below the 12 GeV Z2 floor
    assert find_z1_z2(e_ok + mu_low) is None

    three_e_one_mu = [lep(30, 0, 0, 0.000511, +1, 0), lep(25, 0, 1, 0.000511, -1, 0),
                       lep(20, 0, 2, 0.000511, +1, 0), lep(15, 0, 3, 0.105658, -1, 1)]
    assert find_z1_z2(three_e_one_mu) is None

    print("test_find_z1_z2: PASS (2e2mu, 4mu, all-same-charge reject, "
          "Z2-window reject, 3e1mu-structural reject)")


def test_full_pipeline():
    (e_pt1, e_pt2), (e_eta1, e_eta2), (e_phi1, e_phi2), (e_m1, e_m2) = (
        (45.5, 45.5), (0.0, 0.0), (0.0, math.pi), (0.000511, 0.000511)
    )
    (m_pt1, m_pt2), (m_eta1, m_eta2), (m_phi1, m_phi2), (m_m1, m_m2) = (
        (15.0, 15.0), (0.0, 0.0), (0.0, math.pi), (0.105658, 0.105658)
    )

    events = ak.Array({
        "Electrons_pt":  [[e_pt1, e_pt2], [30, 25, 20, 15], [], []],
        "Electrons_eta": [[e_eta1, e_eta2], [0, 0, 0, 0], [], []],
        "Electrons_phi": [[e_phi1, e_phi2], [0, 1, 2, 3], [], []],
        "Electrons_mass": [[e_m1, e_m2], [5.11e-4] * 4, [], []],
        "Electrons_charge": [[1, -1], [1, -1, 1, -1], [], []],
        # evt1: last electron fails isolation -> only 3 of 4 electrons selected
        "Electrons_pfRelIso03_all": [[0.1, 0.1], [0.1, 0.1, 0.1, 0.9], [], []],
        "Electrons_cutBased": [[3, 3], [3, 3, 3, 3], [], []],
        "Muons_pt":  [[m_pt1, m_pt2], [], [30, 25, 20, 15], [30, 25, 20, 15]],
        "Muons_eta": [[m_eta1, m_eta2], [], [0, 0, 0, 0], [0, 0, 0, 0]],
        "Muons_phi": [[m_phi1, m_phi2], [], [0, 1, 2, 3], [0, 1, 2, 3]],
        "Muons_mass": [[m_m1, m_m2], [], [0.105658] * 4, [0.105658] * 4],
        "Muons_charge": [[1, -1], [], [1, -1, 1, 1], [1, -1, 1, 1]],
        # evt2: last muon fails isolation -> only 3 of 4 muons selected
        "Muons_pfRelIso04_all": [[0.1, 0.1], [], [0.1, 0.1, 0.1, 0.9], [0.1, 0.1, 0.1, 0.1]],
        "Muons_looseId": [[True, True], [], [True, True, True, True], [True, True, True, True]],
        "source_record": [30521, 30521, 30522, 30522],
        "run": [1, 1, 1, 1], "luminosityBlock": [1, 1, 1, 1], "event": [1, 2, 3, 4],
    })
    # evt0: valid 2e2mu (ee~91, mumu~30) -> 1 final candidate
    # evt1: 4 raw electrons, 1 fails iso -> 3 selected -> dropped before exactly-4
    # evt2: 4 raw muons, 1 fails iso -> 3 selected -> dropped before exactly-4
    # evt3: 4 raw muons, all pass quality, but charge sum = 1-1+1+1 = +2 -> dropped at charge stage

    leptons = build_selected_leptons(events)
    assert ak.num(leptons).tolist() == [4, 3, 3, 4]

    cutflow, candidates = run_selection(events, leptons)
    assert cutflow["after_parse_time_selection"]["combined"] == 4
    assert cutflow["after_ge4_quality_leptons"]["combined"] == 2  # evt0, evt3
    assert cutflow["exactly4_charge0"]["combined"] == 1  # only evt0 (evt3 fails charge sum)
    assert len(candidates) == 1
    assert candidates[0]["channel"] == "2e2mu"
    assert abs(candidates[0]["m_z1"] - 91.0) < 0.5
    assert abs(candidates[0]["m_z2"] - 30.0) < 0.5
    assert candidates[0]["source_record"] == 30521

    print("test_full_pipeline: PASS (iso cuts drop specific leptons, exactly-4 filter, "
          "charge-sum-zero filter, and Z1/Z2 all wired correctly end-to-end)")


if __name__ == "__main__":
    test_find_z1_z2()
    test_full_pipeline()
    print("ALL SYNTHETIC TESTS PASS")
