#!/usr/bin/env python3
"""
dup_rate_probe.py - measure the real SingleElectron / SingleMuon event overlap.

The pipeline's cross-record de-duplication keys on (run, luminosityBlock, event).
The 2-file smoke test only found ~0.003% overlap because those files barely
shared lumisections. This probe answers "what is the true overlap" cheaply: it
reads ONLY the scalar branches run / luminosityBlock / event (plus the nMuon /
nElectron counters) - no particle kinematics, no mass-calc - so it covers far
more files per record than a full parse fits in memory.

Memory-frugal: one run era at a time. It builds the SingleMuon key set for the
era (the higher-priority "keep" side), then streams the SingleElectron files and
counts how many of their events land in that set. Peak memory ~ one record's
key set.

Per era (G: 30529 vs 30530, H: 30562 vs 30563) it reports:
  * raw overlap: SingleElectron events whose (run,lumi,event) is also in the
    SingleMuon set, as a fraction of all SingleElectron events. This is the
    "same collision event is in both datasets" rate the ~2% expectation is about.
  * count-proxy overlap: same, but SE side restricted to >=1 electron and the
    SM set restricted to >=1 muon (counters only - NO pt/eta cuts). Upper bound
    on what the pipeline's post-selection de-dup would remove.

Usage:
    python scripts/dup_rate_probe.py --files-per-record 15 --out probe.txt
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import uproot

from services.metadata.fetcher import MetadataFetcher

ERAS = {
    "Run2016G": {"electron": 30529, "muon": 30530},
    "Run2016H": {"electron": 30562, "muon": 30563},
}


def _keys(arr) -> np.ndarray:
    run = np.asarray(arr["run"], dtype=object)
    lumi = np.asarray(arr["luminosityBlock"], dtype=object)
    evt = np.asarray(arr["event"], dtype=object)
    return (run << 96) | (lumi << 64) | evt


def _fetch_urls(record_id: int, emit, attempts: int = 6):
    """_fetch_files_for_record with retry - the opendata.cern.ch metadata host
    resolves intermittently from inside Docker."""
    fetcher = MetadataFetcher()
    for a in range(1, attempts + 1):
        try:
            return fetcher._fetch_files_for_record(record_id)
        except Exception as e:
            emit(f"    (fetch {record_id} attempt {a}/{attempts}: "
                 f"{type(e).__name__}; retrying)")
            time.sleep(10)
    raise RuntimeError(f"could not fetch file list for record {record_id}")


def _iter_file_arrays(record_id: int, n_files: int, emit):
    urls = _fetch_urls(record_id, emit)[:n_files]
    for i, url in enumerate(urls, 1):
        try:
            with uproot.open(url) as f:
                arr = f["Events"].arrays(
                    ["run", "luminosityBlock", "event", "nMuon", "nElectron"],
                    library="np",
                )
            yield i, len(urls), arr
        except Exception as e:
            emit(f"    !! {record_id} file {i}: {type(e).__name__}: {str(e)[:100]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files-per-record", type=int, default=15)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    n = args.files_per_record

    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    t0 = time.time()
    emit("=" * 78)
    emit(f"SingleElectron / SingleMuon event-overlap probe  "
         f"({n} files/record, id branches only)")
    emit("=" * 78)

    for era, recs in ERAS.items():
        emit(f"\n[{era}]  SingleElectron {recs['electron']}  vs  SingleMuon {recs['muon']}")

        # --- build the SingleMuon key sets for this era ---
        mu_all: set[int] = set()
        mu_withmu: set[int] = set()
        mu_events = mu_files = 0
        for i, tot, arr in _iter_file_arrays(recs["muon"], n, emit):
            k = _keys(arr)
            mu_events += len(k)
            mu_files += 1
            mu_all.update(int(x) for x in k)
            hm = np.asarray(arr["nMuon"]) >= 1
            mu_withmu.update(int(x) for x in k[hm])
            emit(f"    muon {recs['muon']} file {i}/{tot}: {len(k):,} events "
                 f"(set now {len(mu_all):,})")

        # --- stream SingleElectron, count hits against the muon sets ---
        se_events = se_files = 0
        se_withe = 0
        raw_hits = proxy_hits = 0
        for i, tot, arr in _iter_file_arrays(recs["electron"], n, emit):
            k = _keys(arr)
            se_events += len(k)
            se_files += 1
            he = np.asarray(arr["nElectron"]) >= 1
            se_withe += int(he.sum())
            for x, has_e in zip(k.tolist(), he.tolist()):
                xi = int(x)
                if xi in mu_all:
                    raw_hits += 1
                if has_e and xi in mu_withmu:
                    proxy_hits += 1
            emit(f"    electron {recs['electron']} file {i}/{tot}: {len(k):,} events "
                 f"(raw hits {raw_hits:,}, proxy hits {proxy_hits:,})")

        raw_frac = raw_hits / se_events if se_events else 0.0
        proxy_frac = proxy_hits / se_withe if se_withe else 0.0
        emit(f"\n  {era} RESULT:")
        emit(f"    SingleElectron {recs['electron']}: {se_files} files, {se_events:,} events "
             f"({se_withe:,} with >=1 electron)")
        emit(f"    SingleMuon     {recs['muon']}: {mu_files} files, {mu_events:,} events "
             f"({len(mu_all):,} unique keys)")
        emit(f"    raw overlap:         {raw_hits:,} / {se_events:,} = "
             f"{raw_frac*100:.3f}% of SingleElectron events")
        emit(f"    count-proxy overlap: {proxy_hits:,} / {se_withe:,} = "
             f"{proxy_frac*100:.3f}%  (>=1e vs >=1mu, no pt/eta cuts -> upper bound "
             f"on pipeline de-dup)")
        del mu_all, mu_withmu

    emit(f"\nprobe wall time: {time.time()-t0:.0f}s")
    emit("=" * 78)

    if args.out:
        with open(args.out, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        print(f"written: {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
