# Upstream Divergence Map

Read-only inventory of every code/config difference between Matan's fork
(`MatanBerko/atlas-utilization`) and upstream (`Zhavi221/atlas-utilization`),
in two tiers, with a physics-impact assessment and classification for each.

**This document proposes nothing to upstream itself.** Part 3's "draft GitHub
issues" are plain text living only in this file. Nothing in this task opened,
commented on, or pushed to anything except this fork's own new branch.

Fetch date/time: **2026-09-23, 11:14 JDT** (session clock). All facts below
were re-verified fresh at that time via `git diff`/`git show`/`git log`
against the live `origin` and `upstream` remotes — nothing here is carried
over from memory or from an earlier draft.

---

## Part 0 — Verified baseline

### Remotes and safety guard

```
origin    https://github.com/MatanBerko/atlas-utilization.git (fetch)
origin    https://github.com/MatanBerko/atlas-utilization.git (push)
upstream  https://github.com/Zhavi221/atlas-utilization.git   (fetch)
upstream  DISABLED_NEVER_PUSH                                  (push)
```

The `upstream` remote's push URL is already a non-functional placeholder
string, pre-configured before this task, as an extra safety guard against an
accidental write. This task added nothing to that guard and relied on it as
one more layer, not the only one — no `git push` command in this task ever
named `upstream` as a target.

### Key commits (all confirmed by direct `git rev-parse` / `git log`, not assumed)

| Ref | SHA |
|---|---|
| `origin/master` | `8cf737e1acf0fa736b78864e631dc6cc98e05772` |
| `upstream/master` | `c296b9276f8bcfff2df938b505ac23593779bada` |
| `origin/feature/hgg-selection-and-output` | `f33d8d47a060082d70c4dd1451e81ad29cd0950d` |
| `origin/analysis/m0m1j0-cms` | `08c23092be4e1abb5f735e406377c21c1901b1d4` |
| `docs/upstream-divergence-map` (this branch) | branched from `origin/master` @ `8cf737e`, no other commits yet |

`git rev-list --left-right --count origin/master...upstream/master` →
**60 ahead / 41 behind** — matches the brief exactly.

### Tier 1 scope confirmed exactly

`git diff --name-status origin/master upstream/master` shows **13 files
with content differences** (`M`), separable cleanly from everything else:

```
M  config.cms_records_master.yaml
M  config.cms_singleelectronsinglemuon.yaml
M  config.short_parse_btag.yaml
M  config.short_parse_local.yaml
M  domain/config.py
M  orchestration/handlers/mass_calculation_handler.py
M  orchestration/handlers/parsing_handler.py
M  services/calculations/consts.py
M  services/parsing/file_parser.py
M  services/parsing/schemas.py
M  services/pipelines/histograms_pipeline.py
M  services/pipelines/im_pipeline.py
M  services/storage/sqlite_shards.py
```

= exactly "9 code files + 4 config files" as the brief claimed. A further 62
files show as `D` (fork has them, upstream doesn't) — of these, this document
itemizes the two the brief called out specifically: the 7 `tests/*.py` files
and `services/parsing/event_deduplication.py`. The remaining ~54 `D` files
are fork-only studies/docs/scripts (e.g. `studies/`, other `docs/*.md`) with
no shared-pipeline content and are out of this document's scope.

### The 7 deleted test files, confirmed

`git show --stat 6ff3c316a5f0781027fc504dd7bd8421a8dab6a7` (author
`arielamar123`, **2026-09-09 16:11:02 +0000**, message `"remove tests"`)
deletes exactly:

```
tests/test_global_final_state_threshold.py
tests/test_issue_10_legacy_leptons.py
tests/test_issue_13_partial_file_reads.py
tests/test_issue_6_required_selection.py
tests/test_mass_calculation_stats.py
tests/test_parse_mc_selection.py
tests/test_xrootd_source_selection.py
```

`git branch -a --contains 6ff3c31` confirms this commit is on
`upstream/master`. **One discrepancy worth flagging**: `6ff3c31`'s own diff
removes `tests/test_mass_calculation_stats.py` as an 89-line file, but the
fork's currently-kept copy of that same filename is 76 lines when diffed
against upstream's pre-deletion history — i.e. the fork's copy is not
byte-identical to what upstream had right before deleting it (likely edited
independently on each side at some point). Noted for honesty; it doesn't
change this document's conclusions about the deletion itself.

### Tier 2 scope confirmed exactly

`git diff --stat origin/master origin/feature/hgg-selection-and-output --
domain/ orchestration/ services/ 'config*.yaml'` shows **13 shared code
files** (10 modified + 3 new): `domain/config.py`, `domain/statistics.py`,
`orchestration/handlers/fetch_metadata_handler.py`,
`orchestration/handlers/parsing_handler.py`,
`services/calculations/physics_calcs.py`, `services/metadata/fetcher.py`,
`services/parsing/event_selection.py`, `services/parsing/file_parser.py`,
`services/parsing/schemas.py`, `services/parsing/threaded_processor.py`, plus
new files `services/parsing/mc_weights.py`,
`services/parsing/trigger_requirements.py`,
`services/parsing/validated_runs.py` — exactly matching the brief's "13
files" claim.

**Contradicts the brief only in scale, not in kind**: the same diff also
adds **10 brand-new `config.cms_hgg_*.yaml` files** (~950 lines) that are not
"shared code" at all — they are the H→γγ study's own analysis-specific
configs. They are excluded from Part 1's itemization on purpose (touching
H→γγ's own files is explicitly out of scope for this task), but are named
here so their absence from the inventory below isn't mistaken for an
oversight.

### A genuinely useful discovery: this isn't the first upstream-comparison exercise

Two existing docs already in this repo — `docs/UPSTREAM_SYNC_TRIAGE.md` and
`docs/UPSTREAM_SYNC_SAFE16_VERIFICATION.md` — record an **earlier, different**
exercise: triaging upstream's 41 commits for what was safe to **cherry-pick
into** the fork (the opposite direction from this document, which is about
what the fork should **propose to** upstream). That earlier work resulted in
branch `sync/upstream-safe-16`, which **is merged into `origin/master`**
(confirmed: `git merge-base --is-ancestor origin/sync/upstream-safe-16
origin/master` succeeds). This explains something that would otherwise look
surprising: of upstream's 41 ahead-commits, most of their real fixes are
already reconciled into the fork (independently or via cherry-pick), which is
why only 13 files still show a genuine content difference rather than dozens.

That earlier triage also **independently found and flagged** the exact same
issue this document's Part 2(b) treats as its central finding: upstream
commit `f43cc93` ("FIx incorrect KNOWN_MASSES units") was explicitly held
back as a "NEEDS MY DECISION" item, for precisely the unit-mismatch reason
detailed below, and confirms the fork's own `e848f4d` ("Make MeV->GeV
invariant-mass scaling schema-aware") is the commit that introduced
`schema_needs_mev_to_gev_conversion()`. This document's independent, from-code
verification (Part 2(b)) reaches the identical conclusion by a different
route — two independent checks agreeing is a meaningfully stronger basis for
Part 3's Issue A than either alone.

### `analysis/m0m1j0-cms`: confirmed clean, one explained exception

Per instruction not to touch this branch, it was only read, never modified.
Confirmed: no shared code (`domain/`, `orchestration/`, `services/`, root
`config*.yaml`) differs between it and `feature/hgg-selection-and-output`. The
only file-level difference found (`studies/hgg_cms/stats/unblind/
make_money_plot.py` and 3 sibling plot files) is explained entirely by
`analysis/m0m1j0-cms`'s branch point predating a later, unrelated feature-
branch commit (`f33d8d4`, "Money plot: add --style slide cosmetic variant for
talk slides") confined to another study's own files — benign, not a hidden
divergence.

### No contradictions found beyond the two noted above

Every other claim in the brief (the 5 SHAs, the 60/41 ahead/behind count, the
13+13 file counts, the 7-test-file deletion, the CMS_KNOWN_LIMITATIONS.md
cross-reference material) was independently verified and matches exactly.

---

## Part 1 — Difference inventory

Every item below is classified as exactly one of **ADOPT-UPSTREAM**,
**KEEP-OURS-PROPOSE**, **KEEP-OURS-PRIVATE**, or **NEEDS-DECISION**. None is
left unclassified. Where an untested physics claim is made, it is marked
**UNVERIFIED — reasoning only** together with the reasoning; nothing is
asserted as "looks equivalent" without evidence.

A structural note before the table: **Tier 1 has exactly one ADOPT-UPSTREAM
candidate** *(corrected — this originally read "zero," which is now false;
see T1-17)*. Of the 13 differing files, 11 are cases of "fork added a
capability upstream lacks" and one (`services/pipelines/histograms_pipeline.py`,
T1-17) is a pure textual no-op — confirmed by an AST (parsed-code-structure)
comparison to compile to the exact same program as upstream's version, with
the alignment already prepared on branch `chore/align-noop-files-with-upstream`
— so there is nothing to lose and one fewer divergence to carry by adopting
it. A second file that looked like the same situation
(`services/storage/sqlite_shards.py`, T1-18) was checked the same way and
did **not** pass: see T1-18 for why it stays NEEDS-DECISION rather than also
becoming ADOPT-UPSTREAM. Likewise, **"ADOPT-UPSTREAM" does not structurally
apply to Tier 2** at all — Tier 2 compares the fork's own feature branch
against the fork's own master, so there is no "upstream" side to adopt from;
Tier 2 items are classified among the other three labels only.

### Tier 1 — `master` vs `upstream/master`

---

**T1-01** — `config.cms_records_master.yaml:77-106 @ 8cf737e` vs `: (absent) @ c296b927`

*What differs:* Fork's file has a `selection_by_record` block giving records
`"30530"`/`"30563"` (SingleMuon streams) their own `particle_counts`
(≥1 muon, electron requirement dropped/widened) instead of the global block
(≥1 electron). Upstream's file has no such block — every record uses the same
global `particle_counts`.

*Physics effect — CMS:* Without this, running this exact config upstream
would apply the ≥1-electron global requirement to the SingleMuon records too,
discarding ~97% of that stream's events (documented in
`docs/CMS_KNOWN_LIMITATIONS.md`) — the SingleMuon data would be present in
name but functionally unusable.

*Physics effect — ATLAS:* None. ATLAS releases never use
`specific_record_ids`/`selection_by_record` at all; this key is inert for any
ATLAS config that doesn't set it (and none do).

*Classification:* **KEEP-OURS-PRIVATE** — this is a config *value* (which
record IDs, which counts) specific to this fork's own CMS datasets, not a
generic capability in itself. The generic mechanism it exercises is T1-06;
propose that, not this file's literal contents.

---

**T1-02** — `config.cms_records_master.yaml:116-118 @ 8cf737e` vs `: (absent) @ c296b927`

*What differs:* Fork's `kinematic_cuts` block has a `bjets: {pt_min: 30.0,
eta_max: 4.5}` entry; upstream's corresponding block has `jets:` but no
`bjets:`.

*Physics effect — CMS:* `services/calculations/physics_calcs.py`'s
`filter_events_by_kinematics` matches a `kinematic_cuts` entry only to the
identically-named collection — a `jets:` entry is never applied to `BJets`.
Without this line, on a config with `enable_jet_tagging: true`, tagged
b-jets would receive **zero** pT/η cuts, contrary to what the config appears
to specify. `docs/CMS_KNOWN_LIMITATIONS.md` documents this was found for
real, on real output (a b-jet at 15 GeV / |η|=2.90 despite `pt_min:
30`/`eta_max: 2.5`), and already fixed in 9 fork configs.

*Physics effect — ATLAS:* None for *this* file (CMS-only), but see T1-04 —
the same missing-`bjets`-cuts pattern exists in an ATLAS-only config today.

*Classification:* **KEEP-OURS-PRIVATE** — config data, not a generic
capability. See T1-07 for the generic, proposable guard against this
mistake.

---

**T1-03** — `config.cms_singleelectronsinglemuon.yaml:76-78 @ 8cf737e` vs `: (absent) @ c296b927`

Same missing-`bjets:`-cuts pattern as T1-02, same file otherwise identical
to `config.cms_records_master.yaml` at the blob level (their hashes matched
in an earlier diff pass). Same physics effect, same reasoning.

*Classification:* **KEEP-OURS-PRIVATE**.

---

**T1-04** — `config.short_parse_btag.yaml:73-75 @ 8cf737e` vs `: (absent) @ c296b927`

*What differs:* Same missing-`bjets:`-cuts pattern. **This file is an
ATLAS-only config** (no `specific_record_ids`, uses ATLAS `release_years`)
with `enable_jet_tagging: true` set (confirmed: `grep -n
enable_jet_tagging config.short_parse_btag.yaml` → line 79, `true`).

*Physics effect — ATLAS:* If this exact config file were run against
upstream's code today, `BJets` would receive **zero** kinematic cuts — this
is a live, currently-latent bug in an ATLAS-only file, not merely a
hypothetical. It is the single strongest piece of evidence that the
missing-bjets-cuts problem is not a CMS-only concern.

*Physics effect — CMS:* N/A (ATLAS config).

*Classification:* **KEEP-OURS-PRIVATE** (config data). Cross-referenced
explicitly in Part 3 Issue B, which leads with this exact ATLAS example.

---

**T1-05** — `config.short_parse_local.yaml:73-75 @ 8cf737e` vs `: (absent) @ c296b927`

Same missing-`bjets:`-cuts pattern, but **dormant**: this file has no
`enable_jet_tagging` key at all, and `domain/config.py`'s default is
`enable_jet_tagging: bool = False` — so no `BJets` collection is ever created
for this config, and the missing cut has no effect while the file is used
as-is.

*Physics effect — ATLAS:* None today (dormant); would become live the moment
someone added `enable_jet_tagging: true` to this file without also adding
`bjets:`.

*Physics effect — CMS:* N/A.

*Classification:* **KEEP-OURS-PRIVATE**.

---

**T1-06** — `domain/config.py:64-69,334 @ 8cf737e` vs `: (absent) @ c296b927`

*What differs:* Fork's `ParsingConfig` dataclass has a
`selection_by_record: Optional[dict] = None` field, wired through
`PipelineConfig.from_dict`. Upstream has neither the field nor the wiring.

*Physics effect — CMS:* This is the config-schema half of the per-trigger-
stream selection mechanism (T1-01, T1-14). Without it, a config file setting
this key would be silently ignored (an unknown YAML key, dropped at parse
time) rather than raising an error — the SingleMuon-inclusion fix could not
be expressed at all upstream.

*Physics effect — ATLAS:* None — `Optional[...] = None` default, inert for
every config that doesn't set the key, which is every current ATLAS config.

*Classification:* **KEEP-OURS-PROPOSE** — generic (any experiment combining
multiple trigger streams could use this), fully opt-in/default-off.

---

**T1-07** — `domain/config.py:92-113 @ 8cf737e` vs `: (absent) @ c296b927`

*What differs:* Fork's `ParsingConfig.__post_init__` logs a `WARNING`
(no exception, no behavior change) when `enable_jet_tagging` is true and
`kinematic_cuts` has a `jets` entry but no `bjets` entry — exactly the
mistake behind T1-02/03/04/05.

*Physics effect — CMS and ATLAS, identically:* Pure logging addition; zero
behavior change for any existing run on either experiment. Its entire value
is turning a silent, hard-to-find mistake (only discoverable by manual code
tracing, as `docs/CMS_KNOWN_LIMITATIONS.md` documents happening) into a
visible one at config-construction time, before any file is even opened.

*Classification:* **KEEP-OURS-PROPOSE** — as safe an upstream change as
exists in this entire inventory: it is a warning-only, no-op-for-existing-
configs addition, and T1-04 proves the exact failure mode it guards against
is not hypothetical for ATLAS either.

---

**T1-08** — `services/calculations/consts.py:4-11 @ 8cf737e` vs `:4-14 @ c296b927`

*What differs:* Fork's `KNOWN_MASSES` stores GeV values (`Muons: 0.105`,
`Electrons: 0.000511`, `Taus: 1.77686`). Upstream's stores MeV values
(`Muons: 105.6583755`, `Electrons: 0.51099895069`, `Taus: 1776.93`), with a
new comment: `"Known masses in MeV (converted to GeV later by
_convert_array_to_gev)"`.

*Physics effect:* See T1-09/T1-10 — this table's units are only correct
paired with upstream's own *unconditional* MeV→GeV conversion (T1-09). In
isolation this file is internally self-consistent for an MeV-native release;
the actual bug is that upstream's overall design assumes every release is
MeV-native, which is false for CMS and for at least one ATLAS release. See
Part 2(a) for the full quantification.

*Classification:* **KEEP-OURS-PROPOSE** — bundled with T1-09/T1-10/T1-13 as
one upstream issue (Part 3, Issue A); this file alone is only half the
mechanism.

---

**T1-09** — `services/pipelines/im_pipeline.py:48,59,115-116,146-149 @ 8cf737e` vs `:103,133-134 @ c296b927`

*What differs:* Fork computes `apply_mev_to_gev =
schema_needs_mev_to_gev_conversion(release_year)` and only calls
`_convert_array_to_gev` (÷1000) when that flag is true. Upstream calls
`_convert_array_to_gev` **unconditionally** on every computed invariant mass,
for every release.

*Physics effect — CMS:* CMS NanoAOD `pt`/`eta`/`phi`/`mass` branches are
already in GeV (verified directly on real data: an e-pair invariant mass of
~91 GeV appears as ~91 *before* any scaling — see T1-10's schema comment).
Upstream's unconditional ÷1000 would shrink every CMS invariant mass by
exactly 1000× — a Z peak would compute as ~0.091 instead of ~91. This is not
a subtle bias; it is a wrong-by-three-orders-of-magnitude, trivially
detectable corruption, confirmed **not** UNVERIFIED — it follows directly
from reading both code paths and the schema's own documented cross-check.

*Physics effect — ATLAS:* Confirmed via `services/parsing/schemas.py`'s
`"2025e-13tev-beta"` entry (T1-10): this ATLAS release's flat branches
(`lep_pt`, `jet_pt`, ...) are **also already GeV-native** (cross-checked
against a known-MeV ATLAS release for the same MC sample, dsid 301204,
dividing by 1000 to confirm equivalence — comment preserved verbatim in
T1-10). Upstream's unconditional conversion would apply the same 1000×
shrink to this ATLAS release's masses too. **This is a live latent bug in
upstream affecting ATLAS data, with zero CMS involvement in the mechanism.**

*Classification:* **KEEP-OURS-PROPOSE** — the single strongest candidate in
this entire document; independently corroborated by
`docs/UPSTREAM_SYNC_TRIAGE.md`'s own prior finding (Part 0).

---

**T1-10** — `services/parsing/schemas.py:87-247 (native_pt_unit tags), 592-622 (both functions) @ 8cf737e` vs `: (absent, all of it) @ c296b927`

*What differs:* Fork tags every entry in `RELEASE_SCHEMAS` with
`"native_pt_unit": "MeV" | "GeV" | "unknown"`, each with a comment
documenting how it was verified on real data, and defines
`get_native_pt_unit()`/`schema_needs_mev_to_gev_conversion()` — the latter
returning `True` (apply the ÷1000 conversion) for *everything except* an
explicit `"GeV"` tag, including "unknown", a missing key, or a lookup
failure. Upstream has none of this: no key, no functions, confirmed by
`git diff` showing zero matches for `native_pt_unit`,
`schema_needs_mev_to_gev_conversion`, or `get_native_pt_unit` anywhere in its
`schemas.py`.

*Physics effect:* This is the evidence layer for T1-09's finding, and its
own default-to-`True` behavior is precisely why T1-09 can be proposed as
byte-identical for existing configs: adopting this mechanism upstream would
require every *existing* release to keep converting (nothing tagged, default
`True`) and only skip the conversion for a release someone explicitly,
deliberately tags `"GeV"` after verifying it, exactly as the fork did for
its own two GeV-native releases.

*Classification:* **KEEP-OURS-PROPOSE** — same issue as T1-09/T1-08/T1-13.

---

**T1-11** — `services/parsing/schemas.py:45-49,129 @ 8cf737e` vs `: (absent) @ c296b927`

*What differs:* Fork declares `NANOAOD_EVENT_ID_BRANCHES = ["run",
"luminosityBlock", "event"]` and attaches it to the `cms-nanoaod` schema via
an `"event_id_branches"` key. Upstream has neither.

*Physics effect — CMS:* This is what lets the parser read per-event identity
branches as scalar columns rather than physics-object fields — required
input for T1-14/T1-19's de-duplication and T1-16's `source_record` tagging.
Without it, cross-record de-duplication cannot be built at all (no stable
per-event key to match on).

*Physics effect — ATLAS:* None; no ATLAS schema declares this key.

*Classification:* **KEEP-OURS-PROPOSE** — generic scalar-id-branch
declaration, reusable by any flat-schema experiment; superseded in the
feature branch by a more general form (T2-15) worth proposing instead of
this narrower version if this reaches an actual PR.

---

**T1-12** — `services/parsing/schemas.py:74-75 @ 8cf737e` vs `: (absent) @ c296b927`

*What differs:* `RECORD_ID_TO_SCHEMA` maps records `30522`/`30555`
(DoubleMuon, the m0m1j0 study's own records) to `"cms-nanoaod"`. Upstream has
no entries for these record IDs at all.

*Physics effect — CMS:* Without registration, `FileParser` falls back to
auto-detection, which — per the fork's own comment on this exact mapping —
does not work for NanoAOD's flat branch naming, and silently produced
**0/0 files processed** for these two records before they were registered
(a real, previously-hit failure mode, not hypothetical).

*Physics effect — ATLAS:* None; record-ID lookups are CMS-only.

*Classification:* **KEEP-OURS-PRIVATE** — these two specific record IDs are
this fork's own study data, not a generic capability. The generic fix for
the *class* of problem (silent 0-event fallback for any unregistered record)
is proposed separately, and more thoroughly, at T2-18.

---

**T1-13** — `orchestration/handlers/mass_calculation_handler.py:26,29-43,356-360 @ 8cf737e` vs `: (absent) @ c296b927`

*What differs:* Fork parses the release/schema id back out of each parsed
ROOT filename (`release_year_from_parsed_filename`) and computes
`needs_scaling = schema_needs_mev_to_gev_conversion(release_year)` **per
file**, so a single run mixing releases stays correct. Upstream has neither
function; its `_convert_array_to_gev` call (T1-09) has no per-file gating to
receive.

*Physics effect:* Directly downstream of T1-09/T1-10 — this is the call site
that would need to exist for that mechanism to be usable at the mass-
calculation stage. Same CMS/ATLAS effects as T1-09.

*Classification:* **KEEP-OURS-PROPOSE** — same issue as T1-08/09/10.

---

**T1-14** — `orchestration/handlers/parsing_handler.py:206-306 @ 8cf737e` vs `:190-230 @ c296b927`

*What differs:* Fork orders `metadata.items()` so muon-requirement records
(per `selection_by_record`) are processed **first**, constructs an
`EventDeduplicator` when `selection_by_record` is set, and calls
`deduplicator.filter_new(...)` on every batch. Upstream processes records in
whatever order `metadata.items()` yields and has no de-duplication step at
all (no import of `event_deduplication`, confirmed absent in T1-19).

*Physics effect — CMS:* Without this, combining SingleElectron and
SingleMuon streams from the same run era would double-count any event that
fired both triggers — documented at ~2% of events at full scale
(`docs/CMS_KNOWN_LIMITATIONS.md`), and the *order* matters too: without
muon-first ordering, the wrong copy (SingleElectron's, with the weaker
lepton requirement) would be the one kept.

*Physics effect — ATLAS:* None; only activates when `selection_by_record` is
set, which no ATLAS config does.

*Classification:* **KEEP-OURS-PROPOSE** — generic multi-trigger-stream
de-duplication capability, needed by any experiment combining overlapping
primary datasets.

---

**T1-15** — `orchestration/handlers/parsing_handler.py:332-350 @ 8cf737e` vs `: (absent) @ c296b927`

*What differs:* Fork tracks per-record file-open success/failure counts and
raises `RuntimeError` if more than `MAX_FILE_FAILURE_RATE` (20%) of a
record's files fail to open, aborting rather than silently continuing.
Upstream has no such guard — a record whose files mostly fail to open (a
redirector issue, an exhausted connection pool, a bad URL) would finish with
near-zero retained events and **no error**, indistinguishable from a record
that genuinely has low yield.

*Physics effect — CMS and ATLAS, identically:* Purely a robustness guard, not
a physics-selection change; a run that would previously finish silently
wrong now aborts loudly instead. No effect on a run where files open
normally (the historical case for every completed run on either experiment
to date).

*Classification:* **KEEP-OURS-PROPOSE** — fully generic, experiment-neutral,
matches the exact "loud failure on high file-open-failure rates" gap in
upstream's design.

---

**T1-16** — `services/parsing/file_parser.py:124-161,282,299-303,521 @ 8cf737e` vs `:122-124,243,259,477 @ c296b927`

*What differs:* Fork extracts an `"EventIds"` branch group (via T1-11's
schema declaration), re-attaches `run`/`luminosityBlock`/`event` as top-level
scalar columns on the parsed event record, and (separately) tags every event
with a `source_record` integer field derived from the CMS record ID. If a
schema declares `event_id_branches` but they turn out unreadable, this
raises rather than silently continuing. Upstream has none of this — no
`EventIds` handling, no `source_record` field.

*Physics effect — CMS:* This is the data feeding T1-14/T1-19's
de-duplication (the composite key) and gives every event a reliable
provenance tag even after chunk-merging combines multiple records' output
into one file — replacing the previous filename-only labelling, which
mislabelled events whenever multiple records shared an output chunk.

*Physics effect — ATLAS:* None; `EventIds`/`source_record` are only produced
when a schema declares `event_id_branches`, which no ATLAS schema does.

*Classification:* **KEEP-OURS-PROPOSE** — same theme as T1-11; note the
feature branch's T2-15 generalizes this into a reusable named-group
mechanism, which is the better version to actually propose if this reaches
an implementation.

---

**T1-17** — `services/pipelines/histograms_pipeline.py:200-215 @ 8cf737e` vs `:201-214 @ c296b927`

*What differs:* A blank-line and a comment's position are swapped relative
to a line of code (the comment `"# Split SQLite files across histogram
batch jobs"` moves from immediately after the `if` block it describes to
immediately before it). **No executable line differs; the diff is
whitespace/comment placement only.**

*Physics effect — CMS and ATLAS:* None. Confirmed by reading both sides in
full; the executable statements are identical, only in a different textual
order relative to the comment.

*Classification:* **ADOPT-UPSTREAM** — *(corrected; was KEEP-OURS-PRIVATE)*.
The original classification was wrong: if a difference truly has no
executable content, adopting upstream's version costs nothing and shrinks
the fork's divergence for free — there is no reason to carry a permanent,
pointless difference just because it happens to be harmless. This is no
longer a claim resting only on reading the diff: it has since been proven
by an AST (Abstract Syntax Tree — the parsed structure of the code, with
comments and whitespace stripped out) comparison performed as part of a
separate branch-alignment task, and the alignment itself has already been
prepared. Branch `chore/align-noop-files-with-upstream` (created from this
same fork master) replaces this file with upstream's exact content and
records, in its commit message, that the fork's and upstream's ASTs for
this file are byte-for-byte **identical** — the two versions compile to the
exact same program. Adopting is a pure win: zero behavior change, one less
divergence to track.

---

**T1-18** — `services/storage/sqlite_shards.py:46-102 @ 8cf737e` vs `:46-96 @ c296b927`

*What differs:* The `CREATE TABLE IF NOT EXISTS` statements for
`final_state_counts` and `shard_metadata` are swapped in order, and the
`record_final_state_count`/`set_metadata` method definitions are likewise
swapped in order within the class. Both tables and both methods exist,
unchanged, on both sides.

*Physics effect — CMS and ATLAS:* None expected — `CREATE TABLE IF NOT
EXISTS` statement order and method-definition order inside a Python class
have no runtime effect that either experiment's use of this code could
observe.

*Classification:* **NEEDS-DECISION** — *(corrected from KEEP-OURS-PRIVATE;
NOT reclassified to ADOPT-UPSTREAM, despite that being requested — see
below for why)*. This item was checked by the same AST comparison used for
T1-17, as part of the `chore/align-noop-files-with-upstream` branch-
alignment task, specifically because this document's own claim of "no
executable difference" should not simply be trusted for a second file just
because it held for the first. **The result was different: the AST is NOT
identical.** Reordering two statements moves them to a different position
in the parse tree even when neither statement's own content changes, so a
literal AST comparison correctly reports this file as changed, not merely
reformatted. Informally, the reordering is still very likely harmless — the
two `CREATE TABLE` statements create two unrelated tables with no
dependency on each other, and the two methods do not call each other during
class construction — but "very likely harmless, by reasoning" is a weaker
standard than the proof that supported T1-17's reclassification, and this
document does not treat the two as equivalent. This file was deliberately
**left unchanged** on `chore/align-noop-files-with-upstream` rather than
replaced. Whether to adopt upstream's version anyway on the weaker,
still-reasonable "independent statements" argument, or to hold out for a
stronger proof (e.g. a canonicalized/order-independent AST diff, or a
maintainer's explicit sign-off that this specific class of reordering is
always safe to treat as a no-op) is a judgment call this document is not
positioned to make silently, and so it does not.

---

**T1-19** — `services/parsing/event_deduplication.py:1-103 @ 8cf737e` (whole file) vs `: (does not exist) @ c296b927`

*What differs:* Fork-only module. `EventDeduplicator` keys on a packed
128-bit-safe composite integer (`run << 96 | luminosityBlock << 64 |
event`, using Python object-dtype big-ints specifically to avoid any
overflow/collision risk on the full 64-bit `event` value), keeps the first
occurrence of each key across an entire run (stateful — "One instance per
pipeline run", per its own docstring), and reports drops broken down by run
number. Its own docstring documents a known scale limitation: at full scale
(~2×10⁸ events) the plain Python `set` this uses would need to become a
more memory-frugal structure — explicitly left as a noted follow-up, not
hidden.

*Physics effect — CMS:* This is the class T1-14 calls; see T1-14's physics
effect (prevents ~2% double-counting when combining trigger streams).

*Physics effect — ATLAS:* None; never imported/called except from T1-14's
now-CMS-only code path.

*Classification:* **KEEP-OURS-PROPOSE** — same GitHub issue as T1-06/14
(Part 3, Issue C); this is the reusable engine underneath that mechanism.

---

**T1-20** — `tests/test_global_final_state_threshold.py`, `test_issue_10_legacy_leptons.py`, `test_issue_13_partial_file_reads.py`, `test_issue_6_required_selection.py`, `test_mass_calculation_stats.py`, `test_parse_mc_selection.py`, `test_xrootd_source_selection.py` @ `8cf737e` (all present, fork-only) vs `: (all deleted by upstream commit 6ff3c31, 2026-09-09) @ c296b927`

*What differs:* Upstream deleted its entire `tests/` directory in one commit,
message `"remove tests"`, no further explanation in the commit body. The
fork kept (and, per Part 0's discrepancy note, in one case independently
modified) copies of these files.

*Physics effect:* None directly — these are test files, not pipeline code.
Indirect effect: keeping them gives the fork regression coverage for several
of the fixes reconciled via `sync/upstream-safe-16` (per
`docs/UPSTREAM_SYNC_TRIAGE.md`'s own note that the fork "currently has no
`tests/` directory at all [before that sync], so keeping these costs nothing
and gives free regression coverage").

*Classification:* **NEEDS-DECISION** — genuinely undecidable from the code
alone. The commit message gives no reasoning (deliberate policy change on
upstream's side? tests rewritten elsewhere and not yet visible in this diff?
an oversight?), and this document is explicitly forbidden from contacting
upstream to ask. Whether to raise this at all — and if so, as a bug-style
issue or as a plain question — is a judgment call the brief itself flagged
as "possibly a question, not an issue." See Part 3's Issue J (framed as a
question) and the closing summary's explicit ask to Matan/supervisor.

---

### Tier 2 — `feature/hgg-selection-and-output` vs `master`

All Tier 2 items compare `origin/feature/hgg-selection-and-output @
f33d8d47a060082d70c4dd1451e81ad29cd0950d` ("feature" below) against
`origin/master @ 8cf737e1acf0fa736b78864e631dc6cc98e05772` ("master" below).
Every new field/module described here is confirmed, by direct reading of its
own docstring and `ParsingConfig.__post_init__`'s validation, to default to
`None`/`False` and be a complete no-op for every config file that exists
today on either branch — this is asserted only where the code itself states
and enforces it, not assumed.

---

**T2-01** — `domain/config.py:70 @ master` (insertion point) vs `:70-134 @ feature`

*What differs:* New `ParsingConfig` fields `extra_scalar_branches:
Optional[dict]` and `extra_object_fields: Optional[dict]` — generic hooks to
read extra scalar branch groups or extra per-object jagged fields beyond
whatever a schema declares by default, each validated as a dict of
name→list-of-strings in `__post_init__`.

*Physics effect — CMS:* Lets a study (e.g. H→γγ, which needs
`Photon_electronVeto`/`Photon_mvaID_WP90` beyond the default field list)
request extra fields without editing the shared schema. No effect unless a
config sets one of these keys.

*Physics effect — ATLAS:* None — absent/`None` for every current config,
confirmed reproducing "existing behaviour exactly" per the field's own
comment.

*Classification:* **KEEP-OURS-PROPOSE** — generic extensibility hook, no
CMS-specific logic in the mechanism itself.

---

**T2-02** — `domain/config.py:70 @ master` vs `:70-134,176-222,446-451 @ feature`

*What differs:* New field `validated_runs_json: Optional[str]` — a path to a
CMS-style "golden JSON" file of certified `(run, lumisection)` ranges. Wired
through to `orchestration/handlers/parsing_handler.py` (T2-07) and backed by
the new `services/parsing/validated_runs.py` module (T2-24).

*Physics effect — CMS:* Enables filtering data (never simulation — see
T2-24's guard) to only DQM-certified runs/lumisections, a standard CMS
data-quality step currently entirely absent from this pipeline.

*Physics effect — ATLAS:* **UNVERIFIED — reasoning only.** ATLAS has an
analogous concept ("Good Run Lists", typically XML, not CMS's JSON
run→lumi-range shape). The *mechanism* here (composite run/lumi key,
vectorized membership test, simulation guard, opt-in) is generic, but the
current *loader* is written specifically for CMS golden-JSON's shape — using
it for an ATLAS GRL as-is would require writing a new loader, not just
pointing at a different file. Not tested against any ATLAS GRL file in this
task (out of scope; no cluster/data access used).

*Classification:* **KEEP-OURS-PROPOSE**, with that caveat carried into Part
3's Issue L.

---

**T2-03** — `domain/config.py:70 @ master` vs `:70-134,176-222,446-451 @ feature`

*What differs:* New field `trigger_requirements: Optional[dict]` —
`{"mode": "any"|"all", "paths": [...]}`, validated in `__post_init__` (mode
must be one of the two literals, paths must be a non-empty list of
non-empty strings). Wired through `orchestration/handlers/parsing_handler.py`
(T2-08, including a per-record override under `selection_by_record`) and the
new `services/parsing/trigger_requirements.py` module (T2-23).

*Physics effect — CMS:* Lets a config keep only events where a configured
HLT trigger path fired — applies to **both** data and simulation (no
simulation guard, unlike T2-02, since the design intentionally requires the
same trigger bit in MC — documented in the module's own docstring).

*Physics effect — ATLAS:* None today (no ATLAS config sets this key); the
mechanism itself is generic — any experiment's HLT/L1 bit, by branch name,
would work identically.

*Classification:* **KEEP-OURS-PROPOSE** — fully generic, no
CMS-specific assumption in the code.

---

**T2-04** — `domain/config.py:70 @ master` vs `:70-134,176-222,446-451 @ feature`

*What differs:* New fields `read_event_weights: bool = False` and
`read_pileup_info: bool = False`. Backed by the new
`services/parsing/mc_weights.py` module (T2-19).

*Physics effect — CMS:* Opts in to reading `genWeight` (simulation-only
generator weight) and `PV_npvsGood`/`Pileup_nTrueInt` (pileup info), needed
for any MC-normalized analysis (e.g. H→γγ signal samples).

*Physics effect — ATLAS:* None — these branch names
(`genWeight`/`PV_npvsGood`/`Pileup_nTrueInt`) are CMS NanoAOD-specific
constants; the *gating pattern* (detect simulation-vs-data per file, refuse
loudly if a simulation-only field is requested on data) is generic, but an
ATLAS equivalent would need its own branch-name constants and its own
`file_is_simulation`-equivalent, not a drop-in reuse.

*Classification:* **KEEP-OURS-PROPOSE** — propose the *pattern*, not the
literal CMS branch names, as Part 3's Issue N makes explicit.

---

**T2-05** — `domain/statistics.py:70 @ master` vs `:71-80,134 @ feature`

*What differs:* New `ParsingStatistics.sumw_by_record: Optional[dict]` field
— per-record `{genEventSumw, genEventCount, genEventSumw2, n_files_processed,
processed_files, n_files_failed}`, populated only when `read_event_weights`
is set (T2-04), and included in `to_dict()`'s output.

*Physics effect — CMS:* Provides the MC-normalization denominator
(`genEventSumw`), computed **only from the files that actually succeeded** in
this run (not the full record), with the failed-file count carried alongside
so a caller can't silently misinterpret a partial sum as the full record's
sum.

*Physics effect — ATLAS:* None — `None` by default, and `read_event_weights`
(the only thing that populates it) has no ATLAS caller.

*Classification:* **KEEP-OURS-PROPOSE** — generic MC-weight bookkeeping,
same issue as T2-04/T2-19 (Part 3, Issue N).

---

**T2-06** — `services/metadata/fetcher.py:43,57 @ master` vs `:44-52,67-105 @ feature`; `orchestration/handlers/fetch_metadata_handler.py:8-9,87 @ master` vs `:10-12,12-61,140-152 @ feature`

*What differs:* New `_classify_cms_url()` in `fetcher.py`, classifying a CMS
Open Data URL as DATA/MC by its EOS path (`/eos/opendata/cms/mc/` vs
`/eos/opendata/cms/Run<year><era>/`), since CMS record keys carry no `_mc`
suffix the way ATLAS release-year keys do. New `_cms_record_id()`/
`_cms_key_violations()` helpers in `fetch_metadata_handler.py` route any
`"record_<id>"` cache key (for a registered `cms-nanoaod` record) through
this new classifier instead of the ATLAS-only `_classify_url` (RUCIO
namespace regexes), which cannot parse a CMS EOS path at all.

*Physics effect — CMS:* Fixes a **real, already-observed crash**: per the
code's own comment, the first cluster job that pinned its file via a
pre-written cache (a cache hit) aborted on a perfectly valid CMS DoubleEG URL
because the old cache-validation logic tried to apply ATLAS's RUCIO-pattern
classifier to it and found no match (raising, since `_classify_url` raises
on an unclassifiable URL by design). This change fixes that crash without
touching `_classify_url`'s own ATLAS logic at all.

*Physics effect — ATLAS:* None — every non-CMS-record key still goes through
the exact prior `_classify_url`/`"_mc"`-suffix logic, confirmed unchanged by
the diff.

*Classification:* **KEEP-OURS-PROPOSE** — CMS-specific classifier, but pure
addition (new function, new branch in existing code, zero change to any
ATLAS code path); fixes a genuine, previously-hit failure.

---

**T2-07** — `orchestration/handlers/parsing_handler.py:171 @ master` vs `:178-201,357-372 @ feature`

*What differs:* When `validated_runs_json` (T2-02) is set, a
`ValidatedRunsFilter` is loaded once per run and applied to every batch
**before** particle/kinematic selection and **before** de-duplication —
deliberately ordered first so a rejected event is never counted "selected"
by a later stage, and so de-duplication's composite keys are only ever built
from certified events.

*Physics effect — CMS:* Ordering matters for correctness of the retention
percentages reported by both this filter and de-duplication; getting it
backward would make de-dup's %-dropped figure include events that would have
been rejected anyway for data-quality reasons, muddying which stage is
responsible for which drop.

*Physics effect — ATLAS:* None — inert unless `validated_runs_json` is set.

*Classification:* **KEEP-OURS-PROPOSE** — same issue as T2-02/T2-24.

---

**T2-08** — `orchestration/handlers/parsing_handler.py:242-276 @ master` vs `:283-309,373-400 @ feature`

*What differs:* When `trigger_requirements` (T2-03) is set (globally or via a
per-record override under `selection_by_record`), the required HLT paths are
automatically added to the "Trigger" scalar branch group (no need to also
list them in `extra_scalar_branches`), validated via
`validate_trigger_requirements`, and the filter is applied **after** the
validated-runs filter but **before** particle/kinematic selection and
de-duplication — same "dedup keys only from post-filter events" reasoning as
T2-07. Applies to data **and** simulation, unlike T2-07.

*Physics effect — CMS:* Lets an analysis require a specific HLT path fired,
consistently in data and MC, with per-record override support (useful when
different trigger-stream records need different paths).

*Physics effect — ATLAS:* None — inert unless `trigger_requirements` is set.

*Classification:* **KEEP-OURS-PROPOSE** — same issue as T2-03/T2-23.

---

**T2-09** — `orchestration/handlers/parsing_handler.py:286 @ master` vs `:409-436 @ feature`

*What differs:* Before applying de-duplication, the code now checks
`is_simulation(working_events)` and **raises `RuntimeError`** if
de-duplication is enabled (via `selection_by_record`) and the events being
processed look like simulation.

*Physics effect — CMS:* This is a pure safety guard against a specific,
concrete failure mode described in the code's own comment: simulated NanoAOD
sets `run == 1` for every event, and `(luminosityBlock, event)` can repeat
across different samples/files — so running de-duplication on simulation
would silently delete genuine signal events, keyed on a collision that means
nothing physically. Before this guard, a config that mixed a
trigger-stream-combined data record with a simulation record in the same run
would have applied de-dup to the simulation too, with no error.

*Physics effect — ATLAS:* None — only reachable when `selection_by_record`
is set, which is CMS-only today.

*Classification:* **KEEP-OURS-PROPOSE** — purely defensive, raises loudly
rather than corrupting data silently; same issue as T1-14/T1-19/T2-24 (all
part of the de-duplication feature family — Part 3, Issue C).

---

**T2-10** — `orchestration/handlers/parsing_handler.py:227,350 @ master` vs `:258-267,501-541 @ feature`

*What differs:* When `read_event_weights` (T2-04) is set, the handler tracks
`processed_urls` (files whose Events tree parsed successfully) per record,
then reads exactly those files' Runs-tree `genEventSumw`/`genEventCount`/
`genEventSumw2` via the new `aggregate_sumw_for_processed_files` (T2-19),
storing the result in `sumw_by_record` (T2-05). By construction (per the
code's own comment), reaching this point with `read_event_weights` enabled
means every processed file in the record is simulation — a data file would
already have raised earlier (T2-19's guard).

*Physics effect — CMS:* Ensures the MC-normalization numerator (a selected-
event `genWeight` sum, computed downstream in the study's own code) and this
denominator (`genEventSumw`) are computed over the **identical file set** —
explicitly guarding against a described bias risk: if a file's Events tree
parsed but its Runs tree could not be read, silently omitting it from the
denominator while including it in the numerator would bias the normalization
upward. `aggregate_sumw_for_processed_files` raises loudly instead of
omitting silently.

*Physics effect — ATLAS:* None — CMS NanoAOD-specific branch names, and only
active when `read_event_weights` is set.

*Classification:* **KEEP-OURS-PROPOSE** — same issue as T2-04/T2-05/T2-19.

---

**T2-11** — `orchestration/handlers/parsing_handler.py:393,397 @ master` vs `:585-652 @ feature`

*What differs:* New log-only reporting: per-run validated-runs retention
percentages, per-path trigger-requirement pass rates, `genEventSumw` totals,
a **skipped-file failure-reason breakdown** (`failure_reason_counts`, keyed
by exception type name), and a **branch-accessibility-probe retry report**
(count of retries and final failures, per file). All purely additive log
lines using new `ParsingStatisticsCollector.get_summary()` keys (T2-21);
nothing here changes `parsed_files`, `parsing_stats`, or any value written to
an output file.

*Physics effect — CMS and ATLAS, identically:* None on results; purely
operational visibility. Explicitly documented as producing zero output for
every run to date on either experiment ("this project's real files always
have had every requested branch accessible on the first try... nonzero only
under the transient-read-failure conditions this fix targets").

*Classification:* **KEEP-OURS-PROPOSE** — zero-risk, pure-logging addition;
directly supports Part 3's Issue D (loud failure visibility).

---

**T2-12** — `services/calculations/physics_calcs.py:230,322 @ master` vs `:231-281,374-391 @ feature`; `services/parsing/event_selection.py:54 @ master` vs `:55-64 @ feature`

*What differs:* New generic per-object kinematic-cut types `bool_require`
(all listed boolean fields must be `True`) and `bool_any_of` (at least one
must be `True`), implemented via `_boolean_field_mask` — which accepts a
genuinely boolean field or an integer field whose *only* values are 0/1, and
raises for anything else (e.g. a multi-valued ordinal field like `cutBased`'s
0–3 scale) rather than silently truthy-casting it.

*Physics effect — CMS:* Enables cuts like CMS photon ID
(`bool_require: [electronVeto, mvaID_WP90]`) or the barrel/endcap
supercluster-η acceptance gap (`bool_any_of: [isScEtaEB, isScEtaEE]`),
neither expressible in the pre-existing `pt_min`/`eta_max`/
`rel_isolation_max`-only cut vocabulary.

*Physics effect — ATLAS:* None today (no ATLAS config uses these keys); the
mechanism is generic (any boolean or genuinely-0/1 field, any collection).

*Classification:* **KEEP-OURS-PROPOSE** — generic, safely-guarded (raises
rather than silently mis-casting), no CMS-specific logic.

---

**T2-13** — `services/calculations/physics_calcs.py:322 @ master` vs `:392-403 @ feature`; `services/parsing/event_selection.py:54 @ master` vs `:65-70 @ feature`

*What differs:* New generic `eta_exclude: {min, max}` — a symmetric
|η|-window exclusion cut, distinct from (and explicitly documented as **not
a substitute for**) `bool_any_of`'s supercluster-eta gate.

*Physics effect — CMS and ATLAS:* Generic |η|-window exclusion, usable by
either experiment; no current config uses it.

*Classification:* **KEEP-OURS-PROPOSE** — small, generic, safe addition.

---

**T2-14** — `services/parsing/file_parser.py:31 @ master` vs `:33-105 @ feature`

*What differs:* Three new exception classes —
`RequiredScalarBranchMissingError(ValueError)`,
`RequiredObjectFieldMissingError(RequiredScalarBranchMissingError)`, and
`UnregisteredRecordSchemaError(RequiredScalarBranchMissingError)` — each
subclassing `ValueError` (so any existing `except ValueError` still works)
but deliberately **not swallowed** as an ordinary per-file failure by
`ThreadedFileProcessor.process_files` (T2-17/21/22), instead aggregated
across every file in a record into one clear, run-aborting error.

*Physics effect — CMS and ATLAS, identically:* No effect on any run where
every declared branch/field/record schema is present and correct — which is
every run to date on either experiment, per the code's own stated
assumption. Effect is entirely in the failure case: what was previously a
silent per-file skip-and-continue for a missing required branch/field/schema
becomes a loud, aggregated, run-aborting error instead.

*Classification:* **KEEP-OURS-PROPOSE** — directly matches the brief's
anticipated "loud failure on unregistered record IDs" gap; Part 3's Issue D.

---

**T2-15** — `services/parsing/file_parser.py:250 @ master` vs `:429-537 @ feature` (`_resolve_scalar_groups`); `services/parsing/schemas.py:658 @ master` vs `:689-730 @ feature` (`get_scalar_branch_groups`)

*What differs:* Generalizes T1-11/T1-16's `EventIds`-only special case into
an arbitrary number of named scalar branch groups
(`schemas.get_scalar_branch_groups` merges a schema's own
`event_id_branches` — kept, under the built-in name `"EventIds"`, for
backward compatibility — with any additional `scalar_branch_groups` a schema
declares, and with caller-supplied `extra_scalar_branches`, T2-01).
`_resolve_scalar_groups` additionally validates that no group/branch name
collides with a physics-object collection name or reserved field, and that
no branch is claimed by two different groups.

*Physics effect — CMS:* This is the mechanism T2-08's "Trigger" group and any
future named scalar group are built on; a collision or ambiguous branch
name is now a clear `ValueError` at resolution time rather than a silent
overwrite.

*Physics effect — ATLAS:* None — returns `{}` for "every ATLAS release
today" per the function's own docstring, a strict generalization with no
behavior change for schemas that don't opt in.

*Classification:* **KEEP-OURS-PROPOSE** — cleaner, more general replacement
for T1-11/T1-16; propose this version, not the older one, if implemented.

---

**T2-16** — `services/parsing/file_parser.py:254 @ master` vs `:526-560 @ feature` (`_resolve_object_fields`)

*What differs:* Merges caller-requested `extra_object_fields` (T2-01) into a
schema's default per-object field list, de-duplicating harmlessly if a field
is already present, but raising `ValueError` if a named collection doesn't
exist in the schema at all. Separately, if a requested extra field turns out
inaccessible in a *specific* file (passes the schema-level check but fails
the per-file accessibility probe), that raises `RequiredObjectFieldMissingError`
(T2-14) rather than silently vanishing.

*Physics effect — CMS:* Needed for H→γγ's photon-ID fields
(`electronVeto`, `mvaID_WP90`) — without the hard-fail, a field silently
missing from one file in a batch would just not exist on that batch's
`Photons` collection, with no signal that anything was wrong.

*Physics effect — ATLAS:* None — `extra_object_fields` absent/`None`
reproduces existing behavior exactly.

*Classification:* **KEEP-OURS-PROPOSE** — generic extensibility with a
correctness guard, same theme as T2-01/T2-14.

---

**T2-17** — `services/parsing/file_parser.py:476 @ master` vs `:788-900 (approx.) @ feature`; `services/parsing/threaded_processor.py:52-159 @ master` vs `:53-272 (approx.) @ feature`

*What differs:* `_filter_accessible_branches`'s per-branch accessibility
probe now retries a branch that fails to read (not one genuinely absent from
`tree.keys()` — that case still fails immediately, no retry) with a fixed
backoff schedule `_PROBE_RETRY_DELAYS_SEC = [2.0, 5.0, 10.0]` before giving
up, reporting `on_probe_retry`/`on_probe_final_failure` callback counts that
`threaded_processor.py` collects into `probe_stats` and surfaces via T2-11's
reporting.

*Physics effect — CMS:* Recovers from a transient per-branch read failure
(the same class of issue `docs/UPSTREAM_SYNC_TRIAGE.md`'s prior triage
hypothesized for the "muon looseId/pfRelIso04_all silently dropped" bug —
attributed there to XRootD handle-cache races) instead of permanently
dropping that branch for the whole batch after a single failed attempt.

*Physics effect — ATLAS:* **This is not CMS-specific at all.** Transient
XRootD read failures are a generic network/storage-layer phenomenon;
ATLAS's own `analysis/m0m1j0-mumujet` branch (per that same prior-triage
document) independently hit and worked around a related symptom. Leading
with ATLAS relevance here is appropriate — see Part 3's Issue E.

*Classification:* **KEEP-OURS-PROPOSE** — robustness improvement, no
experiment-specific logic in the retry mechanism itself.

---

**T2-18** — `services/parsing/file_parser.py:294 @ master` vs `:602-624 (approx.) @ feature`

*What differs:* In `_extract_branches_by_schema`, a `release_year` of the
form `"record_<id>"` with no entry in `RECORD_ID_TO_SCHEMA` now raises
`UnregisteredRecordSchemaError` immediately, instead of falling through to
`_auto_detect_branches` with only a `WARNING` log line. Auto-detection is
still attempted, unchanged, for a non-record `release_year` with no schema
match.

*Physics effect — CMS:* Directly closes the exact failure mode T1-12
describes: an unregistered CMS record silently produced 0/0 files processed
before. This makes that specific, already-observed failure mode impossible
to hit silently again.

*Physics effect — ATLAS:* None — the changed branch only fires for
`"record_*"`-shaped release years, which no ATLAS release uses.

*Classification:* **KEEP-OURS-PROPOSE** — same family as T2-14, directly
supersedes the ad hoc situation T1-12 was itemized under.

---

**T2-19** — `services/parsing/mc_weights.py` (new file, 1-226) @ feature vs `: (does not exist) @ master`

*What differs:* New module. `file_is_simulation()` detects simulation by
checking a file's own `Events`-tree branch **names** (presence of
`genWeight`) — metadata, not a value read, so (per its own docstring) it
isn't subject to the same transient-read-failure hazard T2-17 targets.
`SimulationFieldRequestedOnDataError` (subclassing T2-14's
`RequiredScalarBranchMissingError`) raises if `read_event_weights`/
`read_pileup_info` is requested on a file that looks like real data.
`resolve_weight_and_pileup_groups` builds the "Weights"/"Pileup" scalar
groups (T2-15's mechanism) per file, since a single run can mix data and
simulation CMS records.

*Physics effect — CMS:* Provides the CMS-specific implementation behind
T2-04/T2-05/T2-10; the per-file (not per-run) simulation detection is
specifically necessary because CMS record IDs, unlike ATLAS release-years,
are not split into a data/MC pair naming convention.

*Physics effect — ATLAS:* None — entirely new, CMS-branch-name-specific
module; not imported by any ATLAS code path.

*Classification:* **KEEP-OURS-PROPOSE** — bundled with T2-04/T2-05/T2-10 as
one proposal (Part 3, Issue N): propose the *pattern* (per-file simulation
detection, simulation-only-field guard), described generically, with CMS's
branch names as the reference implementation.

---

**T2-20** — `services/parsing/schemas.py:75 @ master` vs `:76-105 @ feature`

*What differs:* Nine new `RECORD_ID_TO_SCHEMA` entries: the H→γγ study's two
data records (30521, 30554, DoubleEG) and six simulation records (37350,
68497, 71013, 70173, 74132, 67611 — ggH/VBF/W±H/ZH/ttH), plus one Z→ee
control-region record (35669, DYJetsToLL_M-50). Each entry's comment
documents that the record's own file was opened and its branch list checked
directly (flat NanoAOD naming, `run`/`luminosityBlock`/`event` present,
`genWeight` correctly present/absent per data-vs-MC) before being added —
same verification pattern as every prior addition to this mapping.

*Physics effect — CMS:* Registers the H→γγ study's own input datasets;
without these entries, the same silent-fallback/loud-failure behavior
described in T1-12/T2-18 would apply to them.

*Physics effect — ATLAS:* None.

*Classification:* **KEEP-OURS-PRIVATE** — these are this fork's own study's
specific record IDs, not a generic capability; the generic capability they
exercise (T2-18's loud failure) is what's actually proposable.

---

**T2-21** — `services/parsing/threaded_processor.py:248 @ master` vs `:350-417 @ feature`

*What differs:* `ParsingStatisticsCollector` gains
`_failure_reason_counts` (a dict of exception-type-name → count, populated
in `record_failure`) and `record_probe_stats`/`_n_probe_retries`/
`_n_probe_final_failures`/`_files_with_probe_retries` (populated from
T2-17's probe callbacks), both surfaced through `get_summary()`'s new keys
and consumed by T2-11's reporting.

*Physics effect — CMS and ATLAS, identically:* Pure bookkeeping; no effect
on which events are selected or how masses are computed.

*Classification:* **KEEP-OURS-PROPOSE** — bundled with T2-11/T2-17 (Part 3,
Issues D/E).

---

**T2-22** — `services/parsing/threaded_processor.py:89-159 @ master` vs `:114-260 (approx.) @ feature`

*What differs:* When `read_event_weights` is enabled, a `PartialFileReadError`
(a file whose read failed partway through but whose completed prefix is
normally still retained and yielded, per the fork's existing behavior) is
now instead treated as a **loud, aggregated failure**
(`RequiredScalarBranchMissingError`, T2-14), not a partial batch.

*Physics effect — CMS:* Documented rationale in the code: a partial read used
to still be yielded (its events, including any `genWeight`, get used
downstream) while the file itself was only reported via `on_error`, never
`on_success` — so it would never land in a `processed_urls` list built from
`on_success` alone, meaning its `genEventSumw` (T2-10) would be silently
excluded from the aggregation while its events' `genWeight` values were
still used — biasing the MC normalization's numerator-vs-denominator upward.
The code's own comment further establishes that this situation, if it
occurs, is *always* a simulation file (a data file would already have raised
`SimulationFieldRequestedOnDataError` earlier), so this new branch never
fires for real collision data or for any run with `read_event_weights` off.

*Physics effect — ATLAS:* None — only reachable when `read_event_weights` is
set, CMS-only today.

*Classification:* **KEEP-OURS-PROPOSE** — closes a specific, well-reasoned
MC-normalization correctness gap; bundled with T2-04/05/10/19 (Issue N).

---

**T2-23** — `services/parsing/trigger_requirements.py` (new file) @ feature vs `: (does not exist) @ master`

*What differs:* New module implementing T2-03/T2-08's HLT filter:
`validate_trigger_requirements`, `apply_trigger_requirement`,
`trigger_group_branches`. Booleans are defensively coerced with
`.astype(bool)` in case a caller feeds a differently-typed array "from a
non-NanoAOD source" (the module's own docstring already anticipates
experiment-generic reuse).

*Physics effect:* Same as T2-03/T2-08.

*Classification:* **KEEP-OURS-PROPOSE** — same issue (Part 3, Issue M).

---

**T2-24** — `services/parsing/validated_runs.py` (new file) @ feature vs `: (does not exist) @ master`

*What differs:* New module implementing T2-02/T2-07's golden-JSON filter.
Parses and validates the JSON shape with error messages naming the specific
problematic run/entry (not a generic parse error), packs `(run,
luminosityBlock)` into a single `uint64` key (`run << 32 | lumi`, with a
comment noting CMS run numbers and lumisection numbers both comfortably fit
32 bits each) for a fully vectorized membership test, and is deliberately
kept separate from `event_selection.py` specifically because — per its own
docstring — this is "a data-quality gate that either applies in full or not
at all... and, critically, must never be silently applied to simulation",
unlike the physics-analysis choices in `event_selection.py`.

*Physics effect:* Same as T2-02/T2-07, including the same ATLAS-applicability
caveat (UNVERIFIED — the JSON shape is CMS-specific; the mechanism is
generic).

*Classification:* **KEEP-OURS-PROPOSE** — same issue (Part 3, Issue L).

---

### Classification totals

*(Corrected. T1-17 moves from KEEP-OURS-PRIVATE to ADOPT-UPSTREAM. T1-18
moves from KEEP-OURS-PRIVATE to NEEDS-DECISION — **not** to ADOPT-UPSTREAM;
see T1-18's own entry for why an AST check performed for a separate branch-
alignment task found its "no executable difference" claim did not hold the
way T1-17's did. Net effect: ADOPT-UPSTREAM +1, KEEP-OURS-PRIVATE −2,
NEEDS-DECISION +1, verified by recounting the 20 Tier-1 and 24 Tier-2 items
directly rather than assumed.)*

| | ADOPT-UPSTREAM | KEEP-OURS-PROPOSE | KEEP-OURS-PRIVATE | NEEDS-DECISION | Total |
|---|---|---|---|---|---|
| Tier 1 | 1 | 11 | 6 | 2 | 20 |
| Tier 2 | 0 (N/A by construction) | 23 | 1 | 0 | 24 |
| **Total** | **1** | **34** | **7** | **2** | **44** |

---

## Part 2 — Extra scrutiny on physics

### (a) `KNOWN_MASSES` units — quantifying the corruption, and separately flagging the fork's own rounding

**The corruption mechanism, quantified.** Upstream's `KNOWN_MASSES` (MeV
values) is only correct paired with its own unconditional
`_convert_array_to_gev` (÷1000) call on every computed invariant mass
(T1-08/T1-09). If CMS data (whose `pt`/`eta`/`phi`/`mass` branches are
already GeV, confirmed on real data) were run end-to-end through upstream's
current code exactly as it stands, the effect is **not** "the mass constant
is off by 1000×, causing a subtle bias in one term of the invariant-mass
formula" — it is that the *entire final invariant mass* gets divided by 1000
regardless of the constant's role, because that division is unconditional
and independent of which unit each object's mass actually is. A genuine 91
GeV dimuon (Z-peak) invariant mass would compute as ~0.091 — wrong by
exactly three orders of magnitude, uniformly, for every combination,
trivially visible on the very first histogram (nothing would land anywhere
near a known resonance). This is the same, single mechanism as T1-09/T1-10,
not a second independent bug — `KNOWN_MASSES`' own MeV values are internally
*consistent* with upstream's unconditional-scaling design; the actual defect
is that the design's implicit assumption ("every release is MeV-native")
is false for CMS, and — independently confirmed via T1-10's own schema
comment — also false for at least one ATLAS release
(`"2025e-13tev-beta"`).

**Separately: the fork's own muon mass is a rounded value — flagged, not
fixed, per explicit instruction.** Fork's `KNOWN_MASSES["Muons"] = 0.105`
GeV vs. PDG's `0.1056583755` GeV — **0.6221% low**
(`(0.1056583755 − 0.105) / 0.1056583755`). Quantifying where this does and
doesn't matter, using the two-body invariant mass relation
`m_inv² ≈ 2 m_μ² + 2(E₁E₂ − p⃗₁·p⃗₂)`:

- **Near the Z peak (~91 GeV) or Higgs (~125 GeV):** the `2m_μ²` term
  contributes ≈0.022 GeV² against an `m_inv²` of ≈8,281 GeV² (Z) or ≈15,625
  GeV² (Higgs) — a relative contribution on the order of **10⁻⁶**. A 0.62%
  error in a quantity contributing at the 10⁻⁶ level is utterly negligible,
  swamped many times over by NanoAOD's own momentum-scale/resolution
  uncertainty (≳1% typically). **Negligible.**
- **Near the kinematic threshold (M close to 2·m_μ ≈ 0.211 GeV, i.e. very
  low-mass, highly collimated dimuon pairs):** here the mass term is
  comparable to or dominates `M²` itself, and the sensitivity of the
  reconstructed mass to the input mass constant is order-1 (not the ≈10⁻⁶
  suppression seen at high mass) — a 0.62%-low mass constant can propagate
  into a reconstructed-mass shift of comparable fractional size (order
  0.1–0.6%, depending exactly how close to threshold) in that specific
  regime. **Not negligible relative to that regime's own precision.**

This is stated only as a quantified flag on where the rounding does and
doesn't matter, per explicit instruction: it is **not** offered as an
explanation for, and does not resolve, the separately-known low-mass
excess in the m0m1j0 study — that question remains, as instructed, entirely
outside this document's scope.

### (b) `native_pt_unit` / `schema_needs_mev_to_gev_conversion` — confirmed, not merely plausible

**Confirmed true, by direct code reading on both sides, independently
corroborated by a pre-existing document.** Upstream's `schemas.py` contains
**zero** occurrences of `native_pt_unit`, `get_native_pt_unit`,
`schema_needs_mev_to_gev_conversion`, or any equivalent per-release unit
tag — verified via `git diff`/`git grep` returning empty for all four
searches against `upstream/master`'s `schemas.py`. Upstream's
`_convert_array_to_gev` call in `im_pipeline.py` is unconditional (T1-09),
with nothing to gate it even if it wanted to. The fork's own
`"2025e-13tev-beta"` schema entry (T1-10) documents, in its own comment, a
direct real-data cross-check establishing this ATLAS release is GeV-native:
for MC dsid 301204, `lep_pt` median/max match "the same physical values as
2024r-pp's MeV numbers for the same sample divided by 1000" — i.e., someone
already confirmed by hand that treating this release as MeV-native and
dividing by 1000 would be wrong.

Combined with T1-09's CMS finding, this means: **upstream's current code, if
pointed at either (a) any CMS NanoAOD data, or (b) ATLAS release
`"2025e-13tev-beta"`, would silently compute every invariant mass exactly
1000× too small, with no error, no warning, and no CMS involvement required
to trigger case (b).** This is, as the brief anticipated, the single
strongest, most concretely-evidenced case in this entire document — and it
is independently corroborated by `docs/UPSTREAM_SYNC_TRIAGE.md`'s own,
separately-conducted triage (Part 0), which flagged upstream's
`f43cc93` commit for the identical reason before this task began.

### (c) Binning — footnote only, per explicit instruction

The shared pipeline uses fixed 10 GeV histogram bins from 0–10 TeV
(`docs/CMS_KNOWN_LIMITATIONS.md`: "Histogram bin width is fixed at 10 GeV
rather than resolution-based... deliberately parked for a later task").
arXiv:2501.05603 ("BumpNet") instead uses variable bin widths — half the
combined-object mass resolution σ(m), with σ evaluated at pT = m/2 — and its
own histogram-inclusion criteria require ≥100 events and >30 bins, which the
fixed-10-GeV scheme cannot always satisfy for narrow-mass channels. This is
recorded here as a cross-reference only, exactly as instructed: **propose
nothing, change nothing.**

### (d) `services/parsing/event_deduplication.py` — fork-only, described in full

`EventDeduplicator` (T1-19) is a single stateful instance per pipeline run.
Its key, `_composite_keys`, packs `run`, `luminosityBlock`, and `event` into
one Python object-dtype (arbitrary-precision) integer via
`(run << 96) | (luminosityBlock << 64) | event`, chosen specifically to
avoid any overflow or collision risk on the full 64-bit range of `event`.
`filter_new` keeps the **first** occurrence of each key seen (across the
whole run, not just within one batch — `_seen` persists across calls) and
drops every subsequent occurrence, whether the repeat is within the same
batch or across a previously-processed batch/record; it reports drops
broken down by run number for a per-era summary. It is a **no-op** — returns
the input array completely unchanged — whenever the input events lack all
three of `run`/`luminosityBlock`/`event` (`has_id_fields` returns `False`),
which makes it always safe to call unconditionally.

**Behavior if run on ATLAS data:** ATLAS schemas never declare
`event_id_branches` (T1-11), so no ATLAS-parsed event record ever carries
`run`/`luminosityBlock`/`event` as top-level scalar fields in the first
place. `has_id_fields` would therefore always return `False` for ATLAS data,
and `filter_new` would be an unconditional no-op — it is not merely "safe"
for ATLAS in some approximate sense, it is **structurally unreachable**
for ATLAS as the code exists today, since `EventDeduplicator` is never even
instantiated except from `orchestration/handlers/parsing_handler.py`'s
`selection_by_record`-gated code path (T1-14), which no ATLAS config
populates.

---

## Part 3 — Draft GitHub issues

**These are plain text. None of them has been filed, referenced, or in any
way communicated to upstream. They exist only inside this file, for Matan
and his supervisor to review before any decision is made about whether to
ever raise them.**

Each issue below is a consolidation of one or more KEEP-OURS-PROPOSE items
from Part 1 (named explicitly), since a real GitHub issue proposing "please
add per-record selection AND cross-record de-duplication AND the safety
guard for it" is far more useful to a maintainer than three disconnected
one-line issues for the same feature.

---

### Issue A — Release-tagged native momentum/energy unit handling (supersedes issue #28's framing)

*Covers: T1-08, T1-09, T1-10, T1-13*

**Problem.** This project's invariant-mass calculation unconditionally
converts every computed mass by ×1e-3 (`_convert_array_to_gev`), on the
assumption that every input release stores momentum/energy in MeV. **This
assumption is false for at least one ATLAS release already in this
project's own schema table**: release `"2025e-13tev-beta"` was independently
verified (real-data cross-check against a known-MeV release, same MC
sample) to be GeV-native. Under the current unconditional-conversion design,
any invariant mass computed from this release is silently wrong by a factor
of exactly 1000 — with no error, no warning, and no involvement of any
non-ATLAS data format. This is a live latent bug affecting ATLAS data today,
independent of any other experiment.

The same root problem also blocks correct support for any GeV-native data
format in general (e.g. CMS NanoAOD, whose `pt`/`eta`/`phi`/`mass` branches
are GeV-native, confirmed on real data: an e-pair invariant mass reads ~91
before any scaling).

**Proposed fix (generic).** Tag each schema entry in `RELEASE_SCHEMAS` with
an explicit `native_pt_unit: "MeV" | "GeV"`. Gate the ×1e-3 conversion behind
a resolver function that defaults to "convert" (today's behavior) for any
release with no tag, an unrecognized tag, or a lookup failure, and skips the
conversion **only** when a release is explicitly tagged `"GeV"`.

**Opt-in / default-off, verified in the reference implementation.** Every
*existing* schema entry keeps converting unless someone explicitly adds a
`native_pt_unit: "GeV"` tag after verifying it — the resolver's own default
is "unknown → convert." This means adopting this mechanism changes the
output of **zero** existing configs unless a maintainer deliberately opts a
specific release in.

**Evidence.** Not UNVERIFIED — directly confirmed by reading both code
paths and the schema table's own documented real-data cross-checks (see this
document's Part 2(b)). Independently corroborated by a separate, earlier
triage of this same repository's history (`docs/UPSTREAM_SYNC_TRIAGE.md`),
which flagged the specific upstream commit that introduced the MeV-only
assumption (`f43cc93`) for this exact reason, before this document existed.

---

### Issue B — Missing `bjets:` kinematic-cuts entry silently leaves tagged b-jets uncut (ATLAS-affecting today)

*Covers: T1-02, T1-03, T1-04, T1-05, T1-07*

**Problem — leading with ATLAS impact.** `filter_events_by_kinematics`
applies a `kinematic_cuts` entry only to the exactly-named collection it
matches — a `jets:` entry is never applied to a `BJets` collection produced
by b-tagging. **This project's own ATLAS-only config
`config.short_parse_btag.yaml` has `enable_jet_tagging: true` and a `jets:`
cut but no `bjets:` cut today** — meaning any b-tagged jet in a run of this
exact file receives zero pT/η cuts, silently, regardless of what its
`jets:` block specifies. This was independently discovered via manual code
tracing during unrelated work and confirmed on real CMS output (a b-jet at
15 GeV / |η|=2.90 despite `pt_min: 30`/`eta_max: 2.5`), but the underlying
code defect is entirely experiment-neutral and the ATLAS config above shows
it is not merely a CMS scenario.

**Proposed fix (generic).** Add a config-construction-time `WARNING` (no
behavior change, no exception) whenever `enable_jet_tagging: true` and
`kinematic_cuts` has a `jets` entry with no matching `bjets` entry.

**Opt-in / default-off.** This is a logging-only addition — byte-identical
output for every existing config on either experiment, verified by reading
the guard's own code (it only calls `logging.warning`, nothing else).

**Evidence.** Confirmed directly: `config.short_parse_btag.yaml` (ATLAS)
has `enable_jet_tagging: true` and no `bjets:` cut as of this writing,
independent of anything CMS-related.

**Limitation of this issue as drafted — stated plainly, not redrafted here.**
The fix above is a `WARNING` only. If filed and accepted exactly as written,
it makes the mistake visible in a log; it does **not** stop it from
happening. Upstream's ATLAS-only `config.short_parse_btag.yaml` would still,
after this fix, tag b-jets and then apply zero pT/η cuts to them — the run
would simply also print a warning while doing so. Actually correcting the
cut itself means adding a `bjets:` block to upstream's own ATLAS config
file, and that is a different kind of change entirely: it would alter which
b-jets pass selection in an existing ATLAS analysis, i.e. it changes ATLAS
physics output. A change that changes physics output for an existing
config cannot be proposed as opt-in/default-off the way every other issue
in this document is — there is no "off" setting for "this config's own
numbers now cut differently." That makes it a physics decision for ATLAS
analysers to make deliberately, not something a generic-pipeline issue can
carry or default its way into. This document does not draft that config
change, and does not propose one.

---

### Issue C — Per-record selection profiles + cross-trigger-stream event de-duplication

*Covers: T1-06, T1-11 (superseded by its generalized form, see note),
T1-14, T1-16 (superseded), T1-19, T2-09*

**Problem, stated generically.** An analysis that combines multiple primary
datasets/trigger streams covering overlapping data (e.g. CMS's
SingleElectron + SingleMuon primary datasets from the same run era) faces
two problems with no generic support today: (1) each stream may need its own
per-record selection profile (e.g. requiring a different lepton flavor per
record) rather than one global selection applied uniformly, and (2) an event
firing multiple streams' triggers is legitimately present in more than one
input file and must be de-duplicated by a stable per-event key, not
double-counted.

**Proposed fix (generic).** A `selection_by_record` config block mapping a
record identifier to its own selection overrides; a stateful
de-duplicator keyed on a schema-declared per-event identity (e.g.
`run`/`luminosityBlock`/`event` for CMS, but declared per-schema, not
hardcoded); and a mandatory guard that refuses to apply de-duplication to
anything that looks like simulation (since a Monte Carlo sample's per-event
identity fields, if it has any, are not guaranteed to be a genuine
unique-event key — simulated NanoAOD famously sets `run == 1` for every
event).

**Opt-in / default-off.** All of it is gated behind `selection_by_record`
being present at all; no config on either experiment sets this key today,
so adopting it changes nothing for any existing run.

**Evidence.** CMS: documented, with retention percentages, in
`docs/CMS_KNOWN_LIMITATIONS.md` (SingleMuon retention rose from ~3% to
~75–76% once this was built). ATLAS: **UNVERIFIED — would require an ATLAS
analysis actually combining overlapping trigger streams to test against**;
no such ATLAS config exists in this repository today, so this claim is
reasoning-only, not tested.

*Note for whoever picks this up:* prefer T2-15's generalized named-
scalar-group mechanism over T1-11/T1-16's original `EventIds`-only version
if implementing this from scratch — it is a strict, cleaner generalization
of the same idea.

---

### Issue D — Loud failure for missing required branches/fields, unregistered record schemas, and high file-open-failure rates

*Covers: T1-15, T1-12 (context), T2-11, T2-14, T2-16, T2-18, T2-21*

**Problem, stated generically.** Several categories of misconfiguration or
infrastructure failure currently degrade silently instead of erroring: (1) a
record ID with no registered branch-naming schema falls back to
auto-detection that is documented not to work for at least one real naming
convention, previously producing 0 files processed with only a `WARNING`
log line; (2) a declared-but-unreadable required scalar branch or per-object
field is silently dropped rather than raising; (3) a record whose files
mostly fail to open finishes with near-zero events and no error at all,
indistinguishable from a record that genuinely has low yield.

**Proposed fix (generic).** A small family of specific exceptions
(subclassing a common base so existing `except ValueError`/generic-exception
handling isn't broken) for each case, deliberately **not** swallowed by the
per-file processing loop the way an ordinary parse failure is — instead
aggregated across a whole record into one clear, run-aborting error listing
every affected file. Separately, a configurable file-open-failure-rate
threshold (e.g. 20%) above which the run aborts instead of silently
continuing with a near-empty result. All purely additive: a run where
everything is correctly configured and every file opens is unaffected.

**Opt-in / default-off.** These change behavior only in a failure case that
previously produced silently-wrong output; the "correct configuration,
healthy infrastructure" path — every completed run to date on either
experiment — is unaffected either way, so there is no meaningful sense in
which this needs its own separate opt-in flag; it is a strict improvement
with no successful-run side effect.

**Evidence.** Not UNVERIFIED for the record-schema case: this exact failure
mode (0/0 files processed for an unregistered record) previously occurred
for real, for CMS records 30522/30555 before they were registered
(T1-12). The file-open-failure-rate case and the missing-branch cases are
design-level protections against described-but-not-yet-observed scenarios on
this project (network blips, exhausted connection pools) — reasoning-based,
not fabricated, but not each individually reproduced in this task.

---

### Issue E — Retry transient per-branch read failures before giving up (ATLAS-relevant)

*Covers: T1-15 (related theme), T2-17, T2-21 (probe-stats half)*

**Problem — leading with ATLAS impact.** A per-branch accessibility check
that fails once is currently treated as permanent — the branch is dropped
from that batch's schema for the rest of the file. **This project's own
earlier ATLAS work (`analysis/m0m1j0-mumujet`, documented in
`docs/UPSTREAM_SYNC_TRIAGE.md`) hypothesized exactly this mechanism as the
cause of a real bug**: `Muons_looseId`/`Muons_pfRelIso04_all` silently
vanishing from merged output, attributed to XRootD's background handle-cache
pruner racing with active reads and throwing an "Invalid operation"
exception on an otherwise-good branch. This is a generic network/storage
reliability issue, not specific to any one experiment's data format.

**Proposed fix (generic).** Retry a branch read that fails (but is
confirmed present in the file's own branch list — a genuinely absent branch
still fails immediately, no retry) with a short backoff schedule (e.g. 2s,
5s, 10s) before giving up, recording retry/final-failure counts purely for
visibility.

**Opt-in / default-off.** No config flag needed — this changes behavior only
in the failure case (a branch that currently permanently vanishes after one
transient failure now has a chance to recover); a file where every branch
reads cleanly on the first try, which is every file processed to date on
either experiment per the code's own comment, is entirely unaffected,
including its timing (no retry loop is even entered).

**Evidence.** UNVERIFIED that this specific mechanism (retry-with-backoff)
would have fixed the specific historical ATLAS bug that motivated flagging
it here — the prior triage's own conclusion was "I can't be certain without
testing," and no such test was run in this task (out of scope: no cluster
access). Stated honestly as a plausible, well-reasoned fix for a
described failure mode, not a confirmed one.

---

### Issue F — Generic per-object boolean and |η|-window kinematic cuts

*Covers: T2-12, T2-13*

**Problem, stated generically.** The kinematic-cut vocabulary
(`pt_min`/`eta_max`/`rel_isolation_max`) cannot express "this boolean flag
must be true," "at least one of these flags must be true," or an |η|-window
exclusion — all physically meaningful selection criteria for various object
ID working points across experiments.

**Proposed fix (generic).** `bool_require`/`bool_any_of` (accepting a
genuinely boolean field, or an integer field whose only values are 0/1,
raising for anything else — e.g. a multi-valued ordinal field is rejected
rather than silently mis-cast) and `eta_exclude` (a symmetric |η|-window
exclusion).

**Opt-in / default-off.** New, optional cut-block keys; absent for every
existing config on either experiment, verified by direct code reading —
these keys are simply never checked unless present.

**Evidence.** CMS: motivated by real, named use cases (photon ID
`electronVeto`/`mvaID_WP90`; barrel/endcap supercluster-η acceptance gap).
ATLAS: **UNVERIFIED — reasoning only**; no ATLAS config currently has an
identified use case for these keys, though nothing about the mechanism is
CMS-specific.

---

### Issue G — (capability gap, not yet built anywhere) Generic numeric cut on an arbitrary per-object field

*Design-only — not a fork/upstream difference; described per this task's
explicit brief, no implementation exists on either branch.*

**Problem.** The only numeric per-lepton isolation cut,
`rel_isolation_max`, is hardcoded to electrons only
(`ELECTRON_REL_ISOLATION_FIELD`). CMS's own muon isolation branch,
`Muon_pfRelIso04_all`, is already a relative quantity (unlike the electron
field, which needs a cone-energy/pT computation) — there is currently no way
to express a numeric cut on it, or on any other arbitrary per-object numeric
field, at all.

**Proposed fix (generic, design sketch only — not built, not tested).** A
generic `{"field_min"/"field_max": {"field_name": value}}`-style cut type,
analogous to the boolean cuts of Issue F but for arbitrary numeric fields
rather than a hardcoded isolation-specific one.

**Status.** Explicitly out of scope for this task to design in detail or
implement — flagged here only because the brief specifically named it as an
expected candidate worth recording as a gap. No code exists for this on
either the fork or upstream.

---

### Issue H — (capability gap, not yet built anywhere) Integer/bit-mask per-object cuts (e.g. CMS `Jet_jetId`)

*Design-only — not a fork/upstream difference.*

**Problem.** CMS's `Jet_jetId` is an integer bitmask (not a plain 0/1 field —
its real-world values are things like 0, 2, 6), so it cannot be expressed
even by Issue F's `bool_require`/`bool_any_of` (which explicitly *rejects*
a non-0/1-valued integer field as a probable configuration mistake, by
design). There is currently no generic way to require a specific bit be
set in an integer field.

**Proposed fix (generic, design sketch only).** A `bit_require: {field:
name, bits: [...]}`-style cut checking that specific bits are set via
bitwise AND, distinct in both name and validation from the boolean cuts of
Issue F (so the existing "reject non-0/1 integers" safety check in
`bool_require` is not weakened).

**Status.** Out of scope to implement; recorded as a described gap only, per
the brief.

---

### Issue I — (capability gap, not yet built anywhere) ΔR-based overlap removal between object collections

*Design-only — not a fork/upstream difference.*

**Problem.** `docs/CMS_KNOWN_LIMITATIONS.md` already documents that, with no
overlap removal, CMS electron/photon/jet collections (frequently the same
underlying calorimeter cluster reconstructed multiple ways) produce
spike-shaped "self-pair" histograms near 0 GeV for 2-body combinations that
cross those collections — and separately notes an unrelated m0m1j0 finding
worth stating here explicitly since it is directly on-topic and not itself
sensitive: **93% of the leading jet in the m0m1j0 selection fell within
ΔR<0.4 of a selected muon**, meaning the two collections substantially
overlap in that analysis. The tau-specific instance of this general issue is
separately tracked and deliberately deprioritized per an existing team
decision (`docs/CMS_KNOWN_LIMITATIONS.md`, discussed with Maryna,
2026-09-03) — not reopened here.

**Proposed fix (generic, design sketch only).** A configurable ΔR-based
cleaning step removing an object from one collection if it falls within a
threshold ΔR of any object in another named collection, generic across any
two collections/experiments.

**Status.** Out of scope to implement; the existing tau-vs-electron/jet
instance of this same general problem is intentionally deferred per team
decision, not reopened by recording this gap.

---

### Issue J — (question, not a bug report) Why was the upstream test suite removed?

*Covers: T1-20*

Framed deliberately as a question rather than an issue, per this task's own
brief. Upstream commit `6ff3c31` ("remove tests", 2026-09-09) deleted all
seven test files that existed in upstream's history at that point, several
of them added by upstream's own preceding commits as regression coverage
for real fixes. The commit message gives no reasoning. **This document
takes no position on whether this was a deliberate policy choice (e.g. tests
being restructured or moved elsewhere, not yet visible from this diff) or an
oversight** — that would require asking upstream directly, which is outside
this task's scope entirely. Recorded here only so the question exists
somewhere durable, for Matan/his supervisor to decide whether it's ever
worth asking.

---

### Issue K — CMS Open Data URL classification for cache validation

*Covers: T2-06*

**Problem.** Cache-validation logic classifies every cached URL by matching
ATLAS's RUCIO-namespace patterns; a CMS record's URL (a different path
convention, EOS-based) matches neither pattern and is rejected as
unclassifiable — this caused a real crash on a valid cache-hit CMS URL.

**Proposed fix.** An EOS-path-based classifier used only for
`"record_<id>"` cache keys belonging to a registered CMS schema; every other
key keeps the exact prior ATLAS logic, unchanged.

**Opt-in / default-off.** Structurally cannot affect any ATLAS key — the new
code path is only reachable for a CMS-record-shaped cache key.

**Evidence.** Confirmed: this crash was previously observed on the first
cluster job using a pre-written cache, per the code's own comment describing
it directly.

---

### Issue L — Pluggable certified-run/lumisection filtering ("golden JSON" / GRL-style)

*Covers: T2-02, T2-07, T2-24*

**Problem, stated generically.** There is no generic way to restrict data
(never simulation) to certified good runs/lumisections — a standard
data-quality step in both CMS (golden JSON) and ATLAS (Good Run Lists),
though the two use different file formats.

**Proposed fix.** A vectorized run/lumisection membership filter, applied
before selection and de-duplication, with a mandatory guard against ever
being applied to simulation.

**Opt-in / default-off.** Gated entirely behind an optional config path; no
config sets it today.

**Evidence — honest caveat.** CMS: the shipped loader parses CMS's specific
golden-JSON shape and was verified against this project's own reference
file (see `data/cms/validated_runs/README.md`). ATLAS: **UNVERIFIED — reasoning
only.** ATLAS's GRL format is XML-based and structurally different; the
*mechanism* (vectorized run/lumi keying, MC guard, pre-selection ordering)
generalizes cleanly, but the *loader* as it exists today would need a new
ATLAS-GRL-specific parser, not a drop-in reuse. This issue should be framed
to a maintainer as "here's a mechanism, CMS-shaped reference implementation
included" rather than "this already works for ATLAS."

---

### Issue M — Configurable HLT/trigger-path requirement filter

*Covers: T2-03, T2-08, T2-23*

**Problem, stated generically.** No generic way exists to require a
specific trigger path fired, in data or simulation, applied consistently
before selection/de-duplication.

**Proposed fix.** A `{"mode": "any"|"all", "paths": [...]}`-shaped filter
against a schema-declared trigger scalar-branch group, with an optional
per-record override.

**Opt-in / default-off.** Gated behind an optional config key; no config
sets it today; no CMS-specific assumption in the mechanism (branch names are
config-supplied, not hardcoded).

**Evidence.** Design is generic and directly usable by ATLAS as-is (unlike
Issue L, no format mismatch exists here) — **UNVERIFIED only in the sense
that no ATLAS config has actually exercised it**, not because the mechanism
itself has any CMS dependency.

---

### Issue N — Optional MC generator-weight and pileup-info reading, with normalization bookkeeping

*Covers: T2-04, T2-05, T2-10, T2-19, T2-22*

**Problem, stated generically.** No generic way exists to read per-event
Monte Carlo generator weights or pileup information, or to aggregate a
correct normalization denominator (sum of generator weights) that is
guaranteed to cover exactly the same file set as whatever numerator a
downstream analysis computes.

**Proposed fix (generic pattern; CMS branch names as reference, not as the
generalized contract).** Per-file (not per-run) simulation detection by
inspecting a file's own branch list, not a global data/MC flag — necessary
because CMS record IDs (unlike ATLAS release-years) don't split into a
data/MC-paired naming convention. A hard error (not a silent no-op) if a
simulation-only field is requested on what looks like real data. Aggregation
of the normalization sum restricted to exactly the files that succeeded in
this run, with any partial/failed read treated as a loud failure rather than
silently excluded from the sum while its events are still used elsewhere.

**Opt-in / default-off.** Two boolean flags, both default `False`; every
existing config is unaffected.

**Evidence.** CMS-specific branch names (`genWeight`, `PV_npvsGood`,
`Pileup_nTrueInt`) are the reference implementation; an ATLAS equivalent
would need its own constants and its own simulation-detection logic — this
issue should be framed as "here is the pattern and a working CMS
implementation of it," not as an ATLAS-ready feature.

---

### Issue O — Generic hooks to read extra branches/fields beyond a schema's defaults

*Covers: T2-01, T2-15 (as the underlying mechanism), T2-16*

**Problem, stated generically.** A study needing one or two extra fields
beyond a schema's default field list (e.g. photon ID flags for an H→γγ
analysis) currently has no way to request them without editing the shared
schema itself.

**Proposed fix.** `extra_scalar_branches`/`extra_object_fields` config
hooks, merged with a schema's own declarations, validated for name
collisions with existing collections/reserved fields, and raising loudly
(not silently dropping) if a requested extra field turns out unreadable in a
specific file.

**Opt-in / default-off.** Both default to `None`; confirmed by the field's
own code comment to "reproduce existing behaviour exactly" when unset.

**Evidence.** Not UNVERIFIED — directly used by this fork's own H→γγ study
today (the motivating, working use case for `Photon_electronVeto`/
`Photon_mvaID_WP90`).

---

*(End of document. No further edits were made to any other file. No network
request other than local `git` operations against the already-fetched
`origin`/`upstream` remotes was made in the course of writing this
document.)*
