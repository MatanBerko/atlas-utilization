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
# Resource requests -- REVISED after the smoke test actually ran (4 files,
# both records, job 5036819.pbs on 2026-09-14, AFTER fixing the
# RECORD_ID_TO_SCHEMA registration bug found by that same smoke test):
# exit 0, walltime 00:03:38 (218s), mem 6,682,004kb (~6.4 GiB) peak,
# 9,096,942 raw events processed -> ~41,730 events/sec. These replace the
# original pre-smoke-test estimates (an I/O-throughput projection from the
# unrelated, tight-selection H->ZZ->4l reference job), which this real
# measurement shows were on the right order for walltime but likely
# understated for memory:
#   mem=12gb    -- the smoke test's single accumulated chunk (6,495,777
#                  events, 1,325.3 MB on disk, per the "Saved final chunk"
#                  log line) already used 6.4 GiB peak process memory --
#                  roughly a 5x data-size-to-process-memory ratio. It never
#                  hit chunk_yield_threshold_bytes=2GB (the config's
#                  per-chunk flush threshold) because it was the run's only/
#                  final chunk. The full-scale run WILL hit that 2GB
#                  threshold repeatedly; at the same ~5x ratio that
#                  projects to ~10 GiB peak. 12gb leaves real margin above
#                  that, not the untested 8gb guess this comment used to
#                  make.
#   walltime=1h30m -- the smoke test's own measured throughput
#                  (~41,730 events/sec) projects the full run's
#                  94,148,416 raw events (30522: 45,235,604 + 30555:
#                  48,912,812, both independently verified in this
#                  project's earlier H->ZZ->4l work,
#                  reports/higgs_4lepton_zz/summary.md on
#                  analysis/higgs-4lepton-clean) to ~38 minutes -- 1h30m is
#                  ~2.4x that measured projection, real margin without the
#                  original guess's much larger, untested 4h pad. Still
#                  well under queue N's 12h default and 72h hard max.
#   io=40       -- kept unchanged; the smoke test didn't isolate a clean
#                  bytes/sec throughput figure (only an events/sec rate),
#                  so there is no better measurement to revise this from
#                  yet. Still comfortably above the ~32.8 MiB/s aggregate
#                  the H->ZZ->4l reference job measured.
# ---------------------------------------------------------------------------
#PBS -N m0m1j0_fullscale
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=12gb
#PBS -l walltime=01:30:00
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
