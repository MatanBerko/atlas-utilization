#!/usr/bin/env python
"""Full run 25 Oct 2026, step 1: quote the NanoAOD branch titles of the
muon and electron ID branches, read from real files (one data, one MC).

Reads only the branch list / titles (no event data). Run inside a PBS job.

    python branch_titles.py --record 30521 --file-index 0 --record 67801 --file-index 0 --out titles.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import uproot  # noqa: E402

from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

BRANCHES = ("Muon_looseId", "Muon_mediumId", "Muon_pfRelIso04_all", "Electron_cutBased")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record", type=int, action="append", required=True)
    p.add_argument("--file-index", type=int, action="append", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    result = []
    for rid, fi in zip(args.record, args.file_index):
        url = fetch_file_list(rid)[fi]
        with uproot.open(url) as f:
            tree = f["Events"]
            entry = {"record_id": rid, "file_index": fi, "url": url, "branches": {}}
            for b in BRANCHES:
                if b in tree:
                    br = tree[b]
                    entry["branches"][b] = {"present": True, "title": br.title,
                                            "interpretation": str(br.interpretation)}
                else:
                    entry["branches"][b] = {"present": False}
        result.append(entry)
        print(json.dumps(entry, indent=2))
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
