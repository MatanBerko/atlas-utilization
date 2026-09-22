#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_m0m1j0_ttbar.sh
#
# m0m1j0 CMS histogram -- Part B: one PBS job PER INPUT FILE of the ttbar
# dilepton MC sample (record 67801, RECIPE.md section 8), same array-job
# / mapping-file technique as the data study's pbs_m0m1j0_full.sh (no
# "#PBS -J" header -- submit_ttbar.sh always passes "-J 1-<total_jobs>"
# explicitly, sized from generate_ttbar_job_index_map.py's own fresh
# portal fetch). Used for BOTH the 2-file pilot and the full 49-file run
# -- which one depends only on which mapping file/OUTPUT_BASE the caller
# points at (submit_ttbar.sh's PILOT vs FULL mode).
#
# Calls run_m0m1j0_on_mc_file.py (NOT the data driver) -- no golden-JSON
# filter, genWeight tracked, same object selection as data.
#
# Resource requests: same profile as the data full run (measured 24-42s
# wall, ~2GB peak over a similarly-sized NanoAOD(SIM) file) --
#   mem=5gb, walltime=00:30:00 (task's own cap for this task),
#   ncpus=1, io=30.
# ---------------------------------------------------------------------------
#PBS -N m0m1j0_ttbar
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=5gb
#PBS -l walltime=00:30:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_ttbar/m0m1j0_ttbar_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_ttbar/m0m1j0_ttbar_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/m0m1j0_cms/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
OUTPUT_BASE="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_ttbar}"
MAPPING_FILE="${MAPPING_FILE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_ttbar/job_index_map.txt}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

if [[ ! -f "$MAPPING_FILE" ]]; then
    echo "MAPPING_FILE not found: $MAPPING_FILE -- was generate_ttbar_job_index_map.py run before submitting?" >&2
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

python -u studies/m0m1j0_cms/cluster/run_m0m1j0_on_mc_file.py \
    --record-id "$RECORD_ID" \
    --file-index "$FILE_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
