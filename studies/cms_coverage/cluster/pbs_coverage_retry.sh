#!/bin/bash
# One PBS array subjob per RETRIED file. MAPPING_FILE has 4 columns:
# "<array_index> <record_id> <file_index> <original_job_index>" -- the 4th
# column is used for the output dir so retried jobs land back in their
# ORIGINAL job_<N> directory (the merge step expects job_1..job_57 exactly
# once each), not a fresh 1..22 numbering.
#PBS -N cms_coverage_retry
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=5gb
#PBS -l walltime=00:20:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/cms_coverage_full/retry2_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/cms_coverage_full/retry2_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/cms_coverage/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
OUTPUT_BASE="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/cms_coverage_full}"
MAPPING_FILE="${MAPPING_FILE:?MAPPING_FILE not set}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set}"
LINE=$(sed -n "${JOB_INDEX}p" "$MAPPING_FILE")
read -r MAP_INDEX RECORD_ID FILE_INDEX ORIG_JOB_INDEX <<< "$LINE"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/job_${ORIG_JOB_INDEX}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Retry array index $JOB_INDEX -> original job_${ORIG_JOB_INDEX}, record=$RECORD_ID file_index=$FILE_INDEX"

python -u studies/cms_coverage/cluster/run_coverage_on_file.py \
    --record-id "$RECORD_ID" \
    --file-index "$FILE_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR"

echo "Retry array index $JOB_INDEX finished at $(date)"
