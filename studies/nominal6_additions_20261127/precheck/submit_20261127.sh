#!/bin/bash
# Nominal-6 additions precheck submission (27 Nov 2026), run on wipp-home in bash -l.
# NEW work dir only; the production runs tree (work/mcexp_20261103/full) is not touched.
set -euo pipefail
B=/storage/agrp/berkom/atlas-utilization
C=6de9d3e605900a628bae372bdba4ea3308e9750f
R=$B/checkouts/mcexp_20261103/repo_$C
W=$B/work/mcexp_20261103/nominal6_precheck_20261127
Q=/opt/pbs/bin/qsub
test "$(git -C $R rev-parse HEAD)" = $C
test -z "$(git -C $R status --porcelain)"
test -d $W/scripts && test ! -e $W/runs
mkdir -p $W/runs $W/logs $W/evidence
cp -n $W/scripts/mapping_precheck_file0.txt $W/mapping_precheck_file0.txt
N=$(wc -l < $W/mapping_precheck_file0.txt); test "$N" = 14
J=$($Q -J 1-$N -N n6_pre -l mem=6gb,walltime=03:00:00,io=25 -o "$W/logs/f_^array_index^.out" -e "$W/logs/f_^array_index^.err" \
     -v WORK_DIR=$W,REPO_DIR=$R,OUTPUT_BASE=$W/runs,MAPPING_FILE=$W/mapping_precheck_file0.txt \
     $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh)
G=$($Q -N n6_gen -l select=1:ncpus=1:mem=8gb,walltime=03:00:00,io=25 -o $W/logs/gen_check.out -e $W/logs/gen_check.err \
     -v WORK_DIR=$W,REPO_DIR=$R $W/scripts/pbs_gen_check.sh)
K=$($Q -N n6_cards -l select=1:ncpus=1:mem=2gb,walltime=03:00:00,io=25 -o $W/logs/gridpack_cards.out -e $W/logs/gridpack_cards.err \
     -v WORK_DIR=$W,GRIDPACKS=$W/scripts/gridpacks.txt $W/scripts/pbs_gridpack_cards.sh)
A=$($Q -N n6_ana -l select=1:ncpus=1:mem=4gb,walltime=01:00:00,io=25 -o $W/logs/analysis.out -e $W/logs/analysis.err \
     -W depend=afterany:$J -v WORK_DIR=$W $W/scripts/pbs_analysis.sh)
printf "%s\n" "precheck_array $J" "gen_check $G" "gridpack_cards $K" "analysis $A" | tee $W/jobids.txt
# Retry of the generator check (27 Nov 2026, after 5662737 failed: the env has no aiohttp for HTTPS; gen_check.py now
# opens the root:// URL as the driver does). New log names; the first attempt's logs are left in place.
#   $Q -N n6_gen -l select=1:ncpus=1:mem=8gb,walltime=03:00:00,io=25 -o $W/logs/gen_check_retry1.out \
#      -e $W/logs/gen_check_retry1.err -v WORK_DIR=$W,REPO_DIR=$R $W/scripts/pbs_gen_check_v2.sh
