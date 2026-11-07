# The exact commands run on wipp-home (ssh wipp-home 'bash -l -s' < this) on 7 Nov 2026 for D15: the 4 released
# rare-top samples as full-production arrays, from the same pin and into the same work dir as tiers 1-5.
# The mapping files (studies/mc_expansion_20261103/mappings/mapping_<rid>.txt, make_d15_mappings.py) were first
# copied to $W/evidence/d15_mappings_incoming/ by scp. Output: submit_D15_raretop.txt.
set -euo pipefail
B=/storage/agrp/berkom/atlas-utilization; C=6de9d3e605900a628bae372bdba4ea3308e9750f
R=$B/checkouts/mcexp_20261103/repo_$C; W=$B/work/mcexp_20261103/full; Q=/opt/pbs/bin/qsub
test "$(git -C $R rev-parse HEAD)" = $C && test -z "$(git -C $R status --porcelain)" && echo "checkout $C clean"
echo "quota before: $(lfs quota -u berkom /storage | tail -1 | awk '{print $6}')"
echo "my queued before: $(/opt/pbs/bin/qstat -u berkom -t 2>/dev/null | awk '$10=="Q"' | wc -l), running: $(/opt/pbs/bin/qstat -u berkom -t 2>/dev/null | awk '$10=="R"' | wc -l)"
# walltime: 4 x (precheck wall of file 0 x size(largest file)/size(file 0)), rounded up on 2/3/6/12/24 h
declare -A WT=([68325]=06:00:00 [64873]=24:00:00 [68206]=12:00:00 [68185]=24:00:00)
for rid in 68325 64873 68206 68185; do
  test ! -e $W/mappings/mapping_$rid.txt && test ! -e $W/runs/record$rid && test ! -e $W/logs/$rid
  ! grep -q "^$rid " $W/jobids.txt
done
echo "no existing mapping/output/log/jobids line for the 4 records"
for rid in 68325 64873 68206 68185; do
  cp -n $W/evidence/d15_mappings_incoming/mapping_$rid.txt $W/mappings/mapping_$rid.txt
  n=$(wc -l < $W/mappings/mapping_$rid.txt); wt=${WT[$rid]}
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
