#!/usr/bin/env python
"""Full-production mappings for the 54 new samples (MC expansion, task A1 step 4).

A minimal ADDED variant of studies/cms_mc_weights_v3/fullrun_prep/make_fullrun_mappings.py (which
only knows the 13 records of the 17 Oct sweep). Since P1 option B (3 Nov 18:49) the MC driver
reads the COMPLETE list (fetch_file_list_complete: every index file of the record); the mapping lists
those files. The page-1 list (fetch_file_list, still used for data) is recorded for comparison. Found 3 Nov 2026: that page shows at most 5 index files, so for some records it is shorter
than the record's full file index (`_file_indices` of the record API), and for 69717 / 72761 the
portal's own index lists fewer files than `distribution.number_files`. This script therefore
records, per record, the page-1 list, the full index list and number_files; it STOPS only if the
page-1 list is not an exact prefix of the full index (then file indices would be ambiguous).
Writes one PBS mapping file per record ("<array_index> <record_id> <file_index>", 1-based,
contiguous -- the format cluster/pbs_mc_pilot.sh reads) and mappings/inputs_20261103.json.

    python studies/mc_expansion_20261103/make_mcexp_mappings.py
"""
from __future__ import annotations

import gzip
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
from studies.m0m1j0_cms.design_checks.common import fetch_file_list, fetch_file_list_complete  # noqa: E402
import requests  # noqa: E402

API = "https://opendata.cern.ch/api/records/{}"

REG = json.loads((REPO / "studies/cms_mc_weights_v3/cms_mc_normalisation_v4.json").read_text())["records"]
EV = REPO / "studies/cms_mc_weights_v3/sources/mcexp_20261103/records"
OUT = HERE / "mappings"


def main():
    new = sorted((int(r) for r, v in REG.items() if "decision_2026_11_03" in v and v["in_full_run"]),
                 key=lambda r: (REG[str(r)]["tier"], r))
    OUT.mkdir(exist_ok=True)
    inputs = {}
    for rid in new:
        with gzip.open(EV / f"{rid}.json.gz", "rt") as f:
            n_saved = json.load(f)["metadata"]["distribution"]["number_files"]
        page1 = fetch_file_list(rid)
        meta = requests.get(API.format(rid), timeout=60).json()["metadata"]
        urls = fetch_file_list_complete(rid)          # P1 option B (Matan, 3 Nov 18:49): what the MC driver now reads
        index = urls
        if page1 != urls[:len(page1)]:
            raise SystemExit(f"STOP: record {rid}: the page-1 list is not an exact prefix of the complete list")
        (OUT / f"mapping_{rid}.txt").write_text("".join(f"{i} {rid} {fi}\n" for i, fi in enumerate(range(len(urls)), 1)))
        inputs[str(rid)] = {"tier": REG[str(rid)]["tier"], "n_files": len(urls), "files": urls,
                            "n_files_page1": len(page1), "n_files_full_index": len(index),
                            "portal_number_files": meta["distribution"]["number_files"],
                            "saved_number_files": n_saved}
        flag = "" if len(page1) == len(urls) == n_saved else f"  <-- page 1 {len(page1)}, complete {len(urls)}, number_files {n_saved}"
        print(f"tier {REG[str(rid)]['tier']} {rid}: {len(urls)} files{flag}", flush=True)
    (OUT / "inputs_20261103.json").write_text(json.dumps(
        {"what": "portal file index of the 54 new samples, read live", "read": time.strftime("%Y-%m-%d %H:%M %Z"),
         "records": inputs}, indent=1) + "\n")
    per_tier = {}
    for v in inputs.values():
        per_tier[v["tier"]] = per_tier.get(v["tier"], 0) + v["n_files"]
    print("files per tier:", dict(sorted(per_tier.items())), "total", sum(per_tier.values()))


if __name__ == "__main__":
    main()
