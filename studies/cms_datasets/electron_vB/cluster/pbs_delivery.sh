#!/bin/bash
# Step D1: build the combined four-dataset BumpNet delivery from the full
# production shards. Run as a batch job rather than interactively: the
# funnel copies every rare4 shard to scratch and concatenates the pooled
# mass arrays, which is more than an interactive analysis-node session
# should hold.
#
# Environment: REPO_DIR, RUNS_DIR, OUT_DIR, OUT_PREFIX
#PBS -S /bin/bash
#PBS -q N
#PBS -m n
#PBS -l select=1:ncpus=1:mem=32gb
#PBS -l walltime=06:00:00
#PBS -l io=50

set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
# The funnel's scratch copies go to $TMPDIR, never to $HOME.
export TMPDIR="${TMPDIR:-/tmp}"

REPO_DIR="${REPO_DIR:?}"
RUNS_DIR="${RUNS_DIR:?}"
OUT_DIR="${OUT_DIR:?}"
OUT_PREFIX="${OUT_PREFIX:?}"
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python

cd "$REPO_DIR"
echo "commit=$(git rev-parse HEAD) host=$(hostname) $(date)"
echo "runs-dir=$RUNS_DIR out-dir=$OUT_DIR prefix=$OUT_PREFIX TMPDIR=$TMPDIR"
df -h "$TMPDIR" | tail -1

# No extra flags: the builder's own defaults are the delivery's rules --
# upstream-exact names with _width_10.0, no per-histogram minimum, no
# filled-bin cut, >=100 events per final state once on the combined shards.
/usr/bin/time -v "$PY" -u studies/cms_datasets/deliver/build_four_dataset_delivery.py \
  --runs-dir "$RUNS_DIR" --out-dir "$OUT_DIR" --out-prefix "$OUT_PREFIX"

echo "done $(date)"
