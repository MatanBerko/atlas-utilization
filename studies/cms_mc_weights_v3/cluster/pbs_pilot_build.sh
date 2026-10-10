#!/bin/bash
# Pilot Part 3/4: the builds and the data-vs-MC comparison.
#
# A job rather than interactive work: these read every pilot shard (3.2 GB
# compressed, ~250M entries) and hold the masses and weights in memory to
# group them across files, which is far too heavy for a shared analysis node.
#
# WHAT selects the stage:
#   build_default      3a -- builder defaults, --keep-scratch
#   build_unweighted   3b -- identical except --peak-on unweighted
#   build_unpruned     Part 4's input: --min-events-per-fs 1 --keep-scratch,
#                      so nothing is pruned and the shards carry _mcw
#   analyse            3b/3c analysis of the two builds above
#   compare            Part 4 data-vs-MC plots
#PBS -N mcv3_build
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

WORK_DIR="${WORK_DIR:?WORK_DIR not set}"
REPO_DIR="${REPO_DIR:-${WORK_DIR}/repo}"
WHAT="${WHAT:?WHAT not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
DATA_RUNS="${DATA_RUNS:-/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched4_full_20261007}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export MPLCONFIGDIR="${WORK_DIR}/.mplconfig"
export XDG_CACHE_HOME="${WORK_DIR}/.cache"
export HOME="${WORK_DIR}/.jobhome"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$HOME"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

echo "Job $PBS_JOBID on $(hostname) at $(date)"
echo "commit=$(git rev-parse HEAD)  WHAT=$WHAT"
ulimit -n || true

case "$WHAT" in
  build_default)
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
        --runs-dir "$WORK_DIR/runs" \
        --out-dir "$WORK_DIR/build_default" --out-prefix pilot \
        --scratch-dir "$WORK_DIR/scratch_default" --keep-scratch
    ;;
  build_unweighted)
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
        --runs-dir "$WORK_DIR/runs" \
        --out-dir "$WORK_DIR/build_unweighted" --out-prefix pilot_unweighted \
        --peak-on unweighted \
        --scratch-dir "$WORK_DIR/scratch_unweighted"
    ;;
  build_unpruned)
    # Part 4's input. --min-events-per-fs 1 makes the shared prune a no-op
    # (it returns immediately for min_events <= 1), so the scratch shards keep
    # every final state AND carry the builder's own final _mcw weights.
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
        --runs-dir "$WORK_DIR/runs" \
        --out-dir "$WORK_DIR/build_unpruned" --out-prefix pilot_unpruned \
        --min-events-per-fs 1 \
        --scratch-dir "$WORK_DIR/scratch_unpruned" --keep-scratch
    ;;
  analyse)
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/analyse_pilot_builds.py \
        --weighted-report "$WORK_DIR/build_default/pilot_build_report.json" \
        --unweighted-report "$WORK_DIR/build_unweighted/pilot_unweighted_build_report.json" \
        --summed-root "$WORK_DIR/build_default/pilot_summedSM_mc.root" \
        --out-dir "$WORK_DIR/analysis"
    ;;
  compare)
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/compare_data_mc.py \
        --data-runs-dir "$DATA_RUNS" \
        --mc-scratch-dir "$WORK_DIR/scratch_unpruned" \
        --out-dir "$WORK_DIR/plots"
    ;;
  *)
    echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac

echo "Job $PBS_JOBID ($WHAT) finished at $(date)"
