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
    `uproot.recreate(...)`.
  - UPDATE (Step 2, full run): the shared pipeline writes TH1F (float32
    bin contents), not TH1D. uproot's plain `file[key] = (values, edges)`
    shortcut always produces a TH1D regardless of the array's dtype
    (confirmed directly: a float32 values array still round-trips as
    TH1D) -- so matching TH1F requires uproot's lower-level
    `uproot.writing.identify.to_TH1x` constructor instead, which DOES
    key its return class off the dtype of its `data` argument per its
    own docstring ("The dtype of this array determines the return type
    of this function (TH1C, TH1D, TH1F, TH1I, or TH1S)"). See
    `to_writable_th1f` below -- confirmed round-trips as a genuine TH1F
    with float32 bin contents, readable by real ROOT/PyROOT elsewhere,
    with no PyROOT needed on this end at all.
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
import uproot.writing.identify as _uproot_identify

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


# --- Display-range parity with the shared pipeline's trim_empty_tail -----
#
# services/pipelines/histograms_pipeline.py:26-41 (trim_empty_tail, exact
# source at the commit this branch was built from):
#
#     def trim_empty_tail(hist: ROOT.TH1F) -> None:
#         last_filled = 0
#         for b in range(hist.GetNbinsX(), 0, -1):
#             if hist.GetBinContent(b) > 0:
#                 last_filled = b
#                 break
#         if last_filled > 0:
#             hist.GetXaxis().SetRangeUser(
#                 hist.GetXaxis().GetXmin(),
#                 hist.GetBinLowEdge(last_filled + 1)
#             )
#
# Read precisely (not paraphrased): this scans from the LAST bin down to
# bin 1 for the last one with content > 0 ("last_filled", a 1-based ROOT
# bin index). If NONE is found (an all-empty histogram), the function
# returns without touching the axis at all -- the axis is left exactly as
# it was before the call (for a histogram whose axis was never previously
# ranged, that is ROOT's own untouched-TAxis default: fFirst=0, fLast=0,
# the kAxisRange status bit NOT set -- see below). If one IS found, it
# calls SetRangeUser(GetXmin(), <last_filled bin's own upper edge>) --
# note the LOWER bound passed is the axis's own original minimum, NOT the
# first filled bin: this function trims only the TRAILING (upper) empty
# region, never a leading one. That matters here because our own
# histograms' filled region does not start at the axis minimum (the
# pipeline's peak-removal step already deleted everything below the peak
# from the underlying mass array, so bins between 0 and the peak are
# empty-but-present on the fixed 0-10000 GeV grid) -- trim_empty_tail, run
# on a real pipeline histogram in this same situation, would NOT crop that
# leading empty region either. Replicating it exactly (not "improving" it
# to crop both sides) is the point: a pipeline-produced file and ours must
# open identically.
#
# What SetRangeUser(ufirst, ulast) actually sets, per ROOT's own source
# (root.cern, tag v6-32; TAxis.h:65 for the bit, TAxis.cxx:1052-1100 for
# the two methods -- fetched and quoted directly, not from memory):
#
#     // TAxis.h:65
#     kAxisRange = BIT(11),   // i.e. 1 << 11 == 0x800 == 2048
#
#     // TAxis.cxx:1052-1072
#     void TAxis::SetRange(Int_t first, Int_t last) {
#       Int_t nCells = fNbins + 1;
#       if (last < first || (first < 0 && last < 0) ||
#           (first > nCells && last > nCells) || (first == 0 && last == 0)) {
#         fFirst = 1; fLast = fNbins; SetBit(kAxisRange, false);
#       } else {
#         fFirst = std::max(first, 0);
#         fLast = std::min(last, nCells);
#         SetBit(kAxisRange, true);
#       }
#     }
#
#     // TAxis.cxx:1080-1100
#     void TAxis::SetRangeUser(Double_t ufirst, Double_t ulast) {
#       Int_t ifirst = FindFixBin(ufirst);
#       Int_t ilast = FindFixBin(ulast);
#       if (GetBinUpEdge(ifirst) <= ufirst) ifirst += 1;
#       if (GetBinLowEdge(ilast) >= ulast) ilast -= 1;
#       SetRange(ifirst, ilast);
#     }
#
# Working through trim_empty_tail's own call with ufirst=GetXmin() (bin 1's
# own lower edge -- FindFixBin gives ifirst=1, the edge-fix does not move
# it) and ulast=GetBinLowEdge(last_filled+1) (EXACTLY bin last_filled+1's
# lower edge, so FindFixBin gives last_filled+1, and the edge-fix
# `GetBinLowEdge(ilast) >= ulast` is then true, so ilast -= 1 gives
# last_filled): the net, always-taken result is fFirst=1, fLast=last_filled,
# kAxisRange SET.
#
# CRUCIALLY, per that same source: TAxis::GetFirst()/GetLast() -- the
# methods any real reader (ROOT's own Draw(), TBrowser, TAxis's own context
# menu, etc.) actually calls to find the display range -- are:
#
#     Int_t TAxis::GetFirst() const { if (!TestBit(kAxisRange)) return 1; return fFirst; }
#     Int_t TAxis::GetLast()  const { if (!TestBit(kAxisRange)) return fNbins; return fLast; }
#
# i.e. fFirst/fLast are IGNORED unless the kAxisRange bit is set. Writing
# fFirst/fLast alone (which uproot's to_TAxis(fFirst=..., fLast=...) DOES
# support directly) without also setting that bit would therefore be a
# complete no-op for any real reader -- confirmed empirically too (see
# _set_trim_empty_tail_range's own docstring for why the bit cannot be set
# by assigning to the axis model's `_members["@fBits"]`, and what does
# work instead).
#
# UNVERIFIED: no ROOT installation (PyROOT) is available in this project's
# cluster conda env (RECIPE.md section 7a) or, checked directly for this
# task, in any other env on that account either -- so the round-trip below
# is verified by re-opening the written file with uproot and checking
# fFirst/fLast/the raw fBits value directly, not by opening it in real
# ROOT. No real pipeline-produced ROOT histogram (one that went through
# trim_empty_tail for real) was found anywhere in this repository or on
# the cluster to compare against byte-for-byte either (searched both,
# 2026-09-24) -- the ROOT source quoted above is the evidence in its
# place, not a live comparison.

_KAXISRANGE_BIT = 1 << 11  # TAxis.h:65, kAxisRange = BIT(11)


def _last_nonempty_root_bin(values: np.ndarray) -> int:
    """The 1-based ROOT bin index of the last bin with content > 0, or 0 if
    none (all-empty histogram) -- the exact same scan trim_empty_tail
    itself does (services/pipelines/histograms_pipeline.py:32-36), just
    vectorized instead of a Python loop counting down from the end."""
    nonzero = np.nonzero(values > 0)[0]
    if len(nonzero) == 0:
        return 0
    return int(nonzero[-1]) + 1  # numpy index -> 1-based ROOT bin


def _set_trim_empty_tail_range(xaxis, last_filled_root_bin: int) -> None:
    """Sets `xaxis` (a `uproot.writing.identify.to_TAxis(...)` result) to
    the exact fFirst/fLast/kAxisRange state trim_empty_tail's own
    SetRangeUser call produces (see the module-level derivation above):
    fFirst=1, fLast=last_filled_root_bin, kAxisRange set. A no-op if
    `last_filled_root_bin` is 0 (all-empty histogram), matching
    trim_empty_tail's own `if last_filled > 0:` guard exactly -- an
    all-empty histogram's axis is left in ROOT's untouched-TAxis default
    (fFirst=0, fLast=0, kAxisRange unset), which is already uproot's own
    default for a `to_TAxis(...)` call with no fFirst/fLast given, so
    nothing needs to change for that case.

    Why this cannot be done by setting `fFirst`/`fLast` alone: uproot's
    `to_TAxis(fFirst=..., fLast=...)` parameters DO write real fFirst/fLast
    TAxis members (confirmed by round-trip below) -- but the kAxisRange
    status bit lives on the TAxis's inherited TObject base, and uproot's
    writer does NOT source that bit from the model's own
    `_members["@fBits"]` at write time (confirmed by direct experiment:
    setting it there has no effect on the written bytes) -- instead, every
    writable model's `_serialize(out, header, name, tobject_flags)` method
    receives the eventual on-disk flags word as its `tobject_flags`
    ARGUMENT, threaded down recursively from the top-level `serialize()`
    call (which always starts it at 0) and ORs in fixed bits along the way
    (e.g. `uproot.models.TNamed.Model_TNamed._serialize` unconditionally
    ORs in kIsOnHeap|kNotDeleted) -- there is no public parameter, on
    `to_TAxis`, `to_TH1x`, or anywhere else in uproot's writing API, that
    lets a caller inject an additional bit into that word for one specific
    sub-object. This function does the only thing that reaches it: it
    wraps THIS axis instance's own bound `_serialize` method (a per-object,
    per-write-call override, not a global monkeypatch of the uproot
    class -- every other histogram/axis in this or any other file is
    unaffected) so that whatever `tobject_flags` it would have received is
    OR'd with kAxisRange before being forwarded to the real implementation.
    Verified round-trip (this module's own test suite, and manually via
    `uproot.open(...)["...."] .member("fXaxis").member("@fBits")`):
    fBits reads back as kIsOnHeap|kNotDeleted|kAxisRange, exactly as a real
    ROOT-written ranged axis would (module docstring above), with bin
    contents byte-for-byte unaffected.
    """
    if last_filled_root_bin <= 0:
        return
    xaxis._members["fFirst"] = 1
    xaxis._members["fLast"] = int(last_filled_root_bin)
    original_serialize = xaxis._serialize

    def _serialize_with_axis_range(out, header, name, tobject_flags, _orig=original_serialize):
        return _orig(out, header, name, np.uint32(tobject_flags) | np.uint32(_KAXISRANGE_BIT))

    xaxis._serialize = _serialize_with_axis_range


def to_writable_th1f(values: np.ndarray, edges: np.ndarray, title: str):
    """Builds a genuine, writable ROOT TH1F (float32 bin contents) from a
    (values, edges) numpy pair, via uproot.writing.identify.to_TH1x
    directly (see this module's docstring: uproot's plain
    `file[key] = (values, edges)` shortcut always writes a TH1D
    regardless of dtype; to_TH1x's own docstring says its `data`
    argument's dtype IS what selects TH1F vs TH1D vs ... -- confirmed by
    writing+reading back one directly, `classname == "TH1F"`).

    `title` becomes both the TH1's title and (once assigned via
    `file[name] = to_writable_th1f(...)`) its ROOT-internal name -- the
    key used in that assignment is what actually determines the
    read-back `.name`; `title` here only needs to be informative, not
    necessarily identical to the eventual key (callers should still pass
    the same string for both, to keep name==title as in the pilot).

    `data` must include the underflow (index 0) and overflow (last index)
    bins around the real bin contents (ROOT's own TH1 on-disk convention);
    `values` here has no under/overflow of its own (this study's inputs
    are already clipped into range by make_fixed_grid_histogram), so
    those two slots are always zero.

    The written histogram's x-axis DISPLAY range (never its bin content)
    is set to match the shared pipeline's own trim_empty_tail exactly --
    see the module-level comment above _last_nonempty_root_bin for the
    full derivation and citations.
    """
    n_bins = len(values)
    data = np.zeros(n_bins + 2, dtype=np.float32)
    data[1:-1] = values.astype(np.float32)

    xaxis = _uproot_identify.to_TAxis(
        "xaxis", "", n_bins, float(edges[0]), float(edges[-1]),
        fXbins=np.asarray(edges, dtype=np.float64),
    )
    _set_trim_empty_tail_range(xaxis, _last_nonempty_root_bin(values))

    values_f64 = values.astype(np.float64)
    return _uproot_identify.to_TH1x(
        fName=None,
        fTitle=title,
        data=data,
        fEntries=float(values_f64.sum()),
        fTsumw=float(values_f64.sum()),
        fTsumw2=float((values_f64 ** 2).sum()),
        fTsumwx=0.0,
        fTsumwx2=0.0,
        fSumw2=None,
        fXaxis=xaxis,
    )


def verify_written_th1f(root_path: str, expected: Dict[str, np.ndarray]) -> None:
    """Re-opens `root_path` with uproot and asserts, for every
    `key -> values` pair in `expected`, that the on-disk histogram's
    class is exactly TH1F, its bin contents equal `values` (float32
    precision -- rtol chosen to comfortably clear float32 rounding of
    typical bin-count magnitudes here, well under 1 part in 10^5), AND its
    x-axis display range matches trim_empty_tail's own behaviour exactly
    (see _set_trim_empty_tail_range's docstring for the full derivation):
    fFirst=1, fLast=<last bin with content>0>, kAxisRange bit set -- or,
    for an all-empty histogram, fFirst=fLast=0 and the bit unset (the
    untouched-axis default, since trim_empty_tail itself is a no-op on an
    all-empty histogram). Raises AssertionError with a specific message
    identifying which histogram/aspect failed, rather than silently
    trusting the write.
    """
    import uproot as _uproot
    f = _uproot.open(root_path)
    on_disk = set(k.split(";")[0] for k in f.keys())
    missing = set(expected) - on_disk
    if missing:
        raise AssertionError(f"{root_path}: expected histogram(s) missing after write: {sorted(missing)}")
    for key, values in expected.items():
        hist = f[key]
        if hist.classname != "TH1F":
            raise AssertionError(f"{root_path}: {key} is {hist.classname}, expected TH1F")
        on_disk_values = hist.values()
        if not np.allclose(on_disk_values, values.astype(np.float32), rtol=1e-5, atol=1e-3):
            raise AssertionError(
                f"{root_path}: {key} bin contents do not match after write/read "
                f"(max abs diff {np.max(np.abs(on_disk_values - values)):.6g})"
            )

        expected_last = _last_nonempty_root_bin(values)
        xaxis = hist.member("fXaxis")
        actual_first = xaxis.member("fFirst")
        actual_last = xaxis.member("fLast")
        actual_range_bit = bool(xaxis.member("@fBits") & _KAXISRANGE_BIT)
        if expected_last <= 0:
            expected_first, expected_bit = 0, False
        else:
            expected_first, expected_bit = 1, True
            expected_last = expected_last  # last non-empty bin, already computed
        if (actual_first, actual_last, actual_range_bit) != (expected_first, expected_last, expected_bit):
            raise AssertionError(
                f"{root_path}: {key} display range mismatch -- "
                f"got (fFirst={actual_first}, fLast={actual_last}, kAxisRange={actual_range_bit}), "
                f"expected (fFirst={expected_first}, fLast={expected_last}, kAxisRange={expected_bit})"
            )


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
