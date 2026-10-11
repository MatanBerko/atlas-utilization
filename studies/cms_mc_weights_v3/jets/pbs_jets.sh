#!/bin/bash
# Jet-excess study jobs. WHAT selects the stage:
#   probe   Parts B/C -- the per-file jet probe (array; mapping file)
#   merge   the merge, tables, plots and verdicts
#PBS -N mcv3_jets
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
  probe)
    MAPPING_FILE="${MAPPING_FILE:?MAPPING_FILE not set}"
    JOB_INDEX="${PBS_ARRAY_INDEX:-${JETS_ARRAY_INDEX:-}}"
    if [[ -z "$JOB_INDEX" ]]; then
      echo "neither PBS_ARRAY_INDEX nor JETS_ARRAY_INDEX set" >&2; exit 1
    fi
    LINE=$(sed -n "${JOB_INDEX}p" "$MAPPING_FILE")
    if [[ -z "$LINE" ]]; then
      echo "no mapping line $JOB_INDEX in $MAPPING_FILE" >&2; exit 1
    fi
    read -r MAP_INDEX KIND LABEL RECORD FILE_INDEX <<< "$LINE"
    if [[ "$MAP_INDEX" != "$JOB_INDEX" ]]; then
      echo "mapping line $JOB_INDEX carries index '$MAP_INDEX'" >&2; exit 1
    fi
    # PROBE_DIR lets a re-run write somewhere new instead of overwriting the
    # previous pass, so nothing already on disk is destroyed.
    OUT_DIR="${PROBE_DIR:-$WORK_DIR/probe}"
    OUT="$OUT_DIR/${KIND}_${LABEL}_${RECORD}_${FILE_INDEX}.json"
    mkdir -p "$OUT_DIR"
    echo "kind=$KIND label=$LABEL record=$RECORD file_index=$FILE_INDEX"
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/jets/run_jet_probe_on_file.py \
        --kind "$KIND" --dataset-label "$LABEL" \
        --record-id "$RECORD" --file-index "$FILE_INDEX" \
        --out "$OUT" \
        ${JER_JSON:+--jer-json "$JER_JSON"} \
        ${PU_JSON:+--pu-json "$PU_JSON"}
    ;;
  merge)
    /usr/bin/time -v python -u studies/cms_mc_weights_v3/jets/merge_and_plot_jets.py \
        --probe-dir "${PROBE_DIR:-$WORK_DIR/probe}" \
        --registry studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json \
        --pilot-inputs "${PILOT_INPUTS:?}" \
        --hepdata studies/cms_mc_weights_v3/jets/evidence/hepdata_smp19009.json \
        --out-dir "$WORK_DIR/plots" \
        --evidence "$WORK_DIR/evidence/jet_excess_results.json"
    ;;
  *)
    echo "unknown WHAT=$WHAT" >&2; exit 1 ;;
esac

echo "Job $PBS_JOBID ($WHAT) finished at $(date)"
