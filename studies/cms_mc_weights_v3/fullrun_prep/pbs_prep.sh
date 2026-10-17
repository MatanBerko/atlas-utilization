#!/bin/bash
# Full-run preparation (17 Oct 2026): the builds and the input sweep.
# Per-file production is NOT here: Part C uses cluster/pbs_mc_pilot.sh
# unchanged (same launcher, options and resources as the pilot).
#
# WHAT selects the stage:
#   rebuild_default  Part B1 -- exactly the pilot's build 3a command
#                    (cluster/pbs_pilot_build.sh WHAT=build_default), with the
#                    10 Oct pilot per-file outputs as input (RUNS_DIR, read
#                    only: the builder copies every shard to its scratch dir
#                    before touching it).
#   smoke_builds     Part C -- one per-sample build per smoke record, builder
#                    defaults, --output-mode per-sample (no summed-SM file),
#                    --smoke-test (a report label only: Sigma-w is one file's).
#   sweep            Part D -- fullrun_prep/measure_fullrun_inputs.py.
#PBS -N mcprep
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

WORK_DIR="${WORK_DIR:?WORK_DIR not set}"
REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
WHAT="${WHAT:?WHAT not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
# Nothing is written to $HOME by this job.
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
  rebuild_default)
    RUNS_DIR="${RUNS_DIR:?RUNS_DIR not set}"
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
        --runs-dir "$RUNS_DIR" \
        --out-dir "$WORK_DIR/build_default" --out-prefix pilot \
        --scratch-dir "$WORK_DIR/scratch_default" --keep-scratch
    ;;
  smoke_builds)
    SMOKE_RECORDS="${SMOKE_RECORDS:?SMOKE_RECORDS not set}"
    for rid in ${SMOKE_RECORDS//,/ }; do
        echo "=== smoke build record $rid at $(date)"
        /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
            --runs-dir "$WORK_DIR/runs_smoke" --records "$rid" \
            --out-dir "$WORK_DIR/smoke_builds/record$rid" --out-prefix smoke \
            --output-mode per-sample --smoke-test \
            --scratch-dir "$WORK_DIR/scratch_smoke/record$rid" \
            && echo "=== smoke build record $rid OK" \
            || echo "=== smoke build record $rid FAILED (exit $?)"
    done
    ;;
  sweep)
    python -u studies/cms_mc_weights_v3/fullrun_prep/measure_fullrun_inputs.py \
        --out "$WORK_DIR/evidence/fullrun_inputs.json"
    ;;
  *)
    echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac

echo "Job $PBS_JOBID ($WHAT) finished at $(date)"
