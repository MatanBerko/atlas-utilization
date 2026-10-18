#!/bin/bash
# CMS MC peak fix (18-19 Oct 2026): every stage that reads ROOT files or
# builds, as a PBS job. WHAT selects the stage:
#   verify   step 0: peakfix/verify_finding.py on the full-run build (read-only)
#PBS -N mcpeak
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

WORK_DIR="${WORK_DIR:?WORK_DIR not set}"
REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
WHAT="${WHAT:?WHAT not set}"
FULLRUN="/storage/agrp/berkom/atlas-utilization/work/fullrun_20261017"   # read-only
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

case "$WHAT" in
  verify)
    python -u studies/cms_mc_weights_v3/peakfix/verify_finding.py \
        --build-dir "$FULLRUN/build_default" --prefix fullrun \
        --out "$WORK_DIR/evidence/step0_verify_finding.json"
    ;;
  *)
    echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac
rm -rf "$TMPDIR"
echo "Job $PBS_JOBID ($WHAT) finished at $(date)"
