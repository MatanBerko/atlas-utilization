#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_lumi_coverage.sh -- one PBS array subjob per (dataset, era) record of
# the four delivered datasets: 8 subjobs covering all 390 files.
#
# Follows studies/cms_coverage/cluster/pbs_coverage_full.sh's own pattern
# (same queue, same conda activation, same mapping-file convention,
# single-threaded BLAS). Each subjob only opens the small LuminosityBlocks
# tree of its record's files, so the work is network-bound, not CPU- or
# memory-bound: 4 GB and 4 hours are generous for the largest record
# (DoubleEG Run2016H, 86 files).
#
# -o/-e are supplied by submit_lumi_coverage.sh on the qsub command line,
# which creates the log directory first -- PBS silently discards job logs if
# the directory does not exist.
# ---------------------------------------------------------------------------
#PBS -N lumi_cov_four
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=4gb
#PBS -l walltime=04:00:00
#PBS -l io=30

set -euo pipefail

REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
OUTPUT_DIR="${OUTPUT_DIR:?OUTPUT_DIR not set}"
MAPPING_FILE="${MAPPING_FILE:?MAPPING_FILE not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

if [[ ! -f "$MAPPING_FILE" ]]; then
    echo "MAPPING_FILE not found: $MAPPING_FILE" >&2
    exit 1
fi

RECORD_KEY=$(sed -n "${JOB_INDEX}p" "$MAPPING_FILE")
if [[ -z "$RECORD_KEY" ]]; then
    echo "No mapping-file line for index $JOB_INDEX in $MAPPING_FILE" >&2
    exit 1
fi

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "record_key=$RECORD_KEY output_dir=$OUTPUT_DIR"
echo "repo commit: $(git -C "$REPO_DIR" rev-parse HEAD)"

python -u studies/lumi_coverage_four_datasets/read_lumisections_for_record.py \
    --record-key "$RECORD_KEY" \
    --output-dir "$OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
