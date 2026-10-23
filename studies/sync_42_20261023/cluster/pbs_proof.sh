#!/bin/bash
# Sync with upstream #39 #40 #42 (23 Oct 2026), step 4: real-file proof,
# OLD vs NEW code. Method of studies/sync_35_20261019/cluster/pbs_proof.sh.
#
# The six pinned commits are `git archive` tarballs in $WORK_DIR/code/
# (old_/new_ x master, data, mc). Each job unpacks the one it needs into
# node-local $TMPDIR/repo, so the code adds no files to /storage, and OLD and
# NEW run from the SAME path one after the other.
#
# MODE=perfile  array 0-8, one line of $WORK_DIR/mapping.txt each:
#               "<idx> <kind:master|data|mc> <dataset label> <record> <file_index>".
#               master: --population matched4 (master's own options, as in #35);
#               data:   --population matched5;
#               mc:     the pbs_mc_pilot.sh options (--is-mc ... --population matched4).
# MODE=build    one job: per side, the master four-dataset delivery
#               (DoubleMuon,DoubleEG), the data-branch five-dataset delivery
#               (DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron) and the
#               MC builder (all defaults, --smoke-test); then every comparison
#               into $WORK_DIR/evidence/ (compare.py / mc_compare.py unchanged,
#               from the NEW MC code; the data-runs wrapper from NEW master).
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

W="${WORK_DIR:?WORK_DIR not set}"
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
T="${TMPDIR:-/tmp}/sync42_${PBS_JOBID:-local}"
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
        case "$KIND" in
          master|data)
            POP=matched4; [[ "$KIND" == "data" ]] && POP=matched5
            OUT="$W/runs/$SIDE/$KIND/$LABEL/job_$FI"
            [[ -e "$OUT/job_metadata.json" ]] && { echo "exists, skipping: $OUT"; cd "$T"; continue; }
            mkdir -p "$OUT"
            python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
                --dataset-label "$LABEL" --record-id "$RID" --file-index "$FI" \
                --output-dir "$OUT" --population "$POP"
            ;;
          mc)
            OUT="$W/runs/$SIDE/mc/record$RID/job_$FI"
            [[ -e "$OUT/job_metadata.json" ]] && { echo "exists, skipping: $OUT"; cd "$T"; continue; }
            mkdir -p "$OUT"
            python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
                --is-mc --dataset-label MC --record-id "$RID" --file-index "$FI" \
                --output-dir "$OUT" --population matched4
            ;;
        esac
        cd "$T"
    done
    echo "MODE=perfile done idx=$IDX at $(date)"
    exit 0
fi

index() {  # index <runs dir> <label> <record>
    echo "{\"0\": {\"record_id\": $3, \"file_index\": 0}}" > "$1/$2_index.json"
}

if [[ "$MODE" == "build" ]]; then
    for SIDE in old new; do
        unpack "${SIDE}_master"
        D="$W/runs/$SIDE/master"
        index "$D" DoubleMuon 30522; index "$D" DoubleEG 30521
        (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_datasets/deliver/build_four_dataset_delivery.py \
            --runs-dir "$D" --out-dir "$W/deliver/$SIDE/master" --out-prefix proof \
            --datasets DoubleMuon,DoubleEG)
        unpack "${SIDE}_data"
        D="$W/runs/$SIDE/data"
        index "$D" DoubleMuon 30522; index "$D" SingleMuon 30530; index "$D" DoubleEG 30521
        index "$D" MuonEG 30528; index "$D" SingleElectron 30529
        (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_datasets/deliver/build_four_dataset_delivery.py \
            --runs-dir "$D" --out-dir "$W/deliver/$SIDE/data" --out-prefix proof \
            --datasets DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron)
        unpack "${SIDE}_mc"
        (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
            --runs-dir "$W/runs/$SIDE/mc" --out-dir "$W/deliver/$SIDE/mc" --out-prefix proof \
            --scratch-dir "$T/scratch" --smoke-test)
        rm -rf "$T/scratch"
    done
    unpack new_master
    cp "$T/repo/studies/sync_42_20261023/cluster/compare_data_runs.py" "$T/compare_data_runs.py"
    unpack new_mc
    C="$T/repo/studies/mcport_validation_20261014"
    E="$W/evidence"
    mkdir -p "$E"
    cd "$C"
    rc=0
    python -u "$T/compare_data_runs.py" --compare-dir "$C" --datasets DoubleMuon,DoubleEG \
        --a "$W/runs/old/master" --b "$W/runs/new/master" --out "$E/compare_master_runs.json" || rc=1
    python -u compare.py delivery --a "$W/deliver/old/master" --b "$W/deliver/new/master" \
        --a-runs "$W/runs/old/master" --b-runs "$W/runs/new/master" --prefix proof \
        --out "$E/compare_master_delivery.json" || rc=1
    python -u "$T/compare_data_runs.py" --compare-dir "$C" \
        --datasets DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron \
        --a "$W/runs/old/data" --b "$W/runs/new/data" --out "$E/compare_data_runs.json" || rc=1
    python -u compare.py delivery --a "$W/deliver/old/data" --b "$W/deliver/new/data" \
        --a-runs "$W/runs/old/data" --b-runs "$W/runs/new/data" --prefix proof \
        --out "$E/compare_data_delivery.json" || rc=1
    python -u mc_compare.py runs --a "$W/runs/old/mc" --b "$W/runs/new/mc" \
        --jobs 67801:0,72752:0 --out "$E/compare_mc_runs.json" || rc=1
    python -u mc_compare.py builds --a "$W/deliver/old/mc" --b "$W/deliver/new/mc" \
        --a-runs "$W/runs/old/mc" --b-runs "$W/runs/new/mc" \
        --a-scratch "$T/scratch" --b-scratch "$T/scratch" --out "$E/compare_mc_builds.json" || rc=1
    echo "MODE=build done at $(date) (comparison rc=$rc)"
    exit 0
fi

echo "unknown MODE=$MODE" >&2
exit 1
