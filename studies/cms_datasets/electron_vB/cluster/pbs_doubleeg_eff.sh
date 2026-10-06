#!/bin/bash
# Step D: one PBS array subjob per DoubleEG file.
# Environment: REPO_DIR, MAPPING_FILE ("<array_index> <era> <file_index>"), OUT_DIR
#PBS -S /bin/bash
#PBS -q N
#PBS -m n
#PBS -l select=1:ncpus=1:mem=6gb
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
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python

IDX="${PBS_ARRAY_INDEX:?}"
LINE=$(sed -n "$((IDX+1))p" "$MAPPING_FILE")
read -r MAP_IDX ERA FILEIDX <<< "$LINE"
if [[ "$MAP_IDX" != "$IDX" ]]; then echo "bad mapping line $IDX" >&2; exit 1; fi

mkdir -p "$OUT_DIR"
cd "$REPO_DIR"
echo "[$IDX] commit=$(git rev-parse HEAD) era=$ERA file=$FILEIDX $(date)"
/usr/bin/time -v "$PY" -u studies/cms_datasets/electron_vB/measure_doubleeg_efficiency.py \
  --era "$ERA" --file-index "$FILEIDX" --out "${OUT_DIR}/eff_${ERA}_${FILEIDX}.json"
echo "[$IDX] done $(date)"
