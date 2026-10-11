# Fork master vs upstream master — content-level comparison and decision report

**Date:** 2026-10-11
**Fork master compared:** `db1bd3200e6fd515cfaa04daa6a3f2d3112dad9d` (`db1bd32`)
**Upstream master compared:** `f16768ed6daf0f7ebb358b739bba0c9ffac178c6` (`f16768e`)
**This branch:** `docs/fork-vs-upstream-map-2026-10-11`, branched from fork master, adding only files under `docs/fork_vs_upstream_2026-10-11/`

**Read-only exercise.** Nothing was merged, cherry-picked, rebased or synced. Fork master was not touched. Nothing was pushed, opened, commented on or merged on upstream, and no Pull Request was opened anywhere. The `upstream` remote's push address was set to the non-working placeholder `DISABLED` before anything else happened.

Every number in this report is marked **VERIFIED BY RUNNING** (with the command in Appendix C) or **UNVERIFIED**. Where the code genuinely allows two readings, the word **AMBIGUOUS** appears with both readings written out.

---

## (a) Plain-language summary for Matan

**The headline: the two versions have drifted apart in a lot of places, but none of that drift is touching the CMS data we delivered.**

Here is the reasoning, in plain terms.

The four CMS datasets (DoubleMuon, SingleMuon, DoubleEG, MuonEG) are produced by a self-contained program under `studies/cms_datasets/`. That program borrows some pieces of the shared, two-experiment codebase, but it does not run the shared "pipeline" end to end — it opens the data files itself and writes its own output. So the question "does a difference matter?" becomes "does the delivery actually use that piece of shared code?"

I answered that mechanically rather than by eye. I traced every `import` and every function call from all 104 Python files under `studies/cms_datasets/` into the shared code, following the chain as far as it goes. The result:

- The delivery reaches **14** shared files, and inside them it actually calls **38** functions.
- Of those 38 functions, **30 are character-for-character the same** in both versions.
- **7** exist only in our fork — they are two whole new files we wrote (the CMS certified-run filter and the trigger-path filter).
- **Exactly 1** function differs between the two versions.

That one function decides whether an event has enough objects to fill a given particle combination. Our copy reads only the first digit of each count; upstream fixed it to read the whole number. I tested the two versions against each other over **171,774,906** combinations of label and particle-combination and they gave **the same answer every single time**. The reason is simple: the largest requirement anywhere in our 186 combinations is 4, so an event with 10 or more of something satisfies it either way.

**So: adopting every single upstream improvement into the shared code would not change one number in the delivered data.** Of the 17 items I recommend adopting, 16 are in code the delivery never runs at all, and the 17th is the function above, proven equivalent.

Where the two versions stand, by category (66 items in total):

| Recommendation | Count | What it means |
|---|---|---|
| **PROPOSE TO UPSTREAM** | 20 (+2 pending Maryna) | Things we built that upstream lacks and would probably want |
| **ADOPT FROM UPSTREAM** | 17 | Upstream fixes we are missing and should take |
| **NEEDS DISCUSSION** | 11 | Real physics or naming choices; not ours to settle alone |
| **KEEP DIFFERENT (CMS-specific)** | 8 | Genuinely ours, no reason to share |
| **NO ACTION (identical)** | 8 | Listed only to prove the trace covered them |

### The five findings that matter most

1. **Two of the brief's assumptions were backwards, and the correction is good news.** The brief said upstream PR **#34** reads only the first character of a count. In fact #34 is the commit that **fixed** that; it is *our* fork that still has the bug. And the brief described a difference between upstream's final-state rule and our "Version B" rule — but upstream already has Version B. It arrived in PR **#31** on 4 October as `_filter_events_by_non_jet_object_total`, and I checked it against our rule over 4,096 count patterns: **zero disagreements**. Maryna's expectation that ATLAS would adopt Version B is already satisfied in upstream's code.

2. **The b-jet bug on upstream is real, and I reproduced it.** Upstream's own `config.short_parse_btag.yaml` turns b-tagging on and sets cuts for light jets but not for b-jets. I ran upstream's own code with upstream's own config: a 15 GeV b-jet at |eta| = 2.9 survived, even though the config appears to demand at least 30 GeV. Our configs add the missing line, so we are fine. This is a configuration omission, not broken code — our code change is only a warning that makes the mistake visible.

3. **Our delivered histogram names do not exactly match upstream's.** Upstream names histograms `..._width_10.0`; all 9,793 names in our 14 delivered manifests end in `_width_10`, without the `.0`. Our code can produce either form — there is a switch for it — but the delivered files used the older default. This is the one thing I found that would stop a CMS and an ATLAS histogram being lined up automatically. It needs a decision, not a code fix.

4. **We are missing upstream's network-robustness work.** Upstream added a 120-second timeout on remote file reads and a three-attempt retry with waits of 30, 60 and 120 seconds. We have neither. It changes no physics, only how a job behaves when CERN's servers stall. Worth taking.

5. **The particle-mass units question is still open and is the highest-risk item on the list.** Upstream stores fallback particle masses in MeV and always divides by 1000; we store them in GeV and do not divide. Getting this wrong anywhere is a factor-of-1000 error. It does not affect our delivery, because our data carries its own mass values and the fallback table is never read. But it is unresolved in shared code, upstream issue **#28** is still open about it, and we have a cleaner mechanism ready to propose.

### What I did not do

I did not fix anything. The count-reading bug in our copy, the b-jet configuration gap on upstream, and the final-state rule difference are all documented here and left exactly as they are. No merges, no syncs, no Pull Requests, nothing sent to upstream, nothing sent to anybody.

---

## (b) Re-verified starting facts

Each fact in the brief was re-derived from the live remotes. All six match — nothing has moved.

| Fact as given in the brief | Re-derived value | Verdict |
|---|---|---|
| fork master `db1bd32` | `db1bd3200e6fd515cfaa04daa6a3f2d3112dad9d` | **VERIFIED BY RUNNING** — matches |
| upstream master `f16768e` | `f16768ed6daf0f7ebb358b739bba0c9ffac178c6` | **VERIFIED BY RUNNING** — matches |
| merge base `388b86c` | `388b86cf664cf51003ce4dfc7983700209763e13` | **VERIFIED BY RUNNING** — matches |
| 321 commits only on fork | 321 | **VERIFIED BY RUNNING** — matches |
| 47 commits only on upstream | 47 | **VERIFIED BY RUNNING** — matches |
| 1,448 files changed | 1,448 files changed, 952,778 insertions, 626 deletions | **VERIFIED BY RUNNING** — matches |
| 130 files outside `studies/` and `docs/` | 130 | **VERIFIED BY RUNNING** — matches |

The 130 files break down as (**VERIFIED BY RUNNING**, sums to exactly 130):

| area | files | fork-only | modified on both |
|---|---|---|---|
| `tests/` | 36 | 36 | 0 |
| `reports/` | 33 | 33 | 0 |
| `config*.yaml` | 23 | 18 | 5 |
| shared code + root scripts | 25 | 6 | 19 |
| `scripts/` | 8 | 8 | 0 |
| `logs/` | 3 | 3 | 0 |
| `data/` | 2 | 2 | 0 |

**No file exists on upstream master and is missing from fork master** — there are zero deletions in the whole diff (**VERIFIED BY RUNNING**: `git diff --name-status` yields no `D` entries). Everything upstream has, the fork has in some form; the differences are all additions or modifications.

Two additional facts, not in the brief, that frame everything below (both **VERIFIED BY RUNNING**):

- The delivery reaches **14** shared modules and calls **38** shared functions. Of those 38: **30 AST-identical**, **7 fork-only**, **1 different**.
- `services/pipelines/post_processing_pipeline.py` and `services/storage/sqlite_shards.py` are byte-identical on both masters.

---

## (c) The main table

66 rows. Column meanings:

- **Which side has it** — `FORK ONLY` / `UPSTREAM ONLY` / `BOTH, DIFFERENT` / `IDENTICAL`.
- **CMS delivery** — `USED` with a call path, `IMPORTED BUT NOT CALLED` (its file is loaded but the function never runs), or `NOT REACHED` (nothing under `studies/cms_datasets/` loads it at all).
- **Affects outputs** — `CMS` / `ATLAS` / `BOTH` / `NEITHER`, with the reason.
- **Recommendation** — one of the four the brief specifies. Eight rows carry a fifth label, `NO ACTION (identical - coverage row)`: these are the identical functions the delivery calls, included because the brief asks for them as proof of coverage, and there is no difference to classify. Two rows carry `PROPOSE TO UPSTREAM - pending Maryna's answer`, as the brief directs for the b-jet item.

The same table is in `differences.csv`, machine-readable, same columns and same order.

| ID | Location | What it does (plain language) | Which side has it | CMS delivery | Affects outputs | Recommendation | Risk | Evidence |
|---|---|---|---|---|---|---|---|---|
| D01 | services/calculations/physics_calcs.py :: is_finalstate_contain_combination | Decides whether an event has enough objects to supply a given particle combination; the fork reads only the FIRST character of each count, upstream reads the whole number. | BOTH, DIFFERENT | USED (call path: run_dataset_on_file.py:1448 inside run_combination_funnel) | NEITHER - verified identical answers for every label the delivery can produce, against all 186 combinations | ADOPT FROM UPSTREAM | LOW - proven no behaviour change for this delivery | upstream fix f16768e (#34); fork physics_calcs.py:110-111; upstream physics_calcs.py:116-117; 171,774,906 label x combination pairs tested, 0 disagreements |
| D02 | services/calculations/physics_calcs.py :: limit_particles_in_fs | Caps any object count above 4 when writing a final-state label; the fork's first-character read leaves counts of 10 or more uncapped, upstream caps them to 4. | BOTH, DIFFERENT | IMPORTED BUT NOT CALLED | NEITHER - not on any delivery path; the delivery uses its own exact labels | ADOPT FROM UPSTREAM | LOW | f16768e (#34); fork :91-92; upstream :97-98; the two differ for every label with a count >= 10 (913,521 of 923,521 labels tested) |
| D03 | services/calculations/physics_calcs.py :: group_by_final_state | Builds the final-state label for each event; upstream includes only the object types the data actually carries, the fork always writes all six types. | BOTH, DIFFERENT | NOT REACHED | ATLAS - would change ATLAS label text; the CMS delivery uses its own equivalent copy | ADOPT FROM UPSTREAM | MEDIUM - changes label text for any record that lacks an object type | 88d7a4b (#31); fork :63-76; upstream :63-82; the fork's own study copy already matches upstream's rule (test_upstream_names.py passes) |
| D04 | services/calculations/physics_calcs.py :: _boolean_field_mask | Turns a yes/no data field into a selection mask, and refuses a field that is not genuinely yes/no instead of guessing. | FORK ONLY | NOT REACHED | NEITHER | PROPOSE TO UPSTREAM | LOW - new opt-in helper with no existing caller | fork physics_calcs.py:231-281 |
| D05 | services/calculations/physics_calcs.py :: filter_events_by_kinematics (bool_require / bool_any_of / eta_exclude) | Three new optional object cuts: every listed flag must be true, at least one listed flag must be true, and an eta exclusion window. | FORK ONLY | NOT REACHED | NEITHER - no current config sets any of them | PROPOSE TO UPSTREAM | LOW - absent keys are a complete no-op | fork physics_calcs.py:374-403 |
| D06 | services/calculations/im_calculator.py :: IMCalculator._is_valid_fs | Decides whether an event's object counts form a usable final state; upstream exempts light jets from the cap of 4, the fork caps every type at 4. | BOTH, DIFFERENT | IMPORTED BUT NOT CALLED | ATLAS - the fork's shared copy would drop events with 5 or more light jets; the CMS delivery never calls it | ADOPT FROM UPSTREAM | LOW for CMS / MEDIUM for ATLAS | f16768e (#34); fork :80-87; upstream :87-101; 750 of 14,641 count patterns differ (e/m/b and j each 0..10) |
| D07 | services/calculations/im_calculator.py :: IMCalculator.group_by_final_state | Lists the final states to process; upstream now keeps the true count in the label, the fork still caps it at 4. | BOTH, DIFFERENT | IMPORTED BUT NOT CALLED | ATLAS - label text only | ADOPT FROM UPSTREAM | LOW - matches the group's exact-light-jet-label decision | f16768e (#34); fork :97 (caps the label); upstream :110 (yields it unchanged) |
| D08 | services/calculations/im_calculator.py :: _limit_particles_in_fs and does_final_state_contain_combination | The same first-character count-reading problem as D01 and D02, inside the calculator class. | BOTH, DIFFERENT | IMPORTED BUT NOT CALLED | NEITHER | ADOPT FROM UPSTREAM | LOW | f16768e (#34); fork :116-117 and :138-139; upstream :129-130 and :151-152 |
| D09 | services/calculations/im_calculator.py :: IMCalculator.FINAL_STATE_OBJECTS | A class-level list naming the six object types and their letters; upstream keeps it as a constant, the fork writes the same six out by hand. | UPSTREAM ONLY | NOT REACHED | NEITHER | ADOPT FROM UPSTREAM | LOW - pure tidy-up with no behaviour change | 88d7a4b (#31); upstream im_calculator.py:17-20 |
| D10 | services/calculations/consts.py :: KNOWN_MASSES | Fallback particle masses, used only when the data carries no per-object mass field; the fork stores them in GeV, upstream in MeV. | BOTH, DIFFERENT | USED (call path: run_dataset_on_file.py:1451 -> im_pipeline._calculate_combination_invariant_mass -> IMCalculator.calculate_invariant_mass -> _concat_particles_to_vectors -> _get_particle_mass -> physics_calcs.get_particle_known_mass -> consts.KNOWN_MASSES) - but the dictionary branch is never taken, because all four delivered collections carry a mass field | BOTH if ever read - a factor-1000 mass error; NEITHER for today's delivered inputs | NEEDS DISCUSSION | HIGH - units; a wrong answer here is a 1000x error in every mass | f43cc93 deliberately excluded from the fork; upstream issue #28 open; fork consts.py:4-11; upstream consts.py:4-14; the delivery reads Muon_mass/Electron_mass/Jet_mass at run_dataset_on_file.py:198-203 |
| D11 | services/parsing/schemas.py :: native_pt_unit tags + get_native_pt_unit + schema_needs_mev_to_gev_conversion | Records, for each data release, whether momenta arrive in MeV or GeV, so the divide-by-1000 is applied only where it belongs. | FORK ONLY | IMPORTED BUT NOT CALLED | NEITHER today - no config on either side selects the one GeV-tagged ATLAS release | PROPOSE TO UPSTREAM | LOW - defaults to converting for anything untagged or unknown | fork schemas.py:117-264 and :622-650; verified by running: None, empty, unknown and unregistered inputs all return True (convert) |
| D12 | services/pipelines/im_pipeline.py :: process_final_state and _convert_array_to_gev | Applies the MeV-to-GeV conversion only for MeV-native releases; upstream applies it to every release unconditionally. | BOTH, DIFFERENT | IMPORTED BUT NOT CALLED | NEITHER today; ATLAS if a GeV-native release is ever configured | PROPOSE TO UPSTREAM | LOW - identical behaviour for every release in use today | fork im_pipeline.py:29-48 and :112-116; upstream :103 and :133-134 |
| D13 | services/parsing/schemas.py :: SINGLE_LEPTON_TRIGGER_CHAINS + get_trigger_years | ATLAS single-lepton trigger chain names per data-taking year, used by upstream's trigger matching. | UPSTREAM ONLY | NOT REACHED | ATLAS | NEEDS DISCUSSION | MEDIUM - ATLAS trigger selection is a physics choice | bea982d (#22); upstream schemas.py (4 and 2 occurrences); absent from the fork (0 occurrences of each) |
| D14 | services/parsing/schemas.py :: event_id_branches / NANOAOD_EVENT_ID_BRANCHES / get_scalar_branch_groups | Lets a schema declare per-event identity branches (run, luminosity block, event) and named groups of non-particle branches. | FORK ONLY | IMPORTED BUT NOT CALLED | NEITHER | PROPOSE TO UPSTREAM | LOW - additive declaration; a schema that omits it is unchanged | fork schemas.py:45-49 and :129 |
| D15 | services/parsing/schemas.py :: RECORD_ID_TO_SCHEMA CMS record entries | Maps this fork's CMS record numbers to the NanoAOD schema so they are not silently mis-detected and parsed as zero events. | FORK ONLY | NOT REACHED | CMS | KEEP DIFFERENT (CMS-specific) | LOW - data values specific to this fork's own records | fork schemas.py:74-75; the generic mechanism worth proposing instead is D14 |
| D16 | services/parsing/root_io.py :: open_root_file | Gives remote ROOT file reads a 120-second timeout so a stuck CERN connection cannot hang a job forever. | UPSTREAM ONLY | IMPORTED BUT NOT CALLED | NEITHER - robustness only | ADOPT FROM UPSTREAM | LOW - timeout only; no selection change | 418bb1b; upstream root_io.py:24-25 (xrootd_handler and timeout=120); absent from the fork |
| D17 | services/parsing/trigger_requirements.py (whole module) | Keeps only events in which configured trigger paths actually fired; completely off unless a config asks for it. | FORK ONLY | USED (call path: run_dataset_on_file.py:1669 -> apply_trigger_requirement -> trigger_group_branches) | CMS - part of the delivered selection | PROPOSE TO UPSTREAM | LOW - experiment-neutral and a default no-op | fork services/parsing/trigger_requirements.py, 129 lines; the file is absent from upstream/master:services/parsing/ |
| D18 | services/parsing/validated_runs.py (whole module) | Keeps only the run and luminosity-block pairs CMS certified as good for physics, and refuses to apply itself to simulation. | FORK ONLY | USED (call path: run_dataset_on_file.py:1664 -> ValidatedRunsFilter.__init__ -> _validate_and_parse; :1665 -> apply_validated_runs_filter -> is_simulation) | CMS - part of the delivered selection | PROPOSE TO UPSTREAM | LOW - generic certified-run filtering; default off | fork services/parsing/validated_runs.py, 248 lines; the file is absent from upstream/master:services/parsing/ |
| D19 | services/calculations/combinatorics.py :: get_all_combinations / _expand_with_subleading / get_count / get_start | Generates the 186 object combinations the delivery computes masses for, and reads each combination's count and starting rank. | IDENTICAL | USED (call path: run_dataset_on_file.py:1928 and :574) | NEITHER | NO ACTION (identical - coverage row) | LOW | blob hash equal on both masters; AST equal for all four functions |
| D20 | services/pipelines/post_processing_pipeline.py :: _apply_z_peak_cut / _dilepton_flavor / _find_rightmost_highest_peak / _split_by_first_empty_bin / _aligned_bin_edges | Applies the 110 GeV Z cut to same-flavour lepton pairs, finds the peak, and splits outliers on 10 GeV bin edges. | IDENTICAL | USED (call path: build_trigger_mixing.py:88, :90, :92) | NEITHER | NO ACTION (identical - coverage row) | LOW | sha256 d1656580d3578864d9650d36ad07da9e84e20271a9212bf3ac6959d946e16ce1 on both masters; this is the file #27 (8120fb8) changed, so the fork carries #27 in full |
| D21 | services/storage/sqlite_shards.py :: SqliteArrayShardWriter (__init__ / append_array / commit / close / record_final_state_count / set_metadata) + _serialize_array / _deserialize_array / iter_all_chunks / list_signatures | Writes and reads the SQLite shard files that hold the delivered mass arrays. | IDENTICAL | USED (call path: run_dataset_on_file.py:1948, :1485, :1440, :1483; build_resonance_check.py:34) | NEITHER | NO ACTION (identical - coverage row) | LOW | blob hash equal on both masters; the Sept 2026 map's T1-18 reordering divergence is now gone |
| D22 | services/calculations/physics_calcs.py :: filter_events_by_particle_counts / slice_events_by_field / get_particle_known_mass | Picks the events with enough objects, takes the correctly ranked objects, and supplies each object's mass. | IDENTICAL | USED (call path: im_pipeline._calculate_combination_invariant_mass via IMCalculator.filter_by_particle_counts / slice_by_field / _get_particle_mass) | NEITHER | NO ACTION (identical - coverage row) | LOW | AST equal on both masters, even though the file differs elsewhere |
| D23 | services/calculations/im_calculator.py :: __init__ / calculate_invariant_mass / _concat_particles_to_vectors / _get_particle_mass / filter_by_particle_counts / slice_by_field | Computes the invariant mass of a group of objects - the actual delivered number. | IDENTICAL | USED (call path: run_dataset_on_file.py:1419, then im_pipeline._calculate_combination_invariant_mass) | NEITHER | NO ACTION (identical - coverage row) | LOW | AST equal on both masters, even though the file differs elsewhere |
| D24 | services/pipelines/im_pipeline.py :: _calculate_combination_invariant_mass / prepare_im_combination_name | Runs one combination's mass calculation and builds the signature name its shard is stored under. | IDENTICAL | USED (call path: run_dataset_on_file.py:1451 and :1473) | NEITHER | NO ACTION (identical - coverage row) | LOW | AST equal on both masters, even though the file differs elsewhere |
| D25 | services/consts.py / services/__init__.py / services/calculations/__init__.py | Shared constants and package marker files pulled in along the import path. | IDENTICAL | IMPORTED BUT NOT CALLED (no function in them is called) | NEITHER | NO ACTION (identical - coverage row) | LOW | blob hashes equal on both masters |
| D26 | services/parsing/threaded_processor.py :: _parse_single_file | Retries a failed file three times with 30, 60 then 120 second waits before giving up, and allows 900 seconds per file instead of 300. | UPSTREAM ONLY | NOT REACHED | NEITHER - robustness only | ADOPT FROM UPSTREAM | LOW - retry and timeout only; no selection change | 418bb1b; upstream threaded_processor.py:97 and :140-186; the fork has timeout=300 at :148 and no file-level retry |
| D27 | services/parsing/threaded_processor.py :: process_files signature | Adds optional extra branch groups, extra object fields, event weights, pile-up info and probe statistics to the reader. | FORK ONLY | NOT REACHED | NEITHER - all default off | PROPOSE TO UPSTREAM | LOW - absent arguments reproduce existing behaviour | fork threaded_processor.py:50-90 |
| D28 | services/parsing/threaded_processor.py :: enable_trigger_matching parameter | Passes upstream's trigger-matching switch down to the file reader. | UPSTREAM ONLY | NOT REACHED | ATLAS | NEEDS DISCUSSION | MEDIUM - couples to the #22 trigger-matching design | bea982d (#22) and fe5a560 (#29); upstream has 1 occurrence; the fork has 0 |
| D29 | services/parsing/file_parser.py :: trigger matching (_triggerMatch, enable_trigger_matching, trigger_branches) | Reads ATLAS trigger-match branches and attaches them to each event. | UPSTREAM ONLY | NOT REACHED | ATLAS | NEEDS DISCUSSION | MEDIUM - ATLAS trigger selection is a physics choice | bea982d (#22); upstream file_parser.py (6, 4 and 2 occurrences); the fork has 0 of each |
| D30 | services/parsing/file_parser.py :: _resolve_scalar_groups / _resolve_object_fields / RequiredScalarBranchMissingError / RequiredObjectFieldMissingError | Lets a config ask for extra branches and extra per-object fields, and fails loudly instead of silently dropping a branch it cannot read. | FORK ONLY | NOT REACHED | NEITHER - all default off | PROPOSE TO UPSTREAM | LOW - additive and default off | fork file_parser.py (3, 3, 7 and 2 occurrences); upstream has 0 of each |
| D31 | services/parsing/file_parser.py :: EventIds group / source_record tag / genWeight / PV_npvsGood | Attaches each event's run, luminosity-block and event identity, which record it came from, and optionally its generator weight and pile-up count. | FORK ONLY | NOT REACHED | NEITHER today | PROPOSE TO UPSTREAM | LOW - additive and default off | fork file_parser.py (5, 3, 1 and 1 occurrences); upstream has 0 of each |
| D32 | services/parsing/event_selection.py :: _filter_events_by_non_jet_object_total | Rejects an event with more than four non-light-jet objects in TOTAL, keeping all light jets - the same rule the fork's delivery calls Version B. | UPSTREAM ONLY | NOT REACHED | ATLAS - would apply Version B to ATLAS; the CMS delivery already applies the identical rule in its own code | ADOPT FROM UPSTREAM | LOW - verified identical to the delivered Version B rule | 88d7a4b (#31); upstream event_selection.py:27-28 (LIGHT_JET_FIELD=Jets, MAX_NON_JET_OBJECTS=4) and :114-124; absent from fork shared code; 0 of 4,096 count patterns disagree with the fork's Version B |
| D33 | services/parsing/event_selection.py :: retain_objects_for_storage | Drops object collections the config does not ask to keep, before selection runs. | UPSTREAM ONLY | NOT REACHED | ATLAS | ADOPT FROM UPSTREAM | LOW | 88d7a4b (#31); upstream event_selection.py:127-137; absent from the fork |
| D34 | services/parsing/event_selection.py :: apply_trigger_selection | Keeps only events where a lepton fired a single-lepton trigger, using ATLAS trigger-match branches. | UPSTREAM ONLY | NOT REACHED | ATLAS | NEEDS DISCUSSION | MEDIUM - ATLAS trigger selection is a physics choice | bea982d (#22); upstream event_selection.py:141-218; absent from the fork |
| D35 | services/parsing/event_selection.py :: normalize_yaml_kinematic_cuts (bool_require / bool_any_of / eta_exclude) | Passes the three new optional object cuts from the config file through to the cut code. | FORK ONLY | NOT REACHED | NEITHER | PROPOSE TO UPSTREAM | LOW - absent keys are a no-op | fork event_selection.py:56-69; pairs with D05 |
| D36 | domain/config.py :: ParsingConfig.__post_init__ b-jet cut warning | Prints a warning when b-jet tagging is on and the config cuts light jets but not b-jets, which would silently leave b-jets uncut. | FORK ONLY | NOT REACHED | NEITHER - a warning only; it changes no behaviour | PROPOSE TO UPSTREAM - pending Maryna's answer | LOW - logs a warning and nothing else | fork domain/config.py:156-175; verified by running scripts/test_bjets_warning.py: it fires only for the bug shape and stays silent in all 6 other cases |
| D37 | domain/config.py :: selection_by_record / trigger_requirements / extra_object_fields / extra_scalar_branches / read_event_weights / read_pileup_info | Six new optional config settings: per-record selection, trigger paths, extra fields, extra branches, event weights and pile-up info. | FORK ONLY | NOT REACHED | NEITHER - every one defaults to off or None | PROPOSE TO UPSTREAM | LOW - additive and default off | fork domain/config.py:102-135 and :334 |
| D38 | domain/config.py :: objects_to_calculate enforcement | Makes the configured object list actually constrain what parsing and analysis produce. | UPSTREAM ONLY | NOT REACHED | ATLAS | ADOPT FROM UPSTREAM | LOW | 88d7a4b (#31); 40 changed lines in upstream domain/config.py in that commit |
| D39 | domain/config.py and config.yaml :: trigger_config / enable_trigger_matching | The switch that turns upstream's trigger matching on; it ships set to false. | UPSTREAM ONLY | NOT REACHED | ATLAS | NEEDS DISCUSSION | LOW on its own (it ships off) but it is the entry point to the #22 design | bea982d (#22) and fe5a560 (#29); upstream config.yaml carries trigger_config.enabled=false; the fork's config.yaml has no trigger key at all |
| D40 | domain/events.py :: EventBatch.file_url field | Records which file an event batch came from. | UPSTREAM ONLY | NOT REACHED | NEITHER | ADOPT FROM UPSTREAM | LOW - an extra field with a default value | bea982d (#22); upstream domain/events.py:51; absent from the fork |
| D41 | domain/events.py :: _concatenate_events / _empty_particle_collection | Joins per-file event arrays while keeping collections that only some files have, instead of silently deleting them. | BOTH, IDENTICAL content | NOT REACHED | NEITHER | NO ACTION (identical - coverage row) | LOW | d488f21, the silent collection-drop fix: present in the fork at domain/events.py:20 and :115, with 19 of 19 added lines found |
| D42 | domain/statistics.py :: sumw_by_record | Records per-record generator weight sums so simulation can be normalised later. | FORK ONLY | NOT REACHED | NEITHER - populated only when event weights are switched on | PROPOSE TO UPSTREAM | LOW - an optional field defaulting to None | fork domain/statistics.py, 11 added lines |
| D43 | orchestration/handlers/parsing_handler.py :: EventDeduplicator use and muon-first record ordering | Removes the duplicate when two trigger streams both recorded the same event, and processes the stricter stream first. | FORK ONLY | NOT REACHED | NEITHER today | PROPOSE TO UPSTREAM | LOW - only active when per-record selection is configured | fork parsing_handler.py (EventDeduplicator 2 occurrences, selection_by_record 7); upstream has 0 of each |
| D44 | orchestration/handlers/parsing_handler.py :: MAX_FILE_FAILURE_RATE guard | Aborts a record if more than 20 percent of its files fail to open, instead of quietly finishing with almost no events. | FORK ONLY | NOT REACHED | NEITHER - robustness only | PROPOSE TO UPSTREAM | LOW - only fires on a run that is already broken | fork parsing_handler.py (4 occurrences); upstream has 0 |
| D45 | orchestration/handlers/parsing_handler.py :: trigger-requirement wiring | Passes the configured trigger paths (D17) through to parsing, including per-record overrides. | FORK ONLY | NOT REACHED | NEITHER - default off | PROPOSE TO UPSTREAM | LOW | fork parsing_handler.py (trigger_requirements 16 occurrences); upstream has 0 |
| D46 | orchestration/handlers/parsing_handler.py :: trigger-matching and objects_to_store wiring | Passes upstream's trigger-matching switch and its stored-object list through to parsing. | UPSTREAM ONLY | NOT REACHED | ATLAS | NEEDS DISCUSSION | MEDIUM - part of the #22 and #31 designs | bea982d (#22), fe5a560 (#29), 88d7a4b (#31); upstream parsing_handler.py (enable_trigger_matching 3, apply_trigger_selection 2, objects_to_store 1); the fork has 0 of each |
| D47 | orchestration/handlers/mass_calculation_handler.py :: release_year_from_parsed_filename and the per-file MeV-to-GeV decision | Works out each parsed file's data release so the unit conversion is decided per file, not once for the whole run. | FORK ONLY | NOT REACHED | NEITHER today | PROPOSE TO UPSTREAM | LOW - pairs with D11 and D12 | fork mass_calculation_handler.py:26, :29-43 and :356-360 |
| D48 | orchestration/handlers/mass_calculation_handler.py :: prune_final_states_below_min_events call and objects_to_calculate filtering | Removes under-populated final states at the mass stage as well, and restricts that stage to the configured objects. | UPSTREAM ONLY | NOT REACHED | ATLAS | ADOPT FROM UPSTREAM | LOW - the fork already prunes in post-processing | d98f2c3 and 88d7a4b (#31); the fork prunes only at post_processing_pipeline.py:161, using the same shared function |
| D49 | orchestration/handlers/fetch_metadata_handler.py :: _validate_cache_or_abort CMS handling | Checks that a cached CMS file list really is the data it claims to be before reusing it. | FORK ONLY | NOT REACHED | NEITHER | PROPOSE TO UPSTREAM | LOW | fork fetch_metadata_handler.py, 73 added lines |
| D50 | services/metadata/fetcher.py :: _classify_cms_url | Recognises a CMS Open Data file URL as real data or simulation from its path. | FORK ONLY | NOT REACHED | NEITHER | PROPOSE TO UPSTREAM | LOW - ATLAS URL handling is unchanged | fork services/metadata/fetcher.py, 48 added lines |
| D51 | pipeline/executor.py :: _read_parsed_data_stats allowed_objects filter | Counts only the configured object types when reporting what was parsed. | UPSTREAM ONLY | NOT REACHED | NEITHER - reporting only | ADOPT FROM UPSTREAM | LOW - statistics only | 88d7a4b (#31); 18 changed lines in upstream pipeline/executor.py; the fork has the older unfiltered version |
| D52 | services/pipelines/histograms_pipeline.py :: _group_signatures_by_bumpnet and _group_im_files_by_signature | Matches a final-state label out of a signature name; upstream's pattern accepts any label, the fork's demands the old six-field order and silently skips anything else. | BOTH, DIFFERENT | NOT REACHED | BOTH if the shared histogram stage were ever used for CMS - the fork's pattern silently drops a four-field CMS label such as 0e_2m_5j_1b | ADOPT FROM UPSTREAM | MEDIUM - a silent skip rather than an error | 88d7a4b (#31); fork histograms_pipeline.py:317 and :406; upstream same lines; verified by running: upstream matches 0e_2m_5j_1b, the fork does not |
| D53 | services/parsing/event_deduplication.py (whole module) | Keeps the first copy of each event, so an event recorded by two trigger streams is not counted twice. | FORK ONLY | NOT REACHED | NEITHER today | PROPOSE TO UPSTREAM | LOW - only used when per-record selection is configured | fork services/parsing/event_deduplication.py, 102 lines; absent from upstream |
| D54 | services/parsing/mc_weights.py (whole module) | Reads simulation generator weights and pile-up information, and keeps the bookkeeping needed to normalise them. | FORK ONLY | NOT REACHED | NEITHER - simulation only and default off | NEEDS DISCUSSION | LOW on master, but it overlaps open upstream PR #35 | fork services/parsing/mc_weights.py, 226 lines; the related work is on fork branch feature/cms-mc-weights-v3 and upstream PR #35, both outside master |
| D55 | config.cms_records_master.yaml / config.cms_singleelectronsinglemuon.yaml / config.short_parse_btag.yaml / config.short_parse_local.yaml :: parsing_task_config.kinematic_cuts.bjets | Adds the missing b-jet pT and eta cuts (30 GeV, \|eta\| below 4.5); without the entry, tagged b-jets get no kinematic cuts at all. | FORK ONLY | NOT REACHED (the delivery applies its own cuts in study code) | CMS - and ATLAS would be affected the moment an ATLAS config enabled tagging | PROPOSE TO UPSTREAM - pending Maryna's answer | MEDIUM - a real uncut-object bug on upstream today | verified by running: upstream code with upstream's own config.short_parse_btag.yaml keeps a 15 GeV, \|eta\|=2.9 b-jet despite jets: pt_min 30; the fork's config adds bjets: and the same jet is removed; upstream's own config.yaml does carry a bjets: entry, so config.short_parse_btag.yaml is the only upstream config with the live shape |
| D56 | config.cms_records_master.yaml :: parsing_task_config.selection_by_record (records 30530 and 30563) | Gives the two SingleMuon records their own object-count requirements instead of the global electron requirement. | FORK ONLY | NOT REACHED | CMS | KEEP DIFFERENT (CMS-specific) | LOW - config values for this fork's own records; the generic mechanism is D37 | 16 of the 18 differing keys in this file; upstream has no selection_by_record block in any config |
| D57 | config.yaml :: parsing_task_config.particle_counts.photons and .taus | Writes the photon and tau requirements out explicitly as zero instead of leaving them unstated. | FORK ONLY | NOT REACHED | NEITHER - the same effective selection | KEEP DIFFERENT (CMS-specific) | LOW - it makes an existing default explicit | 4 differing keys; upstream removed these 2 lines in 88d7a4b (#31) |
| D58 | data/cms/validated_runs/ (certified-run JSON and README) | The CMS certified-run list that the golden-JSON filter reads, with its source and checksum recorded. | FORK ONLY | USED (read at run time by D18, default path run_dataset_on_file.py:190-192) | CMS | KEEP DIFFERENT (CMS-specific) | LOW - a CMS data file | fork data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt and README.md |
| D59 | tests/ (36 files) | The fork's regression test suite; upstream deleted its own tests entirely. | FORK ONLY | NOT REACHED | NEITHER | KEEP DIFFERENT (CMS-specific) | LOW | upstream commit 6ff3c31 remove tests; upstream/master has no tests/ directory; the fork has 36 files, listed in REPORT.md Appendix A |
| D60 | reports/ (33 files) and logs/ (3 files) | Written-up results and job logs from this fork's own test runs. | FORK ONLY | NOT REACHED | NEITHER | KEEP DIFFERENT (CMS-specific) | LOW | full list in REPORT.md Appendix A |
| D61 | scripts/ (8 files) | Stand-alone checking scripts the fork wrote for its own verification: b-jet cuts, Z peak, de-duplication and report building. | FORK ONLY | NOT REACHED | NEITHER | KEEP DIFFERENT (CMS-specific) | LOW | full list in REPORT.md Appendix A |
| D62 | submit_mc.sh | One extra progress line echoed into the job log. | UPSTREAM ONLY | NOT REACHED | NEITHER | ADOPT FROM UPSTREAM | LOW - a log line | 3464e1a; 1 line |
| D63 | studies/cms_datasets/deliver/build_dataset_delivery.py :: width_suffix / roi_key | Builds the _width_ ending of each histogram name; the fork's default writes _width_10 while upstream writes _width_10.0, and the delivered files used the default. | FORK ONLY (study code; upstream has only its own shared-pipeline form) | USED (it names every delivered histogram) | CMS - the delivered names do not match upstream's exactly | NEEDS DISCUSSION | MEDIUM - names must match for CMS and ATLAS outputs to be compared directly | verified by running test_width_suffix.py: --upstream-width-suffix gives _width_10.0, the default gives _width_10; all 9,793 names across the 14 committed manifests end in _width_10; both masters' configs set bin_width_gev: 10.0, a float |
| D64 | studies/cms_datasets/cluster/run_dataset_on_file.py :: EMU_OVERLAP_DR_MAX | Removes an electron that sits within dR 0.12 of a selected muon, in all four datasets; the muon is always kept. | FORK ONLY (study code; no overlap removal exists in shared code on either side) | USED (part of the delivered selection) | CMS - and CMS/ATLAS comparability depends on ATLAS doing the same | NEEDS DISCUSSION | MEDIUM - an object-selection choice that must match on both experiments | fork run_dataset_on_file.py:331-344; radius approved by Maryna on 7 Oct 2026, raised from 0.05; no 0.12 value and no overlap-removal code anywhere in shared code on either master |
| D65 | studies/cms_datasets/deliver/build_dataset_delivery.py :: per-histogram minimum entries | Keeps only histograms with at least 100 entries by default; upstream's shared stage applies no minimum and keeps any histogram with at least one entry. | FORK ONLY (study code) | USED (it decides which histograms are delivered) | CMS - fewer histograms than upstream's rule would give | NEEDS DISCUSSION | MEDIUM - it changes which final states appear in the delivery | verified by running test_upstream_names.py: the default floor is 100 and --no-hist-min-entries gives upstream's floor of 1 |
| D66 | pbs_m0m1j0_fullscale.sh and pbs_m0m1j0_smoketest.sh | Two cluster job-submission scripts the fork added for its own muon-plus-jet runs. | FORK ONLY | NOT REACHED | NEITHER | KEEP DIFFERENT (CMS-specific) | LOW - job submission only | fork root directory; both absent from upstream; covered by tests/test_pbs_scripts.py |
---

## (d) ADOPT items and their predicted effect on the delivered data

Seventeen rows are marked ADOPT FROM UPSTREAM. For each, the question is what adopting it would change in the four-dataset delivery (DoubleMuon, SingleMuon, DoubleEG, MuonEG).

**Sixteen of the seventeen: `NO CHANGE: code not reached by the delivery.`**

| ID | What would be adopted | Why no change |
|---|---|---|
| D02 | `limit_particles_in_fs` count reading | Not called on any delivery path; the delivery labels events with its own `exact_final_state_labels` |
| D03 | `physics_calcs.group_by_final_state` generic labels | Not reached; the delivery has its own equivalent, already matching upstream's rule |
| D06 | `IMCalculator._is_valid_fs` light-jet exemption | Imported but never called; the delivery applies its own Version B rule |
| D07 | `IMCalculator.group_by_final_state` uncapped labels | Imported but never called |
| D08 | `_limit_particles_in_fs` / `does_final_state_contain_combination` | Imported but never called |
| D09 | `FINAL_STATE_OBJECTS` constant | Not reached |
| D16 | `open_root_file` xrootd timeout | `root_io` is imported via `schemas`, but `open_root_file` is never called — the delivery opens files with `uproot` directly |
| D26 | `threaded_processor` retry and backoff | Not reached — the delivery does not use the threaded reader |
| D32 | `_filter_events_by_non_jet_object_total` | Not reached — and verified equivalent to the Version B rule the delivery already applies |
| D33 | `retain_objects_for_storage` | Not reached |
| D38 | `objects_to_calculate` enforcement | Not reached |
| D40 | `EventBatch.file_url` | Not reached |
| D48 | prune call in the mass handler | Not reached; the fork already prunes in post-processing with the same shared function |
| D51 | `executor` statistics filter | Not reached; reporting only |
| D52 | `histograms_pipeline` label pattern | Not reached — the delivery builds its own histogram names |
| D62 | `submit_mc.sh` log line | Not reached |

The evidence for each is the trace in `cms_delivery_call_graph.md` sections 2–4, which lists every shared function and whether a call path exists.

**One of the seventeen: `NO CHANGE EXPECTED: reached, but behaviour identical for delivered inputs.`**

**D01 — `physics_calcs.is_finalstate_contain_combination`.** This *is* on the delivery path (`run_dataset_on_file.py:1448`). Adopting upstream's version would change nothing, and this is not an argument from inspection — it was run:

1. **The requirement side.** Built the delivery's own 186-combination set with the delivery's own parameters and listed every requirement in it. Every `start + count` requirement, for every object type, is in the range 1–4. The maximum is **4**. (**VERIFIED BY RUNNING**, `tools/check_counts.py`.)
2. **Per-field equivalence.** The function decides each count field independently and ANDs the results, so agreeing on every single (count, letter, requirement) triple implies agreeing on every label. Tested counts 0–60 against all 16 distinct requirements: **976 triples, 0 disagreements**. (**VERIFIED BY RUNNING**, `tools/check_field.py`.)
3. **Whole-label equivalence.** Tested every label with each of e, m, j, b running 0–30 — 923,521 labels — against all 186 combinations: **171,774,906 pairs, 0 disagreements**. (**VERIFIED BY RUNNING**, `tools/check_exhaustive.py`.)

Why they agree: for a count below 10 both versions read the same digit. For a count of 10 or more, our version reads a digit where the letter should be, fails to recognise the object type, and skips that requirement — treating it as satisfied. Upstream reads the real number and checks it. Since the number is at least 10 and the requirement is at most 4, upstream's check passes too. Both say "satisfied".

**This matters because counts of 10 or more really do occur.** Final-state labels with 10, 11 and 12 light jets appear in the fork's own study evidence files, the largest being 12 (**VERIFIED BY RUNNING**, scan of 198 text files under `studies/cms_datasets/`). In the 14 committed delivery manifests the largest light-jet count is 4, and the largest electron, muon and b-jet counts are 3, 3 and 4 (**VERIFIED BY RUNNING**). So the two-digit case is not observed in the committed four-dataset manifests, but it is observed in the study evidence, and the equivalence above covers it either way.

**Zero rows are `REGRESSION REQUIRED BEFORE SYNC`.**

One caveat stated plainly: this verdict is about the delivered data, which is already on disk and which this task did not touch. Adopting D03, D06, D07, D32, D33, D38 and D52 *would* change what the shared pipeline does for **ATLAS** — that is the point of them. The ATLAS side is outside this comparison's scope.

---

## (e) Physics flags

### Mass units (GeV vs MeV)

Three separate places, all checked.

**1. The fallback mass table** (row D10). Upstream's `KNOWN_MASSES` is in MeV (`Muons: 105.6583755`) and upstream divides every computed mass by 1000 unconditionally. Ours is in GeV (`Muons: 0.105`) and we do not divide. Upstream commit `f43cc93` ("FIx incorrect KNOWN_MASSES units") is **confirmed absent** from fork master: **0 of its 3 significant added lines** are present (**VERIFIED BY RUNNING**, `tools/content_presence.py`). Upstream issue **#28** is open about it.

The table is reached by the delivery but **never read**, because `get_particle_known_mass` prefers the data's own `mass` field and the delivery supplies one for all four of its collections. The function itself is AST-identical on both sides.

**2. The release-tagged unit mechanism** (rows D11, D12, D47). Our fork tags each data release with `native_pt_unit` and divides by 1000 only for MeV-native releases. Checked by running: `MeV` for `2016e-8tev`, `2020e-13tev`, `2024r-hi`, `2024r-pp`; `GeV` for `2025e-13tev-beta` and `cms-nanoaod`; `unknown` for the two `2025r-evgen` releases. The gate returns "convert" for anything untagged, unknown, empty or `None` (**VERIFIED BY RUNNING**). So adopting it upstream would be behaviour-identical for every release upstream uses today.

**No config on either master selects `2025e-13tev-beta`** (**VERIFIED BY RUNNING**, grep across all 6 upstream and 24 fork config files). The ATLAS half of this concern is therefore **latent, not live**.

**3. The Z cut at 110 GeV.** Both masters set `z_peak_cutoff: 110.0` in `config.yaml` and default to `110.0` in `domain/config.py` (**VERIFIED BY RUNNING**). The cut is applied by `_apply_z_peak_cut`, which is AST-identical on both sides. Run on realistic signatures with values 95, 105, 109.999, 110, 120 and 500 GeV: for a same-flavour lepton pair it keeps 110, 120 and 500 and drops the rest — the comparison is `>=`, so exactly 110.0 is kept. For `e0m0`, `j0j1` and `b0b1` it keeps everything, as intended (**VERIFIED BY RUNNING**, `tools/check_edges.py`). **There is no mass-unit or Z-cut difference between the two masters.**

### The BJets kinematic-cut bug on upstream

*Presented as* **PROPOSE TO UPSTREAM — pending Maryna's answer** *(rows D36 and D55). Not reported anywhere; this document is the only place it is written down.*

What happens on upstream today, reproduced by running upstream's own code against upstream's own config file:

- `filter_events_by_kinematics` matches a cut entry to a collection by name. A `jets:` entry maps to `Jets`; `BJets` is matched only by a `bjets:` entry. With no `bjets:` key, the code takes the `cuts is None` branch and assigns the collection through untouched — **no cuts at all**, and no error or warning of any kind.
- **Exactly one upstream config has the live form of this**: `config.short_parse_btag.yaml`, which sets `enable_jet_tagging: true` and `kinematic_cuts.jets: {pt_min: 30.0, eta_max: 4.5}` with no `bjets:` entry. Two upstream configs enable tagging; the other one, `config.yaml`, does carry a `bjets:` entry (`pt_min: 30000.0, eta_max: 2.5`) and is therefore fine. The remaining four upstream configs do not enable tagging (**VERIFIED BY RUNNING**, audit of all 6 upstream and all 24 fork configs).
- Demonstration (**VERIFIED BY RUNNING**, `tools/check_bjets.py`): one event with a 100 GeV / |eta| 0.5 jet and a 15 GeV / |eta| 2.9 jet in both `Jets` and `BJets`.
  - upstream code + upstream config: `Jets` keeps `[100.0]`; `BJets` keeps `[100.0, 15.0]` — the soft, forward b-jet **survives**.
  - fork code + fork config: `BJets` keeps `[100.0]` — removed, correctly.
  - fork code + upstream config: `BJets` keeps `[100.0, 15.0]` — the bug follows the **config**, not the code.

So this is a configuration omission, in one upstream config file. On the fork side, 11 of the 24 configs carry a `bjets:` entry — including all three that enable tagging — and **no fork config has the live bug shape** (**VERIFIED BY RUNNING**). Four of those entries are the fix applied to the four CMS configs that exist on both sides (row D55). Separately we added a code-side guard: a `WARNING` in `ParsingConfig.__post_init__` that fires exactly when tagging is on and `jets` is cut but `bjets` is not. Run against seven cases, it fires for the bug shape and for a real config with `bjets:` stripped in memory, and stays silent in the other five (**VERIFIED BY RUNNING**, `scripts/test_bjets_warning.py`). It changes no behaviour — it only makes the mistake visible at config-load time.

### Count parsing for counts of 10 or more

Covered in full in section (d) under D01. Summary:

- Fork master reads **only the first character** of each count field, in four functions: `physics_calcs.limit_particles_in_fs`, `physics_calcs.is_finalstate_contain_combination`, `IMCalculator._limit_particles_in_fs`, `IMCalculator.does_final_state_contain_combination`. **VERIFIED BY RUNNING.**
- Upstream master reads **the whole number** in all four, fixed by **#34** (`f16768e`, 8 Oct 2026). **VERIFIED BY RUNNING.**
- Concretely, for a count of 10 or more: our version takes the first digit as the count and the second digit as the particle letter. The letter lookup fails, so `limit_particles_in_fs` leaves the label uncapped (`0e_2m_10j_1b` stays as it is, where upstream rewrites it to `0e_2m_4j_1b`), and `is_finalstate_contain_combination` silently skips that object type's requirement. The threshold at which the two first differ is a count of exactly **10** (**VERIFIED BY RUNNING**).
- **Can a delivered final state reach 10 of anything?** For light jets, **yes — observed**: labels with 10, 11 and 12 light jets appear in the fork's study evidence. For electrons, muons and b-jets, **not observed** — the Version B rule caps their total at 4, and the committed manifests top out at 3, 3 and 4. In the 14 committed four-dataset manifests the largest light-jet count is 4; counts of 5 through 9 and 12 appear in the broader study outputs. All **VERIFIED BY RUNNING**.
- **Does it change any delivered number?** No — proven over 171,774,906 cases, as set out under D01.

### The final-state rule difference

**This is the brief's item 6, and the brief's framing needs correcting.** Upstream has *two* rules, at two different stages, and the brief describes only the second.

**Rule 1 — upstream's parsing stage, `event_selection._filter_events_by_non_jet_object_total`, added by #31 (`88d7a4b`, 4 Oct 2026).** Constants `LIGHT_JET_FIELD = "Jets"` and `MAX_NON_JET_OBJECTS = 4`. It rejects an event whose non-light-jet objects, **summed**, exceed 4, and keeps every light jet.

**This is exactly our Version B rule.** Our delivery computes `n_electrons + n_muons + n_bjets` and keeps the event when that total is at most 4 (`run_dataset_on_file.py:2056-2058`; the rare4 delivery reuses the same mask at `:2146`). Tested upstream's own function against our rule over all 4,096 count patterns with e, m, j, b each 0–7: **0 disagreements**, both accepting 280 patterns (**VERIFIED BY RUNNING**, `tools/check_vb_vs_31.py`).

**Rule 2 — upstream's invariant-mass stage, `IMCalculator._is_valid_fs`, as #34 left it.** Rejects a final state if any **single** non-`Jets` type exceeds `max_k` (4); light jets are exempt. This is the rule the brief describes, and the description is accurate.

**Recomputing the disagreement count.** Counting range: e, m and b each 0–10 and j each 0–10, i.e. **14,641** count patterns. All **VERIFIED BY RUNNING** (`tools/check_composed.py`):

| comparison | patterns disagreeing (of 14,641) |
|---|---|
| upstream Rule 1 (#31 parsing) vs our Version B | **0** |
| upstream Rule 2 (#34 `_is_valid_fs`) vs our Version B | **991** |
| upstream Rule 1 **then** Rule 2, as the pipeline applies them, vs our Version B | **1** |

The 991 split into 990 patterns our Version B rejects and #34 alone accepts (any pattern with e+m+b of 5 or more where each type individually stays at 4 or below), plus 1 the other way. That 1 is the all-zero pattern (0,0,0,0): upstream's `min_n = 1` rejects an event with no objects, while Version B considered purely as a count rule accepts it — though the delivery's own `MIN_TOTAL_SELECTED_OBJECTS = 2` population gate rejects it earlier anyway.

**The honest conclusion: once both upstream rules are applied in sequence, as the upstream pipeline actually applies them, upstream's effective rule is Version B.** Rule 2's per-type cap is redundant after Rule 1, because a total of 4 or less forces every individual type to 4 or less. The two sides are not in conflict about the final-state rule.

**On the earlier "~270" figure.** I could not reproduce 270 for the range above. The nearest match is **271**, which comes out of the much narrower range e, m, b each 0–4 and j only 0–2 (375 patterns). The figure is sensitive to the range — the same comparison gives 451 over e,m,b,j each 0–4, and 1,171 over each 0–12. **Earlier figure not reproduced; the range it used was narrower than stated.** My primary figure is the 991 above, with its range given explicitly.

### Outlier split and histogram bin-edge alignment

**Both sides produce identical bin edges for the same input. Confirmed.**

`services/pipelines/post_processing_pipeline.py` is byte-identical on the two masters — sha256 `d1656580d3578864d9650d36ad07da9e84e20271a9212bf3ac6959d946e16ce1` on each (**VERIFIED BY RUNNING**). This is the file upstream PR **#27** (`8120fb8`, "Align outlier split to bin edges") changed, and the content check found **13 of 13** of that commit's added lines present in the fork. The fork carries #27 in full.

Run on 522 values spanning 94 to 2200 GeV with a 10 GeV width (**VERIFIED BY RUNNING**, `tools/check_edges.py`):

- `_aligned_bin_edges` returns **212 edges**, from 90.0 to 2200.0, every one a multiple of 10.0. The two sides' edge arrays are **byte-identical**.
- `_split_by_first_empty_bin` gives the same answer on both: 400 in the main array, 122 outliers, main array topping out at 138.1.
- `_find_rightmost_highest_peak` returns **110.0** on both.

The fork's own `test_exact_jet_labels.py` demonstrates why the alignment matters, and passes: the new grid gives a split at exactly 140.0 GeV with 10.0 GeV bins, where the old approach split at 162.8537 GeV with 9.9756 GeV bins.

### Histogram naming

**The fork's delivered names do NOT match upstream's exactly. One mismatch, in the width suffix.**

Upstream builds every histogram name as `f"ROI_{hist_name_base}_width_{bin_width}"` — the same f-string in four places. `bin_width` comes straight from the config and is never reformatted. Both masters set `bin_width_gev: 10.0`, which YAML reads as a Python float, and `domain/config.py` declares it `float = 10.0`. So upstream writes **`_width_10.0`**.

Our delivery can produce either form. Run (**VERIFIED BY RUNNING**, `test_width_suffix.py`, all checks pass):

- with `--upstream-width-suffix`: `ROI_mass_m0m1_cat_0ex_2mx_5jx_1bx_width_10.0` — character-for-character upstream's
- default: `..._width_10` — upstream's string minus the trailing `.0`

**All 9,793 histogram names across the 14 committed delivery manifests end in `_width_10`** (**VERIFIED BY RUNNING**). The delivered files used the default, not the upstream-matching switch.

Everything else about the names does match. `test_upstream_names.py` extracts upstream master into a temporary tree and calls upstream's own `_convert_to_bumpnet_name`, and our names agree string-for-string across every pilot final state and all 7 combination strings, including two-digit counts (`mass_j0j1j2j3_cat_0ex_1mx_11jx_0bx`, `mass_e0m0b0_cat_1ex_1mx_12jx_4bx`). Our per-event labels also equal upstream's own `group_by_final_state` output for all 34 synthetic test events (**VERIFIED BY RUNNING**).

One further naming note. The committed manifests use the **six-field** form (`0ex_1mx_0jx_0gx_0tx_2bx`, with photons and taus written as zero), while the current code produces the **four-field** form (`0ex_2mx_5jx_1bx`, omitting types the data does not carry) — which is upstream's current rule. So the delivered names are one naming generation behind the code, in two respects: the six-field form and the `_width_10` suffix.

### Anything that would make CMS and ATLAS histograms not directly comparable

Four things, in order of how much they matter:

1. **The `_width_10` vs `_width_10.0` suffix** (row D63). An automated comparison keyed on histogram name would simply not find the partner histogram. This is the one concrete, present-today blocker. Our code already has the switch; the delivered files did not use it.
2. **The six-field vs four-field category form.** Same class of problem: `0ex_1mx_0jx_0gx_0tx_2bx` and `0ex_1mx_0jx_2bx` describe the same event and do not match as strings.
3. **The electron–muon overlap removal at dR < 0.12** (row D64). We remove an electron within dR 0.12 of a selected muon, in all four datasets; the muon is kept. Radius approved by Maryna on 7 October 2026, raised from 0.05. **There is no overlap-removal code anywhere in shared code on either master** (**VERIFIED BY RUNNING**: no `0.12`, no `overlap_removal`, no `delta_r` in `domain/`, `services/`, `orchestration/` or `pipeline/` on either side, apart from two unrelated plot-label coordinates). Ours lives in study code. If ATLAS does not apply the same removal, the two experiments' lepton selections are not the same selection.
4. **The per-histogram minimum of 100 entries** (row D65). We keep only histograms with at least 100 entries; upstream's shared stage applies no minimum and keeps any histogram with at least one entry. Our `--no-hist-min-entries` switch reproduces upstream's floor of 1 (**VERIFIED BY RUNNING**). Different sets of final states survive on the two sides, so the two deliveries would not have the same list of histograms even with identical names.

Items 1, 2 and 4 are settings our own code already supports both ways; item 3 is a genuine physics choice.

---

## (f) Corrections to the September 2026 map and to the brief's "known history"

### Corrections to the brief

**C1 — Item 5 is backwards.** The brief says "#34 reportedly checks only the FIRST CHARACTER of an object-count string, and fork master's `services/calculations/physics_calcs.py` reportedly does the same." In fact **#34 is the fix**. Commit `f16768e` changes `str_amount_particle[0]` / `[1]` to `[:-1]` / `[-1]` in both `limit_particles_in_fs` and `is_finalstate_contain_combination` — and the same pair of changes again in `im_calculator.py`. Upstream master reads the whole number; **fork master still has the first-character behaviour**. The second half of the brief's sentence is right, the first half is not. **VERIFIED BY RUNNING** (`git show f16768e`, plus direct execution of both versions).

A nice independent corroboration: the fork's own `studies/cms_datasets/tests/test_electron_datasets.py` has a check that asserts upstream does *not* cap a 12-light-jet label. That check now **fails** — "ours 0e_2m_12j_1b, upstream 0e_2m_4j_1b" — because upstream has since fixed it. The test extracts upstream master into a temp tree and runs upstream's real code, so this is direct evidence that #34 landed after the test was written. 109 checks, 1 failure, and that is the failure (**VERIFIED BY RUNNING**).

**C2 — Item 6 is incomplete, and the two sides actually agree.** The brief contrasts "upstream #34 rejects an event if any SINGLE non-light-jet type exceeds 4" with "the fork's Version B rejects if electrons+muons+b-jets > 4 IN TOTAL". The description of #34 is accurate but it is only half of upstream's behaviour. Upstream also has `event_selection._filter_events_by_non_jet_object_total` from **#31**, which is the total-based rule — i.e. **Version B** — and verified identical to ours over 4,096 patterns. Applied in sequence, upstream's effective rule is Version B. Full numbers in section (e).

**C3 — Item 4's "#27 aligned outlier split" is already in the fork, in full.** The brief asks whether the fork has equivalent content. It has the identical content: `post_processing_pipeline.py` is byte-identical, and 13 of 13 of `8120fb8`'s added lines are present. Likewise the Z cut at 110 GeV is on both sides.

**C4 — Item 4's "xrootd timeout + retry": the fork has none of it.** Not partial — none. Upstream's `418bb1b` touched two files; the fork has neither change (`timeout=300` where upstream has `900`, no file-level retry, no 120-second xrootd timeout). The fork does have a *different* retry mechanism — a per-branch accessibility-probe retry — which is not the same thing and does not cover a stalled connection.

**C5 — Item 4's "#31 enforce objects_to_calculate": the fork has almost none of it.** 36 of 141 added lines present (26%). The parts the fork lacks include the `event_selection.py` additions, the `executor.py` statistics filter, and the `histograms_pipeline.py` label pattern. What the fork *does* have from #31's theme, it has in its own study code.

**C6 — `services/pipelines/histograms_pipeline.py` is not a direct import of the delivery.** The brief lists it among "known direct imports". It is imported only from inside a Python source string that a *test* file writes out and runs as a subprocess against an extracted copy of upstream master. No file under `cluster/` or `deliver/` imports it. The brief's other eight listed imports are all confirmed real.

**C7 — `services.calculations.physics_calcs` is imported as `from services.calculations import physics_calcs`,** i.e. as a submodule of a package, not as a dotted module path. Worth recording because a naive import scan misses it; my first trace did, and reported 11 shared modules instead of 14.

### Corrections to the September 2026 map (`docs/UPSTREAM_DIVERGENCE_MAP.md`, 2026-09-23)

The map is based on fork master `8cf737e` and upstream master `c296b927`. Both have moved, so it is out of date as a whole. Re-deriving its Tier 1 items against the current masters:

**C8 — T1-17 is no longer a whitespace-only difference, and its ADOPT conclusion no longer holds for the stated reason.** The map records `histograms_pipeline.py` as differing only in a blank line and a comment's position, "confirmed by whole-file AST equality". Today the difference in that file is **functional**: upstream's label pattern is the general `r"_FS_([0-9emjgtb_]+)_IM_..."` while the fork's is the restrictive `r"_FS_(\d+e_\d+m_\d+j_\d+g(?:_\d+t)?(?:_\d+b)?)_IM_..."`. Run on five signatures, upstream matches a four-field CMS label such as `0e_2m_5j_1b` and the fork's **does not match at all** — the code then `continue`s, silently skipping that signature (**VERIFIED BY RUNNING**). Upstream generalised the pattern in #31. Still ADOPT, but now for a real reason, with MEDIUM risk because the failure mode is a silent skip. This is row D52.

**C9 — T1-18 is resolved; there is no divergence left to adopt.** `services/storage/sqlite_shards.py` is now byte-identical on both masters (**VERIFIED BY RUNNING**). The map's long correction history about statement reordering is moot.

**C10 — T1-08/09/10/13 (the mass-units cluster) all still stand, unchanged.** `KNOWN_MASSES` still differs in units, upstream still converts unconditionally, the fork still has the `native_pt_unit` tags and the per-file gating. The map's corrected claim that the ATLAS exposure is **latent rather than live** also still stands: no config on either side selects `2025e-13tev-beta` (**VERIFIED BY RUNNING**).

**C11 — T1-02 through T1-07 (the b-jet cluster) still stand,** and I have strengthened them from reasoning to a reproduction. The map says the missing `bjets:` entry is "live, not hypothetical" for `config.short_parse_btag.yaml`; running upstream's code against upstream's config confirms it exactly.

**C12 — T1-20's "7 deleted test files" is now 36 fork-only test files.** Upstream still has no `tests/` directory. The fork has grown from 7 to 36. The map's NEEDS-DECISION verdict on whether to raise the question with upstream is unchanged by anything in the code.

**C13 — the map has no coverage of the October work,** which is where the live differences now are: #22, #27, #29, #31, #34, the xrootd work, the four-dataset delivery, exact light-jet labels, Version B, and the naming questions. That is not an error in the map, just its age.

### Confirmations of the brief's "known history"

**Item 1 — the Sept 2026 merged fixes are present.** A content-presence check over all 47 upstream-only commits (**VERIFIED BY RUNNING**, `tools/content_presence.py`, measuring what fraction of each commit's significant added lines appear in fork master's files):

- **19 commits at 100%**: `8120fb8` (#27), `96f5be6`, `d34e9f6`, `6d8c3f0`, `0d9461c`, `ae2e481`, `62efb89`, `6046a5b`, `55a065d`, `6f1f484`, `71e0d5d`, `db2132e`, **`d488f21`**, `3b32a3b`, `603d32d`, `df23978`, `31e6075`, `e80d90f`, `a2483df`.
- **5 commits at 95–97%**: `57a12eb`, `2487222`, `237e9b0`, `d53bed1`, `7dc6801` — the shortfalls are config values and docstring text, not logic.
- **`d488f21` (the silent collection-drop fix): 19 of 19 lines, present in full.** `_concatenate_events` and `_empty_particle_collection` are both in `domain/events.py` and the former is called at line 115. **Confirmed present, unmodified.**
- **The fixed-histogram-range trio.** `0d9461c` 100%, `6d8c3f0` 100%, `3464e1a` 78%. `3464e1a`'s 7 "missing" lines are 6 config values (run name, output directory, release list, file limits) plus one `bin_edges = np.arange(...)` line that #27 later rewrote, and 2 `global_ranges=None` arguments the fork no longer has a parameter for. The content that matters is present: `FIXED_MASS_MIN_GEV = 0.0` and `FIXED_MASS_MAX_GEV = 10000.0` are identical on both sides, and `post_processing_pipeline.py` is byte-identical. **Confirmed present, in a form later revised by #27 on both sides.**
- Two low scores that are **not** gaps: `b8d04f9` ("Fix bug in MC/data selection", 27%) was superseded by `71e0d5d`, which is present at 100%, and the fork's MC/data selection logic is line-for-line identical to upstream's today. `d98f2c3` (64%) — the fork has `prune_final_states_below_min_events` in `sqlite_shards.py` and calls it from `post_processing_pipeline.py:161`; upstream additionally calls it from the mass handler (row D48).

**Item 2(a) — `f43cc93` (`KNOWN_MASSES` in MeV with a divide-by-1000) is absent from fork master.** 0 of 3 significant added lines present. **Confirmed absent.** What upstream master does today: `KNOWN_MASSES` holds MeV values with the comment "Known masses in MeV (converted to GeV later by `_convert_array_to_gev`)", and `im_pipeline.process_final_state` calls `_convert_array_to_gev` (a multiply by 1e-3) on every computed mass, for every release, with no gate. CMS NanoAOD is already in GeV, so that path would shrink a CMS mass by 1000. Upstream issue #28 is open. All **VERIFIED BY RUNNING**.

**Item 2(b) — `6ff3c31` ("remove tests") is absent from fork master.** The commit is a deletion-only commit, so there are no added lines to look for; the direct check is that **upstream master has no `tests/` directory at all** while **fork master has 36 test files**. **Confirmed absent.** What upstream master does today: ships no test suite.

**Item 3 — the fork-only CMS work on master is all present**, and all of it is in the table: NanoAOD parsing (D30, D31), object fields and boolean cuts (D04, D05, D35), scalar event fields (D14, D30), the validated-runs golden-JSON filter (D18, D58), CMS trigger requirements (D17, D45), the b-jet cut fix plus the `domain/config.py` guard (D55, D36), and the four-dataset delivery under `studies/` with exact light-jet labels, Version B, the 110 GeV Z cut, the bin-aligned outlier split and upstream-form histogram names (D63, D64, D65 and section (e)). One qualification on "upstream-exact histogram names": the code can produce them, the delivered files did not — see section (e).

**Item 4 — each upstream item, precisely:**

| upstream item | does the fork have equivalent content? |
|---|---|
| **#22 trigger matching** (`bea982d`) | **None.** 30 of 188 added lines (16%). The fork has none of `apply_trigger_selection`, `_triggerMatch`, `SINGLE_LEPTON_TRIGGER_CHAINS`, `get_trigger_years`, `enable_trigger_matching` or `EventBatch.file_url`. Its own `trigger_requirements.py` is a different capability — a check that an HLT path *fired*, not a match of reco objects to trigger objects — and its CMS dR trigger matching lives in study code. Rows D13, D28, D29, D34, D39, D40, D46. |
| **#29 trigger-config wiring** (`fe5a560`) | **None.** 3 of 22 added lines (14%). The fork's `config.yaml` has no `trigger` key of any kind. Rows D28, D39, D46. |
| **#27 aligned outlier split** (`8120fb8`) | **Full.** 13 of 13 added lines; `post_processing_pipeline.py` byte-identical; Z cut 110.0 on both sides. Row D20. |
| **xrootd timeout + retry** (`418bb1b`) | **None.** 16 of 38 added lines (42%), and the 42% is shared boilerplate — the fork has neither the 120-second xrootd timeout, nor the 900-second per-file limit, nor the three-attempt backoff. Rows D16, D26. |
| **#31 enforce `objects_to_calculate`** (`88d7a4b`) | **Partial, mostly absent.** 36 of 141 added lines (26%). Present in spirit: the fork's delivery applies the Version B rule #31 introduced. Absent: the `event_selection.py` functions, the `domain/config.py` enforcement, the `executor.py` filter, the `histograms_pipeline.py` pattern, the `im_calculator` and `physics_calcs` label changes. Rows D03, D09, D32, D33, D38, D48, D51, D52, D57. |
| **#34 high-multiplicity light-jet final states** (`f16768e`) | **None.** 2 of 19 added lines (11%). Fork master is the pre-#34 code in both files. Rows D01, D02, D06, D07, D08. |

**Item 7 — confirmed; see section (g).**

---

## (g) Pending, outside master

Listed only, as the brief directs. None was merged, test-merged, or analysed in depth.

- **Upstream PR #35** (Yuval, ATLAS MC weighting, head `fa63544`) — open on upstream, not merged into upstream master, not in the fork; overlaps the fork's own `services/parsing/mc_weights.py` (row D54).
- **Upstream PR #23** — superseded, not merged.
- **Fork branch `feature/cms-mc-weights-v3`** — the CMS MC weighting work; it is on that branch and **not** on fork master, so it is outside this comparison.

---

## (h) DRAFT discussion points for Maryna

### DRAFT — NOT SENT

*Nothing below has been sent to anyone. No email, no message, no issue, no comment. These are notes for Matan to take into a conversation.*

**(i) Proposals to upstream**

- A certified-run ("golden JSON" / GRL-style) filter, with a guard that stops it ever being applied to simulation. Generic, default off (D18).
- An optional HLT trigger-path requirement filter, per-config and per-record, default off (D17).
- Release-tagged momentum units, so the MeV-to-GeV division happens only where it belongs. Defaults to converting, so nothing upstream uses today changes behaviour (D11, D12, D47).
- A warning when b-tagging is on and a config cuts light jets but not b-jets. Warning only, no behaviour change — and the failure it catches is live on upstream master today (D36, D55).
- Loud failure instead of silent omission for a missing required branch or object field, and an abort when more than 20% of a record's files fail to open (D30, D44).
- Generic per-object boolean cuts and an eta exclusion window, all opt-in no-ops when unset (D04, D05, D35).
- Cross-trigger-stream event de-duplication, plus the per-record selection it needs (D37, D43, D53).
- CMS Open Data URL classification for cache validation (D49, D50).

**(ii) Questions needing her decision**

- **The histogram width suffix.** Upstream writes `_width_10.0`; all 9,793 names in our delivered manifests say `_width_10`. Our code supports both. Should the delivered files be renamed to upstream's form so CMS and ATLAS histograms line up by name? (D63)
- **The category field count.** Our delivered names use the six-field form including `0gx_0tx`; our current code and upstream both use the four-field form that omits absent types. Which form is the reference? (section (e))
- **The electron–muon overlap removal at dR < 0.12.** She approved the radius for CMS on 7 October. Will ATLAS apply the same removal? Nothing in shared code does it on either side, so the two experiments' lepton selections differ until this is settled. (D64)
- **The per-histogram minimum of 100 entries.** Upstream's shared stage keeps any histogram with at least one entry. Should the delivery match that, or should upstream adopt a minimum? Different final states survive under the two rules. (D65)
- **The fallback particle-mass table** (`KNOWN_MASSES`, upstream issue #28). It does not affect our delivery, but it is unresolved in shared code. Is the release-tagged mechanism above the agreed fix? (D10)
- **Upstream's trigger matching (#22/#29).** It is ATLAS-shaped and we have none of it. Do we adopt it, keep our own path-requirement filter, or converge on something that serves both? (D13, D28, D29, D34, D39, D46)
- **Upstream's removal of its test suite** (`6ff3c31`). We now carry 36 test files upstream does not have. Worth asking why, and whether they would take them back.

**(iii) FYI**

- Upstream already has the Version B final-state rule, as `_filter_events_by_non_jet_object_total` from #31. Verified identical to ours over 4,096 count patterns. Her expectation that ATLAS would adopt Version B is already met in upstream's code.
- The whole shared-code divergence has **no effect on the delivered CMS data**: of 38 shared functions the delivery calls, 30 are identical, 7 are ours alone, and the single one that differs was proven equivalent over 171,774,906 cases.
- We are missing #34, which fixes a count-reading bug our copy still has. It is harmless for this delivery and worth taking anyway.
- We are missing upstream's network-robustness work (120-second xrootd timeout, three-attempt retry with backoff). No physics effect; it only helps a job survive a stalled CERN connection.
- Our fork's `test_electron_datasets.py` now has one failing check, and the failure is correct behaviour: it asserts upstream does not cap a 12-light-jet label, and upstream now does. The test needs updating when we take #34.
- The fork's test suite: 346 passed, 7 failed, 11 skipped. All 7 failures are Windows temporary-file-locking errors during cleanup, not code defects.

---

## (i) Appendix

### Appendix A — full file lists

**Shared code and root-level files that differ (25).** `M` = modified on both sides, `A` = fork-only.

```
M  domain/config.py                                   M  services/parsing/event_selection.py
M  domain/events.py                                   M  services/parsing/file_parser.py
M  domain/statistics.py                               A  services/parsing/mc_weights.py
M  orchestration/handlers/fetch_metadata_handler.py   M  services/parsing/root_io.py
M  orchestration/handlers/mass_calculation_handler.py M  services/parsing/schemas.py
M  orchestration/handlers/parsing_handler.py          M  services/parsing/threaded_processor.py
A  pbs_m0m1j0_fullscale.sh                            A  services/parsing/trigger_requirements.py
A  pbs_m0m1j0_smoketest.sh                            A  services/parsing/validated_runs.py
M  pipeline/executor.py                               M  services/pipelines/histograms_pipeline.py
M  services/calculations/consts.py                    M  services/pipelines/im_pipeline.py
M  services/calculations/im_calculator.py             M  submit_mc.sh
M  services/calculations/physics_calcs.py
M  services/metadata/fetcher.py
A  services/parsing/event_deduplication.py
```

**Config files (23).** 18 fork-only, 5 modified on both.

```
A  config.atlas_scale_test.yaml          A  config.cms_hgg_signal_wplush.yaml
A  config.cms_bjet_test.yaml             A  config.cms_hgg_signal_zh.yaml
A  config.cms_fourrecord_test.yaml       A  config.cms_hgg_zee_data.yaml
A  config.cms_hgg_data.yaml              A  config.cms_hgg_zee_dy.yaml
A  config.cms_hgg_signal.yaml            A  config.cms_m0m1j0_fullscale.yaml
A  config.cms_hgg_signal_ggh.yaml        A  config.cms_m0m1j0_smoketest.yaml
A  config.cms_hgg_signal_tth.yaml        A  config.cms_partb_verify.yaml
A  config.cms_hgg_signal_vbf.yaml        A  config.cms_production_test.yaml
A  config.cms_hgg_signal_wminush.yaml    A  config.cms_zpeak_test.yaml
M  config.cms_records_master.yaml        M  config.short_parse_btag.yaml
M  config.cms_singleelectronsinglemuon.yaml  M  config.short_parse_local.yaml
M  config.yaml
```

`configWmaxTotal_up4j_minEvt100_subleading.yaml` exists on both sides and is **identical** — 79 keys compared, 0 differ.

**Fork-only test files (36).**

```
tests/test_background_model.py                  tests/test_merge_zee_outputs.py
tests/test_bias_diagnosis.py                    tests/test_object_fields_and_bool_cuts.py
tests/test_bias_rerun_merge.py                  tests/test_output_blinding.py
tests/test_bias_rerun_seed_identity.py          tests/test_parse_mc_selection.py
tests/test_cms_metadata_cache_validation.py     tests/test_partial_reads_with_weights.py
tests/test_config_records_registered.py         tests/test_pbs_scripts.py
tests/test_dedup_simulation_guard.py            tests/test_probe_retry.py
tests/test_final_background_model.py            tests/test_profile_likelihood.py
tests/test_global_final_state_threshold.py      tests/test_run_selection_on_chunks_roundtrip.py
tests/test_issue_10_legacy_leptons.py           tests/test_run_zee_selection_on_chunks_roundtrip.py
tests/test_issue_13_partial_file_reads.py       tests/test_scalar_event_fields.py
tests/test_issue_6_required_selection.py        tests/test_selection_equivalence.py
tests/test_mass_calculation_stats.py            tests/test_signal_model.py
tests/test_mc_weights.py                        tests/test_stats_model.py
tests/test_merge_full_range_write.py            tests/test_trigger_requirements.py
tests/test_merge_outputs.py                     tests/test_unblind_gate.py
                                                tests/test_unregistered_record_schema.py
                                                tests/test_validated_runs.py
                                                tests/test_xrootd_source_selection.py
                                                tests/test_zee_validation.py
```

Plus 4 study-level test files under `studies/cms_datasets/tests/`: `test_electron_datasets.py`, `test_exact_jet_labels.py`, `test_upstream_names.py`, `test_width_suffix.py`.

**Fork-only scripts (8).**

```
scripts/bjet_check.py                 scripts/make_cms_report.py
scripts/dedup_check.py                scripts/test_bjets_warning.py
scripts/m0m1j0_mumujet_report.py      scripts/verify_bjets_kinematic_cut_fix.py
                                      scripts/zpeak_check.py
                                      scripts/zpeak_postproc_check.py
```

**Fork-only data (2).**

```
data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt
data/cms/validated_runs/README.md
```

**Fork-only logs (3).**

```
logs/hgg_stats/job_list.txt   logs/hgg_stats/job_list_retry1.txt   logs/hgg_stats/run1_result.md
```

**Fork-only reports (33).** 8 Markdown summaries, 3 text/JSON outputs, 22 PNG plots, across `reports/cms_bjet_first_test/`, `cms_bjets_cut_fix/`, `cms_production_singleelectron/`, `cms_production_test/`, `cms_singlemuon_support/`, `m0m1j0_mumujet_smoketest/` and `m0m1j0_mumujet_sync_verification/`.

**Fork-only docs (4),** outside this comparison's scope but listed for completeness: `docs/BRANCH_LAYOUT.md`, `docs/CMS_KNOWN_LIMITATIONS.md`, `docs/UPSTREAM_SYNC_SAFE16_VERIFICATION.md`, `docs/UPSTREAM_SYNC_TRIAGE.md`.

### Appendix B — the import and call graph

In `cms_delivery_call_graph.md`, alongside this file. It contains the scope of the trace, all 14 reached shared modules with their fork-vs-upstream status, the shared modules that differ but are never reached, a function-by-function REACHED / not-reached table for all 80 definitions, the written-out call paths, and the trace's honest limits.

### Appendix C — commands run

Set-up and verification of the starting facts:

```
git clone https://github.com/MatanBerko/atlas-utilization.git fork
git remote add upstream https://github.com/Zhavi221/atlas-utilization.git
git remote set-url --push upstream DISABLED
git remote -v                              # confirms upstream push URL is DISABLED
git fetch upstream
git rev-parse origin/master upstream/master
git merge-base origin/master upstream/master
git rev-list --count upstream/master..origin/master
git rev-list --count origin/master..upstream/master
git diff --stat upstream/master origin/master
git diff --name-only upstream/master origin/master | wc -l
git diff --name-only upstream/master origin/master | grep -v -E '^(studies|docs)/' | wc -l
git diff --name-status upstream/master origin/master | grep -E '^D'      # no output: no deletions
git ls-tree --name-only upstream/master:services/parsing/
git ls-tree --name-only origin/master:services/parsing/
git log --oneline --pretty='%h %ad %an %s' --date=short 388b86c..upstream/master
git show origin/docs/upstream-divergence-map:docs/UPSTREAM_DIVERGENCE_MAP.md
git diff upstream/master origin/master -- <each differing path>
git show f16768e / 88d7a4b / bea982d / fe5a560 / 8120fb8 / 418bb1b / d488f21 / f43cc93
```

Throwaway worktree, for running upstream's own code side by side with the fork's:

```
git worktree add ../wt_upstream upstream/master
# ... all checks below ...
git worktree remove ../wt_upstream --force
git worktree prune
```

Analysis and verification scripts (all written for this task; none committed to the repository):

| script | what it establishes |
|---|---|
| `tools/trace2.py` | Transitive import graph from all 104 files under `studies/cms_datasets/` into shared code, following study-to-study imports; handles `from package import submodule` and imports nested inside functions |
| `tools/fngraph.py` | Function-level REACHED / not-reached map, with class constructors resolved to `__init__` |
| `tools/fn_identity.py` | AST comparison of every reached function between the two masters — the 30 / 7 / 1 result |
| `tools/strimports.py` | Finds shared imports hidden inside string literals (how `histograms_pipeline` is reached) |
| `tools/check_counts.py` | The 186-combination set and its maximum `start + count` of 4 |
| `tools/check_field.py` | Per-field count-parsing equivalence: 976 triples, 0 disagreements |
| `tools/check_exhaustive.py` | Whole-label equivalence: 171,774,906 pairs, 0 disagreements; `limit_particles_in_fs` first differs at a count of 10 |
| `tools/check_rules.py` | Version B vs #34 `_is_valid_fs` across several counting ranges |
| `tools/check_vb_vs_31.py` | Upstream #31's parsing rule vs Version B: 4,096 patterns, 0 disagreements |
| `tools/check_composed.py` | Upstream #31 then #34 composed, vs Version B: 1 disagreement (the all-zero pattern) |
| `tools/check_edges.py` | Bin edges, Z cut, outlier split and peak detection identical on both sides; sha256 of `post_processing_pipeline.py` |
| `tools/check_bjets.py` | Reproduces the uncut-b-jet behaviour with upstream's own code and config |
| `tools/cfg_diff.py` | Key-by-key diff of all 6 configs present on both sides |
| `tools/cfg_bjets.py` | Audit of `enable_jet_tagging` and `bjets:` across all 6 upstream and 24 fork configs |
| `tools/content_presence.py` | Per-commit content-presence percentages for all 47 upstream-only commits |
| `tools/missing_lines.py` | The exact lines missing for the partially-present commits |
| `tools/make_csv.py` | Generates `differences.csv` |

Existing test suites run (fork master only — upstream master has no test suite):

```
PYTHONPATH=. python -m pytest tests/ -q          # 346 passed, 7 failed, 11 skipped
PYTHONPATH=. python studies/cms_datasets/tests/test_width_suffix.py        # ALL CHECKS PASSED
PYTHONPATH=. python studies/cms_datasets/tests/test_upstream_names.py      # ALL CHECKS PASSED
PYTHONPATH=. python studies/cms_datasets/tests/test_exact_jet_labels.py    # ALL CHECKS PASSED
PYTHONPATH=. python studies/cms_datasets/tests/test_electron_datasets.py   # 109 checks, 1 failure (see C1)
PYTHONPATH=. python scripts/test_bjets_warning.py                          # warning fires only for the bug shape
```

The 7 pytest failures are all `PermissionError: [WinError 32]` raised by Python's `tempfile` cleanup while a SQLite handle is still open — a Windows file-locking artefact of the test harness, in `tests/test_global_final_state_threshold.py` (5) and `tests/test_mass_calculation_stats.py` (2). Not code defects. **UNVERIFIED** on Linux, where they would be expected to pass.

No production was run. No remote data was read over xrootd. The Weizmann cluster was not used.

### Appendix D — what is AMBIGUOUS or UNVERIFIED

- **AMBIGUOUS — which histogram naming generation is the reference.** The committed manifests use the six-field category form with `_width_10`; the current code produces the four-field form and can produce `_width_10.0`. Reading 1: the delivered files are the reference, and upstream should be asked to accept them. Reading 2: upstream's current form is the reference, and the delivery should be renamed. The code supports both and I am not picking one. (D63, section (e))
- **AMBIGUOUS — whether #34's per-type cap is intended as a standalone rule.** Reading 1: it is a second, independent safety net, in which case upstream's two rules are deliberately belt-and-braces and the 991-pattern difference against Version B is real but unreachable. Reading 2: it is redundant after #31's parsing filter and was simply not revisited. The code supports both readings; only its authors can say which.
- **UNVERIFIED — behaviour under real data.** Every equivalence claim here was established on synthetic inputs and on the real code, never by re-running the delivery. The brief rules out production runs and xrootd reads, and I did not do either.
- **UNVERIFIED — the 7 pytest failures on Linux.** They are Windows file-locking artefacts; I did not confirm they pass on Linux.
- **UNVERIFIED — the earlier "~270" disagreement figure.** Not reproduced for the range I used. 271 comes out of a much narrower range (e, m, b each 0–4, j only 0–2). My figure is 991, with the range stated.
- **Not observed, rather than impossible** — three places where I am deliberately using the weaker word: counts of 10 or more are **not observed** in the committed four-dataset manifests (they are observed in the wider study evidence); the `KNOWN_MASSES` dictionary branch is **not observed** to be taken by the delivery; and a config selecting `2025e-13tev-beta` is **not observed** on either master.
- **Static tracing limits.** Set out in `cms_delivery_call_graph.md` section 5.6: name-based call resolution, two colliding shared names resolved by hand, `getattr` used only with literal attribute names, and no dynamic import anywhere on a delivery path.
