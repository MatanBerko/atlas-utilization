#!/bin/bash
# electron-datasets task: one PBS array subjob per file, --population matched4
# (or matched, for the master re-run comparison).
#
# Environment:
#   REPO_DIR      pinned checkout to run from
#   MAPPING_FILE  lines: "<array_index> <dataset> <record_id> <file_index> <job_index>"
#   OUT_BASE      outputs go to $OUT_BASE/<dataset>/job_<job_index>
#   POPULATION    matched4 (default) or matched
#   EXTRA_ARGS    e.g. "--debug-event-dump --no-emu-overlap-removal"
#   LOG_DIR       where PBS writes .out/.err (never the home directory)
#PBS -S /bin/bash
#PBS -q N
#PBS -m n
#PBS -l select=1:ncpus=1:mem=8gb
#PBS -l walltime=02:00:00
#PBS -l io=25

set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export TMPDIR="${TMPDIR:-/tmp}"

REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
MAPPING_FILE="${MAPPING_FILE:?MAPPING_FILE not set}"
OUT_BASE="${OUT_BASE:?OUT_BASE not set}"
POPULATION="${POPULATION:-matched4}"
EXTRA_ARGS="${EXTRA_ARGS:-}"
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python

IDX="${PBS_ARRAY_INDEX:?submit as a job array (-J)}"
LINE=$(sed -n "$((IDX+1))p" "$MAPPING_FILE")
if [[ -z "$LINE" ]]; then echo "no mapping line for index $IDX" >&2; exit 1; fi
read -r MAP_IDX DATASET RECORD FILEIDX JOBIDX <<< "$LINE"
if [[ "$MAP_IDX" != "$IDX" ]]; then
  echo "mapping line $IDX has index field '$MAP_IDX'" >&2; exit 1
fi

OUTDIR="${OUT_BASE}/${DATASET}/job_${JOBIDX}"
mkdir -p "$OUTDIR"
cd "$REPO_DIR"
echo "[$IDX] commit=$(git rev-parse HEAD) host=$(hostname) $(date)"
echo "[$IDX] dataset=$DATASET record=$RECORD file_index=$FILEIDX population=$POPULATION outdir=$OUTDIR"
echo "[$IDX] extra_args=$EXTRA_ARGS"

/usr/bin/time -v "$PY" -u studies/cms_datasets/cluster/run_dataset_on_file.py \
  --dataset-label "$DATASET" --record-id "$RECORD" --file-index "$FILEIDX" \
  --output-dir "$OUTDIR" --population "$POPULATION" $EXTRA_ARGS
echo "[$IDX] done $(date)"
