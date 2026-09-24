#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_coverage_full.sh -- one PBS array subjob per DoubleMuon file.
#
# Mirrors studies/m0m1j0_cms/cluster/pbs_m0m1j0_full.sh's own pattern
# exactly (same resource-request style, same mapping-file convention),
# adapted to call run_coverage_on_file.py instead. Resource requests based
# on this survey's own pilot measurement (2 files: 117s/135s wall,
# 2.05/2.30 GB peak memory) with a large safety margin, same as that
# script's own precedent.
# ---------------------------------------------------------------------------
#PBS -N cms_coverage_full
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=5gb
#PBS -l walltime=00:20:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/cms_coverage_full/cms_coverage_full_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/cms_coverage_full/cms_coverage_full_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/cms_coverage/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
OUTPUT_BASE="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/cms_coverage_full}"
MAPPING_FILE="${MAPPING_FILE:-/storage/agrp/berkom/atlas-utilization/output/cms_coverage_full/job_index_map.txt}"

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
read -r MAP_INDEX RECORD_ID FILE_INDEX <<< "$LINE"
if [[ "$MAP_INDEX" != "$JOB_INDEX" ]]; then
    echo "Mapping-file line $JOB_INDEX has index field '$MAP_INDEX', expected '$JOB_INDEX'" >&2
    exit 1
fi

mkdir -p "${TMPDIR:-/tmp}"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/job_${JOB_INDEX}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "record=$RECORD_ID file-index=$FILE_INDEX output-dir=$JOB_OUTPUT_DIR"

python -u studies/cms_coverage/cluster/run_coverage_on_file.py \
    --record-id "$RECORD_ID" \
    --file-index "$FILE_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
