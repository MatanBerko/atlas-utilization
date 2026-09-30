# CMS MC weights: design for BumpNet delivery

Branch `design/cms-mc-weights`, off `origin/investigate/cms-mc-normalisation`
at `1d4ee2a`. Design only — no pipeline code, no config changes, no
histograms produced, no cluster jobs run. Every number below traces to a
file opened in this repo (cited `file:line`), a URL actually fetched
(quoted), or the existing `normalisation_table.csv`/`normalisation_table_v2.csv`.
Anything not verified is marked **UNVERIFIED**.

---

## 1. Production path

**Finding: the delivered DoubleMuon BumpNet ROOT files did NOT go through
`services/pipelines/histograms_pipeline.py` at all.** That module does
`import ROOT` at module level (`services/pipelines/histograms_pipeline.py:16`),
and this project's own cluster conda env has no PyROOT installed — confirmed
directly and documented in the actual production code's own docstring:

> "the cluster's own `atlas-pipeline` conda env... has NO PyROOT installed,
> and there is no system `root`/`root-config` on this account either.
> `services/pipelines/histograms_pipeline.py` does `import ROOT` at MODULE
> level, so it cannot even be IMPORTED in that env... Confirmed directly:
> `$ python -c "import services.pipelines.histograms_pipeline"` →
> `ModuleNotFoundError: No module named 'ROOT'`"
> — `studies/m0m1j0_cms/histograms.py:4-24`

So this study built its own parallel, PyROOT-free implementation, and
**that** implementation is what actually produced every delivered file. The
real chain, traced through the actual driver scripts and confirmed against
`origin/deliver/doublemuon-bumpnet`'s own git history:

| Stage | Script : function | genWeight carried for MC? |
|---|---|---|
| **1. Parse** | `studies/m0m1j0_cms/cluster/run_m0m1j0_on_file.py:265` (`read_events(file_url)`) | **No.** This driver reads DoubleMuon (real data) files only; no `genWeight` branch requested anywhere in this file (confirmed: no match for `genWeight`/`read_event_weights` in the whole file). The shared parser's own MC-weight-reading mechanism (`services/parsing/mc_weights.py`, §A of `INVESTIGATION.md`) is fully built and correct, but this driver never turns it on. |
| **2. Selection + IM calculation** | `run_m0m1j0_on_file.py:284` (`selection.select_event_selection_cutflow(events_golden, ...)` → `result["mass"]`, `result["obj_record"]`) | **No.** No weight field passed through or referenced anywhere in this stage for this driver. |
| **3. Per-job storage** | `run_m0m1j0_on_file.py:327-328` (`build_mass_by_category_npz(mass_by_category_path, result)` → `mass_by_category.npz`) | **No.** Only raw mass values, grouped by category, are written. `genWeight` is absent from this npz's schema as currently written. |
| **4. Merge (real post-processing + histogram FILL)** | `studies/m0m1j0_cms/cluster/merge_full_v2.py:134` (`load_all_mass_by_category`) → `:193` (`raw_count_passes_min_events_prune`, RAW count) → `:198` (`apply_full_postprocessing`, z_peak/max_mass/peak-removal/split) → `:211-212` (`make_fixed_grid_histogram(result["main_array"])`, `studies/m0m1j0_cms/histograms.py:143-161`) | **No — and this is the actual fill step.** `make_fixed_grid_histogram`'s inner loop is `np.add.at(counts, bin_idx, 1.0)` (`histograms.py:160`) — every event contributes a hardcoded weight of exactly `1.0`. There is no weight parameter on this function at all today. |
| **5. Write** | `merge_full_v2.py:238-241` (`uproot.recreate(...)`, `to_writable_th1f(values, edges, key)`, `studies/m0m1j0_cms/histograms.py:329-378`) | N/A — writes whatever `values` array it's given; **also currently writes `fSumw2=None`** (`histograms.py:376`) — no per-bin sum-of-weights-squared array exists in the delivered files today, for anyone. |
| **6. Delivery/cropping** | `origin/deliver/doublemuon-bumpnet:studies/cms_coverage/deliver/crop_bumpnet_root.py` — pure re-windowing of the already-written ROOT file (`uproot.open` → slice to first/last non-zero bin → `uproot.recreate`), no recomputation | N/A — read-only re-window of stage 5's output. |

**A second, older, MC-only code path exists but is a dead end for this
purpose**: `studies/m0m1j0_cms/cluster/run_m0m1j0_on_mc_file.py` +
`merge_ttbar.py` already read `genWeight` (`run_m0m1j0_on_mc_file.py:130`,
`ak.to_numpy(result["sel_events"]["genWeight"])`) and already fill a
genWeight-weighted histogram via plain `np.histogram(mass, weights=genWeight)`
(confirmed in the prior investigation, `INVESTIGATION.md` §A). But this path
is a one-off, ttbar-only study: it never calls `build_m0m1j0_histograms` or
`make_fixed_grid_histogram`, produces a single flat signal region (not
BumpNet per-category histograms), and was never used to build any file on
`deliver/doublemuon-bumpnet`. It is useful evidence that genWeight-through-
the-same-selection-code already works end to end once (`main_mask`-style
companion-array slicing, `studies/m0m1j0_cms/postprocessing.py:75-146`,
already does exactly this for the *data* post-processing chain), but the
actual delivery format comes from the newer path in the table above.

**The single cleanest place for the normalised weight to enter**:
`make_fixed_grid_histogram()`, `studies/m0m1j0_cms/histograms.py:143-161`.
Concretely:
- Change its signature from `make_fixed_grid_histogram(values)` to
  `make_fixed_grid_histogram(values, weights=None)`, defaulting to
  `np.ones_like(values)` when `weights is None` (byte-identical output for
  every existing data call site — no behavior change for anyone not passing
  weights).
- Change line 160 from `np.add.at(counts, bin_idx, 1.0)` to
  `np.add.at(counts, bin_idx, weights[in_range])` (`in_range` already exists
  at line 157, the same boolean mask that selects which values fall inside
  the fixed grid — weights must be sliced by the same mask, index-for-index).
- Two per-event-weight companion arrays then need to reach this call: the
  per-event `genWeight` (aligned with `mass`, sliced through selection/z_peak/
  max_mass/peak-removal/split exactly the way `postprocessing.py`'s
  `main_mask` mechanism already demonstrates for the ttbar study), and the
  per-file normalization factor (§2) multiplied in once per sample, not
  per event (cheaper, and avoids float precision loss from multiplying a
  tiny per-file factor into millions of near-unity `genWeight` values one at
  a time — multiply the *sum*, not each term).
- This also means stage 3 (`build_mass_by_category_npz`) must additionally
  write a `genWeight` array alongside `mass_by_category`, and stage 4
  (`merge_full_v2.py`) must thread it through `apply_full_postprocessing`'s
  existing `main_mask` output (already returned, already exactly this
  purpose — see `postprocessing.py:86-90`) into `make_fixed_grid_histogram`.
- Stage 5 (`to_writable_th1f`) needs one addition: accept an optional
  per-bin sum-of-weights-squared array and pass it as `fSumw2=...` instead
  of the current hardcoded `None` (`histograms.py:376`) — see §8.

> **Plain-language summary:** The files already delivered to Maryna were
> built by a special, hand-written version of the histogram code (because
> the "official" shared code can't even run on this cluster — it needs a
> program, PyROOT, that isn't installed there). That hand-written version
> currently counts every event equally (weight exactly 1), by a single
> hardcoded number buried in one small function. There's exactly one place
> to change that number into "count this event by its proper weight instead
> of by 1" — and doing so is a small, well-contained change, not a rewrite.

---

## 2. Weight formula and units

Per-event weight:

```
weight = genWeight × σ_eff[pb] × 1000 × L[fb⁻¹] / Σ genWeight
```

This is architecturally identical to PR #23's own formula
(`services/calculations/mc_weights.py`, fetched read-only via
`git fetch .../pull/23/head`, unchanged since the last investigation —
confirmed: same head `9be20a9`, same 22-file diff stat against
`origin/master`):

```
w = (sigma * k * eps_filter * L) / N_gen     [compute_normalization]
per-event weight = w * mc_event_weight        [compute_event_weight]
```

with `N_gen` = `sumOfWeights` (PR #23's own comment: *"In practice `N_gen`
is the sum of per-event generator weights (`sumOfWeights`), not the raw
event count"*). Field-by-field mapping onto PR #23's `MCDatasetMetadata`
(`domain/metadata.py`, fetched read-only, unchanged):

| `MCDatasetMetadata` field | ATLAS meaning (PR #23) | CMS design (this document) |
|---|---|---|
| `dataset_number: int` | ATLAS DSID (6-digit) | **CMS record ID** (e.g. `67801`) — not a DSID; see PR#23 gap analysis, `INVESTIGATION.md` §E point 1, for why a 6-digit-DSID regex would never match a CMS record ID or filename |
| `cross_section_pb: float` | atlasopenmagic `get_metadata()["cross_section_pb"]` | **σ_eff** from `normalisation_table_v2.csv` — the portal `total_value` (already final w.r.t. matching/filter, R1) × decay branching ratio where the decay happens outside the ME (R2), × k-factor. i.e. the BR is *folded into* this field, not a separate multiplier — see below. |
| `sum_of_weights: float` | a single ATLAS-metadata-service number, dataset-wide, independent of which files this run touched | **Σ genWeight over exactly the files this run processed** — fork master's own `aggregate_sumw_for_processed_files()` (`services/parsing/mc_weights.py:173-226`), *unchanged*, already implements the correct rule and already raises loudly (not silently) if any processed file's `Runs` tree can't be read (lines 210-218) |
| `k_factor: float = 1.0` | higher-order correction, optional | **Not used as a separate field** — folded into `cross_section_pb` per row already (see `normalisation_table_v2.csv`'s own `k_factor` column, kept there for provenance/audit, not re-applied at weight-computation time) |
| `gen_filt_eff: float = 1.0` | generator filter efficiency, optional | **Fixed at exactly 1.0, always, deliberately.** Reason: R1 (`INVESTIGATION.md` §C(2)) established that the CMS portal's `total_value` *already* includes both `filter_efficiency` and `matching_efficiency` — applying either again here would double-count. `gen_filt_eff` exists on this dataclass for ATLAS's benefit (where the portal-equivalent number genuinely is pre-filter); for CMS it must be pinned to 1.0, not left at its ATLAS-style default meaning. |
| `n_events: Optional[int]` | cross-check only | CMS record's `number_events` (from `candidate_samples.csv`) — cross-check only, unchanged role |
| `physics_short: Optional[str]` | human-readable label | CMS sample label (e.g. `TTTo2L2Nu`) |
| `generator: Optional[str]` | generator name hint | CMS generator string (e.g. `powheg`, `amcatnloFXFX`) — also unchanged role |

**A CMS normalisation file (JSON)**, one entry per record ID, is specified
as the CMS-side producer of these fields, analogous to what
`services/metadata/fetcher.py`'s `fetch_mc_metadata()` does for ATLAS
(query `atlasopenmagic`) but reading `normalisation_table_v2.csv` instead:

```json
{
  "67801": {
    "dataset_number": 67801,
    "cross_section_pb": 89.28,
    "sum_of_weights": null,
    "k_factor": 1.0,
    "gen_filt_eff": 1.0,
    "n_events": 43546000,
    "physics_short": "TTTo2L2Nu",
    "generator": "powheg",
    "provenance": {
      "portal_total_value_pb": 687.1,
      "portal_record_url": "https://opendata.cern.ch/record/67800",
      "br_applied": {"value": 0.10706, "description": "BR(dilepton, e/mu/tau)=BR(Wlep)^2", "source": "PDG (pdg.lbl.gov/2018, pdg.lbl.gov/2019 listing pages)"},
      "reference_sigma_pb": 89.28,
      "reference_order": "NNLO+NNLL (LHC TopWG) x BR(dilep)",
      "reference_url": "https://twiki.cern.ch/twiki/bin/view/LHCPhysics/TtbarNNLO",
      "k_factor": 1.214,
      "matching_filter_already_included": true,
      "table_row_source": "normalisation_table_v2.csv"
    }
  }
}
```

`sum_of_weights` is deliberately `null` in this static file — it is NOT a
per-dataset constant the way ATLAS's `sumOfWeights` is; it depends on
*which files were actually processed this run* (§A's consistency rule), so
it must be computed at run time by `aggregate_sumw_for_processed_files()`
and merged in afterward, never read from a static config.

**A weights-registry output**, in PR #23's exact `weights_registry.json`
format (`services/calculations/weights_registry.py:113-118`, confirmed
unchanged): `{"default_weight": <float>, "weights": {<source_prefix>:
<float>}}`. For CMS, `source_prefix` is the CMS record ID (or the
file-derived source prefix already used elsewhere in this pipeline for
CMS), and each weight is `compute_normalization()`'s output — i.e. the
*per-file* normalization factor that `genWeight` gets multiplied by, not
yet folded in.

**Deliberate difference from PR #23, stated explicitly**: PR #23's
`WeightsRegistry.weight_for()` returns `self.default_weight` (1.0) for any
source prefix it doesn't recognize, logging a warning once and then
proceeding silently (`services/calculations/weights_registry.py:98-111`,
`INVESTIGATION.md` §E point 1). **For CMS, an unknown record ID must raise
a hard error, never fall back to weight 1.0 silently.** Rationale: a CMS
record ID that fails to resolve almost always means the normalisation file
is simply missing an entry for a real, being-processed sample — silently
weighting it as 1.0 would produce a wrong-but-plausible-looking histogram
with no warning visible to whoever reads the final ROOT file (the warning
lives only in a log line, easily missed on a batch job). This mirrors the
same design choice fork master's own `mc_weights.py` already made
(`SimulationFieldRequestedOnDataError`, `services/parsing/mc_weights.py:35-45`
— raises loudly rather than silently mis-detecting data as simulation).

**What would need to change if PR #23 changes before merge**: this design
depends on exactly three things from PR #23's current shape — (1) the
`MCDatasetMetadata` field *names* (not their ATLAS-specific *meaning* —
this design already reinterprets every field for CMS); (2) the
`weights_registry.json` `{"default_weight", "weights"}` shape; (3)
`compute_normalization()`'s formula and its `PB_TO_FB = 1000.0` constant.
If PR #23 is merged with different field names, a different registry
schema, or an additional term in the formula (e.g. a data-driven scale
factor), this design's CMS normalisation-file schema and registry-builder
would need to be re-mapped field-by-field again — the mapping table above
is the thing to re-run against the new PR #23 diff, not the CMS-side
physics content (σ_eff, BR, k-factor), which is independent of PR #23
entirely.

> **Plain-language summary:** The weight for each simulated event is:
> "how big a slice of the real physics process does this one event
> represent" (a fixed per-sample number) times "does this particular
> event count more or less than the average one in this sample" (the raw
> genWeight value CMS already stamps on every event). We reuse the exact
> same data format PR #23 already invented for this, filled in with CMS's
> own numbers instead of ATLAS's — except for one safety difference: if a
> sample turns out to have no entry in our lookup table, we make the whole
> run stop and complain loudly, rather than quietly pretending that
> sample's events are unweighted (which would look fine but be wrong).

---

## 3. Luminosity

**Which golden JSON the pipeline uses on master**: confirmed directly,
`studies/m0m1j0_cms/cluster/run_m0m1j0_on_file.py:105-106`:

```python
DEFAULT_VALIDATED_RUNS_JSON = (
    "data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
```

— the full-2016 legacy golden JSON (run range 271036–284044, spanning every
2016 era, not restricted to G+H), applied at `run_m0m1j0_on_file.py:271`
(`apply_validated_runs_filter`) before any selection.

**Were the 7.653 + 8.740 = 16.393 fb⁻¹ figures computed on this same JSON?**
Opened directly, `studies/cms_mc_weights/evidence/Run2016Glumi.txt`
(header): `#Brilcalc command: brilcalc lumi -c web --begin 278820 --end
280385 -i /mnt/vol/cert.txt -u /fb --normtag /mnt/vol/normtag_PHYSICS.json`.
The path `/mnt/vol/cert.txt` alone doesn't identify the file — but the
file's own self-consistency check does, decisively:

```
#Check JSON:
#(run,ls) in json but not in results: [(284044, 1), (284044, 2), ..., (284044, 30)]
```

Run **284044** — the exact upper bound of `Cert_271036-284044` — appears in
this G-era file's own "in the JSON, cross-checked against" list, even
though 284044 is far outside the G-era run range (`--begin 278820 --end
280385`) being queried. This is only possible if the `cert.txt` fed to
`brilcalc` for this file *is* the full-2016 JSON (up to run 284044), simply
restricted by `--begin`/`--end` to the G-era run range. Confirmed
independently on `Run2016Hlumi.txt`: `--end 284044` matches the JSON's
own upper bound exactly, and its own "in json but not in results" list is
empty (`[]`) — full completeness, consistent with the same identification.
**Both files were computed against the same `Cert_271036-284044` golden
JSON our pipeline uses at `run_m0m1j0_on_file.py:106`.** The portal record
itself, re-fetched directly (`https://opendata.cern.ch/record/1059`), also
links `Cert_271036-284044` (record 14220) as a directly related dataset,
corroborating (though not as decisively as the internal cross-check above).

**Uncertainty, quoted directly from the same fetch**: *"The uncertainty in
the luminosity measurement of 2016 data should be considered as 1.2%"* —
`https://opendata.cern.ch/record/1059`.

**L to use: 16.393 fb⁻¹ ± 1.2% (≈ ±0.20 fb⁻¹), recorded, golden-JSON-restricted,
source `https://opendata.cern.ch/record/1059` +
`evidence/Run2016Glumi.txt`/`Run2016Hlumi.txt`.** No separate, differently-
restricted value needs to be found — this one already is the right one.

> **Plain-language summary:** We checked, rather than assumed, that the
> "16.39 fb⁻¹" luminosity number and the specific list of "good" data runs
> our own pipeline uses are talking about the same underlying certified
> dataset — and they are, confirmed by a clever internal consistency check
> in the luminosity file itself (a run number from far outside its own
> stated range shows up in its cross-check list, which only makes sense if
> it was checked against the full, unrestricted list). So 16.39 fb⁻¹, with
> a 1.2% uncertainty, is the right number to normalize simulation to.

---

## 4. Settle the flagged references

`normalisation_table_v2.csv` (new, alongside `normalisation_table.csv`,
kept for the audit trail) has every row from before plus a `decision`
column. Summary of the six sub-items:

**(a) Drell-Yan.** The lead's belief of ≈6077 pb (3×2025.74) **could not be
sourced** in this session, despite four separate search attempts: CMS's own
cross-section wiki (`wiki.physik.uzh.ch/cms/physics:crosssections`,
opened — points to XSDB but carries no number itself), CMS's XSDB database
directly (`xsecdb-xsdb-official.app.cern.ch` — redirects to CERN SSO,
blocked, confirmed), and general web search (which surfaced a genuine
spread of candidate values — 5558, 5765.4, 6020.85, 6025.6 pb — none of
them opened as a primary source matching exactly 6077.22). **Kept: 5765.4
pb**, the only figure with a real primary source opened directly
(`arXiv:1712.09814`, HTML, §0.3: *"The dilepton DY production for m_ℓℓ >
50 GeV is normalized to σ_th(DY) = 5.765 nb, which is computed at
next-to-next-to-leading order (NNLO) with fewz (v3.1)"*) plus independent
confirmation from `RazorAnalyzer/xSections.dat` (`1921.8*3`, per-flavor ×3
for e/μ/τ — τ included). The 5558–6077 pb spread across different
tune/PDF/scale choices found in secondary search results is a real,
uncharacterized systematic on top of this, not resolved here. **M-10to50**:
18610 pb (`RazorAnalyzer`, a generator-independent theory figure) stands
unchanged — no competing figure was raised for it.

**(b) ggH.** **Changed.** The sample's own gridpack, read directly in the
prior investigation (`evidence/fragments/HIG-RunIISummer20UL16wmLHEGEN-00085.py`),
is literally named `gg_H_quark-mass-effects_NNPDF31_13TeV_M125` — **M125**,
not M125.09. Re-fetching the LHC Higgs WG YR4 table
(`https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV`)
for the exact mH=125.00 GeV row (not 125.09): **N3LO QCD+NLO EW ggH =
48.58 pb** (vs. 48.52 pb at 125.09 — a 0.1% difference; either row would
have been fine, but 125.00 is the one that actually matches this sample).
This also switches the *order* used from NNLO+NNLL (44.08 pb) to N3LO
(48.58 pb), per the task's instruction. New k-factor: 1.683 (was 1.527) —
**larger**, not smaller; the residual, unexplained gap between this
specific "quark-mass-effects" POWHEG implementation and the YR4 reference
is now bigger, still unresolved. VBF: 3.782 pb at M125.00 (was 3.779 at
125.09) — negligible change, k-factor 0.961 (was 0.96).

**(c) gg→ZZ.** **Kept at k=1, labeled LO** (the `/1000`-corrected MCFM
"BackgroundOnly" reference used is itself LO). A genuine higher-order
source **was** found and is reported as an option, not adopted:
`arXiv:2404.05684` ("Complete NLO QCD corrections to ZZ production in
gluon fusion") reports the gluon-induced channel's NLO/LO enhancement as
roughly 1.7× near threshold, falling to roughly 1.4× by 1 TeV invariant
mass, at 13.6 TeV — a mass-dependent K-factor, not a flat number, and at
the wrong collision energy for this exact use (13.6 vs 13 TeV) besides.
Not adopted. All 8 records remain marked **UNUSABLE AS LISTED** (R3, the
`/1000` units problem) independent of this k-factor question.

**(d) WZTo3LNu.** **Changed — falls back to k=1, flagged.**
`evidence/razor_xsections.dat` lines 155–156 list **the identical** 4.42965
pb for both `WZTo3LNu_..._13TeV-powheg-pythia8` *and*
`WZTo3LNu_..._13TeV-amcatnloFXFX-pythia8` — i.e. a single, externally
adopted recommended number applied uniformly regardless of which generator
actually produced the sample, not amcatnloFXFX's own computed value. This
does not satisfy "same generator/configuration" (task 4(d)'s own test). A
candidate same-generator-family figure was found by search (4.924 pb NLO ×
1.08 NLO-EW k-factor = 5.318 pb, attributed to the CMS WZ Run3 paper,
arXiv:2412.02477) but that paper is at **13.6 TeV**, not our 13 TeV Run 2
sample, and was not opened directly in this session (only reached via
search synthesis) — a real energy mismatch on top of an unconfirmed
primary source, so it is reported but not adopted either. Falls back to
k=1.0 (flagged): σ_eff = this sample's own portal value, 5.218 pb,
unmultiplied.

**(e) ZZTo2L2Nu.** **Excluded from the first production**, per the lead's
decision — the 42% k-factor gap against `RazorAnalyzer`'s 0.564 pb is far
outside the 5–18% spread every other decay-in-ME diboson check in this
table shows, and remains unexplained. What would resolve it, concretely:
(1) open a second, independent published ZZTo2L2Nu cross section (a CMS ZZ
measurement paper's own theory line — not yet done); (2) read this
specific record's own McM generator fragment (not yet fetched, unlike the
25 Tier-0/1 fragments already read for R2) for a hidden phase-space cut not
reflected in `filter_efficiency`; (3) find a TuneCP5-era (not
TuneCUETP8M1-era) published reference, since the `RazorAnalyzer` number is
from an older campaign. Row kept in `normalisation_table_v2.csv` for the
audit trail; excluded from the Task 8 output list.

**(f) Provenance note.** Every row in `normalisation_table_v2.csv` sourced
from `RazorAnalyzer/xSections.dat` now carries an explicit note in its
`decision` column: *"the reference value comes from RazorAnalyzer/
xSections.dat, a third-party CMS analysis group's internal cross-section
table — NOT a primary theory source... Treat its agreement as
corroborating, not as an independent theory confirmation."*

> **Plain-language summary:** Of six specific number-choices flagged for
> double-checking: one (ggH) genuinely changes, using a slightly different
> but more correct theory number (the effect is small in absolute terms but
> makes the still-unexplained gap for this sample bigger, not smaller); one
> (WZ) reverts to "use the sample's own number as-is" because the
> supposedly-matching reference turned out to secretly be the same generic
> number regardless of which simulation method made the sample; one
> (Drell-Yan) keeps its current, properly-sourced number because the
> alternative the technical lead suggested couldn't actually be found
> anywhere real, despite genuine effort; one (ZZ→2 leptons+2 neutrinos) is
> left out of the first round of results entirely, because something about
> it doesn't add up and we don't yet know why; and gg→ZZ keeps a
> "leading-order, we know it's probably an underestimate" label, now with a
> specific alternative on file for later, not used yet. Every number
> borrowed from a private lab's internal spreadsheet (rather than an
> official physics reference) is now explicitly labeled as such.

---

## 5. MC statistics

From `normalisation_table_v2.csv`'s `mc_equiv_lumi_over_L` column (MC's own
equivalent luminosity ÷ 16.393 fb⁻¹ data):

| Sample | MC-equivalent lumi ÷ data | Verdict |
|---|---:|---|
| DYJetsToLL_M-50 amcatnloFXFX | 0.344× | **weaker than data** |
| DYJetsToLL_M-50 madgraphMLM | 0.872× | **comparable to data** (nominal, higher stats) |
| DYJetsToLL_M-10to50 amcatnloFXFX | 0.091× | **much weaker** |
| DYJetsToLL_M-10to50 madgraphMLM | 0.073× | **much weaker** |
| TTTo2L2Nu | 29.3× | strong |
| TTToSemiLeptonic | 23.6× | strong |
| ST_tW top/antitop | 10.5× / 11.4× | strong |
| WWTo2L2Nu | 14.4× | strong |
| WZTo3LNu | 62.6× | strong |
| ZZTo4L | 2480× | very strong |
| TTZ / TTW | 352× / 293× | very strong |
| ggH/VBF H→ZZ→4l | ~4900× / ~29000× | very strong (tiny σ_eff, but few enough real physical events expected that raw MC stats swamp it easily) |

Both DY generators' effective statistics are, plainly, at or below the
level of the real 16.393 fb⁻¹ dataset for the dominant M-50 mass window —
this is a genuine statistical limitation for the highest-mass tail of any
BumpNet region dominated by Drell-Yan, not a normalization bug. It means:
any bump search in a DY-dominated high-mass region will have a
*background* histogram whose own statistical fluctuations (from limited
MC, not physics) can be comparable to or larger than what real data alone
would show — a real MC-stats floor on top of whatever data-driven
sensitivity BumpNet has.

**Default choice, as specified, documented here (not decided by this
document — carried over from the technical lead)**:
- Produce **both** DY M-50 generators as **separately normalised, clearly
  labelled** output sets (e.g. `SM_background_amcatnloFXFX.root` /
  `SM_background_madgraphMLM.root` for the two combined-background files,
  §8) — **never add the two generators of the same physical process
  together** (they are two different, non-independent computations of the
  same physics; summing them would not increase real statistical power and
  would double-count the physics they share).
- **madgraphMLM is the nominal set** (0.872× data — the higher-effective-
  statistics choice); amcatnloFXFX is the alternative (0.344×, but the
  more theoretically precise NLO calculation) — a real, stated statistics-
  vs-precision tradeoff, not a free choice.
- **Tier-2 (HT/Zpt-binned DY) plus stitching are the planned fix** for the
  high-mass/high-jet tail's statistics, as a **separate, later** step (out
  of scope here — no stitching is implemented). What stitching would
  require for this specific family, stated without implementing it:
  (1) the exact generator-level HT (or Zpt) cut boundary each Tier-2 bin
  was produced with, read from its own McM fragment (not yet done for any
  Tier-2 sample); (2) an overlap-removal rule applied at the EVENT level
  before histogramming — reject inclusive-sample events whose own
  generator-level HT/Zpt already falls inside a binned sample's covered
  range, so the inclusive and binned samples partition (not overlap) the
  full phase space; (3) each bin's own σ_eff and Σ genWeight computed
  exactly as any other sample (§2 — no shortcut here); (4) a combined
  weight formula that is *not* simply "sum the histograms" but "sum the
  histograms of samples that have already had the overlapping phase space
  removed from each of them." None of this is built; Tier-2 rows are
  informational only in `candidate_samples.csv`, unchanged.

> **Plain-language summary:** For the single most important background
> (Drell-Yan, the main muon-pair-producing process), our simulated sample
> has, roughly speaking, "as much data" as the real collision dataset for
> one generator choice and noticeably less for the more precise one — so
> results in that mass range will be somewhat noisy from the simulation
> side too, not just from real data being limited. We'll produce and
> clearly label both versions rather than picking one and hiding the
> choice, default to the higher-statistics one for the main result, and
> leave the proper long-term fix (stitching together several
> narrower-but-more-plentiful simulated samples) as a follow-up project,
> not something folded into this one.

---

## 6. Event-count thresholds

Every raw-count rule found, file:line, and its MC behavior (default: **all
such rules apply to RAW, unweighted, simulated entries** — because they
exist to guarantee enough real statistics for the threshold/peak-finding
logic itself to be meaningful, a purely numerical question the physical
weight of each entry doesn't change):

1. **`min_events_per_fs` (config.yaml's `min_events_per_fs=100`)** — the
   real, currently-used enforcement point is
   `raw_count_passes_min_events_prune()`,
   `studies/m0m1j0_cms/postprocessing.py:66-72`: `return raw_count >=
   MIN_EVENTS_PER_FINAL_STATE`, called from `merge_full_v2.py:193` on
   `n_raw = len(raw_mass)` — the **raw, pre-z_peak, pre-max_mass, globally-
   merged-across-all-jobs** per-category event count. This mirrors, without
   re-deriving, `services/storage/sqlite_shards.py`'s
   `prune_final_states_below_min_events()` (`sqlite_shards.py:231`:
   `removed = [fs for fs, count in populations.items() if count < min_events]`
   — also a plain count comparison, no weighting concept present at all).
   **For MC**: this stays a raw (unweighted) event count — a category with
   150 raw simulated events but a tiny genWeight-derived physical yield is
   still "150 raw events," statistically meaningful for the peak-finding
   algorithm below it; a category with 50 huge-weight events is not
   rescued by its large weight, because 50 raw entries genuinely isn't
   enough to trust the shape-finding algorithms that run next.
   - A second, **inactive-in-practice** copy of this same logic exists in
     `studies/m0m1j0_cms/histograms.py:460-528`
     (`build_m0m1j0_histograms`'s own `apply_min_events_prune` parameter) —
     checked on the event count *after* z_peak/max_mass cutoff, not before.
     Confirmed this copy is never actually the deciding one for the real
     delivered files: the real per-job driver
     (`run_m0m1j0_on_file.py:292-294`) always calls it with
     `apply_min_events_prune=False`, and the real merge step
     (`merge_full_v2.py`) does its own, separate, RAW-based check via
     `raw_count_passes_min_events_prune()` instead of ever calling
     `build_m0m1j0_histograms` again. **No actual discrepancy in the
     delivered files** — noted here because the two functions' *documented*
     orders differ, which would matter if `build_m0m1j0_histograms`'s own
     threshold parameter were ever flipped to `True` somewhere new.
2. **`z_peak_cutoff`** (`post_processing_pipeline.py:48-70`,
   `_apply_z_peak_cut`) — not itself a count *threshold*, but determines
   the population the count threshold above is taken *before*; unaffected
   by weighting either way (a plain mass-value cut, `arr[arr >=
   z_peak_cutoff]`).
3. **`max_mass_cutoff`** (10 TeV hard cap,
   `post_processing_pipeline.py:236`/`postprocessing.py:122-126`) — same
   character as (2), a plain mass-value cut.
4. **First-empty-bin split** (`_split_by_first_empty_bin`,
   `post_processing_pipeline.py:355-388`): `if first_empty_bin_idx is None
   or first_empty_bin_idx <= 1` (`:376`) — a bin-*count* rule (is there an
   empty histogram bin close enough to the start to trust a split), built
   from `np.histogram(im_array, bins=bin_edges)` counts
   (`post_processing_pipeline.py:368`) — **for MC, this would need to run
   on the weighted OR unweighted array?** This is genuinely ambiguous in
   the existing code (it operates on whatever array it's handed) and is
   flagged as an **open design question, not decided here**: running it on
   raw counts (consistent with the min-events default above) means the
   peak/split-finding shape logic sees "how many simulated events are
   here," independent of their weight — the safer, more conservative
   choice, and the one this design recommends by extension of the same
   rule, but not yet threaded through code anywhere.
5. **Rightmost-highest-peak finder** (`_find_rightmost_highest_peak`,
   `post_processing_pipeline.py:324-352`) — also built from
   `np.histogram(..., bins=bin_edges)` (unweighted counts,
   `post_processing_pipeline.py:336`) — same open question as (4), same
   recommended default (raw counts), same not-yet-implemented status.

**BumpNet's own thresholds are not touched anywhere in this design** — out
of scope, and no proposal here reads or writes anything under that
project.

> **Plain-language summary:** There's one real "don't trust a category with
> too few events" rule in the actual pipeline (100 raw events minimum, and
> it's a genuine count, not a weighted sum) — the default is to keep this
> exactly as a raw headcount for simulation too, since its whole purpose is
> "is there enough data here to trust the shape at all," a question a
> physical weight doesn't answer. Two smaller shape-finding steps
> (find-the-peak, find-the-first-gap) have a similar "how many events are
> in this bin" character but the existing code doesn't cleanly specify
> whether they should count raw events or weighted ones for simulation —
> flagged as a real open question rather than silently guessed at.

---

## 7. Corrections

| Correction | Default | Expected impact (sourced) | Histogram feature affected |
|---|---|---|---|
| **L1PreFiringWeight_Nom** | **APPLY** as an extra per-event multiplicative factor alongside the normalized genWeight | ~2–3% typical correction size for 2016 (secondary citation, `INVESTIGATION.md` §H — the official CMS TWiki recipe page requires CERN SSO and could not be opened directly in either session) | **Overall yield only** — a flat-ish, mostly η-independent (the effect is concentrated at forward η, 2<\|η\|<3, but the *weight itself* is a single per-event number already averaging over the event's own jet/photon topology) rescaling; not expected to reshape jet-multiplicity or b-jet categories relative to each other, and no direct effect on mass-peak width/position |
| **Pileup reweighting** | **DO NOT APPLY** | No measured 2016 data pileup profile file was found on the portal in the original investigation (searched directly; only simulation/config records found) — cannot build the reweighting target without it | Would affect **jet-multiplicity categories** primarily (pileup adds spurious/extra jets) and, more weakly, overall yield; no direct mass-peak-width effect for a two-muon system, but jet-count categories would shift between adjacent bins |
| **Muon ID/isolation/trigger scale factors** | **DO NOT APPLY** | Individual SFs typically within a fraction of a percent of 1.0 (`INVESTIGATION.md` §H, a CMS tag-and-probe reference found via search); the *combined* ID×iso×trigger product per event was not separately quantified in either session | **Overall yield** primarily (a near-flat rescaling per muon, compounding to ~a few % at most for two muons); negligible expected effect on mass-peak shape |
| **B-tag scale factors** | **DO NOT APPLY** | **UNVERIFIED** — no primary CMS BTV source with an explicit typical-magnitude number was successfully opened in either session (`INVESTIGATION.md` §H) | **B-jet categories specifically** — this is the one correction that directly changes which b-jet-multiplicity bin an event lands in (data/MC differ in b-tag efficiency, so the whole b0/b1/b2/... category *population* is what shifts, not just an overall scale); no b-jet SF means the b-jet categories in an MC/data comparison are the least reliable ones in this delivery |
| **Jet energy resolution (JER) smearing** | **DO NOT APPLY** | Nominal JER ~15–20% at 30 GeV jet pT, ~10% at 100 GeV, ~5% at 1 TeV; JER-uncertainty-driven mass-peak-width change of order ±10% on the width itself (citing a CMS dijet-resonance search, `INVESTIGATION.md` §H) | **Jet-containing mass-peak width specifically.** **Flag, stated plainly per the task**: without JER smearing, every simulated mass peak that includes a jet in its invariant-mass combination (e.g. any `m0m1j0`/`m0m1b0`-style category) will be **narrower than the corresponding real-data peak** — jets in real data carry an extra ~10-20%-level smearing from detector resolution that the simulation's own (already-smeared-at-generation, but not re-smeared-to-match-data) jets don't fully reproduce. Any visual/statistical comparison of a jet-containing MC peak against the matching data peak (§9(c)) should expect the **MC peak to look artificially sharper**, not a sign of a normalization bug. |
| **Muon momentum (Rochester) corrections** | **DO NOT APPLY** | Specific numeric dimuon-mass-resolution improvement was **not found** in either session's searches — only qualitative descriptions (`INVESTIGATION.md` §H); **UNVERIFIED** | Dimuon mass-peak **position and width**, in principle (this is exactly what the correction is designed to fix) — but with no sourced magnitude, the practical expectation stated here is qualitative only: a small (likely sub-percent-level, by general knowledge of what these corrections typically target, but **not independently confirmed** this session) shift/narrowing is possible on the dimuon mass scale specifically, distinct from JER's jet-driven effect above |

> **Plain-language summary:** Of six standard corrections, we apply exactly
> one (a data/simulation trigger-timing fix that's free and already sitting
> in every file), and deliberately skip the other five because the
> ingredients to do them properly aren't available yet. The two most
> important consequences to remember when looking at the results: b-jet
> categories are the least trustworthy comparison between simulation and
> real data (because we're not correcting for how often each correctly
> tags a real b-jet), and any simulated mass peak that includes a jet will
> look artificially narrower than the same peak in real data (because we're
> not smearing simulated jets to match how blurry real jets actually are).
> Neither is a bug — both are known, documented gaps.

---

## 8. Outputs

- **Weighted TH1 histograms with per-bin sum-of-weights-squared.** Concrete
  change needed: `to_writable_th1f()` (`studies/m0m1j0_cms/histograms.py:329-378`)
  currently hardcodes `fSumw2=None` (`:376`) — extend it to accept an
  optional `sumw2: Optional[np.ndarray]` parameter (same shape as `values`,
  with the same under/overflow-padding convention already applied to
  `data`, `:357-358`) and pass it through as `fSumw2=sumw2_padded` when
  given. The per-bin sum-of-weights-squared array itself is a second
  accumulator built alongside `counts` inside `make_fixed_grid_histogram`'s
  own `np.add.at` loop (§1): `np.add.at(sumw2, bin_idx, (weights[in_range])
  ** 2)`. **Same names, binning and cropping as the data delivery** — no
  change to `FIXED_MASS_MIN_GEV`/`MAX_GEV`, `BIN_WIDTH_GEV`,
  `_convert_to_bumpnet_name`, or `crop_bumpnet_root.py`'s cropping logic;
  MC histograms go through the identical grid/naming/cropping pipeline data
  already uses, so a data histogram and its matching MC histogram are
  directly overlay-able bin-for-bin. **Written with uproot** — this is
  already how the real delivery works (§1; there is no PyROOT on the
  cluster at all), so this is a continuation of the existing method, not a
  new one.
- **One ROOT file per sample**, plus **one combined "SM background" file**
  per Task 5's two-generator-set rule — i.e. two combined files,
  `SM_background_madgraphMLM.root` (nominal) and
  `SM_background_amcatnloFXFX.root` (alternative), each built by summing
  the (already individually-normalised) per-sample histograms of every
  Tier-1 sample **except** `ZZTo2L2Nu` (§4(e), excluded) and the 8
  `GluGluToContinToZZ*` records (§4(c)/R3, marked UNUSABLE AS LISTED) —
  with the DY M-50 slot filled by whichever generator matches that combined
  file's own label, never both. **Component list recorded in a README**,
  following the existing delivery's own precedent format exactly
  (`origin/deliver/doublemuon-bumpnet:studies/cms_coverage/deliver/committed/README.txt`
  — plain-text, "WHAT THESE FILES ARE" / dataset-and-run-range / naming-
  convention sections): naming the record ID, generator, σ_eff, k-factor,
  and BR used for every component, plus the two excluded samples and why.
- **The leptoquark (42407, LQToBMu_M-400_pair) as a separate signal file**
  — not summed into any background file, using the stop-pair-proxy σ_eff
  from `normalisation_table_v2.csv` (2.276 pb) with its scalar-only and
  small-coupling caveats carried into that file's own README entry
  verbatim.
- **An OPTIONAL pseudo-data mode, OFF by default, pending Maryna.** When
  enabled: a Poisson draw from each normalised bin's expectation value,
  with a fixed, recorded random seed (so the draw is reproducible, not a
  fresh random result every time the mode is re-run). **Why weighted
  histograms are not Poisson, in plain words**: a real data histogram's
  bin content is a genuine event *count* — draw the same experiment twice
  and the statistical spread you'd see is exactly what Poisson statistics
  predicts from that count alone. A *weighted* MC histogram's bin content
  is a *sum of weights*, not a count — one bin with ten events of weight 5
  each and another bin with fifty events of weight 1 each can show the
  *same* bin content, but the first has genuinely less statistical
  information behind it (fewer independent events) than the second, so its
  "true" statistical uncertainty is larger than plain Poisson-on-the-bin-
  content would suggest (this is exactly what the per-bin sum-of-weights-
  squared, `fSumw2`, is *for* — it's the correct uncertainty estimator,
  and it is NOT what you'd get by treating the bin content itself as a
  Poisson mean). Feeding a weighted bin's raw content into a Poisson draw
  would silently understate how uncertain that bin really is. This is
  exactly the same concern already raised in `INVESTIGATION.md` §G about
  BumpNet's own training-data assumptions — carried over as an open
  question for Maryna in §11 below, not resolved here.

> **Plain-language summary:** Every output file will look and be named
> exactly like the files already delivered — same grid, same bin width,
> same category names, same cropping — so a data file and a simulation
> file for the same category can be laid directly on top of each other for
> comparison. New: each histogram also carries its own proper
> "how-uncertain-is-this-bin" number (not present in today's files at
> all), each simulated sample gets its own file, there's one combined
> "all Standard Model backgrounds added together" file per Drell-Yan
> choice (never mixing the two Drell-Yan choices together), the
> leptoquark signal stays in its own separate file, and there's an
> optional, off-by-default mode to turn a smooth simulated prediction into
> a single realistic-looking "pretend dataset" — which is not the same
> thing as real data statistically, explained in plain terms above.

---

## 9. Validation plan (to be executed later, not now)

**(a) Arithmetic closure.** For every sample: Σ(per-event weight) over
every processed event = σ_eff × L, to within 1e-6 relative. This follows
directly from the weight formula (§2) — `Σ weight = Σ(genWeight × σ_eff ×
1000 × L / Σ genWeight) = σ_eff × 1000 × L × (Σ genWeight / Σ genWeight) =
σ_eff × 1000 × L` algebraically, so this check is really testing that the
*implementation* doesn't silently drop, double-count, or mis-slice events
between the Σ genWeight denominator computation and the per-event
weighting loop — exactly the kind of bug the existing
`aggregate_sumw_for_processed_files()` consistency rule (§2, §A) is
designed to catch on the denominator side; this check verifies the
numerator side is equally consistent.

**(b) Per-file genEventSumw vs Σ genWeight check.** Exactly as already done
in Task B of the prior investigation (`INVESTIGATION.md` §B) — re-run per
sample, per file, as a standing regression check before trusting any new
sample's weights, not a one-time thing done only for the original 3
samples.

**(c) Physics check: TTTo2L2Nu (+ tW, Drell-Yan) vs. DoubleMuon data in a
top-enriched region.** **Specific existing histogram names identified**,
read directly from the actual delivered manifest
(`origin/deliver/doublemuon-bumpnet:studies/cms_coverage/deliver/committed/manifest_min26bins.json`,
saved excerpt `evidence/deliver_manifest_m0m1_bjet_entries.json.gz`):

| Histogram (BumpNet name) | Region | n_events (data) | Mass range (GeV) |
|---|---|---:|---|
| `mass_m0m1b0_cat_0ex_2mx_1jx_0gx_0tx_1bx` | 2 muons, 1 jet, exactly 1 b-jet | 43,548 | 140–1100 |
| `mass_m0m1b0_cat_0ex_2mx_2jx_0gx_0tx_1bx` | 2 muons, 2 jets, exactly 1 b-jet | 14,418 | 150–1000 |

Both are dimuon-mass (`m0m1`) histograms in a b-jet-containing category,
with their filled range starting at 140-150 GeV — **already well above the
Z peak** (91 GeV) by construction (the pipeline's own z_peak_cutoff +
peak-removal chain, §6, guarantees this), i.e. genuinely a top-enriched,
not Z-enriched, region, with enough real events (tens of thousands) for a
meaningful comparison. **Expected level of agreement, given §7's
uncorrected effects**: not exact — specifically, (i) the b-jet category
population itself is the least reliable comparison axis (no b-tag SF, §7),
so a normalization-level (overall-yield) discrepancy in *this specific*
category should not automatically be read as a weight-formula bug before
checking a non-b-tagged region for the same behavior; (ii) any real
mass-peak-shape feature in this region will appear **narrower in
simulation than in data** (no JER smearing, §7) — a genuine expected
distortion, not evidence against the normalization itself; (iii) pileup
and muon-SF effects are both expected to be small (§7) and closer to a
flat rescaling, so should not much affect the qualitative *shape*
agreement, only a modest overall-yield offset.

**(d) The leptoquark overlay on the matching data histogram.** Same
mechanism as (c) — overlay the separately-delivered leptoquark signal file
(§8) on whichever existing DoubleMuon BumpNet histogram matches its own
final-state category, at whatever σ_eff (the stop-pair proxy, flagged) is
current at validation time. Not run, not interpreted, per the explicit
out-of-scope instruction against running BumpNet or interpreting Maryna's
excesses.

> **Plain-language summary:** Before trusting any of this, four checks
> should be run (later, not now): does the math add up exactly (a pure
> arithmetic check); does each individual file's own bookkeeping numbers
> agree with what we read from it directly (a repeat of a check already
> done once, now made standard practice); does a real, ttbar-rich slice of
> the actual delivered data look roughly like our normalized simulation
> predicts (using two specific, already-existing histograms with tens of
> thousands of real events, in a region chosen to avoid the Z-peak); and
> does the leptoquark signal, laid on top of the matching real-data plot,
> look like a bump would be expected to look. For the third check, some
> disagreement is *expected* and explained in advance (jets in simulation
> will look artificially narrower; the b-jet-count categories specifically
> are the least trustworthy comparison because a correction we're not
> applying yet mainly affects exactly those).

---

## 10. Implementation plan

**Ordered steps:**
1. Write the CMS normalisation JSON (§2) from `normalisation_table_v2.csv`
   — a small, pure-Python script, no cluster needed.
2. Extend `studies/m0m1j0_cms/cluster/run_m0m1j0_on_mc_file.py`'s
   already-working genWeight-reading pattern into the *current* production
   driver: `run_m0m1j0_on_file.py` (add `read_event_weights=True`-style
   genWeight reading) and `build_mass_by_category_npz` (add a `genWeight`
   column) — **files that would change**:
   `studies/m0m1j0_cms/cluster/run_m0m1j0_on_file.py` (or a new
   `run_m0m1j0_on_mc_file_v2.py`, to avoid touching the already-working
   data driver — the safer choice, avoiding any risk to the existing,
   already-validated data production path).
3. Extend `make_fixed_grid_histogram()` and `to_writable_th1f()`
   (`studies/m0m1j0_cms/histograms.py`) per §1/§8 — small, isolated
   signature additions, default-preserving for every existing (data) call
   site.
4. Extend `merge_full_v2.py` (or a new `merge_full_v2_mc.py`) to thread the
   per-file normalization factor and genWeight array through
   `apply_full_postprocessing`'s existing `main_mask` output into the
   updated `make_fixed_grid_histogram`.
5. Build the weights-registry JSON per sample (§2) — reuses PR #23's
   `weights_registry.py` module directly (importable, no ROOT dependency)
   with a CMS-specific producer script analogous to
   `utils/build_weights_registry.py`.
6. Run validation (a)+(b) from §9 on one small sample first (e.g. 42407,
   12 files, 50,000 events) before the full run.
7. Run the full per-sample production (below), then build the combined
   files (§8).
8. Run validation (c)+(d) from §9.

**Estimated cluster cost.** From `candidate_samples.csv`, the Tier-0/1 set
minus `ZZTo2L2Nu` (excluded, §4(e)): **24 samples, 718 files, ≈502.5
million events** (733 files/518.5M events for all 25 rows, minus
`ZZTo2L2Nu`'s 15 files/15.9M events). One PBS array job per file is this
project's own established convention for this exact study (`pbs_m0m1j0_ttbar.sh`,
`pbs_m0m1j0_full.sh` — both already run this way for the ttbar MC pilot
and the full data production respectively) — so **≈718 array-job tasks**,
each:
- **Queue N, `#PBS -m n`, `threads=1`** (task's own constraints).
- **`-l io=30`** (MB/s) — the value both the existing ttbar MC job
  (`pbs_m0m1j0_ttbar.sh:28`) and the full data job
  (`pbs_m0m1j0_full.sh:45`) already use for this exact kind of per-file
  NanoAOD read.
- **Walltime**: the existing ttbar MC precedent uses `00:30:00`
  (`pbs_m0m1j0_ttbar.sh:27`, "task's own cap for this task"); the existing
  full data precedent uses `00:20:00` ("~30x the pilot's slowest observed
  42s", `pbs_m0m1j0_full.sh:31`). This design's per-file jobs read a
  similar or smaller number of branches (mass calculation + one extra
  scalar branch, `genWeight`) than either precedent, so **`00:30:00` per
  job, matching the more conservative ttbar precedent**, comfortably
  within the task's own `≤ 02:00:00` cap.
- **Outputs under `/storage/agrp/berkom/atlas-utilization/` only**,
  **fewer than 1,000 files per directory** — 718 per-job output
  directories (each holding a handful of files: `mass_by_category.npz`,
  `job_metadata.json`, etc., mirroring the existing per-job output
  layout) comfortably clears this if organized as one subdirectory per
  sample (largest sample, `TTToSemiLeptonic`, is 138 files/output-dirs —
  well under 1,000).
- A handful of subsequent merge jobs (one per sample, local numpy/uproot
  work, likely fast enough to run without a separate PBS submission, or a
  short single-threaded job each if not) — not separately budgeted in
  detail here, since none of the existing precedents needed to (the
  existing `merge_full_v2.py` run for the real data production is not
  documented as having needed its own PBS job in any file read this
  session).

**Risks:**
- The two-parallel-code-paths situation found in §1 (an old, working,
  ttbar-only genWeight path; a newer, BumpNet-category-aware, currently-
  unweighted path) means there is a real temptation to "just extend the
  old path" for speed — this design deliberately recommends extending the
  *newer* path instead, since only the newer path produces
  BumpNet-category, cropped, delivery-format-matching output; extending
  the old path would produce a second, incompatible MC output format.
- `ZZTo2L2Nu`'s unresolved 42% discrepancy (§4(e)) and the gg→ZZ family's
  ×1000 units problem (§4(c)/R3) are both still open — proceeding with
  production for the *other* 23 samples does not require resolving either,
  but neither should be treated as "probably fine" without the specific
  follow-up work already named in §4(e) and §C(5) of `INVESTIGATION.md`.
- The DY M-10to50 samples' very low MC-equivalent statistics (§5, <0.1×
  data) mean any low-mass dimuon category will be MC-statistics-limited
  well before it is data-limited — a real result, not a bug, but one that
  could be mistaken for a normalization problem if not anticipated.
- No cluster job of any kind has been run for this design (out of scope,
  per the task) — every walltime/io estimate above is a precedent-based
  estimate, not a fresh benchmark; the first real production jobs should
  be watched for actual walltime before committing to the full 718-job
  array un-supervised.

> **Plain-language summary:** The rollout is: write one lookup table,
> teach the existing per-file program to also read the weight branch,
> teach the histogram-building code to use weights instead of a hardcoded
> "count everything once," test it on the smallest sample first, then run
> it on the other 23 approved samples (roughly 718 individual files worth
> of work, each expected to take under 30 minutes on the cluster,
> comfortably within the rules given), then build the combined files and
> run the sanity checks. The main risk worth watching: there's an old,
> already-working way to read simulation weights that would be tempting to
> reuse wholesale, but it doesn't produce files in the same format as
> what's already been delivered — the design deliberately extends the
> newer, matching-format code instead, even though that requires slightly
> more new work.

---

## 11. Open questions for Maryna

Carried over, unchanged, from `INVESTIGATION.md` §G:
1. Are MC histograms actually consumed as BumpNet training/testing inputs,
   used only for signal injection on top of real/pseudo-data, or only for
   post-hoc interpretation of an already-found bump? (Three different roles
   with different weight-normalization requirements.)
2. If MC histograms feed the network directly: should they always go
   through the pseudo-data mode (§8) first, given that a weighted histogram
   is not Poisson-distributed the way real data is?
3. Which exact ATLAS leptoquark DSID and decay channel does she want
   overlaid — DSID 312117 (up-type, electron decay) or 312159 (down-type,
   electron decay), both at β=0.5 (only half the LQ pairs decay to a
   visible charged lepton, per `INVESTIGATION.md` §D), neither matching
   CMS's own muon-decay `LQToBMu_M-400_pair` sample in flavor?

**New questions this design raises:**
4. Does Maryna's BumpNet reader actually use the per-bin sum-of-weights-
   squared (`fSumw2`) if we start writing it (§8) — or does it read only
   bin contents today? If the latter, writing `fSumw2` is still correct
   practice but won't change anything she sees until/unless her reader is
   updated to use it.
5. Is the "both DY generators, never summed, madgraphMLM nominal" default
   (§5) actually what she wants for her own analyses, or would she prefer
   a single, pre-chosen DY set (accepting the amcatnloFXFX statistics
   penalty for the more precise NLO calculation, or vice versa)?
6. For the combined "SM background" file (§8): does she want b-jet
   categories included at all, given §7's flag that they're the least
   reliable comparison axis without a b-tag scale factor — or would she
   prefer those categories suppressed/separately labeled in the first
   delivery until that correction exists?

> **Plain-language summary:** Three questions from before still need her
> input (what job simulation actually does in her workflow, whether to
> convert smooth predictions into fake-but-realistic data first, and which
> exact ATLAS comparison sample she meant). Three new ones came up while
> designing this: whether a technical improvement to the files
> (per-bin uncertainties) will actually be used by her existing tools;
> whether picking one specific Drell-Yan simulation as the "default" one
> matches what she'd actually choose; and whether she'd rather we hide the
> b-jet-tagged categories in the first delivery, given we know that
> comparison is currently the least trustworthy one, rather than show them
> with a caveat attached.
