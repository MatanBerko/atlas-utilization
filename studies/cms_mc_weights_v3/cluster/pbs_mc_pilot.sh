#!/bin/bash
# CMS MC pilot: one PBS array subjob per MC file, --is-mc, exactly as
# implemented at the pinned commit. Nothing about the selection, the
# thresholds, the binning or the naming is touched here.
#
# MAPPING_FILE has 3 columns:
#   "<array_index> <record_id> <file_index>"
#
# Walltime and memory come from the environment so one script serves the
# timing job and the three production arrays without being edited:
#   WALLTIME (default 24:00:00), MEM (default 16gb), IO (default 25)
# are applied with qsub -l at submission time, NOT here, so that a resubmit
# can raise them for a single file without touching this file.
#PBS -N mcv3_pilot
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

WORK_DIR="${WORK_DIR:?WORK_DIR not set}"
REPO_DIR="${REPO_DIR:-${WORK_DIR}/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
OUTPUT_BASE="${OUTPUT_BASE:-${WORK_DIR}/runs}"
MAPPING_FILE="${MAPPING_FILE:?MAPPING_FILE not set}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
# Nothing is written to $HOME by this job.
export MPLCONFIGDIR="${WORK_DIR}/.mplconfig"
export XDG_CACHE_HOME="${WORK_DIR}/.cache"
export HOME="${WORK_DIR}/.jobhome"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$HOME"

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

if [[ ! -f "$MAPPING_FILE" ]]; then
    echo "MAPPING_FILE not found: $MAPPING_FILE" >&2
    exit 1
fi

LINE=$(sed -n "${JOB_INDEX}p" "$MAPPING_FILE")
if [[ -z "$LINE" ]]; then
    echo "No mapping-file line for index $JOB_INDEX in $MAPPING_FILE" >&2
    exit 1
fi
read -r MAP_INDEX RECORD_ID FILE_INDEX <<< "$LINE"
if [[ "$MAP_INDEX" != "$JOB_INDEX" ]]; then
    echo "Mapping-file line $JOB_INDEX has index field '$MAP_INDEX', expected '$JOB_INDEX'" >&2
    exit 1
fi

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

# One directory per file, so no directory ever holds more than ~9 files.
JOB_OUTPUT_DIR="${OUTPUT_BASE}/record${RECORD_ID}/job_${FILE_INDEX}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) on $(hostname) at $(date)"
echo "commit=$(git rev-parse HEAD)"
echo "record=$RECORD_ID file_index=$FILE_INDEX out=$JOB_OUTPUT_DIR"

/usr/bin/time -v python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
    --is-mc \
    --dataset-label MC \
    --record-id "$RECORD_ID" \
    --file-index "$FILE_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR" \
    --population matched4

echo "Job $PBS_JOBID (record ${RECORD_ID} file ${FILE_INDEX}) finished at $(date)"
