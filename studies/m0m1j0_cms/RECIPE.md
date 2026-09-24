# m0m1j0 CMS histogram: the ATLAS recipe, and how CMS follows it

Scope of this document: Step 0 of the "CMS m0m1j0 histogram" task. It records,
with file:line citations at commit `9e58e96` (branch `analysis/m0m1j0-cms`,
branched from `design/m0m1j0-bumpnet`), exactly what the group's ATLAS
`config.yaml` recipe does, then states the CMS m0m1j0 selection this study
uses and flags every place it deviates from the ATLAS recipe, with a reason.

This is a **documentation and decision record**, not code. Nothing here
changes any file outside `studies/m0m1j0_cms/`.

Everything below that is not marked UNVERIFIED is a direct reading of the
cited source at the cited commit — no numbers are guessed.

---

## 1. Object cuts (ATLAS, root `config.yaml`)

`config.yaml:114-120` (`kinematic_cuts`), values are **MeV** for `pt_min`
(confirmed: `25000.0` == 25 GeV, etc. — this file's own convention, not
documented in-file but consistent across every object):

| Object    | pt_min (GeV) | eta_max | extra |
|-----------|--------------|---------|-------|
| electrons | 25           | 2.47    | `rel_isolation_max: 0.06` |
| muons     | 25           | 2.5     | — |
| jets      | 30           | 2.5     | — |
| bjets     | 30           | 2.5     | — |
| photons   | 25           | 2.37    | (irrelevant here, see §3) |
| taus      | 20           | 2.5     | (irrelevant here, see §3) |

`enable_jet_tagging: true` (`config.yaml:91`) with
`jet_btagging_thresholds.btagDeepFlavB: 0.5` (`config.yaml:93`) — the CMS
DeepJet threshold used by the *ATLAS-recipe's own CMS b-jet test config*,
distinct from the value this study uses (§5).

## 2. `particle_counts {min, max}`: reject or ignore?

**Finding: full-event rejection, not truncation.** `particle_counts` is a
per-event **range filter on the count of objects that already passed the
kinematic cuts** — an event with a count outside `[min, max]` for ANY listed
object type is dropped entirely from the dataset. Extra objects are never
silently truncated/ignored while keeping the event.

Call site — `services/parsing/event_selection.py:74-103`
(`apply_parsing_event_selection`): kinematic cuts run first
(`physics_calcs.filter_events_by_kinematics`), narrowing each object
collection to only the objects that pass pt/eta/isolation; then
`particle_counts` is applied via
`physics_calcs.filter_events_by_particle_counts(events, mapped, is_exact_count=False, is_particle_counts_range=True)`.

Mechanism — `services/calculations/physics_calcs.py:129-196`
(`filter_events_by_particle_counts`), the range branch:
```python
if is_particle_counts_range:
    range_dict = value
    particle_mask = (obj_count >= range_dict['min']) & (obj_count <= range_dict['max'])
```
`particle_mask` is a per-event boolean; `combined_mask` ANDs it across all
object types; `filtered_events = events[combined_mask]` — events failing any
one object's range are removed completely, not partially trimmed.

**Consequence for photons/taus (`max: 0` at `config.yaml:111-112`):** since
kinematic cuts run first, this means **any event containing at least one
photon or tau that passes the photon/tau kinematic cuts (pt>25 GeV/η<2.37 for
photons, pt>20 GeV/η<2.5 for taus) is rejected from the entire ATLAS
analysis** — not "photons/taus are ignored in this particular combination."
A raw photon/tau that fails those kinematic cuts does not count (it never
reaches the `particle_counts` stage at all). This is a real, load-bearing
selection cut in the ATLAS recipe, not a bookkeeping no-op. See §3 for the
CMS deviation this forces.

## 3. Jets vs BJets, and what "j0" means

**b-tag split**, `services/parsing/file_parser.py:366-411`
(`_calculate_btagging_and_split`), runs at parse time on **raw (uncut)**
jets, only when `enable_jet_tagging` is true:
```python
if "Jet_btagDeepFlavB" in obj_events["DirectObjects"].fields:
    is_bjet = obj_events["DirectObjects"]["Jet_btagDeepFlavB"] > jet_btagging_thresholds["Jet_btagDeepFlavB"]
...
obj_events["BJets"] = obj_events["Jets"][is_bjet]
obj_events["Jets"] = obj_events["Jets"][~is_bjet]
```
"Jets" after this point is the **non-b-tagged remainder**; "BJets" is the
subset above threshold. Downstream kinematic cuts and particle_counts are
then applied separately to "Jets" and "BJets" as distinct object types
(`config.yaml:109-110`, `117-118`) — both get the same pt/eta cuts (30
GeV/2.5) in the ATLAS recipe.

**Field-name confusion, fixed**: commit `47f0a54` ("Fix jet/bjet confusion")
removed a substring-based field lookup (`if obj_name in field`) that could
match "Jets" inside "BJets" (since "Jets" is literally a substring of
"BJets"). Post-fix, `filter_events_by_particle_counts` and all downstream
code key off the **exact** field name (`services/calculations/physics_calcs.py:129-196`,
the `if obj not in events.fields` / `events[obj]` pattern). Confirms: in any
combination name, "j0" (from the "Jets" collection) unambiguously means the
**leading non-b-tagged jet**, never a b-jet.

## 4. How the final-state `cat_` string is built — exact counts, capped at 4

Authoritative source: `services/calculations/physics_calcs.py:61-83`
(`group_by_final_state`). For each event, after kinematic cuts, the **exact**
post-cut object counts are read off (`ak.num`) for six fixed object types in
this fixed order — electrons, muons, jets, photons, taus, bjets — and joined
into a string:
```python
all_events_fs = [f"{e}e_{m}m_{j}j_{g}g_{t}t_{b}b" for e, m, j, g, t, b in zip(e, m, j, g, t, b)]
```
Then `limit_particles_in_fs(fs, 4)` (`physics_calcs.py:86-98`) **caps the
displayed count per object type at 4** — an event with, say, 5 jets is
relabeled to display as "4j" and is bucketed into the *same* final-state
category as a genuine 4-jet event. This is a display-string cap that merges
categories at the tail, not an event-count field that is separately stored;
it is **not** a rejection (the event is still analyzed, just relabeled).

`_convert_to_bumpnet_name` (`services/pipelines/histograms_pipeline.py:419-453`)
turns `("2e_0m_3j_0g", "e0j0")` into `mass_e0j0_cat_2ex_0mx_3jx_0gx` (each
count gets an `x` suffix; the invariant-mass "combo" part, e.g. `e0j0` or
`m0m1j0`, passes through unchanged since it's already index-based). Exact
name for this study's target: `mass_m0m1j0_cat_<Ne>ex_<Nm>mx_<Nj>jx_<Ng>gx[_<Nt>tx][_<Nb>bx]`
for whatever final state actually has ≥2 muons and ≥1 non-b jet.

**`ROI_` prefix**: when histograms are written, the ROOT-internal `TH1F`
name gets a `ROI_` prefix and a `_width_<N>` suffix
(`histograms_pipeline.py:380,520,650`, e.g.
`hist_name = f"ROI_{hist_name_base}_width_{bin_width}"`), while the
*grouping key* / conceptual name used for filenames and BumpNet lookup stays
`mass_<combo>_cat_<fs>` (no `ROI_`). This ROOT-object-name vs. grouping-name
mismatch is a known, already-documented CMS pipeline quirk
(`docs/CMS_KNOWN_LIMITATIONS.md`) — noted here because it is directly
relevant to this study's ROOT output, not being fixed.

## 5. Post-processing / histogram steps that touch a 3-object mass like m0m1j0

Sequence per `services/pipelines/post_processing_pipeline.py:1-9` module
docstring: (1) Z-peak cut + 10 TeV hard cutoff, (2) bin, (3) find peak bin,
(4) remove data before the peak (opt-in, off by default), (5) split into
main/outliers by first empty bin after the peak.

- **`z_peak_cutoff` (115 GeV, `config.yaml:155`) — NOT limited to pure
  2-body dileptons.** `_dilepton_flavor()`
  (`post_processing_pipeline.py:34-45`) decides whether a signature's cut
  applies by checking whether the invariant-mass combo token contains **2 or
  more same-flavor lepton letters anywhere**, regardless of what else is in
  the combo:
  ```python
  def _dilepton_flavor(signature: str) -> bool:
      match = _IM_PART_PATTERN.search(signature)
      particles = _IM_PARTICLE_PATTERN.findall(match.group(1))
      letters = [letter for letter, _rank in particles]
      return any(letters.count(flavor) >= 2 for flavor in _DILEPTON_LETTERS)  # {'e','m'}
  ```
  `m0m1j0` contains two muon tokens (`m0`, `m1`) → `_dilepton_flavor` is
  **True** for it. So in the ATLAS recipe, **the 115 GeV floor is applied to
  the 3-body m0m1j0 mass itself**, not just to a standalone dimuon mass —
  any m0m1j0 event below 115 GeV would be dropped by this cut. This is
  non-obvious and directly answers the task's own question; it is **not** a
  dilepton-only cut in this codebase.
- **`max_mass_cutoff` (10,000 GeV, `config.yaml:156`)** applies uniformly
  "in every channel" per its own comment — no signature-based exception, so
  it applies to m0m1j0 exactly as to any other combination.
- **`exclude_outliers` (`config.yaml:171`, `true`) — signature-level, not
  event-level, and the config's own comment says it is unreliable under
  merging.** Mechanism: after the peak-detection/outlier split (step 5
  above), a whole per-final-state signature is suffixed `_outliers`; the
  histogram-building stage then drops **entire signatures** whose name ends
  in `_outliers` before building any histogram at all — confirmed in both
  the file-list path (`histograms_pipeline.py:158-163`) and the SQLite path
  (`histograms_pipeline.py:230-233`):
  ```python
  if exclude_outliers:
      signatures = [s for s in signatures if not s.endswith("_outliers")]
  ```
  The peak/first-empty-bin split that decides what counts as "outliers" is
  computed from whatever statistics are available at the point it runs. The
  config's own comment (`config.yaml:171`) states this "doesn't work
  properly during merging" — i.e. when many parallel batch/job outputs are
  combined, a signature's outlier/main split computed on one shard's
  statistics need not match what the *merged*, full-statistics distribution
  would show, and `exclude_outliers=true` can then discard a real high-mass
  tail rather than only genuine artifacts. See §6 for the CMS deviation.
- **`min_events_per_fs` (100, `config.yaml:142`)** — implemented in
  `services/storage/sqlite_shards.py:159-238`
  (`prune_final_states_below_min_events`): sums each final state's event
  population **globally across all given SQLite shards** (so, unlike
  `exclude_outliers`, this one is computed post-merge and is not subject to
  the same per-shard inconsistency), then **deletes every signature row**
  belonging to any final state whose total population is `< min_events`
  (`removed = [fs for fs, count in populations.items() if count < min_events]`).
  A final state with fewer than 100 total events across the whole dataset is
  dropped entirely from the histogram output.
- **`apply_peak_removal_at_histogram_level`** — `false` in
  `config.yaml:173`. **CORRECTION (2026-09-22, found by the group's
  supervisor, confirmed by the technical lead directly in
  `post_processing_pipeline.py` lines ~234-256 (SQLite path) and
  ~281-305 (single-array path)):** this flag does **NOT** control
  whether the peak-removal step in this module's own docstring (its
  steps 3-4, "find the rightmost highest bin" / "remove data before the
  peak") runs. That step is **unconditional** — it has no config flag at
  all, and always executes for every final-state mass array, via
  `_find_rightmost_highest_peak` (`post_processing_pipeline.py:324-352`)
  followed by `filtered = arr[arr >= peak_mass]`
  (`post_processing_pipeline.py:241`/`295`). Immediately after, **every**
  array is also split at its first empty bin
  (`_split_by_first_empty_bin`, `post_processing_pipeline.py:355-388`)
  into `..._main` / `..._outliers`, and — because
  `histogram_creation_task_config.exclude_outliers: true`
  (`config.yaml:171`) — **only `_main` ever reaches a histogram**
  (`histograms_pipeline.py:158-163`, `230-233`: any signature ending
  `_outliers` is dropped entirely before histogram-building starts).
  `apply_peak_removal_at_histogram_level` is a **second, separate,
  additional** peak-removal step that runs (only if `true`) on the
  already-built, FIXED-GRID (0-10,000 GeV) merged histogram itself
  (`_apply_peak_removal_to_histogram`, `histograms_pipeline.py:625-643`:
  zeroes every bin strictly before the rightmost highest bin, using
  `ROOT.TH1F.SetBinContent`/`SetBinError` directly on the final
  histogram) — it is `false` in this recipe, so that *second* step does
  not run, but the *first* (array-level, unconditional) one always does.
  **This study's Step 1/2 outputs (`studies/m0m1j0_cms/pilot/`,
  `studies/m0m1j0_cms/full/`) never applied the array-level peak-removal
  or the `_main`/`_outliers` split/`exclude_outliers` filtering — this
  was a real, consequential gap, not a deliberate documented deviation,
  and is corrected in `studies/m0m1j0_cms/v2/` (see that directory's
  `REPORT.md`), which imports and calls the pipeline's own
  `_apply_z_peak_cut`, `_find_rightmost_highest_peak`, and
  `_split_by_first_empty_bin` directly rather than re-deriving them.**
  The error in this document originated from an earlier turn's own
  misreading, not from any instruction given to this study.
- **Order relative to `min_events_per_fs` pruning**: in the SQLite path,
  `prune_final_states_below_min_events` is called **first**
  (`post_processing_pipeline.py:162-164`), against the **raw,
  pre-z_peak/pre-max_mass/pre-peak-removal** per-final-state population
  (the mass-array lengths as originally written by the mass-calculation
  stage) — deleting entire final-state rows from the SQLite shards
  in-place, BEFORE the per-signature `_apply_z_peak_cut` /
  `_find_rightmost_highest_peak` / `_split_by_first_empty_bin` chain
  (`post_processing_pipeline.py:187-256`) ever runs on the (now-pruned)
  remaining signatures. So the real order is: **(1) prune on raw counts,
  (2) z_peak_cutoff + max_mass_cutoff, (3) peak removal, (4) first-empty-
  bin split, (5) histogram from `_main` only** — not "z_peak/max_mass
  then prune on the post-cutoff count", which is what Step 1/2's own
  `min_events_per_fs` implementation did (RECIPE.md section 6.5). `v2`
  corrects this ordering too.
- **`trim_empty_tail`** (`histograms_pipeline.py:26-41`) — confirmed
  display-range-only: it finds the last bin with content `> 0` and calls
  `hist.GetXaxis().SetRangeUser(...)`; it never zeroes or removes stored bin
  content. Safe to mirror with no caveats.

## 6. CMS selection for this study, and every deviation from the ATLAS recipe

The CMS object cuts below were **given directly by the task**, not derived
from `config.yaml` (CMS branch names/values differ physically from ATLAS's
ATLAS-detector-specific quantities); where ATLAS's recipe informs a
*policy* choice (rather than a cut value), that is called out explicitly.

| Object | CMS cut used | Source |
|---|---|---|
| Muons | `pt > 25 GeV`, `\|eta\| < 2.4`, `Muon_mediumId`, `Muon_pfRelIso04_all < 0.15` | given |
| Electrons (count-only) | `pt > 25 GeV`, `\|eta\| < 2.5`, `Electron_cutBased >= 3` | given |
| Jets | `pt > 30 GeV`, `\|eta\| < 2.5`, tight ID `(Jet_jetId & 2) != 0`, ΔR≥0.4 from any selected muon/electron | given; jetId bit meaning per `DESIGN.md` §D1 |
| B-jets | `Jet_btagDeepFlavB > 0.2598` (DeepJet Medium WP, UL2016 postVFP) | given; same value at `config.cms_bjet_test.yaml:78` |
| Trigger | `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ` OR `HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ` | given; both confirmed live and healthy in `DESIGN.md:244-257` |
| Data quality | golden JSON via `services.parsing.validated_runs` | given; reused read-only |

### Deviations from the ATLAS recipe, and why

1. **Muon pt threshold is CMS-native 25 GeV, not converted from ATLAS's
   25,000 MeV value** — these are numerically the same (25 GeV either way);
   no real deviation, noted only because the task called out the MeV-vs-GeV
   framing explicitly.
2. **Photons/taus: not rejected, not counted — deviates from ATLAS's
   `max:0` full-event rejection (§2).** ATLAS's `particle_counts` semantics
   mean any ATLAS event containing a kinematically-passing photon or tau is
   dropped from the whole analysis. Blindly copying that for CMS would
   silently throw away m0m1j0 candidate events for a reason unrelated to the
   m0m1j0 final state itself (CMS photon/tau content was never vetted for
   this study, and NanoAOD photon/tau IDs are a separate, non-trivial
   selection this task explicitly does not include). **Decision: for this
   pilot, photons and taus are not read/selected/counted at all** — they
   neither reject nor appear in the final-state category string. This is
   the deviation the task instructed me to flag rather than copy blindly.
3. **`z_peak_cutoff` (115 GeV) IS mirrored, faithfully, including its
   effect on the m0m1j0 mass itself (§5).** This is simply what the shared
   post-processing code already does for any final state with two
   same-flavor leptons — not an ATLAS-only quirk to special-case. Since
   m0m1j0 contains two muons, this study's own m0m1j0 histograms apply the
   same 115 GeV floor to the reconstructed 3-body mass. Flagged prominently
   here because it is non-obvious and materially shapes the low-mass end of
   the m0m1j0 spectrum.
4. **`exclude_outliers` (signature-dropping) is NOT mirrored.** The ATLAS
   config's own comment documents it as broken under merging (§5), and the
   task's own output spec asks this study to *keep* a small per-event list
   of m0m1j0 > 1 TeV events for inspection, i.e. the opposite of discarding
   them. This pilot's histograms include the full mass range up to the
   `max_mass_cutoff` (10 TeV, §6.5 mirrored); nothing above that is
   silently dropped.
5. **`max_mass_cutoff` (10 TeV) and `min_events_per_fs` (100) ARE
   mirrored as-is** — both are simple, well-defined, merge-safe global
   cuts with no CMS-specific reason to differ. `min_events_per_fs` is
   applied when categorizing per-exact-final-state histograms (§7); it does
   not affect the single inclusive histogram, which is deliberately
   non-standard already (see next point). **Applied at MERGE time only,
   not per job**: `services/storage/sqlite_shards.py`'s
   `prune_final_states_below_min_events` (§5 above) sums each final
   state's population GLOBALLY across every shard before comparing to the
   threshold — so this study's own per-job driver
   (`cluster/run_m0m1j0_on_file.py`) calls
   `histograms.build_m0m1j0_histograms(..., apply_min_events_prune=False)`
   and writes every category it sees, however small; `cluster/merge_pilot.py`
   applies the real >=100 check once, after summing every job's
   histograms by category name. Pruning per-job-file would have
   compared each of the 4 pilot jobs' own (much smaller) single-file
   counts against the threshold, which is not the population the ATLAS
   recipe itself checks.
6. **No multi-stage pipeline architecture is replicated.** The ATLAS
   recipe is a multi-stage system (parse → per-file invariant-mass arrays →
   post-processing → SQLite shards → histogram merge). Reproducing that
   full architecture for a single pilot study is out of proportion to the
   task's own output spec (one script per job producing ROOT+JSON directly,
   then a separate merge step) and is not requested. This study instead
   applies the **same numerical recipe** (cuts, mass calculation, z-peak
   cutoff, max-mass cutoff, fixed binning, BumpNet naming) in a single pass
   per file. If the group later wants full generic-pipeline reuse, that is
   a separate, larger task.
7. **BumpNet-category output is limited to real physics categories that
   arise in the data**, plus one explicit inclusive histogram named
   `mass_m0m1j0_inclusive_ge2m_ge1j` (deliberately non-BumpNet-shaped, so it
   cannot be confused with a real category name). No Z-collapsing, no
   BumpNet-paper categories, no variable binning — all explicitly out of
   scope for this task (superseded from `DESIGN.md`).
8. **No jet-tagging thresholds from `config.yaml`/`jet_btagging_thresholds.btagDeepFlavB: 0.5`
   are used.** That value is the ATLAS-recipe's own generic CMS b-jet test
   threshold; this study uses the task-specified DeepJet Medium WP (0.2598)
   instead, since that is the physically-correct 2016 UL working point
   given in the task and already used at `config.cms_bjet_test.yaml:78`.

### Binning and naming — mirrored exactly

- Fixed grid: `FIXED_MASS_MIN_GEV = 0.0`, `FIXED_MASS_MAX_GEV = 10000.0`
  (`services/pipelines/histograms_pipeline.py:22-23`), 10 GeV bins
  (`config.yaml:166`) — imported directly into this study's script, not
  hardcoded.
- `_fill_mass` boundary handling (`histograms_pipeline.py:67-72`, nudges an
  exact `10000.0` GeV value down by one ULP so it lands in the last real bin
  rather than overflow) — mirrored.
- BumpNet naming (§4) — mirrored exactly, using the real
  `_convert_to_bumpnet_name` function (imported, not reimplemented) and the
  real `group_by_final_state` per-event final-state string builder.
- `trim_empty_tail` (§5, display-range only) — mirrored on final merged
  histograms.

## 7. Outputs this study produces (per job, and after merge)

- One TH1F per **exact** final state with ≥2 muons and ≥1 non-b jet, named
  via the real `_convert_to_bumpnet_name`, e.g.
  `mass_m0m1j0_cat_0ex_2mx_1jx_0gx`.
- One inclusive TH1F across all such final states combined, named
  `mass_m0m1j0_inclusive_ge2m_ge1j` (never confusable with a BumpNet name).
- A ROOT file (TH1F histograms, same binning/naming convention as the
  shared pipeline would produce) and a JSON file with: bin contents per
  histogram, per-category event counts, and a cutflow (events after: read,
  golden JSON, trigger, ≥2 muons after cuts, ≥1 non-b jet after cuts and
  lepton-cleaning, final m0m1j0 built).
- A small JSON list of `(run, luminosityBlock, event, m0m1j0, category)` for
  every event with `m0m1j0 > 1000` GeV, for manual outlier inspection (kept,
  never discarded — see deviation 4 above).

## 7a. Environment finding: no PyROOT on the cluster (2026-09-22)

Running this pilot's own preflight discovered that the Weizmann cluster's
`atlas-pipeline` conda env
(`/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline`) has **no
PyROOT installed at all**, and there is no system `root`/`root-config` on
this account either. This means `services/pipelines/histograms_pipeline.py`
cannot even be **imported** there (`import ROOT` at module level fails
with `ModuleNotFoundError`), confirmed directly:
```
$ python -c "import services.pipelines.histograms_pipeline"
ModuleNotFoundError: No module named 'ROOT'
```
So the task's own instruction to literally `import` `FIXED_MASS_MIN_GEV`/
`MAX_GEV`, `_fill_mass`, `trim_empty_tail`, and `_convert_to_bumpnet_name`
from that module cannot be carried out as a real import in this
environment. **This study does not install PyROOT into the shared env**
(that env is used by other studies, e.g. `studies/hgg_cms`, and modifying
shared infrastructure is outside this task's scope) — instead:
- The two constants and `_convert_to_bumpnet_name` are copied verbatim
  into `studies/m0m1j0_cms/histograms.py`, cited to their exact source
  lines, with an explicit warning that they will silently drift if the
  source ever changes.
- `limit_particles_in_fs` (`services/calculations/physics_calcs.py`) has
  no ROOT/fcntl dependency and is still genuinely imported.
- Histograms are built as plain `(values, edges)` numpy pairs and written
  with `uproot.recreate(...)` instead of PyROOT's `TFile`/`TH1F` —
  confirmed this produces a real ROOT `TH1D` file, readable by actual
  ROOT/PyROOT elsewhere, just not written through PyROOT on this end.
- **CORRECTION (2026-09-24): `trim_empty_tail`'s axis-range trim IS now
  reproduced — the statement below that it "cannot" be, because "there is
  no PyROOT axis object to call `SetRangeUser` on via uproot's writer",
  was true of the mechanism actually used at the time this was written,
  but wrong about the conclusion: it does not follow that the DISPLAY
  RANGE ITSELF cannot be reproduced without PyROOT, only that it cannot be
  reproduced by calling `SetRangeUser` (a PyROOT method) on a PyROOT
  object neither of which exists here. `studies/m0m1j0_cms/histograms.py`'s
  `to_writable_th1f` now sets the same fFirst/fLast TAxis members and the
  TObject `kAxisRange` status bit that a real `SetRangeUser` call would
  produce, worked out directly from ROOT's own source
  (`TAxis.h`/`TAxis.cxx`, quoted in full in that module) rather than by
  calling the method itself — see §7b below for the complete story,
  including why setting the bit needed a workaround uproot's public
  writing API does not otherwise expose. This is no longer a known gap;
  §10 records it as closed.

For historical accuracy the original (now-superseded) reasoning is kept
below rather than deleted:

- ~~`trim_empty_tail`'s cosmetic axis-range trim (display-only, never
  touches stored bin content) is not reproduced in the written ROOT file
  — there is no PyROOT axis object to call `SetRangeUser` on via uproot's
  writer. The same "last non-empty bin" information is available from
  each job's metadata JSON and is applied directly in the pilot's own
  sanity-check PNGs.~~ (superseded, see the correction immediately above)

This section is otherwise still accurate: the rest of the environment gap
(no PyROOT, no live import of `histograms_pipeline.py` itself, the
verbatim-copy workaround for the two constants and
`_convert_to_bumpnet_name`) remains unchanged and is flagged here as a
genuine, non-obvious environment gap worth the group's attention on its
own merits (unclear whether the shared pipeline's own
`histogram_creation_task` has ever been run end-to-end on
this cluster account), separate from anything specific to m0m1j0.

## 7b. Display-range parity closed (2026-09-24)

The technical lead found the one remaining difference from the shared
pipeline's histogram output: `trim_empty_tail`
(`services/pipelines/histograms_pipeline.py:26-41`) sets the written
histogram's x-axis DISPLAY range (never its bin content) to the filled
part; this study's uproot-written files left it unset (`fXaxis.fFirst=0`,
`fLast=0` — confirmed directly in `v2/data/m0m1j0_data_postprocessed.root`
and `v3_variants/data_V0_baseline.root` before this fix).

**What `trim_empty_tail` actually does, read precisely, not paraphrased**
(exact source quoted in full in `histograms.py`'s own module-level
comment above `_last_nonempty_root_bin`): it scans from the last bin down
to bin 1 for the last one with content `> 0`, then calls
`GetXaxis().SetRangeUser(GetXmin(), <that bin's own upper edge>)` — the
LOWER bound passed is the axis's own original minimum, not the first
filled bin. **It trims only the trailing empty region; it never crops a
leading one.** That matters for this study specifically: the peak-removal
step already deletes everything below each category's own peak from the
underlying mass array, so bins between 0 GeV and the peak are
empty-but-present on the shared fixed 0-10000 GeV grid — a real pipeline
histogram in the same situation would leave that leading empty region
un-cropped too, and so does this fix. If no bin has content at all,
`trim_empty_tail` is a complete no-op (the axis is left exactly as it
was — for a never-ranged histogram, ROOT's own default: `fFirst=0`,
`fLast=0`, the range bit unset).

**What that means on disk**, worked out from ROOT's own source
(root.cern, `TAxis.h:65` for `kAxisRange = BIT(11)`; `TAxis.cxx` for
`SetRange`/`SetRangeUser`/`GetFirst`/`GetLast`, all quoted verbatim in
`histograms.py`): the call above always resolves to `fFirst=1`,
`fLast=<last filled bin>`, with the `kAxisRange` status bit SET.
Crucially, `TAxis::GetFirst()`/`GetLast()` — what any real reader (ROOT's
own `Draw()`, a `TBrowser`, etc.) actually calls — **ignore `fFirst`/
`fLast` entirely unless that bit is set**, returning the full range
regardless. Writing `fFirst`/`fLast` alone, without the bit, would
therefore have been a complete no-op for any real reader, not a partial
fix.

**Implementation.** `fFirst`/`fLast` are supported directly by uproot's
own `to_TAxis(...)` call. The `kAxisRange` bit is not exposed by uproot's
writing API at all — confirmed by direct experiment that the bit is NOT
sourced from the axis model's own `_members["@fBits"]` at write time;
every writable model's internal `_serialize(...)` receives the eventual
on-disk flags word as an explicit argument threaded down from the top of
the call chain (with fixed bits ORed in along the way by various classes),
and no parameter anywhere lets a caller add to that word for one specific
sub-object. The fix wraps the one axis instance's own bound `_serialize`
method (per-object, per-write-call; no other histogram or file is
affected) to OR in the bit before delegating to the real implementation.

**Verification.** Round-tripped by writing a real file and reading it back
with uproot: `fFirst`, `fLast`, and the raw `@fBits` value (confirmed
`kIsOnHeap | kNotDeleted | kAxisRange`) all match what a real
`SetRangeUser` call would produce, for both a histogram with content and
an all-empty one (which correctly gets the untouched default, not a
cropped-to-nothing range). **UNVERIFIED against an actual PyROOT-produced
file**: checked directly (2026-09-24), no PyROOT install exists in any
conda env on this cluster account (only `atlas-pipeline` exists, and
`import ROOT` fails there exactly as before), there is no system
`root`/`root-config` binary, and no genuine PyROOT-written TH1 histogram
exists anywhere in this repository or in any output directory on this
account — every "histograms" output directory belonging to other studies
on this account was checked directly and found empty. The verification
above is therefore against ROOT's own quoted source and an uproot
round-trip, not a byte-for-byte comparison against a real pipeline output.

After this fix, the existing merge steps were re-run from the per-job
outputs already on disk (no analysis job was re-run), and every histogram
in every regenerated file was checked bin-for-bin against the previously
committed file, and every category's post-processing counts against the
previous JSON summaries: 316 histograms and 763 categories compared, zero
differences (`cluster/check_display_range_fix_preserves_content.py`,
committed alongside its own passing output). Only the display-range
metadata changed.

## 8. Part B: ttbar MC sample and MC-specific handling

**Sample search (2026-09-22)**: the CERN Open Data portal's own search
API (`https://opendata.cern.ch/api/records?q=...`) does not tokenize
literal CMS dataset names containing consecutive digits/letters like
"TTTo2L2Nu" as a plain keyword query (`q=TTTo2L2Nu` returns 0 hits) — a
trailing-wildcard query (`q=TTTo2L2Nu*`) does work and returned 59 hits,
among which is the exact nominal (no systematic-variation suffix)
sample:

- **Record ID: 67801**
- **Title**: `/TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM`
- **`run_period`**: `["Run2016G", "Run2016H"]` — confirms this is the
  post-VFP ("UL16", not "UL16APV") campaign, matching this study's data
  records exactly, as required.
- **`distribution.number_events`**: 43,546,000
- **`distribution.number_files`**: 49 — confirmed to match
  `fetch_file_list(67801)`'s own returned length exactly.
- **Cross section**: **UNVERIFIED — not published anywhere in this
  record's own metadata.** Checked directly: no key or substring
  matching "cross" appears anywhere in the full metadata JSON returned by
  `https://opendata.cern.ch/api/records/67801` (only `distribution`,
  `methodology`, `usage`, `abstract`, etc. are present, none of which
  carry a cross-section value). This does not block anything in this
  study — no luminosity/cross-section-based normalization is performed
  (task's own explicit instruction), but the number itself is not
  invented or recalled from outside knowledge; it is reported as
  UNVERIFIED per the evidence rule.

The task's own fallback (record 67993, `TTToSemiLeptonic`) was **not**
needed — the dilepton sample exists and was found.

### MC-specific deviations from the data recipe (all documented, none change the object selection)

1. **No golden-JSON (validated-runs) filter at all.**
   `services.parsing.validated_runs.apply_validated_runs_filter` itself
   would refuse to run on simulation (it detects simulation via a
   `genWeight` field or `run==1` and raises rather than silently
   discarding the whole sample, `services/parsing/validated_runs.py:217-227`)
   — this study's MC driver (`cluster/run_m0m1j0_on_mc_file.py`) simply
   never calls it, rather than calling and catching that refusal.
2. **Same trigger requirement, same fail-loudly-if-missing check** — MC
   NanoAOD carries trigger-emulation HLT branches under the same names as
   data; confirmed present in a real file at pilot time (see PILOT
   sanity report, `studies/m0m1j0_cms/v2/REPORT.md`).
3. **`genWeight` is read as an ordinary per-event scalar field** on the
   full `events` record — it survives `apply_trigger`'s and the final
   selection mask's slicing automatically (both are plain
   `events[boolean_mask]` operations, which preserve every field), so no
   special per-object threading (like the muon diagnostic branches
   needed) was required.
4. **Primary histograms are UNWEIGHTED** event counts, for direct
   format-comparability with the data histogram. A **separate**,
   clearly-named file holds genWeight-weighted histograms (fill weight =
   the actual `genWeight` value read, not just its sign). Per-job
   `sum_genWeight` (over ALL read events, the standard MC-normalization
   population — not just selected events) and the negative-weight
   fraction are recorded in each job's `job_metadata.json`.
5. **Not scaled to luminosity** — the DoubleMuon dataset's own
   luminosity has not been independently verified in this project, so no
   number-of-events-per-fb⁻¹ scaling is applied anywhere.
6. **Known limitations, not applied (recorded, not fixed)**: no pileup
   reweighting, no muon-ID/isolation or b-tag scale factors, no trigger
   efficiency correction. Every ttbar number in this study is a raw
   (or genWeight-weighted) simulated event count, nothing more.

## 9. Still UNVERIFIED / left as-is per scope

- `Electron_cutBased >= 3` meaning ("medium, includes isolation") is taken
  from the task as given; this study will quote the branch's own NanoAOD
  title string from a real opened file at run time and record it verbatim
  in the pilot output, rather than assuming it sight-unseen.
- The `ROI_`/grouping-name mismatch (§4) and the `cat_` field-order
  convention are pre-existing, already-documented pipeline quirks
  (`docs/CMS_KNOWN_LIMITATIONS.md`) — noted for awareness, not touched.
- Whether the full 57-file run's final-state population will clear
  `min_events_per_fs = 100` for every category is not knowable from a
  2-file-per-record pilot; the pilot report will state observed counts
  plainly rather than extrapolate.

## 10. Final status (2026-09-24): remaining differences from the shared pipeline

§7b closes the x-axis display-range gap, which was the last remaining
difference in the histogram OUTPUT itself. What remains — accurately, as
of this writing, not as originally scoped — is three items, none of them
in the histogram output:

1. **No cross-dataset de-duplication.** This study reads a single primary
   dataset (DoubleMuon, records 30522/30555 — two run eras of the *same*
   dataset, not two different datasets) — confirmed directly from each
   record's own portal metadata. There is no overlapping second dataset
   here for an event to be double-counted between, unlike the
   SingleElectron+SingleMuon combination the shared pipeline's own
   de-duplication mechanism (`services/parsing/event_deduplication.py`,
   see `docs/UPSTREAM_DIVERGENCE_MAP.md`) exists to handle. Not a gap in
   this study; not applicable to it.

2. **Per-object masses come from each event's own NanoAOD `mass` branch
   (via `vector.zip`), not the shared pipeline's per-object-type
   `KNOWN_MASSES` constants** (`services/calculations/consts.py`, not
   imported here — see `selection.py`'s own module docstring, unchanged
   by this task). Verified directly (2026-09-24) against 500,000 real
   muons from one real DoubleMuon file (record 30522): `Muon_mass` is
   stored as float32 on disk but takes only a small number of distinct
   values, consistent with float16 quantization of the true PDG muon mass
   (`0.1056583755` GeV) somewhere upstream in NanoAOD production —
   `float16(0.1056583755) == 0.10565185546875` matches the file's own
   values exactly. The two dominant quantized values in the sample were
   `0.10565185546875` (153,322 muons, ~14.5%, differing from the exact PDG
   value by `6.5×10⁻⁶` GeV — genuinely below 1e-5) and, MORE commonly,
   `0.105712890625` (905,383 muons, ~85.4%, differing by `5.4×10⁻⁵` GeV —
   **not** below 1e-5). The population mean over all 500,000 muons
   differed from the exact PDG value by `4.6×10⁻⁵` GeV. **This corrects an
   expectation stated when this check was requested (that the difference
   would be below 1e-5 for muons) — the actual, measured figure is closer
   to 1e-5 to 5×10⁻⁵ GeV depending on which quantization bin a given muon
   falls in, not uniformly below 1e-5.** A handful of true outliers exist
   in the same sample (5 muons out of 1,059,710 total array entries,
   including one anomalous `0.125` GeV value clearly unrelated to the
   muon mass) — negligible in count, not representative. Every one of
   these differences — 1e-5 to 5×10⁻⁵ GeV — is physically negligible for
   this study, whose bins are 10 GeV wide and whose mass window starts at
   115 GeV; it is recorded here for completeness and accuracy, not flagged
   as a problem. (Explicitly out of scope, per this task's own
   instruction, and untouched: this is a different question from the
   fork's own separately-flagged, separately-rounded `KNOWN_MASSES["Muons"]
   = 0.105` constant, which this study does not use at all and which is
   not "fixed" here or anywhere else per standing instruction.)

3. **No multi-stage pipeline architecture is replicated** (§6, deviation
   6, unchanged) — this study applies the same numerical recipe in a
   single pass per file rather than reproducing the shared pipeline's
   parse → mass-array → post-processing → SQLite-shard → histogram-merge
   architecture. Still considered out of proportion to this study's own
   scope, as originally stated.

No other known difference from the shared pipeline's own histogram/
selection/post-processing behaviour remains, to the best of this
document's own verification.
