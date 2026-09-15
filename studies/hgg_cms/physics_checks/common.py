"""
Shared helpers for the Phase 2.2 follow-up physics checks (A, B, C).

Selection definitions used everywhere below ("v1 + trigger-mimicking",
approximating arXiv:1804.02716 [CMS-HIG-16-040] Section 5.2 / Table 1 with
NanoAOD branches -- see DESIGN_SELECTION.md Section 2 and the "Update"
section this task adds):

Photon-level v1 preselection:
    pT > 20 GeV; (isScEtaEB OR isScEtaEE); Photon_electronVeto; Photon_mvaID_WP90.

Trigger-mimicking (TM) cuts, Table 1 of the paper (values re-verified
directly against the extracted paper text in this task -- see
physics_checks/table1_verification.txt -- and found to match the task's
statement exactly, no discrepancy):
    H/E < 0.08 (both regions).
    Barrel: R9 > 0.85, OR (0.5 < R9 <= 0.85 AND sieie < 0.015
             AND I_ph < 4.0 GeV AND I_tk < 6.0 GeV).
    Endcap: R9 > 0.90, OR (0.8 < R9 <= 0.90 AND sieie < 0.035
             AND I_ph < 4.0 GeV AND I_tk < 6.0 GeV).
    Charged isolation: (R9 > 0.8 AND I_ch < 20 GeV) OR (I_ch/pT < 0.3).

NanoAOD proxies for the paper's isolation variables (NOT identical to the
paper's own vertex-dependent definitions -- see DESIGN_SELECTION.md
Section 2 step 5 and the Update section):
    I_ch  ~= Photon_pfRelIso03_chg * Photon_pt
    I_ph  ~= (Photon_pfRelIso03_all - Photon_pfRelIso03_chg) * Photon_pt
             (this is "all minus charged", so it includes the neutral-
             hadron component too, not just photon PF candidates -- a
             conservative/looser proxy than the paper's I_ph, stated here
             explicitly since it was an assumption, not a verified match)
    I_tk  ~= I_ch  (no dedicated track-isolation branch in NanoAOD; using
             the charged PF isolation as a stand-in)

Event level: HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90
(unless a check states otherwise); leading two photons passing the photon
cuts; pT1 > mgg/3, pT2 > mgg/4; 100 < mgg < 180 GeV.

Mass from massless photons using stored Photon_pt/eta/phi. Photon_eCorr
is NEVER multiplied back in anywhere in this code.
"""
from __future__ import annotations

import numpy as np

TRIGGER = "HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"
BLIND_LO, BLIND_HI = 115.0, 135.0
EB_EE_GAP = (1.4442, 1.566)


def deltaR(eta1, phi1, eta2, phi2):
    dphi = np.abs(phi1 - phi2)
    dphi = np.where(dphi > np.pi, 2 * np.pi - dphi, dphi)
    return np.sqrt((eta1 - eta2) ** 2 + dphi ** 2)


def p4_massless(pt, eta, phi):
    px = pt * np.cos(phi)
    py = pt * np.sin(phi)
    pz = pt * np.sinh(eta)
    e = np.sqrt(px ** 2 + py ** 2 + pz ** 2)
    return e, px, py, pz


def diphoton_mass_massless(pt1, eta1, phi1, pt2, eta2, phi2):
    e1, px1, py1, pz1 = p4_massless(pt1, eta1, phi1)
    e2, px2, py2, pz2 = p4_massless(pt2, eta2, phi2)
    e, px, py, pz = e1 + e2, px1 + px2, py1 + py2, pz1 + pz2
    m2 = e ** 2 - px ** 2 - py ** 2 - pz ** 2
    return np.sqrt(m2) if np.isscalar(m2) else np.sqrt(np.clip(m2, 0, None))


def effective_sigma_68(values):
    """Half-width of the shortest interval containing 68.3% of `values`."""
    values = np.sort(np.asarray(values))
    n = len(values)
    if n < 4:
        return None
    k = int(np.ceil(0.683 * n))
    if k >= n:
        return 0.5 * float(values[-1] - values[0])
    widths = values[k:] - values[:n - k]
    i = np.argmin(widths)
    return 0.5 * float(widths[i])


def histogram_mode(values, bin_width=0.5, lo=None, hi=None):
    """Mode from a fine histogram (bin centre of the tallest bin)."""
    values = np.asarray(values)
    if lo is None:
        lo = values.min()
    if hi is None:
        hi = values.max()
    if hi <= lo:
        return float(values[0]) if len(values) else None
    nbins = max(1, int(round((hi - lo) / bin_width)))
    counts, edges = np.histogram(values, bins=nbins, range=(lo, hi))
    i = np.argmax(counts)
    return float(0.5 * (edges[i] + edges[i + 1]))


def bootstrap_stat(values, func, n_boot=200, seed=0):
    """Bootstrap standard error of `func(values)`."""
    values = np.asarray(values)
    n = len(values)
    if n < 8:
        return None
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(n_boot):
        sample = values[rng.integers(0, n, size=n)]
        s = func(sample)
        if s is not None:
            stats.append(s)
    if len(stats) < 8:
        return None
    return float(np.std(stats, ddof=1))


def binomial_err(k, n):
    if n == 0:
        return None
    p = k / n
    return float(np.sqrt(p * (1 - p) / n))


def photon_v1_mask(pt, eb, ee, evtoveto, mva90):
    return (pt > 20.0) & (eb | ee) & evtoveto & mva90


def photon_tm_mask(pt, eb, ee, hoe, r9, sieie, i_ch, i_ph, i_tk):
    """Trigger-mimicking cuts, Table 1 + the combined charged-iso requirement."""
    hoe_ok = hoe < 0.08

    barrel_tight = r9 > 0.85
    barrel_loose = (r9 > 0.5) & (r9 <= 0.85) & (sieie < 0.015) & (i_ph < 4.0) & (i_tk < 6.0)
    barrel_ok = eb & (barrel_tight | barrel_loose)

    endcap_tight = r9 > 0.90
    endcap_loose = (r9 > 0.8) & (r9 <= 0.90) & (sieie < 0.035) & (i_ph < 4.0) & (i_tk < 6.0)
    endcap_ok = ee & (endcap_tight | endcap_loose)

    shower_ok = barrel_ok | endcap_ok

    charged_ok = ((r9 > 0.8) & (i_ch < 20.0)) | (np.divide(i_ch, pt, out=np.full_like(pt, np.inf), where=pt > 0) < 0.3)

    return hoe_ok & shower_ok & charged_ok


def compute_isolation_proxies(pt, iso_all, iso_chg):
    i_ch = iso_chg * pt
    i_ph = (iso_all - iso_chg) * pt
    i_tk = i_ch
    return i_ch, i_ph, i_tk
