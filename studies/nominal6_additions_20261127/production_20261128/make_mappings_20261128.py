#!/usr/bin/env python
"""Production file lists (mappings) of the Nominal-6 additions decided on 28 Nov 2026 (v9_decisions): 75561, 72648,
71636, 71640, 74314, plus the WZjj replacement if evidence/wzjj/wzjj_outcome.json names one.

Same method as studies/mc_expansion_20261103/make_d15_mappings.py: the MC driver reads the COMPLETE list
(fetch_file_list_complete at the production pin 6de9d3e: every index file of the record), so the mapping lists those
files; the page-1 list is recorded and must be an exact prefix of it. A record whose complete list is shorter than the
portal's distribution.number_files has files the portal lists but does not publish (as 69717 / 72761): flagged, not
stopped.

Writes production_20261128/mappings/mapping_<rid>.txt ("<array_index> <record_id> <file_index>", 1-based,
contiguous; one PBS array per record) and production_20261128/mappings/inputs_20261128.json.

    python production_20261128/make_mappings_20261128.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
from studies.m0m1j0_cms.design_checks.common import fetch_file_list, fetch_file_list_complete  # noqa: E402
import requests  # noqa: E402

API = "https://opendata.cern.ch/api/records/{}"
RECORDS = {  # item: NanoAOD records (v9_decisions_2026-11-28)
    "N1": [75561, 72648, 71636],
    "N2": [71640],
    "N4": [74314],
}
_wz = json.loads((HERE / "evidence" / "wzjj" / "wzjj_outcome.json").read_text())
if _wz.get("replacement_nano_recid"):
    RECORDS["N1-WZ"] = [int(_wz["replacement_nano_recid"])]
OUT = HERE / "production_20261128" / "mappings"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = {}
    for item, rids in RECORDS.items():
        for rid in rids:
            if (OUT / f"mapping_{rid}.txt").exists():
                raise SystemExit(f"STOP: mapping_{rid}.txt already exists")
            page1 = fetch_file_list(rid)
            meta = requests.get(API.format(rid), timeout=60).json()["metadata"]
            urls = fetch_file_list_complete(rid)
            if page1 != urls[:len(page1)]:
                raise SystemExit(f"STOP: record {rid}: the page-1 list is not an exact prefix of the complete list")
            n_portal = meta["distribution"]["number_files"]
            (OUT / f"mapping_{rid}.txt").write_text("".join(f"{i} {rid} {fi}\n" for i, fi in enumerate(range(len(urls)), 1)))
            sizes = [f.get("size") for f in meta.get("files", [])]
            inputs[str(rid)] = {"item": item, "title": meta.get("title"), "n_files": len(urls), "files": urls,
                                "n_files_page1": len(page1), "n_index_files": len(meta.get("_file_indices", [])),
                                "portal_number_files": n_portal,
                                "portal_number_events": meta["distribution"].get("number_events"),
                                "portal_size_bytes": meta["distribution"].get("size"),
                                "unpublished_files": n_portal - len(urls)}
            flag = "" if len(urls) == n_portal else f"  <-- {n_portal - len(urls)} files listed by the portal but not published"
            print(f"{item} {rid}: {len(urls)} files (page 1: {len(page1)}), "
                  f"{inputs[str(rid)]['portal_number_events']} events{flag}", flush=True)
    (OUT / "inputs_20261128.json").write_text(json.dumps(
        {"what": "portal file index of the Nominal-6 production records, read live (fetch_file_list_complete, pin 6de9d3e)",
         "read": time.strftime("%Y-%m-%d %H:%M %Z"), "records": inputs}, indent=1) + "\n")
    print("total files:", sum(v["n_files"] for v in inputs.values()),
          "events:", sum(v["portal_number_events"] or 0 for v in inputs.values()))


if __name__ == "__main__":
    main()
