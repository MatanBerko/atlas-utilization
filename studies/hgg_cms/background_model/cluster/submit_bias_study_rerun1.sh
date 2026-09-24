#!/bin/bash
# ---------------------------------------------------------------------------
# submit_bias_study_rerun1.sh
#
# Background-model task, bias-study rerun 1: submits the 120-subjob
# rerun (EBEB bernstein_6, notEBEB bernstein_7 -- one new candidate per
# category, tested on the same 60 cells and same per-cell seeds as the
# first run; see BACKGROUND_MODEL_REPORT.md's "Pre-declared selection
# procedure" section for why).
#
# THIS TASK DOES NOT RUN THIS SCRIPT. Prepared only -- see the final
# chat message for the exact commands to run yourself.
#
# DRY_RUN=1: runs every check that doesn't need the real cluster, prints
# the qsub command, does not submit.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-feature/hgg-selection-and-output}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
BIAS_OUT_BASE="${BIAS_OUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_bias/105_180_rerun1}"
BIAS_LOG_BASE="${BIAS_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_bias_rerun1}"
LEAKAGE_JSON="${LEAKAGE_JSON:-/storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/hgg_leakage_mass_template_results.json}"
ORDER_SELECTION_JSON="${ORDER_SELECTION_JSON:-studies/hgg_cms/background_model/results/order_selection_105_180.json}"
PBS_SCRIPT="studies/hgg_cms/background_model/cluster/pbs_hgg_bias_rerun1_array.sh"
DRY_RUN="${DRY_RUN:-0}"

cd "$REPO_DIR"

echo "=== Preflight ==="

if [[ "$DRY_RUN" != "1" ]]; then
    source "$CONDA_PROFILE"
    conda activate "$CONDA_ENV"
    echo "  OK: activated conda env $CONDA_ENV"

    preflight_imports() {
        # Same check as submit_bias_study.sh -- see that script's own
        # header for the ModuleNotFoundError incident this guards against.
        python -c "
import sys
mods = ['iminuit', 'scipy', 'numpy', 'matplotlib', 'studies.hgg_cms.background_model.bias_study']
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

if [[ ! -f "$LEAKAGE_JSON" ]]; then
    echo "PREFLIGHT FAILED: leakage template JSON not found at $LEAKAGE_JSON" >&2; exit 1
fi
echo "  OK: leakage template JSON found"

if [[ ! -f "$ORDER_SELECTION_JSON" ]]; then
    echo "PREFLIGHT FAILED: $ORDER_SELECTION_JSON not found -- this rerun needs the first run's " \
         "already-committed order-selection fit results." >&2
    exit 1
fi
echo "  OK: $ORDER_SELECTION_JSON found"

if ! grep -qE '^#PBS[[:space:]]+-l[[:space:]]+io[[:space:]]*=' "$PBS_SCRIPT"; then
    echo "PREFLIGHT FAILED: $PBS_SCRIPT has no '#PBS -l io=<value>' line -- this cluster's " \
         "scheduler rejects any job missing one (see studies/hgg_cms/cluster/FULL_RUN_README.md)." >&2
    exit 1
fi
echo "  OK: $PBS_SCRIPT requests -l io="

if [[ -d "$BIAS_OUT_BASE" ]] && [[ -n "$(ls -A "$BIAS_OUT_BASE" 2>/dev/null)" ]]; then
    echo "PREFLIGHT FAILED: output directory already exists and is non-empty: $BIAS_OUT_BASE" >&2
    echo "Refusing to overwrite a previous attempt -- move/remove it yourself first." >&2
    exit 1
fi
echo "  OK: output directory $BIAS_OUT_BASE is empty or doesn't exist yet"

mkdir -p "$BIAS_LOG_BASE" "$BIAS_OUT_BASE"

JOB_LIST="${BIAS_LOG_BASE}/job_list_105_180_rerun1.txt"
python studies/hgg_cms/background_model/cluster/make_job_list_rerun1.py \
    --order-selection-json "$ORDER_SELECTION_JSON" \
    --out "$JOB_LIST"

N_JOBS=$(wc -l < "$JOB_LIST")
if [[ "$N_JOBS" -ne 120 ]]; then
    echo "PREFLIGHT FAILED: expected 120 jobs, got $N_JOBS -- check $ORDER_SELECTION_JSON for a " \
         "dropped truth family (would change the count) before submitting." >&2
    exit 1
fi
echo "  OK: job list has exactly 120 lines"

echo "=== Preflight passed -- submitting $N_JOBS subjobs (rerun 1, fit range 105_180) ==="

QSUB_CMD=(qsub -J "1-${N_JOBS}" \
    -v JOB_LIST="$JOB_LIST",OUT_BASE="$BIAS_OUT_BASE",LEAKAGE_JSON="$LEAKAGE_JSON" \
    -o "${BIAS_LOG_BASE}/hgg_bias_rerun1_^array_index^.out" \
    -e "${BIAS_LOG_BASE}/hgg_bias_rerun1_^array_index^.err" \
    "$PBS_SCRIPT")

echo "+ ${QSUB_CMD[*]}"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN-NO-JOBID"
else
    jobid=$("${QSUB_CMD[@]}")
    echo "  $jobid"
    echo "105_180_rerun1 $jobid" >> "${BIAS_LOG_BASE}/submitted_jobs.txt"
    echo ""
    echo "Submitted: $N_JOBS subjobs under job $jobid."
    echo "Outputs under: $BIAS_OUT_BASE/"
    echo "Logs under:    $BIAS_LOG_BASE/"
    echo "Check status with: bash studies/hgg_cms/background_model/cluster/status_bias_study_rerun1.sh"
fi
