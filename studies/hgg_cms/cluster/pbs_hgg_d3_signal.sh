#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_d3_signal.sh
#
# Implementation task 6, Part D3 (signal half): processes ONE FULL ggH
# file (GluGluHToGG, record 37350) -- the exact same file pinned in
# studies/hgg_cms/impl_checks/reproduce_check_b_and_c.py's SIGNAL_URL
# (postVFP GluGluHToGG, 533,000 events -- confirmed in implementation
# task 5) -- through config.cms_hgg_signal_ggh.yaml, then this task's
# selection + output + D3 analysis (cutflow, efficiency, mode/median/
# sigma_eff per category, fine-bin plot, preview single-file ggH yield,
# timing, output sizes).
#
# Same file-pinning mechanism as pbs_hgg_d3_data.sh: pre-write the
# pipeline's metadata cache with exactly this one URL so main.py's
# FetchMetadataHandler uses it as-is (cache hit), never calling the
# record-fetch API -- guarantees EXACTLY this file is processed, zero
# shared-code changes needed.
#
# Wrapped end-to-end in `/usr/bin/time -v` for wall-clock + peak memory --
# these numbers (this is also, by file size/event count, the WORST CASE
# among the 6 signal records -- see pbs_hgg_signal.sh's own comment on
# ggH having by far the most events/file) are what pbs_hgg_signal.sh's
# placeholder #PBS -l mem/walltime values must be set from (x2 safety
# factor) before the full signal submission.
# ---------------------------------------------------------------------------
#PBS -N hgg_d3_signal
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=8gb
#PBS -l walltime=04:00:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_d3/hgg_d3_signal.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_d3/hgg_d3_signal.err

set -euo pipefail

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
BASE_CONFIG="config.cms_hgg_signal_ggh.yaml"
JOB_RUN_DIR="/storage/agrp/berkom/atlas-utilization/output/hgg_d3_signal_ggh"

PINNED_RECORD="37350"
PINNED_URL="root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root"

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
        --is-data false \
        --config "'"$BASE_CONFIG"'"

    python -u studies/hgg_cms/cluster/d3_analysis.py \
        --mode signal \
        --run-dir "'"$JOB_RUN_DIR"'"
' 2> "$TIMING_LOG"

echo "Timing/peak-memory: $TIMING_LOG"
echo "D3 report: ${JOB_RUN_DIR}/d3_signal_report.json"
echo "D3 plot:   ${JOB_RUN_DIR}/d3_signal_mgg_plot.png"
echo "Job $PBS_JOBID finished at $(date)"
