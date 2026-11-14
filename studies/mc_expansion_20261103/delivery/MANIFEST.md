# MANIFEST: sources of every value in the final MC delivery README (14 Nov 2026)

Delivery draft (NOT uploaded, NOT sent): `CMS_Run2016GH_MC-summedSM-71samples_16p393invfb_build2026-11-14_mc.root`
on the cluster at `/storage/agrp/berkom/atlas-utilization/work/mcexp_20261103/full/deliver_20261109/`. It is a byte copy
(`cp -p`, then `cmp` OK) of `full/build_20261109/fullrun_summedSM_mc.root`.

Code: pin `6de9d3e605900a628bae372bdba4ea3308e9750f`. All file:line references below are at that commit. I printed
each one with `git show 6de9d3e:<file> | sed -n <line>p` on 14 Nov (VERIFIED BY READING).
Registry: `studies/cms_mc_weights_v3/cms_mc_normalisation_v5.json` at 5493d0f. The cluster copy is
`full/registry/cms_mc_normalisation_v5.json`, sha256 `6d193c4489c2144a58d59c1b38fce7c43393e70d5532bd6ad95bf1b40e6f01e0`,
equal to the git blob (VERIFIED BY RUNNING). It was passed explicitly with `--registry` (the builder's default is v3:
`build_mc_delivery.py:1081-1083`).

## How the README was made

`delivery/make_readme.py` reads three inputs:
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
