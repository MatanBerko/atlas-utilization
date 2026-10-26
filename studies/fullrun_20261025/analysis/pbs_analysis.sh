#!/bin/bash
# Full run 25 Oct 2026, Prompt B (26 Oct): verification and plots of the full
# run's outputs (analyze_fullrun.py). Read-only on every input; writes only
# into $OUT_DIR (a new folder).
#PBS -S /bin/bash
#PBS -q N
#PBS -m n
set -euo pipefail
R="${REPO_DIR:?}"; W="${WORK_DIR:?}"; O="${OUT_DIR:?}"
T="${TMPDIR:-/tmp}/fr25ana_${PBS_JOBID:-local}"
mkdir -p "$T"; trap 'rm -rf "$T"' EXIT
# Nothing is written to $HOME by this job.
export HOME="$T/home" MPLCONFIGDIR="$T/mpl" XDG_CACHE_HOME="$T/cache" TMPDIR="$T"
mkdir -p "$HOME" "$MPLCONFIGDIR" "$XDG_CACHE_HOME"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
source /usr/wipp/conda/24.5.0/etc/profile.d/conda.sh
conda activate /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
cd "$R"
echo "commit=$(git rev-parse HEAD) host=$(hostname) $(date)"
test ! -e "$O/analysis.json"   # never overwrite
mkdir -p "$O"
/usr/bin/time -v python -u studies/fullrun_20261025/analysis/analyze_fullrun.py \
    --data-build "$W/datachain2/data/deliver/default" --data-runs "$W/data/runs" \
    --mc-build "$W/mc/build_default" --mc-scratch "$W/mc/scratch_default" --out-dir "$O"
echo "done $(date)"
