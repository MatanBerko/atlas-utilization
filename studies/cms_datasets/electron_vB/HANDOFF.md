# HANDOFF — electron datasets, Prompt 1 (BUILD + MEASURE + PILOT)

Everything needed to pick this up without re-deriving anything. Nothing here
was merged into master, and no full production was run.

## 1. Code

| what | value |
|---|---|
| branch | `feature/electron-datasets-vB` (fork `github.com/MatanBerko/atlas-utilization`) |
| branched from | `origin/master` = `4bbe972` (verified before branching) |
| merged in | `origin/prep/electron-datasets` = `f30eb01`, normal merge commit, conflict-free |
| **pinned commit the measurement/pilot/closure jobs ran from** | `5d0d71d2de182267f7ecff694015b1f72cf9fc3c` |
| **pinned commit the mode=`both` pilot re-run ran from** | `3930b43ea9f4390f47c4c77c62e47c8a3f901ff9` (same code plus the Step D default flip) |
| final commit on the branch | see `git log origin/feature/electron-datasets-vB -1` (the report/evidence commit) |

Cluster checkouts, each a detached checkout pinned to one commit:

| commit | path | used for |
|---|---|---|
| `5d0d71d` | `/storage/agrp/berkom/atlas-utilization/checkouts/5d0d71d/repo` | the Step D measurement, the ON/OFF pilots, the run scan and the closure |
| `3930b43` | `.../checkouts/3930b43/repo` | the mode=`both` pilot re-run, after Step D selected `both` |
| `4bbe972` | `.../checkouts/4bbe972/repo` | the master re-run for E1(a) (master's own `--population matched`) |
| `26a7982`, `ac6f343` | `.../checkouts/<hash>/repo` | the aggregation / plotting / delivery-build steps, run interactively on the analysis node with `nice` |

Earlier commits `6e78433`, `7895359` also have checkouts; they were superseded
by `5d0d71d` after two smoke-test fixes and produced no result reported here.

## 2. Jobs

All OpenPBS job arrays, queue `N`, `#PBS -m n`, logs under
`/storage/agrp/berkom/atlas-utilization/logs/electron_vB/` (never `$HOME`).

| job ID | array | what | script |
|---|---|---|---|
| `5190699[]` | 0-7 | run-281707 file scan + HLT-branch presence over ALL 390 files | `cluster/pbs_runscan.sh` |
| `5190700[]` | 0-1 | Step D 2-file timing test | `cluster/pbs_doubleeg_eff.sh` |
| `5190701[]` | 0-15 | pilot, overlap removal **ON**, debug dump | `cluster/pbs_matched4.sh` |
| `5190702[]` | 0-15 | pilot, overlap removal **OFF**, debug dump | `cluster/pbs_matched4.sh` |
| `5190703[]` | 0-7 | master `4bbe972` re-run, `--population matched`, 8 muon pilot files | `cluster/pbs_matched4.sh` (launcher only; the driver is master's) |
| `5190704[]` | 0-132 | Step D, all 133 DoubleEG files | `cluster/pbs_doubleeg_eff.sh` |
| `5190705[]` | 0-67 | E3 closure on run 281707, the 68 files that contain it | `cluster/pbs_closure.sh` |
| `5190810[]` | 0-15 | pilot re-run, removal ON, `--doubleeg-threshold-mode both` (the provisional default Step D selected) | `cluster/pbs_matched4.sh` |

All seven arrays finished with every subjob at exit 0 and no tracebacks.

## 3. Output directories (all NEW, date-suffixed; nothing existing was touched)

```
/storage/agrp/berkom/atlas-utilization/output/cms_datasets/
  runs_matched4_pilot_on_20261006/      pilot, overlap removal ON, mode leading_only (+ *_index.json, pilot_files.json)
  runs_matched4_pilot_off_20261006/     pilot, overlap removal OFF, mode leading_only
  runs_matched4_pilot_onboth_20261006/  pilot, overlap removal ON, mode both  <-- the one the report quotes
  runs_master_matched_pilot_20261006/   master 4bbe972 re-run, matched mode
  electron_vB_20261006/
    mappings/            PBS array mapping files (pilot_all16, pilot_muon8, closure, doubleeg_eff_*)
    doubleeg_eff/        Step D 2-file timing test
    doubleeg_eff_all/    Step D, all 133 files
    closure/             runscan_<dataset>_<era>.json  (all 390 files)
    closure/parts/       per-file closure parts (keys_*.npz, accepted_*.csv, summary_*.json)
    results/evidence/    the aggregated evidence JSONs (copied into the repo)
    results/plots/       the plots (copied into the repo)
  deliver/four_dataset_pilot_20261006/  the B3 builder exercised on the PILOT shards only
```

Read-only and untouched: everything else under `output/`, in particular
`deliver/muon_combined_vB_upstreamnames_w10p0_20261006/` and
`runs_matched_vB_exactlabels_20261005/` (opened with a strict read-only
sqlite connection, `mode=ro&immutable=1`).

Scratch (safe to delete): `/storage/agrp/berkom/atlas-utilization/work/evb_smoke_20261006/`.

## 4. The pilot file list (E0)

First and middle file of every (dataset, era) record list — 16 files. `job_N`
is the directory name under each dataset, and the key in `<Dataset>_index.json`.

| dataset | era | record | file index | which | record has |
|---|---|---:|---:|---|---:|
| DoubleMuon | G | 30522 | 0 | first | 29 |
| DoubleMuon | G | 30522 | 14 | middle | 29 |
| DoubleMuon | H | 30555 | 0 | first | 28 |
| DoubleMuon | H | 30555 | 14 | middle | 28 |
| SingleMuon | G | 30530 | 0 | first | 70 |
| SingleMuon | G | 30530 | 35 | middle | 70 |
| SingleMuon | H | 30563 | 0 | first | 82 |
| SingleMuon | H | 30563 | 41 | middle | 82 |
| DoubleEG | G | 30521 | 0 | first | 47 |
| DoubleEG | G | 30521 | 23 | middle | 47 |
| DoubleEG | H | 30554 | 0 | first | 86 |
| DoubleEG | H | 30554 | 43 | middle | 86 |
| MuonEG | G | 30528 | 0 | first | 29 |
| MuonEG | G | 30528 | 14 | middle | 29 |
| MuonEG | H | 30561 | 0 | first | 19 |
| MuonEG | H | 30561 | 9 | middle | 19 |

`job_0..job_3` per dataset = (G first, G middle, H first, H middle). Record
totals: DoubleMuon 57, SingleMuon 152, DoubleEG 133, MuonEG 48 — matching D1.
Full URLs: `runs_matched4_pilot_on_20261006/pilot_files.json`.

The 8 muon pilot files map onto these existing master-production job
directories under `runs_matched_vB_exactlabels_20261005/` (used read-only for
the E1(c) reproducibility check): DoubleMuon `job_0, job_14, job_29, job_43`;
SingleMuon `job_0, job_35, job_70, job_111`.

## 5. The E3 closure run

Run **281707**, confirmed present in the production golden JSON
(`data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt`,
lumi ranges `[[99,982],[1000,1065],[1087,1089]]`). It lives only in era H.
Files containing it, from `find_run_files.py` over **all 390 files**:
DoubleEG H 33, SingleMuon H 20, DoubleMuon H 9, MuonEG H 6 — 68 files,
8,131,527 golden events of that run. Exact per-file index lists:
`electron_vB_20261006/closure/runscan_<dataset>_<era>.json`
(`files_with_target_run`), and the array mapping `mappings/closure.txt`.

## 6. How to resume

```bash
# 0. a pinned checkout of whatever commit you want to run
C=<commit>; B=/storage/agrp/berkom/atlas-utilization/checkouts
git clone --no-checkout https://github.com/MatanBerko/atlas-utilization.git $B/${C:0:7}/repo
cd $B/${C:0:7}/repo && git fetch origin $C && git checkout --detach $C

# 1. re-run any array (qsub lives at /opt/pbs/bin/qsub; it is NOT on $PATH)
R=$B/${C:0:7}/repo
M=/storage/agrp/berkom/atlas-utilization/output/cms_datasets/electron_vB_20261006
L=/storage/agrp/berkom/atlas-utilization/logs/electron_vB
cd $R
/opt/pbs/bin/qsub -J 0-15 -N evb_pilot_on \
  -o $L/pilot/on_^array_index^.out -e $L/pilot/on_^array_index^.err \
  -v REPO_DIR=$R,MAPPING_FILE=$M/mappings/pilot_all16.txt,\
OUT_BASE=<NEW dated dir>,POPULATION=matched4,EXTRA_ARGS=--debug-event-dump \
  studies/cms_datasets/electron_vB/cluster/pbs_matched4.sh

# 2. aggregate (analysis node, interactive, nice; no ROOT in this env --
#    the delivery builder deliberately uses uproot only)
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python
nice -n 10 $PY studies/cms_datasets/electron_vB/aggregate_doubleeg_efficiency.py \
  --in-dir $M/doubleeg_eff_all --out-json <repo>/studies/cms_datasets/electron_vB/evidence/stepD_doubleeg_efficiency.json \
  --out-plots <repo>/studies/cms_datasets/electron_vB/plots
nice -n 10 $PY studies/cms_datasets/electron_vB/aggregate_closure.py \
  --parts-dir $M/closure/parts --out .../evidence/E3_closure.json
nice -n 10 $PY studies/cms_datasets/electron_vB/compare_shards.py --a-root ... --b-root ... --jobs ... --out ...
nice -n 10 $PY studies/cms_datasets/electron_vB/diff_overlap_removal.py --on-root ... --off-root ... --jobs ... --out ...
nice -n 10 $PY studies/cms_datasets/electron_vB/make_pilot_plots.py --on-root ... --off-root ... --delivery-root ... --out-dir ... --out-json ...
```

## 7. What Prompt 2 (full production) needs

1. Matan's decision on `doubleeg_threshold_mode`. The code default is now
   **`both`**, PROVISIONAL, set by Step D's fixed criterion (barrel Δ = 3.40 pp,
   endcap Δ = 18.11 pp, both above the 2.0 pp threshold and not borderline).
   If he picks `leading_only` instead, pass
   `--doubleeg-threshold-mode leading_only` to every matched4 job; nothing
   else changes.
2. A new dated output directory, `--population matched4` on all 390 files
   (57 + 152 + 133 + 48), one array per dataset, and the per-dataset
   `<Dataset>_index.json` written next to it (`gen_full_mapping` style; the
   pilot's `gen_pilot_mapping.py` shows the format).
3. `build_four_dataset_delivery.py --version rare4` with NO extra flags over
   that directory: with no flags it already does upstream-exact names
   (`_width_10.0`), no per-histogram minimum, no filled-bin cut, and the
   >=100-events-per-final-state rule once on the combined shards.
4. Do NOT run SingleElectron: postponed, no code and no runs in this round.

## 8. Rules that were followed and matter for the next step

* Nothing was pushed anywhere but the fork; no pull request, no action on
  upstream (upstream was fetched read-only, for the C7 naming comparison).
* Nothing was merged into the fork's master.
* No existing output was overwritten or deleted; all new directories carry a
  `_20261006` suffix.
* `prune_final_states_below_min_events` ran only on scratch copies, inside
  `copy_shards`, exactly as the muon delivery does.
* No batch job wrote to `$HOME`; `$TMPDIR` is used for temporaries.
