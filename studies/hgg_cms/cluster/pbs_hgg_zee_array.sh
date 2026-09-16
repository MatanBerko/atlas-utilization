#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_zee_array.sh
#
# Implementation task 6, Part 4: ONE generic array-job template for all
# four Z->e+e- control-region parsing+selection runs -- data or DY
# simulation, main sample or trigger-efficiency sample -- one file PER JOB
# (PBS job array, $PBS_ARRAY_INDEX), exactly the same pattern
# pbs_hgg_data_array.sh already uses successfully for the main analysis's
# 133 DoubleEG files (one job per file keeps output in exact 1:1
# correspondence with one input file, isolates a single bad/slow file's
# retry to one job, and needs no shared-code change to support -- unlike
# the H->gamma-gamma SIGNAL jobs, which deliberately bundle each record's
# files into ONE job because the record-level genEventSumw bookkeeping
# wants them together; here the per-record sumw is instead summed ACROSS
# jobs at merge time, the same way the main run's data-side merge already
# sums per-record EVENT totals across its 133 jobs -- see
# merge_zee_outputs.py).
#
# Unlike pbs_hgg_data_array.sh (which hardcodes TOTAL_FILES=133 for one
# specific dataset), everything dataset-specific here is passed via
# `qsub -v`, so ONE script covers all four runs:
#
#   qsub -J 1-133 -v CONFIG=config.cms_hgg_zee_data.yaml,IS_DATA=true,TOTAL_FILES=133,OUTPUT_BASE=...,MASS_LO=70,MASS_HI=110 pbs_hgg_zee_array.sh
#   qsub -J 1-41  -v CONFIG=config.cms_hgg_zee_dy.yaml,IS_DATA=false,TOTAL_FILES=41,OUTPUT_BASE=...,MASS_LO=70,MASS_HI=110 pbs_hgg_zee_array.sh
#   qsub -J 1-133 -v CONFIG=config.cms_hgg_zee_trigeff_data.yaml,IS_DATA=true,TOTAL_FILES=133,OUTPUT_BASE=...,MASS_LO=95,MASS_HI=1000000,DIPHOTON_TRIGGER_BRANCH=HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90 pbs_hgg_zee_array.sh
#   qsub -J 1-41  -v CONFIG=config.cms_hgg_zee_trigeff_dy.yaml,IS_DATA=false,TOTAL_FILES=41,OUTPUT_BASE=...,MASS_LO=95,MASS_HI=1000000,DIPHOTON_TRIGGER_BRANCH=HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90 pbs_hgg_zee_array.sh
#
# (submit_zee.sh issues exactly these four qsub calls -- see that script,
# which this task does NOT run, per this task's own "prepare, don't
# submit" instruction.)
#
# Resource requests: REUSES the full run's own MEASURED data-array numbers
# (mem=5gb, walltime=01:00:00 -- see pbs_hgg_data_array.sh's header: 16
# Sep 2026, worst observed ~3 min wall / 2.37 GB peak on a ~2,014,154
# -event DoubleEG file) rather than a fresh guess, since every job here is
# STILL exactly one file per job, and DY's own per-file event count
# (~1.75M average -- 71,839,442 events / 41 files, record 35669) is the
# same order of magnitude as the DATA files this was measured on. No
# analysis-layer step here does more per-file work than the main run's
# equivalent step (same TM-cut/pairing formulas, no cross-file
# aggregation within a job) -- so these numbers are expected to be, if
# anything, a slight overestimate, not an underestimate. UNVERIFIED
# beyond that reasoning -- no Z->ee-specific pilot has actually run (this
# task explicitly does not submit anything); re-measure with a small
# array-index pilot (e.g. -J 1-3) before trusting these for the full
# 133+41+133+41 = 348-subjob submission.
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

: "${CONFIG:?must pass -v CONFIG=config.cms_hgg_zee_<variant>.yaml}"
: "${IS_DATA:?must pass -v IS_DATA=true|false}"
: "${TOTAL_FILES:?must pass -v TOTAL_FILES=<133 for data, 41 for DY>}"
MASS_LO="${MASS_LO:-70}"
MASS_HI="${MASS_HI:-110}"
DIPHOTON_TRIGGER_BRANCH="${DIPHOTON_TRIGGER_BRANCH:-}"

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
echo "CONFIG=$CONFIG IS_DATA=$IS_DATA TOTAL_FILES=$TOTAL_FILES MASS_LO=$MASS_LO MASS_HI=$MASS_HI DIPHOTON_TRIGGER_BRANCH=${DIPHOTON_TRIGGER_BRANCH:-<none>}"
echo "Run dir: $JOB_RUN_DIR"

python -u main.py \
    --config "$CONFIG" \
    --run-dir "$JOB_RUN_DIR" \
    --tasks parsing \
    --batch-job-index "$JOB_INDEX" \
    --total-batch-jobs "$TOTAL_FILES" \
    --log-level INFO

echo "Parsing done, running Z->e+e- selection on this job's chunk(s)..."

TRIGGER_ARG=()
if [[ -n "$DIPHOTON_TRIGGER_BRANCH" ]]; then
    TRIGGER_ARG=(--record-diphoton-trigger-bit "$DIPHOTON_TRIGGER_BRANCH")
fi

python -u studies/hgg_cms/cluster/run_zee_selection_on_chunks.py \
    --chunks-dir "${JOB_RUN_DIR}/parsed_data" \
    --output-dir "${JOB_RUN_DIR}/selected" \
    --is-data "$IS_DATA" \
    --config "$CONFIG" \
    --metadata-cache-json "${JOB_RUN_DIR}/metadata_cache.json" \
    --batch-job-index "$JOB_INDEX" \
    --total-batch-jobs "$TOTAL_FILES" \
    --mass-lo "$MASS_LO" \
    --mass-hi "$MASS_HI" \
    "${TRIGGER_ARG[@]}"
# --record-id deliberately omitted: read per event from each chunk's own
# "source_record" field (FileParser attaches this automatically).

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
