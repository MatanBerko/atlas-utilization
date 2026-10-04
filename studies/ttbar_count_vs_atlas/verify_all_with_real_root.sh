#!/bin/bash
# ---------------------------------------------------------------------------
# verify_all_with_real_root.sh (ttbar_count_vs_atlas, Step 6)
#
# Reads back EVERY ROOT file this study writes using REAL PyROOT from a
# CVMFS LCG view -- not uproot, which is what wrote them. Runs the existing,
# unmodified studies/cms_datasets/deliver/verify_with_real_root.py once per
# (uncropped, cropped) pair: 3 variants x 3 bin thresholds = 9 pairs = 18 files.
#
#   bash verify_all_with_real_root.sh <study-dir>
# ---------------------------------------------------------------------------
set -euo pipefail

STUDY_DIR="${1:?usage: verify_all_with_real_root.sh <study-dir>}"
REPO_DIR="${REPO_DIR:-$(pwd)}"
LCG_VIEW="${LCG_VIEW:-/cvmfs/sft.cern.ch/lcg/views/LCG_110/x86_64-el9-gcc13-opt}"

# shellcheck disable=SC1091
source "$LCG_VIEW/setup.sh"
cd "$REPO_DIR"

n_pairs=0
for VARIANT in rare4 pr31 pr31_noOR; do
  for TAG in ge25bins min26bins min31bins; do
    BASE="$STUDY_DIR/$VARIANT/ttbar_notrigger_${VARIANT}_${TAG}"
    echo "=== $VARIANT / $TAG ==="
    python3 studies/cms_datasets/deliver/verify_with_real_root.py \
        --uncropped "${BASE}.root" \
        --cropped   "${BASE}_cropped.root" \
        --out-json  "$STUDY_DIR/$VARIANT/real_root_verify_${TAG}.json"
    n_pairs=$((n_pairs + 1))
  done
done
echo
echo "all $n_pairs (uncropped, cropped) pairs verified with real ROOT -- $((n_pairs * 2)) files"
