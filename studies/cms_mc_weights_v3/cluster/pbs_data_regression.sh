#!/bin/bash
# Part B: re-run the DATA path (no --is-mc) from the pinned v3 commit, so its
# output can be compared against the delivered four-dataset production.
#
# One PBS array subjob per data file. MAPPING_FILE has 4 columns:
#   "<array_index> <dataset_label> <record_id> <file_index>"
# Always --population matched4 and NEVER --is-mc: this job exists to prove the
# data path is unchanged.
#PBS -N mcv3_datareg
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
OUTPUT_BASE="${OUTPUT_BASE:-${WORK_DIR}/data_regression}"
MAPPING_FILE="${MAPPING_FILE:?MAPPING_FILE not set}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
# Nothing is written to $HOME by this job.
export MPLCONFIGDIR="${WORK_DIR}/.mplconfig"
export XDG_CACHE_HOME="${WORK_DIR}/.cache"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME"

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

LINE=$(sed -n "${JOB_INDEX}p" "$MAPPING_FILE")
if [[ -z "$LINE" ]]; then
    echo "No mapping-file line for index $JOB_INDEX in $MAPPING_FILE" >&2
    exit 1
fi
read -r MAP_INDEX DATASET_LABEL RECORD_ID FILE_INDEX <<< "$LINE"
if [[ "$MAP_INDEX" != "$JOB_INDEX" ]]; then
    echo "Mapping-file line $JOB_INDEX has index field '$MAP_INDEX', expected '$JOB_INDEX'" >&2
    exit 1
fi

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/${DATASET_LABEL}/job_${FILE_INDEX}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) on $(hostname) at $(date)"
echo "commit=$(git rev-parse HEAD)"
echo "dataset=$DATASET_LABEL record=$RECORD_ID file_index=$FILE_INDEX out=$JOB_OUTPUT_DIR"
echo "NOTE: --is-mc is deliberately NOT passed; this is the data-path regression."

/usr/bin/time -v python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
    --dataset-label "$DATASET_LABEL" \
    --record-id "$RECORD_ID" \
    --file-index "$FILE_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR" \
    --population matched4

echo "Job $PBS_JOBID (${DATASET_LABEL} file ${FILE_INDEX}) finished at $(date)"
