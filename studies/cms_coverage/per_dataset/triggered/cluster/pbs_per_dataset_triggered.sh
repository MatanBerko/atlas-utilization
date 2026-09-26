#!/bin/bash
# One PBS array subjob per dataset. MAPPING_FILE has 5 columns:
# "<array_index> <record_id> <is_mc:0|1> <dataset_label> <trigger_paths_or_NONE>"
# trigger_paths is a comma-separated list (no spaces) or the literal
# string NONE (MC groups: no trigger requirement, per task instruction).
#PBS -N per_dataset_triggered
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=6gb
#PBS -l walltime=02:00:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/per_dataset_yield_triggered/pdt_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/per_dataset_yield_triggered/pdt_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/per_dataset_yield/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
OUTPUT_BASE="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/per_dataset_yield_triggered}"
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
read -r MAP_INDEX RECORD_ID IS_MC DATASET_LABEL TRIGGER_PATHS <<< "$LINE"
if [[ "$MAP_INDEX" != "$JOB_INDEX" ]]; then
    echo "Mapping-file line $JOB_INDEX has index field '$MAP_INDEX', expected '$JOB_INDEX'" >&2
    exit 1
fi

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/job_${DATASET_LABEL}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "dataset=$DATASET_LABEL record=$RECORD_ID is_mc=$IS_MC trigger_paths=$TRIGGER_PATHS output-dir=$JOB_OUTPUT_DIR"

IS_MC_FLAG=""
if [[ "$IS_MC" == "1" ]]; then
    IS_MC_FLAG="--is-mc"
fi

TRIGGER_ARG=""
if [[ "$TRIGGER_PATHS" != "NONE" ]]; then
    TRIGGER_ARG="--trigger-paths $TRIGGER_PATHS"
fi

python -u studies/cms_coverage/per_dataset/triggered/cluster/run_per_dataset_on_file.py \
    --record-id "$RECORD_ID" \
    --file-index 0 \
    --output-dir "$JOB_OUTPUT_DIR" \
    --dataset-label "$DATASET_LABEL" \
    $IS_MC_FLAG \
    $TRIGGER_ARG

echo "Job $PBS_JOBID (array index $JOB_INDEX, $DATASET_LABEL) finished at $(date)"
