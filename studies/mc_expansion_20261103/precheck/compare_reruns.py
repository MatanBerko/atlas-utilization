#!/usr/bin/env python
"""Reuse evidence (task A1 step 3/4): are the 3 Nov re-runs of file 0 of the 13 delivered samples
identical to the 25 Oct full-run outputs?

For each record: job_metadata.json compared key by key (volatile keys -- creation time, elapsed
times, commit -- reported, not compared), and every SQLite shard compared table by table (row count
and a SHA-256 of the rows in a canonical order). The 25 Oct shards are READ ONLY: each is first
copied to $TMPDIR and opened from the copy. Run in a PBS job (io=25):

    python studies/mc_expansion_20261103/precheck/compare_reruns.py --new <runs_old13> \
        --old /storage/.../work/fullrun_20261025/mc/runs --out <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

RECORDS = [67801, 67993, 35669, 35631, 64895, 64839, 72676, 72752, 75589, 68187, 68073, 37728, 68847]
VOLATILE = {"created_utc", "elapsed_sec", "git_commit", "diagnostics"}


def shard_digest(path: Path, tmp: Path) -> dict:
    copy = tmp / (path.parent.parent.name + "_" + path.name)
    shutil.copy2(path, copy)
    out = {}
    with sqlite3.connect(f"file:{copy}?mode=ro", uri=True) as con:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        for t in tables:
            cols = [r[1] for r in con.execute(f'PRAGMA table_info("{t}")')]
            order = ", ".join(f'"{c}"' for c in cols)
            h = hashlib.sha256()
            n = 0
            for row in con.execute(f'SELECT * FROM "{t}" ORDER BY {order}'):
                h.update(repr(row).encode())
                n += 1
            out[t] = {"rows": n, "sha256": h.hexdigest()}
    copy.unlink()
    return out


def diff_meta(a, b, prefix=""):
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if not prefix and k in VOLATILE:
                continue
            if k not in a or k not in b:
                diffs.append(f"{prefix}{k}: only in {'new' if k in a else 'old'}")
            else:
                diffs += diff_meta(a[k], b[k], f"{prefix}{k}.")
    elif a != b:
        diffs.append(f"{prefix[:-1]}: {str(a)[:80]} != {str(b)[:80]}")
    return diffs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True)
    ap.add_argument("--old", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
    res = {}
    for rid in RECORDS:
        nd, od = Path(a.new) / f"record{rid}" / "job_0", Path(a.old) / f"record{rid}" / "job_0"
        mn, mo = (json.loads((d / "job_metadata.json").read_text()) for d in (nd, od))
        r = {"metadata_differences": diff_meta(mn, mo),
             "volatile": {k: [mn.get(k) if k != "diagnostics" else "(skipped)", mo.get(k) if k != "diagnostics" else "(skipped)"]
                          for k in ("git_commit", "created_utc", "elapsed_sec", "diagnostics")},
             "shards": {}}
        names = sorted({p.name for p in nd.glob("*.sqlite")} | {p.name for p in od.glob("*.sqlite")})
        for n in names:
            if not (nd / n).exists() or not (od / n).exists():
                r["shards"][n] = "MISSING in " + ("new" if not (nd / n).exists() else "old")
                continue
            dn, do = shard_digest(nd / n, tmp), shard_digest(od / n, tmp)
            r["shards"][n] = "IDENTICAL" if dn == do else {"new": dn, "old": do}
        r["identical"] = not r["metadata_differences"] and all(v == "IDENTICAL" for v in r["shards"].values())
        res[str(rid)] = r
        print(rid, "IDENTICAL" if r["identical"] else "DIFFERENT", r["metadata_differences"][:5], flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    out = {"what": "3 Nov re-run of file 0 vs the 25 Oct full-run output, 13 delivered records",
           "all_identical": all(v["identical"] for v in res.values()), "records": res}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print("ALL IDENTICAL" if out["all_identical"] else "NOT ALL IDENTICAL")


if __name__ == "__main__":
    main()
