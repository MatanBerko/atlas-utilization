#!/usr/bin/env python
"""
Synthetic self-checks for the jet-excess probe's pure helpers.

These run on hand-built awkward arrays on any machine, so a mistake in the
awkward plumbing is caught before a cluster job burns an hour on it. They
check behaviour, not plumbing-free arithmetic: empty events, events with no
leptons at all, the jet ordering the extra-jet block depends on, and the
particle-level selection's flavour and charge logic.
"""
from __future__ import annotations

import pathlib
import sys

import awkward as ak
import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_mc_weights_v3.jets.run_jet_probe_on_file import (  # noqa: E402
    apply_jet_cuts, counts_entry, delta_r, dilepton_mass_arrays,
    extra_jet_block, gen_particle_level, min_dr_to, njet_bin, two_leading,
)

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("  ok   {}".format(name))
    else:
        print("  FAIL {} {}".format(name, detail))
        FAILURES.append(name)


def test_delta_r_wraps():
    dr = delta_r(np.array([0.0]), np.array([3.1]), np.array([0.0]),
                 np.array([-3.1]))
    check("delta_r wraps across pi", abs(dr[0] - (2 * np.pi - 6.2)) < 1e-9,
          "got {}".format(dr[0]))


def test_min_dr_handles_empty_events():
    jets = ak.Array([[{"eta": 0.0, "phi": 0.0}], [{"eta": 1.0, "phi": 1.0}], []])
    leptons = ak.Array([[{"eta": 0.1, "phi": 0.0}], [], []])
    out = min_dr_to(jets, leptons)
    flat = ak.to_numpy(ak.flatten(out))
    check("nearest lepton found", abs(flat[0] - 0.1) < 1e-9, "got {}".format(flat[0]))
    check("no leptons -> far away", flat[1] == 99.0, "got {}".format(flat[1]))
    check("no jets -> no entries", len(flat) == 2, "got {}".format(len(flat)))


def test_dilepton_mass_known_value():
    # two back-to-back 45.6 GeV massless objects -> m = 91.2
    m = dilepton_mass_arrays(
        np.array([45.6]), np.array([0.0]), np.array([0.0]), np.array([0.0]),
        np.array([45.6]), np.array([0.0]), np.array([np.pi]), np.array([0.0]))
    check("back-to-back mass", abs(m[0] - 91.2) < 1e-6, "got {}".format(m[0]))


def test_two_leading_sorts_and_pads():
    coll = ak.Array([
        [{"pt": 10.0, "eta": 0.0, "phi": 0.0, "mass": 0.0},
         {"pt": 40.0, "eta": 1.0, "phi": 0.0, "mass": 0.0}],
        [{"pt": 15.0, "eta": 0.0, "phi": 0.0, "mass": 0.0}],
    ])
    two = two_leading(coll, ("pt", "eta"))
    check("leading is the harder one", two["pt"][0][0] == 40.0)
    check("subleading is the softer one", two["pt"][1][0] == 10.0)
    check("missing subleading is zero-filled", two["pt"][1][1] == 0.0)


def test_apply_jet_cuts_matches_the_delivered_shape():
    jets = ak.Array([[
        {"pt": 35.0, "eta": 0.0, "phi": 0.0, "jetId": 6},    # passes
        {"pt": 25.0, "eta": 0.0, "phi": 1.0, "jetId": 6},    # too soft
        {"pt": 35.0, "eta": 2.45, "phi": 2.0, "jetId": 6},   # outside 2.4
        {"pt": 35.0, "eta": 0.0, "phi": 3.0, "jetId": 0},    # fails tight ID
        {"pt": 35.0, "eta": 0.5, "phi": 0.5, "jetId": 6},    # near the lepton
    ]])
    leptons = ak.Array([[{"eta": 0.5, "phi": 0.5}]])
    kept = apply_jet_cuts(jets, leptons, 30.0, 2.4)
    check("only the one good jet survives", ak.to_numpy(ak.num(kept, axis=1))[0] == 1)
    check("and it is the first one", abs(kept.phi[0][0] - 0.0) < 1e-9)

    # the same jets with a pT override: the 25 GeV jet is rescued
    kept2 = apply_jet_cuts(jets, leptons, 30.0, 2.4, pt_override=jets.pt * 1.5)
    check("pT override rescues the soft jet",
          ak.to_numpy(ak.num(kept2, axis=1))[0] == 2)

    # |eta| < 2.5 lets the forward jet back in
    kept3 = apply_jet_cuts(jets, leptons, 30.0, 2.5)
    check("eta 2.5 admits the forward jet",
          ak.to_numpy(ak.num(kept3, axis=1))[0] == 2)


def test_counts_entry_overflows_at_five():
    entry = counts_entry(np.array([0, 3, 5, 9]), np.array([1.0, 2.0, 1.0, 1.0]))
    check("5+ is an overflow bin", entry["w"] == [1.0, 0.0, 0.0, 2.0, 0.0, 2.0],
          "got {}".format(entry["w"]))
    check("raw counts too", entry["raw"] == [1, 0, 0, 1, 0, 2])
    check("njet_bin clips", list(njet_bin([0, 7])) == [0, 5])


def test_extra_jet_block_takes_the_third_jet_onwards():
    jets = ak.Array([[
        {"pt": 100.0, "eta": 0.0, "phi": 0.0, "jetId": 6},
        {"pt": 50.0, "eta": 0.1, "phi": 0.5, "jetId": 6},
        {"pt": 40.0, "eta": 0.2, "phi": 1.0, "jetId": 2},   # fails lep veto
        {"pt": 31.0, "eta": 0.3, "phi": 1.5, "jetId": 6},
    ]])
    leptons = ak.Array([[{"eta": 2.0, "phi": 2.0}]])
    block = extra_jet_block(jets, leptons, leptons, None,
                            np.array([2.0]), [])
    check("two extra jets, weighted", block["xjet_n"] == 4.0,
          "got {}".format(block["xjet_n"]))
    check("two extra jets, raw", block["xjet_n_raw"] == 2)
    check("one of them fails tightLepVeto",
          block["xjet_n_fail_tightlepveto_raw"] == 1)
    check("fewer than three jets gives an empty block",
          extra_jet_block(jets[:, :2], leptons, leptons, None,
                          np.array([1.0]), [])["xjet_n_raw"] == 0)


def test_gen_particle_level_flavour_and_charge():
    def event(pdg1, pt1, pdg2, pt2, njets):
        return {
            "GenDressedLepton_pt": [pt1, pt2],
            "GenDressedLepton_eta": [0.0, 0.1],
            "GenDressedLepton_phi": [0.0, np.pi],
            "GenDressedLepton_mass": [0.0, 0.0],
            "GenDressedLepton_pdgId": [pdg1, pdg2],
            "GenJet_pt": [40.0] * njets,
            "GenJet_eta": [1.0] * njets,
            "GenJet_phi": [1.0 + 0.5 * i for i in range(njets)],
        }

    events = ak.Array([
        event(13, 45.6, -13, 45.6, 2),     # good mumu, 2 jets
        event(11, 45.6, -11, 45.6, 0),     # good ee, 0 jets
        event(13, 45.6, 13, 45.6, 1),      # same sign -> rejected
        event(13, 25.0, -13, 25.0, 1),     # leading too soft -> rejected
    ])
    present = ["GenDressedLepton_pt", "GenJet_pt"]
    njet, ok, flavour = gen_particle_level(events, present)
    check("good mumu accepted", bool(ok[0]) and flavour[0] == 13)
    check("good ee accepted", bool(ok[1]) and flavour[1] == 11)
    check("same sign rejected", not bool(ok[2]))
    check("soft leading lepton rejected", not bool(ok[3]))
    check("jet count right", njet[0] == 2 and njet[1] == 0,
          "got {} {}".format(njet[0], njet[1]))

    missing = gen_particle_level(events, ["GenJet_pt"])
    check("absent dressed leptons degrade gracefully", missing[0] is None)


def main():
    print("jet probe synthetic self-checks")
    for test in (test_delta_r_wraps, test_min_dr_handles_empty_events,
                 test_dilepton_mass_known_value, test_two_leading_sorts_and_pads,
                 test_apply_jet_cuts_matches_the_delivered_shape,
                 test_counts_entry_overflows_at_five,
                 test_extra_jet_block_takes_the_third_jet_onwards,
                 test_gen_particle_level_flavour_and_charge):
        print(test.__name__)
        test()
    if FAILURES:
        print("\n{} FAILED: {}".format(len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
