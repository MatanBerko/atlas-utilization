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
# Resource requests: SET FROM MEASURED PILOT NUMBERS (16 Sep 2026, 1 file
# per record): wall 13-51s, peak mem 0.19-0.79 GB across the 6 records
# (ggH's single file: 0.79 GB for 241,615 events parsed). A FULL signal
# job processes ALL of a record's files, not just one -- checked in the
# code (see run_selection_on_chunks.py's own main(): it loops over chunk
# files ONE AT A TIME via process_one_chunk, never concatenating a
# record's files together, so the SELECTION stage's own memory footprint
# does not grow with file count. The PARSING stage (main.py --tasks
# parsing) is the part that can hold more than one file's data at once:
# pipeline/executor.py:815 gives ThreadedFileProcessor max_threads=8 (see
# threads: 8 in config.cms_hgg_signal.yaml), so up to min(8, n_files)
# files can be read concurrently before EventAccumulator flushes a chunk
# at its chunk_yield_threshold_bytes (2 GB) -- meaning real peak memory
# is bounded well below "linear in total events" in practice, but that
# real ceiling was not measured (only single-file jobs were piloted), so
# a conservative LINEAR estimate is used here instead, exactly as
# intended by the x2 safety margin below.
#   Worst case by TOTAL events (not events/file) is VBF: 2,000,000
#   events over 13 files (signal_sumw.json's genEventCount) -- more than
#   ggH's own 540,000 total despite ggH having more events per file.
#   Scaling ggH's measured 0.79 GB / 241,615 events rate to VBF's
#   2,000,000 events: 0.79 * (2,000,000 / 241,615) = 6.54 GB raw
#   estimate; x2 safety margin = 13.08 GB -> rounded up to 14gb. This is
#   well under the 16 GB threshold, so no record needs splitting into
#   per-file jobs.
#   mem=14gb, walltime=02:00:00 (as specified), io=30 (unchanged; the
#   pilot gave no reason to raise it).
#   ncpus=8 -- matches config.cms_hgg_signal.yaml's threads=8, and unlike
#   the data job, a signal job's ThreadedFileProcessor genuinely reads
#   more than one file per job (up to 13 for VBF), so this pool is
#   actually exercised here.
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
#PBS -l select=1:ncpus=8:mem=14gb
#PBS -l walltime=02:00:00
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
