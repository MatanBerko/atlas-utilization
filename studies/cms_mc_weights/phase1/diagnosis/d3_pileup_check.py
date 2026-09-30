#!/usr/bin/env python
"""
Diagnosis round -- D3: pileup check.

PV_npvsGood is NOT among selection.NEEDED_BRANCHES (studies/m0m1j0_cms/
selection.py), so neither the data coverage-shard production nor the
phase-1 MC per-job outputs carry it -- confirmed by inspecting
NEEDED_BRANCHES directly, not assumed. Per the task's own instruction
("if it is not available in data, say so"), this script does NOT
reprocess the 94M-event DoubleMuon production to add it; D2's audit
reports this absence explicitly instead.

This script DOES report the MC Pileup_nTrueInt mean (a generator-truth
quantity, one small branch, unconditional on any selection) via a direct,
lightweight, read-only read of that single branch across the exact same
file lists already used for phase-1's DY (35671) and TTTo2L2Nu (67801)
samples (recovered from each job's own job_metadata.json file_url --
not a fresh file-list fetch), both a plain mean and a genWeight*L1-
weighted mean (using each sample's own per_file_normalization_factor from
merge_mc_summary.json, i.e. the SAME weight phase-1/D1 already use).
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

MC_WORK_BASE = "/storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1"
SAMPLES = {"35671": "DYJetsToLL_M-50_madgraphMLM", "67801": "TTTo2L2Nu"}
READ_CHUNK_SIZE = 500_000


def main():
    out = {}
    for rid, name in SAMPLES.items():
        summary_path = REPO_ROOT / "studies/cms_mc_weights/phase1" / rid / "merge_mc_summary.json"
        norm = json.loads(summary_path.read_text(encoding="utf-8"))["per_file_normalization_factor"]

        job_dirs = sorted(
            glob.glob(f"{MC_WORK_BASE}/{rid}/job_*/"),
            key=lambda p: int(p.rstrip("/").rsplit("_", 1)[1]),
        )
        n_total = 0
        sum_pu = 0.0
        sum_w = 0.0
        sum_pu_w = 0.0
        n_files = 0
        missing_branch_files = []
        for jd in job_dirs:
            meta_path = Path(jd, "job_metadata.json")
            if not meta_path.is_file():
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            file_url = meta["file_url"]
            n_files += 1
            tree = uproot.open(file_url)["Events"]
            if "Pileup_nTrueInt" not in tree.keys():
                missing_branch_files.append(file_url)
                continue
            n_entries = tree.num_entries
            for start in range(0, n_entries, READ_CHUNK_SIZE):
                stop = min(start + READ_CHUNK_SIZE, n_entries)
                arrs = tree.arrays(["Pileup_nTrueInt", "genWeight", "L1PreFiringWeight_Nom"],
                                    entry_start=start, entry_stop=stop, library="np")
                pu = arrs["Pileup_nTrueInt"].astype(np.float64)
                gw = arrs["genWeight"].astype(np.float64)
                l1 = arrs["L1PreFiringWeight_Nom"].astype(np.float64)
                w = gw * l1 * norm
                n_total += pu.size
                sum_pu += pu.sum()
                sum_w += w.sum()
                sum_pu_w += (pu * w).sum()
            print(f"  {rid} file {file_url.rsplit('/', 1)[-1]}: read", flush=True)

        out[rid] = {
            "name": name,
            "n_files_read": n_files,
            "n_files_missing_pileup_branch": len(missing_branch_files),
            "n_events_total": n_total,
            "pileup_nTrueInt_mean_unweighted": (sum_pu / n_total) if n_total > 0 else None,
            "pileup_nTrueInt_mean_weighted": (sum_pu_w / sum_w) if sum_w > 0 else None,
        }
        print(json.dumps(out[rid], indent=2))

    out["_note"] = (
        "PV_npvsGood is not read by either the DoubleMuon data production "
        "(studies/cms_coverage/cluster/run_coverage_on_file.py) or the phase-1 "
        "MC driver (run_m0m1j0_on_mc_file_v2.py) -- confirmed absent from "
        "selection.NEEDED_BRANCHES. A true data-vs-MC PV_npvsGood comparison "
        "at the Z peak is therefore NOT possible without reprocessing the "
        "full DoubleMuon production, which is out of scope for this "
        "diagnosis round; this is reported as a verification gap, not "
        "silently skipped."
    )
    out_path = REPO_ROOT / "studies/cms_mc_weights/phase1/diagnosis/d3_pileup_result.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
