# sync/upstream-safe-16 — verification against the H->ZZ->4l analysis path

Branch `sync/upstream-safe-16`, cut from `master` (`0ae86dc`), contains exactly
the 16 commits listed below, cherry-picked in this order from
`sync/upstream-2026-09` (already-adapted versions, not upstream's originals).
All 16 applied with **no conflicts requiring a judgement call** — a few
auto-merged without any manual intervention; none touched a line in a way
that required choosing between two different physics behaviours.

This document checks each commit against the H->ZZ->4l analysis path
specifically, as requested. Two facts about that path, confirmed directly
from its own files (read via `git show`, branch never checked out or
modified), make most of this straightforward:

1. **`config.cms_higgs_4lepton_fullscale.yaml`: `do_mass_calculating: false`,
   `do_post_processing: false`, `do_histogram_creation: false`.** The
   H->ZZ->4l pipeline run does **parsing only**. The generic mass-calculation,
   post-processing, and histogram-creation stages never execute for this
   analysis — confirmed from the config file's own `tasks:` block and its own
   comment: "the generic mass-calculation stage is impractically slow at this
   scale."
2. **The three H->ZZ->4l analysis scripts
   (`scripts/higgs_4lepton_zz_report.py`, `..._clean_report.py`,
   `..._partB_report.py`) import nothing from `services.*` or
   `orchestration.*`** — checked directly, their only imports are
   `argparse`/`csv`/`json`/`sys`/`pathlib`/`numpy` and each other. They
   compute the invariant mass and produce the final histogram entirely
   independently, reading `parsed_data/*.root` directly.

So the *only* way any of these 16 commits can affect the H->ZZ->4l result is
by changing what the **parsing** stage writes to `parsed_data/*.root`.

## Per-commit verification

| # | Commit | Touches a listed file? | Verdict |
|---|---|---|---|
| 1 | `576fc45` FIx silent file parsing bug | `file_parser.py` | **No effect.** Guards `obj_events.pop("DirectObjects")` with an existence check. H->ZZ->4l's schema (`cms-nanoaod`) always declares `direct_objects` (`NANOAOD_BTAGGING_OBJECTS = ["Jet_btagDeepFlavB"]`), so `DirectObjects` was always present before this fix too — the guard only changes behaviour for a schema with empty `direct_objects`, which `cms-nanoaod` is not. |
| 2 | `47767e8` Fix division-by-zero in DL1d calculation | `file_parser.py` | **No effect.** Only inside the `elif "BTagging_AntiKt4EMPFlowAuxDyn.DL1dv01_pb" in ...` branch of `_calculate_btagging_and_split` — the ATLAS DL1d code path. CMS data (H->ZZ->4l) takes the earlier `if "Jet_btagDeepFlavB" in ...` branch instead; the DL1d branch is unreachable for this analysis regardless of `enable_jet_tagging`. |
| 3 | `981edaf` Fix key error upon b-tagging | `file_parser.py` | **No effect on a normal run.** Adds an early-return guard in `_calculate_btagging_and_split`, only reachable at all `if enable_jet_tagging` (H->ZZ->4l's config does not enable it — not present in its `parsing_task_config`). Even if it were enabled, `Jets`/`DirectObjects` are always present for a well-formed CMS parse, so the guard's new branch is never taken. |
| 4 | `831f0a0` Fix bug in MC/data selection | `orchestration/handlers/parsing_handler.py` (not on the requested list, checked anyway) | **No effect.** H->ZZ->4l uses `specific_record_ids` (not `release_years`) and `parse_mc: false`, with no `_mc`-suffixed keys in play; the rewritten selection logic passes `record_*` keys through unchanged exactly as the old code did — same reasoning as verified for m0m1j0 in the prior triage. |
| 5 | `cb98d79` fix: apply final-state thresholds across all chunks | `mass_calculation_handler.py`, `sqlite_shards.py` — **not** on the requested list | **No effect.** Both files belong to the mass-calculation stage, which never runs for H->ZZ->4l (`do_mass_calculating: false`). |
| 6 | `6db979c` fix: aggregate final-state thresholds across batch shards | `domain/config.py`, `mass_calculation_handler.py`, `post_processing_handler.py`, **`services/pipelines/post_processing_pipeline.py`** (on the list), `sqlite_shards.py` | **No effect.** `post_processing_pipeline.py` is only invoked via `PostProcessingHandler`, which never runs (`do_post_processing: false`). |
| 7 | `5730656` fix: count final states before combination cuts | `mass_calculation_handler.py`, `sqlite_shards.py` | **No effect** — mass-calc stage, never runs. |
| 8 | `8688323` test: verify global final-state thresholds | `sqlite_shards.py`, new test file | **No effect** — same stage, plus this is test-only code. |
| 9 | `98ac37d` fix: make parse_mc select the requested dataset mode | `parsing_handler.py` | **No effect** — same reasoning as #4 (this is that same fix's follow-up commit); H->ZZ->4l's `record_*` keys pass through both versions identically. |
| 10 | `2bef2e6` fix: enforce required parsing selections | **`services/calculations/physics_calcs.py`** (on the list) | **No effect, verified against the actual config, not assumed.** H->ZZ->4l's `kinematic_cuts` (config lines ~153-159) sets only `pt_min`/`eta_max` for electrons/muons and explicitly documents "No isolation, no ID (looseId/cutBased)" at parse time — `rel_isolation_max` is never configured, so the new exception-raising branch for missing isolation fields is never reached. `pt`/`eta` are core NanoAOD fields always present on Electrons/Muons, so their new exception branches aren't reached either. `particle_counts` for electrons/muons use `min: 0` everywhere in this config (global and every per-record override), so the new "reject all events if a required collection is entirely missing" branch (`required_min > 0`) never activates even in a hypothetical missing-collection scenario. Three independent reasons this is inert for H->ZZ->4l, not one. |
| 11 | `1706483` fix: split legacy combined leptons by flavor | **`file_parser.py`, `schemas.py`** (both on the list) | **No effect.** `_split_combined_leptons` only activates for release keys `"2016e-8tev"`/`"2025e-13tev-beta"` (checked in the function body); the `schemas.py` hunk only edits those same two `RELEASE_SCHEMAS` entries. H->ZZ->4l is exclusively `cms-nanoaod`. |
| 12 | `40fafba` fix: preserve events before partial ROOT read failure | `file_parser.py`, `threaded_processor.py` (on the list) | **No effect on a clean run; behaviour differs only if a batch read genuinely fails mid-file.** Under normal operation `read_error` stays `None` and every line executes identically to before. If a batch *does* fail (network blip, corrupt basket) mid-file, the new code stops at that point (keeping only the prefix, raising `PartialFileReadError`, and having the file correctly counted as failed) instead of the old code's `continue` (skip just that batch, keep reading later batches, and the file silently counts as a full success). This is the one commit where I can't promise "zero effect" unconditionally — only "zero effect unless a mid-file read failure occurs," in which case the new behaviour is more correct (an honest partial failure) but could retain a *different* — likely smaller — set of events than the old silent-skip behaviour would have for that one file. No H->ZZ->4l run has hit this path in this repo's history that I can see logged. |
| 13 | `0e557d9` fix: use native uproot source for XRootD | **`file_parser.py`, `schemas.py`** (both on the list), new `root_io.py` | **No effect on parse output.** Pure plumbing: changes *how* a ROOT file is opened over the network (a different uproot backend, addressing a known handle-cache race condition), not what gets read from it. The `schemas.py` hunk only touches `extract_schema_from_record_id`, a function that (checked with a repo-wide grep) is **never called anywhere** in the actual pipeline — dead code as far as any real run is concerned. |
| 14 | `a4f58cf` fix: persist pipeline timing statistics | `mass_calculation_handler.py`, `post_processing_handler.py`, `histogram_creation_handler.py`, `pipeline/executor.py`, `sqlite_shards.py`, `main.py` — none on the requested list | **No effect** — every touched handler belongs to a stage H->ZZ->4l never runs. |
| 15 | `b240a62` fix error with calculation of invariant mass distribution out of final states with less than 100 events | `config.yaml` (not `config.cms_*`), `domain/config.py`, `mass_calculation_handler.py`, **`services/calculations/im_calculator.py`** (on the list) | **No effect.** `im_calculator.py`'s `IMCalculator` class is only instantiated inside `MassCalculationHandler`, which never runs for H->ZZ->4l. The `config.yaml` change is to the shared default file, not any `config.cms_higgs_4lepton_*.yaml`. |
| 16 | `8a963a0` small config gix | `config.yaml` only | **No effect** — same shared default file, not touched or referenced by any H->ZZ->4l config. |

## Summary

**None of the 16 commits changes the H->ZZ->4l analysis path's output under
normal operation.** Nine of the sixteen touch at least one of the eight
files you asked me to check specifically; every one of those nine was
either inert for the `cms-nanoaod` schema (ATLAS-only or legacy-release-only
code), inert because the stage it belongs to never runs for this config
(`do_mass_calculating`/`do_post_processing`/`do_histogram_creation` are all
`false`), inert because the function it touches is dead code, or (commit #12
only) a change that is a strict no-op on a clean run and only diverges from
old behaviour in a failure scenario, where the new behaviour is more
correct, not less. No config file this analysis actually uses
(`config.cms_higgs_4lepton_*.yaml`) is touched by any of the 16 — confirmed
by a full `git diff --name-only` between `master` and this branch, not just
by reading each commit's stated file list.

**Recommendation: all 16 are safe to merge.** None held back.
