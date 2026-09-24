#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_bias_array.sh
#
# Background-model task, Part 3: ONE PBS array job, one subjob per
# (category, truth family, leakage variant, mass) combination listed in
# JOB_LIST (one line per array index -- see make_job_list.py). Each
# subjob loops over all 8 candidate test functions internally
# (run_bias_job.py's own default), so 120 array indices covers the
# entire main bias study.
#
# TIMED on this laptop before writing this script (NOT run here --
# "prepare, don't submit"): 100 toys x 8 test functions = 800 toy-pairs
# in 39.9s => ~0.050s/toy-pair. At 1000 toys (the 125 GeV subjobs) that
# is ~400s (~6.7 min); at 300 toys (the other 4 masses) ~120s (~2 min).
# walltime=00:30:00 below is a >4x safety margin over the slowest
# (125 GeV) subjob's measured local time, and stays well under the
# 02:00:00 boundary this cluster routes to the `shortE` queue for (see
# studies/hgg_cms/cluster/FULL_RUN_README.md).
#
# Extrapolating this same per-toy-pair rate to the FULL local grid (120
# subjobs x up to 1000 toys x 8 test functions) gives ~5-7 hours total
# wall time on this one laptop -- over the ~3 hour budget this task set,
# which is exactly why this runs as 120 independent ~2-7 minute cluster
# jobs instead of one long local loop.
#
# UPDATE (18 Sep 2026): the FIRST real submission of this script was
# rejected outright by the scheduler ("Job violates queue and/or server
# resource limits") before ever running -- diagnosed with small test
# jobs to be this cluster's undocumented (from this project's side)
# requirement that EVERY job request an -l io=<MB/s> value; jobs without
# one are rejected regardless of walltime/mem, jobs with one (even a
# small "-l io=5") are accepted. Every OTHER PBS script in this repo
# already had an -l io request (see studies/hgg_cms/cluster/*.sh) --
# this one was simply missed when it was written. See
# studies/hgg_cms/cluster/FULL_RUN_README.md for the general rule, now
# recorded there, and tests/test_pbs_scripts.py for a unit test that
# checks every PBS script under studies/hgg_cms has one.
# ---------------------------------------------------------------------------
#PBS -N hgg_bias
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=4gb
#PBS -l walltime=00:30:00
#PBS -l io=5
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_bias/hgg_bias_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_bias/hgg_bias_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
: "${JOB_LIST:?must pass -v JOB_LIST=/path/to/job_list.txt (from make_job_list.py)}"
: "${OUT_BASE:?must pass -v OUT_BASE=/storage/agrp/berkom/atlas-utilization/output/hgg_bias}"
LEAKAGE_JSON="${LEAKAGE_JSON:-/storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/hgg_leakage_mass_template_results.json}"
FIT_RANGE="${FIT_RANGE:-105_180}"
ORDER_SELECTION_JSON="${ORDER_SELECTION_JSON:-${REPO_DIR}/studies/hgg_cms/background_model/results/order_selection_${FIT_RANGE}.json}"
# Part 4's reduced study (110-180, chosen function + 2 runners-up only)
# passes this to restrict run_bias_job.py to those specific test
# functions instead of its "all families' selected+one-above" default.
# Empty (unset) for the main Part 3 study.
TEST_FUNCTIONS_ARG=()
if [[ -n "${TEST_FUNCTIONS:-}" ]]; then
    TEST_FUNCTIONS_ARG=(--test-functions "$TEST_FUNCTIONS")
fi

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

LINE=$(sed -n "${JOB_INDEX}p" "$JOB_LIST")
if [[ -z "$LINE" ]]; then
    echo "No line $JOB_INDEX in $JOB_LIST" >&2
    exit 1
fi
read -r CATEGORY TRUTH_FAMILY LEAKAGE_VARIANT MASS N_TOYS SEED <<< "$LINE"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

# Added 18 Sep 2026, for Part 4 and later runs of this script (the
# already-running/queued Part 3 array is unaffected -- PBS reads a
# script's contents at submission time, not on re-read, so editing this
# file does not retroactively change jobs already submitted). This PBS
# job requests select=1:ncpus=1 above, but numpy/scipy link against
# BLAS/OpenMP libraries that will happily spawn extra threads and use
# more CPU than requested unless told not to -- pin every relevant
# thread-pool env var to 1 so a "1 CPU" job actually stays at 1 CPU.
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

OUT_FILE="${OUT_BASE}/${FIT_RANGE}/${CATEGORY}_${TRUTH_FAMILY}_${LEAKAGE_VARIANT}_m${MASS}.json"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "CATEGORY=$CATEGORY TRUTH_FAMILY=$TRUTH_FAMILY LEAKAGE_VARIANT=$LEAKAGE_VARIANT MASS=$MASS N_TOYS=$N_TOYS SEED=$SEED"

python -u studies/hgg_cms/background_model/cluster/run_bias_job.py \
    --category "$CATEGORY" --fit-range "$FIT_RANGE" \
    --truth-family "$TRUTH_FAMILY" --leakage-variant "$LEAKAGE_VARIANT" \
    --mass "$MASS" --n-toys "$N_TOYS" --seed "$SEED" \
    --order-selection-json "$ORDER_SELECTION_JSON" \
    --leakage-json "$LEAKAGE_JSON" \
    "${TEST_FUNCTIONS_ARG[@]}" \
    --out "$OUT_FILE"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
