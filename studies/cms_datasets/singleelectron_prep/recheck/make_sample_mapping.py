#!/usr/bin/env python
"""
b-tag re-check (19 Oct 2026), Part 2: the deterministic file sample.

Every 10th file by index (index % 10 == 0), at least one per dataset/record:
  data: the 7 Oct production mappings
        output/cms_datasets/runs_matched4_full_20261007/<Dataset>_mapping.txt
        ("<array_index> <dataset> <record_id> <file_index> <job_index>"); the
        index is the per-dataset job index (0..N-1 over both eras);
  MC:   the full run's mappings work/fullrun_20261017/mappings/mapping_<rid>.txt
        ("<array_index> <record_id> <file_index>"); the index is file_index.

Writes the PBS mapping ("<idx> <kind> <label> <record_id> <file_index> <index>",
0-based idx) and a JSON listing every sampled file.

Usage:
    python make_sample_mapping.py --data-mapping-dir <dir> --mc-mapping-dir <dir> \
        --out-mapping sample_mapping.txt --out-json sample_files.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DATASETS = ("DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG")
STEP = 10


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-mapping-dir", required=True)
    ap.add_argument("--mc-mapping-dir", required=True)
    ap.add_argument("--out-mapping", required=True)
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    rows, per_group = [], {}
    for ds in DATASETS:
        lines = Path(args.data_mapping_dir, f"{ds}_mapping.txt").read_text().split("\n")
        files = [ln.split() for ln in lines if ln.strip()]
        picked = [f for f in files if int(f[4]) % STEP == 0] or files[:1]
        per_group[ds] = {"n_files": len(files), "n_sampled": len(picked)}
        rows += [("data", ds, int(f[2]), int(f[3]), int(f[4])) for f in picked]
    for p in sorted(Path(args.mc_mapping_dir).glob("mapping_*.txt")):
        files = [ln.split() for ln in p.read_text().split("\n") if ln.strip()]
        rid = files[0][1]
        picked = [f for f in files if int(f[2]) % STEP == 0] or files[:1]
        per_group[rid] = {"n_files": len(files), "n_sampled": len(picked)}
        rows += [("mc", "MC", int(f[1]), int(f[2]), int(f[2])) for f in picked]

    Path(args.out_mapping).write_text(
        "".join(f"{i} {k} {lab} {rid} {fi} {ix}\n" for i, (k, lab, rid, fi, ix) in enumerate(rows)))
    Path(args.out_json).write_text(json.dumps({
        "rule": f"index % {STEP} == 0 (data: per-dataset job index; MC: file_index), >= 1 per group",
        "per_group": per_group, "n_jobs": len(rows),
        "files": [{"idx": i, "kind": k, "label": lab, "record_id": rid, "file_index": fi, "index": ix}
                  for i, (k, lab, rid, fi, ix) in enumerate(rows)],
    }, indent=1))
    for g, v in per_group.items():
        print(f"{g:<12} {v['n_sampled']:>3} of {v['n_files']}")
    print(f"total {len(rows)} jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
