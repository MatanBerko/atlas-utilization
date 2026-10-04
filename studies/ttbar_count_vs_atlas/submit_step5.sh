#!/bin/bash
# ---------------------------------------------------------------------------
# submit_step5.sh (ttbar_count_vs_atlas, Step 5)
#
# Full --population notrigger --is-mc run: every file of MC record 67801
# (TTTo2L2Nu), one PBS array element per file.
#
# Submitted from a PINNED checkout (REPO_DIR), which must not be touched
# until every job has finished. Writes only under
# work/ttbar_count_vs_atlas/step5_full/.
#
#   REPO_DIR=<pinned repo> bash submit_step5.sh [N_FILES]
# ---------------------------------------------------------------------------
set -euo pipefail
export PATH=/opt/pbs/bin:$PATH

BASE=/storage/agrp/berkom/atlas-utilization/work/ttbar_count_vs_atlas
REPO_DIR="${REPO_DIR:-$BASE/pinned/repo}"
LOGS=/storage/agrp/berkom/atlas-utilization/logs/ttbar_count_vs_atlas
RECORD_ID="${RECORD_ID:-67801}"
N_FILES="${1:-49}"
OUT="$BASE/step5_full"

mkdir -p "$LOGS" "$OUT"
cd "$REPO_DIR"
echo "submitting from pinned checkout $REPO_DIR at commit $(git rev-parse HEAD)"
echo "record $RECORD_ID, $N_FILES files"

LAST=$((N_FILES - 1))
JOBID=$(qsub -J "0-${LAST}" \
  -v "REPO_DIR=${REPO_DIR},RECORD_ID=${RECORD_ID},DATASET_LABEL=DoubleMuon,OUTPUT_BASE=${OUT}" \
  -o "${LOGS}/step5_^array_index^.out" \
  -e "${LOGS}/step5_^array_index^.err" \
  studies/ttbar_count_vs_atlas/pbs_notrigger.sh)
echo "step5 full notrigger run ($N_FILES jobs): $JOBID"
echo "$JOBID" > "$OUT/pbs_job_id.txt"
