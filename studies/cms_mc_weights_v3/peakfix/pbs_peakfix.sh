#!/bin/bash
# CMS MC peak fix (18-19 Oct 2026): every stage that reads ROOT files or
# builds, as a PBS job. WHAT selects the stage:
#   verify   step 0: peakfix/verify_finding.py on the full-run build (read-only)
#   build    step 3: build_mc_delivery.py --peak-scope combined over the full
#            run's runs/ (read-only); all other options default; no
#            --keep-scratch -- the builder removes its scratch dir, and this
#            job removes it on any exit (it creates it, so only its own files)
#   compare  step 4: peakfix/compare_old_new.py, old full-run build vs new
#   datamc   steps 5-6: peakfix/data_vs_mc.py, data delivery vs new build
#   zpeak    step 6: peakfix/z_peak_ratio.py, Z-peak data/MC from stored events
# ROOT inputs of compare/datamc are first copied to node-local /dev/shm (one
# sequential read; uproot's many small reads are slow on the shared disk);
# the copy is removed on exit.
#PBS -N mcpeak
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

WORK_DIR="${WORK_DIR:?WORK_DIR not set}"
REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
WHAT="${WHAT:?WHAT not set}"
B=/storage/agrp/berkom/atlas-utilization
FULLRUN="$B/work/fullrun_20261017"                                   # read-only
DELIVERY="$B/output/cms_datasets/deliver/four_dataset_vB_upstreamnames_w10p0_dr012_20261007"  # read-only
DATA_ROOT="$DELIVERY/four_dataset_matched_vB_upstreamnames_w10p0_dr012_bumpnet.root"
DATA_RUNS="$B/output/cms_datasets/runs_matched4_full_20261007"      # read-only
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="$B/envs/atlas-pipeline"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
# Nothing is written to $HOME by this job.
export MPLCONFIGDIR="${WORK_DIR}/.mplconfig"
export XDG_CACHE_HOME="${WORK_DIR}/.cache"
export HOME="${WORK_DIR}/.jobhome"
export TMPDIR="${WORK_DIR}/tmp_${WHAT}"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$HOME" "$TMPDIR"

LOCAL=""
SCRATCH=""
cleanup() {
  [ -n "$LOCAL" ] && rm -rf "$LOCAL"
  [ -n "$SCRATCH" ] && rm -rf "$SCRATCH"
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

# copy the *_mc.root files of a build dir (or one file) to $LOCAL/<sub>/
stage() {
  local sub="$1"; shift
  mkdir -p "$LOCAL/$sub"
  cp "$@" "$LOCAL/$sub/"
}

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

echo "Job $PBS_JOBID on $(hostname) at $(date)"
echo "commit=$(git rev-parse HEAD)  WHAT=$WHAT"
P=studies/cms_mc_weights_v3/peakfix

case "$WHAT" in
  verify)
    python -u $P/verify_finding.py \
        --build-dir "$FULLRUN/build_default" --prefix fullrun \
        --out "$WORK_DIR/evidence/step0_verify_finding.json"
    ;;
  build)
    test ! -e "$WORK_DIR/build_combined"   # never overwrite an existing output
    test ! -e "$WORK_DIR/scratch_build"
    SCRATCH="$WORK_DIR/scratch_build"
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
        --runs-dir "$FULLRUN/runs" \
        --out-dir "$WORK_DIR/build_combined" --out-prefix peakfix \
        --scratch-dir "$SCRATCH" --peak-scope combined
    echo "scratch left behind by the builder: $(test -e "$SCRATCH" && echo yes || echo no)"
    ;;
  compare)
    test ! -e "$WORK_DIR/evidence/compare"
    LOCAL=$(mktemp -d /dev/shm/mcpeak_XXXXXX)
    stage old "$FULLRUN"/build_default/fullrun_*_mc.root
    stage new "$WORK_DIR"/build_combined/peakfix_*_mc.root
    python -u $P/compare_old_new.py \
        --old-dir "$LOCAL/old" --old-prefix fullrun \
        --new-dir "$LOCAL/new" --new-prefix peakfix \
        --out-dir "$WORK_DIR/evidence/compare"
    ;;
  datamc)
    test ! -e "$WORK_DIR/evidence/data_mc"
    LOCAL=$(mktemp -d /dev/shm/mcpeak_XXXXXX)
    stage new "$WORK_DIR"/build_combined/peakfix_*_mc.root
    stage data "$DATA_ROOT"
    python -u $P/data_vs_mc.py \
        --data "$LOCAL/data/$(basename "$DATA_ROOT")" \
        --new-dir "$LOCAL/new" --new-prefix peakfix \
        --out-dir "$WORK_DIR/evidence/data_mc"
    ;;
  zpeak)
    test ! -e "$WORK_DIR/evidence/zpeak"
    /usr/bin/time -v python -u $P/z_peak_ratio.py \
        --data-runs-dir "$DATA_RUNS" --mc-scratch-dir "$FULLRUN/scratch_default" \
        --out-dir "$WORK_DIR/evidence/zpeak"
    ;;
  *)
    echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac
echo "Job $PBS_JOBID ($WHAT) finished at $(date)"
