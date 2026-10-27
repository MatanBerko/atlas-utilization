## A. One row per ATLAS process

ATLAS σ = Σ cross_section_pb × kFactor × genFiltEff over the **nominal** DSIDs (atlasopenmagic 2024r-pp), CROSS-CHECK only. CMS σ_eff: registry v3 for delivered samples, `evidence/xsec_proposals.json` for proposed ones (PROPOSED, not decided). Ratio = ATLAS / CMS; ⚑ = outside 0.7-1.4. ATLAS files = number of file URLs (`atom.get_urls(dsid)`), nominal DSIDs only. All values VERIFIED BY RUNNING (`mapping.py`).


### V+jets (10 processes)

| ATLAS process | ATLAS DSIDs (nominal) | files | ATLAS σ×k×filter [pb] | CMS status | CMS records | CMS σ_eff [pb] | ATLAS/CMS | note |
|---|---|---:|---:|---|---|---:|---:|---|
| Z/γ* → ℓℓ + jets (ee, μμ, ττ), mass range not stated in the metadata | 700320–700794 (9) | 2135 | 6686 | in the 25-26 Oct delivery | 35669 | 5765 | 1.16 | ee and μμ: Sherpa 2.2.11; ττ: Sherpa 2.2.14. CMS DY M-50 holds all three flavours in one sample.; b/c-hadron filter split per flavour: BFilter / CFilterBVeto / CVetoBVeto (exclusive slices, summed) |
| Z/γ* → ℓℓ + jets, 10 < m(ℓℓ) < 40 GeV (ee, μμ, ττ) | 700467–700903 (9) | 1076 | 9479 | in the 25-26 Oct delivery | 35631 | 1.861e+04 | **0.51** ⚑ | different phase space: ATLAS 10-40 GeV with a multi-lepton filter (ee, μμ) vs CMS 10-50 GeV unfiltered; b/c-hadron filter split per flavour; ee/μμ names also carry 'pT5' (meaning UNKNOWN from the metadata) and list a MultiLeptonFilter |
| Z → νν + jets | 700335, 700336, 700337 | 154 | 446.8 | exists on the CMS portal, not proposed | 74894, 74898, 74902, 74904, 74906, 74896, 74900, 73752, 73746, 73748, 73750, 73766, 73760, 73762, 73764 | — | — | not proposed: D11 (no prompt leptons). CMS has HT-binned LO (no HT < 100 bin) and pT-binned NLO, no inclusive sample.; b/c-hadron filter split |
| W → ℓν + jets (eν, μν, τν; τ split into leptonic / hadronic τ decays) | 700338–700349 (12) | 6627 | 6.539e+04 | proposed in the plan | 69715 (T1), 69717 (T1), 69719 (T1) | 6.153e+04 | 1.06 | CMS set decided by Matan (D1: the three NLO jet-binned pieces, each alone; D2: RazorAnalyzer normalisation).; b/c-hadron filter split per flavour; τν further split L (leptonic τ) / H (hadronic τ) |
| electroweak Z/γ*(→ ℓℓ) + 2 jets (VBF-like, ee, μμ, ττ) | 700358, 700359, 700360 | 3 | 2.338 | exists on the CMS portal, not proposed | 35999 | — | — | not in the plan. CMS DY+jets samples are QCD production and do not contain this. |
| electroweak W(→ ℓν) + 2 jets | 700362, 700363, 700364 | 11 | 25.51 | exists on the CMS portal, not proposed | 35987, 35993 | — | — | not in the plan (§2a lists them as available). |
| electroweak Z(→ νν) + 2 jets | 700361 | 1 | 3.657 | exists on the CMS portal, not proposed | 36001 | — | — | no prompt leptons |
| W → qq' + jets, pT(W) > 200 GeV | 700843 | 130 | 143.2 | exists on the CMS portal, not proposed | 69751, 69753, 69755, 69757 | — | — | no leptons; CMS WJetsToQQ is HT-binned from 200 GeV (different slicing variable) |
| Z → qq + jets, pT(Z) > 200 GeV | 700849 | 29 | 47.47 | exists on the CMS portal, not proposed | 74912, 74914, 74916, 74918 | — | — | no leptons; CMS ZJetsToQQ is HT-binned from 200 GeV |
| Z → bb + jets, pT(Z) > 200 GeV | 700855 | 5 | 13.35 | no CMS 2016 sample found | — | — | — | ZJetsToBB not observed (fetch_cms_extra.py); whether CMS ZJetsToQQ includes b quarks is UNVERIFIED |

### diboson (17 processes)

| ATLAS process | ATLAS DSIDs (nominal) | files | ATLAS σ×k×filter [pb] | CMS status | CMS records | CMS σ_eff [pb] | ATLAS/CMS | note |
|---|---|---:|---:|---|---|---:|---:|---|
| WW → ℓνqq | 700488 | 22 | 47.92 | proposed in the plan | 72658 (T2) | 52.36 | 0.92 |  |
| WZ → ℓν qq (incl. Z → bb) | 700489, 700490 | 9 | 10.99 | proposed in the plan | 72738 (T2) | 10.16 | 1.08 | Z → qq and Z → bb in separate DSIDs (exclusive, summed) |
| WZ → qq νν | 700491 | 4 | 6.544 | no CMS 2016 sample found | — | — | — | WZTo2Q2Nu / WZToQQ2Nu not observed; no leptons |
| WZ → qq ℓℓ | 700492 | 3 | 3.305 | proposed in the plan | 72742 (T2) | 7.133 | **0.46** ⚑ | different phase space: the CMS sample includes γ* → ℓℓ down to m(ℓℓ) = 4 GeV (PLAN D9) |
| ZZ → qq ℓℓ (incl. Z → bb) | 700493, 700494 | 2 | 2.127 | proposed in the plan | 75573 (T2) | 4.311 | **0.49** ⚑ | different phase space: the CMS sample includes γ* → ℓℓ down to m(ℓℓ) = 4 GeV (as WZ → qqℓℓ); Z → qq and Z → bb in separate DSIDs |
| ZZ → qq νν (incl. Z → bb) | 700495, 700496 | 3 | 4.204 | exists on the CMS portal, not proposed | 75571 | — | — | no leptons; not proposed; Z → qq and Z → bb in separate DSIDs |
| VV → ℓℓℓℓ (Sherpa 2.2.12) | 700600 | 1 | 1.297 | in the 25-26 Oct delivery | 75589 | 1.544 | 0.84 |  |
| VV → ℓℓℓν | 700601 | 2 | 4.661 | in the 25-26 Oct delivery | 72752 | 5.789 | 0.81 |  |
| VV → ℓℓνν, opposite sign (WW and ZZ → ℓℓνν together) | 700602 | 6 | 12.08 | in the 25-26 Oct delivery | 72676 | 12.71 | 0.95 | the ATLAS sample also holds ZZ → ℓℓνν; CMS has WW → 2ℓ2ν only (ZZTo2L2Nu 75567 excluded, D14) |
| W±W± → ℓ±ℓ±νν, QCD-induced, 0-1 jets | 700603 | 1 | 0.02221 | exists on the CMS portal, not proposed | 71642 | — | — | CMS WpWpJJ_QCD (madgraph) exists, not proposed |
| VV → ℓννν | 700604 | 2 | 3.108 | proposed in the plan | 72740 (T2) | 3.789 | 0.82 |  |
| VV → νννν | 700605 | 1 | 0.5776 | no CMS 2016 sample found | — | — | — | ZZTo4Nu not observed (PLAN §2d); no leptons |
| electroweak ℓℓℓℓ jj (VBS, incl. triboson-like diagrams) | 700587 | 1 | 0.01151 | exists on the CMS portal, not proposed | 75561 | — | — | CMS ZZJJTo4L_EWKnotop exists, not proposed |
| electroweak ℓℓℓν jj (VBS) | 700588 | 1 | 0.04845 | exists on the CMS portal, not proposed | 69771, 72728 (opt.) | — | — | CMS WLLJJ_WToLNu_EWK and WZJJ_EWK exist; which matches the ATLAS phase space is UNVERIFIED |
| electroweak ℓℓνν jj, opposite sign (VBS) | 700589 | 1 | 0.1934 | exists on the CMS portal, not proposed | 72648 | — | — | CMS WWJJToLNuLNu_EWK_noTop exists, not proposed |
| electroweak ℓ±ℓ±νν jj, same sign (VBS) | 700590 | 1 | 0.0456 | exists on the CMS portal, not proposed | 71638 (opt.) | — | — | CMS WpWpJJ_EWK is in the plan as 'optional' (no proposal) |
| EW-QCD interference terms of the four VBS channels | 700591, 700592, 700593, 700594 | 4 | 0.01973 | no CMS 2016 sample found | — | — | — | no CMS interference sample observed in the plan's searches (not searched by name) |

### triboson (4 processes)

| ATLAS process | ATLAS DSIDs (nominal) | files | ATLAS σ×k×filter [pb] | CMS status | CMS records | CMS σ_eff [pb] | ATLAS/CMS | note |
|---|---|---:|---:|---|---|---:|---:|---|
| WWW (leptonic: 3ℓ3ν, and ℓνℓν jj same-/opposite-sign) | 364242–364339 (5) | 5 | 0.03652 | proposed in the plan | 72701 (T3) | 0.2158 | **0.17** ⚑ | different decay channels: ATLAS leptonic channels only, CMS WWW_4F all decays; split by decay channel and charge (W+W+W- / W-W-W+), summed |
| WWZ (4ℓ2ν, 2ℓ4ν) | 364243, 364244 | 2 | 0.005343 | proposed in the plan | 72711 (T3) | 0.1707 | **0.03** ⚑ | different decay channels: ATLAS leptonic only, CMS all decays |
| WZZ (5ℓ1ν, 3ℓ3ν) | 364245, 364246 | 2 | 0.0009324 | proposed in the plan | 72761 (T3) | 0.05709 | **0.02** ⚑ | different decay channels: ATLAS leptonic only, CMS all decays |
| ZZZ (6ℓ, 4ℓ2ν, 2ℓ4ν) | 364247, 364248, 364249 | 3 | 0.0002721 | proposed in the plan | 75600 (T3) | 0.01476 | **0.02** ⚑ | different decay channels: ATLAS leptonic only, CMS all decays |

### top (13 processes)

| ATLAS process | ATLAS DSIDs (nominal) | files | ATLAS σ×k×filter [pb] | CMS status | CMS records | CMS σ_eff [pb] | ATLAS/CMS | note |
|---|---|---:|---:|---|---|---:|---:|---|
| tt̄, not all-hadronic (single-lepton + dilepton) | 410470 | 190 | 452.3 | in the 25-26 Oct delivery | 67801, 67993 | 457.1 | 0.99 |  |
| tt̄, all-hadronic | 410471 | 148 | 379.4 | proposed in the plan | 67841 (T1) | 378.9 | 1.00 | 601495: name says 'allhad', but the metadata lists a TTbarWToLeptonFilter, a MadGraph generator and σ×filter = 0.089 pb (vs ~379 pb for 410471): its content is UNKNOWN from the metadata |
| single top t-channel, leptonic top decay (top + antitop) | 410658, 410659 | 22 | 70.43 | proposed in the plan | 64793 (T1), 64693 (T1) | 214.2 | **0.33** ⚑ | different decay channels: ATLAS leptonic top decays only, CMS inclusive decays |
| single top s-channel, leptonic (top + antitop) | 410644, 410645 | 2 | 3.35 | proposed in the plan | 64635 (T1) | 3.623 | 0.92 |  |
| single top tW, inclusive decays (top + antitop), diagram removal | 601352, 601355 | 44 | 71.97 | in the 25-26 Oct delivery | 64895, 64839 | 39.12 | **1.84** ⚑ | different decay channels: ATLAS inclusive, CMS NoFullyHadronic; subset DSIDs: dilepton tW (DR pThard=1: 601763/601764; DS: 601624/601628) (+4 subset DSIDs) |
| tt̄W (inclusive) | 410155 | 1 | 0.6008 | in the 25-26 Oct delivery | 68073, 68083 (T4) | 0.6526 | 0.92 | CMS: ℓν part delivered (68073), qq part proposed tier 4 (68083) |
| tt̄Z/γ* → ℓℓ (ee, μμ, ττ) and tt̄Z → νν | 410218, 410219, 410220, 410156 | 4 | 0.2956 | in the 25-26 Oct delivery | 68187 | 0.2439 | 1.21 | one DSID per Z decay (exclusive, summed); the m(ℓℓ) threshold is not stated in the metadata |
| tt̄Z → qq | 410157 | 1 | 0.5863 | proposed in the plan | 68206 (T4) | 0.5113 | 1.15 |  |
| tZ t-channel (4-flavour), excluding all-hadronic decays | 410560 | 1 | 0.2404 | proposed in the plan | 68325 (T4) | 0.07561 | **3.18** ⚑ | different decay channels: ATLAS 'noAllHad' keeps Z → qq with a leptonic top, CMS tZq_ll has Z → ℓℓ only |
| tWZ, Z → ℓℓ | 410408 | 1 | 0.01607 | proposed in the plan | 64873 (T4) | 0.01105 | **1.45** ⚑ | generator order (CMS value is LO, D8) and an ATLAS ΔR(ℓℓ) > 1 cut in the name |
| tt̄tt̄ | 412043 | 1 | 0.01203 | proposed in the plan | 68045 (T4) | 0.008091 | **1.49** ⚑ | generator order: the CMS proposal is the generator NLO value (8.09 fb); D7 recommends 11.97 fb |
| three top quarks (SM) | 304014 | 1 | 0.00164 | exists on the CMS portal, not proposed | 67771, 68067 | — | — | CMS TTTJ + TTTW (LO) exist, not proposed |
| tt̄WW | 410081 | 1 | 0.009904 | exists on the CMS portal, not proposed | 68087 | — | — | CMS TTWW (LO) exists, not proposed |

### Higgs (55 processes)

| ATLAS process | ATLAS DSIDs (nominal) | files | ATLAS σ×k×filter [pb] | CMS status | CMS records | CMS σ_eff [pb] | ATLAS/CMS | note |
|---|---|---:|---:|---|---|---:|---:|---|
| ggF, H → ZZ → 4ℓ | 345060 | 17 | 0.006025 | in the 25-26 Oct delivery | 37728 | 0.01333 | **0.45** ⚑ | different decay channels: ATLAS 4ℓ with ℓ = e, μ; CMS JHUGen ZZ → 4ℓ includes τ |
| ggF, H → WW | 345324 | 1 | 1.136 | proposed in the plan | 37474 (T5) | 1.111 | 1.02 | ATLAS: H → WW → ℓνℓν, name carries a lepton filter 'EF_15_5' |
| ggF, H → ττ | 345120, 345121, 345122, 345123 | 4 | 0.9699 | proposed in the plan | 37446 (T5) | 3.047 | **0.32** ⚑ | filter: the ATLAS pieces carry ττ-decay and lepton/hadron pT filters; split by ττ decay with lepton/hadron pT filters (ll 13/7, ℓ±h∓ 15/20, hh 30/20 GeV), summed |
| ggF, H → invisible (ZZ → 4ν) | 346588 | 5 | 0.05092 | no CMS 2016 sample found | — | — | — | MET > 75 GeV filter; GluGluHToZZTo4Nu not observed; no leptons |
| ggF, H → μμ | 345097 | 1 | 0.01057 | exists on the CMS portal, not proposed | 37432 (opt.) | — | — | in the plan as 'optional' (no proposal) |
| ggF, H → γγ | 343981 | 1 | 0.1103 | exists on the CMS portal, not proposed | 37350 | — | — | photon final state |
| ggF, H → Zγ | 345316 | 13 | 0.007449 | exists on the CMS portal, not proposed | 37604 | — | — | ATLAS and CMS: Z → ℓℓ |
| ggF, H → γ*γ, γ* → ℓℓ (Dalitz) | 345961 | 2 | 0.02092 | exists on the CMS portal, not proposed | 37420, 37276 | — | — |  |
| ggF, H → eτ / μτ (as named) | 345124, 345125 | 29 | 0.0006214 | out of scope | — | — | — | named H → eτ / μτ with a TauFilter; whether this is lepton-flavour-violating (BSM) or a ττ subset is UNKNOWN from the metadata |
| VBF, H → ZZ → 4ℓ | 346228 | 2 | 0.000469 | in the 25-26 Oct delivery | 68847 | 0.001038 | **0.45** ⚑ | different decay channels: ATLAS 4ℓ without τ; CMS JHUGen includes τ |
| VBF, H → WW | 345948 | 1 | 0.08842 | proposed in the plan | 68601 (T5) | 0.08653 | 1.02 | H → WW → ℓνℓν |
| VBF, H → ττ | 346190, 346191, 346192, 346193 | 6 | 0.3064 | proposed in the plan | 68591 (T5) | 0.2372 | 1.29 | possible error on the ATLAS side: the four ATLAS filtered pieces sum to MORE than σ(VBF) × BR(ττ); they do not behave like the ggF pieces (cross-check only); split by ττ decay with lepton/hadron pT filters (ll 13/7, ℓ±h∓ 15/20, hh 30/20 GeV), summed |
| VBF, H → γγ | 346214 | 1 | 0.008585 | exists on the CMS portal, not proposed | 68499 | — | — | photon final state |
| VBF, H → μμ | 345106 | 1 | 0.001038 | exists on the CMS portal, not proposed | 68571 (opt.) | — | — | in the plan as 'optional' |
| VBF, H → bb̄ | 345949 | 1 | 2.203 | exists on the CMS portal, not proposed | 68445 | — | — |  |
| VBF, H → Zγ | 345833 | 6 | 0.0005856 | exists on the CMS portal, not proposed | 68731 | — | — | ATLAS and CMS: Z → ℓℓ |
| VBF, H → γ*γ, γ* → ℓℓ (Dalitz) | 345834 | 1 | 0.008585 | exists on the CMS portal, not proposed | 68559, 68459 | — | — |  |
| VBF, H → ZZ → ℓℓbb | 450576 | 2 | 0.002019 | exists on the CMS portal, not proposed | 68833 | — | — | CMS VBF_HToZZTo2L2X (2ℓ + anything) is a superset |
| VBF, H → eτ / μτ (as named) | 346194, 346195 | 4 | 0.005083 | out of scope | — | — | — | as ggF eτ/μτ |
| VBF, H → all decays | 346317 | 6 | 3.782 | no CMS 2016 sample found | — | — | — | no CMS inclusive-decay VBF H sample observed; overlaps every ATLAS VBF decay sample above |
| W±H, H → ZZ → 4ℓ | 346449, 346450 | 3 | 0.0003768 | proposed in the plan | 71227 (T5), 70383 (T5) | 0.0003768 | 1.00 |  |
| W±H, H → WW | 345325, 345433 | 2 | 0.02164 | proposed in the plan | 41877 (T5), 41873 (T5) | 0.2934 | **0.07** ⚑ | different decay channels: ATLAS W → qq and H → WW → ℓνℓν only; CMS HWJ H → WW and W inclusive (superset) |
| W±H, H → ττ | 345211, 345212 | 2 | 0.0861 | proposed in the plan | 71297 (T5), 70453 (T5) | 0.0861 | 1.00 | 506098 σ×filter = 0.903 pb ≈ σ(W+H) itself, i.e. BR(ττ) apparently not included (ATLAS metadata, cross-check only) |
| W±H, H → μμ | 345104, 345105 | 2 | 0.0003768 | exists on the CMS portal, not proposed | 71295, 70451 | — | — |  |
| W±H, H → γγ | 345317, 345318 | 2 | 0.003116 | exists on the CMS portal, not proposed | 71013, 70173 | — | — | photon final state |
| W±H, H → Zγ | 345320, 345321 | 2 | 0.002105 | exists on the CMS portal, not proposed | 71145, 70301 | — | — | Z decay not stated in the ATLAS metadata; CMS WToAll, Z inclusive per its name |
| W±H, H → γ*γ, γ* → ℓℓ (Dalitz) | 345963, 345964 | 2 | 0.003116 | no CMS 2016 sample found | — | — | — | W±H Dalitz not observed (fetch_cms_extra.py) |
| W±H, H → eτ / μτ (as named) | 345213, 345214, 345215, 345216 | 6 | 1.756e-05 | out of scope | — | — | — | as ggF eτ/μτ |
| W±H, H → ee | 345877, 345878 | 3 | 7.468e-09 | exists on the CMS portal, not proposed | 69343 | — | — | CMS VHToEE covers W±H and ZH together |
| W±H, H → invisible (ZZ → 4ν) | 346605, 346606 | 2 | 0.001439 | exists on the CMS portal, not proposed | 71359, 70515 | — | — | ATLAS: W inclusive, MET > 75 GeV filter. CMS only with W → qq (no leptons); CMS H → invisible normalisation would need a BR decision |
| W±H, H → all decays | 346311, 346312 | 3 | 1.373 | no CMS 2016 sample found | — | — | — | no CMS inclusive W±H sample observed (VHToNonbb 69389 is W±H + ZH, H ≠ bb) |
| qq̄ → ZH, H → bb̄ | 345056 | 1 | 0.08866 | exists on the CMS portal, not proposed | 74118 | — | — | Z → νν (ATLAS and CMS) |
| qq̄ → ZH, H → cc̄ | 345112 | 1 | 0.004401 | exists on the CMS portal, not proposed | 74126 | — | — | Z → νν (ATLAS and CMS). 346726: name 'vvcc', but the metadata 'process' field says H → bb (ATLAS metadata inconsistency) |
| qq̄ → ZH, H → μμ | 345103 | 1 | 0.0002089 | exists on the CMS portal, not proposed | 74682 | — | — |  |
| qq̄ → ZH, H → ττ | 345217 | 1 | 0.04774 | proposed in the plan | 74684 (T5) | 0.04774 | 1.00 | 506099 σ×filter = 0.787 pb ≈ σ(ZH) itself, BR(ττ) apparently not included (ATLAS metadata) |
| qq̄ → ZH, H → γγ | 345319 | 1 | 0.001728 | exists on the CMS portal, not proposed | 74132 | — | — | photon final state |
| qq̄ → ZH, H → Zγ | 345322 | 1 | 0.001167 | exists on the CMS portal, not proposed | 74292 | — | — |  |
| qq̄ → ZH, H → γ*γ, γ* → ℓℓ (Dalitz) | 345965 | 1 | 0.001728 | exists on the CMS portal, not proposed | 74670, 74652 | — | — |  |
| qq̄ → ZH, H → WW | 345445, 341456, 341458, 341460 | 4 | 0.008328 | proposed in the plan | 41914 (T5) | 0.1627 | **0.05** ⚑ | different decay channels: ATLAS Z → νν only; CMS HZJ H → WW, Z inclusive (superset); ℓνqq split by Z → νeνe / νμνμ / ντντ (341456/58/60; Maryna's class 'ggF Higgs', but the metadata says qq → ZH) |
| qq̄ → ZH, H → ZZ → 4ℓ | 346645 | 1 | 0.0002089 | exists on the CMS portal, not proposed | 74314 | — | — | ATLAS: Z inclusive. CMS ZH_HToZZ_4LFilter: not proposed, its portal 'matching efficiency' looks misplaced (D13, UNVERIFIED) |
| qq̄ → ZH, H → ee | 345876 | 2 | 4.141e-09 | exists on the CMS portal, not proposed | 69343 | — | — | CMS VHToEE covers W±H and ZH |
| qq̄ → ZH, H → invisible (ZZ → 4ν) | 346607 | 1 | 0.0007977 | exists on the CMS portal, not proposed | 74892 | — | — | ATLAS: Z inclusive, MET > 75 GeV. CMS only with Z → qq |
| qq̄ → ZH, H → eτ / μτ (as named) | 345218, 345219 | 4 | 9.734e-06 | out of scope | — | — | — | as ggF eτ/μτ |
| qq̄ → ZH, H → all decays | 346310 | 2 | 0.7612 | no CMS 2016 sample found | — | — | — | no CMS inclusive ZH sample observed |
| gg → ZH, H → bb̄ | 345058 | 1 | 0.01429 | exists on the CMS portal, not proposed | 36597 | — | — | Z → νν (ATLAS and CMS) |
| gg → ZH, H → cc̄ | 345114 | 1 | 0.0007095 | exists on the CMS portal, not proposed | 36605 | — | — | Z → νν (ATLAS and CMS) |
| gg → ZH, H → γγ | 345061 | 1 | 0.0002785 | exists on the CMS portal, not proposed | 36611, 36617, 36623 | — | — | photon final state |
| gg → ZH, H → ZZ → 4ℓ | 345066 | 1 | 3.368e-05 | exists on the CMS portal, not proposed | 40062 | — | — | ATLAS: Z inclusive. CMS GluGluToZH_HToZZTo4L (JHUGen) exists: PLAN §2g says 'not observed' for this cell, which is a correction |
| gg → ZH, H → μμ | 345098 | 1 | 3.368e-05 | no CMS 2016 sample found | — | — | — | not observed |
| gg → ZH, H → ττ | 600686 | 1 | 0.007696 | no CMS 2016 sample found | — | — | — | ATLAS: Z inclusive; CMS not observed |
| gg → ZH, H → WW | 346524 | 1 | 0.002869 | proposed in the plan | 40095 (T5) | 0.002648 | 1.08 | different decay channels: CMS proposal is Z → ℓℓ only; ATLAS: Z inclusive. CMS proposed sample has Z → ℓℓ only; GluGluZH_HToWWTo2L2Nu 40090 (Z inclusive, H → 2ℓ2ν) also exists |
| gg → ZH, H → invisible (ZZ → 4ν) | 345596 | 1 | 0.0001286 | exists on the CMS portal, not proposed | 36929 | — | — | ATLAS: Z inclusive. CMS only with Z → qq |
| tt̄H, H → all decays | 346343, 346344, 346345 | 3 | 0.5071 | proposed in the plan | 67645 (T4), 67691 (T4) | 0.5071 | 1.00 | subset DSIDs (ATLAS-side overlap with the inclusive ones): γγ 346189/346525 (+ Herwig 346526, 346601), ZZ → 4ℓ 346340-346342 (+ Herwig 346452-346454), ττ 346919/346923/346927, Zγ 346198, ZZ → 4ν 346632-346634 (the metadata 'process' field of all three says 'allhad', the names say semilep/allhad/dilep). On the CMS side all of them are inside ttH → bb + ttH → non-bb.; split by tt̄ decay, summed (+17 subset DSIDs) |
| tHq (tHjb), H → γγ and ZZ → 4ℓ | 346188, 346414 | 2 | 7.326e-06 | exists on the CMS portal, not proposed | 65657, 65649 | — | — | CMS THQ_ctcvcp: generated at a non-SM coupling, needs reweighting (D13, UNVERIFIED); not proposed |
| tWH, H → γγ and ZZ → 4ℓ | 346486, 346511 | 2 | 3.868e-05 | exists on the CMS portal, not proposed | 65725, 65721 | — | — | CMS THW_ctcvcp: as tHq |

### photon (6 processes)

| ATLAS process | ATLAS DSIDs (nominal) | files | ATLAS σ×k×filter [pb] | CMS status | CMS records | CMS σ_eff [pb] | ATLAS/CMS | note |
|---|---|---:|---:|---|---|---:|---:|---|
| tt̄γ | 410389 | 3 | 5.364 | out of scope | 67439, 67459, 67453 | — | — | photons deferred |
| γ + jets (prompt photon), pT(γ)-sliced | 364541–364547 (7) | 402 | 4.644e+05 | out of scope | — | — | — | pT(γ) slices 17 → E_CMS (Sherpa); 8 → ∞ (Pythia8) |
| γγ (+ jets), m(γγ)-sliced | 364350–364354 (5) | 82 | 295.4 | out of scope | — | — | — | m(γγ) slices 0 → E_CMS (Sherpa); 55 → ∞ (Pythia8) |
| V + γ (ℓℓγ, ννγ, ℓνγ, qqγ, bbγ, EW ℓνγjj / ℓℓγjj) | 700398–700710 (12) | 602 | 1469 | out of scope | — | — | — |  |
| V + γγ and γγγ | 700195–700007 (8) | 14 | 10.57 | out of scope | — | — | — |  |
| electroweak γ + 2 jets, pT(γ) > 140 GeV (Maryna's class 'QCD jets') | 700442 | 1 | 1.388 | out of scope | — | — | — | the metadata describes it as 'Electroweak Sherpa gamma + 2,3j@LO', not QCD multijet |

### QCD (1 processes)

| ATLAS process | ATLAS DSIDs (nominal) | files | ATLAS σ×k×filter [pb] | CMS status | CMS records | CMS σ_eff [pb] | ATLAS/CMS | note |
|---|---|---:|---:|---|---|---:|---:|---|
| QCD dijet (Pythia8, JZ0-JZ12 leading-jet-pT slices) | 364700–364712 (13) | 1611 | 7.805e+10 | out of scope | — | — | — | in Maryna's 'EW boson / V+jets / diboson' class; this IS a QCD multijet set; JZ0 … JZ12 slices |

### BSM (2 processes)

| ATLAS process | ATLAS DSIDs (nominal) | files | ATLAS σ×k×filter [pb] | CMS status | CMS records | CMS σ_eff [pb] | ATLAS/CMS | note |
|---|---|---:|---:|---|---|---:|---:|---|
| Z' → ττ, SSM 3 TeV | 801976 | 2 | 1.246 | out of scope | — | — | — |  |
| W' → τν, SSM 3 TeV | 801978 | 1 | 0.01141 | out of scope | — | — | — |  |

Like-for-like checks for the flagged single-top ratios (W → ℓν = 0.3272, W → hadrons = 0.6741, settled PDG values):

- st_tchan: ATLAS leptonic / (CMS inclusive × BR(W → ℓν)): **1.005**
- st_tchan alt pThard=1 / (CMS × BR(W → ℓν)): **0.845**
- st_tW: ATLAS inclusive × (1 − BR(W → had)²) / CMS NoFullyHadronic: **1.004**
- VV_2l2v_os + nothing: ATLAS / CMS WW → 2ℓ2ν: **0.951**
- VBF_tautau: ATLAS sum of the 4 filtered pieces / CMS σ(VBF) × BR(ττ): **1.291**

## B. ATLAS alternative generators for the same process (ATLAS-side double counting is their business)

Listed for Maryna: mixing a nominal and an alternative set would count the process twice on the ATLAS side.

| ATLAS process | nominal DSIDs (files) | alternative | DSIDs | files |
|---|---|---|---|---:|
| tt̄, not all-hadronic (single-lepton + dilepton) | 410470 (190) | Powheg+Herwig7 (single-lepton 411233 + dilepton 411234) | 411233, 411234 | 110 |
| tt̄, not all-hadronic (single-lepton + dilepton) | 410470 (190) | Powheg+Pythia8 pThard=1 (dilepton 601491 + single-lepton 601497) | 601491, 601497 | 183 |
| tt̄, all-hadronic | 410471 (148) | Powheg+Herwig7 | 411316 | 165 |
| tt̄, all-hadronic | 410471 (148) | Powheg+Pythia8 pThard=1 (name; see note) | 601495 | 1 |
| single top t-channel, leptonic top decay (top + antitop) | 410658, 410659 (22) | Powheg+Herwig7 (600017 antitop, 600018 top) | 600017, 600018 | 30 |
| single top t-channel, leptonic top decay (top + antitop) | 410658, 410659 (22) | Powheg+Pythia8 pThard=1 (601487 antitop, 601489 top) | 601487, 601489 | 37 |
| single top s-channel, leptonic (top + antitop) | 410644, 410645 (2) | Powheg+Herwig7 (600019 antitop, 600020 top) | 600019, 600020 | 3 |
| single top tW, inclusive decays (top + antitop), diagram removal | 601352, 601355 (44) | DR, pThard=1 (601761, 601762) | 601761, 601762 | 55 |
| single top tW, inclusive decays (top + antitop), diagram removal | 601352, 601355 (44) | diagram subtraction DS (601627, 601631) | 601627, 601631 | 33 |
| tt̄W (inclusive) | 410155 (1) | Sherpa 2.2.8 (700000) | 700000 | 1 |
| tt̄tt̄ | 412043 (1) | aMC@NLO+Herwig7 | 412044 | 1 |
| tt̄γ | 410389 (3) | MG+Pythia8 older (410082 non-allhad, 410087 allhad) | 410082, 410087 | 16 |
| tt̄γ | 410389 (3) | MG+Herwig7 (410395 non-allhad, 410396 allhad) | 410395, 410396 | 5 |
| γ + jets (prompt photon), pT(γ)-sliced | 364541, 364542, 364543, 364544 … (402) | Pythia8 (423099-423112) | 423099–423112 (14) | 170 |
| γγ (+ jets), m(γγ)-sliced | 364350, 364351, 364352, 364353 … (82) | Pythia8 2DP20 (302520-302534; Maryna's class 'HC model (SM modes)') | 302520–302534 (15) | 35 |
| ggF, H → ZZ → 4ℓ | 345060 (17) | Powheg+Herwig7, no τ (346446) | 346446 | 13 |
| ggF, H → WW | 345324 (1) | Powheg+Herwig7, no τ (346802) | 346802 | 7 |
| ggF, H → ττ | 345120, 345121, 345122, 345123 (4) | Powheg+Herwig7 (600565-600568) | 600565, 600566, 600567, 600568 | 24 |
| ggF, H → γγ | 343981 (1) | Powheg+Herwig7 (346797) | 346797 | 14 |
| VBF, H → ZZ → 4ℓ | 346228 (2) | Powheg+Herwig7 (346447) | 346447 | 7 |
| VBF, H → WW | 345948 (1) | Powheg+Herwig7 (346877) | 346877 | 3 |
| VBF, H → WW | 345948 (1) | MadGraph+Herwig7 (500335; Maryna's class 'Higgs related') | 500335 | 1 |
| VBF, H → ττ | 346190, 346191, 346192, 346193 (6) | Powheg+Herwig7 (600569-600572) | 600569, 600570, 600571, 600572 | 8 |
| VBF, H → γγ | 346214 (1) | Powheg+Herwig7 (346878) | 346878 | 2 |
| W±H, H → ZZ → 4ℓ | 346449, 346450 (3) | Powheg+Pythia8 'shw' (346646, 346647) | 346646, 346647 | 3 |
| W±H, H → ττ | 345211, 345212 (2) | Powheg+Herwig7 (600573, 600574) | 600573, 600574 | 3 |
| W±H, H → ττ | 345211, 345212 (2) | aMC@NLO FxFx W+H only (506098) | 506098 | 2 |
| W±H, H → γγ | 345317, 345318 (2) | Powheg+Herwig7 (346880, 346881) | 346880, 346881 | 3 |
| qq̄ → ZH, H → bb̄ | 345056 (1) | Powheg+Herwig7 (346398) | 346398 | 1 |
| qq̄ → ZH, H → cc̄ | 345112 (1) | Powheg+Herwig7 (346726) | 346726 | 1 |
| qq̄ → ZH, H → ττ | 345217 (1) | Powheg+Herwig7 (600575) | 600575 | 2 |
| qq̄ → ZH, H → ττ | 345217 (1) | aMC@NLO FxFx (506099) | 506099 | 1 |
| qq̄ → ZH, H → γγ | 345319 (1) | Powheg+Herwig7 (346879) | 346879 | 2 |
| qq̄ → ZH, H → γγ | 345319 (1) | aMC@NLO FxFx, Z → qq (506813) | 506813 | 1 |
| qq̄ → ZH, H → ZZ → 4ℓ | 346645 (1) | Powheg+Herwig7 (346448) | 346448 | 1 |
| gg → ZH, H → bb̄ | 345058 (1) | Powheg+Herwig7 (346400) | 346400 | 1 |
| gg → ZH, H → cc̄ | 345114 (1) | Powheg+Herwig7 (346728) | 346728 | 1 |
| gg → ZH, H → γγ | 345061 (1) | Powheg+Herwig7 (346882) | 346882 | 1 |
| gg → ZH, H → γγ | 345061 (1) | aMC@NLO, Z → qq (506814) | 506814 | 1 |
| gg → ZH, H → ZZ → 4ℓ | 345066 (1) | Powheg+Herwig7 (346451) | 346451 | 1 |
| tHq (tHjb), H → γγ and ZZ → 4ℓ | 346188, 346414 (2) | aMC@NLO+Herwig7 γγ (346602) | 346602 | 1 |

86 DSIDs are alternatives and 21 are decay/filter subsets of another listed DSID (tW dilepton, tt̄H by decay; see notes in table A). Also: the V+jets b/c-filter splits and the pT/mass/JZ slices are exclusive pieces of one sample and are NOT double counting.


## C. Higgs: ATLAS production × decay vs CMS (input to D13)

Cell = ATLAS nominal DSIDs → CMS. ● delivered, ◆ proposed (tier 4/5), ○ on the CMS portal, not proposed, ✗ no CMS 2016 sample found, — not in the ATLAS list, (oos) out of scope.

| decay ↓ / production → | ggF | VBF | W±H | qq̄ → ZH | gg → ZH | tt̄H | tHq (tHjb) | tWH |
|---|---|---|---|---|---|---|---|---|
| ZZ → 4ℓ | ● 345060 → 37728 | ● 346228 → 68847 | ◆ 346449,346450 → 71227,70383 | ○ 346645 → 74314 | ○ 345066 → 40062 | — | — | — |
| WW | ◆ 345324 → 37474 | ◆ 345948 → 68601 | ◆ 345325,345433 → 41877,41873 | ◆ 345445,341456,341458,341460 → 41914 | ◆ 346524 → 40095 | — | — | — |
| ττ | ◆ 345120,345121,345122,345123 → 37446 | ◆ 346190,346191,346192,346193 → 68591 | ◆ 345211,345212 → 71297,70453 | ◆ 345217 → 74684 | ✗ 600686 | — | — | — |
| invisible (ZZ → 4ν) | ✗ 346588 | — | ○ 346605,346606 → 71359,70515 | ○ 346607 → 74892 | ○ 345596 → 36929 | — | — | — |
| μμ | ○ 345097 → 37432 | ○ 345106 → 68571 | ○ 345104,345105 → 71295,70451 | ○ 345103 → 74682 | ✗ 345098 | — | — | — |
| γγ | ○ 343981 → 37350 | ○ 346214 → 68499 | ○ 345317,345318 → 71013,70173 | ○ 345319 → 74132 | ○ 345061 → 36611,36617,36623 | — | — | — |
| Zγ | ○ 345316 → 37604 | ○ 345833 → 68731 | ○ 345320,345321 → 71145,70301 | ○ 345322 → 74292 | — | — | — | — |
| γ*γ, γ* → ℓℓ (Dalitz) | ○ 345961 → 37420,37276 | ○ 345834 → 68559,68459 | ✗ 345963,345964 | ○ 345965 → 74670,74652 | — | — | — | — |
| eτ / μτ (as named) | (oos) 345124,345125 | (oos) 346194,346195 | (oos) 345213,345214,345215,345216 | (oos) 345218,345219 | — | — | — | — |
| bb̄ | — | ○ 345949 → 68445 | — | ○ 345056 → 74118 | ○ 345058 → 36597 | — | — | — |
| ZZ → ℓℓbb | — | ○ 450576 → 68833 | — | — | — | — | — | — |
| all decays | — | ✗ 346317 | ✗ 346311,346312 | ✗ 346310 | — | ◆ 346343,346344,346345 → 67645,67691 | — | — |
| ee | — | — | ○ 345877,345878 → 69343 | ○ 345876 → 69343 | — | — | — | — |
| cc̄ | — | — | — | ○ 345112 → 74126 | ○ 345114 → 36605 | — | — | — |
| γγ and ZZ → 4ℓ | — | — | — | — | — | — | ○ 346188,346414 → 65657,65649 | ○ 346486,346511 → 65725,65721 |

Cost of adding CMS samples for the cells marked ○ (ESTIMATES, PLAN §4 method: files × 6014/497 + 2240/13 per sample cluster files; CPU at the delivered ggH → 4ℓ rate):

| group | cells | samples | portal files | events | cluster files | CPU h |
|---|---|---:|---:|---:|---:|---:|
| recommended to add | ggF_mumu, ggF_Zgam, VBF_mumu, VBF_Zgam, WH_mumu, WH_Zgam, qqZH_mumu, qqZH_Zgam, ggZH_ZZ4l | 11 | 67 | 4.3 M | 2,706 | 4.2 |
| photon final state (deferred) | ggF_gamgam, VBF_gamgam, WH_gamgam, qqZH_gamgam, ggZH_gamgam | 8 | 84 | 2.0 M | 2,395 | 1.9 |
| other (tiny, overlapping, or needs a decision) | ggF_dalitz, VBF_dalitz, VBF_ZZllbb, WH_ee, qqZH_dalitz, qqZH_ZZ4l, qqZH_ee, tHjb, tWH | 13 | 222 | 35.7 M | 4,926 | 34.9 |
| no leptons on the CMS side | VBF_bb, WH_inv, qqZH_bb_vv, qqZH_cc_vv, qqZH_inv, ggZH_bb_vv, ggZH_cc_vv, ggZH_inv | 9 | 135 | 14.4 M | 3,184 | 14.0 |
| **all ○ cells** | | 41 | 508 | 56.4 M | 13,212 | 55.0 |
| (for scale: plan tier 5) | 15 proposed | 15 | 280 | | 5,973 | 36.4 |

## D. Reverse check: CMS samples (delivered or in the plan) with no ATLAS counterpart in Maryna's list

| CMS record | sample | plan tier / role | note |
|---|---|---|---|
| 69745 | WJetsToLNu_amcatnloFXFX (inclusive NLO) | 1 / alternative | W+jets inclusive NLO: alternative only (D1 decided the jet-binned set) |
| 69747 | WJetsToLNu_madgraphMLM (inclusive LO) | 1 / alternative | W+jets inclusive LO: alternative only (D1 decided) |
| 64759 | ST_t-channel_top_4f_InclusiveDecays | 1 / alternative | t-channel 4-flavour: alternative for D4; ATLAS uses Powheg t-channel (flavour scheme not stated in the metadata) |
| 64659 | ST_t-channel_antitop_4f_InclusiveDecays | 1 / alternative | t-channel 4-flavour antitop: as 64759 |
| 68185 | TTZToLL_M-1to10 | 4 / recommended | tt̄ + ℓℓ with 1 < m(ℓℓ) < 10 GeV: ATLAS tt̄ee/μμ/ττ state no m(ℓℓ) threshold in the metadata, so whether they cover it is UNKNOWN |
| 37616 | GluGluHToZZTo2L2Nu_M125 | 5 / recommended | ggF H → ZZ → 2ℓ2ν: ATLAS list has ggF H → ZZ → 4ν and → 4ℓ but no 2ℓ2ν; a genuine lepton background, cheap (2 files) |
| 68741 | VBF_HToZZTo2L2Nu_M125 | 5 / recommended | VBF H → ZZ → 2ℓ2ν: no ATLAS counterpart (ATLAS has VBF ZZ → 4ℓ and → ℓℓbb only); 21 files |
| 64633 | ST_s-channel_4f_hadronicDecays | — / optional | s-channel hadronic (optional): ATLAS has leptonic s-channel only |
| 72678 | WWTo2L2Nu_DoubleScattering | — / optional | WW double-parton scattering (optional): no ATLAS counterpart |
| 68071 | ttWJetsToLNu_5f_EWK | — / optional | tt̄W EWK (optional): ATLAS tt̄W (aMC@NLO 410155 / Sherpa 700000) — whether the EW part is inside is UNKNOWN |
| 37678 | GluGluHToZZTo2L2Q_M125 | — / optional | ggF H → ZZ → 2ℓ2q (optional): no ATLAS counterpart |
| 71003 | WplusH_HToBB_WToLNu_M-125 | — / optional | W+H → bb, W → ℓν (optional): ATLAS has VH → bb only with Z → νν |
| 70163 | WminusH_HToBB_WToLNu_M-125 | — / optional | W−H → bb, W → ℓν (optional): as 71003 |
| 74116 | ZH_HToBB_ZToLL_M-125 | — / optional | ZH → bb, Z → ℓℓ (optional): as 71003 |
| 36595 | ggZH_HToBB_ZToLL_M-125 | — / optional | gg → ZH → bb, Z → ℓℓ (optional): as 71003 |
| 32783 | bbH_inclusive_M-125_4FS_yb2 | — / optional | bb̄H inclusive (optional): no bb̄H in the ATLAS list |
| 37532 | GluGluHToWWToLNuQQ_M-125 | — / optional | ggF H → WW → ℓνqq (optional): ATLAS has H → WW → ℓνqq only in qq̄ → ZH (Z → νν) |

All 13 delivered samples have an ATLAS counterpart.
