# HANDOFF — CMS full run with loose muon/electron IDs (25 Oct 2026 directories)

Branch `run/cms-fullrun-20261025` (origin only), made from `origin/lean/cms-layer-20261023`
@ `33d77f5` (= upstream master `29291ae` + 63 CMS files). Decision (Maryna, 24 Oct, approved
by Matan): muons CMS Loose ID (`Muon_looseId`), isolation `pfRelIso04_all < 0.15` kept;
electrons `cutBased >= 2` (Loose); jets unchanged.

Nothing is submitted for the full run. No Pull Request; nothing upstream; no message sent.

## Step 0 — preflight (24 Oct 2026) — DONE

- `upstream/master` = `29291ae` (unchanged) and `origin/lean/cms-layer-20261023` = `33d77f5`
  — VERIFIED BY RUNNING (`git rev-parse` after `git fetch`).
- File quota on /storage: **72,328** files used (soft limit 150,000; Matan's ceiling 125,000)
  — VERIFIED BY RUNNING (`quota -s` on wipp-home). Space 293.7 GB of 4 TB.
- `ssh wipp-campus`: timed out (one try). `wipp-home` is used.
- Branch `run/cms-fullrun-20261025` created from the lean branch.

## Step 1 — branch titles — DONE

PBS job `5331420` (io=1, wn001, 25 s, exit 0), from the pinned clone
`checkouts/fullrun_20261025/step1_c0ce7bd` (commit `c0ce7bd`). Script `cluster/branch_titles.py`,
launcher `cluster/pbs_titles.sh`; output `evidence/branch_titles.json`. VERIFIED BY RUNNING.
Both files (data DoubleEG Run2016G record 30521 file 0; MC TTTo2L2Nu record 67801 file 0) have
all three branches, with identical titles:

| branch | type | title (verbatim) |
|---|---|---|
| `Muon_looseId` | bool | "muon is loose muon" |
| `Muon_mediumId` | bool | "cut-based ID, medium WP" |
| `Muon_pfRelIso04_all` | float32 | "PF relative isolation dR=0.4, total (deltaBeta corrections)" |
| `Electron_cutBased` | int32 | "cut-based ID Fall17 V2 (0:fail, 1:veto, 2:loose, 3:medium, 4:tight)" |

So `cutBased >= 2` is "loose or tighter" exactly as the title defines it.

## Step 2 — code change — DONE

Every use in CMS code before the change (lean `33d77f5`, `git grep`):

| file:line (before) | what | now |
|---|---|---|
| `studies/m0m1j0_cms/selection.py:18,20` | docstring (mediumId, cutBased>=3) | looseId, cutBased>=2 (+ a dated note) |
| `studies/m0m1j0_cms/selection.py:57` | `ELECTRON_CUTBASED_MIN = 3` | `= 2` |
| `studies/m0m1j0_cms/selection.py:97` | `NEEDED_BRANCHES` "Muon_mediumId" | `MUON_ID_BRANCH` (new constant = "Muon_looseId") |
| `studies/m0m1j0_cms/selection.py:159,168` | `select_muons` reads/uses mediumId | reads `events[MUON_ID_BRANCH]`, cuts on `looseId`; iso `< MUON_ISO_MAX` (0.15) unchanged |
| `studies/m0m1j0_cms/selection.py:179,184` | `select_electrons` `cutBased >= ELECTRON_CUTBASED_MIN` | unchanged code; constant now 2 |
| `studies/cms_datasets/cluster/run_dataset_on_file.py:201` | driver branch list "Muon_mediumId" | `selection.MUON_ID_BRANCH` |
| `studies/cms_datasets/cluster/run_dataset_on_file.py:203` | driver reads "Electron_cutBased" | unchanged |
| `studies/cms_datasets/cluster/run_dataset_on_file.py:2305-2306` | `selection.select_muons` / `select_electrons` | unchanged (same functions) |
| `studies/cms_datasets/cluster/run_dataset_on_file.py:2320` | diagnostics-only electron mask, `>= selection.ELECTRON_CUTBASED_MIN` | unchanged (already the constant) |
| `studies/cms_datasets/electron_prep/common.py:132-133` | `selection.select_muons` / `select_electrons` | unchanged (same functions) |
| `studies/cms_datasets/tests/test_btag_singleelectron.py:86` | synthetic "Muon_mediumId" column | "Muon_looseId" |

No other CMS file names a muon/electron ID: every muon and electron selection (data and MC; the
MC path runs the same driver with `--is-mc`) goes through `select_muons` / `select_electrons` and
the selection.py constants. `docs/CMS_KNOWN_LIMITATIONS.md` mentions `looseId` only for the
upstream FileParser field-drop issue; the CMS driver does not use FileParser — it reads its
required branches directly and stops if one is missing (`read_events`).

New test `studies/cms_datasets/tests/test_loose_lepton_ids.py` (17 checks): looseId used (and
mediumId not) by `select_muons`, `NEEDED_BRANCHES` and the driver branch list; iso 0.15 kept
(strict `<`); `ELECTRON_CUTBASED_MIN == 2` and cutBased 2/3/4 kept, 0/1 dropped; the driver's
diagnostics mask matches `select_electrons`; jets unchanged (tight ID bit, 0.2489 b-tag).

`docs/CMS_LAYER.md`: added the line "24 Oct 2026, Maryna: loose muon and electron IDs; muon iso
< 0.15 kept". (Its "byte-identical to `de012d2`" check now also differs in the 3 changed files
and the new test, by design.)

Tests (`evidence/local_tests.txt`, Mac, `PYTHONPATH=.`): **all 16 CMS test files + the new one
pass, 0 failures — VERIFIED BY RUNNING.** The 5 skips in `tests/` are the network tests that read
real ROOT files (`RUN_NETWORK_TESTS=1`); they are skipped by design (ROOT reading only in PBS).

## Step 3 — small real-file check — DONE (details: `PRECHECK.md`)

- Jobs `5331447[]` (7 files) and `5331448` (builds + comparison), wipp-home; all exit 0.
  Code: OLD `33d77f5` vs NEW `9588cdb` tarballs from the pinned clone
  `checkouts/fullrun_20261025/precheck_9588cdb`. Work: `work/fullrun_20261025/precheck/`.
- **0 exceptions: every OLD-selected muon/electron is NEW-selected on all 7 files** — VERIFIED BY RUNNING.
- Triggered events, file 0: electrons ×1.49 DoubleMuon, ×1.27 SingleMuon, ×1.13 DoubleEG,
  ×1.58 MuonEG, ×1.12 SingleElectron, ×1.08 both MC; muons ×1.01–1.03 (×2.4 DoubleEG and ×1.4
  SingleElectron on tens of muons). Accepted events: DoubleMuon +1.8 %, SingleMuon +1.4 %,
  DoubleEG +19.7 %, MuonEG +19.7 %, SingleElectron +9.9 %, MC +1.8 % / +1.5 %.
- Overlap removal costs MuonEG 31 → 65 events, DoubleEG 0 → 2, others 0.
- Data build 201 → 214 histograms (none lost); MC summedSM 296 → 302.
- Scripts: `cluster/pbs_precheck.sh`, `cluster/object_compare.py`, `cluster/build_compare.py`,
  `make_precheck_plots.py`; PNGs in `precheck_plots/`; evidence in `evidence/`.

## Step 4 — full run prepared, NOTHING submitted — DONE

### Mappings (job `5331479`, io=1, from clone `step4_67e3f28`; VERIFIED BY RUNNING)

Data, `work/fullrun_20261025/mappings_data/` (copies of the mapping files in `evidence/mappings_data/`):
the lean branch's `gen_full_mapping.py` loops over the four old datasets only, so a minimal
ADDED script, `gen_full_mapping_5.py`, does the same with the five matched5 datasets (same
helpers, same file formats, same "STOP if the portal count differs from the record table").

| dataset | era G record (files) | era H record (files) | total | array |
|---|---|---|---:|---|
| DoubleMuon | 30522 (29) | 30555 (28) | 57 | 0-56 |
| SingleMuon | 30530 (70) | 30563 (82) | 152 | 0-151 |
| DoubleEG | 30521 (47) | 30554 (86) | 133 | 0-132 |
| MuonEG | 30528 (29) | 30561 (19) | 48 | 0-47 |
| SingleElectron | 30529 (71) | 30562 (80) | 151 | 0-150 |
| **total** | | | **541** | (= 7 Oct's 390 + 151 SingleElectron) |

MC, `work/fullrun_20261025/mappings_mc/` (`make_fullrun_mappings.py`, unchanged): 13 records,
**497 files**, every one of the 13 mapping files **byte-identical** to
`work/fullrun_20261017/mappings/` (read-only). 75589 file 98 is in (line 99), as on 17 Oct (the
audit expects exactly that one Σw failure; Matan's 17 Oct option A).

### Launchers (VERIFIED by reading; the production ones were not run as such)

- **Data production `electron_vB/cluster/pbs_matched4.sh` with `POPULATION=matched5`: works
  unchanged.** It reads the 5-column, 0-based mapping that `gen_full_mapping_5.py` writes, and
  passes `--population` to the driver; its fixed 8 GB / 2 h / io=25 fits (the slowest precheck
  file took 432 s). One remark: it does not point `HOME`, `MPLCONFIGDIR` or `XDG_CACHE_HOME`
  away from the home directory, unlike the MC launcher. It was used this way on 7 Oct. Whether
  anything is written to `$HOME` is UNVERIFIED — for the technical lead.
- **MC production `cms_mc_weights_v3/cluster/pbs_mc_pilot.sh`: works unchanged** (1-based
  mapping, `-l mem=6gb,walltime=…,io=25` at qsub, exactly as on 17 Oct).
- **Data delivery launcher `electron_vB/cluster/pbs_delivery.sh` would need a change:** it passes
  no `--datasets`, and the builder's default is the four old datasets, so it would build
  **without SingleElectron**. Not changed. The ADDED `cluster/pbs_post.sh` runs the builder with
  `--datasets DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron` (other options default).
- `electron_vB/check_production_complete.py` checks four datasets only: the ADDED
  `check_production_complete_5.py` runs its `main()` unchanged with the five datasets (tested on a
  synthetic folder: it finds a missing SingleElectron file that the original misses).
- `electron_vB/make_delivery_plots.py` loops over the four old datasets for its per-dataset
  diagnostic plots, so SingleElectron is absent from those (its histogram plots read the delivered
  file and do include it). Not changed.
- `fullrun/audit_production.py` always exits 0 (the verdict is inside its JSON): `pbs_post.sh
  WHAT=mc_gate` turns the verdict into an exit code.
- `rule_check.py` is copied byte-identical from `origin/feature/cms-mc-multiplicity40-20261023`
  `studies/multiplicity40_20261023/` into `studies/fullrun_20261025/rule_check.py` (same depth,
  so its repo-root path still works). It needs an "exact" build next to the default build.

`cluster/pbs_post.sh` (ADDED) was tested stage by stage on the precheck outputs (jobs
`5335417`–`5335424`, `work/fullrun_20261025/posttest/`, evidence in `evidence/posttest/`):
`data_check` stopped with exit 1 as it should (1 file per dataset); a job with `afterok` on it did
**not** run; `data_build` 214 histograms; `data_exact` 608; `data_checks`: rule check R1–R7 all
true, delivery plots written; `mc_gate` read "OK" from the 17 Oct audit (read-only);
`mc_rule_builds` 222 / 1,034 histograms; `mc_rulecheck` R1–R7 all true. VERIFIED BY RUNNING.

### OpenPBS dependency syntax (tested with io=1 dummy jobs, `cluster/pbs_dummy.sh`; `evidence/deptest/`)

| test | result (VERIFIED BY RUNNING) |
|---|---|
| `-W depend=afterok:5331480[].pbs` (array, all subjobs exit 0) | ran after the whole array |
| array depending on array, `-J 0-1 -W depend=afterok:<array>[].pbs` | ran after the whole array |
| `-W depend=afterok:<array>[].pbs`, one subjob exit 1 (twice: 5331483, 5331537) | **RAN anyway** |
| `-W depend=afterany:<array>[].pbs`, one subjob exit 1 | ran |
| `-W depend=afternotok:<array>[].pbs`, one subjob exit 1 | **never ran** (deleted) |
| `-W depend=afterok:<array>[1].pbs` (one subjob) | refused: "illegal -W value" |
| single job exit 1, `afterok:<id>` / `afternotok:<id>` | not run / ran |
| several: `-W depend=afterok:<id1>:<id2>` (single jobs) | works (5335421) |

**So on this cluster `afterok` on an array does NOT protect against failed subjobs.** The
working pattern: `afterany:<array1>[]:<array2>[]:…` to a single check job that exits non-zero
when anything is missing, then `afterok:<check job>` (single job — this works) for every build.
Quote array IDs in zsh: `'<id>[]'`.

## Ready to submit

Pin: **commit `75b399e2dfdacc50affd4e2c78bc865b12f000cc`** on `run/cms-fullrun-20261025` (all
code; later commits only add this study's HANDOFF and evidence files, no code). Run from wipp-home, in bash
(`ssh wipp-home 'bash -s' <<'EOF' … EOF`), after the technical lead's check and Matan's go.

```bash
B=/storage/agrp/berkom/atlas-utilization
CK=$B/checkouts/fullrun_20261025; W=$B/work/fullrun_20261025
C=75b399e2dfdacc50affd4e2c78bc865b12f000cc; R=$CK/repo_75b399e
Q=/opt/pbs/bin/qsub; FIVE="DoubleMuon SingleMuon DoubleEG MuonEG SingleElectron"
MCREC="67993 75589 67801 68187 35669 72752 35631 68847 68073 64895 64839 72676 37728"

# 0. pinned checkout + layout (new directories only)
git clone -q --no-checkout https://github.com/MatanBerko/atlas-utilization.git $R
git -C $R checkout -q $C && test "$(git -C $R rev-parse HEAD)" = $C
mkdir -p $W/data/runs $W/data/evidence $W/logs/post $W/mc/mappings $W/mc/runs $W/mc/evidence
cp $W/mappings_data/*_index.json $W/data/runs/          # what the builder and the check read
cp $W/mappings_mc/mapping_*.txt $W/mc/mappings/

# 1. data production: 5 arrays, 541 files (launcher unchanged; 8gb 2h io=25 inside it)
for ds in $FIVE; do
  n=$(wc -l < $W/mappings_data/${ds}_mapping.txt); mkdir -p $W/data/logs/$ds
  J=$($Q -J 0-$((n-1)) -N fr25_$ds \
      -o "$W/data/logs/$ds/f_^array_index^.out" -e "$W/data/logs/$ds/f_^array_index^.err" \
      -v REPO_DIR=$R,MAPPING_FILE=$W/mappings_data/${ds}_mapping.txt,OUT_BASE=$W/data/runs,POPULATION=matched5 \
      $R/studies/cms_datasets/electron_vB/cluster/pbs_matched4.sh)
  echo "$ds $J $n" | tee -a $W/data/jobids.txt
done

# 2. MC production: 13 arrays, 497 files (exactly the 17 Oct submit_production.sh loop)
for rid in $MCREC; do
  n=$(wc -l < $W/mc/mappings/mapping_$rid.txt); wt=02:00:00; case $rid in 68187|68073) wt=03:00:00;; esac
  mkdir -p $W/mc/logs/$rid
  J=$($Q -J 1-$n -N mcfull_$rid -l mem=6gb,walltime=$wt,io=25 \
      -o "$W/mc/logs/$rid/f_^array_index^.out" -e "$W/mc/logs/$rid/f_^array_index^.err" \
      -v WORK_DIR=$W/mc,REPO_DIR=$R,OUTPUT_BASE=$W/mc/runs,MAPPING_FILE=$W/mc/mappings/mapping_$rid.txt \
      $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh)
  echo "$rid $J $n $wt" | tee -a $W/mc/jobids.txt     # the format audit_production.py reads
done

# 3. post-production chain (afterany on arrays -> a gate job -> afterok on the gate)
DATA_ARR=$(awk '{printf ":%s", $2}' $W/data/jobids.txt); MC_ARR=$(awk '{printf ":%s", $2}' $W/mc/jobids.txt)
P=$R/studies/fullrun_20261025/cluster/pbs_post.sh
post() { local what=$1 res=$2; shift 2; $Q -N fr25_$what -l $res \
  -o $W/logs/post/$what.out -e $W/logs/post/$what.err -v WORK_DIR=$W,REPO_DIR=$R,WHAT=$what "$@" $P; }
F=$R/studies/cms_mc_weights_v3/fullrun/pbs_fullrun.sh
mcpost() { local what=$1 res=$2; shift 2; $Q -l $res -o $W/logs/post/mc_$what.out -e $W/logs/post/mc_$what.err \
  -v WORK_DIR=$W/mc,REPO_DIR=$R,WHAT=$what "$@" $F; }
# data: completeness (5 datasets) -> default build + exact build -> rule check + delivery plots
DC=$(post data_check select=1:ncpus=1:mem=4gb,walltime=01:00:00,io=25 -W depend=afterany$DATA_ARR)
DB=$(post data_build select=1:ncpus=1:mem=32gb,walltime=06:00:00,io=25 -W depend=afterok:$DC)
DE=$(post data_exact select=1:ncpus=1:mem=32gb,walltime=06:00:00,io=25 -W depend=afterok:$DC)
DK=$(post data_checks select=1:ncpus=1:mem=16gb,walltime=02:00:00,io=25 -W depend=afterok:$DB:$DE)
# MC: audit -> gate on its verdict -> build (defaults, 64gb 8h) -> sanity; rule-check builds
MA=$(mcpost audit select=1:ncpus=1:mem=4gb,walltime=01:00:00,io=25 -W depend=afterany$MC_ARR)
MG=$(post mc_gate select=1:ncpus=1:mem=1gb,walltime=00:10:00,io=1 -W depend=afterok:$MA)
MB=$(mcpost build select=1:ncpus=1:mem=64gb,walltime=08:00:00,io=25 -W depend=afterok:$MG)
MS=$(mcpost sanity select=1:ncpus=1:mem=16gb,walltime=02:00:00,io=25 -W depend=afterok:$MB)
MR=$(post mc_rule_builds select=1:ncpus=1:mem=32gb,walltime=04:00:00,io=25 -W depend=afterok:$MG)
MK=$(post mc_rulecheck select=1:ncpus=1:mem=16gb,walltime=02:00:00,io=25 -W depend=afterok:$MR)
printf "%s\n" "data_check $DC" "data_build $DB" "data_exact $DE" "data_checks $DK" \
  "mc_audit $MA" "mc_gate $MG" "mc_build $MB" "mc_sanity $MS" "mc_rule_builds $MR" "mc_rulecheck $MK" | tee $W/post_jobids.txt
```

What each step runs (for reading, the scripts are the source):
- audit, data: `python studies/fullrun_20261025/check_production_complete_5.py --runs-root $W/data/runs --out $W/data/evidence/production_complete.json` (exit 1 if anything missing or incomplete).
- audit, MC: `pbs_fullrun.sh WHAT=audit` = `python studies/cms_mc_weights_v3/fullrun/audit_production.py --work $W/mc --out $W/mc/evidence/production_audit.json`; gate = verdict "OK" (expects exactly one Σw failure, 75589 file 98).
- data build: `python studies/cms_datasets/deliver/build_four_dataset_delivery.py --runs-dir $W/data/runs --datasets DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron --out-dir $W/data/deliver/default --out-prefix fullrun` (defaults: rare4, #40 rule, ≥100 events per final state). The exact build adds `--multiplicity-rule exact` → `$W/data/deliver/exact` (rule-check input only, not a delivery).
- MC build: `pbs_fullrun.sh WHAT=build` = `build_mc_delivery.py --runs-dir $W/mc/runs --out-dir $W/mc/build_default --out-prefix fullrun --scratch-dir $W/mc/scratch_default --keep-scratch` (all physics options default), 64 GB, 8 h.
- checks: `rule_check.py --kind data` (exact vs default data build) and `--kind mc` (record 67801, per-sample, default vs exact — the 23 Oct method); `make_delivery_plots.py --runs-root $W/data/runs --delivery-dir $W/data/deliver/default --out-dir $W/data/evidence/plots --out-json …`; `pbs_fullrun.sh WHAT=sanity` = `sanity_and_plots.py --build-dir $W/mc/build_default --prefix fullrun --audit $W/mc/evidence/production_audit.json --out-dir $W/mc/evidence/plots`.
- Memory/walltime of the post jobs are proposals (the data build launcher uses 32 GB / 6 h; the MC build 64 GB / 8 h as asked). The `reproduce` stage of `pbs_fullrun.sh` is not in the chain (it compares to the 10 Oct pilot, which used the old IDs, so differences are expected).

### File-count projection (quota now **73,784**, VERIFIED BY RUNNING `lfs quota`, 25 Oct 07:20)

| item | basis | files |
|---|---|---:|
| data production, 541 jobs | measured: 9 per job folder + 4 SQLite `-shm`/`-wal` the builder leaves in each folder + 2 logs = 15 | 8,115 |
| data mappings, builds, evidence, logs | precheck/posttest outputs: ~6 per build, plots, JSONs | ~100 |
| MC production, 497 jobs | 17 Oct: 6,014 (runs 4,473 + logs 1,002 + …) | 6,014 |
| MC build and post (incl. kept scratch 1,488) | 17 Oct: ~2,240 | 2,240 |
| MC rule-check builds | posttest: ~10 (scratch on the node) | ~10 |
| pinned clone `repo_75b399e` | measured clones ~170 | ~170 |
| **total new** | | **~16,650** |
| **projected after the full run** | 73,784 + 16,650 | **~90,400** — under 125,000 |

(7 Oct scaling instead: 4,694 × 541/390 = 6,511 for data, giving ~88,800. Either way well under
125,000. UNVERIFIED until the run.) If anything, the full SingleElectron is the bigger unknown:
its file 0 was small (113 k events), the other 150 may be larger, but the file count does not
depend on size.

Today this task added 1,456 files (72,328 → 73,784): three pinned clones (~500), the precheck
(~300), the post-launcher test and the mappings.

Local repo switched back to `master`. STOPPED: next is the technical lead's check, then the
separate submit prompt.

## Submitted (25 Oct) — PARTLY: 17 of 18 production arrays; record 37728 and the 10 post jobs NOT submitted

**Status: 1,030 of 1,038 file jobs are submitted and running/queued. The submission STOPPED at
the 18th array because of a cluster limit. Nothing was retried or cancelled.** Evidence:
`evidence/submitted_20261025/` (job lists, the submit script exactly as executed, its output, the
HOME test).

- Host: wipp-home (wipp-an1). `ssh wipp-campus` failed once ("No route to host").
- Pinned clone `checkouts/fullrun_20261025/repo_75b399e`, HEAD `75b399e2dfdacc50affd4e2c78bc865b12f000cc` — VERIFIED BY RUNNING.
- Preflight (VERIFIED BY RUNNING): origin branch head `da3b93d` contains `75b399e`; the commits
  after it touch only `HANDOFF.md` and `evidence/`; upstream/master still `29291ae`; no
  fr25_*/mcfull_* job was queued; none of the three jobids files existed; mappings 57/152/133/48/151
  (541) data lines and 13 MC files with 497 lines.
- **File quota before submitting: 73,784** (17:07, `lfs quota`); 73,794 just before the first
  qsub; **75,942** at 17:33. VERIFIED BY RUNNING.

### HOME test (step 1)

Job `5340532` (io=1, 1 min) with `-v HOME=$W/jobhome,MPLCONFIGDIR=$W/jobhome/mpl,XDG_CACHE_HOME=$W/jobhome/cache`
printed `HOME=/srv01/agrp/berkom` (**PBS overrides HOME**) while MPLCONFIGDIR and
XDG_CACHE_HOME did arrive. Per the instruction for this case, **the data arrays were submitted
unchanged, exactly as on 7 Oct (no HOME redirect).** A listing of the home folder before the
submission is in `work/fullrun_20261025/data/evidence/home_before.txt` (kept on the cluster only,
not in git: it lists private file names). `$W/jobhome/` (empty) was created for the test.

### What was submitted (17:07:48, `evidence/submitted_20261025/submit_output.txt`)

The "Ready to submit" block was run verbatim (extracted from this file by script), with a
no-double-submit guard and `set -euo pipefail` in front (`submit_run_as_executed.sh`).

| data array | job | files |
|---|---|---:|
| DoubleMuon | `5340544[]` | 57 |
| SingleMuon | `5340545[]` | 152 |
| DoubleEG | `5340546[]` | 133 |
| MuonEG | `5340547[]` | 48 |
| SingleElectron | `5340548[]` | 151 |

| MC record | job | files | walltime |
|---|---|---:|---|
| 67993 | `5340549[]` | 138 | 02:00:00 |
| 75589 | `5340550[]` | 99 | 02:00:00 |
| 67801 | `5340551[]` | 49 | 02:00:00 |
| 68187 | `5340552[]` | 42 | 03:00:00 |
| 35669 | `5340553[]` | 41 | 02:00:00 |
| 72752 | `5340554[]` | 31 | 02:00:00 |
| 35631 | `5340555[]` | 25 | 02:00:00 |
| 68847 | `5340556[]` | 24 | 02:00:00 |
| 68073 | `5340557[]` | 12 | 03:00:00 |
| 64895 | `5340558[]` | 11 | 02:00:00 |
| 64839 | `5340559[]` | 10 | 02:00:00 |
| 72676 | `5340560[]` | 7 | 02:00:00 |
| **37728** | **NOT SUBMITTED** | 8 | 02:00:00 |

**The failure:** the qsub of record 37728 answered
`qsub: would exceed complex's per-user limit of jobs in 'Q' state`. The server has
`queued_jobs_threshold = [u:PBS_GENERIC=1000]`: at most 1,000 queued subjobs per user. At that
moment 998 were queued and 32 running (541 + 489 = 1,030 submitted); 8 more would pass 1,000.
`set -e` stopped the script there, so `$W/post_jobids.txt` does not exist and **none of the 10
post jobs (data_check … mc_rulecheck) were submitted.** `$W/mc/logs/37728/` exists (empty).
Second limit seen: `max_run_res.io = [u:PBS_GENERIC=800]`, so with io=25 at most **32 jobs of
this user run at once**; the scheduler is working through the arrays in submission order.
Both limits are VERIFIED BY RUNNING (`qmgr -c "list server"`, qstat counts).

### First results (VERIFIED BY RUNNING, 17:33)

- All 57 DoubleMuon subjobs finished: 57 logs with `Exit status: 0`, 0 tracebacks, 57
  `job_metadata.json`. `5340544[0]` Exit_status 0 (3:01 wall), `.out` ends
  `[DoubleMuon] wrote …/data/runs/DoubleMuon/job_0/dataset_shard_inclusive.sqlite, …, and job_metadata.json … (179.0s elapsed)` / `[0] done Sun Oct 25 05:11:07 PM IST 2026`;
  `5340544[7]` Exit_status 0, `(31.7s elapsed)` / `[7] done …05:08:41 PM`.
- SingleMuon: 71 finished, all `Exit status: 0`, 0 tracebacks; 32 running, 52 queued.
- All MC arrays: queued, none started yet (they are behind the data arrays) — "queued, none
  finished yet" for MC.

### What Prompt B must do

0. Read this section. Do not resubmit anything that is in the two job lists above.
1. **The missing pieces need a decision by the technical lead / Matan first** (not done here
   because this task said STOP on a qsub failure):
   - (a) record 37728: submit it ONCE, exactly as the MC loop line for that record
     (`-J 1-8 -N mcfull_37728 -l mem=6gb,walltime=02:00:00,io=25`, same -o/-e/-v), when the
     user's queued count is below 992, and append `37728 <job> 8 02:00:00` to `$W/mc/jobids.txt`
     (the audit reads that file and would otherwise not expect 37728 at all);
   - (b) the post chain: the written block makes `data_check` and `mc_audit` depend
     (`afterany`) on the array IDs. If the arrays have already finished, it is UNVERIFIED
     whether this PBS accepts a dependency on a finished job. Options: submit the chain as
     written while the arrays are still in the queue; or, once they have all finished, submit the
     same 10 jobs with the two `-W depend=afterany…` arguments removed (the gates inside
     data_check / mc_gate still stop the builds if anything is missing). Either is a deviation
     from the written block only in timing / that one argument; the lead should pick.
2. Still running → report progress (per array: finished / running / queued, any non-zero exit
   or traceback) and stop.
3. All production finished: run (or let the chain run) data_check and the MC audit + gate.
   If data_check or mc_gate fails → list the failed files, resubmit each failed file ONCE
   (data: pbs_matched4.sh as a one-file array or with the mapping line; MC: pbs_mc_pilot.sh with
   `PILOT_ARRAY_INDEX`), then a NEW gate → build → checks chain (new output names; never
   overwrite). The expected MC Σw failure 75589 file 98 is not a failure.
4. All OK → verify the builds and checks (rule checks R1–R7, sanity report, plots) and prepare
   the delivery (no upload, no message without Matan).
5. Home folder: compare `ls -la --time-style=full-iso` of `~`, `~/.cache`, `~/.config` (and
   `~/.local`, `~/.matplotlib` if they appear) with `$W/data/evidence/home_before.txt`, to check
   whether the data jobs (HOME not redirected) wrote anything there.
