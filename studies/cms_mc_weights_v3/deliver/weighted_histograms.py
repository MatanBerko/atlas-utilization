#!/usr/bin/env python
"""
Weighted histograms for the CMS MC delivery (DESIGN.md D7).

The data delivery writes TH1F with float32 contents and no Sumw2, via
`studies/m0m1j0_cms/histograms.py::to_writable_th1f`. Weighted MC needs
TH1D with a real Sumw2 array, so that a bin's error is sqrt(sum of w^2)
rather than sqrt(content) -- which for weighted contents is meaningless and,
for a negative bin, undefined.

This module adds exactly that, and nothing else:

  * `fill_weighted_fixed_grid` -- (sum_w, sum_w2, edges) on the SHARED fixed
    grid, using the same bin-index arithmetic and the same exact-10000.0-GeV
    boundary handling as `make_fixed_grid_histogram`, so a weighted MC
    histogram and the data histogram of the same name have identical binning.
  * `to_writable_th1d` -- a genuine TH1D with `fSumw2` of length nbins + 2.
  * `verify_written_th1d` -- the read-back assertion: classname, bin contents,
    len(fSumw2) == nbins + 2, and errors == sqrt(sum w^2). An absent or
    wrong-length Sumw2 raises.

`studies/m0m1j0_cms/histograms.py` is deliberately NOT modified: it is on the
delivered data path, and Hard Rule 8 keeps data-side behaviour untouched. The
bin-mapping code below is therefore a mirror, and
`studies/cms_mc_weights_v3/tests/test_mc_weights_v3.py` asserts the mirror
agrees with the original for unit weights.
"""
from __future__ import annotations

import math
import pathlib
import sys

import numpy as np
import uproot
import uproot.writing.identify as uproot_identify

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from studies.m0m1j0_cms.histograms import (  # noqa: E402
    BIN_WIDTH_GEV,
    FIXED_MASS_MAX_GEV,
    FIXED_MASS_MIN_GEV,
    _n_bins,
)


def fill_weighted_fixed_grid(masses, weights):
    """(sum_w, sum_w2, edges) on the shared fixed grid.

    Mirrors make_fixed_grid_histogram's own mapping exactly: NaN masses are
    dropped, a mass exactly equal to FIXED_MASS_MAX_GEV is nudged down by one
    ULP so it lands in the last real bin rather than overflow, and anything
    outside [min, max) is dropped. `weights` must be the same length as
    `masses` -- a mismatch raises rather than being silently truncated.
    """
    masses = np.asarray(masses, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if masses.shape != weights.shape:
        raise ValueError(
            f"masses and weights must have the same shape; got {masses.shape} "
            f"and {weights.shape}")

    n_bins = _n_bins()
    sum_w = np.zeros(n_bins, dtype=np.float64)
    sum_w2 = np.zeros(n_bins, dtype=np.float64)
    edges = np.linspace(FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV, n_bins + 1)

    finite = ~np.isnan(masses)
    m = masses[finite]
    w = weights[finite]
    nudged = np.where(
        m == FIXED_MASS_MAX_GEV,
        math.nextafter(FIXED_MASS_MAX_GEV, FIXED_MASS_MIN_GEV),
        m,
    )
    in_range = (nudged >= FIXED_MASS_MIN_GEV) & (nudged < FIXED_MASS_MAX_GEV)
    idx = np.floor((nudged[in_range] - FIXED_MASS_MIN_GEV) / BIN_WIDTH_GEV).astype(np.int64)
    idx = np.clip(idx, 0, n_bins - 1)
    w_in = w[in_range]
    np.add.at(sum_w, idx, w_in)
    np.add.at(sum_w2, idx, w_in * w_in)
    return sum_w, sum_w2, edges


def to_writable_th1d(values: np.ndarray, sum_w2: np.ndarray,
                     edges: np.ndarray, title: str, n_entries: float):
    """A writable TH1D carrying an explicit fSumw2 array.

    `values` / `sum_w2` are the real bins only; the underflow (index 0) and
    overflow (last index) slots ROOT's on-disk layout needs are added here and
    are always zero, because the inputs are already clipped into range by
    fill_weighted_fixed_grid.

    `n_entries` is the RAW entry count, not the weighted sum: ROOT's fEntries
    counts fills, and reporting the weighted sum there would make a reader
    believe the sample has more (or fewer, with negative weights) events than
    it does.
    """
    values = np.asarray(values, dtype=np.float64)
    sum_w2 = np.asarray(sum_w2, dtype=np.float64)
    if values.shape != sum_w2.shape:
        raise ValueError("values and sum_w2 must have the same shape")
    n_bins = len(values)

    data = np.zeros(n_bins + 2, dtype=np.float64)
    data[1:-1] = values
    sumw2_on_disk = np.zeros(n_bins + 2, dtype=np.float64)
    sumw2_on_disk[1:-1] = sum_w2

    xaxis = uproot_identify.to_TAxis(
        "xaxis", "", n_bins, float(edges[0]), float(edges[-1]),
        fXbins=np.asarray(edges, dtype=np.float64),
    )
    return uproot_identify.to_TH1x(
        fName=None,
        fTitle=title,
        data=data,
        fEntries=float(n_entries),
        fTsumw=float(values.sum()),
        fTsumw2=float(sum_w2.sum()),
        fTsumwx=0.0,
        fTsumwx2=0.0,
        fSumw2=sumw2_on_disk,
        fXaxis=xaxis,
    )


def verify_written_th1d(root_path: str, expected: dict) -> dict:
    """D7's read-back assertion.

    `expected` is {key: (values, sum_w2)}. For every key this checks, and
    raises AssertionError naming the key and the aspect on any failure:

      * the key exists on disk;
      * its class is exactly TH1D (not TH1F -- float32 contents silently lose
        a small weight added to a populated bin);
      * len(fSumw2) == n_bins + 2, i.e. a real Sumw2 array is present. An
        absent or zero-length Sumw2 FAILS THE BUILD, because a TH1D without
        one reports sqrt(content) errors;
      * bin contents match;
      * errors == sqrt(sum w^2) bin by bin.
    """
    checked = {}
    with uproot.open(root_path) as f:
        on_disk = {k.split(";")[0] for k in f.keys()}
        missing = sorted(set(expected) - on_disk)
        if missing:
            raise AssertionError(
                f"{root_path}: expected histogram(s) missing after write: {missing}")
        for key, (values, sum_w2) in expected.items():
            hist = f[key]
            if hist.classname != "TH1D":
                raise AssertionError(
                    f"{root_path}: {key} is {hist.classname}, expected TH1D "
                    "(weighted MC must not be written as TH1F)")
            try:
                fsumw2 = hist.member("fSumw2")
            except Exception as exc:  # noqa: BLE001
                raise AssertionError(
                    f"{root_path}: {key} has no fSumw2 member ({exc}) -- a "
                    "weighted histogram without Sumw2 reports sqrt(content) "
                    "errors, which is wrong for weighted contents and "
                    "undefined for a negative bin.") from exc
            n_bins = len(np.asarray(values))
            if len(fsumw2) != n_bins + 2:
                raise AssertionError(
                    f"{root_path}: {key} fSumw2 has length {len(fsumw2)}, "
                    f"expected n_bins + 2 = {n_bins + 2}")
            got_values = hist.values(flow=False)
            if not np.allclose(got_values, values, rtol=1e-12, atol=0.0):
                raise AssertionError(
                    f"{root_path}: {key} bin contents do not match after "
                    f"write/read (max abs diff "
                    f"{np.max(np.abs(got_values - values)):.6g})")
            got_errors = hist.errors(flow=False)
            want_errors = np.sqrt(np.asarray(sum_w2, dtype=np.float64))
            if not np.allclose(got_errors, want_errors, rtol=1e-12, atol=0.0):
                raise AssertionError(
                    f"{root_path}: {key} bin errors are not sqrt(sum w^2) "
                    f"(max abs diff "
                    f"{np.max(np.abs(got_errors - want_errors)):.6g})")
            checked[key] = {
                "classname": hist.classname,
                "n_bins": int(n_bins),
                "len_fSumw2": int(len(fsumw2)),
                "sum_w": float(np.sum(values)),
                "sum_w2": float(np.sum(sum_w2)),
            }
    return checked


def negative_or_empty_bin_inventory(values: np.ndarray, sum_w2: np.ndarray) -> dict:
    """D7 / the data-MC negative-bin problem: per histogram, how many bins
    inside the FILLED RANGE have content <= 0.

    "Filled range" is first..last bin that received at least one entry, which
    is `sum_w2 > 0` -- not `values != 0`, because a bin whose positive and
    negative weights cancel exactly has content 0 but was filled, and that is
    precisely the case worth counting. Bins outside the filled range are
    structurally empty and are not a problem for anyone.
    """
    values = np.asarray(values, dtype=np.float64)
    sum_w2 = np.asarray(sum_w2, dtype=np.float64)
    filled = np.nonzero(sum_w2 > 0)[0]
    if filled.size == 0:
        return {
            "n_filled_bins": 0, "first_filled_bin": None, "last_filled_bin": None,
            "n_bins_in_filled_range": 0, "n_bins_le_zero_in_filled_range": 0,
            "n_bins_lt_zero_in_filled_range": 0, "n_bins_eq_zero_in_filled_range": 0,
            "n_bins_never_filled_in_range": 0, "n_filled_bins_le_zero": 0,
            "n_filled_bins_lt_zero": 0, "n_filled_bins_eq_zero": 0,
            "most_negative_content": None,
        }
    first, last = int(filled[0]), int(filled[-1])
    window = values[first:last + 1]
    window_w2 = sum_w2[first:last + 1]
    was_filled = window_w2 > 0
    return {
        "n_filled_bins": int(filled.size),
        "first_filled_bin": first,
        "last_filled_bin": last,
        "n_bins_in_filled_range": int(window.size),
        # The headline number BumpNet cares about: every non-positive bin
        # inside the range it would fit over, whether it was filled or not.
        "n_bins_le_zero_in_filled_range": int(np.count_nonzero(window <= 0)),
        "n_bins_lt_zero_in_filled_range": int(np.count_nonzero(window < 0)),
        "n_bins_eq_zero_in_filled_range": int(np.count_nonzero(window == 0)),
        # Split out, because the two causes are different problems. A bin that
        # was never filled is a statistics problem (more MC, or wider bins). A
        # bin that WAS filled and still came out <= 0 is the negative-weight
        # cancellation that only an NLO sample produces, and is the case the
        # open question for Maryna is about.
        "n_bins_never_filled_in_range": int(np.count_nonzero(~was_filled)),
        "n_filled_bins_le_zero": int(np.count_nonzero(was_filled & (window <= 0))),
        "n_filled_bins_lt_zero": int(np.count_nonzero(was_filled & (window < 0))),
        "n_filled_bins_eq_zero": int(np.count_nonzero(was_filled & (window == 0))),
        "most_negative_content": float(window.min()) if window.size else None,
    }
