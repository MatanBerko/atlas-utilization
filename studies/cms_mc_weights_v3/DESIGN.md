# CMS Monte-Carlo event weights, v3 — design

**Branch:** `design/cms-mc-weights-v3` (from fork master `db1bd32`)
**Scope of this round:** read-only verification and this document. No
pipeline code, no `--is-mc` implementation, no MC production, no batch jobs.
**Audience:** physicist reviewer.

Every number below is labelled **VERIFIED BY RUNNING** (this round ran
something and saw it) or **UNVERIFIED** (taken from a document, a commit
message or a table). "Not observed" is never written as "impossible".

Reference commits:

| What | Commit |
|---|---|
| fork master (delivered four-dataset production) | `db1bd32` |
| upstream master, includes PR #34 | `f16768e` |
| PR #35 head (Yuval/aesenc, **not merged**) | `fa63544`, branched from `f16768e` |
| PR #23 head (superseded) | `9be20a9` |

All four were confirmed **VERIFIED BY RUNNING** (`git rev-parse`); PR #35's
merge base with `upstream/master` is exactly `f16768e`.

---

## Part A — the technical lead's reading of PR #35

All file:line citations are at `fa63544`.

### A1 — weights as a parallel `_mcw` signature, buffered with the masses — **CONFIRMED**

* `services/pipelines/im_pipeline.py:24` — `MC_WEIGHT_SUFFIX = "_mcw"`.
* `im_pipeline.py:193-197` — weights are produced only when
  `config["mc_weighting_enabled"]` is set **and** the sliced events still
  carry `MC_EVENT_INFO_FIELD`.
* `im_pipeline.py:202-226` — `_event_weights` returns
  `weights * norm`, i.e. **per-event generator weight × per-DSID
  normalisation**; the final weight, not an intermediate.
* `im_pipeline.py:244` appends the masses to the buffer and
  `im_pipeline.py:248` appends `combination_name + MC_WEIGHT_SUFFIX` to the
  *same* buffer dict, both **before** the threshold test at
  `im_pipeline.py:251`. So a flush can never store masses without their
  weights. The code says so itself in the comment at `im_pipeline.py:245-246`.

### A2 — identical masks on masses and weights; weighted peak finding; unweighted empty-bin split — **CONFIRMED**

In `services/pipelines/post_processing_pipeline.py`:

* `252-261` — `keep = _z_peak_mask(...)`, then `keep &= arr <= max_mass_cutoff`,
  applied to `arr` and, if present, to `warr`. One boolean mask, both arrays.
* `263-271` — the peak is located by
  `_find_rightmost_highest_peak(arr, bin_width, logger, weights=warr)`, and
  `_find_rightmost_highest_peak` (`370-394`) passes `weights` straight into
  `np.histogram`. **Peak finding is on the weighted spectrum.**
* `275-286` — `main_mask = _main_array_mask(arr, bin_width, logger)`, and
  `_main_array_mask` (`397-434`) calls `np.histogram(im_array, bins=bin_edges)`
  with **no** `weights` argument. **The empty-bin split is on unweighted
  counts.** The same mask is then applied to `warr`.
* `_z_peak_mask` is at `48-69` and is a pure mask, deliberately exposed as one
  (see its own docstring and `_main_array_mask`'s).

### A3 — TH1D + Sumw2 whenever any `_mcw` signature exists; weights paired chunk by chunk — **CONFIRMED**

* `services/pipelines/histograms_pipeline.py:262` —
  `weighted = any(s.endswith(MC_WEIGHT_SUFFIX) for s in signatures)`;
  `263` strips the `_mcw` signatures from the list to be histogrammed.
* `histograms_pipeline.py:68-81` — `_new_histogram` returns
  `ROOT.TH1D(...)` followed by `hist.Sumw2()` when `weighted`, else `TH1F`.
* `histograms_pipeline.py:367-390` — `_iter_weighted_signature_chunks`
  yields `(masses, weights)` per stored chunk and requires chunk-for-chunk
  alignment (`len(weights) == len(chunks)` and every pair equal in length);
  a misaligned sibling is ignored with a warning rather than misapplied.

**Worth flagging for the port:** `weighted` is a **global** flag computed over
the union of signatures across every input shard. One `_mcw` signature
anywhere switches *every* histogram in that run to TH1D+Sumw2, including
histograms that have no weights at all. That is harmless for a pure-MC run
and harmless for a pure-data run, but it means a mixed run would silently
change the on-disk class of the data histograms. Our design never mixes them
in one run (see D1), so this is a note, not a defect.

### A4 — the `require_metadata` gap — **CONFIRMED**, and worse than stated

`orchestration/handlers/mass_calculation_handler.py:217-222`:

```
if MC_EVENT_INFO_FIELD not in particle_arrays.fields:
    self.logger.warning(
        f"MC weighting enabled but {root_file_path.name} carries no MC event "
        "info; its events will be unweighted."
    )
    return
```

This branch **never looks at `mc_cfg.require_metadata`**. Every other failure
path in the same function does: no generator-weight branch (`237-239`), no
dataset number (`248-250`), no fetchable metadata (`268-270`) — each raises
under `require_metadata`. Only "no MC info at all" is a warning-and-continue.
The file's masses are then stored with `mc_event_weights = None`
(`im_pipeline.py:193`, the `MC_EVENT_INFO_FIELD in sliced_events.fields` test
fails), i.e. with no `_mcw` sibling at all.

The downstream fallback is confirmed in both places the lead named:
`post_processing_pipeline.py:245-250` (length mismatch → warning → `warr = None`)
and `histograms_pipeline.py:384-388` (misaligned sibling → warning → fill
unweighted).

**The amplification the lead did not state:** `post_processing_pipeline.py:225-234`
concatenates the mass chunks of a signature across **all** input shards, and
the weight chunks likewise, before comparing lengths. So one weightless file
in a multi-file run makes `len(warr) != len(arr)` for the merged signature,
and line `250` sets `warr = None` for the **whole merged signature** — the
correctly-weighted events from every other file lose their weights too. The
failure is not localised to the bad file.

### A5 — `sumOfWeights` is the whole-DSID metadata value — **CONFIRMED**

`services/metadata/fetcher.py:388` —
`sum_of_weights = self._to_float(raw.get("sumOfWeights"))`, where `raw` comes
from `atom.get_metadata(str(dataset_id))` (`fetcher.py:379`), i.e.
atlasopenmagic's per-DSID metadata for the entire sample. Nothing in the path
relates it to the files actually processed. It is consumed unchanged by
`services/calculations/mc_weights.py::compute_normalization`, which divides the
expected yield by `metadata.sum_of_weights`.

### A6 — `prune_final_states_below_min_events` never counts `_mcw`, removes it with its final state — **CONFIRMED**

`services/storage/sqlite_shards.py:176-178` adds an optional `(_mcw)?` group to
the signature pattern; `216-217` destructures it as `is_weight` and skips the
event-count accumulation when it is set (`and not is_weight`); `222` still
records the signature under its final state, so `237-242` deletes it along with
the final state. Exactly as described.

### A7 — `cms-nanoaod` has a generator-weight branch but no channel-number branch — **CONFIRMED**

`services/parsing/schemas.py:140-148` — `MC_EVENT_WEIGHT_BRANCHES` contains
`"cms-nanoaod": "genWeight"` (line `145`).
`schemas.py:154-164` — `MC_CHANNEL_NUMBER_BRANCHES` has **no** `cms-nanoaod`
key. `schemas.py:166-169` — `MC_RUN_NUMBER_BRANCHES` has only `2024r-pp`.

Consequence, traced through: `services/parsing/file_parser.py::_mc_event_info_branches`
would build an `_mcEventInfo` record containing only `_mcEventWeight`;
`domain/events.py::dsids_in_events` returns an empty array when
`MC_CHANNEL_NUMBER_FIELD` is absent from the record; and
`mass_calculation_handler.py:241-251` then raises under `require_metadata`.
**So yes — as written, PR #35 in strict mode aborts on CMS files.**

This round additionally **VERIFIED BY RUNNING** *why* no such branch is mapped:
CMS NanoAOD has no per-event dataset identifier at all. Scanning the full
Events-tree branch list of one MC file (record 37728, 1504 branches) and one
data file (record 30522, 1380 branches) for any of
`dsid|channel|sample|dataset|process|procid|mcid|xsec|crossSection|lheweight|genId`
returned exactly one MC hit, `LHEWeight_originalXWGTUP` — the LHE original
weight, not a sample identifier
(`studies/cms_mc_weights_v3/evidence/dataset_identity_branches.json`).

### A8 — field names, metadata shape, config block — **CONFIRMED**

* `domain/events.py:17-20` — `MC_EVENT_INFO_FIELD = "_mcEventInfo"`,
  `MC_EVENT_WEIGHT_FIELD = "_mcEventWeight"`,
  `MC_CHANNEL_NUMBER_FIELD = "_mcChannelNumber"`,
  `MC_RUN_NUMBER_FIELD = "_mcRunNumber"`.
* `domain/metadata.py:38,52-57` — `MCDatasetMetadata` with exactly
  `dataset_number`, `cross_section_pb`, `sum_of_weights`, `k_factor`,
  `gen_filt_eff`, `physics_short`.
* `domain/config.py:231,243-251` — `MCWeightingConfig` with `enabled`,
  `target_luminosity_fb`, `luminosity_by_campaign`, `require_metadata`;
  `config.py:458` — `enabled` requires `parsing_task_config.parse_mc: true`.

**One small discrepancy, for the port:** `config.yaml` ships
`require_metadata: true` (its own comment says so), but the dataclass default
is `require_metadata: bool = False` (`config.py:251`) and `from_dict` reads
`mc_dict.get("require_metadata", False)` (`config.py:454`). A config that omits
the key therefore gets the *permissive* behaviour, which is the opposite of the
shipped intent. Not a blocker; worth fixing when the port happens.

### Does PR #35 merge cleanly into fork master? — **No. VERIFIED BY RUNNING.**

A local throwaway branch off `design/cms-mc-weights-v3` merged `fa63544` with
`git merge --no-commit --no-ff`. Result: **13 conflicting files, 53 conflict
hunks** — matching the lead's observation of 13 files exactly.

| File | conflict hunks |
|---|---:|
| `services/parsing/file_parser.py` | 10 |
| `services/parsing/threaded_processor.py` | 8 |
| `orchestration/handlers/mass_calculation_handler.py` | 7 |
| `services/pipelines/histograms_pipeline.py` | 6 |
| `domain/config.py` | 4 |
| `orchestration/handlers/parsing_handler.py` | 4 |
| `domain/events.py` | 3 |
| `services/parsing/root_io.py` | 3 |
| `pipeline/executor.py` | 2 |
| `services/pipelines/post_processing_pipeline.py` | 2 |
| `services/storage/sqlite_shards.py` | 2 |
| `config.yaml` | 1 |
| `services/parsing/schemas.py` | 1 |

The merge was aborted, the throwaway branch deleted, and `git ls-remote --heads
origin` confirmed nothing of it reached any remote.

### A9 — upstream #34 vs the fork's exact labels

**Names and labels AGREE, including two-digit counts. The event-acceptance
rule DIFFERS.** All of the following is **VERIFIED BY RUNNING**
(`studies/cms_mc_weights_v3/probe/check_a9_labels_and_rules.py`, output in
`evidence/check_a9_labels_and_rules_out.json`).

*What agrees:*

* The label construction is the same expression on both sides:
  `"_".join(f"{count}{letter}")` over the configured object tuple, filtered to
  the types present in the event record, in the same fixed order
  `(Electrons e, Muons m, Jets j, Photons g, Taus t, BJets b)`. Upstream:
  `services/calculations/im_calculator.py:17-20,71-77` at `f16768e`. Fork:
  `studies/cms_datasets/cluster/run_dataset_on_file.py:211-214,1196-1219`.
* The histogram-name rule `re.findall(r'(\d+)([emjgtb])', fs_str)` is shared
  verbatim (upstream `services/pipelines/histograms_pipeline.py:443`; fork
  `studies/m0m1j0_cms/histograms.py:132`, copied with a "do not edit
  independently" note). A ten-jet label produces
  `mass_m0m1_cat_0ex_2mx_10jx_1bx` — the two-digit count survives.
* The signature-grouping regex `_FS_([0-9emjgtb_]+)_IM_([emjgtb\d]+)$` matches a
  two-digit count and returns `("0e_2m_10j_1b", "m0m1")`.
* Neither side truncates any more: upstream #34 removed the
  `_limit_particles_in_fs(fs, threshold=4)` call from `group_by_final_state`
  (`im_calculator.py:107-110`); the fork removed the same call from its own
  grouping (`run_dataset_on_file.py:552`).

*What differs — the acceptance rule.*

Upstream #34's `_is_valid_fs` (`im_calculator.py:87-99`) rejects an event if
the number of distinct present object types falls outside `min_n..max_n` (1..4
from `config.yaml:141-142`), or if any **non-Jets** type's count exceeds
`max_k` (4 from `config.yaml:144`). Light jets are exempt. The rule is
**per type**.

The fork's delivered Version B (`rare4`) rule rejects an event if
**electrons + muons + b-jets > 4** in total
(`run_dataset_on_file.py:2055-2059`, reused by `rare4` at `2146`), keeping every light jet. The rule is on
the **total**.

Scanning every count pattern with `e, m, b ∈ 0..6` and `j ∈ 0..2`, the two
rules disagree on **271 patterns**: **270** that upstream #34 keeps and
Version B rejects (e.g. `0e_2m_0j_3b`, `0e_3m_0j_2b`, `0e_1m_0j_4b` — each
individual count ≤ 4 but the sum > 4), and **1** that Version B keeps and
upstream #34 rejects, namely the empty pattern `0e_0m_0j_0b` (upstream's
`min_n = 1` requires at least one present type; such an event has no objects
and produces no masses, so this one is academic).

*One shared-code residue, and why it is harmless here.* Upstream #34 fixed the
count parse from `str_amount_particle[0]/[1]` to `[:-1]/[-1]` in both
`im_calculator.py` and `physics_calcs.py`. Fork master `db1bd32` still has the
single-character version (`services/calculations/physics_calcs.py:91-92,110-111`),
and the delivered driver calls that shared function at
`run_dataset_on_file.py:1448`. On a label such as `0e_2m_10j_1b` it reads
`("1", "0")` for the jet token, fails to map the letter `0`, and silently skips
that type's requirement — i.e. treats it as satisfied. **VERIFIED BY RUNNING:**
the largest `start + count` requirement over the delivered 186-combination set
is **4** for every one of Electrons, Muons, Jets and BJets, so a true count of
≥ 10 satisfies every requirement anyway and skipping the check returns the same
answer the correct check would. No delivered result changes. The fork documents
this limitation itself at `run_dataset_on_file.py:517-526`; this round confirms
the arithmetic rather than taking it on trust.

**Reported, not synced.** No upstream commit is merged or cherry-picked here.

---

## Part B — honest state of the old MC work

### B1 — the old MC branches

All commits/dates **VERIFIED BY RUNNING** (`git log`). None of these branches
is touched by this round; they stay as a record.

| Branch | Head | Date | Base vs `db1bd32` | Commits | What it is |
|---|---|---|---|---:|---|
| `feature/cms-mc-weights-v2` | `c89d0f0` | 2026-09-30 | `741726c0` | 21 | The furthest-along MC implementation: an `--is-mc` mode added to the *then-current* driver, a PBS array production, an MC delivery builder, V1–V5 validation scripts, and `v2/PAUSED.md`. |
| `feature/cms-mc-weights-phase1` | `8684a8c` | 2026-09-30 | `4f50b992` | 14 | Phase-1: a standalone MC driver + merge + PBS for three samples, the normalisation registry builder, and the diagnosis rounds (D1–D5, E1–E2) that produced the Z-peak numbers. |
| `design/cms-mc-weights` | `3930d88` | 2026-09-30 | `4f50b992` | 3 | The v1 design document only. |
| `investigate/cms-mc-normalisation` | `1d4ee2a` | 2026-09-30 | `4f50b992` | 2 | `INVESTIGATION.md` + the normalisation tables. No pipeline code. |
| `feature/cms-mc-weights-and-probe-retry` | `3cf6ffd` | 2026-09-16 | `3cf6ffd` (an ancestor of master) | 0 | Fully contained in master's history; documents `read_event_weights`/`read_pileup_info` and the probe retry. |

**Why none of it is reusable as-is.** Every one of these branches predates the
delivered selection. The v2 MC driver
(`studies/m0m1j0_cms/cluster/run_m0m1j0_on_mc_file_v2.py`) and its delivery
builder were written against a selection that was:

* **muon-only** — DoubleMuon and SingleMuon; no DoubleEG, no MuonEG, no
  electron-muon overlap removal, no electron trigger matching, no
  `--population matched4`;
* **capped at 4 per type** — labels went through
  `limit_particles_in_fs(fs, 4)`, so 5-light-jet events were merged into `4j`
  and the exact labels `5j, 6j, …` the delivery now requires did not exist;
* **on the old Z cut and old names**;
* **per-dataset runs** — one production per sample, with the four-dataset
  de-duplication order and the inclusive/exclusive split absent;
* **separate weight shards** — the weights lived in their own arrays/files
  rather than as aligned siblings of each mass signature, so nothing in it
  matches PR #35's conventions.

These are differences in the *physics selection*, not in the plumbing, so the
weight machinery cannot be lifted across even where its arithmetic is right.
What *is* reusable is the normalisation research (B2) and the generator
conclusion (B3).

`v2/PAUSED.md` (**UNVERIFIED**, read from the branch) records that MC
production was stopped on 2026-09-30 ~16:53 IDT pending Maryna's confirmation
of the final-state rule; 19 PBS arrays were `qdel`'d, two samples (42407 fully,
67801/DoubleMuon fully) had already completed, and nothing was deleted.

### B2 — the normalisation registry and the tables

`studies/cms_mc_weights/cms_mc_normalisation.json` on
`feature/cms-mc-weights-v2` holds **12 records**; the tables
(`normalisation_table.csv`, `normalisation_table_v2.csv`) hold **25 rows**.
Both counts **VERIFIED BY RUNNING** (parsed the files out of the branch).

*In the registry* (record → sample, σ in pb, **UNVERIFIED** — these are the
registry's own values):

| Record | Sample | `cross_section_pb` | `sum_of_weights` |
|---:|---|---:|---|
| 42407 | LQToBMu_M-400_pair | 2.276 | `null` |
| 67801 | TTTo2L2Nu | 89.28 | `null` |
| 67993 | TTToSemiLeptonic | 367.86 | `null` |
| 35669 | DYJetsToLL_M-50 amcatnloFXFX | 5765.4 | `null` |
| 35671 | DYJetsToLL_M-50 madgraphMLM | 5765.4 | `null` |
| 64895 | ST_tW_top_5f_NoFullyHadronicDecays | 19.56 | `null` |
| 64839 | ST_tW_antitop_5f_NoFullyHadronicDecays | 19.56 | `null` |
| 72676 | WWTo2L2Nu | 12.178 | `null` |
| 72752 | WZTo3LNu_amcatnloFXFX | 5.218 | `null` |
| 75589 | ZZTo4L | 1.256 | `null` |
| 68187 | TTZToLLNuNu_M-10 | 0.2529 | `null` |
| 68073 | TTWJetsToLNu | 0.2043 | `null` |

Every record has `k_factor = 1.0` and `gen_filt_eff = 1.0`, and every
`sum_of_weights` is `null`. That last point matters: **the registry has never
carried a sum of weights at all**, so D4's "measure it from the Runs trees of
the files that actually succeeded" is not merely preferable to #35's
whole-sample metadata — for CMS it is the only available route.

*Tabulated but missing from the registry* — **13 records**:

| Record | Sample |
|---:|---|
| 35631 | DYJetsToLL_M-10to50_amcatnloFXFX |
| 35633 | DYJetsToLL_M-10to50_madgraphMLM |
| 75567 | ZZTo2L2Nu |
| 38428 | GluGluToContinToZZTo2e2mu |
| 38430 | GluGluToContinToZZTo2e2nu |
| 38432 | GluGluToContinToZZTo2e2tau |
| 38434 | GluGluToContinToZZTo2mu2nu |
| 38436 | GluGluToContinToZZTo2mu2tau |
| 38438 | GluGluToContinToZZTo4e |
| 38440 | GluGluToContinToZZTo4mu |
| 38442 | GluGluToContinToZZTo4tau |
| 37728 | GluGluHToZZTo4L_M125 |
| 68847 | VBF_HToZZTo4L_M125 |

(12 + 13 = 25, the full table. **VERIFIED BY RUNNING**.)

**The caveats, restated unchanged (all UNVERIFIED — quoted from the tables):**

1. **Portal σ includes matching/filter efficiency but NOT decay branching
   ratios** for samples whose decay is done by a separate Pythia/JHUGen step.
   The table marks these `"yes (R1, w.r.t. matching/filter — NOT w.r.t. decay
   BR)"` and applies the BR by hand: e.g. 37728 ggH→ZZ→4l applies
   `BR(H→llll, l = e/μ/τ) = 2.768e-4`; 67801 TTTo2L2Nu applies
   `BR(dilepton) = 0.10706`; 64895/64839 apply a selection factor `0.5456`
   for `NoFullyHadronicDecays`.
2. **The gg→ZZ portal values are ~1000× too large.** The table's note R3: the
   portal `total_value` is 1015–1031× the independently-referenced MCFM value
   for every one of the six charged-4-lepton final states that has a
   reference — "essentially a clean factor of 1000", i.e. a pb-vs-fb
   mislabelling for this record family. The row is marked **UNUSABLE AS
   LISTED** and `sigma_eff` uses the /1000-corrected value. This whole family
   is also absent from the registry.
3. **The ZZTo2L2Nu 42% discrepancy is unresolved.** Record 75567: the
   generator-level portal value 0.9738 pb against RazorAnalyzer's 0.564 pb, a
   42% correction where every other decay-in-ME diboson check in the table is
   5–15%. Excluded from the first production by the lead's decision; the three
   things that would resolve it are listed in the table's own `decision`
   field. Also absent from the registry.

### B3 — where "Z-peak data/MC agreement ~0.1% after NLO Drell-Yan" comes from

**Source:** `studies/cms_mc_weights/phase1/DIAGNOSIS.md`, section
*"(a) Truly inclusive Z-peak ratio (all jet counts, including 0)"*, line
**490**, on `feature/cms-mc-weights-v2` (identically on
`feature/cms-mc-weights-phase1`).

**The actual numbers** (**UNVERIFIED** — read from the document, not re-run):

| Configuration | Data | MC (weighted) | Ratio | ± stat |
|---|---:|---:|---:|---:|
| LO madgraphMLM + ttbar, 60–120 GeV | 9,053,171 | 9,431,620 | **0.960** | 0.0006 |
| NLO amcatnloFXFX + ttbar, 60–120 GeV | 9,053,171 | 9,040,863 | **1.0014** | 0.0009 |
| LO, 76–106 GeV | 8,648,738 | 9,026,691 | 0.958 | 0.0007 |
| NLO, 76–106 GeV | 8,648,738 | 8,633,277 | **1.0018** | 0.0009 |

So the figure is **1.0014 ± 0.0009**, i.e. **0.14% off unity** — the document's
own summary line (`DIAGNOSIS.md:608`) phrases it as "within 0.2%". "~0.1%" is a
rounding of 0.14%; it is not a separate number and there is no 0.1% result in
the file.

**Is it still meaningful under the new selection? Partly — and not as a
validation.**

* It was measured on a **DoubleMuon-only** population, with the old capped
  labels, the old Z cut and only **two** MC samples (DY + ttbar), using an
  independent from-scratch driver rather than the delivered selection code
  path. None of those are the delivered four-dataset Version B selection. As a
  statement about *the current selection*, it carries no weight at all.
* What **does** transfer is the **generator conclusion**: the comparison is a
  ratio of the same quantity computed two ways, and the LO/NLO gap (0.960 vs
  1.0014 inclusive; per-jet-count 0.92/1.19/1.31 vs ≈1.00 for 0/1/2 jets) is a
  property of the Drell-Yan sample, not of the lepton selection. That is why
  D10 keeps **35669 (amcatnloFXFX, NLO)** as the nominal DY pilot.
* The same document records two residuals that are **not** fixed by the
  generator choice and will reappear: a **≥3-jet excess of ≈29% even with NLO
  DY**, and a **generator-independent pileup mismatch** visible directly in the
  `PV_npvsGood` shape (0-jet data/MC of 0.68 / 1.11 / 1.71 across
  `PV_npvsGood ≤ 15 / 16–25 / > 25`). Both were measured, not corrected.

### B4 — `work/cms_mc_v2/` top level (`ls` only)

**VERIFIED BY RUNNING** (`ls -la`, nothing opened, nothing modified):

```
35669/  35671/  42407/  42407_test/  64839/  64895/  67801/
68073/  68187/  72676/  72752/  75589/
pilot_data_regression/   repo/
```

All 14 entries are directories, all `berkom:watlas`, timestamps 2026-09-30
16:31–16:38. **One honest inconsistency:** `v2/PAUSED.md` states that
35671, 64895, 64839, 72676, 72752, 75589, 68187 and 68073 had "no output
directories created"; top-level directories for all of them do exist. Their
contents were **not** inspected (this round is `ls`-only on that tree), so
whether they are empty skeletons or hold partial output is **not observed**.

---

## Part C — probing real MC NanoAOD files

**All of Part C is VERIFIED BY RUNNING.** Script
`studies/cms_mc_weights_v3/probe/probe_mc_records.py`, committed and pushed
before running, executed on the Weizmann analysis node `wipp-an1` under
`nice -n 10` from a checkout pinned to `964bc5a`, conda env
`/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline` (uproot 5.6.2,
numpy 2.4.6). Outputs:
`/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_design_20261010/probe_out_v2/`,
copied into `studies/cms_mc_weights_v3/evidence/probe_mc_records.json`.
Records probed: the 12 v2-registry records **plus 37728**. One file each
(portal file index 0), resolved through the repo's own
`studies/m0m1j0_cms/design_checks/common.py::fetch_file_list` — no URL was
typed anywhere. Total wall time for all 13 records ≈ 46 s.

### C1 — campaign: all 13 are UL16 **postVFP** NanoAODv9. No APV.

| Record | Portal dataset title | postVFP? |
|---:|---|---|
| 42407 | `/LQToBMu_M-400_pair_TuneCP2_13TeV-madgraph-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` | yes |
| 67801 | `/TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` | yes |
| 35671 | `/DYJetsToLL_M-50_TuneCP5_13TeV-madgraphMLM-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` | yes |
| 64895 | `/ST_tW_top_5f_NoFullyHadronicDecays_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM` | yes |
| 64839 | `/ST_tW_antitop_5f_NoFullyHadronicDecays_TuneCP5_13TeV-powheg-pythia8/…v17-v1/NANOAODSIM` | yes |
| 72676 | `/WWTo2L2Nu_TuneCP5_13TeV-powheg-pythia8/…v17-v1/NANOAODSIM` | yes |
| 72752 | `/WZTo3LNu_TuneCP5_13TeV-amcatnloFXFX-pythia8/…v17-v1/NANOAODSIM` | yes |
| 75589 | `/ZZTo4L_TuneCP5_13TeV_powheg_pythia8/…v17-v1/NANOAODSIM` | yes |
| 68187 | `/TTZToLLNuNu_M-10_TuneCP5_13TeV-amcatnlo-pythia8/…v17-v1/NANOAODSIM` | yes |
| 68073 | `/TTWJetsToLNu_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/…v17-v1/NANOAODSIM` | yes |
| 67993 | `/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/…v17-v1/NANOAODSIM` | yes |
| 35669 | `/DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/…v17-v1/NANOAODSIM` | yes |
| 37728 | `/GluGluHToZZTo4L_M125_TuneCP5_13TeV_powheg2_JHUGenV7011_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM` | yes |

Every title carries `RunIISummer20UL16NanoAODv9` with the
`106X_mcRun2_asymptotic_v17` global tag, and **none** contains `APV` or
`preVFP`. `records_not_postVFP` is empty. **Nothing to flag.** (The APV twin
would read `RunIISummer20UL16NanoAODAPVv9` with `…_preVFP_…`; the probe
classifies and flags that case explicitly, it just did not occur.)

### C2 — branch presence: nothing missing, on any record

`records_with_missing_branches` is **empty**. Present on all 13:

* every HLT path of the four acceptances —
  `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ`,
  `HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ`, `HLT_IsoMu24`, `HLT_IsoTkMu24`,
  `HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ`,
  `HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ`,
  `HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ` — **and**
  `HLT_Ele27_WPTight_Gsf`;
* `nTrigObj`, `TrigObj_pt`, `TrigObj_eta`, `TrigObj_phi`, `TrigObj_id`,
  `TrigObj_filterBits`;
* `genWeight`;
* `L1PreFiringWeight_Nom`, `L1PreFiringWeight_Up`, `L1PreFiringWeight_Dn`;
* `Pileup_nTrueInt`; `run`, `luminosityBlock`, `event`;
* a `Runs` tree carrying both `genEventSumw` and `genEventCount` (one entry
  per file in all 13).

**`run == 1` on all 13 records** (min = max = 1 over the probe window;
`records_where_run_is_not_always_1` is empty). This matters for D3 — see the
note there.

`L1PreFiringWeight_Nom` is a real, non-trivial correction: per-record mean
0.957–0.984, minimum 0.137–0.363, maximum exactly 1.0.
`Pileup_nTrueInt` spans 0–51 with a mean of 21.7–22.0 on every record.

### C3 — `TrigObj_filterBits` title: byte-identical in MC and data

The MC title's sha256 is
`0c79d6aa35c2be4ea2703de094367aaacd1f62c9209a67e4ee103d03687aab96` on **all 13
records**, and that is the same sha256 as the recorded data-file title in
`studies/cms_datasets/electron_prep/evidence/trigobj_titles_electron_datasets.json`
(itself identical across all 8 data (dataset, era) files).
`records_filterBits_title_differs_from_data` is **empty**.

The electron and muon portions, quoted verbatim from the title (identical
string in MC and data — one quote serves for both):

> `extra bits of associated information: 1 = CaloIdL_TrackIdL_IsoVL, 2 = 1e
> (WPTight), 4 = 1e (WPLoose), 8 = OverlapFilter PFTau, 16 = 2e, 32 = 1e-1mu,
> 64 = 1e-1tau, 128 = 3e, 256 = 2e-1mu, 512 = 1e-2mu, 1024 = 1e
> (32_L1DoubleEG_AND_L1SingleEGOr), 2048 = 1e (CaloIdVT_GsfTrkIdT), 4096 = 1e
> (PFJet), 8192 = 1e (Photon175_OR_Photon200) for Electron (PixelMatched
> e/gamma); 1 = TrkIsoVVL, 2 = Iso, 4 = OverlapFilter PFTau, 8 = IsoTkMu,
> 1024 = 1mu (Mu50) for Muon; …`

So every bit the four acceptances use means the same thing in MC as in data:

| Bit | Object | Meaning in the title | Used by |
|---:|---|---|---|
| 1 | muon | `TrkIsoVVL` | DoubleMuon |
| 2 | muon | `Iso` | SingleMuon |
| 16 | electron | `2e` | DoubleEG |
| 32 | electron | `1e-1mu` | MuonEG |
| 2 | electron | `1e (WPTight)` | SingleElectron candidate (`HLT_Ele27_WPTight_Gsf`) |

The id-guard title is also identical:
`ID of the object: 11 = Electron (PixelMatched e/gamma), 22 = Photon
(PixelMatch-vetoed e/gamma), 13 = Muon, 15 = Tau, 1 = Jet, 6 = FatJet,
2 = MET, 3 = HT, 4 = MHT` — so `id == 11` for electrons and `id == 13` for
muons hold in MC unchanged.

**Consequence for the design:** the runtime bit-meaning assertion
(`run_dataset_on_file.py:1800`, `assert_trigobj_bit_meanings`) will pass on MC
files with no change, and the MC path can keep it as-is rather than relaxing it.

### C4 — fired fractions and negative-weight fractions

Fired fraction over the probe window (10,000 events, or the whole file where
smaller). **VERIFIED as a count**; these are *not* physics efficiencies — no
golden JSON, no object selection, no matching, and MC trigger emulation is
not data (see the data/MC section).

| Rec | n probed | Mu17_Mu8_DZ | Mu17_TkMu8_DZ | IsoMu24 | IsoTkMu24 | Ele23_Ele12_DZ | Mu23_Ele12_DZ | Mu8_Ele23_DZ | Ele27_WPTight |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 42407 | 5,676 | 0.78224 | 0.84144 | 0.96970 | 0.96794 | 0.00035 | 0.04651 | 0.04246 | 0.01022 |
| 67801 | 10,000 | 0.10310 | 0.11150 | 0.38790 | 0.38390 | 0.08070 | 0.14710 | 0.16080 | 0.30490 |
| 35671 | 10,000 | 0.14940 | 0.15630 | 0.22490 | 0.22380 | 0.12430 | 0.00230 | 0.00240 | 0.16470 |
| 64895 | 10,000 | 0.03040 | 0.03330 | 0.26370 | 0.26270 | 0.02040 | 0.03450 | 0.04000 | 0.18940 |
| 64839 | 10,000 | 0.02670 | 0.02890 | 0.26690 | 0.26190 | 0.02270 | 0.03580 | 0.04000 | 0.19360 |
| 72676 | 10,000 | 0.06940 | 0.07140 | 0.32590 | 0.32250 | 0.05810 | 0.10050 | 0.10730 | 0.24960 |
| 72752 | 10,000 | 0.11170 | 0.11600 | 0.23170 | 0.23040 | 0.09130 | 0.06530 | 0.07080 | 0.18120 |
| 75589 | 10,000 | 0.14130 | 0.14840 | 0.18630 | 0.18470 | 0.10230 | 0.04090 | 0.05000 | 0.13000 |
| 68187 | 10,000 | 0.11430 | 0.12180 | 0.23760 | 0.23580 | 0.09330 | 0.06520 | 0.07490 | 0.20090 |
| 68073 | 9,451 | 0.07608 | 0.08264 | 0.30536 | 0.29986 | 0.06179 | 0.09597 | 0.10771 | 0.24992 |
| 67993 | 10,000 | 0.01330 | 0.01590 | 0.21720 | 0.21540 | 0.00700 | 0.01310 | 0.01820 | 0.16590 |
| 35669 | 10,000 | 0.13790 | 0.14260 | 0.20870 | 0.20710 | 0.11740 | 0.00290 | 0.00260 | 0.16080 |
| 37728 | 4,000 | 0.29900 | 0.30750 | 0.32775 | 0.32300 | 0.21250 | 0.09350 | 0.10975 | 0.23975 |

Every path fires on every record, so **no acceptance is starved of statistics
in any sample**, and the SingleElectron candidate path fires at 1–30%.

**Negative-genWeight fraction, over the WHOLE file** (not the probe window):

| Record | negative fraction | Generator |
|---:|---:|---|
| 68187 TTZToLLNuNu | **0.24760** | amcatnlo |
| 68073 TTWJetsToLNu | **0.21924** | amcatnloFXFX+madspin |
| 72752 WZTo3LNu | **0.16956** | amcatnloFXFX |
| 35669 DYJetsToLL_M-50 | **0.16336** | amcatnloFXFX |
| 75589 ZZTo4L | 0.00515 | powheg |
| 67801 TTTo2L2Nu | 0.00401 | powheg |
| 67993 TTToSemiLeptonic | 0.00395 | powheg |
| 37728 GluGluHToZZTo4L | 0.00375 | powheg2+JHUGen |
| 72676 WWTo2L2Nu | 0.00187 | powheg |
| 64895 ST_tW_top | 0.0000215 | powheg |
| 64839 ST_tW_antitop | 0.0 | powheg |
| 35671 DYJetsToLL_M-50 | 0.0 | madgraphMLM |
| 42407 LQToBMu_M-400 | 0.0 | madgraph (LO) |

Two structural facts that matter for the design, both **VERIFIED BY RUNNING**:

* On **12 of the 13** records, `|genWeight|` takes a **single value** over the
  probe window (`n_distinct_abs_values_capped_at_6 == 1`): the weight is
  `±w₀` with a fixed magnitude, only the sign varies. Example magnitudes:
  35669 `±25259.7`, 67993 `±303.358`, 67801 `±72.6983`, 37728 `±29.1721`,
  68187 `±0.49555`. The exception is 42407, which has ≥ 6 distinct magnitudes
  (range 4.66982–4.80083).
* **35671 (LO madgraphMLM DY) has `genWeight == 1` for every event**
  (min = max = 1, and `sum(genWeight)` equals the event count exactly). It is
  a unit-weight sample.

The first fact is why the negative-weight problem is a *counting* problem: in a
bin of an NLO sample, the content is `w₀ × (n₊ − n₋)` and goes to zero or
negative whenever `n₋ ≥ n₊`. See the data/MC section.

### C5 — whole-file `sum(genWeight)` vs that file's `Runs.genEventSumw`

**They agree on all 13 records**, to between `0` and `4.4e-8` relative —
i.e. float64 round-off on sums of up to ~2×10⁶ terms, not a physics
difference. `records_C5_disagreeing` is **empty**. The event count also
matches `Runs.genEventCount` exactly on all 13. So **no probed file carries a
pre-skim**, and `genEventSumw` is confirmed to be the sum of **`genWeight`**
specifically (not of `Generator_weight` or `LHEWeight_originalXWGTUP`, both of
which also exist in these files).

| Rec | events in file | `sum(genWeight)` | `Runs.genEventSumw` | rel. diff | `genEventCount` == n? | portal files |
|---:|---:|---:|---:|---:|---|---:|
| 42407 | 5,676 | 2.68509146e+04 | 2.68509145e+04 | 1.3e-09 | yes | 12 |
| 67801 | 136,000 | 9.80758269e+06 | 9.80758226e+06 | 4.4e-08 | yes | 49 |
| 35671 | 1,434,319 | 1.43431900e+06 | 1.43431900e+06 | 0.0 | yes | 61 |
| 64895 | 651,757 | 2.11468464e+07 | 2.11468464e+07 | 1.3e-09 | yes | 11 |
| 64839 | 45,342 | 1.47403219e+06 | 1.47403215e+06 | 3.2e-08 | yes | 10 |
| 72676 | 15,000 | 1.66292347e+05 | 1.66292349e+05 | 1.3e-08 | yes | 7 |
| 72752 | 457,263 | 3.87580586e+06 | 3.87580594e+06 | 1.8e-08 | yes | 31 |
| 75589 | 168,000 | 2.22533092e+05 | 2.22533091e+05 | 4.7e-09 | yes | 99 |
| 68187 | 25,000 | 6.25383619e+03 | 6.25383620e+03 | 1.6e-09 | yes | 42 |
| 68073 | 9,451 | 3.28043852e+03 | 3.28043862e+03 | 3.2e-08 | yes | 12 |
| 67993 | 1,233,000 | 3.71086923e+08 | 3.71086921e+08 | 5.6e-09 | yes | 138 |
| 35669 | 1,933,726 | 3.28869839e+10 | 3.28869841e+10 | 6.8e-09 | yes | 41 |
| 37728 | 4,000 | 1.15813237e+05 | 1.15813237e+05 | 2.3e-09 | yes | 8 |

The portal's own `number_files` equals the length of the resolved file list on
every record. **Note the extreme per-file size spread** — file index 0 holds
4,000 events for 37728 but 1,933,726 for 35669 — so per-file job sizing cannot
assume `total_events / n_files`.

**This result is the direct evidence that D4 is implementable:** `genEventSumw`
is per-file and exact, so summing it over exactly the files that succeeded
gives the right denominator without any whole-sample metadata.

---

## Part D — the design

The decisions in D1–D10 are **fixed defaults set by the technical lead**. They
are not re-opened here. Where this round's evidence bears on one, it is marked
either as a supporting note or, where it actually conflicts, as
**CONTRADICTED BY EVIDENCE**, with the decision left to Matan.

### D1 — Architecture

CMS MC runs through the **same study driver as data**,
`studies/cms_datasets/cluster/run_dataset_on_file.py --population matched4`,
via a new `--is-mc` mode, plus a new MC delivery builder alongside
`studies/cms_datasets/deliver/build_four_dataset_delivery.py`.

**PR #35 is not merged.** Its conventions are mirrored (`_mcEventInfo`,
`_mcEventWeight`, `_mcChannelNumber`, `_mcRunNumber`, `MCDatasetMetadata`'s
field names, the reserved `_mcw` suffix, the "identical masks on masses and
weights" rule) so that a later port is mechanical rather than a
re-derivation. Given the 13-file / 53-hunk conflict measured above, mirroring
rather than merging is the only way to avoid blocking this work on that merge.

**With `--is-mc` absent, data output must stay byte-for-byte identical.** Not
proved in this round — this round changes no code. The implementation round
must prove it against the existing delivered production outputs, read-only
(see the implementation plan). The precedent exists: the v2 branch did exactly
this proof for its own `--is-mc` addition
(`studies/cms_mc_weights/v2/compare_v2_data_regression.py`, and
`phase1/prove_default_preserving.py`), so the technique is known to work on
this driver.

### D2 — Event acceptance in MC

**No de-duplication.** The four-dataset veto order
(`DELIVERY_VETO_ORDER_4 = [DoubleMuon, SingleMuon, DoubleEG, MuonEG]`,
`run_dataset_on_file.py:269`) exists to stop a real event being counted twice
across four overlapping data streams. A simulated event exists once, so there
is nothing to de-duplicate. The inclusive/exclusive machinery
(`exclusive_mask_from_acceptances`, `attribute_to_exclusive_dataset`) is
therefore not applied to the MC population.

**An MC event is STORED if it passes ANY of the four data acceptances** —
using the identical code: `evaluate_four_acceptances`
(`run_dataset_on_file.py:1070-1088`) on post-overlap-removal objects, the same
`trigobj_best_match` with the same trigger-object id guard (electrons 11,
muons 13), the same bit meanings re-read from the file's own branch titles at
runtime (`assert_trigobj_bit_meanings`, confirmed in C3 to pass unchanged on
MC), the same `dR < 0.12` electron-muon overlap removal applied **before**
matching and before final-state assignment
(`EMU_OVERLAP_DR_MAX = 0.12`, `run_dataset_on_file.py:344`,
applied at `1802-1807`), the same DoubleEG rule (both matched electrons
offline `pT > 30`), the same MuonEG rule (path decision + ≥ 1 selected offline
muon, because the muon leg is unmatchable in 2016 NanoAOD, plus an electron
matched to bit 32 above the fired path's electron-leg threshold: 12 GeV for
`Mu23_Ele12_DZ`, 23 GeV for `Mu8_Ele23_DZ`,
`MUONEG_ELECTRON_LEG_PT_MIN_GEV_BY_PATH`, `run_dataset_on_file.py:325-329`),
the same Version B reject rule, the same exact labels and the same names.

**OR the SingleElectron candidate condition:** `HLT_Ele27_WPTight_Gsf` fired
**and** ≥ 1 selected electron (after overlap removal) matched to a `TrigObj`
with `id == 11`, `filterBits & 2`, `TrigObj_pt >= 27`.

**Stored per event:** the four acceptance flags, the `HLT_Ele27_WPTight_Gsf`
decision, and the **offline** `pT` of the leading Ele27-matched electron
(`-1` when there is none).

**Reason, restated:** an event passing *only* SingleElectron would otherwise
never be stored at all, and SingleElectron must later be addable without a new
full MC run. Storing the offline `pT` rather than a boolean is what makes the
still-undecided offline threshold (27 / 30 / 35 GeV — out of scope here)
a *re-reading* of the shards rather than a re-production.

**The CURRENT delivery builder uses only the union of the four flags.** The
Ele27 information is written and ignored until SingleElectron is decided.

*Supporting evidence from this round:* C2 confirms `HLT_Ele27_WPTight_Gsf` is
present on all 13 records, C3 confirms electron bit 2 means `1e (WPTight)` in
MC exactly as in data, and C4 shows the path firing at 1–30% per sample — so
the condition is computable and not statistics-starved anywhere.

### D3 — Storage

**In memory**, per-event MC information is a `"_"`-prefixed record mirroring
PR #35: `_mcEventInfo` with

* `_mcEventWeight` = `genWeight`;
* `_mcChannelNumber` = the **CERN Open Data record ID**, supplied by the driver
  from the job's `--record-id` argument, **never parsed from file names**;
* `_mcRunNumber` = `run`.

It is carried through every event mask exactly like the object collections
(`ak.Array[mask]` preserves all fields, which is what makes PR #35's alignment
argument work).

> **Note on `_mcChannelNumber`.** PR #35's handler docstring insists the
> dataset number "is never inferred from file names" and is read from the
> events. CMS cannot honour that: **VERIFIED BY RUNNING**, a CMS MC NanoAOD
> file carries no per-event dataset identifier of any kind (1504 branches
> scanned; the only match for any of
> `dsid|channel|sample|dataset|process|mcid|xsec|genId` was
> `LHEWeight_originalXWGTUP`, the LHE weight). Taking it from the job's own
> `--record-id` argument is not an inference from a file name — it is the
> job's declared input — but it *is* a deviation from #35, and it is listed
> as an open question for Yuval.

> **Note on `_mcRunNumber`.** **VERIFIED BY RUNNING: `run == 1` on all 13
> records.** In ATLAS, `mcRunNumber` selects the production campaign and hence
> the target luminosity (`MC_RUN_NUMBER_TO_CAMPAIGN`,
> `schemas.py:171-176`; `_campaign_of`, `mass_calculation_handler.py:288`).
> In CMS it is a constant and carries **no** information. Storing it keeps the
> record shape identical to #35's — which is the stated point of D3 — but it
> must never be used to drive campaign or luminosity logic. D5 fixes a single
> campaign anyway, so nothing depends on it. This is a note, not a
> contradiction of D3.

**In shards**, each mass signature gets **aligned sibling arrays written in the
same flush**, holding `genWeight`, `L1PreFiringWeight_Nom`, `Pileup_nTrueInt`,
an integer acceptance bitmask, and the Ele27-matched electron `pT`.

The suffix **`_mcw` is RESERVED** for the final normalised weight, exactly as
in PR #35, and is produced **only at build time**. Nothing the driver writes
ever uses it.

**Sibling naming — the proposal, and why.** Raw siblings use a single family:

| Suffix | Contents | dtype |
|---|---|---|
| `_mcraw_genw` | `genWeight` | float64 |
| `_mcraw_l1pf` | `L1PreFiringWeight_Nom` | float32 |
| `_mcraw_puntrue` | `Pileup_nTrueInt` | float32 (as stored in NanoAOD) |
| `_mcraw_acc` | acceptance bitmask (below) | uint8 |
| `_mcraw_ele27pt` | offline `pT` of the leading Ele27-matched electron, `-1` if none | float32 |

Acceptance bitmask, one bit per condition, in `DELIVERY_VETO_ORDER_4` order
followed by the candidate:

| Bit | Value | Condition |
|---:|---:|---|
| 0 | 1 | DoubleMuon accepted |
| 1 | 2 | SingleMuon accepted |
| 2 | 4 | DoubleEG accepted |
| 3 | 8 | MuonEG accepted |
| 4 | 16 | SingleElectron candidate (`HLT_Ele27_WPTight_Gsf` fired **and** a matched electron with `TrigObj_pt >= 27`) |

A separate `_mcraw_hltele27` is **not** needed: bit 4 already encodes "fired
and matched", and `_mcraw_ele27pt >= 0` distinguishes "matched" from "not".
The bare path decision is recoverable because an event with bit 4 unset and
`_mcraw_ele27pt == -1` either did not fire or had no matched electron — if the
reviewer wants the fire decision separable from the match, add a sixth bit
rather than a sixth array. **Flagged as a one-line choice for the
implementation round**, not decided here.

Justification for the `_mcraw_<field>` family:

1. **One regex alternative covers all of them.** `(?:_mcw|_mcraw_[a-z0-9]+)?$`
   is a single addition wherever a signature pattern must tolerate siblings —
   as against one alternative per field.
2. **No possible confusion with the final weight.** `_mcw` means "normalised,
   build-time, ready to fill"; `_mcraw_` means "raw, per-event, not yet
   normalised". A reader cannot mistake one for the other, and a build-time bug
   that read `_mcraw_genw` where it meant `_mcw` would be off by the whole
   normalisation factor and so immediately visible.
3. **It can never be histogrammed as data.** **VERIFIED BY RUNNING:** the
   histogram-grouping regex `_FS_([0-9emjgtb_]+)_IM_([emjgtb\d]+)$` does not
   match any `_mcraw_*` or `_mcw` name, because the trailing `_` breaks the
   `[emjgtb\d]+$` group. Siblings are structurally invisible to the histogram
   stage unless explicitly asked for.
4. **It does not collide with `_main` / `_outliers`.** Post-processing appends
   those *after* the signature, so a post-processed sibling reads
   `…_IM_m0m1_main_mcw` — PR #35's own spelling
   (`post_processing_pipeline.py:281,286`) — and `_mcraw_*` siblings follow the
   same shape.
5. Lowercase-with-underscore matches every existing signature token.

**How `prune_final_states_below_min_events` must treat siblings:** never
counted as events, removed together with their final state.

**Does the fork's current regex leave orphans? YES — VERIFIED BY RUNNING.**
`studies/cms_mc_weights_v3/probe/check_d3_sibling_pruning.py` builds a shard
with two final states — one at 10 events (below the ≥ 100 threshold) and one at
500 — each carrying its physics signature plus `_mcw`, `_mcraw_genw`,
`_mcraw_l1pf` and `_mcraw_acc` siblings, then calls the real
`prune_final_states_below_min_events(min_events=100)`. It removes
`_FS_0e_2m_5j_1b` and deletes that final state's physics signature, and leaves
**all four of its sibling arrays behind as orphans**:

```
job_tag_FS_0e_2m_5j_1b_IM_m0m1_mcraw_acc
job_tag_FS_0e_2m_5j_1b_IM_m0m1_mcraw_genw
job_tag_FS_0e_2m_5j_1b_IM_m0m1_mcraw_l1pf
job_tag_FS_0e_2m_5j_1b_IM_m0m1_mcw
```

The cause: fork master's pattern is the pre-#35, `$`-anchored
`r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)$"` (`services/storage/sqlite_shards.py:176`).
A sibling name does not match, so `continue` at line `213` fires before line
`220` can record it in `signatures_by_db_and_fs` — and the deletion loop
(`234-242`) can only delete what that dict holds. Per-suffix behaviour:

| Suffix | fork master regex | PR #35 regex | proposed fix | histogram grouping |
|---|---|---|---|---|
| (the physics signature) | matches | matches | matches | matches |
| `_mcw` | **no** | matches | matches | no |
| `_mcraw_genw` | **no** | **no** | matches | no |
| `_mcraw_l1pf` | **no** | **no** | matches | no |
| `_mcraw_puntrue` | **no** | **no** | matches | no |
| `_mcraw_acc` | **no** | **no** | matches | no |
| `_mcraw_ele27pt` | **no** | **no** | matches | no |

Note PR #35's regex fixes `_mcw` only; the raw siblings would orphan under #35
too. **The specified fix** (one line, data-behaviour-neutral because no data
signature ends in `_mcw` or `_mcraw_*`):

```python
pattern = re.compile(r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)(_mcw|_mcraw_[a-z0-9]+)?$")
...
final_state, combination, is_sibling = pattern.search(signature).groups()
if final_state not in counted_final_states and not is_sibling:
    ...                 # siblings never contribute to the event count
signatures_by_db_and_fs.setdefault((path, final_state), []).append(signature)
```

i.e. exactly PR #35's change with `_mcraw_[a-z0-9]+` added to the alternation.
The implementation round must add a regression test asserting zero orphans
after a prune — the check script above is already that test in embryo.

### D4 — Normalisation (build time)

```
w_event = genWeight
        × L1PreFiringWeight_Nom
        × (cross_section_pb × 1000 × k_factor × gen_filt_eff × L_fb) / sum_of_weights
```

with **`L_fb = 16.393`** (Run2016G 7.653 + H 8.740).

**`sum_of_weights` = the sum of the Runs-tree `genEventSumw` over EXACTLY the
files that processed successfully.** This is the deliberate CMS difference from
PR #35, which uses the whole-sample metadata value (A5, confirmed at
`fetcher.py:388`). Two independent reasons:

1. **It is the only correct denominator for a partial production.** If a
   sample's 99 files yield 97 successes, dividing by the whole-sample
   `sumOfWeights` under-normalises that sample by ~2% with no warning
   anywhere. PR #35 cannot detect this; `v2/PAUSED.md` is a concrete example
   of a production that stopped part-way through several samples.
2. **It is measurable and exact.** **VERIFIED BY RUNNING (C5):** on all 13
   probed files, `sum(genWeight)` over every event equals that file's own
   `Runs.genEventSumw` to ≤ 4.4e-8 relative, and the event count equals
   `Runs.genEventCount` exactly. And the v2 registry's `sum_of_weights` is
   `null` for all 12 records (B2) — there is no stored whole-sample value to
   use even if we wanted one.

**A file whose `sum(genWeight)` disagrees with its own `genEventSumw` is
excluded, and its Σw with it.** That test is the pre-skim detector: a skimmed
file would have fewer events than `genEventCount` and a smaller weight sum
than `genEventSumw`, so using its `genEventSumw` would inflate the denominator
and under-normalise the sample. Proposed tolerance: **1e-6 relative** — three
orders of magnitude above the largest round-off observed (4.4e-8) and far below
any real skim. Record the per-file numbers in the build metadata so the
tolerance can be revisited from data rather than from argument.

**Unknown record → hard error.** Equivalent to `require_metadata: true`, and
deliberately *without* PR #35's A4 gap: there is no code path in which an MC
file is stored unweighted after a warning. If a record is not in the registry,
or a file fails the Σw check, or a required sibling is missing, the build
aborts.

**The registry** is JSON in `MCDatasetMetadata` shape, **keyed by record ID**,
with provenance — i.e. the shape of
`studies/cms_mc_weights/cms_mc_normalisation.json` continued, extended with
the measured `sum_of_weights` and the list of files it came from.

**Which field carries the BR and the filter efficiency — explicitly, to stop
double counting.** In the v2 tables and registry:

* **`cross_section_pb` carries EVERYTHING**: the best theory production cross
  section at the chosen order, times the decay branching ratio where the decay
  is a separate generator step, times any generator-level selection factor.
  It is the table's `sigma_eff_pb` column. Examples (**UNVERIFIED**, from
  `normalisation_table_v2.csv`): 67801 `89.28 pb` = NNLO+NNLL ttbar × BR(dilep)
  0.10706; 37728 `0.013447 pb` = 48.58 pb (N3LO QCD + NLO EW ggH, YR4,
  mH = 125.00) × BR(H→llll) 2.768e-4; 64895 `19.56 pb` = NNLO tW 71.7/2 ×
  selection factor 0.5456.
* **`k_factor` is pinned to 1.0** and must never be set to anything else. The
  table's `k_factor` column (e.g. 1.214 for 67801, 1.683 for 37728) is the
  *ratio* `sigma_eff / generator_level_sigma`, recorded in `provenance` for
  audit. It is already inside `cross_section_pb`. Setting it again multiplies
  the correction twice.
* **`gen_filt_eff` is pinned to 1.0** for the same reason. The portal's
  matching/filter efficiency is already folded into the portal's own
  generator-level σ — and we do not use that σ, we use the theory reference —
  so there is no separate efficiency left to apply. Where a sample has a
  genuine generator-level decay filter (64895/64839 `NoFullyHadronicDecays`),
  its selection factor is inside `cross_section_pb` as above, not here.

So the formula's `× k_factor × gen_filt_eff` evaluates to `× 1 × 1` for every
CMS record, and the registry's `provenance` block is the only place the
ingredients appear separately. **This is a semantic difference from PR #35,
where the three fields are independent ATLAS metadata values**, and it must be
stated in the registry file itself so nobody later "fixes" `k_factor` from the
provenance block.

### D5 — Single campaign

**UL16 postVFP only.** Any APV/preVFP record is an error — it cannot be
normalised to the Run2016G+H luminosity, and its detector conditions do not
match.

Implementation: the registry carries the record's portal dataset title, and the
build asserts `RunIISummer20UL16NanoAODv9` present with neither `APV` nor
`preVFP`. **VERIFIED BY RUNNING (C1):** all 13 candidate records already
satisfy this; the check will not reject anything currently planned, it exists
to catch the mistake of adding an APV sibling record later (they exist for most
of these samples).

Corollary: `luminosity_by_campaign` is not used. `target_luminosity_fb` is the
single value 16.393, and `_mcRunNumber` plays no part (see D3).

### D6 — Post-processing

Follows PR #35's semantics exactly:

* identical boolean masks applied to masses and weights at every step;
* **Z cut 110 GeV** for same-flavour dilepton channels, unchanged from data;
* **peak removal on the WEIGHTED spectrum** (#35's `_find_rightmost_highest_peak(…, weights=warr)`);
* **bin-aligned split** on the shared grid (`_aligned_bin_edges`), on
  unweighted counts as in #35;
* **≥ 100 events per final state counted on RAW MC entries**, applied once, on
  the combined shards — i.e. on the `final_state_counts` table the driver
  already writes, with siblings never counted (D3);
* **weighted yields also reported** alongside the raw counts in the build
  metadata.

**Open question flagged, as instructed:** because the peak is found on the
weighted MC spectrum and on the unweighted data spectrum, **MC and data
histograms with the same name can be cut at different masses**. The names are
identical by design (D7), so a downstream consumer that assumes a common first
filled bin will be wrong. This is recorded in Open questions, not resolved
here.

*A second, related consequence worth the reviewer's attention:* with
`genWeight = ±w₀` of fixed magnitude (C4), the weighted spectrum of an NLO
sample is `w₀ × (n₊ − n₋)` per bin, so the *rightmost highest* weighted bin can
sit somewhere the unweighted maximum does not — which is precisely the effect
#35's comment at `post_processing_pipeline.py:263-265` invokes in favour of
weighted peak finding. The direction of the effect is as #35 argues; the
magnitude in our selection is unmeasured and belongs in the pilot.

### D7 — Output

**TH1D with Sumw2, names identical to data.** No name, binning
(fixed 10 GeV bins over 0–10000 GeV), or range changes.

**How Sumw2 is written via uproot.** The fork writes histograms without
PyROOT, through
`studies/m0m1j0_cms/histograms.py::to_writable_th1f` →
`uproot.writing.identify.to_TH1x`, currently with `fSumw2=None` and float32
contents (which is what selects TH1F). The weighted variant:

* bin contents `float64` of length `n_bins + 2` (ROOT's on-disk convention —
  index 0 underflow, last index overflow), which selects **TH1D**;
* `fSumw2` an explicit `float64` array of the **same** length `n_bins + 2`,
  holding `Σ w²` per bin;
* `fTsumw = Σ w`, `fTsumw2 = Σ w²`, `fEntries` = the **raw** entry count.

**VERIFIED BY RUNNING**
(`studies/cms_mc_weights_v3/probe/check_d7_sumw2_roundtrip.py`, uproot 5.6.2),
on a deliberately mixed-sign fill including a negative weight: the written
object reads back with `classname == "TH1D"`, bin contents equal to
`np.histogram(x, bins, weights=w)` exactly, `variances()` equal to
`np.histogram(x, bins, weights=w*w)` exactly, `errors()` equal to
`sqrt(Σ w²)` exactly, and `len(fSumw2) == n_bins + 2`. The negative-weight bin
read back with content `+1.0` from weights `(+2, −1)` and error
`sqrt(4 + 1) = 2.236` — content lowered, error raised, which is the correct
behaviour and the reason Sumw2 is mandatory rather than optional.

**Verification on read-back** (to be wired into the implementation round as a
hard assertion, the way `verify_written_th1f` already is for data): re-open
each written file, assert `classname == "TH1D"`, and assert
`errors() == sqrt(Σ w²)` recomputed from the shards for a sampled set of
histograms. An absent or zero-length `fSumw2` must fail the build, not warn —
a TH1D without Sumw2 silently reports `sqrt(content)` errors, which for
weighted contents is meaningless and, for a negative bin, undefined.

**Delivery format is an OPEN QUESTION for Maryna.** Proposed default:
**per-sample ROOT files plus one summed-SM file.** Per-sample files are the
only form that lets a background be re-weighted, excluded (e.g. ZZTo2L2Nu,
B2 caveat 3) or re-normalised without re-running anything; the summed-SM file
is what a BumpNet-style consumer actually wants to see against data. Both are
cheap to write in the same build, so the cost of offering both is one extra
file per build rather than a decision.

### D8 — Coverage cap

`COVERAGE_CAP_PER_SIGNATURE = 500_000` (`run_dataset_on_file.py:363`). When a
signature exceeds it, the driver keeps a random subsample —
`rng = np.random.default_rng(seed=0)`,
`pick = rng.choice(arr.size, size=COVERAGE_CAP_PER_SIGNATURE, replace=False)` —
and records `CAPPED::<signature> = "true_size=<n>"` in the shard metadata
(`run_dataset_on_file.py:1476-1484`).

**For MC:** the siblings are subsampled with **the same `pick` indices** (they
are aligned by construction, and `pick` is already materialised), and when the
cap triggers the kept entries' weights are scaled by
`f = true_size / kept = true_size / 500_000`, recorded in metadata as
`CAPPED::<signature> = "true_size=<n> scale=<f>"`.

Two notes for the reviewer:

* **The expected yield is preserved**: `Σ w' = f · Σ_kept w ≈ Σ_true w`.
* **The uncertainty correctly grows.** `Σ w'² = f² · Σ_kept w² ≈ f · Σ_true w²`,
  so the bin error is inflated by `√f` relative to the uncapped sample. That is
  the right answer — the information really was discarded — but it means a
  capped MC histogram carries a larger error than the full sample would, and
  that must be visible in the report rather than discovered later.
* The cap applies **per signature per file**, so the same final state can be
  capped in one file and not another; the scale factor is therefore per
  (file, signature) and must be applied before the per-file arrays are merged.

**How often it triggers must be reported** — per sample, per signature, with
`true_size` — in the build metadata and the pilot report. In the delivered data
production the driver already tracks `n_capped_signatures` and
`max_signature_size`; the MC build reuses both. The MC rate is **not observed**
yet: it depends on the MC equivalent luminosity per sample, and for the largest
sample (35669, ~1.9M events in a single file) it is plausible but unmeasured.

### D9 — What is and is not applied

**Applied:**

* `genWeight` — sign and magnitude, as read. (C4: magnitudes up to ±25259.7;
  negative fractions up to 24.8%.)
* `L1PreFiringWeight_Nom` — the nominal L1 prefiring correction. (C2: present
  on all 13 records; mean 0.957–0.984, minimum 0.137. A real few-percent
  effect, not a no-op.)

**Not applied, stored for later where possible:**

* **Pileup reweighting** — `Pileup_nTrueInt` is stored (`_mcraw_puntrue`), so a
  pileup weight can be applied at build time later without re-running the
  driver. B3's diagnosis found a real, generator-independent data/MC pileup
  mismatch, so this is the most likely next correction.
* **Lepton ID / reco / trigger scale factors** — not applied, and **not
  storable** as a stored input: they need the official per-object SF maps keyed
  on (pT, η), which are not in NanoAOD. What *is* implicitly preserved is that
  the selected objects' kinematics are recoverable only through a re-run, so
  adding these later **will** require re-processing. That asymmetry (pileup is
  addable, lepton SFs are not) should be understood before the full production.
* **b-tag scale factors** — same, with the extra wrinkle of the WP mismatch
  below. `btagWeight_CSVV2` and `btagWeight_DeepCSVB` exist in these files
  (**VERIFIED BY RUNNING**, from the branch scan) but are for the wrong
  taggers — our selection uses `Jet_btagDeepFlavB`.
* **JER** (jet energy resolution smearing) — not applied. B3 identified a
  low-pT jet migration effect that JER smearing is one candidate explanation
  for.

### D10 — Pilot samples for the next round

| Record | Sample | Role | Probe status |
|---:|---|---|---|
| 67801 | TTTo2L2Nu (powheg) | dominant top background | postVFP, all branches, C5 OK, 0.40% negative weights |
| 35669 | DYJetsToLL_M-50 amcatnloFXFX (NLO) | nominal Drell-Yan, per B3 | postVFP, all branches, C5 OK, **16.3% negative weights** |
| 37728 | GluGluHToZZTo4L_M125 | signal | postVFP, all branches, C5 OK, 0.38% negative weights |

All three **VERIFIED BY RUNNING** as UL16 postVFP NanoAODv9 with every required
branch present and `sum(genWeight) == genEventSumw`.

**37728 must be added to the registry** (it is tabulated but missing, B2). The
entry, taken from `normalisation_table_v2.csv` row 25 (**UNVERIFIED** — these
are the table's values, not re-derived here), with **BR(H→4l including tau)
applied** and the k-factor already folded in per D4:

```json
"37728": {
  "dataset_number": 37728,
  "cross_section_pb": 0.013447,
  "k_factor": 1.0,
  "gen_filt_eff": 1.0,
  "sum_of_weights": null,
  "physics_short": "GluGluHToZZTo4L_M125",
  "generator": "powheg2 + JHUGenV7011 + pythia8",
  "campaign": "RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2",
  "provenance": {
    "portal_total_value_pb": 28.87,
    "portal_value_is": "PRODUCTION ONLY -- the JHUGen decay card ZZ4l_withtaus.input is a separate step from the gg_H_quark-mass-effects POWHEG production gridpack",
    "reference_sigma_pb": 48.58,
    "reference_order": "N3LO QCD + NLO EW ggH production, LHC Higgs WG YR4, mH = 125.00 GeV",
    "reference_url": "https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV",
    "br_applied_description": "BR(H->llll, l = e/mu/tau), LHC Higgs WG BR table",
    "br_value": 0.0002768,
    "k_factor_from_table": 1.683,
    "cross_section_pb_derivation": "48.58 * 0.0002768 = 0.013447 pb -- order correction AND decay BR are both inside cross_section_pb; k_factor and gen_filt_eff stay 1.0 (see DESIGN.md D4)",
    "flag": "the production-level k-factor 1.683 is notably larger than the VBF sibling's 0.961; the residual gap against this specific POWHEG quark-mass-effects implementation is NOT explained. Carried forward as a flag, not resolved.",
    "table_row_source": "studies/cms_mc_weights/normalisation_table_v2.csv (feature/cms-mc-weights-v2), row recid=37728"
  }
}
```

`sum_of_weights` stays `null` in the registry and is filled by the build from
the Runs trees of the files that succeeded (D4).

**Pilot checks against data**, each with a PNG plot:

1. **Z peak in μμ and in ee** — separately, because the ee channel exercises
   DoubleEG, the electron trigger matching, the `pT > 30` rule and the overlap
   removal, none of which the v2/phase-1 muon-only work ever tested. This is
   the check that establishes whether B3's 1.0014 survives the new selection.
2. **Jet multiplicity** — on the exact labels, so the 5j/6j/… bins that the
   old capped labels hid are visible. B3's unresolved ≥ 3-jet ≈29% excess is
   expected to reappear here.
3. **e-μ spectrum** — the MuonEG channel, whose muon leg is unmatchable, so its
   data/MC behaviour is the least constrained of the four.

---

## Item-by-item comparison: this design vs PR #35

| Item | PR #35 (`fa63544`) | This design (CMS) | Must CMS differ? |
|---|---|---|---|
| **Cross-section source** | `atlasopenmagic.get_metadata(dsid)["cross_section_pb"]`, fetched at run time (`fetcher.py:379,387`) | A committed JSON registry keyed by **record ID**, with per-record provenance | **Yes.** atlasopenmagic has no CMS Open Data records; the CERN portal's own σ is production-only for decayed samples and, for the gg→ZZ family, off by ~1000× (B2 caveats 1–2). A value that needs a human decision and a citation per sample cannot be fetched. |
| **k-factor / filter efficiency** | Separate metadata fields `k_factor`, `gen_filt_eff`, each defaulting to 1.0 | **Pinned to 1.0**; both the order correction and the decay BR are folded into `cross_section_pb`; the ingredients live in `provenance` | **Yes**, as a semantic difference. The CMS numbers are derived per sample from a theory reference times a BR; there is no per-field CMS source to populate. Keeping the fields at 1.0 preserves #35's arithmetic exactly. |
| **Sum of weights** | Whole-DSID `sumOfWeights` from metadata (`fetcher.py:388`); unrelated to the files processed | Sum of `Runs.genEventSumw` over **exactly the files that succeeded**; a file failing the `sum(genWeight) == genEventSumw` check is excluded with its Σw | **Yes.** The CMS registry has no `sum_of_weights` at all (`null` on all 12 records), and #35's approach silently under-normalises a partial production. C5 shows the per-file value is exact. |
| **Luminosity** | `target_luminosity_fb` with an optional `luminosity_by_campaign` keyed on the MC run number | Single `L_fb = 16.393` (G 7.653 + H 8.740); no campaign map | **Yes.** `run == 1` in CMS MC (**VERIFIED**), so #35's campaign mechanism has no input. D5 fixes one campaign regardless. |
| **genWeight sign** | Used as read; `_event_weights` multiplies the raw value, negatives included (`im_pipeline.py:218-226`) | Identical — used as read, sign included | **No difference.** |
| **Weight alignment through the Z cut** | One boolean mask applied to both arrays (`post_processing_pipeline.py:252-259`) | Same | **No difference.** |
| **…through peak removal** | Peak found on the **weighted** spectrum; the resulting mask applied to both (`263-271`) | Same | **No difference.** |
| **…through the outlier split** | Split on **unweighted** counts; `main_mask` applied to both (`275-286`) | Same | **No difference.** |
| **Sumw2 / bin errors** | `ROOT.TH1D` + `hist.Sumw2()` via PyROOT (`histograms_pipeline.py:68-81`) | `uproot.writing.identify.to_TH1x` with float64 contents and an explicit `fSumw2` of length `n_bins + 2`; read-back asserted | **Yes, mechanically.** The fork's histogram path does not use PyROOT. The on-disk result is the same TH1D with the same `fSumw2` (**VERIFIED BY RUNNING**). |
| **Pileup** | Not applied, not stored | Not applied; `Pileup_nTrueInt` **stored** as `_mcraw_puntrue` | **Addition**, not a conflict. |
| **L1 prefiring** | Not applied (no such weight in ATLAS PHYSLITE) | `L1PreFiringWeight_Nom` **applied**; Up/Dn present and available | **Yes.** CMS-specific branch; a real few-percent effect (C2). |
| **Lepton / b-tag scale factors** | Not applied | Not applied | **No difference.** |
| **DSID ↔ record ID** | `_mcChannelNumber` read from the events' own `mcChannelNumber`, explicitly never from file names | `_mcChannelNumber` = the **record ID from the job's `--record-id`** | **Yes, unavoidable.** **VERIFIED BY RUNNING:** CMS NanoAOD carries no per-event dataset identifier (1504 branches scanned). Open question for Yuval. |
| **Metadata-missing policy** | `require_metadata` honoured on four paths but **not** on "no MC info at all" (A4) | Hard error on every path; no code route stores MC unweighted | **Yes**, deliberately. Fixes #35's A4 gap rather than inheriting it. |
| **Sibling pruning** | `(_mcw)?$` added to the prune pattern (`sqlite_shards.py:178`) | `(_mcw|_mcraw_[a-z0-9]+)?$` — #35's change plus the raw-sibling family | **Extension.** #35's regex alone leaves `_mcraw_*` orphans (**VERIFIED**). |
| **De-duplication** | n/a (ATLAS has no four-stream overlap) | **None** in MC; store on the OR of the four acceptances ∪ the SingleElectron candidate | **CMS-specific.** |
| **Coverage cap** | No such cap | Cap inherited from the data driver; weights scaled by `true_size / kept` and recorded | **CMS-specific** (study-local cap). |

---

## Every data/MC difference known at this point

1. **Trigger emulation fidelity.** MC HLT decisions come from an emulation of
   the 2016 menu, not from the online system. Path-level efficiencies and
   turn-on shapes do not match data to the accuracy the fired fractions in C4
   might suggest — those are counts, nothing more. The *bit meanings* and
   *object ids* are identical (**VERIFIED**, C3), so the matching logic is
   sound; the *rates* are not a data/MC comparison.
2. **No golden JSON in MC.** The data path applies
   `ValidatedRunsFilter` / `apply_validated_runs_filter`
   (`run_dataset_on_file.py:1664-1665`) against
   `Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt`. MC has no
   certified-run concept; `run == 1` throughout (**VERIFIED**). `--is-mc` must
   **skip** that filter — and must not silently pass every event through a
   filter that would reject them all. The data-side luminosity 16.393 fb⁻¹ is
   itself the *post*-golden-JSON number, so the MC normalisation is already
   consistent with the filtered data.
3. **Prescales.** Data paths can be prescaled; MC emulation has no prescale.
   The four delivered acceptances use unprescaled DZ/Iso paths, and the
   driver's own nested-reference prescale test exists for exactly this
   (`NESTED_REFERENCE_PAIRS`, `datasets_records.py:62-78`), but
   `HLT_Ele27_WPTight_Gsf` — the SingleElectron candidate — is one of the pairs
   under test, and its prescale behaviour in data is **not observed** by this
   round. It must be settled before SingleElectron is used quantitatively.
4. **MuonEG muon leg.** The muon leg cannot be trigger-matched in 2016 NanoAOD
   (`run_dataset_on_file.py:320-322`), so the MuonEG acceptance uses the path
   decision plus ≥ 1 selected offline muon. That approximation has a different
   efficiency in MC than in data, and nothing in the current design measures
   the difference. MuonEG is therefore the least-constrained of the four
   channels — which is why D10 makes the e-μ spectrum a pilot check.
5. **b-tag working point mismatch.** The selection uses
   `BTAG_DEEPFLAVB_MEDIUM_WP = 0.2598` (`studies/m0m1j0_cms/selection.py:64`,
   applied at `:243`). The documented UL16 **postVFP** DeepJet medium WP is
   **0.2489** (**UNVERIFIED** — a known open item; the group decision is
   pending). **MC must use the SAME 0.2598 as data** — this round changes
   nothing. The consequence to state plainly: both data and MC are then at a
   slightly tighter-than-nominal WP, which largely cancels in a data/MC ratio
   but means any b-tag efficiency or scale factor taken from an official
   0.2489 source will not apply as-is. Resolving the WP later changes both
   sides together.
6. **NLO negative weights → empty or negative bins.** **VERIFIED BY RUNNING:**
   negative-weight fractions of 16.3% (35669 DY NLO), 17.0% (72752), 21.9%
   (68073) and 24.8% (68187), with `|genWeight|` a single fixed magnitude per
   sample on 12 of 13 records. A bin's content is then `w₀ × (n₊ − n₋)`, which
   is **zero when `n₊ = n₋` and negative when `n₋ > n₊`** — both of which will
   occur in sparse tail bins, exactly where a bump hunt looks.
   **BumpNet's log-polynomial smoothing needs positive bins.** This is the
   single most likely practical blocker in the whole design. It is *not*
   addressed by anything in D1–D10 and is listed as an open question; the
   realistic options (wider bins for MC, a positivity floor, fitting the
   summed-SM histogram rather than per-sample ones, or quoting the MC
   uncertainty rather than the MC content) all change physics meaning and are
   not ours to pick.
7. **DY M-50 NLO MC luminosity is below the data luminosity.**
   **UNVERIFIED** (from `normalisation_table_v2.csv`): 35669 amcatnloFXFX has
   an MC-equivalent luminosity of **5.6437 fb⁻¹** against data's 16.393 fb⁻¹
   — a ratio of **0.344**. The LO twin 35671 gives ~14.3 fb⁻¹ (~0.87×) but is
   measurably wrong on normalisation and jet multiplicity (B3). So the nominal
   DY choice buys correctness at the cost of MC statistical error roughly
   `√(1/0.344) ≈ 1.7×` larger than data's in DY-dominated bins — worst exactly
   in the low-population tail bins where finding 6 also bites.
8. **Per-file event counts vary enormously.** **VERIFIED** (C5): file index 0
   holds 4,000 events for 37728 and 1,933,726 for 35669. Job sizing for the
   MC production cannot assume `number_events / number_files`.
9. **MC carries extra branches that must not be used by accident.**
   **VERIFIED:** `Generator_weight` and `LHEWeight_originalXWGTUP` also exist
   alongside `genWeight`, and `btagWeight_CSVV2` / `btagWeight_DeepCSVB` exist
   for taggers we do not use. C5 independently establishes that
   `Runs.genEventSumw` is the sum of **`genWeight`**, which is the branch
   PR #35 maps for `cms-nanoaod` — so the mapping is right, but the build
   should assert the branch name rather than rely on it.

---

## Open questions

Drafted, **not sent**.

### For Yuval (PR #35 author)

1. **The `require_metadata` gap (A4).**
   `mass_calculation_handler.py:217-222` warns and returns when a file has no
   `_mcEventInfo`, without checking `require_metadata`, while all four other
   failure paths raise. Downstream, the length mismatch makes
   `post_processing_pipeline.py:250` write the **whole merged signature**
   unweighted — losing the weights of the good files too, not just the bad
   one's. Is the asymmetry intentional (e.g. to tolerate a data file
   accidentally in an MC list)? If not, should that branch raise under
   `require_metadata`, and should the post-processing mismatch be a hard error
   rather than a warning?
2. **Subset normalisation (A5 / D4).** `sumOfWeights` is the whole-DSID value.
   For a partial production — which `v2/PAUSED.md` is a real example of — this
   under-normalises the sample by the unprocessed fraction, silently. We intend
   to sum the per-file `Runs.genEventSumw` over exactly the files that
   succeeded (**VERIFIED** to equal `sum(genWeight)` per file to ≤ 4.4e-8 on
   all 13 records we probed). Does ATLAS PHYSLITE expose a per-file equivalent
   we should be using the same way, and would you take the same change
   upstream?
3. **Weighted peak finding (A2).** `_find_rightmost_highest_peak` locates the
   peak on the weighted spectrum, with the stated reason that this is the
   distribution BumpNet sees. With CMS NLO samples the weighted spectrum can be
   zero or negative in a bin (16–25% negative weights, fixed `|genWeight|`), so
   "the rightmost bin equal to the maximum" can land on a statistical
   fluctuation of cancelling weights. Was the weighted choice load-bearing, or
   would you accept locating the peak on unweighted counts and applying the
   resulting mask to both?
4. **The raw-count ≥ 100 rule (D6).** We intend to apply the
   ≥ 100-events-per-final-state threshold to **raw MC entries**, not weighted
   yields, so the rule means the same thing in MC as in data. The side effect
   is that a final state can survive on 100 raw entries whose weighted yield is
   negligible (or, with negative weights, near zero). Is raw-count the
   intended semantics, and should a weighted-yield floor be added alongside
   rather than instead?
5. **The synthetic `_mcChannelNumber` (D3).** The handler docstring is explicit
   that the dataset number comes from the events and never from file names.
   CMS NanoAOD has no per-event dataset identifier at all (**VERIFIED**: 1504
   branches scanned; only `LHEWeight_originalXWGTUP` matched any identity
   pattern) and `run == 1` everywhere. We set `_mcChannelNumber` to the CERN
   Open Data **record ID** from the job's `--record-id` argument. Is reusing
   the `_mcChannelNumber` name for a non-DSID identifier acceptable, or would
   you rather see a distinct field so the contract stays "DSID or nothing"?
6. **Minor:** `config.yaml` ships `require_metadata: true` but
   `MCWeightingConfig` defaults it to `False` and `from_dict` reads
   `.get("require_metadata", False)`. A config omitting the key gets the
   permissive behaviour, opposite to the shipped intent. Intentional?

### For Maryna

1. **Delivery format.** Per-sample ROOT files, one summed-SM file, or both? We
   propose both as the default (D7): per-sample is the only form that allows a
   background to be re-weighted or excluded without re-running, and the summed
   file is what the bump hunt consumes.
2. **Negative and empty MC bins.** With NLO Drell-Yan at 16.3% negative weights
   (and up to 24.8% for TTZ/TTW), sparse tail bins will come out at zero or
   negative. If the smoothing needs positive bins, which trade-off do you want:
   a coarser MC binning, a positivity floor, using only the summed-SM
   histogram, or treating MC as an uncertainty band rather than a central
   value? This changes physics meaning, so it is yours to pick.
3. **MC statistical precision vs DY generator.** NLO DY (35669) gives the right
   normalisation and jet multiplicity but only ~0.344× the data luminosity;
   LO DY (35671) gives ~0.87× but is measurably wrong. Is 1.7× larger MC error
   in DY-dominated bins acceptable, or do you want both generators delivered so
   the choice can be made per-category?
4. **Which backgrounds are in the first MC delivery?** 12 records are in the
   registry; 13 more are tabulated but absent, including the whole gg→ZZ family
   (units problem, B2 caveat 2), ZZTo2L2Nu (42% discrepancy, caveat 3) and
   both Higgs records. Confirm the first-production list.
5. **The b-tag WP.** `0.2598` is used on both sides. The documented UL16
   postVFP DeepJet medium is `0.2489`. Nothing changes until the group decides,
   but the decision affects data and MC together and any official b-tag SF
   source will assume the nominal value.
6. **The ≥3-jet excess.** B3 measured ≈29% data/MC excess at ≥3 jets that NLO
   DY does **not** fix, and a generator-independent pileup mismatch. Should the
   pilot try to resolve these (pileup reweighting is the obvious first step,
   and `Pileup_nTrueInt` is stored for it), or report them and proceed?

---

## Implementation plan for the NEXT round

Not implemented now. No code outside `studies/cms_mc_weights_v3/` was touched
in this round.

### Steps and files

**Step 1 — `--is-mc` in the data driver.**
`studies/cms_datasets/cluster/run_dataset_on_file.py`.
Add `--is-mc` and `--record-id` is already there. When set:
skip `apply_validated_runs_filter` (difference 2); replace the per-dataset
trigger gate (`apply_trigger_requirement(..., own_paths)`, line `1669`) with
the OR over all four datasets' paths plus `HLT_Ele27_WPTight_Gsf`; read
`genWeight`, `L1PreFiringWeight_Nom`, `Pileup_nTrueInt` alongside
`BASE_OBJECT_BRANCHES`; build `_mcEventInfo` and carry it through every mask;
compute the five acceptance flags and the Ele27-matched electron `pT`; store
`keep = OR of the five` instead of `acceptances[dataset_label]["accepted"]`;
skip the exclusive/veto machinery entirely. **Every branch of this must be
behind `if args.is_mc`**, with the data path reached by exactly the same
statements as today.

**Step 2 — sibling arrays in the funnel.**
`run_dataset_on_file.py::run_combination_funnel` (around lines `1436-1490`).
After `combo_row_mask` and the NaN mask are applied and after the coverage cap
picks `pick`, write the five `_mcraw_*` siblings through the same
`writer_incl.append_array` call sequence, in the same flush. The three masks
that must be applied to siblings in order are: the final-state group mask, the
`combo_row_mask`, the `nan_mask`, and then `pick` if the cap fired.

**Step 3 — the prune regex fix.**
`services/storage/sqlite_shards.py:176` → the three-group pattern in D3. This
is the only shared-`services/` change in the plan. It is data-neutral because
no data signature can end in `_mcw` or `_mcraw_*`.

**Step 4 — the registry.**
New `studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json`: the 12 v2 records
plus 37728 (D10), keyed by record ID, each carrying the portal dataset title
for the D5 campaign assertion, `cross_section_pb` as σ_eff with `k_factor` and
`gen_filt_eff` pinned to 1.0, `sum_of_weights: null`, and the full provenance
block. A header comment stating the D4 no-double-counting rule.

**Step 5 — the MC delivery builder.**
New `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py`, mirroring
`studies/cms_datasets/deliver/build_four_dataset_delivery.py`. Responsibilities:
verify every processed file against the Σw check and accumulate
`sum_of_weights` per record over the survivors; compute `w_event` per entry;
write `_mcw` siblings; run the D6 post-processing with masses and weights in
lockstep; write TH1D+Sumw2 per sample and one summed-SM file; assert on
read-back; emit the metadata report (per-sample Σw, file counts, cap incidence
and scale factors, raw and weighted yields per final state, negative-bin
inventory).

### Tests

| Test | What it asserts |
|---|---|
| **Alignment property tests** | For a synthetic record with known values, every mask in the chain (final-state group → `combo_row_mask` → NaN → coverage-cap `pick` → Z cut → peak removal → outlier split) leaves `len(masses) == len(sibling)` and element `i` still describes event `i`. Property-based over random masks, not fixed examples, because the whole design rests on this. |
| **Data byte-identity regression** | Run the driver **without** `--is-mc` on a fixed set of already-delivered production files and compare the output shards byte-for-byte against the existing delivered outputs, **read-only** (never overwriting them). Precedent: `studies/cms_mc_weights/v2/compare_v2_data_regression.py` and `phase1/prove_default_preserving.py` on the v2 branch. |
| **Sumw2 read-back** | For each written file: `classname == "TH1D"`, `len(fSumw2) == n_bins + 2`, and `errors() == sqrt(Σ w²)` recomputed from the shards. Absent or zero-length `fSumw2` fails the build. Extend `studies/m0m1j0_cms/histograms.py::verify_written_th1f`. |
| **Orphan-sibling regression** | After `prune_final_states_below_min_events`, zero signatures remain for any removed final state. `check_d3_sibling_pruning.py` is this test already. |
| **Registry closure** | For each record: `cross_section_pb × 1000 × k × ε × L / Σw × Σ(genWeight)` equals the reported weighted yield, to float tolerance — the arithmetic-closure check the v2 branch called V1/V2. |
| **Campaign guard** | A record whose portal title contains `APV` or `preVFP` is rejected by the build (D5), tested against a real APV record id. |
| **Negative-bin inventory** | Not a pass/fail test: a report of how many bins per histogram are zero or negative, so open question 2 for Maryna can be answered with numbers. |

### Pilot plan and cluster resource estimate

Three samples (D10), full file sets, four datasets' worth of acceptances in one
pass each.

| Record | Portal files | Portal events | Basis |
|---:|---:|---:|---|
| 67801 TTTo2L2Nu | 49 | 43,546,000 | **VERIFIED** (portal API) |
| 35669 DYJetsToLL_M-50 NLO | 41 | 71,839,442 | **VERIFIED** |
| 37728 GluGluHToZZTo4L_M125 | 8 | 1,000,000 | **VERIFIED** |
| **total** | **98** | **116,385,442** | |

Estimate basis, stated so it can be checked rather than trusted: the v2 round
ran 49 files of 67801 as a PBS array of one job per file (**UNVERIFIED**, from
`v2/PAUSED.md`), so **one job per file, 98 jobs** is the known-workable shape.
Per-file wall time is **not observed** for the matched4 selection on MC; the
delivered data production's own per-file timings are the right input and were
not read this round. What this round *did* measure: reading one float branch
over every event of a 1.9M-event file via xrootd took **4.5 s** (**VERIFIED**),
so I/O is not the constraint — the combinatorial funnel over 186 combinations
is, and that cost is the same as the data side's per event.

Resource request shape (to be filled from the data production's measured
timings before submitting): 98 single-core jobs, one per file, the same memory
ceiling as the delivered data jobs, writing only under a new dated work
directory. **No batch job is submitted in this round.**

---

## Evidence index

Everything cited as VERIFIED BY RUNNING is reproducible from this branch.

| Artifact | What it is |
|---|---|
| `probe/probe_mc_records.py` | Part C probe. 13 records, one file each, read-only. |
| `probe/probe_dataset_identity_branches.py` | D3: dataset-identifier search in one MC and one data file. |
| `probe/check_a9_labels_and_rules.py` | A9: combinations, two-digit labels/names, acceptance-rule divergence. |
| `probe/check_d3_sibling_pruning.py` | D3: orphan siblings after a real prune, plus the per-suffix regex table. |
| `probe/check_d7_sumw2_roundtrip.py` | D7: weighted TH1 + Sumw2 through uproot, read back. |
| `evidence/probe_mc_records.json` / `.txt` | Part C results (cluster, pinned commit `964bc5a`). |
| `evidence/dataset_identity_branches.json` | D3 branch scan (cluster, pinned commit `8e997e8`). |
| `evidence/check_a9_labels_and_rules_out.json` | A9 results (local). |
| `evidence/check_d3_sibling_pruning_out.json` | D3 results (local). |
| `evidence/check_d7_sumw2_roundtrip_out.json` | D7 results (local). |
| `HANDOFF.md` | Commit, what was run where, where the cluster outputs are, how to resume. |

Cluster outputs (read-only, untouched thereafter):
`/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_design_20261010/`
