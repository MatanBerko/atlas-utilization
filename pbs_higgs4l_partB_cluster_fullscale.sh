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
# Resource requests (see the accompanying explanation for the full
# reasoning):
#   mem=6gb    -- laptop run peaked ~4.1 GiB; ~1.5x headroom, plus margin for
#                 the cross-record de-duplication set (accumulates across all
#                 six records in one process, untested at this file count).
#   walltime=8h -- laptop's last fully-successful 238-file run took ~6h23m;
#                 the cluster's measured single-file open+read latency is
#                 ~3.5x faster than the laptop's (5.0s vs 17.7s, same file),
#                 suggesting a real run could finish in ~2h, but that ratio
#                 measures connection/metadata latency, not confirmed bulk
#                 transfer throughput -- 8h keeps real margin above the
#                 known-good laptop baseline rather than trusting the
#                 optimistic projection.
#   io=50      -- ~294 GiB / ~108 min (the ~2h optimistic point estimate)
#                 ~= 46.5 MB/s, rounded up to 50 MB/s.
#
# Run this AFTER pbs_higgs4l_partB_cluster_smoketest.sh has been reviewed and
# has confirmed non-zero events for all six records.
# ---------------------------------------------------------------------------
#PBS -N higgs4l_partB_fullscale
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=6gb
#PBS -l walltime=08:00:00
#PBS -l io=50
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
