#!/bin/bash
# One PBS array subjob per file, for a full dataset delivery run.
# MAPPING_FILE has 4 columns: "<array_index> <dataset_label> <record_id> <file_index>"
# (from gen_full_run_mapping.py). Always --population generic (a full
# delivery run; v0 exists only for the Step 3 regression check).
# Output layout: /storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs/<dataset_label>/job_<array_index>/
#PBS -N cms_ds_full
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=8gb
#PBS -l walltime=02:00:00
#PBS -l io=25
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/cms_datasets_full/full_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/cms_datasets_full/full_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/deliver_all_datasets_bumpnet/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
OUTPUT_ROOT="${OUTPUT_ROOT:-/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs}"
MAPPING_FILE="${MAPPING_FILE:?MAPPING_FILE not set}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

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
read -r MAP_INDEX DATASET_LABEL RECORD_ID FILE_INDEX <<< "$LINE"
if [[ "$MAP_INDEX" != "$JOB_INDEX" ]]; then
    echo "Mapping-file line $JOB_INDEX has index field '$MAP_INDEX', expected '$JOB_INDEX'" >&2
    exit 1
fi

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_ROOT}/${DATASET_LABEL}/job_${JOB_INDEX}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "dataset=$DATASET_LABEL record=$RECORD_ID file_index=$FILE_INDEX output-dir=$JOB_OUTPUT_DIR"
echo "git commit: $(git rev-parse HEAD)"

/usr/bin/time -v python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
    --dataset-label "$DATASET_LABEL" \
    --record-id "$RECORD_ID" \
    --file-index "$FILE_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR" \
    --population generic

echo "Job $PBS_JOBID (array index $JOB_INDEX, ${DATASET_LABEL} record=$RECORD_ID file=$FILE_INDEX) finished at $(date)"
