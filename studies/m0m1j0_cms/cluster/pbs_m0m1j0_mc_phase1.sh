#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_m0m1j0_mc_phase1.sh
#
# Phase-1 MC weights task -- one PBS array job PER INPUT FILE of a single
# MC record, PBS_ARRAY_INDEX used directly as the 0-based file-index (no
# mapping file needed -- one record per submission, unlike the multi-
# record data "full" run). Calls run_m0m1j0_on_mc_file_v2.py (the NEW MC
# driver, A1/A4/A5) -- run_m0m1j0_on_file.py and merge_full_v2.py
# themselves are untouched by this task.
#
# Same resource profile as the existing ttbar MC job
# (pbs_m0m1j0_ttbar.sh): mem=5gb, io=30, ncpus=1, walltime=00:30:00
# (task's own <=02:00:00 cap, kept at the more conservative existing
# precedent since this driver reads a similar or smaller branch set).
#
# Usage (per sample):
#   qsub -J 0-11  -v RECORD_ID=42407,OUTPUT_BASE=/storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1/42407 \
#        -o /storage/agrp/berkom/atlas-utilization/logs/cms_mc_phase1/42407_^array_index^.out \
#        -e /storage/agrp/berkom/atlas-utilization/logs/cms_mc_phase1/42407_^array_index^.err \
#        studies/m0m1j0_cms/cluster/pbs_m0m1j0_mc_phase1.sh
# ---------------------------------------------------------------------------
#PBS -N m0m1j0_mc_phase1
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=5gb
#PBS -l walltime=00:30:00
#PBS -l io=30

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"

: "${RECORD_ID:?RECORD_ID not set}"
: "${OUTPUT_BASE:?OUTPUT_BASE not set}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

mkdir -p "${TMPDIR:-/tmp}"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/job_${JOB_INDEX}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "record=$RECORD_ID file-index=$JOB_INDEX output-dir=$JOB_OUTPUT_DIR"

python -u studies/m0m1j0_cms/cluster/run_m0m1j0_on_mc_file_v2.py \
    --record-id "$RECORD_ID" \
    --file-index "$JOB_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
