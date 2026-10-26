"""The recommended MC expansion samples and their alternatives (plan of 26 Oct 2026).

A plain data module: PLAN.md, candidates.json, the probe list and the statistics all read
it. Nothing here is a registry entry: no cross section in this file is decided. Tiers are
the proposed priority order (PLAN.md explains it). `role`:
  recommended  - proposed for the next production, cross section proposed in XSEC_PROPOSALS.md
  alternative  - a competing choice for a decision in PLAN.md ("Decisions for Matan")
  optional     - available and orthogonal, but low value; no cross-section proposal yet
"""

# (nano recid, short name, group, tier, role)
SAMPLES = [
    # Tier 1: the large missing backgrounds that can fake or add leptons (W+jets, single top, tt hadronic)
    (69715, "WJetsToLNu_0J_amcatnloFXFX", "a_wjets", 1, "recommended"),
    (69717, "WJetsToLNu_1J_amcatnloFXFX", "a_wjets", 1, "recommended"),
    (69719, "WJetsToLNu_2J_amcatnloFXFX", "a_wjets", 1, "recommended"),
    (69745, "WJetsToLNu_amcatnloFXFX (inclusive NLO)", "a_wjets", 1, "alternative"),
    (69747, "WJetsToLNu_madgraphMLM (inclusive LO)", "a_wjets", 1, "alternative"),
    (64793, "ST_t-channel_top_5f_InclusiveDecays", "b_singletop", 1, "recommended"),
    (64693, "ST_t-channel_antitop_5f_InclusiveDecays", "b_singletop", 1, "recommended"),
    (64759, "ST_t-channel_top_4f_InclusiveDecays", "b_singletop", 1, "alternative"),
    (64659, "ST_t-channel_antitop_4f_InclusiveDecays", "b_singletop", 1, "alternative"),
    (64635, "ST_s-channel_4f_leptonDecays", "b_singletop", 1, "recommended"),
    (67841, "TTToHadronic", "c_tthad", 1, "recommended"),
    # Tier 2: dibosons with one Z/W decaying to quarks (the leptonic ones are already delivered)
    (72742, "WZTo2Q2L_mllmin4p0", "d_diboson", 2, "recommended"),
    (75573, "ZZTo2Q2L_mllmin4p0", "d_diboson", 2, "recommended"),
    (72738, "WZTo1L1Nu2Q", "d_diboson", 2, "recommended"),
    (72658, "WWTo1L1Nu2Q", "d_diboson", 2, "recommended"),
    (72740, "WZTo1L3Nu", "d_diboson", 2, "recommended"),
    # Tier 3: tribosons (inclusive decays, NLO)
    (72701, "WWW_4F (ext1)", "e_triboson", 3, "recommended"),
    (72711, "WWZ_4F (ext1)", "e_triboson", 3, "recommended"),
    (72761, "WZZ (ext1)", "e_triboson", 3, "recommended"),
    (75600, "ZZZ (ext1)", "e_triboson", 3, "recommended"),
    # Tier 4: rare top
    (68325, "tZq_ll_4f", "f_raretop", 4, "recommended"),
    (64873, "ST_tWll_5f", "f_raretop", 4, "recommended"),
    (67645, "ttHTobb_M125 (powheg)", "f_raretop", 4, "recommended"),
    (67691, "ttHToNonbb_M125 (powheg)", "f_raretop", 4, "recommended"),
    (68206, "TTZToQQ", "f_raretop", 4, "recommended"),
    (68083, "TTWJetsToQQ", "f_raretop", 4, "recommended"),
    (68045, "TTTT", "f_raretop", 4, "recommended"),
    (68185, "TTZToLL_M-1to10", "f_raretop", 4, "recommended"),
    # Tier 5: more Higgs (production modes x decays with leptons)
    (37474, "GluGluHToWWTo2L2Nu_M-125", "g_higgs", 5, "recommended"),
    (68601, "VBFHToWWTo2L2Nu_M125", "g_higgs", 5, "recommended"),
    (41877, "HWplusJ_HToWW_M-125", "g_higgs", 5, "recommended"),
    (41873, "HWminusJ_HToWW_M-125", "g_higgs", 5, "recommended"),
    (41914, "HZJ_HToWW_M-125 (ext1)", "g_higgs", 5, "recommended"),
    (40095, "GluGluZH_HToWW_ZTo2L_M-125 (ext1)", "g_higgs", 5, "recommended"),
    (37446, "GluGluHToTauTau_M125", "g_higgs", 5, "recommended"),
    (68591, "VBFHToTauTau_M125", "g_higgs", 5, "recommended"),
    (71297, "WplusHToTauTau_M125", "g_higgs", 5, "recommended"),
    (70453, "WminusHToTauTau_M125", "g_higgs", 5, "recommended"),
    (74684, "ZHToTauTau_M125", "g_higgs", 5, "recommended"),
    (37616, "GluGluHToZZTo2L2Nu_M125", "g_higgs", 5, "recommended"),
    (68741, "VBF_HToZZTo2L2Nu_M125", "g_higgs", 5, "recommended"),
    (71227, "WplusH_HToZZTo4L_M125", "g_higgs", 5, "recommended"),
    (70383, "WminusH_HToZZTo4L_M125", "g_higgs", 5, "recommended"),
    # optional (available, orthogonal, low value; no proposal yet)
    (64633, "ST_s-channel_4f_hadronicDecays", "b_singletop", 9, "optional"),
    (72678, "WWTo2L2Nu_DoubleScattering", "d_diboson", 9, "optional"),
    (71638, "WpWpJJ_EWK", "d_diboson", 9, "optional"),
    (72728, "WZJJ_EWK_InclusivePolarization", "d_diboson", 9, "optional"),
    (68071, "ttWJetsToLNu_5f_EWK", "f_raretop", 9, "optional"),
    (37678, "GluGluHToZZTo2L2Q_M125", "g_higgs", 9, "optional"),
    (37432, "GluGluHToMuMu_M125", "g_higgs", 9, "optional"),
    (68571, "VBFHToMuMu_M125", "g_higgs", 9, "optional"),
    (71003, "WplusH_HToBB_WToLNu_M-125", "g_higgs", 9, "optional"),
    (70163, "WminusH_HToBB_WToLNu_M-125", "g_higgs", 9, "optional"),
    (74116, "ZH_HToBB_ZToLL_M-125", "g_higgs", 9, "optional"),
    (36595, "ggZH_HToBB_ZToLL_M-125", "g_higgs", 9, "optional"),
    (32783, "bbH_inclusive_M-125_4FS_yb2", "g_higgs", 9, "optional"),
    (37532, "GluGluHToWWToLNuQQ_M-125", "g_higgs", 9, "optional"),
]

# The probe (step 4) reads file 0 of these: every recommended sample of tiers 1-4, the
# W+jets alternatives (needed for the W+jets decision), and four Higgs samples that stand
# for the Higgs generator families (powheg ggH/VBF, powheg-minlo HWJ). At most ~30.
PROBE = [r for r, _, _, t, role in SAMPLES if t <= 4 and role == "recommended"] + \
        [69745, 69747, 37474, 68601, 37446, 41877]


def by_recid():
    return {r: dict(recid=r, name=n, group=g, tier=t, role=role) for r, n, g, t, role in SAMPLES}
