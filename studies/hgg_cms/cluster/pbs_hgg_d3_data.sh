#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_d3_data.sh
#
# Implementation task 6, Part D3 (data half): processes ONE FULL DoubleEG
# Run2016G file -- the exact same file pinned in
# studies/hgg_cms/impl_checks/reproduce_check_b_and_c.py's DATA_FILES[0]
# (originally from check_c_trigger_mimicking.py) -- through the REAL
# production config (config.cms_hgg_data.yaml), then this task's
# selection + output + D3 analysis (cutflow, sideband-only plot, blinded
# count, timing, output sizes).
#
# The exact file is pinned by PRE-WRITING the pipeline's own metadata
# cache (services/metadata/cache.py) with exactly this one URL before
# running main.py -- FetchMetadataHandler.handle() uses a cache HIT
# as-is, without ever calling the record-fetch API, so this is a
# non-invasive, zero-shared-code-change way to guarantee we process
# EXACTLY this file (not "whichever file the API lists first").
#
# Wrapped end-to-end in `/usr/bin/time -v` for wall-clock + peak memory
# (Part D3's timing/memory requirement) -- these numbers are what
# pbs_hgg_data_array.sh's placeholder #PBS -l mem/walltime values must be
# set from (with the requested x2 safety factor) before the full 133-file
# submission.
# ---------------------------------------------------------------------------
#PBS -N hgg_d3_data
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=4gb
#PBS -l walltime=03:00:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_d3/hgg_d3_data.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_d3/hgg_d3_data.err

set -euo pipefail

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
BASE_CONFIG="config.cms_hgg_data.yaml"
JOB_RUN_DIR="/storage/agrp/berkom/atlas-utilization/output/hgg_d3_data"

# The exact file pinned by check_c_trigger_mimicking.py / this task's own
# reproduce_check_b_and_c.py, via XRootD (see that script's own comments
# for why XRootD is preferred over HTTPS here).
PINNED_RECORD="30521"
PINNED_URL="root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root"

mkdir -p "${TMPDIR:-/tmp}" "$JOB_RUN_DIR"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

echo "Job $PBS_JOBID starting on $(hostname) at $(date)"
echo "Run dir: $JOB_RUN_DIR"
echo "Pinned file: $PINNED_URL"

python -c "
import json
json.dump({'record_${PINNED_RECORD}': ['${PINNED_URL}']}, open('${JOB_RUN_DIR}/metadata_cache.json', 'w'), indent=2)
"

TIMING_LOG="${JOB_RUN_DIR}/timing_and_memory.log"

/usr/bin/time -v bash -c '
    set -euo pipefail
    python -u main.py \
        --config "'"$BASE_CONFIG"'" \
        --run-dir "'"$JOB_RUN_DIR"'" \
        --tasks parsing \
        --log-level INFO

    python -u studies/hgg_cms/cluster/run_selection_on_chunks.py \
        --chunks-dir "'"$JOB_RUN_DIR"'/parsed_data" \
        --output-dir "'"$JOB_RUN_DIR"'/selected" \
        --is-data true \
        --config "'"$BASE_CONFIG"'"

    python -u studies/hgg_cms/cluster/d3_analysis.py \
        --mode data \
        --run-dir "'"$JOB_RUN_DIR"'"
' 2> "$TIMING_LOG"

echo "Timing/peak-memory: $TIMING_LOG"
echo "D3 report: ${JOB_RUN_DIR}/d3_data_report.json"
echo "D3 plot:   ${JOB_RUN_DIR}/d3_data_mgg_plot.png"
echo "Job $PBS_JOBID finished at $(date)"
