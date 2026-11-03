#!/bin/bash
# MC expansion (written in A1, 3 Nov 2026; for A2/B): post-production stages that the existing
# launchers do not cover. Production = studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh (unchanged);
# audit and build = studies/cms_mc_weights_v3/fullrun/pbs_fullrun.sh WHAT=audit / build with
# EXPECTED_SW_FAILURES, REGISTRY, EXTRA_RUNS_DIR.
# Environment: REPO_DIR (pinned clone), WORK_DIR (= work/mcexp_20261103/full), WHAT [, RULE_RECORDS].
# WHAT:
#   gate          exit 0 only if $W/evidence/production_audit.json says "OK"
#   checks        studies/mc_expansion_20261103/post/checks_v4.py on $W/build_default (prefix fullrun)
#   rule_builds   for each record in RULE_RECORDS: per-sample builds, default (#40) rule and exact
#   rulecheck     studies/fullrun_20261025/rule_check.py --kind mc for each of those records (R1-R7)
#PBS -N mcexp_post
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
set -euo pipefail
W="${WORK_DIR:?WORK_DIR not set}"; R="${REPO_DIR:?REPO_DIR not set}"; WHAT="${WHAT:?WHAT not set}"
RULE_RECORDS="${RULE_RECORDS:-67801 69715 67841 64759}"
DATA=/storage/agrp/berkom/atlas-utilization/work/fullrun_20261025/deliver/data/CMS_Run2016GH_DoubleMuon-SingleMuon-DoubleEG-MuonEG-SingleElectron_16p393invfb_prod2026-10-25_data_bumpnet_uncropped.root
OLD=/storage/agrp/berkom/atlas-utilization/work/fullrun_20261025/mc/runs
V4=studies/cms_mc_weights_v3/cms_mc_normalisation_v4.json
source /usr/wipp/conda/24.5.0/etc/profile.d/conda.sh
conda activate /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
T="${TMPDIR:-/tmp}/mcexp_post_${PBS_JOBID:-local}"; mkdir -p "$T"; trap 'rm -rf "$T"' EXIT
export OMP_NUM_THREADS=1 HOME="$T/home" MPLCONFIGDIR="$T/mpl" XDG_CACHE_HOME="$T/cache" PYTHONDONTWRITEBYTECODE=1
mkdir -p "$HOME" "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$W/evidence"
cd "$R"
echo "Job ${PBS_JOBID:-local} WHAT=$WHAT commit=$(git rev-parse HEAD) host=$(hostname) $(date)"
case "$WHAT" in
  gate)
    python - "$W/evidence/production_audit.json" <<'PYEOF'
import json, sys
v = json.load(open(sys.argv[1]))["verdict"]
print("production audit verdict:", v)
sys.exit(0 if v == "OK" else 1)
PYEOF
    ;;
  checks)
    test ! -e "$W/evidence/checks_v4"
    python -u studies/mc_expansion_20261103/post/checks_v4.py --build-dir "$W/build_default" --prefix fullrun \
        --runs "$W/runs" --data-root "$DATA" --out "$W/evidence/checks_v4" \
        --data-runs /storage/agrp/berkom/atlas-utilization/work/fullrun_20261025/data/runs --mc-scratch "$W/scratch_default"
    ;;
  rule_builds)
    for rid in $RULE_RECORDS; do
      runs="$W/runs"; [ -d "$W/runs/record$rid" ] || runs="$OLD"
      for rule in upstream40 exact; do
        out="$W/rulecheck/$rid/$rule"; test ! -e "$out"
        extra=(); [ "$rule" = exact ] && extra=(--multiplicity-rule exact)
        /usr/bin/time -v python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py --runs-dir "$runs" \
            --records "$rid" --output-mode per-sample --out-dir "$out" --out-prefix "$rule" \
            --scratch-dir "$T/scratch" --registry "$V4" "${extra[@]}"
        rm -rf "$T/scratch"
      done
    done
    ;;
  rulecheck)
    rc=0
    for rid in $RULE_RECORDS; do
      python -u studies/fullrun_20261025/rule_check.py --kind mc \
          --exact-dir "$W/rulecheck/$rid/exact" --up40-dir "$W/rulecheck/$rid/upstream40" \
          --exact-prefix exact --up40-prefix upstream40 --record "$rid" \
          --out "$W/evidence/rule_check_mc_$rid.json" || rc=1
    done
    exit $rc
    ;;
  *) echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac
echo "WHAT=$WHAT done at $(date)"
