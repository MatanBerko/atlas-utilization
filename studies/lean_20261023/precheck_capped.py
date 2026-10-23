#!/usr/bin/env python
"""
Read-only pre-check for the coming full run (lean-branch task, step 6).

The #40 builders (data and MC, default --multiplicity-rule upstream40) STOP
when a coverage-capped signature (a mass list randomly trimmed to 500,000
entries in one file, CAPPED::<signature> in the shard) would be merged under
the #40 label. This reads every job_metadata.json of

  --data-runs  the 7 Oct four-dataset data production (<Dataset>/job_<n>/)
  --mc-runs    the 17 Oct MC full run (record<ID>/job_<n>/)

and reports, per dataset / MC sample:
  - number of files, files with n_capped_signatures > 0 (rare4, the version
    the builders read; and any version);
  - which signatures (data: the CAPPED:: keys of the rare4 inclusive shard of
    such a file, opened read-only; MC: mc_capped_signatures_rare4), and
    whether the #40 rule would merge each (upstream limit_particles_in_fs);
  - max_signature_size (rare4) over the files: how close each one is to the trim;
  - the number of files on disk under each runs dir.

Read-only. Writes one JSON. Run as a tiny PBS job (io=1).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sqlite3
import sys
from collections import defaultdict

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from services.calculations import physics_calcs  # noqa: E402

CAP = 500_000
FS_RE = re.compile(r"_FS_([0-9a-z_]+?)_IM_")


def merged_under_40(sig: str):
    m = FS_RE.search(sig)
    if not m:
        return None
    return physics_calcs.limit_particles_in_fs(m.group(1), 4) != m.group(1)


def count_files(root: pathlib.Path) -> int:
    return sum(len(files) + len(dirs) for _r, dirs, files in os.walk(root)) + 1


def scan(groups: dict, shard_name: str | None, mc: bool) -> dict:
    out = {}
    for group, metas in sorted(groups.items()):
        row = {"n_files": len(metas), "n_files_capped_rare4": 0, "n_files_capped_any_version": 0,
               "max_signature_size_rare4": 0, "max_signature_size_file": None,
               "capped_signatures": []}
        for mp in metas:
            m = json.loads(mp.read_text())
            r4 = m.get("rare4_diagnostics") or {}
            size = int(r4.get("max_signature_size_this_job", 0))
            if size > row["max_signature_size_rare4"]:
                row["max_signature_size_rare4"] = size
                row["max_signature_size_file"] = mp.parent.name
            n_any = int(m.get("n_capped_signatures", 0)) + sum(
                int((m.get(f"{v}_diagnostics") or {}).get("n_capped_signatures", 0))
                for v in ("top4", "nonjet4", "rare4"))
            row["n_files_capped_any_version"] += n_any > 0
            if int(r4.get("n_capped_signatures", 0)) > 0:
                row["n_files_capped_rare4"] += 1
                if mc:
                    sigs = sorted((m.get("mc_capped_signatures_rare4") or {}).keys())
                else:
                    conn = sqlite3.connect(f"file:{mp.parent / shard_name}?mode=ro", uri=True)
                    try:
                        sigs = sorted(k[len("CAPPED::"):] for (k,) in conn.execute(
                            "SELECT key FROM shard_metadata WHERE key LIKE 'CAPPED::%'"))
                    finally:
                        conn.close()
                for s in sigs:
                    row["capped_signatures"].append(
                        {"job": mp.parent.name, "signature": s,
                         "would_be_merged_under_40": merged_under_40(s)})
        row["n_capped_signatures_that_would_stop_the_builder"] = sum(
            1 for c in row["capped_signatures"] if c["would_be_merged_under_40"])
        out[group] = row
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-runs", required=True, type=pathlib.Path)
    ap.add_argument("--mc-runs", required=True, type=pathlib.Path)
    ap.add_argument("--registry", type=pathlib.Path,
                    default=REPO_ROOT / "studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = defaultdict(list)
    for mp in sorted(args.data_runs.glob("*/job_*/job_metadata.json")):
        data[mp.parent.parent.name].append(mp)
    mc = defaultdict(list)
    for mp in sorted(args.mc_runs.glob("record*/job_*/job_metadata.json")):
        mc[mp.parent.parent.name].append(mp)
    names = {f"record{rid}": rec.get("physics_short")
             for rid, rec in json.loads(args.registry.read_text())["records"].items()}

    res = {"cap_entries": CAP,
           "data": {"runs_dir": str(args.data_runs),
                    "per_dataset": scan(data, "dataset_shard_rare4_inclusive.sqlite", mc=False),
                    "n_files_on_disk": count_files(args.data_runs)},
           "mc": {"runs_dir": str(args.mc_runs),
                  "per_sample": scan(mc, None, mc=True),
                  "n_files_on_disk": count_files(args.mc_runs)}}
    for rec, row in res["mc"]["per_sample"].items():
        row["physics_short"] = names.get(rec)
    for kind, key in (("data", "per_dataset"), ("mc", "per_sample")):
        rows = res[kind][key].values()
        res[kind]["totals"] = {
            "n_files": sum(r["n_files"] for r in rows),
            "n_files_capped_rare4": sum(r["n_files_capped_rare4"] for r in rows),
            "n_files_capped_any_version": sum(r["n_files_capped_any_version"] for r in rows),
            "n_capped_signatures_rare4": sum(len(r["capped_signatures"]) for r in rows),
            "n_that_would_stop_the_builder": sum(
                r["n_capped_signatures_that_would_stop_the_builder"] for r in rows),
            "max_signature_size_rare4": max(r["max_signature_size_rare4"] for r in rows),
        }
    pathlib.Path(args.out).write_text(json.dumps(res, indent=2))
    print(json.dumps({k: {"totals": v["totals"], "n_files_on_disk": v["n_files_on_disk"]}
                      for k, v in res.items() if k in ("data", "mc")}, indent=1))
    for kind, key in (("data", "per_dataset"), ("mc", "per_sample")):
        for g, r in res[kind][key].items():
            print(kind, g, r.get("physics_short", ""), r["n_files"], "capped(rare4)",
                  r["n_files_capped_rare4"], "max", r["max_signature_size_rare4"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
