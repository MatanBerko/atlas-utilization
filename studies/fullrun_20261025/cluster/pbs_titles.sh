#!/bin/bash
# Full run 25 Oct 2026, step 1: branch titles of one data and one MC file.
#PBS -S /bin/bash
#PBS -q N
#PBS -m n
#PBS -l select=1:ncpus=1:mem=2gb
#PBS -l walltime=00:30:00
#PBS -l io=1
set -euo pipefail
REPO_DIR="${REPO_DIR:?REPO_DIR not set}"
OUT="${OUT:?OUT not set}"
T="${TMPDIR:-/tmp}/titles_${PBS_JOBID:-local}"
mkdir -p "$T"; trap 'rm -rf "$T"' EXIT
# Nothing is written to $HOME by this job.
export HOME="$T/home" XDG_CACHE_HOME="$T/cache"; mkdir -p "$HOME" "$XDG_CACHE_HOME"
export PYTHONDONTWRITEBYTECODE=1
cd "$REPO_DIR"
echo "commit=$(git rev-parse HEAD) host=$(hostname) $(date)"
/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python -u \
    studies/fullrun_20261025/cluster/branch_titles.py \
    --record 30521 --file-index 0 --record 67801 --file-index 0 --out "$OUT"
