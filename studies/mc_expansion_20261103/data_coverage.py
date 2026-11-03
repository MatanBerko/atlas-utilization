#!/usr/bin/env python
"""Data coverage check (A2 step 2, 3 Nov 2026). READ-ONLY: no data code or output is changed.

For each data record of the five delivered datasets (Run2016G and H), compare
  * the files the 25 Oct data production used: studies/fullrun_20261025/evidence/mappings_data/<Dataset>_mapping.txt
    (lines "<job> <dataset> <record> <file_index> <job>"; byte copies of work/fullrun_20261025/mappings_data/),
    and, if given (--full-files), the URL list the mapping generator wrote at the time (full_files.json);
  * the portal file page 1 (fetch_file_list, what the data driver reads) -- live;
  * the record's complete index (fetch_file_list_complete) and number_files / number_events / size -- live.
Writes evidence/data_coverage.json and prints a table. Run: python studies/mc_expansion_20261103/data_coverage.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import defaultdict

import requests

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
from studies.m0m1j0_cms.design_checks.common import fetch_file_list, fetch_file_list_complete  # noqa: E402

MAPS = REPO / "studies/fullrun_20261025/evidence/mappings_data"
API = "https://opendata.cern.ch/api/records/{}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full-files", default=None, help="full_files.json of the 25 Oct data mappings (URLs used)")
    a = ap.parse_args()
    used = defaultdict(set)
    ds_of = {}
    for m in sorted(MAPS.glob("*_mapping.txt")):
        for line in m.read_text().split("\n"):
            if not line.strip():
                continue
            _job, ds, rec, fi, _ = line.split()
            used[int(rec)].add(int(fi))
            ds_of[int(rec)] = ds
    urls_used = {}
    if a.full_files:
        for f in json.loads(pathlib.Path(a.full_files).read_text())["files"]:
            urls_used.setdefault(int(f["record_id"]), {})[int(f["file_index"])] = f["url"]
    out = {}
    for rec in sorted(used):
        page1 = fetch_file_list(rec)
        full = fetch_file_list_complete(rec)
        meta = requests.get(API.format(rec), timeout=60).json()["metadata"]
        d = meta["distribution"]
        size = {f["uri"]: f["size"] for x in meta["_file_indices"] for f in x.get("files", [])}
        idx = sorted(used[rec])
        used_urls = [page1[i] for i in idx if i < len(page1)]
        missing = [u for u in full if u not in set(used_urls)]
        miss_bytes = sum(size.get(u, 0) for u in missing)
        r = {"dataset": ds_of[rec], "files_used_25oct": len(idx), "indices_contiguous_from_0": idx == list(range(len(idx))),
             "files_page1_now": len(page1), "files_complete_index": len(full), "portal_number_files": d.get("number_files"),
             "page1_prefix_of_complete": full[:len(page1)] == page1,
             "missing_vs_complete_index": len(missing), "missing_files": missing,
             "missing_bytes_fraction": miss_bytes / d["size"] if d.get("size") else None,
             "unpublished_vs_number_files": (d.get("number_files") or 0) - len(full)}
        if rec in urls_used:
            r["urls_25oct_equal_page1_now"] = [urls_used[rec][i] for i in idx] == used_urls
        out[str(rec)] = r
        print(f"{rec} {ds_of[rec]:14s} used {len(idx):4d}  page1 {len(page1):4d}  complete {len(full):4d}  "
              f"number_files {d.get('number_files')}  missing {len(missing)}"
              + (f" ({r['missing_bytes_fraction']:.1%} of bytes)" if missing else "")
              + (f"  25Oct URLs == page1 now: {r.get('urls_25oct_equal_page1_now')}" if rec in urls_used else ""))
    (HERE / "evidence" / "data_coverage.json").write_text(json.dumps(out, indent=1) + "\n")
    print("ANY MISSING:", any(v["missing_vs_complete_index"] for v in out.values()))


if __name__ == "__main__":
    main()
