#!/bin/bash
# Full run 25 Oct 2026, step 4: write the data (five datasets, G+H) and MC
# (13 records) full-run mappings. Portal HTTP only, no ROOT reading.
#PBS -S /bin/bash
#PBS -q N
#PBS -m n
#PBS -l select=1:ncpus=1:mem=2gb
#PBS -l walltime=00:30:00
#PBS -l io=1
set -euo pipefail
REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
W="${WORK_DIR:?WORK_DIR not set}"
T="${TMPDIR:-/tmp}/fr25map_${PBS_JOBID:-local}"
mkdir -p "$T"; trap 'rm -rf "$T"' EXIT
# Nothing is written to $HOME by this job.
export HOME="$T/home" XDG_CACHE_HOME="$T/cache"; mkdir -p "$HOME" "$XDG_CACHE_HOME"
export PYTHONDONTWRITEBYTECODE=1
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python
cd "$REPO_DIR"
echo "commit=$(git rev-parse HEAD) host=$(hostname) $(date)"
"$PY" -u studies/fullrun_20261025/gen_full_mapping_5.py --out-dir "$W/mappings_data"
"$PY" -u studies/cms_mc_weights_v3/fullrun_prep/make_fullrun_mappings.py --out-dir "$W/mappings_mc"
echo "done $(date)"
