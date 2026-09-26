"""
Ceiling task -- new object types (Photons, Taus, MET) and overlap-removal
diagnostics, on top of the UNCHANGED electron/muon/jet/b-jet definitions in
studies/m0m1j0_cms/selection.py (imported, not reimplemented, by callers of
this module).

See DEFINITIONS.md for the source and justification of every choice here
(photon cuts reused verbatim from config.cms_hgg_data.yaml's own already-
verified H->gg recipe; tau cuts proposed fresh, flagged for supervisor
confirmation; MET represented as a massless, eta=0 pseudo-object per the
BumpNet paper's MassMET recipe).

Photon/tau kinematic+ID cuts are applied via the real, unmodified
services.calculations.physics_calcs.filter_events_by_kinematics (the same
function config.cms_hgg_data.yaml already exercises in production) --
called with different parameters, not reimplemented. Delta-R overlap
removal has no shared-code equivalent (confirmed: no deltaR/delta_r/
overlap_removal/clean_by helper exists anywhere under services/), so it is
new code here, using the same 0.4 threshold and cartesian/min-dR/fill_none
pattern already established for jet-lepton cleaning
(studies/m0m1j0_cms/selection.py's _clean_and_cut_jets).
"""
from __future__ import annotations

from typing import Dict, Tuple

import awkward as ak
import numpy as np
import vector

from services.calculations import physics_calcs

vector.register_awkward()

# --- Photon cuts (DEFINITIONS.md; config.cms_hgg_data.yaml:279-284) -------
PHOTON_PT_MIN_GEV = 20.0
PHOTON_BOOL_REQUIRE = ("electronVeto", "mvaID_WP90")
PHOTON_BOOL_ANY_OF = ("isScEtaEB", "isScEtaEE")

PHOTON_REQUIRED_BRANCHES = (
    "nPhoton", "Photon_pt", "Photon_eta", "Photon_phi", "Photon_mass",
    "Photon_mvaID_WP90", "Photon_electronVeto",
    "Photon_isScEtaEB", "Photon_isScEtaEE",
)

# --- Tau cuts (DEFINITIONS.md -- proposed fresh, needs supervisor sign-off)
TAU_PT_MIN_GEV = 20.0
TAU_ETA_MAX = 2.3
TAU_VSJET_MEDIUM_BIT = 16
TAU_VSE_VVLOOSE_BIT = 2
TAU_VSMU_TIGHT_BIT = 8

TAU_REQUIRED_BRANCHES = (
    "nTau", "Tau_pt", "Tau_eta", "Tau_phi", "Tau_mass",
    "Tau_idDeepTau2017v2p1VSjet", "Tau_idDeepTau2017v2p1VSe",
    "Tau_idDeepTau2017v2p1VSmu", "Tau_idDecayModeOldDMs",
)

MET_REQUIRED_BRANCHES = ("MET_pt", "MET_phi")

OVERLAP_DR = 0.4  # same threshold as selection.py's JET_LEPTON_CLEAN_DR


def select_photons_precleaning(events: ak.Array) -> ak.Array:
    """pT + ID cuts only (no delta-R overlap removal yet) -- callers pass
    this through overlap_removal() for the actual selected collection and
    the overlap diagnostics in one step."""
    raw = ak.zip({
        "pt": events.Photon_pt, "eta": events.Photon_eta,
        "phi": events.Photon_phi, "mass": events.Photon_mass,
        "mvaID_WP90": events.Photon_mvaID_WP90,
        "electronVeto": events.Photon_electronVeto,
        "isScEtaEB": events.Photon_isScEtaEB,
        "isScEtaEE": events.Photon_isScEtaEE,
    })
    wrapped = ak.zip({"Photons": raw}, depth_limit=1)
    cuts = {"Photons": {
        "pt": {"min": PHOTON_PT_MIN_GEV},
        "bool_require": list(PHOTON_BOOL_REQUIRE),
        "bool_any_of": list(PHOTON_BOOL_ANY_OF),
    }}
    filtered = physics_calcs.filter_events_by_kinematics(wrapped, cuts)
    return filtered.Photons


def select_taus_precleaning(events: ak.Array) -> ak.Array:
    """pT/eta + DeepTau WP + decay-mode-finding cuts only (no delta-R
    overlap removal yet) -- see select_photons_precleaning's docstring."""
    vsjet = events.Tau_idDeepTau2017v2p1VSjet
    vse = events.Tau_idDeepTau2017v2p1VSe
    vsmu = events.Tau_idDeepTau2017v2p1VSmu
    pass_vsjet = (vsjet & TAU_VSJET_MEDIUM_BIT) != 0
    pass_vse = (vse & TAU_VSE_VVLOOSE_BIT) != 0
    pass_vsmu = (vsmu & TAU_VSMU_TIGHT_BIT) != 0

    raw = ak.zip({
        "pt": events.Tau_pt, "eta": events.Tau_eta, "phi": events.Tau_phi,
        "mass": events.Tau_mass,
        "decayModeFinding": events.Tau_idDecayModeOldDMs,
        "passVSjet": pass_vsjet, "passVSe": pass_vse, "passVSmu": pass_vsmu,
    })
    wrapped = ak.zip({"Taus": raw}, depth_limit=1)
    cuts = {"Taus": {
        "pt": {"min": TAU_PT_MIN_GEV},
        "eta": {"min": -TAU_ETA_MAX, "max": TAU_ETA_MAX},
        "bool_require": ["decayModeFinding", "passVSjet", "passVSe", "passVSmu"],
    }}
    filtered = physics_calcs.filter_events_by_kinematics(wrapped, cuts)
    return filtered.Taus


def _p4(obj: ak.Array) -> ak.Array:
    return vector.zip({"pt": obj.pt, "eta": obj.eta, "phi": obj.phi, "mass": obj.mass})


def _min_dr_to_collection(target: ak.Array, reference: ak.Array) -> ak.Array:
    """Per-target-particle minimum delta-R to any particle in `reference`,
    within the same event. An event where `reference` is empty contributes
    no cartesian partners for its target particles, so ak.min gives None
    per particle there -- filled with +inf (i.e. "infinitely far", so such
    a particle is never spuriously flagged as overlapping)."""
    if len(target) == 0:
        return ak.Array([])
    pairs_t, pairs_r = ak.unzip(ak.cartesian([_p4(target), _p4(reference)], nested=True))
    dr = pairs_t.deltaR(pairs_r)
    min_dr = ak.min(dr, axis=-1)
    return ak.fill_none(min_dr, np.inf)


def overlap_removal(
    target: ak.Array, lepton_ref: ak.Array, jet_ref: ak.Array, dr_threshold: float = OVERLAP_DR,
) -> Tuple[ak.Array, Dict]:
    """Delta-R<`dr_threshold` cleaning of `target` (photons or taus)
    against BOTH `lepton_ref` (selected electrons+muons) and `jet_ref`
    (selected Jets+BJets), all measured on the SAME pre-cleaning candidate
    set so the lepton- and jet-overlap fractions are directly comparable
    (not sequential, so double-overlap isn't hidden in whichever check runs
    first). Returns (kept_target, diagnostics)."""
    n_candidates = int(ak.sum(ak.num(target)))
    if n_candidates == 0:
        diagnostics = {
            "n_candidates": 0, "n_overlap_lepton": 0, "n_overlap_jet": 0,
            "n_overlap_either": 0, "frac_overlap_lepton": None,
            "frac_overlap_jet": None, "frac_overlap_either": None,
        }
        return target, diagnostics

    min_dr_lep = _min_dr_to_collection(target, lepton_ref)
    min_dr_jet = _min_dr_to_collection(target, jet_ref)
    near_lepton = min_dr_lep < dr_threshold
    near_jet = min_dr_jet < dr_threshold
    near_either = near_lepton | near_jet

    n_near_lepton = int(ak.sum(ak.sum(near_lepton, axis=1)))
    n_near_jet = int(ak.sum(ak.sum(near_jet, axis=1)))
    n_near_either = int(ak.sum(ak.sum(near_either, axis=1)))

    diagnostics = {
        "n_candidates": n_candidates,
        "n_overlap_lepton": n_near_lepton,
        "n_overlap_jet": n_near_jet,
        "n_overlap_either": n_near_either,
        "frac_overlap_lepton": n_near_lepton / n_candidates,
        "frac_overlap_jet": n_near_jet / n_candidates,
        "frac_overlap_either": n_near_either / n_candidates,
    }
    kept = target[~near_either]
    return kept, diagnostics


def build_object_record_6type(muons, electrons, jets, photons, taus) -> ak.Array:
    """Photons/Taus are already first-class in the shared final-state
    naming (services.calculations.physics_calcs.group_by_final_state
    already reads particle_counts.Photons/.Taus, and
    consts.LETTER_PARTICLE_MAPPING already maps 'g'/'t' to them) -- this
    only needs to zip them in alongside the 4 existing fields, reusing
    everything downstream unmodified."""
    return ak.zip(
        {
            "Electrons": electrons, "Muons": muons,
            "Jets": jets["Jets"], "BJets": jets["BJets"],
            "Photons": photons, "Taus": taus,
        },
        depth_limit=1,
    )


def build_met_pseudo_object(events: ak.Array) -> ak.Array:
    """BumpNet paper (arXiv:2501.05603 sec 2.2.2) MassMET recipe: MET's
    four-vector has its longitudinal momentum (p_z) and mass both set to
    zero. Represented as a length-1-per-event jagged pseudo-collection with
    eta forced to 0.0 (pz = pt*sinh(eta) = 0 exactly at eta=0, under the
    same pt/eta/phi/mass vector.zip convention services.calculations.
    im_calculator.IMCalculator already uses for every other object type --
    zero changes needed on that side) and mass forced to 0.0. MET has no
    mass branch in NanoAOD (confirmed: MET_pt/_phi/_sumEt/_significance/
    _covXX/_covXY/_covYY only, no MET_mass, in the real file checked), so
    this is not overriding a real value, just supplying the one the branch
    never had."""
    pt = ak.singletons(events.MET_pt)
    phi = ak.singletons(events.MET_phi)
    eta = ak.zeros_like(pt)
    mass = ak.zeros_like(pt)
    return ak.zip({"pt": pt, "eta": eta, "phi": phi, "mass": mass})


def add_met_variants(combinations: list) -> list:
    """New (not shared) augmentation, needed because
    services.calculations.combinatorics.get_all_combinations's min_count/
    max_count apply globally across all object_types, with no way to cap
    one type (MET) at exactly 1 while allowing others up to 4 -- so MET
    cannot be passed as an ordinary 7th get_all_combinations object_type.
    For each combination dict already produced by the real, unmodified
    get_all_combinations(), adds a second variant with a 'METObject':
    (1, 0) slot appended (MET is always exactly 1 object per event, never
    leading/subleading). Both the original and the +MET variant are kept,
    so the incremental yield MET variants add can be measured directly
    against the same base grid."""
    met_variants = []
    for combo in combinations:
        augmented = dict(combo)
        augmented["METObject"] = (1, 0)
        met_variants.append(augmented)
    return combinations + met_variants
