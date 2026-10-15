#!/bin/bash
# Overlap-convention study (15 Oct 2026): one PBS array subjob per file.
# Read-only measurement; writes only to $OUT_DIR.
#
# Environment:
#   REPO_DIR      pinned checkout to run from
#   MAPPING_FILE  lines: "<array_index> <dataset> <record_id> <file_index>"
#   OUT_DIR       where the per-file JSON/NPZ go
#PBS -S /bin/bash
#PBS -q N
#PBS -m n
#PBS -l select=1:ncpus=1:mem=12gb
#PBS -l walltime=03:00:00
#PBS -l io=25

set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export TMPDIR="${TMPDIR:-/tmp}"

REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
MAPPING_FILE="${MAPPING_FILE:?MAPPING_FILE not set}"
OUT_DIR="${OUT_DIR:?OUT_DIR not set}"
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python

IDX="${PBS_ARRAY_INDEX:?submit as a job array (-J)}"
LINE=$(sed -n "$((IDX+1))p" "$MAPPING_FILE")
read -r MAP_IDX DATASET RECORD FILEIDX <<< "$LINE"
if [[ "$MAP_IDX" != "$IDX" ]]; then echo "mapping line $IDX has index '$MAP_IDX'" >&2; exit 1; fi

mkdir -p "$OUT_DIR"
cd "$REPO_DIR"
echo "[$IDX] commit=$(git rev-parse HEAD) host=$(hostname) $(date)"
echo "[$IDX] dataset=$DATASET record=$RECORD file_index=$FILEIDX"
/usr/bin/time -v "$PY" -u studies/overlap_convention_20261015/measure_overlap_on_file.py \
  --dataset-label "$DATASET" --record-id "$RECORD" --file-index "$FILEIDX" --out-dir "$OUT_DIR"
echo "[$IDX] done $(date)"
