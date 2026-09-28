#!/usr/bin/env python
"""
Step 4 pilot: one file per era per core dataset (DoubleMuon, DoubleEG,
MuonEG, SingleMuon, SingleElectron -- 10 jobs total), --population generic.
JetHT and MET are deliberately NOT included here (task's own instruction:
"Do NOT run JetHT or MET beyond Step 1").

File index 0 is used for both eras of every dataset -- an arbitrary, fixed,
reproducible choice (the pilot's purpose is a cost/sanity estimate, not
coverage), each cross-checked against the SAME file this task's own Step 1
scan already read (so job_metadata.json's own event counts can be checked
against Step 1's n_read for the identical file as an extra consistency
check, at no additional cost).

Usage:
    python gen_step4_pilot_mapping.py --out <mapping.txt>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_datasets.cluster.datasets_records import DATASETS  # noqa: E402

PILOT_DATASET_LABELS = ["DoubleMuon", "DoubleEG", "MuonEG", "SingleMuon", "SingleElectron"]
PILOT_FILE_INDEX = 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()

    by_label = {d.label: d for d in DATASETS}
    lines = []
    idx = 1
    for label in PILOT_DATASET_LABELS:
        d = by_label[label]
        for record_id in (d.record_g, d.record_h):
            lines.append(f"{idx} {label} {record_id} {PILOT_FILE_INDEX} generic")
            idx += 1

    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"wrote {len(lines)} job lines to {args.out}")
    for line in lines:
        print(" ", line)


if __name__ == "__main__":
    main()
