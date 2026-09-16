#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_merge_full.sh
#
# Implementation task 6, Part 1: OPTIONAL small PBS job for merge_outputs.py,
# in case running it directly on the analysis node (with `nice`) turns out
# to take longer than "a few minutes" -- e.g. if the merged ROOT read/write
# step (--merged-dir, on by default) is slower than expected for the real
# full-run output sizes. Not needed if the direct `nice python ...` command
# in FULL_RUN_README.md / the task's own handover message finishes quickly;
# this is the fallback, not the default path.
#
# Requests: queue N, walltime 00:30:00, mem 4gb -- generous for a job that
# only reads ~139 small JSON files plus the (small, selected-events-only)
# per-job ROOT outputs and writes a handful of merged files; #PBS -m n (no
# email) per this project's cluster rules. Logs go to Lustre, never $HOME.
#
# Usage (from $HOME/atlas-utilization, matching every other job script
# here):
#   qsub -o /storage/agrp/berkom/atlas-utilization/logs/hgg_full/merge/merge.out \
#        -e /storage/agrp/berkom/atlas-utilization/logs/hgg_full/merge/merge.err \
#        studies/hgg_cms/cluster/pbs_hgg_merge_full.sh
# ---------------------------------------------------------------------------
#PBS -N hgg_merge
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=4gb
#PBS -l walltime=00:30:00
#PBS -l io=10
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_full/merge/hgg_merge.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_full/merge/hgg_merge.err

set -euo pipefail

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
FULL_BASE="/storage/agrp/berkom/atlas-utilization/output/hgg_full"
MERGED_DIR="${FULL_BASE}/merged"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

echo "Job $PBS_JOBID (hgg_merge) starting on $(hostname) at $(date)"

mkdir -p "$MERGED_DIR"

# merge_outputs.py exits 1 for a legitimate "status: INCOMPLETE" (still
# writes its summary JSON -- that is a real, useful result, not a crash),
# so exit-code capture must not let `set -e` kill this script on that.
DATA_RC=0
python -u studies/hgg_cms/cluster/merge_outputs.py --mode data \
    --jobs-base "${FULL_BASE}/data" \
    --merged-dir "$MERGED_DIR" \
    --out "${MERGED_DIR}/merge_summary_data.json" || DATA_RC=$?

SIGNAL_RC=0
python -u studies/hgg_cms/cluster/merge_outputs.py --mode signal \
    --record ggh="${FULL_BASE}/signal/ggh" \
    --record vbf="${FULL_BASE}/signal/vbf" \
    --record wplush="${FULL_BASE}/signal/wplush" \
    --record wminush="${FULL_BASE}/signal/wminush" \
    --record zh="${FULL_BASE}/signal/zh" \
    --record tth="${FULL_BASE}/signal/tth" \
    --merged-dir "$MERGED_DIR" \
    --out "${MERGED_DIR}/merge_summary_signal.json" || SIGNAL_RC=$?

echo "Job $PBS_JOBID (hgg_merge) finished at $(date): data_rc=$DATA_RC signal_rc=$SIGNAL_RC"
exit $(( DATA_RC != 0 || SIGNAL_RC != 0 ))
