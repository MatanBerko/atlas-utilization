#!/bin/bash
# ---------------------------------------------------------------------------
# submit_lumi_coverage.sh -- submit the four-dataset luminosity-coverage
# read as one 8-subjob PBS array.
#
# Mirrors studies/cms_coverage/cluster/submit_coverage_full.sh's preflight
# pattern: refuse to submit unless the pinned checkout is clean, on the
# expected branch and identical to its remote, refuse to submit into a
# non-empty output directory, and create the log directory before qsub.
# Adds a file-count quota check, because this account runs near its inode
# limit.
#
# Everything it writes lives under WORK_DIR; nothing is written to $HOME and
# nothing under output/ is touched.
#
# Usage: WORK_DIR=... REPO_DIR=... EXPECTED_BRANCH=... ./submit_lumi_coverage.sh
# ---------------------------------------------------------------------------
set -euo pipefail

WORK_DIR="${WORK_DIR:?WORK_DIR not set}"
REPO_DIR="${REPO_DIR:-$WORK_DIR/repo}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-study/lumi-coverage-four-datasets}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
OUTPUT_DIR="${OUTPUT_DIR:-$WORK_DIR/out}"
LOG_DIR="${LOG_DIR:-$WORK_DIR/logs}"
MAPPING_FILE="${MAPPING_FILE:-$WORK_DIR/record_keys.txt}"
QUOTA_FILE_LIMIT="${QUOTA_FILE_LIMIT:-150000}"
QUOTA_HEADROOM="${QUOTA_HEADROOM:-5000}"
export PATH="/opt/pbs/bin:$PATH"

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

# File-count quota: this array adds 8 output JSONs plus 16 log files, but
# refuse to submit at all if the account is within QUOTA_HEADROOM of its
# inode limit.
files_used=$(lfs quota -u "$(whoami)" /storage 2>/dev/null | awk '/\/storage/ {print $6; exit}' | tr -d '*')
if [[ -n "$files_used" ]]; then
    echo "  file-count quota: $files_used used of $QUOTA_FILE_LIMIT"
    if (( files_used + QUOTA_HEADROOM > QUOTA_FILE_LIMIT )); then
        echo "PREFLIGHT FAILED: only $((QUOTA_FILE_LIMIT - files_used)) files left under the quota" >&2
        exit 1
    fi
    echo "  OK: $((QUOTA_FILE_LIMIT - files_used)) files of headroom"
else
    echo "  WARNING: could not read the file-count quota" >&2
fi

mkdir -p "$OUTPUT_DIR" "$LOG_DIR"
if [[ -n "$(ls -A "$OUTPUT_DIR" 2>/dev/null)" ]]; then
    echo "PREFLIGHT FAILED: $OUTPUT_DIR is not empty" >&2
    ls -l "$OUTPUT_DIR" >&2
    exit 1
fi
echo "  OK: $OUTPUT_DIR empty, $LOG_DIR created"

cat > "$MAPPING_FILE" <<'KEYS'
DoubleMuon_G
DoubleMuon_H
SingleMuon_G
SingleMuon_H
DoubleEG_G
DoubleEG_H
MuonEG_G
MuonEG_H
KEYS
N_JOBS=$(wc -l < "$MAPPING_FILE")
echo "  OK: mapping file $MAPPING_FILE with $N_JOBS records"

echo "=== Preflight passed -- submitting ==="
JOBID=$(qsub -J "1-${N_JOBS}" \
    -o "${LOG_DIR}/lumi_cov_^array_index^.out" \
    -e "${LOG_DIR}/lumi_cov_^array_index^.err" \
    -v REPO_DIR="$REPO_DIR",OUTPUT_DIR="$OUTPUT_DIR",MAPPING_FILE="$MAPPING_FILE" \
    "$REPO_DIR/studies/lumi_coverage_four_datasets/cluster/pbs_lumi_coverage.sh")
echo "$JOBID"
echo "$JOBID" > "$WORK_DIR/job_id.txt"

echo ""
echo "Submitted: four-dataset luminosity coverage array ($N_JOBS subjobs)."
echo "Output under: $OUTPUT_DIR/"
echo "Logs under:   $LOG_DIR/"
