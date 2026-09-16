#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_hgg_data_array.sh
#
# H->gamma-gamma DATA parsing: one PBS job PER INPUT FILE, via a PBS job
# array (OpenPBS -J start-end, $PBS_ARRAY_INDEX). 133 files total across
# DoubleEG records 30521 (Run2016G, 47 files) + 30554 (Run2016H, 86
# files) -- see studies/hgg_cms/impl_checks/signal_sumw.json / the task's
# own INVENTORY.md for these counts. One file per job (rather than a few
# large multi-file jobs) is used here because this task's per-event
# OUTPUT is explicitly "one output per input file, merged later"
# (studies/hgg_cms/output.py) -- one job per file keeps every job's own
# single chunk output in exact 1:1 correspondence with one input file,
# and isolates a single bad/slow file's retry to one job instead of
# re-running a whole multi-file batch.
#
# Uses config.cms_hgg_data.yaml with --batch-job-index/--total-batch-jobs
# (utils/batching.py's get_batch_slice_by_year: with total_batches equal
# to the exact total file count across both records, each batch gets
# EXACTLY one file). IMPORTANT: every one of the 133 array subjobs fetches
# this record's file list from the CERN Open Data API INDEPENDENTLY (no
# shared cache between them), then flattens+slices it with ZERO sorting
# anywhere in the pipeline -- so index<->file consistency across all 133
# jobs relies on the portal returning the same file order every time it's
# queried. This was checked (not just assumed) -- see
# studies/hgg_cms/impl_checks/mapping_check/ for the offline verification
# tool, the evidence gathered, and this finding's own writeup; read that
# before trusting a specific index -> file assignment for anything beyond
# "one file per index, no duplicates, full coverage".
#
# --run-dir is passed explicitly (main.py's own documented mechanism "for
# multi-job PBS arrays") rather than letting main.py auto-generate a
# second-resolution timestamped run directory -- job array tasks launched
# together can easily land in the SAME wall-clock second, which would
# make them collide on one auto-generated run_dir and overwrite each
# other's output. --run-dir gives each array index its own deterministic
# directory instead. config.cms_hgg_data.yaml's own parsing_task_config
# paths (output_path/file_urls_path/jobs_logs_path) are left as their
# RELATIVE defaults on purpose, so utils/paths.py's
# update_config_paths_with_run_dir (only rewrites relative-or-missing
# paths, never touches an already-absolute one) nests them correctly
# under --run-dir with zero manual config-editing here.
#
# Resource requests: SET FROM MEASURED PILOT NUMBERS (16 Sep 2026, 2
# real files from record 30521): job 1 (2,014,154 events) took 2:03 wall
# (117s of that in parsing), 2.37 GB peak; job 2 took 3:00 wall, 2.15 GB
# peak. Worst observed: ~3 min wall, 2.37 GB peak.
#   mem=5gb    -- ~2x the observed 2.37 GB peak, rounded up.
#   walltime=01:00:00 -- ~20x the observed ~3 min wall (generous margin);
#     also keeps this job routed to the shortE queue, as observed for
#     <=02:00 requests during the pilot (this is an OBSERVATION from the
#     pilot run, not something confirmed against a written site policy
#     document -- recheck if routing behavior ever seems to change).
#   ncpus=1    -- config.cms_hgg_data.yaml sets threads=8
#     (pipeline/executor.py:815, ThreadedFileProcessor(max_threads=8)),
#     but that pool only ever has ONE file to read per data job (each
#     array index is batch-sliced to exactly one file -- see this
#     script's own comment on get_batch_slice_by_year above), so at most
#     one thread is ever actually active per job regardless of the
#     configured thread count. Requesting ncpus=8 x133 concurrent array
#     subjobs would reserve 1,064 cores' worth of scheduling for cores
#     that are provably never used here -- this is a deliberate judgment
#     call (the pilot itself ran successfully with ncpus=1); revisit if
#     you'd rather match the config's thread count literally.
#
# Log files: "^array_index^" is OpenPBS's own substitution token for a
# job array's Output_Path/Error_Path -- each subjob gets its own log file
# named with its actual array index, so two subjobs submitted under the
# same array (e.g. -J 1-133, or the pilot's -J 1-2) never share a log
# file. This is the default for a bare `qsub` of this script (e.g. the
# eventual full-run submission); submit_pilot.sh instead overrides -o/-e
# on the qsub command line (which takes priority over this #PBS header)
# to redirect the PILOT's logs under .../logs/hgg_pilot/ instead of here
# -- see that script for the exact invocation.
#
# Output directory: OUTPUT_BASE, if set via `qsub -v OUTPUT_BASE=...`,
# overrides where this job's output goes (used by submit_pilot.sh to
# redirect the pilot's 2-file run under .../output/hgg_pilot/data/,
# keeping the full run's own .../output/cms_hgg_data/ directory
# completely untouched and empty until the full run actually happens).
# ---------------------------------------------------------------------------
#PBS -N hgg_data
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -J 1-133
#PBS -l select=1:ncpus=1:mem=5gb
#PBS -l walltime=01:00:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/hgg_data/hgg_data_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/hgg_data/hgg_data_^array_index^.err

set -euo pipefail

REPO_DIR="$HOME/atlas-utilization"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
BASE_CONFIG="config.cms_hgg_data.yaml"
TOTAL_FILES=133
LUSTRE_BASE="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/cms_hgg_data}"

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

mkdir -p "${TMPDIR:-/tmp}"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

JOB_RUN_DIR="${LUSTRE_BASE}/job_${JOB_INDEX}"
mkdir -p "$JOB_RUN_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "TMPDIR=$TMPDIR"
echo "Run dir: $JOB_RUN_DIR"

python -u main.py \
    --config "$BASE_CONFIG" \
    --run-dir "$JOB_RUN_DIR" \
    --tasks parsing \
    --batch-job-index "$JOB_INDEX" \
    --total-batch-jobs "$TOTAL_FILES" \
    --log-level INFO

echo "Parsing done, running H->gamma-gamma selection on this job's chunk(s)..."

python -u studies/hgg_cms/cluster/run_selection_on_chunks.py \
    --chunks-dir "${JOB_RUN_DIR}/parsed_data" \
    --output-dir "${JOB_RUN_DIR}/selected" \
    --is-data true \
    --config "$BASE_CONFIG"
# --record-id deliberately omitted: read per event from each chunk's own
# "source_record" field (FileParser attaches this automatically).

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
