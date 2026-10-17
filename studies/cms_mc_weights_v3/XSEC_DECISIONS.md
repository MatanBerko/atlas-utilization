# CMS MC cross sections: the decisions of 15 Oct 2026

This is the human-readable twin of the registry
`cms_mc_normalisation_v3.json`. Both are generated from the same input,
`sources/v4_decisions_2026-10-15.json`, which holds Matan's reviewed values,
transcribed exactly as he gave them. Nothing here was re-derived or rounded.

**Update 17 Oct 2026.** One value changed, by Matan's decision of 15 Oct:
72752 WZ is now **5.789 pb** = 5.218 × 51.11 / 46.068 (exact k-factor; it was
5.787, which came from the k-factor rounded to 1.109). And the MC builder
now **refuses** any record whose registry entry has `in_full_run = false`
(see open point 4). No other value or record changed.

**Convention (unchanged).** `cross_section_pb` is σ_eff: the production cross
section × branching ratio × any generator-level selection × any k-factor.
That means `k_factor` and `gen_filt_eff` stay pinned to 1.0 in the registry,
and `sum_of_weights` stays null, because it is measured at build time.

**Status of the numbers.**
- The decided values, constructions and citations are Matan's: **UNVERIFIED
  by this task**, which transcribed them and did not re-open the theory pages.
- The "portal generator" column and the matching efficiencies were read live
  from the CERN Open Data API on 15 Oct 2026: **VERIFIED BY RUNNING**
  (`evidence/portal_crosscheck_20261015.json`). All 13 quoted generator values
  match.
- The new/old ratios are arithmetic on the two registries: **VERIFIED BY
  RUNNING** (`evidence/xsec_old_vs_new_20261015.json`).

## All records in the registry

| nano / mini | sample | σ_eff [pb] | construction | order | previous [pb] | new/old | full run | portal generator [pb] / matching eff. |
|---|---|---:|---|---|---:|---:|---|---|
| 67801 / 67800 | TTTo2L2Nu | **89.28** | 833.9 pb x 0.10706, where 0.10706 = (0.1071 + 0.1063 + 0.1138)^2 | NNLO+NNLL | 89.28 | 1.0000 | **yes** | 687.1 / 1.0 |
| 67993 / 67992 | TTToSemiLeptonic | **367.86** | 833.9 pb x 0.44113, where 0.44113 = 2 x 0.3272 x 0.6741 | NNLO+NNLL | 367.86 | 1.0000 | **yes** | 687.1 / 1.0 |
| 35669 / 35668 | DYJetsToLL_M-50_amcatnloFXFX | **5765.4** | 3 x 1921.8 pb | secondary-table | 5765.4 | 1.0000 | **yes** | 6422.0 / 0.4 |
| 35631 / 35630 | DYJetsToLL_M-10to50_amcatnloFXFX | **18610** | table value, 18610.0 pb | secondary-table | — (was excluded) | new | **yes** | 20480.0 / 0.6 |
| 64895 / 64894 | ST_tW_top_5f_NoFullyHadronicDecays | **19.56** | 71.7 pb / 2 x (1 - 0.6741^2) | approx. NNLO | 19.56 | 1.0000 | **yes** | 32.45 / 1.0 |
| 64839 / 64838 | ST_tW_antitop_5f_NoFullyHadronicDecays | **19.56** | 71.7 pb / 2 x (1 - 0.6741^2) (antitop half) | approx. NNLO | 19.56 | 1.0000 | **yes** | 32.51 / 1.0 |
| 72676 / 72675 | WWTo2L2Nu | **12.708** | 118.7 pb x 0.10706 | NNLO | 12.178 | 1.0435 | **yes** | 11.09 / 1.0 |
| 72752 / 72751 | WZTo3LNu_amcatnloFXFX | **5.789** (was 5.787 until 17 Oct) | generator 5.218 pb x (51.11 / 46.068) | NLO generator x NNLO/NLO k-factor | 5.218 | 1.1094 | **yes** | 5.218 / 0.6 |
| 75589 / 75588 | ZZTo4L | **1.544** | generator 1.325 pb x (16.91 / 14.51) | NLO generator x NNLO/NLO k-factor | 1.256 | 1.2293 | **yes** | 1.325 / 1.0 |
| 68187 / 68186 | TTZToLLNuNu_M-10 | **0.2439** | generator value | NLO | 0.2529 | 0.9644 | **yes** | 0.2439 / 1.0 |
| 68073 / 68072 | TTWJetsToLNu | **0.2151** | generator value | NLO | 0.2043 | 1.0529 | **yes** | 0.2151 / 0.6 |
| 37728 / 37727 | GluGluHToZZTo4L_M125 | **0.013335** | 48.58 pb x 2.745e-4 | N3LO QCD + NLO EW | 0.013447 | 0.9917 | **yes** | 28.87 / 1.0 |
| 68847 / 68846 | VBF_HToZZTo4L_M125 | **0.0010382** | 3.782 pb x 2.745e-4 | not stated in the decision list (the earlier v2 table recorded NNLO QCD + NLO EW for this page; UNVERIFIED here, for Matan to confirm) | — (was excluded) | new | **yes** | 3.935 / 1.0 |
| 35671 / 35670 | DYJetsToLL_M-50_madgraphMLM | **5765.4** | unchanged from the previous registry (3 x 1921.8 pb) | secondary-table | 5765.4 | 1.0000 | no — would double-count Drell-Yan with 35669; cross-check only | 5396.0 / 0.4 |
| 42407 / 42406 | LQToBMu_M-400_pair | **2.276** | unchanged from the previous registry | unchanged (previous: NNLOapprox+NNLL stop-pair proxy) | 2.276 | 1.0000 | no — BSM signal, not SM background | None / None |

### Sources and notes, per record

**67801 TTTo2L2Nu** — σ_eff 89.28 pb
- Source: LHC Top WG twiki TtbarNNLO: 13 TeV, mt = 172.5 GeV, NNLO+NNLL. <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/TtbarNNLO>
- Source: PDG W branching ratios: pdglive node S043, individually measured values (e, mu, tau). <https://pdglive.lbl.gov/Particle.action?node=S043>
- Note: Value unchanged; sources re-checked.

**67993 TTToSemiLeptonic** — σ_eff 367.86 pb
- Source: LHC Top WG twiki TtbarNNLO: 13 TeV, mt = 172.5 GeV, NNLO+NNLL. <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/TtbarNNLO>
- Source: PDG W branching ratios: pdglive node S043, individually measured leptonic values; BR(W -> hadrons) = 0.6741. <https://pdglive.lbl.gov/Particle.action?node=S043>
- Note: Value unchanged; sources re-checked.

**35669 DYJetsToLL_M-50_amcatnloFXFX** — σ_eff 5765.4 pb
- Source: RazorAnalyzer public cross-section table (SECONDARY source): line "DYJetsToLL_M-50_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 1921.8*3" under "#13 TeV Spring 15 MC". <https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat>
- Note: Value unchanged. Citation CORRECTED: the old citation arXiv:1712.09814 (an electroweak Z+2-jets paper) is replaced by the RazorAnalyzer table. 2015-era value; a newer CMS-internal 6077.22 pb (not public) is ~5% higher; the generator NLO value is 6422 pb.
- Old citation replaced: arXiv:1712.09814

**35631 DYJetsToLL_M-10to50_amcatnloFXFX** — σ_eff 18610 pb
- Source: RazorAnalyzer public cross-section table (SECONDARY source): line "DYJetsToLL_M-10to50_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 18610.0" under "#13 TeV Spring 15 MC". <https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat>
- Note: NEW in the full run (was excluded). Chosen for consistency with 35669 (same table), so there is no artificial step at m(ll) = 50 GeV.

**64895 ST_tW_top_5f_NoFullyHadronicDecays** — σ_eff 19.56 pb
- Source: LHC Top WG twiki SingleTopRefXsec: tW, 13 TeV, mt = 172.5 GeV, approx. NNLO. <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec>
- Note: Value unchanged. Citation CORRECTED: the old citation arXiv:2208.00924 (a CMS tW measurement) is replaced by the LHC Top WG twiki.
- Old citation replaced: arXiv:2208.00924
- Alternative recorded, not used: aN3LO 79.5 pb, arXiv:2106.12910 Sect. 2 (would give 21.69 pb)

**64839 ST_tW_antitop_5f_NoFullyHadronicDecays** — σ_eff 19.56 pb
- Source: LHC Top WG twiki SingleTopRefXsec: tW, 13 TeV, mt = 172.5 GeV, approx. NNLO. <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec>
- Note: Same as 64895 (antitop half). Value unchanged; old citation arXiv:2208.00924 replaced.
- Old citation replaced: arXiv:2208.00924
- Alternative recorded, not used: aN3LO 79.5 pb, arXiv:2106.12910 Sect. 2 (would give 21.69 pb)

**72676 WWTo2L2Nu** — σ_eff 12.708 pb
- Source: arXiv:1408.5243: Table 1, 13 TeV, NNLO (includes gg -> WW; 4FNS). <https://arxiv.org/abs/1408.5243>
- Note: Previous 12.178 pb came from the RazorAnalyzer table and could not be traced to a theory source; replaced by the NNLO value.

**72752 WZTo3LNu_amcatnloFXFX** — σ_eff 5.789 pb (corrected 17 Oct: exact k-factor 51.11/46.068, was 5.787)
- Source: CERN Open Data record 72751 (generator cross section): metadata.cross_section.total_value. <https://opendata.cern.ch/record/72751>
- Source: arXiv:1604.08576: Table 1, 13 TeV, on-shell NNLO/NLO (k-factor). <https://arxiv.org/abs/1604.08576>
- Note: Approximation: an on-shell k-factor is applied to a sample that also contains gamma*/low-mass pairs.
- Arithmetic note: 5.218 x 51.11 / 46.068 = 5.78909 -> 5.789 pb (exact k-factor). The value 5.787 used until 17 Oct equalled 5.218 x 1.109 (k rounded to 4 significant figures); corrected to the exact formula by Matan's decision of 15 Oct 2026, applied 17 Oct 2026.

**75589 ZZTo4L** — σ_eff 1.544 pb
- Source: CERN Open Data record 75588 (generator cross section): metadata.cross_section.total_value. <https://opendata.cern.ch/record/75588>
- Source: arXiv:1405.2219: Table 1, 13 TeV NNLO/NLO (includes gg -> ZZ) (k-factor). <https://arxiv.org/abs/1405.2219>
- Note: If gg -> ZZ samples are ever added, switch to a qqbar-only k-factor to avoid double counting.

**68187 TTZToLLNuNu_M-10** — σ_eff 0.2439 pb
- Source: CERN Open Data record 68186 (generator cross section): metadata.cross_section.total_value. <https://opendata.cern.ch/record/68186>
- Note: ORDER: NLO (no NNLO exists for ttZ).

**68073 TTWJetsToLNu** — σ_eff 0.2151 pb
- Source: CERN Open Data record 68072 (generator cross section): metadata.cross_section.total_value. <https://opendata.cern.ch/record/68072>
- Note: ORDER: NLO (no NNLO exists for ttW).

**37728 GluGluHToZZTo4L_M125** — σ_eff 0.013335 pb
- Source: LHC Higgs WG twiki CERNYellowReportPageAt13TeV: ggF, mH = 125.00 GeV, N3LO QCD + NLO EW. <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV>
- Source: LHC Higgs WG twiki CERNYellowReportPageBR: H -> ZZ -> 4l, l = e, mu, tau, mH = 125.00 GeV. <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR>
- Note: FIX: the previous 0.013447 used the branching ratio at mH = 125.09 GeV (2.768e-4) while the production cross section is at 125.00 GeV, a mass mix-up. Both are now at 125.00 GeV.

**68847 VBF_HToZZTo4L_M125** — σ_eff 0.0010382 pb
- Source: LHC Higgs WG twiki CERNYellowReportPageAt13TeV: VBF, mH = 125.00 GeV. <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV>
- Source: LHC Higgs WG twiki CERNYellowReportPageBR: H -> ZZ -> 4l, l = e, mu, tau, mH = 125.00 GeV. <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR>
- Note: NEW in the full run (was excluded). Uses the same Higgs WG pages as 37728 (mH = 125.00 GeV).

**35671 DYJetsToLL_M-50_madgraphMLM** — σ_eff 5765.4 pb
- Source: RazorAnalyzer public cross-section table (SECONDARY source): same line as 35669. <https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat>
- Note: NOT in the full run: LO sample that would double-count Drell-Yan with 35669. Kept in the registry as a cross-check only.

**42407 LQToBMu_M-400_pair** — σ_eff 2.276 pb
- Source: previous registry provenance (LHC SUSY WG stop-pair proxy): see provenance block. <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SUSYCrossSections13TeVstopsbottom>
- Note: NOT in the full run: BSM signal, not a Standard Model background. Kept in the registry because existing code and tests use it.

## Not in the registry (still excluded)

| record | why |
|---|---|
| 35633 DYJetsToLL_M-10to50 madgraphMLM (LO) | would double-count Drell-Yan with 35631 (portal 15880 pb, matching eff. 0.8, read live) |
| 38428–38442 (gg→ZZ family) | portal values ~1000× too large; gg→ZZ is already inside the ZZTo4L k-factor |
| 75567 ZZTo2L2Nu | unresolved 42% mismatch |

## Open points for Matan (nothing was changed because of them)

1. **72752 WZ arithmetic — RESOLVED 17 Oct.** 5.218 × 51.11 / 46.068 = 5.7891.
   The earlier 5.787 equalled 5.218 × 1.109 (rounded k-factor). Matan decided
   on 15 Oct to use the exact formula; the registry now holds 5.789 pb.
2. **68847 VBF order label.** The decision list gives no order for this
   record. The earlier v2 table called the same Higgs WG page "NNLO QCD + NLO
   EW". Please confirm that label.
3. **Matching efficiency.** The portal lists a matching efficiency below 1 for
   the FxFx/MLM samples:
   - 0.4 for 35669 and 35671;
   - 0.6 for 35631, 72752 and 68073;
   - 0.8 for the excluded 35633.

   Whether the portal `total_value` already includes it is an open question.
   It only matters for values taken from the portal: 72752 (through its
   generator value) and 68073. Reported only; nothing was decided.
4. **`in_full_run` — RESOLVED 17 Oct.** Until 17 Oct the builder did not read
   the flag. Since 17 Oct (Matan's decision of 15 Oct) `build_mc_delivery.py`
   refuses to build if any input record has `in_full_run = false` in the
   registry (today 35671 and 42407), with an error naming the record and the
   registry's reason. Tested in `tests/test_builder_end_to_end.py`.
