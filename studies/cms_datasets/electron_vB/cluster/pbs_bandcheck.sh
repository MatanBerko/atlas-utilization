#!/bin/bash
# Step B GATE 2: verify against the data that every event that changed
# between dR 0.05 and dR 0.12 has an electron in the 0.05-0.12 band.
# Environment: REPO_DIR, MAPPING_FILE ("<array_index> <dataset> <job>"),
#              KEYS_JSON, PILOT_FILES, OUT_DIR, [LOWMASS_CUT]
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
KEYS_JSON="${KEYS_JSON:?}"
PILOT_FILES="${PILOT_FILES:?}"
OUT_DIR="${OUT_DIR:?}"
LOWMASS_CUT="${LOWMASS_CUT:-}"
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python

IDX="${PBS_ARRAY_INDEX:?}"
LINE=$(sed -n "$((IDX+1))p" "$MAPPING_FILE")
read -r MAP_IDX DATASET JOB <<< "$LINE"
if [[ "$MAP_IDX" != "$IDX" ]]; then echo "bad mapping line $IDX" >&2; exit 1; fi

EXTRA=""
if [[ -n "$LOWMASS_CUT" ]]; then EXTRA="--dump-lowmass-pairs $LOWMASS_CUT"; fi

mkdir -p "$OUT_DIR"
cd "$REPO_DIR"
echo "[$IDX] commit=$(git rev-parse HEAD) $DATASET $JOB $(date)"
/usr/bin/time -v "$PY" -u studies/cms_datasets/electron_vB/verify_radius_band.py \
  --dataset "$DATASET" --job "$JOB" --keys-json "$KEYS_JSON" \
  --pilot-files "$PILOT_FILES" --out "${OUT_DIR}/${DATASET}_${JOB}.json" $EXTRA
echo "[$IDX] done $(date)"
