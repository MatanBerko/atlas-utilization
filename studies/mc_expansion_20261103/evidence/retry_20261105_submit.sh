# The exact commands run on wipp-home (ssh wipp-home 'bash -l -s') on 5 Nov 2026 ~20:10 IST: retry of the 93
# tier-4/5 subjobs that failed on 4 Nov with the CERN portal's 504. Outputs: retry_20261105_list.txt (built first by a
# read-only scan of $W/logs/<record>/f_<idx>.err: exit != 0 AND "504 Server Error" AND "record API not reachable";
# columns record, array_index, file_index, files_in_folder), retry_20261105_moved_folders.txt,
# retry_20261105_submitted.txt.
set -euo pipefail
B=/storage/agrp/berkom/atlas-utilization; C=6de9d3e605900a628bae372bdba4ea3308e9750f
R=$B/checkouts/mcexp_20261103/repo_$C; W=$B/work/mcexp_20261103/full; Q=/opt/pbs/bin/qsub
L=$W/evidence/retry_20261105_list.txt; F=$W/failed_20261104_portal504
test "$(git -C $R rev-parse HEAD)" = $C && test -z "$(git -C $R status --porcelain)"
test ! -e $F && test ! -e $W/jobids_retry1.txt
M=$W/evidence/retry_20261105_moved_folders.txt; : > $M
while read r idx fi nf; do
  d=$W/runs/record$r/job_$fi
  [ -d "$d" ] && [ -z "$(find "$d" -mindepth 1 -print -quit)" ] || { echo "NOT EMPTY/MISSING $d"; exit 1; }
  mkdir -p $F/$r; mv -n "$d" $F/$r/; test -d $F/$r/job_$fi && test ! -e "$d"
  echo "$d -> $F/$r/job_$fi" >> $M
done < $L
S=$W/evidence/retry_20261105_submitted.txt; : > $S
while read r idx fi nf; do
  wt=$(awk -v r=$r '$1==r && $2 ~ /^54390(3[89]|[4-6][0-9])/ {print $4}' $W/jobids.txt)   # the A2b-1 walltime
  [ -n "$wt" ] || { echo "no walltime for $r"; exit 1; }
  o=$W/logs/$r/f_${idx}_retry1; test ! -e $o.out && test ! -e $o.err
  J=$($Q -N mcexp_${r}_r1 -l mem=6gb,walltime=$wt,io=25 -o $o.out -e $o.err \
      -v WORK_DIR=$W,REPO_DIR=$R,OUTPUT_BASE=$W/runs,MAPPING_FILE=$W/mappings/mapping_$r.txt,PILOT_ARRAY_INDEX=$idx \
      $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh)
  echo "$r $J 1 $wt retry1 array_index=$idx file_index=$fi" | tee -a $W/jobids_retry1.txt >> $S
done < $L
