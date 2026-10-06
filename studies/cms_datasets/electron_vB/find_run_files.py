#!/usr/bin/env python
"""
Two jobs in one cheap pass over every file of one (dataset, era):

1. E3: which files contain the closure run? Reads ONLY the `run` branch,
   exactly as studies/cms_datasets/electron_prep/find_common_run.py does
   (this is that script extended from a sample to ALL files, and to
   recording which file each run is in rather than only the run set).

2. D2: is every HLT branch needed to evaluate all FOUR acceptances present
   in this file? The tree header is already open, so the check is free. A
   missing branch anywhere is a STOP condition for the delivery, and this
   is where it would be found.

Usage (one array subjob per dataset+era):
    python find_run_files.py --dataset DoubleEG --era G --run 281707 \
        --out /storage/.../closure/runscan_DoubleEG_G.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402
from studies.cms_datasets.cluster.run_dataset_on_file import MATCHED4_TRIGGER_PATHS  # noqa: E402
from studies.cms_datasets.electron_prep.common import record_for  # noqa: E402

NEEDED_HLT = sorted({p for paths in MATCHED4_TRIGGER_PATHS.values() for p in paths})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True)
    p.add_argument("--era", required=True, choices=["G", "H"])
    p.add_argument("--run", type=int, required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    record_id = record_for(args.dataset, args.era)
    urls = fetch_file_list(record_id)
    print(f"{args.dataset} {args.era} record {record_id}: {len(urls)} files", flush=True)

    per_file = []
    files_with_run = []
    missing_hlt = {}
    t0 = time.time()
    for i, url in enumerate(urls):
        entry = {"file_index": i}
        try:
            tree = uproot.open(url)["Events"]
            keys = set(tree.keys())
            absent = [b for b in NEEDED_HLT if b not in keys]
            entry["missing_hlt_branches"] = absent
            if absent:
                missing_hlt[str(i)] = absent
            runs = tree["run"].array(library="np")
            uniq = np.unique(runs)
            entry["n_entries"] = int(tree.num_entries)
            entry["n_runs"] = int(uniq.size)
            entry["run_min"] = int(uniq.min())
            entry["run_max"] = int(uniq.max())
            entry["has_target_run"] = bool(args.run in set(int(x) for x in uniq))
            entry["n_entries_target_run"] = int((runs == args.run).sum())
            if entry["has_target_run"]:
                files_with_run.append(i)
        except Exception as exc:  # noqa: BLE001
            entry["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
            print(f"  file {i}: ERROR {entry['error']}", flush=True)
        per_file.append(entry)
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(urls)} files, {time.time() - t0:.0f}s", flush=True)

    out = {
        "what": "all files of one (dataset, era): which contain the closure run, "
                "and whether every HLT branch the four acceptances need is present",
        "dataset": args.dataset, "era": args.era, "record_id": record_id,
        "target_run": args.run, "n_files": len(urls),
        "needed_hlt_branches": NEEDED_HLT,
        "files_with_target_run": files_with_run,
        "n_files_with_target_run": len(files_with_run),
        "n_entries_target_run_total": int(sum(
            e.get("n_entries_target_run", 0) for e in per_file)),
        "files_with_missing_hlt_branches": missing_hlt,
        "n_files_with_missing_hlt_branches": len(missing_hlt),
        "n_files_with_read_errors": sum(1 for e in per_file if "error" in e),
        "elapsed_sec": round(time.time() - t0, 1),
        "per_file": per_file,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"files with run {args.run}: {files_with_run}")
    print(f"files missing an HLT branch: {len(missing_hlt)}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
