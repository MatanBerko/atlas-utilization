#!/bin/bash
# ttbar PR #40 test (21 Oct 2026): every post-production stage as a PBS job.
# Production itself is studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh,
# unchanged.
#
# WHAT selects the stage (REPO_DIR = the pinned checkout to run from):
#   audit        audit_production.py over $WORK_DIR/runs and the mapping
#   build_exact  builder, --multiplicity-rule exact -> build_exact/
#   build_pr40   builder, --multiplicity-rule pr40  -> build_pr40/
#   build_base   the UNMODIFIED builder (REPO_DIR = the cd22aa2 checkout)
#                -> build_base/
#   compare      compare_builds.py, build_exact vs build_base, bit for bit
#   rulecheck    rule_check.py (R1-R7) and check_oracle.py against
#                c2488b7's own code ($WORK_DIR/evidence/oracle_c2488b7.tar,
#                unpacked into $TMPDIR, never into a checkout)
# Every build: --records 67801 --output-mode per-sample, all other options
# at their defaults. An existing output directory is never overwritten.
#PBS -N ttpr40_post
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

W="${WORK_DIR:?WORK_DIR not set}"
REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
WHAT="${WHAT:?WHAT not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
STUDY=studies/cms_ttbar_pr40_20261021

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
# Nothing is written to $HOME by this job.
export MPLCONFIGDIR="${W}/.mplconfig"
export XDG_CACHE_HOME="${W}/.cache"
export HOME="${W}/.jobhome"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$HOME"

# Builder scratch: node-local $TMPDIR when it has >= 30 GB free, otherwise
# inside the work dir. The builder removes it when it finishes.
T="${TMPDIR:-}"
if [[ -n "$T" && -d "$T" ]] && (( $(df -Pk "$T" | awk 'NR==2 {print $4}') >= 30*1024*1024 )); then
    SCRATCH="$T/scratch_${WHAT}"
else
    SCRATCH="$W/scratch_${WHAT}"
fi

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

echo "Job ${PBS_JOBID:-local} on $(hostname) at $(date)"
echo "commit=$(git rev-parse HEAD)  WHAT=$WHAT  scratch=$SCRATCH"
ulimit -n || true

build() {  # build <rule|base> <out dir name> <prefix>
    test ! -e "$W/$2"   # never overwrite an existing output
    local rule_args=()
    if [[ "$1" != "base" ]]; then
        rule_args=(--multiplicity-rule "$1")
    fi
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
        --runs-dir "$W/runs" --records 67801 --output-mode per-sample \
        --out-dir "$W/$2" --out-prefix "$3" --scratch-dir "$SCRATCH" \
        ${rule_args[@]+"${rule_args[@]}"}
}

case "$WHAT" in
  audit)
    python -u "$STUDY/audit_production.py" --work "$W" \
        --mapping "$W/mappings/mapping_67801.txt" --out "$W/evidence/production_audit.json"
    ;;
  build_exact) build exact build_exact exact ;;
  build_pr40)  build pr40  build_pr40  pr40 ;;
  build_base)  build base  build_base  base ;;
  compare)
    python -u "$STUDY/compare_builds.py" \
        --a "$W/build_exact/exact_record67801_mc.root" \
        --b "$W/build_base/base_record67801_mc.root" \
        --out "$W/evidence/compare_exact_vs_base.json"
    ;;
  rulecheck)
    python -u "$STUDY/rule_check.py" --exact-dir "$W/build_exact" --pr40-dir "$W/build_pr40" \
        --out "$W/evidence/rule_check.json"
    python -u "$STUDY/check_oracle.py" --side cms --out "$W/evidence/oracle_answers.json" \
        --report "$W/build_pr40/pr40_build_report.json" \
        --exact-report "$W/build_exact/exact_build_report.json" --runs-dir "$W/runs"
    O="${T:-$W}/oracle_c2488b7_${PBS_JOBID:-local}"
    mkdir -p "$O"
    tar -xf "$W/evidence/oracle_c2488b7.tar" -C "$O"
    echo "oracle: commit $(git get-tar-commit-id < "$W/evidence/oracle_c2488b7.tar")"
    (cd "$O" && python -I -u "$REPO_DIR/$STUDY/check_oracle.py" --side oracle --oracle-tree "$O" \
        --answers "$W/evidence/oracle_answers.json" --out "$W/evidence/oracle_result.json")
    rm -rf "$O"
    ;;
  *)
    echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac
echo "done at $(date)"
