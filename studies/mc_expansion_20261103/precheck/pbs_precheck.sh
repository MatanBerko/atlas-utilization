#!/bin/bash
# MC expansion A1 step 3 (3 Nov 2026): post-production stages of the small real-file check.
# Production itself is studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh, unchanged.
# WHAT:
#   compare  re-runs of file 0 of the 13 delivered vs the 25 Oct outputs (read only, copied to TMPDIR)
#   build_A  smoke build, 13 delivered re-runs, registry v3 (the default)
#   build_B  same, registry v4 given explicitly (must equal build_A)
#   build_C  smoke build, 54 new + 13 re-runs (--extra-runs-dir), registry v4
#   build_D  smoke build, 54 new + the 25 Oct outputs (file 0, --extra-runs-dir, read only), registry v4
#   report   precheck_report.py (per-sample table, stacks, weight scale)
#   compare_builds  A vs B and C vs D, histogram by histogram (compare_builds.py)
#   checks_test     the B-step checks (post/checks_v4.py) run once on smoke build C, to test the script
#PBS -N mcexp_pre
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
set -euo pipefail
W="${WORK_DIR:?WORK_DIR not set}"; R="${REPO_DIR:?REPO_DIR not set}"; WHAT="${WHAT:?WHAT not set}"
OLD=/storage/agrp/berkom/atlas-utilization/work/fullrun_20261025/mc/runs
source /usr/wipp/conda/24.5.0/etc/profile.d/conda.sh
conda activate /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
export OMP_NUM_THREADS=1 MPLCONFIGDIR="$W/.mplconfig" XDG_CACHE_HOME="$W/.cache" HOME="$W/.jobhome"
export TMPDIR="$W/tmp_$WHAT"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$HOME" "$TMPDIR" "$W/builds" "$W/evidence"
cd "$R"
echo "Job $PBS_JOBID on $(hostname) at $(date)"; echo "commit=$(git rev-parse HEAD) WHAT=$WHAT"
B="python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py --out-prefix smoke --smoke-test --file-indices 0"
V4=studies/cms_mc_weights_v3/cms_mc_normalisation_v4.json
case "$WHAT" in
  compare) python -u studies/mc_expansion_20261103/precheck/compare_reruns.py --new "$W/runs_old13" --old "$OLD" \
             --out "$W/evidence/compare_reruns.json" ;;
  build_A) test ! -e "$W/builds/A"; /usr/bin/time -v $B --runs-dir "$W/runs_old13" --out-dir "$W/builds/A" --scratch-dir "$TMPDIR/s" ;;
  build_B) test ! -e "$W/builds/B"; /usr/bin/time -v $B --runs-dir "$W/runs_old13" --out-dir "$W/builds/B" --scratch-dir "$TMPDIR/s" --registry "$V4" ;;
  build_C) test ! -e "$W/builds/C"; /usr/bin/time -v $B --runs-dir "$W/runs_new" --extra-runs-dir "$W/runs_old13" \
             --out-dir "$W/builds/C" --scratch-dir "$TMPDIR/s" --registry "$V4" ;;
  build_D) test ! -e "$W/builds/D"
           find "$OLD" -path '*/job_0/*' -type f -printf '%p %s %T@\n' | sort > "$W/evidence/old_job0_listing_before_D.txt"
           /usr/bin/time -v $B --runs-dir "$W/runs_new" --extra-runs-dir "$OLD" \
             --out-dir "$W/builds/D" --scratch-dir "$TMPDIR/s" --registry "$V4"
           find "$OLD" -path '*/job_0/*' -type f -printf '%p %s %T@\n' | sort > "$W/evidence/old_job0_listing_after_D.txt"
           cmp "$W/evidence/old_job0_listing_before_D.txt" "$W/evidence/old_job0_listing_after_D.txt" && echo "25 Oct job_0 dirs unchanged" ;;
  compare_builds) python -u studies/mc_expansion_20261103/precheck/compare_builds.py \
             --pair "$W/builds/A" "$W/builds/B" --pair "$W/builds/C" "$W/builds/D" --out "$W/evidence/compare_builds.json" ;;
  checks_test) test ! -e "$W/evidence/checks_v4_on_C"
           python -u studies/mc_expansion_20261103/post/checks_v4.py --build-dir "$W/builds/C" --prefix smoke \
             --runs "$W/runs_new" --out "$W/evidence/checks_v4_on_C" \
             --data-root /storage/agrp/berkom/atlas-utilization/work/fullrun_20261025/deliver/data/CMS_Run2016GH_DoubleMuon-SingleMuon-DoubleEG-MuonEG-SingleElectron_16p393invfb_prod2026-10-25_data_bumpnet_uncropped.root ;;
  report)  python -u studies/mc_expansion_20261103/precheck/precheck_report.py --runs "$W/runs_new" "$W/runs_old13" \
             --build-a "$W/builds/A" --build-c "$W/builds/C" --out "$W/evidence/report" ;;
  *) echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac
rm -rf "$TMPDIR"
echo "done $WHAT $(date)"
