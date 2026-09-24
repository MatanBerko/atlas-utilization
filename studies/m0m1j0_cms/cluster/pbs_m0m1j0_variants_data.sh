#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_m0m1j0_variants_data.sh
#
# Selection-variants task (supervisor request). One PBS job PER INPUT FILE
# of records 30522/30555 (same files as the existing V0-only full run),
# computing ALL FOUR selection variants (V0/V1/V2/V3) in one pass per file
# via run_m0m1j0_variants_on_file.py -- one file read, one golden-JSON
# filter, four selections applied to the same in-memory events.
#
# Resource requests, larger than the V0-only full run (pbs_m0m1j0_full.sh:
# mem=5gb, walltime=00:20:00) because this job does 4x the selection work
# per file:
#   mem=6gb, walltime=00:35:00 (task's own <=40min cap, with margin),
#   ncpus=1, io=30 (same value as every other per-file job in this study).
# ---------------------------------------------------------------------------
#PBS -N m0m1j0_variants_data
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=6gb
#PBS -l walltime=00:35:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_variants_data/m0m1j0_variants_data_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_variants_data/m0m1j0_variants_data_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/m0m1j0_cms/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
OUTPUT_BASE="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_variants_data}"
MAPPING_FILE="${MAPPING_FILE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_variants_data/job_index_map.txt}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

if [[ ! -f "$MAPPING_FILE" ]]; then
    echo "MAPPING_FILE not found: $MAPPING_FILE -- was generate_job_index_map.py run before submitting?" >&2
    exit 1
fi

LINE=$(sed -n "${JOB_INDEX}p" "$MAPPING_FILE")
if [[ -z "$LINE" ]]; then
    echo "No mapping-file line for index $JOB_INDEX in $MAPPING_FILE (file has $(wc -l < "$MAPPING_FILE") lines)" >&2
    exit 1
fi
read -r MAP_INDEX RECORD_ID FILE_INDEX <<< "$LINE"
if [[ "$MAP_INDEX" != "$JOB_INDEX" ]]; then
    echo "Mapping-file line $JOB_INDEX has index field '$MAP_INDEX', expected '$JOB_INDEX' -- file may be corrupt or misaligned" >&2
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

python -u studies/m0m1j0_cms/cluster/run_m0m1j0_variants_on_file.py \
    --record-id "$RECORD_ID" \
    --file-index "$FILE_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
