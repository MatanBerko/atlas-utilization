#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_m0m1j0_fullscale.sh
#
# FULL two-record m0m1j0 (two leading muons + leading jet) parsing run on
# the Weizmann ATLAS Grid cluster (PBS queue N). Parses all files for
# records 30522 (DoubleMuon Run2016G, 29 files, 45,235,604 events, 39.3 GiB)
# and 30555 (DoubleMuon Run2016H, 28 files, 48,912,812 events, 42.9 GiB) --
# 57 files, 94,148,416 raw events, 82.2 GiB total -- streamed via XRootD,
# never downloaded wholesale. File/event/size counts are the ones
# independently verified for these two records in this project's earlier
# H->ZZ->4l work (reports/higgs_4lepton_zz/summary.md on
# analysis/higgs-4lepton-clean), not re-derived here.
#
# Uses config.cms_m0m1j0_fullscale.yaml: same loose parse-time selection as
# the smoke test (>=2 muons pT>5/|eta|<2.4, >=1 jet, no other cut), just
# with max_files_to_process unset. This job only runs the PARSING stage --
# the invariant mass itself is computed afterward by
# scripts/m0m1j0_mumujet_report.py, not the generic mass-calculation stage.
#
# DO NOT SUBMIT THIS JOB until pbs_m0m1j0_smoketest.sh has actually run and
# been reviewed, and the pipeline operator has explicitly approved
# proceeding to full scale.
#
# Resource requests -- sized as a PROJECTION from the closest available
# precedent (the six-record H->ZZ->4l full run, analysis/higgs-4lepton-
# clean, pbs_higgs4l_partB_cluster_fullscale.sh): 238 files / 293.9 GiB
# finished in 2h33m (9180s) at a measured ~5.2 GiB peak memory, i.e. an
# aggregate throughput of ~32.8 MiB/s. This job's 82.2 GiB at that same
# throughput projects to ~43 minutes of pure I/O time -- but that reference
# job used the tight H->ZZ->4l >=4-lepton selection (low retention, small
# per-chunk accumulator contents); THIS job's selection is far looser
# (>=2mu+1jet), so many more events survive per file, meaning more
# kinematic-cut/particle-count filtering CPU time and more/larger chunk
# writes to Lustre than the I/O-only projection captures. Sized with
# generous headroom over the raw projection for exactly that reason, not
# because of any specific measurement of this selection's own overhead --
# the smoke test (pbs_m0m1j0_smoketest.sh) is what will tell us whether
# this margin was actually needed, and its real numbers should inform a
# revision here before this script is ever submitted, the same way the
# H->ZZ->4l fullscale script's own resource comment was revised after ITS
# smoke test ran.
#   mem=8gb     -- headroom above the 5.2 GiB reference peak, for the
#                  larger volume of retained events this looser selection
#                  keeps in memory between chunk flushes (the same
#                  chunk_yield_threshold_bytes=2GB config value caps this,
#                  but with more real events per chunk than the reference
#                  job saw).
#   walltime=4h -- ~5.6x the ~43-minute raw I/O-throughput projection above,
#                  to cover the extra filtering/writing overhead this
#                  selection's much higher retention implies. Still well
#                  under queue N's 12h default and 72h hard max.
#   io=40       -- headroom above the reference job's measured ~32.8 MiB/s
#                  aggregate throughput.
# ---------------------------------------------------------------------------
#PBS -N m0m1j0_fullscale
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=8gb
#PBS -l walltime=04:00:00
#PBS -l io=40
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_fullscale.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_fullscale.err

set -euo pipefail

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
CONFIG="config.cms_m0m1j0_fullscale.yaml"

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
