#!/usr/bin/env python
"""
Diagnosis round -- D2 (partial): empirical within-DoubleMuon duplicate-event
check.

docs/CMS_KNOWN_LIMITATIONS.md documents a ~2% duplicate rate, but that
figure is for the SingleElectron+SingleMuon CROSS-record overlap (same
event firing two different primary-dataset triggers) handled by
services/parsing/event_deduplication.py -- a different code path entirely,
not used anywhere in the DoubleMuon coverage production
(studies/cms_coverage/cluster/run_coverage_on_file.py calls no
de-duplication step at all).

This script instead directly checks, empirically, whether the SAME event
(run, luminosityBlock, event) appears more than once WITHIN the 57
DoubleMuon files that actually produced the delivery (records 30522
Run2016G-only, 30555 Run2016H-only -- non-overlapping eras). Reads ONLY
the 3 small integer branches needed for the key (not the full event
selection) -- read-only, no selection/output touched.

Usage: python d2_dedup_check.py --out <path>
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import uproot

RECORD_FILES_JSON = "/storage/agrp/berkom/atlas-utilization/output/cms_coverage_full/job_index_map_summary.json"
READ_CHUNK_SIZE = 1_000_000


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()

    summary = json.loads(Path(RECORD_FILES_JSON).read_text(encoding="utf-8"))
    all_urls = []
    for rid, d in summary["per_record"].items():
        for u in d["urls"]:
            all_urls.append((rid, u))

    t0 = time.time()
    frames = []
    failed_files = []

    for rid, url in all_urls:
        try:
            tree = uproot.open(url)["Events"]
            n_entries = tree.num_entries
            for start in range(0, n_entries, READ_CHUNK_SIZE):
                stop = min(start + READ_CHUNK_SIZE, n_entries)
                arrs = tree.arrays(["run", "luminosityBlock", "event"],
                                    entry_start=start, entry_stop=stop, library="np")
                df = pd.DataFrame({
                    "run": arrs["run"].astype(np.int64),
                    "lumi": arrs["luminosityBlock"].astype(np.int64),
                    "event": arrs["event"].astype(np.int64),
                    "record": rid,
                })
                frames.append(df)
            print(f"  read {rid} {url.rsplit('/', 1)[-1]}: {n_entries} events", flush=True)
        except Exception as e:  # noqa: BLE001
            failed_files.append({"record": rid, "url": url, "error": f"{type(e).__name__}: {e}"})
            print(f"FAILED reading {url}: {type(e).__name__}: {e}", flush=True)

    all_df = pd.concat(frames, ignore_index=True)
    n_total = len(all_df)
    dup_mask = all_df.duplicated(subset=["run", "lumi", "event"], keep="first")
    n_dup = int(dup_mask.sum())
    per_record_total = all_df.groupby("record").size().to_dict()
    per_record_dup = all_df.loc[dup_mask].groupby("record").size().to_dict()

    result = {
        "n_files_checked": len(all_urls) - len(failed_files),
        "n_files_failed": len(failed_files),
        "failed_files": failed_files,
        "n_total_events_keyed": n_total,
        "n_duplicate_events_within_doublemuon": n_dup,
        "duplicate_fraction": (n_dup / n_total) if n_total > 0 else None,
        "per_record_total": per_record_total,
        "per_record_duplicates": per_record_dup,
        "elapsed_sec": time.time() - t0,
        "note": (
            "This checks WITHIN the DoubleMuon dataset only (records 30522+30555, "
            "the only two records used for this delivery). It does NOT check for "
            "the documented SingleElectron/SingleMuon cross-record ~2% overlap, "
            "which is a different mechanism not applicable here (DoubleMuon is a "
            "single primary dataset, not combined with SingleMuon/SingleElectron "
            "in this production)."
        ),
    }
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("failed_files",)}, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
