#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_higgs4l_partB_cluster_fullscale.sh
#
# FULL six-record H -> ZZ -> 4l Part B parsing run on the Weizmann ATLAS Grid
# cluster (PBS queue N). Parses all 238 files (~294 GiB raw, streamed via
# XRootD -- never downloaded wholesale) across records
# 30521/30554/30522/30555/30528/30561, using
# config.cms_higgs_4lepton_cluster.yaml (identical selection to the laptop's
# config.cms_higgs_4lepton_fullscale.yaml: Part A working points + Part B's
# sip3d<4/|dxy|<0.5/|dz|<1.0 impact-parameter cuts, applied later by the
# analysis script -- this job only does the PARSING stage).
#
# Resource requests -- revised after the smoke test actually ran (12 files,
# all six records, job 4999602.pbs on 2026-09-09): exit 0, walltime 00:11:27,
# mem 4030484kb (~3.84 GiB) peak, throughput 22.1 MB/s measured (15,175 MiB /
# 687s). These replace the pre-run estimates that were used to size the
# original request (laptop-baseline projection + single-file latency ratio).
#   mem=5gb    -- smoke test peaked 3.84 GiB; modest headroom above that,
#                 not the earlier untested-margin guess.
#   walltime=8h -- unchanged. 294 GiB / 22.1 MB/s (measured) ~= 3.8h
#                 projected; 8h leaves real margin (~2.1x the projection)
#                 without being excessive.
#   io=25      -- measured throughput was 22.1 MB/s, not the 46.5 MB/s the
#                 original request assumed (that was based on an optimistic
#                 latency-ratio projection, not a real measurement).
#                 Declaring io= at the actually-sustained rate avoids
#                 reserving shared I/O capacity this job won't use.
#
# Run this AFTER pbs_higgs4l_partB_cluster_smoketest.sh has been reviewed and
# has confirmed non-zero events for all six records.
# ---------------------------------------------------------------------------
#PBS -N higgs4l_partB_fullscale
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=5gb
#PBS -l walltime=08:00:00
#PBS -l io=25
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/higgs4l_partB_fullscale.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/higgs4l_partB_fullscale.err

set -euo pipefail

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
CONFIG="config.cms_higgs_4lepton_cluster.yaml"

# PBS provides a per-job scratch $TMPDIR that is cleaned up automatically on
# job exit; only fall back to creating one if it's somehow unset.
mkdir -p "${TMPDIR:-/tmp}"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

echo "Job $PBS_JOBID starting on $(hostname) at $(date)"
echo "TMPDIR=$TMPDIR"

python -u main.py \
    --config "$CONFIG" \
    --tasks parsing \
    --log-level INFO

echo "Job $PBS_JOBID finished at $(date)"
