#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_notrigger.sh (ttbar-count-vs-atlas study, Steps 4 and 5)
#
# One PBS array element per INPUT FILE of a single MC record, run with
# --population notrigger --is-mc. PBS_ARRAY_INDEX is used directly as the
# 0-based file index, so the pilot (Step 4) and the full run (Step 5) use
# the identical script and differ only in the -J range.
#
# Writes three inclusive shards per file (rare4 / pr31 / pr31_noOR) plus
# job_metadata.json, under OUTPUT_BASE/job_<index>/.
# ---------------------------------------------------------------------------
#PBS -N tt_notrig
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=8gb
#PBS -l walltime=02:00:00
#PBS -l io=30

set -euo pipefail

REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"

: "${RECORD_ID:?RECORD_ID not set}"
: "${OUTPUT_BASE:?OUTPUT_BASE not set}"
# Only used for the job tag / signature prefix: --population notrigger
# applies no HLT requirement and no de-duplication, so this label selects
# no trigger and vetoes nothing.
DATASET_LABEL="${DATASET_LABEL:-DoubleMuon}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/job_${JOB_INDEX}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) on $(hostname) at $(date)"
echo "repo=$REPO_DIR commit=$(git rev-parse HEAD)"
echo "record=$RECORD_ID file-index=$JOB_INDEX out=$JOB_OUTPUT_DIR"

python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
    --dataset-label "$DATASET_LABEL" \
    --record-id "$RECORD_ID" \
    --file-index "$JOB_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR" \
    --population notrigger --is-mc

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
