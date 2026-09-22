#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_m0m1j0_full.sh
#
# m0m1j0 CMS histogram -- Step 2 FULL RUN: one PBS job PER INPUT FILE, via
# a PBS job array, over ALL files of records 30522 (Run2016G) and 30555
# (Run2016H). Same physics selection, same per-job driver
# (run_m0m1j0_on_file.py) as the pilot -- see
# studies/m0m1j0_cms/RECIPE.md and studies/m0m1j0_cms/pilot/PILOT_REPORT.md.
#
# Array size is NOT hardcoded here (unlike the pilot's fixed -J 1-4): the
# actual file count depends on the portal's CURRENT file list, re-fetched
# fresh by generate_job_index_map.py at submission time (this task's own
# instruction: the portal's list has changed within a single day before).
# There is deliberately NO "#PBS -J" line in this file -- submit_full.sh
# always passes "-J 1-<total_jobs>" explicitly on the qsub command line
# (total_jobs from that generation step, confirmed 57 = 29+28 as of
# 2026-09-22, but never assumed fixed by this script itself).
#
# Each subjob resolves ITS OWN (record_id, file_index) by reading line
# $PBS_ARRAY_INDEX of MAPPING_FILE (one "<index> <record_id> <file_index>"
# line per job, written by generate_job_index_map.py) -- not by an inline
# per-index case statement (impractical at 57+ entries, and would embed a
# submission-time snapshot INTO version control, which the mapping file
# on Lustre deliberately avoids).
#
# Resource requests: SAME per-file profile as the pilot (measured 24-42s
# wall, ~2GB peak memory over 4 files -- see PILOT_REPORT.md), with the
# task's own explicit large safety margin:
#   mem=5gb            -- ~2x the pilot's observed 2.29 GB peak.
#   walltime=00:20:00  -- ~30x the pilot's slowest observed 42s.
#   ncpus=1            -- one file per job, no internal thread pool.
#   io=30              -- REQUIRED by this site's scheduler for every job;
#                          same value as the pilot's own comparable job.
#
# Log files: "^array_index^" is OpenPBS's own per-subjob log-path
# substitution token (same convention as the pilot's own PBS script).
# ---------------------------------------------------------------------------
#PBS -N m0m1j0_full
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=5gb
#PBS -l walltime=00:20:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_full/m0m1j0_full_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_full/m0m1j0_full_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/m0m1j0_cms/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
OUTPUT_BASE="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_full}"
MAPPING_FILE="${MAPPING_FILE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_full/job_index_map.txt}"

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

python -u studies/m0m1j0_cms/cluster/run_m0m1j0_on_file.py \
    --record-id "$RECORD_ID" \
    --file-index "$FILE_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
