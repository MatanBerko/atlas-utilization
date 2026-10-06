#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_measure.sh (electron_prep) -- one array element per input file.
#
# PBS_ARRAY_INDEX selects a line from JOBLIST, a file of
# "LABEL ERA FILE_INDEX" rows written by submit_measurements.sh into the
# OUTPUT directory (never into the pinned repo, which must stay untouched
# while jobs run).
#
# PREPARATION ONLY: measure_per_file.py reads input files and writes one
# small JSON per file under OUTPUT_DIR. It writes nowhere else.
# ---------------------------------------------------------------------------
#PBS -N eprep_meas
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=8gb
#PBS -l walltime=02:00:00
#PBS -l io=25

set -euo pipefail

REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"

: "${JOBLIST:?JOBLIST not set}"
: "${OUTPUT_DIR:?OUTPUT_DIR not set}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

IDX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"
LINE=$(sed -n "$((IDX + 1))p" "$JOBLIST")
if [ -z "$LINE" ]; then
    echo "no joblist line for array index $IDX in $JOBLIST" >&2
    exit 1
fi
read -r LABEL ERA FINDEX <<< "$LINE"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"
export PYTHONPATH="$REPO_DIR"

echo "Job $PBS_JOBID (array index $IDX) on $(hostname) at $(date)"
echo "repo=$REPO_DIR commit=$(git rev-parse HEAD)"
echo "dataset=$LABEL era=$ERA file-index=$FINDEX out=$OUTPUT_DIR"

python -u studies/cms_datasets/electron_prep/measure_per_file.py \
    --dataset "$LABEL" --era "$ERA" --file-index "$FINDEX" \
    --output-dir "$OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $IDX) finished at $(date)"
