# MANIFEST: sources of every value in the final MC delivery README (14 Nov 2026)

Delivery package (NOT uploaded, NOT sent; README finalised 14 Nov 2026): `CMS_Run2016GH_MC-summedSM-71samples_16p393invfb_build2026-11-14_mc.root`
on the cluster at `/storage/agrp/berkom/atlas-utilization/work/mcexp_20261103/full/deliver_20261109/`. It is a byte copy
(`cp -p`, then `cmp` OK) of `full/build_20261109/fullrun_summedSM_mc.root`.

Code: pin `6de9d3e605900a628bae372bdba4ea3308e9750f`. All file:line references below are at that commit. I printed
each one with `git show 6de9d3e:<file> | sed -n <line>p` on 14 Nov (VERIFIED BY READING).
Registry: `studies/cms_mc_weights_v3/cms_mc_normalisation_v5.json` at 5493d0f. The cluster copy is
`full/registry/cms_mc_normalisation_v5.json`, sha256 `6d193c4489c2144a58d59c1b38fce7c43393e70d5532bd6ad95bf1b40e6f01e0`,
equal to the git blob (VERIFIED BY RUNNING). It was passed explicitly with `--registry` (the builder's default is v3:
`build_mc_delivery.py:1081-1083`).

## How the README was made

`delivery/make_readme.py` reads five inputs:
- `studies/cms_mc_weights_v3/sources/v7_decisions_2026-11-14.json` (Matan's decisions of 14 Nov 2026: binning option C,
  W+jets portal values VERIFIED BY MATAN, 68847 order label, QCD excluded), documentation only;
- `evidence/final_build/start_masses_20261114.json` (output of `delivery/start_masses.py` at 070a569, PBS job 5541770;
  the per-histogram table is `<ROOT file>.start_masses.csv`);
- the registry v5 (sample table, σ_eff, construction, order, source, status);
- `evidence/final_build/checks_final.json` (output of `post/checks_final.py` at d7fc115, run in PBS job 5537708);
- `evidence/final_build/build_report_summary.json` (extracted from `full/build_20261109/fullrun_build_report.json`).

## Build metadata (fullrun_build_report.json; VERIFIED BY RUNNING)

| value | report key |
|---|---|
| code commit 6de9d3e605900a628bae372bdba4ea3308e9750f | `git_commit` |
| registry = full/registry/cms_mc_normalisation_v5.json | `registry` |
| extra runs dir = fullrun_20261025/mc/runs (the 13 reused samples) | `extra_runs_dirs` |
| 71 samples = exactly the v5 `full_run_records` = the records with `in_full_run: true` (none missing, none extra) | `samples` vs registry |
| peak_on weighted, peak_scope combined, min_events_basis raw, output both, min 100, rule upstream40 | `options` |
| L 16.393, Z cut 110, max 10,000, 10 GeV, 1000 bins, tolerance 1e-6 | `constants` |
| capped signatures 0; 1 file excluded (75589, the expected Σw failure 75589:98 of 25 Oct) | `samples[*]` |

## README value → source

| README value | source (pin 6de9d3e unless stated) |
|---|---|
| muon pT > 25, abs(eta) < 2.4, iso < 0.15, Loose ID | `studies/m0m1j0_cms/selection.py:56,57,58,61` |
| electron pT > 25, abs(eta) < 2.5, cut-based >= 2 | `selection.py:63,64,67` |
| jet pT > 30, abs(eta) < 2.5, dR 0.4 cleaning, tight jet ID | `selection.py:69,70,71,214` |
| b-tag DeepJet 0.2489 | `selection.py:77` |
| e-μ overlap dR < 0.12 | `studies/cms_datasets/cluster/run_dataset_on_file.py:489,833` |
| trigger-object match dR < 0.1 | `run_dataset_on_file.py:247` |
| DoubleMuon paths; >= 2 matched, leading > 17 | `studies/cms_datasets/cluster/datasets_records.py:31`; `run_dataset_on_file.py:248-249` |
| SingleMuon: HLT_IsoMu24 only in matched mode; > 24 | `run_dataset_on_file.py:242,250-251` (generic list `datasets_records.py:38`) |
| DoubleEG path; 2 matched; both > 30 offline | `datasets_records.py:33`; `run_dataset_on_file.py:400-402,416` |
| MuonEG paths; electron leg 12 / 23 | `datasets_records.py:35-36`; `run_dataset_on_file.py:423-426` |
| SingleElectron Ele27; online >= 27, offline > 32 | `datasets_records.py:40`; `run_dataset_on_file.py:323,460-461,1315` |
| data priority DoubleMuon > SingleMuon > DoubleEG > MuonEG > SingleElectron | `run_dataset_on_file.py:272,444` |
| MC trigger-any over all paths, store if any acceptance | `run_dataset_on_file.py:2179,2273` |
| MC event union of the 5 acceptances | `run_dataset_on_file.py:382`; `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py:601-607` |
| stored MC weights genWeight, L1PreFiringWeight_Nom | `run_dataset_on_file.py:352-353,389-390,1441`; `build_mc_delivery.py:409-419` |
| 500,000 entries per signature cap (D8) | `run_dataset_on_file.py:508` |
| weight formula genW × L1PF × σ_eff × 1000 × L / Σw | `build_mc_delivery.py:21-25,365` |
| L = 16.393 fb⁻¹ | `build_mc_delivery.py:149` |
| Σw per-file tolerance 1e-6 | `build_mc_delivery.py:151,252` |
| shard read (rare4 = delivered Version B) | `build_mc_delivery.py:155` |
| multiplicity rule upstream #40, threshold 4 | `studies/cms_datasets/common/multiplicity.py:56,58` |
| 10 GeV bins | `studies/cms_coverage/cluster/merge_and_count.py:60` |
| Z-peak cut 110 GeV, max mass 10,000 GeV, >= 100 events | `merge_and_count.py:71,72,73` |
| peak removal on the weighted combined distribution | `build_mc_delivery.py:1044,1049,1057` |
| rightmost highest peak; split at first empty bin (upstream) | `services/pipelines/post_processing_pipeline.py:370,434` |
| --keep-scratch, --registry, --extra-runs-dir | `build_mc_delivery.py:1076,1081,1084` |
| per-sample σ_eff, construction, order, source, estimate flag | registry v5 `records[<id>]` (`cross_section_pb`, `decision_2026_11_07` / `decision_2026_11_03` / `decision_2026_10_15`, `estimate`) |
| 40062 ESTIMATE 6.22392e-05 pb | registry v5 `records["40062"]` (`estimate: true`) |
| E1 (CMS ÷ ATLAS 0.92–1.24 by process), E2 | registry v5 `decisions`; `HANDOFF.md:254-255` (A2 section, E1) |
| E3 (ttZ k = 1) | `studies/cms_mc_weights_v3/sources/v6_decisions_2026-11-07.json`; `HANDOFF.md` "D15 (7 Nov)" |
| QCD excluded (Matan, 14 Nov 2026) | `HANDOFF.md` "Final MC build (14 Nov 2026)"; probe: `studies/mc_expansion_20261103/QCD_PROBE.md` |
| 69717: 30 of 117 files; 72761: 6 of 9 files; 69717 MC luminosity ≈ 0.08 × data (ESTIMATE) | `HANDOFF.md:94,107,258,297`; `evidence/file_index_coverage.json` |
| D3 counts, 69717 share of the summed yield, per-sample table, names/edges, data/MC | `evidence/final_build/checks_final.json` (`post/checks_final.py` at d7fc115) |
| R1–R7 all pass (67801, 69715, 67841, 64759) | cluster `full/evidence/rule_check_mc_<rid>_20261109.json` (`all_rules_pass: true`) |

## Start masses section (README "COMPARING THESE MC HISTOGRAMS WITH THE CMS DATA HISTOGRAMS")

| README value | source |
|---|---|
| peak = the rightmost highest 10 GeV bin; masses below its low edge removed | pin 6de9d3e `services/pipelines/post_processing_pipeline.py:370-394` (`_find_rightmost_highest_peak`), grid `:359-367` |
| tail split at the first empty bin above the peak | pin `post_processing_pipeline.py:397-431` (`_main_array_mask`), `:434-438` (`_split_by_first_empty_bin`) |
| data cut found from the data alone | pin `studies/cms_coverage/cluster/merge_and_count.py:220-225` (data via `build_four_dataset_delivery.py`, 25 Oct MANIFEST row "Peak removal") |
| MC cut found from the weighted sum of all samples | pin `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py:456-462` (`find_peak_mass`), `:505-534` (`combined_cuts`), options `:1044,1049`; build report `options` (weighted, combined) |
| ATLAS pipeline also cuts data and MC separately | upstream/master 0f4c614 (VERIFIED BY READING, 14 Nov 2026): separate runs `submit_data.sh:32` (`RUN_DIR=..._data_...`) and `submit_mc.sh:32` (`..._mc_...`); post-processing reads only its run's `im_arrays/` (`utils/paths.py:89-92`); the peak is found per FS_IM key on the arrays of that input dir (`services/pipelines/post_processing_pipeline.py:209,268-270`); no step re-aligns data and MC start masses (`git grep` for align/start mass: none). Since 0f4c614 (14 Nov) the ATLAS data post-processing even runs per batch (`post_processing_pipeline.py:177-179`, `submit_data.sh:79`) |
| same axis 0-10,000 GeV, 10 GeV, 313 shared names equal | `start_masses.py` asserts equal edges for every shared histogram; `checks_final.json` `names_binning.edges.n_axis_equal` = 313 |
| 165 of 313 differ; shift distribution; 109 by one bin; 111 MC later | `evidence/final_build/start_masses_20261114.json` (`n_first_filled_same` 148, `shift_mc_minus_data_gev`) |
| cropped data axis = the data's first..last filled bin (all 313) | `checks_final.json` `names_binning.edges.per_histogram` (`cropped_data_lo_gev` = `data_first_gev`, `cropped_data_hi_gev` = `data_last_gev`) |
| mu + 1 jet example: 70 / 90 GeV, 1.60 own range, 1.19 from the common start | `start_masses_20261114.json` `examples` |
| 18 MC-only names | `start_masses_20261114.json` `mc_only` |
| single lepton + jets data/MC 1.1-1.9 | `checks_final.json` `data_mc_categories` (e/mu + 1-3 jets, own and common range) |
| W+jets portal values VERIFIED BY MATAN on the live portal (14 Nov 2026) | `v7_decisions_2026-11-14.json` `wjets_portal_values` |
| 68847 order "NNLO QCD + NLO EW (LHC Higgs WG YR4, mH = 125.00 GeV)" | `v7_decisions_2026-11-14.json` `68847` (value unchanged; registry v5 untouched) |
| binning decided: option C | `v7_decisions_2026-11-14.json` `binning` |

## Per-sample files (README "PER-SAMPLE FILES"; added 15 Nov 2026)

| README value | source |
|---|---|
| 71 per-sample files = byte copies of `full/build_20261109/fullrun_record<r>_mc.root` | PBS job 5541835 (`full/build_jobs/pbs_persample_20261114.sh`): `cp -p` then `cmp` for each file, `set -e` (VERIFIED BY RUNNING); names from `full/build_jobs/per_sample_names_20261114.txt` (registry `physics_short`, as the 25 Oct names) |
| per-sample files add up to the summed file; largest relative difference 4.8e-16 (contents), 5.8e-16 (Sumw2); 19,587 histograms in all; no name missing either way | `evidence/final_build/per_sample_sumcheck_20261114.json` (`delivery/per_sample_sumcheck.py` at bac88d7, same job) |
| each per-sample histogram cut at the SAME peak and split masses as the summed histogram (found once on the weighted sum of all samples) | pin 6de9d3e `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py:36-46` (docstring), `:826-831` (`cuts_by_name = combined_cuts(...)` per name over all records), `:832-837` (each record post-processed with those cuts), `:566` (`peak_mass = cuts["peak_mass"]`), `:580` (`split = cuts["split_mass"]`), `:842-847` (per-sample files written), `:849-853` + `:1003` (`sum_histograms`: summed file = sum of the per-sample histograms); build report `options.peak_scope` = combined |
| per-sample README values (σ_eff, order, construction, source, status, Σw, normalisation, files used, negative-weight fraction, share) | registry v5 + `v7_decisions_2026-11-14.json` (via `make_readme.py` helpers); `checks_final.json` `samples`; generator `delivery/make_per_sample_readmes.py` |
| files in the record (published / listed) | `mappings/inputs_20261103.json` and `mappings/inputs_D15_20261107.json` (`portal_number_files`, read live 3 and 7 Nov); the 13 samples reused from 25 Oct: every file of the record's complete file index (`studies/mc_expansion_20261103/HANDOFF.md:102,311`: their complete lists equal the 25 Oct input lists; the portal `number_files` of these 13 was not re-read here) |
