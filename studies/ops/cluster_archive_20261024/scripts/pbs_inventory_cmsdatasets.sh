#!/bin/bash
# Phase 1, read-only: one level deeper under output/cms_datasets (inventory.walk).
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
set -euo pipefail
R="${REPORT_DIR:?}"
export HOME="${TMPDIR:-/tmp}/inv_home"; mkdir -p "$HOME"
export PYTHONDONTWRITEBYTECODE=1
/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python -u - "$R" <<"PY"
import json, os, sys
sys.path.insert(0, sys.argv[1])
import inventory as I
base = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets"
out = {}
for e in sorted(os.scandir(base), key=lambda e: e.name):
    if e.is_dir(follow_symlinks=False):
        out[e.name] = I.walk(e.path)
    else:
        s = e.stat(follow_symlinks=False)
        out[e.name] = {"inodes": 1, "files": 1, "bytes": s.st_size, "newest": "", "loose_file": True}
json.dump(out, open(sys.argv[1] + "/inventory_output_cms_datasets.json", "w"), indent=1)
print(sum(v["inodes"] for v in out.values()) + 1, "inodes incl. the folder")
PY
