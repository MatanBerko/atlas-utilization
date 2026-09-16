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
     not the hardcoded 100-180 GeV H->gamma-gamma window -- the main
     Z->ee sample uses 70-110 GeV, the trigger-efficiency sample uses
     >~95 GeV (see run_zee_selection_on_chunks.py's own CLI). Re-derived
     here (not reusing studies.hgg_cms.selection.leading_pair_mass, which
     hardcodes its window as module-level constants) rather than
     modifying that module, consistent with this project's established
     "verbatim copy for a variant, don't parametrize the original" style
     (see studies/hgg_cms/selection.py's own docstring re:
     physics_checks/common.py).

No blinding logic here at all -- unlike the H->gamma-gamma signal region,
a Z peak at ~91 GeV is not a blinded quantity for this analysis, and the
70-110 / >95 GeV windows used here don't overlap the H->gamma-gamma blind
window (115-135 GeV) in any case.
"""
from __future__ import annotations

from typing import Dict, Optional

import awkward as ak
import numpy as np

from studies.hgg_cms.selection import apply_tm_selection, diphoton_mass_massless

DEFAULT_MASS_LO, DEFAULT_MASS_HI = 70.0, 110.0


def leading_pair_mass_windowed(photons: ak.Array, mass_lo: float, mass_hi: Optional[float]) -> Dict[str, ak.Array]:
    """Same pairing/scaled-pT/category logic as
    studies.hgg_cms.selection.leading_pair_mass, but with a caller-supplied
    mass window instead of the hardcoded 100-180 GeV one. ``mass_hi=None``
    means no upper bound (used by the trigger-efficiency sample's
    ">~95 GeV" window)."""
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
