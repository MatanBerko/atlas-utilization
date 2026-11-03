#!/usr/bin/env python
"""Planning numbers for the full production of the 54 new samples (task A1 step 4). Local, read-only.

Inputs:
  * mappings/inputs_20261103.json      -- the files the unchanged driver can reach (page-1 list)
  * the record API (live): per-file sizes, number_events, size of every record
  * evidence/precheck/precheck_report.json -- file 0 of every sample, run on 3 Nov (PBS 5433276[]):
        CPU seconds per event read, stored events per event read
  * evidence/precheck/files_per_job.json   -- measured cluster files per job (outputs + 2 logs)
Estimates (labelled ESTIMATE): events in a file = file size x number_events / record size;
CPU of a file = its events x (file-0 elapsed / file-0 events read). Writes evidence/full_production_plan.json.
"""
from __future__ import annotations

import json
import pathlib

import requests

HERE = pathlib.Path(__file__).resolve().parent
API = "https://opendata.cern.ch/api/records/{}"
WALL = {2: "02:00:00", 3: "03:00:00"}
BUILD_FILES_PER_SAMPLE = 2240 / 13      # 17 Oct MC build + post incl. kept scratch (PLAN §4)


def main():
    inp = json.loads((HERE / "mappings" / "inputs_20261103.json").read_text())["records"]
    pre = json.loads((HERE / "evidence" / "precheck" / "precheck_report.json").read_text())["samples"]
    fpj = json.loads((HERE / "evidence" / "precheck" / "files_per_job.json").read_text())
    per_job_files = fpj["median_files_per_job_incl_logs"]
    rows = {}
    for rid, v in inp.items():
        meta = requests.get(API.format(rid), timeout=60).json()["metadata"]
        size_of = {f["uri"]: f["size"] for x in meta["_file_indices"] for f in x["files"]}
        d = meta["distribution"]
        ev_per_byte = d["number_events"] / d["size"]
        p = pre[rid]
        s_per_ev = p["elapsed_sec"] / p["events_read"]
        ev = [size_of[u] * ev_per_byte for u in v["files"]]
        cpu = [e * s_per_ev for e in ev]
        tier = v["tier"]
        wall = 3 if (tier == 4 or max(cpu) > 0.6 * 7200) else 2
        rows[rid] = {"tier": tier, "name": p["name"], "files": len(v["files"]), "files_full_index": v["n_files_full_index"],
                     "portal_number_files": v["portal_number_files"],
                     "events_estimate": sum(ev), "events_portal": d["number_events"],
                     "fraction_of_events_reachable_estimate": sum(ev) / d["number_events"],
                     "cpu_s_per_event_file0": s_per_ev, "cpu_hours": sum(cpu) / 3600,
                     "max_cpu_s_per_file": max(cpu), "walltime": WALL[wall],
                     "cluster_files": len(v["files"]) * per_job_files}
    tiers = {}
    for r in rows.values():
        t = tiers.setdefault(r["tier"], {"samples": 0, "files": 0, "events": 0.0, "cpu_hours": 0.0, "cluster_files": 0.0})
        t["samples"] += 1
        t["files"] += r["files"]
        t["events"] += r["events_estimate"]
        t["cpu_hours"] += r["cpu_hours"]
        t["cluster_files"] += r["cluster_files"]
    out = {"what": "ESTIMATES for the A2 full production of the 54 new samples", "per_job_files": per_job_files,
           "build_files_per_sample": BUILD_FILES_PER_SAMPLE, "samples": rows,
           "tiers": dict(sorted(tiers.items()))}
    (HERE / "evidence" / "full_production_plan.json").write_text(json.dumps(out, indent=1) + "\n")
    for t, v in sorted(tiers.items()):
        print(t, v)


if __name__ == "__main__":
    main()
