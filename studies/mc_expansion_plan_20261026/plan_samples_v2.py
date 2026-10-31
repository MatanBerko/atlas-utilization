"""The MC expansion sample list after Matan's decisions of 26-31 Oct 2026 (DECISIONS.md).

A plain data module, like plan_samples.py (which is kept unchanged as the 26 Oct plan).
Nothing here is a registry entry and no cross section in this file is decided.
`status`:
  planned  - in the final list (DECISIONS.md), cross section PROPOSED in XSEC_PROPOSALS_v2.md
  on_hold  - no ATLAS nominal counterpart; waiting for Maryna (card kept, not planned)
"""

# (nano recid, short name, group, tier, status, decision that put it here)
SAMPLES_V2 = [
    # Tier 1: W+jets (D1-D3), single top t-channel 4f (D4, D5) and s-channel (D5), tt hadronic
    (69715, "WJetsToLNu_0J_amcatnloFXFX", "a_wjets", 1, "planned", "D1"),
    (69717, "WJetsToLNu_1J_amcatnloFXFX", "a_wjets", 1, "planned", "D1"),
    (69719, "WJetsToLNu_2J_amcatnloFXFX", "a_wjets", 1, "planned", "D1"),
    (64759, "ST_t-channel_top_4f_InclusiveDecays", "b_singletop", 1, "planned", "D4"),
    (64659, "ST_t-channel_antitop_4f_InclusiveDecays", "b_singletop", 1, "planned", "D4"),
    (64635, "ST_s-channel_4f_leptonDecays", "b_singletop", 1, "planned", "D5"),
    (67841, "TTToHadronic", "c_tthad", 1, "planned", "plan"),
    # Tier 2: dibosons (D9) and ZZ -> 2l2nu (D14)
    (72742, "WZTo2Q2L_mllmin4p0", "d_diboson", 2, "planned", "D9"),
    (75573, "ZZTo2Q2L_mllmin4p0", "d_diboson", 2, "planned", "D9"),
    (72738, "WZTo1L1Nu2Q", "d_diboson", 2, "planned", "D9"),
    (72658, "WWTo1L1Nu2Q", "d_diboson", 2, "planned", "D9"),
    (72740, "WZTo1L3Nu", "d_diboson", 2, "planned", "D9"),
    (75567, "ZZTo2L2Nu", "d_diboson", 2, "planned", "D14"),
    # Tier 3: tribosons, ext1 only (D10), and electroweak V + 2 jets (D12)
    (72701, "WWW_4F (ext1)", "e_triboson", 3, "planned", "D10"),
    (72711, "WWZ_4F (ext1)", "e_triboson", 3, "planned", "D10"),
    (72761, "WZZ (ext1)", "e_triboson", 3, "planned", "D10"),
    (75600, "ZZZ (ext1)", "e_triboson", 3, "planned", "D10"),
    (35999, "EWKZ2Jets_ZToLL_M-50", "h_ewk_v2j", 3, "planned", "D12"),
    (35987, "EWKWMinus2Jets_WToLNu_M-50", "h_ewk_v2j", 3, "planned", "D12"),
    (35993, "EWKWPlus2Jets_WToLNu_M-50", "h_ewk_v2j", 3, "planned", "D12"),
    # Tier 4: rare top (D7 for tttt); four samples ON HOLD (no ATLAS nominal counterpart)
    (67645, "ttHTobb_M125 (powheg)", "f_raretop", 4, "planned", "plan"),
    (67691, "ttHToNonbb_M125 (powheg)", "f_raretop", 4, "planned", "plan"),
    (68083, "TTWJetsToQQ", "f_raretop", 4, "planned", "plan"),
    (68045, "TTTT", "f_raretop", 4, "planned", "D7"),
    (68325, "tZq_ll_4f", "f_raretop", 4, "on_hold", "hold"),
    (64873, "ST_tWll_5f", "f_raretop", 4, "on_hold", "D8"),
    (68206, "TTZToQQ", "f_raretop", 4, "on_hold", "hold"),
    (68185, "TTZToLL_M-1to10", "f_raretop", 4, "on_hold", "hold"),
    # Tier 5: Higgs, the 15 planned + 11 new (D13)
    (37474, "GluGluHToWWTo2L2Nu_M-125", "g_higgs", 5, "planned", "D13"),
    (68601, "VBFHToWWTo2L2Nu_M125", "g_higgs", 5, "planned", "D13"),
    (41877, "HWplusJ_HToWW_M-125", "g_higgs", 5, "planned", "D13"),
    (41873, "HWminusJ_HToWW_M-125", "g_higgs", 5, "planned", "D13"),
    (41914, "HZJ_HToWW_M-125 (ext1)", "g_higgs", 5, "planned", "D13"),
    (40095, "GluGluZH_HToWW_ZTo2L_M-125 (ext1)", "g_higgs", 5, "planned", "D13"),
    (37446, "GluGluHToTauTau_M125", "g_higgs", 5, "planned", "D13"),
    (68591, "VBFHToTauTau_M125", "g_higgs", 5, "planned", "D13"),
    (71297, "WplusHToTauTau_M125", "g_higgs", 5, "planned", "D13"),
    (70453, "WminusHToTauTau_M125", "g_higgs", 5, "planned", "D13"),
    (74684, "ZHToTauTau_M125", "g_higgs", 5, "planned", "D13"),
    (37616, "GluGluHToZZTo2L2Nu_M125", "g_higgs", 5, "planned", "D13"),
    (68741, "VBF_HToZZTo2L2Nu_M125", "g_higgs", 5, "planned", "D13"),
    (71227, "WplusH_HToZZTo4L_M125", "g_higgs", 5, "planned", "D13"),
    (70383, "WminusH_HToZZTo4L_M125", "g_higgs", 5, "planned", "D13"),
    (37432, "GluGluHToMuMu_M125", "g_higgs", 5, "planned", "D13"),
    (68571, "VBFHToMuMu_M125", "g_higgs", 5, "planned", "D13"),
    (71295, "WplusHToMuMu_M125", "g_higgs", 5, "planned", "D13"),
    (70451, "WminusHToMuMu_M125", "g_higgs", 5, "planned", "D13"),
    (74682, "ZHToMuMu_M125", "g_higgs", 5, "planned", "D13"),
    (37604, "GluGluHToZG_ZToLL_M-125", "g_higgs", 5, "planned", "D13"),
    (68731, "VBFHToZG_ZToLL_M-125", "g_higgs", 5, "planned", "D13"),
    (71145, "WplusH_HToZG_WToAll_M-125", "g_higgs", 5, "planned", "D13"),
    (70301, "WminusH_HToZG_WToAll_M-125", "g_higgs", 5, "planned", "D13"),
    (74292, "ZH_HToZG_ZToAll_M-125", "g_higgs", 5, "planned", "D13"),
    (40062, "GluGluToZH_HToZZTo4L_M125", "g_higgs", 5, "planned", "D13"),
    # Tier 6: Z -> nunu + jets, HT-binned LO, HT > 100 GeV (D11)
    (74894, "ZJetsToNuNu_HT-100To200", "i_znunu", 6, "planned", "D11"),
    (74898, "ZJetsToNuNu_HT-200To400", "i_znunu", 6, "planned", "D11"),
    (74902, "ZJetsToNuNu_HT-400To600", "i_znunu", 6, "planned", "D11"),
    (74904, "ZJetsToNuNu_HT-600To800", "i_znunu", 6, "planned", "D11"),
    (74906, "ZJetsToNuNu_HT-800To1200", "i_znunu", 6, "planned", "D11"),
    (74896, "ZJetsToNuNu_HT-1200To2500", "i_znunu", 6, "planned", "D11"),
    (74900, "ZJetsToNuNu_HT-2500ToInf", "i_znunu", 6, "planned", "D11"),
]

# The 31 Oct probe: file 0 of every planned sample that was never probed (35 records, in the
# order of the task). Index = PBS array index.
PROBE2 = [64759, 64659, 75567, 35999, 35987, 35993,
          74894, 74898, 74902, 74904, 74906, 74896, 74900,
          41873, 41914, 40095, 68591, 71297, 70453, 74684, 37616, 68741, 71227, 70383,
          37432, 68571, 71295, 70451, 74682, 37604, 68731, 71145, 70301, 74292, 40062]


def by_recid_v2():
    return {r: dict(recid=r, name=n, group=g, tier=t, status=s, decision=d)
            for r, n, g, t, s, d in SAMPLES_V2}
