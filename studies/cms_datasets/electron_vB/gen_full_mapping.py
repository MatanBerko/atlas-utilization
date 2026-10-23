#!/usr/bin/env python
"""
Step C: build the full-production file list -- every file of every
(dataset, era) for the four delivered datasets.

Writes, into --out-dir:
  <Dataset>_index.json   {job index: {record_id, file_index}}, era G first
                         then era H, which is the format
                         build_four_dataset_delivery.py reads;
  <Dataset>_mapping.txt  "<array_index> <dataset> <record_id> <file_index>
                          <job_index>" -- one PBS array per dataset, so the
                          array index IS the job index;
  full_files.json        the complete list with URLs, for the handoff.

One array per dataset keeps every output directory well under the 1000-file
limit (the largest is SingleMuon at 152).

Usage:
    python gen_full_mapping.py --out-dir /storage/.../runs_matched4_full_<date>
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
from studies.cms_datasets.cluster.datasets_records import DATASETS  # noqa: E402
from studies.cms_datasets.electron_prep.common import record_for  # noqa: E402

ERAS = ("G", "H")
EXPECTED_TOTALS = {d.label: d.expected_files_g_plus_h for d in DATASETS}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_files = []
    totals = {}
    for dataset in DELIVERY_VETO_ORDER_4:
        index = {}
        rows = []
        job = 0
        for era in ERAS:
            record_id = record_for(dataset, era)
            urls = fetch_file_list(record_id)
            for file_index, url in enumerate(urls):
                index[str(job)] = {"record_id": record_id, "file_index": file_index}
                rows.append(f"{job} {dataset} {record_id} {file_index} {job}")
                all_files.append({"job_index": job, "dataset": dataset, "era": era,
                                  "record_id": record_id, "file_index": file_index,
                                  "url": url})
                job += 1
        totals[dataset] = job
        expected = EXPECTED_TOTALS[dataset]
        status = "OK" if job == expected else f"MISMATCH (expected {expected})"
        if job != expected:
            raise SystemExit(
                f"STOP: {dataset} has {job} files on the portal but the record "
                f"table expects {expected}. Refusing to build a production "
                f"mapping that does not match the agreed file counts.")
        (out_dir / f"{dataset}_index.json").write_text(json.dumps(index, indent=2),
                                                       encoding="utf-8")
        (out_dir / f"{dataset}_mapping.txt").write_text("\n".join(rows) + "\n",
                                                        encoding="utf-8")
        print(f"{dataset:12s} {job:4d} files  {status}  -> {dataset}_index.json, "
              f"{dataset}_mapping.txt (array 0-{job - 1})")

    (out_dir / "full_files.json").write_text(json.dumps({
        "what": "full production file list, all four datasets, Run2016G+H",
        "datasets": list(DELIVERY_VETO_ORDER_4), "eras": list(ERAS),
        "n_files_per_dataset": totals, "n_files_total": sum(totals.values()),
        "files": all_files}, indent=2), encoding="utf-8")
    print(f"\nTOTAL {sum(totals.values())} files (expected "
          f"{sum(EXPECTED_TOTALS[d] for d in DELIVERY_VETO_ORDER_4)})")
    print(f"wrote {out_dir / 'full_files.json'}")


if __name__ == "__main__":
    main()
