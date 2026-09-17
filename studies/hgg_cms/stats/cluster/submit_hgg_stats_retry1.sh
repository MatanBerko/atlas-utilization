#!/bin/bash
# ---------------------------------------------------------------------------
# submit_hgg_stats_retry1.sh
#
# Statistical-model task: retry #1 for the 18 Sep 2026 hgg_stats
# validation run (job 5057683[], commit 15bd3a5) -- resubmits ONLY the
# missing work from the 8 subjobs that hit the 02:00:00 walltime on
# slow nodes (see make_retry_job_list_1.py for the full accounting:
# sig_injection mu=2.0 needs 750 more toys, mass_scan_bkg needs 100
# more), in much smaller batches (63 and 10 toys/job respectively) so
# each comfortably finishes under 2h even on the slowest node seen so
# far.
#
# Same preflight as submit_hgg_stats.sh (conda env + iminuit import,
# branch, clean tree, model files present, `-l io=` check). Outputs go
# into the SAME per-job-type subdirectories as the original run, named
# `retry1_job_<index>.json` (via OUT_PREFIX=retry1_ on the shared PBS
# script) so they can never collide with the original run's
# `job_<index>.json` files regardless of index numbering. Logs are
# unique (`hgg_stats_retry1_<index>.out/.err`). The job ID is appended
# to the SAME submitted_jobs.txt as the original run, as a 4-field line
# (`label jobid job_list_path out_prefix`) so status_hgg_stats.sh can
# correctly interpret both the original 2-field line already there and
# this new line without reprocessing or touching what's already on
# disk.
#
# THIS TASK DOES NOT RUN THIS SCRIPT (no SSH/qsub access). Prepared
# only -- see the final chat message for the exact commands.
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
OUT_PREFIX="retry1_"
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
                 "conda env $CONDA_ENV -- see MISSING lines above. See " \
                 "studies/hgg_cms/cluster/ENVIRONMENT.md for expected versions." >&2
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
    echo "PREFLIGHT FAILED: $JOBLIST_FILE not found -- has submit_hgg_stats.sh been run and " \
         "the original job actually submitted? This retry is meant to fill in missing work from " \
         "that run, not stand alone." >&2
    exit 1
fi
echo "  OK: original run's $JOBLIST_FILE found"

RETRY_JOB_LIST="${STATS_LOG_BASE}/job_list_retry1.txt"
if [[ -f "$RETRY_JOB_LIST" ]]; then
    echo "PREFLIGHT FAILED: $RETRY_JOB_LIST already exists -- refusing to overwrite a previous " \
         "retry1 attempt's job list. Remove/move it yourself first if you really want to redo this." >&2
    exit 1
fi
python studies/hgg_cms/stats/cluster/make_retry_job_list_1.py --out "$RETRY_JOB_LIST"

N_JOBS=$(wc -l < "$RETRY_JOB_LIST")
if [[ "$N_JOBS" -ne 22 ]]; then
    echo "PREFLIGHT FAILED: expected 22 retry job-list lines, got $N_JOBS -- check " \
         "make_retry_job_list_1.py." >&2
    exit 1
fi
echo "  OK: retry job list has exactly 22 lines"

# Refuse if any retry1_ output already exists from an earlier attempt --
# never silently overwrite.
EXISTING=$(find "$STATS_OUT_BASE" -name "retry1_job_*.json" 2>/dev/null | head -1 || true)
if [[ -n "$EXISTING" ]]; then
    echo "PREFLIGHT FAILED: found existing retry1_job_*.json output (e.g. $EXISTING) -- refusing to " \
         "resubmit over a previous retry1 attempt. Move it aside yourself first." >&2
    exit 1
fi
echo "  OK: no existing retry1_job_*.json output found"

echo "=== Preflight passed -- submitting $N_JOBS subjobs (retry1) ==="

QSUB_CMD=(qsub -J "1-${N_JOBS}" \
    -v JOB_LIST="$RETRY_JOB_LIST",OUT_BASE="$STATS_OUT_BASE",OUT_PREFIX="$OUT_PREFIX" \
    -o "${STATS_LOG_BASE}/hgg_stats_retry1_^array_index^.out" \
    -e "${STATS_LOG_BASE}/hgg_stats_retry1_^array_index^.err" \
    "$PBS_SCRIPT")

echo "+ ${QSUB_CMD[*]}"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN-NO-JOBID"
else
    jobid=$("${QSUB_CMD[@]}")
    echo "  $jobid"
    echo "hgg_stats_retry1 $jobid $RETRY_JOB_LIST $OUT_PREFIX" >> "$JOBLIST_FILE"
    echo ""
    echo "Submitted: $N_JOBS subjobs under job $jobid."
    echo "Outputs under: $STATS_OUT_BASE/<job_type>/${OUT_PREFIX}job_NNNN.json"
    echo "Logs under:    $STATS_LOG_BASE/hgg_stats_retry1_*.out/.err"
    echo "Check status with: bash studies/hgg_cms/stats/cluster/status_hgg_stats.sh"
fi
