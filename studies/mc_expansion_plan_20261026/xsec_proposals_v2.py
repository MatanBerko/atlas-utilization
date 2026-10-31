"""Cross-section PROPOSALS v2 (31 Oct 2026), after Matan's decisions (DECISIONS.md).

NOT a registry. Nothing here is applied anywhere. For Matan's sample-by-sample review.
- Cards whose decision did not change them are copied from evidence/xsec_proposals.json (v1,
  26 Oct) unchanged and say so.
- New / changed cards use the numbers below, each re-read on 31 Oct 2026 from the page named in
  SOURCES_V2 (VERIFIED BY RUNNING: curl + text extraction; arXiv numbers from the TeX source).
- Generator values come from the MiniAOD records (evidence/records/, atlas_mapping/cms_records/).
- ATLAS values are cross-checks only (atlas_mapping/atlas_bkg_metadata.json, release 2024r-pp).
- Where no decision settles the convention, the card lists OPTIONS and says DECISION NEEDED.

    python3 studies/mc_expansion_plan_20261026/xsec_proposals_v2.py

writes evidence/xsec_proposals_v2.json and XSEC_PROPOSALS_v2.md.
"""
from __future__ import annotations

import gzip
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from plan_samples_v2 import SAMPLES_V2  # noqa: E402
from xsec_proposals import SOURCES  # noqa: E402  (v1 sources, read 26 Oct)

REC_DIRS = (HERE / "evidence" / "records", HERE / "atlas_mapping" / "cms_records")
ATLAS = json.loads((HERE / "atlas_mapping" / "atlas_bkg_metadata.json").read_text())["datasets"]
V1 = {p["recid"]: p for p in json.loads((HERE / "evidence" / "xsec_proposals.json").read_text())["proposals"]}

# ---- new sources (31 Oct): key -> (url, where, as printed) ----
SOURCES_V2 = dict(SOURCES)
SOURCES_V2.update({
    "ST_NLO_T": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec",
                 "section 'Single-top t channel cross sections (superseded)', 13 TeV table, rows 'top' / 'anti-top', column 'Central value' (Hathor NLO; page rev. r36, 2022-12-06; re-read 31 Oct 2026)",
                 "136.02 / 80.95"),
    "ST_NLO_S": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec",
                 "section 'Single-top s channel cross sections', 13 TeV table, rows 'top' / 'anti-top' / 'top + anti-top', column 'Central value' (re-read 31 Oct 2026)",
                 "6.35 / 3.97 / 10.32"),
    "ST_TW_OLD": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec",
                  "section 'Single-top Wt channel cross sections', 13 TeV, row 'top + antitop' (re-read 31 Oct 2026)",
                  "71.7"),
    "PDG_W": ("https://pdglive.lbl.gov/Particle.action?node=S043",
              "W DECAY MODES Γ2 e+ν, Γ3 μ+ν, Γ4 τ+ν, Γ5 hadrons (re-read 31 Oct 2026)",
              "(10.71 ± 0.16) %, (10.63 ± 0.15) %, (11.38 ± 0.21) %, (67.41 ± 0.27) %"),
    "PDG_Z": ("https://pdglive.lbl.gov/Particle.action?node=S044",
              "Z DECAY MODES Γ1 e+e−, Γ2 μ+μ−, Γ3 τ+τ−, Γ7 invisible, Γ8 hadrons (re-read 31 Oct 2026, D6)",
              "(3.3632 ± 0.0042) %, (3.3662 ± 0.0066) %, (3.3696 ± 0.0083) %, (20.000 ± 0.055) %, (69.911 ± 0.056) %"),
    "YR4_XS": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV",
               "rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026",
               "ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)"),
    "YR4_BR2": ("https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR",
                "rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026",
                "μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02"),
    "TTTT_NLO": ("https://arxiv.org/abs/1711.02116",
                 "Table 5 (TeX label table:4t), row µ = HT/4, column 'LO + NLO' (complete NLO QCD+EW); re-read from the arXiv TeX source 31 Oct 2026",
                 "11.97 (+18 % −21 %) fb"),
    "RAZOR_ZNN": ("https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat",
                  "lines 96-103, 'ZJetsToNuNu_HT-<bin>_13TeV-madgraph <LO>*1.23' (SECONDARY source; older CUETP8M1 samples; the origin of 1.23 is not stated in the file); re-read 31 Oct 2026",
                  "e.g. line 96: ZJetsToNuNu_HT-100To200_13TeV-madgraph 280.35*1.23"),
    "RAZOR_DY": ("https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat",
                 "line 90 (the value our delivered DY M-50 uses); re-read 31 Oct 2026",
                 "DYJetsToLL_M-50_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 1921.8*3"),
    "SMP16018": ("https://arxiv.org/abs/1712.09814",
                 "CMS SMP-16-018 (EW Z + 2 jets, 13 TeV 2016), §2 and abstract: region m(ℓℓ) > 50, pT(j) > 25, m(jj) > 120 GeV, ℓ = e or μ; LO MadGraph prediction and measurement; text: 'agreement within 5 % with the NLO predictions of vbfnlo'; read from the arXiv TeX source 31 Oct 2026",
                 "σ_LO = 543 +7 −9 (scale) ± 22 (PDF) fb; measured 534 ± 20 (stat) ± 57 (syst) fb"),
    "SMP17011": ("https://arxiv.org/abs/1903.04040",
                 "CMS SMP-17-011 (EW W + 2 jets, 13 TeV 2016), §2 and §8: region pT(j) > 25, m(jj) > 120 GeV; LO 'for the ℓνjj final state (with ℓ = e, μ or τ)'; measurement 'per channel'; text: 'in agreement within 2-5 % with the NLO predictions of vbfnlo'; read from the arXiv TeX source 31 Oct 2026",
                 "σ_LO = 6.81 +0.03 −0.06 (scale) ± 0.26 (PDF) pb; measured 6.23 ± 0.12 (stat) ± 0.61 (syst) pb"),
    "POWHEG_ZZ": ("https://arxiv.org/abs/1311.1365",
                  "Nason & Zanderighi, 'W+W−, WZ and ZZ production in the POWHEG-BOX-V2', §1 (TeX source, read 31 Oct 2026)",
                  "'Singly resonant contributions and interference effects were included, and in fact all diagrams relevant to the production of four leptons were accounted for, with the exception of interference effects between W+W− and ZZ'"),
    "SHERPA_MAN": ("https://sherpa.hepforge.org/doc/SHERPA-MC-2.2.11.html",
                   "Sherpa 2.2.11 manual §5.6.14 (read 31 Oct 2026)",
                   "'Min_N_TChannels: Limits the minimum number of t-channel propagators in the process to the given value.'"),
    "JHUGEN_SRC": ("https://raw.githubusercontent.com/JHUGen/JHUGen/master/JHUGenerator/main.F90",
                   "comment block lines 357-368 and help text line 7269 (JHUGen master, read 31 Oct 2026; the sample used v7.2.3, assumed equivalent: UNVERIFIED for that version)",
                   "DecayMode=8: Z --> l+ l- (l=e,mu,tau); 9: Z --> anything; 'WriteFailedEvents: Write events that fail in the LHE file, but with a weight of 0'"),
})

# ---- numbers as printed by the sources ----
W_E, W_MU, W_TAU = 0.1071, 0.1063, 0.1138
W_L = W_E + W_MU + W_TAU                                  # 0.3272
Z_LL = 0.033632 + 0.033662 + 0.033696                     # 0.10099
Z_INV = 0.20000
ST_T_NLO, ST_TBAR_NLO, ST_S_NLO = 136.02, 80.95, 10.32
ST_T_NNLO, ST_TBAR_NNLO, ST_S_NNLO = 134.2, 80.0, 11.073
GGF, VBF, WPH, WMH, QQZH, GGZH = 48.58, 3.782, 0.8400, 0.5328, 0.7612, 0.1227
BR_MUMU, BR_ZGAM, BR_ZZ, BR_4L = 2.176e-4, 1.533e-3, 0.02619, 2.745e-4
ZZ_NLO, ZZ_NNLO = 14.51, 16.91
K_ZZ = ZZ_NNLO / ZZ_NLO
TTTT_NLO_FB, TTTT_NLL_FB = 11.97, 14.65
DY_NNLO = 3 * 1921.8                                       # our delivered DY M-50, RazorAnalyzer line 90
EWZ_LO_FB, EWZ_MEAS_FB = 543.0, 534.0
EWW_LO_PB, EWW_MEAS_PB = 6.81, 6.23
K_ZNN_RAZOR = 1.23
ATLAS_TOP_BR = 0.3246                                      # implied by ATLAS t/s-channel (DECISIONS.md D5)


def load(recid):
    for d in REC_DIRS:
        p = d / f"{recid}.json.gz"
        if p.exists():
            with gzip.open(p, "rt") as f:
                return json.load(f)["metadata"]
    raise FileNotFoundError(recid)


def rec(recid):
    m = load(recid)
    mini = int([r["recid"] for r in m["relations"] if r["type"] == "isParentOf"][0])
    x = load(mini).get("cross_section") or {}
    return dict(dataset=m["title"], mini=mini, xs=x, link=f"https://opendata.cern.ch/record/{recid}",
                api=f"https://opendata.cern.ch/api/records/{mini}",
                gen=float(x["total_value"]) if x.get("total_value") else None)


def atlas(*dsids):
    """sum of sigma x kFactor x genFiltEff over the given ATLAS DSIDs (cross-check only)."""
    s = 0.0
    for d in dsids:
        m = ATLAS[str(d)]["metadata"]
        s += m["cross_section_pb"] * m["kFactor"] * m["genFiltEff"]
    return s


K_DY = DY_NNLO / rec(35671)["gen"]                         # 5765.4 / 5396 (LO inclusive DY M-50, CP5)


def card(recid, status, decision, sentence, factors, order, kfac, look, convention,
         alternatives=(), atlas_line="", notes="", options=None, first=None):
    value = math.prod(v for _, v, _ in factors) if factors else None
    return dict(recid=recid, status=status, decision=decision, sentence=sentence, factors=factors,
                sigma_eff_pb=value, order=order, kfactor=kfac, look=look, convention=convention,
                alternatives=list(alternatives), atlas=atlas_line, notes=notes, options=options, first=first)


def from_v1(recid, decision, atlas_line="", status="unchanged from v1", extra_note=""):
    p = V1[recid]
    c = card(recid, status, decision, p["sentence"], [tuple(f) for f in p["factors"]], p["order"],
             "", p["look"], p["convention"], [tuple(a) for a in p["alternatives"]], atlas_line,
             (p["notes"] + (" " + extra_note if extra_note else "")).strip())
    c["sigma_eff_pb"] = p["sigma_eff_pb"]
    return c


def ratio(a, b):
    return f"{a / b:.3f}"


def cards():
    out = []
    a = out.append
    # ======================= tier 1 =======================
    w_atlas = atlas(*range(700338, 700350))
    for rid in (69715, 69717, 69719):
        a(from_v1(rid, "D1, D2", f"No ATLAS sample per jet piece. Whole W → ℓν: ATLAS 700338-700349 = {w_atlas:.0f} pb vs CMS 61,526.7 pb → ATLAS/CMS = {ratio(w_atlas, 61526.7)} (MAPPING.md table A). D2's primary cross-check, ATLAS arXiv:1603.09222 Table 3 (3 × 20.08 nb = 60,240 pb), is −2.1 %."))
    for rid, nm, xs, xs_nnlo, d_atlas in ((64759, "top", ST_T_NLO, ST_T_NNLO, 410658), (64659, "antitop", ST_TBAR_NLO, ST_TBAR_NNLO, 410659)):
        at = atlas(d_atlas)
        a(card(rid, "CHANGED (D4: 4-flavour sample; D5: old Top WG NLO value)", "D4, D5",
               f"Single {nm} production in the t-channel, 4-flavour scheme (POWHEG + MadSpin), all top decays.",
               [(f"σ(t-channel {nm}), Hathor NLO", xs, "ST_NLO_T")],
               "NLO QCD (Hathor), 13 TeV, mt = 172.5 GeV", "none (the sample is normalised to the total directly)",
               f"SingleTopRefXsec, section 'Single-top t channel cross sections (superseded)', 13 TeV table, row '{'top' if nm == 'top' else 'anti-top'}', Central value = {xs}. (The section is marked 'superseded' on the page; D5 uses it on purpose, to match ATLAS.)",
               "D5: match ATLAS = the OLD Top WG page throughout.",
               [(f"SingleTopNNLORef NNLO {xs_nnlo} pb (recorded alternative, D5)", xs_nnlo / xs - 1),
                ("generator value (portal)", rec(rid)["gen"] / xs - 1)],
               f"ATLAS {d_atlas} (leptonic top decays only, four-flavour): σ×k = {at:.3f} pb. Like-for-like with our PDG W BR: {at:.3f} / ({xs} × {W_L:.4f}) = {ratio(at, xs * W_L)}; with ATLAS's own implied BR 0.3246: {ratio(at, xs * ATLAS_TOP_BR)}.",
               "Card (evidence/cards/" + str(rid) + "): MadSpin decays the top inclusively. Probe 31 Oct: all 42 branches present."))
    at_s = atlas(410644, 410645)
    a(card(64635, "CHANGED (D5: old Top WG NLO value)", "D5",
           "Single top (or antitop) in the s-channel, top → b W, W → ℓν (ℓ = e, μ, τ).",
           [("σ(s-channel, top + antitop), Hathor NLO", ST_S_NLO, "ST_NLO_S"),
            ("BR(W → ℓν) = 0.1071 + 0.1063 + 0.1138 (BR(t → Wb) = 1 assumed)", W_L, "PDG_W")],
           "NLO QCD (Hathor)", "none",
           "SingleTopRefXsec, 's channel' 13 TeV table, row 'top + anti-top' = 10.32. pdglive S043: Γ2, Γ3, Γ4.",
           "D5 (old page) × settled PDG individual W branching ratios.",
           [(f"SingleTopNNLORef NNLO 11.073 × {W_L:.4f} (recorded alternative, D5)", ST_S_NNLO / ST_S_NLO - 1),
            (f"ATLAS's implied leptonic BR 0.3246 instead of 0.3272", ATLAS_TOP_BR / W_L - 1),
            ("generator value 3.549 pb (portal)", rec(64635)["gen"] / (ST_S_NLO * W_L) - 1)],
           f"ATLAS 410644 + 410645 (leptonic): {at_s:.4f} pb → ATLAS/CMS = {ratio(at_s, ST_S_NLO * W_L)} (= 0.3246 / 0.3272).",
           "BR arithmetic: 0.1071 + 0.1063 + 0.1138 = 0.3272; 10.32 × 0.3272 = 3.3767 pb. Card (evidence/cards/64635): 'decay t > w+ b, w+ > ell+ vl' with ell = e, μ, τ."))
    a(from_v1(67841, "plan (no decision changed it)", f"ATLAS 410471 (all-hadronic): {atlas(410471):.1f} pb → ATLAS/CMS = {ratio(atlas(410471), 378.933)}."))
    # ======================= tier 2 =======================
    e1 = "E1 applies: ATLAS uses Sherpa generator values with kFactor = 1 and has no gg → VV samples; the CMS NNLO total includes the loop-induced gg part."
    a(from_v1(72742, "D9", f"ATLAS 700492 = {atlas(700492):.3f} pb → ATLAS/CMS = {ratio(atlas(700492), 7.13263)}: different phase space (CMS includes γ* → ℓℓ down to m(ℓℓ) = 4 GeV). " + e1))
    a(from_v1(75573, "D9", f"ATLAS 700493 + 700494 = {atlas(700493, 700494):.3f} pb → ATLAS/CMS = {ratio(atlas(700493, 700494), 4.31083)}: different phase space (γ* down to 4 GeV on the CMS side). " + e1))
    a(from_v1(72738, "D9", f"ATLAS 700489 + 700490 = {atlas(700489, 700490):.3f} pb → ATLAS/CMS = {ratio(atlas(700489, 700490), 10.1614)}. " + e1))
    a(from_v1(72658, "D9", f"ATLAS 700488 = {atlas(700488):.3f} pb → ATLAS/CMS = {ratio(atlas(700488), 52.3623)}. " + e1))
    a(from_v1(72740, "D9", f"ATLAS 700604 = {atlas(700604):.4f} pb → ATLAS/CMS = {ratio(atlas(700604), 3.78876)}. " + e1))
    r75 = rec(75567)
    onshell = ZZ_NNLO * 2 * Z_LL * Z_INV
    onshell_nlo = ZZ_NLO * 2 * Z_LL * Z_INV
    r89 = rec(75589)
    at_llvv = atlas(700602)
    first = [
        "**Generator-card check first (D14 condition).** Cards: `evidence/cards/75567/powheg.input` and, for comparison, the delivered ZZTo4L `evidence/cards/75589/powheg.input` (both fetched 31 Oct from <https://opendata.cern.ch/eos/opendata/cms/lhe_generators/2016-sim/gridpacks/75567/powheg.input> and `.../75589/powheg.input`).",
        "  - 75567 line 2: `mllmin 4d0         ! default 0.1 GeV this is minimum invar mass for Z leptons`; line 31: `leptons-nu 1`. No Z-mass window, no `zerowidth`, no other m(ℓℓ) setting in the file.",
        "  - 75589 (delivered ZZTo4L): **the same file** except the PDF set (306000 vs 325300) and the decay flag (`leptonic 1` vs `leptons-nu 1`); the same `mllmin 4d0` line.",
        "  - The POWHEG-BOX-V2 ZZ code includes 'all diagrams relevant to the production of four leptons … with the exception of interference effects between W+W− and ZZ' (arXiv:1311.1365 §1; singly-resonant and interference terms included). So the charged pair is **Z/γ* down to m(ℓℓ) = 4 GeV**, not an on-shell Z; the νν pair has no photon.",
        f"  - **Verdict: the card supports the low-m(ℓℓ) / γ* explanation qualitatively** — the sample is not on-shell ZZ, and the generator setting that inflates it is exactly the one already accepted for our ZZTo4L (whose portal value {r89['gen']} pb is {r89['gen'] / (ZZ_NLO * Z_LL ** 2):.1f} × its on-shell NLO expectation 14.51 × 0.10099² = {ZZ_NLO * Z_LL ** 2:.4f} pb, because there both pairs can be γ*). **It does not prove the size**: the card cannot say how much of the +42.6 % (vs on-shell NNLO; +{(r75['gen'] / onshell_nlo - 1) * 100:.0f} % vs on-shell NLO {onshell_nlo:.4f} pb) sits at low m(ℓℓ).",
        "  - Not verified from the card: that `leptons-nu` means ℓ = e, μ, τ and all three ν flavours (the POWHEG-BOX ZZ manual/`alloweddec` was not opened; UNVERIFIED). If τ were excluded, the on-shell expectation would be 2/3 as large and the ratio larger.",
        "  - A quantitative check is possible (not done: outside this task): one PBS job reading `LHEPart_*` of file 0 to measure the fraction of the generator σ with 60 < m(ℓℓ) < 120 GeV. If generator σ × that fraction ≈ the on-shell NLO 0.5861 pb, the 42 % is explained.",
    ]
    a(card(75567, "NEW (D14)", "D14 (conditional), D9",
           "ZZ → ℓℓνν: one Z/γ* → ℓℓ (m(ℓℓ) > 4 GeV) and one Z → νν, POWHEG NLO (qq̄ only).",
           [("generator σ (portal, MiniAOD 75566)", r75["gen"], "portal"),
            ("k = 16.91 / 14.51 (ZZ NNLO/NLO, includes gg → ZZ)", K_ZZ, "ZZ")],
           "NLO generator × NNLO/NLO k-factor", f"k = {K_ZZ:.5f} (arXiv:1405.2219 Table 1, row 13)",
           "First the card check above. Then arXiv:1405.2219 Table 1, row 13: 14.51 and 16.91 pb; the portal value 9.738e-01 on MiniAOD record 75566; pdglive S044 Γ1-Γ3, Γ7 for the fallback.",
           "D9 convention (generator × NNLO/NLO k), as our ZZTo4L 75589 and ZZTo2Q2L 75573. CONDITIONAL (D14): proposed only if Matan accepts the card check as verifying the low-m(ℓℓ) explanation; otherwise the fallback below.",
           [(f"FALLBACK (D14): on-shell 16.91 × 2 × {Z_LL:.5f} × {Z_INV:.4f} = {onshell:.4f} pb", onshell / (r75['gen'] * K_ZZ) - 1),
            ("generator value alone (0.9738 pb)", 1 / K_ZZ - 1)],
           f"ATLAS has no ZZ → ℓℓνν on its own: 700602 'VV → ℓℓνν, opposite sign' ({at_llvv:.3f} pb, m(ℓℓ) > 4 GeV) holds WW and ZZ together. CMS WW → 2ℓ2ν 12.71 pb (delivered) + this card {r75['gen'] * K_ZZ:.3f} pb = {12.708 + r75['gen'] * K_ZZ:.2f} pb → ATLAS/CMS = {ratio(at_llvv, 12.708 + r75['gen'] * K_ZZ)}; with the fallback: {ratio(at_llvv, 12.708 + onshell)}. E1 applies (no gg on the ATLAS side). Not decisive.",
           "Probe 31 Oct (file 0, 750,000 events): all 42 branches present, negative-weight fraction 0.0011 (portal 0.0011), Σw = Runs Σw to 5e-9. No overlap with WWTo2L2Nu: the POWHEG ZZ code has no W+W− diagrams (arXiv:1311.1365 §1).",
           first=first))
    # ======================= tier 3 =======================
    for rid, dsids in ((72701, (364242, 364336, 364337, 364338, 364339)), (72711, (364243, 364244)), (72761, (364245, 364246)), (75600, (364247, 364248, 364249))):
        a(from_v1(rid, "D10", "ATLAS has leptonic channels only (MAPPING.md table A, ratios 0.02-0.17): no like-for-like ATLAS value."))
    ewk = {35999: ("Z/γ* → ℓℓ (e, μ, τ) + 2 jets, purely electroweak (QED = 4, QCD = 0)", (700358, 700359, 700360), EWZ_MEAS_FB / EWZ_LO_FB, "SMP16018",
                   "534 / 543 (measured / LO, m(ℓℓ) > 50, pT(j) > 25, m(jj) > 120 GeV, ℓ = e, μ)",
                   "`generate p p > l+ l- j j / t t~ h QED=4 QCD=0` (ℓ = e, μ, τ); run card: mmll = 50 (m(ℓℓ) > 50 GeV), ptj = 10, etaj = 6.5, mmjj = 10 (m(jj) > 10 GeV), deltaeta = 0 (no Δη cut), drjj = 0, ptl = 0, etal = −1 (none)"),
           35987: ("W⁻ → ℓ⁻ν̄ (e, μ, τ) + 2 jets, purely electroweak (QCD = 0)", (700362, 700363, 700364), EWW_MEAS_PB / EWW_LO_PB, "SMP17011",
                   "6.23 / 6.81 (measured / LO, pT(j) > 25, m(jj) > 120 GeV)",
                   "`generate p p > l- vl~ j j / t t~ h QCD=0` (ℓ = e, μ, τ); run card: mmnl = 50 (m(ℓν) > 50 GeV), ptj = 10, etaj = 6.5, mmjj = 10, deltaeta = 0, ptl = 0"),
           35993: ("W⁺ → ℓ⁺ν (e, μ, τ) + 2 jets, purely electroweak (QCD = 0)", (700362, 700363, 700364), EWW_MEAS_PB / EWW_LO_PB, "SMP17011",
                   "6.23 / 6.81 (measured / LO, pT(j) > 25, m(jj) > 120 GeV)",
                   "`generate p p > l+ vl j j / t t~ h QCD=0` (ℓ = e, μ, τ); run card: mmnl = 50, ptj = 10, etaj = 6.5, mmjj = 10, deltaeta = 0, ptl = 0")}
    cms_w_sum = rec(35987)["gen"] + rec(35993)["gen"]
    for rid, (sent, dsids, kmeas, src, ktxt, cardtxt) in ewk.items():
        r = rec(rid)
        at = atlas(*dsids)
        cms_tot = r["gen"] if rid == 35999 else cms_w_sum
        opts = [("(a) generator LO value (portal)", r["gen"], "portal record " + r["api"]),
                (f"(b) generator × {ktxt} = × {kmeas:.4f}", r["gen"] * kmeas, src)]
        a(card(rid, "NEW (D12) — DECISION NEEDED on the value", "D12",
               sent + ".",
               [("generator σ (portal), LO", r["gen"], "portal")],
               "LO (MadGraph, no extra partons)", "none in option (a); option (b) applies a measured/LO ratio",
               f"Card `evidence/cards/{rid}/*proc_card.dat` and `*run_card.dat`; the portal value on MiniAOD {r['mini']}; {SOURCES_V2[src][0]} for option (b).",
               "No settled convention: no NNLO exists, and the published NLO (VBFNLO) and the measurement are in a narrower phase space (m(jj) > 120, pT(j) > 25 GeV) than the sample (m(jj) > 10, pT(j) > 10 GeV). The table shows (a) as the placeholder only.",
               [((f"option (b) " + ktxt), kmeas - 1)],
               f"ATLAS {dsids[0]}-{dsids[-1]} (Sherpa LO, 'Min_N_TChannels', per flavour ≈ {at / 3:.3f} pb): {at:.3f} pb for 3 flavours ({'Z' if rid == 35999 else 'W⁺ + W⁻ together'}) vs CMS {cms_tot:.2f} pb → ATLAS/CMS = {ratio(at, cms_tot)} (per flavour CMS {cms_tot / 3:.2f} pb). NOT like-for-like, see the note.",
               f"Generator-level cuts (card): {cardtxt}. **Why CMS ≈ 2.7-2.8 × ATLAS:** (1) `QED=4 QCD=0` keeps every purely electroweak diagram, including s-channel diboson/triboson-like ones (WZ/ZZ/WW with V → qq); ATLAS's names say 'Min_N_TChannels', which in Sherpa 'limits the minimum number of t-channel propagators' (Sherpa 2.2.11 manual §5.6.14), i.e. removes pure s-channel diagrams; (2) the CMS cuts are very loose (m(jj) > 10, pT(j) > 10 GeV); ATLAS's generator cuts are not in the public metadata (UNKNOWN; job options not opened, rule: metadata only). **Overlap flag (physics choice, not decided):** the s-channel diboson part of this sample (V → qq with m(jj) ≈ mW/mZ) is the same process as tier-2 {'WZTo2Q2L 72742 / ZZTo2Q2L 75573' if rid == 35999 else 'WZTo1L1Nu2Q 72738 / WWTo1L1Nu2Q 72658'}; using both counts it twice in that region. Options: keep both and accept it (CMS SMP-16-018 calls the diboson contribution 'small' in its m(jj) > 120 region; our histograms have no m(jj) cut); remove events with LHE m(jj) near mW/mZ from this sample (new builder code); its size can be measured from LHEPart (not done). Probe 31 Oct: all 42 branches present, no negative weights.",
               options=opts))
    # ======================= tier 4 =======================
    a(from_v1(67645, "plan", f"ATLAS tt̄H 346343-346345 (all decays) = {atlas(346343, 346344, 346345):.4f} pb vs CMS bb + non-bb = 0.5071 → 1.00 (MAPPING.md)."))
    a(from_v1(67691, "plan", "As 67645 (ATLAS/CMS 1.00 for tt̄H as a whole)."))
    a(from_v1(68083, "plan", f"ATLAS tt̄W inclusive 410155 = {atlas(410155):.4f} pb vs CMS ℓν (delivered 0.2151) + qq (this card 0.4375) = 0.6526 → {ratio(atlas(410155), 0.6526)}."))
    r68 = rec(68045)
    a(card(68045, "CHANGED (D7)", "D7",
           "Four top quarks, all decays, NLO (aMC@NLO).",
           [("σ(tt̄tt̄), complete NLO QCD+EW, µ = HT/4 [11.97 fb]", TTTT_NLO_FB / 1000, "TTTT_NLO")],
           "complete NLO QCD + EW", "none (the sample is normalised to the published total)",
           "arXiv:1711.02116 Table 5, row µ = HT/4, column 'LO + NLO' = 11.97 fb.",
           "D7: the published complete-NLO value, matching ATLAS.",
           [("generator NLO value 8.091 fb (portal, MiniAOD 68044)", r68["gen"] / (TTTT_NLO_FB / 1000) - 1),
            ("NLO(QCD+EW)+NLL′ 14.65 fb (arXiv:2212.03259 Table I)", TTTT_NLL_FB / TTTT_NLO_FB - 1)],
           f"ATLAS 412043: 10.673 fb × k 1.1267 = {atlas(412043) * 1000:.3f} fb → ATLAS/CMS = {ratio(atlas(412043), TTTT_NLO_FB / 1000)}.",
           "Proposed / generator = 1.479."))
    for rid in (68325, 64873, 68206, 68185):
        a(from_v1(rid, "ON HOLD (D8 / no ATLAS nominal counterpart; waiting for Maryna)", "", status="ON HOLD — card kept unchanged from v1, not for review now"))
    # ======================= tier 5 =======================
    h_atlas = {37474: "ATLAS 345324 (H → WW → ℓνℓν): ATLAS/CMS 1.02 (MAPPING.md).",
               68601: "ATLAS 345948: ATLAS/CMS 1.02 (MAPPING.md).",
               41877: "ATLAS W±H → WW has W → qq and H → ℓνℓν only (0.07, different channels): no like-for-like value.",
               41873: "As 41877.",
               41914: "ATLAS qq̄ → ZH → WW is Z → νν only (0.05, different channels): no like-for-like value.",
               40095: "ATLAS 346524 is Z-inclusive (ATLAS/CMS 1.08 is not like-for-like).",
               37446: "ATLAS ggF → ττ pieces carry ττ-decay and pT filters (0.32): no like-for-like value.",
               68591: "ATLAS VBF → ττ pieces sum to more than σ × BR (1.29; looks like an ATLAS-side issue, MAPPING.md).",
               71297: "ATLAS 345211/345212 (W±H → ττ): 1.00 (same YR4 inputs).", 70453: "As 71297.",
               74684: "ATLAS 345217: 1.00.", 37616: "No ATLAS counterpart (reverse check, MAPPING.md D).",
               68741: "No ATLAS counterpart.", 71227: "ATLAS 346449/346450: 1.00.", 70383: "As 71227."}
    for rid in (37474, 68601, 41877, 41873, 41914, 40095, 37446, 68591, 71297, 70453, 74684, 37616, 68741, 71227, 70383):
        note = ""
        if rid in (37616, 68741, 40095):
            note = "The Z branching ratios here are now the settled D6 values (pdglive S044, re-checked 31 Oct, unchanged), so the number is unchanged."
        a(from_v1(rid, "D13 (planned 15)", h_atlas[rid], extra_note=note))
    newh = [
        (37432, "Gluon-fusion Higgs, H → μμ.", [("σ(ggF), N3LO", GGF, "YR4_XS"), ("BR(H → μμ)", BR_MUMU, "YR4_BR2")], "N3LO QCD + NLO EW", (345097,),
         "Pythia: '25:onIfMatch = 13 -13'.", "YR4 ggF table, 125.00 → 4.858E+01; BR page, table 'H → bb, ττ, μμ, cc', 125.00, H → μμ = 2.176E-04."),
        (68571, "VBF Higgs, H → μμ.", [("σ(VBF)", VBF, "YR4_XS"), ("BR(H → μμ)", BR_MUMU, "YR4_BR2")], "approx. NNLO QCD + NLO EW", (345106,),
         "Pythia: '25:onIfMatch = 13 -13'.", "YR4 VBF table, 125.00 → 3.782E+00; BR H → μμ = 2.176E-04."),
        (71295, "W⁺H (W any decay, POWHEG MiNLO HWJ), H → μμ.", [("σ(W⁺H)", WPH, "YR4_XS"), ("BR(H → μμ)", BR_MUMU, "YR4_BR2")], "NNLO QCD + NLO EW", (345104,),
         "POWHEG card: idvecbos 24, vdecaymode 10 (inclusive); Pythia '25:onIfMatch = 13 -13'.", "YR4 WH table, 125.00, column W⁺H = 8.400E-01; BR H → μμ."),
        (70451, "W⁻H (W any decay), H → μμ.", [("σ(W⁻H)", WMH, "YR4_XS"), ("BR(H → μμ)", BR_MUMU, "YR4_BR2")], "NNLO QCD + NLO EW", (345105,),
         "POWHEG card: idvecbos −24, vdecaymode 10; Pythia '25:onIfMatch = 13 -13'.", "YR4 WH table, column W⁻H = 5.328E-01; BR H → μμ."),
        (74682, "qq̄ → ZH (Z any decay, POWHEG MiNLO HZJ), H → μμ.", [("σ(ZH, all but gg → ZH)", QQZH, "YR4_XS"), ("BR(H → μμ)", BR_MUMU, "YR4_BR2")], "NNLO QCD + NLO EW", (345103,),
         "POWHEG card: vdecaymode 10 (Z inclusive), minlo 1; Pythia '25:onIfMatch = 13 -13'. Normalised to 'all but gg → ZH' as 74684 (no gg → ZH → μμ sample exists).", "YR4 ZH process table: 'all but gg→ZH' = 0.7612; BR H → μμ."),
        (37604, "Gluon-fusion Higgs, H → Zγ with Z → ℓℓ (e, μ, τ).", [("σ(ggF)", GGF, "YR4_XS"), ("BR(H → Zγ)", BR_ZGAM, "YR4_BR2"), ("BR(Z → ℓℓ) = 0.033632 + 0.033662 + 0.033696 (D6)", Z_LL, "PDG_Z")], "N3LO QCD + NLO EW", (345316,),
         "Pythia: '25:onIfMatch = 23 22', '23:onIfAny = 11 13 15', '23:mMin = 50.0' (the Z is cut at m > 50 GeV; the small loss below 50 GeV is not corrected for).", "YR4 ggF 4.858E+01; BR page table 'H → gg, γγ, Zγ', 125.00, H → Zγ = 1.533E-03; pdglive S044 Γ1-Γ3."),
        (68731, "VBF Higgs, H → Zγ with Z → ℓℓ (e, μ, τ).", [("σ(VBF)", VBF, "YR4_XS"), ("BR(H → Zγ)", BR_ZGAM, "YR4_BR2"), ("BR(Z → ℓℓ) (D6)", Z_LL, "PDG_Z")], "approx. NNLO QCD + NLO EW", (345833,),
         "Pythia: '25:onIfMatch = 23 22', '23:onIfAny = 11 13 15', '23:mMin = 50.0'.", "YR4 VBF 3.782E+00; BR H → Zγ 1.533E-03; pdglive S044."),
        (71145, "W⁺H (W any decay), H → Zγ (Z any decay).", [("σ(W⁺H)", WPH, "YR4_XS"), ("BR(H → Zγ)", BR_ZGAM, "YR4_BR2")], "NNLO QCD + NLO EW", (345321,),
         "POWHEG card: vdecaymode 10; Pythia only '25:onIfMatch = 23 22' (no Z-decay restriction, so the Z from H decays inclusively, consistent with the name 'WToAll'). No Z BR applied.", "YR4 WH W⁺H 8.400E-01; BR H → Zγ 1.533E-03."),
        (70301, "W⁻H (W any decay), H → Zγ (Z any decay).", [("σ(W⁻H)", WMH, "YR4_XS"), ("BR(H → Zγ)", BR_ZGAM, "YR4_BR2")], "NNLO QCD + NLO EW", (345320,),
         "As 71145 (idvecbos −24).", "YR4 WH W⁻H 5.328E-01; BR H → Zγ."),
        (74292, "qq̄ → ZH (Z any decay), H → Zγ (Z any decay).", [("σ(ZH, all but gg → ZH)", QQZH, "YR4_XS"), ("BR(H → Zγ)", BR_ZGAM, "YR4_BR2")], "NNLO QCD + NLO EW", (345322,),
         "POWHEG card: vdecaymode 10, minlo 1; Pythia only '25:onIfMatch = 23 22'. No Z BR applied.", "YR4 ZH 'all but gg→ZH' 0.7612; BR H → Zγ."),
    ]
    for rid, sent, fac, order, dsids, note, look in newh:
        val = math.prod(v for _, v, _ in fac)
        at = atlas(*dsids)
        atl = f"ATLAS {', '.join(map(str, dsids))}: {at:.4g} pb → ATLAS/CMS = {ratio(at, val)}."
        if rid in (68571, 71295, 70451, 74682):
            atl += " ATLAS's genFiltEff for these H → μμ samples is 0.0002745 = the YR4 H → 4ℓ BR, not the H → μμ BR 2.176E-04 (2.176/2.745 = 0.793): an ATLAS-side metadata slip (its ggF H → μμ 345097 uses 0.0002176 and agrees to 1.000). Cross-check only."
        a(card(rid, "NEW (D13)", "D13", sent, fac, order, "none (YR4 total × YR4 BR)", look,
               "YR4 at 125.00 GeV × YR4 BR" + (" × PDG Z → ℓℓ (D6)" if rid in (37604, 68731) else "") + " (settled Higgs convention).",
               [("generator value (portal)", rec(rid)["gen"] / val - 1)], atl, note + " Probe 31 Oct: all 42 branches present."))
    r40 = rec(40062)
    eps = 1 - (1 - Z_LL) ** 2
    c = card(40062, "NEW (D13) — DECISION NEEDED on the value", "D13",
             "gg → ZH (associated Z any decay), H → ZZ → ℓℓ + anything (ℓ = e, μ, τ), JHUGen, with a JHUGen 4-lepton filter.",
             [("generator σ (portal, MiniAOD 40061) — placeholder only", r40["gen"], "portal")],
             "LO (JHUGen gg → ZH)", "see options",
             "The two JHUGen cards (fetched 31 Oct from the genproductions links in the record, because the portal copies return HTTP 404): `evidence/cards/40062/ggZH_NNPDF31_13TeV_M125.input` ('Process=51 VH_PC=gg DecayMode1=9': associated Z → anything) and `ZZ2l2any_withtaus_filter4l.input` ('DecayMode1=8 DecayMode2=9 FilterNLept=4 WriteFailedEvents=2': H → Z(→ ℓℓ, ℓ = e, μ, τ) Z(→ anything), keep events with 4 leptons).",
             "No settled convention: the sample is not 'H → 4ℓ'. Its σ needs the efficiency of the 4-lepton filter, which is not published.",
             [], f"ATLAS 345066 (gg → ZH, Z inclusive, H → ZZ → 4ℓ): {atlas(345066):.3g} pb — a different selection (no filter), not like-for-like.",
             f"The portal record is odd: total_value {r40['gen']:.3e} pb, 'matching efficiency' 0.2 on a JHUGen sample (the same pattern as the ZH → ZZ filtered samples left out on 26 Oct), total_value_uncertainty 2.330e+10. Probe 31 Oct: every genWeight = 1.0, no zero weights, so failed events are not in the NanoAOD and the filter efficiency cannot be measured from it. The sample is tiny: any option gives ≲ 4 events in 16.4 fb⁻¹ before selection.",
             options=[("(a) portal total_value as is", r40["gen"], "portal record " + r40["api"] + " (UNVERIFIED whether the filter is included)"),
                      ("(b) portal total_value × portal 'matching efficiency' 0.2 (read as the filter efficiency)", r40["gen"] * 0.2, "portal (interpretation UNVERIFIED)"),
                      (f"(c) YR4 0.1227 × BR(H → ZZ) 0.02619 × BR(Z → ℓℓ) 0.10099 × ε(4ℓ) with ε ESTIMATED as P(at least one of the two other Zs → ℓℓ) = 1 − (1 − 0.10099)² = {eps:.4f}", GGZH * BR_ZZ * Z_LL * eps, "YR4_XS, YR4_BR2, PDG_Z; ε is an ESTIMATE (ignores the filter's lepton definition, e.g. whether τ count)")])
    a(c)
    # ======================= tier 6 =======================
    bins = [(74894, "100-200", 280.35), (74898, "200-400", 77.67), (74902, "400-600", 10.73), (74904, "600-800", 2.559),
            (74906, "800-1200", 1.1796), (74896, "1200-2500", 0.28833), (74900, "2500-Inf", 0.006945)]
    RAZOR_LINE = {74894: 96, 74898: 97, 74902: 98, 74904: 100, 74906: 101, 74896: 102, 74900: 103}
    for rid, ht, razor_lo in bins:
        r = rec(rid)
        lo, hi = ht.split("-")
        opts = [("(a) generator LO value (portal)", r["gen"], "portal record " + r["api"]),
                ("(b) generator × 1.23 (the k the RazorAnalyzer table applies to these HT bins)", r["gen"] * K_ZNN_RAZOR, "RAZOR_ZNN (SECONDARY; origin of 1.23 not stated)"),
                (f"(c) generator × k_DY = 5765.4 / 5396 = {K_DY:.4f} (our DY NNLO normalisation ÷ the CP5 LO inclusive DY M-50 madgraphMLM portal value, MiniAOD 35670)", r["gen"] * K_DY, "RAZOR_DY + portal 35670; assumes the Z → νν and Z → ℓℓ LO/NNLO ratios are equal")]
        a(card(rid, "NEW (D11) — DECISION NEEDED on the value", "D11",
               f"Z → νν (3 flavours) + 0-4 partons, LO MadGraph MLM, generator-level jet HT {lo}-{hi} GeV.",
               [("generator σ (portal), LO", r["gen"], "portal")],
               "LO (MLM-merged, 0-4 partons)", "options (b), (c)",
               f"Card `evidence/cards/{rid}/*run_card.dat`: htjmin = {lo}, htjmax = {hi if hi != 'Inf' else '1d5'}; RazorAnalyzer line {RAZOR_LINE[rid]} for (b); RazorAnalyzer line 90 and the portal record 35670 for (c).",
               "No settled convention for an LO HT-binned V+jets set (our W and DY are NLO). The bins are used as they are (no stitching, D11). D6 BRs do not enter: the generator produces Z → νν directly; in (c) only the ratio NNLO/LO of the same boson enters.",
               [("option (b) × 1.23", K_ZNN_RAZOR - 1), (f"option (c) × {K_DY:.4f}", K_DY - 1)],
               f"ATLAS Z → νν (700335-700337, Sherpa NLO, kFactor 1, b/c/light filters summed) = {atlas(700335, 700336, 700337):.1f} pb, sliced differently ('pTV2' in the name; the slicing is not explained in the metadata): no like-for-like ATLAS value for an HT bin. The sum of the 7 CMS bins at option (a) is {sum(rec(b[0])['gen'] for b in bins):.1f} pb.",
               f"The RazorAnalyzer LO value for the older CUETP8M1 sample of this bin was {razor_lo} pb (vs {r['gen']} pb here, CP5). Probe 31 Oct: all 42 branches present, no negative weights; LHE_HT in file 0 lies inside {lo}-{hi} GeV (min/max in PLAN_v2_summary.md). Bins contiguous and exclusive from 100 GeV (cards).",
               options=opts))
    return out


def order_key(c):
    t = {r: (tier, i) for i, (r, _, _, tier, _, _) in enumerate(SAMPLES_V2)}
    return t[c["recid"]]


def fmt(v):
    return f"{v:.6g}"


def render(cs):
    names = {r: n for r, n, *_ in SAMPLES_V2}
    tiers = {r: t for r, _, _, t, _, _ in SAMPLES_V2}
    L = ["# Cross-section PROPOSALS v2 (31 Oct 2026) — after Matan's decisions", "",
         "Supersedes `XSEC_PROPOSALS.md` (26 Oct) for the sample list and the normalisation; that file is kept unchanged.",
         "Decisions: `DECISIONS.md`. **Nothing here is applied.** No value enters any registry or config; every value",
         "stays PROPOSED until Matan confirms it. Order = the order of review: tier 1 first.", "",
         "How to read the labels:",
         "- **unchanged from v1**: the card of `XSEC_PROPOSALS.md` copied as it was (its sources were read on 26 Oct 2026,",
         "  VERIFIED BY RUNNING then); only the ATLAS cross-check line and the decision reference are new.",
         "- **NEW / CHANGED**: every source number re-read on **31 Oct 2026** from the page linked (VERIFIED BY RUNNING: curl",
         "  + text extraction, arXiv numbers from the TeX source); table 'Sources used'.",
         "- Generator values, filter and matching efficiencies: CERN Open Data API, MiniAOD record (VERIFIED BY RUNNING,",
         "  raw copies in `evidence/records/` and `atlas_mapping/cms_records/`). The matching efficiency is shown and **never",
         "  multiplied in** (open point since 15 Oct).",
         "- **DECISION NEEDED**: no decision settles the value; the card lists options with sources and does not choose.",
         "  The σ_eff shown for it is the generator value, as a placeholder for the cost table only.",
         "- ATLAS values (σ × kFactor × genFiltEff, `atlas_mapping/atlas_bkg_metadata.json`, release 2024r-pp) are cross-checks only.",
         "- σ_eff arithmetic: `xsec_proposals_v2.py` (VERIFIED BY RUNNING).", ""]
    # summary table
    L += ["## Summary (review list)", "", "| # | tier | record | sample | status | proposed σ_eff [pb] | decision |", "|---:|---:|---|---|---|---:|---|"]
    for i, c in enumerate(cs, 1):
        v = fmt(c["sigma_eff_pb"]) if not c["options"] else "options"
        L.append(f"| {i} | {tiers[c['recid']]} | {c['recid']} | {names[c['recid']]} | {c['status']} | {v} | {c['decision']} |")
    L.append("")
    used = sorted({s for c in cs for _, _, s in c["factors"] if s != "portal"} |
                  {"SMP16018", "SMP17011", "RAZOR_ZNN", "RAZOR_DY", "POWHEG_ZZ", "SHERPA_MAN", "JHUGEN_SRC", "ST_NNLO_T", "ST_NNLO_S", "TTTT_NLL", "ATLAS_W"})
    L += ["## Sources used", "", "| key | link | where | as printed |", "|---|---|---|---|"]
    for k in used:
        u, where, txt = SOURCES_V2[k]
        L.append(f"| {k} | <{u}> | {where} | {txt} |")
    L.append("")
    cur = None
    for i, c in enumerate(cs, 1):
        r = rec(c["recid"])
        x = r["xs"]
        t = tiers[c["recid"]]
        if t != cur:
            cur = t
            L += [f"# Tier {t}", ""]
        L += [f"## {i}. {c['recid']} {names[c['recid']]} — tier {t} — {c['status']}", ""]
        if c["first"]:
            L += c["first"] + [""]
        L += [f"- **What it is:** {c['sentence']}",
              f"- **Dataset:** `{r['dataset']}` (MiniAOD parent {r['mini']}; <{r['link']}>)"]
        if c["options"]:
            L += ["- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):", ""]
            for lab, v, src in c["options"]:
                s = f"{SOURCES_V2[src.split(' ')[0]][0]}" if src.split(" ")[0] in SOURCES_V2 else src
                L.append(f"  - {lab}: **{fmt(v)} pb** — {s}" + (f" ({src})" if src.split(' ')[0] in SOURCES_V2 and ' ' in src else ""))
            L.append("")
        else:
            L += [f"- **Proposed σ_eff = {fmt(c['sigma_eff_pb'])} pb** = " + " × ".join(fmt(v) for _, v, _ in c["factors"]), ""]
            for lab, v, s in c["factors"]:
                src = f"portal API <{r['api']}> metadata.cross_section.total_value" if s == "portal" else f"{SOURCES_V2[s][0]} — {SOURCES_V2[s][1]} — as printed: {SOURCES_V2[s][2]}"
                L.append(f"  - {lab}: **{fmt(v)}** — {src}")
            L.append("")
        L += [f"- **Order:** {c['order']}."]
        if c["kfactor"]:
            L.append(f"- **k-factor and source:** {c['kfactor']}.")
        L += [f"- **Filter / matching efficiency (portal):** filter = {x.get('filter_efficiency')}, matching = {x.get('matching_efficiency')} (not multiplied in); total_value = {x.get('total_value')} pb, negative-weight fraction = {x.get('neg_weight_fraction')} (<{r['api']}>)."]
        if not c["options"] and r["gen"]:
            L.append(f"- **Proposed / generator:** {c['sigma_eff_pb'] / r['gen']:.4f}")
        L += [f"- **What Matan should open and look for:** {c['look']}",
              f"- **Decision / convention:** {c['decision']} — {c['convention']}"]
        if c["alternatives"]:
            L.append("- **Alternatives (effect on σ_eff):** " + "; ".join(f"{lab} → {d * 100:+.1f} %" for lab, d in c["alternatives"]))
        else:
            L.append("- **Alternatives:** none with a public source found.")
        if c["atlas"]:
            L.append(f"- **ATLAS cross-check:** {c['atlas']}")
        if c["notes"]:
            L.append(f"- **Note:** {c['notes']}")
        L.append("")
    L += ["## Numbers that could not be verified", "",
          "- 75567: the meaning of the POWHEG flag `leptons-nu` (which lepton and neutrino flavours) — the POWHEG-BOX ZZ manual was not opened (UNVERIFIED); the share of its σ at low m(ℓℓ) is not measured.",
          "- 40062: the 4-lepton filter efficiency (not published; option (c) uses an ESTIMATE); the meaning of its portal 'matching efficiency' 0.2 (UNVERIFIED); JHUGen v7.2.3 flag meanings taken from the current JHUGen master (UNVERIFIED for that version).",
          "- 35999 / 35987 / 35993: ATLAS's generator-level cuts (not in the public metadata: UNKNOWN); the size of the s-channel diboson part in the CMS samples (not measured); SMP-17-011 calls its LO 'ℓ = e, μ or τ' but its measurement 'per channel' — the ratio 6.23 / 6.81 is taken as printed, the ambiguity is not resolved.",
          "- Z → νν option (b): the origin of the RazorAnalyzer 1.23 (not stated in the file; SECONDARY). Option (c) assumes equal NNLO/LO ratios for Z → νν and Z → ℓℓ (not shown by any source).",
          "- Unchanged v1 cards: sources read 26 Oct, not re-read today (except PDG W/Z, YR4 and the old Top WG page, which were re-read and are unchanged).", ""]
    return "\n".join(L)


def main():
    cs = sorted(cards(), key=order_key)
    (HERE / "evidence" / "xsec_proposals_v2.json").write_text(json.dumps(
        {"what": "PROPOSALS v2 (31 Oct 2026), not applied; options = DECISION NEEDED",
         "sources": SOURCES_V2, "cards": cs}, indent=1, ensure_ascii=False) + "\n")
    (HERE / "XSEC_PROPOSALS_v2.md").write_text(render(cs))
    for c in cs:
        print(c["recid"], c["status"][:30], fmt(c["sigma_eff_pb"]) if c["sigma_eff_pb"] else "-",
              [fmt(v) for _, v, _ in c["options"]] if c["options"] else "")


if __name__ == "__main__":
    main()
