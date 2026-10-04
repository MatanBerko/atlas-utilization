#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_yield.sh (electron_prep, Step 5 yield projection)
#
# Pools the EXISTING generic (unmatched) DoubleEG + MuonEG inclusive shards
# through the delivery's own post-processing funnel, to project which
# final-state categories the electron datasets could add.
#
# The delivered shards are read-only inputs: the funnel works on scratch
# COPIES (copy_shards), and nothing under output/cms_datasets/runs/ is
# written, moved or deleted.
# ---------------------------------------------------------------------------
#PBS -N eprep_yield
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=8gb
#PBS -l walltime=02:00:00
#PBS -l io=25

set -euo pipefail

REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
: "${OUT_JSON:?OUT_JSON not set}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"
export PYTHONPATH="$REPO_DIR"

# The funnel copies every shard to scratch; prefer node-local space and fall
# back to our own work area if the node is short.
NEED_KB=$((4 * 1024 * 1024))
LOCAL_TMP="${TMPDIR:-/tmp}"
AVAIL_KB=$(df -Pk "$LOCAL_TMP" 2>/dev/null | awk 'NR==2{print $4}')
if [ -n "${AVAIL_KB:-}" ] && [ "$AVAIL_KB" -ge "$NEED_KB" ]; then
    export TMPDIR="$LOCAL_TMP"
else
    export TMPDIR="/storage/agrp/berkom/atlas-utilization/work/electron_prep/_scratch_yield_${PBS_JOBID%%.*}"
    mkdir -p "$TMPDIR"
fi
cleanup() { case "$TMPDIR" in */electron_prep/_scratch_yield_*) rm -rf "$TMPDIR" ;; esac; }
trap cleanup EXIT

echo "Job $PBS_JOBID on $(hostname) at $(date)"
echo "repo=$REPO_DIR commit=$(git rev-parse HEAD)  TMPDIR=$TMPDIR"

python -u studies/cms_datasets/electron_prep/project_cost_and_yield.py \
    --part yield --out "$OUT_JSON"

echo "Job $PBS_JOBID finished at $(date)"
