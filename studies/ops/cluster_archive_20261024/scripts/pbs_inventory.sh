#!/bin/bash
# Phase 1 inventory job: read-only metadata walk (inventory.py).
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
set -euo pipefail
R="${REPORT_DIR:?}"
export HOME="${TMPDIR:-/tmp}/inv_home"; mkdir -p "$HOME"
export PYTHONDONTWRITEBYTECODE=1
echo "inventory on $(hostname) at $(date)"
/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python -u "$R/inventory.py" "$R/inventory.json"
echo "done at $(date)"
