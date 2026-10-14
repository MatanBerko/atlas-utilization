# Running the CMS production and delivery from the rebuilt master

How to reproduce the 7 Oct 2026 four-dataset delivery (DoubleMuon,
SingleMuon, DoubleEG, MuonEG; Run2016G+H; 390 files) from this branch. The
settings below are the ones the 7 Oct production actually used: the job logs
show `population=matched4` and empty `extra_args` for every Step C job, and
the delivery build ran with no extra flags. The physics settings (DoubleEG
threshold mode `both`, e–μ overlap removal at dR < 0.12, debug dump off) are
the code defaults, so no options are needed.

Background, numbers and limitations: `electron_vB/HANDOFF.md`,
`electron_vB/REPORT_production.md`, `electron_vB/DELIVERY_NOTES.md`. What the
CMS layer consists of: `docs/CMS_LAYER.md`.

## Cluster conventions (Weizmann)

- Login node: `ssh wipp-campus` (or `wipp-home`).
- `qsub`/`qstat` are in `/opt/pbs/bin`. A non-interactive ssh does not
  put them on `PATH`, so use the full path or `zsh -l -c "..."`.
- Queue `N`, `#PBS -m n`, logs never in `$HOME`.
- Python env: `/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline`
  (the PBS scripts use it directly).
- Watch the file quota: `lfs quota -u berkom /storage` (150,000-file soft
  limit). One full production writes about 390 × 11 files.

## 0. A checkout pinned to one commit

```bash
C=<commit>; B=/storage/agrp/berkom/atlas-utilization
git clone --no-checkout https://github.com/MatanBerko/atlas-utilization.git $B/checkouts/<dated_dir>/repo
cd $B/checkouts/<dated_dir>/repo && git fetch origin $C && git checkout --detach $C
R=$PWD
PY=$B/envs/atlas-pipeline/bin/python
```

## 1. File lists (Step C input)

```bash
RUNS=$B/output/cms_datasets/runs_matched4_full_<date>     # NEW directory
$PY studies/cms_datasets/electron_vB/gen_full_mapping.py --out-dir $RUNS
```

This writes `<Dataset>_mapping.txt`, `<Dataset>_index.json` and
`full_files.json`. It refuses to continue unless the portal file counts are
57 / 152 / 133 / 48.

## 2. Per-file production (Step C), one array per dataset

```bash
L=$B/logs/<dated_dir>; mkdir -p $L/DoubleMuon $L/SingleMuon $L/DoubleEG $L/MuonEG
for D in DoubleMuon:0-56 SingleMuon:0-151 DoubleEG:0-132 MuonEG:0-47; do
  N=${D%%:*}; J=${D##*:}
  /opt/pbs/bin/qsub -J $J -N c_$N -l walltime=03:00:00 \
    -o $L/$N/f_^array_index^.out -e $L/$N/f_^array_index^.err \
    -v REPO_DIR=$R,MAPPING_FILE=$RUNS/${N}_mapping.txt,OUT_BASE=$RUNS,POPULATION=matched4 \
    studies/cms_datasets/electron_vB/cluster/pbs_matched4.sh
done
```

`EXTRA_ARGS` is left unset (empty), as on 7 Oct. Each job writes
`$RUNS/<Dataset>/job_<N>/` with `job_metadata.json` and the shard files.

Completeness check (Step C3):

```bash
$PY studies/cms_datasets/electron_vB/check_production_complete.py --help
```

## 3. Delivery build (Step D1)

```bash
OUT=$B/output/cms_datasets/deliver/<NEW dated dir>
/opt/pbs/bin/qsub -N d1 -o $L/delivery.out -e $L/delivery.err \
  -v REPO_DIR=$R,RUNS_DIR=$RUNS,OUT_DIR=$OUT,OUT_PREFIX=<prefix> \
  studies/cms_datasets/electron_vB/cluster/pbs_delivery.sh
```

With no extra flags, `build_four_dataset_delivery.py` (default
`--version rare4`) applies the delivery rules: upstream-exact names ending in
`_width_10.0`, no per-histogram minimum, no filled-bin cut, and the
≥100-events-per-final-state rule applied once over the combined shards. The
7 Oct prefix was `four_dataset_matched_vB_upstreamnames_w10p0_dr012`.

## 4. Checks and plots (Steps D2–D4)

```bash
$PY studies/cms_datasets/electron_vB/verify_delivery.py --help
$PY studies/cms_datasets/electron_vB/make_delivery_plots.py --help
```

## 5. Tests (no cluster needed)

```bash
python studies/cms_datasets/tests/test_width_suffix.py
python studies/cms_datasets/tests/test_upstream_names.py
python studies/cms_datasets/tests/test_exact_jet_labels.py
python studies/cms_datasets/tests/test_electron_datasets.py \
    --pilot-final-states studies/cms_datasets/electron_vB/evidence/pilot_final_states.json
python -m unittest tests.test_validated_runs
```

Known results on this branch (identical to the old master `ba89791` for the
four script tests): see `docs/CMS_LAYER.md`, "Tests".
`test_exact_jet_labels.py` and one note-check in `test_electron_datasets.py`
pin the old one-digit label reading that upstream PR #34 fixed, so they
report failures on both the old and the new master.
