# CMS delivery call graph: `studies/cms_datasets/` into shared code

Generated 2026-10-11 from fork master `db1bd32` by static AST analysis
(`tools/trace2.py`, `tools/fngraph.py` — sources listed in REPORT.md Appendix C).
Every count in this file is **VERIFIED BY RUNNING** those scripts; the exact
commands are in REPORT.md Appendix C.

"Shared code" means `services/`, `domain/`, `orchestration/`, `pipeline/`.

> **Read with section 5.6.** This is a trace of imports and calls. It cannot
> see code the delivery **copied** instead of importing, and the delivery does
> copy several upstream functions. See section 5.6 and REPORT.md section (c),
> "Limitation of the import trace: copied code".

---

## 1. Scope of the trace

| quantity | value |
|---|---|
| `.py` files under `studies/cms_datasets/` (seeds) | 104 |
| of those, under `cluster/` or `deliver/` (the delivery proper) | 42 |
| shared modules reached from **all** of `studies/cms_datasets/` | 14 |
| shared modules reached from the **delivery** (`cluster/`+`deliver/`) | 14 |
| non-shared repo-local modules pulled in on the way | 17 |
| shared function/method definitions in those modules | 80 |
| of those, **reached** by the delivery | 38 |
| of those, **not reached** | 42 |

The transitive closure is identical whether the seeds are the delivery only or
every file under `studies/cms_datasets/`: both reach the same 14 shared modules.
Following study-to-study imports (`studies.m0m1j0_cms.selection`,
`studies.m0m1j0_cms.histograms`, `studies.cms_coverage.*`) adds **no** further
shared module.

## 2. Shared modules reached, and their fork-vs-upstream status

| # | shared module | fork vs upstream | reached by delivery |
|---|---|---|---|
| 1 | `services/__init__.py` | IDENTICAL | yes |
| 2 | `services/calculations/__init__.py` | IDENTICAL | yes |
| 3 | `services/calculations/combinatorics.py` | IDENTICAL | yes |
| 4 | `services/calculations/consts.py` | BOTH, DIFFERENT | yes |
| 5 | `services/calculations/im_calculator.py` | BOTH, DIFFERENT | yes |
| 6 | `services/calculations/physics_calcs.py` | BOTH, DIFFERENT | yes |
| 7 | `services/consts.py` | IDENTICAL | yes |
| 8 | `services/parsing/root_io.py` | BOTH, DIFFERENT | yes |
| 9 | `services/parsing/schemas.py` | BOTH, DIFFERENT | yes |
| 10 | `services/parsing/trigger_requirements.py` | FORK ONLY | yes |
| 11 | `services/parsing/validated_runs.py` | FORK ONLY | yes |
| 12 | `services/pipelines/im_pipeline.py` | BOTH, DIFFERENT | yes |
| 13 | `services/pipelines/post_processing_pipeline.py` | IDENTICAL | yes |
| 14 | `services/storage/sqlite_shards.py` | IDENTICAL | yes |

Six of the fourteen are **byte-identical** between fork master and upstream
master. They are listed here on purpose: the brief asks for every shared
function the delivery calls, *including* identical ones, as proof of coverage.

## 3. Shared modules that DIFFER but are NOT reached at all

These differ between the two masters and no file under `studies/cms_datasets/`
imports them, directly or transitively:

| shared module | fork vs upstream |
|---|---|
| `domain/config.py` | BOTH, DIFFERENT |
| `domain/events.py` | BOTH, DIFFERENT |
| `domain/statistics.py` | BOTH, DIFFERENT |
| `orchestration/handlers/fetch_metadata_handler.py` | BOTH, DIFFERENT |
| `orchestration/handlers/mass_calculation_handler.py` | BOTH, DIFFERENT |
| `orchestration/handlers/parsing_handler.py` | BOTH, DIFFERENT |
| `pipeline/executor.py` | BOTH, DIFFERENT |
| `services/metadata/fetcher.py` | BOTH, DIFFERENT |
| `services/parsing/event_deduplication.py` | FORK ONLY |
| `services/parsing/event_selection.py` | BOTH, DIFFERENT |
| `services/parsing/file_parser.py` | BOTH, DIFFERENT |
| `services/parsing/mc_weights.py` | FORK ONLY |
| `services/parsing/threaded_processor.py` | BOTH, DIFFERENT |
| `services/pipelines/histograms_pipeline.py` | BOTH, DIFFERENT |

## 4. Function-level map

`REACHED` = a call path exists from a `cluster/` or `deliver/` file.
`not reached` = defined in a module the delivery imports, but never called
on any static path ("IMPORTED BUT NOT CALLED" in REPORT.md's table).

### `services/calculations/combinatorics.py` — IDENTICAL

| function / method | status | first call site |
|---|---|---|
| `_expand_with_subleading` | **REACHED** | via another shared function |
| `get_all_combinations` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1928` |
| `get_count` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:574` |
| `get_start` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:574` |

### `services/calculations/im_calculator.py` — BOTH, DIFFERENT

| function / method | status | first call site |
|---|---|---|
| `IMCalculator.__init__` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1419` |
| `IMCalculator._concat_particles_to_vectors` | **REACHED** | via another shared function |
| `IMCalculator._get_all_events_fs` | not reached | — |
| `IMCalculator._get_particle_mass` | **REACHED** | via another shared function |
| `IMCalculator._is_valid_fs` | not reached | — |
| `IMCalculator._limit_particles_in_fs` | not reached | — |
| `IMCalculator.calculate_invariant_mass` | **REACHED** | via another shared function |
| `IMCalculator.does_final_state_contain_combination` | not reached | — |
| `IMCalculator.filter_by_kinematics` | not reached | — |
| `IMCalculator.filter_by_particle_counts` | **REACHED** | via another shared function |
| `IMCalculator.final_state_counts` | not reached | — |
| `IMCalculator.get_events_for_final_state` | not reached | — |
| `IMCalculator.group_by_final_state` | not reached | — |
| `IMCalculator.slice_by_field` | **REACHED** | via another shared function |

### `services/calculations/physics_calcs.py` — BOTH, DIFFERENT

| function / method | status | first call site |
|---|---|---|
| `_boolean_field_mask` | not reached | — |
| `_kinematic_cuts_is_per_object` | not reached | — |
| `calc_inv_mass` | not reached | — |
| `concat_events` | not reached | — |
| `extract_object_types` | not reached | — |
| `filter_events_by_kinematics` | not reached | — |
| `filter_events_by_particle_counts` | **REACHED** | via another shared function |
| `get_particle_known_mass` | **REACHED** | via another shared function |
| `group_by_final_state` | not reached | — |
| `is_finalstate_contain_combination` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1448` |
| `limit_particles_in_fs` | not reached | — |
| `slice_events_by_field` | **REACHED** | via another shared function |

### `services/parsing/root_io.py` — BOTH, DIFFERENT

| function / method | status | first call site |
|---|---|---|
| `open_root_file` | not reached | — |

### `services/parsing/schemas.py` — BOTH, DIFFERENT

| function / method | status | first call site |
|---|---|---|
| `build_branch_name` | not reached | — |
| `extract_schema_from_record_id` | not reached | — |
| `get_available_releases` | not reached | — |
| `get_native_pt_unit` | not reached | — |
| `get_scalar_branch_groups` | not reached | — |
| `get_schema_for_release` | not reached | — |
| `normalize_release_year` | not reached | — |
| `schema_needs_mev_to_gev_conversion` | not reached | — |

### `services/parsing/trigger_requirements.py` — FORK ONLY

| function / method | status | first call site |
|---|---|---|
| `apply_trigger_requirement` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1669` |
| `trigger_group_branches` | **REACHED** | via another shared function |
| `validate_trigger_requirements` | not reached | — |

### `services/parsing/validated_runs.py` — FORK ONLY

| function / method | status | first call site |
|---|---|---|
| `ValidatedRunsFilter.__init__` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1664` |
| `ValidatedRunsFilter.__repr__` | not reached | — |
| `_validate_and_parse` | **REACHED** | via another shared function |
| `apply_validated_runs_filter` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1665` |
| `is_simulation` | **REACHED** | via another shared function |
| `resolve_validated_runs_path` | **REACHED** | via another shared function |

### `services/pipelines/im_pipeline.py` — BOTH, DIFFERENT

| function / method | status | first call site |
|---|---|---|
| `_accumulate_invariant_mass` | not reached | — |
| `_calculate_combination_invariant_mass` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1451` |
| `_convert_array_to_gev` | not reached | — |
| `_fs_dict_exceeding_threshold` | not reached | — |
| `_save_fs_mapping` | not reached | — |
| `_save_remaining_accumulated_data` | not reached | — |
| `prepare_im_combination_name` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1473` |
| `process_final_state` | not reached | — |

### `services/pipelines/post_processing_pipeline.py` — IDENTICAL

| function / method | status | first call site |
|---|---|---|
| `_aligned_bin_edges` | **REACHED** | via another shared function |
| `_apply_z_peak_cut` | **REACHED** | `studies/cms_datasets/deliver/committed/muon_combined/scripts/build_trigger_mixing.py:102` |
| `_dilepton_flavor` | **REACHED** | via another shared function |
| `_find_rightmost_highest_peak` | **REACHED** | `studies/cms_datasets/deliver/committed/muon_combined/scripts/build_trigger_mixing.py:90` |
| `_get_batch_files` | not reached | — |
| `_init_logging` | not reached | — |
| `_process_im_sqlite` | not reached | — |
| `_process_single_array` | not reached | — |
| `_split_by_first_empty_bin` | **REACHED** | `studies/cms_datasets/deliver/committed/muon_combined/scripts/build_trigger_mixing.py:92` |
| `process_im_arrays` | not reached | — |

### `services/storage/sqlite_shards.py` — IDENTICAL

| function / method | status | first call site |
|---|---|---|
| `SqliteArrayShardWriter.__init__` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1948` |
| `SqliteArrayShardWriter.append_array` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1485` |
| `SqliteArrayShardWriter.append_many` | not reached | — |
| `SqliteArrayShardWriter.close` | **REACHED** | `studies/cms_datasets/cluster/merge_pilot.py:219` |
| `SqliteArrayShardWriter.commit` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1982` |
| `SqliteArrayShardWriter.record_final_state_count` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1440` |
| `SqliteArrayShardWriter.set_metadata` | **REACHED** | `studies/cms_datasets/cluster/run_dataset_on_file.py:1483` |
| `_deserialize_array` | **REACHED** | `studies/cms_datasets/cluster/compare_regression.py:93` |
| `_serialize_array` | **REACHED** | via another shared function |
| `get_total_entries` | not reached | — |
| `iter_all_chunks` | **REACHED** | `studies/cms_datasets/deliver/committed/muon_combined/scripts/build_resonance_check.py:34` |
| `iter_arrays_for_signature` | not reached | — |
| `list_signatures` | **REACHED** | `studies/cms_datasets/deliver/build_dataset_delivery.py:192` |
| `prune_final_states_below_min_events` | not reached | — |

## 5. The call paths that matter, written out

These are the paths the difference table in REPORT.md cites in its
"CMS delivery" column. Line numbers are fork master `db1bd32`.

### 5.1 Entry point

`studies/cms_datasets/cluster/run_dataset_on_file.py` is the per-file driver
(2290 lines) that produces the delivered shards. Its shared-code imports are
all at lines 176-185:

```
176  from services.calculations import physics_calcs
177  from services.calculations.combinatorics import get_all_combinations, get_count, get_start
178  from services.calculations.im_calculator import IMCalculator
179  from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter
180  from services.parsing.trigger_requirements import apply_trigger_requirement
181  from services.pipelines.im_pipeline import (
182      _calculate_combination_invariant_mass,
183      prepare_im_combination_name,
184  )
185  from services.storage.sqlite_shards import SqliteArrayShardWriter
186  from studies.m0m1j0_cms import selection          # study code, not shared
```

### 5.2 Event selection (golden JSON, then trigger)

```
run_dataset_on_file.main
  :1664  ValidatedRunsFilter(args.validated_runs_json)
           -> services/parsing/validated_runs.py :: ValidatedRunsFilter.__init__
                -> resolve_validated_runs_path
                -> _validate_and_parse
  :1665  apply_validated_runs_filter(events, validated_runs)
           -> services/parsing/validated_runs.py :: apply_validated_runs_filter
                -> is_simulation
  :1669  apply_trigger_requirement(...)
           -> services/parsing/trigger_requirements.py :: apply_trigger_requirement
                -> trigger_group_branches
```

Both modules are **fork-only**; upstream master has no file at either path
(confirmed with `git ls-tree --name-only upstream/master:services/parsing/`,
see REPORT.md Appendix C).

### 5.3 The combination funnel - where the delivered masses are produced

```
run_dataset_on_file.run_combination_funnel          (:1409)
  :1419  IMCalculator(...)                           -> IMCalculator.__init__
  :1436  _group_by_final_state_with_mask(obj_record)  [STUDY code, :463 - Version B labels]
  :1440  writer_incl.record_final_state_count(...)   -> SqliteArrayShardWriter.record_final_state_count
  :1448  physics_calcs.is_finalstate_contain_combination(label, combination)
                                                      -> physics_calcs :: is_finalstate_contain_combination
  :1451  _calculate_combination_invariant_mass(fs_events, combination, im_config, calculator, ...)
           -> services/pipelines/im_pipeline.py :: _calculate_combination_invariant_mass
                -> calculator.filter_by_particle_counts  -> physics_calcs :: filter_events_by_particle_counts
                -> calculator.slice_by_field             -> physics_calcs :: slice_events_by_field
                -> calculator.calculate_invariant_mass
                     -> IMCalculator._concat_particles_to_vectors
                          -> IMCalculator._get_particle_mass
                               -> physics_calcs :: get_particle_known_mass
                                    -> services/calculations/consts.py :: KNOWN_MASSES   [only if no mass field]
  :1473  prepare_im_combination_name(job_tag, label, combination)
                                                      -> im_pipeline :: prepare_im_combination_name
  :1485  writer_incl.append_array(signature, arr)     -> SqliteArrayShardWriter.append_array
                                                            -> _serialize_array
  :1928  get_all_combinations(...)                    -> combinatorics :: get_all_combinations
                                                            -> _expand_with_subleading
  :574   get_start(value) / get_count(value)          -> combinatorics :: get_start / get_count
```

**The `KNOWN_MASSES` branch is never taken by this delivery.**
`get_particle_known_mass` returns the collection's own per-object `mass` field
whenever that field exists, and consults `KNOWN_MASSES` only when it does not.
The delivery reads `Muon_mass`, `Electron_mass` and `Jet_mass`
(`run_dataset_on_file.py:198-203`) and builds only
`Electrons / Muons / Jets / BJets` (`OBJECT_TYPES`, line 206), with `BJets`
derived from the same `Jet_*` branches. So all four collections carry `mass`
and the dictionary is not read. See REPORT.md row D10.

### 5.4 Post-processing (Z cut, outlier split, peak detection)

```
studies/cms_datasets/deliver/committed/muon_combined/scripts/build_trigger_mixing.py
  :64   iter_all_chunks(...)              -> services/storage/sqlite_shards.py :: iter_all_chunks
  :88   _apply_z_peak_cut(...)            -> services/pipelines/post_processing_pipeline.py :: _apply_z_peak_cut
                                               -> _dilepton_flavor
  :90   _find_rightmost_highest_peak(...) -> post_processing_pipeline :: _find_rightmost_highest_peak
                                               -> _aligned_bin_edges
  :92   _split_by_first_empty_bin(...)    -> post_processing_pipeline :: _split_by_first_empty_bin
                                               -> _aligned_bin_edges
```

`services/pipelines/post_processing_pipeline.py` is **byte-identical** on both
masters (sha256 `d1656580...6ce1` on each - verified by running
`tools/check_edges.py`). This is the file upstream PR **#27** (`8120fb8`,
"Align outlier split to bin edges") changed, so the fork already carries #27
content in full, including the Z cut at 110 GeV.

### 5.5 Shared code the delivery does NOT run

The whole shared *pipeline* is unreached. The delivery is a standalone driver:
it opens ROOT files itself with `uproot`, builds its own object record through
`studies.m0m1j0_cms.selection`, and writes SQLite shards directly. It therefore
never executes:

- `services/parsing/file_parser.py`, `event_selection.py`, `threaded_processor.py`,
  `event_deduplication.py`, `mc_weights.py`
- `services/pipelines/histograms_pipeline.py`
- `services/metadata/fetcher.py`
- all of `orchestration/`, all of `domain/`, all of `pipeline/`

`services/pipelines/histograms_pipeline.py` deserves a note because the brief
listed it as a direct import. It is imported, but **only from inside a Python
source string** that `studies/cms_datasets/tests/test_electron_datasets.py:623`
writes to a temp directory and runs as a subprocess against an extracted copy
of upstream master. No `cluster/` or `deliver/` file imports it. See REPORT.md
correction C6.

### 5.6 Honest limits of this trace

- **Static only.** Reachability is computed from import statements and call
  expressions, not from running the delivery on data.
- **Name-based call resolution.** A call `x.foo()` is matched to a shared
  definition named `foo`. Two shared names collide:
  `group_by_final_state` (both `physics_calcs` and `IMCalculator`) and
  `__init__` (three classes). Both collisions were resolved by hand against
  the call sites; neither changes a REACHED / not-reached verdict, because
  *neither* `group_by_final_state` is called by the delivery (it uses its own
  `_group_by_final_state_with_mask`) and all three constructors are reached.
- **`getattr` is used** in `physics_calcs` (8 occurrences) and
  `im_calculator` (6). In every case the attribute name is a literal string,
  for example `getattr(particle_counts, "Muons", zero_array)`, so no call
  target is hidden. No `importlib`, `eval` or `exec` appears in any `cluster/`
  or `deliver/` file; `importlib` appears only in two `matching/` smoke-test
  scripts, `eval` only in one `tests/` file.
- **Unreached is not the same as dead.** A function this delivery never calls
  may still be run by the shared pipeline for ATLAS, or by another study.
  "NOT REACHED" in REPORT.md is a statement about the four-dataset CMS
  delivery only.
- **COPIED code is invisible to this trace** *(added 2026-10-11, second
  pass)*. The delivery contains its own copies of several upstream
  functions rather than importing them -- the final-state label
  construction copied from upstream `88d7a4b`, the `ROI_..._width_...`
  naming f-string, `FINAL_STATE_OBJECTS`, and upstream's no-minimum-entries
  behaviour. An import-and-call trace cannot see any of those, so it will
  say "NOT REACHED" about the upstream original while the delivery runs an
  identical copy of its own. Every such copy is listed, with whether the
  upstream original has moved since the commit it cites, in REPORT.md
  section (c), "Limitation of the import trace: copied code". Of the nine
  copies meant to track upstream, none has drifted; the two that differ are
  deliberate snapshots of superseded behaviour kept as test references.
