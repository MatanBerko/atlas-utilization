#!/bin/bash
# ---------------------------------------------------------------------------
# submit_pilot.sh
#
# Submits a SMALL PILOT of the H->gamma-gamma cluster run: 2 DATA files
# (via the data job array, indices 1-2 only) + 1 file per SIGNAL record
# (via max_files_to_process:1 override configs, generated on the fly
# here) -- NOT the full run.
#
# DO NOT extend this to the full submission (pbs_hgg_data_array.sh's full
# -J 1-133, and pbs_hgg_signal.sh with max_files_to_process left unset)
# until this pilot's jobs have all finished, their logs and outputs have
# been reviewed against studies/hgg_cms/cluster/PILOT_CHECKLIST.md, and a
# human has explicitly decided to proceed. This script does NOT
# auto-continue to the full run -- it only submits the pilot and stops.
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
mkdir -p "${LOG_BASE}/hgg_data" "${LOG_BASE}/hgg_signal" "${LOG_BASE}/hgg_signal_pilot"

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
echo "Pilot submitted: 2 data jobs + 6 signal jobs (1 file each)."
echo "Check status with: qstat -u \$USER"
echo "When all pilot jobs finish, follow studies/hgg_cms/cluster/PILOT_CHECKLIST.md"
echo "before submitting the full run (studies/hgg_cms/cluster/submit_full.sh, NOT provided by"
echo "this task on purpose -- the full submission is a separate, explicit decision)."
