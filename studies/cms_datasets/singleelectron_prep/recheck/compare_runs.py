#!/usr/bin/env python
"""
b-tag re-check (19 Oct 2026): prove the study-only override is inert at the
default value. Compares a NORMAL driver run with a wrapper run at
--btag-wp 0.2598 on the same file.

Every file present in the normal run is compared byte for byte. SQLite shards
that differ in bytes are then compared table by table (every row, ordered).
job_metadata.json is compared key by key; only keys that record WHEN or HOW
LONG ('created_utc', 'elapsed_sec') are allowed to differ. Files only in the
wrapper run (the wrapper's debug_events.csv) are listed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

VOLATILE = {"created_utc", "elapsed_sec"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sqlite_rows(p: Path) -> dict:
    with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as c:
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {t: hashlib.sha256(repr(sorted(c.execute(f"SELECT * FROM {t}").fetchall(), key=repr)).encode()).hexdigest()
                for t in tables}


def json_diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k in VOLATILE:
                continue
            out += json_diff(a.get(k), b.get(k), f"{path}/{k}")
        return out
    return [] if a == b else [path]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--normal", required=True)
    ap.add_argument("--wrapped", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    n, w = Path(args.normal), Path(args.wrapped)
    res = {"label": args.label, "files": {}, "only_in_wrapped": sorted(
        str(p.relative_to(w)) for p in w.rglob("*") if p.is_file() and not (n / p.relative_to(w)).exists())}
    ok = True
    for p in sorted(x for x in n.rglob("*") if x.is_file()):
        rel = p.relative_to(n)
        q = w / rel
        r = {"in_wrapped": q.exists()}
        if q.exists():
            r["bytes_identical"] = sha(p) == sha(q)
            if not r["bytes_identical"]:
                if p.suffix == ".sqlite":
                    a, b = sqlite_rows(p), sqlite_rows(q)
                    r["tables_identical"] = a == b
                    r["tables_differing"] = sorted(t for t in set(a) | set(b) if a.get(t) != b.get(t))
                    ok &= r["tables_identical"]
                elif p.suffix == ".json":
                    d = json_diff(json.loads(p.read_text()), json.loads(q.read_text()))
                    r["json_keys_differing_besides_volatile"] = d
                    ok &= not d
                else:
                    ok = False
        else:
            ok = False
        res["files"][str(rel)] = r
    res["verdict_identical"] = ok
    res["n_files_bytes_identical"] = sum(1 for r in res["files"].values() if r.get("bytes_identical"))
    res["n_files"] = len(res["files"])
    Path(args.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "files"}, indent=1))
    for f, r in res["files"].items():
        print(f"  {f}: {r}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
