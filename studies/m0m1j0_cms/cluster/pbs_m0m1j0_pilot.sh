#!/bin/bash
# ---------------------------------------------------------------------------
# pbs_m0m1j0_pilot.sh
#
# m0m1j0 CMS histogram -- Step 1 CLUSTER PILOT ONLY: exactly 4 jobs, one
# per input file, via a PBS job array (-J 1-4, $PBS_ARRAY_INDEX). This is
# the FIRST TWO files of each of the two DoubleMuon records this task
# uses (30522 = Run2016G, 30555 = Run2016H), per the task's own pilot
# scope -- NOT the full 57-file run, which is a separate, later,
# explicitly-not-started task.
#
# Array-index -> (record, file-index-within-record) mapping (fixed here,
# not derived from any external batching module -- there are only 4 jobs
# and the mapping is simple enough to state directly and verify by eye):
#   1 -> record 30522 (Run2016G), file-index 0 (first file)
#   2 -> record 30522 (Run2016G), file-index 1 (second file)
#   3 -> record 30555 (Run2016H), file-index 0 (first file)
#   4 -> record 30555 (Run2016H), file-index 1 (second file)
# Each job independently queries the CERN Open Data portal's own file list
# for its record (studies.m0m1j0_cms.design_checks.common.fetch_file_list)
# and records the EXACT URL + event count it read in its own
# job_metadata.json (studies/m0m1j0_cms/cluster/run_m0m1j0_on_file.py) --
# the merge step (merge_pilot.py) re-fetches that same list and verifies
# identity/coverage against it, since the task's own instructions note the
# portal's file list has changed within a single day before.
#
# Resource requests: NO PRIOR TIMING DATA EXISTS for this exact job (first
# run of this pilot) -- set with a large, explicit safety margin rather
# than a measured number, per the task's own instruction ("estimate...
# with large safety margin (nodes differ up to ~5-6x)"). Revisit once the
# pilot's own measured elapsed_sec (job_metadata.json) is available.
#   mem=6gb      -- one NanoAOD file's worth of Muon/Electron/Jet branches
#                    plus trigger booleans held in memory as awkward
#                    arrays; the closest measured precedent on this
#                    cluster (studies/hgg_cms/cluster/pbs_hgg_data_array.sh,
#                    photon-only branches from a similar-size file) peaked
#                    at 2.37 GB, so 6gb leaves comfortable headroom for
#                    reading more object types here.
#   walltime=01:00:00 -- keeps this job in the fast/short queue class (an
#                    OBSERVATION from the hgg_cms pilot, not a documented
#                    site policy -- see that pilot's own PBS script
#                    comment) while giving ~20x the hgg_cms pilot's own
#                    worst observed wall time (~3 min) for a comparable
#                    single-file XRootD read + selection job.
#   ncpus=1      -- one file per job, no internal thread pool used by this
#                    study's own scripts.
#   io=30        -- REQUIRED by this site's scheduler for every job; same
#                    value used by the comparable hgg_cms data-pilot job
#                    (one XRootD-read NanoAOD file per job).
#
# Log files: "^array_index^" is OpenPBS's own per-subjob log-path
# substitution token (same convention as
# studies/hgg_cms/cluster/pbs_hgg_data_array.sh).
# ---------------------------------------------------------------------------
#PBS -N m0m1j0_pilot
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
#PBS -J 1-4
#PBS -l select=1:ncpus=1:mem=6gb
#PBS -l walltime=01:00:00
#PBS -l io=30
#PBS -o /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_pilot/m0m1j0_pilot_^array_index^.out
#PBS -e /storage/agrp/berkom/atlas-utilization/logs/m0m1j0_pilot/m0m1j0_pilot_^array_index^.err

set -euo pipefail

REPO_DIR="${REPO_DIR:-/storage/agrp/berkom/atlas-utilization/work/m0m1j0_cms/repo}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
OUTPUT_BASE="${OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_pilot}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

JOB_INDEX="${PBS_ARRAY_INDEX:?PBS_ARRAY_INDEX not set -- submit as a job array (-J)}"

case "$JOB_INDEX" in
    1) RECORD_ID=30522; FILE_INDEX=0 ;;
    2) RECORD_ID=30522; FILE_INDEX=1 ;;
    3) RECORD_ID=30555; FILE_INDEX=0 ;;
    4) RECORD_ID=30555; FILE_INDEX=1 ;;
    *) echo "PBS_ARRAY_INDEX=$JOB_INDEX is not one of the 4 pilot indices (1-4)" >&2; exit 1 ;;
esac

mkdir -p "${TMPDIR:-/tmp}"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

cd "$REPO_DIR"

JOB_OUTPUT_DIR="${OUTPUT_BASE}/job_${JOB_INDEX}"
mkdir -p "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) starting on $(hostname) at $(date)"
echo "record=$RECORD_ID file-index=$FILE_INDEX output-dir=$JOB_OUTPUT_DIR"

python -u studies/m0m1j0_cms/cluster/run_m0m1j0_on_file.py \
    --record-id "$RECORD_ID" \
    --file-index "$FILE_INDEX" \
    --output-dir "$JOB_OUTPUT_DIR"

echo "Job $PBS_JOBID (array index $JOB_INDEX) finished at $(date)"
