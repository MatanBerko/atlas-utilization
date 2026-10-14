#!/usr/bin/env python
"""
Pilot Part 1: per-file event counts for the three pilot samples, so the PBS
walltime and memory requests can be sized from the real input rather than
guessed.

Opens each file's header only -- `tree.num_entries` plus the Runs-tree totals
-- and reads NO event data, so the whole sweep is a few seconds of network per
file rather than a full read. Also re-checks each record's file count against
the CERN Open Data portal.

Read-only. Writes one JSON into --out and nothing else.

Run:
    python studies/cms_mc_weights_v3/cluster/measure_pilot_inputs.py \
        --out /storage/.../work/cms_mc_v3_pilot_<date>/evidence/pilot_inputs.json
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

# The pilot samples and the file counts DESIGN.md D10 states for them. A
# mismatch against the portal is a hard error: the walltime projection and the
# Sigma-w accounting both assume the full file set.
PILOT_RECORDS = {
    "67801": {"physics_short": "TTTo2L2Nu", "expected_files": 49},
    "35669": {"physics_short": "DYJetsToLL_M-50_amcatnloFXFX", "expected_files": 41},
    "37728": {"physics_short": "GluGluHToZZTo4L_M125", "expected_files": 8},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--records", default=None,
                    help="comma-separated subset (default: all three pilot records)")
    args = ap.parse_args()

    records = ([r.strip() for r in args.records.split(",") if r.strip()]
               if args.records else list(PILOT_RECORDS))

    out = {
        "what": "per-file event counts for the CMS MC pilot (record 67801, "
                "35669, 37728), from file headers only",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "records": {},
    }
    grand_events = 0
    grand_files = 0
    for rid in records:
        meta = PILOT_RECORDS[rid]
        portal = fetch_record_number_events(int(rid))
        urls = fetch_file_list(int(rid))
        if len(urls) != meta["expected_files"]:
            raise SystemExit(
                f"STOP: record {rid} has {len(urls)} files on the portal but the "
                f"pilot expects {meta['expected_files']}.")
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
                count = int(np.asarray(
                    runs["genEventCount"].array(library="np")).sum())
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
        total = sum(counts)
        largest = max(files, key=lambda f: f["n_events"])
        mismatched = [f["file_index"] for f in files if not f["count_matches_events"]]
        out["records"][rid] = {
            "physics_short": meta["physics_short"],
            "n_files": len(files),
            "portal_number_files": portal["number_files"],
            "portal_number_events": portal["number_events"],
            "sum_of_file_events": total,
            "sum_matches_portal_number_events": total == portal["number_events"],
            "min_events": min(counts),
            "median_events": int(np.median(counts)),
            "max_events": max(counts),
            "largest_file_index": largest["file_index"],
            "sum_runs_gen_event_sumw": sum(f["runs_gen_event_sumw"] for f in files),
            "files_whose_genEventCount_differs_from_num_entries": mismatched,
            "sweep_seconds": round(time.perf_counter() - t0, 1),
            "files": files,
        }
        grand_events += total
        grand_files += len(files)
        print(f"[{rid}] {meta['physics_short']}: {len(files)} files, "
              f"{total:,} events (portal says {portal['number_events']:,}), "
              f"largest = file {largest['file_index']} with "
              f"{largest['n_events']:,}", flush=True)

    out["totals"] = {
        "n_records": len(records),
        "n_files": grand_files,
        "n_events": grand_events,
    }
    path = pathlib.Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nTOTAL: {grand_files} files, {grand_events:,} events")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
