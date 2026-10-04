#!/bin/bash
# ---------------------------------------------------------------------------
# submit_step3_step4.sh (ttbar-count-vs-atlas study)
#
# Submits, from a PINNED checkout (REPO_DIR, which must not be touched until
# every job has finished):
#   * Step 3 proof 1 -- 4 data-mode regression jobs on the 4 pilot data files
#   * Step 3 proof 2 -- 1 matched --is-mc job on TTTo2L2Nu (67801) file 0
#   * Step 4         -- 2 notrigger --is-mc pilot jobs on 67801 files 0 and 1
#
# Nothing under output/ or work/cms_mc_v2/ is written: every job writes only
# under work/ttbar_count_vs_atlas/.
# ---------------------------------------------------------------------------
set -euo pipefail
export PATH=/opt/pbs/bin:$PATH

BASE=/storage/agrp/berkom/atlas-utilization/work/ttbar_count_vs_atlas
REPO_DIR="${REPO_DIR:-$BASE/pinned/repo}"
LOGS=/storage/agrp/berkom/atlas-utilization/logs/ttbar_count_vs_atlas
mkdir -p "$LOGS"

cd "$REPO_DIR"
echo "submitting from pinned checkout $REPO_DIR at commit $(git rev-parse HEAD)"

# --- Step 3 proof 1: data-mode regression, 4 files -------------------------
OUT_REGR="$BASE/step3_data_regression"
mkdir -p "$OUT_REGR"
J1=$(qsub -J 0-3 \
  -v "REPO_DIR=${REPO_DIR},OUTPUT_BASE=${OUT_REGR}" \
  -o "${LOGS}/step3_regr_^array_index^.out" \
  -e "${LOGS}/step3_regr_^array_index^.err" \
  studies/ttbar_count_vs_atlas/pbs_regression_data.sh)
echo "step3 data regression (4 jobs): $J1"

# --- Step 3 proof 2: matched --is-mc identity, TTTo2L2Nu file 0 ------------
OUT_IDENT="$BASE/step3_mc_identity"
mkdir -p "$OUT_IDENT"
J2=$(qsub \
  -v "REPO_DIR=${REPO_DIR},RECORD_ID=67801,DATASET_LABEL=DoubleMuon,FILE_INDEX=0,OUTPUT_BASE=${OUT_IDENT}" \
  -o "${LOGS}/step3_ident.out" \
  -e "${LOGS}/step3_ident.err" \
  studies/ttbar_count_vs_atlas/pbs_mc_matched_identity.sh)
echo "step3 mc matched identity (1 job): $J2"

# --- Step 4: notrigger pilot, TTTo2L2Nu files 0 and 1 ----------------------
OUT_PILOT="$BASE/step4_pilot"
mkdir -p "$OUT_PILOT"
J3=$(qsub -J 0-1 \
  -v "REPO_DIR=${REPO_DIR},RECORD_ID=67801,DATASET_LABEL=DoubleMuon,OUTPUT_BASE=${OUT_PILOT}" \
  -o "${LOGS}/step4_pilot_^array_index^.out" \
  -e "${LOGS}/step4_pilot_^array_index^.err" \
  studies/ttbar_count_vs_atlas/pbs_notrigger.sh)
echo "step4 notrigger pilot (2 jobs): $J3"
