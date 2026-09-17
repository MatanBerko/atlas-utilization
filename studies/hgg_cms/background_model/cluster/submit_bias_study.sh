#!/bin/bash
# ---------------------------------------------------------------------------
# submit_bias_study.sh
#
# Background-model task, Part 3: submits the main bias study (120
# subjobs, fit-range 105-180 -- see make_job_list.py / pbs_hgg_bias_array.sh).
#
# THIS TASK DOES NOT RUN THIS SCRIPT. Prepared only, per the "prepare,
# don't submit" instruction -- see BACKGROUND_MODEL_REPORT.md's Part 3
# section and the final chat message for the exact commands to run
# yourself.
#
# DRY_RUN=1: generates the job list and prints the qsub command without
# submitting.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-feature/hgg-selection-and-output}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
BIAS_OUT_BASE="${BIAS_OUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_bias}"
BIAS_LOG_BASE="${BIAS_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_bias}"
LEAKAGE_JSON="${LEAKAGE_JSON:-/storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/hgg_leakage_mass_template_results.json}"
FIT_RANGE="${FIT_RANGE:-105_180}"
DRY_RUN="${DRY_RUN:-0}"

cd "$REPO_DIR"

echo "=== Preflight ==="

if [[ "$DRY_RUN" != "1" ]]; then
    source "$CONDA_PROFILE"
    conda activate "$CONDA_ENV"
    echo "  OK: activated conda env $CONDA_ENV"

    branch=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)
    if [[ "$branch" != "$EXPECTED_BRANCH" ]]; then
        echo "PREFLIGHT FAILED: on branch '$branch', expected '$EXPECTED_BRANCH'" >&2; exit 1
    fi
    if [[ -n "$(git -C "$REPO_DIR" status --porcelain)" ]]; then
        echo "PREFLIGHT FAILED: dirty working tree" >&2; git status --short >&2; exit 1
    fi
    echo "  OK: branch=$branch, clean tree"

    if [[ ! -f "$LEAKAGE_JSON" ]]; then
        echo "PREFLIGHT FAILED: leakage template JSON not found at $LEAKAGE_JSON" >&2; exit 1
    fi
    echo "  OK: leakage template JSON found"
else
    echo "  [DRY_RUN] skipping conda/git/file checks that need the real cluster"
fi

mkdir -p "$BIAS_LOG_BASE" "$BIAS_OUT_BASE/$FIT_RANGE"

JOB_LIST="${BIAS_LOG_BASE}/job_list_${FIT_RANGE}.txt"
python studies/hgg_cms/background_model/cluster/make_job_list.py \
    --order-selection-json "studies/hgg_cms/background_model/results/order_selection_${FIT_RANGE}.json" \
    --out "$JOB_LIST"

N_JOBS=$(wc -l < "$JOB_LIST")
echo "=== Preflight passed -- submitting $N_JOBS subjobs (fit range $FIT_RANGE) ==="

QSUB_CMD=(qsub -J "1-${N_JOBS}" \
    -v JOB_LIST="$JOB_LIST",OUT_BASE="$BIAS_OUT_BASE",LEAKAGE_JSON="$LEAKAGE_JSON",FIT_RANGE="$FIT_RANGE" \
    -o "${BIAS_LOG_BASE}/hgg_bias_${FIT_RANGE}_^array_index^.out" \
    -e "${BIAS_LOG_BASE}/hgg_bias_${FIT_RANGE}_^array_index^.err" \
    studies/hgg_cms/background_model/cluster/pbs_hgg_bias_array.sh)

echo "+ ${QSUB_CMD[*]}"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN-NO-JOBID"
else
    jobid=$("${QSUB_CMD[@]}")
    echo "  $jobid"
    echo "$FIT_RANGE $jobid" >> "${BIAS_LOG_BASE}/submitted_jobs.txt"
    echo ""
    echo "Submitted: $N_JOBS subjobs under job $jobid."
    echo "Outputs under: $BIAS_OUT_BASE/$FIT_RANGE/"
    echo "Logs under:    $BIAS_LOG_BASE/"
    echo "Check status with: bash studies/hgg_cms/background_model/cluster/status_bias_study.sh"
fi
