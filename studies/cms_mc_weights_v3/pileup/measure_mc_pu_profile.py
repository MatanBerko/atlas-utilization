#!/usr/bin/env python
"""
Part A2: the MC pileup profile of a pilot sample, over ALL GENERATED EVENTS.

The denominator of a pileup reweighting must be the `Pileup_nTrueInt`
distribution of every generated event of the sample, not of the events the
selection happened to store -- the selection sculpts pileup, so using stored
events would build the bias into the weight.

Reads exactly two branches (`Pileup_nTrueInt`, `genWeight`) from every file of
one record and histograms nTrueInt on the official weight file's own grid
(unit-width bins, 0..99), both unweighted and genWeight-weighted. Nothing else
is read and nothing is written except one small JSON.

Run (one job per sample):
    python studies/cms_mc_weights_v3/pileup/measure_mc_pu_profile.py \
        --record 35669 --out <work>/evidence/mc_pu_profile_35669.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime, timezone

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import uproot  # noqa: E402

from studies.cms_mc_weights_v3.cluster.measure_pilot_inputs import (  # noqa: E402
    PILOT_RECORDS,
)
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

# The official weight file's own binning: 99 unit-width bins over [0, 99).
EDGES = np.arange(0.0, 100.0, 1.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-files", type=int, default=None,
                    help="debug only; the real run reads every file")
    args = ap.parse_args()

    rid = str(args.record)
    if rid not in PILOT_RECORDS:
        raise SystemExit(f"{rid} is not a pilot record ({sorted(PILOT_RECORDS)})")

    urls = fetch_file_list(int(rid))
    expected = PILOT_RECORDS[rid]["expected_files"]
    if len(urls) != expected:
        raise SystemExit(
            f"record {rid}: portal lists {len(urls)} files, pilot expects {expected}")
    if args.max_files:
        urls = urls[: args.max_files]

    n_bins = len(EDGES) - 1
    counts = np.zeros(n_bins, dtype=np.float64)       # unweighted event counts
    sumw = np.zeros(n_bins, dtype=np.float64)         # genWeight-weighted
    n_events = 0
    total_genw = 0.0
    n_neg = 0
    per_file = []
    n_above_range = 0
    t0 = time.perf_counter()

    for idx, url in enumerate(urls):
        t1 = time.perf_counter()
        n_this = 0
        gw_this = 0.0
        with uproot.open(url) as f:
            tree = f["Events"]
            for chunk in tree.iterate(["Pileup_nTrueInt", "genWeight"],
                                      step_size="100 MB", library="np"):
                nti = np.asarray(chunk["Pileup_nTrueInt"], dtype=np.float64)
                gw = np.asarray(chunk["genWeight"], dtype=np.float64)
                c, _ = np.histogram(nti, bins=EDGES)
                w, _ = np.histogram(nti, bins=EDGES, weights=gw)
                counts += c
                sumw += w
                n_this += int(nti.size)
                gw_this += float(gw.sum())
                n_neg += int((gw < 0).sum())
                n_above_range += int((nti >= EDGES[-1]).sum())
        n_events += n_this
        total_genw += gw_this
        per_file.append({"file_index": idx, "n_events": n_this,
                         "sum_genweight": gw_this,
                         "seconds": round(time.perf_counter() - t1, 1)})
        print(f"  [{rid}] file {idx:>3}: {n_this:>9,} events "
              f"({time.perf_counter() - t1:.1f}s)", flush=True)

    out = {
        "what": "Part A2: MC pileup profile over ALL generated events",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "record_id": rid,
        "physics_short": PILOT_RECORDS[rid]["physics_short"],
        "n_files": len(urls),
        "n_events_total": n_events,
        "sum_genweight_total": total_genw,
        "n_events_with_negative_genweight": n_neg,
        "negative_genweight_fraction": (n_neg / n_events) if n_events else None,
        "n_events_with_nTrueInt_at_or_above_99": n_above_range,
        "edges": EDGES.tolist(),
        "counts_unweighted": counts.tolist(),
        "sumw_genweight": sumw.tolist(),
        "mean_nTrueInt_unweighted": float(
            (counts * (EDGES[:-1] + 0.5)).sum() / counts.sum()) if counts.sum() else None,
        "mean_nTrueInt_genweighted": float(
            (sumw * (EDGES[:-1] + 0.5)).sum() / sumw.sum()) if sumw.sum() else None,
        "sweep_seconds": round(time.perf_counter() - t0, 1),
        "per_file": per_file,
    }
    path = pathlib.Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n[{rid}] {n_events:,} events over {len(urls)} files; "
          f"mean nTrueInt (genW) = {out['mean_nTrueInt_genweighted']:.3f}; "
          f"{n_above_range} event(s) at/above nTrueInt 99")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
