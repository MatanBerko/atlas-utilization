"""Steps 2-5 of the ATLAS DSID mapping (27 Oct 2026). Research and planning only.

Every ATLAS DSID of Maryna's background list is assigned to ONE physics process (PROCS below),
using only the public ATLAS Open Data metadata in atlas_bkg_metadata.json (physics_short, process,
description). Each process is mapped to the CMS side:

  delivered    in the 25-26 Oct delivery (registry v3, read only; its cross_section_pb)
  proposed     proposed in the plan (plan_samples.py tier; sigma_eff from evidence/xsec_proposals.json, PROPOSED)
  portal       exists on the CMS portal but not proposed (record IDs from candidates.json or cms_extra_records.json)
  none         no CMS 2016 sample found (= not observed in the searches; not "does not exist")
  out_of_scope photons / QCD / BSM / unclear physics

ATLAS sigma = cross_section_pb x kFactor x genFiltEff of the NOMINAL DSIDs only (alternative generators are
listed but not summed). It is a CROSS-CHECK only, never a source for a CMS cross section.
Writes mapping.json, mapping_tables.md, higgs_scope.json. No cross section is changed anywhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE.parent
REPO = PLAN.parents[1]
sys.path.insert(0, str(PLAN))
from plan_samples import by_recid  # noqa: E402

META = json.loads((HERE / "atlas_bkg_metadata.json").read_text())["datasets"]
REG = json.loads((REPO / "studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json").read_text())
DELIVERED = {int(k): REG["records"][k]["cross_section_pb"] for k in REG["full_run_records"]}
PROPOSED = {p["recid"]: p["sigma_eff_pb"] for p in json.loads((PLAN / "evidence/xsec_proposals.json").read_text())["proposals"]}
PLANS = by_recid()
CANDS = {c["nano_recid"]: c for c in json.loads((PLAN / "candidates.json").read_text())["candidates"]}
EXTRA = {r["nano_recid"]: r for r in json.loads((HERE / "cms_extra_records.json").read_text())["rows"] if r["status"] == "found"}

# Process table. nominal: DSIDs summed for the ATLAS sigma. alt: {label: DSIDs} = other generators / tunes for the
# SAME process (ATLAS-side double counting is ATLAS's business; listed for Maryna). subset: DSIDs that are a
# decay- or filter-subset of the same process (also overlap if mixed with the nominal).
# cms: list of CMS record IDs; status as in the module docstring. h = (production, decay) for Higgs rows.
P = []


def proc(key, label, cat, nominal, cms, status, note="", alt=None, subset=None, slicing="", ratio_note="", h=None):
    P.append(dict(key=key, label=label, cat=cat, nominal=[str(d) for d in nominal], cms=cms, status=status,
                  note=note, alt={k: [str(d) for d in v] for k, v in (alt or {}).items()},
                  subset=[str(d) for d in (subset or [])], slicing=slicing, ratio_note=ratio_note, h=h))


R = lambda a, b: list(range(a, b + 1))  # noqa: E731

# ---------------- V + jets ----------------
proc("Zll_jets", "Z/γ* → ℓℓ + jets (ee, μμ, ττ), mass range not stated in the metadata", "V+jets",
     R(700320, 700325) + R(700792, 700794), [35669], "delivered",
     slicing="b/c-hadron filter split per flavour: BFilter / CFilterBVeto / CVetoBVeto (exclusive slices, summed)",
     note="ee and μμ: Sherpa 2.2.11; ττ: Sherpa 2.2.14. CMS DY M-50 holds all three flavours in one sample.")
proc("Zll_lowmass", "Z/γ* → ℓℓ + jets, 10 < m(ℓℓ) < 40 GeV (ee, μμ, ττ)", "V+jets",
     R(700467, 700472) + R(700901, 700903), [35631], "delivered",
     slicing="b/c-hadron filter split per flavour; ee/μμ names also carry 'pT5' (meaning UNKNOWN from the metadata) "
             "and list a MultiLeptonFilter",
     ratio_note="different phase space: ATLAS 10-40 GeV with a multi-lepton filter (ee, μμ) vs CMS 10-50 GeV unfiltered")
proc("Znunu_jets", "Z → νν + jets", "V+jets", R(700335, 700337), [74894, 74898, 74902, 74904, 74906, 74896, 74900,
     73752, 73746, 73748, 73750, 73766, 73760, 73762, 73764], "portal",
     slicing="b/c-hadron filter split", note="not proposed: D11 (no prompt leptons). CMS has HT-binned LO "
     "(no HT < 100 bin) and pT-binned NLO, no inclusive sample.")
proc("Wlnu_jets", "W → ℓν + jets (eν, μν, τν; τ split into leptonic / hadronic τ decays)", "V+jets",
     R(700338, 700349), [69715, 69717, 69719], "proposed",
     slicing="b/c-hadron filter split per flavour; τν further split L (leptonic τ) / H (hadronic τ)",
     note="CMS set decided by Matan (D1: the three NLO jet-binned pieces, each alone; D2: RazorAnalyzer normalisation).")
proc("EWZll_jj", "electroweak Z/γ*(→ ℓℓ) + 2 jets (VBF-like, ee, μμ, ττ)", "V+jets", R(700358, 700360), [35999], "portal",
     note="not in the plan. CMS DY+jets samples are QCD production and do not contain this.")
proc("EWWlnu_jj", "electroweak W(→ ℓν) + 2 jets", "V+jets", R(700362, 700364), [35987, 35993], "portal",
     note="not in the plan (§2a lists them as available).")
proc("EWZnunu_jj", "electroweak Z(→ νν) + 2 jets", "V+jets", [700361], [36001], "portal", note="no prompt leptons")
proc("Wqq_highpt", "W → qq' + jets, pT(W) > 200 GeV", "V+jets", [700843], [69751, 69753, 69755, 69757], "portal",
     note="no leptons; CMS WJetsToQQ is HT-binned from 200 GeV (different slicing variable)")
proc("Zqq_highpt", "Z → qq + jets, pT(Z) > 200 GeV", "V+jets", [700849], [74912, 74914, 74916, 74918], "portal",
     note="no leptons; CMS ZJetsToQQ is HT-binned from 200 GeV")
proc("Zbb_highpt", "Z → bb + jets, pT(Z) > 200 GeV", "V+jets", [700855], [], "none",
     note="ZJetsToBB not observed (fetch_cms_extra.py); whether CMS ZJetsToQQ includes b quarks is UNVERIFIED")

# ---------------- dibosons ----------------
proc("WW_lvqq", "WW → ℓνqq", "diboson", [700488], [72658], "proposed")
proc("WZ_lvqq", "WZ → ℓν qq (incl. Z → bb)", "diboson", [700489, 700490], [72738], "proposed",
     slicing="Z → qq and Z → bb in separate DSIDs (exclusive, summed)")
proc("WZ_qqvv", "WZ → qq νν", "diboson", [700491], [], "none", note="WZTo2Q2Nu / WZToQQ2Nu not observed; no leptons")
proc("WZ_qqll", "WZ → qq ℓℓ", "diboson", [700492], [72742], "proposed",
     ratio_note="different phase space: the CMS sample includes γ* → ℓℓ down to m(ℓℓ) = 4 GeV (PLAN D9)")
proc("ZZ_qqll", "ZZ → qq ℓℓ (incl. Z → bb)", "diboson", [700493, 700494], [75573], "proposed",
     slicing="Z → qq and Z → bb in separate DSIDs",
     ratio_note="different phase space: the CMS sample includes γ* → ℓℓ down to m(ℓℓ) = 4 GeV (as WZ → qqℓℓ)")
proc("ZZ_qqvv", "ZZ → qq νν (incl. Z → bb)", "diboson", [700495, 700496], [75571], "portal",
     slicing="Z → qq and Z → bb in separate DSIDs", note="no leptons; not proposed")
proc("VV_4l", "VV → ℓℓℓℓ (Sherpa 2.2.12)", "diboson", [700600], [75589], "delivered")
proc("VV_3lv", "VV → ℓℓℓν", "diboson", [700601], [72752], "delivered")
proc("VV_2l2v_os", "VV → ℓℓνν, opposite sign (WW and ZZ → ℓℓνν together)", "diboson", [700602], [72676], "delivered",
     ratio_note="the ATLAS sample also holds ZZ → ℓℓνν; CMS has WW → 2ℓ2ν only (ZZTo2L2Nu 75567 excluded, D14)")
proc("WW_ss_qcd", "W±W± → ℓ±ℓ±νν, QCD-induced, 0-1 jets", "diboson", [700603], [71642], "portal",
     note="CMS WpWpJJ_QCD (madgraph) exists, not proposed")
proc("VV_lvvv", "VV → ℓννν", "diboson", [700604], [72740], "proposed")
proc("VV_4v", "VV → νννν", "diboson", [700605], [], "none", note="ZZTo4Nu not observed (PLAN §2d); no leptons")
proc("VBS_4ljj", "electroweak ℓℓℓℓ jj (VBS, incl. triboson-like diagrams)", "diboson", [700587], [75561], "portal",
     note="CMS ZZJJTo4L_EWKnotop exists, not proposed")
proc("VBS_3lvjj", "electroweak ℓℓℓν jj (VBS)", "diboson", [700588], [69771, 72728], "portal",
     note="CMS WLLJJ_WToLNu_EWK and WZJJ_EWK exist; which matches the ATLAS phase space is UNVERIFIED")
proc("VBS_2l2vjj_os", "electroweak ℓℓνν jj, opposite sign (VBS)", "diboson", [700589], [72648], "portal",
     note="CMS WWJJToLNuLNu_EWK_noTop exists, not proposed")
proc("VBS_2l2vjj_ss", "electroweak ℓ±ℓ±νν jj, same sign (VBS)", "diboson", [700590], [71638], "portal",
     note="CMS WpWpJJ_EWK is in the plan as 'optional' (no proposal)")
proc("VBS_interference", "EW-QCD interference terms of the four VBS channels", "diboson", R(700591, 700594), [], "none",
     note="no CMS interference sample observed in the plan's searches (not searched by name)")

# ---------------- tribosons ----------------
proc("WWW", "WWW (leptonic: 3ℓ3ν, and ℓνℓν jj same-/opposite-sign)", "triboson", [364242] + R(364336, 364339),
     [72701], "proposed", slicing="split by decay channel and charge (W+W+W- / W-W-W+), summed",
     ratio_note="different decay channels: ATLAS leptonic channels only, CMS WWW_4F all decays")
proc("WWZ", "WWZ (4ℓ2ν, 2ℓ4ν)", "triboson", [364243, 364244], [72711], "proposed",
     ratio_note="different decay channels: ATLAS leptonic only, CMS all decays")
proc("WZZ", "WZZ (5ℓ1ν, 3ℓ3ν)", "triboson", [364245, 364246], [72761], "proposed",
     ratio_note="different decay channels: ATLAS leptonic only, CMS all decays")
proc("ZZZ", "ZZZ (6ℓ, 4ℓ2ν, 2ℓ4ν)", "triboson", R(364247, 364249), [75600], "proposed",
     ratio_note="different decay channels: ATLAS leptonic only, CMS all decays")

# ---------------- top ----------------
proc("tt_nonallhad", "tt̄, not all-hadronic (single-lepton + dilepton)", "top", [410470], [67801, 67993], "delivered",
     alt={"Powheg+Herwig7 (single-lepton 411233 + dilepton 411234)": [411233, 411234],
          "Powheg+Pythia8 pThard=1 (dilepton 601491 + single-lepton 601497)": [601491, 601497]})
proc("tt_allhad", "tt̄, all-hadronic", "top", [410471], [67841], "proposed",
     alt={"Powheg+Herwig7": [411316], "Powheg+Pythia8 pThard=1 (name; see note)": [601495]},
     note="601495: name says 'allhad', but the metadata lists a TTbarWToLeptonFilter, a MadGraph generator and "
          "σ×filter = 0.089 pb (vs ~379 pb for 410471): its content is UNKNOWN from the metadata")
proc("st_tchan", "single top t-channel, leptonic top decay (top + antitop)", "top", [410658, 410659], [64793, 64693], "proposed",
     alt={"Powheg+Herwig7 (600017 antitop, 600018 top)": [600017, 600018],
          "Powheg+Pythia8 pThard=1 (601487 antitop, 601489 top)": [601487, 601489]},
     ratio_note="different decay channels: ATLAS leptonic top decays only, CMS inclusive decays")
proc("st_schan", "single top s-channel, leptonic (top + antitop)", "top", [410644, 410645], [64635], "proposed",
     alt={"Powheg+Herwig7 (600019 antitop, 600020 top)": [600019, 600020]})
proc("st_tW", "single top tW, inclusive decays (top + antitop), diagram removal", "top", [601352, 601355], [64895, 64839],
     "delivered", alt={"DR, pThard=1 (601761, 601762)": [601761, 601762], "diagram subtraction DS (601627, 601631)": [601627, 601631]},
     subset=[601763, 601764, 601624, 601628],
     note="subset DSIDs: dilepton tW (DR pThard=1: 601763/601764; DS: 601624/601628)",
     ratio_note="different decay channels: ATLAS inclusive, CMS NoFullyHadronic")
proc("ttW", "tt̄W (inclusive)", "top", [410155], [68073, 68083], "delivered",
     alt={"Sherpa 2.2.8 (700000)": [700000]}, note="CMS: ℓν part delivered (68073), qq part proposed tier 4 (68083)")
proc("ttZ_ll_vv", "tt̄Z/γ* → ℓℓ (ee, μμ, ττ) and tt̄Z → νν", "top", [410218, 410219, 410220, 410156], [68187], "delivered",
     slicing="one DSID per Z decay (exclusive, summed); the m(ℓℓ) threshold is not stated in the metadata")
proc("ttZ_qq", "tt̄Z → qq", "top", [410157], [68206], "proposed")
proc("tZq", "tZ t-channel (4-flavour), excluding all-hadronic decays", "top", [410560], [68325], "proposed",
     ratio_note="different decay channels: ATLAS 'noAllHad' keeps Z → qq with a leptonic top, CMS tZq_ll has Z → ℓℓ only")
proc("tWZ", "tWZ, Z → ℓℓ", "top", [410408], [64873], "proposed",
     ratio_note="generator order (CMS value is LO, D8) and an ATLAS ΔR(ℓℓ) > 1 cut in the name")
proc("tttt", "tt̄tt̄", "top", [412043], [68045], "proposed", alt={"aMC@NLO+Herwig7": [412044]},
     ratio_note="generator order: the CMS proposal is the generator NLO value (8.09 fb); D7 recommends 11.97 fb")
proc("ttt", "three top quarks (SM)", "top", [304014], [67771, 68067], "portal", note="CMS TTTJ + TTTW (LO) exist, not proposed")
proc("ttWW", "tt̄WW", "top", [410081], [68087], "portal", note="CMS TTWW (LO) exists, not proposed")
proc("ttgamma", "tt̄γ", "photon", [410389], [67439, 67459, 67453], "out_of_scope",
     alt={"MG+Pythia8 older (410082 non-allhad, 410087 allhad)": [410082, 410087],
          "MG+Herwig7 (410395 non-allhad, 410396 allhad)": [410395, 410396]},
     note="photons deferred")

# ---------------- photons / QCD / BSM (out of scope) ----------------
proc("gamma_jets", "γ + jets (prompt photon), pT(γ)-sliced", "photon", R(364541, 364547), [], "out_of_scope",
     alt={"Pythia8 (423099-423112)": R(423099, 423112)}, slicing="pT(γ) slices 17 → E_CMS (Sherpa); 8 → ∞ (Pythia8)")
proc("diphoton", "γγ (+ jets), m(γγ)-sliced", "photon", R(364350, 364354), [], "out_of_scope",
     alt={"Pythia8 2DP20 (302520-302534; Maryna's class 'HC model (SM modes)')": R(302520, 302534)},
     slicing="m(γγ) slices 0 → E_CMS (Sherpa); 55 → ∞ (Pythia8)")
proc("Vgamma", "V + γ (ℓℓγ, ννγ, ℓνγ, qqγ, bbγ, EW ℓνγjj / ℓℓγjj)", "photon",
     R(700398, 700404) + [700352, 700353, 700507, 700709, 700710], [], "out_of_scope")
proc("Vgammagamma", "V + γγ and γγγ", "photon", R(700195, 700201) + [700007], [], "out_of_scope")
proc("EWgamma_jj", "electroweak γ + 2 jets, pT(γ) > 140 GeV (Maryna's class 'QCD jets')", "photon", [700442], [], "out_of_scope",
     note="the metadata describes it as 'Electroweak Sherpa gamma + 2,3j@LO', not QCD multijet")
proc("qcd_dijet", "QCD dijet (Pythia8, JZ0-JZ12 leading-jet-pT slices)", "QCD", R(364700, 364712), [], "out_of_scope",
     slicing="JZ0 … JZ12 slices", note="in Maryna's 'EW boson / V+jets / diboson' class; this IS a QCD multijet set")
proc("bsm_Zprime_tautau", "Z' → ττ, SSM 3 TeV", "BSM", [801976], [], "out_of_scope")
proc("bsm_Wprime_taunu", "W' → τν, SSM 3 TeV", "BSM", [801978], [], "out_of_scope")

# ---------------- Higgs (production x decay) ----------------
def H(key, prod, dec, nominal, cms, status, **kw):
    proc(key, f"{prod}, H → {dec}", "Higgs", nominal, cms, status, h=(prod, dec), **kw)


TAU_SPLIT = "split by ττ decay with lepton/hadron pT filters (ll 13/7, ℓ±h∓ 15/20, hh 30/20 GeV), summed"
H("ggF_ZZ4l", "ggF", "ZZ → 4ℓ", [345060], [37728], "delivered", alt={"Powheg+Herwig7, no τ (346446)": [346446]},
  ratio_note="different decay channels: ATLAS 4ℓ with ℓ = e, μ; CMS JHUGen ZZ → 4ℓ includes τ")
H("ggF_WW", "ggF", "WW", [345324], [37474], "proposed", alt={"Powheg+Herwig7, no τ (346802)": [346802]},
  note="ATLAS: H → WW → ℓνℓν, name carries a lepton filter 'EF_15_5'")
H("ggF_tautau", "ggF", "ττ", R(345120, 345123), [37446], "proposed", alt={"Powheg+Herwig7 (600565-600568)": R(600565, 600568)},
  slicing=TAU_SPLIT, ratio_note="filter: the ATLAS pieces carry ττ-decay and lepton/hadron pT filters")
H("ggF_ZZ4nu", "ggF", "invisible (ZZ → 4ν)", [346588], [], "none", note="MET > 75 GeV filter; GluGluHToZZTo4Nu not observed; no leptons")
H("ggF_mumu", "ggF", "μμ", [345097], [37432], "portal", note="in the plan as 'optional' (no proposal)")
H("ggF_gamgam", "ggF", "γγ", [343981], [37350], "portal", alt={"Powheg+Herwig7 (346797)": [346797]}, note="photon final state")
H("ggF_Zgam", "ggF", "Zγ", [345316], [37604], "portal", note="ATLAS and CMS: Z → ℓℓ")
H("ggF_dalitz", "ggF", "γ*γ, γ* → ℓℓ (Dalitz)", [345961], [37420, 37276], "portal")
H("ggF_etau_mutau", "ggF", "eτ / μτ (as named)", [345124, 345125], [], "out_of_scope",
  note="named H → eτ / μτ with a TauFilter; whether this is lepton-flavour-violating (BSM) or a ττ subset is UNKNOWN from the metadata")
H("VBF_ZZ4l", "VBF", "ZZ → 4ℓ", [346228], [68847], "delivered", alt={"Powheg+Herwig7 (346447)": [346447]},
  ratio_note="different decay channels: ATLAS 4ℓ without τ; CMS JHUGen includes τ")
H("VBF_WW", "VBF", "WW", [345948], [68601], "proposed", note="H → WW → ℓνℓν",
  alt={"Powheg+Herwig7 (346877)": [346877], "MadGraph+Herwig7 (500335; Maryna's class 'Higgs related')": [500335]})
H("VBF_tautau", "VBF", "ττ", R(346190, 346193), [68591], "proposed", alt={"Powheg+Herwig7 (600569-600572)": R(600569, 600572)},
  slicing=TAU_SPLIT, ratio_note="possible error on the ATLAS side: the four ATLAS filtered pieces sum to MORE than σ(VBF) × BR(ττ); "
  "they do not behave like the ggF pieces (cross-check only)")
H("VBF_gamgam", "VBF", "γγ", [346214], [68499], "portal", alt={"Powheg+Herwig7 (346878)": [346878]}, note="photon final state")
H("VBF_mumu", "VBF", "μμ", [345106], [68571], "portal", note="in the plan as 'optional'")
H("VBF_bb", "VBF", "bb̄", [345949], [68445], "portal")
H("VBF_Zgam", "VBF", "Zγ", [345833], [68731], "portal", note="ATLAS and CMS: Z → ℓℓ")
H("VBF_dalitz", "VBF", "γ*γ, γ* → ℓℓ (Dalitz)", [345834], [68559, 68459], "portal")
H("VBF_ZZllbb", "VBF", "ZZ → ℓℓbb", [450576], [68833], "portal", note="CMS VBF_HToZZTo2L2X (2ℓ + anything) is a superset")
H("VBF_etau_mutau", "VBF", "eτ / μτ (as named)", [346194, 346195], [], "out_of_scope", note="as ggF eτ/μτ")
H("VBF_incl", "VBF", "all decays", [346317], [], "none",
  note="no CMS inclusive-decay VBF H sample observed; overlaps every ATLAS VBF decay sample above")
H("WH_ZZ4l", "W±H", "ZZ → 4ℓ", [346449, 346450], [71227, 70383], "proposed",
  alt={"Powheg+Pythia8 'shw' (346646, 346647)": [346646, 346647]})
H("WH_WW", "W±H", "WW", [345325, 345433], [41877, 41873], "proposed",
  ratio_note="different decay channels: ATLAS W → qq and H → WW → ℓνℓν only; CMS HWJ H → WW and W inclusive (superset)")
H("WH_tautau", "W±H", "ττ", [345211, 345212], [71297, 70453], "proposed",
  alt={"Powheg+Herwig7 (600573, 600574)": [600573, 600574], "aMC@NLO FxFx W+H only (506098)": [506098]},
  note="506098 σ×filter = 0.903 pb ≈ σ(W+H) itself, i.e. BR(ττ) apparently not included (ATLAS metadata, cross-check only)")
H("WH_mumu", "W±H", "μμ", [345104, 345105], [71295, 70451], "portal")
H("WH_gamgam", "W±H", "γγ", [345317, 345318], [71013, 70173], "portal", alt={"Powheg+Herwig7 (346880, 346881)": [346880, 346881]},
  note="photon final state")
H("WH_Zgam", "W±H", "Zγ", [345320, 345321], [71145, 70301], "portal", note="Z decay not stated in the ATLAS metadata; CMS WToAll, Z inclusive per its name")
H("WH_dalitz", "W±H", "γ*γ, γ* → ℓℓ (Dalitz)", [345963, 345964], [], "none", note="W±H Dalitz not observed (fetch_cms_extra.py)")
H("WH_etau_mutau", "W±H", "eτ / μτ (as named)", R(345213, 345216), [], "out_of_scope", note="as ggF eτ/μτ")
H("WH_ee", "W±H", "ee", [345877, 345878], [69343], "portal", note="CMS VHToEE covers W±H and ZH together")
H("WH_inv", "W±H", "invisible (ZZ → 4ν)", [346605, 346606], [71359, 70515], "portal",
  note="ATLAS: W inclusive, MET > 75 GeV filter. CMS only with W → qq (no leptons); CMS H → invisible normalisation would need a BR decision")
H("WH_incl", "W±H", "all decays", [346311, 346312], [], "none", note="no CMS inclusive W±H sample observed (VHToNonbb 69389 is W±H + ZH, H ≠ bb)")
H("qqZH_bb_vv", "qq̄ → ZH", "bb̄", [345056], [74118], "portal", note="Z → νν (ATLAS and CMS)", alt={"Powheg+Herwig7 (346398)": [346398]})
H("qqZH_cc_vv", "qq̄ → ZH", "cc̄", [345112], [74126], "portal", alt={"Powheg+Herwig7 (346726)": [346726]},
  note="Z → νν (ATLAS and CMS). 346726: name 'vvcc', but the metadata 'process' field says H → bb (ATLAS metadata inconsistency)")
H("qqZH_mumu", "qq̄ → ZH", "μμ", [345103], [74682], "portal")
H("qqZH_tautau", "qq̄ → ZH", "ττ", [345217], [74684], "proposed",
  alt={"Powheg+Herwig7 (600575)": [600575], "aMC@NLO FxFx (506099)": [506099]},
  note="506099 σ×filter = 0.787 pb ≈ σ(ZH) itself, BR(ττ) apparently not included (ATLAS metadata)")
H("qqZH_gamgam", "qq̄ → ZH", "γγ", [345319], [74132], "portal", alt={"Powheg+Herwig7 (346879)": [346879], "aMC@NLO FxFx, Z → qq (506813)": [506813]},
  note="photon final state")
H("qqZH_Zgam", "qq̄ → ZH", "Zγ", [345322], [74292], "portal")
H("qqZH_dalitz", "qq̄ → ZH", "γ*γ, γ* → ℓℓ (Dalitz)", [345965], [74670, 74652], "portal")
H("qqZH_WW", "qq̄ → ZH", "WW", [345445, 341456, 341458, 341460], [41914], "proposed",
  slicing="ℓνqq split by Z → νeνe / νμνμ / ντντ (341456/58/60; Maryna's class 'ggF Higgs', but the metadata says qq → ZH)",
  ratio_note="different decay channels: ATLAS Z → νν only; CMS HZJ H → WW, Z inclusive (superset)")
H("qqZH_ZZ4l", "qq̄ → ZH", "ZZ → 4ℓ", [346645], [74314], "portal", alt={"Powheg+Herwig7 (346448)": [346448]},
  note="ATLAS: Z inclusive. CMS ZH_HToZZ_4LFilter: not proposed, its portal 'matching efficiency' looks misplaced (D13, UNVERIFIED)")
H("qqZH_ee", "qq̄ → ZH", "ee", [345876], [69343], "portal", note="CMS VHToEE covers W±H and ZH")
H("qqZH_inv", "qq̄ → ZH", "invisible (ZZ → 4ν)", [346607], [74892], "portal", note="ATLAS: Z inclusive, MET > 75 GeV. CMS only with Z → qq")
H("qqZH_etau_mutau", "qq̄ → ZH", "eτ / μτ (as named)", [345218, 345219], [], "out_of_scope", note="as ggF eτ/μτ")
H("qqZH_incl", "qq̄ → ZH", "all decays", [346310], [], "none", note="no CMS inclusive ZH sample observed")
H("ggZH_bb_vv", "gg → ZH", "bb̄", [345058], [36597], "portal", note="Z → νν (ATLAS and CMS)", alt={"Powheg+Herwig7 (346400)": [346400]})
H("ggZH_cc_vv", "gg → ZH", "cc̄", [345114], [36605], "portal", note="Z → νν (ATLAS and CMS)", alt={"Powheg+Herwig7 (346728)": [346728]})
H("ggZH_gamgam", "gg → ZH", "γγ", [345061], [36611, 36617, 36623], "portal",
  alt={"Powheg+Herwig7 (346882)": [346882], "aMC@NLO, Z → qq (506814)": [506814]}, note="photon final state")
H("ggZH_ZZ4l", "gg → ZH", "ZZ → 4ℓ", [345066], [40062], "portal", alt={"Powheg+Herwig7 (346451)": [346451]},
  note="ATLAS: Z inclusive. CMS GluGluToZH_HToZZTo4L (JHUGen) exists: PLAN §2g says 'not observed' for this cell, which is a correction")
H("ggZH_mumu", "gg → ZH", "μμ", [345098], [], "none", note="not observed")
H("ggZH_tautau", "gg → ZH", "ττ", [600686], [], "none", note="ATLAS: Z inclusive; CMS not observed")
H("ggZH_WW", "gg → ZH", "WW", [346524], [40095], "proposed",
  note="ATLAS: Z inclusive. CMS proposed sample has Z → ℓℓ only; GluGluZH_HToWWTo2L2Nu 40090 (Z inclusive, H → 2ℓ2ν) also exists",
  ratio_note="different decay channels: CMS proposal is Z → ℓℓ only")
H("ggZH_inv", "gg → ZH", "invisible (ZZ → 4ν)", [345596], [36929], "portal", note="ATLAS: Z inclusive. CMS only with Z → qq")
H("ttH_incl", "tt̄H", "all decays", [346343, 346344, 346345], [67645, 67691], "proposed",
  slicing="split by tt̄ decay, summed", subset=[346189, 346525, 346526, 346601, 346340, 346341, 346342, 346452, 346453, 346454,
  346919, 346923, 346927, 346198, 346632, 346633, 346634],
  note="subset DSIDs (ATLAS-side overlap with the inclusive ones): γγ 346189/346525 (+ Herwig 346526, 346601), ZZ → 4ℓ "
       "346340-346342 (+ Herwig 346452-346454), ττ 346919/346923/346927, Zγ 346198, ZZ → 4ν 346632-346634 "
       "(the metadata 'process' field of all three says 'allhad', the names say semilep/allhad/dilep). "
       "On the CMS side all of them are inside ttH → bb + ttH → non-bb.")
H("tHjb", "tHq (tHjb)", "γγ and ZZ → 4ℓ", [346188, 346414], [65657, 65649], "portal", alt={"aMC@NLO+Herwig7 γγ (346602)": [346602]},
  note="CMS THQ_ctcvcp: generated at a non-SM coupling, needs reweighting (D13, UNVERIFIED); not proposed")
H("tWH", "tWH", "γγ and ZZ → 4ℓ", [346486, 346511], [65725, 65721], "portal", note="CMS THW_ctcvcp: as tHq")


def sig(d):
    m = META[d]["metadata"]
    return float(m["cross_section_pb"]) * float(m["kFactor"]) * float(m["genFiltEff"])


def nfiles(d):
    return META[d]["metadata"]["n_files_get_urls"]


def cms_sigma(recids, status):
    vals = []
    for r in recids:
        if r in DELIVERED:
            vals.append(DELIVERED[r])
        elif r in PROPOSED and r in PLANS and PLANS[r]["role"] == "recommended":
            vals.append(PROPOSED[r])
        else:
            return None
    return sum(vals) if vals else None


def cms_name(r):
    if r in CANDS:
        return CANDS[r]["dataset"].split("/")[1]
    if r in EXTRA:
        return EXTRA[r]["dataset"].split("/")[1]
    return "UNKNOWN"


def cms_info(r):
    c = CANDS.get(r) or EXTRA.get(r) or {}
    return dict(recid=r, name=cms_name(r), events=c.get("number_events"), files=c.get("number_files"),
                portal_total_value=(c.get("portal_cross_section") or {}).get("total_value"),
                delivered=r in DELIVERED, plan_role=PLANS.get(r, {}).get("role"), plan_tier=PLANS.get(r, {}).get("tier"))


def main():
    used = {}
    for p in P:
        for d in p["nominal"] + [x for v in p["alt"].values() for x in v] + p["subset"]:
            assert d in META, d
            assert d not in used, (d, used.get(d), p["key"])
            used[d] = p["key"]
    missing = sorted(set(META) - set(used))
    assert not missing, missing
    rows = []
    for p in P:
        a = sum(sig(d) for d in p["nominal"])
        c = cms_sigma(p["cms"], p["status"]) if p["status"] in ("delivered", "proposed") else None
        ratio = a / c if c else None
        flag = ratio is not None and not (0.7 <= ratio <= 1.4)
        rows.append(dict(
            key=p["key"], process=p["label"], category=p["cat"], higgs_cell=p["h"],
            atlas_nominal_dsids=p["nominal"], atlas_alternatives=p["alt"], atlas_subset_dsids=p["subset"],
            atlas_sigma_nominal_pb_CROSSCHECK=a,
            atlas_sigma_per_dsid_pb={d: sig(d) for d in p["nominal"] + [x for v in p["alt"].values() for x in v] + p["subset"]},
            atlas_files_nominal=sum(nfiles(d) for d in p["nominal"]),
            atlas_files_alternatives={k: sum(nfiles(d) for d in v) for k, v in p["alt"].items()},
            slicing=p["slicing"], cms_status=p["status"], cms_records=[cms_info(r) for r in p["cms"]],
            cms_sigma_eff_pb=c, cms_sigma_source=("registry v3 (delivered) / xsec_proposals.json (PROPOSED)" if c else None),
            ratio_atlas_over_cms=ratio, ratio_flag=flag, ratio_note=p["ratio_note"] if (flag or p["ratio_note"]) else "",
            note=p["note"]))
    # a few like-for-like cross-checks the flagged ratios need (VERIFIED BY RUNNING: arithmetic on the numbers above)
    BR_W_LEP = 0.1071 + 0.1063 + 0.1138   # settled PDG convention
    BR_W_HAD = 0.6741
    by = {r["key"]: r for r in rows}
    extra = {
        "st_tchan: ATLAS leptonic / (CMS inclusive × BR(W → ℓν))": by["st_tchan"]["atlas_sigma_nominal_pb_CROSSCHECK"] / (by["st_tchan"]["cms_sigma_eff_pb"] * BR_W_LEP),
        "st_tchan alt pThard=1 / (CMS × BR(W → ℓν))": sum(sig(d) for d in ["601487", "601489"]) / (by["st_tchan"]["cms_sigma_eff_pb"] * BR_W_LEP),
        "st_tW: ATLAS inclusive × (1 − BR(W → had)²) / CMS NoFullyHadronic": by["st_tW"]["atlas_sigma_nominal_pb_CROSSCHECK"] * (1 - BR_W_HAD ** 2) / by["st_tW"]["cms_sigma_eff_pb"],
        "VV_2l2v_os + nothing: ATLAS / CMS WW → 2ℓ2ν": by["VV_2l2v_os"]["ratio_atlas_over_cms"],
        "VBF_tautau: ATLAS sum of the 4 filtered pieces / CMS σ(VBF) × BR(ττ)": by["VBF_tautau"]["ratio_atlas_over_cms"],
    }
    out = dict(what="ATLAS background DSID → physics process → CMS sample mapping (27 Oct 2026). ATLAS σ are CROSS-CHECKS only.",
               atlas_source="atlas_bkg_metadata.json (atlasopenmagic, release 2024r-pp)",
               n_dsids=len(used), n_processes=len(rows), rows=rows, like_for_like_checks=extra)
    (HERE / "mapping.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    return out


if __name__ == "__main__":
    o = main()
    from collections import Counter
    print("DSIDs", o["n_dsids"], "processes", o["n_processes"])
    print(Counter(r["cms_status"] for r in o["rows"]))
    print(Counter((r["category"], r["cms_status"]) for r in o["rows"]))
    for r in o["rows"]:
        if r["ratio_atlas_over_cms"] is not None:
            print(f"{r['key']:18s} A={r['atlas_sigma_nominal_pb_CROSSCHECK']:.5g} C={r['cms_sigma_eff_pb']:.5g} "
                  f"ratio={r['ratio_atlas_over_cms']:.3f} {'FLAG' if r['ratio_flag'] else ''}")
    for k, v in o["like_for_like_checks"].items():
        print(f"{k}: {v:.3f}")
