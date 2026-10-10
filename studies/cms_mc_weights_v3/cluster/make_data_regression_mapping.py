#!/usr/bin/env python
"""
Part B: pick the data files for the regression and write the PBS mapping file.

Two files per dataset (DoubleMuon, SingleMuon, DoubleEG, MuonEG) = 8 files, the
cap this round is allowed. For each dataset it takes the LOWEST and the HIGHEST
job index the delivered production actually has, so the pair is not two
adjacent near-identical files and -- because the per-dataset index runs era G
first and era H second -- the two picks land in different run eras.

The delivered production is read ONLY to discover which files exist; nothing
under output/ is written, moved or opened for anything but reading.

Mapping format, 5 space-separated columns:
    <array_index> <dataset_label> <record_id> <file_index> <job_dir_index>

`job_dir_index` is the delivered production's own `job_<n>` directory name, so
the re-run output lands at the same relative path and the comparison lines up
one-to-one. It is NOT the same number as `file_index`: the production indexes
jobs continuously across both run eras while `file_index` restarts per record.

Run:
    python studies/cms_mc_weights_v3/cluster/make_data_regression_mapping.py \
        --runs-dir /storage/.../output/cms_datasets/runs_matched4_full_20261007 \
        --out      /storage/.../work/cms_mc_v3_impl_<date>/data_files.txt
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

DATASETS = ("DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG")
FILES_PER_DATASET = 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    runs_dir = pathlib.Path(args.runs_dir)
    rows, chosen = [], []
    idx = 0
    for dataset in DATASETS:
        index_path = runs_dir / f"{dataset}_index.json"
        if not index_path.exists():
            raise SystemExit(f"missing per-file index: {index_path}")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        job_keys = sorted(index, key=int)
        if len(job_keys) < FILES_PER_DATASET:
            raise SystemExit(f"{dataset}: only {len(job_keys)} job(s) available")
        picks = [job_keys[0], job_keys[-1]]
        for job_key in picks:
            record_id = int(index[job_key]["record_id"])
            file_index = int(index[job_key]["file_index"])
            job_dir = runs_dir / dataset / f"job_{job_key}"
            if not (job_dir / "job_metadata.json").exists():
                raise SystemExit(
                    f"{dataset} job_{job_key}: no job_metadata.json -- that file's "
                    "delivered output is incomplete, so it cannot be a regression "
                    "reference.")
            idx += 1
            rows.append(f"{idx} {dataset} {record_id} {file_index} {job_key}")
            chosen.append({
                "array_index": idx, "dataset": dataset, "record_id": record_id,
                "file_index": file_index, "job_dir_index": job_key,
                "delivered_job_dir": str(job_dir),
            })

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    (out.parent / (out.stem + "_chosen.json")).write_text(
        json.dumps({"runs_dir": str(runs_dir), "files_per_dataset": FILES_PER_DATASET,
                    "n_files": len(chosen), "chosen": chosen}, indent=2),
        encoding="utf-8")

    print(out.read_text(encoding="utf-8"), end="")
    print(f"\n{len(rows)} file(s) across {len(DATASETS)} dataset(s)")
    for c in chosen:
        print(f"  {c['dataset']:12s} job_{c['job_dir_index']:<4s} "
              f"record={c['record_id']} file_index={c['file_index']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
