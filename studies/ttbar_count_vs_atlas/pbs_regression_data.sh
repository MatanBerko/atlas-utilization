#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_regression_data.sh (ttbar-count-vs-atlas study, Step 3 proof 1)
#
# Re-runs the 4 DATA pilot files in --population matched DATA mode (no
# --is-mc) with the branch's modified run_dataset_on_file.py, so the
# resulting normal / top4 / nonjet4 / rare4 shards can be compared
# byte-for-byte against the already-delivered production output (which is
# read-only and is never touched by this job).
#
# Submitted as a 4-element array; PBS_ARRAY_INDEX picks the row below.
#   0: DoubleMuon record 30522 file 0   (delivered as DoubleMuon/job_0)
#   1: DoubleMuon record 30555 file 0   (delivered as DoubleMuon/job_29)
#   2: SingleMuon record 30530 file 0   (delivered as SingleMuon/job_0)
#   3: SingleMuon record 30563 file 0   (delivered as SingleMuon/job_70)
# ---------------------------------------------------------------------------
#PBS -N tt_regr_data
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

: "${OUTPUT_BASE:?OUTPUT_BASE not set}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

IDX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

LABELS=(DoubleMuon DoubleMuon SingleMuon SingleMuon)
RECORDS=(30522 30555 30530 30563)
FILEIDX=(0 0 0 0)
RUNNAMES=(DoubleMuon_30522_0 DoubleMuon_30555_0 SingleMuon_30530_0 SingleMuon_30563_0)

LABEL="${LABELS[$IDX]}"
RECORD="${RECORDS[$IDX]}"
FINDEX="${FILEIDX[$IDX]}"
RUNNAME="${RUNNAMES[$IDX]}"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/${RUNNAME}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $IDX) on $(hostname) at $(date)"
echo "repo=$REPO_DIR commit=$(git rev-parse HEAD)"
echo "label=$LABEL record=$RECORD file-index=$FINDEX out=$JOB_OUTPUT_DIR"

python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
    --dataset-label "$LABEL" \
    --record-id "$RECORD" \
    --file-index "$FINDEX" \
    --output-dir "$JOB_OUTPUT_DIR" \
    --population matched

echo "Job $PBS_JOBID (array index $IDX) finished at $(date)"
