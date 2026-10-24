#!/bin/bash
# Full run 25 Oct 2026, step 3: small real-file check, OLD (lean 33d77f5:
# Muon_mediumId, electron cutBased >= 3) vs NEW (this branch: Muon_looseId,
# cutBased >= 2). Method of studies/sync_42_20261023/cluster/pbs_proof.sh
# (on master): each side is a `git archive` tarball in $WORK_DIR/code/
# (old.tar, new.tar), unpacked into node-local $TMPDIR/repo, so OLD and NEW
# run from the SAME path, one after the other, in the same job.
#
# MODE=perfile  array 0-6, one line of $WORK_DIR/mapping.txt each:
#               "<idx> <kind:data|mc> <dataset label> <record> <file_index>".
#               data: --population matched5, and once more with
#                     --no-emu-overlap-removal (only to count the events the
#                     overlap removal costs; never built);
#               mc:   the pbs_mc_pilot.sh options (--is-mc --dataset-label MC
#                     --population matched4).
#               Then object_compare.py (NEW code, OLD selection.py copy).
# MODE=build    one job: per side, the matched5 data delivery build
#               (build_four_dataset_delivery.py --datasets <five>, defaults)
#               and the MC smoke build (build_mc_delivery.py --smoke-test,
#               defaults); then build_compare.py into $WORK_DIR/evidence/.
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

W="${WORK_DIR:?WORK_DIR not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
T="${TMPDIR:-/tmp}/fr25pre_${PBS_JOBID:-local}"
mkdir -p "$T"
trap 'rm -rf "$T"' EXIT
# Nothing is written to $HOME by this job.
export HOME="$T/home" MPLCONFIGDIR="$T/mpl" XDG_CACHE_HOME="$T/cache"
mkdir -p "$HOME" "$MPLCONFIGDIR" "$XDG_CACHE_HOME"
source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

unpack() {  # unpack <old|new> -> $T/repo
    rm -rf "$T/repo"
    mkdir -p "$T/repo"
    tar -xf "$W/code/$1.tar" -C "$T/repo"
    echo "code $1: commit $(git get-tar-commit-id < "$W/code/$1.tar") sha256 $(sha256sum "$W/code/$1.tar" | cut -c1-16)"
}

echo "MODE=${MODE} on $(hostname) at $(date)"

if [[ "$MODE" == "perfile" ]]; then
    IDX="${PBS_ARRAY_INDEX:?}"
    read -r MI KIND LABEL RID FI <<< "$(sed -n "$((IDX + 1))p" "$W/mapping.txt")"
    [[ "$MI" == "$IDX" ]] || { echo "mapping line mismatch: $MI != $IDX" >&2; exit 1; }
    for SIDE in old new; do
        unpack "$SIDE"
        cd "$T/repo"
        [[ "$SIDE" == "old" ]] && cp studies/m0m1j0_cms/selection.py "$T/old_selection.py"
        case "$KIND" in
          data)
            for OR in on off; do
                if [[ "$OR" == "on" ]]; then
                    OUT="$W/runs/$SIDE/data/$LABEL/job_$FI"; EXTRA=""
                else
                    OUT="$W/runs/$SIDE/data_noor/$LABEL/job_$FI"; EXTRA="--no-emu-overlap-removal"
                fi
                [[ -e "$OUT/job_metadata.json" ]] && { echo "exists, skipping: $OUT"; continue; }
                mkdir -p "$OUT"
                python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
                    --dataset-label "$LABEL" --record-id "$RID" --file-index "$FI" \
                    --output-dir "$OUT" --population matched5 $EXTRA
            done
            ;;
          mc)
            OUT="$W/runs/$SIDE/mc/record$RID/job_$FI"
            if [[ -e "$OUT/job_metadata.json" ]]; then
                echo "exists, skipping: $OUT"
            else
                mkdir -p "$OUT"
                python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
                    --is-mc --dataset-label MC --record-id "$RID" --file-index "$FI" \
                    --output-dir "$OUT" --population matched4
            fi
            ;;
        esac
        cd "$T"
    done
    # NEW code is unpacked now; OLD selection.py was copied above.
    mkdir -p "$W/evidence/objects"
    MCFLAG=""; [[ "$KIND" == "mc" ]] && MCFLAG="--is-mc"
    NAME="$LABEL"; [[ "$KIND" == "mc" ]] && NAME="MC_$RID"
    (cd "$T/repo" && python -u studies/fullrun_20261025/cluster/object_compare.py \
        --label "$LABEL" --record "$RID" --file-index "$FI" \
        --old-selection "$T/old_selection.py" --out "$W/evidence/objects/$NAME.json" $MCFLAG)
    echo "MODE=perfile done idx=$IDX at $(date)"
    exit 0
fi

index() {  # index <runs dir> <label> <record>
    echo "{\"0\": {\"record_id\": $3, \"file_index\": 0}}" > "$1/$2_index.json"
}

if [[ "$MODE" == "build" ]]; then
    for SIDE in old new; do
        unpack "$SIDE"
        D="$W/runs/$SIDE/data"
        index "$D" DoubleMuon 30522; index "$D" SingleMuon 30530; index "$D" DoubleEG 30521
        index "$D" MuonEG 30528; index "$D" SingleElectron 30529
        (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_datasets/deliver/build_four_dataset_delivery.py \
            --runs-dir "$D" --out-dir "$W/deliver/$SIDE/data" --out-prefix precheck \
            --datasets DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron)
        (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
            --runs-dir "$W/runs/$SIDE/mc" --out-dir "$W/deliver/$SIDE/mc" --out-prefix precheck \
            --scratch-dir "$T/scratch" --smoke-test)
        rm -rf "$T/scratch"
    done
    unpack new
    mkdir -p "$W/evidence"
    (cd "$T/repo" && python -u studies/fullrun_20261025/cluster/build_compare.py \
        --work "$W" --out "$W/evidence/build_compare.json")
    echo "MODE=build done at $(date)"
    exit 0
fi

echo "unknown MODE=$MODE" >&2
exit 1
