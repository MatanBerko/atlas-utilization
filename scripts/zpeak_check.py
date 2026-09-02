#!/usr/bin/env python3
"""
zpeak_check.py - standalone Z-peak sanity check for the CMS data path.

This is a *diagnostic* script, separate from the pipeline. It does not modify
any pipeline code or output. It reads the invariant-mass arrays produced by the
"mass_calculating" stage (run with config.cms_zpeak_test.yaml, post-processing
DISABLED) and checks whether same-flavour lepton pairs pile up near the Z-boson
mass (~91.2 GeV).

What it does
------------
* Locates the invariant-mass output for a run (a SQLite shard `im_batch_*.sqlite`
  under `im_arrays/`, or loose `*.npy` files as a fallback).
* Pulls out the electron-pair mass values (IM signature `e0e1`) and the
  muon-pair mass values (IM signature `m0m1`).
* Reports, on the RAW pipeline values with no correction: how many pairs were
  found per channel, which 2 GeV bin in the 85-97 GeV window holds the most
  entries (the candidate Z peak), and a short plain-language verdict.
* Runs a scale sanity check as a regression guard. The mass-calculation stage
  is supposed to hand back invariant masses already in GeV. It used to blanket-
  multiply every value by 1e-3 (`im_pipeline._convert_array_to_gev`), which is
  only right for MeV-native releases (ATLAS DAOD) and left CMS NanoAOD masses
  1000x too small (~0.09 instead of ~91). That is now gated per release/schema
  by `schemas.schema_needs_mev_to_gev_conversion`. If the raw electron-pair
  median still looks off by a round power of ten, this script raises a loud
  SCALE ALARM (the fix is not taking effect for this data) and additionally
  shows a rescaled view so the physics is still visible. When the raw values
  are already at the GeV scale it just says so and does everything on them.
* Bins the values 60-120 GeV in 2 GeV steps and writes a bar-chart PNG next to
  the data.

Usage
-----
    python scripts/zpeak_check.py                 # newest run under ./output
    python scripts/zpeak_check.py --run-dir PATH  # a specific run directory
    python scripts/zpeak_check.py --im-dir PATH   # a specific im_arrays dir
    python scripts/zpeak_check.py --no-autoscale  # skip the rescaled fallback view
"""

from __future__ import annotations

import argparse
import io
import math
import os
import re
import sqlite3
import sys
import zlib
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# --------------------------------------------------------------------------- #
# locating the data
# --------------------------------------------------------------------------- #
def find_latest_run_dir(base: str = "./output") -> Path | None:
    base_p = Path(base)
    if not base_p.is_dir():
        return None
    candidates = [d for d in base_p.iterdir() if d.is_dir() and (d / "im_arrays").is_dir()]
    if not candidates:
        candidates = [d for d in base_p.iterdir() if d.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return candidates[0]


def resolve_im_dir(args) -> Path:
    if args.im_dir:
        return Path(args.im_dir)
    run_dir = Path(args.run_dir) if args.run_dir else find_latest_run_dir(args.base_output)
    if run_dir is None:
        sys.exit(f"[zpeak_check] Could not find any run directory under {args.base_output!r}")
    im_dir = run_dir / "im_arrays"
    if not im_dir.is_dir():
        sys.exit(f"[zpeak_check] No im_arrays/ directory in run dir: {run_dir}")
    return im_dir


# --------------------------------------------------------------------------- #
# reading invariant-mass arrays  (SQLite shard, or loose .npy files)
# --------------------------------------------------------------------------- #
def _deserialize_array(payload: bytes) -> np.ndarray:
    """Mirror of services.storage.sqlite_shards._deserialize_array."""
    raw = zlib.decompress(payload)
    return np.load(io.BytesIO(raw), allow_pickle=False)


# signature / filename look like:
#   <prefix>_FS_<Xe>_<Xm>_<Xj>_<Xg>_<Xt>_<Xb>_IM_<letter><rank>...
FS_IM_RE = re.compile(r"_FS_([0-9a-z_]+)_IM_([0-9a-z]+)$")


def iter_signature_arrays(im_dir: Path):
    """Yield (fs_str, im_str, np.ndarray) for every stored invariant-mass chunk."""
    shards = sorted(im_dir.glob("*.sqlite"))
    npys = sorted(im_dir.glob("*.npy"))

    if shards:
        for shard in shards:
            conn = sqlite3.connect(str(shard))
            try:
                rows = conn.execute(
                    "SELECT signature, payload FROM array_chunks ORDER BY id"
                ).fetchall()
            finally:
                conn.close()
            for signature, payload in rows:
                m = FS_IM_RE.search(signature)
                if not m:
                    continue
                yield m.group(1), m.group(2), _deserialize_array(payload)
        return

    for nf in npys:
        m = FS_IM_RE.search(nf.stem)
        if not m:
            continue
        yield m.group(1), m.group(2), np.load(str(nf), allow_pickle=True)


# --------------------------------------------------------------------------- #
# analysis
# --------------------------------------------------------------------------- #
PURE_FS = {
    "e0e1": "2e_0m_0j_0g_0t_0b",   # exactly two electrons, nothing else
    "m0m1": "0e_2m_0j_0g_0t_0b",   # exactly two muons, nothing else
}
CHANNELS = [
    ("e0e1", "electron pairs (e+e-)"),
    ("m0m1", "muon pairs (mu+ mu-)"),
]

BIN_LO, BIN_HI, BIN_STEP = 60.0, 120.0, 2.0
Z_WINDOW = (85.0, 97.0)
Z_MASS = 91.1876


def collect(im_dir: Path):
    """Return {im_str: {'all': array, 'pure': array}} for the two lepton-pair channels."""
    wanted = {im for im, _ in CHANNELS}
    buckets = {im: {"all": [], "pure": []} for im in wanted}
    for fs_str, im_str, arr in iter_signature_arrays(im_dir):
        if im_str not in wanted:
            continue
        arr = np.asarray(arr, dtype="float64").ravel()
        arr = arr[np.isfinite(arr)]
        buckets[im_str]["all"].append(arr)
        if fs_str == PURE_FS[im_str]:
            buckets[im_str]["pure"].append(arr)
    out = {}
    for im_str, d in buckets.items():
        out[im_str] = {
            "all": np.concatenate(d["all"]) if d["all"] else np.array([]),
            "pure": np.concatenate(d["pure"]) if d["pure"] else np.array([]),
        }
    return out


def infer_pipeline_scale(ref_vals: np.ndarray):
    """
    Regression guard. Work out whether the pipeline's raw invariant masses are
    on the GeV scale or still off by a round power of ten. Uses the electron-
    pair channel as reference (high stats, dominated by real Z->ee).
    Returns (factor, explanation); factor == 1.0 means "looks correct".
    """
    v = ref_vals[np.isfinite(ref_vals)]
    v = v[v > 0]
    if v.size < 20:
        return 1.0, "not enough electron-pair values to judge the scale; taking raw numbers as-is."
    med = float(np.median(v))
    p = int(round(math.log10(Z_MASS / med)))
    factor = 10.0 ** p
    if p == 0:
        return 1.0, (f"raw electron-pair median is {med:.4g} GeV - already at the GeV scale, "
                     f"no correction needed (this is the expected result after the "
                     f"per-schema MeV/GeV fix).")
    return factor, (
        f"raw electron-pair median is {med:.4g}, about {factor:g}x away from the Z mass "
        f"({Z_MASS:.1f} GeV). The mass-calculation stage is NOT returning GeV for this "
        f"data - the per-schema MeV->GeV gating "
        f"(schemas.schema_needs_mev_to_gev_conversion) is not taking effect here. "
        f"Showing a rescaled (x{factor:g}) view below so the physics is still visible."
    )


def peak_bin(values: np.ndarray, edges: np.ndarray):
    """Return (bin_lo, bin_hi, count) for the fullest bin inside the Z window."""
    counts, _ = np.histogram(values, bins=edges)
    centers = 0.5 * (edges[:-1] + edges[1:])
    in_win = (centers >= Z_WINDOW[0]) & (centers <= Z_WINDOW[1])
    if not in_win.any() or counts[in_win].sum() == 0:
        return None
    win_idx = np.where(in_win)[0]
    best = win_idx[np.argmax(counts[win_idx])]
    return float(edges[best]), float(edges[best + 1]), int(counts[best])


def verdict(values: np.ndarray, edges: np.ndarray) -> str:
    n = values.size
    if n == 0:
        return ("NO DATA - no pairs were reconstructed for this channel at all. "
                "Either parsing kept no events of this type, or the combination "
                "was dropped upstream.")
    in_range = values[(values >= BIN_LO) & (values <= BIN_HI)]
    pk = peak_bin(values, edges)
    counts, _ = np.histogram(values, bins=edges)
    centers = 0.5 * (edges[:-1] + edges[1:])
    total = counts.sum()

    if pk is None:
        return (f"{n} pairs, {in_range.size} in 60-120 GeV, but none in the 85-97 GeV "
                "window - no Z peak where one is expected.")

    lo, hi, peak_count = pk
    sb_mask = (centers < 88.0) | (centers > 94.0)
    sb_avg = counts[sb_mask].mean() if sb_mask.any() else 0.0
    peak_frac = peak_count / total if total else 0.0
    contrast = (peak_count / sb_avg) if sb_avg > 0 else float("inf")
    peak_ok = abs(0.5 * (lo + hi) - Z_MASS) <= 3.0

    if in_range.size < 20:
        return (f"only {in_range.size} pairs in 60-120 GeV - too low statistics to be sure. "
                f"Fullest in-window bin: {lo:.0f}-{hi:.0f} GeV ({peak_count} entries)"
                + (", consistent with the Z mass." if peak_ok else "."))

    if peak_ok and (contrast >= 2.0 or peak_frac >= 0.15):
        return (f"CLEAR Z peak at {lo:.0f}-{hi:.0f} GeV "
                f"({peak_count} of {total} in-range entries, ~{peak_frac * 100:.0f}%, "
                f"~{contrast:.1f}x the off-peak bin average). Matches the Z boson "
                f"(~{Z_MASS:.1f} GeV): parsing and mass calculation are working for "
                f"this channel, and the mass scale is correct.")
    if peak_ok:
        return (f"a modest excess at {lo:.0f}-{hi:.0f} GeV ({peak_count} entries, "
                f"~{contrast:.1f}x off-peak). Right location for the Z but the sample "
                f"is thin - looks OK, more files would firm it up.")
    return (f"the fullest in-window bin is {lo:.0f}-{hi:.0f} GeV, offset from the "
            f"expected ~{Z_MASS:.1f} GeV. With {in_range.size} in-range pairs this hints "
            f"at a problem beyond the overall scale (wrong fields, or bad kinematics).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", default=None, help="Pipeline run directory (contains im_arrays/)")
    ap.add_argument("--im-dir", default=None, help="Directly point at an im_arrays directory")
    ap.add_argument("--base-output", default="./output", help="Where run directories live (default ./output)")
    ap.add_argument("--out", default=None, help="Output PNG path (default: <im_dir>/zpeak_check.png)")
    ap.add_argument("--no-autoscale", action="store_true",
                    help="If the scale alarm fires, do not show the rescaled fallback view")
    args = ap.parse_args()

    im_dir = resolve_im_dir(args)
    out_png = Path(args.out) if args.out else im_dir / "zpeak_check.png"

    print("=" * 74)
    print("CMS Z-peak sanity check  (di-lepton invariant mass, post-processing OFF)")
    print("=" * 74)
    print(f"invariant-mass source : {im_dir}")
    shard_list = sorted(p.name for p in im_dir.glob('*.sqlite'))
    npy_count = len(list(im_dir.glob('*.npy')))
    print(f"  sqlite shards       : {shard_list or 'none'}")
    print(f"  loose .npy files    : {npy_count}")
    print(f"binning               : {BIN_LO:.0f}-{BIN_HI:.0f} GeV in {BIN_STEP:.0f} GeV steps")
    print(f"Z-peak search window  : {Z_WINDOW[0]:.0f}-{Z_WINDOW[1]:.0f} GeV  (PDG Z mass {Z_MASS:.4f} GeV)")

    edges = np.arange(BIN_LO, BIN_HI + 0.5 * BIN_STEP, BIN_STEP)
    data = collect(im_dir)

    # --- scale sanity check (regression guard) on the RAW electron-pair values ---
    factor, scale_note = infer_pipeline_scale(data["e0e1"]["all"])
    alarm = factor != 1.0
    show_rescaled = alarm and not args.no_autoscale

    print()
    print("SCALE CHECK (regression guard)")
    if alarm:
        print("  *** SCALE ALARM ***")
        print(f"  {scale_note}")
        if args.no_autoscale:
            print("  (--no-autoscale set: rescaled fallback view suppressed)")
    else:
        print(f"  OK - {scale_note}")
    print()

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    any_data = False

    for ax, (im_str, label) in zip(axes, CHANNELS):
        raw_all = data[im_str]["all"]
        raw_pure = data[im_str]["pure"]
        raw_in = raw_all[(raw_all >= BIN_LO) & (raw_all <= BIN_HI)]

        print("-" * 74)
        print(f"CHANNEL: {label}   (IM signature '{im_str}')")
        print(f"  total pairs found (all final states)   : {raw_all.size}")
        print(f"  RAW values in {BIN_LO:.0f}-{BIN_HI:.0f} GeV               : {raw_in.size}")
        print(f"  pairs in pure '{PURE_FS[im_str]}' final state : {raw_pure.size}")

        pk_raw = peak_bin(raw_all, edges)
        if pk_raw:
            print(f"  RAW candidate Z bin (all final states) : "
                  f"{pk_raw[0]:.0f}-{pk_raw[1]:.0f} GeV  with {pk_raw[2]} entries")
        else:
            print(f"  RAW candidate Z bin (all final states) : none in "
                  f"{Z_WINDOW[0]:.0f}-{Z_WINDOW[1]:.0f} GeV")
        pk_raw_pure = peak_bin(raw_pure, edges)
        if pk_raw_pure:
            print(f"  RAW candidate Z bin (pure final state) : "
                  f"{pk_raw_pure[0]:.0f}-{pk_raw_pure[1]:.0f} GeV  with {pk_raw_pure[2]} entries")
        print(f"  interpretation (RAW): {verdict(raw_all, edges)}")

        plot_vals = raw_all
        if show_rescaled:
            resc_all = raw_all * factor
            resc_in = resc_all[(resc_all >= BIN_LO) & (resc_all <= BIN_HI)]
            pk_resc = peak_bin(resc_all, edges)
            peak_txt = (f"peak {pk_resc[0]:.0f}-{pk_resc[1]:.0f} GeV / {pk_resc[2]} entries"
                        if pk_resc else "no in-window peak")
            print(f"  [rescaled x{factor:g}] {resc_in.size} in-range, {peak_txt}")
            print(f"  interpretation (rescaled x{factor:g}): {verdict(resc_all, edges)}")
            plot_vals = resc_all
        print()

        plot_in = plot_vals[(plot_vals >= BIN_LO) & (plot_vals <= BIN_HI)]
        counts, _ = np.histogram(plot_in, bins=edges)
        centers = 0.5 * (edges[:-1] + edges[1:])
        if plot_in.size:
            any_data = True
        ax.bar(centers, counts, width=BIN_STEP * 0.9, color="#3b7dd8", edgecolor="#1f3f6e")
        ax.axvline(Z_MASS, color="#d1495b", linestyle="--", linewidth=1.5, label=f"Z {Z_MASS:.1f} GeV")
        ax.axvspan(Z_WINDOW[0], Z_WINDOW[1], color="#d1495b", alpha=0.08)
        scale_txt = f"  (RESCALED x{factor:g})" if show_rescaled else "  (raw)"
        ax.set_title(f"{label}{scale_txt}\n{plot_in.size} entries in {BIN_LO:.0f}-{BIN_HI:.0f} GeV")
        ax.set_xlabel("invariant mass [GeV]")
        ax.set_ylabel("pairs / 2 GeV")
        ax.legend(loc="upper right", fontsize=9)

    if show_rescaled:
        sup = f"CMS di-lepton invariant mass - SCALE ALARM: values shown rescaled x{factor:g}"
    else:
        sup = "CMS di-lepton invariant mass - Z-peak check (raw pipeline output)"
    fig.suptitle(sup, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)

    print("=" * 74)
    print(f"chart written to: {out_png}")
    if not any_data:
        print("WARNING: no entries fell in the plotting range for either channel.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
