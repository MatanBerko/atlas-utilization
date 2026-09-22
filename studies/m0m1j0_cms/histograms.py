"""
m0m1j0 CMS histogram -- Step 1 ROOT histogram building.

ROOT-dependent (unlike studies/m0m1j0_cms/selection.py): builds one TH1F
per exact final state (>=2 muons, >=1 light jet) plus one deliberately
non-BumpNet-named inclusive TH1F, on the SAME fixed grid and using the
SAME naming convention the shared pipeline would use -- imported directly,
not re-derived (RECIPE.md sections 4, 6, 7):

  - FIXED_MASS_MIN_GEV / FIXED_MASS_MAX_GEV / _fill_mass / trim_empty_tail
    from services.pipelines.histograms_pipeline (never hardcoded here).
  - _convert_to_bumpnet_name from the same module, for the real
    "mass_<combo>_cat_<fs>" name -- the ROOT-internal TH1F name additionally
    gets a "ROI_" prefix at write time here, exactly mirroring
    services/pipelines/histograms_pipeline.py:380 (the known ROI_/grouping-
    name mismatch documented in docs/CMS_KNOWN_LIMITATIONS.md, not fixed).
  - limit_particles_in_fs from services.calculations.physics_calcs, for the
    exact-count/capped-at-4 final-state string (RECIPE.md section 4) -- see
    the "Grouping note" below for why group_by_final_state itself is not
    called directly.

MIN_EVENTS_PER_FINAL_STATE (config.yaml's min_events_per_fs=100, RECIPE.md
section 5/6.5) is applied here: a final state's histogram is only created
if its own event count (after the z_peak/max_mass cutoff already applied
to `mass` by the caller) is >= the threshold. Dropped final states are
reported, never silently omitted from the returned metadata.

Grouping note: this module reimplements the six-field per-event
final-state STRING construction that
services.calculations.physics_calcs.group_by_final_state also does
internally (same fields, same order, same formula) rather than calling
that generator directly -- group_by_final_state only yields
`(label, events[mask])`, not the mask itself, so there is no way to slice
the SEPARATELY-computed `mass` array (not a field of `obj_record`) in
lockstep with its output. Reusing group_by_final_state would have meant
either bundling `mass` into `obj_record` as a fake jagged field (fragile:
ak.num(events) there is called on the whole record, so a flat non-jagged
field breaks it) or recomputing the mask afterwards anyway. The two
non-trivial pieces of the shared naming/categorization logic --
limit_particles_in_fs's >4 capping rule and _convert_to_bumpnet_name's
exact string format -- ARE imported and reused directly (see below); only
the trivial "join six counts into `{e}e_{m}m_{j}j_{g}g_{t}t_{b}b`" loop is
duplicated, verbatim, from services/calculations/physics_calcs.py:61-83.
"""
from __future__ import annotations

from typing import Dict, Tuple

import awkward as ak
import numpy as np
import ROOT

from services.calculations.physics_calcs import limit_particles_in_fs
from services.pipelines.histograms_pipeline import (
    FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV, _fill_mass, _convert_to_bumpnet_name,
    trim_empty_tail,
)

from studies.m0m1j0_cms.selection import MIN_EVENTS_PER_FINAL_STATE

BIN_WIDTH_GEV = 10.0  # config.yaml:166, mirrored
INCLUSIVE_HIST_NAME = "mass_m0m1j0_inclusive_ge2m_ge1j"


def _n_bins() -> int:
    span = FIXED_MASS_MAX_GEV - FIXED_MASS_MIN_GEV
    n = round(span / BIN_WIDTH_GEV)
    if abs(n * BIN_WIDTH_GEV - span) > 1e-9:
        raise ValueError(
            f"FIXED_MASS range [{FIXED_MASS_MIN_GEV}, {FIXED_MASS_MAX_GEV}] is not an "
            f"exact multiple of BIN_WIDTH_GEV={BIN_WIDTH_GEV}"
        )
    return int(n)


def make_fixed_grid_histogram(name: str, values) -> ROOT.TH1F:
    """One TH1F on the shared fixed grid, filled via the pipeline's own
    _fill_mass (handles the exact-10000.0-GeV boundary the same way the
    shared pipeline does)."""
    hist = ROOT.TH1F(name, name, _n_bins(), FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV)
    hist.Sumw2()
    values_np = ak.to_numpy(values) if not isinstance(values, np.ndarray) else values
    for v in values_np:
        if np.isnan(v):
            continue
        _fill_mass(hist, float(v))
    return hist


def per_event_raw_and_capped_final_state(obj_record: ak.Array):
    """Per-event (raw_fs_string, capped_bumpnet_category) numpy string
    arrays, aligned 1:1 with `obj_record` -- the same six-field formula
    services.calculations.physics_calcs.group_by_final_state uses
    internally (see this module's "Grouping note"), exposed here so
    callers needing a PER-EVENT category (the outlier event list, the
    merge step's top-categories plot) don't duplicate this a third time.
    """
    n = len(obj_record)
    if n == 0:
        empty = np.array([], dtype=object)
        return empty, empty
    zero = np.zeros(n, dtype=np.int64)
    counts = ak.num(obj_record)
    e = ak.to_numpy(getattr(counts, "Electrons", zero))
    m = ak.to_numpy(getattr(counts, "Muons", zero))
    j = ak.to_numpy(getattr(counts, "Jets", zero))
    g = zero
    t = zero
    b = ak.to_numpy(getattr(counts, "BJets", zero))
    raw_fs = np.array(
        [f"{e_}e_{m_}m_{j_}j_{g_}g_{t_}t_{b_}b" for e_, m_, j_, g_, t_, b_ in zip(e, m, j, g, t, b)]
    )
    capped = np.array([
        _convert_to_bumpnet_name(limit_particles_in_fs(str(fs), 4), "m0m1j0") for fs in raw_fs
    ])
    return raw_fs, capped


def build_m0m1j0_histograms(
    obj_record: ak.Array, mass: ak.Array, apply_min_events_prune: bool = True
) -> Tuple[Dict[str, ROOT.TH1F], Dict[str, dict]]:
    """
    Args:
        obj_record: events already restricted to >=2 selected muons and
            >=1 selected light jet, zipped with Electrons/Muons/Jets/BJets
            fields (studies.m0m1j0_cms.selection.build_object_record).
        mass: the m0m1j0 mass for each of those same events, in the same
            order, with the z_peak_cutoff/max_mass_cutoff already applied
            (NaN for events cut out -- studies.m0m1j0_cms.selection
            .apply_z_peak_and_mass_cutoff).
        apply_min_events_prune: whether to drop (rather than write) a
            category whose OWN event count here is below
            MIN_EVENTS_PER_FINAL_STATE. min_events_per_fs is, in the
            ATLAS recipe, a GLOBAL population count taken AFTER merging
            every job's shards (services/storage/sqlite_shards.py
            :159-238, RECIPE.md section 5) -- so a per-job cluster driver
            processing a single file MUST pass False here (a single file's
            own count is not the right population to prune on) and let a
            separate merge step apply this check once, after summing
            every job's histograms by category. Defaults True for
            standalone/single-shot use (e.g. this module's own tests).

    Returns:
        (histograms, meta) where `histograms` maps the real BumpNet
        category name (or INCLUSIVE_HIST_NAME) -> TH1F, with every
        TH1F's ROOT-internal name carrying the ROI_/width_ decoration
        (see this module's docstring); `meta` reports, per category, the
        event count and whether min_events_per_fs pruned it, plus the
        inclusive count -- always present, even for dropped categories.
    """
    mass_np = ak.to_numpy(mass)
    n_total_events = len(mass_np)

    histograms: Dict[str, ROOT.TH1F] = {}
    meta: Dict[str, dict] = {}

    inclusive_hist = make_fixed_grid_histogram(
        f"ROI_{INCLUSIVE_HIST_NAME}_width_{int(BIN_WIDTH_GEV)}", mass_np
    )
    trim_empty_tail(inclusive_hist)
    histograms[INCLUSIVE_HIST_NAME] = inclusive_hist
    meta[INCLUSIVE_HIST_NAME] = {
        "n_events_in_histogram": int(np.sum(~np.isnan(mass_np))),
        "n_events_before_z_peak_and_mass_cutoff": n_total_events,
        "pruned_by_min_events_per_fs": False,
    }

    if n_total_events == 0:
        return histograms, meta

    _raw_fs_per_event, bumpnet_name_per_event = per_event_raw_and_capped_final_state(obj_record)

    # Group directly by the final BumpNet name (already capped at 4 --
    # limit_particles_in_fs is applied inside
    # per_event_raw_and_capped_final_state), so e.g. 4 vs 5 muons -- which
    # both display as "4mx" -- are correctly accumulated into ONE
    # histogram rather than silently overwriting each other.
    mass_by_bumpnet_name: Dict[str, list] = {}
    for bumpnet_name in np.unique(bumpnet_name_per_event):
        mask = bumpnet_name_per_event == bumpnet_name
        mass_by_bumpnet_name.setdefault(str(bumpnet_name), []).append(mass_np[mask])

    dropped_categories = []
    for bumpnet_name, mass_chunks in mass_by_bumpnet_name.items():
        cat_mass = np.concatenate(mass_chunks)
        n_events_in_cat = int(np.sum(~np.isnan(cat_mass)))
        n_events_before_cutoff = len(cat_mass)

        if apply_min_events_prune and n_events_in_cat < MIN_EVENTS_PER_FINAL_STATE:
            dropped_categories.append(bumpnet_name)
            meta[bumpnet_name] = {
                "n_events_in_histogram": 0,
                "n_events_before_z_peak_and_mass_cutoff": n_events_before_cutoff,
                "n_events_after_cutoff_before_pruning": n_events_in_cat,
                "pruned_by_min_events_per_fs": True,
            }
            continue

        hist = make_fixed_grid_histogram(f"ROI_{bumpnet_name}_width_{int(BIN_WIDTH_GEV)}", cat_mass)
        trim_empty_tail(hist)
        histograms[bumpnet_name] = hist
        meta[bumpnet_name] = {
            "n_events_in_histogram": n_events_in_cat,
            "n_events_before_z_peak_and_mass_cutoff": n_events_before_cutoff,
            "pruned_by_min_events_per_fs": False,
        }

    meta["_dropped_categories_below_min_events_per_fs"] = dropped_categories
    return histograms, meta
