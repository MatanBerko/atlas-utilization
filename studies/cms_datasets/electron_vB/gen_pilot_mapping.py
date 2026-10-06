#!/usr/bin/env python
"""
E0: build the pilot file list -- for each (dataset, era) pair, the FIRST
file and the MIDDLE file of that record's own portal file list. Four
datasets x two eras x two files = 16 files.

Writes, into --out-dir:
  <Dataset>_index.json   {job index: {record_id, file_index}} -- the same
                         format the existing production runs use, so
                         build_four_dataset_delivery.py can read it;
  pilot_mapping.txt      "<array_index> <dataset> <record_id> <file_index>"
                         one line per job, for the PBS array;
  pilot_files.json       the full list with URLs and record file counts,
                         for HANDOFF.md.

Usage:
    python gen_pilot_mapping.py --out-dir /storage/.../runs_matched4_pilot_<date>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402
from studies.cms_datasets.cluster.run_dataset_on_file import DELIVERY_VETO_ORDER_4  # noqa: E402
from studies.cms_datasets.electron_prep.common import record_for  # noqa: E402

ERAS = ("G", "H")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    pilot = []
    for dataset in DELIVERY_VETO_ORDER_4:
        index = {}
        job = 0
        for era in ERAS:
            record_id = record_for(dataset, era)
            urls = fetch_file_list(record_id)
            n = len(urls)
            picks = [("first", 0), ("middle", n // 2)]
            for which, file_index in picks:
                index[str(job)] = {"record_id": record_id, "file_index": file_index}
                pilot.append({
                    "job_index": job, "dataset": dataset, "era": era,
                    "record_id": record_id, "n_files_in_record": n,
                    "which": which, "file_index": file_index,
                    "url": urls[file_index],
                })
                all_rows.append(f"{len(all_rows)} {dataset} {record_id} {file_index}")
                job += 1
        (out_dir / f"{dataset}_index.json").write_text(json.dumps(index, indent=2),
                                                       encoding="utf-8")
        print(f"{dataset}: {len(index)} pilot files -> {dataset}_index.json")

    # The PBS array mapping is per dataset (one array per dataset, indices
    # 0..3 matching the index JSON), so the flat mapping file is written
    # only as a human-readable record.
    (out_dir / "pilot_mapping.txt").write_text("\n".join(all_rows) + "\n", encoding="utf-8")
    (out_dir / "pilot_files.json").write_text(json.dumps({
        "what": "E0 pilot file list: first and middle file of every (dataset, era)",
        "datasets": list(DELIVERY_VETO_ORDER_4), "eras": list(ERAS),
        "n_files": len(pilot), "files": pilot,
    }, indent=2), encoding="utf-8")
    print(f"\n{len(pilot)} pilot files total")
    for e in pilot:
        print(f"  {e['dataset']:12s} {e['era']} job_{e['job_index']} "
              f"record {e['record_id']} file {e['file_index']:3d} "
              f"({e['which']} of {e['n_files_in_record']})")
    print(f"\nwrote {out_dir / 'pilot_files.json'}")


if __name__ == "__main__":
    main()
