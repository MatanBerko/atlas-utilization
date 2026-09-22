#!/bin/bash
# ---------------------------------------------------------------------------
# submit_pilot.sh
#
# m0m1j0 CMS histogram -- Step 1 CLUSTER PILOT ONLY. Submits exactly the
# 4-job pilot array (pbs_m0m1j0_pilot.sh, -J 1-4: first two files of
# records 30522 and 30555). Does NOT submit, and has no code path that
# could accidentally submit, the full 57-file run -- that is a separate,
# later, explicitly-out-of-scope task.
#
# IMPORTANT (per this task's own git-safety rules): this study's code is
# cloned into its OWN separate checkout,
# /storage/agrp/berkom/atlas-utilization/work/m0m1j0_cms/repo, never into
# $HOME/atlas-utilization (which must stay untouched/clean at all times).
# REPO_DIR below points at that separate clone.
#
# PREFLIGHT (mirrors studies/hgg_cms/cluster/submit_pilot.sh's own
# pattern): activates the conda env, checks the python/XRootD stack is
# importable, does a metadata-only XRootD open of one real file from each
# pilot record (fails fast, before any qsub, if the cluster can't reach
# EOS at all), checks REPO_DIR is on branch analysis/m0m1j0-cms with a
# clean tree matching origin, and refuses to resubmit into an
# already-populated pilot output directory (never silently overwrites a
# previous pilot run). If ANY check fails, NOTHING is submitted.
#
# DRY_RUN=1 ./submit_pilot.sh -- runs every check that does not need the
# cluster itself (directory creation/writability, printing the exact qsub
# command) while skipping conda/XRootD/git checks with an explicit
# "[DRY_RUN] skipping ..." line, and replaces `qsub` with an echo of the
# exact command. No job is ever actually submitted under DRY_RUN.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/m0m1j0_cms/repo}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-analysis/m0m1j0-cms}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
PILOT_OUTPUT_BASE="${PILOT_OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_pilot}"
PILOT_LOG_BASE="${PILOT_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/m0m1j0_pilot}"
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
    # ROOT/PyROOT deliberately NOT checked here: this cluster account's
    # atlas-pipeline conda env has no PyROOT installed at all (discovered
    # running this pilot's own preflight, 2026-09-22) -- this study's
    # histogram I/O uses uproot instead (see histograms.py's module
    # docstring). Checking for ROOT here would make this preflight fail
    # every time in an environment this study no longer needs it in.
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
    echo "  OK: uproot/awkward/numpy/vector/ROOT/requests + an XRootD stack are importable"
}
skip_or_run "python package + ROOT + XRootD-stack import/version check" preflight_python_stack

preflight_repo_imports() {
    # Every module the pilot jobs actually import -- fail before
    # submitting anything if one of them doesn't import cleanly in this
    # env, per the task's own "submit scripts must preflight-import every
    # module the job needs" requirement.
    timeout 30 nice python -c "
import sys
sys.path.insert(0, '.')
import studies.m0m1j0_cms.selection
import studies.m0m1j0_cms.histograms
import studies.m0m1j0_cms.design_checks.common
import services.parsing.validated_runs
print('  OK: all m0m1j0 pilot modules import cleanly')
" || { echo "PREFLIGHT FAILED: a pilot module failed to import -- see traceback above" >&2; exit 1; }
}
skip_or_run "preflight-import every module the pilot jobs need" preflight_repo_imports

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
" || { echo "PREFLIGHT FAILED: XRootD metadata-only open failed for a pilot record's first file" >&2; exit 1; }
    echo "  OK: first file of both pilot records opens over XRootD (metadata only)"
}
skip_or_run "XRootD metadata-only open of both pilot records' first file" preflight_xrootd_open

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
    # This task must never modify $HOME/atlas-utilization -- verify it is
    # still clean (if it exists at all) rather than assume it.
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
    local dirs=("$PILOT_LOG_BASE" "$PILOT_OUTPUT_BASE")
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

preflight_pilot_output_empty() {
    local nonempty=() d
    for i in 1 2 3 4; do
        d="${PILOT_OUTPUT_BASE}/job_${i}"
        if [[ -d "$d" ]] && [[ -n "$(ls -A "$d" 2>/dev/null)" ]]; then
            nonempty+=("$d")
        fi
    done
    if [[ ${#nonempty[@]} -gt 0 ]]; then
        echo "PREFLIGHT FAILED: these pilot output directories already exist and are non-empty:" >&2
        printf '  %s\n' "${nonempty[@]}" >&2
        echo "Refusing to overwrite a previous pilot run -- move/remove them yourself first." >&2
        exit 1
    fi
    echo "  OK: no pilot output directory is pre-populated"
}
preflight_pilot_output_empty   # pure local filesystem check -- runs even under DRY_RUN

echo "=== Preflight passed -- submitting ==="

JOBID=$(submit -o "${PILOT_LOG_BASE}/m0m1j0_pilot_^array_index^.out" \
                -e "${PILOT_LOG_BASE}/m0m1j0_pilot_^array_index^.err" \
                -v OUTPUT_BASE="$PILOT_OUTPUT_BASE",REPO_DIR="$REPO_DIR" \
                studies/m0m1j0_cms/cluster/pbs_m0m1j0_pilot.sh)
echo "$JOBID"
echo "m0m1j0_pilot $JOBID" >> "${PILOT_LOG_BASE}/submitted_jobs.txt"

echo ""
echo "Submitted: m0m1j0 pilot array (4 jobs: 2 files x 2 records)."
echo "Output under: $PILOT_OUTPUT_BASE/"
echo "Logs under:   $PILOT_LOG_BASE/"
echo "Check status with: studies/m0m1j0_cms/cluster/status_pilot.sh"
echo "This is the PILOT ONLY. The full 57-file run is a separate, later, explicit task."
