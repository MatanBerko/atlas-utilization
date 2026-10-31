# Cross-section PROPOSALS v2 (31 Oct 2026) — after Matan's decisions

Supersedes `XSEC_PROPOSALS.md` (26 Oct) for the sample list and the normalisation; that file is kept unchanged.
Decisions: `DECISIONS.md`. **Nothing here is applied.** No value enters any registry or config; every value
stays PROPOSED until Matan confirms it. Order = the order of review: tier 1 first.

How to read the labels:
- **unchanged from v1**: the card of `XSEC_PROPOSALS.md` copied as it was (its sources were read on 26 Oct 2026,
  VERIFIED BY RUNNING then); only the ATLAS cross-check line and the decision reference are new.
- **NEW / CHANGED**: every source number re-read on **31 Oct 2026** from the page linked (VERIFIED BY RUNNING: curl
  + text extraction, arXiv numbers from the TeX source); table 'Sources used'.
- Generator values, filter and matching efficiencies: CERN Open Data API, MiniAOD record (VERIFIED BY RUNNING,
  raw copies in `evidence/records/` and `atlas_mapping/cms_records/`). The matching efficiency is shown and **never
  multiplied in** (open point since 15 Oct).
- **DECISION NEEDED**: no decision settles the value; the card lists options with sources and does not choose.
  The σ_eff shown for it is the generator value, as a placeholder for the cost table only.
- ATLAS values (σ × kFactor × genFiltEff, `atlas_mapping/atlas_bkg_metadata.json`, release 2024r-pp) are cross-checks only.
- σ_eff arithmetic: `xsec_proposals_v2.py` (VERIFIED BY RUNNING).

## Summary (review list)

| # | tier | record | sample | status | proposed σ_eff [pb] | decision |
|---:|---:|---|---|---|---:|---|
| 1 | 1 | 69715 | WJetsToLNu_0J_amcatnloFXFX | unchanged from v1 | 49999.6 | D1, D2 |
| 2 | 1 | 69717 | WJetsToLNu_1J_amcatnloFXFX | unchanged from v1 | 8403.31 | D1, D2 |
| 3 | 1 | 69719 | WJetsToLNu_2J_amcatnloFXFX | unchanged from v1 | 3123.8 | D1, D2 |
| 4 | 1 | 64759 | ST_t-channel_top_4f_InclusiveDecays | CHANGED (D4: 4-flavour sample; D5: old Top WG NLO value) | 136.02 | D4, D5 |
| 5 | 1 | 64659 | ST_t-channel_antitop_4f_InclusiveDecays | CHANGED (D4: 4-flavour sample; D5: old Top WG NLO value) | 80.95 | D4, D5 |
| 6 | 1 | 64635 | ST_s-channel_4f_leptonDecays | CHANGED (D5: old Top WG NLO value) | 3.3767 | D5 |
| 7 | 1 | 67841 | TTToHadronic | unchanged from v1 | 378.933 | plan (no decision changed it) |
| 8 | 2 | 72742 | WZTo2Q2L_mllmin4p0 | unchanged from v1 | 7.13263 | D9 |
| 9 | 2 | 75573 | ZZTo2Q2L_mllmin4p0 | unchanged from v1 | 4.31083 | D9 |
| 10 | 2 | 72738 | WZTo1L1Nu2Q | unchanged from v1 | 10.1614 | D9 |
| 11 | 2 | 72658 | WWTo1L1Nu2Q | unchanged from v1 | 52.3623 | D9 |
| 12 | 2 | 72740 | WZTo1L3Nu | unchanged from v1 | 3.78876 | D9 |
| 13 | 2 | 75567 | ZZTo2L2Nu | NEW (D14) | 1.13487 | D14 (conditional), D9 |
| 14 | 3 | 72701 | WWW_4F (ext1) | unchanged from v1 | 0.2158 | D10 |
| 15 | 3 | 72711 | WWZ_4F (ext1) | unchanged from v1 | 0.1707 | D10 |
| 16 | 3 | 72761 | WZZ (ext1) | unchanged from v1 | 0.05709 | D10 |
| 17 | 3 | 75600 | ZZZ (ext1) | unchanged from v1 | 0.01476 | D10 |
| 18 | 3 | 35999 | EWKZ2Jets_ZToLL_M-50 | NEW (D12) — DECISION NEEDED on the value | options | D12 |
| 19 | 3 | 35987 | EWKWMinus2Jets_WToLNu_M-50 | NEW (D12) — DECISION NEEDED on the value | options | D12 |
| 20 | 3 | 35993 | EWKWPlus2Jets_WToLNu_M-50 | NEW (D12) — DECISION NEEDED on the value | options | D12 |
| 21 | 4 | 67645 | ttHTobb_M125 (powheg) | unchanged from v1 | 0.295335 | plan |
| 22 | 4 | 67691 | ttHToNonbb_M125 (powheg) | unchanged from v1 | 0.211765 | plan |
| 23 | 4 | 68083 | TTWJetsToQQ | unchanged from v1 | 0.4375 | plan |
| 24 | 4 | 68045 | TTTT | CHANGED (D7) | 0.01197 | D7 |
| 25 | 4 | 68325 | tZq_ll_4f | ON HOLD — card kept unchanged from v1, not for review now | 0.07561 | ON HOLD (D8 / no ATLAS nominal counterpart; waiting for Maryna) |
| 26 | 4 | 64873 | ST_tWll_5f | ON HOLD — card kept unchanged from v1, not for review now | 0.01105 | ON HOLD (D8 / no ATLAS nominal counterpart; waiting for Maryna) |
| 27 | 4 | 68206 | TTZToQQ | ON HOLD — card kept unchanged from v1, not for review now | 0.5113 | ON HOLD (D8 / no ATLAS nominal counterpart; waiting for Maryna) |
| 28 | 4 | 68185 | TTZToLL_M-1to10 | ON HOLD — card kept unchanged from v1, not for review now | 0.0537 | ON HOLD (D8 / no ATLAS nominal counterpart; waiting for Maryna) |
| 29 | 5 | 37474 | GluGluHToWWTo2L2Nu_M-125 | unchanged from v1 | 1.11145 | D13 (planned 15) |
| 30 | 5 | 68601 | VBFHToWWTo2L2Nu_M125 | unchanged from v1 | 0.0865272 | D13 (planned 15) |
| 31 | 5 | 41877 | HWplusJ_HToWW_M-125 | unchanged from v1 | 0.179508 | D13 (planned 15) |
| 32 | 5 | 41873 | HWminusJ_HToWW_M-125 | unchanged from v1 | 0.113859 | D13 (planned 15) |
| 33 | 5 | 41914 | HZJ_HToWW_M-125 (ext1) | unchanged from v1 | 0.162668 | D13 (planned 15) |
| 34 | 5 | 40095 | GluGluZH_HToWW_ZTo2L_M-125 (ext1) | unchanged from v1 | 0.00264806 | D13 (planned 15) |
| 35 | 5 | 37446 | GluGluHToTauTau_M125 | unchanged from v1 | 3.04694 | D13 (planned 15) |
| 36 | 5 | 68591 | VBFHToTauTau_M125 | unchanged from v1 | 0.237207 | D13 (planned 15) |
| 37 | 5 | 71297 | WplusHToTauTau_M125 | unchanged from v1 | 0.0526848 | D13 (planned 15) |
| 38 | 5 | 70453 | WminusHToTauTau_M125 | unchanged from v1 | 0.0334172 | D13 (planned 15) |
| 39 | 5 | 74684 | ZHToTauTau_M125 | unchanged from v1 | 0.0477425 | D13 (planned 15) |
| 40 | 5 | 37616 | GluGluHToZZTo2L2Nu_M125 | unchanged from v1 | 0.0342475 | D13 (planned 15) |
| 41 | 5 | 68741 | VBF_HToZZTo2L2Nu_M125 | unchanged from v1 | 0.0026662 | D13 (planned 15) |
| 42 | 5 | 71227 | WplusH_HToZZTo4L_M125 | unchanged from v1 | 0.00023058 | D13 (planned 15) |
| 43 | 5 | 70383 | WminusH_HToZZTo4L_M125 | unchanged from v1 | 0.000146254 | D13 (planned 15) |
| 44 | 5 | 37432 | GluGluHToMuMu_M125 | NEW (D13) | 0.010571 | D13 |
| 45 | 5 | 68571 | VBFHToMuMu_M125 | NEW (D13) | 0.000822963 | D13 |
| 46 | 5 | 71295 | WplusHToMuMu_M125 | NEW (D13) | 0.000182784 | D13 |
| 47 | 5 | 70451 | WminusHToMuMu_M125 | NEW (D13) | 0.000115937 | D13 |
| 48 | 5 | 74682 | ZHToMuMu_M125 | NEW (D13) | 0.000165637 | D13 |
| 49 | 5 | 37604 | GluGluHToZG_ZToLL_M-125 | NEW (D13) | 0.00752104 | D13 |
| 50 | 5 | 68731 | VBFHToZG_ZToLL_M-125 | NEW (D13) | 0.00058552 | D13 |
| 51 | 5 | 71145 | WplusH_HToZG_WToAll_M-125 | NEW (D13) | 0.00128772 | D13 |
| 52 | 5 | 70301 | WminusH_HToZG_WToAll_M-125 | NEW (D13) | 0.000816782 | D13 |
| 53 | 5 | 74292 | ZH_HToZG_ZToAll_M-125 | NEW (D13) | 0.00116692 | D13 |
| 54 | 5 | 40062 | GluGluToZH_HToZZTo4L_M125 | NEW (D13) — DECISION NEEDED on the value | options | D13 |
| 55 | 6 | 74894 | ZJetsToNuNu_HT-100To200 | NEW (D11) — DECISION NEEDED on the value | options | D11 |
| 56 | 6 | 74898 | ZJetsToNuNu_HT-200To400 | NEW (D11) — DECISION NEEDED on the value | options | D11 |
| 57 | 6 | 74902 | ZJetsToNuNu_HT-400To600 | NEW (D11) — DECISION NEEDED on the value | options | D11 |
| 58 | 6 | 74904 | ZJetsToNuNu_HT-600To800 | NEW (D11) — DECISION NEEDED on the value | options | D11 |
| 59 | 6 | 74906 | ZJetsToNuNu_HT-800To1200 | NEW (D11) — DECISION NEEDED on the value | options | D11 |
| 60 | 6 | 74896 | ZJetsToNuNu_HT-1200To2500 | NEW (D11) — DECISION NEEDED on the value | options | D11 |
| 61 | 6 | 74900 | ZJetsToNuNu_HT-2500ToInf | NEW (D11) — DECISION NEEDED on the value | options | D11 |

## Sources used

| key | link | where | as printed |
|---|---|---|---|
| ATLAS_W | <https://arxiv.org/abs/1603.09222> | ATLAS, PLB 759 (2016) 601, Table 3, row 'W±', 'Predicted ... Total' (DYNNLO NNLO QCD + NLO EW, CT14nnlo; per lepton flavour) | 20.08 nb |
| JHUGEN_SRC | <https://raw.githubusercontent.com/JHUGen/JHUGen/master/JHUGenerator/main.F90> | comment block lines 357-368 and help text line 7269 (JHUGen master, read 31 Oct 2026; the sample used v7.2.3, assumed equivalent: UNVERIFIED for that version) | DecayMode=8: Z --> l+ l- (l=e,mu,tau); 9: Z --> anything; 'WriteFailedEvents: Write events that fail in the LHE file, but with a weight of 0' |
| PDG_W | <https://pdglive.lbl.gov/Particle.action?node=S043> | W DECAY MODES Γ2 e+ν, Γ3 μ+ν, Γ4 τ+ν, Γ5 hadrons (re-read 31 Oct 2026) | (10.71 ± 0.16) %, (10.63 ± 0.15) %, (11.38 ± 0.21) %, (67.41 ± 0.27) % |
| PDG_Z | <https://pdglive.lbl.gov/Particle.action?node=S044> | Z DECAY MODES Γ1 e+e−, Γ2 μ+μ−, Γ3 τ+τ−, Γ7 invisible, Γ8 hadrons (re-read 31 Oct 2026, D6) | (3.3632 ± 0.0042) %, (3.3662 ± 0.0066) %, (3.3696 ± 0.0083) %, (20.000 ± 0.055) %, (69.911 ± 0.056) % |
| POWHEG_ZZ | <https://arxiv.org/abs/1311.1365> | Nason & Zanderighi, 'W+W−, WZ and ZZ production in the POWHEG-BOX-V2', §1 (TeX source, read 31 Oct 2026) | 'Singly resonant contributions and interference effects were included, and in fact all diagrams relevant to the production of four leptons were accounted for, with the exception of interference effects between W+W− and ZZ' |
| RAZOR | <https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat> | line 64, under '#13 TeV Spring 15 MC' (SECONDARY source; same table as our DY 1921.8*3, line 90) | WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7 |
| RAZOR_DY | <https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat> | line 90 (the value our delivered DY M-50 uses); re-read 31 Oct 2026 | DYJetsToLL_M-50_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 1921.8*3 |
| RAZOR_ZNN | <https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat> | lines 96-103, 'ZJetsToNuNu_HT-<bin>_13TeV-madgraph <LO>*1.23' (SECONDARY source; older CUETP8M1 samples; the origin of 1.23 is not stated in the file); re-read 31 Oct 2026 | e.g. line 96: ZJetsToNuNu_HT-100To200_13TeV-madgraph 280.35*1.23 |
| SHERPA_MAN | <https://sherpa.hepforge.org/doc/SHERPA-MC-2.2.11.html> | Sherpa 2.2.11 manual §5.6.14 (read 31 Oct 2026) | 'Min_N_TChannels: Limits the minimum number of t-channel propagators in the process to the given value.' |
| SMP16018 | <https://arxiv.org/abs/1712.09814> | CMS SMP-16-018 (EW Z + 2 jets, 13 TeV 2016), §2 and abstract: region m(ℓℓ) > 50, pT(j) > 25, m(jj) > 120 GeV, ℓ = e or μ; LO MadGraph prediction and measurement; text: 'agreement within 5 % with the NLO predictions of vbfnlo'; read from the arXiv TeX source 31 Oct 2026 | σ_LO = 543 +7 −9 (scale) ± 22 (PDF) fb; measured 534 ± 20 (stat) ± 57 (syst) fb |
| SMP17011 | <https://arxiv.org/abs/1903.04040> | CMS SMP-17-011 (EW W + 2 jets, 13 TeV 2016), §2 and §8: region pT(j) > 25, m(jj) > 120 GeV; LO 'for the ℓνjj final state (with ℓ = e, μ or τ)'; measurement 'per channel'; text: 'in agreement within 2-5 % with the NLO predictions of vbfnlo'; read from the arXiv TeX source 31 Oct 2026 | σ_LO = 6.81 +0.03 −0.06 (scale) ± 0.26 (PDF) pb; measured 6.23 ± 0.12 (stat) ± 0.61 (syst) pb |
| ST_NLO_S | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec> | section 'Single-top s channel cross sections', 13 TeV table, rows 'top' / 'anti-top' / 'top + anti-top', column 'Central value' (re-read 31 Oct 2026) | 6.35 / 3.97 / 10.32 |
| ST_NLO_T | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec> | section 'Single-top t channel cross sections (superseded)', 13 TeV table, rows 'top' / 'anti-top', column 'Central value' (Hathor NLO; page rev. r36, 2022-12-06; re-read 31 Oct 2026) | 136.02 / 80.95 |
| ST_NNLO_S | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef> | section 'Single-top-quark s channel cross-sections', 13 TeV table, rows 'top quark' / 'top antiquark' / 'top quark + antiquark' (NNLO, Liu & Gao arXiv:1807.03835) | 6.828 / 4.245 / 11.073 |
| ST_NNLO_T | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef> | section 'Single top-quark t channel cross-sections', 13 TeV table, rows 'top quark' / 'top antiquark' (MCFM NNLO, mt = 172.5 GeV, page dated 2026-10-02) | 134.2 / 80.0 |
| TTBAR | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/TtbarNNLO> | table 'Updated reference cross sections ...' (Updated: July 2022), block '13 TeV', column 'Central value' | 833.9 |
| TTTT_NLL | <https://arxiv.org/abs/2212.03259> | Table I, √s = 13 TeV, NLO(QCD+EW)+NLL′ (µ0 = 2 mt) | 14.65(2) fb |
| TTTT_NLO | <https://arxiv.org/abs/1711.02116> | Table 5 (TeX label table:4t), row µ = HT/4, column 'LO + NLO' (complete NLO QCD+EW); re-read from the arXiv TeX source 31 Oct 2026 | 11.97 (+18 % −21 %) fb |
| WW | <https://arxiv.org/abs/1408.5243> | Table I (on-shell W+W−, 4FNS, includes gg → WW), row 13: σNNLO | 118.7 pb |
| WZ | <https://arxiv.org/abs/1604.08576> | Table 1 (on-shell W±Z), row √s = 13: σNLO, σNNLO | 46.068(3) pb, 51.11(3) pb |
| YR4_BR | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR> | rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) | bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04 |
| YR4_BR2 | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR> | rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026 | μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02 |
| YR4_XS | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV> | rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 | ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb) |
| ZZ | <https://arxiv.org/abs/1405.2219> | Table 1 (inclusive ZZ, includes gg → ZZ at NNLO), row 13: σNLO, σNNLO | 14.51 pb, 16.91 pb |

# Tier 1

## 1. 69715 WJetsToLNu_0J_amcatnloFXFX — tier 1 — unchanged from v1

- **What it is:** W boson decaying to a charged lepton (e, μ or τ) and a neutrino, with exactly 0 extra parton(s) in the NLO matrix element (one of three pieces that together make all of W+jets).
- **Dataset:** `/WJetsToLNu_0J_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 69714; <https://opendata.cern.ch/record/69715>)
- **Proposed σ_eff = 49999.6 pb** = 53300 × 0.938079

  - generator σ (portal, 0J piece): **53300** — portal API <https://opendata.cern.ch/api/records/69714> metadata.cross_section.total_value
  - k = 61526.7 / (53300 + 8958 + 3330), NNLO inclusive ÷ sum of the three NLO pieces: **0.938079** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat — line 64, under '#13 TeV Spring 15 MC' (SECONDARY source; same table as our DY 1921.8*3, line 90) — as printed: WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7

- **Order:** NLO generator × NNLO/NLO k-factor (inclusive W → ℓν, FEWZ NNLO in the table).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.9 (not multiplied in); total_value = 5.330e+04 pb, negative-weight fraction = 9.888e-02 (<https://opendata.cern.ch/api/records/69714>).
- **Proposed / generator:** 0.9381
- **What Matan should open and look for:** RazorAnalyzer xSections.dat line 64: 'WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7'. The three portal values on the MiniAOD records 69714 / 69716 / 69718 (metadata.cross_section.total_value).
- **Decision / convention:** D1, D2 — No published total for a jet-multiplicity piece → generator × k-factor. The k-factor numerator is the same SECONDARY table as our DY (Matan, 15 Oct), for consistency. Not a paper table, so the 'k-factor from a paper table' rule is only partly met.
- **Alternatives (effect on σ_eff):** k from the inclusive NLO sample instead (61526.7 / 66970) → -2.1 %; primary source instead: ATLAS 1603.09222 Table 3, 3 × 20.08 nb = 60240 pb → -2.1 %
- **ATLAS cross-check:** No ATLAS sample per jet piece. Whole W → ℓν: ATLAS 700338-700349 = 65395 pb vs CMS 61,526.7 pb → ATLAS/CMS = 1.063 (MAPPING.md table A). D2's primary cross-check, ATLAS arXiv:1603.09222 Table 3 (3 × 20.08 nb = 60,240 pb), is −2.1 %.
- **Note:** Portal matching efficiencies 0.9 / 0.2 / 0.1 are shown but NOT multiplied in. The three portal values add up to 65588 pb, close to the inclusive NLO sample's 66970 pb, which suggests total_value already includes the matching efficiency (if it did not, the pieces would sum to 50095 pb). Also, the inclusive NLO value 66970 pb × 0.4 = 26788 pb would be less than half of every W → ℓν prediction and measurement (ATLAS measured 3 × 20.64 nb), so for this record total_value must already include the matching efficiency. Evidence for the open point, not a decision.

## 2. 69717 WJetsToLNu_1J_amcatnloFXFX — tier 1 — unchanged from v1

- **What it is:** W boson decaying to a charged lepton (e, μ or τ) and a neutrino, with exactly 1 extra parton(s) in the NLO matrix element (one of three pieces that together make all of W+jets).
- **Dataset:** `/WJetsToLNu_1J_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 69716; <https://opendata.cern.ch/record/69717>)
- **Proposed σ_eff = 8403.31 pb** = 8958 × 0.938079

  - generator σ (portal, 1J piece): **8958** — portal API <https://opendata.cern.ch/api/records/69716> metadata.cross_section.total_value
  - k = 61526.7 / (53300 + 8958 + 3330), NNLO inclusive ÷ sum of the three NLO pieces: **0.938079** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat — line 64, under '#13 TeV Spring 15 MC' (SECONDARY source; same table as our DY 1921.8*3, line 90) — as printed: WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7

- **Order:** NLO generator × NNLO/NLO k-factor (inclusive W → ℓν, FEWZ NNLO in the table).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.2 (not multiplied in); total_value = 8.958e+03 pb, negative-weight fraction = 2.574e-01 (<https://opendata.cern.ch/api/records/69716>).
- **Proposed / generator:** 0.9381
- **What Matan should open and look for:** RazorAnalyzer xSections.dat line 64: 'WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7'. The three portal values on the MiniAOD records 69714 / 69716 / 69718 (metadata.cross_section.total_value).
- **Decision / convention:** D1, D2 — No published total for a jet-multiplicity piece → generator × k-factor. The k-factor numerator is the same SECONDARY table as our DY (Matan, 15 Oct), for consistency. Not a paper table, so the 'k-factor from a paper table' rule is only partly met.
- **Alternatives (effect on σ_eff):** k from the inclusive NLO sample instead (61526.7 / 66970) → -2.1 %; primary source instead: ATLAS 1603.09222 Table 3, 3 × 20.08 nb = 60240 pb → -2.1 %
- **ATLAS cross-check:** No ATLAS sample per jet piece. Whole W → ℓν: ATLAS 700338-700349 = 65395 pb vs CMS 61,526.7 pb → ATLAS/CMS = 1.063 (MAPPING.md table A). D2's primary cross-check, ATLAS arXiv:1603.09222 Table 3 (3 × 20.08 nb = 60,240 pb), is −2.1 %.
- **Note:** Portal matching efficiencies 0.9 / 0.2 / 0.1 are shown but NOT multiplied in. The three portal values add up to 65588 pb, close to the inclusive NLO sample's 66970 pb, which suggests total_value already includes the matching efficiency (if it did not, the pieces would sum to 50095 pb). Also, the inclusive NLO value 66970 pb × 0.4 = 26788 pb would be less than half of every W → ℓν prediction and measurement (ATLAS measured 3 × 20.64 nb), so for this record total_value must already include the matching efficiency. Evidence for the open point, not a decision.

## 3. 69719 WJetsToLNu_2J_amcatnloFXFX — tier 1 — unchanged from v1

- **What it is:** W boson decaying to a charged lepton (e, μ or τ) and a neutrino, with exactly 2 extra parton(s) in the NLO matrix element (one of three pieces that together make all of W+jets).
- **Dataset:** `/WJetsToLNu_2J_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 69718; <https://opendata.cern.ch/record/69719>)
- **Proposed σ_eff = 3123.8 pb** = 3330 × 0.938079

  - generator σ (portal, 2J piece): **3330** — portal API <https://opendata.cern.ch/api/records/69718> metadata.cross_section.total_value
  - k = 61526.7 / (53300 + 8958 + 3330), NNLO inclusive ÷ sum of the three NLO pieces: **0.938079** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat — line 64, under '#13 TeV Spring 15 MC' (SECONDARY source; same table as our DY 1921.8*3, line 90) — as printed: WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7

- **Order:** NLO generator × NNLO/NLO k-factor (inclusive W → ℓν, FEWZ NNLO in the table).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.1 (not multiplied in); total_value = 3.330e+03 pb, negative-weight fraction = 3.439e-01 (<https://opendata.cern.ch/api/records/69718>).
- **Proposed / generator:** 0.9381
- **What Matan should open and look for:** RazorAnalyzer xSections.dat line 64: 'WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7'. The three portal values on the MiniAOD records 69714 / 69716 / 69718 (metadata.cross_section.total_value).
- **Decision / convention:** D1, D2 — No published total for a jet-multiplicity piece → generator × k-factor. The k-factor numerator is the same SECONDARY table as our DY (Matan, 15 Oct), for consistency. Not a paper table, so the 'k-factor from a paper table' rule is only partly met.
- **Alternatives (effect on σ_eff):** k from the inclusive NLO sample instead (61526.7 / 66970) → -2.1 %; primary source instead: ATLAS 1603.09222 Table 3, 3 × 20.08 nb = 60240 pb → -2.1 %
- **ATLAS cross-check:** No ATLAS sample per jet piece. Whole W → ℓν: ATLAS 700338-700349 = 65395 pb vs CMS 61,526.7 pb → ATLAS/CMS = 1.063 (MAPPING.md table A). D2's primary cross-check, ATLAS arXiv:1603.09222 Table 3 (3 × 20.08 nb = 60,240 pb), is −2.1 %.
- **Note:** Portal matching efficiencies 0.9 / 0.2 / 0.1 are shown but NOT multiplied in. The three portal values add up to 65588 pb, close to the inclusive NLO sample's 66970 pb, which suggests total_value already includes the matching efficiency (if it did not, the pieces would sum to 50095 pb). Also, the inclusive NLO value 66970 pb × 0.4 = 26788 pb would be less than half of every W → ℓν prediction and measurement (ATLAS measured 3 × 20.64 nb), so for this record total_value must already include the matching efficiency. Evidence for the open point, not a decision.

## 4. 64759 ST_t-channel_top_4f_InclusiveDecays — tier 1 — CHANGED (D4: 4-flavour sample; D5: old Top WG NLO value)

- **What it is:** Single top production in the t-channel, 4-flavour scheme (POWHEG + MadSpin), all top decays.
- **Dataset:** `/ST_t-channel_top_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 64758; <https://opendata.cern.ch/record/64759>)
- **Proposed σ_eff = 136.02 pb** = 136.02

  - σ(t-channel top), Hathor NLO: **136.02** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec — section 'Single-top t channel cross sections (superseded)', 13 TeV table, rows 'top' / 'anti-top', column 'Central value' (Hathor NLO; page rev. r36, 2022-12-06; re-read 31 Oct 2026) — as printed: 136.02 / 80.95

- **Order:** NLO QCD (Hathor), 13 TeV, mt = 172.5 GeV.
- **k-factor and source:** none (the sample is normalised to the total directly).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 1.134e+02 pb, negative-weight fraction = 3.161e-02 (<https://opendata.cern.ch/api/records/64758>).
- **Proposed / generator:** 1.1995
- **What Matan should open and look for:** SingleTopRefXsec, section 'Single-top t channel cross sections (superseded)', 13 TeV table, row 'top', Central value = 136.02. (The section is marked 'superseded' on the page; D5 uses it on purpose, to match ATLAS.)
- **Decision / convention:** D4, D5 — D5: match ATLAS = the OLD Top WG page throughout.
- **Alternatives (effect on σ_eff):** SingleTopNNLORef NNLO 134.2 pb (recorded alternative, D5) → -1.3 %; generator value (portal) → -16.6 %
- **ATLAS cross-check:** ATLAS 410658 (leptonic top decays only, four-flavour): σ×k = 44.155 pb. Like-for-like with our PDG W BR: 44.155 / (136.02 × 0.3272) = 0.992; with ATLAS's own implied BR 0.3246: 1.000.
- **Note:** Card (evidence/cards/64759): MadSpin decays the top inclusively. Probe 31 Oct: all 42 branches present.

## 5. 64659 ST_t-channel_antitop_4f_InclusiveDecays — tier 1 — CHANGED (D4: 4-flavour sample; D5: old Top WG NLO value)

- **What it is:** Single antitop production in the t-channel, 4-flavour scheme (POWHEG + MadSpin), all top decays.
- **Dataset:** `/ST_t-channel_antitop_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 64658; <https://opendata.cern.ch/record/64659>)
- **Proposed σ_eff = 80.95 pb** = 80.95

  - σ(t-channel antitop), Hathor NLO: **80.95** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec — section 'Single-top t channel cross sections (superseded)', 13 TeV table, rows 'top' / 'anti-top', column 'Central value' (Hathor NLO; page rev. r36, 2022-12-06; re-read 31 Oct 2026) — as printed: 136.02 / 80.95

- **Order:** NLO QCD (Hathor), 13 TeV, mt = 172.5 GeV.
- **k-factor and source:** none (the sample is normalised to the total directly).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 6.793e+01 pb, negative-weight fraction = 2.929e-02 (<https://opendata.cern.ch/api/records/64658>).
- **Proposed / generator:** 1.1917
- **What Matan should open and look for:** SingleTopRefXsec, section 'Single-top t channel cross sections (superseded)', 13 TeV table, row 'anti-top', Central value = 80.95. (The section is marked 'superseded' on the page; D5 uses it on purpose, to match ATLAS.)
- **Decision / convention:** D4, D5 — D5: match ATLAS = the OLD Top WG page throughout.
- **Alternatives (effect on σ_eff):** SingleTopNNLORef NNLO 80.0 pb (recorded alternative, D5) → -1.2 %; generator value (portal) → -16.1 %
- **ATLAS cross-check:** ATLAS 410659 (leptonic top decays only, four-flavour): σ×k = 26.273 pb. Like-for-like with our PDG W BR: 26.273 / (80.95 × 0.3272) = 0.992; with ATLAS's own implied BR 0.3246: 1.000.
- **Note:** Card (evidence/cards/64659): MadSpin decays the top inclusively. Probe 31 Oct: all 42 branches present.

## 6. 64635 ST_s-channel_4f_leptonDecays — tier 1 — CHANGED (D5: old Top WG NLO value)

- **What it is:** Single top (or antitop) in the s-channel, top → b W, W → ℓν (ℓ = e, μ, τ).
- **Dataset:** `/ST_s-channel_4f_leptonDecays_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 64634; <https://opendata.cern.ch/record/64635>)
- **Proposed σ_eff = 3.3767 pb** = 10.32 × 0.3272

  - σ(s-channel, top + antitop), Hathor NLO: **10.32** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec — section 'Single-top s channel cross sections', 13 TeV table, rows 'top' / 'anti-top' / 'top + anti-top', column 'Central value' (re-read 31 Oct 2026) — as printed: 6.35 / 3.97 / 10.32
  - BR(W → ℓν) = 0.1071 + 0.1063 + 0.1138 (BR(t → Wb) = 1 assumed): **0.3272** — https://pdglive.lbl.gov/Particle.action?node=S043 — W DECAY MODES Γ2 e+ν, Γ3 μ+ν, Γ4 τ+ν, Γ5 hadrons (re-read 31 Oct 2026) — as printed: (10.71 ± 0.16) %, (10.63 ± 0.15) %, (11.38 ± 0.21) %, (67.41 ± 0.27) %

- **Order:** NLO QCD (Hathor).
- **k-factor and source:** none.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 3.549e+00 pb, negative-weight fraction = 1.744e-01 (<https://opendata.cern.ch/api/records/64634>).
- **Proposed / generator:** 0.9515
- **What Matan should open and look for:** SingleTopRefXsec, 's channel' 13 TeV table, row 'top + anti-top' = 10.32. pdglive S043: Γ2, Γ3, Γ4.
- **Decision / convention:** D5 — D5 (old page) × settled PDG individual W branching ratios.
- **Alternatives (effect on σ_eff):** SingleTopNNLORef NNLO 11.073 × 0.3272 (recorded alternative, D5) → +7.3 %; ATLAS's implied leptonic BR 0.3246 instead of 0.3272 → -0.8 %; generator value 3.549 pb (portal) → +5.1 %
- **ATLAS cross-check:** ATLAS 410644 + 410645 (leptonic): 3.3500 pb → ATLAS/CMS = 0.992 (= 0.3246 / 0.3272).
- **Note:** BR arithmetic: 0.1071 + 0.1063 + 0.1138 = 0.3272; 10.32 × 0.3272 = 3.3767 pb. Card (evidence/cards/64635): 'decay t > w+ b, w+ > ell+ vl' with ell = e, μ, τ.

## 7. 67841 TTToHadronic — tier 1 — unchanged from v1

- **What it is:** Top-quark pairs with both W bosons decaying to quarks.
- **Dataset:** `/TTToHadronic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 67840; <https://opendata.cern.ch/record/67841>)
- **Proposed σ_eff = 378.933 pb** = 833.9 × 0.454411

  - σ(tt̄), NNLO+NNLL, mt = 172.5 GeV: **833.9** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/TtbarNNLO — table 'Updated reference cross sections ...' (Updated: July 2022), block '13 TeV', column 'Central value' — as printed: 833.9
  - BR(W → hadrons)²: **0.454411** — https://pdglive.lbl.gov/Particle.action?node=S043 — W DECAY MODES Γ2 e+ν, Γ3 μ+ν, Γ4 τ+ν, Γ5 hadrons (re-read 31 Oct 2026) — as printed: (10.71 ± 0.16) %, (10.63 ± 0.15) %, (11.38 ± 0.21) %, (67.41 ± 0.27) %

- **Order:** NNLO+NNLL.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 6.871e+02 pb, negative-weight fraction = 4.038e-03 (<https://opendata.cern.ch/api/records/67840>).
- **Proposed / generator:** 0.5515
- **What Matan should open and look for:** TtbarNNLO: the 13 TeV block of the first table, 'Central value' = 833.9. pdglive S043: the four W decay fractions.
- **Decision / convention:** plan (no decision changed it) — Settled convention (833.9 pb × 0.6741², as in the hint).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS 410471 (all-hadronic): 379.4 pb → ATLAS/CMS = 1.001.
- **Note:** With the individual PDG values the three tt̄ samples add up to 0.10706 + 0.44113 + 0.45441 = 1.0026 of tt̄ (the PDG W fractions sum to 1.0013). A +0.26 % overcount of tt̄ that follows from the settled convention; reported, not changed.

# Tier 2

## 8. 72742 WZTo2Q2L_mllmin4p0 — tier 2 — unchanged from v1

- **What it is:** W → quarks plus a lepton pair (e, μ, τ; Z or virtual photon, m(ℓℓ) > 4 GeV), NLO, 0-1 extra parton.
- **Dataset:** `/WZTo2Q2L_mllmin4p0_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 72741; <https://opendata.cern.ch/record/72742>)
- **Proposed σ_eff = 7.13263 pb** = 6.429 × 1.10945

  - generator σ (portal): **6.429** — portal API <https://opendata.cern.ch/api/records/72741> metadata.cross_section.total_value
  - k = 51.11 / 46.068 (WZ NNLO/NLO): **1.10945** — https://arxiv.org/abs/1604.08576 — Table 1 (on-shell W±Z), row √s = 13: σNLO, σNNLO — as printed: 46.068(3) pb, 51.11(3) pb

- **Order:** NLO generator × NNLO/NLO k-factor.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.7 (not multiplied in); total_value = 6.429e+00 pb, negative-weight fraction = 1.882e-01 (<https://opendata.cern.ch/api/records/72741>).
- **Proposed / generator:** 1.1094
- **What Matan should open and look for:** arXiv:1604.08576 Table 1, row 13: σNLO 46.068, σNNLO 51.11. The portal value on the MiniAOD record.
- **Decision / convention:** D9 — Phase space (γ* included, m(ℓℓ) > 4) matches no published total → generator × k-factor, exactly as our WZTo3LNu 72752.
- **Alternatives (effect on σ_eff):** on-shell WZ instead: 51.11 × 0.6741 × 0.10099 → -51.2 %
- **ATLAS cross-check:** ATLAS 700492 = 3.305 pb → ATLAS/CMS = 0.463: different phase space (CMS includes γ* → ℓℓ down to m(ℓℓ) = 4 GeV). E1 applies: ATLAS uses Sherpa generator values with kFactor = 1 and has no gg → VV samples; the CMS NNLO total includes the loop-induced gg part.
- **Note:** Approximation as for 72752: an on-shell k-factor applied to a sample that also contains γ* → ℓℓ. Card: 'p p > V ell+ ell-', V = W, 'decay w+ > q q'.

## 9. 75573 ZZTo2Q2L_mllmin4p0 — tier 2 — unchanged from v1

- **What it is:** Z → quarks plus a lepton pair (e, μ, τ; m(ℓℓ) > 4 GeV), NLO, 0-1 extra parton.
- **Dataset:** `/ZZTo2Q2L_mllmin4p0_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 75572; <https://opendata.cern.ch/record/75573>)
- **Proposed σ_eff = 4.31083 pb** = 3.699 × 1.1654

  - generator σ (portal): **3.699** — portal API <https://opendata.cern.ch/api/records/75572> metadata.cross_section.total_value
  - k = 16.91 / 14.51 (ZZ NNLO/NLO, includes gg → ZZ): **1.1654** — https://arxiv.org/abs/1405.2219 — Table 1 (inclusive ZZ, includes gg → ZZ at NNLO), row 13: σNLO, σNNLO — as printed: 14.51 pb, 16.91 pb

- **Order:** NLO generator × NNLO/NLO k-factor.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.7 (not multiplied in); total_value = 3.699e+00 pb, negative-weight fraction = 1.761e-01 (<https://opendata.cern.ch/api/records/75572>).
- **Proposed / generator:** 1.1654
- **What Matan should open and look for:** arXiv:1405.2219 Table 1, row 13: 14.51 and 16.91. The portal value on the MiniAOD record.
- **Decision / convention:** D9 — Same as our ZZTo4L 75589.
- **Alternatives (effect on σ_eff):** on-shell ZZ instead: 16.91 × 2 × 0.10099 × 0.69911 → -44.6 %
- **ATLAS cross-check:** ATLAS 700493 + 700494 = 2.127 pb → ATLAS/CMS = 0.493: different phase space (γ* down to 4 GeV on the CMS side). E1 applies: ATLAS uses Sherpa generator values with kFactor = 1 and has no gg → VV samples; the CMS NNLO total includes the loop-induced gg part.
- **Note:** The k-factor includes gg → ZZ; no gg → ZZ → 2ℓ2q sample is proposed, so nothing is counted twice.

## 10. 72738 WZTo1L1Nu2Q — tier 2 — unchanged from v1

- **What it is:** W → ℓν (e, μ, τ) with Z → quarks, NLO, 0-1 extra parton.
- **Dataset:** `/WZTo1L1Nu2Q_4f_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 72737; <https://opendata.cern.ch/record/72738>)
- **Proposed σ_eff = 10.1614 pb** = 9.159 × 1.10945

  - generator σ (portal): **9.159** — portal API <https://opendata.cern.ch/api/records/72737> metadata.cross_section.total_value
  - k = 51.11 / 46.068: **1.10945** — https://arxiv.org/abs/1604.08576 — Table 1 (on-shell W±Z), row √s = 13: σNLO, σNNLO — as printed: 46.068(3) pb, 51.11(3) pb

- **Order:** NLO generator × NNLO/NLO k-factor.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.6 (not multiplied in); total_value = 9.159e+00 pb, negative-weight fraction = 2.116e-01 (<https://opendata.cern.ch/api/records/72737>).
- **Proposed / generator:** 1.1094
- **What Matan should open and look for:** arXiv:1604.08576 Table 1, row 13: σNLO 46.068, σNNLO 51.11. The portal value on the MiniAOD record.
- **Decision / convention:** D9 — Generator × k-factor, as 72752.
- **Alternatives (effect on σ_eff):** on-shell WZ instead: 51.11 × 0.3272 × 0.69911 → +15.1 %
- **ATLAS cross-check:** ATLAS 700489 + 700490 = 10.995 pb → ATLAS/CMS = 1.082. E1 applies: ATLAS uses Sherpa generator values with kFactor = 1 and has no gg → VV samples; the CMS NNLO total includes the loop-induced gg part.
- **Note:** Here the boson decaying to quarks is an on-shell Z, so the on-shell construction is also defensible; a choice for Matan.

## 11. 72658 WWTo1L1Nu2Q — tier 2 — unchanged from v1

- **What it is:** One W → ℓν (e, μ, τ) and the other W → quarks, NLO, 0-1 extra parton.
- **Dataset:** `/WWTo1L1Nu2Q_4f_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 72657; <https://opendata.cern.ch/record/72658>)
- **Proposed σ_eff = 52.3623 pb** = 118.7 × 0.441131

  - σ(WW), NNLO, includes gg → WW: **118.7** — https://arxiv.org/abs/1408.5243 — Table I (on-shell W+W−, 4FNS, includes gg → WW), row 13: σNNLO — as printed: 118.7 pb
  - BR = 2 × 0.3272 × 0.6741: **0.441131** — https://pdglive.lbl.gov/Particle.action?node=S043 — W DECAY MODES Γ2 e+ν, Γ3 μ+ν, Γ4 τ+ν, Γ5 hadrons (re-read 31 Oct 2026) — as printed: (10.71 ± 0.16) %, (10.63 ± 0.15) %, (11.38 ± 0.21) %, (67.41 ± 0.27) %

- **Order:** NNLO.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.6 (not multiplied in); total_value = 5.089e+01 pb, negative-weight fraction = 1.981e-01 (<https://opendata.cern.ch/api/records/72657>).
- **Proposed / generator:** 1.0289
- **What Matan should open and look for:** arXiv:1408.5243 Table I, row 13, σNNLO = 118.7. pdglive S043.
- **Decision / convention:** D9 — Same construction as our WWTo2L2Nu 72676 (118.7 pb × BR).
- **Alternatives (effect on σ_eff):** generator value instead → -2.8 %
- **ATLAS cross-check:** ATLAS 700488 = 47.918 pb → ATLAS/CMS = 0.915. E1 applies: ATLAS uses Sherpa generator values with kFactor = 1 and has no gg → VV samples; the CMS NNLO total includes the loop-induced gg part.

## 12. 72740 WZTo1L3Nu — tier 2 — unchanged from v1

- **What it is:** W → ℓν (e, μ, τ) with Z → νν, NLO, 0-1 extra parton.
- **Dataset:** `/WZTo1L3Nu_4f_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 72739; <https://opendata.cern.ch/record/72740>)
- **Proposed σ_eff = 3.78876 pb** = 3.415 × 1.10945

  - generator σ (portal): **3.415** — portal API <https://opendata.cern.ch/api/records/72739> metadata.cross_section.total_value
  - k = 51.11 / 46.068: **1.10945** — https://arxiv.org/abs/1604.08576 — Table 1 (on-shell W±Z), row √s = 13: σNLO, σNNLO — as printed: 46.068(3) pb, 51.11(3) pb

- **Order:** NLO generator × NNLO/NLO k-factor.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.6 (not multiplied in); total_value = 3.415e+00 pb, negative-weight fraction = 2.133e-01 (<https://opendata.cern.ch/api/records/72739>).
- **Proposed / generator:** 1.1094
- **What Matan should open and look for:** arXiv:1604.08576 Table 1, row 13: σNLO 46.068, σNNLO 51.11. The portal value on the MiniAOD record.
- **Decision / convention:** D9 — Generator × k-factor, as 72752 (the sample is the full ℓννν final state).
- **Alternatives (effect on σ_eff):** on-shell WZ instead: 51.11 × 0.3272 × 0.20000 → -11.7 %
- **ATLAS cross-check:** ATLAS 700604 = 3.1081 pb → ATLAS/CMS = 0.820. E1 applies: ATLAS uses Sherpa generator values with kFactor = 1 and has no gg → VV samples; the CMS NNLO total includes the loop-induced gg part.

## 13. 75567 ZZTo2L2Nu — tier 2 — NEW (D14)

**Generator-card check first (D14 condition).** Cards: `evidence/cards/75567/powheg.input` and, for comparison, the delivered ZZTo4L `evidence/cards/75589/powheg.input` (both fetched 31 Oct from <https://opendata.cern.ch/eos/opendata/cms/lhe_generators/2016-sim/gridpacks/75567/powheg.input> and `.../75589/powheg.input`).
  - 75567 line 2: `mllmin 4d0         ! default 0.1 GeV this is minimum invar mass for Z leptons`; line 31: `leptons-nu 1`. No Z-mass window, no `zerowidth`, no other m(ℓℓ) setting in the file.
  - 75589 (delivered ZZTo4L): **the same file** except the PDF set (306000 vs 325300) and the decay flag (`leptonic 1` vs `leptons-nu 1`); the same `mllmin 4d0` line.
  - The POWHEG-BOX-V2 ZZ code includes 'all diagrams relevant to the production of four leptons … with the exception of interference effects between W+W− and ZZ' (arXiv:1311.1365 §1; singly-resonant and interference terms included). So the charged pair is **Z/γ* down to m(ℓℓ) = 4 GeV**, not an on-shell Z; the νν pair has no photon.
  - **Verdict: the card supports the low-m(ℓℓ) / γ* explanation qualitatively** — the sample is not on-shell ZZ, and the generator setting that inflates it is exactly the one already accepted for our ZZTo4L (whose portal value 1.325 pb is 9.0 × its on-shell NLO expectation 14.51 × 0.10099² = 0.1480 pb, because there both pairs can be γ*). **It does not prove the size**: the card cannot say how much of the +42.6 % (vs on-shell NNLO; +66 % vs on-shell NLO 0.5861 pb) sits at low m(ℓℓ).
  - Not verified from the card: that `leptons-nu` means ℓ = e, μ, τ and all three ν flavours (the POWHEG-BOX ZZ manual/`alloweddec` was not opened; UNVERIFIED). If τ were excluded, the on-shell expectation would be 2/3 as large and the ratio larger.
  - A quantitative check is possible (not done: outside this task): one PBS job reading `LHEPart_*` of file 0 to measure the fraction of the generator σ with 60 < m(ℓℓ) < 120 GeV. If generator σ × that fraction ≈ the on-shell NLO 0.5861 pb, the 42 % is explained.

- **What it is:** ZZ → ℓℓνν: one Z/γ* → ℓℓ (m(ℓℓ) > 4 GeV) and one Z → νν, POWHEG NLO (qq̄ only).
- **Dataset:** `/ZZTo2L2Nu_TuneCP5_13TeV_powheg_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 75566; <https://opendata.cern.ch/record/75567>)
- **Proposed σ_eff = 1.13487 pb** = 0.9738 × 1.1654

  - generator σ (portal, MiniAOD 75566): **0.9738** — portal API <https://opendata.cern.ch/api/records/75566> metadata.cross_section.total_value
  - k = 16.91 / 14.51 (ZZ NNLO/NLO, includes gg → ZZ): **1.1654** — https://arxiv.org/abs/1405.2219 — Table 1 (inclusive ZZ, includes gg → ZZ at NNLO), row 13: σNLO, σNNLO — as printed: 14.51 pb, 16.91 pb

- **Order:** NLO generator × NNLO/NLO k-factor.
- **k-factor and source:** k = 1.16540 (arXiv:1405.2219 Table 1, row 13).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 9.738e-01 pb, negative-weight fraction = 1.053e-03 (<https://opendata.cern.ch/api/records/75566>).
- **Proposed / generator:** 1.1654
- **What Matan should open and look for:** First the card check above. Then arXiv:1405.2219 Table 1, row 13: 14.51 and 16.91 pb; the portal value 9.738e-01 on MiniAOD record 75566; pdglive S044 Γ1-Γ3, Γ7 for the fallback.
- **Decision / convention:** D14 (conditional), D9 — D9 convention (generator × NNLO/NLO k), as our ZZTo4L 75589 and ZZTo2Q2L 75573. CONDITIONAL (D14): proposed only if Matan accepts the card check as verifying the low-m(ℓℓ) explanation; otherwise the fallback below.
- **Alternatives (effect on σ_eff):** FALLBACK (D14): on-shell 16.91 × 2 × 0.10099 × 0.2000 = 0.6831 pb → -39.8 %; generator value alone (0.9738 pb) → -14.2 %
- **ATLAS cross-check:** ATLAS has no ZZ → ℓℓνν on its own: 700602 'VV → ℓℓνν, opposite sign' (12.079 pb, m(ℓℓ) > 4 GeV) holds WW and ZZ together. CMS WW → 2ℓ2ν 12.71 pb (delivered) + this card 1.135 pb = 13.84 pb → ATLAS/CMS = 0.873; with the fallback: 0.902. E1 applies (no gg on the ATLAS side). Not decisive.
- **Note:** Probe 31 Oct (file 0, 750,000 events): all 42 branches present, negative-weight fraction 0.0011 (portal 0.0011), Σw = Runs Σw to 5e-9. No overlap with WWTo2L2Nu: the POWHEG ZZ code has no W+W− diagrams (arXiv:1311.1365 §1).

# Tier 3

## 14. 72701 WWW_4F (ext1) — tier 3 — unchanged from v1

- **What it is:** WWW production at NLO, all decays.
- **Dataset:** `/WWW_4F_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 72699; <https://opendata.cern.ch/record/72701>)
- **Proposed σ_eff = 0.2158 pb** = 0.2158

  - generator σ (portal), NLO: **0.2158** — portal API <https://opendata.cern.ch/api/records/72699> metadata.cross_section.total_value

- **Order:** NLO.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 2.158e-01 pb, negative-weight fraction = 4.672e-02 (<https://opendata.cern.ch/api/records/72699>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** The MiniAOD record 72699: metadata.cross_section.total_value.
- **Decision / convention:** D10 — No NNLO exists → generator value at NLO (settled convention, as ttZ/ttW).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS has leptonic channels only (MAPPING.md table A, ratios 0.02-0.17): no like-for-like ATLAS value.

## 15. 72711 WWZ_4F (ext1) — tier 3 — unchanged from v1

- **What it is:** WWZ production at NLO, all decays.
- **Dataset:** `/WWZ_4F_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 72709; <https://opendata.cern.ch/record/72711>)
- **Proposed σ_eff = 0.1707 pb** = 0.1707

  - generator σ (portal), NLO: **0.1707** — portal API <https://opendata.cern.ch/api/records/72709> metadata.cross_section.total_value

- **Order:** NLO.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 1.707e-01 pb, negative-weight fraction = 4.649e-02 (<https://opendata.cern.ch/api/records/72709>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** The MiniAOD record 72709: metadata.cross_section.total_value.
- **Decision / convention:** D10 — No NNLO exists → generator value at NLO (settled convention, as ttZ/ttW).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS has leptonic channels only (MAPPING.md table A, ratios 0.02-0.17): no like-for-like ATLAS value.

## 16. 72761 WZZ (ext1) — tier 3 — unchanged from v1

- **What it is:** WZZ production at NLO, all decays.
- **Dataset:** `/WZZ_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 72759; <https://opendata.cern.ch/record/72761>)
- **Proposed σ_eff = 0.05709 pb** = 0.05709

  - generator σ (portal), NLO: **0.05709** — portal API <https://opendata.cern.ch/api/records/72759> metadata.cross_section.total_value

- **Order:** NLO.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 5.709e-02 pb, negative-weight fraction = 4.614e-02 (<https://opendata.cern.ch/api/records/72759>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** The MiniAOD record 72759: metadata.cross_section.total_value.
- **Decision / convention:** D10 — No NNLO exists → generator value at NLO (settled convention, as ttZ/ttW).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS has leptonic channels only (MAPPING.md table A, ratios 0.02-0.17): no like-for-like ATLAS value.

## 17. 75600 ZZZ (ext1) — tier 3 — unchanged from v1

- **What it is:** ZZZ production at NLO, all decays.
- **Dataset:** `/ZZZ_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 75598; <https://opendata.cern.ch/record/75600>)
- **Proposed σ_eff = 0.01476 pb** = 0.01476

  - generator σ (portal), NLO: **0.01476** — portal API <https://opendata.cern.ch/api/records/75598> metadata.cross_section.total_value

- **Order:** NLO.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 1.476e-02 pb, negative-weight fraction = 5.439e-02 (<https://opendata.cern.ch/api/records/75598>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** The MiniAOD record 75598: metadata.cross_section.total_value.
- **Decision / convention:** D10 — No NNLO exists → generator value at NLO (settled convention, as ttZ/ttW).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS has leptonic channels only (MAPPING.md table A, ratios 0.02-0.17): no like-for-like ATLAS value.

## 18. 35999 EWKZ2Jets_ZToLL_M-50 — tier 3 — NEW (D12) — DECISION NEEDED on the value

- **What it is:** Z/γ* → ℓℓ (e, μ, τ) + 2 jets, purely electroweak (QED = 4, QCD = 0).
- **Dataset:** `/EWKZ2Jets_ZToLL_M-50_TuneCP5_withDipoleRecoil_13TeV-madgraph-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 35998; <https://opendata.cern.ch/record/35999>)
- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):

  - (a) generator LO value (portal): **6.206 pb** — portal record https://opendata.cern.ch/api/records/35998
  - (b) generator × 534 / 543 (measured / LO, m(ℓℓ) > 50, pT(j) > 25, m(jj) > 120 GeV, ℓ = e, μ) = × 0.9834: **6.10314 pb** — https://arxiv.org/abs/1712.09814

- **Order:** LO (MadGraph, no extra partons).
- **k-factor and source:** none in option (a); option (b) applies a measured/LO ratio.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 6.206e+00 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/35998>).
- **What Matan should open and look for:** Card `evidence/cards/35999/*proc_card.dat` and `*run_card.dat`; the portal value on MiniAOD 35998; https://arxiv.org/abs/1712.09814 for option (b).
- **Decision / convention:** D12 — No settled convention: no NNLO exists, and the published NLO (VBFNLO) and the measurement are in a narrower phase space (m(jj) > 120, pT(j) > 25 GeV) than the sample (m(jj) > 10, pT(j) > 10 GeV). The table shows (a) as the placeholder only.
- **Alternatives (effect on σ_eff):** option (b) 534 / 543 (measured / LO, m(ℓℓ) > 50, pT(j) > 25, m(jj) > 120 GeV, ℓ = e, μ) → -1.7 %
- **ATLAS cross-check:** ATLAS 700358-700360 (Sherpa LO, 'Min_N_TChannels', per flavour ≈ 0.779 pb): 2.338 pb for 3 flavours (Z) vs CMS 6.21 pb → ATLAS/CMS = 0.377 (per flavour CMS 2.07 pb). NOT like-for-like, see the note.
- **Note:** Generator-level cuts (card): `generate p p > l+ l- j j / t t~ h QED=4 QCD=0` (ℓ = e, μ, τ); run card: mmll = 50 (m(ℓℓ) > 50 GeV), ptj = 10, etaj = 6.5, mmjj = 10 (m(jj) > 10 GeV), deltaeta = 0 (no Δη cut), drjj = 0, ptl = 0, etal = −1 (none). **Why CMS ≈ 2.7-2.8 × ATLAS:** (1) `QED=4 QCD=0` keeps every purely electroweak diagram, including s-channel diboson/triboson-like ones (WZ/ZZ/WW with V → qq); ATLAS's names say 'Min_N_TChannels', which in Sherpa 'limits the minimum number of t-channel propagators' (Sherpa 2.2.11 manual §5.6.14), i.e. removes pure s-channel diagrams; (2) the CMS cuts are very loose (m(jj) > 10, pT(j) > 10 GeV); ATLAS's generator cuts are not in the public metadata (UNKNOWN; job options not opened, rule: metadata only). **Overlap flag (physics choice, not decided):** the s-channel diboson part of this sample (V → qq with m(jj) ≈ mW/mZ) is the same process as tier-2 WZTo2Q2L 72742 / ZZTo2Q2L 75573; using both counts it twice in that region. Options: keep both and accept it (CMS SMP-16-018 calls the diboson contribution 'small' in its m(jj) > 120 region; our histograms have no m(jj) cut); remove events with LHE m(jj) near mW/mZ from this sample (new builder code); its size can be measured from LHEPart (not done). Probe 31 Oct: all 42 branches present, no negative weights.

## 19. 35987 EWKWMinus2Jets_WToLNu_M-50 — tier 3 — NEW (D12) — DECISION NEEDED on the value

- **What it is:** W⁻ → ℓ⁻ν̄ (e, μ, τ) + 2 jets, purely electroweak (QCD = 0).
- **Dataset:** `/EWKWMinus2Jets_WToLNu_M-50_TuneCP5_withDipoleRecoil_13TeV-madgraph-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 35986; <https://opendata.cern.ch/record/35987>)
- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):

  - (a) generator LO value (portal): **32.1 pb** — portal record https://opendata.cern.ch/api/records/35986
  - (b) generator × 6.23 / 6.81 (measured / LO, pT(j) > 25, m(jj) > 120 GeV) = × 0.9148: **29.3661 pb** — https://arxiv.org/abs/1903.04040

- **Order:** LO (MadGraph, no extra partons).
- **k-factor and source:** none in option (a); option (b) applies a measured/LO ratio.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 3.210e+01 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/35986>).
- **What Matan should open and look for:** Card `evidence/cards/35987/*proc_card.dat` and `*run_card.dat`; the portal value on MiniAOD 35986; https://arxiv.org/abs/1903.04040 for option (b).
- **Decision / convention:** D12 — No settled convention: no NNLO exists, and the published NLO (VBFNLO) and the measurement are in a narrower phase space (m(jj) > 120, pT(j) > 25 GeV) than the sample (m(jj) > 10, pT(j) > 10 GeV). The table shows (a) as the placeholder only.
- **Alternatives (effect on σ_eff):** option (b) 6.23 / 6.81 (measured / LO, pT(j) > 25, m(jj) > 120 GeV) → -8.5 %
- **ATLAS cross-check:** ATLAS 700362-700364 (Sherpa LO, 'Min_N_TChannels', per flavour ≈ 8.502 pb): 25.506 pb for 3 flavours (W⁺ + W⁻ together) vs CMS 71.18 pb → ATLAS/CMS = 0.358 (per flavour CMS 23.73 pb). NOT like-for-like, see the note.
- **Note:** Generator-level cuts (card): `generate p p > l- vl~ j j / t t~ h QCD=0` (ℓ = e, μ, τ); run card: mmnl = 50 (m(ℓν) > 50 GeV), ptj = 10, etaj = 6.5, mmjj = 10, deltaeta = 0, ptl = 0. **Why CMS ≈ 2.7-2.8 × ATLAS:** (1) `QED=4 QCD=0` keeps every purely electroweak diagram, including s-channel diboson/triboson-like ones (WZ/ZZ/WW with V → qq); ATLAS's names say 'Min_N_TChannels', which in Sherpa 'limits the minimum number of t-channel propagators' (Sherpa 2.2.11 manual §5.6.14), i.e. removes pure s-channel diagrams; (2) the CMS cuts are very loose (m(jj) > 10, pT(j) > 10 GeV); ATLAS's generator cuts are not in the public metadata (UNKNOWN; job options not opened, rule: metadata only). **Overlap flag (physics choice, not decided):** the s-channel diboson part of this sample (V → qq with m(jj) ≈ mW/mZ) is the same process as tier-2 WZTo1L1Nu2Q 72738 / WWTo1L1Nu2Q 72658; using both counts it twice in that region. Options: keep both and accept it (CMS SMP-16-018 calls the diboson contribution 'small' in its m(jj) > 120 region; our histograms have no m(jj) cut); remove events with LHE m(jj) near mW/mZ from this sample (new builder code); its size can be measured from LHEPart (not done). Probe 31 Oct: all 42 branches present, no negative weights.

## 20. 35993 EWKWPlus2Jets_WToLNu_M-50 — tier 3 — NEW (D12) — DECISION NEEDED on the value

- **What it is:** W⁺ → ℓ⁺ν (e, μ, τ) + 2 jets, purely electroweak (QCD = 0).
- **Dataset:** `/EWKWPlus2Jets_WToLNu_M-50_TuneCP5_withDipoleRecoil_13TeV-madgraph-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 35992; <https://opendata.cern.ch/record/35993>)
- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):

  - (a) generator LO value (portal): **39.08 pb** — portal record https://opendata.cern.ch/api/records/35992
  - (b) generator × 6.23 / 6.81 (measured / LO, pT(j) > 25, m(jj) > 120 GeV) = × 0.9148: **35.7516 pb** — https://arxiv.org/abs/1903.04040

- **Order:** LO (MadGraph, no extra partons).
- **k-factor and source:** none in option (a); option (b) applies a measured/LO ratio.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 3.908e+01 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/35992>).
- **What Matan should open and look for:** Card `evidence/cards/35993/*proc_card.dat` and `*run_card.dat`; the portal value on MiniAOD 35992; https://arxiv.org/abs/1903.04040 for option (b).
- **Decision / convention:** D12 — No settled convention: no NNLO exists, and the published NLO (VBFNLO) and the measurement are in a narrower phase space (m(jj) > 120, pT(j) > 25 GeV) than the sample (m(jj) > 10, pT(j) > 10 GeV). The table shows (a) as the placeholder only.
- **Alternatives (effect on σ_eff):** option (b) 6.23 / 6.81 (measured / LO, pT(j) > 25, m(jj) > 120 GeV) → -8.5 %
- **ATLAS cross-check:** ATLAS 700362-700364 (Sherpa LO, 'Min_N_TChannels', per flavour ≈ 8.502 pb): 25.506 pb for 3 flavours (W⁺ + W⁻ together) vs CMS 71.18 pb → ATLAS/CMS = 0.358 (per flavour CMS 23.73 pb). NOT like-for-like, see the note.
- **Note:** Generator-level cuts (card): `generate p p > l+ vl j j / t t~ h QCD=0` (ℓ = e, μ, τ); run card: mmnl = 50, ptj = 10, etaj = 6.5, mmjj = 10, deltaeta = 0, ptl = 0. **Why CMS ≈ 2.7-2.8 × ATLAS:** (1) `QED=4 QCD=0` keeps every purely electroweak diagram, including s-channel diboson/triboson-like ones (WZ/ZZ/WW with V → qq); ATLAS's names say 'Min_N_TChannels', which in Sherpa 'limits the minimum number of t-channel propagators' (Sherpa 2.2.11 manual §5.6.14), i.e. removes pure s-channel diagrams; (2) the CMS cuts are very loose (m(jj) > 10, pT(j) > 10 GeV); ATLAS's generator cuts are not in the public metadata (UNKNOWN; job options not opened, rule: metadata only). **Overlap flag (physics choice, not decided):** the s-channel diboson part of this sample (V → qq with m(jj) ≈ mW/mZ) is the same process as tier-2 WZTo1L1Nu2Q 72738 / WWTo1L1Nu2Q 72658; using both counts it twice in that region. Options: keep both and accept it (CMS SMP-16-018 calls the diboson contribution 'small' in its m(jj) > 120 region; our histograms have no m(jj) cut); remove events with LHE m(jj) near mW/mZ from this sample (new builder code); its size can be measured from LHEPart (not done). Probe 31 Oct: all 42 branches present, no negative weights.

# Tier 4

## 21. 67645 ttHTobb_M125 (powheg) — tier 4 — unchanged from v1

- **What it is:** tt̄H with H → bb̄ (all top decays).
- **Dataset:** `/ttHTobb_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 67644; <https://opendata.cern.ch/record/67645>)
- **Proposed σ_eff = 0.295335 pb** = 0.5071 × 0.5824

  - σ(ttH), NLO QCD + NLO EW, mH = 125.00: **0.5071** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → bb), mH = 125.00: **0.5824** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** NLO QCD + NLO EW.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 5.013e-01 pb, negative-weight fraction = 1.036e-02 (<https://opendata.cern.ch/api/records/67644>).
- **Proposed / generator:** 0.5891
- **What Matan should open and look for:** CERNYellowReportPageAt13TeV, ttH table, 125.00 → 5.071E-01. CERNYellowReportPageBR, 'Higgs → 2 fermions', 125.00, H → bb = 5.824E-01.
- **Decision / convention:** plan — LHC Higgs WG YR4 at 125.00 GeV (settled).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS tt̄H 346343-346345 (all decays) = 0.5071 pb vs CMS bb + non-bb = 0.5071 → 1.00 (MAPPING.md).

## 22. 67691 ttHToNonbb_M125 (powheg) — tier 4 — unchanged from v1

- **What it is:** tt̄H with every Higgs decay except H → bb̄.
- **Dataset:** `/ttHToNonbb_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 67690; <https://opendata.cern.ch/record/67691>)
- **Proposed σ_eff = 0.211765 pb** = 0.5071 × 0.4176

  - σ(ttH): **0.5071** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - 1 − BR(H → bb): **0.4176** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** NLO QCD + NLO EW.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 5.013e-01 pb, negative-weight fraction = 1.033e-02 (<https://opendata.cern.ch/api/records/67690>).
- **Proposed / generator:** 0.4224
- **What Matan should open and look for:** As 67645. Pythia setting in the record: '25:offIfAny = 5 -5'.
- **Decision / convention:** plan — YR4 at 125.00 GeV.
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** As 67645 (ATLAS/CMS 1.00 for tt̄H as a whole).

## 23. 68083 TTWJetsToQQ — tier 4 — unchanged from v1

- **What it is:** tt̄W with W → quarks, NLO, 0-1 extra parton.
- **Dataset:** `/TTWJetsToQQ_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 68082; <https://opendata.cern.ch/record/68083>)
- **Proposed σ_eff = 0.4375 pb** = 0.4375

  - generator σ (portal), NLO: **0.4375** — portal API <https://opendata.cern.ch/api/records/68082> metadata.cross_section.total_value

- **Order:** NLO.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.6 (not multiplied in); total_value = 4.375e-01 pb, negative-weight fraction = 2.264e-01 (<https://opendata.cern.ch/api/records/68082>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** MiniAOD record 68082, total_value (matching efficiency 0.6 shown, not applied -- the same open point as 68073).
- **Decision / convention:** plan — No NNLO → generator NLO, as our ttW 68073.
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS tt̄W inclusive 410155 = 0.6008 pb vs CMS ℓν (delivered 0.2151) + qq (this card 0.4375) = 0.6526 → 0.921.

## 24. 68045 TTTT — tier 4 — CHANGED (D7)

- **What it is:** Four top quarks, all decays, NLO (aMC@NLO).
- **Dataset:** `/TTTT_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 68044; <https://opendata.cern.ch/record/68045>)
- **Proposed σ_eff = 0.01197 pb** = 0.01197

  - σ(tt̄tt̄), complete NLO QCD+EW, µ = HT/4 [11.97 fb]: **0.01197** — https://arxiv.org/abs/1711.02116 — Table 5 (TeX label table:4t), row µ = HT/4, column 'LO + NLO' (complete NLO QCD+EW); re-read from the arXiv TeX source 31 Oct 2026 — as printed: 11.97 (+18 % −21 %) fb

- **Order:** complete NLO QCD + EW.
- **k-factor and source:** none (the sample is normalised to the published total).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 8.091e-03 pb, negative-weight fraction = 2.814e-01 (<https://opendata.cern.ch/api/records/68044>).
- **Proposed / generator:** 1.4794
- **What Matan should open and look for:** arXiv:1711.02116 Table 5, row µ = HT/4, column 'LO + NLO' = 11.97 fb.
- **Decision / convention:** D7 — D7: the published complete-NLO value, matching ATLAS.
- **Alternatives (effect on σ_eff):** generator NLO value 8.091 fb (portal, MiniAOD 68044) → -32.4 %; NLO(QCD+EW)+NLL′ 14.65 fb (arXiv:2212.03259 Table I) → +22.4 %
- **ATLAS cross-check:** ATLAS 412043: 10.673 fb × k 1.1267 = 12.025 fb → ATLAS/CMS = 1.005.
- **Note:** Proposed / generator = 1.479.

## 25. 68325 tZq_ll_4f — tier 4 — ON HOLD — card kept unchanged from v1, not for review now

- **What it is:** Single top + Z/γ* → ℓℓ (e, μ, τ; same-flavour m(ℓℓ) > 30 GeV) + a light quark, NLO.
- **Dataset:** `/tZq_ll_4f_ckm_NLO_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 68324; <https://opendata.cern.ch/record/68325>)
- **Proposed σ_eff = 0.07561 pb** = 0.07561

  - generator σ (portal), NLO: **0.07561** — portal API <https://opendata.cern.ch/api/records/68324> metadata.cross_section.total_value

- **Order:** NLO.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 7.561e-02 pb, negative-weight fraction = 3.647e-01 (<https://opendata.cern.ch/api/records/68324>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** MiniAOD record 68324, total_value.
- **Decision / convention:** ON HOLD (D8 / no ATLAS nominal counterpart; waiting for Maryna) — No NNLO → generator NLO.
- **Alternatives:** none with a public source found.

## 26. 64873 ST_tWll_5f — tier 4 — ON HOLD — card kept unchanged from v1, not for review now

- **What it is:** Single top + W + a lepton pair (e, μ, τ), LO (no Higgs diagrams).
- **Dataset:** `/ST_tWll_5f_TuneCP5_13TeV-madgraph-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 64872; <https://opendata.cern.ch/record/64873>)
- **Proposed σ_eff = 0.01105 pb** = 0.01105

  - generator σ (portal), LO: **0.01105** — portal API <https://opendata.cern.ch/api/records/64872> metadata.cross_section.total_value

- **Order:** LO.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 1.105e-02 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/64872>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** MiniAOD record 64872, total_value.
- **Decision / convention:** ON HOLD (D8 / no ATLAS nominal counterpart; waiting for Maryna) — CANNOT follow the convention: only an LO generator value exists (no NLO sample, no published total for this phase space). Decision for Matan.
- **Alternatives:** none with a public source found.

## 27. 68206 TTZToQQ — tier 4 — ON HOLD — card kept unchanged from v1, not for review now

- **What it is:** tt̄Z with Z → quarks (u, d, s, c, b), NLO.
- **Dataset:** `/TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 68204; <https://opendata.cern.ch/record/68206>)
- **Proposed σ_eff = 0.5113 pb** = 0.5113

  - generator σ (portal), NLO: **0.5113** — portal API <https://opendata.cern.ch/api/records/68204> metadata.cross_section.total_value

- **Order:** NLO.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 5.113e-01 pb, negative-weight fraction = 2.517e-01 (<https://opendata.cern.ch/api/records/68204>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** MiniAOD record 68204, total_value.
- **Decision / convention:** ON HOLD (D8 / no ATLAS nominal counterpart; waiting for Maryna) — No NNLO → generator NLO, as our ttZ 68187.
- **Alternatives:** none with a public source found.

## 28. 68185 TTZToLL_M-1to10 — tier 4 — ON HOLD — card kept unchanged from v1, not for review now

- **What it is:** tt̄ + lepton pair (e, μ, τ) with 1 < m(ℓℓ) < 10 GeV (virtual photon), NLO -- fills the gap below our TTZToLLNuNu_M-10.
- **Dataset:** `/TTZToLL_M-1to10_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 68184; <https://opendata.cern.ch/record/68185>)
- **Proposed σ_eff = 0.0537 pb** = 0.0537

  - generator σ (portal), NLO: **0.0537** — portal API <https://opendata.cern.ch/api/records/68184> metadata.cross_section.total_value

- **Order:** NLO.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 5.370e-02 pb, negative-weight fraction = 2.212e-01 (<https://opendata.cern.ch/api/records/68184>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** MiniAOD record 68184, total_value.
- **Decision / convention:** ON HOLD (D8 / no ATLAS nominal counterpart; waiting for Maryna) — No NNLO → generator NLO.
- **Alternatives:** none with a public source found.

# Tier 5

## 29. 37474 GluGluHToWWTo2L2Nu_M-125 — tier 5 — unchanged from v1

- **What it is:** Gluon-fusion Higgs, H → WW → ℓνℓν (ℓ = e, μ, τ).
- **Dataset:** `/GluGluHToWWTo2L2Nu_M-125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 37473; <https://opendata.cern.ch/record/37474>)
- **Proposed σ_eff = 1.11145 pb** = 48.58 × 0.2137 × 0.10706

  - σ(ggF), N3LO QCD + NLO EW: **48.58** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04
  - BR(W → ℓν)² = 0.3272²: **0.10706** — https://pdglive.lbl.gov/Particle.action?node=S043 — W DECAY MODES Γ2 e+ν, Γ3 μ+ν, Γ4 τ+ν, Γ5 hadrons (re-read 31 Oct 2026) — as printed: (10.71 ± 0.16) %, (10.63 ± 0.15) %, (11.38 ± 0.21) %, (67.41 ± 0.27) %

- **Order:** N3LO QCD + NLO EW.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 2.147e+01 pb, negative-weight fraction = 3.452e-05 (<https://opendata.cern.ch/api/records/37473>).
- **Proposed / generator:** 0.0518
- **What Matan should open and look for:** YR4 13 TeV ggF table, 125.00 → 4.858E+01; BR page 'Higgs → 2 gauge bosons', 125.00, WW = 2.137E-01.
- **Decision / convention:** D13 (planned 15) — YR4 × YR4 BR × PDG W BRs (settled).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS 345324 (H → WW → ℓνℓν): ATLAS/CMS 1.02 (MAPPING.md).
- **Note:** Pythia: '25:onIfMatch = 24 -24', '24:onIfMatch = 11 12 / 13 14 / 15 16'.

## 30. 68601 VBFHToWWTo2L2Nu_M125 — tier 5 — unchanged from v1

- **What it is:** Vector-boson-fusion Higgs, H → WW → ℓνℓν (ℓ = e, μ, τ).
- **Dataset:** `/VBFHToWWTo2L2Nu_M125_TuneCP5_13TeV_powheg2_JHUGenV714_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 68600; <https://opendata.cern.ch/record/68601>)
- **Proposed σ_eff = 0.0865272 pb** = 3.782 × 0.2137 × 0.10706

  - σ(VBF), approx. NNLO QCD + NLO EW: **3.782** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04
  - BR(W → ℓν)²: **0.10706** — https://pdglive.lbl.gov/Particle.action?node=S043 — W DECAY MODES Γ2 e+ν, Γ3 μ+ν, Γ4 τ+ν, Γ5 hadrons (re-read 31 Oct 2026) — as printed: (10.71 ± 0.16) %, (10.63 ± 0.15) %, (11.38 ± 0.21) %, (67.41 ± 0.27) %

- **Order:** approx. NNLO QCD + NLO EW.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 3.892e+00 pb, negative-weight fraction = 6.562e-04 (<https://opendata.cern.ch/api/records/68600>).
- **Proposed / generator:** 0.0222
- **What Matan should open and look for:** YR4 VBF table, 125.00 → 3.782E+00; BR WW 2.137E-01.
- **Decision / convention:** D13 (planned 15) — YR4 (settled).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS 345948: ATLAS/CMS 1.02 (MAPPING.md).
- **Note:** JHUGen card: DecayMode1=10 DecayMode2=10 (W → ℓν, ℓ = e, μ, τ).

## 31. 41877 HWplusJ_HToWW_M-125 — tier 5 — unchanged from v1

- **What it is:** W+H production, W decaying any way, H → WW (any decay).
- **Dataset:** `/HWplusJ_HToWW_M-125_TuneCP5_13TeV-powheg-jhugen727-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 41876; <https://opendata.cern.ch/record/41877>)
- **Proposed σ_eff = 0.179508 pb** = 0.84 × 0.2137

  - σ(W+H), NNLO QCD + NLO EW: **0.84** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** NNLO QCD + NLO EW.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 8.720e-01 pb, negative-weight fraction = 2.785e-02 (<https://opendata.cern.ch/api/records/41876>).
- **Proposed / generator:** 0.2059
- **What Matan should open and look for:** YR4 WH table, 125.00, column 'W+H (pb)' = 8.400E-01; BR WW.
- **Decision / convention:** D13 (planned 15) — YR4 (settled).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS W±H → WW has W → qq and H → ℓνℓν only (0.07, different channels): no like-for-like value.
- **Note:** Cards: vdecaymode 10 (W inclusive), JHUGen DecayMode 11/11 (W → anything).

## 32. 41873 HWminusJ_HToWW_M-125 — tier 5 — unchanged from v1

- **What it is:** W−H production, W decaying any way, H → WW (any decay).
- **Dataset:** `/HWminusJ_HToWW_M-125_TuneCP5_13TeV-powheg-jhugen727-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 41872; <https://opendata.cern.ch/record/41873>)
- **Proposed σ_eff = 0.113859 pb** = 0.5328 × 0.2137

  - σ(W−H), NNLO QCD + NLO EW: **0.5328** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** NNLO QCD + NLO EW.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 5.445e-01 pb, negative-weight fraction = 2.625e-02 (<https://opendata.cern.ch/api/records/41872>).
- **Proposed / generator:** 0.2091
- **What Matan should open and look for:** YR4 WH table, 125.00, column 'W−H (pb)' = 5.328E-01; BR WW.
- **Decision / convention:** D13 (planned 15) — YR4 (settled).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** As 41877.
- **Note:** Cards: vdecaymode 10 (W inclusive), JHUGen DecayMode 11/11 (W → anything).

## 33. 41914 HZJ_HToWW_M-125 (ext1) — tier 5 — unchanged from v1

- **What it is:** qq̄ → ZH, Z decaying any way, H → WW (any decay).
- **Dataset:** `/HZJ_HToWW_M-125_TuneCP5_13TeV-powheg-jhugen727-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 41912; <https://opendata.cern.ch/record/41914>)
- **Proposed σ_eff = 0.162668 pb** = 0.7612 × 0.2137

  - σ(ZH, all but gg → ZH): **0.7612** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** NNLO QCD + NLO EW.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = None (not multiplied in); total_value = 9.595e-01 pb, negative-weight fraction = 2.965e-02 (<https://opendata.cern.ch/api/records/41912>).
- **Proposed / generator:** 0.1695
- **What Matan should open and look for:** YR4 ZH process table: 'qq/qg→ZH, gg→HZ+qqbar (all but gg→ZH)' = 0.7612.
- **Decision / convention:** D13 (planned 15) — YR4 'all but gg→ZH' value, the page's own recommendation for an NLO qq̄ → ZH sample.
- **Alternatives (effect on σ_eff):** total pp → ZH 0.8839 instead (would double-count gg → ZH) → +16.1 %
- **ATLAS cross-check:** ATLAS qq̄ → ZH → WW is Z → νν only (0.05, different channels): no like-for-like value.
- **Note:** Portal shows no matching efficiency for this record (None).

## 34. 40095 GluGluZH_HToWW_ZTo2L_M-125 (ext1) — tier 5 — unchanged from v1

- **What it is:** gg → ZH, Z → ℓℓ (e, μ, τ), H → WW (any decay).
- **Dataset:** `/GluGluZH_HToWW_ZTo2L_M-125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 40093; <https://opendata.cern.ch/record/40095>)
- **Proposed σ_eff = 0.00264806 pb** = 0.1227 × 0.2137 × 0.10099

  - σ(gg → ZH), NLO+NLL: **0.1227** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04
  - BR(Z → ℓℓ) = 0.033632 + 0.033662 + 0.033696: **0.10099** — https://pdglive.lbl.gov/Particle.action?node=S044 — Z DECAY MODES Γ1 e+e−, Γ2 μ+μ−, Γ3 τ+τ−, Γ7 invisible, Γ8 hadrons (re-read 31 Oct 2026, D6) — as printed: (3.3632 ± 0.0042) %, (3.3662 ± 0.0066) %, (3.3696 ± 0.0083) %, (20.000 ± 0.055) %, (69.911 ± 0.056) %

- **Order:** NLO+NLL QCD.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = None (not multiplied in); total_value = 6.185e-03 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/40093>).
- **Proposed / generator:** 0.4281
- **What Matan should open and look for:** YR4 ZH process table: 'gg→ZH' = 0.1227. pdglive S044: Γ1, Γ2, Γ3.
- **Decision / convention:** D13 (planned 15) — YR4 gg → ZH; Z branching ratios from PDG individually measured values (by analogy with the W convention -- NOT settled, see Decisions).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS 346524 is Z-inclusive (ATLAS/CMS 1.08 is not like-for-like).
- **Note:** POWHEG card: vdecaymode 11 ('inclusive leptons'); Pythia '25:onIfMatch = 24 -24'. The Z branching ratios here are now the settled D6 values (pdglive S044, re-checked 31 Oct, unchanged), so the number is unchanged.

## 35. 37446 GluGluHToTauTau_M125 — tier 5 — unchanged from v1

- **What it is:** gluon-fusion Higgs, H → ττ.
- **Dataset:** `/GluGluHToTauTau_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 37445; <https://opendata.cern.ch/record/37446>)
- **Proposed σ_eff = 3.04694 pb** = 48.58 × 0.06272

  - σ(production), YR4: **48.58** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → ττ): **0.06272** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** YR4 order of the production mode.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 2.146e+01 pb, negative-weight fraction = 5.185e-03 (<https://opendata.cern.ch/api/records/37445>).
- **Proposed / generator:** 0.1420
- **What Matan should open and look for:** YR4 ggF table 4.858E+01; BR page 'Higgs → 2 fermions', 125.00, ττ = 6.272E-02.
- **Decision / convention:** D13 (planned 15) — YR4 (settled).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS ggF → ττ pieces carry ττ-decay and pT filters (0.32): no like-for-like value.
- **Note:** Pythia: '25:onIfMatch = 15 -15'.

## 36. 68591 VBFHToTauTau_M125 — tier 5 — unchanged from v1

- **What it is:** VBF Higgs, H → ττ.
- **Dataset:** `/VBFHToTauTau_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 68590; <https://opendata.cern.ch/record/68591>)
- **Proposed σ_eff = 0.237207 pb** = 3.782 × 0.06272

  - σ(production), YR4: **3.782** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → ττ): **0.06272** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** YR4 order of the production mode.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 3.861e+00 pb, negative-weight fraction = 6.407e-04 (<https://opendata.cern.ch/api/records/68590>).
- **Proposed / generator:** 0.0614
- **What Matan should open and look for:** YR4 VBF table 3.782E+00; BR page 'Higgs → 2 fermions', 125.00, ττ = 6.272E-02.
- **Decision / convention:** D13 (planned 15) — YR4 (settled).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS VBF → ττ pieces sum to more than σ × BR (1.29; looks like an ATLAS-side issue, MAPPING.md).
- **Note:** Pythia: '25:onIfMatch = 15 -15'.

## 37. 71297 WplusHToTauTau_M125 — tier 5 — unchanged from v1

- **What it is:** W+H (W any decay) Higgs, H → ττ.
- **Dataset:** `/WplusHToTauTau_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 71296; <https://opendata.cern.ch/record/71297>)
- **Proposed σ_eff = 0.0526848 pb** = 0.84 × 0.06272

  - σ(production), YR4: **0.84** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → ττ): **0.06272** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** YR4 order of the production mode.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 8.670e-01 pb, negative-weight fraction = 2.792e-02 (<https://opendata.cern.ch/api/records/71296>).
- **Proposed / generator:** 0.0608
- **What Matan should open and look for:** YR4 WH table, W+H 8.400E-01; BR page 'Higgs → 2 fermions', 125.00, ττ = 6.272E-02.
- **Decision / convention:** D13 (planned 15) — YR4 (settled).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS 345211/345212 (W±H → ττ): 1.00 (same YR4 inputs).
- **Note:** Pythia: '25:onIfMatch = 15 -15'.

## 38. 70453 WminusHToTauTau_M125 — tier 5 — unchanged from v1

- **What it is:** W−H (W any decay) Higgs, H → ττ.
- **Dataset:** `/WminusHToTauTau_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 70452; <https://opendata.cern.ch/record/70453>)
- **Proposed σ_eff = 0.0334172 pb** = 0.5328 × 0.06272

  - σ(production), YR4: **0.5328** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → ττ): **0.06272** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** YR4 order of the production mode.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 5.412e-01 pb, negative-weight fraction = 2.648e-02 (<https://opendata.cern.ch/api/records/70452>).
- **Proposed / generator:** 0.0617
- **What Matan should open and look for:** YR4 WH table, W−H 5.328E-01; BR page 'Higgs → 2 fermions', 125.00, ττ = 6.272E-02.
- **Decision / convention:** D13 (planned 15) — YR4 (settled).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** As 71297.
- **Note:** Pythia: '25:onIfMatch = 15 -15'.

## 39. 74684 ZHToTauTau_M125 — tier 5 — unchanged from v1

- **What it is:** qq̄ → ZH (Z any decay) Higgs, H → ττ.
- **Dataset:** `/ZHToTauTau_M125_CP5_13TeV-powheg-pythia8_ext1/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 74683; <https://opendata.cern.ch/record/74684>)
- **Proposed σ_eff = 0.0477425 pb** = 0.7612 × 0.06272

  - σ(production), YR4: **0.7612** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → ττ): **0.06272** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** YR4 order of the production mode.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 7.891e-01 pb, negative-weight fraction = 2.902e-02 (<https://opendata.cern.ch/api/records/74683>).
- **Proposed / generator:** 0.0605
- **What Matan should open and look for:** YR4 ZH process table, all but gg→ZH 0.7612; BR page 'Higgs → 2 fermions', 125.00, ττ = 6.272E-02.
- **Decision / convention:** D13 (planned 15) — YR4 (settled).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS 345217: 1.00.
- **Note:** Pythia: '25:onIfMatch = 15 -15'.

## 40. 37616 GluGluHToZZTo2L2Nu_M125 — tier 5 — unchanged from v1

- **What it is:** Gluon-fusion Higgs, H → ZZ → ℓℓνν with ℓ = e or μ only (no τ).
- **Dataset:** `/GluGluHToZZTo2L2Nu_M125_TuneCP5_13TeV_powheg2_JHUGenV735_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 37615; <https://opendata.cern.ch/record/37616>)
- **Proposed σ_eff = 0.0342475 pb** = 48.58 × 0.02619 × 0.0269176

  - σ(production), YR4: **48.58** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → ZZ): **0.02619** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04
  - 2 × BR(Z → ee + μμ) × BR(Z → νν) = 2 × 0.067294 × 0.20000: **0.0269176** — https://pdglive.lbl.gov/Particle.action?node=S044 — Z DECAY MODES Γ1 e+e−, Γ2 μ+μ−, Γ3 τ+τ−, Γ7 invisible, Γ8 hadrons (re-read 31 Oct 2026, D6) — as printed: (3.3632 ± 0.0042) %, (3.3662 ± 0.0066) %, (3.3696 ± 0.0083) %, (20.000 ± 0.055) %, (69.911 ± 0.056) %

- **Order:** YR4 order of the production mode.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 2.887e+01 pb, negative-weight fraction = 4.919e-03 (<https://opendata.cern.ch/api/records/37615>).
- **Proposed / generator:** 0.0012
- **What Matan should open and look for:** YR4 tables; BR ZZ 2.619E-02. JHUGen card DecayMode1=3 (Z → νν), DecayMode2=0 (Z → ee, μμ; no τ).
- **Decision / convention:** D13 (planned 15) — YR4 × PDG Z BRs (Z convention not settled, see Decisions).
- **Alternatives (effect on σ_eff):** YR4 4-fermion column 'H → l+ l- νl νl, l = e or μ' 1.055E-02 instead (WRONG here: it also contains H → WW → ℓνℓν) → +1396.5 %
- **ATLAS cross-check:** No ATLAS counterpart (reverse check, MAPPING.md D).
- **Note:** The Z branching ratios here are now the settled D6 values (pdglive S044, re-checked 31 Oct, unchanged), so the number is unchanged.

## 41. 68741 VBF_HToZZTo2L2Nu_M125 — tier 5 — unchanged from v1

- **What it is:** VBF Higgs, H → ZZ → ℓℓνν with ℓ = e or μ only (no τ).
- **Dataset:** `/VBF_HToZZTo2L2Nu_M125_TuneCP5_13TeV_powheg2_JHUGenV735_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v3/NANOAODSIM` (MiniAOD parent 68740; <https://opendata.cern.ch/record/68741>)
- **Proposed σ_eff = 0.0026662 pb** = 3.782 × 0.02619 × 0.0269176

  - σ(production), YR4: **3.782** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → ZZ): **0.02619** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04
  - 2 × BR(Z → ee + μμ) × BR(Z → νν) = 2 × 0.067294 × 0.20000: **0.0269176** — https://pdglive.lbl.gov/Particle.action?node=S044 — Z DECAY MODES Γ1 e+e−, Γ2 μ+μ−, Γ3 τ+τ−, Γ7 invisible, Γ8 hadrons (re-read 31 Oct 2026, D6) — as printed: (3.3632 ± 0.0042) %, (3.3662 ± 0.0066) %, (3.3696 ± 0.0083) %, (20.000 ± 0.055) %, (69.911 ± 0.056) %

- **Order:** YR4 order of the production mode.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 3.935e+00 pb, negative-weight fraction = 7.240e-04 (<https://opendata.cern.ch/api/records/68740>).
- **Proposed / generator:** 0.0007
- **What Matan should open and look for:** YR4 tables; BR ZZ 2.619E-02. JHUGen card DecayMode1=3 (Z → νν), DecayMode2=0 (Z → ee, μμ; no τ).
- **Decision / convention:** D13 (planned 15) — YR4 × PDG Z BRs (Z convention not settled, see Decisions).
- **Alternatives (effect on σ_eff):** YR4 4-fermion column 'H → l+ l- νl νl, l = e or μ' 1.055E-02 instead (WRONG here: it also contains H → WW → ℓνℓν) → +1396.5 %
- **ATLAS cross-check:** No ATLAS counterpart.
- **Note:** The Z branching ratios here are now the settled D6 values (pdglive S044, re-checked 31 Oct, unchanged), so the number is unchanged.

## 42. 71227 WplusH_HToZZTo4L_M125 — tier 5 — unchanged from v1

- **What it is:** W+H production (W any decay), H → ZZ → 4ℓ (ℓ = e, μ, τ).
- **Dataset:** `/WplusH_HToZZTo4L_M125_TuneCP5_13TeV_powheg2-minlo-HWJ_JHUGenV7011_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 71226; <https://opendata.cern.ch/record/71227>)
- **Proposed σ_eff = 0.00023058 pb** = 0.84 × 0.0002745

  - σ(W+H): **0.84** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → ZZ → 4ℓ, ℓ = e, μ, τ): **0.0002745** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** NNLO QCD + NLO EW.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 8.648e-01 pb, negative-weight fraction = 2.778e-02 (<https://opendata.cern.ch/api/records/71226>).
- **Proposed / generator:** 0.0003
- **What Matan should open and look for:** YR4 WH table; BR page 'Higgs → 4 fermions', H → llll (l = e,μ,τ) = 2.745E-04. JHUGen card DecayMode 8/8.
- **Decision / convention:** D13 (planned 15) — Same BR as our ggH/VBF → 4ℓ (2.745e-4).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS 346449/346450: 1.00.

## 43. 70383 WminusH_HToZZTo4L_M125 — tier 5 — unchanged from v1

- **What it is:** W−H production (W any decay), H → ZZ → 4ℓ (ℓ = e, μ, τ).
- **Dataset:** `/WminusH_HToZZTo4L_M125_TuneCP5_13TeV_powheg2-minlo-HWJ_JHUGenV7011_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 70382; <https://opendata.cern.ch/record/70383>)
- **Proposed σ_eff = 0.000146254 pb** = 0.5328 × 0.0002745

  - σ(W−H): **0.5328** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → ZZ → 4ℓ, ℓ = e, μ, τ): **0.0002745** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) — as printed: bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04

- **Order:** NNLO QCD + NLO EW.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 5.409e-01 pb, negative-weight fraction = 2.544e-02 (<https://opendata.cern.ch/api/records/70382>).
- **Proposed / generator:** 0.0003
- **What Matan should open and look for:** YR4 WH table; BR page 'Higgs → 4 fermions', H → llll (l = e,μ,τ) = 2.745E-04. JHUGen card DecayMode 8/8.
- **Decision / convention:** D13 (planned 15) — Same BR as our ggH/VBF → 4ℓ (2.745e-4).
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** As 71227.

## 44. 37432 GluGluHToMuMu_M125 — tier 5 — NEW (D13)

- **What it is:** Gluon-fusion Higgs, H → μμ.
- **Dataset:** `/GluGluHToMuMu_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 37431; <https://opendata.cern.ch/record/37432>)
- **Proposed σ_eff = 0.010571 pb** = 48.58 × 0.0002176

  - σ(ggF), N3LO: **48.58** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → μμ): **0.0002176** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026 — as printed: μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02

- **Order:** N3LO QCD + NLO EW.
- **k-factor and source:** none (YR4 total × YR4 BR).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 2.146e+01 pb, negative-weight fraction = 5.238e-03 (<https://opendata.cern.ch/api/records/37431>).
- **Proposed / generator:** 0.0005
- **What Matan should open and look for:** YR4 ggF table, 125.00 → 4.858E+01; BR page, table 'H → bb, ττ, μμ, cc', 125.00, H → μμ = 2.176E-04.
- **Decision / convention:** D13 — YR4 at 125.00 GeV × YR4 BR (settled Higgs convention).
- **Alternatives (effect on σ_eff):** generator value (portal) → +202908.1 %
- **ATLAS cross-check:** ATLAS 345097: 0.01057 pb → ATLAS/CMS = 1.000.
- **Note:** Pythia: '25:onIfMatch = 13 -13'. Probe 31 Oct: all 42 branches present.

## 45. 68571 VBFHToMuMu_M125 — tier 5 — NEW (D13)

- **What it is:** VBF Higgs, H → μμ.
- **Dataset:** `/VBFHToMuMu_M125_TuneCP5_withDipoleRecoil_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 68570; <https://opendata.cern.ch/record/68571>)
- **Proposed σ_eff = 0.000822963 pb** = 3.782 × 0.0002176

  - σ(VBF): **3.782** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → μμ): **0.0002176** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026 — as printed: μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02

- **Order:** approx. NNLO QCD + NLO EW.
- **k-factor and source:** none (YR4 total × YR4 BR).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 3.861e+00 pb, negative-weight fraction = 6.713e-04 (<https://opendata.cern.ch/api/records/68570>).
- **Proposed / generator:** 0.0002
- **What Matan should open and look for:** YR4 VBF table, 125.00 → 3.782E+00; BR H → μμ = 2.176E-04.
- **Decision / convention:** D13 — YR4 at 125.00 GeV × YR4 BR (settled Higgs convention).
- **Alternatives (effect on σ_eff):** generator value (portal) → +469058.3 %
- **ATLAS cross-check:** ATLAS 345106: 0.001038 pb → ATLAS/CMS = 1.261. ATLAS's genFiltEff for these H → μμ samples is 0.0002745 = the YR4 H → 4ℓ BR, not the H → μμ BR 2.176E-04 (2.176/2.745 = 0.793): an ATLAS-side metadata slip (its ggF H → μμ 345097 uses 0.0002176 and agrees to 1.000). Cross-check only.
- **Note:** Pythia: '25:onIfMatch = 13 -13'. Probe 31 Oct: all 42 branches present.

## 46. 71295 WplusHToMuMu_M125 — tier 5 — NEW (D13)

- **What it is:** W⁺H (W any decay, POWHEG MiNLO HWJ), H → μμ.
- **Dataset:** `/WplusHToMuMu_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 71294; <https://opendata.cern.ch/record/71295>)
- **Proposed σ_eff = 0.000182784 pb** = 0.84 × 0.0002176

  - σ(W⁺H): **0.84** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → μμ): **0.0002176** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026 — as printed: μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02

- **Order:** NNLO QCD + NLO EW.
- **k-factor and source:** none (YR4 total × YR4 BR).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 8.670e-01 pb, negative-weight fraction = 2.751e-02 (<https://opendata.cern.ch/api/records/71294>).
- **Proposed / generator:** 0.0002
- **What Matan should open and look for:** YR4 WH table, 125.00, column W⁺H = 8.400E-01; BR H → μμ.
- **Decision / convention:** D13 — YR4 at 125.00 GeV × YR4 BR (settled Higgs convention).
- **Alternatives (effect on σ_eff):** generator value (portal) → +474230.4 %
- **ATLAS cross-check:** ATLAS 345104: 0.0002306 pb → ATLAS/CMS = 1.261. ATLAS's genFiltEff for these H → μμ samples is 0.0002745 = the YR4 H → 4ℓ BR, not the H → μμ BR 2.176E-04 (2.176/2.745 = 0.793): an ATLAS-side metadata slip (its ggF H → μμ 345097 uses 0.0002176 and agrees to 1.000). Cross-check only.
- **Note:** POWHEG card: idvecbos 24, vdecaymode 10 (inclusive); Pythia '25:onIfMatch = 13 -13'. Probe 31 Oct: all 42 branches present.

## 47. 70451 WminusHToMuMu_M125 — tier 5 — NEW (D13)

- **What it is:** W⁻H (W any decay), H → μμ.
- **Dataset:** `/WminusHToMuMu_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 70450; <https://opendata.cern.ch/record/70451>)
- **Proposed σ_eff = 0.000115937 pb** = 0.5328 × 0.0002176

  - σ(W⁻H): **0.5328** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → μμ): **0.0002176** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026 — as printed: μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02

- **Order:** NNLO QCD + NLO EW.
- **k-factor and source:** none (YR4 total × YR4 BR).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 5.412e-01 pb, negative-weight fraction = 2.622e-02 (<https://opendata.cern.ch/api/records/70450>).
- **Proposed / generator:** 0.0002
- **What Matan should open and look for:** YR4 WH table, column W⁻H = 5.328E-01; BR H → μμ.
- **Decision / convention:** D13 — YR4 at 125.00 GeV × YR4 BR (settled Higgs convention).
- **Alternatives (effect on σ_eff):** generator value (portal) → +466704.1 %
- **ATLAS cross-check:** ATLAS 345105: 0.0001463 pb → ATLAS/CMS = 1.261. ATLAS's genFiltEff for these H → μμ samples is 0.0002745 = the YR4 H → 4ℓ BR, not the H → μμ BR 2.176E-04 (2.176/2.745 = 0.793): an ATLAS-side metadata slip (its ggF H → μμ 345097 uses 0.0002176 and agrees to 1.000). Cross-check only.
- **Note:** POWHEG card: idvecbos −24, vdecaymode 10; Pythia '25:onIfMatch = 13 -13'. Probe 31 Oct: all 42 branches present.

## 48. 74682 ZHToMuMu_M125 — tier 5 — NEW (D13)

- **What it is:** qq̄ → ZH (Z any decay, POWHEG MiNLO HZJ), H → μμ.
- **Dataset:** `/ZHToMuMu_M125_CP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 74681; <https://opendata.cern.ch/record/74682>)
- **Proposed σ_eff = 0.000165637 pb** = 0.7612 × 0.0002176

  - σ(ZH, all but gg → ZH): **0.7612** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → μμ): **0.0002176** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026 — as printed: μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02

- **Order:** NNLO QCD + NLO EW.
- **k-factor and source:** none (YR4 total × YR4 BR).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 7.891e-01 pb, negative-weight fraction = 2.905e-02 (<https://opendata.cern.ch/api/records/74681>).
- **Proposed / generator:** 0.0002
- **What Matan should open and look for:** YR4 ZH process table: 'all but gg→ZH' = 0.7612; BR H → μμ.
- **Decision / convention:** D13 — YR4 at 125.00 GeV × YR4 BR (settled Higgs convention).
- **Alternatives (effect on σ_eff):** generator value (portal) → +476302.9 %
- **ATLAS cross-check:** ATLAS 345103: 0.0002089 pb → ATLAS/CMS = 1.261. ATLAS's genFiltEff for these H → μμ samples is 0.0002745 = the YR4 H → 4ℓ BR, not the H → μμ BR 2.176E-04 (2.176/2.745 = 0.793): an ATLAS-side metadata slip (its ggF H → μμ 345097 uses 0.0002176 and agrees to 1.000). Cross-check only.
- **Note:** POWHEG card: vdecaymode 10 (Z inclusive), minlo 1; Pythia '25:onIfMatch = 13 -13'. Normalised to 'all but gg → ZH' as 74684 (no gg → ZH → μμ sample exists). Probe 31 Oct: all 42 branches present.

## 49. 37604 GluGluHToZG_ZToLL_M-125 — tier 5 — NEW (D13)

- **What it is:** Gluon-fusion Higgs, H → Zγ with Z → ℓℓ (e, μ, τ).
- **Dataset:** `/GluGluHToZG_ZToLL_M-125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 37602; <https://opendata.cern.ch/record/37604>)
- **Proposed σ_eff = 0.00752104 pb** = 48.58 × 0.001533 × 0.10099

  - σ(ggF): **48.58** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → Zγ): **0.001533** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026 — as printed: μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02
  - BR(Z → ℓℓ) = 0.033632 + 0.033662 + 0.033696 (D6): **0.10099** — https://pdglive.lbl.gov/Particle.action?node=S044 — Z DECAY MODES Γ1 e+e−, Γ2 μ+μ−, Γ3 τ+τ−, Γ7 invisible, Γ8 hadrons (re-read 31 Oct 2026, D6) — as printed: (3.3632 ± 0.0042) %, (3.3662 ± 0.0066) %, (3.3696 ± 0.0083) %, (20.000 ± 0.055) %, (69.911 ± 0.056) %

- **Order:** N3LO QCD + NLO EW.
- **k-factor and source:** none (YR4 total × YR4 BR).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 2.938e+01 pb, negative-weight fraction = 5.164e-03 (<https://opendata.cern.ch/api/records/37602>).
- **Proposed / generator:** 0.0003
- **What Matan should open and look for:** YR4 ggF 4.858E+01; BR page table 'H → gg, γγ, Zγ', 125.00, H → Zγ = 1.533E-03; pdglive S044 Γ1-Γ3.
- **Decision / convention:** D13 — YR4 at 125.00 GeV × YR4 BR × PDG Z → ℓℓ (D6) (settled Higgs convention).
- **Alternatives (effect on σ_eff):** generator value (portal) → +390537.3 %
- **ATLAS cross-check:** ATLAS 345316: 0.007449 pb → ATLAS/CMS = 0.990.
- **Note:** Pythia: '25:onIfMatch = 23 22', '23:onIfAny = 11 13 15', '23:mMin = 50.0' (the Z is cut at m > 50 GeV; the small loss below 50 GeV is not corrected for). Probe 31 Oct: all 42 branches present.

## 50. 68731 VBFHToZG_ZToLL_M-125 — tier 5 — NEW (D13)

- **What it is:** VBF Higgs, H → Zγ with Z → ℓℓ (e, μ, τ).
- **Dataset:** `/VBFHToZG_ZToLL_M-125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 68729; <https://opendata.cern.ch/record/68731>)
- **Proposed σ_eff = 0.00058552 pb** = 3.782 × 0.001533 × 0.10099

  - σ(VBF): **3.782** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → Zγ): **0.001533** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026 — as printed: μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02
  - BR(Z → ℓℓ) (D6): **0.10099** — https://pdglive.lbl.gov/Particle.action?node=S044 — Z DECAY MODES Γ1 e+e−, Γ2 μ+μ−, Γ3 τ+τ−, Γ7 invisible, Γ8 hadrons (re-read 31 Oct 2026, D6) — as printed: (3.3632 ± 0.0042) %, (3.3662 ± 0.0066) %, (3.3696 ± 0.0083) %, (20.000 ± 0.055) %, (69.911 ± 0.056) %

- **Order:** approx. NNLO QCD + NLO EW.
- **k-factor and source:** none (YR4 total × YR4 BR).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 3.861e+00 pb, negative-weight fraction = 5.926e-04 (<https://opendata.cern.ch/api/records/68729>).
- **Proposed / generator:** 0.0002
- **What Matan should open and look for:** YR4 VBF 3.782E+00; BR H → Zγ 1.533E-03; pdglive S044.
- **Decision / convention:** D13 — YR4 at 125.00 GeV × YR4 BR × PDG Z → ℓℓ (D6) (settled Higgs convention).
- **Alternatives (effect on σ_eff):** generator value (portal) → +659313.4 %
- **ATLAS cross-check:** ATLAS 345833: 0.0005856 pb → ATLAS/CMS = 1.000.
- **Note:** Pythia: '25:onIfMatch = 23 22', '23:onIfAny = 11 13 15', '23:mMin = 50.0'. Probe 31 Oct: all 42 branches present.

## 51. 71145 WplusH_HToZG_WToAll_M-125 — tier 5 — NEW (D13)

- **What it is:** W⁺H (W any decay), H → Zγ (Z any decay).
- **Dataset:** `/WplusH_HToZG_WToAll_M-125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 71144; <https://opendata.cern.ch/record/71145>)
- **Proposed σ_eff = 0.00128772 pb** = 0.84 × 0.001533

  - σ(W⁺H): **0.84** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → Zγ): **0.001533** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026 — as printed: μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02

- **Order:** NNLO QCD + NLO EW.
- **k-factor and source:** none (YR4 total × YR4 BR).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 8.668e-01 pb, negative-weight fraction = 2.993e-02 (<https://opendata.cern.ch/api/records/71144>).
- **Proposed / generator:** 0.0015
- **What Matan should open and look for:** YR4 WH W⁺H 8.400E-01; BR H → Zγ 1.533E-03.
- **Decision / convention:** D13 — YR4 at 125.00 GeV × YR4 BR (settled Higgs convention).
- **Alternatives (effect on σ_eff):** generator value (portal) → +67212.8 %
- **ATLAS cross-check:** ATLAS 345321: 0.001288 pb → ATLAS/CMS = 1.000.
- **Note:** POWHEG card: vdecaymode 10; Pythia only '25:onIfMatch = 23 22' (no Z-decay restriction, so the Z from H decays inclusively, consistent with the name 'WToAll'). No Z BR applied. Probe 31 Oct: all 42 branches present.

## 52. 70301 WminusH_HToZG_WToAll_M-125 — tier 5 — NEW (D13)

- **What it is:** W⁻H (W any decay), H → Zγ (Z any decay).
- **Dataset:** `/WminusH_HToZG_WToAll_M-125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 70300; <https://opendata.cern.ch/record/70301>)
- **Proposed σ_eff = 0.000816782 pb** = 0.5328 × 0.001533

  - σ(W⁻H): **0.5328** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → Zγ): **0.001533** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026 — as printed: μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02

- **Order:** NNLO QCD + NLO EW.
- **k-factor and source:** none (YR4 total × YR4 BR).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 5.413e-01 pb, negative-weight fraction = 2.572e-02 (<https://opendata.cern.ch/api/records/70300>).
- **Proposed / generator:** 0.0015
- **What Matan should open and look for:** YR4 WH W⁻H 5.328E-01; BR H → Zγ.
- **Decision / convention:** D13 — YR4 at 125.00 GeV × YR4 BR (settled Higgs convention).
- **Alternatives (effect on σ_eff):** generator value (portal) → +66172.2 %
- **ATLAS cross-check:** ATLAS 345320: 0.0008168 pb → ATLAS/CMS = 1.000.
- **Note:** As 71145 (idvecbos −24). Probe 31 Oct: all 42 branches present.

## 53. 74292 ZH_HToZG_ZToAll_M-125 — tier 5 — NEW (D13)

- **What it is:** qq̄ → ZH (Z any decay), H → Zγ (Z any decay).
- **Dataset:** `/ZH_HToZG_ZToAll_M-125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 74291; <https://opendata.cern.ch/record/74292>)
- **Proposed σ_eff = 0.00116692 pb** = 0.7612 × 0.001533

  - σ(ZH, all but gg → ZH): **0.7612** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); page rev. r29, 2024-07-24; re-read 31 Oct 2026 — as printed: ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227 (pb)
  - BR(H → Zγ): **0.001533** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: table 'H → bb, H → ττ, H → μμ, H → cc' (column H → μμ, BR); table 'H → gg, H → γγ, H → Zγ' (column H → Zγ, BR); table 'H → WW, H → ZZ' (column H → ZZ); re-read 31 Oct 2026 — as printed: μμ 2.176E-04; Zγ 1.533E-03; ZZ 2.619E-02

- **Order:** NNLO QCD + NLO EW.
- **k-factor and source:** none (YR4 total × YR4 BR).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 1.0 (not multiplied in); total_value = 7.891e-01 pb, negative-weight fraction = 2.864e-02 (<https://opendata.cern.ch/api/records/74291>).
- **Proposed / generator:** 0.0015
- **What Matan should open and look for:** YR4 ZH 'all but gg→ZH' 0.7612; BR H → Zγ.
- **Decision / convention:** D13 — YR4 at 125.00 GeV × YR4 BR (settled Higgs convention).
- **Alternatives (effect on σ_eff):** generator value (portal) → +67522.5 %
- **ATLAS cross-check:** ATLAS 345322: 0.001167 pb → ATLAS/CMS = 1.000.
- **Note:** POWHEG card: vdecaymode 10, minlo 1; Pythia only '25:onIfMatch = 23 22'. No Z BR applied. Probe 31 Oct: all 42 branches present.

## 54. 40062 GluGluToZH_HToZZTo4L_M125 — tier 5 — NEW (D13) — DECISION NEEDED on the value

- **What it is:** gg → ZH (associated Z any decay), H → ZZ → ℓℓ + anything (ℓ = e, μ, τ), JHUGen, with a JHUGen 4-lepton filter.
- **Dataset:** `/GluGluToZH_HToZZTo4L_M125_TuneCP5_13TeV-jhugenv723-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 40061; <https://opendata.cern.ch/record/40062>)
- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):

  - (a) portal total_value as is: **0.000233 pb** — portal record https://opendata.cern.ch/api/records/40061 (UNVERIFIED whether the filter is included)
  - (b) portal total_value × portal 'matching efficiency' 0.2 (read as the filter efficiency): **4.66e-05 pb** — portal (interpretation UNVERIFIED)
  - (c) YR4 0.1227 × BR(H → ZZ) 0.02619 × BR(Z → ℓℓ) 0.10099 × ε(4ℓ) with ε ESTIMATED as P(at least one of the two other Zs → ℓℓ) = 1 − (1 − 0.10099)² = 0.1918: **6.22392e-05 pb** — YR4_XS, YR4_BR2, PDG_Z; ε is an ESTIMATE (ignores the filter's lepton definition, e.g. whether τ count)

- **Order:** LO (JHUGen gg → ZH).
- **k-factor and source:** see options.
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.2 (not multiplied in); total_value = 2.330e-04 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/40061>).
- **What Matan should open and look for:** The two JHUGen cards (fetched 31 Oct from the genproductions links in the record, because the portal copies return HTTP 404): `evidence/cards/40062/ggZH_NNPDF31_13TeV_M125.input` ('Process=51 VH_PC=gg DecayMode1=9': associated Z → anything) and `ZZ2l2any_withtaus_filter4l.input` ('DecayMode1=8 DecayMode2=9 FilterNLept=4 WriteFailedEvents=2': H → Z(→ ℓℓ, ℓ = e, μ, τ) Z(→ anything), keep events with 4 leptons).
- **Decision / convention:** D13 — No settled convention: the sample is not 'H → 4ℓ'. Its σ needs the efficiency of the 4-lepton filter, which is not published.
- **Alternatives:** none with a public source found.
- **ATLAS cross-check:** ATLAS 345066 (gg → ZH, Z inclusive, H → ZZ → 4ℓ): 3.37e-05 pb — a different selection (no filter), not like-for-like.
- **Note:** The portal record is odd: total_value 2.330e-04 pb, 'matching efficiency' 0.2 on a JHUGen sample (the same pattern as the ZH → ZZ filtered samples left out on 26 Oct), total_value_uncertainty 2.330e+10. Probe 31 Oct: every genWeight = 1.0, no zero weights, so failed events are not in the NanoAOD and the filter efficiency cannot be measured from it. The sample is tiny: any option gives ≲ 4 events in 16.4 fb⁻¹ before selection.

# Tier 6

## 55. 74894 ZJetsToNuNu_HT-100To200 — tier 6 — NEW (D11) — DECISION NEEDED on the value

- **What it is:** Z → νν (3 flavours) + 0-4 partons, LO MadGraph MLM, generator-level jet HT 100-200 GeV.
- **Dataset:** `/ZJetsToNuNu_HT-100To200_TuneCP5_13TeV-madgraphMLM-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 74893; <https://opendata.cern.ch/record/74894>)
- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):

  - (a) generator LO value (portal): **266.3 pb** — portal record https://opendata.cern.ch/api/records/74893
  - (b) generator × 1.23 (the k the RazorAnalyzer table applies to these HT bins): **327.549 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_ZNN (SECONDARY; origin of 1.23 not stated))
  - (c) generator × k_DY = 5765.4 / 5396 = 1.0685 (our DY NNLO normalisation ÷ the CP5 LO inclusive DY M-50 madgraphMLM portal value, MiniAOD 35670): **284.53 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_DY + portal 35670; assumes the Z → νν and Z → ℓℓ LO/NNLO ratios are equal)

- **Order:** LO (MLM-merged, 0-4 partons).
- **k-factor and source:** options (b), (c).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.1 (not multiplied in); total_value = 2.663e+02 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/74893>).
- **What Matan should open and look for:** Card `evidence/cards/74894/*run_card.dat`: htjmin = 100, htjmax = 200; RazorAnalyzer line 96 for (b); RazorAnalyzer line 90 and the portal record 35670 for (c).
- **Decision / convention:** D11 — No settled convention for an LO HT-binned V+jets set (our W and DY are NLO). The bins are used as they are (no stitching, D11). D6 BRs do not enter: the generator produces Z → νν directly; in (c) only the ratio NNLO/LO of the same boson enters.
- **Alternatives (effect on σ_eff):** option (b) × 1.23 → +23.0 %; option (c) × 1.0685 → +6.8 %
- **ATLAS cross-check:** ATLAS Z → νν (700335-700337, Sherpa NLO, kFactor 1, b/c/light filters summed) = 446.8 pb, sliced differently ('pTV2' in the name; the slicing is not explained in the metadata): no like-for-like ATLAS value for an HT bin. The sum of the 7 CMS bins at option (a) is 353.0 pb.
- **Note:** The RazorAnalyzer LO value for the older CUETP8M1 sample of this bin was 280.35 pb (vs 266.3 pb here, CP5). Probe 31 Oct: all 42 branches present, no negative weights; LHE_HT in file 0 lies inside 100-200 GeV (min/max in PLAN_v2_summary.md). Bins contiguous and exclusive from 100 GeV (cards).

## 56. 74898 ZJetsToNuNu_HT-200To400 — tier 6 — NEW (D11) — DECISION NEEDED on the value

- **What it is:** Z → νν (3 flavours) + 0-4 partons, LO MadGraph MLM, generator-level jet HT 200-400 GeV.
- **Dataset:** `/ZJetsToNuNu_HT-200To400_TuneCP5_13TeV-madgraphMLM-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 74897; <https://opendata.cern.ch/record/74898>)
- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):

  - (a) generator LO value (portal): **73.02 pb** — portal record https://opendata.cern.ch/api/records/74897
  - (b) generator × 1.23 (the k the RazorAnalyzer table applies to these HT bins): **89.8146 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_ZNN (SECONDARY; origin of 1.23 not stated))
  - (c) generator × k_DY = 5765.4 / 5396 = 1.0685 (our DY NNLO normalisation ÷ the CP5 LO inclusive DY M-50 madgraphMLM portal value, MiniAOD 35670): **78.0188 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_DY + portal 35670; assumes the Z → νν and Z → ℓℓ LO/NNLO ratios are equal)

- **Order:** LO (MLM-merged, 0-4 partons).
- **k-factor and source:** options (b), (c).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.1 (not multiplied in); total_value = 7.302e+01 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/74897>).
- **What Matan should open and look for:** Card `evidence/cards/74898/*run_card.dat`: htjmin = 200, htjmax = 400; RazorAnalyzer line 97 for (b); RazorAnalyzer line 90 and the portal record 35670 for (c).
- **Decision / convention:** D11 — No settled convention for an LO HT-binned V+jets set (our W and DY are NLO). The bins are used as they are (no stitching, D11). D6 BRs do not enter: the generator produces Z → νν directly; in (c) only the ratio NNLO/LO of the same boson enters.
- **Alternatives (effect on σ_eff):** option (b) × 1.23 → +23.0 %; option (c) × 1.0685 → +6.8 %
- **ATLAS cross-check:** ATLAS Z → νν (700335-700337, Sherpa NLO, kFactor 1, b/c/light filters summed) = 446.8 pb, sliced differently ('pTV2' in the name; the slicing is not explained in the metadata): no like-for-like ATLAS value for an HT bin. The sum of the 7 CMS bins at option (a) is 353.0 pb.
- **Note:** The RazorAnalyzer LO value for the older CUETP8M1 sample of this bin was 77.67 pb (vs 73.02 pb here, CP5). Probe 31 Oct: all 42 branches present, no negative weights; LHE_HT in file 0 lies inside 200-400 GeV (min/max in PLAN_v2_summary.md). Bins contiguous and exclusive from 100 GeV (cards).

## 57. 74902 ZJetsToNuNu_HT-400To600 — tier 6 — NEW (D11) — DECISION NEEDED on the value

- **What it is:** Z → νν (3 flavours) + 0-4 partons, LO MadGraph MLM, generator-level jet HT 400-600 GeV.
- **Dataset:** `/ZJetsToNuNu_HT-400To600_TuneCP5_13TeV-madgraphMLM-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 74901; <https://opendata.cern.ch/record/74902>)
- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):

  - (a) generator LO value (portal): **9.914 pb** — portal record https://opendata.cern.ch/api/records/74901
  - (b) generator × 1.23 (the k the RazorAnalyzer table applies to these HT bins): **12.1942 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_ZNN (SECONDARY; origin of 1.23 not stated))
  - (c) generator × k_DY = 5765.4 / 5396 = 1.0685 (our DY NNLO normalisation ÷ the CP5 LO inclusive DY M-50 madgraphMLM portal value, MiniAOD 35670): **10.5927 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_DY + portal 35670; assumes the Z → νν and Z → ℓℓ LO/NNLO ratios are equal)

- **Order:** LO (MLM-merged, 0-4 partons).
- **k-factor and source:** options (b), (c).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.1 (not multiplied in); total_value = 9.914e+00 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/74901>).
- **What Matan should open and look for:** Card `evidence/cards/74902/*run_card.dat`: htjmin = 400, htjmax = 600; RazorAnalyzer line 98 for (b); RazorAnalyzer line 90 and the portal record 35670 for (c).
- **Decision / convention:** D11 — No settled convention for an LO HT-binned V+jets set (our W and DY are NLO). The bins are used as they are (no stitching, D11). D6 BRs do not enter: the generator produces Z → νν directly; in (c) only the ratio NNLO/LO of the same boson enters.
- **Alternatives (effect on σ_eff):** option (b) × 1.23 → +23.0 %; option (c) × 1.0685 → +6.8 %
- **ATLAS cross-check:** ATLAS Z → νν (700335-700337, Sherpa NLO, kFactor 1, b/c/light filters summed) = 446.8 pb, sliced differently ('pTV2' in the name; the slicing is not explained in the metadata): no like-for-like ATLAS value for an HT bin. The sum of the 7 CMS bins at option (a) is 353.0 pb.
- **Note:** The RazorAnalyzer LO value for the older CUETP8M1 sample of this bin was 10.73 pb (vs 9.914 pb here, CP5). Probe 31 Oct: all 42 branches present, no negative weights; LHE_HT in file 0 lies inside 400-600 GeV (min/max in PLAN_v2_summary.md). Bins contiguous and exclusive from 100 GeV (cards).

## 58. 74904 ZJetsToNuNu_HT-600To800 — tier 6 — NEW (D11) — DECISION NEEDED on the value

- **What it is:** Z → νν (3 flavours) + 0-4 partons, LO MadGraph MLM, generator-level jet HT 600-800 GeV.
- **Dataset:** `/ZJetsToNuNu_HT-600To800_TuneCP5_13TeV-madgraphMLM-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 74903; <https://opendata.cern.ch/record/74904>)
- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):

  - (a) generator LO value (portal): **2.409 pb** — portal record https://opendata.cern.ch/api/records/74903
  - (b) generator × 1.23 (the k the RazorAnalyzer table applies to these HT bins): **2.96307 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_ZNN (SECONDARY; origin of 1.23 not stated))
  - (c) generator × k_DY = 5765.4 / 5396 = 1.0685 (our DY NNLO normalisation ÷ the CP5 LO inclusive DY M-50 madgraphMLM portal value, MiniAOD 35670): **2.57392 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_DY + portal 35670; assumes the Z → νν and Z → ℓℓ LO/NNLO ratios are equal)

- **Order:** LO (MLM-merged, 0-4 partons).
- **k-factor and source:** options (b), (c).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.1 (not multiplied in); total_value = 2.409e+00 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/74903>).
- **What Matan should open and look for:** Card `evidence/cards/74904/*run_card.dat`: htjmin = 600, htjmax = 800; RazorAnalyzer line 100 for (b); RazorAnalyzer line 90 and the portal record 35670 for (c).
- **Decision / convention:** D11 — No settled convention for an LO HT-binned V+jets set (our W and DY are NLO). The bins are used as they are (no stitching, D11). D6 BRs do not enter: the generator produces Z → νν directly; in (c) only the ratio NNLO/LO of the same boson enters.
- **Alternatives (effect on σ_eff):** option (b) × 1.23 → +23.0 %; option (c) × 1.0685 → +6.8 %
- **ATLAS cross-check:** ATLAS Z → νν (700335-700337, Sherpa NLO, kFactor 1, b/c/light filters summed) = 446.8 pb, sliced differently ('pTV2' in the name; the slicing is not explained in the metadata): no like-for-like ATLAS value for an HT bin. The sum of the 7 CMS bins at option (a) is 353.0 pb.
- **Note:** The RazorAnalyzer LO value for the older CUETP8M1 sample of this bin was 2.559 pb (vs 2.409 pb here, CP5). Probe 31 Oct: all 42 branches present, no negative weights; LHE_HT in file 0 lies inside 600-800 GeV (min/max in PLAN_v2_summary.md). Bins contiguous and exclusive from 100 GeV (cards).

## 59. 74906 ZJetsToNuNu_HT-800To1200 — tier 6 — NEW (D11) — DECISION NEEDED on the value

- **What it is:** Z → νν (3 flavours) + 0-4 partons, LO MadGraph MLM, generator-level jet HT 800-1200 GeV.
- **Dataset:** `/ZJetsToNuNu_HT-800To1200_TuneCP5_13TeV-madgraphMLM-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 74905; <https://opendata.cern.ch/record/74906>)
- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):

  - (a) generator LO value (portal): **1.077 pb** — portal record https://opendata.cern.ch/api/records/74905
  - (b) generator × 1.23 (the k the RazorAnalyzer table applies to these HT bins): **1.32471 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_ZNN (SECONDARY; origin of 1.23 not stated))
  - (c) generator × k_DY = 5765.4 / 5396 = 1.0685 (our DY NNLO normalisation ÷ the CP5 LO inclusive DY M-50 madgraphMLM portal value, MiniAOD 35670): **1.15073 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_DY + portal 35670; assumes the Z → νν and Z → ℓℓ LO/NNLO ratios are equal)

- **Order:** LO (MLM-merged, 0-4 partons).
- **k-factor and source:** options (b), (c).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.1 (not multiplied in); total_value = 1.077e+00 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/74905>).
- **What Matan should open and look for:** Card `evidence/cards/74906/*run_card.dat`: htjmin = 800, htjmax = 1200; RazorAnalyzer line 101 for (b); RazorAnalyzer line 90 and the portal record 35670 for (c).
- **Decision / convention:** D11 — No settled convention for an LO HT-binned V+jets set (our W and DY are NLO). The bins are used as they are (no stitching, D11). D6 BRs do not enter: the generator produces Z → νν directly; in (c) only the ratio NNLO/LO of the same boson enters.
- **Alternatives (effect on σ_eff):** option (b) × 1.23 → +23.0 %; option (c) × 1.0685 → +6.8 %
- **ATLAS cross-check:** ATLAS Z → νν (700335-700337, Sherpa NLO, kFactor 1, b/c/light filters summed) = 446.8 pb, sliced differently ('pTV2' in the name; the slicing is not explained in the metadata): no like-for-like ATLAS value for an HT bin. The sum of the 7 CMS bins at option (a) is 353.0 pb.
- **Note:** The RazorAnalyzer LO value for the older CUETP8M1 sample of this bin was 1.1796 pb (vs 1.077 pb here, CP5). Probe 31 Oct: all 42 branches present, no negative weights; LHE_HT in file 0 lies inside 800-1200 GeV (min/max in PLAN_v2_summary.md). Bins contiguous and exclusive from 100 GeV (cards).

## 60. 74896 ZJetsToNuNu_HT-1200To2500 — tier 6 — NEW (D11) — DECISION NEEDED on the value

- **What it is:** Z → νν (3 flavours) + 0-4 partons, LO MadGraph MLM, generator-level jet HT 1200-2500 GeV.
- **Dataset:** `/ZJetsToNuNu_HT-1200To2500_TuneCP5_13TeV-madgraphMLM-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 74895; <https://opendata.cern.ch/record/74896>)
- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):

  - (a) generator LO value (portal): **0.2495 pb** — portal record https://opendata.cern.ch/api/records/74895
  - (b) generator × 1.23 (the k the RazorAnalyzer table applies to these HT bins): **0.306885 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_ZNN (SECONDARY; origin of 1.23 not stated))
  - (c) generator × k_DY = 5765.4 / 5396 = 1.0685 (our DY NNLO normalisation ÷ the CP5 LO inclusive DY M-50 madgraphMLM portal value, MiniAOD 35670): **0.26658 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_DY + portal 35670; assumes the Z → νν and Z → ℓℓ LO/NNLO ratios are equal)

- **Order:** LO (MLM-merged, 0-4 partons).
- **k-factor and source:** options (b), (c).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.1 (not multiplied in); total_value = 2.495e-01 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/74895>).
- **What Matan should open and look for:** Card `evidence/cards/74896/*run_card.dat`: htjmin = 1200, htjmax = 2500; RazorAnalyzer line 102 for (b); RazorAnalyzer line 90 and the portal record 35670 for (c).
- **Decision / convention:** D11 — No settled convention for an LO HT-binned V+jets set (our W and DY are NLO). The bins are used as they are (no stitching, D11). D6 BRs do not enter: the generator produces Z → νν directly; in (c) only the ratio NNLO/LO of the same boson enters.
- **Alternatives (effect on σ_eff):** option (b) × 1.23 → +23.0 %; option (c) × 1.0685 → +6.8 %
- **ATLAS cross-check:** ATLAS Z → νν (700335-700337, Sherpa NLO, kFactor 1, b/c/light filters summed) = 446.8 pb, sliced differently ('pTV2' in the name; the slicing is not explained in the metadata): no like-for-like ATLAS value for an HT bin. The sum of the 7 CMS bins at option (a) is 353.0 pb.
- **Note:** The RazorAnalyzer LO value for the older CUETP8M1 sample of this bin was 0.28833 pb (vs 0.2495 pb here, CP5). Probe 31 Oct: all 42 branches present, no negative weights; LHE_HT in file 0 lies inside 1200-2500 GeV (min/max in PLAN_v2_summary.md). Bins contiguous and exclusive from 100 GeV (cards).

## 61. 74900 ZJetsToNuNu_HT-2500ToInf — tier 6 — NEW (D11) — DECISION NEEDED on the value

- **What it is:** Z → νν (3 flavours) + 0-4 partons, LO MadGraph MLM, generator-level jet HT 2500-Inf GeV.
- **Dataset:** `/ZJetsToNuNu_HT-2500ToInf_TuneCP5_13TeV-madgraphMLM-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 74899; <https://opendata.cern.ch/record/74900>)
- **Proposed σ_eff: DECISION NEEDED** — options (the cost table uses (a) as a placeholder):

  - (a) generator LO value (portal): **0.005614 pb** — portal record https://opendata.cern.ch/api/records/74899
  - (b) generator × 1.23 (the k the RazorAnalyzer table applies to these HT bins): **0.00690522 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_ZNN (SECONDARY; origin of 1.23 not stated))
  - (c) generator × k_DY = 5765.4 / 5396 = 1.0685 (our DY NNLO normalisation ÷ the CP5 LO inclusive DY M-50 madgraphMLM portal value, MiniAOD 35670): **0.00599832 pb** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat (RAZOR_DY + portal 35670; assumes the Z → νν and Z → ℓℓ LO/NNLO ratios are equal)

- **Order:** LO (MLM-merged, 0-4 partons).
- **k-factor and source:** options (b), (c).
- **Filter / matching efficiency (portal):** filter = 1.000e+00, matching = 0.1 (not multiplied in); total_value = 5.614e-03 pb, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/74899>).
- **What Matan should open and look for:** Card `evidence/cards/74900/*run_card.dat`: htjmin = 2500, htjmax = 1d5; RazorAnalyzer line 103 for (b); RazorAnalyzer line 90 and the portal record 35670 for (c).
- **Decision / convention:** D11 — No settled convention for an LO HT-binned V+jets set (our W and DY are NLO). The bins are used as they are (no stitching, D11). D6 BRs do not enter: the generator produces Z → νν directly; in (c) only the ratio NNLO/LO of the same boson enters.
- **Alternatives (effect on σ_eff):** option (b) × 1.23 → +23.0 %; option (c) × 1.0685 → +6.8 %
- **ATLAS cross-check:** ATLAS Z → νν (700335-700337, Sherpa NLO, kFactor 1, b/c/light filters summed) = 446.8 pb, sliced differently ('pTV2' in the name; the slicing is not explained in the metadata): no like-for-like ATLAS value for an HT bin. The sum of the 7 CMS bins at option (a) is 353.0 pb.
- **Note:** The RazorAnalyzer LO value for the older CUETP8M1 sample of this bin was 0.006945 pb (vs 0.005614 pb here, CP5). Probe 31 Oct: all 42 branches present, no negative weights; LHE_HT in file 0 lies inside 2500-Inf GeV (min/max in PLAN_v2_summary.md). Bins contiguous and exclusive from 100 GeV (cards).

## Numbers that could not be verified

- 75567: the meaning of the POWHEG flag `leptons-nu` (which lepton and neutrino flavours) — the POWHEG-BOX ZZ manual was not opened (UNVERIFIED); the share of its σ at low m(ℓℓ) is not measured.
- 40062: the 4-lepton filter efficiency (not published; option (c) uses an ESTIMATE); the meaning of its portal 'matching efficiency' 0.2 (UNVERIFIED); JHUGen v7.2.3 flag meanings taken from the current JHUGen master (UNVERIFIED for that version).
- 35999 / 35987 / 35993: ATLAS's generator-level cuts (not in the public metadata: UNKNOWN); the size of the s-channel diboson part in the CMS samples (not measured); SMP-17-011 calls its LO 'ℓ = e, μ or τ' but its measurement 'per channel' — the ratio 6.23 / 6.81 is taken as printed, the ambiguity is not resolved.
- Z → νν option (b): the origin of the RazorAnalyzer 1.23 (not stated in the file; SECONDARY). Option (c) assumes equal NNLO/LO ratios for Z → νν and Z → ℓℓ (not shown by any source).
- Unchanged v1 cards: sources read 26 Oct, not re-read today (except PDG W/Z, YR4 and the old Top WG page, which were re-read and are unchanged).
