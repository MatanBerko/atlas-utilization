"""
H->gamma-gamma event selection (implementation task 6, Part B3).

Consumes the shared pipeline's parsed output (see this package's
README/PIPELINE.md for the exact data flow) -- ROOT files with a flat
"events" tree, one branch per photon field (``Photons_pt``,
``Photons_eta``, ...) plus scalar branches (``run``, ``luminosityBlock``,
``event``, ``PV_npvsGood``, and for simulation ``genWeight``,
``Pileup_nTrueInt``, ``source_record``).

The pipeline's own config (config.cms_hgg_data.yaml / config.cms_hgg_signal.yaml)
already applies the "v1" photon preselection to every photon in the output
(pt > 20 GeV, electronVeto, mvaID_WP90, isScEtaEB-or-isScEtaEE -- see
``physics_checks/common.py``'s ``photon_v1_mask``, and this task's B2
kinematic_cuts). This module applies everything AFTER that: the
trigger-mimicking (TM) cuts, pairing, mass, the scaled-pT cuts, the mass
window, and the barrel/endcap category -- using DEFINITIONS IDENTICAL to
``physics_checks/common.py`` (a verbatim copy of the design branch's
reference implementation, not re-derived).

``physics_checks/common.py`` operates on flat, per-event numpy arrays
(used for a small, non-vectorized, one-event-at-a-time reference
computation in the original physics checks). For a full file's worth of
events, this module re-expresses the SAME formulas in a vectorized,
awkward-array-native form (jagged: variable photons per event) --
verified event-by-event identical to common.py's own functions in
tests/test_selection_equivalence.py, not just assumed equivalent, because
one numpy idiom common.py uses (``np.divide(..., out=..., where=...)``)
does not work on awkward arrays at all (confirmed: raises TypeError) and
had to be rewritten as ``ak.where(...)``.

BLINDING: this module returns per-event masses for ALL events (data and
simulation) -- it does not know or care which caller will look at data.
Blinding (never printing/plotting an individual data mass in
[115, 135] GeV) is the OUTPUT WRITER's job (see output.py), not this
module's. Never touches ``Photon_eCorr``.
"""
from __future__ import annotations

from typing import Dict, Tuple

import awkward as ak
import numpy as np

MASS_LO, MASS_HI = 100.0, 180.0


def p4_massless(pt: ak.Array, eta: ak.Array, phi: ak.Array):
    """Same formula as common.py's p4_massless, vectorized over jagged
    awkward arrays instead of flat numpy."""
    px = pt * np.cos(phi)
    py = pt * np.sin(phi)
    pz = pt * np.sinh(eta)
    e = np.sqrt(px ** 2 + py ** 2 + pz ** 2)
    return e, px, py, pz


def diphoton_mass_massless(pt1, eta1, phi1, pt2, eta2, phi2):
    """Same formula as common.py's diphoton_mass_massless, vectorized."""
    e1, px1, py1, pz1 = p4_massless(pt1, eta1, phi1)
    e2, px2, py2, pz2 = p4_massless(pt2, eta2, phi2)
    e, px, py, pz = e1 + e2, px1 + px2, py1 + py2, pz1 + pz2
    m2 = e ** 2 - px ** 2 - py ** 2 - pz ** 2
    return np.sqrt(ak.where(m2 > 0, m2, 0.0))


def compute_isolation_proxies(pt, iso_all, iso_chg):
    """Identical formula to common.py's compute_isolation_proxies."""
    i_ch = iso_chg * pt
    i_ph = (iso_all - iso_chg) * pt
    i_tk = i_ch
    return i_ch, i_ph, i_tk


def photon_tm_mask(pt, eb, ee, hoe, r9, sieie, i_ch, i_ph, i_tk):
    """Trigger-mimicking cuts -- same thresholds as common.py's
    photon_tm_mask (Table 1 + the combined charged-isolation requirement),
    rewritten for jagged awkward arrays: the one line that used
    ``np.divide(..., out=..., where=...)`` (not supported on awkward
    arrays -- confirmed to raise TypeError, see this module's docstring)
    is replaced with the equivalent ``ak.where``, verified event-by-event
    identical to common.py's own output in
    tests/test_selection_equivalence.py."""
    hoe_ok = hoe < 0.08

    barrel_tight = r9 > 0.85
    barrel_loose = (r9 > 0.5) & (r9 <= 0.85) & (sieie < 0.015) & (i_ph < 4.0) & (i_tk < 6.0)
    barrel_ok = eb & (barrel_tight | barrel_loose)

    endcap_tight = r9 > 0.90
    endcap_loose = (r9 > 0.8) & (r9 <= 0.90) & (sieie < 0.035) & (i_ph < 4.0) & (i_tk < 6.0)
    endcap_ok = ee & (endcap_tight | endcap_loose)

    shower_ok = barrel_ok | endcap_ok

    ich_over_pt = ak.where(pt > 0, i_ch / pt, np.inf)
    charged_ok = ((r9 > 0.8) & (i_ch < 20.0)) | (ich_over_pt < 0.3)

    return hoe_ok & shower_ok & charged_ok


def apply_tm_selection(photons: ak.Array) -> ak.Array:
    """Photons already passed the pipeline's v1 preselection (pt>20,
    electronVeto, mvaID_WP90, isScEtaEB-or-EE). Returns the subset that
    ALSO passes the trigger-mimicking cuts."""
    i_ch, i_ph, i_tk = compute_isolation_proxies(
        photons.pt, photons.pfRelIso03_all, photons.pfRelIso03_chg
    )
    tm_mask = photon_tm_mask(
        photons.pt, photons.isScEtaEB, photons.isScEtaEE,
        photons.hoe, photons.r9, photons.sieie, i_ch, i_ph, i_tk,
    )
    return photons[tm_mask]


def leading_pair_mass(photons: ak.Array) -> Dict[str, ak.Array]:
    """For events with >=2 TM-passing photons, take the two highest-pT
    ones (leading pair -- NOT "any pair"), compute the diphoton mass, the
    scaled-pT cut values, and the category. Events with <2 TM-passing
    photons get masked out entirely (not just given NaN/None) -- callers
    must combine the returned "has_pair" mask with their own event
    selection.

    Returns a dict of per-event (flat, not jagged) awkward arrays, one
    entry per event in the input: has_pair, mgg, pt1, pt2, eta1, eta2,
    phi1, phi2, cat, plus the full per-photon record for lead/sublead
    (r9, hoe, sieie, pfRelIso03_all, pfRelIso03_chg, mvaID, isScEtaEB,
    isScEtaEE) for the output writer.
    """
    has_pair = ak.num(photons) >= 2
    # Sort by pt descending within each event; pad/clip so indexing [0]/[1]
    # is always safe even for events with <2 photons (their result is
    # discarded via has_pair, but must not crash while being computed).
    order = ak.argsort(photons.pt, axis=1, ascending=False)
    sorted_photons = photons[order]
    padded = ak.pad_none(sorted_photons, 2, axis=1, clip=True)
    lead = padded[:, 0]
    sublead = padded[:, 1]

    mgg = diphoton_mass_massless(lead.pt, lead.eta, lead.phi, sublead.pt, sublead.eta, sublead.phi)
    scaled_ok = (lead.pt > mgg / 3.0) & (sublead.pt > mgg / 4.0)
    mass_window_ok = (mgg > MASS_LO) & (mgg < MASS_HI)

    both_eb = ak.to_numpy(ak.fill_none(lead.isScEtaEB & sublead.isScEtaEB, False))
    cat = ak.Array(np.where(both_eb, "EBEB", "notEBEB"))

    return {
        "has_pair": has_pair,
        "scaled_and_window_ok": ak.fill_none(scaled_ok & mass_window_ok, False),
        "mgg": ak.fill_none(mgg, np.nan),
        "category": cat,
        "lead": lead,
        "sublead": sublead,
    }


def select_diphoton_events(events: ak.Array) -> Dict[str, ak.Array]:
    """Full analysis-layer selection on one chunk of pipeline output
    (photons already v1-preselected). Returns a dict of per-event flat
    arrays for every ORIGINAL input event, with a final ``selected`` mask
    -- callers slice ``events`` (and their own genWeight/run/etc.) by that
    mask themselves, so this function never has to know about
    data-vs-simulation columns.
    """
    photons = events["Photons"]
    tm_photons = apply_tm_selection(photons)
    pair = leading_pair_mass(tm_photons)

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
