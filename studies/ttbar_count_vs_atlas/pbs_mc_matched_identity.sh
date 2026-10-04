#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_mc_matched_identity.sh (ttbar-count-vs-atlas study, Step 3 proof 2)
#
# Re-runs ONE TTTo2L2Nu (record 67801) file in --population matched --is-mc
# -- exactly the mode the paused MC v2 production used -- with the branch's
# modified run_dataset_on_file.py, so its normal / top4 / nonjet4 mass
# shards and its weight shards can be compared against the paused run's own
# already-written output for that same file.
#
# The paused run under work/cms_mc_v2/ is READ-ONLY here: this job writes
# only under its own OUTPUT_BASE and never into work/cms_mc_v2/.
# ---------------------------------------------------------------------------
#PBS -N tt_mc_ident
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
: "${DATASET_LABEL:?DATASET_LABEL not set}"
: "${FILE_INDEX:?FILE_INDEX not set}"
: "${OUTPUT_BASE:?OUTPUT_BASE not set}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/${DATASET_LABEL}_job_${FILE_INDEX}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID on $(hostname) at $(date)"
echo "repo=$REPO_DIR commit=$(git rev-parse HEAD)"
echo "record=$RECORD_ID label=$DATASET_LABEL file-index=$FILE_INDEX out=$JOB_OUTPUT_DIR"

python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
    --dataset-label "$DATASET_LABEL" \
    --record-id "$RECORD_ID" \
    --file-index "$FILE_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR" \
    --population matched --is-mc

echo "Job $PBS_JOBID finished at $(date)"
