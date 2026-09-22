"""
m0m1j0 CMS histogram -- Step 1 analysis-layer selection.

Pure awkward-array / vector-library physics: object selection, jet-lepton
cleaning, b-tag split, the m0m1j0 four-vector mass, and final-state
categorization. Deliberately ROOT-free (no ``import ROOT``) so it can be
imported and unit-tested on a machine without PyROOT (e.g. this project's
Windows dev machine) -- see ``studies/m0m1j0_cms/tests/`` for the
synthetic-event self-checks. ROOT-dependent histogram building lives in
``studies/m0m1j0_cms/histograms.py``, which imports this module.

Every cut value and every deviation from the group's ATLAS ``config.yaml``
recipe is documented, with citations, in ``studies/m0m1j0_cms/RECIPE.md``
-- this module implements that document; it is not a second source of
truth for the numbers themselves.

Object handling summary (RECIPE.md section 6):
  - Muons: pt>25 GeV, |eta|<2.4, mediumId, pfRelIso04_all<0.15. Used both
    for the m0m1j0 mass (leading + subleading) and for jet cleaning.
  - Electrons: pt>25 GeV, |eta|<2.5, cutBased>=3. COUNT-ONLY: used for
    jet cleaning and the final-state category string, never for the mass.
  - Jets: raw jets are split into b-tagged/light FIRST (mirrors the ATLAS
    recipe's parse-time split order, RECIPE.md section 3), by
    Jet_btagDeepFlavB > BTAG_DEEPFLAVB_MEDIUM_WP; pt/eta/tight-ID cuts and
    delta-R lepton cleaning are then applied to BOTH resulting collections.
  - Photons/taus: not read, not selected, not counted at all (RECIPE.md
    deviation 2 -- ATLAS's particle_counts max:0 would otherwise reject
    whole events for a reason unrelated to m0m1j0).
  - m0m1j0 mass: built from each object's own NanoAOD (pt, eta, phi, mass)
    branches via ``vector.zip`` -- not the shared pipeline's
    per-object-type KNOWN_MASSES constants (services/calculations/consts.py,
    not imported here), since CMS NanoAOD already carries a real mass
    branch for both muons and jets and the task specifies "full
    four-vectors (pt, eta, phi, mass)" explicitly.
  - z_peak_cutoff (115 GeV) and max_mass_cutoff (10000 GeV) are mirrored
    faithfully onto the m0m1j0 mass itself (RECIPE.md section 5/6.3),
    since m0m1j0 contains two muons and the shared pipeline's own
    _dilepton_flavor() check does not special-case 3+-object combinations.
"""
from __future__ import annotations

from typing import Dict

import awkward as ak
import numpy as np
import vector

vector.register_awkward()

# --- CMS object cuts (task spec; RECIPE.md section 6) -----------------
MUON_PT_MIN_GEV = 25.0
MUON_ETA_MAX = 2.4
MUON_ISO_MAX = 0.15

ELECTRON_PT_MIN_GEV = 25.0
ELECTRON_ETA_MAX = 2.5
ELECTRON_CUTBASED_MIN = 3  # medium; branch title quoted verbatim at read time

JET_PT_MIN_GEV = 30.0
JET_ETA_MAX = 2.5
JET_LEPTON_CLEAN_DR = 0.4

# DeepJet Medium WP, UL2016 postVFP -- same value as config.cms_bjet_test.yaml:78
BTAG_DEEPFLAVB_MEDIUM_WP = 0.2598

TRIGGER_BRANCHES = (
    "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ",
    "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ",
)

# Mirrored from config.yaml:155-156 (RECIPE.md section 5/6.3, 6.5).
Z_PEAK_CUTOFF_GEV = 115.0
MAX_MASS_CUTOFF_GEV = 10000.0

# Mirrored from config.yaml:142 / services/storage/sqlite_shards.py (RECIPE.md
# section 5/6.5) -- applied per exact final state, not to the inclusive histogram.
MIN_EVENTS_PER_FINAL_STATE = 100

NEEDED_BRANCHES = (
    "run", "luminosityBlock", "event",
    *TRIGGER_BRANCHES,
    "nMuon", "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass",
    "Muon_mediumId", "Muon_pfRelIso04_all", "Muon_charge",
    "nElectron", "Electron_pt", "Electron_eta", "Electron_phi", "Electron_mass",
    "Electron_cutBased",
    "nJet", "Jet_pt", "Jet_eta", "Jet_phi", "Jet_mass", "Jet_jetId",
    "Jet_btagDeepFlavB",
)

# Step 2, requirement B (low-mass dimuon diagnostic): read if present,
# never required -- unlike NEEDED_BRANCHES above, a file missing one of
# these does NOT fail the job; it's simply recorded as absent and that
# muon's value for it is NaN in the diagnostic output (see
# select_muons's extra_fields and compute_dimuon_diagnostics below).
# DIAGNOSTIC ONLY: none of these are read for, or affect, the m0m1j0
# selection itself.
OPTIONAL_MUON_DIAGNOSTIC_BRANCHES = (
    "Muon_isGlobal", "Muon_isTracker", "Muon_isPFcand",
    "Muon_nStations", "Muon_nTrackerLayers",
)


def require_trigger_branches(available_fields: list) -> None:
    """Fail loudly (per the task's own instruction) if either named HLT
    path is absent from a file, rather than silently treating it as
    'did not fire'."""
    missing = [b for b in TRIGGER_BRANCHES if b not in available_fields]
    if missing:
        raise ValueError(
            f"Required trigger branch(es) missing from this file: {missing}. "
            f"Refusing to silently treat a missing branch as 'not fired'."
        )


def apply_trigger(events: ak.Array) -> ak.Array:
    require_trigger_branches(events.fields)
    fired = events[TRIGGER_BRANCHES[0]] | events[TRIGGER_BRANCHES[1]]
    return events[fired]


def _p4(obj: ak.Array) -> ak.Array:
    return vector.zip({
        "pt": obj.pt, "eta": obj.eta, "phi": obj.phi, "mass": obj.mass,
    })


def select_muons(events: ak.Array, extra_fields: Dict[str, ak.Array] = None) -> ak.Array:
    """`extra_fields` (Step 2, requirement B) is purely additive
    passthrough for the low-mass dimuon diagnostic (e.g. charge, and
    whichever of OPTIONAL_MUON_DIAGNOSTIC_BRANCHES a given file has) --
    it does NOT affect the selection mask below in any way, which is
    unchanged from the pilot (RECIPE.md/PILOT_REPORT.md)."""
    fields = {
        "pt": events.Muon_pt, "eta": events.Muon_eta, "phi": events.Muon_phi,
        "mass": events.Muon_mass, "mediumId": events.Muon_mediumId,
        "pfRelIso04_all": events.Muon_pfRelIso04_all,
    }
    if extra_fields:
        fields.update(extra_fields)
    muons = ak.zip(fields)
    mask = (
        (muons.pt > MUON_PT_MIN_GEV)
        & (abs(muons.eta) < MUON_ETA_MAX)
        & muons.mediumId
        & (muons.pfRelIso04_all < MUON_ISO_MAX)
    )
    return muons[mask]


def select_electrons(events: ak.Array) -> ak.Array:
    electrons = ak.zip({
        "pt": events.Electron_pt, "eta": events.Electron_eta,
        "phi": events.Electron_phi, "mass": events.Electron_mass,
        "cutBased": events.Electron_cutBased,
    })
    mask = (
        (electrons.pt > ELECTRON_PT_MIN_GEV)
        & (abs(electrons.eta) < ELECTRON_ETA_MAX)
        & (electrons.cutBased >= ELECTRON_CUTBASED_MIN)
    )
    return electrons[mask]


def _clean_and_cut_jets(raw_jets: ak.Array, muons: ak.Array, electrons: ak.Array) -> ak.Array:
    """pt/eta/tight-ID cuts, then delta-R>=0.4 cleaning against every
    selected muon AND every selected electron (CMS jets include leptons in
    their constituents -- see DESIGN.md D3's ~93% overlap finding)."""
    kin_mask = (
        (raw_jets.pt > JET_PT_MIN_GEV)
        & (abs(raw_jets.eta) < JET_ETA_MAX)
        & ((raw_jets.jetId & 2) != 0)
    )
    cut_jets = raw_jets[kin_mask]

    jets_p4 = _p4(cut_jets)
    leptons = ak.concatenate([muons, electrons], axis=1)
    leptons_p4 = _p4(leptons)

    pairs_jet, pairs_lep = ak.unzip(ak.cartesian([jets_p4, leptons_p4], nested=True))
    dr = pairs_jet.deltaR(pairs_lep)
    min_dr = ak.min(dr, axis=-1)
    # A jet in an event with zero selected leptons has an empty inner list
    # (its event contributed no cartesian partners); ak.min on an empty
    # list gives None per jet -- fill with "far away" (i.e. clean). Using
    # fill_none alone (rather than a separate has-any-leptons ak.where)
    # keeps this uniformly per-jet-shaped -- mixing a per-event scalar
    # branch into ak.where here previously produced an irreducible union
    # type when some events had zero jets in this collection (e.g. no
    # b-tagged jets at all), confirmed via
    # studies/m0m1j0_cms/tests/test_selection_synthetic.py.
    min_dr = ak.fill_none(min_dr, JET_LEPTON_CLEAN_DR + 1.0)
    far_from_leptons = min_dr >= JET_LEPTON_CLEAN_DR

    return cut_jets[far_from_leptons]


def select_and_split_jets(events: ak.Array, muons: ak.Array, electrons: ak.Array) -> Dict[str, ak.Array]:
    """Split RAW jets into b-tagged/light first (ATLAS recipe order,
    RECIPE.md section 3), then apply jet cuts + lepton cleaning to both."""
    raw_jets = ak.zip({
        "pt": events.Jet_pt, "eta": events.Jet_eta, "phi": events.Jet_phi,
        "mass": events.Jet_mass, "jetId": events.Jet_jetId,
        "btagDeepFlavB": events.Jet_btagDeepFlavB,
    })
    is_bjet = raw_jets.btagDeepFlavB > BTAG_DEEPFLAVB_MEDIUM_WP
    raw_bjets = raw_jets[is_bjet]
    raw_light = raw_jets[~is_bjet]

    return {
        "BJets": _clean_and_cut_jets(raw_bjets, muons, electrons),
        "Jets": _clean_and_cut_jets(raw_light, muons, electrons),
    }


def compute_m0m1j0(muons: ak.Array, jets: ak.Array) -> ak.Array:
    """Invariant mass of leading muon + subleading muon + leading light
    jet, from full (pt, eta, phi, mass) four-vectors, in GeV. Only
    meaningful for events with >=2 muons and >=1 jet -- callers must
    restrict to such events first (ak.num checks below only guard against
    a crash on padding, not against a physically meaningless input)."""
    mu_order = ak.argsort(muons.pt, axis=1, ascending=False)
    sorted_muons = muons[mu_order]
    jet_order = ak.argsort(jets.pt, axis=1, ascending=False)
    sorted_jets = jets[jet_order]

    padded_mu = ak.pad_none(sorted_muons, 2, axis=1, clip=True)
    padded_jet = ak.pad_none(sorted_jets, 1, axis=1, clip=True)
    mu0, mu1, j0 = padded_mu[:, 0], padded_mu[:, 1], padded_jet[:, 0]

    p4_mu0 = _p4(mu0)
    p4_mu1 = _p4(mu1)
    p4_j0 = _p4(j0)
    total = p4_mu0 + p4_mu1 + p4_j0
    return ak.fill_none(total.mass, np.nan)


def compute_dimuon_mass(muons: ak.Array) -> ak.Array:
    """Invariant mass of the leading + subleading muon alone (no jet) --
    used only for the pilot's own sanity-check plot (Z peak near 91 GeV),
    not part of the m0m1j0 selection itself. Same four-vector convention
    as compute_m0m1j0."""
    order = ak.argsort(muons.pt, axis=1, ascending=False)
    sorted_muons = muons[order]
    padded = ak.pad_none(sorted_muons, 2, axis=1, clip=True)
    mu0, mu1 = padded[:, 0], padded[:, 1]
    total = _p4(mu0) + _p4(mu1)
    return ak.fill_none(total.mass, np.nan)


def compute_dimuon_diagnostics(muons: ak.Array) -> Dict[str, ak.Array]:
    """Step 2, requirement B: DIAGNOSTIC ONLY, no cut, does not touch the
    selection or the histograms. For the leading + subleading selected
    muon: delta-R between them, the product of their charges (+1 same-
    sign, -1 opposite-sign), the subleading/leading pT ratio, and
    (leading, subleading) values of whichever OPTIONAL_MUON_DIAGNOSTIC_
    BRANCHES were present in this file's `muons` record (NaN for any
    that were not -- see run_m0m1j0_on_file.py's optional-branch read).
    Used to help distinguish "duplicate reconstruction of one physical
    muon" (expect delta-R ~ 0, pT ratio ~ 1, often same charge, likely
    isGlobal/isTracker differing between the two) from "genuine collimated
    pair" (no such pattern) for the low-mass (<2, <4 GeV) dimuon events
    seen in the pilot's own sanity plot -- RECIPE.md/PILOT_REPORT.md do
    not decide this; that decision is explicitly out of scope here."""
    order = ak.argsort(muons.pt, axis=1, ascending=False)
    sorted_muons = muons[order]
    padded = ak.pad_none(sorted_muons, 2, axis=1, clip=True)
    mu0, mu1 = padded[:, 0], padded[:, 1]

    dr = ak.fill_none(_p4(mu0).deltaR(_p4(mu1)), np.nan)
    charge_product = ak.fill_none(mu0.charge * mu1.charge, 0)
    pt_ratio = ak.fill_none(mu1.pt / mu0.pt, np.nan)

    out = {"dr": dr, "charge_product": charge_product, "pt_ratio": pt_ratio}
    for branch in OPTIONAL_MUON_DIAGNOSTIC_BRANCHES:
        field = branch[len("Muon_"):]
        if field in muons.fields:
            out[f"{field}_mu0"] = ak.fill_none(mu0[field], np.nan)
            out[f"{field}_mu1"] = ak.fill_none(mu1[field], np.nan)
        else:
            n = len(muons)
            out[f"{field}_mu0"] = ak.Array(np.full(n, np.nan))
            out[f"{field}_mu1"] = ak.Array(np.full(n, np.nan))
    return out


def leading_jet_pt(jets: ak.Array) -> ak.Array:
    """pT of the leading (highest-pT) selected light jet per event -- used
    only for the pilot's own sanity-check plot."""
    order = ak.argsort(jets.pt, axis=1, ascending=False)
    sorted_jets = jets[order]
    padded = ak.pad_none(sorted_jets, 1, axis=1, clip=True)
    return ak.fill_none(padded[:, 0].pt, np.nan)


def build_object_record(muons: ak.Array, electrons: ak.Array, jets: Dict[str, ak.Array]) -> ak.Array:
    """Zips selected objects into the canonical field-name layout
    (Electrons/Muons/Jets/BJets) that
    ``services.calculations.physics_calcs.group_by_final_state`` expects
    -- reusing that function directly for the final-state category string
    rather than re-deriving its counting/capping logic."""
    return ak.zip(
        {"Electrons": electrons, "Muons": muons, "Jets": jets["Jets"], "BJets": jets["BJets"]},
        depth_limit=1,
    )


def apply_z_peak_and_mass_cutoff(mass: ak.Array) -> ak.Array:
    """Mirrors config.yaml's z_peak_cutoff (115 GeV) and max_mass_cutoff
    (10000 GeV), applied directly to the m0m1j0 mass -- see RECIPE.md
    section 5/6.3 for why z_peak_cutoff is NOT dilepton-only in this
    codebase and is therefore mirrored here rather than skipped."""
    keep = (mass >= Z_PEAK_CUTOFF_GEV) & (mass <= MAX_MASS_CUTOFF_GEV)
    return ak.where(keep, mass, np.nan)


def select_event_selection_cutflow(events: ak.Array, muon_extra_branches=None) -> Dict[str, ak.Array]:
    """Runs the full per-event selection chain and returns everything
    downstream code (histograms.py, the outlier-event list) needs,
    including a step-by-step cutflow count. Does not apply the golden-JSON
    filter -- callers apply that first (it needs a loaded
    ValidatedRunsFilter, kept out of this ROOT/validated-runs-free module
    on purpose) and pass in the already-filtered ``events``.

    `muon_extra_branches` (Step 2, requirement B): an iterable of raw
    NanoAOD branch names (e.g. ["Muon_charge", "Muon_isGlobal"]) present
    on `events`. Deliberately taken as NAMES, not pre-sliced arrays: this
    function extracts them from `triggered` -- i.e. AFTER the trigger cut
    below -- not from the caller's original `events`. A caller that
    instead pre-slices fields from `events` and passes those arrays in
    will silently have the WRONG length once the trigger cut removes any
    events (confirmed: this crashed every job of the very first Step 2
    full-run submission, 2026-09-22, with an ak.zip "cannot broadcast
    RegularArray of size <after-trigger> with RegularArray of size
    <before-trigger>" error -- exactly this mismatch. The pilot's own
    local integration test did not catch it because its synthetic fixture
    had every event pass the trigger, so before/after-trigger lengths
    happened to be equal there and only diverged on real data). Passing
    NAMES instead of arrays makes this bug structurally impossible: the
    extraction always happens against whatever `triggered` is here, at
    the one place that's authoritative for it.

    When given, `sel_muons` in the returned dict carries those fields
    through the same selection mask as every other muon property, so
    callers can run compute_dimuon_diagnostics(sel_muons) on it; the
    selection itself is UNAFFECTED either way -- this is passthrough only
    (see select_muons).
    """
    n_after_golden = len(events)

    triggered = apply_trigger(events)
    n_after_trigger = len(triggered)

    muon_extra_fields = None
    if muon_extra_branches:
        muon_extra_fields = {}
        for branch in muon_extra_branches:
            field = branch[len("Muon_"):] if branch.startswith("Muon_") else branch
            muon_extra_fields[field] = triggered[branch]

    muons = select_muons(triggered, extra_fields=muon_extra_fields)
    electrons = select_electrons(triggered)
    jets = select_and_split_jets(triggered, muons, electrons)

    has_ge2mu = ak.num(muons) >= 2
    n_after_ge2mu = int(ak.sum(has_ge2mu))

    has_ge1jet = ak.num(jets["Jets"]) >= 1
    final_mask = has_ge2mu & has_ge1jet
    n_after_ge1jet = int(ak.sum(final_mask))

    sel_events = triggered[final_mask]
    sel_muons = muons[final_mask]
    sel_electrons = electrons[final_mask]
    sel_jets = {"Jets": jets["Jets"][final_mask], "BJets": jets["BJets"][final_mask]}

    raw_mass = compute_m0m1j0(sel_muons, sel_jets["Jets"])
    mass = apply_z_peak_and_mass_cutoff(raw_mass)
    n_after_z_peak_and_mass_cutoff = int(ak.sum(~np.isnan(ak.to_numpy(mass))))

    obj_record = build_object_record(sel_muons, sel_electrons, sel_jets)

    return {
        "n_after_golden_json": n_after_golden,
        "n_after_trigger": n_after_trigger,
        "n_after_ge2mu": n_after_ge2mu,
        "n_after_ge1jet_after_cleaning": n_after_ge1jet,
        "n_after_z_peak_and_mass_cutoff": n_after_z_peak_and_mass_cutoff,
        "sel_events": sel_events,
        "sel_muons": sel_muons,
        "obj_record": obj_record,
        "raw_mass": raw_mass,
        "mass": mass,
    }
