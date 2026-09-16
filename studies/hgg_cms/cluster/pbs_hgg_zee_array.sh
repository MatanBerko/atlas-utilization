#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_zee_array.sh
#
# Implementation task 6, Part 4 (REVISED 16 Sep 2026): ONE generic array-
# job template for the Z->e+e- control-region parsing+selection run --
# data OR DY simulation, one file PER JOB (PBS job array,
# $PBS_ARRAY_INDEX), exactly the same pattern pbs_hgg_data_array.sh
# already uses successfully for the main analysis's 133 DoubleEG files.
#
# REVISED from an earlier 4-variant design (data/DY x main/trigger-
# efficiency): the "trigger-efficiency" variant was a SEPARATE cluster job
# filtering on a different trigger AND requiring a fresh parse of the same
# files a second time. That's no longer needed -- BOTH the energy-scale
# sample and the trigger-efficiency sample are now OFFLINE CUTS
# (studies/hgg_cms/validation/zee/) on ONE stored 60-180 GeV table from
# ONE run per dataset, since both trigger bits are stored per event
# (config.cms_hgg_zee_{data,dy}.yaml's trigger_requirements now lists BOTH
# HLT_Ele27_WPTight_Gsf and the diphoton trigger, mode=any -- see those
# configs' own comments for why filtering on the diphoton trigger ALONE
# was a bug). So now just TWO qsub calls, not four:
#
#   qsub -J 1-133 -v CONFIG=config.cms_hgg_zee_data.yaml,IS_DATA=true,TOTAL_FILES=133,OUTPUT_BASE=... pbs_hgg_zee_array.sh
#   qsub -J 1-41  -v CONFIG=config.cms_hgg_zee_dy.yaml,IS_DATA=false,TOTAL_FILES=41,OUTPUT_BASE=... pbs_hgg_zee_array.sh
#
# (submit_zee.sh issues exactly these two qsub calls -- see that script,
# which this task does NOT run, per this task's own "prepare, don't
# submit" instruction.)
#
# Resource requests: REUSES the full run's own MEASURED data-array numbers
# (mem=5gb, walltime=01:00:00 -- see pbs_hgg_data_array.sh's header: 16
# Sep 2026, worst observed ~3 min wall / 2.37 GB peak on a ~2,014,154
# -event DoubleEG file) rather than a fresh guess, since every job here is
# STILL exactly one file per job, and DY's own per-file event count
# (~1.75M average -- 71,839,442 events / 41 files, record 35669) is the
# same order of magnitude as the DATA files this was measured on. The
# ONLY extra per-file work now is the DY-only electron-veto-leakage
# estimate (run_zee_selection_on_chunks.py's compute_hgg_veto_leakage) --
# a second application of the same TM-cut/pairing formulas to a second,
# disjoint photon subset already in memory, not a second file read, so it
# should not meaningfully change these numbers. UNVERIFIED beyond that
# reasoning -- no Z->ee-specific pilot has actually run (this task
# explicitly does not submit anything); re-measure with the small
# --pilot run (2 data + 2 DY subjobs) before trusting these for the full
# 133+41 = 174-subjob submission.
#
# --run-dir (explicit, not main.py's auto-generated one) for the same
# reason as pbs_hgg_data_array.sh: concurrently-launched array subjobs can
# land in the same wall-clock second and would otherwise collide on one
# auto-generated directory.
# ---------------------------------------------------------------------------
#PBS -N hgg_zee
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -J 1-133
#PBS -l select=1:ncpus=1:mem=5gb
#PBS -l walltime=01:00:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_zee/hgg_zee_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_zee/hgg_zee_^array_index^.err

set -euo pipefail

: "${CONFIG:?must pass -v CONFIG=config.cms_hgg_zee_data.yaml or config.cms_hgg_zee_dy.yaml}"
: "${IS_DATA:?must pass -v IS_DATA=true|false}"
: "${TOTAL_FILES:?must pass -v TOTAL_FILES=<133 for data, 41 for DY>}"
# The stored window is fixed at 60-180 GeV for both datasets (see
# zee_selection.py's own module docstring for the justification) --
# overridable only for local testing, never needed in real submission.
MASS_LO="${MASS_LO:-60}"
MASS_HI="${MASS_HI:-180}"

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
LUSTRE_BASE="${OUTPUT_BASE:?must pass -v OUTPUT_BASE=/storage/.../output/hgg_zee/<variant>}"

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

mkdir -p "${TMPDIR:-/tmp}"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

JOB_RUN_DIR="${LUSTRE_BASE}/job_${JOB_INDEX}"
mkdir -p "$JOB_RUN_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "CONFIG=$CONFIG IS_DATA=$IS_DATA TOTAL_FILES=$TOTAL_FILES MASS_LO=$MASS_LO MASS_HI=$MASS_HI"
echo "Run dir: $JOB_RUN_DIR"

python -u main.py \
    --config "$CONFIG" \
    --run-dir "$JOB_RUN_DIR" \
    --tasks parsing \
    --batch-job-index "$JOB_INDEX" \
    --total-batch-jobs "$TOTAL_FILES" \
    --log-level INFO

echo "Parsing done, running Z->e+e- selection on this job's chunk(s)..."

python -u studies/hgg_cms/cluster/run_zee_selection_on_chunks.py \
    --chunks-dir "${JOB_RUN_DIR}/parsed_data" \
    --output-dir "${JOB_RUN_DIR}/selected" \
    --is-data "$IS_DATA" \
    --config "$CONFIG" \
    --metadata-cache-json "${JOB_RUN_DIR}/metadata_cache.json" \
    --batch-job-index "$JOB_INDEX" \
    --total-batch-jobs "$TOTAL_FILES" \
    --mass-lo "$MASS_LO" \
    --mass-hi "$MASS_HI"
# --record-id deliberately omitted: read per event from each chunk's own
# "source_record" field (FileParser attaches this automatically).

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
