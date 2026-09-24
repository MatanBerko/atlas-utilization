#!/bin/bash
# ---------------------------------------------------------------------------
# submit_hgg_stats_randnuis.sh
#
# Statistical-model task: PREPARED, NOT SUBMITTED. The decisive
# pull-width diagnostic -- 500 toys at mu_true=1, job_type
# `sig_injection_randnuis`, where each toy's TRUE nuisance values are
# drawn from their own unit-Gaussian constraint instead of fixed at
# nominal (see run_toy_job.py's own docstring for the full rationale).
#
# PRE-SET EXPECTATION, stated here before this is ever run: if the
# hypothesis in STATS_REPORT.md is correct (the FIXED-nuisance toy
# design mechanically produces pull width < 1), this run's pull width
# should come out at 1.00+-0.05.
#
# This is an ADDED diagnostic -- it does NOT touch, overwrite, or
# invalidate the existing sig_injection toys or results; output goes
# under sig_injection/ with a distinct OUT_PREFIX (randnuis_) so it can
# never collide with anything already on disk (the original run, retry1,
# or the sig-pull rerun).
#
# THIS TASK DOES NOT RUN THIS SCRIPT (no SSH/qsub access). Prepared
# only, at the user's explicit request -- see the final chat message
# for the exact commands.
#
# DRY_RUN=1: runs every check that doesn't need the real cluster, prints
# the qsub command, does not submit.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-feature/hgg-selection-and-output}"
CONDA_PROFILE="${CONDA_PROFILE:-/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline}"
STATS_OUT_BASE="${STATS_OUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_stats}"
STATS_LOG_BASE="${STATS_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_stats}"
PBS_SCRIPT="studies/hgg_cms/stats/cluster/pbs_hgg_stats_array.sh"
OUT_PREFIX="randnuis_"
DRY_RUN="${DRY_RUN:-0}"

cd "$REPO_DIR"

echo "=== Preflight ==="

if [[ "$DRY_RUN" != "1" ]]; then
    source "$CONDA_PROFILE"
    conda activate "$CONDA_ENV"
    echo "  OK: activated conda env $CONDA_ENV"

    preflight_imports() {
        python -c "
import sys
mods = ['iminuit', 'scipy', 'numpy', 'studies.hgg_cms.stats.model', 'studies.hgg_cms.stats.fit']
failed = []
for name in mods:
    try:
        m = __import__(name, fromlist=['__name__'])
        ver = getattr(m, '__version__', 'n/a (no __version__ attribute)')
        print(f'  OK: {name} (version {ver})')
    except ImportError as e:
        print(f'  MISSING: {name} -- {type(e).__name__}: {e}')
        failed.append(name)
if failed:
    print('FAILED modules: ' + ', '.join(failed), file=sys.stderr)
    sys.exit(1)
" || {
            echo "PREFLIGHT FAILED: one or more required Python modules are not importable in " \
                 "conda env $CONDA_ENV -- see MISSING lines above." >&2
            exit 1
        }
    }
    preflight_imports

    # this job_type only exists as of the commit that added it -- fail
    # fast with a clear message rather than 20 subjobs erroring on an
    # unrecognized --job-type choice.
    python -c "
from studies.hgg_cms.stats.cluster.run_toy_job import JOB_TYPES
assert 'sig_injection_randnuis' in JOB_TYPES, 'sig_injection_randnuis job type not found -- wrong commit?'
print('  OK: sig_injection_randnuis job type is registered')
"
else
    echo "  [DRY_RUN] skipping conda activation + import check (needs the real cluster env)"
fi

branch=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)
if [[ "$branch" != "$EXPECTED_BRANCH" ]]; then
    echo "PREFLIGHT FAILED: on branch '$branch', expected '$EXPECTED_BRANCH'" >&2; exit 1
fi
if [[ -n "$(git -C "$REPO_DIR" status --porcelain)" ]]; then
    echo "PREFLIGHT FAILED: dirty working tree" >&2; git status --short >&2; exit 1
fi
commit=$(git -C "$REPO_DIR" rev-parse HEAD)
echo "  OK: branch=$branch, clean tree, commit=$commit"

if [[ ! -f "studies/hgg_cms/signal_model/results/signal_model.json" ]] || \
   [[ ! -f "studies/hgg_cms/background_model/results/background_model_final.json" ]]; then
    echo "PREFLIGHT FAILED: signal_model.json / background_model_final.json not found." >&2
    exit 1
fi
echo "  OK: signal_model.json and background_model_final.json found"

if ! grep -qE '^#PBS[[:space:]]+-l[[:space:]]+io[[:space:]]*=' "$PBS_SCRIPT"; then
    echo "PREFLIGHT FAILED: $PBS_SCRIPT has no '#PBS -l io=<value>' line." >&2
    exit 1
fi
echo "  OK: $PBS_SCRIPT requests -l io="

JOBLIST_FILE="${STATS_LOG_BASE}/submitted_jobs.txt"
if [[ ! -f "$JOBLIST_FILE" ]]; then
    echo "PREFLIGHT FAILED: $JOBLIST_FILE not found -- has submit_hgg_stats.sh been run first?" >&2
    exit 1
fi
echo "  OK: original run's $JOBLIST_FILE found"

JOB_LIST="${STATS_LOG_BASE}/job_list_randnuis.txt"
if [[ -f "$JOB_LIST" ]]; then
    echo "PREFLIGHT FAILED: $JOB_LIST already exists -- refusing to overwrite a previous attempt's " \
         "job list. Remove/move it yourself first if you really want to redo this." >&2
    exit 1
fi
python studies/hgg_cms/stats/cluster/make_job_list_randnuis.py --out "$JOB_LIST"

N_JOBS=$(wc -l < "$JOB_LIST")
if [[ "$N_JOBS" -ne 20 ]]; then
    echo "PREFLIGHT FAILED: expected 20 job-list lines, got $N_JOBS -- check " \
         "make_job_list_randnuis.py." >&2
    exit 1
fi
echo "  OK: job list has exactly 20 lines (500 toys)"

EXISTING=$(find "$STATS_OUT_BASE" -name "${OUT_PREFIX}job_*.json" 2>/dev/null | head -1 || true)
if [[ -n "$EXISTING" ]]; then
    echo "PREFLIGHT FAILED: found existing ${OUT_PREFIX}job_*.json output (e.g. $EXISTING) -- " \
         "refusing to resubmit over a previous attempt. Move it aside yourself first." >&2
    exit 1
fi
echo "  OK: no existing ${OUT_PREFIX}job_*.json output found"

echo "=== Preflight passed -- submitting $N_JOBS subjobs (randomized-nuisance pull-width diagnostic) ==="

QSUB_CMD=(qsub -J "1-${N_JOBS}" \
    -v JOB_LIST="$JOB_LIST",OUT_BASE="$STATS_OUT_BASE",OUT_PREFIX="$OUT_PREFIX" \
    -o "${STATS_LOG_BASE}/hgg_stats_randnuis_^array_index^.out" \
    -e "${STATS_LOG_BASE}/hgg_stats_randnuis_^array_index^.err" \
    "$PBS_SCRIPT")

echo "+ ${QSUB_CMD[*]}"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN-NO-JOBID"
else
    jobid=$("${QSUB_CMD[@]}")
    echo "  $jobid"
    echo "hgg_stats_randnuis $jobid $JOB_LIST $OUT_PREFIX" >> "$JOBLIST_FILE"
    echo ""
    echo "Submitted: $N_JOBS subjobs under job $jobid."
    echo "Outputs under: $STATS_OUT_BASE/sig_injection/${OUT_PREFIX}job_NNNN.json"
    echo "Logs under:    $STATS_LOG_BASE/hgg_stats_randnuis_*.out/.err"
    echo "Check status with: bash studies/hgg_cms/stats/cluster/status_hgg_stats.sh"
    echo ""
    echo "IMPORTANT: do NOT merge this with the normal merge_hgg_stats.py run -- these toys have a"
    echo "DIFFERENT truth (randomized nuisances) than the rest of sig_injection (fixed at nominal),"
    echo "so pooling them would silently mix two different toy designs into one pull_width number."
    echo "Analyze this batch separately, e.g.:"
    echo "  python -c \""
    echo "import json, glob, numpy as np"
    echo "from studies.hgg_cms.stats.fit import strict_valid"
    echo "results = []"
    echo "for f in glob.glob('$STATS_OUT_BASE/sig_injection/${OUT_PREFIX}job_*.json'):"
    echo "    results += json.load(open(f))['results']"
    echo "ok = [r for r in results if not r['failed']]"
    echo "good = [r for r in ok if strict_valid(r.get('alt_fmin_post_hesse'), r.get('mu_err'))]"
    echo "pull = np.array([(r['mu_hat']-1.0)/r['mu_err'] for r in good])"
    echo "print('n_toys=', len(results), 'n_used=', len(ok), 'n_strict_valid=', len(good))"
    echo "print('pull_mean=', pull.mean(), 'pull_width=', pull.std())"
    echo "\""
fi
