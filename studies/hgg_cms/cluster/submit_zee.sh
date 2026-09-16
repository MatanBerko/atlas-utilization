#!/bin/bash
# ---------------------------------------------------------------------------
# submit_zee.sh
#
# Implementation task 6, Part 4 (REVISED TWICE, 16 Sep 2026): submits the
# Z->e+e- control-region run -- TWO array jobs, both using
# pbs_hgg_zee_array.sh:
#   1. data (151 subjobs, config.cms_hgg_zee_data.yaml -- SingleElectron,
#      NOT DoubleEG; see that config's own comment)
#   2. DY sim ( 41 subjobs, config.cms_hgg_zee_dy.yaml)
# 192 scheduler entries total. All output under a NEW tree,
# /storage/agrp/berkom/atlas-utilization/output/hgg_zee/ (logs under
# .../logs/hgg_zee/) -- entirely separate from hgg_full/.
#
# REVISED from an earlier 4-variant design (see pbs_hgg_zee_array.sh's own
# header for the full story): the "trigger-efficiency" sample is no
# longer a separate cluster job -- both configs store the diphoton bit
# (via extra_scalar_branches) and the analysis-layer selects the energy
# -scale, trigger-efficiency, and Mass90-sculpting-demonstration sub
# -samples OFFLINE from this one dataset (studies/hgg_cms/validation/zee/).
#
# REVISED AGAIN: the data config now reads SingleElectron (30529+30562,
# 151 files), not DoubleEG (30521+30554, 133 files) -- DoubleEG's own
# trigger-stream list never includes HLT_Ele27_WPTight_Gsf at all, so an
# "Ele27-fired" subset of DoubleEG would have been conditioned on ALSO
# firing a DoubleEG trigger (biasing exactly the measurements this sample
# exists to make). Verified against the CERN Open Data portal's own
# record metadata -- see studies/hgg_cms/impl_checks/mapping_check/
# zee_trigger_stream_verification.md.
#
# THIS TASK DOES NOT RUN THIS SCRIPT. Prepared only, per the task's own
# "prepare, don't submit" instruction -- read PILOT_FIRST_RECOMMENDATION
# below before ever running it for real.
#
# PILOT_FIRST_RECOMMENDATION: no Z->ee-specific pilot has been run on this
# cluster -- pbs_hgg_zee_array.sh's resource requests are REUSED from the
# main run's measured DoubleEG-job numbers (reasoned to be a fair
# estimate, with an explicit flag for SingleElectron's somewhat higher
# per-file event count -- see that script's own header), not directly
# measured for these 2 configs. Strongly recommended: first run this
# script with --pilot (2 data + 2 DY subjobs, 4 total, not 192), inspect
# real wall/mem numbers with `qstat -fx <jobid>` the same way
# PILOT_CHECKLIST.md describes for the main run, and re-check
# pbs_hgg_zee_array.sh's mem/walltime against them before ever passing
# --full.
#
# PREFLIGHT (same battery as submit_full.sh) runs BEFORE any qsub; nothing
# is submitted if anything fails: conda activation; python/XRootD package
# versions; an XRootD metadata-only open of one SingleElectron file and
# one DY file (also checks both trigger branches are present); $REPO_DIR
# on this branch at origin's current tip with a clean tree; every log/
# output directory writable; hgg_zee/ output directories must be empty or
# not exist yet.
#
# DRY_RUN=1: skips the checks that need the real cluster, still runs the
# pure local/filesystem checks, and prints every qsub command instead of
# submitting.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-feature/hgg-selection-and-output}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
ZEE_BASE="${ZEE_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_zee}"
ZEE_LOG_BASE="${ZEE_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_zee}"
LUSTRE_QUOTA_PATH="${LUSTRE_QUOTA_PATH:-/storage/agrp/berkom}"
DRY_RUN="${DRY_RUN:-0}"

MODE=""   # "pilot" or "full"
for arg in "$@"; do
    case "$arg" in
        --pilot) MODE="pilot" ;;
        --full) MODE="full" ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done
if [[ -z "$MODE" ]]; then
    echo "Usage: bash submit_zee.sh --pilot   (2 data + 2 DY subjobs, 4 total)" >&2
    echo "   or: bash submit_zee.sh --full    (the real run, 192 subjobs -- read PILOT_FIRST_RECOMMENDATION above first)" >&2
    exit 1
fi

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
    local desc="$1"; shift
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "[DRY_RUN] skipping: $desc (requires the real cluster)"
        return 0
    fi
    "$@"
}

echo "=== Preflight ==="

preflight_conda() {
    if [[ ! -f "$CONDA_PROFILE" ]]; then
        echo "PREFLIGHT FAILED: conda profile not found at $CONDA_PROFILE" >&2; exit 1
    fi
    # shellcheck disable=SC1090
    source "$CONDA_PROFILE" || { echo "PREFLIGHT FAILED: failed to source $CONDA_PROFILE" >&2; exit 1; }
    conda activate "$CONDA_ENV" || { echo "PREFLIGHT FAILED: failed to activate conda env $CONDA_ENV" >&2; exit 1; }
    echo "  OK: activated conda env $CONDA_ENV"
}
skip_or_run "conda profile + env activation" preflight_conda

preflight_xrootd_open() {
    timeout 60 nice python -c "
import sys, uproot
urls = {
    'SingleElectron Run2016G (record 30529, data)': 'root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleElectron/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/110000/43B00DA0-41AF-D042-9F41-7F95FBE5E59F.root',
    'DYJetsToLL_M-50 (record 35669)': 'root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/30000/0082C29D-E74C-024A-BE9B-97B29EE7A4A2.root',
}
ok = True
for label, url in urls.items():
    try:
        f = uproot.open(url)
        keys = f['Events'].keys()
        assert 'HLT_Ele27_WPTight_Gsf' in keys, 'HLT_Ele27_WPTight_Gsf missing'
        assert 'HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90' in keys, 'diphoton trigger missing'
        assert 'Photon_electronVeto' in keys, 'Photon_electronVeto missing'
        print(f'  {label}: opened OK, {len(keys)} branches, both trigger bits present')
    except Exception as e:
        print(f'  {label}: FAILED -- {type(e).__name__}: {e}')
        ok = False
if not ok:
    sys.exit(1)
" || { echo "PREFLIGHT FAILED: XRootD metadata-only open failed" >&2; exit 1; }
}
skip_or_run "XRootD metadata-only open + branch check (data + DY)" preflight_xrootd_open

preflight_git() {
    if [[ ! -d "$REPO_DIR/.git" ]]; then
        echo "PREFLIGHT FAILED: $REPO_DIR is not a git checkout" >&2; exit 1
    fi
    local branch commit remote_commit
    branch=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)
    if [[ "$branch" != "$EXPECTED_BRANCH" ]]; then
        echo "PREFLIGHT FAILED: $REPO_DIR is on branch '$branch', expected '$EXPECTED_BRANCH'" >&2; exit 1
    fi
    if [[ -n "$(git -C "$REPO_DIR" status --porcelain)" ]]; then
        echo "PREFLIGHT FAILED: $REPO_DIR has a dirty working tree:" >&2
        git -C "$REPO_DIR" status --short >&2; exit 1
    fi
    git -C "$REPO_DIR" fetch origin "$EXPECTED_BRANCH" --quiet
    commit=$(git -C "$REPO_DIR" rev-parse HEAD)
    remote_commit=$(git -C "$REPO_DIR" rev-parse "origin/$EXPECTED_BRANCH")
    if [[ "$commit" != "$remote_commit" ]]; then
        echo "PREFLIGHT FAILED: local HEAD ($commit) != origin/$EXPECTED_BRANCH ($remote_commit)" >&2; exit 1
    fi
    echo "  OK: branch=$branch commit=$commit matches origin/$EXPECTED_BRANCH, clean tree"
}
skip_or_run "\$REPO_DIR branch/commit/clean-tree check" preflight_git

preflight_dirs() {
    local dirs=("$ZEE_LOG_BASE" "$ZEE_BASE")
    local d probe
    for d in "${dirs[@]}"; do
        mkdir -p "$d" || { echo "PREFLIGHT FAILED: could not create $d" >&2; exit 1; }
        probe="$d/.preflight_write_test_$$"
        if ! ( : > "$probe" ) 2>/dev/null; then
            echo "PREFLIGHT FAILED: $d exists but is not writable" >&2; exit 1
        fi
        rm -f "$probe"
    done
    echo "  OK: log/output base directories exist and are writable"
}
preflight_dirs

preflight_outputs_empty() {
    local check_dirs=("$ZEE_BASE/data_${MODE}" "$ZEE_BASE/dy_${MODE}")
    local nonempty=() d
    for d in "${check_dirs[@]}"; do
        if [[ -d "$d" ]] && [[ -n "$(ls -A "$d" 2>/dev/null)" ]]; then
            nonempty+=("$d")
        fi
    done
    if [[ ${#nonempty[@]} -gt 0 ]]; then
        echo "PREFLIGHT FAILED: these output directories already exist and are non-empty:" >&2
        printf '  %s\n' "${nonempty[@]}" >&2
        echo "Refusing to overwrite a previous attempt -- move/remove them yourself first." >&2
        exit 1
    fi
}
preflight_outputs_empty

echo "=== Preflight passed -- submitting ($MODE) ==="

mkdir -p "$ZEE_LOG_BASE"
JOBLIST_FILE="${ZEE_LOG_BASE}/submitted_jobs_${MODE}.txt"
: > "$JOBLIST_FILE"

if [[ "$MODE" == "pilot" ]]; then
    ARRAY_RANGE_DATA="1-2"
    ARRAY_RANGE_DY="1-2"
else
    ARRAY_RANGE_DATA="1-151"
    ARRAY_RANGE_DY="1-41"
fi

submit_variant() {
    local name="$1" config="$2" is_data="$3" total_files="$4" array_range="$5" output_base="$6"
    echo "--- $name: $array_range of $total_files files ---"
    local jobid
    jobid=$(submit -J "$array_range" \
        -v CONFIG="$config",IS_DATA="$is_data",TOTAL_FILES="$total_files",OUTPUT_BASE="$output_base" \
        -o "${ZEE_LOG_BASE}/${name}_^array_index^.out" \
        -e "${ZEE_LOG_BASE}/${name}_^array_index^.err" \
        studies/hgg_cms/cluster/pbs_hgg_zee_array.sh)
    echo "  $jobid"
    echo "$name $jobid" >> "$JOBLIST_FILE"
}

submit_variant "data_${MODE}" config.cms_hgg_zee_data.yaml true 151 "$ARRAY_RANGE_DATA" \
    "${ZEE_BASE}/data_${MODE}"
submit_variant "dy_${MODE}" config.cms_hgg_zee_dy.yaml false 41 "$ARRAY_RANGE_DY" \
    "${ZEE_BASE}/dy_${MODE}"

echo ""
echo "Submitted ($MODE): 2 array jobs."
echo "All output under: $ZEE_BASE/"
echo "All logs under:    $ZEE_LOG_BASE/"
echo "Job IDs saved to:  $JOBLIST_FILE"
echo "Check status with: bash studies/hgg_cms/cluster/status_zee.sh --mode $MODE"
