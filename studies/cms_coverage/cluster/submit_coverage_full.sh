#!/bin/bash
# ---------------------------------------------------------------------------
# submit_coverage_full.sh -- submit the full 57-file coverage run as one
# PBS array job. Mirrors studies/m0m1j0_cms/cluster/submit_full.sh's
# pattern (preflight checks, fresh portal fetch for the job-index map,
# refuse to submit into a non-empty output dir), reusing that study's own
# generate_job_index_map.py directly (RECORDS=(30522, 30555) is exactly
# this survey's DoubleMuon record pair too -- no copy needed).
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/cms_coverage/repo}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-survey/cms-coverage}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
FULL_OUTPUT_BASE="${FULL_OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/cms_coverage_full}"
FULL_LOG_BASE="${FULL_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/cms_coverage_full}"
export PATH="/opt/pbs/bin:$PATH"

cd "$REPO_DIR"

echo "=== Preflight ==="
source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
echo "  OK: activated conda env $CONDA_ENV"

branch=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)
if [[ "$branch" != "$EXPECTED_BRANCH" ]]; then
    echo "PREFLIGHT FAILED: $REPO_DIR is on branch '$branch', expected '$EXPECTED_BRANCH'" >&2
    exit 1
fi
if [[ -n "$(git -C "$REPO_DIR" status --porcelain)" ]]; then
    echo "PREFLIGHT FAILED: $REPO_DIR has a dirty working tree" >&2
    git -C "$REPO_DIR" status --short >&2
    exit 1
fi
git -C "$REPO_DIR" fetch origin "$EXPECTED_BRANCH" --quiet
commit=$(git -C "$REPO_DIR" rev-parse HEAD)
remote_commit=$(git -C "$REPO_DIR" rev-parse "origin/$EXPECTED_BRANCH")
if [[ "$commit" != "$remote_commit" ]]; then
    echo "PREFLIGHT FAILED: local HEAD ($commit) != origin/$EXPECTED_BRANCH ($remote_commit)" >&2
    exit 1
fi
echo "  OK: branch=$branch commit=$commit matches origin/$EXPECTED_BRANCH, clean tree"

mkdir -p "$FULL_LOG_BASE" "$FULL_OUTPUT_BASE"

nonempty=()
while IFS= read -r -d '' d; do
    if [[ -n "$(ls -A "$d" 2>/dev/null)" ]]; then
        nonempty+=("$d")
    fi
done < <(find "$FULL_OUTPUT_BASE" -mindepth 1 -maxdepth 1 -type d -name 'job_*' -print0 2>/dev/null)
if [[ ${#nonempty[@]} -gt 0 ]]; then
    echo "PREFLIGHT FAILED: ${#nonempty[@]} job_* output directories already exist under $FULL_OUTPUT_BASE" >&2
    exit 1
fi
echo "  OK: $FULL_OUTPUT_BASE has no pre-existing job_* output directories"

echo "=== Generating job-index map (fresh portal fetch, reusing m0m1j0's own generator) ==="
MAPPING_FILE="${FULL_OUTPUT_BASE}/job_index_map.txt"
SUMMARY_FILE="${FULL_OUTPUT_BASE}/job_index_map_summary.json"
python studies/m0m1j0_cms/cluster/generate_job_index_map.py \
    --out-map "$MAPPING_FILE" --out-summary "$SUMMARY_FILE"

TOTAL_JOBS=$(python -c "import json; print(json.load(open('$SUMMARY_FILE'))['total_jobs'])")
if [[ -z "$TOTAL_JOBS" || "$TOTAL_JOBS" -lt 1 ]]; then
    echo "PREFLIGHT FAILED: job-index map reports $TOTAL_JOBS total jobs" >&2
    exit 1
fi
echo "  total jobs to submit: $TOTAL_JOBS"

echo "=== Preflight passed -- submitting ==="
JOBID=$(qsub -J "1-${TOTAL_JOBS}" \
    -o "${FULL_LOG_BASE}/cms_coverage_full_^array_index^.out" \
    -e "${FULL_LOG_BASE}/cms_coverage_full_^array_index^.err" \
    -v OUTPUT_BASE="$FULL_OUTPUT_BASE",REPO_DIR="$REPO_DIR",MAPPING_FILE="$MAPPING_FILE" \
    studies/cms_coverage/cluster/pbs_coverage_full.sh)
echo "$JOBID"

echo ""
echo "Submitted: cms_coverage full run array ($TOTAL_JOBS jobs)."
echo "Output under: $FULL_OUTPUT_BASE/"
echo "Logs under:   $FULL_LOG_BASE/"
