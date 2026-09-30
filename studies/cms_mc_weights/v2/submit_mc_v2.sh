#!/bin/bash
set -euo pipefail
export PATH=/opt/pbs/bin:$PATH
cd /storage/agrp/berkom/atlas-utilization/work/cms_mc_v2/repo
mkdir -p /storage/agrp/berkom/atlas-utilization/logs/cms_mc_v2

WORK=/storage/agrp/berkom/atlas-utilization/work/cms_mc_v2

submit_one() {
  local RID="$1" NF="$2" LABEL="$3"
  local OUTBASE="$WORK/$RID"
  mkdir -p "$OUTBASE/$LABEL"
  local LAST=$((NF-1))
  JOBID=$(qsub -J "0-${LAST}" \
    -v "RECORD_ID=${RID},DATASET_LABEL=${LABEL},OUTPUT_BASE=${OUTBASE}" \
    -o "/storage/agrp/berkom/atlas-utilization/logs/cms_mc_v2/${RID}_${LABEL}_^array_index^.out" \
    -e "/storage/agrp/berkom/atlas-utilization/logs/cms_mc_v2/${RID}_${LABEL}_^array_index^.err" \
    studies/cms_mc_weights/v2/pbs_mc_v2.sh)
  echo "record $RID label $LABEL ($NF files): $JOBID"
}

# $1 = list of "record:nfiles" pairs to submit (both DoubleMuon and SingleMuon)
for spec in "$@"; do
  RID="${spec%%:*}"
  NF="${spec##*:}"
  submit_one "$RID" "$NF" "DoubleMuon"
  submit_one "$RID" "$NF" "SingleMuon"
done
