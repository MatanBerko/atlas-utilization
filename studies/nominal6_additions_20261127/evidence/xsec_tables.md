#### N1 75561 — ZZJJTo4L_EWKnotop_TuneCP5_13TeV-madgraph-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [75560](https://opendata.cern.ch/record/75560)) | 0.0009928 | filter 1, matching 1, neg. weights 0 | VERIFIED (saved record) |
| (b) McM generator value ([SUS-RunIISummer20UL16wmLHEGEN-00134](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/SUS-RunIISummer20UL16wmLHEGEN-00134)) | 0.0007165 | filter 1, match 1 | VERIFIED (saved request JSON); user-entered value |
| (c) none found for the generator phase space | — |  | CMS measured EW VBS in fiducial regions with reconstruction-like cuts (e.g. EW ZZjj 0.33 fb, SM 0.275 fb, arXiv:2008.07013 abstract; EW W+W-jj 10.2 fb, SM 9.1 fb, arXiv:2205.05711 abstract). These are NOT the generator phase space of the samples (m_jj > 100 GeV, |eta_l| < 3 at generator level), so they cannot be used directly; no NLO calculation for the generator phase space was found. |
| (e) ATLAS σ×k×ε (700587, 700591) | 0.01382 | 700587: 0.01151×1×1; 700591: 0.0023142×1×1 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.07182 |

- **R1:** Decay inside the MadGraph matrix element (process card decay chain `v > l v`); no separate decay step, no filter (fragment filterEfficiency 1.0), no matching (ickkw 0): R1 applies, the portal total_value is the complete generator cross section of the sample.
- **(d) registry v5 analogue:** Dibosons (E1): generator x NNLO/NLO k-factor (WZ, ZZ) or NNLO total x BR (WW); tribosons 72701/72711 and ttZ/ttW: generator NLO value as is. No EW VV+2j precedent: E2 dropped the EW V+2j samples (35999/35987/35993) before any value was chosen.
- **Generator settings:** CMS card: p p > z z j j $ t t~ QED=4 QCD=0, z > l+ l- (l = e mu tau), on-shell Z decay chain; m_jj > 100, |eta_l| < 3, |eta_j| < 5, pT_j > 10 GeV. ATLAS Sherpa: off-shell 4 charged leptons + 2 jets, m_ll > 0.25/0.46/3.8 GeV (ee/mumu/tautau), pT_l > 5, 2 jets pT > 15, NO m_jj cut, 0,1j@LO merged; incl. gamma* and triboson-like diagrams. McM 7.1654e-4 pb differs from the portal 9.928e-4 pb (factor 1.39; unexplained).

#### N1 69771 — WLLJJ_WToLNu_EWK_TuneCP5_13TeV_madgraph-madspin-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [69770](https://opendata.cern.ch/record/69770)) | 0.03566 | filter 1, matching 1, neg. weights 0 | VERIFIED (saved record) |
| (b) McM generator value ([SMP-RunIISummer20UL16wmLHEGEN-00539](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/SMP-RunIISummer20UL16wmLHEGEN-00539)) | 0.01654 | filter 1, match 1 | VERIFIED (saved request JSON); user-entered value |
| (c) none found for the generator phase space | — |  | CMS measured EW VBS in fiducial regions with reconstruction-like cuts (e.g. EW ZZjj 0.33 fb, SM 0.275 fb, arXiv:2008.07013 abstract; EW W+W-jj 10.2 fb, SM 9.1 fb, arXiv:2205.05711 abstract). These are NOT the generator phase space of the samples (m_jj > 100 GeV, |eta_l| < 3 at generator level), so they cannot be used directly; no NLO calculation for the generator phase space was found. |
| (e) ATLAS σ×k×ε (700588, 700592) | 0.0562 | 700588: 0.048453×1×1; 700592: 0.0077437×1×1 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.6346 |

- **R1:** Decay inside the MadGraph matrix element (process card decay chain `v > l v`); no separate decay step, no filter (fragment filterEfficiency 1.0), no matching (ickkw 0): R1 applies, the portal total_value is the complete generator cross section of the sample.
- **(d) registry v5 analogue:** Dibosons (E1): generator x NNLO/NLO k-factor (WZ, ZZ) or NNLO total x BR (WW); tribosons 72701/72711 and ttZ/ttW: generator NLO value as is. No EW VV+2j precedent: E2 dropped the EW V+2j samples (35999/35987/35993) before any value was chosen.
- **Generator settings:** CMS card (nearest in genproductions, named ..._notop; the gridpack is named WZ3lnujj_ewk WITHOUT notop: match UNVERIFIED): p p > w+- z j j $ t t~ QED=4 QCD=0, on-shell decay chain, m_jj > 100, |eta_l| < 3. ATLAS lllvjj: off-shell, no m_jj cut. McM 0.01654 pb is 0.46 x the portal 0.03566 pb (unexplained; could be one W charge only - UNVERIFIED).

#### N1 72648 — WWJJToLNuLNu_EWK_noTop_TuneCP5_13TeV-madgraph-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [72647](https://opendata.cern.ch/record/72647)) | 0.09219 | filter 1, matching 1, neg. weights 0 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-03478](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-03478)) | 0.09283 | filter 1, match 1 | VERIFIED (saved request JSON); user-entered value |
| (c) none found for the generator phase space | — |  | CMS measured EW VBS in fiducial regions with reconstruction-like cuts (e.g. EW ZZjj 0.33 fb, SM 0.275 fb, arXiv:2008.07013 abstract; EW W+W-jj 10.2 fb, SM 9.1 fb, arXiv:2205.05711 abstract). These are NOT the generator phase space of the samples (m_jj > 100 GeV, |eta_l| < 3 at generator level), so they cannot be used directly; no NLO calculation for the generator phase space was found. |
| (e) ATLAS σ×k×ε (700589, 700593) | 0.1997 | 700589: 0.19336×1×1; 700593: 0.0063366×1×1 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.4617 |

- **R1:** Decay inside the MadGraph matrix element (process card decay chain `v > l v`); no separate decay step, no filter (fragment filterEfficiency 1.0), no matching (ickkw 0): R1 applies, the portal total_value is the complete generator cross section of the sample.
- **(d) registry v5 analogue:** Dibosons (E1): generator x NNLO/NLO k-factor (WZ, ZZ) or NNLO total x BR (WW); tribosons 72701/72711 and ttZ/ttW: generator NLO value as is. No EW VV+2j precedent: E2 dropped the EW V+2j samples (35999/35987/35993) before any value was chosen.
- **Generator settings:** CMS card (linked in the fragment): p p > w+ w- j j $ t t~ QED=4 QCD=0, w > l v; m_jj > 100, no eta cuts, dR(jj, ll, jl) > 0.4. ATLAS llvvjj_os: ALL opposite-sign l l nu nu (also ZZ -> ll nunu and non-resonant), no m_jj cut.

#### N1 71636 — WpWpJJ_EWKnotop_TuneCP5_13TeV-madgraph-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [71635](https://opendata.cern.ch/record/71635)) | 0.02694 | filter 1, matching 1, neg. weights 0 | VERIFIED (saved record) |
| (b) McM generator value ([SUS-RunIISummer20UL16wmLHEGEN-00122](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/SUS-RunIISummer20UL16wmLHEGEN-00122)) | 0.0287 | filter 1, match 1 | VERIFIED (saved request JSON); user-entered value |
| (c) none found for the generator phase space | — |  | CMS measured EW VBS in fiducial regions with reconstruction-like cuts (e.g. EW ZZjj 0.33 fb, SM 0.275 fb, arXiv:2008.07013 abstract; EW W+W-jj 10.2 fb, SM 9.1 fb, arXiv:2205.05711 abstract). These are NOT the generator phase space of the samples (m_jj > 100 GeV, |eta_l| < 3 at generator level), so they cannot be used directly; no NLO calculation for the generator phase space was found. |
| (e) ATLAS σ×k×ε (700590, 700594) | 0.04894 | 700590: 0.045598×1×1; 700594: 0.0033375×1×1 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.5505 |

- **R1:** Decay inside the MadGraph matrix element (process card decay chain `v > l v`); no separate decay step, no filter (fragment filterEfficiency 1.0), no matching (ickkw 0): R1 applies, the portal total_value is the complete generator cross section of the sample.
- **(d) registry v5 analogue:** Dibosons (E1): generator x NNLO/NLO k-factor (WZ, ZZ) or NNLO total x BR (WW); tribosons 72701/72711 and ttZ/ttW: generator NLO value as is. No EW VV+2j precedent: E2 dropped the EW V+2j samples (35999/35987/35993) before any value was chosen.
- **Generator settings:** CMS card (nearest in genproductions WpWpJJ_EWK-QCD, name matches the gridpack): BOTH w+w+jj AND w-w-jj (so W-W- is inside, correcting the 24 Nov 'no separate W-W-'), m_jj > 100, |eta_l| < 3. ATLAS llvvjj_ss: off-shell, pT_l > 5, no m_jj cut.

#### N2 71640 — WpWpJJ_QCDnotop_TuneCP5_13TeV-madgraph-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [71639](https://opendata.cern.ch/record/71639)) | 0.02037 | filter 1, matching 1, neg. weights 0 | VERIFIED (saved record) |
| (b) McM generator value ([SUS-RunIISummer20UL16wmLHEGEN-00123](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/SUS-RunIISummer20UL16wmLHEGEN-00123)) | 0.02227 | filter 1, match 1 | VERIFIED (saved request JSON); user-entered value |
| (c) none found for the generator phase space | — |  | no published QCD same-sign WWjj total for these cuts |
| (e) ATLAS σ×k×ε (700603) | 0.02221 | 700603: 0.022206×1×1 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.9173 |

- **R1:** Decay inside the MadGraph matrix element (process card decay chain `v > l v`); no separate decay step, no filter (fragment filterEfficiency 1.0), no matching (ickkw 0): R1 applies, the portal total_value is the complete generator cross section of the sample.
- **(d) registry v5 analogue:** Dibosons (E1): generator x NNLO/NLO k-factor (WZ, ZZ) or NNLO total x BR (WW); tribosons 72701/72711 and ttZ/ttW: generator NLO value as is. No EW VV+2j precedent: E2 dropped the EW V+2j samples (35999/35987/35993) before any value was chosen.
- **Generator settings:** CMS card: p p > w+w+ j j and w-w- j j, QED=2 QCD=99, $ t t~, m_jj > 100, |eta_l| < 3. ATLAS 700603: Sherpa 0,1j@LO Order(*,4), pT_l > 5, >= 2 jets pT > 15, no m_jj cut. McM 0.02227 pb vs portal 0.02037 pb.

#### N3 37276 — GluGluHToEEG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnlo_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [37275](https://opendata.cern.ch/record/37275)) | 0.002816 | filter 1, matching 0.3, neg. weights 0.2151 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-04069](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-04069)) | 0.0008082 | filter 1, match 0.308 | VERIFIED (saved request JSON); user-entered value |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 0.003498 | 48.58 x 7.20e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->eegamma) = 7.20e-5 estimated with Pythia 8 for m_ll < 30 GeV (an ATLAS MC estimate, not a theory calculation; agrees with Refs. [74,76] within 3 % 'when extrapolated to a common phase space') |
| (c) YR4 sigma x B(CMS MCFM) | — |  | CMS-HIG-17-007 gives no ee value (only mumu) |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 0.002505 | 48.58 x 1.533e-3 x 0.033632 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 5.797e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345961) | 0.02092 | 345961: 28.3×1.717×0.0004306 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.1346 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO HEFT ggH 0,1,2j FxFx (ptj 10, qCut 30); decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas; no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Match of these master-branch cards to the gridpack: UNVERIFIED (see the gridpack check). ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 37420 — GluGluHToMuMuG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnlo_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [37419](https://opendata.cern.ch/record/37419)) | 0.001858 | filter 1, matching 0.3, neg. weights 0.2151 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-04063](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-04063)) | 0.0008082 | filter 1, match 0.308 | VERIFIED (saved request JSON); user-entered value |
| (c) YR4 sigma x B(CMS MCFM, m_mumu < 50 GeV) | 0.001861 | 48.58 x 3.83e-5 | CMS-HIG-17-007, arXiv:1806.05996, Eq. (1) and text: B(H->gamma*gamma->mumugamma) = 3.83e-5 from MCFM 7.0.1; the paper separates H->gamma*gamma from H->Zgamma at m_ll = 50 GeV (the cut is stated in the text around Eq. (1), not next to the number: INTERPRETATION) |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 0.001661 | 48.58 x 3.42e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->mumugamma) = 3.42e-5, Pythia 8, m_ll < 30 GeV |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 0.002507 | 48.58 x 1.533e-3 x 0.033662 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 3.825e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345961) | 0.02092 | 345961: 28.3×1.717×0.0004306 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.0888 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO HEFT ggH 0,1,2j FxFx (ptj 10, qCut 30); decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas; no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Match of these master-branch cards to the gridpack: UNVERIFIED (see the gridpack check). ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 68459 — VBFHToEEG_M125_Dalitz_TuneCP5_13TeV-amcatnlo-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [68458](https://opendata.cern.ch/record/68458)) | 0.000315 | filter 1, matching 1, neg. weights 0.3429 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-04047](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-04047)) | 1 | filter 1, match 1 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 0.0002723 | 3.782 x 7.20e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->eegamma) = 7.20e-5 estimated with Pythia 8 for m_ll < 30 GeV (an ATLAS MC estimate, not a theory calculation; agrees with Refs. [74,76] within 3 % 'when extrapolated to a common phase space') |
| (c) YR4 sigma x B(CMS MCFM) | — |  | CMS-HIG-17-007 gives no ee value (only mumu) |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 0.000195 | 3.782 x 1.533e-3 x 0.033632 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 8.329e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345834) | 0.008585 | 345834: 3.782×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.03669 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO VBF NLO; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas; no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Match of these master-branch cards to the gridpack: UNVERIFIED (see the gridpack check). ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 68559 — VBFHToMuMuG_M125_Dalitz_TuneCP5_13TeV-amcatnlo-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [68558](https://opendata.cern.ch/record/68558)) | 0.000208 | filter 1, matching 1, neg. weights 0.3435 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-04044](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-04044)) | 1 | filter 1, match 1 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(CMS MCFM, m_mumu < 50 GeV) | 0.0001449 | 3.782 x 3.83e-5 | CMS-HIG-17-007, arXiv:1806.05996, Eq. (1) and text: B(H->gamma*gamma->mumugamma) = 3.83e-5 from MCFM 7.0.1; the paper separates H->gamma*gamma from H->Zgamma at m_ll = 50 GeV (the cut is stated in the text around Eq. (1), not next to the number: INTERPRETATION) |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 0.0001293 | 3.782 x 3.42e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->mumugamma) = 3.42e-5, Pythia 8, m_ll < 30 GeV |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 0.0001952 | 3.782 x 1.533e-3 x 0.033662 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 5.5e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345834) | 0.008585 | 345834: 3.782×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.02423 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO VBF NLO; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas; no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Match of these master-branch cards to the gridpack: UNVERIFIED (see the gridpack check). ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 69681 — WHToEEG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnloFXFX_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [69680](https://opendata.cern.ch/record/69680)) | 0.0001238 | filter 1, matching 0.3, neg. weights 0.1937 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-03857](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-03857)) | 1 | filter 1, match 0.318 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 9.884e-05 | 1.373 x 7.20e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->eegamma) = 7.20e-5 estimated with Pythia 8 for m_ll < 30 GeV (an ATLAS MC estimate, not a theory calculation; agrees with Refs. [74,76] within 3 % 'when extrapolated to a common phase space') |
| (c) YR4 sigma x B(CMS MCFM) | — |  | CMS-HIG-17-007 gives no ee value (only mumu) |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 7.078e-05 | 1.373 x 1.533e-3 x 0.033632 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 9.018e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345963, 345964) | 0.003116 | 345963: 0.5328×1×0.00227; 345964: 0.84×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.03973 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO WH 0,1,2j NLO FxFx; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas; no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Match of these master-branch cards to the gridpack: UNVERIFIED (see the gridpack check). ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 69699 — WHToMuMuG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnloFXFX_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [69698](https://opendata.cern.ch/record/69698)) | 8.169e-05 | filter 1, matching 0.3, neg. weights 0.1933 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-03848](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-03848)) | 1 | filter 1, match 0.318 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(CMS MCFM, m_mumu < 50 GeV) | 5.258e-05 | 1.373 x 3.83e-5 | CMS-HIG-17-007, arXiv:1806.05996, Eq. (1) and text: B(H->gamma*gamma->mumugamma) = 3.83e-5 from MCFM 7.0.1; the paper separates H->gamma*gamma from H->Zgamma at m_ll = 50 GeV (the cut is stated in the text around Eq. (1), not next to the number: INTERPRETATION) |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 4.695e-05 | 1.373 x 3.42e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->mumugamma) = 3.42e-5, Pythia 8, m_ll < 30 GeV |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 7.084e-05 | 1.373 x 1.533e-3 x 0.033662 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 5.951e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345963, 345964) | 0.003116 | 345963: 0.5328×1×0.00227; 345964: 0.84×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.02621 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO WH 0,1,2j NLO FxFx; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas; no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Match of these master-branch cards to the gridpack: UNVERIFIED (see the gridpack check). ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 74652 — ZHToEEG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnloFXFX_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [74651](https://opendata.cern.ch/record/74651)) | 6.762e-05 | filter 1, matching 0.3, neg. weights 0.1988 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-03856](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-03856)) | 1 | filter 1, match 0.4 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 5.481e-05 | 0.7612 x 7.20e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->eegamma) = 7.20e-5 estimated with Pythia 8 for m_ll < 30 GeV (an ATLAS MC estimate, not a theory calculation; agrees with Refs. [74,76] within 3 % 'when extrapolated to a common phase space') |
| (c) YR4 sigma x B(CMS MCFM) | — |  | CMS-HIG-17-007 gives no ee value (only mumu) |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 3.925e-05 | 0.7612 x 1.533e-3 x 0.033632 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 8.883e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345965) | 0.001728 | 345965: 0.7612×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.03913 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO ZH 0,1,2j NLO FxFx; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas; no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Match of these master-branch cards to the gridpack: UNVERIFIED (see the gridpack check). ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 74670 — ZHToMuMuG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnloFXFX_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [74669](https://opendata.cern.ch/record/74669)) | 4.459e-05 | filter 1, matching 0.3, neg. weights 0.1992 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-03850](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-03850)) | 1 | filter 1, match 0.4 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(CMS MCFM, m_mumu < 50 GeV) | 2.915e-05 | 0.7612 x 3.83e-5 | CMS-HIG-17-007, arXiv:1806.05996, Eq. (1) and text: B(H->gamma*gamma->mumugamma) = 3.83e-5 from MCFM 7.0.1; the paper separates H->gamma*gamma from H->Zgamma at m_ll = 50 GeV (the cut is stated in the text around Eq. (1), not next to the number: INTERPRETATION) |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 2.603e-05 | 0.7612 x 3.42e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->mumugamma) = 3.42e-5, Pythia 8, m_ll < 30 GeV |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 3.928e-05 | 0.7612 x 1.533e-3 x 0.033662 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 5.858e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345965) | 0.001728 | 345965: 0.7612×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.02581 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO ZH 0,1,2j NLO FxFx; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas; no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Match of these master-branch cards to the gridpack: UNVERIFIED (see the gridpack check). ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N4 74314 — ZH_HToZZ_4LFilter_M125_TuneCP5_13TeV_powheg2-minlo-HZJ_JHUGenV7011_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [74313](https://opendata.cern.ch/record/74313)) | 0.7935 | filter 1, matching 0.2, neg. weights 0.02914 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-00239](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-00239)) | 1 | filter 1, match 0.1509 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) A: YR4 qq->ZH x BR(H->4l, l=e,mu,tau) | 0.0002089 | 0.7612 x 2.745e-4 | the convention of v5 71227/70383 (WH H->ZZ->4l) and of ATLAS 346645; counts only events with 4 leptons from the Higgs, so it misses the filtered events where the 4th/3rd lepton comes from the associated Z |
| (c) B: v5 40062 convention (estimate) | 0.0003861 | 0.7612 x 0.02619 x 0.10099 x 0.19178 | eps = 1-(1-BR(Z->ll))^2: P(at least one of the other H-Z and the associated Z -> ll), as 40062; ESTIMATE; ignores tau decays and lepton counting details |
| (c) C: YR4 qq->ZH x BR(H->ZZ) x BR(Z->ll) x McM validation efficiency 0.1509 | 0.0003038 | 0.7612 x 0.02619 x 0.10099 x 0.15088 | only valid if 0.1509 is the filter efficiency relative to H->Z(ll)Z(any); what 0.1509 is relative to is NOT documented (open) |
| (c) D: portal 0.7935 x BR(H->ZZ) x BR(Z->ll) x 0.1509 | 0.0003167 | 0.7935 x 0.02619 x 0.10099 x 0.15088 | generator production sigma instead of YR4 |
| (c) E: measure the filter content in file 0 (precheck, generator particles) | — |  | REPORT section 5: fraction of events by H->ZZ and associated-Z decay |
| (e) ATLAS σ×k×ε (346645) | 0.0002089 | 346645: 0.7612×1×0.0002745 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 3798 |

- **R1:** Production POWHEG HZJ MiNLO (Z -> all, vdecaymode 10, min_z_mass 10 GeV); H decay in a SEPARATE JHUGen step (DecayMode1=8 Z->2l incl. tau, DecayMode2=9 Z->anything, FilterNLept=4, WriteFailedEvents=2). R1: the decay BR is NOT inside the portal value; the portal value 0.7935 pb is close to the ZH production sigma (YR4 qq->ZH 0.7612, ZH total 0.8839), so the 4-lepton filter efficiency is NOT inside it either (if it were, the production sigma would be ~4-5 pb). The portal 'matching_efficiency' 0.2 (McM match_efficiency 0.1509, the validation efficiency) is therefore most likely the JHUGen filter efficiency, not a jet-matching efficiency (INTERPRETATION, open).
- **(d) registry v5 analogue:** 40062 ggZH 4l (ESTIMATE, 0.1227 x 0.02619 x 0.10099 x 0.19178); 71227/70383 WH 4l (YR4 x 2.745e-4); 37728/68847 ggF/VBF 4l (YR4 x 2.745e-4).
- **Generator settings:** ATLAS 346645 = 0.7612 x 2.745e-4 (S2: the same 2.745e-4 is used as filter for H->mumu samples).

