#!/bin/bash
set -euo pipefail
source /usr/wipp/conda/24.5.0/etc/profile.d/conda.sh
conda activate /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
cd /storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1/repo

WORK=/storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1

for spec in "64895:11" "64839:10" "72676:7" "72752:31" "75589:99" "68187:42" "68073:12" "35669:41"; do
  RID="${spec%%:*}"
  NF="${spec##*:}"
  mkdir -p "studies/cms_mc_weights/phase1/${RID}"
  echo "=== merging ${RID} (${NF} files) ==="
  python -u studies/m0m1j0_cms/cluster/merge_full_v2_mc.py \
    --record-id "${RID}" \
    --jobs-base "${WORK}/${RID}" \
    --n-files "${NF}" \
    --out-dir "studies/cms_mc_weights/phase1/${RID}"

  echo "=== V1/V2 for ${RID} ==="
  python -u studies/cms_mc_weights/phase1/validate_v1_v2.py \
    --record-id "${RID}" \
    --jobs-base "${WORK}/${RID}" \
    --merge-summary "studies/cms_mc_weights/phase1/${RID}/merge_mc_summary.json" \
    --out "studies/cms_mc_weights/phase1/${RID}/validate_v1_v2_result.json"
done

echo "ALL D4 MERGES DONE"
