# HANDOFF — MC-port validation, 14 Oct 2026

Checks that `feature/cms-mc-on-master-20261014` (the MC weighting work ported
onto the rebuilt master, with no upstream file modified) changes nothing:
(A) data outputs identical to this morning's rebuild validation, and
(B) MC outputs identical to the 10 Oct pilot.

## Commits

| what | commit |
|---|---|
| NEW: `feature/cms-mc-on-master-20261014` | `5906dcf8591f7b9bd83a4c36e41cc03b59b9f39a` |
| OLD MC: `origin/feature/cms-mc-weights-v3` | `68ab2817cd3afc84d9d07587dcf403badd344b4a` |
| 10 Oct pilot production (reference) | `cbfb837` (run_dataset_on_file.py and services/ identical to `68ab281`) |
| 10 Oct pilot builds (reference) | `08bc459` (builder identical to `68ab281`) |
| data reference: rebuild validation NEW side | `6a055e8` (this morning) |

## Cluster directories (all NEW)

```
B=/storage/agrp/berkom/atlas-utilization
$B/checkouts/mcport_20261014/new_5906dcf/      pinned NEW checkout
$B/checkouts/mcport_20261014/oldmc_68ab281/    pinned OLD-MC checkout (builder only)
$B/work/mcport_20261014/
  inputs/          data_mapping.txt + <Dataset>_index.json (copied from the
                   rebuild validation inputs), mc_mapping.txt, compare.py,
                   mc_compare.py, make_plots.py
  data/            A: NEW per-file data outputs <Dataset>/job_<0|1>/
  data_delivery/   A: NEW 8-file mini delivery
  mc_new/          B: WORK_DIR for the NEW side: runs/record<ID>/job_<fi>/,
                   build_default/, scratch_default/
  mc_old/          B: WORK_DIR for the OLD builder: runs/ = COPIES of the 6
                   pilot job directories, build_default/, scratch_default/
  logs/{data,data_delivery,mc,build}/
  results/
```

Read-only references (never written; shards are copied before opening):
`$B/work/rebuild_validation_20261014/{new,delivery_new}/` and
`$B/work/cms_mc_v3_pilot_20261011/runs/record{67801,35669,37728}/job_{0,1}/`.

## The files

A (data): the same 8 files as the rebuild validation:
DoubleMuon 30522/0-1, SingleMuon 30530/0-1, DoubleEG 30521/0-1, MuonEG 30528/0-1.

B (MC): the first 2 pilot files of each pilot process (lines 1-2 of each
pilot mapping file): 67801 TTTo2L2Nu files 0,1; 35669 DYJetsToLL_M-50 NLO
files 0,1; 37728 GluGluHToZZTo4L_M125 files 0,1.

## Commands

```bash
W=$B/work/mcport_20261014; R=$B/checkouts/mcport_20261014/new_5906dcf; RO=$B/checkouts/mcport_20261014/oldmc_68ab281

# A1. data per-file (same launcher/options as 7 Oct and the rebuild validation)
cd $R && /opt/pbs/bin/qsub -J 0-7 -N mp_data -l walltime=03:00:00 \
  -o $W/logs/data/f_^array_index^.out -e $W/logs/data/f_^array_index^.err \
  -v REPO_DIR=$R,MAPPING_FILE=$W/inputs/data_mapping.txt,OUT_BASE=$W/data,POPULATION=matched4 \
  studies/cms_datasets/electron_vB/cluster/pbs_matched4.sh
# A2. data mini delivery (after A1)
cd $R && /opt/pbs/bin/qsub -N mp_ddel -o $W/logs/data_delivery/d.out -e $W/logs/data_delivery/d.err \
  -v REPO_DIR=$R,RUNS_DIR=$W/data,OUT_DIR=$W/data_delivery,OUT_PREFIX=rv8_four_dataset \
  studies/cms_datasets/electron_vB/cluster/pbs_delivery.sh

# B1. MC per-file, pilot options (--is-mc --dataset-label MC --population matched4)
cd $R && /opt/pbs/bin/qsub -J 1-6 -N mp_mc -l mem=6gb,walltime=02:00:00,io=25 \
  -o $W/logs/mc/f_^array_index^.out -e $W/logs/mc/f_^array_index^.err \
  -v WORK_DIR=$W/mc_new,REPO_DIR=$R,OUTPUT_BASE=$W/mc_new/runs,MAPPING_FILE=$W/inputs/mc_mapping.txt \
  studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh
# B2. MC builds, pilot 3a options (WHAT=build_default), each side its own checkout (after B1)
for S in new:$R old:$RO; do /opt/pbs/bin/qsub -N mp_b_${S%%:*} -l mem=64gb,walltime=08:00:00 \
  -o $W/logs/build/${S%%:*}.out -e $W/logs/build/${S%%:*}.err \
  -v WORK_DIR=$W/mc_${S%%:*},REPO_DIR=${S#*:},WHAT=build_default \
  ${S#*:}/studies/cms_mc_weights_v3/cluster/pbs_pilot_build.sh; done
```

## Jobs

| PBS id | array | what | status |
|---|---|---|---|
| `5223495[]` | 0-7 | A1 data per-file, NEW checkout | submitted 14 Oct 2026 |
| `5223496[]` | 1-6 | B1 MC per-file, NEW checkout | submitted 14 Oct 2026 |
| — | — | A2 data mini delivery; B2 two MC builds | submitted after A1 / B1 finish |

Check: `ssh wipp-campus '/opt/pbs/bin/qstat -u berkom -t'`.

### How to resume

1. Wait for both arrays (each `.out` ends with `done` / `finished`).
2. Submit A2 and B2 (commands above).
3. Compare (analysis node, `nice -n 10`, `PY=$B/envs/atlas-pipeline/bin/python`, cwd `$W/inputs`):
   - `$PY compare.py runs --a $B/work/rebuild_validation_20261014/new --b $W/data --out $W/results/data_runs_rebuild_vs_mcport.json`
   - `$PY compare.py delivery --a $B/work/rebuild_validation_20261014/delivery_new --b $W/data_delivery --a-runs $B/work/rebuild_validation_20261014/new --b-runs $W/data --prefix rv8_four_dataset --out $W/results/data_delivery_rebuild_vs_mcport.json`
   - `$PY mc_compare.py runs --a $W/mc_old/runs --b $W/mc_new/runs --jobs 67801:0,67801:1,35669:0,35669:1,37728:0,37728:1 --out $W/results/mc_runs_pilot_vs_new.json`
   - `$PY mc_compare.py builds --a $W/mc_old/build_default --b $W/mc_new/build_default --a-runs $W/mc_old/runs --b-runs $W/mc_new/runs --a-scratch $W/mc_old/scratch_default --b-scratch $W/mc_new/scratch_default --out $W/results/mc_builds_old_vs_new.json`
   - D3 data-neutrality on real shards: `$PY $R/studies/cms_mc_weights_v3/cluster/check_prune_regex_data_neutral.py --runs-dir $B/work/rebuild_validation_20261014/new --mapping $W/inputs/data_mapping.txt --scratch $W/prune_scratch --out $W/results/prune_regex_data_neutral.json`
4. Plots, then archive the two checkouts (tar.gz, verify, remove only the uncompressed dirs).

## File count (`lfs quota -u berkom /storage`)

| when | files |
|---|---:|
| before this task | 109,202 |
| after checkouts + inputs + pilot copies | 111,378 |
