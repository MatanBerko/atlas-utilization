# Upstream #39 #40 #42 sync: real-file proof, 23 Oct 2026

**Result: every CMS output is identical between OLD and NEW code, on all three branches —
VERIFIED BY RUNNING.**

- **Jobs:** per-file array `5305468[]` (9 subjobs) and build/compare job `5305469`
  (`-W depend=afterok`), on wipp-home, 23 Oct 2026 16:32–17:43. All 10 exited with status 0.
- **Evidence:** `evidence/proof/`: the six comparison JSONs and the build/compare log
  (`build.log`). The originals are in `work/sync42_20261023/evidence/` and `logs/`.
- **Comparison scripts:** the unchanged `studies/mcport_validation_20261014/compare.py` and
  `mc_compare.py`, taken from the NEW MC code. The data per-file comparisons go through
  `cluster/compare_data_runs.py`, which only narrows compare.py's dataset list (to 2 or 5
  datasets, file 0). It is the #35 wrapper, with the list as an argument.
- **Method:** that of `studies/sync_35_20261019`.
  - Each commit was exported with `git archive` to `checkouts/sync42_20261023/<side>_<branch>.tar`.
  - The job unpacked it into node-local scratch, and OLD then NEW ran from the same path in
    the same job.
  - `git_commit` in the job metadata therefore reads "UNKNOWN" on both sides; the commit is
    recorded by the tar header (`git get-tar-commit-id`) in the logs.

## What was compared

| branch | OLD | NEW | tarball sha256 (OLD / NEW) |
|---|---|---|---|
| master | `origin/master` `aaf945a` (upstream 7f2da5d + CMS) | `sync/master-upstream-42-20261023` `6ad6822` (+ upstream 29291ae; CMS production code unchanged) | `b729e678d4c5051f` / `d737880885095dd9` |
| data | `feature/cms-btag-singleelectron-20261020` `b6b441c` | `sync/data-upstream-42-20261023` `c0e734b` | `ce1053cfb55c9c7a` / `ada75d5c15144730` |
| MC | `feature/cms-mc-btag-singleelectron-20261020` `cd22aa2` | `sync/mc-upstream-42-20261023` `dc760da` | `2bd9c4cb99b20706` / `290d06b8defbc0c2` |

Each NEW commit = its OLD commit + a plain merge of upstream/master `29291ae` (#39 9af30d2,
#40 5fbf1ef, #42 29291ae) + the CMS test update of step 3. The master side also has this
study's own files. No CMS production file differs between OLD and NEW (`git diff`: only
upstream files, `studies/cms_datasets/tests/` and `studies/sync_42_20261023/`).

Options used:

- **master per-file:** `--dataset-label <DS> --record-id <R> --file-index 0 --population matched4`
  (master's own options, as in #35). DoubleMuon 30522, DoubleEG 30521.
- **data-branch per-file:** the same with `--population matched5`, for the five datasets with
  the branch registry's Run2016G record IDs: DoubleMuon 30522, SingleMuon 30530, DoubleEG
  30521, MuonEG 30528, SingleElectron 30529.
- **MC per-file:** `--is-mc --dataset-label MC --record-id <R> --file-index 0 --population matched4`
  (exactly `pbs_mc_pilot.sh`), for 67801 (TTTo2L2Nu) and 72752 (WZTo3LNu).
- **master delivery:** `build_four_dataset_delivery.py --datasets DoubleMuon,DoubleEG` (the
  rest are defaults).
- **data delivery (matched5):** the same builder,
  `--datasets DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron`.
- **MC build:** `build_mc_delivery.py --smoke-test` with all defaults (`--peak-scope combined`,
  `--peak-on weighted`, `--min-events-basis raw`, `--output-mode both`).

## Per-file outputs

| branch | file | shards compared | shards identical | job_metadata leaves | physics differences | provenance differences |
|---|---|---:|---:|---:|---:|---|
| master | DoubleMuon 30522 / 0 | 8 | 8 | 12,114 | 0 | created_utc, elapsed_sec |
| master | DoubleEG 30521 / 0 | 8 | 8 | 8,488 | 0 | created_utc, elapsed_sec |
| data | DoubleMuon 30522 / 0 | 8 | 8 | 12,792 | 0 | created_utc, elapsed_sec |
| data | SingleMuon 30530 / 0 | 8 | 8 | 10,975 | 0 | created_utc, elapsed_sec |
| data | DoubleEG 30521 / 0 | 8 | 8 | 9,221 | 0 | created_utc, elapsed_sec |
| data | MuonEG 30528 / 0 | 8 | 8 | 9,456 | 0 | created_utc, elapsed_sec |
| data | SingleElectron 30529 / 0 | 8 | 8 | 9,272 | 0 | created_utc, elapsed_sec |
| MC | 67801 / 0 (TTTo2L2Nu; 136,000 read, 78,632 accepted, 197 labels) | 8 (every mass array and every `_mcraw_*` sibling, element by element) | 8 | — | 0 | created_utc, elapsed_sec |
| MC | 72752 / 0 (WZTo3LNu; 457,263 read, 163,294 accepted, 168 labels) | 8 (same) | 8 | — | 0 | created_utc, elapsed_sec |
| **total** | 9 files | **72** | **72** | | **0** | |

## Delivery builds

| output | histograms OLD / NEW | bins compared | identical (names, edges, contents, variances, entries, titles) | totals OLD = NEW |
|---|---|---:|---|---|
| master `proof_bumpnet.root` | 220 / 220 | 220,440 | yes | 216,498 entries |
| master `proof_bumpnet_cropped.root` | 220 / 220 | 6,830 | yes | 216,498 entries |
| master `build_summary_rare4_four_dataset.json`, `manifest_proof.json` | — | — | yes (apart from 2 normalised directory paths) | — |
| data (matched5) `proof_bumpnet.root` | 548 / 548 | 549,096 | yes | 862,854 entries |
| data (matched5) `proof_bumpnet_cropped.root` | 548 / 548 | 18,465 | yes | 862,854 entries |
| data `build_summary_rare4_four_dataset.json`, `manifest_proof.json` | — | — | yes (apart from 2 normalised directory paths) | — |
| MC `proof_record67801_mc.root` | 1,217 / 1,217 | 1,219,434 | yes (Sumw2 present) | Σw = 5,184,429.555446958 |
| MC `proof_record72752_mc.root` | 1,118 / 1,118 | 1,120,236 | yes (Sumw2 present) | Σw = 52,267.21065391979 |
| MC `proof_summedSM_mc.root` | 1,292 / 1,292 | 1,294,584 | yes (Sumw2 present) | Σw = 5,236,696.766100869 |
| MC `proof_build_report.json` | — | — | yes; only `generated_utc` differs | — |

The MC build is a **smoke test**: Σw comes from one file per sample, so the yields are not
physics. The point is that the NEW code produces bit-identical histograms and an identical
report.

## Why nothing changed (static check, `evidence/static_check.json`)

Upstream changed 8 files between 7f2da5d and 29291ae. The definitions that CMS code can reach
by name are `IMCalculator._get_all_events_fs` / `_limit_particles_in_fs` (#40),
`physics_calcs.limit_particles_in_fs` (#40), and `physics_calcs.filter_events_by_kinematics` and
`consts.MUON_REL_ISOLATION_FIELD` (#39). By reading, none of them is executed by CMS production:

- CMS builds its own exact labels and never calls the capping function;
- the IMCalculator methods CMS executes (`filter_by_particle_counts`, `slice_by_field`,
  `calculate_invariant_mass`, via `_calculate_combination_invariant_mass`) are unchanged;
- CMS has its own object selection, so #39's muon isolation does not reach it;
- no CMS file imports the #42 parsing/trigger code or reads `config.yaml`.

The JSON's `verdicts_by_reading` gives file:line for each.

The finished m0m1j0 study (`studies/m0m1j0_cms/histograms.py:455`) still calls
`limit_particles_in_fs`, so re-running that study would now give #40's labels. It was not
re-run or changed (out of scope). The delivery builders import only its naming and binning
helpers.

## Local tests (step 3, `evidence/local_tests.txt`)

All CMS test files pass on the three NEW branches (7 / 8 / 14 files). Two CMS test files pinned
upstream's OLD `limit_particles_in_fs` behaviour and were updated on the NEW branches (test
expectations only; commit `dc1da07`, cherry-picked as `c0e734b` and `dc760da`):

- `studies/cms_datasets/tests/test_exact_jet_labels.py`. 19 checks failed on NEW, all of them
  expecting the old "every count above 4 → 4" cap.
  - Now: 2 muons + 1 b-jet leave one jet slot, so the capped reference groups 3/4/5/6/11 jets
    under `0e_2m_1j_1b` (5 events, 1 label instead of 2).
  - The "unchanged final state" check now uses "labels the cap leaves as they are" instead of
    "≤ 3 light jets".
  - The capping table states #40's results, with Maryna's examples (`0e_1m_5j_0b → 0e_1m_3j_0b`,
    `2e_0m_5j_1b → 2e_0m_1j_1b`, …).
- `studies/cms_datasets/tests/test_electron_datasets.py`. 3 checks failed. This test compares
  CMS labels with upstream's live `group_by_final_state` (read from `upstream/master`), so it
  failed on OLD code too once upstream reached #40.
  - Pointed at each upstream commit: 7f2da5d and 9af30d2 give 109/109 checks; 5fbf1ef and
    29291ae give 3 failures.
  - The expectations now state #40's capped upstream labels. Two specs that #40 leaves
    unchanged were added, so the label-format check stays meaningful.

No CMS production code was changed.

## Files

- New in `checkouts/sync42_20261023/`:
  - the 6 pinned tarballs;
  - `pinned_code_20261023.tar.gz`, which holds all six. Verified: gzip OK, 6 entries, each
    byte-identical (sha256) to its original.
- New in `work/sync42_20261023/`: runs (18), deliveries (6), logs, evidence, the mapping, the
  script copy, `jobids.txt` and the `code` link.
- **Cluster file count 122,579 → 122,878 (+299)** (23 Oct 17:46), within ≤ 125,000.
  `qstat -u berkom` is empty.
