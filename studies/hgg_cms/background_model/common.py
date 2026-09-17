"""
Background-model task, Part 1: sideband data loading, binning, and the
blinding mask.

BLINDING (strict, per this task's own out-of-scope rules): refuses any
path whose name contains "BLINDED" before ever opening it, then reads
through `studies.hgg_cms.output.read_output(unblind=False)`, which
independently re-asserts that no data event with 115 <= m_gg <= 135 GeV
is present -- the same two-layer check
`studies/hgg_cms/validation/common.py` uses. On top of that, the
per-category HISTOGRAM itself is built with an explicit sideband mask
(bins whose center falls in [115, 135) are excluded from every
likelihood sum) -- belt-and-suspenders on top of the fact that
`data_sidebands.root` is independently known to contain zero events in
that window at all.
"""
from __future__ import annotations

import os
from pathlib import Path

import awkward as ak
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
import sys
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.output import read_output, BLINDED_MARKER  # noqa: E402

DEFAULT_MERGED_DIR = os.environ.get("HGG_MERGED_DIR", r"C:\Users\matan\hgg_full_merged")
CATEGORIES = ["EBEB", "notEBEB"]
BLIND_LO, BLIND_HI = 115.0, 135.0

DEFAULT_FIT_LO, DEFAULT_FIT_HI, BIN_WIDTH = 105.0, 180.0, 0.25
ROBUSTNESS_FIT_LO = 110.0


def _merged_dir() -> Path:
    d = Path(DEFAULT_MERGED_DIR)
    if not d.exists():
        raise FileNotFoundError(f"merged-output directory not found: {d}")
    return d


def load_data_sidebands() -> ak.Array:
    path = _merged_dir() / "data_sidebands.root"
    if BLINDED_MARKER in path.name:
        raise PermissionError(f"REFUSING to load {path}: filename contains {BLINDED_MARKER!r}.")
    arr = read_output(path, unblind=False)
    # Second, independent assert -- required explicitly by this task's rules.
    if "is_data" in arr.fields and "m_gg" in arr.fields and len(arr) > 0:
        is_data = ak.to_numpy(arr["is_data"])
        if is_data.any():
            mgg = ak.to_numpy(arr["m_gg"])[is_data]
            assert not ((mgg >= BLIND_LO) & (mgg <= BLIND_HI)).any(), (
                f"BLINDING VIOLATION detected in {path} -- aborting."
            )
    return arr


def category_mask(cat: np.ndarray, which: str) -> np.ndarray:
    cat = np.asarray(cat)
    if which == "EBEB":
        return cat == "EBEB"
    if which == "notEBEB":
        return cat != "EBEB"
    raise ValueError(which)


def bin_edges(lo: float, hi: float, bin_width: float = BIN_WIDTH) -> np.ndarray:
    n_bins = int(round((hi - lo) / bin_width))
    return np.linspace(lo, hi, n_bins + 1)


def sideband_bin_mask(edges: np.ndarray, blind_lo: float = BLIND_LO, blind_hi: float = BLIND_HI) -> np.ndarray:
    """True for bins whose CENTER lies OUTSIDE [blind_lo, blind_hi) -- i.e.
    the bins kept in the likelihood. Explicit boolean mask, not a slice,
    so it is trivially auditable and testable."""
    centers = 0.5 * (edges[:-1] + edges[1:])
    return ~((centers >= blind_lo) & (centers < blind_hi))


def histogram_counts(mgg: np.ndarray, edges: np.ndarray) -> np.ndarray:
    counts, _ = np.histogram(mgg, bins=edges)
    return counts.astype(float)


def load_category_histograms(lo: float = DEFAULT_FIT_LO, hi: float = DEFAULT_FIT_HI,
                              bin_width: float = BIN_WIDTH) -> dict:
    """Returns {category: {"edges", "counts", "sideband_mask", "n_sideband_total"}}."""
    arr = load_data_sidebands()
    mgg_all = ak.to_numpy(arr["m_gg"])
    cat_all = ak.to_numpy(arr["category"])

    edges = bin_edges(lo, hi, bin_width)
    mask = sideband_bin_mask(edges)

    out = {}
    for cat in CATEGORIES:
        m = category_mask(cat_all, cat)
        mgg = mgg_all[m]
        counts = histogram_counts(mgg, edges)
        out[cat] = {
            "edges": edges, "counts": counts, "sideband_mask": mask,
            "n_events_total_in_range": int(counts.sum()),
            "n_sideband_total": int(counts[mask].sum()),
            "n_events_raw": int(m.sum()),
        }
    return out
