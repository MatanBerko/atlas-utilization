#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_stats_array.sh
#
# Statistical-model task, Parts 2 and 3.3/3.5: ONE PBS array job, one
# subjob per line of JOB_LIST (`job_type mu_true n_toys seed` -- see
# make_job_list.py). All toys are synthetic (Poisson-drawn from the
# model's own prediction) -- no data file, blinded or otherwise, is ever
# opened by this job.
#
# WALLTIME: sized from a laptop timing measurement (see
# make_job_list.py's own docstring and STATS_REPORT.md) with a
# comfortable margin below the true per-job cost; walltime=02:00:00 is
# the maximum that still routes to the shortE queue (see
# studies/hgg_cms/cluster/FULL_RUN_README.md).
# ---------------------------------------------------------------------------
#PBS -N hgg_stats
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=4gb
#PBS -l walltime=02:00:00
#PBS -l io=5
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_stats/hgg_stats_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_stats/hgg_stats_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
: "${JOB_LIST:?must pass -v JOB_LIST=/path/to/job_list.txt (from make_job_list.py)}"
: "${OUT_BASE:?must pass -v OUT_BASE=/storage/agrp/berkom/atlas-utilization/output/hgg_stats}"

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

LINE=$(sed -n "${JOB_INDEX}p" "$JOB_LIST")
if [[ -z "$LINE" ]]; then
    echo "No line $JOB_INDEX in $JOB_LIST" >&2
    exit 1
fi
read -r JOB_TYPE MU_TRUE N_TOYS SEED <<< "$LINE"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

OUT_DIR="${OUT_BASE}/${JOB_TYPE}"
OUT_FILE="${OUT_DIR}/job_$(printf '%04d' "$JOB_INDEX").json"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "JOB_TYPE=$JOB_TYPE MU_TRUE=$MU_TRUE N_TOYS=$N_TOYS SEED=$SEED"

python -u studies/hgg_cms/stats/cluster/run_toy_job.py \
    --job-type "$JOB_TYPE" --mu-true "$MU_TRUE" --n-toys "$N_TOYS" --seed "$SEED" \
    --out "$OUT_FILE"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
