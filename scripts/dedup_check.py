#!/usr/bin/env python3
"""
dedup_check.py - verify CMS per-trigger-stream tagging + de-duplication.

Two modes:

  --selftest
      Exercise services.parsing.event_deduplication.EventDeduplicator with
      synthetic events (no pipeline run needed). Checks that:
        * a duplicate (run, lumi, event) seen in an earlier (higher-priority)
          stream is dropped from a later stream,
        * duplicates within a single batch are collapsed,
        * distinct events are all kept,
        * the priority rule = "first stream fed wins".

  --run-dir PATH   (default: newest run under ./output)
      Read that run's parsed_data/*.root and report:
        * events per source_record (the real per-event origin field, not the
          filename), so per-record retention is visible even when records share
          an output file,
        * any residual (run, luminosityBlock, event) duplicates (should be 0 -
          de-dup happens during parsing, before chunks are written).
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np


def _selftest() -> int:
    import awkward as ak
    from services.parsing.event_deduplication import EventDeduplicator

    def mk(run, lumi, evt, tag):
        n = len(evt)
        return ak.Array(
            {
                "Muons": [[] for _ in range(n)],
                "run": np.full(n, run, dtype=np.uint32),
                "luminosityBlock": np.array(lumi, dtype=np.uint32),
                "event": np.array(evt, dtype=np.uint64),
                "source_record": np.full(n, tag, dtype=np.int64),
            }
        )

    d = EventDeduplicator()
    # Higher-priority stream (SingleMuon) fed first.
    mu = mk(278820, [10, 10, 11], [1001, 1002, 2001], 30530)
    kept_mu, drop_mu = d.filter_new(mu)
    # Lower-priority stream (SingleElectron): 1002 and 2001 also fired the muon
    # trigger (duplicates); 3001 is electron-only; 4001 appears twice in-batch.
    el = mk(278820, [10, 11, 12, 12], [1002, 2001, 3001, 3001], 30529)
    kept_el, drop_el = d.filter_new(el)

    ok = True
    if drop_mu != 0:
        print(f"FAIL: first stream should drop nothing, dropped {drop_mu}"); ok = False
    if len(kept_mu) != 3:
        print(f"FAIL: expected 3 muon events kept, got {len(kept_mu)}"); ok = False
    if drop_el != 3:  # 1002, 2001 (cross-stream) + one 3001 (in-batch)
        print(f"FAIL: expected 3 electron events dropped, got {drop_el}"); ok = False
    kept_evts = sorted(int(x) for x in ak.to_list(kept_el["event"]))
    if kept_evts != [3001]:
        print(f"FAIL: expected only event 3001 kept from electron stream, got {kept_evts}")
        ok = False
    if d.total_dropped != 3 or d.dropped_by_run.get(278820) != 3:
        print(f"FAIL: summary counters wrong: {d.summary()}"); ok = False

    print(d.summary())
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def _find_latest_run_dir(base: str) -> Path | None:
    b = Path(base)
    if not b.is_dir():
        return None
    cands = [d for d in b.iterdir() if d.is_dir() and (d / "parsed_data").is_dir()]
    if not cands:
        return None
    cands.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return cands[0]


def _inspect_run(run_dir: Path) -> int:
    import uproot

    parsed = run_dir / "parsed_data"
    roots = sorted(parsed.glob("*.root"))
    if not roots:
        print(f"no parsed_data/*.root under {run_dir}")
        return 1

    print("=" * 74)
    print(f"parsed-data inspection: {run_dir}")
    print("=" * 74)

    per_record = Counter()
    key_seen: set[tuple[int, int, int]] = set()
    dup_keys = 0
    total = 0
    missing_fields = []

    for rf in roots:
        with uproot.open(rf) as f:
            t = f["events"]
            keys = set(k.split(";")[0] for k in t.keys())
            need = {"run", "luminosityBlock", "event", "source_record"}
            if not need.issubset(keys):
                missing_fields.append((rf.name, sorted(need - keys)))
                continue
            run = np.asarray(t["run"].array(library="np"), dtype=np.int64)
            lumi = np.asarray(t["luminosityBlock"].array(library="np"), dtype=np.int64)
            evt = np.asarray(t["event"].array(library="np")).astype(object)
            src = np.asarray(t["source_record"].array(library="np"), dtype=np.int64)
            n = len(run)
            total += n
            for s in src.tolist():
                per_record[int(s)] += 1
            for i in range(n):
                k = (int(run[i]), int(lumi[i]), int(evt[i]))
                if k in key_seen:
                    dup_keys += 1
                else:
                    key_seen.add(k)
        print(f"  {rf.name}: {n:,} events")

    if missing_fields:
        print()
        for name, miss in missing_fields:
            print(f"  !! {name} missing fields: {miss}")
        print("  -> parser did not tag events; per-stream/dedup cannot be verified here")
        return 2

    print()
    print(f"total events in parsed_data : {total:,}")
    print("events per source_record (real per-event origin):")
    for rec, cnt in sorted(per_record.items()):
        print(f"    record {rec}: {cnt:,}")
    print()
    print(f"residual (run,lumi,event) duplicates across all parsed files: {dup_keys}")
    if dup_keys == 0:
        print("RESULT: PASS - no duplicate collision events remain after parsing.")
        return 0
    print("RESULT: FAIL - duplicates present; de-duplication did not fully apply.")
    return 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--base-output", default="./output")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    run_dir = Path(args.run_dir) if args.run_dir else _find_latest_run_dir(args.base_output)
    if run_dir is None or not run_dir.is_dir():
        sys.exit(f"[dedup_check] no run dir under {args.base_output!r}")
    return _inspect_run(run_dir)


if __name__ == "__main__":
    raise SystemExit(main())
