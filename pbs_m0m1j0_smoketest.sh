#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_m0m1j0_smoketest.sh
#
# SMOKE TEST for the m0m1j0 (two leading muons + leading jet) parse: records
# 30522 (DoubleMuon Run2016G) + 30555 (DoubleMuon Run2016H) only, capped at
# 2 files/record (4 files total) via config.cms_m0m1j0_smoketest.yaml.
#
# Purpose: confirm, before committing to the full run, that (a) the loud-
# failure guard (MAX_FILE_FAILURE_RATE=0.20, cherry-picked onto this branch
# from analysis/higgs-4lepton-clean commit f9a361d) is present and active,
# (b) the parse-time selection (>=2 muons pT>5/|eta|<2.4, >=1 jet, no other
# cut) actually retains a sane fraction of events for THIS looser selection
# -- the H->ZZ->4l >=4-lepton selection retained roughly 5-8% for muon
# streams; this selection is far looser so a substantially higher retention
# is expected, and this run measures the real number rather than assuming
# it, and (c) conda activation + Lustre output both work non-interactively
# under PBS.
#
# Resource requests are sized from the H->ZZ->4l precedent jobs on this
# cluster (analysis/higgs-4lepton-clean, pbs_higgs4l_partB_cluster_*.sh):
# that six-record/12-file smoke test measured 00:11:27 walltime, ~3.84 GiB
# peak memory, 22.1 MB/s throughput. This job is only 4 files (2 records),
# so should be faster on raw I/O -- but this selection is much looser
# (>=2mu+1jet vs >=4 leptons), meaning many more events survive per file
# and therefore more CPU time in kinematic-cut/particle-count filtering and
# more chunk-write volume. mem/io kept at or above that precedent's smoke
# test values rather than scaled down, precisely because this run is what
# will tell us whether that assumption held.
#   mem=6gb     -- matches the 4-lepton smoke test's request (3.84 GiB
#                  measured peak there, for a tighter selection over 3x the
#                  files); kept as-is rather than reduced, for margin.
#   walltime=30m -- same as the 4-lepton smoke test's request; only 4 files.
#   io=50       -- same as the 4-lepton smoke test's request.
#
# Run this BEFORE pbs_m0m1j0_fullscale.sh. Do not submit the full-scale job
# until this smoke test has been reviewed.
# ---------------------------------------------------------------------------
#PBS -N m0m1j0_smoketest
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=6gb
#PBS -l walltime=00:30:00
#PBS -l io=50
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_smoketest.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_smoketest.err

set -euo pipefail

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
CONFIG="config.cms_m0m1j0_smoketest.yaml"

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
