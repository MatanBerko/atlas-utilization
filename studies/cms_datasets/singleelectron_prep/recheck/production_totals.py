#!/usr/bin/env python
"""
b-tag re-check (19 Oct 2026), Part 2: per-file numbers of the EXISTING
productions (read-only; JSON only, no ROOT) -- the denominators for the
sample fractions and the scale factors of the projection, and the per-file
reference the sample's 0.2598 runs must reproduce.

  data: output/cms_datasets/runs_matched4_full_20261007/<Dataset>/job_<n>/job_metadata.json
  MC:   work/fullrun_20261017/runs/record<rid>/job_<n>/job_metadata.json
        + samples[rid].normalisation_factor from build_default/fullrun_build_report.json

Writes one JSON to stdout-named --out.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

B = Path("/storage/agrp/berkom/atlas-utilization")
DATA = B / "output/cms_datasets/runs_matched4_full_20261007"
MC = B / "work/fullrun_20261017"
DATASETS = ("DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG")


def essentials(m: dict) -> dict:
    r4 = m.get("rare4_diagnostics") or {}
    return {"file_index": m.get("file_index"), "record_id": m.get("record_id"),
            "n_read": m.get("n_read"), "n_after_gate": m.get("n_after_gate"),
            "n_exclusive": m.get("n_exclusive"),
            "rare4_kept": r4.get("n_kept_le4_lepton_bjet"),
            "rare4_incl": r4.get("final_state_label_event_counts_inclusive"),
            "rare4_excl": r4.get("final_state_label_event_counts_exclusive")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="-")
    args = ap.parse_args()
    out = {"data": {}, "mc": {}, "mc_norm": {}}
    for ds in DATASETS:
        for line in (DATA / f"{ds}_mapping.txt").read_text().split("\n"):
            if not line.strip():
                continue
            _i, _d, rid, fi, job = line.split()
            m = json.loads((DATA / ds / f"job_{job}" / "job_metadata.json").read_text())
            out["data"].setdefault(ds, {})[job] = essentials(m)
    for p in sorted((MC / "mappings").glob("mapping_*.txt")):
        for line in p.read_text().split("\n"):
            if not line.strip():
                continue
            _i, rid, fi = line.split()
            m = json.loads((MC / "runs" / f"record{rid}" / f"job_{fi}" / "job_metadata.json").read_text())
            out["mc"].setdefault(rid, {})[fi] = essentials(m)
    rep = json.loads((MC / "build_default/fullrun_build_report.json").read_text())
    for rid, s in rep["samples"].items():
        out["mc_norm"][rid] = {"normalisation_factor": s["normalisation_factor"],
                               "physics_short": s["physics_short"],
                               "excluded_files": [e["file_index"] for e in s["per_file_sigma_w"]
                                                  if str(e.get("verdict", "")).startswith("EXCLUDED")]}
    txt = json.dumps(out)
    if args.out == "-":
        print(txt)
    else:
        Path(args.out).write_text(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
