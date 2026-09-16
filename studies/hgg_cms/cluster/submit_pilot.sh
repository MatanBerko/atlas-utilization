#!/bin/bash
# ---------------------------------------------------------------------------
# submit_pilot.sh
#
# Submits, together, everything that must pass BEFORE the full run is
# even considered:
#   1. D1/D2 -- exact reproduction of check_c_trigger_mimicking.py /
#      check_b_vertex.py, as a cluster job (pbs_hgg_d1d2_reproduce.sh).
#   2. D3 -- one full DoubleEG Run2016G file + one full ggH file, through
#      the real production configs, with the D3 analysis (cutflow,
#      efficiency, shape, plots, preview yield, timing) attached
#      (pbs_hgg_d3_data.sh / pbs_hgg_d3_signal.sh).
#   3. A SMALL PILOT of the full run itself: 2 DATA files (via the data
#      job array, indices 1-2 only) + 1 file per SIGNAL record (via
#      max_files_to_process:1 override configs, generated on the fly
#      here).
# None of this is the full run. ALL of the above write under
# /storage/agrp/berkom/atlas-utilization/output/hgg_pilot/ (and logs
# under .../logs/hgg_pilot/) -- kept entirely separate from the full
# run's own output directories, which stay untouched and empty until a
# human explicitly submits the full run.
#
# DO NOT extend this to the full submission (pbs_hgg_data_array.sh's full
# -J 1-133, and pbs_hgg_signal.sh with max_files_to_process left unset)
# until: (a) D1/D2's acceptance criteria (pbs_hgg_d1d2_reproduce.sh's own
# comment header) are met or any difference has been root-caused and
# reported -- not forced into agreement; (b) D3's cutflow/efficiency/
# shape/timing numbers have been reviewed and used to replace the
# placeholder #PBS -l mem/walltime values in pbs_hgg_data_array.sh and
# pbs_hgg_signal.sh; (c) this pilot's jobs have all finished and their
# logs/outputs have been reviewed against
# studies/hgg_cms/cluster/PILOT_CHECKLIST.md; and (d) a human has
# explicitly decided to proceed. This script does NOT auto-continue to
# the full run -- it only submits these validation + pilot jobs and
# stops.
#
# PREFLIGHT: before ANY qsub, this script activates the conda env and
# runs a battery of checks (python package versions, an XRootD
# metadata-only open of both D3 files, that $REPO_DIR is on the right
# branch/commit with a clean tree, that every log/output directory
# exists and is writable, and that no pilot output directory is already
# populated from a previous run). If ANY check fails, NOTHING is
# submitted -- a half-submitted pilot is not possible. Preflight python
# checks run under `nice` (this runs on the shared analysis/login node)
# and are bounded by `timeout` so a stuck network call cannot hang this
# script for minutes.
#
# DRY_RUN=1 ./submit_pilot.sh -- runs everything that does NOT need the
# actual cluster (directory creation/writability checks against whatever
# PILOT_BASE/PILOT_LOG_BASE resolve to, the real pilot-config YAML
# templating, and printing the exact qsub commands + log paths that would
# be used) while SKIPPING, with an explicit "[DRY_RUN] skipping ..."
# line, the checks that inherently need the cluster (conda activation,
# the python-package/XRootD-stack check, the XRootD network open, and the
# $HOME/atlas-utilization git check) and replacing every `qsub` call with
# an echo of the exact command. No job is ever actually submitted under
# DRY_RUN.
#
# This script itself does not run python/qsub in this repo's own CI or
# local-development context -- it is meant to be run BY HAND, on the
# cluster login node, after `git pull`-ing this branch there (DRY_RUN=1
# is the one exception -- see above).
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-feature/hgg-selection-and-output}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
PILOT_BASE="${PILOT_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_pilot}"
PILOT_LOG_BASE="${PILOT_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_pilot}"
DRY_RUN="${DRY_RUN:-0}"

cd "$REPO_DIR"

# --- submit(): the ONLY thing that ever calls qsub. Under DRY_RUN, prints
# the exact command instead of running it and returns a clearly-fake
# jobid placeholder (so callers that capture "$(submit ...)" don't choke
# on an empty string). The trace line goes to stderr so command
# substitution never accidentally captures it instead of the real jobid. ---
submit() {
    echo "+ qsub $*" >&2
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "DRY-RUN-NO-JOBID"
    else
        qsub "$@"
    fi
}

skip_or_run() {
    # skip_or_run "description" -- function_name
    local desc="$1"
    shift
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "[DRY_RUN] skipping: $desc (requires the real cluster)"
        return 0
    fi
    "$@"
}

# ---------------------------------------------------------------------------
# Preflight
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
    'DoubleEG Run2016G (D3 data)': 'root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root',
    'GluGluHToGG (D3 signal)': 'root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root',
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
" || { echo "PREFLIGHT FAILED: XRootD metadata-only open failed for a D3 file" >&2; exit 1; }
    echo "  OK: both D3 files open over XRootD (metadata only)"
}
skip_or_run "XRootD metadata-only open of both D3 files" preflight_xrootd_open

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
    # "the expected commit" = whatever origin/<branch> currently points to
    # (not a hardcoded sha, which would go stale the moment this branch is
    # next pushed to) -- i.e. "you have pulled the latest, nothing stale,
    # nothing uncommitted."
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
        "$PILOT_LOG_BASE/d1d2" "$PILOT_LOG_BASE/d3" "$PILOT_LOG_BASE/data" "$PILOT_LOG_BASE/signal"
        "$PILOT_BASE/configs"
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

preflight_pilot_outputs_empty() {
    local check_dirs=(
        "$PILOT_BASE/d1d2_reproduce" "$PILOT_BASE/d3_data" "$PILOT_BASE/d3_signal_ggh"
        "$PILOT_BASE/data/job_1" "$PILOT_BASE/data/job_2"
    )
    local label
    for label in ggh vbf wplush wminush zh tth; do
        check_dirs+=("$PILOT_BASE/signal/${label}")
    done
    local nonempty=() d
    for d in "${check_dirs[@]}"; do
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
preflight_pilot_outputs_empty   # pure local filesystem check -- runs even under DRY_RUN

echo "=== Preflight passed -- submitting ==="

# ---------------------------------------------------------------------------
# D1/D2 + D3 (each script's own #PBS header already points at
# $PILOT_LOG_BASE/{d1d2,d3}/ and its own output under $PILOT_BASE/ -- see
# pbs_hgg_d1d2_reproduce.sh / pbs_hgg_d3_data.sh / pbs_hgg_d3_signal.sh)
# ---------------------------------------------------------------------------
echo "--- D1/D2: exact reproduction of check_c/check_b on the cluster ---"
D1D2_JOBID=$(submit studies/hgg_cms/cluster/pbs_hgg_d1d2_reproduce.sh)
echo "  $D1D2_JOBID"

echo "--- D3: one full DoubleEG file + one full ggH file ---"
D3_DATA_JOBID=$(submit studies/hgg_cms/cluster/pbs_hgg_d3_data.sh)
echo "  data: $D3_DATA_JOBID"
D3_SIGNAL_JOBID=$(submit studies/hgg_cms/cluster/pbs_hgg_d3_signal.sh)
echo "  signal: $D3_SIGNAL_JOBID"

# ---------------------------------------------------------------------------
# DATA pilot: 2 files (array indices 1-2), redirected to
# $PILOT_BASE/data/job_{1,2} via OUTPUT_BASE, with unique per-index logs
# under $PILOT_LOG_BASE/data/ (^array_index^ is OpenPBS's own array-index
# substitution token for -o/-e).
# ---------------------------------------------------------------------------
echo "--- DATA pilot: 2 files (array indices 1-2) ---"
submit -J 1-2 \
    -v OUTPUT_BASE="${PILOT_BASE}/data" \
    -o "${PILOT_LOG_BASE}/data/hgg_data_pilot_^array_index^.out" \
    -e "${PILOT_LOG_BASE}/data/hgg_data_pilot_^array_index^.err" \
    studies/hgg_cms/cluster/pbs_hgg_data_array.sh

# ---------------------------------------------------------------------------
# SIGNAL pilot: 1 file per record, via max_files_to_process:1 override
# configs written to LUSTRE (not $TMPDIR -- PBS worker nodes cannot see
# the submitting node's /tmp), passed as ABSOLUTE paths, each redirected
# to $PILOT_BASE/signal/<label> via OUTPUT_BASE, with unique per-label
# logs under $PILOT_LOG_BASE/signal/ passed on the qsub command line
# (pbs_hgg_signal.sh's own #PBS header cannot reference the LABEL
# variable, so this MUST be done here, not in the script).
# ---------------------------------------------------------------------------
echo "--- SIGNAL pilot: 1 file per record ---"
PILOT_CFG_DIR="${PILOT_BASE}/configs"

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
    pilot_config="${PILOT_CFG_DIR}/${base_config}.pilot.yaml"
    python - "$base_config" "$pilot_config" "$label" <<'PYEOF'
import sys
import yaml

base_path, out_path, label = sys.argv[1:4]
cfg = yaml.safe_load(open(base_path, encoding="utf-8"))
cfg["parsing_task_config"]["max_files_to_process"] = 1
cfg["run_metadata"]["run_name"] = f"cms_hgg_signal_{label}_pilot"
# base_output_dir is NOT set here -- pbs_hgg_signal.sh's OUTPUT_BASE (set
# below via qsub -v) takes priority, so setting it here would be
# dead/misleading configuration.
with open(out_path, "w", encoding="utf-8") as f:
    yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
PYEOF
    echo "  submitting $label (config=$pilot_config)"
    submit \
        -v CONFIG="$pilot_config",LABEL="${label}_pilot",OUTPUT_BASE="${PILOT_BASE}/signal/${label}" \
        -o "${PILOT_LOG_BASE}/signal/hgg_signal_${label}_pilot.out" \
        -e "${PILOT_LOG_BASE}/signal/hgg_signal_${label}_pilot.err" \
        studies/hgg_cms/cluster/pbs_hgg_signal.sh
done

echo ""
echo "Submitted: D1/D2 (1 job) + D3 (2 jobs: data, signal) + pilot (2 data array"
echo "jobs + 6 signal jobs, 1 file each)."
echo "All output under: $PILOT_BASE/"
echo "All logs under:    $PILOT_LOG_BASE/"
echo "Check status with: qstat -u \$USER"
echo "When ALL of the above finish, follow studies/hgg_cms/cluster/PILOT_CHECKLIST.md"
echo "(covers D1/D2's acceptance criteria, D3's numbers, and the pilot's own outputs)"
echo "before submitting the full run (studies/hgg_cms/cluster/submit_full.sh, NOT provided by"
echo "this task on purpose -- the full submission is a separate, explicit decision)."
