#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_bias_rerun1_array.sh
#
# Background-model task, bias-study rerun 1: ONE PBS array job, one
# subjob per (category, truth family, leakage variant, mass) cell listed
# in JOB_LIST (7 fields per line -- see make_job_list_rerun1.py), each
# evaluating exactly ONE new candidate test function (EBEB bernstein_6,
# notEBEB bernstein_7 -- the field is per-line, not a single global
# value, since it differs by category) against that cell, reusing the
# SAME per-cell seed as the first run (see
# tests/test_bias_rerun_seed_identity.py for the proof this reproduces
# the same pseudo-datasets). 120 array indices = the full 60-cell grid
# x 2 categories.
#
# RESOURCE REQUESTS:
# - `-l io=5`: MANDATORY on this cluster for every job regardless of
#   walltime/mem (see studies/hgg_cms/cluster/FULL_RUN_README.md's
#   "Every PBS job must request -l io=<value>" section -- the first
#   bias-study submission was rejected outright without one).
# - walltime=00:15:00: the first run's own EBEB/125-GeV subjobs (8 test
#   functions x 1000 toys) took ~6 minutes; this rerun's subjobs
#   evaluate exactly ONE test function (not 8), so ~6min/8 ~= 45s is the
#   expected worst case (125 GeV, 1000 toys) -- 15 minutes is a >15x
#   safety margin, and stays far under the 02:00:00 boundary this
#   cluster routes to the `shortE` queue for.
# - mem=4gb: matches the main bias-study array's own (already-adequate)
#   request; nothing about evaluating one function instead of eight
#   increases memory needs.
# - OMP/OPENBLAS/MKL_NUM_THREADS=1: pinned so this ncpus=1 job can't use
#   more CPU than requested (added 18 Sep 2026 to the main bias-study
#   script after the fact; included here from the start).
# ---------------------------------------------------------------------------
#PBS -N hgg_bias_rerun1
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=4gb
#PBS -l walltime=00:15:00
#PBS -l io=5
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_bias_rerun1/hgg_bias_rerun1_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_bias_rerun1/hgg_bias_rerun1_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
: "${JOB_LIST:?must pass -v JOB_LIST=/path/to/job_list_rerun1.txt (from make_job_list_rerun1.py)}"
: "${OUT_BASE:?must pass -v OUT_BASE=/storage/agrp/berkom/atlas-utilization/output/hgg_bias/105_180_rerun1}"
LEAKAGE_JSON="${LEAKAGE_JSON:-/storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/hgg_leakage_mass_template_results.json}"
FIT_RANGE="105_180"
ORDER_SELECTION_JSON="${ORDER_SELECTION_JSON:-${REPO_DIR}/studies/hgg_cms/background_model/results/order_selection_${FIT_RANGE}.json}"

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

LINE=$(sed -n "${JOB_INDEX}p" "$JOB_LIST")
if [[ -z "$LINE" ]]; then
    echo "No line $JOB_INDEX in $JOB_LIST" >&2
    exit 1
fi
read -r CATEGORY TRUTH_FAMILY LEAKAGE_VARIANT MASS N_TOYS SEED TEST_FUNCTION <<< "$LINE"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

OUT_FILE="${OUT_BASE}/${CATEGORY}_${TRUTH_FAMILY}_${LEAKAGE_VARIANT}_m${MASS}.json"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "CATEGORY=$CATEGORY TRUTH_FAMILY=$TRUTH_FAMILY LEAKAGE_VARIANT=$LEAKAGE_VARIANT MASS=$MASS N_TOYS=$N_TOYS SEED=$SEED TEST_FUNCTION=$TEST_FUNCTION"

python -u studies/hgg_cms/background_model/cluster/run_bias_job.py \
    --category "$CATEGORY" --fit-range "$FIT_RANGE" \
    --truth-family "$TRUTH_FAMILY" --leakage-variant "$LEAKAGE_VARIANT" \
    --mass "$MASS" --n-toys "$N_TOYS" --seed "$SEED" \
    --order-selection-json "$ORDER_SELECTION_JSON" \
    --leakage-json "$LEAKAGE_JSON" \
    --test-functions "$TEST_FUNCTION" \
    --out "$OUT_FILE"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
