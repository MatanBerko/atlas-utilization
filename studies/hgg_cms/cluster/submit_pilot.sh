#!/bin/bash
# ---------------------------------------------------------------------------
# submit_pilot.sh
#
# Submits, together, everything that must pass BEFORE the full run is
# even considered:
#   1. D1/D2 -- exact reproduction of check_c_trigger_mimicking.py /
#      check_b_vertex.py, as a cluster job (pbs_hgg_d1d2_reproduce.sh).
#   2. D3 -- one full DoubleEG Run2016G file + one full ggH file, through
#      the real production configs, with the D3 analysis (cutflow,
#      efficiency, shape, plots, preview yield, timing) attached
#      (pbs_hgg_d3_data.sh / pbs_hgg_d3_signal.sh).
#   3. A SMALL PILOT of the full run itself: 2 DATA files (via the data
#      job array, indices 1-2 only) + 1 file per SIGNAL record (via
#      max_files_to_process:1 override configs, generated on the fly
#      here).
# None of this is the full run.
#
# DO NOT extend this to the full submission (pbs_hgg_data_array.sh's full
# -J 1-133, and pbs_hgg_signal.sh with max_files_to_process left unset)
# until: (a) D1/D2's acceptance criteria (pbs_hgg_d1d2_reproduce.sh's own
# comment header) are met or any difference has been root-caused and
# reported -- not forced into agreement; (b) D3's cutflow/efficiency/
# shape/timing numbers have been reviewed and used to replace the
# placeholder #PBS -l mem/walltime values in pbs_hgg_data_array.sh and
# pbs_hgg_signal.sh; (c) this pilot's jobs have all finished and their
# logs/outputs have been reviewed against
# studies/hgg_cms/cluster/PILOT_CHECKLIST.md; and (d) a human has
# explicitly decided to proceed. This script does NOT auto-continue to
# the full run -- it only submits these validation + pilot jobs and
# stops.
#
# This script itself does not run python/qsub in this repo's own CI or
# local-development context -- it is meant to be run BY HAND, on the
# cluster login node, after `git pull`-ing this branch there. It is not
# invoked by anything in this task's own local checks (see
# studies/hgg_cms/cluster/README.md's "local checks" section for what
# WAS actually run/verified without cluster access).
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="$HOME/atlas-utilization"
cd "$REPO_DIR"

LOG_BASE="/storage/agrp/berkom/atlas-utilization/logs"
mkdir -p "${LOG_BASE}/hgg_data" "${LOG_BASE}/hgg_signal" "${LOG_BASE}/hgg_signal_pilot" \
         "${LOG_BASE}/hgg_d1d2" "${LOG_BASE}/hgg_d3"

echo "=== Submitting D1/D2: exact reproduction of check_c/check_b on the cluster ==="
D1D2_JOBID=$(qsub studies/hgg_cms/cluster/pbs_hgg_d1d2_reproduce.sh)
echo "  $D1D2_JOBID"

echo "=== Submitting D3: one full DoubleEG file + one full ggH file ==="
D3_DATA_JOBID=$(qsub studies/hgg_cms/cluster/pbs_hgg_d3_data.sh)
echo "  data: $D3_DATA_JOBID"
D3_SIGNAL_JOBID=$(qsub studies/hgg_cms/cluster/pbs_hgg_d3_signal.sh)
echo "  signal: $D3_SIGNAL_JOBID"

echo "=== Submitting DATA pilot: 2 files (array indices 1-2) ==="
qsub -J 1-2 studies/hgg_cms/cluster/pbs_hgg_data_array.sh

echo "=== Submitting SIGNAL pilot: 1 file per record ==="
# A pilot-only config per record, generated here (NOT committed -- lives
# only in $TMPDIR on the submitting host) with max_files_to_process: 1,
# so the pilot touches exactly one file per production mode.
PILOT_CFG_DIR="${TMPDIR:-/tmp}/hgg_signal_pilot_configs"
mkdir -p "$PILOT_CFG_DIR"

declare -A SIGNAL_CONFIGS=(
    [ggh]=config.cms_hgg_signal_ggh.yaml
    [vbf]=config.cms_hgg_signal_vbf.yaml
    [wplush]=config.cms_hgg_signal_wplush.yaml
    [wminush]=config.cms_hgg_signal_wminush.yaml
    [zh]=config.cms_hgg_signal_zh.yaml
    [tth]=config.cms_hgg_signal_tth.yaml
)

for label in "${!SIGNAL_CONFIGS[@]}"; do
    base_config="${SIGNAL_CONFIGS[$label]}"
    pilot_config="${PILOT_CFG_DIR}/${base_config}.pilot.yaml"
    python - "$base_config" "$pilot_config" "$label" <<'PYEOF'
import sys
import yaml

base_path, out_path, label = sys.argv[1:4]
cfg = yaml.safe_load(open(base_path, encoding="utf-8"))
cfg["parsing_task_config"]["max_files_to_process"] = 1
cfg["run_metadata"]["run_name"] = f"cms_hgg_signal_{label}_pilot"
# base_output_dir is NOT set here -- pbs_hgg_signal.sh always passes
# --run-dir explicitly (derived from LABEL, e.g.
# .../output/cms_hgg_signal_ggh_pilot), which takes priority over
# run_metadata.base_output_dir in main.py, so setting it here would be
# dead/misleading configuration.
with open(out_path, "w", encoding="utf-8") as f:
    yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
PYEOF
    echo "  submitting $label (config=$pilot_config)"
    qsub -v CONFIG="$pilot_config",LABEL="${label}_pilot" studies/hgg_cms/cluster/pbs_hgg_signal.sh
done

echo ""
echo "Submitted: D1/D2 (1 job) + D3 (2 jobs: data, signal) + pilot (2 data array"
echo "jobs + 6 signal jobs, 1 file each)."
echo "Check status with: qstat -u \$USER"
echo "When ALL of the above finish, follow studies/hgg_cms/cluster/PILOT_CHECKLIST.md"
echo "(covers D1/D2's acceptance criteria, D3's numbers, and the pilot's own outputs)"
echo "before submitting the full run (studies/hgg_cms/cluster/submit_full.sh, NOT provided by"
echo "this task on purpose -- the full submission is a separate, explicit decision)."
