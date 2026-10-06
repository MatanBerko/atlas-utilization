#!/bin/bash
# E3 support: scan every file of one (dataset, era) for the closure run and
# check that all four datasets' HLT branches are present.
# Environment: REPO_DIR, MAPPING_FILE ("<array_index> <dataset> <era>"), OUT_DIR, RUN
#PBS -S /bin/bash
#PBS -q N
#PBS -m n
#PBS -l select=1:ncpus=1:mem=4gb
#PBS -l walltime=03:00:00
#PBS -l io=40

set -euo pipefail
export OMP_NUM_THREADS=1
export TMPDIR="${TMPDIR:-/tmp}"
REPO_DIR="${REPO_DIR:?}"
MAPPING_FILE="${MAPPING_FILE:?}"
OUT_DIR="${OUT_DIR:?}"
RUN="${RUN:?}"
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python

IDX="${PBS_ARRAY_INDEX:?}"
LINE=$(sed -n "$((IDX+1))p" "$MAPPING_FILE")
read -r MAP_IDX DATASET ERA <<< "$LINE"
if [[ "$MAP_IDX" != "$IDX" ]]; then echo "bad mapping line $IDX" >&2; exit 1; fi

mkdir -p "$OUT_DIR"
cd "$REPO_DIR"
echo "[$IDX] commit=$(git rev-parse HEAD) $DATASET $ERA run=$RUN $(date)"
"$PY" -u studies/cms_datasets/electron_vB/find_run_files.py \
  --dataset "$DATASET" --era "$ERA" --run "$RUN" \
  --out "${OUT_DIR}/runscan_${DATASET}_${ERA}.json"
echo "[$IDX] done $(date)"
