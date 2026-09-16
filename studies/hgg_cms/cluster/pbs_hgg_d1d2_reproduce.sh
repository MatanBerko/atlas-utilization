#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_d1d2_reproduce.sh
#
# Implementation task 6, Part D1/D2, run as a CLUSTER JOB (moved off the
# local machine because repeated local runs -- on two different internet
# connections -- hit persistent transient failures reading the ggH file
# over HTTPS; see studies/hgg_cms/impl_checks/reproduce_check_b_and_c.py's
# own module docstring/comments for the full history).
#
# Runs studies/hgg_cms/impl_checks/reproduce_check_b_and_c.py UNCHANGED in
# its logic -- same pre-set acceptance criteria, same exact pinned files
# and event ranges as check_c_trigger_mimicking.py / check_b_vertex.py --
# only the transport for the 3 pinned files is now XRootD (root://) instead
# of HTTPS (see that script's SIGNAL_URL/DATA_FILES comments for why).
#
# Output: reproduce_check_b_and_c.py is given --output-path pointing
# straight at Lustre, so the results JSON is written there directly --
# never under $HOME/the repo checkout (batch jobs must not write there;
# see PILOT_CHECKLIST.md). All pilot/validation output lives under
# .../output/hgg_pilot/ -- kept entirely separate from the full run's own
# (untouched, empty) output directories.
#
# Resource basis: mem=4gb/walltime=03:00:00 below are PLACEHOLDER GUESSES
# (this job has never actually run -- there is no local D3 measurement to
# base them on, since local D3 runs were abandoned due to persistent
# remote-read failures). After the pilot, read this job's own
# /usr/bin/time -v peak memory and PBS's own accounted walltime
# (`qstat -fx <jobid>` after it finishes) and see PILOT_CHECKLIST.md for
# how to size the full run's requests from them.
#
# ACCEPTANCE CRITERIA (pre-set, must NOT be changed after seeing results --
# see the script's own `reference` dict for the exact numbers):
#   - signal_n_offline_selected_match  : n_offline_selected == 19986
#   - signal_hlt_given_offline_match   : n_hlt_pass_given_offline == 19792
#   - data_n_candidates_match          : n_candidates_100_180 total == 92
#   - data_n_sideband_match            : n_sideband total == 70
#   - data_n_blinded_match             : n_blinded (COUNT ONLY) total == 22
#   - signal_shape_n_match             : shape sample size == 19792
#   (mode/sigma_eff values are reported for comparison against check_b's
#   numbers by eye/in the report -- not booleaned here since check_b's
#   comparison is "within bootstrap uncertainty", not exact equality.)
# If ANY of the boolean "*_match" fields in the output JSON's "comparison"
# dict is false, DO NOT edit either implementation to force agreement --
# report it and investigate the root cause instead (see the main task's
# own explicit instruction on this point).
# ---------------------------------------------------------------------------
#PBS -N hgg_d1d2_reproduce
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=4gb
#PBS -l walltime=03:00:00
#PBS -l io=10
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_pilot/d1d2/hgg_d1d2_reproduce.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_pilot/d1d2/hgg_d1d2_reproduce.err

set -euo pipefail

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
LUSTRE_OUT="/storage/agrp/berkom/atlas-utilization/output/hgg_pilot/d1d2_reproduce"

mkdir -p "${TMPDIR:-/tmp}" "$LUSTRE_OUT"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

echo "Job $PBS_JOBID starting on $(hostname) at $(date)"
echo "TMPDIR=$TMPDIR"

/usr/bin/time -v python -u studies/hgg_cms/impl_checks/reproduce_check_b_and_c.py \
    --output-path "${LUSTRE_OUT}/reproduce_check_b_and_c_results.json" \
    2> "${LUSTRE_OUT}/timing_and_stderr.log"

echo "Results written to: ${LUSTRE_OUT}/reproduce_check_b_and_c_results.json"
echo "Timing/peak-memory (from /usr/bin/time -v): ${LUSTRE_OUT}/timing_and_stderr.log"
echo "Job $PBS_JOBID finished at $(date)"
