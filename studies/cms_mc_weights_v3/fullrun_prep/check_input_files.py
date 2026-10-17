#!/usr/bin/env python
"""
Full-run preparation (17 Oct 2026), Part C2/C3: read-only consistency check
of every input file of the 13 full-run records.

Per file:
  * Events.num_entries vs Runs.genEventCount (bookkeeping written at
    production time);
  * sum(genWeight) over ALL events vs Runs.genEventSumw -- exactly the
    builder's per-file Sigma-w self-check (tolerance 1e-6), so this predicts
    which files the full-run build would exclude. Reading the whole genWeight
    branch also decompresses every basket of it: a truncated file fails here;
  * the file's size on EOS (xrootd stat) vs the size the CERN portal lists.
Per record: sum of num_entries vs the portal's number_events.
The portal publishes NO per-file event count (checked 17 Oct 2026: the file
index carries uri, size, adler32 checksum only).

--checksum-files R:F[,R:F...] additionally streams those files and compares
their adler32 with the portal's.

Read-only: opens files over xrootd, writes one JSON.

Run:
    python studies/cms_mc_weights_v3/fullrun_prep/check_input_files.py \
        --out <json> [--records 75589] [--checksum-files 75589:98] [--workers 8]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import numpy as np
import requests

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import uproot  # noqa: E402
from XRootD import client as xrd  # noqa: E402

from studies.m0m1j0_cms.design_checks.common import (  # noqa: E402
    CMS_RECID_FILEPAGE_URL, fetch_record_number_events,
)

FULL_RUN = [67801, 67993, 35669, 35631, 64895, 64839, 72676, 72752, 75589,
            68187, 68073, 37728, 68847]
SIGMA_W_TOLERANCE = 1e-6   # = build_mc_delivery.SIGMA_W_TOLERANCE


def portal_files(rid: int) -> list[dict]:
    """The portal's file list, in the same order fetch_file_list uses."""
    d = requests.get(CMS_RECID_FILEPAGE_URL.format(rid), timeout=60).json()
    return [f for idx in d["index_files"]["files"] for f in idx["files"]]


def eos_size(uri: str) -> int | None:
    host, path = uri.split("//", 2)[1], "/" + uri.split("//", 2)[2]
    st, info = xrd.FileSystem(f"root://{host}").stat(path)
    return int(info.size) if st.ok else None


def adler32_stream(uri: str, chunk: int = 64 * 1024 * 1024) -> str:
    f = xrd.File()
    st, _ = f.open(uri)
    if not st.ok:
        raise RuntimeError(st.message)
    a, off = 1, 0
    while True:
        st, data = f.read(offset=off, size=chunk)
        if not st.ok:
            raise RuntimeError(st.message)
        if not data:
            break
        a = zlib.adler32(data, a)
        off += len(data)
    f.close()
    return f"{a & 0xffffffff:08x}"


def check_file(rid: int, idx: int, pf: dict) -> dict:
    t0 = time.perf_counter()
    out = {"record": rid, "file_index": idx, "uri": pf["uri"],
           "portal_size": int(pf["size"]), "portal_checksum": pf.get("checksum")}
    try:
        with uproot.open(pf["uri"]) as f:
            ev = f["Events"]
            runs = f["Runs"]
            out["num_entries"] = int(ev.num_entries)
            out["runs_gen_event_count"] = int(np.asarray(runs["genEventCount"].array(library="np")).sum())
            out["runs_gen_event_sumw"] = float(np.asarray(runs["genEventSumw"].array(library="np"),
                                                          dtype=np.float64).sum())
            gw = np.asarray(ev["genWeight"].array(library="np"), dtype=np.float64)
            out["n_genweight_read"] = int(gw.size)
            out["sum_genweight"] = float(gw.sum())
        out["count_matches"] = out["num_entries"] == out["runs_gen_event_count"]
        rel = abs(out["sum_genweight"] - out["runs_gen_event_sumw"]) / abs(out["runs_gen_event_sumw"])
        out["sigma_w_rel_diff"] = rel
        out["sigma_w_check_passes"] = rel <= SIGMA_W_TOLERANCE
        out["read_ok"] = out["n_genweight_read"] == out["num_entries"]
    except Exception as exc:  # report, never hide
        out["read_ok"] = False
        out["error"] = f"{type(exc).__name__}: {exc}"
    out["eos_size"] = eos_size(pf["uri"])
    out["size_matches_portal"] = out["eos_size"] == out["portal_size"]
    out["seconds"] = round(time.perf_counter() - t0, 1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--records", default=None)
    ap.add_argument("--checksum-files", default="")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    records = [int(r) for r in args.records.split(",")] if args.records else FULL_RUN
    want_ck = {tuple(int(x) for x in s.split(":")) for s in args.checksum_files.split(",") if s}

    result = {"what": "read-only consistency check of the full-run input files",
              "generated_utc": datetime.now(timezone.utc).isoformat(),
              "sigma_w_tolerance": SIGMA_W_TOLERANCE, "records": {}}
    for rid in records:
        pfs = portal_files(rid)
        portal = fetch_record_number_events(rid)
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            files = list(ex.map(lambda a: check_file(rid, *a), enumerate(pfs)))
        for f in files:
            if (rid, f["file_index"]) in want_ck:
                f["eos_adler32"] = adler32_stream(f["uri"])
                f["checksum_matches_portal"] = f"adler32:{f['eos_adler32']}" == f["portal_checksum"]
        bad = [f for f in files if not (f.get("read_ok") and f.get("count_matches")
                                         and f.get("sigma_w_check_passes") and f["size_matches_portal"])]
        result["records"][str(rid)] = {
            "n_files": len(files), "portal_number_files": portal["number_files"],
            "sum_num_entries": sum(f.get("num_entries", 0) for f in files),
            "portal_number_events": portal["number_events"],
            "sum_matches_portal": sum(f.get("num_entries", 0) for f in files) == portal["number_events"],
            "files_with_any_mismatch": [f["file_index"] for f in bad],
            "files": files,
        }
        print(f"[{rid}] {len(files)} files, sum entries {result['records'][str(rid)]['sum_num_entries']:,} "
              f"(portal {portal['number_events']:,}); mismatches: "
              f"{[(f['file_index'], {k: f.get(k) for k in ('count_matches', 'sigma_w_check_passes', 'size_matches_portal', 'read_ok', 'error') if f.get(k) is not True}) for f in bad]}",
              flush=True)
    pathlib.Path(args.out).write_text(json.dumps(result, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
