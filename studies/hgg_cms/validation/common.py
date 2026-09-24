"""
Implementation task 6, Part 3: shared helpers for the first-round
validation analyses (A-F). Runs LOCALLY, on the laptop, against the
merged outputs copied off the cluster after Part 1's merge reported
"COMPLETE" -- never on the cluster, never over the network for the ROOT
files themselves.

BLINDING (belt-and-suspenders, matches this task's own instruction that
"every analysis script must assert, on the data it loads, that no event
has 115 <= m_gg <= 135 and that no loaded path contains 'BLINDED', and
abort otherwise"): every loader below (1) refuses any path whose name
contains "BLINDED" BEFORE ever opening it, then (2) reads it through
``studies.hgg_cms.output.read_output(unblind=False)``, which
independently re-asserts that no data event with 115<=m_gg<=135 GeV is
present, regardless of filename -- i.e. the same two checks
merge_outputs.py's merged-ROOT writer already relies on, applied again
here on the READ side.
"""
from __future__ import annotations

import os
from pathlib import Path

import awkward as ak
import numpy as np

import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.output import read_output, BLINDED_MARKER  # noqa: E402
from studies.hgg_cms.physics_checks.common import (  # noqa: E402
    effective_sigma_68, histogram_mode,
)

DEFAULT_MERGED_DIR = os.environ.get("HGG_MERGED_DIR", r"C:\Users\matan\hgg_full_merged")

SIGNAL_LABELS = ["ggh", "vbf", "wplush", "wminush", "zh", "tth"]
SIGNAL_RECORD_IDS = {
    "ggh": "37350", "vbf": "68497", "wplush": "71013",
    "wminush": "70173", "zh": "74132", "tth": "67611",
}
SIGNAL_CROSS_SECTIONS_PB = {
    "ggh": 48.58, "vbf": 3.782, "wplush": 0.84, "wminush": 0.5328,
    "zh": 0.7612,  # qq/qg->ZH only -- see signal_sumw_notes.md
    "tth": 0.5071,
}
BR_HGG = 0.00227
LUMI_FB = 16.393380531
LUMI_UNCERTAINTY_PCT = 1.2

CATEGORIES = ["EBEB", "notEBEB"]
BLIND_LO, BLIND_HI = 115.0, 135.0
SIDEBAND_LO, SIDEBAND_HI = 100.0, 180.0


def merged_dir() -> Path:
    d = Path(DEFAULT_MERGED_DIR)
    if not d.exists():
        raise FileNotFoundError(
            f"merged-output directory not found: {d} -- set HGG_MERGED_DIR "
            f"to the folder you copied hgg_full/merged/*.root into."
        )
    return d


def _safe_read(path: Path) -> ak.Array:
    if BLINDED_MARKER in path.name:
        raise PermissionError(
            f"REFUSING to load {path}: filename contains '{BLINDED_MARKER}'. "
            f"No validation script may ever open a blinded-signal-region file."
        )
    arr = read_output(path, unblind=False)
    # Second, independent assert (belt-and-suspenders on top of
    # read_output's own) -- required explicitly by this task's rules.
    if "is_data" in arr.fields and "m_gg" in arr.fields and len(arr) > 0:
        is_data = ak.to_numpy(arr["is_data"])
        if is_data.any():
            mgg = ak.to_numpy(arr["m_gg"])[is_data]
            assert not ((mgg >= BLIND_LO) & (mgg <= BLIND_HI)).any(), (
                f"BLINDING VIOLATION detected in {path} by common.py's own "
                f"second check -- aborting."
            )
    return arr


def load_data_sidebands() -> ak.Array:
    path = merged_dir() / "data_sidebands.root"
    return _safe_read(path)


def load_signal(label: str) -> ak.Array:
    if label not in SIGNAL_LABELS:
        raise ValueError(f"unknown signal label {label!r}, expected one of {SIGNAL_LABELS}")
    path = merged_dir() / f"signal_{label}.root"
    return _safe_read(path)


def load_all_signal() -> dict:
    return {label: load_signal(label) for label in SIGNAL_LABELS}


def sideband_mask(mgg: np.ndarray) -> np.ndarray:
    """True for events in [100,115) u (135,180] -- excludes the blinded
    window by construction (it is never populated in data_sidebands.root
    anyway, but signal m_gg CAN legitimately fall in [115,135], so this
    mask is also used to restrict SIGNAL to the sideband range when a
    check explicitly wants that)."""
    mgg = np.asarray(mgg)
    return ((mgg >= SIDEBAND_LO) & (mgg < BLIND_LO)) | ((mgg > BLIND_HI) & (mgg <= SIDEBAND_HI))


def category_mask(cat: np.ndarray, which: str) -> np.ndarray:
    cat = np.asarray(cat)
    if which == "EBEB":
        return cat == "EBEB"
    if which == "notEBEB":
        return cat != "EBEB"
    raise ValueError(which)


def eff_sumw_pileup_weighted(genWeight: np.ndarray, pileup_weight: np.ndarray = None) -> float:
    """Sum of genWeight, optionally multiplied by a per-event pileup
    weight -- used by Part D/E's "before vs after pileup reweighting"
    comparison."""
    genWeight = np.asarray(genWeight)
    if pileup_weight is None:
        return float(genWeight.sum())
    return float((genWeight * np.asarray(pileup_weight)).sum())


def expected_yield(label: str, sum_genWeight_selected: float, genEventSumw_processed: float,
                    lumi_fb: float = LUMI_FB) -> float:
    sigma_pb = SIGNAL_CROSS_SECTIONS_PB[label]
    return sigma_pb * 1000.0 * BR_HGG * lumi_fb * (sum_genWeight_selected / genEventSumw_processed)


def weighted_mode_and_sigma68(values: np.ndarray, weights: np.ndarray,
                               bin_width: float = 0.5, lo: float = 110.0, hi: float = 140.0):
    """genWeight-aware mode + effective-sigma68, computed from a WEIGHTED
    histogram (not physics_checks/common.py's unweighted, sorted-array
    effective_sigma_68 -- that one has no notion of per-event weight, and
    a naive weighted-array sort/cumsum is not well-defined once any
    weights are negative, which genWeight legitimately can be for the
    amc@NLO-generated records here). Binned instead: mode = center of the
    tallest bin; sigma68 = half the width of the narrowest contiguous
    run of bins whose SUMMED weight is >= 68.3% of the total (an O(n^2)
    scan over ~60 bins by default -- trivially fast, and well-defined even
    with a few small negative-weight bins as long as the signal peak
    dominates, which it does here). Returns (mode, sigma68) with sigma68
    None if the total weight is <= 0."""
    values = np.asarray(values)
    weights = np.asarray(weights)
    edges = np.arange(lo, hi + bin_width, bin_width)
    counts, edges = np.histogram(values, bins=edges, weights=weights)
    centers = 0.5 * (edges[:-1] + edges[1:])
    mode = float(centers[np.argmax(counts)])

    total = float(counts.sum())
    if total <= 0:
        return mode, None
    target = 0.683 * total
    prefix = np.concatenate([[0.0], np.cumsum(counts)])
    n = len(counts)
    best_width = None
    for i in range(n):
        for j in range(i, n):
            if prefix[j + 1] - prefix[i] >= target:
                width = edges[j + 1] - edges[i]
                if best_width is None or width < best_width:
                    best_width = width
                break
    sigma68 = float(best_width / 2.0) if best_width is not None else None
    return mode, sigma68


def derive_pileup_weights(data_pv: np.ndarray, mc_pv: np.ndarray, mc_weight: np.ndarray,
                           pv_max: int = 60, min_mc_raw_entries: int = 20,
                           clip_range=(0.1, 5.0)):
    """w(n) = normalized_data_fraction(n) / normalized_MC_fraction(n), for
    integer PV_npvsGood bins 0..pv_max. Sensible handling of empty/low-
    statistics MC bins: a bin with fewer than `min_mc_raw_entries` RAW
    (unweighted) MC entries gets weight 1.0 (no reweighting -- not enough
    MC statistics there to trust a ratio) and is listed in
    "low_stat_fallback_bins"; every weight is additionally clipped to
    `clip_range` to avoid a single fluctuating bin (on either side)
    producing a pathological weight. Returns (bin_edges, weights_array,
    diagnostics_dict)."""
    data_pv = np.asarray(data_pv)
    mc_pv = np.asarray(mc_pv)
    mc_weight = np.asarray(mc_weight)

    edges = np.arange(0, pv_max + 2) - 0.5  # integer bins centered on 0..pv_max
    data_counts, _ = np.histogram(data_pv, bins=edges)
    mc_counts_raw, _ = np.histogram(mc_pv, bins=edges)
    mc_counts_weighted, _ = np.histogram(mc_pv, bins=edges, weights=mc_weight)

    data_frac = data_counts / max(data_counts.sum(), 1)
    mc_frac = mc_counts_weighted / mc_counts_weighted.sum() if mc_counts_weighted.sum() != 0 else np.zeros_like(mc_counts_weighted)

    weights = np.ones_like(data_frac)
    low_stat_bins = []
    for i in range(len(weights)):
        if mc_counts_raw[i] < min_mc_raw_entries or mc_frac[i] == 0:
            weights[i] = 1.0
            low_stat_bins.append(i)
        else:
            weights[i] = data_frac[i] / mc_frac[i]
    weights = np.clip(weights, clip_range[0], clip_range[1])

    diagnostics = {
        "pv_max": pv_max, "min_mc_raw_entries": min_mc_raw_entries, "clip_range": list(clip_range),
        "low_stat_fallback_bins": low_stat_bins,
        "n_low_stat_fallback_bins": len(low_stat_bins),
        "n_bins_total": len(weights),
    }
    return edges, weights, diagnostics


def apply_pileup_weight(pv_values: np.ndarray, edges: np.ndarray, weights: np.ndarray) -> np.ndarray:
    pv_values = np.asarray(pv_values)
    idx = np.clip(np.digitize(pv_values, edges) - 1, 0, len(weights) - 1)
    return weights[idx]


def stat_uncertainty_sqrt_sumw2(genWeight: np.ndarray, mask: np.ndarray = None,
                                 scale: float = 1.0) -> float:
    """sqrt(Sum genWeight^2) over the (optionally masked) events, scaled by
    the same normalization factor `scale` used to turn a raw weight sum
    into an expected yield -- i.e. the statistical uncertainty ON THE
    EXPECTED YIELD from finite simulation statistics."""
    genWeight = np.asarray(genWeight)
    if mask is not None:
        genWeight = genWeight[np.asarray(mask)]
    return scale * float(np.sqrt(np.sum(genWeight ** 2)))
