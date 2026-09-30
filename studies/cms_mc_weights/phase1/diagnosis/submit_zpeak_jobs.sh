#!/bin/bash
set -euo pipefail
export PATH=/opt/pbs/bin:$PATH
cd /storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1/repo
mkdir -p /storage/agrp/berkom/atlas-utilization/logs/cms_mc_phase1_zpeak

WORK=/storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1/diagnosis_zpeak

submit_one() {
  local RID="$1" NF="$2" ISMC="$3"
  local OUTBASE="$WORK/$RID"
  mkdir -p "$OUTBASE"
  local LAST=$((NF-1))
  local VFLAG=""
  if [[ "$ISMC" == "1" ]]; then VFLAG=",IS_MC=1"; fi
  JOBID=$(qsub -J "0-${LAST}" \
    -v "RECORD_ID=${RID},OUTPUT_BASE=${OUTBASE}${VFLAG}" \
    -o "/storage/agrp/berkom/atlas-utilization/logs/cms_mc_phase1_zpeak/${RID}_^array_index^.out" \
    -e "/storage/agrp/berkom/atlas-utilization/logs/cms_mc_phase1_zpeak/${RID}_^array_index^.err" \
    studies/cms_mc_weights/phase1/diagnosis/pbs_zpeak_reader.sh)
  echo "record $RID ($NF files, is_mc=$ISMC): $JOBID"
}

submit_one 30522 29 0
submit_one 30555 28 0
submit_one 35671 61 1
submit_one 35669 41 1
submit_one 67801 49 1
