# Lean CMS branch — report (23–24 Oct 2026)

**In one line:** `lean/cms-layer-20261023` (`33d77f5`) is upstream master `29291ae` plus 63 added
files, the minimal CMS layer. On 7 real files it gives outputs **identical** to the full branch
`de012d2`, from the per-file databases to the final histograms. The read-only pre-check found
**no trimmed mass lists** in the 7 Oct data or the 17 Oct MC productions, so the #40 builders would
not have stopped on them.

Every number is VERIFIED BY RUNNING unless marked UNVERIFIED. No code was changed; no existing
branch was changed; no upstream file was touched (the gate printed nothing before every push).

## The lean branch

- 63 files added on top of `29291ae`, all byte-identical to `de012d2`, except `docs/CMS_LAYER.md`
  (rewritten: base, the file list grouped A/B/C with one line per file, where the records live).
  The other 201 files that `de012d2` adds are records of past studies; they stay on the existing branches.
- The 60 files on the given list, plus **3 added** (all on `de012d2`, none a record):
  - `studies/cms_datasets/electron_prep/common.py`: code, imported by `electron_vB/gen_full_mapping.py`
    (the data mapping maker);
  - `studies/cms_mc_weights_v3/evidence/fullrun_inputs_20261017.json`: an input, read by
    `fullrun_prep/make_fullrun_mappings.py` (the MC full-run mapping maker);
  - `studies/cms_mc_weights_v3/evidence/probe_mc_records.json`: an input, read by `build_registry.py`,
    which `test_mc_weights_v3.py` runs.
- Deliberately NOT added: `studies/m0m1j0_cms/v2/data/merge_v2_summary.json`, a past-study record read
  only by `merge_and_count.py`'s own `main()` self-check. No builder or launcher runs that self-check.

## Static checks and tests (Mac)

| check | result |
|---|---|
| (a) diff against `de012d2` for every added file except `docs/CMS_LAYER.md` | empty |
| (b) gate | empty |
| (c) `git diff --name-status upstream/master lean` | 63 lines, all `A`; the set equals the list + 3 |
| (d) every imported repo module and every repo path written in the code/launchers exists | yes, after the 3 additions (the rest are comments or the one self-check above) |
| (e) every Python entry point (28) runs `--help` / imports | 28/28 exit 0; `build_registry.py --check` OK (15 records); `make_fullrun_mappings.py` writes its 13 mappings |
| 15 test files (group B), lean vs `de012d2` | all exit 0 on both; output identical apart from one file path that a test cuts at 90 characters |

Logs: `evidence/local_tests/{lean,de012d2}/`.

## Real-file proof (cluster, OLD = `de012d2`, NEW = lean `33d77f5`)

Method of `sync_42_20261023`: both commits as `git archive` tarballs, unpacked in node-local scratch,
OLD then NEW from the same path in the same job; compared with the unchanged
`mcport_validation_20261014/compare.py` and `mc_compare.py` (from the OLD tarball).
Jobs `5311724[]` (7 files) and `5311725` (builds + comparisons), all exit 0.

| comparison | result |
|---|---|
| data per-file, file 0 of DoubleMuon, SingleMuon, DoubleEG, MuonEG, SingleElectron (`--population matched5`) | **identical**: 40/40 databases (every table, every mass array element by element); 0 physics differences in `job_metadata.json` |
| MC per-file, 67801 and 72752 file 0 (the `pbs_mc_pilot.sh` options) | **identical**: 16/16 databases (mass arrays and every MC sibling array, `_mcw` / `_mcraw_*`); 0 physics differences |
| data five-dataset matched5 delivery (default rule, #40) | **identical**: 201/201 histograms in the uncropped and the cropped ROOT file; summary and manifest identical |
| MC builder `--smoke-test`, defaults | **identical**: 290 + 292 + 296 histograms (67801, 72752, summed SM; names, edges, contents, variances, entries); build report identical apart from paths |

Only `created_utc` and `elapsed_sec` differ in the job records, as expected.

## Pre-check for the full run (job `5311726`, io=1, read-only)

The #40 builders STOP if a mass list was randomly trimmed to 500,000 entries in a file and would be
merged. Every `job_metadata.json` of the two past productions was read:

| production | files | files with a trimmed list (rare4 / any version) | largest list (rare4) |
|---|---|---|---|
| 7 Oct data, `output/cms_datasets/runs_matched4_full_20261007` | 390 | **0 / 0** | 292,176 (SingleMuon) |
| 17 Oct MC full run, `work/fullrun_20261017/runs` | 497 | **0 / 0** | 142,407 (DYJetsToLL_M-50) |

Per dataset / sample, the largest list:
- data: DoubleMuon 234,094; SingleMuon 292,176; DoubleEG 73,942; MuonEG 1,495;
- MC: TTTo2L2Nu 58,986; TTToSemiLeptonic 44,480; DYJetsToLL_M-50 142,407; DYJetsToLL_M-10to50 5,337;
  WZ 60,847; ZZ 65,161; WW 77,469; others below 54,000.

Full table: `evidence/cluster/precheck_capped.json`.

Caveats:
- The largest data list is 58% of the trim size. SingleElectron was not in the 7 Oct production, so
  its sizes are UNVERIFIED.
- The 7 Oct data run used the four-dataset setup; the coming five-dataset run is UNVERIFIED until it runs.

**File counts of those productions** (for planning the full run's quota):
- 7 Oct data: its HANDOFF records no file count. On disk now: 4,694 files and folders under its runs dir.
- 17 Oct MC: its HANDOFF records +6,014 in `work/fullrun_20261017` (production), and +8,254 in total
  with the build and its checkout. On disk now: 4,984 under `runs/`.
- So a full data + MC run is roughly 10,000–15,000 new files (UNVERIFIED estimate). With 123,867 used
  now, that would pass the 125,000 working limit, though not the 150,000 soft quota. Space must be
  made or the limit raised before the full run.

## Where things are

- Branches:
  - `lean/cms-layer-20261023` @ `33d77f5` (no records);
  - `study/lean-branch-proof-20261023` (this report, evidence, tools).
- Cluster (`/storage/agrp/berkom/atlas-utilization/`):
  - `checkouts/lean_20261023/`: `{old,new,tools}.tar` and `lean_20261023_code_tarballs.tar.gz`
    (verified: the three tarballs inside are byte-identical);
  - `work/lean_20261023/`: runs, deliveries, logs, evidence.
- File count: 123,602 before → **123,867** after (+265).
