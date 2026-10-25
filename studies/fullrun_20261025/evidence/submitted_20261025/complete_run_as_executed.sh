set -euo pipefail
B=/storage/agrp/berkom/atlas-utilization
CK=$B/checkouts/fullrun_20261025; W=$B/work/fullrun_20261025
C=75b399e2dfdacc50affd4e2c78bc865b12f000cc; R=$CK/repo_75b399e
Q=/opt/pbs/bin/qsub
test "$(git -C $R rev-parse HEAD)" = $C
echo "start $(date --iso-8601=seconds) on $(hostname)"
# guards
[ ! -e $W/post_jobids.txt ] || { echo "STOP: post_jobids exists"; exit 9; }
if /opt/pbs/bin/qstat -x -f 2>/dev/null | grep -qE "Job_Name = (mcfull_37728|fr25_data_|fr25_mc_|mcfull_post)"; then echo "STOP: job already exists"; exit 9; fi
NQR=$(/opt/pbs/bin/qstat -t -u berkom | tail -n +6 | grep -v "\[\]" | awk '$10=="Q"||$10=="R"||$10=="H"' | wc -l)
echo "queued+running+held pieces: $NQR"
MC_OK=0
if [ "$NQR" -le 990 ]; then
  # step 1: record 37728, exactly the MC loop body of the block
  rid=37728
  n=$(wc -l < $W/mc/mappings/mapping_$rid.txt); wt=02:00:00; case $rid in 68187|68073) wt=03:00:00;; esac
  mkdir -p $W/mc/logs/$rid
  if J=$($Q -J 1-$n -N mcfull_$rid -l mem=6gb,walltime=$wt,io=25 \
      -o "$W/mc/logs/$rid/f_^array_index^.out" -e "$W/mc/logs/$rid/f_^array_index^.err" \
      -v WORK_DIR=$W/mc,REPO_DIR=$R,OUTPUT_BASE=$W/mc/runs,MAPPING_FILE=$W/mc/mappings/mapping_$rid.txt \
      $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh); then
    echo "$rid $J $n $wt" | tee -a $W/mc/jobids.txt
    echo "mc/jobids.txt lines: $(wc -l < $W/mc/jobids.txt)"
    MC_OK=1
  else
    echo "37728 qsub REFUSED -> MC post jobs will not be submitted"
  fi
else
  echo "count > 990 -> 37728 and MC post jobs not submitted"
fi
# step 2: dependency lists from arrays NOT finished now
unfinished() { while read -r _ id _rest; do st=$(/opt/pbs/bin/qstat -x "$id" | tail -1 | awk '{print $10}'); if [ "$st" = F ]; then echo "LEFT OUT (finished): $id" >&2; else printf ":%s" "$id"; fi; done < "$1"; }
DATA_ARR=$(unfinished $W/data/jobids.txt); MC_ARR=$(unfinished $W/mc/jobids.txt)
echo "DATA_ARR=$DATA_ARR"; echo "MC_ARR=$MC_ARR"
[ -n "$DATA_ARR" ] && [ -n "$MC_ARR" ] || { echo "STOP: empty dependency list"; exit 9; }
P=$R/studies/fullrun_20261025/cluster/pbs_post.sh
post() { local what=$1 res=$2; shift 2; $Q -N fr25_$what -l $res \
  -o $W/logs/post/$what.out -e $W/logs/post/$what.err -v WORK_DIR=$W,REPO_DIR=$R,WHAT=$what "$@" $P; }
F=$R/studies/cms_mc_weights_v3/fullrun/pbs_fullrun.sh
mcpost() { local what=$1 res=$2; shift 2; $Q -l $res -o $W/logs/post/mc_$what.out -e $W/logs/post/mc_$what.err \
  -v WORK_DIR=$W/mc,REPO_DIR=$R,WHAT=$what "$@" $F; }
# data: completeness (5 datasets) -> default build + exact build -> rule check + delivery plots
DC=$(post data_check select=1:ncpus=1:mem=4gb,walltime=01:00:00,io=25 -W depend=afterany$DATA_ARR)
DB=$(post data_build select=1:ncpus=1:mem=32gb,walltime=06:00:00,io=25 -W depend=afterok:$DC)
DE=$(post data_exact select=1:ncpus=1:mem=32gb,walltime=06:00:00,io=25 -W depend=afterok:$DC)
DK=$(post data_checks select=1:ncpus=1:mem=16gb,walltime=02:00:00,io=25 -W depend=afterok:$DB:$DE)
MA=not-submitted; MG=not-submitted; MB=not-submitted; MS=not-submitted; MR=not-submitted; MK=not-submitted
if [ "$MC_OK" = 1 ]; then
# MC: audit -> gate on its verdict -> build (defaults, 64gb 8h) -> sanity; rule-check builds
MA=$(mcpost audit select=1:ncpus=1:mem=4gb,walltime=01:00:00,io=25 -W depend=afterany$MC_ARR)
MG=$(post mc_gate select=1:ncpus=1:mem=1gb,walltime=00:10:00,io=1 -W depend=afterok:$MA)
MB=$(mcpost build select=1:ncpus=1:mem=64gb,walltime=08:00:00,io=25 -W depend=afterok:$MG)
MS=$(mcpost sanity select=1:ncpus=1:mem=16gb,walltime=02:00:00,io=25 -W depend=afterok:$MB)
MR=$(post mc_rule_builds select=1:ncpus=1:mem=32gb,walltime=04:00:00,io=25 -W depend=afterok:$MG)
MK=$(post mc_rulecheck select=1:ncpus=1:mem=16gb,walltime=02:00:00,io=25 -W depend=afterok:$MR)
fi
printf "%s\n" "data_check $DC" "data_build $DB" "data_exact $DE" "data_checks $DK" \
  "mc_audit $MA" "mc_gate $MG" "mc_build $MB" "mc_sanity $MS" "mc_rule_builds $MR" "mc_rulecheck $MK" | tee $W/post_jobids.txt
echo "end $(date --iso-8601=seconds)"
