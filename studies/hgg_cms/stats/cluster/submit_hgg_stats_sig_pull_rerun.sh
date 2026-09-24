#!/bin/bash
# ---------------------------------------------------------------------------
# submit_hgg_stats_sig_pull_rerun.sh
#
# Statistical-model task: PREPARED, NOT SUBMITTED. A full-statistics
# rerun of sig_injection (mu_true in {0.5, 1.0, 2.0}, 1000 toys each)
# with the FIXED code (mu_err via explicit HESSE + fmin diagnostics),
# needed because the pull_width criterion (pull mean and width, from
# this task's own pre-set Part 2.2 spec) cannot be evaluated at all
# from the already-collected sig_injection toys -- they have no mu_err
# field (see STATS_REPORT.md's own review of the 18 Sep 2026 run).
#
# 124 subjobs (see make_job_list_sig_pull_rerun.py for the batch-size
# accounting), same preflight as submit_hgg_stats.sh, same PBS script
# (pbs_hgg_stats_array.sh) with OUT_PREFIX=pullrerun_ so output can
# never collide with the original run's or retry1's files in the same
# per-job-type subdirectory, and disjoint seeds (20280918+) from both.
#
# THIS TASK DOES NOT RUN THIS SCRIPT (no SSH/qsub access). Prepared
# only, at the user's explicit request to see the cost before deciding
# whether to run it prior to unblinding -- see the final chat message.
#
# DRY_RUN=1: runs every check that doesn't need the real cluster, prints
# the qsub command, does not submit.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-feature/hgg-selection-and-output}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
STATS_OUT_BASE="${STATS_OUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_stats}"
STATS_LOG_BASE="${STATS_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_stats}"
PBS_SCRIPT="studies/hgg_cms/stats/cluster/pbs_hgg_stats_array.sh"
OUT_PREFIX="pullrerun_"
DRY_RUN="${DRY_RUN:-0}"

cd "$REPO_DIR"

echo "=== Preflight ==="

if [[ "$DRY_RUN" != "1" ]]; then
    source "$CONDA_PROFILE"
    conda activate "$CONDA_ENV"
    echo "  OK: activated conda env $CONDA_ENV"

    preflight_imports() {
        python -c "
import sys
mods = ['iminuit', 'scipy', 'numpy', 'studies.hgg_cms.stats.model', 'studies.hgg_cms.stats.fit']
failed = []
for name in mods:
    try:
        m = __import__(name, fromlist=['__name__'])
        ver = getattr(m, '__version__', 'n/a (no __version__ attribute)')
        print(f'  OK: {name} (version {ver})')
    except ImportError as e:
        print(f'  MISSING: {name} -- {type(e).__name__}: {e}')
        failed.append(name)
if failed:
    print('FAILED modules: ' + ', '.join(failed), file=sys.stderr)
    sys.exit(1)
" || {
            echo "PREFLIGHT FAILED: one or more required Python modules are not importable in " \
                 "conda env $CONDA_ENV -- see MISSING lines above." >&2
            exit 1
        }
    }
    preflight_imports
else
    echo "  [DRY_RUN] skipping conda activation + import check (needs the real cluster env)"
fi

branch=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)
if [[ "$branch" != "$EXPECTED_BRANCH" ]]; then
    echo "PREFLIGHT FAILED: on branch '$branch', expected '$EXPECTED_BRANCH'" >&2; exit 1
fi
if [[ -n "$(git -C "$REPO_DIR" status --porcelain)" ]]; then
    echo "PREFLIGHT FAILED: dirty working tree" >&2; git status --short >&2; exit 1
fi
commit=$(git -C "$REPO_DIR" rev-parse HEAD)
echo "  OK: branch=$branch, clean tree, commit=$commit"

if [[ ! -f "studies/hgg_cms/signal_model/results/signal_model.json" ]] || \
   [[ ! -f "studies/hgg_cms/background_model/results/background_model_final.json" ]]; then
    echo "PREFLIGHT FAILED: signal_model.json / background_model_final.json not found." >&2
    exit 1
fi
echo "  OK: signal_model.json and background_model_final.json found"

if ! grep -qE '^#PBS[[:space:]]+-l[[:space:]]+io[[:space:]]*=' "$PBS_SCRIPT"; then
    echo "PREFLIGHT FAILED: $PBS_SCRIPT has no '#PBS -l io=<value>' line." >&2
    exit 1
fi
echo "  OK: $PBS_SCRIPT requests -l io="

JOBLIST_FILE="${STATS_LOG_BASE}/submitted_jobs.txt"
if [[ ! -f "$JOBLIST_FILE" ]]; then
    echo "PREFLIGHT FAILED: $JOBLIST_FILE not found -- has submit_hgg_stats.sh been run first?" >&2
    exit 1
fi
echo "  OK: original run's $JOBLIST_FILE found"

JOB_LIST="${STATS_LOG_BASE}/job_list_sig_pull_rerun.txt"
if [[ -f "$JOB_LIST" ]]; then
    echo "PREFLIGHT FAILED: $JOB_LIST already exists -- refusing to overwrite a previous attempt's " \
         "job list. Remove/move it yourself first if you really want to redo this." >&2
    exit 1
fi
python studies/hgg_cms/stats/cluster/make_job_list_sig_pull_rerun.py --out "$JOB_LIST"

N_JOBS=$(wc -l < "$JOB_LIST")
if [[ "$N_JOBS" -ne 124 ]]; then
    echo "PREFLIGHT FAILED: expected 124 job-list lines, got $N_JOBS -- check " \
         "make_job_list_sig_pull_rerun.py." >&2
    exit 1
fi
echo "  OK: job list has exactly 124 lines"

EXISTING=$(find "$STATS_OUT_BASE" -name "${OUT_PREFIX}job_*.json" 2>/dev/null | head -1 || true)
if [[ -n "$EXISTING" ]]; then
    echo "PREFLIGHT FAILED: found existing ${OUT_PREFIX}job_*.json output (e.g. $EXISTING) -- " \
         "refusing to resubmit over a previous attempt. Move it aside yourself first." >&2
    exit 1
fi
echo "  OK: no existing ${OUT_PREFIX}job_*.json output found"

echo "=== Preflight passed -- submitting $N_JOBS subjobs (sig_injection pull-width rerun) ==="

QSUB_CMD=(qsub -J "1-${N_JOBS}" \
    -v JOB_LIST="$JOB_LIST",OUT_BASE="$STATS_OUT_BASE",OUT_PREFIX="$OUT_PREFIX" \
    -o "${STATS_LOG_BASE}/hgg_stats_pullrerun_^array_index^.out" \
    -e "${STATS_LOG_BASE}/hgg_stats_pullrerun_^array_index^.err" \
    "$PBS_SCRIPT")

echo "+ ${QSUB_CMD[*]}"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN-NO-JOBID"
else
    jobid=$("${QSUB_CMD[@]}")
    echo "  $jobid"
    echo "hgg_stats_sig_pull_rerun $jobid $JOB_LIST $OUT_PREFIX" >> "$JOBLIST_FILE"
    echo ""
    echo "Submitted: $N_JOBS subjobs under job $jobid."
    echo "Outputs under: $STATS_OUT_BASE/sig_injection/${OUT_PREFIX}job_NNNN.json"
    echo "Logs under:    $STATS_LOG_BASE/hgg_stats_pullrerun_*.out/.err"
    echo "Check status with: bash studies/hgg_cms/stats/cluster/status_hgg_stats.sh"
    echo "Merge normally (same command as before) -- merge_hgg_stats.py globs *job_*.json per"
    echo "job_type, so these pullrerun_ files are picked up automatically and pooled with the"
    echo "original toys for median_Z/pull_mean/P(Z>=3,5) (more toys only helps those), while"
    echo "pull_width itself is computed ONLY from whichever toys actually carry a usable mu_err"
    echo "(i.e. these new ones) -- no separate merge step needed."
fi
