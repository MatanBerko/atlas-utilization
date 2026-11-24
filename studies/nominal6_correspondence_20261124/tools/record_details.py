#!/usr/bin/env python
"""Details of the CMS candidate records (read-only public CERN Open Data record API).

Per NanoAOD record id: the NanoAOD record and its MiniAOD parent (relations type isParentOf, as the 27 Oct plan's
fetch_cms_extra.py), both saved raw to evidence/records/<recid>.json.gz. Reported: title, events, files from
distribution, the COMPLETE file count = sum of number_files over all _file_indices (as fetch_file_list_complete,
studies/m0m1j0_cms/design_checks/common.py:96-127 at 6de9d3e) and the number of file entries listed in them, a flag
when the two or distribution.number_files disagree (files listed but not published), the generators named in the
production steps, and the MiniAOD portal cross_section block.

    python record_details.py <recid> [<recid> ...] > evidence/record_details.json
"""
import gzip
import json
import sys
import time
import urllib.request
from pathlib import Path

API = "https://opendata.cern.ch/api/records/{}"
OUT = Path(__file__).resolve().parents[1] / "evidence" / "records"


def fetch(url):
    err = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"{url}: {err}")


def record(recid):
    p = OUT / f"{recid}.json.gz"
    if p.exists():
        with gzip.open(p, "rt") as f:
            return json.load(f)
    rec = fetch(API.format(recid))
    with gzip.open(p, "wt") as f:
        json.dump(rec, f, sort_keys=True)
    return rec


def generators(meta):
    found = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "generators" and isinstance(v, list):
                    found.extend(str(g) for g in v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(meta.get("methodology", {}))
    return sorted(set(found))


def details(recid):
    m = record(recid)["metadata"]
    dist = m.get("distribution", {})
    idx = m.get("_file_indices", [])
    n_index = sum(int(i.get("number_files", 0)) for i in idx)
    n_listed = sum(len(i.get("files") or []) for i in idx)
    par = [r for r in m.get("relations", []) if r.get("type") == "isParentOf"]
    mini = int(par[0]["recid"]) if par else None
    mm = record(mini)["metadata"] if mini else {}
    return {"nano_recid": int(recid), "mini_recid": mini, "title": m.get("title"),
            "mini_title": mm.get("title"), "events": dist.get("number_events"), "files_distribution": dist.get("number_files"),
            "files_complete_index": n_index, "files_listed_in_index_entries": n_listed,
            "files_flag": None if n_index == dist.get("number_files") == n_listed else
            f"distribution {dist.get('number_files')} / index sum {n_index} / listed {n_listed}",
            "size_bytes": dist.get("size"), "generators": generators(m) or generators(mm),
            "portal_cross_section": mm.get("cross_section"), "abstract": (m.get("abstract") or {}).get("description"),
            "link": f"https://opendata.cern.ch/record/{recid}", "mini_link": f"https://opendata.cern.ch/record/{mini}"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    out = {"read": time.strftime("%Y-%m-%d %H:%M %Z"), "records": {}}
    for r in sys.argv[1:]:
        out["records"][r] = details(r)
        d = out["records"][r]
        print(r, d["mini_recid"], d["title"][:80], d["events"], d["files_complete_index"], d["files_flag"],
              (d["portal_cross_section"] or {}).get("total_value"), file=sys.stderr, flush=True)
    json.dump(out, sys.stdout, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
