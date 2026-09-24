#!/bin/bash
# ---------------------------------------------------------------------------
# submit_ttbar.sh
#
# m0m1j0 CMS histogram -- Part B: submits the ttbar dilepton MC array
# (record 67801, RECIPE.md section 8) -- either the 2-file PILOT (default,
# MODE=pilot) or, only once you've reviewed the pilot's own sanity plots
# and decided to proceed, the FULL 49-file run (MODE=full). Same
# preflight pattern as the data study's submit_full.sh; genWeight is
# additionally checked to be present in a real file before submitting
# anything (the MC driver would fail loudly on it anyway, but catching
# this at preflight, before any job is queued, is cheaper).
#
# Usage:
#   bash submit_ttbar.sh                # pilot (2 files)
#   MODE=full bash submit_ttbar.sh       # full run (49 files) -- run this
#                                         # only after reviewing the
#                                         # pilot's sanity PNGs yourself.
#
# Output/log bases differ by MODE (never mixes pilot and full output):
#   pilot: output/m0m1j0_ttbar_pilot/, logs/m0m1j0_ttbar_pilot/
#   full:  output/m0m1j0_ttbar_full/,  logs/m0m1j0_ttbar_full/
#
# DRY_RUN=1 -- same semantics as the data study's submit scripts.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/m0m1j0_cms/repo}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-analysis/m0m1j0-cms}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
MODE="${MODE:-pilot}"
DRY_RUN="${DRY_RUN:-0}"

if [[ "$MODE" != "pilot" && "$MODE" != "full" ]]; then
    echo "MODE must be 'pilot' or 'full', got '$MODE'" >&2
    exit 1
fi

TTBAR_OUTPUT_BASE="${TTBAR_OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_ttbar_${MODE}}"
TTBAR_LOG_BASE="${TTBAR_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/m0m1j0_ttbar_${MODE}}"

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

echo "=== Preflight (MODE=$MODE) ==="

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
preflight_conda   # always run, even under DRY_RUN -- needed by the map generator below

preflight_python_stack() {
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
import studies.m0m1j0_cms.postprocessing
import studies.m0m1j0_cms.design_checks.common
import studies.m0m1j0_cms.cluster.run_m0m1j0_on_mc_file
print('  OK: all m0m1j0 ttbar modules import cleanly')
" || { echo "PREFLIGHT FAILED: a ttbar module failed to import -- see traceback above" >&2; exit 1; }
}
skip_or_run "preflight-import every module the ttbar jobs need" preflight_repo_imports

preflight_xrootd_open_and_genweight() {
    timeout 60 nice python -c "
import sys
sys.path.insert(0, '.')
import uproot
from studies.m0m1j0_cms.design_checks.common import fetch_file_list
try:
    url = fetch_file_list(67801)[0]
    f = uproot.open(url)
    keys = set(f['Events'].keys())
    n_branches = len(keys)
    print(f'  record 67801: opened {url} OK, Events tree has {n_branches} branches (metadata only)')
    if 'genWeight' not in keys:
        print('  MISSING: genWeight branch not found in this file')
        sys.exit(1)
    print('  OK: genWeight branch present')
    missing_trig = [b for b in ('HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ', 'HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ') if b not in keys]
    if missing_trig:
        print(f'  MISSING: trigger branch(es) {missing_trig}')
        sys.exit(1)
    print('  OK: both trigger branches present')
except Exception as e:
    print(f'  FAILED to open/verify -- {type(e).__name__}: {e}')
    sys.exit(1)
" || { echo "PREFLIGHT FAILED: XRootD open or genWeight/trigger-branch check failed for the ttbar record's first file" >&2; exit 1; }
}
skip_or_run "XRootD open + genWeight/trigger-branch check (ttbar record's first file)" preflight_xrootd_open_and_genweight

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
            echo "PREFLIGHT FAILED: \$HOME/atlas-utilization has uncommitted changes -- this task must never touch it." >&2
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
    local dirs=("$TTBAR_LOG_BASE" "$TTBAR_OUTPUT_BASE")
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
preflight_dirs

preflight_output_empty() {
    local nonempty=()
    if [[ -d "$TTBAR_OUTPUT_BASE" ]]; then
        while IFS= read -r -d '' d; do
            if [[ -n "$(ls -A "$d" 2>/dev/null)" ]]; then
                nonempty+=("$d")
            fi
        done < <(find "$TTBAR_OUTPUT_BASE" -mindepth 1 -maxdepth 1 -type d -name 'job_*' -print0 2>/dev/null)
    fi
    if [[ ${#nonempty[@]} -gt 0 ]]; then
        echo "PREFLIGHT FAILED: ${#nonempty[@]} job_* output directories already exist under $TTBAR_OUTPUT_BASE" >&2
        echo "Refusing to mix a fresh submission with leftover output -- move/remove them yourself first." >&2
        exit 1
    fi
    echo "  OK: $TTBAR_OUTPUT_BASE has no pre-existing job_* output directories"
}
preflight_output_empty

echo "=== Generating ttbar job-index map (fresh portal fetch) ==="
MAPPING_FILE="${TTBAR_OUTPUT_BASE}/job_index_map.txt"
SUMMARY_FILE="${TTBAR_OUTPUT_BASE}/job_index_map_summary.json"
LIMIT_ARGS=()
if [[ "$MODE" == "pilot" ]]; then
    LIMIT_ARGS=(--limit-files 2)
fi
python studies/m0m1j0_cms/cluster/generate_ttbar_job_index_map.py \
    --out-map "$MAPPING_FILE" --out-summary "$SUMMARY_FILE" "${LIMIT_ARGS[@]}" \
    || { echo "PREFLIGHT FAILED: could not generate the ttbar job-index map from the portal" >&2; exit 1; }

TOTAL_JOBS=$(python -c "import json; print(json.load(open('$SUMMARY_FILE'))['total_jobs'])")
if [[ -z "$TOTAL_JOBS" || "$TOTAL_JOBS" -lt 1 ]]; then
    echo "PREFLIGHT FAILED: job-index map reports $TOTAL_JOBS total jobs -- refusing to submit" >&2
    exit 1
fi
echo "  total jobs to submit: $TOTAL_JOBS"

echo "=== Preflight passed -- submitting ($MODE) ==="

JOBID=$(submit -J "1-${TOTAL_JOBS}" \
                -o "${TTBAR_LOG_BASE}/m0m1j0_ttbar_^array_index^.out" \
                -e "${TTBAR_LOG_BASE}/m0m1j0_ttbar_^array_index^.err" \
                -v OUTPUT_BASE="$TTBAR_OUTPUT_BASE",REPO_DIR="$REPO_DIR",MAPPING_FILE="$MAPPING_FILE" \
                studies/m0m1j0_cms/cluster/pbs_m0m1j0_ttbar.sh)
echo "$JOBID"
echo "m0m1j0_ttbar_${MODE} $JOBID $TOTAL_JOBS" >> "${TTBAR_LOG_BASE}/submitted_jobs.txt"

echo ""
echo "Submitted: m0m1j0 ttbar $MODE array ($TOTAL_JOBS jobs)."
echo "Output under: $TTBAR_OUTPUT_BASE/"
echo "Logs under:   $TTBAR_LOG_BASE/"
if [[ "$MODE" == "pilot" ]]; then
    echo "This is the PILOT ONLY. Review its sanity plots before running MODE=full."
fi
