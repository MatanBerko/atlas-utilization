# Cluster file-count inventory and archive plan — 24 Oct 2026 (Phase 1)

Area: `/storage/agrp/berkom/atlas-utilization/`. Every count is VERIFIED BY RUNNING unless marked
UNVERIFIED: PBS jobs `5311883` and `5311903` (io=1, read-only `lstat`/`scandir` walks, no link
followed; `scripts/`), raw data in `evidence/inventory*.json`. "Files" means inodes (files +
folders + links), which is what the quota counts.

## Quota

| | used | soft quota | hard limit |
|---|---:|---:|---:|
| files | **123,879** (24 Oct, after this phase's report files; 123,867 before) | 150,000 | 200,000 |
| space | 307,537,632 KB ≈ 293 GiB | 4 TiB | 5 TiB |

The walk counted **123,871** inodes under the area; with the second job's report files that is the quota's figure, so nothing is unexplained.

## Top level

| folder | files | size | newest change | note |
|---|---:|---:|---|---|
| `checkouts/` | 3,539 | 6.01 GB | 2026-10-24 00:14 | pinned code copies; 24 of them were already packed into .tar on 11 Oct |
| `envs/` | 23,401 | 0.92 GB | 2026-09-17 09:47 | the Python environment — never touched, never proposed |
| `home_backup_20261018/` | 14 | 0.00 GB | 2026-10-18 20:11 | $HOME backup of 18 Oct — never touched, never proposed |
| `logs/` | 7,104 | 0.01 GB | 2026-10-07 17:42 | PBS logs of finished jobs, 9 Sep – 7 Oct |
| `output/` | 25,026 | 31.91 GB | 2026-10-11 10:56 | older study outputs and the 7 Oct data production |
| `work/` | 64,786 | 138.21 GB | 2026-10-24 00:20 | per-task work folders |

## work/

| folder | files | size | newest change | what it is | still read by a planned step? | proposal |
|---|---:|---:|---|---|---|---|
| `fullrun_20261017` | 7,564 | 73.90 GB | 2026-10-18 19:46 | MC full run of 17-18 Oct (497 files, 13 samples) and its builds | past result we may compare against | **KEEP** |
| `electron_prep` | 5,518 | 0.47 GB | 2026-10-04 14:35 | electron-dataset preparation measurements (4 Oct) | finished; superseded by the 7 Oct production | **ARCHIVE (A)** |
| `ttbar_count_vs_atlas` | 5,406 | 5.32 GB | 2026-10-05 11:15 | ttbar combination-count check vs ATLAS PR #31 (4-5 Oct) | finished | **ARCHIVE (A)** |
| `cms_mc_v3_pilot_20261011` | 3,834 | 26.60 GB | 2026-10-12 10:12 | MC v3 pilot production and builds (11-12 Oct) | superseded by the 17 Oct full run; cited by the MC v3 handoffs; was PROTECTED on 11 Oct | **KEEP** |
| `cms_mc_v2` | 3,708 | 5.46 GB | 2026-09-30 16:53 | MC v2 production, cancelled 30 Sep | finished/cancelled; superseded by v3 | **ARCHIVE (A)** |
| `cms_mc_phase1` | 3,012 | 1.20 GB | 2026-10-01 10:13 | MC phase-1 study (30 Sep) | finished; superseded by v3 | **ARCHIVE (A)** |
| `cms_mc_v3_impl_20261011` | 2,271 | 0.38 GB | 2026-10-11 10:12 | MC v3 implementation checks (10-11 Oct) | named as an input by HANDOFF_IMPLEMENTATION.md | **KEEP** |
| `deliver_all_datasets_bumpnet` | 1,878 | 0.10 GB | 2026-09-29 10:12 | all-dataset delivery attempt, trigger preflight (28-29 Sep) | finished; superseded by the 7 Oct delivery | **ARCHIVE (B, optional)** |
| `cms_mc_v3_design_20261010` | 1,862 | 0.16 GB | 2026-10-10 17:29 | MC v3 design checks (10 Oct) | named as an input by the MC v3 HANDOFF | **KEEP** |
| `rare4_production_pinned` | 1,636 | 0.14 GB | 2026-09-30 22:59 | rare4 production (30 Sep) | finished; superseded | **ARCHIVE (B, optional)** |
| `rare4_delivery` | 1,629 | 0.14 GB | 2026-10-01 00:20 | rare4 delivery (1 Oct) | finished; superseded | **ARCHIVE (B, optional)** |
| `rare4_pilot_pinned` | 1,617 | 0.14 GB | 2026-09-30 22:53 | rare4 pilot (30 Sep) | finished | **ARCHIVE (B, optional)** |
| `nonjet4_production_pinned` | 1,571 | 0.13 GB | 2026-09-30 10:41 | nonjet4 production (30 Sep) | finished; superseded | **ARCHIVE (B, optional)** |
| `nonjet4_delivery` | 1,564 | 0.13 GB | 2026-09-30 15:04 | nonjet4 delivery (30 Sep) | finished; superseded | **ARCHIVE (B, optional)** |
| `nonjet4_pilot_pinned` | 1,551 | 0.13 GB | 2026-09-30 10:13 | nonjet4 pilot (30 Sep) | finished | **ARCHIVE (B, optional)** |
| `muon_combined_delivery` | 1,491 | 0.11 GB | 2026-09-29 15:22 | muon combined delivery (29 Sep) | finished; superseded | **ARCHIVE (B, optional)** |
| `matched_top4_production_pinned` | 1,480 | 0.11 GB | 2026-09-29 15:22 | top-4 production (29 Sep) | finished; superseded | **ARCHIVE (B, optional)** |
| `top4_pilot_pinned` | 1,462 | 0.11 GB | 2026-09-29 15:22 | top-4 pilot (29 Sep) | finished | **ARCHIVE (B, optional)** |
| `matching_validation_pinned` | 1,421 | 0.11 GB | 2026-09-29 11:53 | trigger-matching validation (29 Sep) | finished | **ARCHIVE (B, optional)** |
| `muoneg_run_pinned` | 1,380 | 0.09 GB | 2026-09-29 10:39 | MuonEG generic delivery (28-29 Sep) | finished; superseded | **ARCHIVE (B, optional)** |
| `m0m1j0_cms` | 1,329 | 0.04 GB | 2026-09-24 10:12 | m0m1j0 CMS study (21-24 Sep) | finished study | **ARCHIVE (B, optional)** |
| `upstream_trigger_cms` | 1,220 | 0.05 GB | 2026-09-24 11:14 | upstream trigger-matching check (23-24 Sep) | finished | **ARCHIVE (B, optional)** |
| `ceiling_yield` | 1,124 | 0.05 GB | 2026-09-26 14:17 | ceiling-yield study (26 Sep) | finished | **ARCHIVE (B, optional)** |
| `per_dataset_yield` | 1,056 | 0.04 GB | 2026-09-27 10:12 | per-dataset yield study (25-27 Sep) | finished | **ARCHIVE (B, optional)** |
| `cms_coverage` | 1,011 | 0.05 GB | 2026-09-25 10:12 | CMS coverage survey (24-25 Sep) | finished | **ARCHIVE (B, optional)** |
| `investigate_bumpnet_rejection` | 910 | 0.05 GB | 2026-09-28 11:52 | BumpNet rejection investigation (28 Sep) | finished | **ARCHIVE (B, optional)** |
| `deliver_doublemuon_bumpnet` | 889 | 0.05 GB | 2026-09-28 10:12 | DoubleMuon delivery (27-28 Sep) | finished; superseded | **ARCHIVE (B, optional)** |
| `serecheck_20261019` | 778 | 0.05 GB | 2026-10-19 14:13 | SingleElectron re-check + b-tag study (19 Oct) | recent, small | **KEEP** |
| `ttbar_pr40_20261021` | 725 | 12.84 GB | 2026-10-21 19:51 | ttbar test of upstream #40 (21 Oct) | recent proof, cited by the #40 work | **KEEP** |
| `generic_cuts` | 721 | 0.04 GB | 2026-09-25 10:12 | generic field/bit cuts validation (24-25 Sep) | finished | **ARCHIVE (B, optional)** |
| `mcprep_20261017` | 511 | 5.66 GB | 2026-10-17 11:03 | MC full-run preparation (17 Oct) | recent; input sweep for the 17 Oct run | **KEEP** |
| `cms_mc_v3_jets_20261011` | 395 | 0.18 GB | 2026-10-11 21:24 | MC v3 jet-excess study (11 Oct) | small | **KEEP** |
| `mcport_20261014` | 387 | 1.68 GB | 2026-10-14 14:13 | MC-port validation (14 Oct) | small; its compare tools are reused | **KEEP** |
| `cms_mc_v3_pileup_20261011` | 349 | 0.17 GB | 2026-10-11 11:18 | MC v3 pileup study (11 Oct) | small | **KEEP** |
| `btagse_20261020` | 316 | 0.71 GB | 2026-10-20 14:29 | b-tag / SingleElectron real-file checks (20 Oct) | recent, small | **KEEP** |
| `sync42_20261023` | 307 | 0.37 GB | 2026-10-23 22:27 | sync with upstream #39/#40/#42 proof (23 Oct) | recent proof, cited | **KEEP** |
| `lean_20261023` | 260 | 0.31 GB | 2026-10-24 00:13 | lean-branch proof (23-24 Oct) | recent proof, cited | **KEEP** |
| `rebuild_validation_20261014` | 255 | 0.17 GB | 2026-10-14 12:23 | rebuilt-master validation (14 Oct) | small | **KEEP** |
| `sync35b_20261020` | 141 | 0.26 GB | 2026-10-19 19:43 | sync with upstream #35 proof (19-20 Oct) | small | **KEEP** |
| `peakfix_20261018` | 61 | 0.22 GB | 2026-10-19 10:59 | MC peak fix (18 Oct) | small | **KEEP** |
| `mult40_20261023` | 44 | 0.02 GB | 2026-10-23 23:22 | #40-as-default proof (23 Oct) | recent proof, cited | **KEEP** |
| `overlapconv_20261015` | 40 | 0.03 GB | 2026-10-15 15:49 | overlap-convention study (15 Oct) | small | **KEEP** |
| `lumi_coverage_four_20261013` | 34 | 0.17 GB | 2026-10-13 11:54 | luminosity coverage check (13 Oct) | small | **KEEP** |
| `se_hltconf_20261007` | 22 | 0.06 GB | 2026-10-07 17:44 | SingleElectron HLT config check (7 Oct) | small | **KEEP** |
| `evb_smoke_20261006` | 14 | 0.00 GB | 2026-10-06 15:57 | electron datasets vB smoke test (6 Oct) | small | **KEEP** |
| `smoke_20261021` | 7 | 0.00 GB | 2026-10-21 18:23 | cluster health-check smoke job (21 Oct) | small | **KEEP** |
| `cms_mc_norm_investigation` | 6 | 0.00 GB | 2026-09-30 10:13 | MC normalisation investigation (30 Sep) | small | **KEEP** |
| `cluster_archive_20261024` | 5 | 0.00 GB | 2026-10-24 00:20 | THIS task's report/log folder | in use | **KEEP** |
| `cluster_cleanup_20261011` | 4 | 0.00 GB | 2026-10-11 10:22 | the 11 Oct cleanup's log folder | small | **KEEP** |
| `acltest_20261008` | 3 | 0.00 GB | 2026-10-08 15:32 | ACL test folder: grants Maryna (marybo) access | ACL — must not be changed | **KEEP (ACL)** |
| `cms_mc_v3_counts_20261011` | 3 | 0.00 GB | 2026-10-11 16:00 | MC v3 count check (11 Oct) | small | **KEEP** |
| `se_smoke_20261007` | 3 | 0.00 GB | 2026-10-07 17:34 | SingleElectron smoke test (7 Oct) | small | **KEEP** |

## output/

| folder | files | size | newest change | proposal |
|---|---:|---:|---|---|
| `cms_datasets` (see below) | 17,077 | 20.88 GB | 2026-10-11 10:56 | per subfolder |
| `hgg_zee` | 2,775 | 3.84 GB | 2026-09-17 08:59 | KEEP — H→γγ study output (16-17 Sep); not needed for the target |
| `hgg_full` | 2,099 | 0.57 GB | 2026-09-16 16:57 | KEEP — H→γγ study output (16-17 Sep); not needed for the target |
| `m0m1j0_full_v2` | 402 | 0.10 GB | 2026-09-22 19:47 | KEEP — older study output (Sep); not needed for the target |
| `m0m1j0_full` | 345 | 0.09 GB | 2026-09-22 11:52 | KEEP — older study output (Sep); not needed for the target |
| `m0m1j0_variants_data` | 345 | 0.08 GB | 2026-09-23 15:40 | KEEP — older study output (Sep); not needed for the target |
| `ceiling_yield` | 298 | 0.42 GB | 2026-09-26 14:17 | KEEP — older study output (Sep); not needed for the target |
| `m0m1j0_variants_ttbar` | 297 | 0.04 GB | 2026-09-23 15:30 | KEEP — older study output (Sep); not needed for the target |
| `hgg_bias` | 256 | 0.00 GB | 2026-09-17 14:35 | KEEP — H→γγ study output (16-17 Sep); not needed for the target |
| `hgg_stats` | 249 | 0.02 GB | 2026-09-18 10:12 | KEEP — H→γγ study output (16-17 Sep); not needed for the target |
| `m0m1j0_ttbar_full` | 199 | 0.07 GB | 2026-09-22 20:17 | KEEP — older study output (Sep); not needed for the target |
| `hgg_pilot` | 189 | 0.11 GB | 2026-09-16 16:56 | KEEP — H→γγ study output (16-17 Sep); not needed for the target |
| `cms_coverage_full` | 176 | 0.06 GB | 2026-09-30 15:46 | KEEP — older study output (Sep); not needed for the target |
| `per_dataset_yield_triggered` | 68 | 0.05 GB | 2026-09-26 11:23 | KEEP — older study output (Sep); not needed for the target |
| `per_dataset_yield` | 65 | 0.11 GB | 2026-09-26 10:56 | KEEP — older study output (Sep); not needed for the target |
| `cms_higgs_4lepton_cluster_fullscale_20260909_113726` | 40 | 3.43 GB | 2026-09-11 10:12 | KEEP — older study output (Sep); not needed for the target |
| `m0m1j0_pilot` | 21 | 0.01 GB | 2026-09-22 11:04 | KEEP — older study output (Sep); not needed for the target |
| `ceiling_yield_pilot` | 18 | 0.01 GB | 2026-09-26 12:20 | KEEP — older study output (Sep); not needed for the target |
| `reports` | 17 | 0.00 GB | 2026-09-14 21:26 | KEEP — older study output (Sep); not needed for the target |
| `deliver_doublemuon_bumpnet` | 16 | 0.00 GB | 2026-09-27 20:08 | KEEP — older study output (Sep); not needed for the target |
| `investigate_bumpnet_rejection` | 14 | 0.00 GB | 2026-09-28 11:51 | KEEP — older study output (Sep); not needed for the target |
| `cms_m0m1j0_smoketest_20260914_211743` | 13 | 0.84 GB | 2026-09-14 21:26 | KEEP — older study output (Sep); not needed for the target |
| `cms_higgs_4lepton_cluster_smoketest_20260909_111303` | 12 | 0.33 GB | 2026-09-09 11:24 | KEEP — older study output (Sep); not needed for the target |
| `cms_m0m1j0_smoketest_20260914_203247` | 12 | 0.84 GB | 2026-09-14 20:42 | KEEP — older study output (Sep); not needed for the target |
| `m0m1j0_ttbar_pilot` | 11 | 0.00 GB | 2026-09-22 20:08 | KEEP — older study output (Sep); not needed for the target |
| `cms_m0m1j0_smoketest_20260914_202709` | 8 | 0.00 GB | 2026-09-14 20:27 | KEEP — older study output (Sep); not needed for the target |
| `cms_coverage_merge` | 3 | 0.00 GB | 2026-09-24 15:33 | KEEP — older study output (Sep); not needed for the target |

### output/cms_datasets/

| folder | files | size | newest change | what it is | proposal |
|---|---:|---:|---|---|---|
| `runs_matched4_full_20261007` | 4,694 | 4.38 GB | 2026-10-11 10:56 | the 7 Oct four-dataset data production (390 files); past result we may compare against; the full-run pre-check read it | KEEP |
| `runs_matched_rare4` | 2,522 | 3.90 GB | 2026-10-01 00:21 | rare4 data runs (1 Oct); superseded by 7 Oct | KEEP (could be archived later: 2,522) |
| `runs_matched_vB_exactlabels_20261005` | 2,519 | 3.90 GB | 2026-10-06 13:27 | vB exact-labels data runs (5-6 Oct); read-only reference of the 7 Oct pilot comparison | KEEP (could be archived later: 2,519) |
| `runs_matched_nonjet4` | 2,106 | 2.84 GB | 2026-10-01 00:21 | nonjet4 data runs (30 Sep); superseded | KEEP (could be archived later: 2,106) |
| `runs_matched` | 1,686 | 1.98 GB | 2026-10-01 00:21 | matched data runs (29 Sep); superseded | KEEP (could be archived later: 1,686) |
| `runs` | 956 | 0.96 GB | 2026-10-04 14:31 | generic data runs (28 Sep - 4 Oct); superseded | KEEP (could be archived later: 956) |
| `electron_vB_20261006` | 390 | 0.21 GB | 2026-10-06 16:56 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `singleelectron_prep_20261007` | 319 | 0.01 GB | 2026-10-07 17:48 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `deliver` | 264 | 0.25 GB | 2026-10-07 16:37 | the delivered BumpNet ROOT files; grants Maryna (marybo) access; delivered; ACL — must not be changed | KEEP (ACL) |
| `preflight` | 255 | 0.02 GB | 2026-09-28 17:55 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `runs_matched4_pilot_on_20261006` | 187 | 0.46 GB | 2026-10-06 16:00 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `runs_matched4_pilot_dr012_20261007` | 186 | 0.46 GB | 2026-10-07 14:36 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `runs_matched4_pilot_off_20261006` | 186 | 0.46 GB | 2026-10-06 16:04 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `runs_matched4_pilot_onboth_20261006` | 186 | 0.46 GB | 2026-10-06 16:45 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `vB_upstreamnames_pilot` | 89 | 0.07 GB | 2026-10-06 13:26 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `runs_master_matched_pilot_20261006` | 83 | 0.14 GB | 2026-10-06 16:05 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `vB_exactlabels_pilot` | 75 | 0.06 GB | 2026-10-06 13:26 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `matching_validation` | 70 | 0.05 GB | 2026-09-30 10:12 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `run` | 57 | 0.08 GB | 2026-09-28 21:41 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `rare4_pilot` | 56 | 0.06 GB | 2026-09-30 22:55 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `studies` | 50 | 0.08 GB | 2026-10-04 11:26 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `nonjet4_pilot` | 49 | 0.04 GB | 2026-09-30 10:40 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `electron_vB_20261007` | 35 | 0.00 GB | 2026-10-07 16:39 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `top4_pilot` | 31 | 0.03 GB | 2026-09-29 13:51 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| `plots` | 12 | 0.00 GB | 2026-09-28 18:18 | older pilot / prep output (28 Sep – 7 Oct); small | KEEP |
| 14 loose files (mappings, summaries) | 14 | — | Sep | | KEEP |

## checkouts/ and logs/

- `checkouts/`: 3,539 files. The five largest are git clones of recent tasks (`ttbar_pr40` 839, `peakfix` 767, `fullrun` 690, `mult40` 664, `serecheck` 518). The rest are already single `.tar` files (11 Oct) or a few tarballs. KEEP: they are small, and some are cited as the pinned code of recent proofs.
- `logs/`: 7,104 files in about 30 folders of PBS output from 9 Sep – 7 Oct (H→γγ, m0m1j0, coverage, the 7 Oct electron_vB production, MC phase 1/v2). Every outcome is summarised in a pushed handoff. **ARCHIVE (A)**, as one file.

## What the planned steps read

- The full run uses the lean branch `lean/cms-layer-20261023` @ `33d77f5` and NEW folders. Its code names no folder of this area (`git grep` on the lean branch: only usage examples), so no folder above is an input of the full run.
- Recent proofs that may be cited (`work/lean_20261023`, `mult40_20261023`, `sync42_20261023`, `ttbar_pr40_20261021`): KEEP (together 1,336 files).
- Past results to compare against (`output/cms_datasets/runs_matched4_full_20261007`, `work/fullrun_20261017`): KEEP.
- Two folders grant Maryna (marybo) access through an ACL (found on 11 Oct): `output/cms_datasets/deliver/` and `work/acltest_20261008`. KEEP: packing them would remove what she can see.

## Archive plan

Each folder becomes ONE `archive/20261024/<name>.tar.gz` plus ONE `<name>.manifest.tsv` (path, size, sha256 of every file), so a folder of N files costs 2 after its original is removed. Creating `archive/20261024/` adds 2. The projections are arithmetic on the counts above: UNVERIFIED until done.

| group | folders | files now | size | files after removing the originals | total after |
|---|---|---:|---:|---:|---:|
| **A (recommended)** | `logs`, `work/electron_prep`, `work/ttbar_count_vs_atlas`, `work/cms_mc_v2`, `work/cms_mc_phase1` | 24,748 | 12.46 GB | 10 | **99,139** |
| B (optional, more margin) | the 20 superseded 24 Sep – 1 Oct work folders marked B above | 26,940 | 1.81 GB | 40 | 72,239 (with A) |

- With **A** the area goes to about **99,139** files. A full run of 10,000–15,000 new files (UNVERIFIED estimate) then ends at about 109,139–114,139, under 125,000 with about 11,000 to spare.
- Adding **B** brings it to about 72,239. It is not needed for the target, but these are old, finished folders, each superseded by the 7 Oct production and delivery.
- Not proposed: the older `output/cms_datasets/runs*` folders (9,789 files, 13.6 GB), which could be archived later if more room is needed; the H→γγ and m0m1j0 outputs; everything from 6 Oct on.
- Space: group A is 12.5 GB before compression and the area has about 3.7 TiB free under the soft quota, so space is not a constraint. The originals stay until a separate "delete originals" message.

## Phase 2 — archived and verified (24 Oct 2026, VERIFIED BY RUNNING)

Approved by Matan: all 25 folders of groups A and B. PBS array `5311954[]` (0–24, io=25), every subjob exit 0.
Archives in `/storage/agrp/berkom/atlas-utilization/archive/20261024/` (`<name>.tar.gz` + `<name>.manifest.tsv`, where `<name>` is the path with "/" → "_").
Verification results are in `work/cluster_archive_20261024/verify/` and in `evidence/verify/` here.
"Entries" = files + folders + links in the manifest = the archive's members (equal to the Phase 1 inventory count for every folder).
"Checked" = the regular files whose sha256 was recomputed from the archive stream and matched the manifest. **The originals are untouched.**

| folder | entries (= inventory) | files sha256-checked | size before | archive | gzip test | members == manifest | verified |
|---|---:|---:|---:|---:|---|---|---|
| `logs` | 7,104 | 7,047 | 0.01 GB | 0.001 GB | ok | yes | **yes** |
| `work/electron_prep` | 5,518 | 4,615 | 0.47 GB | 0.330 GB | ok | yes | **yes** |
| `work/ttbar_count_vs_atlas` | 5,406 | 4,376 | 5.32 GB | 4.956 GB | ok | yes | **yes** |
| `work/cms_mc_v2` | 3,708 | 3,245 | 5.46 GB | 4.320 GB | ok | yes | **yes** |
| `work/cms_mc_phase1` | 3,012 | 2,168 | 1.20 GB | 0.689 GB | ok | yes | **yes** |
| `work/deliver_all_datasets_bumpnet` | 1,878 | 1,482 | 0.10 GB | 0.067 GB | ok | yes | **yes** |
| `work/rare4_production_pinned` | 1,636 | 1,375 | 0.14 GB | 0.098 GB | ok | yes | **yes** |
| `work/rare4_delivery` | 1,629 | 1,369 | 0.14 GB | 0.098 GB | ok | yes | **yes** |
| `work/rare4_pilot_pinned` | 1,617 | 1,364 | 0.14 GB | 0.098 GB | ok | yes | **yes** |
| `work/nonjet4_production_pinned` | 1,571 | 1,321 | 0.13 GB | 0.091 GB | ok | yes | **yes** |
| `work/nonjet4_delivery` | 1,564 | 1,315 | 0.13 GB | 0.091 GB | ok | yes | **yes** |
| `work/nonjet4_pilot_pinned` | 1,551 | 1,309 | 0.13 GB | 0.091 GB | ok | yes | **yes** |
| `work/muon_combined_delivery` | 1,491 | 1,245 | 0.11 GB | 0.075 GB | ok | yes | **yes** |
| `work/matched_top4_production_pinned` | 1,480 | 1,242 | 0.11 GB | 0.075 GB | ok | yes | **yes** |
| `work/top4_pilot_pinned` | 1,462 | 1,232 | 0.11 GB | 0.074 GB | ok | yes | **yes** |
| `work/matching_validation_pinned` | 1,421 | 1,199 | 0.11 GB | 0.073 GB | ok | yes | **yes** |
| `work/muoneg_run_pinned` | 1,380 | 1,165 | 0.09 GB | 0.063 GB | ok | yes | **yes** |
| `work/m0m1j0_cms` | 1,329 | 1,016 | 0.04 GB | 0.027 GB | ok | yes | **yes** |
| `work/upstream_trigger_cms` | 1,220 | 1,022 | 0.05 GB | 0.041 GB | ok | yes | **yes** |
| `work/ceiling_yield` | 1,124 | 961 | 0.05 GB | 0.034 GB | ok | yes | **yes** |
| `work/per_dataset_yield` | 1,056 | 850 | 0.04 GB | 0.033 GB | ok | yes | **yes** |
| `work/cms_coverage` | 1,011 | 803 | 0.05 GB | 0.035 GB | ok | yes | **yes** |
| `work/investigate_bumpnet_rejection` | 910 | 751 | 0.05 GB | 0.041 GB | ok | yes | **yes** |
| `work/deliver_doublemuon_bumpnet` | 889 | 732 | 0.05 GB | 0.040 GB | ok | yes | **yes** |
| `work/generic_cuts` | 721 | 615 | 0.04 GB | 0.032 GB | ok | yes | **yes** |
| **total (25)** | **51,688** | | 14.27 GB | 11.57 GB | | | **25/25** |

- Quota after Phase 2: **124,011 files**, 330,985,564 KB (the 50 archive files, the archive folders and the job logs are new).
- If the 25 originals are deleted: 124,011 − 51,688 = **72,323 files** (UNVERIFIED projection), and about 14.3 GB freed against the 11.6 GB of archives.

