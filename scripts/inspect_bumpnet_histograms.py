#!/usr/bin/env python3
"""
inspect_bumpnet_histograms.py - check whether a full pipeline run produced
histograms that are actually usable as BumpNet input.

Diagnostic only; does not modify pipeline code or output. Given a run directory
it does three things:

1. HISTOGRAMS - opens the histogram ROOT file(s) under histograms/ and lists
   every TH1: name (which encodes final state + mass combo), entry count, bin
   count, x-range. Flags each against the BumpNet paper's retention cut
   (arXiv:2501.05603): "Only histograms containing at least 100 events and
   with greater than 30 bins are retained for further analysis."

2. POST-PROCESSING / Z-PEAK - for the same-flavour di-lepton channels
   (IM part e0e1 = ee pair, m0m1 = mumu pair) compares the invariant-mass
   distribution BEFORE post-processing (im_arrays/*.sqlite) with AFTER
   (im_arrays_processed/*.sqlite), and reports what happened to the
   ~91 GeV Z-peak region and to everything below the 115 GeV z_peak_cutoff.

3. FORMAT - reports the ROOT file structure (object classes, naming) so it can
   be compared against what the ATLAS side of this same pipeline emits.

Usage:
    python scripts/inspect_bumpnet_histograms.py --run-dir output/<run>
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sqlite3
import sys
import zlib
from pathlib import Path

import numpy as np

try:
    import uproot
except Exception:  # pragma: no cover
    uproot = None

# BumpNet retention cut (arXiv:2501.05603, sec. on ATLAS application):
BUMPNET_MIN_EVENTS = 100
BUMPNET_MIN_BINS = 30            # paper says "greater than 30"
Z_MASS = 91.1876
Z_WINDOW = (88.0, 94.0)
Z_PEAK_CUTOFF_DEFAULT = 115.0    # post_processing default z_peak_cutoff


# --------------------------------------------------------------------------- #
def _deserialize(payload: bytes) -> np.ndarray:
    return np.load(io.BytesIO(zlib.decompress(payload)), allow_pickle=False)


FS_IM_RE = re.compile(r"_FS_([0-9a-z_]+)_IM_([0-9a-z]+?)(?:_main|_outliers)?$")
_IM_PARTICLES = re.compile(r"([emjgtb])(\d+)")


def same_flavor_dilepton(im_str: str) -> str | None:
    """Return 'ee' / 'mm' if the IM part is a same-flavour lepton pair, else None."""
    letters = [l for l, _ in _IM_PARTICLES.findall(im_str)]
    if letters.count("e") >= 2:
        return "ee"
    if letters.count("m") >= 2:
        return "mm"
    return None


def load_sqlite_signatures(db_path: Path) -> dict[str, np.ndarray]:
    """signature -> concatenated array (all chunks)."""
    out: dict[str, list] = {}
    if not db_path.exists():
        return {}
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute("SELECT signature, payload FROM array_chunks ORDER BY id").fetchall()
    finally:
        con.close()
    for sig, payload in rows:
        out.setdefault(sig, []).append(_deserialize(payload))
    return {k: (np.concatenate(v) if len(v) > 1 else v[0]) for k, v in out.items()}


def fs_im_key(sig: str) -> str:
    m = re.search(r"(_FS_.+)", sig)
    return m.group(1) if m else sig


# --------------------------------------------------------------------------- #
def section_histograms(run_dir: Path) -> None:
    print("=" * 78)
    print("1. HISTOGRAMS  (final ROOT output vs BumpNet retention cut)")
    print("=" * 78)
    hist_dir = run_dir / "histograms"
    roots = sorted(hist_dir.glob("*.root")) if hist_dir.is_dir() else []
    print(f"histograms/ dir      : {hist_dir}  (exists={hist_dir.is_dir()})")
    print(f"ROOT files found     : {[p.name for p in roots] or 'NONE'}")
    if not roots:
        print("\n>>> No histogram ROOT file was produced. Histogram-creation stage "
              "either did not run or failed. See the run log.\n")
        return
    if uproot is None:
        print(">>> uproot not available; cannot read ROOT files here.")
        return

    print(f"\nBumpNet cut: >= {BUMPNET_MIN_EVENTS} entries AND > {BUMPNET_MIN_BINS} bins\n")
    total = passed = 0
    for rp in roots:
        print(f"--- {rp.name} ---")
        f = uproot.open(rp)
        keys = [k for k in f.keys()]
        th1 = []
        for k in keys:
            try:
                obj = f[k]
            except Exception:
                continue
            if hasattr(obj, "values") and hasattr(obj, "axis"):
                th1.append((k, obj))
        if not th1:
            print("   (no TH1 objects)")
        hdr = f"   {'histogram name':<62} {'entries':>10} {'bins':>6} {'x-range':>18}  BumpNet"
        print(hdr)
        for k, obj in th1:
            total += 1
            vals = np.asarray(obj.values())
            entries = float(vals.sum())
            nbins = len(vals)
            edges = np.asarray(obj.axis().edges())
            xr = f"[{edges[0]:.0f},{edges[-1]:.0f}]"
            ok = (entries >= BUMPNET_MIN_EVENTS) and (nbins > BUMPNET_MIN_BINS)
            passed += ok
            name = k[:-2] if k.endswith(";1") else k
            why = "" if ok else "  <-- " + ", ".join(
                ([] if entries >= BUMPNET_MIN_EVENTS else [f"{entries:.0f} entries < {BUMPNET_MIN_EVENTS}"]) +
                ([] if nbins > BUMPNET_MIN_BINS else [f"{nbins} bins <= {BUMPNET_MIN_BINS}"])
            )
            print(f"   {name:<62} {entries:>10.0f} {nbins:>6d} {xr:>18}  {'PASS' if ok else 'fail'}{why}")
        print()
    print(f"TOTAL histograms: {total};  meet BumpNet bar (>=100 evt & >30 bins): {passed};  fall short: {total - passed}")
    print()


def section_postprocessing(run_dir: Path) -> None:
    print("=" * 78)
    print("2. POST-PROCESSING vs the Z-PEAK  (di-lepton channels, before -> after)")
    print("=" * 78)
    im_dir = run_dir / "im_arrays"
    pp_dir = run_dir / "im_arrays_processed"
    before_dbs = sorted(im_dir.glob("*.sqlite")) if im_dir.is_dir() else []
    after_dbs = sorted(pp_dir.glob("*.sqlite")) if pp_dir.is_dir() else []
    print(f"before (im_arrays)          : {[p.name for p in before_dbs] or 'NONE'}")
    print(f"after  (im_arrays_processed): {[p.name for p in after_dbs] or 'NONE'}")
    if not before_dbs:
        print(">>> No mass-calc output to compare.\n")
        return

    before: dict[str, np.ndarray] = {}
    for db in before_dbs:
        for sig, arr in load_sqlite_signatures(db).items():
            before.setdefault(fs_im_key(sig), []).append(arr)
    before = {k: np.concatenate(v) for k, v in before.items()}

    after: dict[str, np.ndarray] = {}
    for db in after_dbs:
        for sig, arr in load_sqlite_signatures(db).items():
            after.setdefault(sig, []).append(arr)   # already _FS_..._main/_outliers
    after = {k: np.concatenate(v) for k, v in after.items()}

    # focus on same-flavour di-lepton FS_IM keys
    dilep_keys = []
    for key in sorted(before):
        m = FS_IM_RE.search(key)
        if m and same_flavor_dilepton(m.group(2)):
            dilep_keys.append(key)

    if not dilep_keys:
        print(">>> No same-flavour di-lepton (e0e1 / m0m1) channels in the mass-calc output.\n")
        return

    print(f"\nz_peak_cutoff (post-proc default) = {Z_PEAK_CUTOFF_DEFAULT} GeV: for ee/mumu channels "
          f"post-processing drops every mass below it (Z peak + low sideband).\n")
    for key in dilep_keys:
        b = np.asarray(before[key], dtype="float64")
        b = b[np.isfinite(b)]
        n_b = b.size
        n_b_zwin = int(((b >= Z_WINDOW[0]) & (b <= Z_WINDOW[1])).sum())
        n_b_below = int((b < Z_PEAK_CUTOFF_DEFAULT).sum())
        med_b = float(np.median(b)) if n_b else float("nan")

        a_main = after.get(f"{key}_main", np.array([]))
        a_out = after.get(f"{key}_outliers", np.array([]))
        a_all = np.concatenate([a_main, a_out]) if (len(a_main) or len(a_out)) else np.array([])
        a_all = a_all[np.isfinite(a_all)]
        n_a = a_all.size
        n_a_zwin = int(((a_all >= Z_WINDOW[0]) & (a_all <= Z_WINDOW[1])).sum())
        n_a_below = int((a_all < Z_PEAK_CUTOFF_DEFAULT).sum())

        print(f"channel {key}")
        print(f"   BEFORE : {n_b:>7d} masses | median {med_b:7.2f} GeV | "
              f"{n_b_zwin} in Z-window {Z_WINDOW} | {n_b_below} below {Z_PEAK_CUTOFF_DEFAULT:.0f} GeV")
        print(f"   AFTER  : {n_a:>7d} masses ({len(a_main)} main + {len(a_out)} outliers) | "
              f"{n_a_zwin} in Z-window | {n_a_below} below {Z_PEAK_CUTOFF_DEFAULT:.0f} GeV")
        if n_b_zwin > 0 and n_a_zwin == 0:
            print(f"   => Z-peak region CLEARED ({n_b_zwin} -> 0). Post-processing removed it as intended.")
        elif n_b_zwin > 0 and n_a_zwin < n_b_zwin:
            print(f"   => Z-peak region reduced {n_b_zwin} -> {n_a_zwin} (partial).")
        elif n_b_zwin == 0:
            print(f"   => nothing in the Z window before post-processing (nothing to remove).")
        else:
            print(f"   => Z-peak region UNCHANGED ({n_b_zwin} -> {n_a_zwin}). Post-processing did NOT act.")
        if n_a == 0:
            print(f"   => channel is EMPTY after post-processing (everything was cut).")
        print()


def section_format(run_dir: Path) -> None:
    print("=" * 78)
    print("3. HISTOGRAM FILE FORMAT")
    print("=" * 78)
    hist_dir = run_dir / "histograms"
    roots = sorted(hist_dir.glob("*.root")) if hist_dir.is_dir() else []
    if not roots or uproot is None:
        print("No ROOT file to inspect (or uproot unavailable).")
        print("Per histograms_pipeline.py the format is: one ROOT TFile "
              "(single_output_file), ROOT.TH1F objects named "
              "'ROI_mass_<combo>_cat_<fs>_width_<w>' (use_bumpnet_naming=true) - "
              "identical code path to the ATLAS side.\n")
        return
    for rp in roots:
        f = uproot.open(rp)
        classes = {}
        for k in f.keys():
            try:
                classes[f[k].classname] = classes.get(f[k].classname, 0) + 1
            except Exception:
                pass
        print(f"{rp.name}: {dict(classes)}")
        sample = [k[:-2] if k.endswith(';1') else k for k in list(f.keys())[:5]]
        for s in sample:
            print(f"   e.g. {s}")
    print("\nThis is the same TFile + TH1F + 'ROI_..._cat_..._width_' convention the "
          "ATLAS side of this pipeline writes (histograms_pipeline.py is shared).\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True, help="pipeline run directory")
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        sys.exit(f"run dir not found: {run_dir}")

    print(f"run directory: {run_dir}\n")
    section_histograms(run_dir)
    section_postprocessing(run_dir)
    section_format(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
