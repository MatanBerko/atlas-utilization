#!/bin/bash
# Nominal-6 production (28 Nov 2026), run on wipp-home in bash -l. One PBS array per sample, from the pin 6de9d3e,
# studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh unchanged, into the NEW runs dir nominal6_runs_20261128/runs.
# Same submit_tier pattern as studies/mc_expansion_20261103/evidence/submit_A2_batch1.sh; jobids.txt in its format
# "<record> <job> <n> <walltime>" (the format audit_production.py reads).
set -euo pipefail
B=/storage/agrp/berkom/atlas-utilization
C=6de9d3e605900a628bae372bdba4ea3308e9750f
R=$B/checkouts/mcexp_20261103/repo_$C
W=$B/work/mcexp_20261103/nominal6_runs_20261128
Q=/opt/pbs/bin/qsub
test "$(git -C $R rev-parse HEAD)" = $C
test -z "$(git -C $R status --porcelain)"
test -d $W/mappings && test ! -e $W/runs && test ! -e $W/jobids.txt
mkdir -p $W/runs $W/logs
while read -r rid wt; do
  n=$(wc -l < $W/mappings/mapping_$rid.txt)
  mkdir -p $W/logs/$rid
  J=$($Q -J 1-$n -N n6_$rid -l mem=6gb,walltime=$wt,io=25 \
      -o "$W/logs/$rid/f_^array_index^.out" -e "$W/logs/$rid/f_^array_index^.err" \
      -v WORK_DIR=$W,REPO_DIR=$R,OUTPUT_BASE=$W/runs,MAPPING_FILE=$W/mappings/mapping_$rid.txt \
      $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh)
  echo "$rid $J $n $wt" | tee -a $W/jobids.txt
done <<'LIST'
75561 06:00:00
72648 02:00:00
71636 06:00:00
71640 06:00:00
74314 24:00:00
72720 48:00:00
LIST
test "$(wc -l < $W/jobids.txt)" = 6
echo "subjobs: $(awk '{s+=$3} END {print s}' $W/jobids.txt)"
