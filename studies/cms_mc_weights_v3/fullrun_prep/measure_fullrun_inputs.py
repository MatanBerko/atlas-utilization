#!/usr/bin/env python
"""
Full-run preparation (17 Oct 2026), Part D input: per-file event counts for
all 13 full-run records, so the full-run walltime, memory, disk and file
count can be projected from the real input rather than guessed.

Same method as cluster/measure_pilot_inputs.py (which is restricted to the
three pilot records): the portal's file list and totals from the CERN Open
Data API, then each file's HEADER only -- `Events.num_entries` and the Runs
totals -- with NO event data read.

The record list is the registry's `full_run_records`; it is checked to be
exactly the 13 records named in the task, so a registry change cannot
silently change what is measured.

Read-only. Writes one JSON into --out and nothing else.

Run:
    python studies/cms_mc_weights_v3/fullrun_prep/measure_fullrun_inputs.py \
        --out <work>/evidence/fullrun_inputs.json [--records 67993,72752]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime, timezone

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import uproot  # noqa: E402

from studies.m0m1j0_cms.design_checks.common import (  # noqa: E402
    fetch_file_list, fetch_record_number_events,
)

REGISTRY = REPO_ROOT / "studies" / "cms_mc_weights_v3" / "cms_mc_normalisation_v3.json"
EXPECTED_FULL_RUN = {67801, 67993, 35669, 35631, 64895, 64839, 72676, 72752,
                     75589, 68187, 68073, 37728, 68847}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--records", default=None,
                    help="comma-separated subset (default: all 13 full-run records)")
    args = ap.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    full_run = [int(r) for r in registry["full_run_records"]]
    if set(full_run) != EXPECTED_FULL_RUN:
        raise SystemExit(f"STOP: registry full_run_records {sorted(full_run)} != the "
                         f"13 records of the task {sorted(EXPECTED_FULL_RUN)}")
    records = ([int(r) for r in args.records.split(",") if r.strip()]
               if args.records else full_run)

    out = {
        "what": "per-file event counts for the 13 CMS MC full-run records, "
                "from file headers only (no event data read)",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "records": {},
    }
    for rid in records:
        rec = registry["records"][str(rid)]
        portal = fetch_record_number_events(rid)
        urls = fetch_file_list(rid)
        if len(urls) != portal["number_files"]:
            raise SystemExit(
                f"STOP: record {rid} file list ({len(urls)}) disagrees with the "
                f"portal's own number_files ({portal['number_files']}).")
        files = []
        t0 = time.perf_counter()
        for idx, url in enumerate(urls):
            t1 = time.perf_counter()
            with uproot.open(url) as f:
                n_events = int(f["Events"].num_entries)
                runs = f["Runs"]
                sumw = float(np.asarray(
                    runs["genEventSumw"].array(library="np"), dtype=np.float64).sum())
                count = int(np.asarray(runs["genEventCount"].array(library="np")).sum())
            files.append({
                "file_index": idx,
                "n_events": n_events,
                "runs_gen_event_sumw": sumw,
                "runs_gen_event_count": count,
                "count_matches_events": count == n_events,
                "open_seconds": round(time.perf_counter() - t1, 2),
                "url": url,
            })
            print(f"  [{rid}] file {idx:>3}: {n_events:>10,} events "
                  f"({time.perf_counter() - t1:.1f}s)", flush=True)
        counts = [f["n_events"] for f in files]
        largest = max(files, key=lambda f: f["n_events"])
        out["records"][str(rid)] = {
            "physics_short": rec["physics_short"],
            "n_files": len(files),
            "portal_number_files": portal["number_files"],
            "portal_number_events": portal["number_events"],
            "sum_of_file_events": sum(counts),
            "sum_matches_portal_number_events": sum(counts) == portal["number_events"],
            "min_events": min(counts),
            "median_events": int(np.median(counts)),
            "max_events": max(counts),
            "largest_file_index": largest["file_index"],
            "first_file_events": files[0]["n_events"],
            "sum_runs_gen_event_sumw": sum(f["runs_gen_event_sumw"] for f in files),
            "files_whose_genEventCount_differs_from_num_entries":
                [f["file_index"] for f in files if not f["count_matches_events"]],
            "sweep_seconds": round(time.perf_counter() - t0, 1),
            "files": files,
        }
        print(f"[{rid}] {rec['physics_short']}: {len(files)} files, {sum(counts):,} "
              f"events (portal {portal['number_events']:,}), largest file "
              f"{largest['file_index']} = {largest['n_events']:,}", flush=True)
    out["totals"] = {
        "n_records": len(out["records"]),
        "n_files": sum(r["n_files"] for r in out["records"].values()),
        "n_events": sum(r["sum_of_file_events"] for r in out["records"].values()),
    }
    path = pathlib.Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nTOTAL: {out['totals']}\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
