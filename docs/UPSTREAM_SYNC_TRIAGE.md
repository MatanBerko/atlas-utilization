# Upstream sync triage — 2026-09

Fetched `upstream` (github.com/Zhavi221/atlas-utilization) and compared
`upstream/master` against my fork's `origin/master`. Merge base: `388b86c`
(2026-08-31). Upstream is 41 commits ahead of fork master; fork master is
10 commits ahead of upstream (untouched by this triage — see "My fork's own
10 commits" at the end). Every commit below was read via its actual diff
(`git show <hash>`), not inferred from its subject line. 13 of the 41 are
merge commits with no independent content of their own — noted at the end,
not re-litigated per-commit.

Two known bugs this triage checks every commit against:
- **(a)** `Muons_looseId` / `Muons_pfRelIso04_all` silently dropped when
  parsing merges many batches together (found on `analysis/m0m1j0-mumujet`).
- **(b)** Silent parsing failures / records yielding zero events (the
  general bug class the loud-failure guard on `analysis/m0m1j0-mumujet`
  was built for).

---

## ALREADY PRESENT — fork already has these, verified by reading the code, not just the message

### `e80d90f` "FIx incorrect particle mass field"
Changes `get_particle_known_mass`/`_get_particle_mass` (physics_calcs.py,
im_calculator.py) to read a particle's own `'mass'` field instead of a
nonexistent `'m'` field. **My fork's `origin/master` already contains this
exact code, verified byte-for-byte**:
```python
def get_particle_known_mass(particle_type: str, particle_array: ak.Array) -> ak.Array:
    if 'mass' in particle_array.fields:
        return particle_array['mass']
    return consts.KNOWN_MASSES.get(particle_type, 0.0)
```
Skip — cherry-picking would be a no-op at best, a spurious conflict at worst.

### `603d32d` "Fix jet/bjet confusion"
Removes a `find_actual_field_name()` helper that matched collection names by
**substring** (`if obj_name in field`) instead of exact match — since
`"Jets"` is a substring of `"BJets"`, this could silently confuse the two
collections. **My fork's `origin/master` already has no such function** and
already does exact `if obj not in events.fields` checks throughout
`physics_calcs.py`. Additionally, this upstream commit's own diff introduces
a log-statement placement bug in `slice_events_by_field` (the "Could not
find" warning ends up on the branch where the object *was* found, not where
it's missing) — my fork's existing code doesn't have that bug either; it's
already correctly placed. Skip — fork's version is not just equivalent but
strictly better than this commit's own end state.

### `3b32a3b` "Fix IM combination multiplicity limit bug"
Removes an `elif is_exact_count:` branch in `filter_events_by_particle_counts`
that forced an *exact* particle-count match instead of "at least N", and
(in the same commit) fixes the log-placement bug `603d32d` had just
introduced. **My fork's `origin/master` already matches this commit's final
state exactly** — no `elif is_exact_count` branch, log line already
correctly placed. Skip.

**All three of the task's named candidates are confirmed present**, plus
this triage found no additional undisclosed ALREADY PRESENT commits beyond
these three (every other commit was checked against fork master's actual
code and genuinely differs).

---

## NEEDS MY DECISION — would change output of existing work, or previously declined

### `d488f21` "Union instead of intersection for object types" — **excluded, as instructed**
Replaces `ak.concatenate([batch.events for batch in batches])` with a
per-collection concatenation that preserves a collection even when only
*some* files/batches have it (previously: concatenating batches with
different top-level fields silently kept only fields common to *every*
batch — e.g. one file with no electrons would delete "Electrons" from every
event in the merged chunk).
**Relevant to known bug (a), but I don't think it actually fixes it**: this
operates at the *top-level collection* granularity (Electrons/Muons/Jets
present-or-absent), not the *within-collection sub-field* granularity our
bug shows (Muons present in every batch, but `Muons.looseId` present in only
some). Even if adopted, I'd expect it to leave bug (a) unfixed, because the
nested `ak.concatenate` call it makes per-collection would hit the exact
same union-vs-intersection problem one level down. Excluded per your
instruction regardless; noted here only because you asked me to flag
relevance to the known bug explicitly.

### `3464e1a` "use fixed histogram range [0, 10000] GeV, align peak detection bins" — **excluded, as instructed**
Only touches `services/pipelines/histograms_pipeline.py`,
`services/pipelines/post_processing_pipeline.py`, `config.yaml`,
`submit_mc.sh` — the generic histogram-creation pipeline stage.
**Doesn't touch m0m1j0 either way**: `scripts/m0m1j0_mumujet_report.py`
builds its own histogram directly with `numpy`/`uproot`, with its own
hardcoded `[0, 1000]` GeV / 10 GeV-bin constants, and never imports
`histograms_pipeline.py`. Excluded as instructed; would have been a no-op
for m0m1j0 even if included.

### `0d9461c` "make fixed histogram ranges merge-safe" — **excluded (depends on `3464e1a`)**
Directly imports and uses `3464e1a`'s `FIXED_MASS_MIN_GEV`/`MAX_GEV`
constants and its `trim_empty_tails_in_file` function. Cannot be taken
without `3464e1a`. Same "doesn't touch m0m1j0" reasoning applies.

### `6d8c3f0` "fix: remove obsolete histogram range scan" — **excluded (depends on `3464e1a`)**
Removes the `global_ranges.json` scan-and-pass-through machinery that only
becomes obsolete once `3464e1a`'s fixed-range approach replaces it. Same
dependency chain, same exclusion, same "doesn't touch m0m1j0" reasoning.

### `f43cc93` "FIx incorrect KNOWN_MASSES units" — **flagging as a new NEEDS MY DECISION item; not in your original list of two**
Changes `KNOWN_MASSES` (services/calculations/consts.py) from GeV values
(`Muons: 0.105`, `Electrons: 0.000511`, `Taus: 1.77686`) to MeV values
(`105.6583755`, `0.51099895069`, `1776.93`), with a new comment: "Known
masses in MeV (converted to GeV later by `_convert_array_to_gev`)".

This is only correct under upstream's assumption that the MeV→GeV `×1e-3`
conversion is *unconditionally* applied downstream to every mass this table
feeds. **My fork's code does not make that assumption** — it has a
schema-aware `schema_needs_mev_to_gev_conversion()` gate (see
`docs/M0M1J0_SPEC_INVESTIGATION.md`) that explicitly *skips* the ×1e-3
conversion for CMS NanoAOD (GeV-native) data, specifically to avoid the
factor-of-1000 bug this project has hit before. If `KNOWN_MASSES` is ever
used as a fallback for a CMS collection that happens to lack its own
`'mass'` field (currently none do — Electrons/Muons/Jets/Photons/Taus all
carry `mass` in the `cms-nanoaod` schema — but this is a latent landmine,
not a structural guarantee), this table would silently hand back an MeV-scale
number into a pipeline that never rescales it for CMS. I'm not taking this
without your say-so: it changes a physics constant's meaning project-wide,
and the risk is specifically in the unit-consistency work this fork has
already done that upstream doesn't seem to model.

---

## RELEVANT TO A KNOWN BUG

### Bug (a) — muon looseId / pfRelIso04_all dropped during chunk merging

**`6046a5b` "fix: use native uproot source for XRootD" — I think this
plausibly fixes it, and it's the strongest candidate.** Adds
`services/parsing/root_io.py::open_root_file()`, which forces uproot's
*native* XRootD source instead of its default fsspec-based one, with this
comment: "Uproot's default fsspec XRootD backend maintains a background
file-handle cache. Its cache pruner can race with active/closed handles and
emit an unhandled `Invalid operation` exception." That is exactly the class
of intermittent, per-read failure I hypothesized when I found bug (a): my
working theory (documented on `analysis/m0m1j0-mumujet`) is that
`_filter_accessible_branches`'s single-entry test read intermittently fails
for *some* batches over XRootD, silently excluding an optional field
(`looseId`, `pfRelIso04_all`) from that batch's schema, after which
concatenating batches with inconsistent field sets drops the field
project-wide. A race condition in the XRootD handle cache is a very
plausible cause of exactly that kind of intermittent per-batch failure.
I can't be certain without testing — **this is what Stage 3 actually
tests.**

**`d488f21`** — relevant in spirit (see NEEDS MY DECISION above) but
excluded per instruction, and I don't think it would have fixed this
specific bug even if included (wrong granularity).

**`57a12eb`** (see bug (b) below) — same general "silent data loss across
batches" theme, but addresses a different mechanism (a batch read throwing
an exception entirely, not a field being silently absent from an otherwise-
successful read). Tangential to (a), not a direct fix.

### Bug (b) — silent parsing failures / records yielding zero events

**`a2483df` "FIx silent file parsing bug"** — guards
`obj_events.pop("DirectObjects")` with `if "DirectObjects" in obj_events.keys()`.
Previously this would `KeyError` whenever a schema's `direct_objects` ends up
empty for a file, crashing that file's parse — caught per-file elsewhere as
a failure, silently reducing that record's retained-event count with no
obvious signal beyond a lower-than-expected retention percentage. Directly
relevant; genuine fix.

**`57a12eb` "fix: preserve events before partial ROOT read failure"** — the
strongest match for this bug class. Previously, if a batch *within* a file
failed to read partway through (network blip, corrupted basket), the code
did `continue`: silently skipping that batch and reporting the file as a
full, unqualified success — with fewer events than it should have had, no
warning, and no trace in the retention numbers pointing at why. This commit
makes that condition raise a proper `PartialFileReadError` carrying the
events actually read plus the underlying cause, has it counted as a
(partially-)failed file with the completed prefix preserved, and is backed
by real tests (`tests/test_issue_13_partial_file_reads.py`, not part of my
SAFE TO TAKE set — see "remove tests" below). This is precisely "silent
[...] records yielding [fewer events than they should]" turned loud.

**`df23978` "Fix key error upon b-tagging"** — same KeyError-guard pattern
as `a2483df`, but only reachable when `enable_jet_tagging=True`. None of my
CMS configs (including m0m1j0's) enable jet tagging, so this is real but
low-relevance for my own work specifically.

**`6f1f484` "fix: enforce required parsing selections"** — converts several
silent-degrade paths in `filter_events_by_particle_counts` /
`filter_events_by_kinematics` into either a hard `ValueError` or a correctly
*enforced* exclusion. Previously, if a particle collection a `particle_counts`
rule required was entirely missing from a batch, the code just `continue`d —
silently **not enforcing that requirement at all**, letting events through
that shouldn't have passed. The fix instead masks those events out. This
doesn't manifest as literally "zero events" but is the same family of bug:
a configured requirement silently not being applied. Verified this doesn't
change m0m1j0's own behavior (our `particle_counts`/`kinematic_cuts` only
ever reference `pt`/`eta`, which are always present in the CMS schema, so
the new exception paths are never hit by our config) — SAFE TO TAKE, but
also worth flagging as on-topic for bug (b).

---

## SAFE TO TAKE

Every commit below was read in full; none touches a file our m0m1j0
configuration or `scripts/m0m1j0_mumujet_report.py` path actually exercises
in a way that changes behavior, or the change was verified not to alter our
specific code path.

| Commit | Subject | Why safe |
|---|---|---|
| `31e6075` | Fix division-by-zero in DL1d calculation | ATLAS PHYSLITE b-tagging branch only (`BTagging_AntiKt4EMPFlowAuxDyn.DL1dv01_*`); CMS uses `Jet_btagDeepFlavB`, a different code path entirely. Doesn't touch CMS. Genuine numerical-safety fix. |
| `a2483df` | FIx silent file parsing bug | See bug (b) above. |
| `df23978` | Fix key error upon b-tagging | See bug (b) above; low relevance since we don't enable jet tagging, but harmless and correct either way. |
| `55a065d` | fix: split legacy combined leptons by flavor | Only activates for release years `"2016e-8tev"`/`"2025e-13tev-beta"`; explicitly returns unchanged for everything else, `cms-nanoaod` included. Verified by reading the guard clause. |
| `57a12eb` | fix: preserve events before partial ROOT read failure | See bug (b) above. |
| `6046a5b` | fix: use native uproot source for XRootD | See bug (a) above. |
| `6f1f484` | fix: enforce required parsing selections | See bug (b) above; verified our own config never reaches the new exception paths. |
| `71e0d5d` | fix: make parse_mc select the requested dataset mode | Rewrites ATLAS release-year `_mc`-suffix pairing logic. Verified: for `specific_record_ids`-based CMS parsing (`release_years: []`, keys like `record_30522`), the new `select_metadata_for_parsing()` takes the `key.startswith("record_")` branch and passes our keys through unchanged regardless of `parse_mc` — same as the old code's behavior for us. |
| `b8d04f9` | Fix bug in MC/data selection | Builds on `71e0d5d` (adds `normalize_release_year` import/usage to the same area); confirmed against upstream's actual final `parsing_handler.py` that both commits together produce a well-defined, working end state. Same "record_ prefix passes through unchanged" reasoning applies to us. |
| `62efb89` | fix: persist pipeline timing statistics | Generic mass-calc/post-processing/histogram stage instrumentation only (`pipeline/executor.py`, the three orchestration handlers, `sqlite_shards.py`). m0m1j0 runs `--tasks parsing` only and never touches these handlers. |
| `ae2e481` | fix error with calculation of invariant mass distribution out of final states with less than 100 events | Touches `im_calculator.py` (a `group_by_final_state` refactor) and the generic mass-calc handler/config. `scripts/m0m1j0_mumujet_report.py` never imports `IMCalculator` — computes masses directly. |
| `d98f2c3`, `7dc6801`, `d53bed1`, `db2132e` | final-state-threshold fix chain | All four confined to `orchestration/handlers/mass_calculation_handler.py`, `.../post_processing_handler.py`, `services/pipelines/post_processing_pipeline.py`, `services/storage/sqlite_shards.py`, plus one new test file and one `domain/config.py` field addition. Verified the *net* semantic diff across the whole chain (past the CRLF churn — see next row) is a legitimate, incremental fix to how `min_events_per_fs` is enforced in the generic mass-calc/post-processing stage. m0m1j0 doesn't use that stage. |
| `237e9b0`, `2487222` | final-state-threshold fix + CRLF cleanup | Same files as the row above; `237e9b0` accidentally introduced CRLF line endings across ~1,369 lines, `2487222` reverts the churn ("chore: remove CRLF churn" is its own subject). Diffed the tree before `237e9b0` against after `2487222` directly: the real net change matches the small, legitimate commits in the row above — no extra hidden change. `config.yaml` also gets 2 lines touched here; not our config file. |
| `d34e9f6`, `96f5be6` | small config gix / Minor config fixes | Only touch `config.yaml`, the project's shared default template — not any `config.cms_m0m1j0_*.yaml` file. No effect on m0m1j0 either way. |

**On `6ff3c31` "remove tests" — recommending we *not* take this one commit,
despite the "safe" bucket its siblings are in.** Several of the commits
above (`55a065d`, `57a12eb`, `6046a5b`, `6f1f484` [as `test_issue_6_...`],
`71e0d5d`, `62efb89`) each added their own test file under `tests/`; this
later commit deletes all of them in one shot. It isn't a bug fix — it
doesn't change any runtime behavior at all, only test-suite bookkeeping —
so it doesn't cleanly belong in any of the four buckets. My fork currently
has no `tests/` directory at all, so keeping these costs nothing and gives
free regression coverage for the fixes we're importing. I'm treating this
as a repo-hygiene call, not a physics/analysis judgment call, so I'm not
stopping to ask about it — but flagging it here so you can audit that
decision. If you'd rather match upstream's own final state exactly (no
tests), say so and I'll remove them.

---

## Merge commits — no independent action needed

13 of the 41 commits are `Merge pull request`/`Merge branch` commits:
`c296b92`, `f16c9cc`, `87139d3`, `712ac58`, `771261f`, `017dfe4`, `fb086aa`,
`d03d260`, `f775191`, `1ca1bfc`, `0631300`, `63aa29a`, `d2b4af3`. Each one
combines branches whose real commits are already individually triaged
above; none introduces its own additional diff content beyond its parents
(checked each one's own diff size — all small and consistent with a plain
merge, no surprise conflict-resolution edits hiding extra changes). No
separate handling needed: cherry-picking the real commits above achieves
the same end state as these merges would.

---

## My fork's own 10 commits (on `origin/master`, not this triage's subject)

These are untouched by this triage and will be verified as preserved after
the sync (see final summary) — listed here only for completeness since they
explain why `origin/master` and `upstream/master` diverge in both
directions, not just one:

```
0ae86dc Warn when jet tagging is enabled but bjets: kinematic cut is missing
e1702e3 Add missing bjets: kinematic-cuts entry to 9 CMS configs
2eb2ec5 CMS: per-trigger-stream selection + de-duplication for SingleMuon support
38b900c CMS: verify PR#17 cherry-picks (Part B), first b-jet test (Part C), doc update (Part D)
0d0ca45 Fix IM combination multiplicity limit bug
47f0a54 Fix jet/bjet confusion
84f4ceb FIx incorrect particle mass field
bd051be CMS: scope to SingleElectron records, larger production run, known-limitations doc
bbe2eb2 Fix histogram stage crash on missing global_ranges.json + add CMS report
e848f4d Make MeV->GeV invariant-mass scaling schema-aware
```

Note `84f4ceb`, `47f0a54`, `0d0ca45` — these are my fork's own independent
fixes for the exact same three bugs upstream's `e80d90f`/`603d32d`/`3b32a3b`
fix, confirming the ALREADY PRESENT bucket above from the other direction:
both sides independently arrived at (functionally, for `84f4ceb`/`0d0ca45`;
better, for `47f0a54`) the same fix.

`e848f4d` "Make MeV->GeV invariant-mass scaling schema-aware" is the commit
that introduced `schema_needs_mev_to_gev_conversion()` — the mechanism the
`f43cc93` NEEDS MY DECISION item above would put at risk if adopted blindly.
