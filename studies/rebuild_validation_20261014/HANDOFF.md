# HANDOFF — rebuild validation, 14 Oct 2026

Old code vs new code on the same 8 files. Everything needed to resume
without re-deriving anything.

## Commits

| side | branch | commit |
|---|---|---|
| OLD | `archive/master-2026-10-14` (= fork master) | `ba89791b5fe0167070c7e1bb2f3c231802f064fd` |
| NEW | `rebuild/master-2026-10-14` | `6a055e88dacaf669322926df78f82afa62a91cf6` |
| 7 Oct production (reference, read-only) | — | `06778c9b21ae9243ec49e1455ed055edfe608291` |

## Cluster directories (all NEW, created 14 Oct 2026)

```
B=/storage/agrp/berkom/atlas-utilization
$B/checkouts/rebuild_validation_20261014/old_ba89791/   pinned checkout, OLD
$B/checkouts/rebuild_validation_20261014/new_6a055e8/   pinned checkout, NEW
$B/work/rebuild_validation_20261014/
  inputs/    mapping.txt (8 lines), files.json (URLs), compare.py (copy of this folder's)
  old/       OLD per-file outputs <Dataset>/job_<0|1>/ + <Dataset>_index.json
  new/       NEW per-file outputs, same layout
  delivery_old/, delivery_new/   mini deliveries (8 files each side)
  logs/{old,new,delivery}/
  results/   comparison JSONs and plots
```

Read-only reference: `$B/output/cms_datasets/runs_matched4_full_20261007/`
(the 7 Oct production; never written to. Shard files are copied to a temp
dir before they are opened).

## The 8 files

First 2 files (job 0 and job 1) of each dataset's 7 Oct production list,
all era G:

| dataset | record | file index | job |
|---|---:|---:|---:|
| DoubleMuon | 30522 | 0, 1 | 0, 1 |
| SingleMuon | 30530 | 0, 1 | 0, 1 |
| DoubleEG | 30521 | 0, 1 | 0, 1 |
| MuonEG | 30528 | 0, 1 | 0, 1 |

URLs: `inputs/files.json`.

## Commands (identical for both sides except REPO_DIR and OUT_BASE)

Same launcher, population and options as the 7 Oct Step C (logs show
`population=matched4`, empty `extra_args`, `walltime=03:00:00`):

```bash
W=$B/work/rebuild_validation_20261014
for S in old:old_ba89791 new:new_6a055e8; do
  SIDE=${S%%:*}; R=$B/checkouts/rebuild_validation_20261014/${S##*:}
  cd $R && /opt/pbs/bin/qsub -J 0-7 -N rv_$SIDE -l walltime=03:00:00 \
    -o $W/logs/$SIDE/f_^array_index^.out -e $W/logs/$SIDE/f_^array_index^.err \
    -v REPO_DIR=$R,MAPPING_FILE=$W/inputs/mapping.txt,OUT_BASE=$W/$SIDE,POPULATION=matched4 \
    studies/cms_datasets/electron_vB/cluster/pbs_matched4.sh
done
```

Mini delivery, each side with its own checkout, no extra flags (as on 7 Oct):

```bash
cd $R && /opt/pbs/bin/qsub -N rv_d_$SIDE -o $W/logs/delivery/$SIDE.out -e $W/logs/delivery/$SIDE.err \
  -v REPO_DIR=$R,RUNS_DIR=$W/$SIDE,OUT_DIR=$W/delivery_$SIDE,OUT_PREFIX=rv8_four_dataset \
  studies/cms_datasets/electron_vB/cluster/pbs_delivery.sh
```

Comparisons (analysis node, `nice`):

```bash
PY=$B/envs/atlas-pipeline/bin/python
nice -n 10 $PY $W/inputs/compare.py runs --a $W/old --b $W/new --out $W/results/runs_old_vs_new.json
nice -n 10 $PY $W/inputs/compare.py runs --a $B/output/cms_datasets/runs_matched4_full_20261007 --b $W/new --out $W/results/runs_7oct_vs_new.json
nice -n 10 $PY $W/inputs/compare.py delivery --a $W/delivery_old --b $W/delivery_new \
  --a-runs $W/old --b-runs $W/new --prefix rv8_four_dataset --out $W/results/delivery_old_vs_new.json
```

## Jobs

| PBS id | array | what | status |
|---|---|---|---|
| `5223392[]` | 0-7 | OLD per-file production (`old_ba89791`) | submitted 14 Oct 2026 |
| `5223393[]` | 0-7 | NEW per-file production (`new_6a055e8`) | submitted 14 Oct 2026 |
| — | — | mini deliveries `rv_d_old` / `rv_d_new` | submitted after both arrays finish |

Check: `ssh wipp-campus '/opt/pbs/bin/qstat -u berkom -t'`; logs in `$W/logs/{old,new}/f_<i>.out`.

### How to resume

1. Wait for both arrays; each subjob ends with `[<i>] done` in its `.out`.
2. Submit the two mini deliveries (command above).
3. Run the three comparisons, then plots (`make_plots.py`, this folder).
4. Archive the two checkouts: `tar czf` each inside
   `$B/checkouts/rebuild_validation_20261014/`, verify with `tar tzf`,
   then remove only the two uncompressed checkout directories.

## File count (`lfs quota -u berkom /storage`)

| when | files |
|---|---:|
| before this task | 108,944 |
| after checkouts + inputs | 110,940 |
