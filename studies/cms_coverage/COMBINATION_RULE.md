# The combination rule, from the shared code (Part 0)

Everything below was read directly from the shared code at the commit this
branch (`survey/cms-coverage`) was cut from
(`040ba672cada7ba861a78e048d8808cb47b30897`, `analysis/m0m1j0-cms`) and
reproduced by calling the real functions, not re-derived. This document
does not change any code; it explains what the code already does.

## The object types and the combinatorics rule

Source: `config.yaml:135-144` (`mass_calculation_task_config`), applied
through `services/calculations/combinatorics.py::get_all_combinations`.

```yaml
objects_to_calculate: [Electrons, Muons, Jets, BJets]
min_particles_in_combination: 1        # distinct particle TYPES per combination
max_particles_in_combination: 4
min_count_particle_in_combination: 1   # count PER TYPE
max_count_particle_in_combination: 4
max_total_particles_in_combination: 4  # hard cap, all types summed
include_subleading: true
max_subleading_index: 1
```

In plain words: a "combination" is a recipe for one invariant-mass
histogram — pick between 1 and 4 *distinct object types* (electron, muon,
jet, b-jet), between 1 and 4 *particles of each chosen type*, but never
more than 4 objects *in total* across the whole combination (so, e.g., 2
electrons + 2 jets is allowed at exactly the cap, but 2 electrons + 3 jets
is not — 5 > 4). A single-particle "combination" (just one object, no
partner) is excluded — an invariant mass needs at least two four-vectors —
so every combination has 2, 3, or 4 objects in total. `include_subleading:
true` additionally asks for variants that use the **second**-highest-pT
object of a type (e.g. `e1`, the sub-leading electron) instead of, or
alongside, the leading one (`e0`), up to `max_subleading_index: 1` (so we
go one rank deep — no "third electron" variants).

## Reproducing the count

**VERIFIED BY RUNNING**, calling `get_all_combinations` with these exact
arguments:

```python
from services.calculations.combinatorics import get_all_combinations
object_types = ["Electrons", "Muons", "Jets", "BJets"]
kwargs = dict(object_types=object_types, min_particles=1, max_particles=4,
              min_count=1, max_count=4, max_total_particles=4)
len(get_all_combinations(**kwargs, include_subleading=False))               # -> 65
len(get_all_combinations(**kwargs, include_subleading=True,
                          max_subleading_index=1))                          # -> 186
```

This reproduces the technical lead's numbers **exactly**: **65 without
sub-leading variants, 186 with them**.

Breakdown of the 186 (all from the same call, computed directly):

| by distinct object types in the combination | count |
|---|---|
| 1 type (e.g. `e0e1`, `m0m1j0`... wait, 1-type means e.g. two electrons only) | 12 |
| 2 types | 78 |
| 3 types | 80 |
| 4 types | 16 |

| by total object count | count |
|---|---|
| 2 objects | 28 |
| 3 objects | 60 |
| 4 objects | 98 |

| leading-only (every type at start index 0) | 65 |
|---|---|
| includes at least one sub-leading (start index ≥ 1) start index | 121 |

(65 + 121 = 186, consistent with the two counts above by construction —
`get_all_combinations` builds the 65 leading-only combinations first, then
adds every valid sub-leading variant of each on top, so the "leading-only"
row here is the same 65 as the `include_subleading=False` count.)

## Matching a combination against an event's final-state category

Source: `services/calculations/physics_calcs.py::is_finalstate_contain_combination`
(lines 101-126; `services/calculations/im_calculator.py`'s
`IMCalculator.does_final_state_contain_combination`, lines 130-152, is the
same logic as an instance method — both are used by the real pipeline
depending on call site, and this study calls the module-level one
directly).

An event's final-state category is a string like `"2e_0m_3j_0g"` (built by
`physics_calcs.group_by_final_state`, lines 61-83: the *exact* post-cut
counts of electrons/muons/jets/photons/taus/bjets, in that fixed order,
each count capped at 4 for display via `limit_particles_in_fs`). A
combination — e.g. `{"Muons": (2, 0), "Jets": (1, 0)}`, meaning "2 muons
starting at rank 0, 1 jet starting at rank 0" — is considered to "fit" a
final state if, for every object type the combination needs, the final
state's actual count is at least `start + count` (enough objects to reach
past the requested rank window). A combination that needs a sub-leading
object (`start=1`) therefore requires *one more* object of that type to be
present than the same count would with `start=0` — e.g. `m1j0` (sub-leading
muon + leading jet) needs at least 2 muons in the event, not 1, since index
1 is the second muon.

## Naming a histogram

Two functions, both real, imported and called (not reimplemented) except
where noted:

- `services/pipelines/im_pipeline.py::prepare_im_combination_name` (lines
  297-346): builds the per-event-batch signature name, e.g.
  `{filename}_FS_2e_0m_3j_0g_IM_e0j0` — the "IM" part is `letter+rank`
  for every object in the combination, joined in a fixed canonical order
  (Electrons, Muons, Jets, BJets, Photons, Taus).
- `services/pipelines/histograms_pipeline.py::_convert_to_bumpnet_name`
  (lines 419-453): turns `("2e_0m_3j_0g", "e0j0")` into the final BumpNet
  histogram name `mass_e0j0_cat_2ex_0mx_3jx_0gx` — the `"cat_"` block is
  simply the final-state string with each count re-suffixed `x` (so
  `"2e"` → `"2ex"`), still capped at 4 per type. **This function could not
  be live-imported in the cluster environment**: `histograms_pipeline.py`
  does `import ROOT` at module level, and this cluster account's
  `atlas-pipeline` conda env has no PyROOT installed at all — confirmed
  directly (`ModuleNotFoundError: No module named 'ROOT'` on a bare
  `import services.pipelines.histograms_pipeline`), an environment gap
  `studies/m0m1j0_cms/histograms.py`'s own docstring already discovered
  and documented in detail (2026-09-22). Rather than make a third
  independent copy, this study **imports the existing, already-cited,
  byte-identical copy directly from `studies.m0m1j0_cms.histograms`**
  (read-only import of another study's module, not a re-derivation) —
  that module's own docstring already traces it back to
  `histograms_pipeline.py:419-453` at the commit it was copied from. If
  the source ever changes, both copies would need re-diffing; this is the
  same known, flagged risk that module already carries, not a new one.

## Which post-processing applies to which combination

Source: `services/pipelines/post_processing_pipeline.py`.

- **`z_peak_cutoff` (115 GeV) applies to any combination whose IM part
  contains two or more letters of the *same* flavor from `{e, m}`
  (electron or muon), anywhere in the combination — not only to a pure
  2-body dilepton.** This is `_dilepton_flavor` (lines 34-45): it regex-
  extracts every `(letter, rank)` token from the IM part of the signature
  and returns `True` if either `'e'` or `'m'` appears **twice or more**.
  `_apply_z_peak_cut` (lines 48-70) then drops every mass value below the
  cutoff **only** for signatures where `_dilepton_flavor` is `True`; every
  other signature is returned untouched. This is exactly why `m0m1j0`
  (muon0 + muon1 + jet0 — two muon letters) starts at 115 GeV: the cut
  applies to the whole 3-body mass, not a separate dimuon sub-system. A
  combination like `e0m0j0` (one electron, one muon, one jet — no
  same-flavor pair) is **not** dilepton-flavored and receives **no**
  z-peak cut. This survey applies `_apply_z_peak_cut` **per pattern×
  category signature**, exactly as the shared code decides it, not as a
  blanket rule — verified per-signature in the merge step (Part 1).
- **`max_mass_cutoff` (10,000 GeV)** applies uniformly, no exception, to
  every signature (`post_processing_pipeline.py:236`/`283`).
- **Peak removal** (`_find_rightmost_highest_peak`, lines 324-352, followed
  by `filtered = arr[arr >= peak_mass]`) is unconditional for every
  signature — it has no config flag gating it at all (confirmed directly;
  see `studies/m0m1j0_cms/RECIPE.md` §5 for the earlier, corrected
  misunderstanding of `apply_peak_removal_at_histogram_level`, which
  controls a *different*, second, histogram-level step this survey does
  not use).
- **First-empty-bin split** (`_split_by_first_empty_bin`, lines 355-388)
  also runs unconditionally on every signature's peak-filtered array, and
  is what decides `_main` vs `_outliers` (only `_main` ever reaches a
  histogram, since `exclude_outliers: true`).
- **`min_events_per_fs` (100)** is enforced on the **raw, pre-z-peak**
  per-final-state population, summed **globally across the whole merged
  dataset** (`services/storage/sqlite_shards.py::prune_final_states_below_min_events`),
  **before** the z-peak/max-mass/peak-removal/split chain runs on the
  surviving signatures — not after. This survey reproduces that exact
  order (see Part 2).

## Grid anchoring: why raw masses, not a histogram, must be stored

Two different functions in `post_processing_pipeline.py` anchor their bins
completely differently, and this determines the storage design (Part 1.2):

- `_find_rightmost_highest_peak` (line 332-335) anchors its bins to
  **multiples of `bin_width` starting from 0**:
  `min_mass = floor(min(arr)/bin_width)*bin_width`,
  `bin_edges = arange(min_mass, max_mass+bin_width, bin_width)`. A fixed,
  absolute-position grid (e.g. 10 GeV bins at 0, 10, 20, ...) would
  reproduce this step's bin *counts* exactly.
- `_split_by_first_empty_bin` (line 361-367) does **not** use that grid at
  all. It recomputes its own: `min_mass = np.min(im_array)`,
  `max_mass = np.max(im_array)`, `bin_edges = np.linspace(min_mass,
  max_mass, nbins+1)` — a grid **anchored at this specific, already-
  peak-filtered array's own exact minimum and maximum**, not at 0 and not
  at any fixed multiple. The bin edges (and therefore which values are
  "main" vs "outliers") depend on the *exact floating-point* values of
  this one array. No histogram, however fine, stored on a fixed grid can
  reproduce this exactly, because the split point itself moves with the
  precise data.

**Conclusion (Part 1.2 decision): store raw per-(pattern×category) masses
as float32, not a histogram**, with a per-job size cap (Part 1). A fine
histogram plus min/max would exactly reproduce `_find_rightmost_highest_peak`
but not `_split_by_first_empty_bin` — raw values reproduce both exactly, by
construction, since they are fed into the same, real, imported functions
this survey calls.
