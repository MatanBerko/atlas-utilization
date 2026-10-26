#!/bin/bash
# MC expansion plan (26 Oct 2026): probe file 0 of each planned sample, one PBS array
# subjob per sample (index = position in plan_samples.PROBE). Read-only on the inputs;
# writes only probe_<recid>.json into OUT_DIR. Submit from the pinned checkout with e.g.
#   qsub -J 0-29 -l select=1:ncpus=1:mem=4gb,walltime=01:00:00,io=25 \
#        -o "$W/logs/p_^array_index^.out" -e "$W/logs/p_^array_index^.err" \
#        -v REPO_DIR=$R,WORK_DIR=$W,OUT_DIR=$W/probe $R/studies/mc_expansion_plan_20261026/cluster/pbs_probe.sh
#PBS -N mcplan_probe
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
WORK_DIR="${WORK_DIR:?WORK_DIR not set}"
OUT_DIR="${OUT_DIR:?OUT_DIR not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"

export OMP_NUM_THREADS=1
export MPLCONFIGDIR="${WORK_DIR}/.mplconfig"
export XDG_CACHE_HOME="${WORK_DIR}/.cache"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$OUT_DIR"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

echo "Job $PBS_JOBID (array index $PBS_ARRAY_INDEX) on $(hostname) at $(date)"
echo "commit=$(git rev-parse HEAD)"
/usr/bin/time -v python -u studies/mc_expansion_plan_20261026/probe_sample.py \
    --index "$PBS_ARRAY_INDEX" --out-dir "$OUT_DIR"
echo "[$PBS_ARRAY_INDEX] done $(date)"
