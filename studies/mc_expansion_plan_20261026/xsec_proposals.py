"""Cross-section PROPOSALS for the planned MC samples (26 Oct 2026) -- for Matan's manual check.

NOT a registry. Nothing here is applied anywhere. Every source number below was read on
26 Oct 2026 from the page named in SOURCES (the location and the number as printed are in SOURCES, copied into evidence/xsec_proposals.json);
every generator value comes from the MiniAOD record in evidence/records/ (portal API).

    python3 studies/mc_expansion_plan_20261026/xsec_proposals.py

writes evidence/xsec_proposals.json and XSEC_PROPOSALS.md.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from plan_samples import SAMPLES  # noqa: E402

# ---- sources: key -> (url, where on the page, number(s) exactly as printed) ----
SOURCES = {
    "TTBAR": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/TtbarNNLO",
              "table 'Updated reference cross sections ...' (Updated: July 2022), block '13 TeV', column 'Central value'",
              "833.9"),
    "ST_NNLO_T": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef",
                  "section 'Single top-quark t channel cross-sections', 13 TeV table, rows 'top quark' / 'top antiquark' (MCFM NNLO, mt = 172.5 GeV, page dated 2026-10-02)",
                  "134.2 / 80.0"),
    "ST_NNLO_S": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef",
                  "section 'Single-top-quark s channel cross-sections', 13 TeV table, rows 'top quark' / 'top antiquark' / 'top quark + antiquark' (NNLO, Liu & Gao arXiv:1807.03835)",
                  "6.828 / 4.245 / 11.073"),
    "ST_NNLO_TW": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef",
                   "section 'Single-top-quark tW channel cross-sections', 13 TeV, row 'top quark + antiquark' (NLO + NNLL soft-gluon third order, Kidonakis arXiv:2102.11300)",
                   "79.3"),
    "ST_NLO_T": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec",
                 "section 'Single-top t channel cross sections (superseded)', 13 TeV, rows 'top' / 'anti-top' (Hathor NLO)",
                 "136.02 / 80.95"),
    "ST_NLO_S": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec",
                 "section 'Single-top s channel cross sections', 13 TeV, rows 'top' / 'anti-top' / 'top + anti-top' (Hathor NLO)",
                 "6.35 / 3.97 / 10.32"),
    "ST_TW_OLD": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec",
                  "section 'Single-top Wt channel cross sections', 13 TeV, row 'top + antitop' (Kidonakis approx. NNLO)",
                  "71.7"),
    "PDG_W": ("https://pdglive.lbl.gov/Particle.action?node=S043",
              "W DECAY MODES: e+ nu, mu+ nu, tau+ nu, hadrons",
              "(10.71 ± 0.16) %, (10.63 ± 0.15) %, (11.38 ± 0.21) %, (67.41 ± 0.27) %"),
    "PDG_Z": ("https://pdglive.lbl.gov/Particle.action?node=S044",
              "Z DECAY MODES: Gamma1 e+e-, Gamma2 mu+mu-, Gamma3 tau+tau-, Gamma7 invisible, Gamma8 hadrons",
              "(3.3632 ± 0.0042) %, (3.3662 ± 0.0066) %, (3.3696 ± 0.0083) %, (20.000 ± 0.055) %, (69.911 ± 0.056) %"),
    "RAZOR": ("https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat",
              "line 64, under '#13 TeV Spring 15 MC' (SECONDARY source; same table as our DY 1921.8*3, line 90)",
              "WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7"),
    "ATLAS_W": ("https://arxiv.org/abs/1603.09222",
                "ATLAS, PLB 759 (2016) 601, Table 3, row 'W±', 'Predicted ... Total' (DYNNLO NNLO QCD + NLO EW, CT14nnlo; per lepton flavour)",
                "20.08 nb"),
    "WZ": ("https://arxiv.org/abs/1604.08576",
           "Table 1 (on-shell W±Z), row √s = 13: σNLO, σNNLO",
           "46.068(3) pb, 51.11(3) pb"),
    "ZZ": ("https://arxiv.org/abs/1405.2219",
           "Table 1 (inclusive ZZ, includes gg → ZZ at NNLO), row 13: σNLO, σNNLO",
           "14.51 pb, 16.91 pb"),
    "WW": ("https://arxiv.org/abs/1408.5243",
           "Table I (on-shell W+W−, 4FNS, includes gg → WW), row 13: σNNLO",
           "118.7 pb"),
    "TTTT_NLO": ("https://arxiv.org/abs/1711.02116",
                 "Table 5, µ = HT/4, column 'LO + NLO' (complete NLO QCD+EW)",
                 "11.97 fb"),
    "TTTT_NLL": ("https://arxiv.org/abs/2212.03259",
                 "Table I, √s = 13 TeV, NLO(QCD+EW)+NLL′ (µ0 = 2 mt)",
                 "14.65(2) fb"),
    "YR4_XS": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV",
               "rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table",
               "ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227; ttH 5.071E-01 (pb)"),
    "YR4_BR": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR",
               "rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)",
               "bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04"),
    "JHUGEN": ("https://raw.githubusercontent.com/JHUGen/JHUGen/master/JHUGenerator/main.F90",
               "comment block at lines 357-368 (JHUGen master; the samples used v7.x -- assumed unchanged, UNVERIFIED for the exact version)",
               "DecayMode=0: Z --> l+ l- (l=e,mu); 3: Z --> nu nubar; 8: Z --> l+ l- (l=e,mu,tau); 10: W --> l nu_l (l=e,mu,tau); 11: W --> anything"),
}

# ---- the numbers, as printed by the sources above ----
TT = 833.9
W_E, W_MU, W_TAU, W_HAD = 0.1071, 0.1063, 0.1138, 0.6741
W_L = W_E + W_MU + W_TAU                       # 0.3272
Z_EE, Z_MM, Z_TT, Z_INV, Z_HAD = 0.033632, 0.033662, 0.033696, 0.20000, 0.69911
Z_LL = Z_EE + Z_MM + Z_TT                      # 0.10099
ST_T, ST_TBAR = 134.2, 80.0
ST_S = 11.073                                  # 6.828 + 4.245
ST_T_NLO, ST_TBAR_NLO, ST_S_NLO = 136.02, 80.95, 10.32
W_RAZOR = 61526.7
W_ATLAS = 3 * 20080.0                          # 20.08 nb per flavour x 3 flavours
WZ_NLO, WZ_NNLO = 46.068, 51.11
ZZ_NLO, ZZ_NNLO = 14.51, 16.91
WW_NNLO = 118.7
GGF, VBF, WPH, WMH, QQZH, GGZH, TTH = 48.58, 3.782, 0.8400, 0.5328, 0.7612, 0.1227, 0.5071
BR_BB, BR_TAUTAU, BR_WW, BR_ZZ, BR_4L = 0.5824, 0.06272, 0.2137, 0.02619, 2.745e-4

K_WZ = WZ_NNLO / WZ_NLO
K_ZZ = ZZ_NNLO / ZZ_NLO


def portal():
    rows = json.loads((HERE / "evidence" / "records_summary.json").read_text())["rows"]
    return {r["nano_recid"]: r for r in rows}


P = portal()


def gen(recid):
    x = P[recid]["portal_cross_section"] or {}
    return float(x["total_value"]) if x.get("total_value") else None


# W+jets: jet-binned NLO set, k = NNLO inclusive / sum of the three generator values
W_BINS_GEN = gen(69715) + gen(69717) + gen(69719)
K_W = W_RAZOR / W_BINS_GEN


def P_(recid, key, sentence, factors, order, convention, look, alternatives, notes=""):
    """factors: list of (label, value, source key or 'portal')."""
    value = math.prod(v for _, v, _ in factors)
    return dict(recid=recid, sentence=sentence, factors=factors, sigma_eff_pb=value, order=order,
                convention=convention, look=look, alternatives=alternatives, notes=notes, key=key)


def proposals():
    out = []
    a = out.append
    ttlook = ("TtbarNNLO: the 13 TeV block of the first table, 'Central value' = 833.9. "
              "pdglive S043: the four W decay fractions.")
    # ---------------- tier 1 ----------------
    for rid, j in ((69715, "0J"), (69717, "1J"), (69719, "2J")):
        a(P_(rid, "W", f"W boson decaying to a charged lepton (e, μ or τ) and a neutrino, with exactly {j[0]} extra parton(s) in the NLO matrix element (one of three pieces that together make all of W+jets).",
             [(f"generator σ (portal, {j} piece)", gen(rid), "portal"),
              ("k = 61526.7 / (53300 + 8958 + 3330), NNLO inclusive ÷ sum of the three NLO pieces", K_W, "RAZOR")],
             "NLO generator × NNLO/NLO k-factor (inclusive W → ℓν, FEWZ NNLO in the table)",
             "No published total for a jet-multiplicity piece → generator × k-factor. The k-factor numerator is the same SECONDARY table as our DY (Matan, 15 Oct), for consistency. Not a paper table, so the 'k-factor from a paper table' rule is only partly met.",
             "RazorAnalyzer xSections.dat line 64: 'WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7'. The three portal values on the MiniAOD records 69714 / 69716 / 69718 (metadata.cross_section.total_value).",
             [("k from the inclusive NLO sample instead (61526.7 / 66970)", W_RAZOR / gen(69745) / K_W - 1),
              ("primary source instead: ATLAS 1603.09222 Table 3, 3 × 20.08 nb = 60240 pb", W_ATLAS / W_RAZOR - 1)],
             "Portal matching efficiencies 0.9 / 0.2 / 0.1 are shown but NOT multiplied in. The three portal values add up to 65588 pb, close to the inclusive NLO sample's 66970 pb, which suggests total_value already includes the matching efficiency (if it did not, the pieces would sum to 50095 pb). Also, the inclusive NLO value 66970 pb × 0.4 = 26788 pb would be less than half of every W → ℓν prediction and measurement (ATLAS measured 3 × 20.64 nb), so for this record total_value must already include the matching efficiency. Evidence for the open point, not a decision."))
    a(P_(69745, "W", "Inclusive W → ℓν (e, μ, τ) + 0, 1, 2 partons at NLO (alternative to the three pieces).",
         [("NNLO inclusive W → ℓν, 3 lepton flavours", W_RAZOR, "RAZOR")],
         "NNLO QCD (secondary table)", "Table value, same construction as our DY M-50 (3 × 1921.8).",
         "RazorAnalyzer line 64 (61526.7).",
         [("ATLAS 1603.09222 Table 3 (primary), 60240 pb", W_ATLAS / W_RAZOR - 1)]))
    a(P_(69747, "W", "Inclusive W → ℓν (e, μ, τ) + up to 4 partons at LO (alternative; the only set that could be stitched with the LO jet-/HT-binned samples).",
         [("NNLO inclusive W → ℓν, 3 lepton flavours", W_RAZOR, "RAZOR")],
         "NNLO QCD (secondary table) applied to an LO sample", "Table value; an LO sample normalised to NNLO (k = 61526.7 / 54110 = 1.137 relative to its generator value).",
         "RazorAnalyzer line 64 (61526.7).",
         [("ATLAS 1603.09222 Table 3 (primary), 60240 pb", W_ATLAS / W_RAZOR - 1)]))
    for rid, nm, val, nlo, fs in ((64793, "top", ST_T, ST_T_NLO, "5"), (64693, "antitop", ST_TBAR, ST_TBAR_NLO, "5"),
                                  (64759, "top", ST_T, ST_T_NLO, "4"), (64659, "antitop", ST_TBAR, ST_TBAR_NLO, "4")):
        a(P_(rid, "STT", f"Single {nm} production in the t-channel ({fs}-flavour scheme), all top decays.",
             [(f"σ(t-channel {nm}), NNLO", val, "ST_NNLO_T")],
             "NNLO QCD (MCFM)", "Top WG recommendation (the old Hathor NLO page now says 'Superseded by NNLO predictions').",
             f"SingleTopNNLORef, 't channel' 13 TeV table, row '{'top quark' if nm == 'top' else 'top antiquark'}', Central value = {val}.",
             [("Top WG Hathor NLO (superseded)", nlo / val - 1)]))
    a(P_(64635, "STS", "Single top (or antitop) in the s-channel, top decaying to b + W → ℓν (e, μ, τ).",
         [("σ(s-channel, top + antitop), NNLO", ST_S, "ST_NNLO_S"),
          ("BR(W → ℓν) = 0.1071 + 0.1063 + 0.1138", W_L, "PDG_W")],
         "NNLO QCD", "Top WG recommendation × PDG individually measured W branching ratios (settled convention).",
         "SingleTopNNLORef, 's channel' 13 TeV table, row 'top quark + antiquark' = 11.073. pdglive S043.",
         [("Top WG Hathor NLO (10.32 pb)", ST_S_NLO / ST_S - 1)],
         "Generator card (evidence/cards/64635): 'decay t > w+ b, w+ > ell+ vl' with ell = e, μ, τ."))
    a(P_(67841, "TTH", "Top-quark pairs with both W bosons decaying to quarks.",
         [("σ(tt̄), NNLO+NNLL, mt = 172.5 GeV", TT, "TTBAR"), ("BR(W → hadrons)²", W_HAD ** 2, "PDG_W")],
         "NNLO+NNLL", "Settled convention (833.9 pb × 0.6741², as in the hint).", ttlook, [],
         "With the individual PDG values the three tt̄ samples add up to 0.10706 + 0.44113 + 0.45441 = 1.0026 of tt̄ (the PDG W fractions sum to 1.0013). A +0.26 % overcount of tt̄ that follows from the settled convention; reported, not changed."))
    # ---------------- tier 2 ----------------
    wz_look = "arXiv:1604.08576 Table 1, row 13: σNLO 46.068, σNNLO 51.11. The portal value on the MiniAOD record."
    a(P_(72742, "WZ", "W → quarks plus a lepton pair (e, μ, τ; Z or virtual photon, m(ℓℓ) > 4 GeV), NLO, 0-1 extra parton.",
         [("generator σ (portal)", gen(72742), "portal"), ("k = 51.11 / 46.068 (WZ NNLO/NLO)", K_WZ, "WZ")],
         "NLO generator × NNLO/NLO k-factor", "Phase space (γ* included, m(ℓℓ) > 4) matches no published total → generator × k-factor, exactly as our WZTo3LNu 72752.",
         wz_look, [("on-shell WZ instead: 51.11 × 0.6741 × 0.10099", WZ_NNLO * W_HAD * Z_LL / (gen(72742) * K_WZ) - 1)],
         "Approximation as for 72752: an on-shell k-factor applied to a sample that also contains γ* → ℓℓ. Card: 'p p > V ell+ ell-', V = W, 'decay w+ > q q'."))
    a(P_(75573, "ZZ", "Z → quarks plus a lepton pair (e, μ, τ; m(ℓℓ) > 4 GeV), NLO, 0-1 extra parton.",
         [("generator σ (portal)", gen(75573), "portal"), ("k = 16.91 / 14.51 (ZZ NNLO/NLO, includes gg → ZZ)", K_ZZ, "ZZ")],
         "NLO generator × NNLO/NLO k-factor", "Same as our ZZTo4L 75589.",
         "arXiv:1405.2219 Table 1, row 13: 14.51 and 16.91. The portal value on the MiniAOD record.",
         [("on-shell ZZ instead: 16.91 × 2 × 0.10099 × 0.69911", ZZ_NNLO * 2 * Z_LL * Z_HAD / (gen(75573) * K_ZZ) - 1)],
         "The k-factor includes gg → ZZ; no gg → ZZ → 2ℓ2q sample is proposed, so nothing is counted twice."))
    a(P_(72738, "WZ", "W → ℓν (e, μ, τ) with Z → quarks, NLO, 0-1 extra parton.",
         [("generator σ (portal)", gen(72738), "portal"), ("k = 51.11 / 46.068", K_WZ, "WZ")],
         "NLO generator × NNLO/NLO k-factor", "Generator × k-factor, as 72752.", wz_look,
         [("on-shell WZ instead: 51.11 × 0.3272 × 0.69911", WZ_NNLO * W_L * Z_HAD / (gen(72738) * K_WZ) - 1)],
         "Here the boson decaying to quarks is an on-shell Z, so the on-shell construction is also defensible; a choice for Matan."))
    a(P_(72658, "WW", "One W → ℓν (e, μ, τ) and the other W → quarks, NLO, 0-1 extra parton.",
         [("σ(WW), NNLO, includes gg → WW", WW_NNLO, "WW"), ("BR = 2 × 0.3272 × 0.6741", 2 * W_L * W_HAD, "PDG_W")],
         "NNLO", "Same construction as our WWTo2L2Nu 72676 (118.7 pb × BR).",
         "arXiv:1408.5243 Table I, row 13, σNNLO = 118.7. pdglive S043.",
         [("generator value instead", gen(72658) / (WW_NNLO * 2 * W_L * W_HAD) - 1)]))
    a(P_(72740, "WZ", "W → ℓν (e, μ, τ) with Z → νν, NLO, 0-1 extra parton.",
         [("generator σ (portal)", gen(72740), "portal"), ("k = 51.11 / 46.068", K_WZ, "WZ")],
         "NLO generator × NNLO/NLO k-factor", "Generator × k-factor, as 72752 (the sample is the full ℓννν final state).", wz_look,
         [("on-shell WZ instead: 51.11 × 0.3272 × 0.20000", WZ_NNLO * W_L * Z_INV / (gen(72740) * K_WZ) - 1)]))
    # ---------------- tier 3 ----------------
    for rid, nm in ((72701, "WWW"), (72711, "WWZ"), (72761, "WZZ"), (75600, "ZZZ")):
        a(P_(rid, "VVV", f"{nm} production at NLO, all decays.",
             [("generator σ (portal), NLO", gen(rid), "portal")], "NLO",
             "No NNLO exists → generator value at NLO (settled convention, as ttZ/ttW).",
             f"The MiniAOD record {P[rid]['mini_recid']}: metadata.cross_section.total_value.", []))
    # ---------------- tier 4 ----------------
    a(P_(68325, "TZQ", "Single top + Z/γ* → ℓℓ (e, μ, τ; same-flavour m(ℓℓ) > 30 GeV) + a light quark, NLO.",
         [("generator σ (portal), NLO", gen(68325), "portal")], "NLO", "No NNLO → generator NLO.",
         "MiniAOD record 68324, total_value.", []))
    a(P_(64873, "TWLL", "Single top + W + a lepton pair (e, μ, τ), LO (no Higgs diagrams).",
         [("generator σ (portal), LO", gen(64873), "portal")], "LO",
         "CANNOT follow the convention: only an LO generator value exists (no NLO sample, no published total for this phase space). Decision for Matan.",
         "MiniAOD record 64872, total_value.", []))
    a(P_(67645, "TTHX", "tt̄H with H → bb̄ (all top decays).",
         [("σ(ttH), NLO QCD + NLO EW, mH = 125.00", TTH, "YR4_XS"), ("BR(H → bb), mH = 125.00", BR_BB, "YR4_BR")],
         "NLO QCD + NLO EW", "LHC Higgs WG YR4 at 125.00 GeV (settled).",
         "CERNYellowReportPageAt13TeV, ttH table, 125.00 → 5.071E-01. CERNYellowReportPageBR, 'Higgs → 2 fermions', 125.00, H → bb = 5.824E-01.", []))
    a(P_(67691, "TTHX", "tt̄H with every Higgs decay except H → bb̄.",
         [("σ(ttH)", TTH, "YR4_XS"), ("1 − BR(H → bb)", 1 - BR_BB, "YR4_BR")],
         "NLO QCD + NLO EW", "YR4 at 125.00 GeV.",
         "As 67645. Pythia setting in the record: '25:offIfAny = 5 -5'.", []))
    a(P_(68206, "TTV", "tt̄Z with Z → quarks (u, d, s, c, b), NLO.",
         [("generator σ (portal), NLO", gen(68206), "portal")], "NLO", "No NNLO → generator NLO, as our ttZ 68187.",
         "MiniAOD record 68204, total_value.", []))
    a(P_(68083, "TTV", "tt̄W with W → quarks, NLO, 0-1 extra parton.",
         [("generator σ (portal), NLO", gen(68083), "portal")], "NLO", "No NNLO → generator NLO, as our ttW 68073.",
         "MiniAOD record 68082, total_value (matching efficiency 0.6 shown, not applied -- the same open point as 68073).", []))
    a(P_(68045, "TTTT", "Four top quarks, all decays, NLO.",
         [("generator σ (portal), NLO", gen(68045), "portal")], "NLO",
         "Rule 'no NNLO → generator NLO' applied, BUT published higher-accuracy values exist and are much larger: decision for Matan.",
         "MiniAOD record 68044, total_value = 8.091e-03.",
         [("NLO QCD+EW, arXiv:1711.02116 Table 5: 11.97 fb", 0.01197 / gen(68045) - 1),
          ("NLO(QCD+EW)+NLL′, arXiv:2212.03259 Table I: 14.65 fb", 0.01465 / gen(68045) - 1)]))
    a(P_(68185, "TTV", "tt̄ + lepton pair (e, μ, τ) with 1 < m(ℓℓ) < 10 GeV (virtual photon), NLO -- fills the gap below our TTZToLLNuNu_M-10.",
         [("generator σ (portal), NLO", gen(68185), "portal")], "NLO", "No NNLO → generator NLO.",
         "MiniAOD record 68184, total_value.", []))
    # ---------------- tier 5: Higgs ----------------
    hww = BR_WW * W_L ** 2
    a(P_(37474, "H", "Gluon-fusion Higgs, H → WW → ℓνℓν (ℓ = e, μ, τ).",
         [("σ(ggF), N3LO QCD + NLO EW", GGF, "YR4_XS"), ("BR(H → WW)", BR_WW, "YR4_BR"), ("BR(W → ℓν)² = 0.3272²", W_L ** 2, "PDG_W")],
         "N3LO QCD + NLO EW", "YR4 × YR4 BR × PDG W BRs (settled).",
         "YR4 13 TeV ggF table, 125.00 → 4.858E+01; BR page 'Higgs → 2 gauge bosons', 125.00, WW = 2.137E-01.", [],
         "Pythia: '25:onIfMatch = 24 -24', '24:onIfMatch = 11 12 / 13 14 / 15 16'."))
    a(P_(68601, "H", "Vector-boson-fusion Higgs, H → WW → ℓνℓν (ℓ = e, μ, τ).",
         [("σ(VBF), approx. NNLO QCD + NLO EW", VBF, "YR4_XS"), ("BR(H → WW)", BR_WW, "YR4_BR"), ("BR(W → ℓν)²", W_L ** 2, "PDG_W")],
         "approx. NNLO QCD + NLO EW", "YR4 (settled).", "YR4 VBF table, 125.00 → 3.782E+00; BR WW 2.137E-01.", [],
         "JHUGen card: DecayMode1=10 DecayMode2=10 (W → ℓν, ℓ = e, μ, τ)."))
    for rid, nm, xs in ((41877, "W+H", WPH), (41873, "W−H", WMH)):
        a(P_(rid, "H", f"{nm} production, W decaying any way, H → WW (any decay).",
             [(f"σ({nm}), NNLO QCD + NLO EW", xs, "YR4_XS"), ("BR(H → WW)", BR_WW, "YR4_BR")],
             "NNLO QCD + NLO EW", "YR4 (settled).", f"YR4 WH table, 125.00, column '{nm} (pb)' = {xs:.3E}; BR WW.", [],
             "Cards: vdecaymode 10 (W inclusive), JHUGen DecayMode 11/11 (W → anything)."))
    a(P_(41914, "H", "qq̄ → ZH, Z decaying any way, H → WW (any decay).",
         [("σ(ZH, all but gg → ZH)", QQZH, "YR4_XS"), ("BR(H → WW)", BR_WW, "YR4_BR")],
         "NNLO QCD + NLO EW", "YR4 'all but gg→ZH' value, the page's own recommendation for an NLO qq̄ → ZH sample.",
         "YR4 ZH process table: 'qq/qg→ZH, gg→HZ+qqbar (all but gg→ZH)' = 0.7612.",
         [("total pp → ZH 0.8839 instead (would double-count gg → ZH)", 0.8839 / QQZH - 1)],
         "Portal shows no matching efficiency for this record (None)."))
    a(P_(40095, "H", "gg → ZH, Z → ℓℓ (e, μ, τ), H → WW (any decay).",
         [("σ(gg → ZH), NLO+NLL", GGZH, "YR4_XS"), ("BR(H → WW)", BR_WW, "YR4_BR"), ("BR(Z → ℓℓ) = 0.033632 + 0.033662 + 0.033696", Z_LL, "PDG_Z")],
         "NLO+NLL QCD", "YR4 gg → ZH; Z branching ratios from PDG individually measured values (by analogy with the W convention -- NOT settled, see Decisions).",
         "YR4 ZH process table: 'gg→ZH' = 0.1227. pdglive S044: Γ1, Γ2, Γ3.", [],
         "POWHEG card: vdecaymode 11 ('inclusive leptons'); Pythia '25:onIfMatch = 24 -24'."))
    for rid, nm, xs, src in ((37446, "gluon-fusion", GGF, "ggF table 4.858E+01"), (68591, "VBF", VBF, "VBF table 3.782E+00"),
                             (71297, "W+H (W any decay)", WPH, "WH table, W+H 8.400E-01"), (70453, "W−H (W any decay)", WMH, "WH table, W−H 5.328E-01"),
                             (74684, "qq̄ → ZH (Z any decay)", QQZH, "ZH process table, all but gg→ZH 0.7612")):
        a(P_(rid, "H", f"{nm} Higgs, H → ττ.",
             [("σ(production), YR4", xs, "YR4_XS"), ("BR(H → ττ)", BR_TAUTAU, "YR4_BR")],
             "YR4 order of the production mode", "YR4 (settled).", f"YR4 {src}; BR page 'Higgs → 2 fermions', 125.00, ττ = 6.272E-02.", [],
             "Pythia: '25:onIfMatch = 15 -15'."))
    br2l2nu = BR_ZZ * 2 * (Z_EE + Z_MM) * Z_INV
    for rid, nm, xs in ((37616, "Gluon-fusion", GGF), (68741, "VBF", VBF)):
        a(P_(rid, "H", f"{nm} Higgs, H → ZZ → ℓℓνν with ℓ = e or μ only (no τ).",
             [("σ(production), YR4", xs, "YR4_XS"), ("BR(H → ZZ)", BR_ZZ, "YR4_BR"),
              ("2 × BR(Z → ee + μμ) × BR(Z → νν) = 2 × 0.067294 × 0.20000", 2 * (Z_EE + Z_MM) * Z_INV, "PDG_Z")],
             "YR4 order of the production mode", "YR4 × PDG Z BRs (Z convention not settled, see Decisions).",
             "YR4 tables; BR ZZ 2.619E-02. JHUGen card DecayMode1=3 (Z → νν), DecayMode2=0 (Z → ee, μμ; no τ).",
             [("YR4 4-fermion column 'H → l+ l- νl νl, l = e or μ' 1.055E-02 instead (WRONG here: it also contains H → WW → ℓνℓν)", 1.055e-2 / br2l2nu - 1)]))
    for rid, nm, xs in ((71227, "W+H", WPH), (70383, "W−H", WMH)):
        a(P_(rid, "H", f"{nm} production (W any decay), H → ZZ → 4ℓ (ℓ = e, μ, τ).",
             [(f"σ({nm})", xs, "YR4_XS"), ("BR(H → ZZ → 4ℓ, ℓ = e, μ, τ)", BR_4L, "YR4_BR")],
             "NNLO QCD + NLO EW", "Same BR as our ggH/VBF → 4ℓ (2.745e-4).",
             "YR4 WH table; BR page 'Higgs → 4 fermions', H → llll (l = e,μ,τ) = 2.745E-04. JHUGen card DecayMode 8/8.", []))
    return out


def tier_of():
    return {r: (t, n, role) for r, n, _, t, role in SAMPLES}


def render(props) -> str:
    T = tier_of()
    L = ["# Cross-section PROPOSALS for the planned samples (26 Oct 2026)", "",
         "**Nothing here is applied.** No value enters any registry or config. Each section is for Matan's",
         "manual check, one sample at a time, in the order of the plan's tiers. Format as in the 14-15 Oct review.", "",
         "Status of the numbers:",
         "- Every source number was **read on 26 Oct 2026 from the page linked** (VERIFIED BY RUNNING: fetched with curl /",
         "  pdf text extraction; where on the page and the number as printed: table 'Sources used' below).",
         "- Every generator value and efficiency was **read from the CERN Open Data API** on 26 Oct 2026",
         "  (VERIFIED BY RUNNING; raw copies `evidence/records/<MiniAOD recid>.json.gz`).",
         "- The proposed σ_eff is arithmetic on those numbers (VERIFIED BY RUNNING, `xsec_proposals.py`).",
         "- Whether each proposal is *right* is for Matan: these are proposals, not decisions.",
         "- 'matching eff.' is shown exactly as on the portal and is **never multiplied in** (open point since 15 Oct).", ""]
    srcs = sorted({s for p in props for _, _, s in p["factors"] if s != "portal"})
    L += ["## Sources used", "", "| key | link | where | as printed |", "|---|---|---|---|"]
    for k in srcs + [k for k in ("TTTT_NLO", "TTTT_NLL", "ATLAS_W", "ST_NLO_T", "ST_NLO_S", "ST_NNLO_TW", "ST_TW_OLD", "JHUGEN") if k not in srcs]:
        u, where, txt = SOURCES[k]
        L.append(f"| {k} | <{u}> | {where} | {txt} |")
    L.append("")
    for i, p in enumerate(sorted(props, key=lambda p: (T[p["recid"]][0], T[p["recid"]][2] != "recommended")), 1):
        r = P[p["recid"]]
        x = r["portal_cross_section"] or {}
        tier, name, role = T[p["recid"]]
        g = gen(p["recid"])
        L += [f"## {i}. {p['recid']} {name} — tier {tier}{' (ALTERNATIVE, for a decision in PLAN.md)' if role != 'recommended' else ''}", "",
              f"- **What it is:** {p['sentence']}",
              f"- **Dataset:** `{r['dataset']}` (MiniAOD parent {r['mini_recid']}; <{r['link']}>)",
              f"- **Proposed σ_eff = {p['sigma_eff_pb']:.6g} pb** = " + " × ".join(f"{v:.6g}" for _, v, _ in p["factors"]), ""]
        for lab, v, s in p["factors"]:
            src = f"portal API <{r['mini_api']}> metadata.cross_section.total_value" if s == "portal" else f"{SOURCES[s][0]} — {SOURCES[s][1]}"
            L.append(f"  - {lab}: **{v:.6g}** — {src}")
        L += ["",
              f"- **Order:** {p['order']}.",
              f"- **Portal (generator) values:** total_value = {x.get('total_value')} pb, filter eff. = {x.get('filter_efficiency')}, "
              f"matching eff. = {x.get('matching_efficiency')}, negative-weight fraction = {x.get('neg_weight_fraction')} "
              f"(<{r['mini_api']}>).",
              f"- **Proposed / generator:** {p['sigma_eff_pb'] / g:.4f}" if g else "- **Proposed / generator:** no generator value on the portal.",
              f"- **What Matan should open and look for:** {p['look']}",
              f"- **Convention:** {p['convention']}"]
        if p["alternatives"]:
            L.append("- **Alternatives considered:** " + "; ".join(f"{lab} → {d * 100:+.1f} %" for lab, d in p["alternatives"]))
        else:
            L.append("- **Alternatives considered:** none with a public source found.")
        if p["notes"]:
            L.append(f"- **Note:** {p['notes']}")
        L.append("")
    L += ["## Not verified / not proposed", "",
          "- ZZTo2L2Nu 75567: excluded on 15 Oct (unresolved 42 % mismatch between its portal value and expectations); history re-stated in PLAN.md, not resolved here.",
          "- tHq 65649, tHW 65721: not proposed. Their portal values (0.7449 and 0.1466 pb) are about 10× the YR4 SM values (7.425E-02 and 1.517E-02 pb, read on the YR4 page) -- consistent with generation at a non-SM coupling point plus reweighting weights (name 'ctcvcp'); UNVERIFIED, would need per-event reweighting the pipeline does not do.",
          "- ZH → ZZ (74314, 74300, 74384, 74440): not proposed. Their portal records show 'matching efficiency' 0.2-0.9 on POWHEG samples, which looks like a lepton-filter efficiency in the wrong field; UNVERIFIED.",
          "- Optional samples (PLAN.md): no proposal yet.",
          "- QCD multijet and photon samples: out of scope (no cross-section research).", ""]
    return "\n".join(L)


def main():
    props = proposals()
    out = [{k: v for k, v in p.items()} for p in props]
    (HERE / "evidence" / "xsec_proposals.json").write_text(json.dumps(
        {"what": "PROPOSALS only, not applied", "constants": {"K_W": K_W, "K_WZ": K_WZ, "K_ZZ": K_ZZ, "W_L": W_L, "Z_LL": Z_LL},
         "sources": SOURCES, "proposals": out}, indent=1, ensure_ascii=False) + "\n")
    (HERE / "XSEC_PROPOSALS.md").write_text(render(props))
    for p in props:
        print(p["recid"], f"{p['sigma_eff_pb']:.6g}")


if __name__ == "__main__":
    main()
