#!/bin/bash
# Nominal-6 additions precheck (27 Nov 2026): per-sample summary of the file-0 production outputs (precheck_analysis.py),
# READ ONLY on the outputs; the precheck-only registry is passed explicitly.
#PBS -N n6_ana
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
set -euo pipefail
W="${WORK_DIR:?WORK_DIR not set}"
source /usr/wipp/conda/24.5.0/etc/profile.d/conda.sh
conda activate /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
export OMP_NUM_THREADS=1 MPLCONFIGDIR="$W/.mplconfig" XDG_CACHE_HOME="$W/.cache" HOME="$W/.jobhome"
echo "Job $PBS_JOBID on $(hostname) at $(date)"
python -u "$W/scripts/precheck_analysis.py" --runs "$W/runs" --logs "$W/logs" --mapping "$W/mapping_precheck_file0.txt" \
  --registry "$W/scripts/precheck_registry_PRECHECK_ONLY.json" --inputs "$W/scripts/inputs_20261127.json" --out "$W/evidence"
echo "done $(date)"
