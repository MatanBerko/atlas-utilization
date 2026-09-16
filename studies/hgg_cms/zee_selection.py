"""
Z->e+e- control-region selection (implementation task 6, Part 4), via
photon-object reconstruction -- the same tag-and-probe method the
reference paper itself uses (arXiv:1804.02716 Section 1 / Table 2; see
DESIGN_SELECTION.md Section 5.2).

Same photon-collection selection as the main H->gamma-gamma analysis
(studies.hgg_cms.selection): trigger-mimicking (TM) cuts (H/E, R9, sieie,
isolation -- REUSED verbatim from studies.hgg_cms.selection, unchanged,
since those formulas don't reference electronVeto at all), leading-pT-pair
forming, and the same scaled-pT cuts (pT1 > m/3, pT2 > m/4) -- but with
TWO changes from the main analysis:

  1. Photon_electronVeto is INVERTED here (electronVeto == False required,
     not True) -- electrons reconstructed as "photon" objects are exactly
     what this control sample wants. This is done HERE, at the analysis
     layer, not by the parsing-stage kinematic_cuts (which only supports
     "must be True"/"at least one of these is True" -- there is no "must
     be False" cut type in services/calculations/physics_calcs.py, and
     adding one would be a shared-pipeline code change, out of this
     task's scope). The Z->ee parsing configs (config.cms_hgg_zee_*.yaml)
     therefore simply OMIT electronVeto from kinematic_cuts.bool_require
     entirely, so both electronVeto==True and ==False photons survive
     into the parsed chunks; this module is what actually selects the
     ==False ones.

  2. The final pair-mass window is a parameter (``mass_lo``/``mass_hi``),
     not the hardcoded 100-180 GeV H->gamma-gamma window. Re-derived here
     (not reusing studies.hgg_cms.selection.leading_pair_mass, which
     hardcodes its window as module-level constants) rather than
     modifying that module, consistent with this project's established
     "verbatim copy for a variant, don't parametrize the original" style
     (see studies/hgg_cms/selection.py's own docstring re:
     physics_checks/common.py).

REVISED (16 Sep 2026): the STORED output window is now ONE fixed range,
60-180 GeV (``DEFAULT_MASS_LO``/``DEFAULT_MASS_HI`` below), covering
every downstream offline sub-sample this task needs from a single parsed
dataset -- narrower per-purpose windows (70-110 for the energy-scale
sample, >95 for the trigger-efficiency probe, the same 70-110 again for
the Mass90-sculpting demonstration) are all just OFFLINE CUTS on this one
stored table (studies/hgg_cms/validation/zee/), not separate parsing
runs or separate stored-mass windows. This replaces an earlier design
that ran two DIFFERENT windows through two DIFFERENT cluster job
variants -- collapsed into one pass once it became clear the real
distinguishing cut between the "energy scale" and "trigger efficiency"
sub-samples is which TRIGGER BIT fired (Ele27 for both), not the mass
window.

  - **Lower bound (60 GeV)**: comfortably below the Z lineshape's own
    low-mass tail (a few GeV width) with wide margin, and a standard
    lower edge for a Z-window control sample in CMS-style analyses.
  - **Upper bound (180 GeV), justified explicitly**: matches the main
    H->gamma-gamma analysis's own upper mass edge (studies.hgg_cms.
    selection.MASS_HI) for two concrete reasons: (a) it is wide enough to
    show the FULL shape of the Mass90-sculpting demonstration (2c) --
    the depletion is expected just below ~90 GeV, and seeing a good
    stretch of UNDEPLETED spectrum above it (up to 110, the energy-scale
    window's own upper edge, with margin beyond) is needed to see the
    depletion is a real feature, not an artifact of the window's own
    edge; (b) it lets this control sample's high-mass tail be directly
    compared against the main analysis's own 135-180 GeV sideband
    region's background composition, useful context for the electron
    -veto-leakage estimate (see studies/hgg_cms/validation/zee/
    hgg_leakage_estimate.py) without needing yet another window choice.
    Going higher than 180 GeV serves no purpose this task needs.

BLINDING -- NO H->gamma-gamma EXPOSURE, STATED EXPLICITLY: the 60-180
GeV window numerically OVERLAPS the H->gamma-gamma blind window
(115-135 GeV), but this is NOT a blinding violation and NOT the
H->gamma-gamma signal region. The leading pair selected here is built
from photons with ``electronVeto == False`` (inverted); the main
H->gamma-gamma analysis's own selection (studies.hgg_cms.selection,
config.cms_hgg_data.yaml's parsing-level filter) requires
``electronVeto == True`` on both leading photons. These are two
DISJOINT-BY-CONSTRUCTION candidate objects -- a photon cannot
simultaneously satisfy ``electronVeto == True`` and ``== False``, so the
leading pair this module selects is never the same pair (often not even
drawn from the same photon subset at all) as the main analysis's own
diphoton candidate. The output field is named ``m_ee`` (never ``m_gg``)
specifically so no tool -- including this project's own blinding
asserts, which key on ``m_gg`` -- could ever conflate the two. No script
in this task reads, prints, or plots this sample's 115-135 GeV events as
if they were H->gamma-gamma signal-region data, and none should.
"""
from __future__ import annotations

from typing import Dict, Optional

import awkward as ak
import numpy as np

from studies.hgg_cms.selection import apply_tm_selection, diphoton_mass_massless

DEFAULT_MASS_LO, DEFAULT_MASS_HI = 60.0, 180.0

# Offline sub-window cuts (studies/hgg_cms/validation/zee/ applies these
# to the ONE stored 60-180 GeV table -- not separate stored windows).
ENERGY_SCALE_MASS_LO, ENERGY_SCALE_MASS_HI = 70.0, 110.0
TRIGGER_EFF_MASS_LO = 95.0


def leading_pair_mass_windowed(photons: ak.Array, mass_lo: float, mass_hi: Optional[float]) -> Dict[str, ak.Array]:
    """Same pairing/scaled-pT/category logic as
    studies.hgg_cms.selection.leading_pair_mass, but with a caller-supplied
    mass window instead of the hardcoded 100-180 GeV one. ``mass_hi=None``
    means no upper bound. The cluster job always calls this with the
    STORED window (DEFAULT_MASS_LO/HI, 60-180) -- narrower windows
    (ENERGY_SCALE_*, TRIGGER_EFF_MASS_LO) are applied OFFLINE, as cuts on
    that stored table, not by calling this function again with a
    different window."""
    has_pair = ak.num(photons) >= 2
    order = ak.argsort(photons.pt, axis=1, ascending=False)
    sorted_photons = photons[order]
    padded = ak.pad_none(sorted_photons, 2, axis=1, clip=True)
    lead = padded[:, 0]
    sublead = padded[:, 1]

    mgg = diphoton_mass_massless(lead.pt, lead.eta, lead.phi, sublead.pt, sublead.eta, sublead.phi)
    scaled_ok = (lead.pt > mgg / 3.0) & (sublead.pt > mgg / 4.0)
    window_ok = mgg > mass_lo
    if mass_hi is not None:
        window_ok = window_ok & (mgg < mass_hi)

    both_eb = ak.to_numpy(ak.fill_none(lead.isScEtaEB & sublead.isScEtaEB, False))
    cat = ak.Array(np.where(both_eb, "EBEB", "notEBEB"))

    return {
        "has_pair": has_pair,
        "scaled_and_window_ok": ak.fill_none(scaled_ok & window_ok, False),
        "mgg": ak.fill_none(mgg, np.nan),
        "category": cat,
        "lead": lead,
        "sublead": sublead,
    }


def select_zee_events(events: ak.Array, mass_lo: float = DEFAULT_MASS_LO,
                       mass_hi: Optional[float] = DEFAULT_MASS_HI) -> Dict[str, ak.Array]:
    """Full Z->ee (via inverted-electronVeto photon objects) selection on
    one chunk of pipeline output (photons already v1-preselected EXCEPT
    for electronVeto -- see module docstring). Mirrors
    studies.hgg_cms.selection.select_diphoton_events's structure/return
    shape exactly (so the same output-writing pattern applies), with
    "selected" now meaning "passes the inverted-electronVeto Z->ee
    selection with the given mass window", not the H->gamma-gamma one."""
    photons = events["Photons"]
    inverted_veto_photons = photons[~photons.electronVeto]
    tm_photons = apply_tm_selection(inverted_veto_photons)
    pair = leading_pair_mass_windowed(tm_photons, mass_lo, mass_hi)

    selected = pair["has_pair"] & pair["scaled_and_window_ok"]

    return {
        "n_tm_photons": ak.num(tm_photons),
        "has_pair": pair["has_pair"],
        "mgg": pair["mgg"],
        "category": pair["category"],
        "selected": selected,
        "lead": pair["lead"],
        "sublead": pair["sublead"],
    }
