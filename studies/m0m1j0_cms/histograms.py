"""
m0m1j0 CMS histogram -- Step 1 ROOT histogram building.

ENVIRONMENT FINDING (discovered running the pilot, 2026-09-22): the
cluster's own `atlas-pipeline` conda env
(/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline) has NO
PyROOT installed, and there is no system `root`/`root-config` on this
account either. `services/pipelines/histograms_pipeline.py` does
`import ROOT` at MODULE level, so it cannot even be IMPORTED in that
env -- not just "the histogram-building call fails", the whole module
fails at `import`. Confirmed directly:
    $ python -c "import services.pipelines.histograms_pipeline"
    ModuleNotFoundError: No module named 'ROOT'
This means the task's own instruction to literally `import` FIXED_MASS_
MIN_GEV/MAX_GEV, _fill_mass, trim_empty_tail, and _convert_to_bumpnet_name
from that module cannot be carried out as a real import in this
environment -- doing so would make every cluster job crash immediately.
This is a real, non-obvious environment gap worth the group's attention
separately (whether the shared pipeline's own histogram_creation_task
has ever actually been run end-to-end on this cluster account is
unclear); it is NOT something this study is authorized to fix by
installing PyROOT into the shared `atlas-pipeline` env (that env is used
by other studies, e.g. studies/hgg_cms, and modifying shared
infrastructure is outside this task's scope).

WORKAROUND USED HERE (no shared code or environment touched):
  - The two numeric constants (FIXED_MASS_MIN_GEV/MAX_GEV) and the
    _convert_to_bumpnet_name function are copied VERBATIM below, with an
    explicit citation to the exact source lines they were copied from
    (services/pipelines/histograms_pipeline.py:22-23, 419-453 at the
    commit this branch was built from) -- byte-identical logic, just not
    a live `import` (which is impossible here). If that module's logic
    ever changes, this copy will silently drift -- flagged here so a
    future reader knows to re-diff it, not treated as fixed forever.
  - limit_particles_in_fs IS still a real, live import from
    services.calculations.physics_calcs -- that module has no ROOT/fcntl
    dependency at all and imports cleanly in this env (confirmed
    directly), so no copy was needed for it.
  - Histograms are built and returned as plain (values, edges) numpy
    array pairs instead of ROOT.TH1F objects, and written to disk via
    `uproot.recreate(...)` (confirmed: uproot writes a genuine ROOT TH1D
    from a (values, edges) tuple, readable by real ROOT/PyROOT
    elsewhere, with no PyROOT needed on this end at all) rather than via
    PyROOT's TFile/TH1F -- same on-disk ROOT histogram format, same
    binning, same naming, just written through a different library.
  - trim_empty_tail's cosmetic axis-range trim (ROOT's SetRangeUser,
    display-only, never touches stored bin content per
    histograms_pipeline.py:26-41) is NOT reproduced in the written ROOT
    file here -- there is no PyROOT axis object to call SetRangeUser on
    via uproot's writer. The same information (last non-empty bin) is
    reported in each job's JSON metadata and applied directly in the
    pilot's own sanity-check PNGs instead.

Builds one histogram per exact final state (>=2 muons, >=1 light jet)
plus one deliberately non-BumpNet-named inclusive histogram, on the SAME
fixed grid and using the SAME naming convention the shared pipeline
would use (RECIPE.md sections 4, 6, 7) -- ROI_-prefixed ROOT-internal
name, "mass_<combo>_cat_<fs>" grouping name, exact-count/capped-at-4
final-state string.

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
field breaks it) or recomputing the mask afterwards anyway. limit_particles_in_fs's
>4 capping rule IS imported and reused directly; only the trivial "join
six counts into `{e}e_{m}m_{j}j_{g}g_{t}t_{b}b`" loop is duplicated,
verbatim, from services/calculations/physics_calcs.py:61-83.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import awkward as ak
import numpy as np

from services.calculations.physics_calcs import limit_particles_in_fs

from studies.m0m1j0_cms.selection import MIN_EVENTS_PER_FINAL_STATE

# Copied verbatim from services/pipelines/histograms_pipeline.py:22-23 --
# see this module's docstring for why these cannot be live-imported here.
FIXED_MASS_MIN_GEV = 0.0
FIXED_MASS_MAX_GEV = 10000.0

BIN_WIDTH_GEV = 10.0  # config.yaml:166, mirrored
INCLUSIVE_HIST_NAME = "mass_m0m1j0_inclusive_ge2m_ge1j"

Histogram = Tuple[np.ndarray, np.ndarray]  # (bin_values, bin_edges) -- uproot's own histogram-write shape


def _n_bins() -> int:
    span = FIXED_MASS_MAX_GEV - FIXED_MASS_MIN_GEV
    n = round(span / BIN_WIDTH_GEV)
    if abs(n * BIN_WIDTH_GEV - span) > 1e-9:
        raise ValueError(
            f"FIXED_MASS range [{FIXED_MASS_MIN_GEV}, {FIXED_MASS_MAX_GEV}] is not an "
            f"exact multiple of BIN_WIDTH_GEV={BIN_WIDTH_GEV}"
        )
    return int(n)


def _convert_to_bumpnet_name(fs_str: str, im_str: str) -> str:
    """Copied verbatim from
    services/pipelines/histograms_pipeline.py:419-453 (this module's
    docstring explains why it cannot be live-imported in this
    environment). Do not edit independently of that source."""
    combo = im_str if im_str else "none"
    import re
    fs_particles = re.findall(r'(\d+)([emjgtb])', fs_str)
    fs_formatted = "_".join(f"{c}{p}x" for c, p in fs_particles)
    result = f"mass_{combo}_cat_{fs_formatted}"
    if 'cat' not in result and 'hCat' not in result:
        raise ValueError(
            f"Generated histogram name '{result}' doesn't contain 'cat' -- "
            "BumpNet incompatible"
        )
    return result


def make_fixed_grid_histogram(values) -> Histogram:
    """One (values, edges) histogram pair on the shared fixed grid,
    reproducing _fill_mass's own exact-10000.0-GeV boundary handling
    (services/pipelines/histograms_pipeline.py:67-72: nudge an exact max
    value down by one ULP so it lands in the last real bin, not
    overflow) -- see this module's docstring for why that function is
    reimplemented rather than imported."""
    n_bins = _n_bins()
    counts = np.zeros(n_bins, dtype=np.float64)
    edges = np.linspace(FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV, n_bins + 1)

    values_np = ak.to_numpy(values) if not isinstance(values, np.ndarray) else values
    finite = values_np[~np.isnan(values_np)]
    nudged = np.where(finite == FIXED_MASS_MAX_GEV, math.nextafter(FIXED_MASS_MAX_GEV, FIXED_MASS_MIN_GEV), finite)
    in_range = (nudged >= FIXED_MASS_MIN_GEV) & (nudged < FIXED_MASS_MAX_GEV)
    bin_idx = np.floor((nudged[in_range] - FIXED_MASS_MIN_GEV) / BIN_WIDTH_GEV).astype(np.int64)
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)
    np.add.at(counts, bin_idx, 1.0)
    return counts, edges


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
) -> Tuple[Dict[str, Histogram], Dict[str, dict]]:
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
        category name (or INCLUSIVE_HIST_NAME) -> (values, edges), with
        the ROI_/width_ ROOT-internal-name decoration applied by the
        CALLER at write time (see cluster/run_m0m1j0_on_file.py); `meta`
        reports, per category, the event count and whether
        min_events_per_fs pruned it, plus the inclusive count -- always
        present, even for dropped categories.
    """
    mass_np = ak.to_numpy(mass)
    n_total_events = len(mass_np)

    histograms: Dict[str, Histogram] = {}
    meta: Dict[str, dict] = {}

    histograms[INCLUSIVE_HIST_NAME] = make_fixed_grid_histogram(mass_np)
    meta[INCLUSIVE_HIST_NAME] = {
        "n_events_in_histogram": int(np.sum(~np.isnan(mass_np))),
        "n_events_before_z_peak_and_mass_cutoff": n_total_events,
        "pruned_by_min_events_per_fs": False,
    }

    if n_total_events == 0:
        meta["_dropped_categories_below_min_events_per_fs"] = []
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

        histograms[bumpnet_name] = make_fixed_grid_histogram(cat_mass)
        meta[bumpnet_name] = {
            "n_events_in_histogram": n_events_in_cat,
            "n_events_before_z_peak_and_mass_cutoff": n_events_before_cutoff,
            "pruned_by_min_events_per_fs": False,
        }

    meta["_dropped_categories_below_min_events_per_fs"] = dropped_categories
    return histograms, meta
