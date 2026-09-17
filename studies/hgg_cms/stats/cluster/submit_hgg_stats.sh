#!/bin/bash
# ---------------------------------------------------------------------------
# submit_hgg_stats.sh
#
# Statistical-model task, Parts 2 and 3.3/3.5: submits the validation and
# expected-band/look-elsewhere toy jobs (80 subjobs -- see
# make_job_list.py). All toys are synthetic; no data is read.
#
# THIS TASK DOES NOT RUN THIS SCRIPT (no SSH/qsub access from here).
# Prepared only -- see the final chat message for the exact commands to
# run yourself, then paste the merged results back.
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
    echo "PREFLIGHT FAILED: signal_model.json / background_model_final.json not found -- this run " \
         "needs the already-committed model inputs." >&2
    exit 1
fi
echo "  OK: signal_model.json and background_model_final.json found"

if ! grep -qE '^#PBS[[:space:]]+-l[[:space:]]+io[[:space:]]*=' "$PBS_SCRIPT"; then
    echo "PREFLIGHT FAILED: $PBS_SCRIPT has no '#PBS -l io=<value>' line -- this cluster's " \
         "scheduler rejects any job missing one (see studies/hgg_cms/cluster/FULL_RUN_README.md)." >&2
    exit 1
fi
echo "  OK: $PBS_SCRIPT requests -l io="

if [[ -d "$STATS_OUT_BASE" ]] && [[ -n "$(ls -A "$STATS_OUT_BASE" 2>/dev/null)" ]]; then
    echo "PREFLIGHT FAILED: output directory already exists and is non-empty: $STATS_OUT_BASE" >&2
    echo "Refusing to overwrite a previous attempt -- move/remove it yourself first." >&2
    exit 1
fi
echo "  OK: output directory $STATS_OUT_BASE is empty or doesn't exist yet"

mkdir -p "$STATS_LOG_BASE" "$STATS_OUT_BASE"

JOB_LIST="${STATS_LOG_BASE}/job_list.txt"
python studies/hgg_cms/stats/cluster/make_job_list.py --out "$JOB_LIST"

N_JOBS=$(wc -l < "$JOB_LIST")
if [[ "$N_JOBS" -ne 80 ]]; then
    echo "PREFLIGHT FAILED: expected 80 job-list lines, got $N_JOBS -- check make_job_list.py." >&2
    exit 1
fi
echo "  OK: job list has exactly 80 lines"

echo "=== Preflight passed -- submitting $N_JOBS subjobs ==="

QSUB_CMD=(qsub -J "1-${N_JOBS}" \
    -v JOB_LIST="$JOB_LIST",OUT_BASE="$STATS_OUT_BASE" \
    -o "${STATS_LOG_BASE}/hgg_stats_^array_index^.out" \
    -e "${STATS_LOG_BASE}/hgg_stats_^array_index^.err" \
    "$PBS_SCRIPT")

echo "+ ${QSUB_CMD[*]}"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN-NO-JOBID"
else
    jobid=$("${QSUB_CMD[@]}")
    echo "  $jobid"
    echo "hgg_stats $jobid" >> "${STATS_LOG_BASE}/submitted_jobs.txt"
    echo ""
    echo "Submitted: $N_JOBS subjobs under job $jobid."
    echo "Outputs under: $STATS_OUT_BASE/<job_type>/"
    echo "Logs under:    $STATS_LOG_BASE/"
    echo "Check status with: bash studies/hgg_cms/stats/cluster/status_hgg_stats.sh"
fi
