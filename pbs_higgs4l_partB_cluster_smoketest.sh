#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_higgs4l_partB_cluster_smoketest.sh
#
# SMOKE TEST for the cluster migration: same six records as the full run
# (30521/30554/30522/30555/30528/30561), capped at 2 files/record (12 files
# total, ~16 GiB) via config.cms_higgs_4lepton_cluster_smoketest.yaml.
#
# Purpose: confirm, on the cluster and BEFORE committing to the ~8h full
# run, that (a) this batch script's PBS resource requests are workable,
# (b) conda activation works non-interactively under PBS, (c) output lands
# on Lustre at the right path, and (d) -- the point that matters most, after
# the laptop's six-record run silently produced zero events for four of six
# records -- that ALL SIX records yield non-zero retained events here. Check
# the per-record "Retention record_XXXXX: N / M events kept" lines in
# logs/pipeline.log under this run's output directory.
#
# Same resource shape as the full run (mem/io) so this is a faithful dress
# rehearsal of the real request, just with a much shorter walltime given the
# ~20x smaller file count.
# ---------------------------------------------------------------------------
#PBS -N higgs4l_partB_smoketest
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=6gb
#PBS -l walltime=00:30:00
#PBS -l io=50
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/higgs4l_partB_smoketest.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/higgs4l_partB_smoketest.err

set -euo pipefail

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
CONFIG="config.cms_higgs_4lepton_cluster_smoketest.yaml"

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
