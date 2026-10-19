#!/bin/bash
# SingleElectron / b-tag re-check (19 Oct 2026). STUDY ONLY -- nothing in
# production changes; the b-tag threshold is changed only inside the job
# process by recheck/btag_override_run.py.
#
# MODE (env):
#   proof   run the driver NORMALLY and via the wrapper at 0.2598 on one data
#           file and one MC file (in $TMPDIR) and compare (compare_runs.py);
#           only the comparison JSONs are kept
#   se_a    Part 1A: the 7 Oct measure_singleelectron.py, UNCHANGED, on 10
#           SingleElectron files per subjob (PBS_ARRAY_INDEX*10 ...)
#   se_b    Part 1B: the same script via the wrapper at DeepJet 0.25
#   sample  Part 2: one sampled data/MC file per subjob, driver run twice in
#           $TMPDIR (0.2598, 0.25) with --debug-event-dump; keeps only
#           summary.json + nb.npz (merge_pair.py)
# Env: MODE, WORK_DIR, STUDY_REPO, MC_REPO (MC driver, full-run pin 294ee59),
#      SE_MAPPING (se_a/se_b), SAMPLE_MAPPING (sample)
# Resources are given with qsub -l; logs with qsub -j oe -o <log dir>.
#PBS -q N
#PBS -m n
#PBS -S /bin/bash

set -euo pipefail
MODE="${MODE:?}"; W="${WORK_DIR:?}"; SR="${STUDY_REPO:?}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
# Nothing is written to $HOME by this job.
export HOME="$W/.jobhome" MPLCONFIGDIR="$W/.mplconfig" XDG_CACHE_HOME="$W/.cache"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$HOME" "$MPLCONFIGDIR" "$XDG_CACHE_HOME"
export TMPDIR="${TMPDIR:-/tmp}"
JT=$(mktemp -d "$TMPDIR/serecheck_XXXXXX")
trap 'rm -rf "$JT"' EXIT

source /usr/wipp/conda/24.5.0/etc/profile.d/conda.sh
conda activate /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python
R="$SR/studies/cms_datasets/singleelectron_prep/recheck"
DRV=studies/cms_datasets/cluster/run_dataset_on_file.py
echo "MODE=$MODE job=${PBS_JOBID:-} idx=${PBS_ARRAY_INDEX:-} host=$(hostname) $(date)"
echo "study commit=$(git -C "$SR" rev-parse HEAD)  mc driver commit=$(git -C "${MC_REPO:-$SR}" rev-parse HEAD)"

case "$MODE" in
  proof)
    for which in data mc; do
      if [[ $which == data ]]; then repo=$SR; args=(--dataset-label DoubleMuon --record-id 30522 --file-index 0 --population matched4)
      else repo=${MC_REPO:?}; args=(--is-mc --dataset-label MC --record-id 35631 --file-index 0 --population matched4); fi
      out="$W/evidence/override_proof_${which}.json"
      test ! -e "$out"
      (cd "$repo" && /usr/bin/time -v "$PY" -u "$DRV" "${args[@]}" --output-dir "$JT/$which/normal")
      "$PY" -u "$R/btag_override_run.py" --target driver --btag-wp 0.2598 --driver-repo "$repo" \
          --capture-out "$JT/$which/cap.npz" -- "${args[@]}" --debug-event-dump --output-dir "$JT/$which/wrapped"
      "$PY" "$R/compare_runs.py" --normal "$JT/$which/normal" --wrapped "$JT/$which/wrapped" \
          --label "$which" --out "$out" || echo "PROOF FAILED for $which"
    done
    ;;
  se_a|se_b)
    IDX="${PBS_ARRAY_INDEX:?}"
    sub=$([[ $MODE == se_a ]] && echo a_0p2598 || echo b_0p25)
    mkdir -p "$W/se/$sub"
    for n in $(seq $((IDX*10)) $((IDX*10+9))); do
      LINE=$(sed -n "$((n+1))p" "${SE_MAPPING:?}"); [[ -z "$LINE" ]] && break
      read -r MAP_IDX ERA FI <<< "$LINE"
      [[ "$MAP_IDX" == "$n" ]] || { echo "bad mapping line $n" >&2; exit 1; }
      final="$W/se/$sub/tnp_${ERA}_${FI}.json"
      if [[ -e "$final" ]]; then echo "exists: $final"; continue; fi
      if [[ $MODE == se_a ]]; then
        (cd "$SR" && /usr/bin/time -v "$PY" -u studies/cms_datasets/singleelectron_prep/measure_singleelectron.py \
            --era "$ERA" --file-index "$FI" --out "$JT/t.json")
      else
        /usr/bin/time -v "$PY" -u "$R/btag_override_run.py" --target measure_se --btag-wp 0.25 --driver-repo "$SR" \
            -- --era "$ERA" --file-index "$FI" --out "$JT/t.json"
      fi
      mv "$JT/t.json" "$final"
    done
    ;;
  sample)
    IDX="${PBS_ARRAY_INDEX:?}"
    LINE=$(sed -n "$((IDX+1))p" "${SAMPLE_MAPPING:?}")
    read -r MAP_IDX KIND LABEL RID FI IX <<< "$LINE"
    [[ "$MAP_IDX" == "$IDX" ]] || { echo "bad mapping line $IDX" >&2; exit 1; }
    OUT="$W/sample/${LABEL}_${RID}/f${FI}"
    if [[ -e "$OUT/summary.json" ]]; then echo "exists: $OUT"; exit 0; fi
    if [[ $KIND == data ]]; then repo=$SR; args=(--dataset-label "$LABEL" --record-id "$RID" --file-index "$FI")
    else repo=${MC_REPO:?}; args=(--is-mc --dataset-label MC --record-id "$RID" --file-index "$FI"); fi
    args+=(--population matched4 --debug-event-dump)
    for wp in 0.2598 0.25; do
      tag=${wp/./p}
      /usr/bin/time -v "$PY" -u "$R/btag_override_run.py" --target driver --btag-wp "$wp" --driver-repo "$repo" \
          --capture-out "$JT/cap_$tag.npz" -- "${args[@]}" --output-dir "$JT/run_$tag"
      cp "$JT/run_$tag/job_metadata.json" "$JT/meta_$tag.json"
      rm -rf "$JT/run_$tag"
    done
    "$PY" "$R/merge_pair.py" --work "$JT" --out-dir "$OUT" --job "$LINE"
    ;;
  *) echo "unknown MODE=$MODE" >&2; exit 1 ;;
esac
echo "MODE=$MODE done $(date)"
