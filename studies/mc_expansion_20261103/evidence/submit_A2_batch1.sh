# The exact script run on wipp-home (ssh wipp-home 'bash -l -s' < this) on 3 Nov 2026 19:05 IST for A2:
# timing job 5434328 + batch 1 (tiers 1-3). Output: submit_A2_batch1.txt. For A2b, reuse the variable
# definitions and submit_tier unchanged (do NOT re-run the clone/mkdir/cp lines or the timing job).
set -euo pipefail
B=/storage/agrp/berkom/atlas-utilization
C=6de9d3e605900a628bae372bdba4ea3308e9750f
CK=$B/checkouts/mcexp_20261103; W=$B/work/mcexp_20261103/full; R=$CK/repo_$C; Q=/opt/pbs/bin/qsub
PY=$B/envs/atlas-pipeline/bin/python
echo "quota before: $(lfs quota -u berkom /storage | tail -1 | awk '{print $6}')"
echo "my queued subjobs before: $(/opt/pbs/bin/qstat -u berkom -t 2>/dev/null | awk '$10=="Q"' | wc -l)"
test ! -e $R && test ! -e $W
git clone -q --no-checkout https://github.com/MatanBerko/atlas-utilization.git $R
git -C $R checkout -q $C && test "$(git -C $R rev-parse HEAD)" = $C && echo "HEAD ok $C"
mkdir -p $W/mappings $W/runs $W/evidence $W/logs/post $W/timing/runs
cp $R/studies/mc_expansion_20261103/mappings/mapping_*.txt $W/mappings/
echo "mapping files: $(ls $W/mappings | wc -l), lines: $(cat $W/mappings/mapping_*.txt | wc -l)"
PLAN=$R/studies/mc_expansion_20261103/evidence/full_production_plan.json
# timing job: largest 68045 file (file index 18 = mapping line 19)
L19=$(sed -n 19p $W/mappings/mapping_68045.txt); echo "mapping_68045 line 19: $L19"; test "$L19" = "19 68045 18"
JT=$($Q -N mcexp_t68045 -l mem=6gb,walltime=24:00:00,io=25 -o $W/logs/t68045.out -e $W/logs/t68045.err \
     -v WORK_DIR=$W/timing,REPO_DIR=$R,OUTPUT_BASE=$W/timing/runs,MAPPING_FILE=$W/mappings/mapping_68045.txt,PILOT_ARRAY_INDEX=19 \
     $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh)
echo "timing_68045 $JT" | tee $W/timing_jobid.txt
submit_tier() {
  for rid in $($PY -c "import json;d=json.load(open('$PLAN'))['samples'];print(' '.join(r for r,s in sorted(d.items()) if s['tier']==$1))"); do
    n=$(wc -l < $W/mappings/mapping_$rid.txt)
    wt=$($PY -c "import json;print(json.load(open('$PLAN'))['samples']['$rid']['walltime'])")
    mkdir -p $W/logs/$rid
    if [ "$n" -gt 1 ]; then J=$($Q -J 1-$n -N mcexp_$rid -l mem=6gb,walltime=$wt,io=25 \
        -o "$W/logs/$rid/f_^array_index^.out" -e "$W/logs/$rid/f_^array_index^.err" \
        -v WORK_DIR=$W,REPO_DIR=$R,OUTPUT_BASE=$W/runs,MAPPING_FILE=$W/mappings/mapping_$rid.txt \
        $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh)
    else J=$($Q -N mcexp_$rid -l mem=6gb,walltime=$wt,io=25 -o "$W/logs/$rid/f_1.out" -e "$W/logs/$rid/f_1.err" \
        -v WORK_DIR=$W,REPO_DIR=$R,OUTPUT_BASE=$W/runs,MAPPING_FILE=$W/mappings/mapping_$rid.txt,PILOT_ARRAY_INDEX=1 \
        $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh); fi
    echo "$rid $J $n $wt" | tee -a $W/jobids.txt
  done; }
submit_tier 1; submit_tier 2; submit_tier 3
echo "batch 1 subjobs: $(awk '{s+=$3} END{print s}' $W/jobids.txt) in $(wc -l < $W/jobids.txt) arrays"
echo "my queued subjobs after: $(/opt/pbs/bin/qstat -u berkom -t 2>/dev/null | awk '$10=="Q"' | wc -l)"
echo "quota after: $(lfs quota -u berkom /storage | tail -1 | awk '{print $6}')"
date
