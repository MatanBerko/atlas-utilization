#!/bin/bash
# One PBS array subjob per remaining dataset. MAPPING_FILE has 4 columns:
# "<array_index> <record_id> <is_mc:0|1> <dataset_label>".
#PBS -N per_dataset_yield
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=6gb
#PBS -l walltime=01:00:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/per_dataset_yield/pd_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/per_dataset_yield/pd_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/per_dataset_yield/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
OUTPUT_BASE="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/per_dataset_yield}"
MAPPING_FILE="${MAPPING_FILE:?MAPPING_FILE not set}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set}"
LINE=$(sed -n "${JOB_INDEX}p" "$MAPPING_FILE")
read -r MAP_INDEX RECORD_ID IS_MC DATASET_LABEL <<< "$LINE"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/job_${DATASET_LABEL}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Array index $JOB_INDEX -> dataset=$DATASET_LABEL record=$RECORD_ID is_mc=$IS_MC"

IS_MC_FLAG=""
if [[ "$IS_MC" == "1" ]]; then
    IS_MC_FLAG="--is-mc"
fi

python -u studies/cms_coverage/per_dataset/cluster/run_per_dataset_on_file.py \
    --record-id "$RECORD_ID" \
    --file-index 0 \
    --output-dir "$JOB_OUTPUT_DIR" \
    --dataset-label "$DATASET_LABEL" \
    $IS_MC_FLAG

echo "Array index $JOB_INDEX ($DATASET_LABEL) finished at $(date)"
