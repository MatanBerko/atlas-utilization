#!/bin/bash
# Pileup study jobs. WHAT selects the stage:
#   pu_profile   Part A2 -- MC nTrueInt profile over all generated events of
#                one record (RECORD=<id>)
#   probe        Part B  -- the per-file pileup probe (array; mapping file)
#PBS -N mcv3_pileup
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

WORK_DIR="${WORK_DIR:?WORK_DIR not set}"
REPO_DIR="${REPO_DIR:-${WORK_DIR}/repo}"
WHAT="${WHAT:?WHAT not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
# Nothing is written to the real $HOME by this job.
export MPLCONFIGDIR="${WORK_DIR}/.mplconfig"
export XDG_CACHE_HOME="${WORK_DIR}/.cache"
export HOME="${WORK_DIR}/.jobhome"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$HOME"

source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"
cd "$REPO_DIR"

echo "Job $PBS_JOBID on $(hostname) at $(date)"
echo "commit=$(git rev-parse HEAD)  WHAT=$WHAT"

case "$WHAT" in
  pu_profile)
    RECORD="${RECORD:?RECORD not set}"
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/pileup/measure_mc_pu_profile.py \
        --record "$RECORD" \
        --out "$WORK_DIR/evidence/mc_pu_profile_${RECORD}.json"
    ;;
  probe)
    MAPPING_FILE="${MAPPING_FILE:?MAPPING_FILE not set}"
    JOB_INDEX="${PBS_ARRAY_INDEX:-${PILEUP_ARRAY_INDEX:-}}"
    if [[ -z "$JOB_INDEX" ]]; then
      echo "neither PBS_ARRAY_INDEX nor PILEUP_ARRAY_INDEX set" >&2; exit 1
    fi
    LINE=$(sed -n "${JOB_INDEX}p" "$MAPPING_FILE")
    if [[ -z "$LINE" ]]; then
      echo "no mapping line $JOB_INDEX in $MAPPING_FILE" >&2; exit 1
    fi
    read -r MAP_INDEX KIND LABEL RECORD FILE_INDEX <<< "$LINE"
    if [[ "$MAP_INDEX" != "$JOB_INDEX" ]]; then
      echo "mapping line $JOB_INDEX carries index '$MAP_INDEX'" >&2; exit 1
    fi
    OUT="$WORK_DIR/probe/${KIND}_${LABEL}_${RECORD}_${FILE_INDEX}.json"
    mkdir -p "$WORK_DIR/probe"
    echo "kind=$KIND label=$LABEL record=$RECORD file_index=$FILE_INDEX"
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/pileup/run_pileup_probe_on_file.py \
        --kind "$KIND" --dataset-label "$LABEL" \
        --record-id "$RECORD" --file-index "$FILE_INDEX" \
        --out "$OUT"
    ;;
  *)
    echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac

echo "Job $PBS_JOBID ($WHAT) finished at $(date)"
