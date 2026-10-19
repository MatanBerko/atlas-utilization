#!/usr/bin/env python
"""
SingleElectron re-check (19 Oct 2026), Part 1A: compare the re-run with the
7 Oct results.

1. Per file: every tnp_<era>_<idx>.json of the re-run vs the 7 Oct one, every
   key compared; only 'elapsed_sec' and 'git_commit' may differ.
2. Aggregated: the re-run's stepB_tnp.json / stepD_thresholds.json (made by
   the UNCHANGED 7 Oct aggregate_tnp.py / aggregate_threshold.py) vs the 7 Oct
   evidence files, key by key (input paths excluded).

Usage:
    python compare_7oct.py --new-dir se/a_0p2598 --old-dir <7 Oct tnp> \
        --new-evidence <dir> --old-evidence <dir> --out <json>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PER_FILE_VOLATILE = {"elapsed_sec", "git_commit"}
AGG_VOLATILE = {"elapsed_sec", "in_dir", "out_json", "out_plots", "stepb_json", "delivery_json", "old_json"}


def diff(a, b, ignore, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k in ignore:
                continue
            out += diff(a.get(k), b.get(k), ignore, f"{path}/{k}")
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, ignore, f"{path}[{i}]")
        return out
    return [] if a == b else [path]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new-dir", required=True)
    ap.add_argument("--old-dir", required=True)
    ap.add_argument("--new-evidence", required=True)
    ap.add_argument("--old-evidence", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    new = {p.name: p for p in Path(args.new_dir).glob("tnp_*.json")}
    old = {p.name: p for p in Path(args.old_dir).glob("tnp_*.json")}
    per_file = {}
    for name in sorted(set(new) | set(old)):
        if name not in new or name not in old:
            per_file[name] = {"missing_in": "new" if name not in new else "old"}
            continue
        d = diff(json.loads(old[name].read_text()), json.loads(new[name].read_text()), PER_FILE_VOLATILE)
        per_file[name] = {"identical": not d, "differing_keys": d[:50], "n_differing": len(d)}
    agg = {}
    for f in ("stepB_tnp.json", "stepD_thresholds.json"):
        a = json.loads(Path(args.old_evidence, f).read_text())
        b = json.loads(Path(args.new_evidence, f).read_text())
        d = diff(a, b, AGG_VOLATILE)
        agg[f] = {"identical": not d, "differing_keys": d[:100], "n_differing": len(d)}
    res = {
        "n_files_old": len(old), "n_files_new": len(new),
        "n_files_identical": sum(1 for v in per_file.values() if v.get("identical")),
        "n_files_missing": sum(1 for v in per_file.values() if "missing_in" in v),
        "files_not_identical": {k: v for k, v in per_file.items() if not v.get("identical")},
        "differing_keys_union": sorted({k for v in per_file.values() for k in v.get("differing_keys", [])}
                                       , key=str)[:100],
        "aggregated": agg,
    }
    Path(args.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "files_not_identical"}, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
