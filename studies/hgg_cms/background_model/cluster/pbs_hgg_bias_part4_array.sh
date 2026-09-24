#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_bias_part4_array.sh
#
# Background-model task, Part 4 (110-180 GeV robustness check): ONE PBS
# array job, one subjob per (category, truth family) cell listed in
# JOB_LIST (7 fields per line -- see make_job_list_part4.py: category
# truth_family leakage_variant mass n_toys seed test_functions_csv).
# Each subjob evaluates its category's own set of test functions (the
# chosen bernstein_6 plus its runner-up(s) -- 3 for EBEB, only 2 for
# notEBEB, since notEBEB has only 2 eligible candidates total; see
# make_job_list_part4.py's own module docstring) against ONE truth
# model, nominal leakage only, m_H=125 only, >=500 toys.
#
# WALLTIME: rerun 1's own worst cells (notEBEB, bernstein_7, 1000 toys,
# ONE test function) needed more than the original 15-minute request and
# were resubmitted with walltime=01:00:00 (all succeeded). A Part-4
# subjob evaluates UP TO 3 test functions (not 1) at 500 toys each (not
# 1000) -- roughly 1.5x the toy-fit workload of one such problem cell.
# Requesting the full walltime=02:00:00 (the maximum that still routes
# to the `shortE` queue -- see studies/hgg_cms/cluster/FULL_RUN_README.md)
# gives a >3x margin over that 1.5x-scaled estimate, comfortably covering
# even a run of consistently slow-converging cells.
# ---------------------------------------------------------------------------
#PBS -N hgg_bias_part4
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=4gb
#PBS -l walltime=02:00:00
#PBS -l io=5
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_bias_part4/hgg_bias_part4_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_bias_part4/hgg_bias_part4_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
: "${JOB_LIST:?must pass -v JOB_LIST=/path/to/job_list_110_180_part4.txt (from make_job_list_part4.py)}"
: "${OUT_BASE:?must pass -v OUT_BASE=/storage/agrp/berkom/atlas-utilization/output/hgg_bias/110_180_part4}"
LEAKAGE_JSON="${LEAKAGE_JSON:-/storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/hgg_leakage_mass_template_results.json}"
FIT_RANGE="110_180"
ORDER_SELECTION_JSON="${ORDER_SELECTION_JSON:-${REPO_DIR}/studies/hgg_cms/background_model/results/order_selection_${FIT_RANGE}.json}"

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

LINE=$(sed -n "${JOB_INDEX}p" "$JOB_LIST")
if [[ -z "$LINE" ]]; then
    echo "No line $JOB_INDEX in $JOB_LIST" >&2
    exit 1
fi
read -r CATEGORY TRUTH_FAMILY LEAKAGE_VARIANT MASS N_TOYS SEED TEST_FUNCTIONS <<< "$LINE"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

OUT_FILE="${OUT_BASE}/${CATEGORY}_${TRUTH_FAMILY}_${LEAKAGE_VARIANT}_m${MASS}.json"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "CATEGORY=$CATEGORY TRUTH_FAMILY=$TRUTH_FAMILY LEAKAGE_VARIANT=$LEAKAGE_VARIANT MASS=$MASS N_TOYS=$N_TOYS SEED=$SEED TEST_FUNCTIONS=$TEST_FUNCTIONS"

python -u studies/hgg_cms/background_model/cluster/run_bias_job.py \
    --category "$CATEGORY" --fit-range "$FIT_RANGE" \
    --truth-family "$TRUTH_FAMILY" --leakage-variant "$LEAKAGE_VARIANT" \
    --mass "$MASS" --n-toys "$N_TOYS" --seed "$SEED" \
    --order-selection-json "$ORDER_SELECTION_JSON" \
    --leakage-json "$LEAKAGE_JSON" \
    --test-functions "$TEST_FUNCTIONS" \
    --out "$OUT_FILE"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
