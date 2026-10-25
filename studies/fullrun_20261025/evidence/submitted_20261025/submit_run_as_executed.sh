set -euo pipefail
W=/storage/agrp/berkom/atlas-utilization/work/fullrun_20261025
# guard: never double-submit
for f in $W/data/jobids.txt $W/mc/jobids.txt $W/post_jobids.txt; do [ ! -e $f ] || { echo "STOP: $f exists"; exit 9; }; done
if /opt/pbs/bin/qstat -u berkom 2>/dev/null | grep -qE " (fr25_|mcfull_)"; then echo "STOP: fr25_/mcfull_ jobs already queued"; exit 9; fi
echo "submission start $(date --iso-8601=seconds) on $(hostname)"
lfs quota -u berkom /storage | tail -1
B=/storage/agrp/berkom/atlas-utilization
CK=$B/checkouts/fullrun_20261025; W=$B/work/fullrun_20261025
C=75b399e2dfdacc50affd4e2c78bc865b12f000cc; R=$CK/repo_75b399e
Q=/opt/pbs/bin/qsub; FIVE="DoubleMuon SingleMuon DoubleEG MuonEG SingleElectron"
MCREC="67993 75589 67801 68187 35669 72752 35631 68847 68073 64895 64839 72676 37728"

# 0. pinned checkout + layout (new directories only)
git clone -q --no-checkout https://github.com/MatanBerko/atlas-utilization.git $R
git -C $R checkout -q $C && test "$(git -C $R rev-parse HEAD)" = $C
mkdir -p $W/data/runs $W/data/evidence $W/logs/post $W/mc/mappings $W/mc/runs $W/mc/evidence
cp $W/mappings_data/*_index.json $W/data/runs/          # what the builder and the check read
cp $W/mappings_mc/mapping_*.txt $W/mc/mappings/

# 1. data production: 5 arrays, 541 files (launcher unchanged; 8gb 2h io=25 inside it)
for ds in $FIVE; do
  n=$(wc -l < $W/mappings_data/${ds}_mapping.txt); mkdir -p $W/data/logs/$ds
  J=$($Q -J 0-$((n-1)) -N fr25_$ds \
      -o "$W/data/logs/$ds/f_^array_index^.out" -e "$W/data/logs/$ds/f_^array_index^.err" \
      -v REPO_DIR=$R,MAPPING_FILE=$W/mappings_data/${ds}_mapping.txt,OUT_BASE=$W/data/runs,POPULATION=matched5 \
      $R/studies/cms_datasets/electron_vB/cluster/pbs_matched4.sh)
  echo "$ds $J $n" | tee -a $W/data/jobids.txt
done

# 2. MC production: 13 arrays, 497 files (exactly the 17 Oct submit_production.sh loop)
for rid in $MCREC; do
  n=$(wc -l < $W/mc/mappings/mapping_$rid.txt); wt=02:00:00; case $rid in 68187|68073) wt=03:00:00;; esac
  mkdir -p $W/mc/logs/$rid
  J=$($Q -J 1-$n -N mcfull_$rid -l mem=6gb,walltime=$wt,io=25 \
      -o "$W/mc/logs/$rid/f_^array_index^.out" -e "$W/mc/logs/$rid/f_^array_index^.err" \
      -v WORK_DIR=$W/mc,REPO_DIR=$R,OUTPUT_BASE=$W/mc/runs,MAPPING_FILE=$W/mc/mappings/mapping_$rid.txt \
      $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh)
  echo "$rid $J $n $wt" | tee -a $W/mc/jobids.txt     # the format audit_production.py reads
done

# 3. post-production chain (afterany on arrays -> a gate job -> afterok on the gate)
DATA_ARR=$(awk '{printf ":%s", $2}' $W/data/jobids.txt); MC_ARR=$(awk '{printf ":%s", $2}' $W/mc/jobids.txt)
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
# MC: audit -> gate on its verdict -> build (defaults, 64gb 8h) -> sanity; rule-check builds
MA=$(mcpost audit select=1:ncpus=1:mem=4gb,walltime=01:00:00,io=25 -W depend=afterany$MC_ARR)
MG=$(post mc_gate select=1:ncpus=1:mem=1gb,walltime=00:10:00,io=1 -W depend=afterok:$MA)
MB=$(mcpost build select=1:ncpus=1:mem=64gb,walltime=08:00:00,io=25 -W depend=afterok:$MG)
MS=$(mcpost sanity select=1:ncpus=1:mem=16gb,walltime=02:00:00,io=25 -W depend=afterok:$MB)
MR=$(post mc_rule_builds select=1:ncpus=1:mem=32gb,walltime=04:00:00,io=25 -W depend=afterok:$MG)
MK=$(post mc_rulecheck select=1:ncpus=1:mem=16gb,walltime=02:00:00,io=25 -W depend=afterok:$MR)
printf "%s\n" "data_check $DC" "data_build $DB" "data_exact $DE" "data_checks $DK" \
  "mc_audit $MA" "mc_gate $MG" "mc_build $MB" "mc_sanity $MS" "mc_rule_builds $MR" "mc_rulecheck $MK" | tee $W/post_jobids.txt
echo "submission end $(date --iso-8601=seconds)"
