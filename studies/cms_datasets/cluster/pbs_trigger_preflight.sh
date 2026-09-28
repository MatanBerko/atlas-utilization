#!/bin/bash
# One PBS array subjob per (dataset, era, file-index-range) batch.
# MAPPING_FILE has 6 columns:
# "<array_index> <dataset_label> <era> <record_id> <file_index_start> <file_index_end>"
# (file_index_end is exclusive).
#PBS -N cms_ds_preflight
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=4gb
#PBS -l walltime=01:00:00
#PBS -l io=20
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/cms_datasets_preflight/pf_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/cms_datasets_preflight/pf_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/deliver_all_datasets_bumpnet/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
OUTPUT_BASE="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/cms_datasets/preflight}"
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
read -r MAP_INDEX DATASET_LABEL ERA RECORD_ID FILE_START FILE_END <<< "$LINE"
if [[ "$MAP_INDEX" != "$JOB_INDEX" ]]; then
    echo "Mapping-file line $JOB_INDEX has index field '$MAP_INDEX', expected '$JOB_INDEX'" >&2
    exit 1
fi

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/job_${DATASET_LABEL}_${ERA}_${FILE_START}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "dataset=$DATASET_LABEL era=$ERA record=$RECORD_ID files=[$FILE_START,$FILE_END) output-dir=$JOB_OUTPUT_DIR"

/usr/bin/time -v python -u studies/cms_datasets/cluster/trigger_preflight_on_file.py \
    --record-id "$RECORD_ID" \
    --file-index-start "$FILE_START" \
    --file-index-end "$FILE_END" \
    --dataset-label "$DATASET_LABEL" \
    --era "$ERA" \
    --output-dir "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX, ${DATASET_LABEL}_${ERA}) finished at $(date)"
