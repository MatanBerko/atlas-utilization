# The exact commands run on wipp-home (ssh wipp-home 'bash -l -s' < this) on 9 Nov 2026: tier 6 (7 Z -> nunu HT bins),
# Matan's decision of 9 Nov (D11 a stands). Same pin, work dir and mappings as tiers 1-5 (the mappings were copied
# to $W/mappings by A2 on 3 Nov and are identical to studies/mc_expansion_20261103/mappings/). Output:
# submit_tier6_20261109.txt.
set -euo pipefail
B=/storage/agrp/berkom/atlas-utilization; C=6de9d3e605900a628bae372bdba4ea3308e9750f
R=$B/checkouts/mcexp_20261103/repo_$C; W=$B/work/mcexp_20261103/full; Q=/opt/pbs/bin/qsub
test "$(git -C $R rev-parse HEAD)" = $C && test -z "$(git -C $R status --porcelain)" && echo "checkout $C clean"
echo "quota before: $(lfs quota -u berkom /storage | tail -1 | awk '{print $6}')"
echo "my queued before: $(/opt/pbs/bin/qstat -u berkom -t 2>/dev/null | awk '$10=="Q"' | wc -l), running: $(/opt/pbs/bin/qstat -u berkom -t 2>/dev/null | awk '$10=="R"' | wc -l)"
# walltime: 4 x (A1 precheck wall of file 0 x size(largest file)/size(file 0)), rounded up on 2/3/6/12/24 h:
# the largest is 74904 (9.28 s x 60.15 = 558 s -> 0.62 h), so 2 h for all seven.
RECS="74894 74896 74898 74900 74902 74904 74906"
for rid in $RECS; do
  test -s $W/mappings/mapping_$rid.txt && test ! -e $W/runs/record$rid && test ! -e $W/logs/$rid
  ! grep -q "^$rid " $W/jobids.txt
done
echo "mappings present; no existing output/log/jobids line for the 7 records"
for rid in $RECS; do
  n=$(wc -l < $W/mappings/mapping_$rid.txt); wt=02:00:00
  mkdir -p $W/logs/$rid
  J=$($Q -J 1-$n -N mcexp_$rid -l mem=6gb,walltime=$wt,io=25 \
      -o "$W/logs/$rid/f_^array_index^.out" -e "$W/logs/$rid/f_^array_index^.err" \
      -v WORK_DIR=$W,REPO_DIR=$R,OUTPUT_BASE=$W/runs,MAPPING_FILE=$W/mappings/mapping_$rid.txt \
      $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh)
  echo "$rid $J $n $wt" | tee -a $W/jobids.txt
done
echo "jobids.txt: $(wc -l < $W/jobids.txt) lines, $(awk '{s+=$3} END{print s}' $W/jobids.txt) subjobs total"
sleep 5
echo "my queued after: $(/opt/pbs/bin/qstat -u berkom -t 2>/dev/null | awk '$10=="Q"' | wc -l), running: $(/opt/pbs/bin/qstat -u berkom -t 2>/dev/null | awk '$10=="R"' | wc -l)"
echo "quota after: $(lfs quota -u berkom /storage | tail -1 | awk '{print $6}')"
date
