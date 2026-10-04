#!/usr/bin/env python
"""
Step 1 support: find a run number present in ALL FIVE datasets
(DoubleMuon, SingleMuon, DoubleEG, MuonEG, SingleElectron), so the
5-dataset closure test has a concrete run to use.

Reads ONLY the `run` branch from a sample of files per dataset, so it is
cheap. The brief suggests run 280016 "if it is" -- this script checks that
rather than assuming it, and reports what it actually finds.

Usage:
    python find_common_run.py --files-per-record 6 \
        --out evidence/common_run_check.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402
from studies.cms_datasets.electron_prep.common import record_for  # noqa: E402

LABELS = ["DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG", "SingleElectron"]
SUGGESTED_RUN = 280016


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--files-per-record", type=int, default=6)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    per_dataset = {}
    for label in LABELS:
        runs = set()
        scanned = []
        for era in ("G", "H"):
            rec = record_for(label, era)
            urls = fetch_file_list(rec)
            n = len(urls)
            take = min(args.files_per_record, n)
            idx = sorted({round(i * (n - 1) / max(take - 1, 1)) for i in range(take)})
            for i in idx:
                try:
                    arr = uproot.open(urls[i])["Events"]["run"].array(library="np")
                except Exception as exc:                      # noqa: BLE001
                    scanned.append({"era": era, "file_index": i, "error": str(exc)[:200]})
                    continue
                u = np.unique(arr)
                runs.update(int(x) for x in u)
                scanned.append({"era": era, "file_index": i, "n_runs_in_file": int(u.size),
                                "run_min": int(u.min()), "run_max": int(u.max())})
        per_dataset[label] = {"runs_seen": sorted(runs), "n_runs_seen": len(runs),
                              "files_scanned": scanned}
        print(f"{label:16s} {len(runs):4d} distinct runs seen "
              f"(range {min(runs) if runs else '-'}..{max(runs) if runs else '-'})")

    common = set(per_dataset[LABELS[0]]["runs_seen"])
    for label in LABELS[1:]:
        common &= set(per_dataset[label]["runs_seen"])
    common = sorted(common)

    # Among the common runs, prefer the one seen in the most files (a proxy
    # for "plenty of events everywhere"), and report the suggested run.
    out = {
        "what": "a run number present in all five datasets, for the closure test",
        "labels": LABELS,
        "files_per_record_scanned": args.files_per_record,
        "note": "this is a SAMPLE of files per record, so `runs_seen` is a lower "
                "bound on each dataset's true run list; a run in `common_runs` is "
                "genuinely present in all five, but a run absent here is not proven "
                "absent.",
        "common_runs": common,
        "n_common_runs": len(common),
        "suggested_run_280016_is_common": SUGGESTED_RUN in common,
        "suggested_run_present_per_dataset": {
            label: (SUGGESTED_RUN in per_dataset[label]["runs_seen"]) for label in LABELS
        },
        "recommended_closure_run": (SUGGESTED_RUN if SUGGESTED_RUN in common
                                    else (common[len(common) // 2] if common else None)),
        "per_dataset": per_dataset,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\ncommon runs across all five: {len(common)}")
    print(f"run {SUGGESTED_RUN} common to all five: {out['suggested_run_280016_is_common']}")
    print(f"per dataset: {out['suggested_run_present_per_dataset']}")
    print(f"recommended closure run: {out['recommended_closure_run']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
