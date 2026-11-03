#!/bin/bash
# ZZTo2L2Nu quick check (3 Nov 2026): one PBS job reading the 5 input files of lhe_mass_check.py.
# Submit from the pinned checkout, e.g.
#   qsub -l select=1:ncpus=1:mem=4gb,walltime=02:00:00,io=25 -o "$W/logs/zzcheck.out" -e "$W/logs/zzcheck.err" \
#        -v REPO_DIR=$R,WORK_DIR=$W $R/studies/mc_expansion_plan_20261026/zz2l2nu_check/pbs_lhe_mass_check.sh
#PBS -N zzcheck
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail
REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
WORK_DIR="${WORK_DIR:?WORK_DIR not set}"
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python
export OMP_NUM_THREADS=1
export MPLCONFIGDIR="${WORK_DIR}/.mplconfig"
export XDG_CACHE_HOME="${WORK_DIR}/.cache"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$WORK_DIR/out"
cd "$REPO_DIR"
echo "Job $PBS_JOBID on $(hostname) at $(date)"
echo "commit=$(git rev-parse HEAD)"
PYTHONPATH="$REPO_DIR" /usr/bin/time -v "$PY" -u studies/mc_expansion_plan_20261026/zz2l2nu_check/lhe_mass_check.py \
    run --out "$WORK_DIR/out/lhe_mass_check.json"
echo "done $(date)"
