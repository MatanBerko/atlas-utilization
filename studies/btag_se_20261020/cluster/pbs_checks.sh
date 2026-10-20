#!/bin/bash
# b-tag 0.2489 + SingleElectron (Maryna, 20 Oct 2026): real-file checks.
#
# Four pinned commits are `git archive` tarballs in $WORK_DIR/code/:
#   old_data = fork master aaf945a           (b-tag 0.2598, --population matched4)
#   new_data = feature/cms-btag-singleelectron-20261020    (0.2489, matched5)
#   old_mc   = sync/mc-upstream-35-20261020 0e98075       (0.2598, 4-flag union)
#   new_mc   = feature/cms-mc-btag-singleelectron-20261020 (0.2489, 5-flag union)
# Each job unpacks the one it needs into node-local $TMPDIR/repo (no code
# files on /storage), and every side runs from the SAME path.
#
# MODE=perfile  array 0-7, one line of $WORK_DIR/mapping.txt each:
#               "<idx> <data|mc> <label> <record> <file_index> <job key> <sides>".
#   old  the OLD code, data --population matched4 / MC --is-mc matched4
#   new  the NEW code, data --population matched5 / MC --is-mc matched4
#   ovr  the NEW code with the b-tag constant set back to 0.2598 for this
#        process only (nothing on disk changes): if ovr == old, the b-tag is
#        the only difference between OLD and NEW.
#   old/new also write the per-event debug dump (--debug-event-dump).
# MODE=build    data delivery builder: NEW 5 datasets, OLD 4 datasets;
#               MC builder --smoke-test (defaults): OLD builder on OLD runs,
#               OLD builder on NEW runs, NEW builder on NEW runs.
# MODE=analyse  $WORK_DIR/scripts/analyse.py -> $WORK_DIR/evidence/.
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

W="${WORK_DIR:?WORK_DIR not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
T="${TMPDIR:-/tmp}/btagse_${PBS_JOBID:-local}"
mkdir -p "$T"
trap 'rm -rf "$T"' EXIT
# Nothing is written to $HOME by this job.
export HOME="$T/home" MPLCONFIGDIR="$T/mpl" XDG_CACHE_HOME="$T/cache"
mkdir -p "$HOME" "$MPLCONFIGDIR" "$XDG_CACHE_HOME"
source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

unpack() {  # unpack <tar name> -> $T/repo
    rm -rf "$T/repo"
    mkdir -p "$T/repo"
    tar -xf "$W/code/$1.tar" -C "$T/repo"
    echo "code $1: commit $(git get-tar-commit-id < "$W/code/$1.tar") sha256 $(sha256sum "$W/code/$1.tar" | cut -c1-16)"
}

DRIVER=studies/cms_datasets/cluster/run_dataset_on_file.py
# The b-tag override for side "ovr": set the constant in this process, run the
# driver's main() in the same process, then assert the value held.
OVR_PY='import runpy, sys
sys.path.insert(0, ".")
from studies.m0m1j0_cms import selection
old = selection.BTAG_DEEPFLAVB_MEDIUM_WP
selection.BTAG_DEEPFLAVB_MEDIUM_WP = 0.2598
print(f"b-tag override for this process: {old} -> {selection.BTAG_DEEPFLAVB_MEDIUM_WP}", flush=True)
sys.argv = [sys.argv[1]] + sys.argv[2:]
runpy.run_path(sys.argv[0], run_name="__main__")
assert selection.BTAG_DEEPFLAVB_MEDIUM_WP == 0.2598
print("b-tag override held: 0.2598", flush=True)'

echo "MODE=${MODE} on $(hostname) at $(date)"

if [[ "$MODE" == "perfile" ]]; then
    IDX="${PBS_ARRAY_INDEX:?}"
    read -r MI KIND LABEL RID FI JOB SIDES <<< "$(sed -n "$((IDX + 1))p" "$W/mapping.txt")"
    [[ "$MI" == "$IDX" ]] || { echo "mapping line mismatch: $MI != $IDX" >&2; exit 1; }
    for SIDE in ${SIDES//,/ }; do
        if [[ "$KIND" == "data" ]]; then
            OUT="$W/runs/$SIDE/data/$LABEL/job_$JOB"
            ARGS=(--dataset-label "$LABEL" --record-id "$RID" --file-index "$FI" --output-dir "$OUT")
            [[ "$SIDE" == "old" ]] && ARGS+=(--population matched4) || ARGS+=(--population matched5)
        else
            OUT="$W/runs/$SIDE/mc/record$RID/job_$JOB"
            ARGS=(--is-mc --dataset-label MC --record-id "$RID" --file-index "$FI"
                  --output-dir "$OUT" --population matched4)
        fi
        [[ "$SIDE" != "ovr" ]] && ARGS+=(--debug-event-dump)
        [[ -e "$OUT/job_metadata.json" ]] && { echo "exists, skipping: $OUT"; continue; }
        if [[ "$SIDE" == "old" ]]; then unpack "old_$KIND"; else unpack "new_$KIND"; fi
        mkdir -p "$OUT"
        cd "$T/repo"
        echo "=== $SIDE $KIND $LABEL $RID/$FI -> $OUT at $(date)"
        if [[ "$SIDE" == "ovr" ]]; then
            python -u -c "$OVR_PY" "$DRIVER" "${ARGS[@]}"
        else
            python -u "$DRIVER" "${ARGS[@]}"
        fi
        cd "$T"
    done
    echo "MODE=perfile done idx=$IDX at $(date)"
    exit 0
fi

if [[ "$MODE" == "build" ]]; then
    # Per-dataset indices (the builder's input format): job key -> file.
    D="$W/runs/new/data"
    echo '{"0": {"record_id": 30522, "file_index": 0}}' > "$D/DoubleMuon_index.json"
    echo '{"0": {"record_id": 30530, "file_index": 0}}' > "$D/SingleMuon_index.json"
    echo '{"0": {"record_id": 30521, "file_index": 0}}' > "$D/DoubleEG_index.json"
    echo '{"0": {"record_id": 30528, "file_index": 0}}' > "$D/MuonEG_index.json"
    echo '{"0": {"record_id": 30529, "file_index": 0}, "1": {"record_id": 30562, "file_index": 0}}' \
        > "$D/SingleElectron_index.json"
    for ds in DoubleMuon SingleMuon DoubleEG MuonEG; do
        cp "$D/${ds}_index.json" "$W/runs/old/data/${ds}_index.json"
    done
    unpack new_data
    (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_datasets/deliver/build_four_dataset_delivery.py \
        --runs-dir "$W/runs/new/data" --out-dir "$W/deliver/new/data" --out-prefix five \
        --datasets DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron)
    unpack old_data
    (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_datasets/deliver/build_four_dataset_delivery.py \
        --runs-dir "$W/runs/old/data" --out-dir "$W/deliver/old/data" --out-prefix four)
    # MC: OLD builder on OLD runs, OLD builder on NEW runs (isolates the
    # b-tag), NEW builder on NEW runs (adds the SingleElectron flag).
    for COMBO in "old_mc old old" "old_mc new oldbuilder_newruns" "new_mc new new"; do
        read -r TARNAME RUNS OUTNAME <<< "$COMBO"
        unpack "$TARNAME"
        (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
            --runs-dir "$W/runs/$RUNS/mc" --out-dir "$W/deliver/$OUTNAME/mc" --out-prefix smoke \
            --scratch-dir "$T/scratch_$OUTNAME" --smoke-test)
        rm -rf "$T/scratch_$OUTNAME"
    done
    echo "MODE=build done at $(date)"
    exit 0
fi

if [[ "$MODE" == "analyse" ]]; then
    # compare.py (studies/mcport_validation_20261014, unchanged) comes from the
    # NEW data code; the analysis script itself is the work-dir copy.
    unpack new_data
    mkdir -p "$W/evidence"
    python -u "$W/scripts/analyse.py" --repo "$T/repo" --work "$W" --out "$W/evidence"
    echo "MODE=analyse done at $(date)"
    exit 0
fi

echo "unknown MODE=$MODE" >&2
exit 1
