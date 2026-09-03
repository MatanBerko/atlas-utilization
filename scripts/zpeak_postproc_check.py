#!/usr/bin/env python3
"""
zpeak_postproc_check.py - before/after post-processing check for the CMS
electron-pair Z-peak cleanup.

Companion to scripts/zpeak_check.py. That script only looks at the RAW
invariant-mass arrays (post-processing OFF) and confirms the di-electron mass
piles up at ~91 GeV. This script additionally reads the POST-PROCESSED arrays
and confirms the post-processing stage still strips that Z region out:

  * raw   im_arrays/*.sqlite            -> signatures ending  _IM_e0e1
  * final im_arrays_processed/*.sqlite  -> signatures ending  _IM_e0e1_main
                                          and                 _IM_e0e1_outliers

Expected (unchanged) behaviour: post_processing_pipeline._apply_z_peak_cut drops
every same-flavour di-lepton mass below `z_peak_cutoff` (default 115.0 GeV), so
the `_main` array must contain NOTHING below 115 GeV and in particular nothing
near the Z mass, even though the raw array has a strong Z peak there.

Usage:
    python scripts/zpeak_postproc_check.py --run-dir output/<run>
    python scripts/zpeak_postproc_check.py            # newest run under ./output
"""
from __future__ import annotations

import argparse
import io
import re
import sqlite3
import sys
import zlib
from pathlib import Path

import numpy as np

Z_MASS = 91.1876
Z_PEAK_CUTOFF = 115.0  # post_processing default; edit if the run overrode it


def _deserialize_array(payload: bytes) -> np.ndarray:
    raw = zlib.decompress(payload)
    return np.load(io.BytesIO(raw), allow_pickle=False)


def find_latest_run_dir(base: str = "./output") -> Path | None:
    base_p = Path(base)
    if not base_p.is_dir():
        return None
    cands = [d for d in base_p.iterdir() if d.is_dir() and (d / "im_arrays").is_dir()]
    if not cands:
        return None
    cands.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return cands[0]


def collect(im_dir: Path, sig_regex: re.Pattern) -> dict[str, np.ndarray]:
    """Return {matched_suffix: concatenated array} over every sqlite shard."""
    out: dict[str, list] = {}
    for shard in sorted(im_dir.glob("*.sqlite")):
        conn = sqlite3.connect(str(shard))
        try:
            rows = conn.execute(
                "SELECT signature, payload FROM array_chunks ORDER BY id"
            ).fetchall()
        finally:
            conn.close()
        for signature, payload in rows:
            m = sig_regex.search(signature)
            if not m:
                continue
            key = m.group(0)
            arr = np.asarray(_deserialize_array(payload), dtype="float64").ravel()
            arr = arr[np.isfinite(arr)]
            out.setdefault(key, []).append(arr)
    return {k: (np.concatenate(v) if v else np.array([])) for k, v in out.items()}


def describe(name: str, arr: np.ndarray) -> None:
    if arr.size == 0:
        print(f"  {name}: (empty)")
        return
    below = int((arr < Z_PEAK_CUTOFF).sum())
    zwin = int(((arr >= 85.0) & (arr <= 97.0)).sum())
    print(f"  {name}: n={arr.size}  min={arr.min():.3f}  max={arr.max():.1f}  "
          f"median={np.median(arr):.1f}")
    print(f"      entries < {Z_PEAK_CUTOFF:.0f} GeV : {below}"
          f"   |   entries in 85-97 GeV (Z window) : {zwin}")
    # coarse histogram 60-160 GeV / 5 GeV
    edges = np.arange(60.0, 165.0, 5.0)
    counts, _ = np.histogram(arr[(arr >= 60) & (arr <= 160)], bins=edges)
    if counts.any():
        peak = int(np.argmax(counts))
        bars = "".join(
            "#" if c == counts.max() else ("+" if c > counts.max() * 0.25 else ".")
            for c in counts
        )
        print(f"      60|{bars}|160  (fullest bin {edges[peak]:.0f}-{edges[peak]+5:.0f} GeV)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--base-output", default="./output")
    args = ap.parse_args()

    run_dir = Path(args.run_dir) if args.run_dir else find_latest_run_dir(args.base_output)
    if run_dir is None or not run_dir.is_dir():
        sys.exit(f"[zpeak_postproc_check] no run dir (looked under {args.base_output!r})")

    raw_dir = run_dir / "im_arrays"
    proc_dir = run_dir / "im_arrays_processed"
    print("=" * 74)
    print("CMS electron-pair Z-peak: BEFORE vs AFTER post-processing")
    print("=" * 74)
    print(f"run dir : {run_dir}")
    print(f"raw     : {raw_dir}")
    print(f"processed: {proc_dir}")
    print(f"z_peak_cutoff assumed: {Z_PEAK_CUTOFF:.1f} GeV  (post-processing default)")
    print()

    raw = collect(raw_dir, re.compile(r"_IM_e0e1$"))
    print(f"BEFORE  (raw im_arrays, signatures *_IM_e0e1)   [{len(raw)} final-state(s)]")
    raw_all = np.concatenate(list(raw.values())) if raw else np.array([])
    describe("e0e1 (all final states, summed)", raw_all)
    print()

    if not proc_dir.is_dir():
        print("AFTER   : no im_arrays_processed/ directory -> post-processing did not run")
        return 1

    main_a = collect(proc_dir, re.compile(r"_IM_e0e1_main$"))
    out_a = collect(proc_dir, re.compile(r"_IM_e0e1_outliers$"))
    print(f"AFTER   (im_arrays_processed, *_IM_e0e1_main)   [{len(main_a)} final-state(s)]")
    main_all = np.concatenate(list(main_a.values())) if main_a else np.array([])
    describe("e0e1_main (all final states, summed)", main_all)
    out_all = np.concatenate(list(out_a.values())) if out_a else np.array([])
    describe("e0e1_outliers (all final states, summed)", out_all)
    print()

    print("-" * 74)
    verdict_ok = True
    if raw_all.size == 0:
        print("INCONCLUSIVE: no raw e0e1 pairs found.")
        verdict_ok = False
    else:
        raw_zwin = int(((raw_all >= 85) & (raw_all <= 97)).sum())
        print(f"raw e0e1 has {raw_zwin} entries in the 85-97 GeV Z window "
              f"({100*raw_zwin/raw_all.size:.0f}% of all raw e0e1).")
    if main_all.size:
        m_below = int((main_all < Z_PEAK_CUTOFF).sum())
        m_zwin = int(((main_all >= 85) & (main_all <= 97)).sum())
        if m_below == 0 and m_zwin == 0:
            print(f"AFTER: e0e1_main has 0 entries below {Z_PEAK_CUTOFF:.0f} GeV and 0 in the "
                  f"Z window -> Z-peak cleanup STILL WORKS as before.")
        else:
            verdict_ok = False
            print(f"AFTER: e0e1_main has {m_below} entries below {Z_PEAK_CUTOFF:.0f} GeV "
                  f"({m_zwin} in the Z window) -> UNEXPECTED, cleanup changed.")
    else:
        print("AFTER: no e0e1_main array -> nothing survived the cut "
              "(also acceptable if raw had only Z-region entries).")
    print("-" * 74)
    print("RESULT:", "PASS - unchanged" if verdict_ok else "CHECK - see above")
    return 0 if verdict_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
