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
# Output: the script's own results JSON
# (reproduce_check_b_and_c_results.json) plus this job's stdout/stderr log,
# copied to Lustre so they survive after the job's scratch space is gone.
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
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_d1d2/hgg_d1d2_reproduce.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_d1d2/hgg_d1d2_reproduce.err

set -euo pipefail

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
LUSTRE_OUT="/storage/agrp/berkom/atlas-utilization/output/hgg_d1d2_reproduce"

mkdir -p "${TMPDIR:-/tmp}" "$LUSTRE_OUT"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

echo "Job $PBS_JOBID starting on $(hostname) at $(date)"
echo "TMPDIR=$TMPDIR"

/usr/bin/time -v python -u studies/hgg_cms/impl_checks/reproduce_check_b_and_c.py \
    2> "${LUSTRE_OUT}/timing_and_stderr.log"

cp studies/hgg_cms/impl_checks/reproduce_check_b_and_c_results.json "$LUSTRE_OUT/"

echo "Results written to: ${LUSTRE_OUT}/reproduce_check_b_and_c_results.json"
echo "Timing/peak-memory (from /usr/bin/time -v): ${LUSTRE_OUT}/timing_and_stderr.log"
echo "Job $PBS_JOBID finished at $(date)"
