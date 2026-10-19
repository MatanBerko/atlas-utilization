#!/bin/bash
# Sync with upstream #35, step B: real-file proof, OLD vs NEW code.
#
# The four pinned commits are `git archive` tarballs in $WORK_DIR/code/
# (old_data = master 45a7e06, new_data = sync/upstream-35-20261019,
# old_mc = feature/cms-mc-peakfix-20261018 24ecb7c, new_mc =
# sync/mc-upstream-35-20261020). Each job unpacks the one it needs into
# node-local $TMPDIR/repo, so the code adds no files to /storage, and OLD and
# NEW run from the SAME path one after the other (any path a program records
# is then identical on both sides).
#
# MODE=perfile  array 0-3, one line of $WORK_DIR/mapping.txt each:
#               "<idx> <kind:data|mc> <dataset label> <record> <file_index>".
#               Runs the per-file driver with the 7 Oct options (data) or the
#               pbs_mc_pilot.sh options (MC), OLD then NEW.
# MODE=build    one job: the data delivery builder and the MC builder
#               (defaults: --peak-scope combined; --smoke-test) on each side,
#               then every comparison into $WORK_DIR/evidence/.
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

W="${WORK_DIR:?WORK_DIR not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
T="${TMPDIR:-/tmp}/sync35b_${PBS_JOBID:-local}"
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

echo "MODE=${MODE} on $(hostname) at $(date)"

if [[ "$MODE" == "perfile" ]]; then
    IDX="${PBS_ARRAY_INDEX:?}"
    read -r MI KIND LABEL RID FI <<< "$(sed -n "$((IDX + 1))p" "$W/mapping.txt")"
    [[ "$MI" == "$IDX" ]] || { echo "mapping line mismatch: $MI != $IDX" >&2; exit 1; }
    for SIDE in old new; do
        unpack "${SIDE}_${KIND}"
        cd "$T/repo"
        if [[ "$KIND" == "data" ]]; then
            OUT="$W/runs/$SIDE/data/$LABEL/job_$FI"
            [[ -e "$OUT/job_metadata.json" ]] && { echo "exists, skipping: $OUT"; continue; }
            mkdir -p "$OUT"
            python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
                --dataset-label "$LABEL" --record-id "$RID" --file-index "$FI" \
                --output-dir "$OUT" --population matched4
        else
            OUT="$W/runs/$SIDE/mc/record$RID/job_$FI"
            [[ -e "$OUT/job_metadata.json" ]] && { echo "exists, skipping: $OUT"; continue; }
            mkdir -p "$OUT"
            python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
                --is-mc --dataset-label MC --record-id "$RID" --file-index "$FI" \
                --output-dir "$OUT" --population matched4
        fi
        cd "$T"
    done
    echo "MODE=perfile done idx=$IDX at $(date)"
    exit 0
fi

if [[ "$MODE" == "build" ]]; then
    for SIDE in old new; do
        unpack "${SIDE}_data"
        D="$W/runs/$SIDE/data"
        echo '{"0": {"record_id": 30522, "file_index": 0}}' > "$D/DoubleMuon_index.json"
        echo '{"0": {"record_id": 30521, "file_index": 0}}' > "$D/DoubleEG_index.json"
        (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_datasets/deliver/build_four_dataset_delivery.py \
            --runs-dir "$D" --out-dir "$W/deliver/$SIDE/data" --out-prefix proof \
            --datasets DoubleMuon,DoubleEG)
        unpack "${SIDE}_mc"
        (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
            --runs-dir "$W/runs/$SIDE/mc" --out-dir "$W/deliver/$SIDE/mc" --out-prefix proof \
            --scratch-dir "$T/scratch" --smoke-test)
        rm -rf "$T/scratch"
    done
    # The comparison scripts (mcport_validation compare.py / mc_compare.py,
    # unchanged) and this task's wrapper come from the NEW MC code.
    unpack new_mc
    C="$T/repo/studies/mcport_validation_20261014"
    E="$W/evidence"
    mkdir -p "$E"
    cd "$C"
    python -u "$T/repo/studies/sync_35_20261019/cluster/compare_data_runs.py" --compare-dir "$C" \
        --a "$W/runs/old/data" --b "$W/runs/new/data" --out "$E/compare_data_runs.json"
    python -u compare.py delivery --a "$W/deliver/old/data" --b "$W/deliver/new/data" \
        --a-runs "$W/runs/old/data" --b-runs "$W/runs/new/data" --prefix proof \
        --out "$E/compare_data_delivery.json"
    python -u mc_compare.py runs --a "$W/runs/old/mc" --b "$W/runs/new/mc" \
        --jobs 67801:0,72752:0 --out "$E/compare_mc_runs.json"
    python -u mc_compare.py builds --a "$W/deliver/old/mc" --b "$W/deliver/new/mc" \
        --a-runs "$W/runs/old/mc" --b-runs "$W/runs/new/mc" \
        --a-scratch "$T/scratch" --b-scratch "$T/scratch" --out "$E/compare_mc_builds.json"
    echo "MODE=build done at $(date)"
    exit 0
fi

echo "unknown MODE=$MODE" >&2
exit 1
