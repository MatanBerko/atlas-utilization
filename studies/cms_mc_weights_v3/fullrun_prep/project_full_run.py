#!/usr/bin/env python
"""
Full-run preparation (17 Oct 2026), Part D: projections for the full MC run.
Arithmetic only -- submits nothing.

Inputs (all measured, see HANDOFF.md):
  --inputs  fullrun_inputs.json  per-file event counts, 13 records (portal + headers)
  --smoke   smoke_test_report.json  Part C: one file per never-run record
  --pilot   pilot_per_file.json  the 98 pilot files of 10 Oct: per file
            n_read, elapsed_sec, peak_rss_gb, output bytes, output files

Sizing rule = the pilot's: per record, the SLOWEST measured rate (events/s)
of that record; worst-file wall = largest file's events / that rate;
requested walltime = 2 x worst-file wall, rounded up to the hour; requested
memory = 1.5 x the largest measured peak, rounded up to the GB.
CPU hours = record events / slowest rate (conservative).
Disk = record events x the largest measured output bytes per event read.
Files created = per job (9 output files + 1 job dir + 2 PBS logs) + 1 record dir.

Writes fullrun_projection.json.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ORDER = [67801, 67993, 35669, 35631, 64895, 64839, 72676, 72752, 75589, 68187,
         68073, 37728, 68847]
PILOT = {67801, 35669, 37728}
FILES_PER_JOB = 9 + 1 + 2   # 8 shards + job_metadata.json, the job dir, .out/.err


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--smoke", required=True)
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--files-now", type=int, required=True,
                    help="current file count of /storage/agrp/berkom")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    inputs = json.loads(Path(args.inputs).read_text())["records"]
    smoke = {str(r["record"]): r for r in json.loads(Path(args.smoke).read_text())["records"]}
    pilot = json.loads(Path(args.pilot).read_text())["files"]

    meas: dict[str, list] = {}
    for f in pilot:
        meas.setdefault(str(f["record"]), []).append({**f, "source": "pilot 10 Oct"})
    for rid, r in smoke.items():
        if r.get("production_success"):
            meas.setdefault(rid, []).append({
                "record": int(rid), "file_index": r["file_index"], "n_read": r["events_read"],
                "elapsed_sec": r["wall_seconds_driver"], "peak_rss_gb": r.get("peak_rss_gb"),
                "output_bytes": r["output_bytes"], "n_output_files": r["n_output_files"],
                "source": "smoke 17 Oct"})

    rows, tot = [], {"files": 0, "events": 0, "cpu_h": 0.0, "disk_gb": 0.0,
                     "files_created": 0, "files_created_if_pilot_reused": 0,
                     "cpu_h_if_pilot_reused": 0.0, "disk_gb_if_pilot_reused": 0.0}
    for rid_i in ORDER:
        rid = str(rid_i)
        inp = inputs[rid]
        m = meas.get(rid, [])
        if not m:
            rows.append({"record": rid_i, "physics_short": inp["physics_short"],
                         "n_files": inp["n_files"], "events": inp["sum_of_file_events"],
                         "NO_MEASUREMENT": True})
            continue
        rates = [x["n_read"] / x["elapsed_sec"] for x in m if x["elapsed_sec"]]
        slow = min(rates)
        peak = max(x["peak_rss_gb"] for x in m if x.get("peak_rss_gb") is not None)
        bpe = max(x["output_bytes"] / x["n_read"] for x in m if x["n_read"])
        events = inp["sum_of_file_events"]
        worst_s = inp["max_events"] / slow
        cpu_h = events / slow / 3600
        disk_gb = events * bpe / 1e9
        files_created = inp["n_files"] * FILES_PER_JOB + 1
        wall_req_h = max(1, math.ceil(2 * worst_s / 3600))
        mem_req_gb = math.ceil(1.5 * peak)
        row = {
            "record": rid_i, "physics_short": inp["physics_short"],
            "n_files": inp["n_files"], "events": events,
            "portal_events_match": inp["sum_matches_portal_number_events"],
            "largest_file_events": inp["max_events"],
            "largest_file_index": inp["largest_file_index"],
            "n_measured_files": len(m), "measured_from": sorted({x["source"] for x in m}),
            "slowest_rate_ev_per_s": slow, "fastest_rate_ev_per_s": max(rates),
            "peak_rss_gb_max": peak, "output_bytes_per_event_max": bpe,
            "projected_cpu_hours": cpu_h, "worst_file_wall_hours": worst_s / 3600,
            "request_walltime_h": wall_req_h, "request_mem_gb": mem_req_gb,
            "queue_by_walltime": "shortE (<=2 h)" if wall_req_h <= 2 else
            ("normE (2-12 h)" if wall_req_h <= 12 else "longE (12-72 h)"),
            "projected_disk_gb": disk_gb, "projected_files_created": files_created,
        }
        rows.append(row)
        tot["files"] += inp["n_files"]
        tot["events"] += events
        tot["cpu_h"] += cpu_h
        tot["disk_gb"] += disk_gb
        tot["files_created"] += files_created
        if rid_i not in PILOT:
            tot["files_created_if_pilot_reused"] += files_created
            tot["cpu_h_if_pilot_reused"] += cpu_h
            tot["disk_gb_if_pilot_reused"] += disk_gb
    tot["file_count_after_full_rerun"] = args.files_now + tot["files_created"]
    tot["file_count_after_if_pilot_reused"] = args.files_now + tot["files_created_if_pilot_reused"]
    tot["soft_quota"] = 150000
    tot["hard_limit"] = 200000
    out = {"rows": rows, "totals": tot, "files_now": args.files_now,
           "rule": __doc__.split("Sizing rule = ")[1].split("Writes")[0].strip()}
    Path(args.out).write_text(json.dumps(out, indent=2))
    for r in rows:
        print(json.dumps(r))
    print(json.dumps(tot, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
