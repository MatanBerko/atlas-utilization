# MANIFEST — where every value in the delivery READMEs comes from

All paths are at commit **`75b399e2dfdacc50affd4e2c78bc865b12f000cc`** (the code pin of the full
run of 25 Oct 2026; branch `run/cms-fullrun-20261025`). Every line number was read with
`git grep -n` / `git show` at that commit on 26 Oct 2026. Values that are not computed by the code
are marked as such.

## Data selection (per-file driver, data and MC alike)

| value | where |
|---|---|
| Muon pT > 25 GeV | `studies/m0m1j0_cms/selection.py:56` `MUON_PT_MIN_GEV = 25.0` |
| Muon \|eta\| < 2.4 | `studies/m0m1j0_cms/selection.py:57` `MUON_ETA_MAX = 2.4` |
| Muon isolation pfRelIso04_all < 0.15 | `studies/m0m1j0_cms/selection.py:58` `MUON_ISO_MAX = 0.15` |
| Muon ID = CMS Loose (`Muon_looseId`) | `studies/m0m1j0_cms/selection.py:61` `MUON_ID_BRANCH = "Muon_looseId"` (24 Oct 2026, Maryna) |
| Electron pT > 25 GeV | `studies/m0m1j0_cms/selection.py:63` |
| Electron \|eta\| < 2.5 | `studies/m0m1j0_cms/selection.py:64` |
| Electron cut-based ID ≥ 2 (Loose; Fall17 V2 scale 0 fail, 1 veto, 2 loose, 3 medium, 4 tight) | `studies/m0m1j0_cms/selection.py:67` `ELECTRON_CUTBASED_MIN = 2`; scale = the file's own branch title (`evidence/branch_titles.json`) |
| Jets pT > 30 GeV, \|eta\| < 2.5 | `studies/m0m1j0_cms/selection.py:69-70` |
| Jet tight ID (`Jet_jetId & 2`) | `studies/m0m1j0_cms/selection.py:214` |
| Jet–lepton cleaning ΔR < 0.4 | `studies/m0m1j0_cms/selection.py:71` `JET_LEPTON_CLEAN_DR = 0.4` |
| b-tag DeepJet `Jet_btagDeepFlavB` > 0.2489 (UL2016 postVFP medium) | `studies/m0m1j0_cms/selection.py:77` `BTAG_DEEPFLAVB_MEDIUM_WP = 0.2489` |
| e–μ overlap removal: electrons within ΔR < 0.12 of a selected muon removed | `studies/cms_datasets/cluster/run_dataset_on_file.py:489` `EMU_OVERLAP_DR_MAX = 0.12`; function at `:831` |
| Golden JSON | `studies/cms_datasets/cluster/run_dataset_on_file.py:192-193` → `data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt`; applied at `:2267` (data only) |

## Datasets, triggers, matching, thresholds, de-duplication

| value | where |
|---|---|
| Records: DoubleMuon 30522 (G) / 30555 (H), 57 files; DoubleEG 30521 / 30554, 133; MuonEG 30528 / 30561, 48; SingleMuon 30530 / 30563, 152; SingleElectron 30529 / 30562, 151 | `studies/cms_datasets/cluster/datasets_records.py:30-40` |
| DoubleMuon triggers `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ`, `HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ` | `datasets_records.py:31` |
| DoubleEG trigger `HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ` | `datasets_records.py:33` |
| MuonEG triggers `HLT_Mu23_TrkIsoVVL_Ele12_…_DZ`, `HLT_Mu8_TrkIsoVVL_Ele23_…_DZ` | `datasets_records.py:35-36` |
| SingleMuon triggers `HLT_IsoMu24`, `HLT_IsoTkMu24` (matching uses `HLT_IsoMu24`) | `datasets_records.py:38`; `run_dataset_on_file.py:242` |
| SingleElectron trigger `HLT_Ele27_WPTight_Gsf` | `datasets_records.py:40` |
| Trigger-object matching ΔR < 0.1 | `run_dataset_on_file.py:247` `MATCH_DR_MAX = 0.1` |
| DoubleMuon: ≥ 2 matched muons, leading > 17 GeV | `run_dataset_on_file.py:248-249` |
| SingleMuon: ≥ 1 matched muon, pT > 24 GeV | `run_dataset_on_file.py:250-251` |
| DoubleEG: 2 matched electrons, online leading leg ≥ 23 GeV, **both electrons offline > 30 GeV** (mode "both") | `run_dataset_on_file.py:400-402, 416` |
| MuonEG: ≥ 1 selected muon; electron leg 12 / 23 GeV by path | `run_dataset_on_file.py:423-427` |
| SingleElectron: online ≥ 27 GeV, **offline > 32 GeV** | `run_dataset_on_file.py:460-461`; acceptance at `:1313` |
| De-duplication priority DoubleMuon > SingleMuon > DoubleEG > MuonEG > SingleElectron | `run_dataset_on_file.py:272` (`DELIVERY_VETO_ORDER_4`) and `:444` (`DELIVERY_VETO_ORDER_5` = + SingleElectron) |
| Pooling: DoubleMuon inclusive, the others exclusive | data build summary `pooling` (`evidence/final_data/build_summary_rare4_four_dataset.json`) |

## Build (post-processing)

| value | where |
|---|---|
| #40 multiplicity rule: `limit_particles_in_fs(label, 4)` (upstream 5fbf1ef), default of both builders | `studies/cms_datasets/common/multiplicity.py:56` `THRESHOLD = 4`, `:58` `DEFAULT_RULE = "upstream40"`, `:95-96`; builders import it at `build_four_dataset_delivery.py:141`, `build_mc_delivery.py:109` |
| ≥ 100 events per final state (once, on all shards combined) | `studies/cms_coverage/cluster/merge_and_count.py:73` `PRIMARY_MIN_EVENTS_PER_FS = 100` |
| Z-peak cut: same-flavour dilepton masses < 110 GeV removed | `merge_and_count.py:71` `Z_PEAK_CUTOFF = 110.0` |
| Max mass 10,000 GeV | `merge_and_count.py:72` |
| 10 GeV bins, 0–10,000 GeV | `merge_and_count.py:60` `BIN_WIDTH_GEV = 10.0`; asserted at `build_four_dataset_delivery.py:360` |
| Peak removal (rightmost highest peak) and outlier split at the first empty bin | upstream `services/pipelines/post_processing_pipeline.py:370` `_find_rightmost_highest_peak`, `:434` `_split_by_first_empty_bin`; data via `merge_and_count.py:215-221`; MC via `build_mc_delivery.py:97` |
| MC peak options: `--peak-on weighted`, `--peak-scope combined`, `--min-events-basis raw` (defaults) | `build_mc_delivery.py:1032, 1037, 1045` |

## MC normalisation

| value | where |
|---|---|
| Event weight = genWeight × L1PreFiringWeight_Nom × σ_eff[pb] × 1000 × L[fb⁻¹] / Σw (k = ε = 1, already in σ_eff) | `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py:21-25`; normalisation at `:366` |
| Σw = sum over the surviving files; per-file check \|Σ genWeight − Runs.genEventSumw\| / Runs.genEventSumw ≤ 1e-6, failing files excluded | `build_mc_delivery.py:14-17, 253-292` |
| L = 16.393 fb⁻¹ | `build_mc_delivery.py:149` `TARGET_LUMINOSITY_FB = 16.393`; documented as Run2016G 7.653 + H 8.740 in `studies/cms_mc_weights_v3/DESIGN.md:881`. **Not computed by the data code** (the data histograms are event counts; the number is the documented G+H integrated luminosity of the golden JSON). |
| MC event union = the five delivered acceptances (four data flags OR SingleElectron bit 6) | `build_mc_delivery.py:601-608` (`event_union_mask`) |
| Cross sections σ_eff (pb), per sample | registry `studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json` (decisions in `XSEC_DECISIONS.md`); the values used are echoed per sample in the build report (`evidence/final_mc/build_report_summary.json`, `samples.<record>.cross_section_pb_sigma_eff`) |

Per-sample values from the build report (VERIFIED BY RUNNING, `fullrun_build_report.json`):

| record | sample | σ_eff (pb) | files used | files excluded | histograms |
|---|---|---:|---:|---:|---:|
| 35631 | DYJetsToLL_M-10to50_amcatnloFXFX | 18610.0 | 25 | 0 | 249 |
| 35669 | DYJetsToLL_M-50_amcatnloFXFX | 5765.4 | 41 | 0 | 314 |
| 37728 | GluGluHToZZTo4L_M125 | 0.013335 | 8 | 0 | 318 |
| 64839 | ST_tW_antitop_5f_NoFullyHadronicDecays | 19.56 | 10 | 0 | 316 |
| 64895 | ST_tW_top_5f_NoFullyHadronicDecays | 19.56 | 11 | 0 | 304 |
| 67801 | TTTo2L2Nu | 89.28 | 49 | 0 | 331 |
| 67993 | TTToSemiLeptonic | 367.86 | 138 | 0 | 308 |
| 68073 | TTWJetsToLNu | 0.2151 | 12 | 0 | 331 |
| 68187 | TTZToLLNuNu_M-10 | 0.2439 | 42 | 0 | 331 |
| 68847 | VBF_HToZZTo4L_M125 | 0.0010382 | 24 | 0 | 327 |
| 72676 | WWTo2L2Nu | 12.708 | 7 | 0 | 303 |
| 72752 | WZTo3LNu_amcatnloFXFX | 5.789 | 31 | 0 | 331 |
| 75589 | ZZTo4L | 1.544 | 98 | 1 (file 98: Σw check failed, 3.7 % short; Matan's 17 Oct option A) | 331 |
| — | summed SM | | | | 331 |

## MC samples NOT included (stated in every README)

W+jets, QCD multijet, single top t-channel and s-channel, fully hadronic tt̄, and smaller
processes (e.g. tribosons, other rare processes). Source: the registry holds exactly the 13
records above (`cms_mc_normalisation_v3.json`); the list of what is absent is the analysis
team's description, not a value computed by the code.
