#!/usr/bin/env python
"""
Full MC run: write one PBS mapping file per record, in the format
cluster/pbs_mc_pilot.sh reads ("<array_index> <record_id> <file_index>",
array index 1-based and contiguous). The file list is re-read live from the
CERN portal and must match the 17 Oct sweep (fullrun_inputs_20261017.json)
in count, or this stops.

--exclude R:F[,R:F...] leaves named files out (ONLY on Matan's decision;
none by default). Writes the mapping files and nothing else.

Run:
    python studies/cms_mc_weights_v3/fullrun_prep/make_fullrun_mappings.py \
        --out-dir <work>/mappings [--records 67993,75589] [--exclude 75589:98]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

SWEEP = REPO_ROOT / "studies" / "cms_mc_weights_v3" / "evidence" / "fullrun_inputs_20261017.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--records", default=None)
    ap.add_argument("--exclude", default="")
    args = ap.parse_args()
    sweep = json.loads(SWEEP.read_text())["records"]
    records = [r.strip() for r in args.records.split(",")] if args.records else list(sweep)
    exclude = {tuple(int(x) for x in s.split(":")) for s in args.exclude.split(",") if s}
    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for rid in records:
        urls = fetch_file_list(int(rid))
        if len(urls) != sweep[rid]["n_files"]:
            raise SystemExit(f"STOP: record {rid} has {len(urls)} files on the portal now, "
                             f"{sweep[rid]['n_files']} in the 17 Oct sweep")
        for i, u in enumerate(urls):
            if u != sweep[rid]["files"][i]["url"]:
                raise SystemExit(f"STOP: record {rid} file {i} URL changed since the sweep")
        idx = [i for i in range(len(urls)) if (int(rid), i) not in exclude]
        lines = [f"{k} {rid} {fi}" for k, fi in enumerate(idx, start=1)]
        (out / f"mapping_{rid}.txt").write_text("\n".join(lines) + "\n")
        print(f"{rid}: {len(lines)} jobs (-J 1-{len(lines)})"
              + (f", excluded {sorted(f for r, f in exclude if r == int(rid))}" if len(idx) < len(urls) else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
