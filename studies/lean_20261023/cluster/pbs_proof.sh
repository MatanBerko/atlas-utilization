#!/bin/bash
# Lean-branch proof (23 Oct 2026), step 5: real-file proof, OLD vs NEW code.
# Method of studies/sync_42_20261023/cluster/pbs_proof.sh (master 8aa6960).
#
#   OLD = feature/cms-mc-multiplicity40-20261023 @ de012d2  ($CO/old.tar)
#   NEW = lean/cms-layer-20261023 tip                        ($CO/new.tar)
#   tools = study/lean-branch-proof-20261023 (this script, compare_data_runs.py,
#           precheck_capped.py)                              ($CO/tools.tar)
# All three are `git archive` tarballs. Each job unpacks the one it needs into
# node-local $TMPDIR/repo, so OLD and NEW run from the SAME path one after
# the other, and the code adds no files to /storage.
#
# MODE=perfile  array 0-6, one line of $WORK_DIR/mapping.txt each:
#               "<idx> <kind:data|mc> <dataset label> <record> <file_index>".
#               data: --population matched5; mc: the pbs_mc_pilot.sh options
#               (--is-mc --dataset-label MC ... --population matched4).
# MODE=build    one job: per side, the five-dataset matched5 delivery (default
#               rule, upstream40) and the MC builder (defaults, --smoke-test);
#               then every comparison into $WORK_DIR/evidence/ (compare.py /
#               mc_compare.py unchanged, from the OLD tarball's
#               studies/mcport_validation_20261014; the data-runs wrapper from tools).
# MODE=precheck the read-only full-run pre-check (precheck_capped.py, tools).
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail

W="${WORK_DIR:?WORK_DIR not set}"
CO="${CHECKOUTS:?CHECKOUTS not set}"
B=/storage/agrp/berkom/atlas-utilization
FIVE=DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron
CONDA_PROFILE="/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh"
CONDA_ENV="$B/envs/atlas-pipeline"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
T="${TMPDIR:-/tmp}/lean_${PBS_JOBID:-local}"
mkdir -p "$T"
trap 'rm -rf "$T"' EXIT
# Nothing is written to $HOME by this job.
export HOME="$T/home" MPLCONFIGDIR="$T/mpl" XDG_CACHE_HOME="$T/cache"
mkdir -p "$HOME" "$MPLCONFIGDIR" "$XDG_CACHE_HOME"
source "$CONDA_PROFILE"
conda activate "$CONDA_ENV"

unpack() {  # unpack <tar name> <dir>
    rm -rf "$2"
    mkdir -p "$2"
    tar -xf "$CO/$1.tar" -C "$2"
    echo "code $1: commit $(git get-tar-commit-id < "$CO/$1.tar") sha256 $(sha256sum "$CO/$1.tar" | cut -c1-16)"
}

echo "MODE=${MODE} on $(hostname) at $(date)"

if [[ "$MODE" == "perfile" ]]; then
    IDX="${PBS_ARRAY_INDEX:?}"
    read -r MI KIND LABEL RID FI <<< "$(sed -n "$((IDX + 1))p" "$W/mapping.txt")"
    [[ "$MI" == "$IDX" ]] || { echo "mapping line mismatch: $MI != $IDX" >&2; exit 1; }
    for SIDE in old new; do
        unpack "$SIDE" "$T/repo"
        cd "$T/repo"
        case "$KIND" in
          data)
            OUT="$W/runs/$SIDE/data/$LABEL/job_$FI"
            test ! -e "$OUT/job_metadata.json"
            mkdir -p "$OUT"
            python -u studies/cms_datasets/cluster/run_dataset_on_file.py \
                --dataset-label "$LABEL" --record-id "$RID" --file-index "$FI" \
                --output-dir "$OUT" --population matched5
            ;;
          mc)
            OUT="$W/runs/$SIDE/mc/record$RID/job_$FI"
            test ! -e "$OUT/job_metadata.json"
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
        unpack "$SIDE" "$T/repo"
        D="$W/runs/$SIDE/data"
        index "$D" DoubleMuon 30522; index "$D" SingleMuon 30530; index "$D" DoubleEG 30521
        index "$D" MuonEG 30528; index "$D" SingleElectron 30529
        test ! -e "$W/deliver/$SIDE"
        (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_datasets/deliver/build_four_dataset_delivery.py \
            --runs-dir "$D" --out-dir "$W/deliver/$SIDE/data" --out-prefix proof --datasets "$FIVE")
        (cd "$T/repo" && TMPDIR="$T" python -u studies/cms_mc_weights_v3/deliver/build_mc_delivery.py \
            --runs-dir "$W/runs/$SIDE/mc" --out-dir "$W/deliver/$SIDE/mc" --out-prefix proof \
            --scratch-dir "$T/scratch" --smoke-test)
        rm -rf "$T/scratch"
    done
    unpack tools "$T/tools"
    unpack old "$T/repo"
    C="$T/repo/studies/mcport_validation_20261014"
    E="$W/evidence"
    mkdir -p "$E"
    cd "$C"
    rc=0
    python -u "$T/tools/studies/lean_20261023/cluster/compare_data_runs.py" --compare-dir "$C" \
        --datasets "$FIVE" --a "$W/runs/old/data" --b "$W/runs/new/data" \
        --out "$E/compare_data_runs.json" || rc=1
    python -u compare.py delivery --a "$W/deliver/old/data" --b "$W/deliver/new/data" \
        --a-runs "$W/runs/old/data" --b-runs "$W/runs/new/data" --prefix proof \
        --out "$E/compare_data_delivery.json" || rc=1
    python -u mc_compare.py runs --a "$W/runs/old/mc" --b "$W/runs/new/mc" \
        --jobs 67801:0,72752:0 --out "$E/compare_mc_runs.json" || rc=1
    python -u mc_compare.py builds --a "$W/deliver/old/mc" --b "$W/deliver/new/mc" \
        --a-runs "$W/runs/old/mc" --b-runs "$W/runs/new/mc" \
        --a-scratch "$T/scratch" --b-scratch "$T/scratch" --out "$E/compare_mc_builds.json" || rc=1
    echo "MODE=build done at $(date) (comparison rc=$rc)"
    exit $rc
fi

if [[ "$MODE" == "precheck" ]]; then
    unpack tools "$T/tools"
    mkdir -p "$W/evidence"
    cd "$T/tools"
    python -u studies/lean_20261023/precheck_capped.py \
        --data-runs "$B/output/cms_datasets/runs_matched4_full_20261007" \
        --mc-runs "$B/work/fullrun_20261017/runs" \
        --out "$W/evidence/precheck_capped.json"
    exit 0
fi

echo "unknown MODE=$MODE" >&2
exit 1
