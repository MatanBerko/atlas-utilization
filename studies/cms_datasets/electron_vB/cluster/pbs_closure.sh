#!/bin/bash
# E3: closure test on one run, one file per array subjob.
# Environment: REPO_DIR, MAPPING_FILE ("<array_index> <dataset> <era> <file_index>"),
#              OUT_DIR, RUN
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
REPO_DIR="${REPO_DIR:?}"
MAPPING_FILE="${MAPPING_FILE:?}"
OUT_DIR="${OUT_DIR:?}"
RUN="${RUN:?}"
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python

IDX="${PBS_ARRAY_INDEX:?}"
LINE=$(sed -n "$((IDX+1))p" "$MAPPING_FILE")
read -r MAP_IDX DATASET ERA FILEIDX <<< "$LINE"
if [[ "$MAP_IDX" != "$IDX" ]]; then echo "bad mapping line $IDX" >&2; exit 1; fi

mkdir -p "$OUT_DIR"
cd "$REPO_DIR"
echo "[$IDX] commit=$(git rev-parse HEAD) $DATASET $ERA file=$FILEIDX run=$RUN $(date)"
/usr/bin/time -v "$PY" -u studies/cms_datasets/electron_vB/closure_run.py \
  --dataset "$DATASET" --era "$ERA" --file-index "$FILEIDX" --run "$RUN" \
  --out-dir "$OUT_DIR"
echo "[$IDX] done $(date)"
