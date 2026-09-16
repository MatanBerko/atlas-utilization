#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_signal.sh
#
# H->gamma-gamma SIGNAL parsing: one PBS job PER PRODUCTION MODE (per
# record) -- ggH (37350, 3 files), VBF (68497, 13), W+H (71013, 4), W-H
# (70173, 15), ZH (74132, 20), ttH (67611, 16); file counts from
# studies/hgg_cms/impl_checks/signal_sumw.json. One job per record (not
# per file, unlike the data array job) because: (a) each production mode
# already needs its own separate cross-section/genEventSumw bookkeeping,
# so a record IS the natural unit of work here; (b) every record has only
# a handful of files (3-20), small enough that one job per record is
# still fast and gives clean, well-scoped retries per production mode.
#
# This is a TEMPLATE, submitted once per record via -v (see
# submit_pilot.sh for the exact invocations): qsub -v
# CONFIG=config.cms_hgg_signal_ggh.yaml,LABEL=ggh pbs_hgg_signal.sh
#
# --run-dir is passed explicitly (same reasoning as pbs_hgg_data_array.sh)
# so each record's run lands in its own fixed, predictable Lustre
# directory rather than an auto-generated timestamped one; the per-record
# configs' parsing_task_config paths are left relative on purpose so
# utils/paths.py's update_config_paths_with_run_dir nests them correctly
# under --run-dir.
#
# Resource requests: PLACEHOLDERS -- no local D3 run of the equivalent
# single-file (ggH) job ever completed (local remote reads were too
# unreliable; D3 was moved to the cluster -- see pbs_hgg_d3_signal.sh,
# which measures this job's per-file cost, using the WORST CASE record
# by events/file, via /usr/bin/time -v). DO NOT SUBMIT until the pilot
# has run and been reviewed, AND these mem/walltime values have been
# replaced with real numbers (x2 safety factor) from D3's + the pilot's
# own measurements -- see studies/hgg_cms/cluster/PILOT_CHECKLIST.md.
#
# Log files: this #PBS header's own -o/-e is a SHARED placeholder --
# since this script is submitted once PER LABEL (6 times for the full
# signal run, once per pilot signal job), every caller MUST override
# -o/-e on the qsub command line with the label baked into the filename
# (a #PBS header directive cannot reference a qsub -v variable, so this
# cannot be fixed inside the header itself) -- see submit_pilot.sh for
# the exact invocation. Submitting this script bare, for more than one
# label, without that override WILL make concurrent jobs share a log file.
#
# Output directory: OUTPUT_BASE, if set via `qsub -v OUTPUT_BASE=...`,
# overrides where this job's output goes (used by submit_pilot.sh to
# redirect each pilot signal job under .../output/hgg_pilot/signal/<label>/,
# keeping the full run's own .../output/cms_hgg_signal_<label>/ directory
# completely untouched and empty until the full run actually happens).
# ---------------------------------------------------------------------------
#PBS -N hgg_signal
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -l select=1:ncpus=1:mem=8gb
#PBS -l walltime=04:00:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_signal/hgg_signal_MUST_BE_OVERRIDDEN_PER_LABEL.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_signal/hgg_signal_MUST_BE_OVERRIDDEN_PER_LABEL.err

set -euo pipefail

: "${CONFIG:?must pass -v CONFIG=config.cms_hgg_signal_<label>.yaml}"
: "${LABEL:?must pass -v LABEL=<label>, e.g. ggh}"

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
JOB_RUN_DIR="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/cms_hgg_signal_${LABEL}}"

mkdir -p "${TMPDIR:-/tmp}" "$JOB_RUN_DIR"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

echo "Job $PBS_JOBID ($LABEL) starting on $(hostname) at $(date)"
echo "TMPDIR=$TMPDIR"
echo "Run dir: $JOB_RUN_DIR"

python -u main.py \
    --config "$CONFIG" \
    --run-dir "$JOB_RUN_DIR" \
    --tasks parsing \
    --log-level INFO

echo "Parsing done, running H->gamma-gamma selection on this record's chunk(s)..."

python -u studies/hgg_cms/cluster/run_selection_on_chunks.py \
    --chunks-dir "${JOB_RUN_DIR}/parsed_data" \
    --output-dir "${JOB_RUN_DIR}/selected" \
    --is-data false \
    --config "$CONFIG"
# --record-id deliberately omitted: read per event from each chunk's own
# "source_record" field (FileParser attaches this automatically).

echo "Job $PBS_JOBID ($LABEL) finished at $(date)"
