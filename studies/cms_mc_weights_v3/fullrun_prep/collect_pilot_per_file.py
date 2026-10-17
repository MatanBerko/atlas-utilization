#!/usr/bin/env python
"""
Full-run preparation (17 Oct 2026), Part D input: the 10 Oct pilot's
per-file measurements (98 files), READ ONLY from the pilot work directory.

Per file: events read, driver wall time, output bytes and file count (from
the job directory), peak RSS and exit status (from the PBS .ER log's
/usr/bin/time -v block; the array index -> file index comes from the pilot's
mapping files). Writes one JSON to --out; nothing is written anywhere else.

Run:
    python studies/cms_mc_weights_v3/fullrun_prep/collect_pilot_per_file.py \
        --pilot-work /storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_pilot_20261011 \
        --out <work>/evidence/pilot_per_file.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

JOBIDS = {"67801": "5208623", "35669": "5208624", "37728": "5208625"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot-work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    w = Path(args.pilot_work)
    files = []
    for rid, jid in JOBIDS.items():
        idx_to_file = {}
        for line in (w / "mappings" / f"mapping_{rid}.txt").read_text().splitlines():
            i, r, f = line.split()
            idx_to_file[int(i)] = int(f)
        for i, fidx in sorted(idx_to_file.items()):
            jd = w / "runs" / f"record{rid}" / f"job_{fidx}"
            meta = json.loads((jd / "job_metadata.json").read_text())
            outs = [p for p in jd.iterdir() if p.is_file()]
            err = w / "logs" / rid / f"{jid}[{i}].pbs.ER"
            text = err.read_text(errors="replace") if err.exists() else ""
            m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)
            x = re.search(r"Exit status: (\d+)", text)
            files.append({
                "record": int(rid), "file_index": fidx, "array_index": i,
                "n_read": meta["n_read"], "elapsed_sec": meta["elapsed_sec"],
                "n_stored": meta.get("n_after_gate"),
                "n_final_state_groups": meta.get("n_final_state_groups"),
                "peak_rss_gb": int(m.group(1)) / 1024 / 1024 if m else None,
                "exit_status": int(x.group(1)) if x else None,
                "output_bytes": sum(p.stat().st_size for p in outs),
                "n_output_files": len(outs),
                "git_commit": meta.get("git_commit"),
            })
    Path(args.out).write_text(json.dumps({"pilot_work": str(w), "files": files}, indent=2))
    print(f"{len(files)} files -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
