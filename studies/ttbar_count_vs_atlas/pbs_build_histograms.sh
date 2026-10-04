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

# run_funnel_at_threshold works on scratch COPIES of the shards (it mutates
# them), so this job needs a few GB of writable scratch. Prefer the node's
# own local space; fall back to a per-job directory on Lustre if the node
# does not have room, rather than failing halfway through the copy.
NEED_KB=$((6 * 1024 * 1024))   # 6 GB
LOCAL_TMP="${TMPDIR:-/tmp}"
AVAIL_KB=$(df -Pk "$LOCAL_TMP" 2>/dev/null | awk 'NR==2{print $4}')
if [ -n "${AVAIL_KB:-}" ] && [ "$AVAIL_KB" -ge "$NEED_KB" ]; then
    export TMPDIR="$LOCAL_TMP"
else
    export TMPDIR="${OUT_BASE}/_scratch_${VARIANT}_${PBS_JOBID%%.*}"
    mkdir -p "$TMPDIR"
    echo "node scratch $LOCAL_TMP has only ${AVAIL_KB:-unknown} KB free; using $TMPDIR"
fi
echo "TMPDIR=$TMPDIR ($(df -Ph "$TMPDIR" | awk 'NR==2{print $4}') free)"
# The study's own scratch directory, if we made one, is ours to remove.
cleanup() { case "$TMPDIR" in "${OUT_BASE}/_scratch_"*) rm -rf "$TMPDIR" ;; esac; }
trap cleanup EXIT

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
