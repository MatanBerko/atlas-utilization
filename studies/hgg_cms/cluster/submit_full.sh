#!/bin/bash
# ---------------------------------------------------------------------------
# submit_full.sh
#
# Submits the FULL H->gamma-gamma cluster run: one data array job
# (-J 1-133, all 133 DoubleEG files across records 30521+30554) and 6
# signal jobs (one per production mode, ALL files of that record --
# max_files_to_process is NOT set in the full configs). All output goes
# under a NEW tree, /storage/agrp/berkom/atlas-utilization/output/hgg_full/
# (logs under .../logs/hgg_full/) -- entirely separate from the pilot's
# hgg_pilot/ tree, which is left untouched.
#
# REFUSES TO RUN unless given --i-reviewed-pilot-and-d3 explicitly. This
# is not a rubber stamp -- before passing it, you must have actually
# checked, per studies/hgg_cms/cluster/PILOT_CHECKLIST.md:
#   1. D1/D2's 6 acceptance-criteria comparisons are all true (or any
#      difference has been root-caused and reported, not forced).
#   2. D3's cutflow/efficiency/shape numbers look sane, and its
#      timing/memory numbers were actually used to size the #PBS -l
#      mem/walltime values now baked into pbs_hgg_data_array.sh and
#      pbs_hgg_signal.sh (see those scripts' own header comments for the
#      numbers used).
#   3. The pilot's own 8 jobs (2 data + 6 signal) all finished with real
#      output, dedup_removed_simulation_events == 0 for every signal
#      pilot, and no blinding violation.
#   4. The Part-1 finding about the data array's index<->file mapping
#      relying on the CERN Open Data portal's file-listing order being
#      stable (see studies/hgg_cms/impl_checks/mapping_check/) has been
#      read and accepted, or the frozen-file-list fix it proposes has
#      been requested instead.
#
# PREFLIGHT (same as submit_pilot.sh, plus full-run-specific checks) runs
# BEFORE any qsub; nothing is submitted if anything fails:
#   - conda activation; python/XRootD package versions; an XRootD
#     metadata-only open of one data file and one signal file; $REPO_DIR
#     on this branch at origin's current tip with a clean tree; every
#     log/output directory writable.
#   - hgg_full/ output directories (data/ and each signal/<label>/) must
#     be empty or not exist yet -- refuses to overwrite a previous full
#     run's partial output.
#   - a Lustre space estimate (see estimate_and_check_space() below):
#     measures the PILOT's own real output size on disk (du -sb) and
#     scales it to the full run's file counts; compares against `lfs
#     quota` if that command exists, otherwise prints the estimate and
#     the exact `lfs quota` command to run by hand, and requires
#     --quota-checked-manually to proceed without an automated check.
#
# DRY_RUN=1: identical semantics to submit_pilot.sh -- skips the checks
# that need the real cluster (marked explicitly), still runs the pure
# local/filesystem checks and the Lustre-space ESTIMATE (skipping the
# actual `lfs quota` call), and prints every qsub command instead of
# submitting.
#
# All submitted job IDs are printed and saved to
# logs/hgg_full/submitted_jobs.txt (one line per job), for status_full.sh
# to read.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-feature/hgg-selection-and-output}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
PILOT_BASE="${PILOT_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_pilot}"
FULL_BASE="${FULL_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_full}"
FULL_LOG_BASE="${FULL_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_full}"
LUSTRE_QUOTA_PATH="${LUSTRE_QUOTA_PATH:-/storage/agrp/berkom}"
DRY_RUN="${DRY_RUN:-0}"

REVIEWED=0
QUOTA_CHECKED_MANUALLY=0
for arg in "$@"; do
    case "$arg" in
        --i-reviewed-pilot-and-d3) REVIEWED=1 ;;
        --quota-checked-manually) QUOTA_CHECKED_MANUALLY=1 ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

if [[ "$REVIEWED" != "1" ]]; then
    cat >&2 <<'EOF'
REFUSING TO SUBMIT: pass --i-reviewed-pilot-and-d3 to confirm you have
actually checked, per studies/hgg_cms/cluster/PILOT_CHECKLIST.md:
  1. D1/D2's 6 acceptance-criteria comparisons are all true (or any
     difference has been root-caused and reported, not forced).
  2. D3's numbers were used to size pbs_hgg_data_array.sh's and
     pbs_hgg_signal.sh's #PBS -l mem/walltime values.
  3. The pilot's 8 jobs all finished with real output, dedup removed 0
     simulation events everywhere, no blinding violation.
  4. The Part-1 index<->file mapping finding (see
     studies/hgg_cms/impl_checks/mapping_check/) has been read and
     accepted.
This script does not submit anything without this flag.
EOF
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
    local desc="$1"
    shift
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "[DRY_RUN] skipping: $desc (requires the real cluster)"
        return 0
    fi
    "$@"
}

# ---------------------------------------------------------------------------
# Preflight (same battery as submit_pilot.sh)
# ---------------------------------------------------------------------------
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
    timeout 30 nice python -c "
import sys
mods = ['uproot', 'awkward', 'numpy', 'yaml']
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
" || { echo "PREFLIGHT FAILED: required python package(s) missing -- see docker/requirements.txt" >&2; exit 1; }
    echo "  OK: uproot/awkward/numpy/yaml + an XRootD stack are importable"
}
skip_or_run "python package + XRootD-stack import/version check" preflight_python_stack

preflight_xrootd_open() {
    timeout 60 nice python -c "
import sys
import uproot
urls = {
    'DoubleEG Run2016G (data)': 'root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root',
    'GluGluHToGG (signal)': 'root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root',
}
ok = True
for label, url in urls.items():
    try:
        f = uproot.open(url)
        n_branches = len(f['Events'].keys())
        print(f'  {label}: opened OK, Events tree has {n_branches} branches (metadata only, no events read)')
    except Exception as e:
        print(f'  {label}: FAILED to open -- {type(e).__name__}: {e}')
        ok = False
if not ok:
    sys.exit(1)
" || { echo "PREFLIGHT FAILED: XRootD metadata-only open failed" >&2; exit 1; }
    echo "  OK: one data file and one signal file open over XRootD (metadata only)"
}
skip_or_run "XRootD metadata-only open of one data + one signal file" preflight_xrootd_open

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

preflight_dirs() {
    local dirs=(
        "$FULL_LOG_BASE/data" "$FULL_LOG_BASE/signal"
        "$FULL_BASE/data" "$FULL_BASE/signal"
    )
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
    echo "  OK: all log/output base directories exist and are writable"
}
preflight_dirs   # pure local filesystem check -- runs even under DRY_RUN

preflight_full_outputs_empty() {
    local check_dirs=("$FULL_BASE/data")
    local label
    for label in ggh vbf wplush wminush zh tth; do
        check_dirs+=("$FULL_BASE/signal/${label}")
    done
    local nonempty=() d
    for d in "${check_dirs[@]}"; do
        if [[ -d "$d" ]] && [[ -n "$(ls -A "$d" 2>/dev/null)" ]]; then
            nonempty+=("$d")
        fi
    done
    if [[ ${#nonempty[@]} -gt 0 ]]; then
        echo "PREFLIGHT FAILED: these full-run output directories already exist and are non-empty:" >&2
        printf '  %s\n' "${nonempty[@]}" >&2
        echo "Refusing to overwrite a previous full-run attempt -- move/remove them yourself first." >&2
        exit 1
    fi
    echo "  OK: no full-run output directory is pre-populated"
}
preflight_full_outputs_empty   # pure local filesystem check -- runs even under DRY_RUN

# ---------------------------------------------------------------------------
# Lustre space estimate: measure the PILOT's real output size (du -sb) and
# scale it to the full run's file counts. See PILOT_CHECKLIST.md's own
# "Storage estimate" section for the formula this refines with real
# numbers once they exist.
# ---------------------------------------------------------------------------
estimate_and_check_space() {
    local data_job1_bytes=0 data_job2_bytes=0 have_data_measurement=0
    if [[ -d "${PILOT_BASE}/data/job_1/selected" ]]; then
        data_job1_bytes=$(du -sb "${PILOT_BASE}/data/job_1/selected" 2>/dev/null | cut -f1)
        data_job1_bytes=${data_job1_bytes:-0}
        have_data_measurement=1
    fi
    if [[ -d "${PILOT_BASE}/data/job_2/selected" ]]; then
        data_job2_bytes=$(du -sb "${PILOT_BASE}/data/job_2/selected" 2>/dev/null | cut -f1)
        data_job2_bytes=${data_job2_bytes:-0}
    fi

    local avg_data_bytes_per_file=0
    if [[ "$have_data_measurement" == "1" ]]; then
        avg_data_bytes_per_file=$(( (data_job1_bytes + data_job2_bytes) / 2 ))
    fi
    local data_total_estimate=$(( avg_data_bytes_per_file * 133 ))

    # Signal: per-label pilot measurement (1 file) scaled by that record's
    # total file count (signal_sumw.json).
    declare -A SIGNAL_NFILES=( [ggh]=3 [vbf]=13 [wplush]=4 [wminush]=15 [zh]=20 [tth]=16 )
    local signal_total_estimate=0
    local label bytes have_signal_measurement=0
    for label in "${!SIGNAL_NFILES[@]}"; do
        bytes=0
        if [[ -d "${PILOT_BASE}/signal/${label}/selected" ]]; then
            bytes=$(du -sb "${PILOT_BASE}/signal/${label}/selected" 2>/dev/null | cut -f1)
            bytes=${bytes:-0}
            have_signal_measurement=1
        fi
        signal_total_estimate=$(( signal_total_estimate + bytes * SIGNAL_NFILES[$label] ))
    done

    local total_estimate=$(( data_total_estimate + signal_total_estimate ))
    local total_estimate_gb
    total_estimate_gb=$(awk -v b="$total_estimate" 'BEGIN{printf "%.3f", b/1024/1024/1024}')

    if [[ "$have_data_measurement" == "0" || "$have_signal_measurement" == "0" ]]; then
        echo "  NOTE: could not measure some pilot output directories directly (looked under $PILOT_BASE)." >&2
        echo "  Estimate below is INCOMPLETE -- run this by hand and re-check:" >&2
        echo "    du -sh ${PILOT_BASE}/data/job_1/selected ${PILOT_BASE}/data/job_2/selected" >&2
        echo "    du -sh ${PILOT_BASE}/signal/*/selected" >&2
    fi
    echo "  Estimated full-run output size: ~${total_estimate_gb} GB (data: $(( data_total_estimate / 1024 / 1024 )) MB, signal: $(( signal_total_estimate / 1024 / 1024 )) MB)"

    if [[ "$DRY_RUN" == "1" ]]; then
        echo "[DRY_RUN] skipping the actual free-space/quota check (requires the real cluster)"
        return 0
    fi

    if command -v lfs >/dev/null 2>&1; then
        echo "  lfs quota output for $LUSTRE_QUOTA_PATH (best-effort parse -- read it yourself too):"
        lfs quota -u "$USER" "$LUSTRE_QUOTA_PATH" 2>&1 | sed 's/^/    /' || true
        echo "  (This script does not auto-parse lfs quota's output -- formats vary across sites/versions."
        echo "   Compare the 'used'/'limit' (or 'quota') columns above against the ~${total_estimate_gb} GB estimate yourself.)"
        if [[ "$QUOTA_CHECKED_MANUALLY" != "1" ]]; then
            echo "PREFLIGHT FAILED: pass --quota-checked-manually after reading the lfs quota output above and confirming there is enough free space for ~${total_estimate_gb} GB." >&2
            exit 1
        fi
        echo "  OK: --quota-checked-manually was passed -- proceeding on your confirmation."
    else
        echo "  'lfs' command not found -- cannot check quota automatically." >&2
        echo "  Run this yourself on the cluster and confirm there is room for ~${total_estimate_gb} GB, then re-run with --quota-checked-manually:" >&2
        echo "    lfs quota -u \$USER $LUSTRE_QUOTA_PATH" >&2
        if [[ "$QUOTA_CHECKED_MANUALLY" != "1" ]]; then
            echo "PREFLIGHT FAILED: --quota-checked-manually not passed." >&2
            exit 1
        fi
        echo "  OK: --quota-checked-manually was passed -- proceeding on your confirmation."
    fi
}
echo "--- Lustre space estimate ---"
estimate_and_check_space

echo "=== Preflight passed -- submitting ==="

mkdir -p "$FULL_LOG_BASE"
JOBLIST_FILE="${FULL_LOG_BASE}/submitted_jobs.txt"
: > "$JOBLIST_FILE"

# ---------------------------------------------------------------------------
# DATA: one array job, all 133 files.
# ---------------------------------------------------------------------------
echo "--- DATA: full array, 133 files ---"
DATA_JOBID=$(submit -J 1-133 \
    -v OUTPUT_BASE="${FULL_BASE}/data" \
    -o "${FULL_LOG_BASE}/data/hgg_data_full_^array_index^.out" \
    -e "${FULL_LOG_BASE}/data/hgg_data_full_^array_index^.err" \
    studies/hgg_cms/cluster/pbs_hgg_data_array.sh)
echo "  $DATA_JOBID"
echo "data_array $DATA_JOBID" >> "$JOBLIST_FILE"

# ---------------------------------------------------------------------------
# SIGNAL: one job per record, ALL files (unmodified full configs -- no
# max_files_to_process override, unlike the pilot).
# ---------------------------------------------------------------------------
echo "--- SIGNAL: 6 records, all files ---"
declare -A SIGNAL_CONFIGS=(
    [ggh]=config.cms_hgg_signal_ggh.yaml
    [vbf]=config.cms_hgg_signal_vbf.yaml
    [wplush]=config.cms_hgg_signal_wplush.yaml
    [wminush]=config.cms_hgg_signal_wminush.yaml
    [zh]=config.cms_hgg_signal_zh.yaml
    [tth]=config.cms_hgg_signal_tth.yaml
)
for label in "${!SIGNAL_CONFIGS[@]}"; do
    base_config="${SIGNAL_CONFIGS[$label]}"
    echo "  submitting $label (config=$base_config)"
    JOBID=$(submit \
        -v CONFIG="$base_config",LABEL="${label}_full",OUTPUT_BASE="${FULL_BASE}/signal/${label}" \
        -o "${FULL_LOG_BASE}/signal/hgg_signal_${label}_full.out" \
        -e "${FULL_LOG_BASE}/signal/hgg_signal_${label}_full.err" \
        studies/hgg_cms/cluster/pbs_hgg_signal.sh)
    echo "    $JOBID"
    echo "signal_${label} $JOBID" >> "$JOBLIST_FILE"
done

echo ""
echo "Submitted: 1 data array job (133 subjobs) + 6 signal jobs."
echo "All output under: $FULL_BASE/"
echo "All logs under:    $FULL_LOG_BASE/"
echo "Job IDs saved to:  $JOBLIST_FILE"
echo "Check status with: bash studies/hgg_cms/cluster/status_full.sh"
