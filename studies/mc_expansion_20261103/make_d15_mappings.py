#!/usr/bin/env python
"""Full-production mappings for the 4 rare-top samples released by D15 (Matan, 7 Nov 2026).

An ADDED sibling of make_mcexp_mappings.py, which only maps the records that were in the full run on
3 Nov: 68325 tZq_ll, 64873 ST_tWll, 68206 TTZToQQ, 68185 TTZToLL_M-1to10 were ON HOLD then.
Same method: the MC driver reads the COMPLETE list (fetch_file_list_complete, every index file of the
record, P1 option B), so the mapping lists those files; the page-1 list is recorded for comparison and
must be an exact prefix of it. A record whose complete list is shorter than the portal's
distribution.number_files has files the portal lists but does not publish (as 69717 / 72761); this is
flagged, not stopped.

Writes mappings/mapping_<rid>.txt ("<array_index> <record_id> <file_index>", 1-based, contiguous) and
mappings/inputs_D15_20261107.json.

    python studies/mc_expansion_20261103/make_d15_mappings.py
"""
from __future__ import annotations

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
D15 = [68325, 64873, 68206, 68185]
OUT = HERE / "mappings"


def main():
    inputs = {}
    for rid in D15:
        if (OUT / f"mapping_{rid}.txt").exists():
            raise SystemExit(f"STOP: mapping_{rid}.txt already exists")
        page1 = fetch_file_list(rid)
        meta = requests.get(API.format(rid), timeout=60).json()["metadata"]
        urls = fetch_file_list_complete(rid)
        if page1 != urls[:len(page1)]:
            raise SystemExit(f"STOP: record {rid}: the page-1 list is not an exact prefix of the complete list")
        n_portal = meta["distribution"]["number_files"]
        (OUT / f"mapping_{rid}.txt").write_text("".join(f"{i} {rid} {fi}\n" for i, fi in enumerate(range(len(urls)), 1)))
        inputs[str(rid)] = {"tier": 4, "title": meta.get("title"), "n_files": len(urls), "files": urls,
                            "n_files_page1": len(page1), "n_index_files": len(meta.get("_file_indices", [])),
                            "portal_number_files": n_portal,
                            "portal_number_events": meta["distribution"].get("number_events"),
                            "portal_size_bytes": meta["distribution"].get("size"),
                            "unpublished_files": n_portal - len(urls)}
        flag = "" if len(urls) == n_portal else f"  <-- {n_portal - len(urls)} files listed by the portal but not published"
        print(f"{rid}: {len(urls)} files (page 1: {len(page1)}), {inputs[str(rid)]['portal_number_events']} events{flag}",
              flush=True)
    (OUT / "inputs_D15_20261107.json").write_text(json.dumps(
        {"what": "portal file index of the 4 D15 rare-top samples, read live", "read": time.strftime("%Y-%m-%d %H:%M %Z"),
         "records": inputs}, indent=1) + "\n")
    print("total files:", sum(v["n_files"] for v in inputs.values()),
          "events:", sum(v["portal_number_events"] or 0 for v in inputs.values()))


if __name__ == "__main__":
    main()
