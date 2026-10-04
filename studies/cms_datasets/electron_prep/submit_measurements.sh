#!/bin/bash
# ---------------------------------------------------------------------------
# submit_measurements.sh (electron_prep)
#
# Builds the joblist and submits ONE PBS array over it, from a checkout
# pinned to a pushed commit (REPO_DIR), which must not be touched until all
# jobs finish.
#
# Sampling (deliberate, and stated in the spec/HANDOFF):
#   SingleMuon     40 files (20 G + 20 H, evenly spaced) -- Step 2 turn-on
#                  tag-and-probe. 26% of the 152 SingleMuon files, well above
#                  the 10% starting point in the brief: electrons are rare in
#                  muon-triggered events (a 14k-event pilot file yielded only
#                  6 probes), so the sample is raised up front to protect the
#                  "< 500 probes per pT bin below 60 GeV" requirement. If a bin
#                  is still short, extend with more indices in the same plan.
#   DoubleEG       16 files (8 G + 8 H)   -- Step 3 leg matching
#   MuonEG         16 files (8 G + 8 H)   -- Step 3 leg matching + Step 4 overlap
#   SingleElectron 16 files (8 G + 8 H)   -- Step 2 loss side + Step 4 overlap
#
# Usage:  REPO_DIR=<pinned repo> bash submit_measurements.sh
# ---------------------------------------------------------------------------
set -euo pipefail
export PATH=/opt/pbs/bin:$PATH

BASE=/storage/agrp/berkom/atlas-utilization/work/electron_prep
REPO_DIR="${REPO_DIR:-$BASE/pinned/repo}"
OUTPUT_DIR="${OUTPUT_DIR:-$BASE/measurements}"
LOGS=/storage/agrp/berkom/atlas-utilization/logs/electron_prep
mkdir -p "$OUTPUT_DIR" "$LOGS"

cd "$REPO_DIR"
echo "submitting from pinned checkout $REPO_DIR at commit $(git rev-parse HEAD)"

# Total file counts per (dataset, era), VERIFIED BY RUNNING against the
# portal file lists (see evidence/file_counts.json).
build_joblist() {
python - "$OUTPUT_DIR/joblist.txt" <<'PYEOF'
import sys
# (label, era, n_files_total, n_to_sample)
PLAN = [
    ("SingleMuon",     "G", 70, 20), ("SingleMuon",     "H", 82, 20),
    ("DoubleEG",       "G", 47,  8), ("DoubleEG",       "H", 86,  8),
    ("MuonEG",         "G", 29,  8), ("MuonEG",         "H", 19,  8),
    ("SingleElectron", "G", 71,  8), ("SingleElectron", "H", 80,  8),
]
rows = []
for label, era, n_total, n_take in PLAN:
    n_take = min(n_take, n_total)
    # Evenly spaced across the whole record, so the sample is not biased
    # toward whichever files happen to be first.
    idx = sorted({round(i * (n_total - 1) / max(n_take - 1, 1)) for i in range(n_take)})
    for i in idx:
        rows.append(f"{label} {era} {i}")
with open(sys.argv[1], "w") as fh:
    fh.write("\n".join(rows) + "\n")
print(f"{len(rows)} jobs")
PYEOF
}

source /usr/wipp/conda/24.5.0/etc/profile.d/conda.sh
conda activate /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
N=$(build_joblist | awk '{print $1}')
conda deactivate || true

echo "joblist: $OUTPUT_DIR/joblist.txt ($N jobs)"
LAST=$((N - 1))

JOBID=$(qsub -J "0-${LAST}" \
  -v "REPO_DIR=${REPO_DIR},JOBLIST=${OUTPUT_DIR}/joblist.txt,OUTPUT_DIR=${OUTPUT_DIR}" \
  -o "${LOGS}/meas_^array_index^.out" \
  -e "${LOGS}/meas_^array_index^.err" \
  studies/cms_datasets/electron_prep/pbs_measure.sh)
echo "electron_prep measurements ($N jobs): $JOBID"
echo "$JOBID" > "$OUTPUT_DIR/pbs_job_id.txt"
