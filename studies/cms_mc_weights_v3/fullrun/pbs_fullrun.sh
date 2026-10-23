#!/bin/bash
# CMS MC full run (17 Oct 2026): every post-production stage as a PBS job.
# Production itself is cluster/pbs_mc_pilot.sh, unchanged (FULL_RUN_PLAN §6).
#
# WHAT selects the stage:
#   audit      §6 step 4: fullrun/audit_production.py
#   build      §6 step 5: the pilot's default build over $WORK_DIR/runs,
#              --out-prefix fullrun --keep-scratch (all other options default)
#   reproduce  step 5a: mc_compare.py runs, the 98 re-run pilot files vs the
#              10 Oct originals (PILOT_RUNS, read-only; compare.py copies each
#              database to $TMPDIR before opening it)
#   sanity     step 5b-d: fullrun/sanity_and_plots.py
#PBS -N mcfull_post
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
export TMPDIR="${WORK_DIR}/tmp_${WHAT}"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$HOME" "$TMPDIR"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

echo "Job $PBS_JOBID on $(hostname) at $(date)"
echo "commit=$(git rev-parse HEAD)  WHAT=$WHAT"
ulimit -n || true

case "$WHAT" in
  audit)
    python -u studies/cms_mc_weights_v3/fullrun/audit_production.py \
        --work "$WORK_DIR" --out "$WORK_DIR/evidence/production_audit.json"
    ;;
  build)
    test ! -e "$WORK_DIR/build_default"   # never overwrite an existing output
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
        --runs-dir "$WORK_DIR/runs" \
        --out-dir "$WORK_DIR/build_default" --out-prefix fullrun \
        --scratch-dir "$WORK_DIR/scratch_default" --keep-scratch
    ;;
  reproduce)
    PILOT_RUNS="${PILOT_RUNS:?PILOT_RUNS not set}"
    JOBS=$(python - <<'EOF'
import os
w = os.environ["WORK_DIR"]
pairs = []
for rid in ("67801", "35669", "37728"):
    for line in open(f"{w}/mappings/mapping_{rid}.txt"):
        _i, r, f = line.split()
        pairs.append(f"{r}:{f}")
print(",".join(pairs))
EOF
)
    cd studies/mcport_validation_20261014
    /usr/bin/time -v python -u mc_compare.py runs --a "$PILOT_RUNS" --b "$WORK_DIR/runs" \
        --jobs "$JOBS" --out "$WORK_DIR/evidence/reproducibility_pilot_vs_fullrun.json"
    ;;
  sanity)
    python -u studies/cms_mc_weights_v3/fullrun/sanity_and_plots.py \
        --build-dir "$WORK_DIR/build_default" --prefix fullrun \
        --audit "$WORK_DIR/evidence/production_audit.json" \
        --out-dir "$WORK_DIR/evidence/plots"
    ;;
  *)
    echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac
rm -rf "$TMPDIR"
echo "Job $PBS_JOBID ($WHAT) finished at $(date)"
