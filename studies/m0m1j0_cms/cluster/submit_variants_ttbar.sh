#!/bin/bash
# ---------------------------------------------------------------------------
# submit_variants_ttbar.sh -- same as submit_variants_data.sh but for the
# ttbar MC sample (record 67801), reusing generate_ttbar_job_index_map.py
# UNCHANGED.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/m0m1j0_cms/repo}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-analysis/m0m1j0-cms}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
OUTPUT_BASE="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_variants_ttbar}"
LOG_BASE="${LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/m0m1j0_variants_ttbar}"
DRY_RUN="${DRY_RUN:-0}"

cd "$REPO_DIR"

submit() {
    echo "+ qsub $*" >&2
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "DRY-RUN-NO-JOBID"
    else
        qsub "$@"
    fi
}

echo "=== Preflight ==="

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
echo "  OK: activated conda env $CONDA_ENV"

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]]; then
    echo "PREFLIGHT FAILED: $REPO_DIR is on branch '$CURRENT_BRANCH', expected '$EXPECTED_BRANCH'" >&2
    exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
    echo "PREFLIGHT FAILED: $REPO_DIR has uncommitted changes -- commit or stash first" >&2
    git status --porcelain >&2
    exit 1
fi
echo "  OK: $REPO_DIR is on $EXPECTED_BRANCH, clean, at $(git rev-parse --short HEAD)"

if [[ -n "$(cd "$HOME/atlas-utilization" && git status --porcelain)" ]]; then
    echo "PREFLIGHT FAILED: \$HOME/atlas-utilization is not clean -- this script must never touch it" >&2
    exit 1
fi
echo "  OK: \$HOME/atlas-utilization is clean (untouched)"

python -c "
import studies.m0m1j0_cms.selection
import studies.m0m1j0_cms.variants
import studies.m0m1j0_cms.histograms
import studies.m0m1j0_cms.postprocessing
import studies.m0m1j0_cms.cluster.run_m0m1j0_variants_on_mc_file
import studies.m0m1j0_cms.cluster.merge_variants
print('  OK: every variants module imports cleanly')
" || { echo "PREFLIGHT FAILED: module import check failed" >&2; exit 1; }

if [[ -d "$OUTPUT_BASE" ]] && [[ -n "$(ls -A "$OUTPUT_BASE" 2>/dev/null)" ]]; then
    echo "PREFLIGHT FAILED: $OUTPUT_BASE already exists and is non-empty -- refusing to mix with a previous attempt" >&2
    exit 1
fi
mkdir -p "$OUTPUT_BASE" "$LOG_BASE"
echo "  OK: $OUTPUT_BASE is fresh/empty, $LOG_BASE exists"

echo "=== Generating job index map (fresh portal fetch) ==="
python studies/m0m1j0_cms/cluster/generate_ttbar_job_index_map.py \
    --out-map "$OUTPUT_BASE/job_index_map.txt" \
    --out-summary "$OUTPUT_BASE/job_index_map_summary.json"

TOTAL_JOBS=$(python -c "import json; print(json.load(open('$OUTPUT_BASE/job_index_map_summary.json'))['total_jobs'])")
echo "Total jobs to submit: $TOTAL_JOBS"

echo "=== Submitting ==="
submit -J "1-${TOTAL_JOBS}" \
    -v "MAPPING_FILE=${OUTPUT_BASE}/job_index_map.txt,OUTPUT_BASE=${OUTPUT_BASE},REPO_DIR=${REPO_DIR}" \
    studies/m0m1j0_cms/cluster/pbs_m0m1j0_variants_ttbar.sh
