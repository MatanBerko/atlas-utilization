#!/bin/bash
# The #40 multiplicity rule as the builders' default (23 Oct 2026), step 3:
# proof on EXISTING per-file outputs (read-only), no new production.
#
# Pinned checkouts (fresh clones of origin, detached):
#   $CHECKOUTS/data  feature/cms-data-multiplicity40-20261023  (the data builder)
#   $CHECKOUTS/mc    feature/cms-mc-multiplicity40-20261023    (MC builder + these scripts)
# Inputs (READ-ONLY):
#   $TT  = work/ttbar_pr40_20261021: runs/ (49 ttbar 67801 files), build_pr40/, build_exact/
#   $S42 = work/sync42_20261023: runs/new/data (five per-file outputs, data-branch NEW side,
#          with their <Dataset>_index.json), deliver/new/data (that proof's NEW data delivery)
#
# WHAT selects the stage; every output directory is new and never overwritten:
#   mc_upstream40   MC builder, DEFAULT rule  -> $W/mc/build_upstream40 (prefix upstream40)
#   mc_exact        MC builder, --multiplicity-rule exact -> $W/mc/build_exact (prefix exact)
#                   both with the ttbar study's options: --records 67801 --output-mode per-sample
#   data_upstream40 data five-dataset builder, DEFAULT rule -> $W/data/upstream40 (prefix proof)
#   data_exact      data builder, --multiplicity-rule exact -> $W/data/exact (prefix proof)
#                   both with the sync42 proof's options: --datasets <five> --out-prefix proof
#   check           every comparison and rule check into $W/evidence/
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

W="${WORK_DIR:?WORK_DIR not set}"
CO="${CHECKOUTS:?CHECKOUTS not set}"
WHAT="${WHAT:?WHAT not set}"
B=/storage/agrp/berkom/atlas-utilization
TT="$B/work/ttbar_pr40_20261021"
S42="$B/work/sync42_20261023"
FIVE=DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="$B/envs/atlas-pipeline"
STUDY=studies/multiplicity40_20261023

export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
T="${TMPDIR:-/tmp}/mult40_${PBS_JOBID:-local}"
mkdir -p "$T"
trap 'rm -rf "$T"' EXIT
# Nothing is written to $HOME by this job.
export HOME="$T/home" MPLCONFIGDIR="$T/mpl" XDG_CACHE_HOME="$T/cache"
mkdir -p "$HOME" "$MPLCONFIGDIR" "$XDG_CACHE_HOME"
source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

echo "Job ${PBS_JOBID:-local} WHAT=$WHAT on $(hostname) at $(date)"
for c in data mc; do echo "checkout $c: $(git -C "$CO/$c" rev-parse HEAD)"; done
df -h "$T" | tail -1

mc_build() {  # mc_build <out dir name> <prefix> [rule args...]
    local out="$W/mc/$1" prefix="$2"; shift 2
    test ! -e "$out"   # never overwrite an existing output
    cd "$CO/mc"
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
        --runs-dir "$TT/runs" --records 67801 --output-mode per-sample \
        --out-dir "$out" --out-prefix "$prefix" --scratch-dir "$T/scratch" "$@"
}

data_build() {  # data_build <out dir name> [rule args...]
    local out="$W/data/$1"; shift
    test ! -e "$out"
    cd "$CO/data"
    TMPDIR="$T" /usr/bin/time -v python -u studies/cms_datasets/deliver/build_four_dataset_delivery.py \
        --runs-dir "$S42/runs/new/data" --datasets "$FIVE" \
        --out-dir "$out" --out-prefix proof "$@"
}

case "$WHAT" in
  mc_upstream40)   mc_build build_upstream40 upstream40 ;;
  mc_exact)        mc_build build_exact exact --multiplicity-rule exact ;;
  data_upstream40) data_build upstream40 ;;
  data_exact)      data_build exact --multiplicity-rule exact ;;
  check)
    E="$W/evidence"
    mkdir -p "$E"
    cd "$CO/mc"
    rc=0
    python -u "$STUDY/compare_root.py" \
        --a "$TT/build_pr40/pr40_record67801_mc.root" \
        --b "$W/mc/build_upstream40/upstream40_record67801_mc.root" \
        --out "$E/compare_mc_upstream40_vs_ttbar_build_pr40.json" || rc=1
    python -u "$STUDY/compare_root.py" \
        --a "$TT/build_exact/exact_record67801_mc.root" \
        --b "$W/mc/build_exact/exact_record67801_mc.root" \
        --out "$E/compare_mc_exact_vs_ttbar_build_exact.json" || rc=1
    for f in proof_bumpnet.root proof_bumpnet_cropped.root; do
        python -u "$STUDY/compare_root.py" --a "$S42/deliver/new/data/$f" --b "$W/data/exact/$f" \
            --out "$E/compare_data_exact_vs_sync42_new_${f%.root}.json" || rc=1
    done
    # The sync42 method (compare.py, unchanged): ROOT files plus the summary
    # and manifest JSONs. The summary is expected to differ by exactly one
    # added key, "multiplicity_rule": "exact".
    (cd studies/mcport_validation_20261014 && python -u compare.py delivery \
        --a "$S42/deliver/new/data" --b "$W/data/exact" \
        --a-runs "$S42/runs/new/data" --b-runs "$S42/runs/new/data" --prefix proof \
        --out "$E/compare_data_exact_vs_sync42_new_delivery.json") || true
    python -u "$STUDY/rule_check.py" --kind data \
        --exact-dir "$W/data/exact" --up40-dir "$W/data/upstream40" \
        --exact-prefix proof --up40-prefix proof --out "$E/rule_check_data.json" || rc=1
    python -u "$STUDY/rule_check.py" --kind mc \
        --exact-dir "$W/mc/build_exact" --up40-dir "$W/mc/build_upstream40" \
        --exact-prefix exact --up40-prefix upstream40 --out "$E/rule_check_mc.json" || rc=1
    echo "check rc=$rc"
    exit $rc
    ;;
  *)
    echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac
echo "done at $(date)"
