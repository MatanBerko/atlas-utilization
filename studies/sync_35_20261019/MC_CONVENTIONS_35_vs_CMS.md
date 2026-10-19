# MC weighting: upstream #35 (ATLAS) vs the CMS MC builder

**Read-only comparison. No code or convention was changed.** Every claim cites
the code. Numbers are labelled **VERIFIED BY RUNNING** or **UNVERIFIED**.

Code compared:

- **#35:** `upstream/master` = `7f2da5d` ("Final MC Weights Implementation").
  Paths are as in that commit.
- **CMS:** the MC builder on `feature/cms-mc-peakfix-20261018` = `24ecb7c`:
  `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py` (below "BMD"), and
  the MC version of `studies/cms_datasets/cluster/run_dataset_on_file.py`
  (below "driver-MC").

## In plain words

The CMS builder was designed from a pre-merge version of #35, and it follows
#35 on almost every step:

- the same normalisation formula, bit-identical on our 13 samples (VERIFIED);
- the same `_mcw` weight arrays;
- the same Z cut, max-mass cut, weighted peak removal and outlier split;
- the same raw ≥100 rule;
- the same TH1D + Sumw2 histograms.

The real differences are deliberate CMS choices that ATLAS has no equivalent
for:

- L1 prefiring;
- Σw measured from the files actually read, with a per-file check;
- the coverage cap;
- hard errors instead of skips.

On the key question (row 7): in ATLAS's standard MC chain, **the peak is found
on the combined spectrum of all MC samples in the run**. That is exactly
what the CMS `--peak-scope combined` default does.

## Comparison table

| # | step | #35 (ATLAS) | CMS builder | same? | to align CMS, and does any number change? |
|---|---|---|---|---|---|
| 1 | per-event weight formula | `w = w_gen × σ[pb]·1000·k·ε·L / Σw`. Normalisation in `services/calculations/mc_weights.py:32-61`; applied per event as `weights * norm` in `services/pipelines/im_pipeline.py:202-226` | `w = genWeight × L1PreFiringWeight_Nom × σ_eff·1000·k·ε·L / Σw`: `normalisation_factor` BMD:327-338, `w = g * p * norm` BMD:374. Times the D8 cap scale where a signature was capped (BMD:376-380) | **Same formula, except two CMS-only factors**: L1 prefiring and the cap scale. The normalisation arithmetic is the same: `compute_normalization` and BMD give **bit-identical** factors (13 records × 1,000 Σw = 13,000 / 13,000 identical; VERIFIED BY RUNNING, `norm_probe.py`) | Dropping prefiring would change every MC weight by the event's prefiring factor (typically a few %, UNVERIFIED). **Not recommended**: prefiring is a CMS detector correction with no ATLAS counterpart. The cap scale only restores the expected yield of subsampled signatures, so it must stay. |
| 2 | source of σ, k, ε | ATLAS Open Data metadata via `atlasopenmagic.get_metadata` (`services/metadata/fetcher.py:357-419`). k and ε default to 1.0 when absent (fetcher.py:399-407) | CMS registry `studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json` (BMD:123, 141-145). σ_eff already contains k and ε, and **k = ε = 1 is enforced** as a hard error (BMD:327-336) | different source, same role | No equivalent metadata service exists for CMS Open Data. The registry could be expressed as #35's `MCDatasetMetadata` (`domain/metadata.py`) without changing any number. |
| 3 | source of Σw | `sumOfWeights` from the dataset metadata (fetcher.py:389), i.e. the published total of the whole dataset. Not checked against the files actually read | Measured per file from `Runs.genEventSumw` and summed over the **surviving** files. Per-file check: \|Σ genWeight − genEventSumw\| / genEventSumw ≤ 1e-6, and a failing file is excluded with its Σw (BMD:214-262; driver-MC:1261-1300) | **different** | Using a whole-sample Σw would make CMS wrong whenever a file is excluded or not read. Today ZZ (75589) uses 98 of 99 files, so a metadata-style Σw would lower ZZ by about the excluded file's share, ≈1% (UNVERIFIED). **Do not align.** CMS is the more careful of the two. |
| 4 | negative weights | Kept signed and added as they are. No special handling (im_pipeline.py:202-226; histograms Fill with weight, `services/pipelines/histograms_pipeline.py:89`) | Kept signed. A negative/empty-bin **inventory** is reported, and no fix is applied (BMD:49, 787-788, 923) | **same** treatment; CMS also reports | none |
| 5 | where weights are attached, and naming | At mass calculation: one `<signature>_mcw` array per invariant-mass array (`im_pipeline.py:24`, `_accumulate_invariant_mass`; written only when `mc_weighting_enabled`, im_pipeline.py:193) | The per-file driver stores raw ingredients as siblings: `_mcraw_genw`, `_mcraw_l1pf`, `_mcraw_puntrue`, `_mcraw_acc`, `_mcraw_ele27pt` (driver-MC:343-350). The builder computes `_mcw` at build time with the **same name** (BMD:341-395) | **same final name** (`_mcw`); different time of computation | none. The CMS way lets σ or L change without re-running the per-file jobs. |
| 6 | Z cut / max-mass cut / outlier split | One boolean mask per step, applied to masses and weights together: Z cut + max mass (`post_processing_pipeline.py:252-261`), split on **unweighted** counts (`_main_array_mask`, :397-432; used at :275). On a mass/weight length mismatch it **warns and writes unweighted** (:244-250; histograms_pipeline.py:387) | Identical semantics as masks (BMD:396-466, 502-565): the same shared `_dilepton_flavor`, `_aligned_bin_edges`, Z_PEAK_CUTOFF and MAX_MASS_CUTOFF, and the split also on unweighted counts (BMD:430-458). A mismatch is a **hard error** (BMD:512-515) | **same cuts**; different failure policy | none for the numbers. The failure policy is a choice; CMS's is stricter. |
| 7 | peak finding, and **how several samples are combined** | Peak on the **weighted** spectrum (`post_processing_pipeline.py:266`, `_find_rightmost_highest_peak(..., weights=warr)`). Combination: see the section below. **All MC samples of a run are pooled per final-state/combination key before the peak is found.** | Weighted peak by default (`--peak-on weighted`, BMD:406-427). `--peak-scope combined` (default since 18 Oct, BMD:980, 748-770): the peak and split mass of each histogram name are found **once on all samples together** (`combined_cuts`, BMD:470-500) and applied to every sample | **same** (ATLAS standard chain = CMS combined) | none |
| 8 | ≥100 events per final state | **Raw** entries; `_mcw` rows are not counted (`services/storage/sqlite_shards.py:178, 217`). Applied once in post-processing over all IM shards in the job (`post_processing_pipeline.py:167`). In non-batch runs a raw pre-count on the parsed files is also applied (`mass_calculation_handler.py:338-369`) | **Raw** by default (`--min-events-basis raw`), applied **once on the combined shards of every surviving file of every sample** (BMD:700-706), with a CMS copy of the shared prune (`deliver/cms_shard_pruning.py`). The copy exists because CMS shards also carry `_mcraw_*` siblings, which #35's pattern `(_mcw)?` does not know | **same rule**, different implementation | Keep the CMS copy. #35's prune would leave `_mcraw_*` siblings as orphan rows. CMS's own tripwire test now fails against #35, by design: `test_cms_shard_pruning_drift.py`, 2 of 4 checks fail ("upstream function changed"), VERIFIED BY RUNNING. Its baseline must be re-recorded when the MC branch is synced with #35. No number change. |
| 9 | histogram filling and output layout | `TH1D` + `Sumw2()` when any `_mcw` exists, `Fill(mass, w)` (histograms_pipeline.py:68-89, 262). Data stays TH1F. **One set of histograms for the whole run** (all DSIDs mixed); the DSID is not kept after mass calculation | TH1D with an explicit `fSumw2`, checked on read-back (`deliver/weighted_histograms.py:88-190`). Output: **one file per sample plus the summed SM file** (`--output-mode both`, BMD:993). Names are identical to data | **same histogram type**; CMS also writes per-sample files | none. Per-sample files are extra information. |
| 10 | missing metadata / `require_metadata` | The final #35 has **no `require_metadata` option** (the pre-merge version described in `DESIGN.md` A4 had one). Missing σ/Σw, no generator-weight branch, no DSID, or an unknown campaign → `RuntimeError`, run aborted (`mass_calculation_handler.py:236-281`, re-raised at :160). **But** a file with no MC info at all is **skipped with a warning** (:222-227). A file with an empty weight vector is **skipped** (`file_parser.py:660`). | Hard error on every path: unknown record, record not in the full run, wrong campaign, missing siblings, alignment (BMD:141-176, 355-373, 819-858) | **different** | No CMS change. Note for ATLAS: when a file is skipped, its events vanish while the metadata Σw still counts them, so that sample comes out under-normalised (UNVERIFIED). |
| 11 | luminosity | One `target_luminosity_fb`, **or** `luminosity_by_campaign`, with the campaign read from each event's MC run number (`domain/config.py:237-290`; `mass_calculation_handler.py:282, 292-309`; `services/parsing/schemas.py:176-181`) | One L = 16.393 fb⁻¹ (Run2016G+H, BMD:117-119), plus a campaign guard: UL16 postVFP only (BMD:147-161) | **equivalent** for a single campaign | none (CMS has one campaign) |
| 12 | anything else | ATLAS only: several DSIDs per file, read per event (`domain/events.py` `dsids_in_events`, `_concatenate_events`); release-scoped metadata; optional histogram-level peak removal on (weighted) content (`histograms_pipeline.py:118, 680`, off by default); weighting off by default, which leaves output identical. `schemas.py:150` lists `cms-nanoaod: genWeight`, but there is no CMS dataset-number branch, so #35 weighting on CMS files would abort with "no dataset number" (UNVERIFIED). | CMS only: L1 prefiring; the D8 coverage cap with weight scale (driver-MC:1816-1840); the per-file Σw check; the event union of the four data acceptance flags (BMD:566-571); the campaign and `in_full_run` guards; per-sample outputs; the negative-bin inventory. **Neither** applies pileup reweighting (CMS stores `Pileup_nTrueInt` as `_mcraw_puntrue` but does not use it) or object scale factors | — | none required |

### Row 7 in detail: how ATLAS combines several samples before peak removal

**Answer: combined, like CMS `--peak-scope combined`. Never per DSID.**
Confidence: **high** for the code path and for the standard `submit_mc.sh`
chain; **medium** for what the ATLAS group actually runs, because that depends
on how they launch jobs.

1. **Several DSIDs share files and arrays.** Parsing concatenates events from
   many input files into each parsed chunk. `_concatenate_events`
   (`domain/events.py:86-…`) merges the MC info of files with different DSIDs.
   `dsids_in_events` returns all DSIDs in a file, and the weight of each event
   is looked up from its own `mcChannelNumber` (`im_pipeline.py:202-226`). So
   one invariant-mass array can hold several DSIDs' masses.
2. **No DSID in the signature.** Each mass array is named
   `<parsed file>_FS_<fs>_IM_<im>` (`prepare_im_combination_name`,
   im_pipeline.py:350). Nothing in the name identifies the DSID.
3. **Post-processing pools across files.** It groups every signature by its
   `_FS_…_IM_…` part, stripping the file/batch prefix
   (`post_processing_pipeline.py:203-208`). It then concatenates all chunks of
   that key from every IM shard it was given (:212-237), before the Z cut and
   the weighted peak (:252-266).
4. **The standard MC submission runs ONE post-processing job over the whole
   run.** `submit_mc.sh:80-101` runs `--tasks post_processing` after all batch
   jobs, on the run directory, so every batch's `im_batch_N.sqlite` is pooled.
   The peak is therefore found on the weighted sum of **all MC DSIDs in the
   run** — the same as CMS `--peak-scope combined`.
5. **Exception (medium confidence).** If a single `main.py` run does all stages
   inside each batch job, with `total_batch_jobs > 1`, post-processing only
   receives that batch's shard (`post_processing_handler.py:46-58`,
   `file_list = context.im_files`). The peak would then be per **batch** of
   files: neither per DSID nor global. `submit_mc.sh` does not do this.
6. **"Combined" means the run's MC samples, not data + MC.** README (#35)
   states weighting is meant for MC-only runs.

The grouping key is the same on both sides. ATLAS cuts per `_FS_…_IM_…` key
and names the histogram afterwards; CMS groups by BumpNet name first (BMD:815-830).
Both use the same name conversion, which is a pure reformat of (fs, im)
(`histograms_pipeline.py:474-…`; CMS copy `studies/m0m1j0_cms/histograms.py:125-140`).
So the two groupings are the same.

## Could the CMS builder reuse #35's functions without modifying upstream?

| #35 function | could replace | benefit | risk | verdict |
|---|---|---|---|---|
| `mc_weights.compute_normalization` + `domain.metadata.MCDatasetMetadata` | BMD `normalisation_factor` arithmetic | one shared formula; **bit-identical** on our samples (VERIFIED, 13,000 / 13,000) | very low. The CMS k=ε=1 guard and the Σw choice stay in CMS code | **yes, if wanted** |
| `post_processing_pipeline._find_rightmost_highest_peak(…, weights=)` | BMD `find_peak_mass` (a reimplementation made before #35 was merged) | removes a copy. With weights=None the arithmetic is already asserted equal by the CMS tests | it is a private (`_`) upstream function and could change silently; a tripwire test like the prune one would be needed | **yes, with a tripwire test** |
| `_z_peak_mask` | BMD `z_peak_keep_mask` | removes a copy | same as above | optional |
| `_main_array_mask` | BMD `main_split_mask` | partial. CMS `combined_cuts` needs the split **mass** to apply it to other samples, which #35 does not return, so `split_mass` must stay | low | optional, small gain |
| `sqlite_shards.prune_final_states_below_min_events` (#35 version) | `cms_shard_pruning.py` | — | **would leave `_mcraw_*` orphan rows**; #35 knows only `_mcw` | **no** (only possible if upstream generalised its pattern, which is an upstream change, out of scope) |
| `histograms_pipeline` weighted fill | `weighted_histograms.py` | — | needs PyROOT and fills per entry (slow); CMS writes with uproot | **no** |
| `MetadataFetcher.fetch_mc_metadata`, `im_pipeline._event_weights` | — | — | ATLAS metadata / DSID-keyed. No prefiring term | **no** |

## Recommended alignments for Matan to decide (nothing implemented)

1. **Required before fork master can take #35:** adapt the CMS per-file
   driver to #35's new 3-value return of `_calculate_combination_invariant_mass`.
   That means 2 call sites: `run_dataset_on_file.py:1451` on master, `:1786`
   on the MC branch. Then repeat the OLD-vs-NEW proof (Part 1d). This is a
   CMS file change; upstream files stay untouched.
2. **Keep** CMS's measured Σw with the per-file check, L1 prefiring, the
   coverage-cap weight scale and the hard-error policy. ATLAS has no
   equivalent, and aligning would make CMS less correct.
3. **Optional:** reuse `compute_normalization` (bit-identical, VERIFIED) and
   `_find_rightmost_highest_peak(weights=)`, each guarded by a tripwire test.
4. **When the MC branch is synced with #35:** re-record the
   `cms_shard_pruning.py` drift baseline against #35's prune (the test fails
   now, by design), and keep the CMS copy for `_mcraw_*` siblings.
5. **No change needed** for row 7: CMS `--peak-scope combined` matches
   ATLAS's standard MC chain.
6. **A question for Yuval, not an action:** #35 skips files with no MC info or
   an empty weight vector while still normalising with the metadata's full Σw.
   Is that intended?
