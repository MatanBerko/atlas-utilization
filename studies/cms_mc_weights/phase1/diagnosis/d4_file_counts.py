#!/usr/bin/env python
"""D4 preflight: report the file count for every requested Tier-1 sample
before submitting anything, per the task's own instruction."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

SAMPLES = {
    "64895": "ST_tW_top_5f_NoFullyHadronicDecays",
    "64839": "ST_tW_antitop_5f_NoFullyHadronicDecays",
    "72676": "WWTo2L2Nu",
    "72752": "WZTo3LNu_amcatnloFXFX",
    "75589": "ZZTo4L",
    "68187": "TTZToLLNuNu_M-10",
    "68073": "TTWJetsToLNu",
    "67993": "TTToSemiLeptonic",
    "35669": "DYJetsToLL_M-50_amcatnloFXFX",
}

out = {}
total = 0
for rid, name in SAMPLES.items():
    urls = fetch_file_list(int(rid))
    out[rid] = {"name": name, "n_files": len(urls)}
    total += len(urls)
    print(f"{rid} {name}: {len(urls)} files", flush=True)

out["_total_all_9_samples"] = total
out["_total_excl_ttsemilep"] = total - out["67993"]["n_files"]
print(json.dumps(out, indent=2))
Path("studies/cms_mc_weights/phase1/diagnosis/d4_file_counts.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8"
)
