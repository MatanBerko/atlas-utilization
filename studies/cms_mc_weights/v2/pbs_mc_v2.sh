#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_mc_v2.sh -- one PBS array job PER INPUT FILE of a single MC record,
# for ONE dataset label (DoubleMuon or SingleMuon), --population matched
# --is-mc. PBS_ARRAY_INDEX used directly as the 0-based file-index.
# ---------------------------------------------------------------------------
#PBS -N mc_v2
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=5gb
#PBS -l walltime=02:00:00
#PBS -l io=30

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/cms_mc_v2/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"

: "${RECORD_ID:?RECORD_ID not set}"
: "${DATASET_LABEL:?DATASET_LABEL not set}"
: "${OUTPUT_BASE:?OUTPUT_BASE not set}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

mkdir -p "${TMPDIR:-/tmp}"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/${DATASET_LABEL}/job_${JOB_INDEX}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "record=$RECORD_ID dataset_label=$DATASET_LABEL file-index=$JOB_INDEX output-dir=$JOB_OUTPUT_DIR"

python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
    --dataset-label "$DATASET_LABEL" \
    --record-id "$RECORD_ID" \
    --file-index "$JOB_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR" \
    --population matched --is-mc

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
