#!/bin/bash
# Part C: the single-file MC smoke test -- ONE file of record 37728
# (GluGluHToZZTo4L_M125) through --is-mc, end to end.
#
# Not an array: one file, one job. Anything larger needs Matan's approval.
#PBS -N mcv3_smoke
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=8gb
#PBS -l walltime=02:00:00
#PBS -l io=25

set -euo pipefail

WORK_DIR="${WORK_DIR:?WORK_DIR not set}"
REPO_DIR="${REPO_DIR:-${WORK_DIR}/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
RECORD_ID="${RECORD_ID:-37728}"
FILE_INDEX="${FILE_INDEX:-0}"
OUTPUT_BASE="${OUTPUT_BASE:-${WORK_DIR}/mc_smoke}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export MPLCONFIGDIR="${WORK_DIR}/.mplconfig"
export XDG_CACHE_HOME="${WORK_DIR}/.cache"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/record${RECORD_ID}/job_${FILE_INDEX}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID on $(hostname) at $(date)"
echo "commit=$(git rev-parse HEAD)"
echo "SMOKE TEST: record=$RECORD_ID file_index=$FILE_INDEX out=$JOB_OUTPUT_DIR"

/usr/bin/time -v python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
    --is-mc \
    --dataset-label MC \
    --record-id "$RECORD_ID" \
    --file-index "$FILE_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR" \
    --population matched4

echo "Job $PBS_JOBID finished at $(date)"
