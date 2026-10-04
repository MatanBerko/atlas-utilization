#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_build_histograms.sh (ttbar_count_vs_atlas, Step 6)
#
# Runs build_study_histograms.py for ONE notrigger variant. Submitted as a
# 3-element array, one element per variant, because the merge step copies
# every shard to scratch and holds the pooled arrays in memory -- that is a
# compute-node job, not a login-node one.
# ---------------------------------------------------------------------------
#PBS -N tt_build
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=8gb
#PBS -l walltime=02:00:00
#PBS -l io=30

set -euo pipefail

REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"

: "${JOBS_DIR:?JOBS_DIR not set}"
: "${OUT_BASE:?OUT_BASE not set}"
EXPECTED_N_FILES="${EXPECTED_N_FILES:-49}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

IDX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"
VARIANTS=(rare4 pr31 pr31_noOR)
VARIANT="${VARIANTS[$IDX]}"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

# Keep the shard scratch copies on the node's own temporary space.
export TMPDIR="${TMPDIR:-/tmp}"

OUT_DIR="${OUT_BASE}/${VARIANT}"
mkdir -p "$OUT_DIR"

echo "Job $PBS_JOBID (array index $IDX, variant $VARIANT) on $(hostname) at $(date)"
echo "repo=$REPO_DIR commit=$(git rev-parse HEAD)"

python -u studies/ttbar_count_vs_atlas/build_study_histograms.py \
    --jobs-dir "$JOBS_DIR" \
    --variant "$VARIANT" \
    --out-dir "$OUT_DIR" \
    --out-prefix "ttbar_notrigger_${VARIANT}" \
    --expected-n-files "$EXPECTED_N_FILES"

echo "Job $PBS_JOBID (variant $VARIANT) finished at $(date)"
