#!/usr/bin/env python
"""
Builds the PBS array mapping file for a full dataset run: one line per
file (one job per file, per this task's own instruction), covering every
file of both eras (G first, then H), using the already-verified file
counts from record_file_lists.json (studies/cms_datasets/evidence/) --
not recomputed or guessed.

Dataset-parameterized so the same generator serves later datasets
(DoubleEG, MuonEG, SingleMuon, SingleElectron) in future tasks.

Mapping file columns: "<array_index> <dataset_label> <record_id> <file_index>"
(--population is fixed to "generic" by the PBS script itself for a full
delivery run, not encoded per-line, since every line uses the same value).

Usage:
    python gen_full_run_mapping.py --dataset-label DoubleMuon \
        --file-lists <record_file_lists.json> --out <mapping.txt>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-label", required=True)
    p.add_argument("--file-lists", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    data = json.loads(Path(args.file_lists).read_text())["records"]
    g_key, h_key = f"{args.dataset_label}_G", f"{args.dataset_label}_H"
    if g_key not in data or h_key not in data:
        raise ValueError(f"{args.dataset_label}: expected keys {g_key!r} and {h_key!r} in {args.file_lists}")

    g_record = data[g_key]["record_id"]
    h_record = data[h_key]["record_id"]
    n_g = data[g_key]["n_files_from_filepage_api"]
    n_h = data[h_key]["n_files_from_filepage_api"]

    lines = []
    idx = 1
    for file_index in range(n_g):
        lines.append(f"{idx} {args.dataset_label} {g_record} {file_index}")
        idx += 1
    for file_index in range(n_h):
        lines.append(f"{idx} {args.dataset_label} {h_record} {file_index}")
        idx += 1

    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"wrote {len(lines)} job lines to {args.out} ({n_g} G-era files, record {g_record}; "
          f"{n_h} H-era files, record {h_record})")


if __name__ == "__main__":
    main()
