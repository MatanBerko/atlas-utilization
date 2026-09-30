#!/bin/bash
set -euo pipefail
export PATH=/opt/pbs/bin:$PATH
cd /storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1/repo
mkdir -p /storage/agrp/berkom/atlas-utilization/logs/cms_mc_phase1

RIDS="64895 64839 72676 72752 75589 68187 68073 35669"
NFILES="11 10 7 31 99 42 12 41"

set -- $NFILES
for RID in $RIDS; do
  NF=$1
  shift
  OUTBASE=/storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1/$RID
  mkdir -p "$OUTBASE"
  LAST=$((NF-1))
  JOBID=$(qsub -J "0-${LAST}" \
    -v RECORD_ID=$RID,OUTPUT_BASE=$OUTBASE \
    -o /storage/agrp/berkom/atlas-utilization/logs/cms_mc_phase1/${RID}_^array_index^.out \
    -e /storage/agrp/berkom/atlas-utilization/logs/cms_mc_phase1/${RID}_^array_index^.err \
    studies/m0m1j0_cms/cluster/pbs_m0m1j0_mc_phase1.sh)
  echo "record $RID ($NF files): $JOBID"
done
