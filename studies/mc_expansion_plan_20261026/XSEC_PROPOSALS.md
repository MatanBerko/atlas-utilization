# Cross-section PROPOSALS for the planned samples (26 Oct 2026)

**Nothing here is applied.** No value enters any registry or config. Each section is for Matan's
manual check, one sample at a time, in the order of the plan's tiers. Format as in the 14-15 Oct review.

Status of the numbers:
- Every source number was **read on 26 Oct 2026 from the page linked** (VERIFIED BY RUNNING: fetched with curl /
  pdf text extraction; where on the page and the number as printed: table 'Sources used' below).
- Every generator value and efficiency was **read from the CERN Open Data API** on 26 Oct 2026
  (VERIFIED BY RUNNING; raw copies `evidence/records/<MiniAOD recid>.json.gz`).
- The proposed σ_eff is arithmetic on those numbers (VERIFIED BY RUNNING, `xsec_proposals.py`).
- Whether each proposal is *right* is for Matan: these are proposals, not decisions.
- 'matching eff.' is shown exactly as on the portal and is **never multiplied in** (open point since 15 Oct).

## Sources used

| key | link | where | as printed |
|---|---|---|---|
| PDG_W | <https://pdglive.lbl.gov/Particle.action?node=S043> | W DECAY MODES: e+ nu, mu+ nu, tau+ nu, hadrons | (10.71 ± 0.16) %, (10.63 ± 0.15) %, (11.38 ± 0.21) %, (67.41 ± 0.27) % |
| PDG_Z | <https://pdglive.lbl.gov/Particle.action?node=S044> | Z DECAY MODES: Gamma1 e+e-, Gamma2 mu+mu-, Gamma3 tau+tau-, Gamma7 invisible, Gamma8 hadrons | (3.3632 ± 0.0042) %, (3.3662 ± 0.0066) %, (3.3696 ± 0.0083) %, (20.000 ± 0.055) %, (69.911 ± 0.056) % |
| RAZOR | <https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat> | line 64, under '#13 TeV Spring 15 MC' (SECONDARY source; same table as our DY 1921.8*3, line 90) | WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7 |
| ST_NNLO_S | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef> | section 'Single-top-quark s channel cross-sections', 13 TeV table, rows 'top quark' / 'top antiquark' / 'top quark + antiquark' (NNLO, Liu & Gao arXiv:1807.03835) | 6.828 / 4.245 / 11.073 |
| ST_NNLO_T | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef> | section 'Single top-quark t channel cross-sections', 13 TeV table, rows 'top quark' / 'top antiquark' (MCFM NNLO, mt = 172.5 GeV, page dated 2026-10-02) | 134.2 / 80.0 |
| TTBAR | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/TtbarNNLO> | table 'Updated reference cross sections ...' (Updated: July 2022), block '13 TeV', column 'Central value' | 833.9 |
| WW | <https://arxiv.org/abs/1408.5243> | Table I (on-shell W+W−, 4FNS, includes gg → WW), row 13: σNNLO | 118.7 pb |
| WZ | <https://arxiv.org/abs/1604.08576> | Table 1 (on-shell W±Z), row √s = 13: σNLO, σNNLO | 46.068(3) pb, 51.11(3) pb |
| YR4_BR | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR> | rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ) | bb 5.824E-01; ττ 6.272E-02; WW 2.137E-01; ZZ 2.619E-02; 4l 2.745E-04 |
| YR4_XS | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV> | rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table | ggF 4.858E+01; VBF 3.782E+00; W+H 8.400E-01, W−H 5.328E-01; all-but-gg→ZH 0.7612, gg→ZH 0.1227; ttH 5.071E-01 (pb) |
| ZZ | <https://arxiv.org/abs/1405.2219> | Table 1 (inclusive ZZ, includes gg → ZZ at NNLO), row 13: σNLO, σNNLO | 14.51 pb, 16.91 pb |
| TTTT_NLO | <https://arxiv.org/abs/1711.02116> | Table 5, µ = HT/4, column 'LO + NLO' (complete NLO QCD+EW) | 11.97 fb |
| TTTT_NLL | <https://arxiv.org/abs/2212.03259> | Table I, √s = 13 TeV, NLO(QCD+EW)+NLL′ (µ0 = 2 mt) | 14.65(2) fb |
| ATLAS_W | <https://arxiv.org/abs/1603.09222> | ATLAS, PLB 759 (2016) 601, Table 3, row 'W±', 'Predicted ... Total' (DYNNLO NNLO QCD + NLO EW, CT14nnlo; per lepton flavour) | 20.08 nb |
| ST_NLO_T | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec> | section 'Single-top t channel cross sections (superseded)', 13 TeV, rows 'top' / 'anti-top' (Hathor NLO) | 136.02 / 80.95 |
| ST_NLO_S | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec> | section 'Single-top s channel cross sections', 13 TeV, rows 'top' / 'anti-top' / 'top + anti-top' (Hathor NLO) | 6.35 / 3.97 / 10.32 |
| ST_NNLO_TW | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef> | section 'Single-top-quark tW channel cross-sections', 13 TeV, row 'top quark + antiquark' (NLO + NNLL soft-gluon third order, Kidonakis arXiv:2102.11300) | 79.3 |
| ST_TW_OLD | <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec> | section 'Single-top Wt channel cross sections', 13 TeV, row 'top + antitop' (Kidonakis approx. NNLO) | 71.7 |
| JHUGEN | <https://raw.githubusercontent.com/JHUGen/JHUGen/master/JHUGenerator/main.F90> | comment block at lines 357-368 (JHUGen master; the samples used v7.x -- assumed unchanged, UNVERIFIED for the exact version) | DecayMode=0: Z --> l+ l- (l=e,mu); 3: Z --> nu nubar; 8: Z --> l+ l- (l=e,mu,tau); 10: W --> l nu_l (l=e,mu,tau); 11: W --> anything |

## 1. 69715 WJetsToLNu_0J_amcatnloFXFX — tier 1

- **What it is:** W boson decaying to a charged lepton (e, μ or τ) and a neutrino, with exactly 0 extra parton(s) in the NLO matrix element (one of three pieces that together make all of W+jets).
- **Dataset:** `/WJetsToLNu_0J_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 69714; <https://opendata.cern.ch/record/69715>)
- **Proposed σ_eff = 49999.6 pb** = 53300 × 0.938079

  - generator σ (portal, 0J piece): **53300** — portal API <https://opendata.cern.ch/api/records/69714> metadata.cross_section.total_value
  - k = 61526.7 / (53300 + 8958 + 3330), NNLO inclusive ÷ sum of the three NLO pieces: **0.938079** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat — line 64, under '#13 TeV Spring 15 MC' (SECONDARY source; same table as our DY 1921.8*3, line 90)

- **Order:** NLO generator × NNLO/NLO k-factor (inclusive W → ℓν, FEWZ NNLO in the table).
- **Portal (generator) values:** total_value = 5.330e+04 pb, filter eff. = 1.000e+00, matching eff. = 0.9, negative-weight fraction = 9.888e-02 (<https://opendata.cern.ch/api/records/69714>).
- **Proposed / generator:** 0.9381
- **What Matan should open and look for:** RazorAnalyzer xSections.dat line 64: 'WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7'. The three portal values on the MiniAOD records 69714 / 69716 / 69718 (metadata.cross_section.total_value).
- **Convention:** No published total for a jet-multiplicity piece → generator × k-factor. The k-factor numerator is the same SECONDARY table as our DY (Matan, 15 Oct), for consistency. Not a paper table, so the 'k-factor from a paper table' rule is only partly met.
- **Alternatives considered:** k from the inclusive NLO sample instead (61526.7 / 66970) → -2.1 %; primary source instead: ATLAS 1603.09222 Table 3, 3 × 20.08 nb = 60240 pb → -2.1 %
- **Note:** Portal matching efficiencies 0.9 / 0.2 / 0.1 are shown but NOT multiplied in. The three portal values add up to 65588 pb, close to the inclusive NLO sample's 66970 pb, which suggests total_value already includes the matching efficiency (if it did not, the pieces would sum to 50095 pb). Also, the inclusive NLO value 66970 pb × 0.4 = 26788 pb would be less than half of every W → ℓν prediction and measurement (ATLAS measured 3 × 20.64 nb), so for this record total_value must already include the matching efficiency. Evidence for the open point, not a decision.

## 2. 69717 WJetsToLNu_1J_amcatnloFXFX — tier 1

- **What it is:** W boson decaying to a charged lepton (e, μ or τ) and a neutrino, with exactly 1 extra parton(s) in the NLO matrix element (one of three pieces that together make all of W+jets).
- **Dataset:** `/WJetsToLNu_1J_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 69716; <https://opendata.cern.ch/record/69717>)
- **Proposed σ_eff = 8403.31 pb** = 8958 × 0.938079

  - generator σ (portal, 1J piece): **8958** — portal API <https://opendata.cern.ch/api/records/69716> metadata.cross_section.total_value
  - k = 61526.7 / (53300 + 8958 + 3330), NNLO inclusive ÷ sum of the three NLO pieces: **0.938079** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat — line 64, under '#13 TeV Spring 15 MC' (SECONDARY source; same table as our DY 1921.8*3, line 90)

- **Order:** NLO generator × NNLO/NLO k-factor (inclusive W → ℓν, FEWZ NNLO in the table).
- **Portal (generator) values:** total_value = 8.958e+03 pb, filter eff. = 1.000e+00, matching eff. = 0.2, negative-weight fraction = 2.574e-01 (<https://opendata.cern.ch/api/records/69716>).
- **Proposed / generator:** 0.9381
- **What Matan should open and look for:** RazorAnalyzer xSections.dat line 64: 'WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7'. The three portal values on the MiniAOD records 69714 / 69716 / 69718 (metadata.cross_section.total_value).
- **Convention:** No published total for a jet-multiplicity piece → generator × k-factor. The k-factor numerator is the same SECONDARY table as our DY (Matan, 15 Oct), for consistency. Not a paper table, so the 'k-factor from a paper table' rule is only partly met.
- **Alternatives considered:** k from the inclusive NLO sample instead (61526.7 / 66970) → -2.1 %; primary source instead: ATLAS 1603.09222 Table 3, 3 × 20.08 nb = 60240 pb → -2.1 %
- **Note:** Portal matching efficiencies 0.9 / 0.2 / 0.1 are shown but NOT multiplied in. The three portal values add up to 65588 pb, close to the inclusive NLO sample's 66970 pb, which suggests total_value already includes the matching efficiency (if it did not, the pieces would sum to 50095 pb). Also, the inclusive NLO value 66970 pb × 0.4 = 26788 pb would be less than half of every W → ℓν prediction and measurement (ATLAS measured 3 × 20.64 nb), so for this record total_value must already include the matching efficiency. Evidence for the open point, not a decision.

## 3. 69719 WJetsToLNu_2J_amcatnloFXFX — tier 1

- **What it is:** W boson decaying to a charged lepton (e, μ or τ) and a neutrino, with exactly 2 extra parton(s) in the NLO matrix element (one of three pieces that together make all of W+jets).
- **Dataset:** `/WJetsToLNu_2J_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 69718; <https://opendata.cern.ch/record/69719>)
- **Proposed σ_eff = 3123.8 pb** = 3330 × 0.938079

  - generator σ (portal, 2J piece): **3330** — portal API <https://opendata.cern.ch/api/records/69718> metadata.cross_section.total_value
  - k = 61526.7 / (53300 + 8958 + 3330), NNLO inclusive ÷ sum of the three NLO pieces: **0.938079** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat — line 64, under '#13 TeV Spring 15 MC' (SECONDARY source; same table as our DY 1921.8*3, line 90)

- **Order:** NLO generator × NNLO/NLO k-factor (inclusive W → ℓν, FEWZ NNLO in the table).
- **Portal (generator) values:** total_value = 3.330e+03 pb, filter eff. = 1.000e+00, matching eff. = 0.1, negative-weight fraction = 3.439e-01 (<https://opendata.cern.ch/api/records/69718>).
- **Proposed / generator:** 0.9381
- **What Matan should open and look for:** RazorAnalyzer xSections.dat line 64: 'WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7'. The three portal values on the MiniAOD records 69714 / 69716 / 69718 (metadata.cross_section.total_value).
- **Convention:** No published total for a jet-multiplicity piece → generator × k-factor. The k-factor numerator is the same SECONDARY table as our DY (Matan, 15 Oct), for consistency. Not a paper table, so the 'k-factor from a paper table' rule is only partly met.
- **Alternatives considered:** k from the inclusive NLO sample instead (61526.7 / 66970) → -2.1 %; primary source instead: ATLAS 1603.09222 Table 3, 3 × 20.08 nb = 60240 pb → -2.1 %
- **Note:** Portal matching efficiencies 0.9 / 0.2 / 0.1 are shown but NOT multiplied in. The three portal values add up to 65588 pb, close to the inclusive NLO sample's 66970 pb, which suggests total_value already includes the matching efficiency (if it did not, the pieces would sum to 50095 pb). Also, the inclusive NLO value 66970 pb × 0.4 = 26788 pb would be less than half of every W → ℓν prediction and measurement (ATLAS measured 3 × 20.64 nb), so for this record total_value must already include the matching efficiency. Evidence for the open point, not a decision.

## 4. 64793 ST_t-channel_top_5f_InclusiveDecays — tier 1

- **What it is:** Single top production in the t-channel (5-flavour scheme), all top decays.
- **Dataset:** `/ST_t-channel_top_5f_InclusiveDecays_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 64792; <https://opendata.cern.ch/record/64793>)
- **Proposed σ_eff = 134.2 pb** = 134.2

  - σ(t-channel top), NNLO: **134.2** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef — section 'Single top-quark t channel cross-sections', 13 TeV table, rows 'top quark' / 'top antiquark' (MCFM NNLO, mt = 172.5 GeV, page dated 2026-10-02)

- **Order:** NNLO QCD (MCFM).
- **Portal (generator) values:** total_value = 1.197e+02 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.851e-03 (<https://opendata.cern.ch/api/records/64792>).
- **Proposed / generator:** 1.1211
- **What Matan should open and look for:** SingleTopNNLORef, 't channel' 13 TeV table, row 'top quark', Central value = 134.2.
- **Convention:** Top WG recommendation (the old Hathor NLO page now says 'Superseded by NNLO predictions').
- **Alternatives considered:** Top WG Hathor NLO (superseded) → +1.4 %

## 5. 64693 ST_t-channel_antitop_5f_InclusiveDecays — tier 1

- **What it is:** Single antitop production in the t-channel (5-flavour scheme), all top decays.
- **Dataset:** `/ST_t-channel_antitop_5f_InclusiveDecays_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 64692; <https://opendata.cern.ch/record/64693>)
- **Proposed σ_eff = 80 pb** = 80

  - σ(t-channel antitop), NNLO: **80** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef — section 'Single top-quark t channel cross-sections', 13 TeV table, rows 'top quark' / 'top antiquark' (MCFM NNLO, mt = 172.5 GeV, page dated 2026-10-02)

- **Order:** NNLO QCD (MCFM).
- **Portal (generator) values:** total_value = 7.174e+01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.727e-03 (<https://opendata.cern.ch/api/records/64692>).
- **Proposed / generator:** 1.1151
- **What Matan should open and look for:** SingleTopNNLORef, 't channel' 13 TeV table, row 'top antiquark', Central value = 80.0.
- **Convention:** Top WG recommendation (the old Hathor NLO page now says 'Superseded by NNLO predictions').
- **Alternatives considered:** Top WG Hathor NLO (superseded) → +1.2 %

## 6. 64635 ST_s-channel_4f_leptonDecays — tier 1

- **What it is:** Single top (or antitop) in the s-channel, top decaying to b + W → ℓν (e, μ, τ).
- **Dataset:** `/ST_s-channel_4f_leptonDecays_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 64634; <https://opendata.cern.ch/record/64635>)
- **Proposed σ_eff = 3.62309 pb** = 11.073 × 0.3272

  - σ(s-channel, top + antitop), NNLO: **11.073** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef — section 'Single-top-quark s channel cross-sections', 13 TeV table, rows 'top quark' / 'top antiquark' / 'top quark + antiquark' (NNLO, Liu & Gao arXiv:1807.03835)
  - BR(W → ℓν) = 0.1071 + 0.1063 + 0.1138: **0.3272** — https://pdglive.lbl.gov/Particle.action?node=S043 — W DECAY MODES: e+ nu, mu+ nu, tau+ nu, hadrons

- **Order:** NNLO QCD.
- **Portal (generator) values:** total_value = 3.549e+00 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 1.744e-01 (<https://opendata.cern.ch/api/records/64634>).
- **Proposed / generator:** 1.0209
- **What Matan should open and look for:** SingleTopNNLORef, 's channel' 13 TeV table, row 'top quark + antiquark' = 11.073. pdglive S043.
- **Convention:** Top WG recommendation × PDG individually measured W branching ratios (settled convention).
- **Alternatives considered:** Top WG Hathor NLO (10.32 pb) → -6.8 %
- **Note:** Generator card (evidence/cards/64635): 'decay t > w+ b, w+ > ell+ vl' with ell = e, μ, τ.

## 7. 67841 TTToHadronic — tier 1

- **What it is:** Top-quark pairs with both W bosons decaying to quarks.
- **Dataset:** `/TTToHadronic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 67840; <https://opendata.cern.ch/record/67841>)
- **Proposed σ_eff = 378.933 pb** = 833.9 × 0.454411

  - σ(tt̄), NNLO+NNLL, mt = 172.5 GeV: **833.9** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/TtbarNNLO — table 'Updated reference cross sections ...' (Updated: July 2022), block '13 TeV', column 'Central value'
  - BR(W → hadrons)²: **0.454411** — https://pdglive.lbl.gov/Particle.action?node=S043 — W DECAY MODES: e+ nu, mu+ nu, tau+ nu, hadrons

- **Order:** NNLO+NNLL.
- **Portal (generator) values:** total_value = 6.871e+02 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 4.038e-03 (<https://opendata.cern.ch/api/records/67840>).
- **Proposed / generator:** 0.5515
- **What Matan should open and look for:** TtbarNNLO: the 13 TeV block of the first table, 'Central value' = 833.9. pdglive S043: the four W decay fractions.
- **Convention:** Settled convention (833.9 pb × 0.6741², as in the hint).
- **Alternatives considered:** none with a public source found.
- **Note:** With the individual PDG values the three tt̄ samples add up to 0.10706 + 0.44113 + 0.45441 = 1.0026 of tt̄ (the PDG W fractions sum to 1.0013). A +0.26 % overcount of tt̄ that follows from the settled convention; reported, not changed.

## 8. 69745 WJetsToLNu_amcatnloFXFX (inclusive NLO) — tier 1 (ALTERNATIVE, for a decision in PLAN.md)

- **What it is:** Inclusive W → ℓν (e, μ, τ) + 0, 1, 2 partons at NLO (alternative to the three pieces).
- **Dataset:** `/WJetsToLNu_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 69744; <https://opendata.cern.ch/record/69745>)
- **Proposed σ_eff = 61526.7 pb** = 61526.7

  - NNLO inclusive W → ℓν, 3 lepton flavours: **61526.7** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat — line 64, under '#13 TeV Spring 15 MC' (SECONDARY source; same table as our DY 1921.8*3, line 90)

- **Order:** NNLO QCD (secondary table).
- **Portal (generator) values:** total_value = 6.697e+04 pb, filter eff. = 1.000e+00, matching eff. = 0.4, negative-weight fraction = 1.570e-01 (<https://opendata.cern.ch/api/records/69744>).
- **Proposed / generator:** 0.9187
- **What Matan should open and look for:** RazorAnalyzer line 64 (61526.7).
- **Convention:** Table value, same construction as our DY M-50 (3 × 1921.8).
- **Alternatives considered:** ATLAS 1603.09222 Table 3 (primary), 60240 pb → -2.1 %

## 9. 69747 WJetsToLNu_madgraphMLM (inclusive LO) — tier 1 (ALTERNATIVE, for a decision in PLAN.md)

- **What it is:** Inclusive W → ℓν (e, μ, τ) + up to 4 partons at LO (alternative; the only set that could be stitched with the LO jet-/HT-binned samples).
- **Dataset:** `/WJetsToLNu_TuneCP5_13TeV-madgraphMLM-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 69746; <https://opendata.cern.ch/record/69747>)
- **Proposed σ_eff = 61526.7 pb** = 61526.7

  - NNLO inclusive W → ℓν, 3 lepton flavours: **61526.7** — https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat — line 64, under '#13 TeV Spring 15 MC' (SECONDARY source; same table as our DY 1921.8*3, line 90)

- **Order:** NNLO QCD (secondary table) applied to an LO sample.
- **Portal (generator) values:** total_value = 5.411e+04 pb, filter eff. = 1.000e+00, matching eff. = 0.4, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/69746>).
- **Proposed / generator:** 1.1371
- **What Matan should open and look for:** RazorAnalyzer line 64 (61526.7).
- **Convention:** Table value; an LO sample normalised to NNLO (k = 61526.7 / 54110 = 1.137 relative to its generator value).
- **Alternatives considered:** ATLAS 1603.09222 Table 3 (primary), 60240 pb → -2.1 %

## 10. 64759 ST_t-channel_top_4f_InclusiveDecays — tier 1 (ALTERNATIVE, for a decision in PLAN.md)

- **What it is:** Single top production in the t-channel (4-flavour scheme), all top decays.
- **Dataset:** `/ST_t-channel_top_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 64758; <https://opendata.cern.ch/record/64759>)
- **Proposed σ_eff = 134.2 pb** = 134.2

  - σ(t-channel top), NNLO: **134.2** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef — section 'Single top-quark t channel cross-sections', 13 TeV table, rows 'top quark' / 'top antiquark' (MCFM NNLO, mt = 172.5 GeV, page dated 2026-10-02)

- **Order:** NNLO QCD (MCFM).
- **Portal (generator) values:** total_value = 1.134e+02 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 3.161e-02 (<https://opendata.cern.ch/api/records/64758>).
- **Proposed / generator:** 1.1834
- **What Matan should open and look for:** SingleTopNNLORef, 't channel' 13 TeV table, row 'top quark', Central value = 134.2.
- **Convention:** Top WG recommendation (the old Hathor NLO page now says 'Superseded by NNLO predictions').
- **Alternatives considered:** Top WG Hathor NLO (superseded) → +1.4 %

## 11. 64659 ST_t-channel_antitop_4f_InclusiveDecays — tier 1 (ALTERNATIVE, for a decision in PLAN.md)

- **What it is:** Single antitop production in the t-channel (4-flavour scheme), all top decays.
- **Dataset:** `/ST_t-channel_antitop_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 64658; <https://opendata.cern.ch/record/64659>)
- **Proposed σ_eff = 80 pb** = 80

  - σ(t-channel antitop), NNLO: **80** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopNNLORef — section 'Single top-quark t channel cross-sections', 13 TeV table, rows 'top quark' / 'top antiquark' (MCFM NNLO, mt = 172.5 GeV, page dated 2026-10-02)

- **Order:** NNLO QCD (MCFM).
- **Portal (generator) values:** total_value = 6.793e+01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.929e-02 (<https://opendata.cern.ch/api/records/64658>).
- **Proposed / generator:** 1.1777
- **What Matan should open and look for:** SingleTopNNLORef, 't channel' 13 TeV table, row 'top antiquark', Central value = 80.0.
- **Convention:** Top WG recommendation (the old Hathor NLO page now says 'Superseded by NNLO predictions').
- **Alternatives considered:** Top WG Hathor NLO (superseded) → +1.2 %

## 12. 72742 WZTo2Q2L_mllmin4p0 — tier 2

- **What it is:** W → quarks plus a lepton pair (e, μ, τ; Z or virtual photon, m(ℓℓ) > 4 GeV), NLO, 0-1 extra parton.
- **Dataset:** `/WZTo2Q2L_mllmin4p0_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 72741; <https://opendata.cern.ch/record/72742>)
- **Proposed σ_eff = 7.13263 pb** = 6.429 × 1.10945

  - generator σ (portal): **6.429** — portal API <https://opendata.cern.ch/api/records/72741> metadata.cross_section.total_value
  - k = 51.11 / 46.068 (WZ NNLO/NLO): **1.10945** — https://arxiv.org/abs/1604.08576 — Table 1 (on-shell W±Z), row √s = 13: σNLO, σNNLO

- **Order:** NLO generator × NNLO/NLO k-factor.
- **Portal (generator) values:** total_value = 6.429e+00 pb, filter eff. = 1.000e+00, matching eff. = 0.7, negative-weight fraction = 1.882e-01 (<https://opendata.cern.ch/api/records/72741>).
- **Proposed / generator:** 1.1094
- **What Matan should open and look for:** arXiv:1604.08576 Table 1, row 13: σNLO 46.068, σNNLO 51.11. The portal value on the MiniAOD record.
- **Convention:** Phase space (γ* included, m(ℓℓ) > 4) matches no published total → generator × k-factor, exactly as our WZTo3LNu 72752.
- **Alternatives considered:** on-shell WZ instead: 51.11 × 0.6741 × 0.10099 → -51.2 %
- **Note:** Approximation as for 72752: an on-shell k-factor applied to a sample that also contains γ* → ℓℓ. Card: 'p p > V ell+ ell-', V = W, 'decay w+ > q q'.

## 13. 75573 ZZTo2Q2L_mllmin4p0 — tier 2

- **What it is:** Z → quarks plus a lepton pair (e, μ, τ; m(ℓℓ) > 4 GeV), NLO, 0-1 extra parton.
- **Dataset:** `/ZZTo2Q2L_mllmin4p0_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 75572; <https://opendata.cern.ch/record/75573>)
- **Proposed σ_eff = 4.31083 pb** = 3.699 × 1.1654

  - generator σ (portal): **3.699** — portal API <https://opendata.cern.ch/api/records/75572> metadata.cross_section.total_value
  - k = 16.91 / 14.51 (ZZ NNLO/NLO, includes gg → ZZ): **1.1654** — https://arxiv.org/abs/1405.2219 — Table 1 (inclusive ZZ, includes gg → ZZ at NNLO), row 13: σNLO, σNNLO

- **Order:** NLO generator × NNLO/NLO k-factor.
- **Portal (generator) values:** total_value = 3.699e+00 pb, filter eff. = 1.000e+00, matching eff. = 0.7, negative-weight fraction = 1.761e-01 (<https://opendata.cern.ch/api/records/75572>).
- **Proposed / generator:** 1.1654
- **What Matan should open and look for:** arXiv:1405.2219 Table 1, row 13: 14.51 and 16.91. The portal value on the MiniAOD record.
- **Convention:** Same as our ZZTo4L 75589.
- **Alternatives considered:** on-shell ZZ instead: 16.91 × 2 × 0.10099 × 0.69911 → -44.6 %
- **Note:** The k-factor includes gg → ZZ; no gg → ZZ → 2ℓ2q sample is proposed, so nothing is counted twice.

## 14. 72738 WZTo1L1Nu2Q — tier 2

- **What it is:** W → ℓν (e, μ, τ) with Z → quarks, NLO, 0-1 extra parton.
- **Dataset:** `/WZTo1L1Nu2Q_4f_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 72737; <https://opendata.cern.ch/record/72738>)
- **Proposed σ_eff = 10.1614 pb** = 9.159 × 1.10945

  - generator σ (portal): **9.159** — portal API <https://opendata.cern.ch/api/records/72737> metadata.cross_section.total_value
  - k = 51.11 / 46.068: **1.10945** — https://arxiv.org/abs/1604.08576 — Table 1 (on-shell W±Z), row √s = 13: σNLO, σNNLO

- **Order:** NLO generator × NNLO/NLO k-factor.
- **Portal (generator) values:** total_value = 9.159e+00 pb, filter eff. = 1.000e+00, matching eff. = 0.6, negative-weight fraction = 2.116e-01 (<https://opendata.cern.ch/api/records/72737>).
- **Proposed / generator:** 1.1094
- **What Matan should open and look for:** arXiv:1604.08576 Table 1, row 13: σNLO 46.068, σNNLO 51.11. The portal value on the MiniAOD record.
- **Convention:** Generator × k-factor, as 72752.
- **Alternatives considered:** on-shell WZ instead: 51.11 × 0.3272 × 0.69911 → +15.1 %
- **Note:** Here the boson decaying to quarks is an on-shell Z, so the on-shell construction is also defensible; a choice for Matan.

## 15. 72658 WWTo1L1Nu2Q — tier 2

- **What it is:** One W → ℓν (e, μ, τ) and the other W → quarks, NLO, 0-1 extra parton.
- **Dataset:** `/WWTo1L1Nu2Q_4f_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 72657; <https://opendata.cern.ch/record/72658>)
- **Proposed σ_eff = 52.3623 pb** = 118.7 × 0.441131

  - σ(WW), NNLO, includes gg → WW: **118.7** — https://arxiv.org/abs/1408.5243 — Table I (on-shell W+W−, 4FNS, includes gg → WW), row 13: σNNLO
  - BR = 2 × 0.3272 × 0.6741: **0.441131** — https://pdglive.lbl.gov/Particle.action?node=S043 — W DECAY MODES: e+ nu, mu+ nu, tau+ nu, hadrons

- **Order:** NNLO.
- **Portal (generator) values:** total_value = 5.089e+01 pb, filter eff. = 1.000e+00, matching eff. = 0.6, negative-weight fraction = 1.981e-01 (<https://opendata.cern.ch/api/records/72657>).
- **Proposed / generator:** 1.0289
- **What Matan should open and look for:** arXiv:1408.5243 Table I, row 13, σNNLO = 118.7. pdglive S043.
- **Convention:** Same construction as our WWTo2L2Nu 72676 (118.7 pb × BR).
- **Alternatives considered:** generator value instead → -2.8 %

## 16. 72740 WZTo1L3Nu — tier 2

- **What it is:** W → ℓν (e, μ, τ) with Z → νν, NLO, 0-1 extra parton.
- **Dataset:** `/WZTo1L3Nu_4f_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 72739; <https://opendata.cern.ch/record/72740>)
- **Proposed σ_eff = 3.78876 pb** = 3.415 × 1.10945

  - generator σ (portal): **3.415** — portal API <https://opendata.cern.ch/api/records/72739> metadata.cross_section.total_value
  - k = 51.11 / 46.068: **1.10945** — https://arxiv.org/abs/1604.08576 — Table 1 (on-shell W±Z), row √s = 13: σNLO, σNNLO

- **Order:** NLO generator × NNLO/NLO k-factor.
- **Portal (generator) values:** total_value = 3.415e+00 pb, filter eff. = 1.000e+00, matching eff. = 0.6, negative-weight fraction = 2.133e-01 (<https://opendata.cern.ch/api/records/72739>).
- **Proposed / generator:** 1.1094
- **What Matan should open and look for:** arXiv:1604.08576 Table 1, row 13: σNLO 46.068, σNNLO 51.11. The portal value on the MiniAOD record.
- **Convention:** Generator × k-factor, as 72752 (the sample is the full ℓννν final state).
- **Alternatives considered:** on-shell WZ instead: 51.11 × 0.3272 × 0.20000 → -11.7 %

## 17. 72701 WWW_4F (ext1) — tier 3

- **What it is:** WWW production at NLO, all decays.
- **Dataset:** `/WWW_4F_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 72699; <https://opendata.cern.ch/record/72701>)
- **Proposed σ_eff = 0.2158 pb** = 0.2158

  - generator σ (portal), NLO: **0.2158** — portal API <https://opendata.cern.ch/api/records/72699> metadata.cross_section.total_value

- **Order:** NLO.
- **Portal (generator) values:** total_value = 2.158e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 4.672e-02 (<https://opendata.cern.ch/api/records/72699>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** The MiniAOD record 72699: metadata.cross_section.total_value.
- **Convention:** No NNLO exists → generator value at NLO (settled convention, as ttZ/ttW).
- **Alternatives considered:** none with a public source found.

## 18. 72711 WWZ_4F (ext1) — tier 3

- **What it is:** WWZ production at NLO, all decays.
- **Dataset:** `/WWZ_4F_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 72709; <https://opendata.cern.ch/record/72711>)
- **Proposed σ_eff = 0.1707 pb** = 0.1707

  - generator σ (portal), NLO: **0.1707** — portal API <https://opendata.cern.ch/api/records/72709> metadata.cross_section.total_value

- **Order:** NLO.
- **Portal (generator) values:** total_value = 1.707e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 4.649e-02 (<https://opendata.cern.ch/api/records/72709>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** The MiniAOD record 72709: metadata.cross_section.total_value.
- **Convention:** No NNLO exists → generator value at NLO (settled convention, as ttZ/ttW).
- **Alternatives considered:** none with a public source found.

## 19. 72761 WZZ (ext1) — tier 3

- **What it is:** WZZ production at NLO, all decays.
- **Dataset:** `/WZZ_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 72759; <https://opendata.cern.ch/record/72761>)
- **Proposed σ_eff = 0.05709 pb** = 0.05709

  - generator σ (portal), NLO: **0.05709** — portal API <https://opendata.cern.ch/api/records/72759> metadata.cross_section.total_value

- **Order:** NLO.
- **Portal (generator) values:** total_value = 5.709e-02 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 4.614e-02 (<https://opendata.cern.ch/api/records/72759>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** The MiniAOD record 72759: metadata.cross_section.total_value.
- **Convention:** No NNLO exists → generator value at NLO (settled convention, as ttZ/ttW).
- **Alternatives considered:** none with a public source found.

## 20. 75600 ZZZ (ext1) — tier 3

- **What it is:** ZZZ production at NLO, all decays.
- **Dataset:** `/ZZZ_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 75598; <https://opendata.cern.ch/record/75600>)
- **Proposed σ_eff = 0.01476 pb** = 0.01476

  - generator σ (portal), NLO: **0.01476** — portal API <https://opendata.cern.ch/api/records/75598> metadata.cross_section.total_value

- **Order:** NLO.
- **Portal (generator) values:** total_value = 1.476e-02 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 5.439e-02 (<https://opendata.cern.ch/api/records/75598>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** The MiniAOD record 75598: metadata.cross_section.total_value.
- **Convention:** No NNLO exists → generator value at NLO (settled convention, as ttZ/ttW).
- **Alternatives considered:** none with a public source found.

## 21. 68325 tZq_ll_4f — tier 4

- **What it is:** Single top + Z/γ* → ℓℓ (e, μ, τ; same-flavour m(ℓℓ) > 30 GeV) + a light quark, NLO.
- **Dataset:** `/tZq_ll_4f_ckm_NLO_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 68324; <https://opendata.cern.ch/record/68325>)
- **Proposed σ_eff = 0.07561 pb** = 0.07561

  - generator σ (portal), NLO: **0.07561** — portal API <https://opendata.cern.ch/api/records/68324> metadata.cross_section.total_value

- **Order:** NLO.
- **Portal (generator) values:** total_value = 7.561e-02 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 3.647e-01 (<https://opendata.cern.ch/api/records/68324>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** MiniAOD record 68324, total_value.
- **Convention:** No NNLO → generator NLO.
- **Alternatives considered:** none with a public source found.

## 22. 64873 ST_tWll_5f — tier 4

- **What it is:** Single top + W + a lepton pair (e, μ, τ), LO (no Higgs diagrams).
- **Dataset:** `/ST_tWll_5f_TuneCP5_13TeV-madgraph-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 64872; <https://opendata.cern.ch/record/64873>)
- **Proposed σ_eff = 0.01105 pb** = 0.01105

  - generator σ (portal), LO: **0.01105** — portal API <https://opendata.cern.ch/api/records/64872> metadata.cross_section.total_value

- **Order:** LO.
- **Portal (generator) values:** total_value = 1.105e-02 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/64872>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** MiniAOD record 64872, total_value.
- **Convention:** CANNOT follow the convention: only an LO generator value exists (no NLO sample, no published total for this phase space). Decision for Matan.
- **Alternatives considered:** none with a public source found.

## 23. 67645 ttHTobb_M125 (powheg) — tier 4

- **What it is:** tt̄H with H → bb̄ (all top decays).
- **Dataset:** `/ttHTobb_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 67644; <https://opendata.cern.ch/record/67645>)
- **Proposed σ_eff = 0.295335 pb** = 0.5071 × 0.5824

  - σ(ttH), NLO QCD + NLO EW, mH = 125.00: **0.5071** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → bb), mH = 125.00: **0.5824** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** NLO QCD + NLO EW.
- **Portal (generator) values:** total_value = 5.013e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 1.036e-02 (<https://opendata.cern.ch/api/records/67644>).
- **Proposed / generator:** 0.5891
- **What Matan should open and look for:** CERNYellowReportPageAt13TeV, ttH table, 125.00 → 5.071E-01. CERNYellowReportPageBR, 'Higgs → 2 fermions', 125.00, H → bb = 5.824E-01.
- **Convention:** LHC Higgs WG YR4 at 125.00 GeV (settled).
- **Alternatives considered:** none with a public source found.

## 24. 67691 ttHToNonbb_M125 (powheg) — tier 4

- **What it is:** tt̄H with every Higgs decay except H → bb̄.
- **Dataset:** `/ttHToNonbb_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 67690; <https://opendata.cern.ch/record/67691>)
- **Proposed σ_eff = 0.211765 pb** = 0.5071 × 0.4176

  - σ(ttH): **0.5071** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - 1 − BR(H → bb): **0.4176** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** NLO QCD + NLO EW.
- **Portal (generator) values:** total_value = 5.013e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 1.033e-02 (<https://opendata.cern.ch/api/records/67690>).
- **Proposed / generator:** 0.4224
- **What Matan should open and look for:** As 67645. Pythia setting in the record: '25:offIfAny = 5 -5'.
- **Convention:** YR4 at 125.00 GeV.
- **Alternatives considered:** none with a public source found.

## 25. 68206 TTZToQQ — tier 4

- **What it is:** tt̄Z with Z → quarks (u, d, s, c, b), NLO.
- **Dataset:** `/TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 68204; <https://opendata.cern.ch/record/68206>)
- **Proposed σ_eff = 0.5113 pb** = 0.5113

  - generator σ (portal), NLO: **0.5113** — portal API <https://opendata.cern.ch/api/records/68204> metadata.cross_section.total_value

- **Order:** NLO.
- **Portal (generator) values:** total_value = 5.113e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.517e-01 (<https://opendata.cern.ch/api/records/68204>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** MiniAOD record 68204, total_value.
- **Convention:** No NNLO → generator NLO, as our ttZ 68187.
- **Alternatives considered:** none with a public source found.

## 26. 68083 TTWJetsToQQ — tier 4

- **What it is:** tt̄W with W → quarks, NLO, 0-1 extra parton.
- **Dataset:** `/TTWJetsToQQ_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 68082; <https://opendata.cern.ch/record/68083>)
- **Proposed σ_eff = 0.4375 pb** = 0.4375

  - generator σ (portal), NLO: **0.4375** — portal API <https://opendata.cern.ch/api/records/68082> metadata.cross_section.total_value

- **Order:** NLO.
- **Portal (generator) values:** total_value = 4.375e-01 pb, filter eff. = 1.000e+00, matching eff. = 0.6, negative-weight fraction = 2.264e-01 (<https://opendata.cern.ch/api/records/68082>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** MiniAOD record 68082, total_value (matching efficiency 0.6 shown, not applied -- the same open point as 68073).
- **Convention:** No NNLO → generator NLO, as our ttW 68073.
- **Alternatives considered:** none with a public source found.

## 27. 68045 TTTT — tier 4

- **What it is:** Four top quarks, all decays, NLO.
- **Dataset:** `/TTTT_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 68044; <https://opendata.cern.ch/record/68045>)
- **Proposed σ_eff = 0.008091 pb** = 0.008091

  - generator σ (portal), NLO: **0.008091** — portal API <https://opendata.cern.ch/api/records/68044> metadata.cross_section.total_value

- **Order:** NLO.
- **Portal (generator) values:** total_value = 8.091e-03 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.814e-01 (<https://opendata.cern.ch/api/records/68044>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** MiniAOD record 68044, total_value = 8.091e-03.
- **Convention:** Rule 'no NNLO → generator NLO' applied, BUT published higher-accuracy values exist and are much larger: decision for Matan.
- **Alternatives considered:** NLO QCD+EW, arXiv:1711.02116 Table 5: 11.97 fb → +47.9 %; NLO(QCD+EW)+NLL′, arXiv:2212.03259 Table I: 14.65 fb → +81.1 %

## 28. 68185 TTZToLL_M-1to10 — tier 4

- **What it is:** tt̄ + lepton pair (e, μ, τ) with 1 < m(ℓℓ) < 10 GeV (virtual photon), NLO -- fills the gap below our TTZToLLNuNu_M-10.
- **Dataset:** `/TTZToLL_M-1to10_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 68184; <https://opendata.cern.ch/record/68185>)
- **Proposed σ_eff = 0.0537 pb** = 0.0537

  - generator σ (portal), NLO: **0.0537** — portal API <https://opendata.cern.ch/api/records/68184> metadata.cross_section.total_value

- **Order:** NLO.
- **Portal (generator) values:** total_value = 5.370e-02 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.212e-01 (<https://opendata.cern.ch/api/records/68184>).
- **Proposed / generator:** 1.0000
- **What Matan should open and look for:** MiniAOD record 68184, total_value.
- **Convention:** No NNLO → generator NLO.
- **Alternatives considered:** none with a public source found.

## 29. 37474 GluGluHToWWTo2L2Nu_M-125 — tier 5

- **What it is:** Gluon-fusion Higgs, H → WW → ℓνℓν (ℓ = e, μ, τ).
- **Dataset:** `/GluGluHToWWTo2L2Nu_M-125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 37473; <https://opendata.cern.ch/record/37474>)
- **Proposed σ_eff = 1.11145 pb** = 48.58 × 0.2137 × 0.10706

  - σ(ggF), N3LO QCD + NLO EW: **48.58** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)
  - BR(W → ℓν)² = 0.3272²: **0.10706** — https://pdglive.lbl.gov/Particle.action?node=S043 — W DECAY MODES: e+ nu, mu+ nu, tau+ nu, hadrons

- **Order:** N3LO QCD + NLO EW.
- **Portal (generator) values:** total_value = 2.147e+01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 3.452e-05 (<https://opendata.cern.ch/api/records/37473>).
- **Proposed / generator:** 0.0518
- **What Matan should open and look for:** YR4 13 TeV ggF table, 125.00 → 4.858E+01; BR page 'Higgs → 2 gauge bosons', 125.00, WW = 2.137E-01.
- **Convention:** YR4 × YR4 BR × PDG W BRs (settled).
- **Alternatives considered:** none with a public source found.
- **Note:** Pythia: '25:onIfMatch = 24 -24', '24:onIfMatch = 11 12 / 13 14 / 15 16'.

## 30. 68601 VBFHToWWTo2L2Nu_M125 — tier 5

- **What it is:** Vector-boson-fusion Higgs, H → WW → ℓνℓν (ℓ = e, μ, τ).
- **Dataset:** `/VBFHToWWTo2L2Nu_M125_TuneCP5_13TeV_powheg2_JHUGenV714_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 68600; <https://opendata.cern.ch/record/68601>)
- **Proposed σ_eff = 0.0865272 pb** = 3.782 × 0.2137 × 0.10706

  - σ(VBF), approx. NNLO QCD + NLO EW: **3.782** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)
  - BR(W → ℓν)²: **0.10706** — https://pdglive.lbl.gov/Particle.action?node=S043 — W DECAY MODES: e+ nu, mu+ nu, tau+ nu, hadrons

- **Order:** approx. NNLO QCD + NLO EW.
- **Portal (generator) values:** total_value = 3.892e+00 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 6.562e-04 (<https://opendata.cern.ch/api/records/68600>).
- **Proposed / generator:** 0.0222
- **What Matan should open and look for:** YR4 VBF table, 125.00 → 3.782E+00; BR WW 2.137E-01.
- **Convention:** YR4 (settled).
- **Alternatives considered:** none with a public source found.
- **Note:** JHUGen card: DecayMode1=10 DecayMode2=10 (W → ℓν, ℓ = e, μ, τ).

## 31. 41877 HWplusJ_HToWW_M-125 — tier 5

- **What it is:** W+H production, W decaying any way, H → WW (any decay).
- **Dataset:** `/HWplusJ_HToWW_M-125_TuneCP5_13TeV-powheg-jhugen727-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 41876; <https://opendata.cern.ch/record/41877>)
- **Proposed σ_eff = 0.179508 pb** = 0.84 × 0.2137

  - σ(W+H), NNLO QCD + NLO EW: **0.84** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** NNLO QCD + NLO EW.
- **Portal (generator) values:** total_value = 8.720e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.785e-02 (<https://opendata.cern.ch/api/records/41876>).
- **Proposed / generator:** 0.2059
- **What Matan should open and look for:** YR4 WH table, 125.00, column 'W+H (pb)' = 8.400E-01; BR WW.
- **Convention:** YR4 (settled).
- **Alternatives considered:** none with a public source found.
- **Note:** Cards: vdecaymode 10 (W inclusive), JHUGen DecayMode 11/11 (W → anything).

## 32. 41873 HWminusJ_HToWW_M-125 — tier 5

- **What it is:** W−H production, W decaying any way, H → WW (any decay).
- **Dataset:** `/HWminusJ_HToWW_M-125_TuneCP5_13TeV-powheg-jhugen727-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 41872; <https://opendata.cern.ch/record/41873>)
- **Proposed σ_eff = 0.113859 pb** = 0.5328 × 0.2137

  - σ(W−H), NNLO QCD + NLO EW: **0.5328** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** NNLO QCD + NLO EW.
- **Portal (generator) values:** total_value = 5.445e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.625e-02 (<https://opendata.cern.ch/api/records/41872>).
- **Proposed / generator:** 0.2091
- **What Matan should open and look for:** YR4 WH table, 125.00, column 'W−H (pb)' = 5.328E-01; BR WW.
- **Convention:** YR4 (settled).
- **Alternatives considered:** none with a public source found.
- **Note:** Cards: vdecaymode 10 (W inclusive), JHUGen DecayMode 11/11 (W → anything).

## 33. 41914 HZJ_HToWW_M-125 (ext1) — tier 5

- **What it is:** qq̄ → ZH, Z decaying any way, H → WW (any decay).
- **Dataset:** `/HZJ_HToWW_M-125_TuneCP5_13TeV-powheg-jhugen727-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 41912; <https://opendata.cern.ch/record/41914>)
- **Proposed σ_eff = 0.162668 pb** = 0.7612 × 0.2137

  - σ(ZH, all but gg → ZH): **0.7612** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** NNLO QCD + NLO EW.
- **Portal (generator) values:** total_value = 9.595e-01 pb, filter eff. = 1.000e+00, matching eff. = None, negative-weight fraction = 2.965e-02 (<https://opendata.cern.ch/api/records/41912>).
- **Proposed / generator:** 0.1695
- **What Matan should open and look for:** YR4 ZH process table: 'qq/qg→ZH, gg→HZ+qqbar (all but gg→ZH)' = 0.7612.
- **Convention:** YR4 'all but gg→ZH' value, the page's own recommendation for an NLO qq̄ → ZH sample.
- **Alternatives considered:** total pp → ZH 0.8839 instead (would double-count gg → ZH) → +16.1 %
- **Note:** Portal shows no matching efficiency for this record (None).

## 34. 40095 GluGluZH_HToWW_ZTo2L_M-125 (ext1) — tier 5

- **What it is:** gg → ZH, Z → ℓℓ (e, μ, τ), H → WW (any decay).
- **Dataset:** `/GluGluZH_HToWW_ZTo2L_M-125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17_ext1-v1/NANOAODSIM` (MiniAOD parent 40093; <https://opendata.cern.ch/record/40095>)
- **Proposed σ_eff = 0.00264806 pb** = 0.1227 × 0.2137 × 0.10099

  - σ(gg → ZH), NLO+NLL: **0.1227** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → WW): **0.2137** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)
  - BR(Z → ℓℓ) = 0.033632 + 0.033662 + 0.033696: **0.10099** — https://pdglive.lbl.gov/Particle.action?node=S044 — Z DECAY MODES: Gamma1 e+e-, Gamma2 mu+mu-, Gamma3 tau+tau-, Gamma7 invisible, Gamma8 hadrons

- **Order:** NLO+NLL QCD.
- **Portal (generator) values:** total_value = 6.185e-03 pb, filter eff. = 1.000e+00, matching eff. = None, negative-weight fraction = 0.000e+00 (<https://opendata.cern.ch/api/records/40093>).
- **Proposed / generator:** 0.4281
- **What Matan should open and look for:** YR4 ZH process table: 'gg→ZH' = 0.1227. pdglive S044: Γ1, Γ2, Γ3.
- **Convention:** YR4 gg → ZH; Z branching ratios from PDG individually measured values (by analogy with the W convention -- NOT settled, see Decisions).
- **Alternatives considered:** none with a public source found.
- **Note:** POWHEG card: vdecaymode 11 ('inclusive leptons'); Pythia '25:onIfMatch = 24 -24'.

## 35. 37446 GluGluHToTauTau_M125 — tier 5

- **What it is:** gluon-fusion Higgs, H → ττ.
- **Dataset:** `/GluGluHToTauTau_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 37445; <https://opendata.cern.ch/record/37446>)
- **Proposed σ_eff = 3.04694 pb** = 48.58 × 0.06272

  - σ(production), YR4: **48.58** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → ττ): **0.06272** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** YR4 order of the production mode.
- **Portal (generator) values:** total_value = 2.146e+01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 5.185e-03 (<https://opendata.cern.ch/api/records/37445>).
- **Proposed / generator:** 0.1420
- **What Matan should open and look for:** YR4 ggF table 4.858E+01; BR page 'Higgs → 2 fermions', 125.00, ττ = 6.272E-02.
- **Convention:** YR4 (settled).
- **Alternatives considered:** none with a public source found.
- **Note:** Pythia: '25:onIfMatch = 15 -15'.

## 36. 68591 VBFHToTauTau_M125 — tier 5

- **What it is:** VBF Higgs, H → ττ.
- **Dataset:** `/VBFHToTauTau_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 68590; <https://opendata.cern.ch/record/68591>)
- **Proposed σ_eff = 0.237207 pb** = 3.782 × 0.06272

  - σ(production), YR4: **3.782** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → ττ): **0.06272** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** YR4 order of the production mode.
- **Portal (generator) values:** total_value = 3.861e+00 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 6.407e-04 (<https://opendata.cern.ch/api/records/68590>).
- **Proposed / generator:** 0.0614
- **What Matan should open and look for:** YR4 VBF table 3.782E+00; BR page 'Higgs → 2 fermions', 125.00, ττ = 6.272E-02.
- **Convention:** YR4 (settled).
- **Alternatives considered:** none with a public source found.
- **Note:** Pythia: '25:onIfMatch = 15 -15'.

## 37. 71297 WplusHToTauTau_M125 — tier 5

- **What it is:** W+H (W any decay) Higgs, H → ττ.
- **Dataset:** `/WplusHToTauTau_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 71296; <https://opendata.cern.ch/record/71297>)
- **Proposed σ_eff = 0.0526848 pb** = 0.84 × 0.06272

  - σ(production), YR4: **0.84** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → ττ): **0.06272** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** YR4 order of the production mode.
- **Portal (generator) values:** total_value = 8.670e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.792e-02 (<https://opendata.cern.ch/api/records/71296>).
- **Proposed / generator:** 0.0608
- **What Matan should open and look for:** YR4 WH table, W+H 8.400E-01; BR page 'Higgs → 2 fermions', 125.00, ττ = 6.272E-02.
- **Convention:** YR4 (settled).
- **Alternatives considered:** none with a public source found.
- **Note:** Pythia: '25:onIfMatch = 15 -15'.

## 38. 70453 WminusHToTauTau_M125 — tier 5

- **What it is:** W−H (W any decay) Higgs, H → ττ.
- **Dataset:** `/WminusHToTauTau_M125_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 70452; <https://opendata.cern.ch/record/70453>)
- **Proposed σ_eff = 0.0334172 pb** = 0.5328 × 0.06272

  - σ(production), YR4: **0.5328** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → ττ): **0.06272** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** YR4 order of the production mode.
- **Portal (generator) values:** total_value = 5.412e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.648e-02 (<https://opendata.cern.ch/api/records/70452>).
- **Proposed / generator:** 0.0617
- **What Matan should open and look for:** YR4 WH table, W−H 5.328E-01; BR page 'Higgs → 2 fermions', 125.00, ττ = 6.272E-02.
- **Convention:** YR4 (settled).
- **Alternatives considered:** none with a public source found.
- **Note:** Pythia: '25:onIfMatch = 15 -15'.

## 39. 74684 ZHToTauTau_M125 — tier 5

- **What it is:** qq̄ → ZH (Z any decay) Higgs, H → ττ.
- **Dataset:** `/ZHToTauTau_M125_CP5_13TeV-powheg-pythia8_ext1/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 74683; <https://opendata.cern.ch/record/74684>)
- **Proposed σ_eff = 0.0477425 pb** = 0.7612 × 0.06272

  - σ(production), YR4: **0.7612** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → ττ): **0.06272** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** YR4 order of the production mode.
- **Portal (generator) values:** total_value = 7.891e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.902e-02 (<https://opendata.cern.ch/api/records/74683>).
- **Proposed / generator:** 0.0605
- **What Matan should open and look for:** YR4 ZH process table, all but gg→ZH 0.7612; BR page 'Higgs → 2 fermions', 125.00, ττ = 6.272E-02.
- **Convention:** YR4 (settled).
- **Alternatives considered:** none with a public source found.
- **Note:** Pythia: '25:onIfMatch = 15 -15'.

## 40. 37616 GluGluHToZZTo2L2Nu_M125 — tier 5

- **What it is:** Gluon-fusion Higgs, H → ZZ → ℓℓνν with ℓ = e or μ only (no τ).
- **Dataset:** `/GluGluHToZZTo2L2Nu_M125_TuneCP5_13TeV_powheg2_JHUGenV735_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` (MiniAOD parent 37615; <https://opendata.cern.ch/record/37616>)
- **Proposed σ_eff = 0.0342475 pb** = 48.58 × 0.02619 × 0.0269176

  - σ(production), YR4: **48.58** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → ZZ): **0.02619** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)
  - 2 × BR(Z → ee + μμ) × BR(Z → νν) = 2 × 0.067294 × 0.20000: **0.0269176** — https://pdglive.lbl.gov/Particle.action?node=S044 — Z DECAY MODES: Gamma1 e+e-, Gamma2 mu+mu-, Gamma3 tau+tau-, Gamma7 invisible, Gamma8 hadrons

- **Order:** YR4 order of the production mode.
- **Portal (generator) values:** total_value = 2.887e+01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 4.919e-03 (<https://opendata.cern.ch/api/records/37615>).
- **Proposed / generator:** 0.0012
- **What Matan should open and look for:** YR4 tables; BR ZZ 2.619E-02. JHUGen card DecayMode1=3 (Z → νν), DecayMode2=0 (Z → ee, μμ; no τ).
- **Convention:** YR4 × PDG Z BRs (Z convention not settled, see Decisions).
- **Alternatives considered:** YR4 4-fermion column 'H → l+ l- νl νl, l = e or μ' 1.055E-02 instead (WRONG here: it also contains H → WW → ℓνℓν) → +1396.5 %

## 41. 68741 VBF_HToZZTo2L2Nu_M125 — tier 5

- **What it is:** VBF Higgs, H → ZZ → ℓℓνν with ℓ = e or μ only (no τ).
- **Dataset:** `/VBF_HToZZTo2L2Nu_M125_TuneCP5_13TeV_powheg2_JHUGenV735_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v3/NANOAODSIM` (MiniAOD parent 68740; <https://opendata.cern.ch/record/68741>)
- **Proposed σ_eff = 0.0026662 pb** = 3.782 × 0.02619 × 0.0269176

  - σ(production), YR4: **3.782** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → ZZ): **0.02619** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)
  - 2 × BR(Z → ee + μμ) × BR(Z → νν) = 2 × 0.067294 × 0.20000: **0.0269176** — https://pdglive.lbl.gov/Particle.action?node=S044 — Z DECAY MODES: Gamma1 e+e-, Gamma2 mu+mu-, Gamma3 tau+tau-, Gamma7 invisible, Gamma8 hadrons

- **Order:** YR4 order of the production mode.
- **Portal (generator) values:** total_value = 3.935e+00 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 7.240e-04 (<https://opendata.cern.ch/api/records/68740>).
- **Proposed / generator:** 0.0007
- **What Matan should open and look for:** YR4 tables; BR ZZ 2.619E-02. JHUGen card DecayMode1=3 (Z → νν), DecayMode2=0 (Z → ee, μμ; no τ).
- **Convention:** YR4 × PDG Z BRs (Z convention not settled, see Decisions).
- **Alternatives considered:** YR4 4-fermion column 'H → l+ l- νl νl, l = e or μ' 1.055E-02 instead (WRONG here: it also contains H → WW → ℓνℓν) → +1396.5 %

## 42. 71227 WplusH_HToZZTo4L_M125 — tier 5

- **What it is:** W+H production (W any decay), H → ZZ → 4ℓ (ℓ = e, μ, τ).
- **Dataset:** `/WplusH_HToZZTo4L_M125_TuneCP5_13TeV_powheg2-minlo-HWJ_JHUGenV7011_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 71226; <https://opendata.cern.ch/record/71227>)
- **Proposed σ_eff = 0.00023058 pb** = 0.84 × 0.0002745

  - σ(W+H): **0.84** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → ZZ → 4ℓ, ℓ = e, μ, τ): **0.0002745** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** NNLO QCD + NLO EW.
- **Portal (generator) values:** total_value = 8.648e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.778e-02 (<https://opendata.cern.ch/api/records/71226>).
- **Proposed / generator:** 0.0003
- **What Matan should open and look for:** YR4 WH table; BR page 'Higgs → 4 fermions', H → llll (l = e,μ,τ) = 2.745E-04. JHUGen card DecayMode 8/8.
- **Convention:** Same BR as our ggH/VBF → 4ℓ (2.745e-4).
- **Alternatives considered:** none with a public source found.

## 43. 70383 WminusH_HToZZTo4L_M125 — tier 5

- **What it is:** W−H production (W any decay), H → ZZ → 4ℓ (ℓ = e, μ, τ).
- **Dataset:** `/WminusH_HToZZTo4L_M125_TuneCP5_13TeV_powheg2-minlo-HWJ_JHUGenV7011_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` (MiniAOD parent 70382; <https://opendata.cern.ch/record/70383>)
- **Proposed σ_eff = 0.000146254 pb** = 0.5328 × 0.0002745

  - σ(W−H): **0.5328** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV — rows mH = 125.00: ggF N3LO table; VBF table; WH table (W+H, W−H columns); ZH process table at 125.0 ('all but gg→ZH', 'gg→ZH'); ttH table
  - BR(H → ZZ → 4ℓ, ℓ = e, μ, τ): **0.0002745** — https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR — rows MH = 125.00: 'Higgs → 2 fermions' (bb, ττ), 'Higgs → 2 gauge bosons' (WW, ZZ), 'Higgs → 4 fermions' (H → llll, l = e,μ,τ)

- **Order:** NNLO QCD + NLO EW.
- **Portal (generator) values:** total_value = 5.409e-01 pb, filter eff. = 1.000e+00, matching eff. = 1.0, negative-weight fraction = 2.544e-02 (<https://opendata.cern.ch/api/records/70382>).
- **Proposed / generator:** 0.0003
- **What Matan should open and look for:** YR4 WH table; BR page 'Higgs → 4 fermions', H → llll (l = e,μ,τ) = 2.745E-04. JHUGen card DecayMode 8/8.
- **Convention:** Same BR as our ggH/VBF → 4ℓ (2.745e-4).
- **Alternatives considered:** none with a public source found.

## Not verified / not proposed

- ZZTo2L2Nu 75567: excluded on 15 Oct (unresolved 42 % mismatch between its portal value and expectations); history re-stated in PLAN.md, not resolved here.
- tHq 65649, tHW 65721: not proposed. Their portal values (0.7449 and 0.1466 pb) are about 10× the YR4 SM values (7.425E-02 and 1.517E-02 pb, read on the YR4 page) -- consistent with generation at a non-SM coupling point plus reweighting weights (name 'ctcvcp'); UNVERIFIED, would need per-event reweighting the pipeline does not do.
- ZH → ZZ (74314, 74300, 74384, 74440): not proposed. Their portal records show 'matching efficiency' 0.2-0.9 on POWHEG samples, which looks like a lepton-filter efficiency in the wrong field; UNVERIFIED.
- Optional samples (PLAN.md): no proposal yet.
- QCD multijet and photon samples: out of scope (no cross-section research).
