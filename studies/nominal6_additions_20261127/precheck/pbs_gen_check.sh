#!/bin/bash
# Nominal-6 additions precheck (27 Nov 2026): generator-level facts from file 0 (gen_check.py), READ ONLY.
#PBS -N n6_gen
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
set -euo pipefail
W="${WORK_DIR:?WORK_DIR not set}"; R="${REPO_DIR:?REPO_DIR not set}"
source /usr/wipp/conda/24.5.0/etc/profile.d/conda.sh
conda activate /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
export OMP_NUM_THREADS=1 MPLCONFIGDIR="$W/.mplconfig" XDG_CACHE_HOME="$W/.cache" HOME="$W/.jobhome"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$HOME"
echo "Job $PBS_JOBID on $(hostname) at $(date); repo commit $(git -C "$R" rev-parse HEAD)"
/usr/bin/time -v python -u "$W/scripts/gen_check.py" --repo "$R" --max-events "${MAX_EVENTS:-100000}" --out "$W/gen_check" \
  --records 37276 37420 68459 68559 69681 69699 74652 74670 37604 68731 70301 71145 74292 74314 75561 69771 72648 71636 71640
echo "done $(date)"
