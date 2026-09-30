#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_zpeak_reader.sh -- one PBS array job PER INPUT FILE of a single
# record (data or MC), PBS_ARRAY_INDEX used directly as the 0-based
# file-index. Calls zpeak_reader.py (diagnostic-only, E2) -- no shared
# code, no delivered data/MC output is touched.
#
# Same conservative resource profile as the existing phase-1 MC job.
#
# Usage (per record):
#   qsub -J 0-56 -v RECORD_ID=30522,OUTPUT_BASE=.../diagnosis_zpeak/30522 \
#        -o .../logs/.../30522_^array_index^.out \
#        -e .../logs/.../30522_^array_index^.err \
#        studies/cms_mc_weights/phase1/diagnosis/pbs_zpeak_reader.sh
#   (add IS_MC=1 in -v for an MC record)
# ---------------------------------------------------------------------------
#PBS -N zpeak_reader
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
IS_MC="${IS_MC:-0}"

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
echo "record=$RECORD_ID file-index=$JOB_INDEX is_mc=$IS_MC output-dir=$JOB_OUTPUT_DIR"

EXTRA_FLAG=""
if [[ "$IS_MC" == "1" ]]; then
    EXTRA_FLAG="--is-mc"
fi

python -u studies/cms_mc_weights/phase1/diagnosis/zpeak_reader.py \
    --record-id "$RECORD_ID" \
    --file-index "$JOB_INDEX" \
    $EXTRA_FLAG \
    --output-dir "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
