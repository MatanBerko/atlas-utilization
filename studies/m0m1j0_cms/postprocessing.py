"""
m0m1j0 CMS histogram -- v2 correction: the shared pipeline's REAL
post-processing, applied via its own functions.

Background (full story in RECIPE.md's "CORRECTION" note, 2026-09-22):
Steps 1/2 of this study (studies/m0m1j0_cms/pilot/, studies/m0m1j0_cms/full/)
never applied the pipeline's array-level peak-removal / first-empty-bin
outlier-split / exclude_outliers chain. That chain has NO config flag --
it is unconditional in `services/pipelines/post_processing_pipeline.py`
for every final-state mass array -- and was mistakenly believed to be
"off" (a misreading of `apply_peak_removal_at_histogram_level`, which
controls a separate, additional, histogram-level step, not this one).
This module imports and calls the pipeline's own functions directly, in
the pipeline's own order, rather than re-deriving them.

Real order (confirmed directly, post_processing_pipeline.py:162-256):
  1. min_events_per_fs pruning, on the RAW (pre-z_peak/pre-max_mass)
     per-final-state population, globally across the whole dataset.
  2. z_peak_cutoff (via the real _apply_z_peak_cut -- only removes
     anything for a same-flavor-dilepton signature; m0m1j0 contains two
     muons, so this always applies here -- RECIPE.md section 5/6.3).
  3. max_mass_cutoff (10 TeV hard cap).
  4. peak removal: the real _find_rightmost_highest_peak, then drop
     everything strictly below the returned peak mass.
  5. first-empty-bin split: the real _split_by_first_empty_bin into
     main/outliers.
  6. histogram from "_main" only -- exclude_outliers=true
     (config.yaml:171) drops any "_outliers"-suffixed signature entirely
     before histogram-building starts (histograms_pipeline.py:158-163,
     230-233) -- so "_outliers" is reported here but never histogrammed.

Exception, deliberately NOT imported: `prune_final_states_below_min_events`
(services/storage/sqlite_shards.py) operates on SQLite database FILES (it
deletes rows in-place) -- this study never uses the SQLite architecture
(RECIPE.md deviation 6), so manufacturing synthetic SQLite files just to
call a file-oriented function on them would be pure overhead for no
behavioral difference. Its LOGIC is mirrored exactly instead: the same
comparison it performs (`count < min_events` -> removed,
services/storage/sqlite_shards.py:229) is applied directly to the same
per-category raw counts this module's caller already holds in memory,
via raw_count_passes_min_events_prune below.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np

from services.pipelines.post_processing_pipeline import (
    _apply_z_peak_cut, _find_rightmost_highest_peak, _split_by_first_empty_bin,
)

from studies.m0m1j0_cms.selection import MAX_MASS_CUTOFF_GEV, MIN_EVENTS_PER_FINAL_STATE, Z_PEAK_CUTOFF_GEV

# config.yaml:154 (peak_detection_bin_width_gev) -- same value as the
# histogram bin width (config.yaml:166); imported nowhere from the
# broken-in-this-env histograms_pipeline.py (RECIPE.md section 7a), so
# stated directly here with its own citation, same as histograms.py does
# for FIXED_MASS_MIN_GEV/MAX_GEV.
PEAK_DETECTION_BIN_WIDTH_GEV = 10.0

_logger = logging.getLogger(__name__)


def raw_count_passes_min_events_prune(raw_count: int) -> bool:
    """Mirrors prune_final_states_below_min_events's own comparison
    (services/storage/sqlite_shards.py:229) -- applied to the RAW,
    pre-z_peak/pre-max_mass per-category count (the real pipeline's
    order: pruning happens BEFORE the z_peak/max_mass/peak/split chain,
    not after -- RECIPE.md correction)."""
    return raw_count >= MIN_EVENTS_PER_FINAL_STATE


def apply_full_postprocessing(raw_mass: np.ndarray, category_label: str) -> Dict:
    """
    Runs the real pipeline's own per-final-state post-processing chain,
    in its own order, on one category's full (globally merged, raw,
    pre-z_peak/pre-max_mass) mass array. Returns a dict with every
    intermediate count, the peak mass, an approximate split mass, and
    main_array/outliers_array -- only main_array is ever histogrammed
    (exclude_outliers=true).

    `category_label` can be any string; it is embedded in a synthetic
    "..._IM_m0m1j0" signature purely so _apply_z_peak_cut's own regex-
    based signature parser recognizes the "m0m1j0" combo token (two
    muons -> same-flavor dilepton -> the z_peak_cutoff floor applies).
    """
    n_raw = len(raw_mass)
    signature = f"{category_label}_IM_m0m1j0"

    after_z_peak = _apply_z_peak_cut(raw_mass, signature, Z_PEAK_CUTOFF_GEV, _logger)
    n_after_z_peak = len(after_z_peak)

    after_max_mass = (
        after_z_peak[after_z_peak <= MAX_MASS_CUTOFF_GEV] if MAX_MASS_CUTOFF_GEV > 0 else after_z_peak
    )
    n_after_max_mass = len(after_max_mass)

    empty_result = {
        "n_raw": n_raw, "n_after_z_peak": n_after_z_peak, "n_after_max_mass": n_after_max_mass,
        "peak_mass": None, "n_after_peak_removal": 0,
        "split_mass": None, "n_main": 0, "n_outliers": 0,
        "main_array": np.array([]), "outliers_array": np.array([]),
    }
    if n_after_max_mass == 0:
        return empty_result

    peak_mass = _find_rightmost_highest_peak(after_max_mass, PEAK_DETECTION_BIN_WIDTH_GEV, _logger)
    filtered = after_max_mass if peak_mass is None else after_max_mass[after_max_mass >= peak_mass]
    n_after_peak_removal = len(filtered)

    if n_after_peak_removal == 0:
        empty_result["peak_mass"] = float(peak_mass) if peak_mass is not None else None
        return empty_result

    main_array, outliers_array = _split_by_first_empty_bin(filtered, PEAK_DETECTION_BIN_WIDTH_GEV, _logger)

    split_mass: Optional[float] = float(np.min(outliers_array)) if len(outliers_array) > 0 else None

    return {
        "n_raw": n_raw,
        "n_after_z_peak": n_after_z_peak,
        "n_after_max_mass": n_after_max_mass,
        "peak_mass": float(peak_mass) if peak_mass is not None else None,
        "n_after_peak_removal": n_after_peak_removal,
        # "split_mass" is the smallest value the real _split_by_first_empty_bin
        # function's own outliers_array actually contains -- a genuine,
        # data-derived boundary, not necessarily bit-identical to that
        # function's internal bin-edge value (which it does not return).
        "split_mass": split_mass,
        "n_main": len(main_array),
        "n_outliers": len(outliers_array),
        "main_array": main_array,
        "outliers_array": outliers_array,
    }
