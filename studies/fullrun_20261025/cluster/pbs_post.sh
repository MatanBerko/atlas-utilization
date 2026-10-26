#!/bin/bash
# Full run 25 Oct 2026: the post-production stages that the existing launchers
# do not cover for FIVE datasets. ADDED; no existing launcher is changed.
#   - electron_vB/cluster/pbs_delivery.sh passes no --datasets, and the data
#     builder's default is the FOUR-dataset list, so it would leave out
#     SingleElectron;
#   - electron_vB/check_production_complete.py checks four datasets only;
#   - fullrun/audit_production.py always exits 0 and OpenPBS afterok on an
#     array does not stop when a subjob failed (tested 24 Oct, HANDOFF.md), so
#     the MC build is gated here on the audit's verdict instead.
# MC production, the MC build, the MC audit and the MC sanity plots stay on
# the existing pbs_mc_pilot.sh and fullrun/pbs_fullrun.sh, unchanged.
#
# Environment: REPO_DIR (pinned clone), WORK_DIR (= work/fullrun_20261025), WHAT.
# Layout: $W/data/runs/{<Dataset>_index.json, <Dataset>/job_<n>/},
#         $W/mc/{mappings,runs,logs,jobids.txt,evidence,build_default}.
# WHAT:
#   data_check     check_production_complete_5.py; non-zero exit if anything is missing
#   data_build     data builder, five datasets, all other options default -> $W/data/deliver/default
#   data_exact     the same with --multiplicity-rule exact (input of the rule check only)
#   data_checks    rule_check.py --kind data, make_delivery_plots.py
#   mc_gate        exit 0 only if $W/mc/evidence/production_audit.json says "OK"
#   mc_rule_builds MC builder on record 67801, per-sample, default rule and exact
#                  (the method of studies/multiplicity40_20261023), node scratch
#   mc_rulecheck   rule_check.py --kind mc on those two builds
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

W="${WORK_DIR:?WORK_DIR not set}"
R="${REPO_DIR:?REPO_DIR not set}"
WHAT="${WHAT:?WHAT not set}"
FIVE=DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
T="${TMPDIR:-/tmp}/fr25post_${PBS_JOBID:-local}"
mkdir -p "$T"
trap 'rm -rf "$T"' EXIT
# Nothing is written to $HOME by this job.
export HOME="$T/home" MPLCONFIGDIR="$T/mpl" XDG_CACHE_HOME="$T/cache"
mkdir -p "$HOME" "$MPLCONFIGDIR" "$XDG_CACHE_HOME"
source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$R"
echo "Job ${PBS_JOBID:-local} WHAT=$WHAT commit=$(git rev-parse HEAD) host=$(hostname) $(date)"
df -h "$T" | tail -1
E="$W/data/evidence"

data_build() {  # data_build <out dir name> [extra args...]
    local out="$W/data/deliver/$1"; shift
    test ! -e "$out"   # never overwrite an existing output
    TMPDIR="$T" /usr/bin/time -v python -u studies/cms_datasets/deliver/build_four_dataset_delivery.py \
        --runs-dir "$W/data/runs" --datasets "$FIVE" \
        --out-dir "$out" --out-prefix fullrun "$@"
}

mc_rule_build() {  # mc_rule_build <out dir name> <prefix> [extra args...]
    local out="$W/mc/rulecheck/$1" prefix="$2"; shift 2
    test ! -e "$out"
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
        --runs-dir "$W/mc/runs" --records 67801 --output-mode per-sample \
        --out-dir "$out" --out-prefix "$prefix" --scratch-dir "$T/scratch" "$@"
    rm -rf "$T/scratch"
}

case "$WHAT" in
  data_check)
    mkdir -p "$E"
    python -u studies/fullrun_20261025/check_production_complete_5.py \
        --runs-root "$W/data/runs" --out "$E/production_complete.json"
    ;;
  data_build) data_build default ;;
  data_exact) data_build exact --multiplicity-rule exact ;;
  data_checks)
    mkdir -p "$E"
    rc=0
    python -u studies/fullrun_20261025/rule_check.py --kind data \
        --exact-dir "$W/data/deliver/exact" --up40-dir "$W/data/deliver/default" \
        --exact-prefix fullrun --up40-prefix fullrun --out "$E/rule_check_data.json" || rc=1
    python -u studies/cms_datasets/electron_vB/make_delivery_plots.py \
        --runs-root "$W/data/runs" --delivery-dir "$W/data/deliver/default" \
        --out-dir "$E/plots" --out-json "$E/delivery_plot_inputs.json" || rc=1
    echo "data_checks rc=$rc"
    exit $rc
    ;;
  mc_gate)
    python - "$W/mc/evidence/production_audit.json" <<'PYEOF'
import json, sys
v = json.load(open(sys.argv[1]))["verdict"]
print("production audit verdict:", v)
sys.exit(0 if v == "OK" else 1)
PYEOF
    ;;
  mc_rule_builds)
    mc_rule_build upstream40 upstream40
    mc_rule_build exact exact --multiplicity-rule exact
    ;;
  mc_rulecheck)
    mkdir -p "$W/mc/evidence"
    python -u studies/fullrun_20261025/rule_check.py --kind mc \
        --exact-dir "$W/mc/rulecheck/exact" --up40-dir "$W/mc/rulecheck/upstream40" \
        --exact-prefix exact --up40-prefix upstream40 --record 67801 \
        --out "$W/mc/evidence/rule_check_mc.json"
    ;;
  *)
    echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac
echo "WHAT=$WHAT done at $(date)"
