#!/usr/bin/env python
"""
Part B: choose the file subset and write the PBS mapping.

Mapping format, 5 columns:
    <array_index> <kind> <dataset_label> <record_id> <file_index>

Data: ~20 DoubleMuon and ~20 DoubleEG files, split between Run2016G and
Run2016H, taken from the delivered production's own per-dataset index so the
files are exactly ones the delivery used. mumu comes from DoubleMuon and ee
from DoubleEG (see the probe's docstring for why).

MC: ~10 files of 35669 (DY NLO) and ~10 of 67801 (ttbar), evenly spaced
through each record's file list so the subset is not biased toward one part
of the sample.

Files are picked evenly spaced through each era's list rather than randomly,
so the selection is reproducible without storing a seed.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_mc_weights_v3.cluster.measure_pilot_inputs import (  # noqa: E402
    PILOT_RECORDS,
)

# Run2016G and Run2016H record IDs, from studies/cms_datasets/cluster/datasets_records.py
DATA_RECORDS = {
    "DoubleMuon": {"G": 30522, "H": 30555},
    "DoubleEG": {"G": 30521, "H": 30554},
}
MC_RECORDS = ("35669", "67801")


def evenly_spaced(items: list, n: int) -> list:
    """n items spread evenly across `items` (all of them if n >= len)."""
    if n >= len(items):
        return list(items)
    step = len(items) / float(n)
    return [items[int(i * step)] for i in range(n)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True,
                    help="the delivered production runs dir (read-only)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-files-per-dataset", type=int, default=20)
    ap.add_argument("--mc-files-per-record", type=int, default=10)
    args = ap.parse_args()

    runs_dir = pathlib.Path(args.runs_dir)
    rows, chosen = [], []
    idx = 0

    for label, eras in DATA_RECORDS.items():
        index_path = runs_dir / f"{label}_index.json"
        if not index_path.exists():
            raise SystemExit(f"missing delivered index: {index_path}")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        by_era = {"G": [], "H": []}
        for job_key in sorted(index, key=int):
            rec = int(index[job_key]["record_id"])
            fi = int(index[job_key]["file_index"])
            era = "G" if rec == eras["G"] else ("H" if rec == eras["H"] else None)
            if era is None:
                raise SystemExit(
                    f"{label} job {job_key}: record {rec} is neither "
                    f"{eras['G']} (G) nor {eras['H']} (H)")
            by_era[era].append((rec, fi))
        half = args.data_files_per_dataset // 2
        for era in ("G", "H"):
            for rec, fi in evenly_spaced(by_era[era], half):
                idx += 1
                rows.append(f"{idx} data {label} {rec} {fi}")
                chosen.append({"array_index": idx, "kind": "data",
                               "dataset_label": label, "era": era,
                               "record_id": rec, "file_index": fi})

    for rid in MC_RECORDS:
        n_files = PILOT_RECORDS[rid]["expected_files"]
        for fi in evenly_spaced(list(range(n_files)), args.mc_files_per_record):
            idx += 1
            rows.append(f"{idx} mc MC {rid} {fi}")
            chosen.append({"array_index": idx, "kind": "mc",
                           "dataset_label": "MC", "record_id": int(rid),
                           "file_index": fi,
                           "physics_short": PILOT_RECORDS[rid]["physics_short"],
                           "n_files_in_record": n_files})

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    (out.parent / (out.stem + "_chosen.json")).write_text(
        json.dumps({"runs_dir": str(runs_dir), "n_jobs": len(rows),
                    "chosen": chosen}, indent=2), encoding="utf-8")

    n_data = sum(1 for c in chosen if c["kind"] == "data")
    n_mc = sum(1 for c in chosen if c["kind"] == "mc")
    print(f"{len(rows)} jobs: {n_data} data + {n_mc} MC")
    for label in DATA_RECORDS:
        for era in ("G", "H"):
            k = sum(1 for c in chosen if c.get("dataset_label") == label
                    and c.get("era") == era)
            print(f"  {label:11s} Run2016{era}: {k} files")
    for rid in MC_RECORDS:
        k = sum(1 for c in chosen if str(c["record_id"]) == rid)
        print(f"  record {rid} ({PILOT_RECORDS[rid]['physics_short']}): {k} of "
              f"{PILOT_RECORDS[rid]['expected_files']} files")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
