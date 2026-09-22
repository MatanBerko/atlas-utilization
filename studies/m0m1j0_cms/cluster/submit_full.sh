#!/bin/bash
# ---------------------------------------------------------------------------
# submit_full.sh
#
# m0m1j0 CMS histogram -- Step 2 FULL RUN. Submits one PBS array job
# covering ALL files of records 30522 (Run2016G) and 30555 (Run2016H),
# freshly fetched from the CERN Open Data portal at submission time (this
# task's own instruction: the portal's file list has changed within a
# single day before, so this is never assumed fixed at 57 -- expected
# 29+28=57 per the Phase 0 inventory, but whatever the portal says today
# is what actually gets submitted and reported).
#
# Same selection, same per-job driver (run_m0m1j0_on_file.py), same
# preflight pattern as the pilot's own submit_pilot.sh -- the physics
# selection itself is NOT re-verified here (that was the pilot's job,
# already reviewed); this preflight re-checks that the environment/imports
# still work and that nothing has drifted since.
#
# IMPORTANT (git-safety rule): $HOME/atlas-utilization must stay
# untouched/clean -- REPO_DIR below points at the study's own separate
# clone, /storage/agrp/berkom/atlas-utilization/work/m0m1j0_cms/repo.
#
# Output goes under a NEW directory, output/m0m1j0_full/ -- the pilot's
# own output/m0m1j0_pilot/ is never touched, read, or overwritten by this
# script.
#
# PREFLIGHT: conda env, python/ROOT-free/XRootD-stack import check, every
# m0m1j0 module's own import check, a metadata-only XRootD open of one
# real file from each record, REPO_DIR branch/commit/clean-tree check
# against origin/analysis/m0m1j0-cms, $HOME/atlas-utilization
# untouched/clean check, output/log dirs exist+writable, and a check that
# output/m0m1j0_full/ isn't already non-empty from a previous attempt
# (never silently mixes partial results from an earlier submission). If
# ANY check fails, NOTHING is submitted.
#
# DRY_RUN=1 ./submit_full.sh -- same semantics as submit_pilot.sh: runs
# every check that doesn't need the real cluster, replaces `qsub` with an
# echo of the exact command, submits nothing. The job-index-map
# generation itself (a real network fetch to the CERN portal) IS run even
# under DRY_RUN, since it's informational and read-only, not a cluster
# action.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/m0m1j0_cms/repo}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-analysis/m0m1j0-cms}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
FULL_OUTPUT_BASE="${FULL_OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_full}"
FULL_LOG_BASE="${FULL_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/m0m1j0_full}"
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

skip_or_run() {
    local desc="$1"
    shift
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "[DRY_RUN] skipping: $desc (requires the real cluster)"
        return 0
    fi
    "$@"
}

echo "=== Preflight ==="

preflight_conda() {
    if [[ ! -f "$CONDA_PROFILE" ]]; then
        echo "PREFLIGHT FAILED: conda profile not found at $CONDA_PROFILE" >&2
        exit 1
    fi
    # shellcheck disable=SC1090
    source "$CONDA_PROFILE" || { echo "PREFLIGHT FAILED: failed to source $CONDA_PROFILE" >&2; exit 1; }
    conda activate "$CONDA_ENV" || { echo "PREFLIGHT FAILED: failed to activate conda env $CONDA_ENV" >&2; exit 1; }
    echo "  OK: activated conda env $CONDA_ENV"
}
skip_or_run "conda profile + env activation" preflight_conda

preflight_python_stack() {
    # ROOT/PyROOT deliberately NOT checked -- this cluster account's
    # atlas-pipeline conda env has no PyROOT installed at all (RECIPE.md
    # section 7a); this study's histogram I/O uses uproot instead.
    timeout 30 nice python -c "
import sys
mods = ['uproot', 'awkward', 'numpy', 'vector', 'requests', 'matplotlib']
missing = []
for m in mods:
    try:
        mod = __import__(m)
        print(f'  {m}: {getattr(mod, \"__version__\", \"?\")}')
    except ImportError as e:
        missing.append(m)
        print(f'  {m}: MISSING ({e})')
xrootd_ok = False
for name in ['fsspec_xrootd', 'XRootD']:
    try:
        mod = __import__(name)
        print(f'  {name}: {getattr(mod, \"__version__\", \"?\")}')
        xrootd_ok = True
    except ImportError:
        print(f'  {name}: not importable')
if not xrootd_ok:
    missing.append('fsspec_xrootd/XRootD (need at least one)')
if missing:
    print('MISSING:', missing)
    sys.exit(1)
" || { echo "PREFLIGHT FAILED: required python package(s) missing" >&2; exit 1; }
    echo "  OK: uproot/awkward/numpy/vector/requests/matplotlib + an XRootD stack are importable"
}
skip_or_run "python package + XRootD-stack import/version check" preflight_python_stack

preflight_repo_imports() {
    timeout 30 nice python -c "
import sys
sys.path.insert(0, '.')
import studies.m0m1j0_cms.selection
import studies.m0m1j0_cms.histograms
import studies.m0m1j0_cms.design_checks.common
import services.parsing.validated_runs
print('  OK: all m0m1j0 full-run modules import cleanly')
" || { echo "PREFLIGHT FAILED: a full-run module failed to import -- see traceback above" >&2; exit 1; }
}
skip_or_run "preflight-import every module the full-run jobs need" preflight_repo_imports

preflight_xrootd_open() {
    timeout 60 nice python -c "
import sys
sys.path.insert(0, '.')
import uproot
from studies.m0m1j0_cms.design_checks.common import fetch_file_list
ok = True
for record_id in (30522, 30555):
    try:
        url = fetch_file_list(record_id)[0]
        f = uproot.open(url)
        n_branches = len(f['Events'].keys())
        print(f'  record {record_id}: opened {url} OK, Events tree has {n_branches} branches (metadata only)')
    except Exception as e:
        print(f'  record {record_id}: FAILED to open -- {type(e).__name__}: {e}')
        ok = False
if not ok:
    sys.exit(1)
" || { echo "PREFLIGHT FAILED: XRootD metadata-only open failed for a record's first file" >&2; exit 1; }
    echo "  OK: first file of both records opens over XRootD (metadata only)"
}
skip_or_run "XRootD metadata-only open of both records' first file" preflight_xrootd_open

preflight_git() {
    if [[ ! -d "$REPO_DIR/.git" ]]; then
        echo "PREFLIGHT FAILED: $REPO_DIR is not a git checkout" >&2
        exit 1
    fi
    local branch commit remote_commit
    branch=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)
    if [[ "$branch" != "$EXPECTED_BRANCH" ]]; then
        echo "PREFLIGHT FAILED: $REPO_DIR is on branch '$branch', expected '$EXPECTED_BRANCH'" >&2
        exit 1
    fi
    if [[ -n "$(git -C "$REPO_DIR" status --porcelain)" ]]; then
        echo "PREFLIGHT FAILED: $REPO_DIR has a dirty working tree:" >&2
        git -C "$REPO_DIR" status --short >&2
        exit 1
    fi
    git -C "$REPO_DIR" fetch origin "$EXPECTED_BRANCH" --quiet
    commit=$(git -C "$REPO_DIR" rev-parse HEAD)
    remote_commit=$(git -C "$REPO_DIR" rev-parse "origin/$EXPECTED_BRANCH")
    if [[ "$commit" != "$remote_commit" ]]; then
        echo "PREFLIGHT FAILED: local HEAD ($commit) != origin/$EXPECTED_BRANCH ($remote_commit)" >&2
        echo "  Pull (or push) to sync before submitting." >&2
        exit 1
    fi
    echo "  OK: branch=$branch commit=$commit matches origin/$EXPECTED_BRANCH, clean tree"
}
skip_or_run "\$REPO_DIR branch/commit/clean-tree check" preflight_git

preflight_home_checkout_untouched() {
    local home_repo="$HOME/atlas-utilization"
    if [[ -d "$home_repo/.git" ]]; then
        if [[ -n "$(git -C "$home_repo" status --porcelain)" ]]; then
            echo "PREFLIGHT FAILED: \$HOME/atlas-utilization has uncommitted changes -- this task must never touch it. Investigate before continuing." >&2
            git -C "$home_repo" status --short >&2
            exit 1
        fi
        echo "  OK: \$HOME/atlas-utilization exists and is clean (untouched)"
    else
        echo "  OK: \$HOME/atlas-utilization is not a git checkout here (nothing to check)"
    fi
}
skip_or_run "\$HOME/atlas-utilization untouched/clean check" preflight_home_checkout_untouched

preflight_dirs() {
    local dirs=("$FULL_LOG_BASE" "$FULL_OUTPUT_BASE")
    local d probe
    for d in "${dirs[@]}"; do
        mkdir -p "$d" || { echo "PREFLIGHT FAILED: could not create $d" >&2; exit 1; }
        probe="$d/.preflight_write_test_$$"
        if ! ( : > "$probe" ) 2>/dev/null; then
            echo "PREFLIGHT FAILED: $d exists but is not writable" >&2
            exit 1
        fi
        rm -f "$probe"
    done
    echo "  OK: log/output base directories exist and are writable"
}
preflight_dirs   # pure local filesystem check -- runs even under DRY_RUN

preflight_full_output_empty() {
    local nonempty=()
    if [[ -d "$FULL_OUTPUT_BASE" ]]; then
        while IFS= read -r -d '' d; do
            if [[ -n "$(ls -A "$d" 2>/dev/null)" ]]; then
                nonempty+=("$d")
            fi
        done < <(find "$FULL_OUTPUT_BASE" -mindepth 1 -maxdepth 1 -type d -name 'job_*' -print0 2>/dev/null)
    fi
    if [[ ${#nonempty[@]} -gt 0 ]]; then
        echo "PREFLIGHT FAILED: ${#nonempty[@]} job_* output directories already exist under $FULL_OUTPUT_BASE" >&2
        echo "Refusing to mix a fresh full-run submission with leftover output -- move/remove them yourself first (never deleted automatically)." >&2
        exit 1
    fi
    echo "  OK: $FULL_OUTPUT_BASE has no pre-existing job_* output directories"
}
preflight_full_output_empty   # pure local filesystem check -- runs even under DRY_RUN

echo "=== Generating job-index map (fresh portal fetch) ==="
MAPPING_FILE="${FULL_OUTPUT_BASE}/job_index_map.txt"
SUMMARY_FILE="${FULL_OUTPUT_BASE}/job_index_map_summary.json"
python studies/m0m1j0_cms/cluster/generate_job_index_map.py \
    --out-map "$MAPPING_FILE" --out-summary "$SUMMARY_FILE" \
    || { echo "PREFLIGHT FAILED: could not generate the job-index map from the portal" >&2; exit 1; }

TOTAL_JOBS=$(python -c "import json; print(json.load(open('$SUMMARY_FILE'))['total_jobs'])")
if [[ -z "$TOTAL_JOBS" || "$TOTAL_JOBS" -lt 1 ]]; then
    echo "PREFLIGHT FAILED: job-index map reports $TOTAL_JOBS total jobs -- refusing to submit" >&2
    exit 1
fi
echo "  total jobs to submit: $TOTAL_JOBS"

echo "=== Preflight passed -- submitting ==="

JOBID=$(submit -J "1-${TOTAL_JOBS}" \
                -o "${FULL_LOG_BASE}/m0m1j0_full_^array_index^.out" \
                -e "${FULL_LOG_BASE}/m0m1j0_full_^array_index^.err" \
                -v OUTPUT_BASE="$FULL_OUTPUT_BASE",REPO_DIR="$REPO_DIR",MAPPING_FILE="$MAPPING_FILE" \
                studies/m0m1j0_cms/cluster/pbs_m0m1j0_full.sh)
echo "$JOBID"
echo "m0m1j0_full $JOBID $TOTAL_JOBS" >> "${FULL_LOG_BASE}/submitted_jobs.txt"

echo ""
echo "Submitted: m0m1j0 full run array ($TOTAL_JOBS jobs)."
echo "Output under: $FULL_OUTPUT_BASE/"
echo "Logs under:   $FULL_LOG_BASE/"
echo "Check status with: studies/m0m1j0_cms/cluster/status_full.sh"
