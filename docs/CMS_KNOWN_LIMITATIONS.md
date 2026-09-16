# CMS pipeline — known limitations and future requirements

## Current scope: all four CMS records (SingleElectron + SingleMuon)

`config.cms_records_master.yaml` now uses **all four** CERN Open Data records:

| Record | Dataset | Selection |
|---|---|---|
| 30529 | `/SingleElectron/Run2016G-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD` | ≥1 electron (global `particle_counts`) |
| 30562 | `/SingleElectron/Run2016H-...` | ≥1 electron |
| 30530 | `/SingleMuon/Run2016G-...` | ≥1 muon (`selection_by_record`) |
| 30563 | `/SingleMuon/Run2016H-...` | ≥1 muon |

This replaces the earlier SingleElectron-only scope, which existed because a
single blanket "≥1 electron" cut applied to every record discarded ~97% of the
SingleMuon data.

### How SingleMuon data is now included

1. **Per-trigger-stream selection.** `parsing_task_config.selection_by_record`
   maps a record id to its own `particle_counts` block. The SingleMuon records
   require ≥1 muon and drop the electron requirement; records not listed use the
   global block (≥1 electron). Kinematic cuts (pt/eta per lepton type) are
   unchanged and stay global. Implemented in
   `orchestration/handlers/parsing_handler.py`.

2. **Per-event source tracking.** The parser now reads the CMS event id
   branches (`run`, `luminosityBlock`, `event`) and tags every event with an
   integer `source_record` field, *before* any chunk merging
   (`services/parsing/schemas.py`, `services/parsing/file_parser.py`). This
   replaces the old filename-only record labelling, which mislabelled events
   whenever multiple records shared an output chunk.

3. **De-duplication.** SingleElectron and SingleMuon datasets of the same run
   era share run-number ranges, so an event that fired both triggers appears in
   both. `services/parsing/event_deduplication.py` keys on
   `(run, luminosityBlock, event)` and keeps the first copy seen; the handler
   processes the muon-requirement records first, so the **SingleMuon copy is
   kept** and the SingleElectron duplicate is dropped.

Verified 2026-09-03 (`config.cms_fourrecord_test.yaml`, 2 files/record):
SingleMuon retention **~75–76%** (was ~3%); a clear dimuon Z-peak at 90–92 GeV
(~17× off-peak, much stronger than the old electron-only muon sample); the
SingleElectron path byte-for-byte unchanged; duplicate events identified and
removed with correct priority. Full write-up:
`reports/cms_singlemuon_support/summary.md`.

### Still to do at full scale

- The de-dup overlap rate seen in the small verification run (~0.003%) is far
  below the ~2% expected for the full datasets, because the 2-files-per-record
  subsets barely share lumisections. A full or lumi-aligned run is needed to
  confirm the ~2% figure.
- `EventDeduplicator` holds a plain Python set of event keys. At full scale
  (~2e8 events) this needs a more memory-frugal structure (packed keys /
  per-era `np.unique`).
- Raw `m0m1` has a small unphysical tail (a NanoAOD bad-value sentinel,
  `min = −16384`); pre-existing in the muon data, fully excluded from the
  post-processed `_main` output. Not yet investigated.

## Related, separately tracked

- **Histogram bin width** is fixed at 10 GeV rather than resolution-based, so
  some narrow-mass channels can never reach BumpNet's ">30 bins" requirement.
  Deliberately parked for a later task.
- **Object overlap** — in CMS NanoAOD an electron is normally also
  reconstructed as a photon and often as a jet (same calorimeter cluster).
  With no overlap removal (delta-R cleaning between the electron, photon and
  jet collections), 2-body combinations such as electron+photon or
  electron+jet are dominated by ~0 GeV "self-pairs", producing spike-shaped
  histograms. This is an upstream reconstruction/selection gap, not a
  post-processing bug.

  Discussed with **Maryna** (2026-09-03): the tau-specific instance of this
  (tau objects overlapping electrons/jets) is a **known issue that is already
  tracked separately**, and the broader team has likewise **deprioritised** it.
  So this is **intentionally deferred**, consistent with the team's stance —
  not an oversight. Adding delta-R overlap removal remains a future decision.

## CMS b-jet tagging — now exercised

The CMS b-tagging path (`Jet_btagDeepFlavB` DeepJet discriminant → split
`Jets` into `Jets` + `BJets`) was **run for the first time on 2026-09-03**
(`config.cms_bjet_test.yaml`, DeepJet Medium WP 0.2598, parsing + mass-calc on
~5.5M SingleElectron events). Outcome: it runs end to end, tags ~7.7% of jets
(plausible for this sample), feeds `BJets` through the combinatorics, and the
b-jet invariant masses have sane shape and scale. Reported as "looks like real
physics", **not** validated — no known-resonance cross-check yet, and the
working point has not been tuned for these files. Full write-up:
`reports/cms_bjet_first_test/summary.md`.

### Fixed, and now guarded: `BJets` silently missing kinematic cuts

`services/calculations/physics_calcs.py`'s `filter_events_by_kinematics`
applies a `kinematic_cuts` entry only to the collection whose exact name it
matches — a `jets:` entry is only ever matched against `Jets`, never against
`BJets` (the tagged-jet collection `FileParser._calculate_btagging_and_split`
produces). Every CMS config that enabled jet tagging had only a `jets:`
entry and no `bjets:` entry, so **`BJets` received no pT/eta cut at all, in
every CMS run to date**, regardless of what the `jets:` block specified.
Found only by manual code tracing (no error, no warning) during the ttbar
b-tagging truth cross-check (`analysis/ttbar-btag-truth-crosscheck`), which
confirmed it on real output: BJets containing a 15 GeV jet and a
\|eta\|=2.90 jet despite `pt_min: 30`/`eta_max: 2.5`.

**Fixed** in the 9 affected CMS configs
(`fix/cms-bjets-kinematic-cuts`, merged to master) and on the
`analysis/ttbar-btag-truth-crosscheck` branch's own two configs, by adding a
`bjets:` entry matching each file's own `jets:` values. The code itself was
correct as-is (ATLAS's `config.yaml` already had a matching `bjets:` entry
and was never affected) — this was a config omission, not a bug fix.

**Guarded against recurring** (`fix/warn-on-missing-bjets-cuts`):
`domain/config.py`'s `ParsingConfig.__post_init__` now logs a WARNING at
config-construction time (i.e. before any parsing starts) whenever
`enable_jet_tagging: true` and `kinematic_cuts` has a `jets` entry but no
`bjets` entry — e.g. `"jet tagging is enabled and kinematic cuts exist for
'jets' but not 'bjets'; the BJets collection will receive NO kinematic
cuts"`. This is a warning only — it does not change parsing behavior or
raise an error, so an existing config that relies on this gap (there
shouldn't be any, but none is assumed) keeps running unchanged; it simply
makes the mistake visible in the log instead of requiring code tracing to
find, the way it was found this time.

## CMS validated-runs ("golden JSON") filter — new, not enabled anywhere yet

An optional data-quality filter, added for the H→γγ study
(`studies/hgg_cms/`) but general-purpose: it keeps only events whose
`(run, luminosityBlock)` falls inside a CMS-certified "good for physics"
range, per a committed golden-JSON file
(`data/cms/validated_runs/README.md` has the source, checksum and
content summary). Implemented in `services/parsing/validated_runs.py`;
hooked into `orchestration/handlers/parsing_handler.py` **before** any
`kinematic_cuts`/`particle_counts` selection and before de-duplication,
so a run/lumisection rejected by this filter is never counted as
"selected" by either later stage.

**New config key**, under `parsing_task_config`:

```yaml
parsing_task_config:
  # Optional. Path resolved from the repository root (or absolute).
  # Absent/omitted (the default -- every current config) = no-op,
  # identical behaviour to before this feature existed.
  validated_runs_json: data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt
```

**Not set in any existing config file** — this section is documentation
only. Enabling it is a deliberate per-config decision for whoever owns
that config's physics scope.

**Simulation guard.** Simulated NanoAOD always has `run == 1` for every
event (there is no real accelerator run for a simulated sample), so
naively applying a real-data run filter to simulation would silently
discard the entire sample. `apply_validated_runs_filter` raises a clear
error instead of running in that case, detected via either of two signals
(the CMS-side truth is `run == 1`; a `genWeight` field, if a caller
requested it through the general scalar-branch-group mechanism from the
prior task, is treated as an equally unambiguous signal). Also raises if
`run`/`luminosityBlock` aren't present at all (e.g. an ATLAS schema),
rather than silently passing every event through unfiltered.

**Format.** A JSON object, run number (string) → list of `[first, last]`
inclusive lumisection ranges — CMS's standard golden-JSON shape,
documented with an example in `data/cms/validated_runs/README.md`.
Malformed files raise a clear, specific error at load time (which run/
entry is wrong), not a generic parse failure.

**Verified against the DoubleEG Run2016G/H files this study uses**
(`studies/hgg_cms/impl_checks/lumi_coverage/`): every file's own
`LuminosityBlocks` tree was read (run/luminosityBlock only, not the full
`Events` tree) and compared against the certified list — see that
directory's summary for the coverage result and the luminosity this
implies.

## CMS HLT trigger requirement — new, not enabled anywhere yet

An optional filter, added for the H→γγ study (`studies/hgg_cms/`) but
general-purpose: keeps only events where one or more configured HLT
trigger bits fired. Implemented in
`services/parsing/trigger_requirements.py`; hooked into
`orchestration/handlers/parsing_handler.py` **after** the validated-runs
filter above and **before** any `kinematic_cuts`/`particle_counts`
selection and de-duplication, for the same reason: an event this filter
rejects must never be counted as "selected" by a later stage, and
de-duplication's `(run, luminosityBlock, event)` keys must only ever be
built from events that also pass the trigger requirement.

**New config key**, under `parsing_task_config`:

```yaml
parsing_task_config:
  # Optional. Absent/omitted (the default -- every current config) = no-op,
  # identical behaviour to before this feature existed.
  trigger_requirements:
    mode: any            # "any": at least one listed path fired. "all": every listed path fired.
    paths:
      - HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90
```

May also be overridden per record, under `selection_by_record[record]`
(same shape), analogous to that block's existing `particle_counts`
override.

**Not set in any existing config file** — this section is documentation
only.

**Applies to data AND simulation** — unlike `validated_runs_json`, there
is no simulation guard here: the design (`studies/hgg_cms/DESIGN_SELECTION.md`
Section 2, step 1) requires the same trigger bit in simulation as in data,
so that trigger inefficiency becomes part of the simulated signal
efficiency automatically.

**No branch listed twice.** The listed `paths` are read automatically
through the general scalar-branch-group mechanism (`services.parsing.
file_parser.FileParser._resolve_scalar_groups`), under the group name
`"Trigger"` — no need to also list them in `extra_scalar_branches`. If a
path happens to also be listed there under the same `"Trigger"` group
name, the two lists are merged and de-duplicated, not treated as a
collision.

**Loud failure for a missing required branch.** If `trigger_requirements`
(or `extra_scalar_branches`) is enabled and a file is missing one of its
declared branches, parsing no longer silently skips that one file and
continues — `FileParser` raises a specific
`RequiredScalarBranchMissingError` (a `ValueError` subclass, so existing
`except ValueError`/`assertRaises(ValueError)` code is unaffected) that
`FileParser.parse_file` and `ThreadedFileProcessor.process_files`
deliberately do not swallow, unlike every other parse failure (network
errors, corrupt files, ...), which keep today's exact behaviour: logged,
file skipped, run continues. `ThreadedFileProcessor.process_files`
aggregates every such error seen while parsing one record's files into a
single error listing every affected file and branch, raised once parsing
that record finishes (never before an existing file's real data is
processed, never silently). Every current config's files all have every
branch they declare, so this changes no existing configuration's observed
behaviour — see `studies/hgg_cms/impl_checks/trigger_branch_presence.json`
for the check confirming this trigger's own branch is present in every
DoubleEG and postVFP signal file this study uses.

**Verified against the DoubleEG Run2016G/H files and the ggH postVFP
signal file** (`tests/test_trigger_requirements.py`'s real-data
cross-check): the pipeline's per-event keep/reject decision matches a
direct `uproot` read of the trigger branch exactly, on 2,000-event samples
of each.

## CMS extra object fields + generic boolean object cuts — new, not enabled anywhere yet

Two related, general-purpose (not CMS-specific in mechanism) additions for
the H→γγ study, letting a config request additional per-object (jagged,
one-value-per-particle) fields and cut on boolean-valued ones, without
changing any existing config's parsed output.

**New config key**, under `parsing_task_config`:

```yaml
parsing_task_config:
  # Optional. Extra per-object fields, on top of each collection's existing
  # default list (pt/eta/phi/mass for Photons). Absent/omitted (the
  # default -- every current config) = no-op, identical fields/dtypes/
  # values to before this feature existed.
  extra_object_fields:
    Photons:
      - cutBased
      - mvaID
      - mvaID_WP80
      - mvaID_WP90
      - electronVeto
      - pixelSeed
      - r9
      - sieie
      - hoe
      - pfRelIso03_all
      - pfRelIso03_chg
      - isScEtaEB
      - isScEtaEE
      - eCorr   # bookkeeping only -- see the warning below

kinematic_cuts:
  photons:
    pt: {min: 20.0}
    bool_require: [electronVeto, mvaID_WP90]   # every listed field must be True
    bool_any_of: [isScEtaEB, isScEtaEE]        # at least one listed field must be True
```

**`extra_object_fields`** (`services/parsing/file_parser.py`'s
`_resolve_object_fields`, `FileParser.parse_file`/`_parse_opened_file`):
merges the requested fields into that collection's existing default list
(a field already in the default list is harmlessly de-duplicated, not an
error); naming follows the schema's own existing convention automatically
(`Photon_<field>` branch → `<field>` in the `Photons` collection), the same
mechanism that already resolves `pt`/`eta`/`phi`/`mass`. Requesting a
collection name the schema doesn't declare at all (a typo, e.g.
`"Jetz"`) is a configuration error. **A field genuinely missing from one
file's tree is a loud, non-swallowed error**
(`RequiredObjectFieldMissingError`, a subclass of task 3's
`RequiredScalarBranchMissingError`, so it's caught by exactly the same
"abort the run, list every affected file and field" handling already in
`FileParser.parse_file` and `ThreadedFileProcessor.process_files`) — never
a silent drop.

**`bool_require` / `bool_any_of`** (`services/calculations/physics_calcs.py`'s
`filter_events_by_kinematics`): extend the existing `kinematic_cuts`
mechanism with two new cut types, applied at the same **object level** as
the existing `pt`/`eta`/`phi` cuts (removing individual particles that fail,
not whole events — `particle_counts` still applies afterward, unchanged,
to the surviving particles). `bool_require` keeps a particle only if every
listed field is `True`; `bool_any_of` keeps it if at least one is. Accepts
a genuinely boolean field, or an integer field whose only values are 0/1;
anything else (e.g. `cutBased`'s 0–3 ordinal scale) raises a clear error
rather than silently truthy-casting a multi-valued field. Referencing a
field that isn't actually present on the collection raises immediately,
with a clear message naming the collection and field — the same
validate-before-computing style already used for `pt`/`eta`/`phi` above,
not a `KeyError` from deep inside a masking operation.

**The CMS barrel/endcap acceptance gap — use `bool_any_of`, not
`eta_exclude`.** CMS defines a photon's detector acceptance by its
**supercluster** η (`|η_SC| < 1.4442` barrel, `1.566 < |η_SC| < 2.5`
endcap), not by the momentum η NanoAOD stores as `Photon_eta` (which is
computed relative to the chosen primary vertex, and differs slightly from
the true supercluster position). NanoAOD provides this as two direct
boolean flags, verified here against a real DoubleEG file's own branch
titles and values (not assumed):

- `Photon_isScEtaEB`, doc string **"is supercluster eta within barrel
  acceptance"** — `True` for momentum `|η|` up to ≈1.451 in the sample
  checked (`Photon_isScEtaEB`/`_isScEtaEE` are themselves computed from the
  true supercluster η, so this is the expected small SC-vs-momentum-η
  difference, not evidence the flag's own boundary is wrong).
- `Photon_isScEtaEE`, doc string **"is supercluster eta within endcap
  acceptance"** — confirmed to include the `|η_SC| < 2.5` upper bound as
  part of its own definition: of 4,366 real photons checked, every one
  flagged `isScEtaEE=True` had momentum `|η| ≤ 2.516`, with only 3 (0.07%)
  slightly over the nominal 2.5 (the same small SC-vs-momentum divergence
  noted above) — not a systematic omission of the bound.
- The two flags are **never both `True`** in the sample checked (0 of
  4,366), confirming they're mutually exclusive as expected.
- Photons with **neither** flag set span momentum `|η|` from 1.428 up to
  2.933 in the sample checked — a far wider range than just the nominal
  1.4442–1.566 gap. This confirms `bool_any_of: [isScEtaEB, isScEtaEE]`
  enforces CMS's **complete** acceptance definition in one check (barrel OR
  endcap, nothing else) — it is not merely a gap-exclusion filter, it also
  excludes anything beyond the outer 2.5 edge.

**Do not use `eta_exclude` for this.** A generic `eta_exclude: {min, max}`
cut type is also added (excludes particles with momentum `|η|` inside the
given window) as a general-purpose tool, unrelated to any CMS specifics.
**It acts on momentum η, not supercluster η, and must not be used for CMS
photon acceptance** — use `bool_any_of: [isScEtaEB, isScEtaEE]` instead, per
the measurements above.

**`Photon_eCorr` — read for bookkeeping only, never applied.** Its doc
string is *"ratio of the calibrated energy/miniaod energy"* —
`Photon_pt`/`mass` are already the calibrated values (confirmed in the
design document's Check A); multiplying by `eCorr` again would
double-correct the energy. `extra_object_fields` may read it (e.g. to log
or sanity-check it), but no code in this pipeline may multiply any
momentum/energy field by it.

**Not set in any existing config file** — this section is documentation
only.

**Verified end-to-end** (`studies/hgg_cms/impl_checks/object_field_survival_check.py`):
requesting 11 extra `Photons` fields and running the real production
pipeline (file batching, cross-file chunk concatenation, event selection,
and a save-to-ROOT-and-read-back round trip) on two real DoubleEG files
from different runs — every requested field survived with the correct
dtype and values identical to a direct, independent `uproot` read, both
immediately after parsing and after the round trip.

**A related, pre-existing, NOT fixed by this work: silent per-object
field loss is possible when files disagree on which optional fields are
accessible.** Investigating the known `Muon_looseId`/`Muon_pfRelIso04_all`
drop bug (`scripts/m0m1j0_mumujet_report.py`'s `FIELD_DROP_WARNING`) found
and directly, empirically confirmed the underlying mechanism: `FileParser.
_filter_accessible_branches` (`services/parsing/file_parser.py`) decides
which fields are readable **per file**, via a single best-effort probe
read with no retry — a genuinely-present field can be wrongly excluded for
one file due to nothing more than a transient read failure during that one
probe (this project's remote reads have shown exactly this kind of
intermittent flakiness throughout tasks 2–4, including one live instance
during this task's own regression checks). Separately, and independently
confirmed with a minimal, from-scratch reproduction: `ak.concatenate`
(used both across a single file's own batches, `file_parser.py`'s
`_read_file_in_batches`, and across different files' batches merged into
one output chunk, `domain/events.py`'s `_concatenate_events`) **silently
keeps only the fields common to every array being combined, with no error
or warning**, when the same collection (e.g. `Muons`) has a different set
of sub-fields across the batches/files being merged. Together: one file
whose probe wrongly excludes an optional field, combined into the same
output chunk as another file where the field WAS read, silently loses that
field for the entire merged chunk — even for the events from the file
where it was read correctly. This was proven as a live capability of the
existing code, not merely theorized. It was **not** reproduced by this
task's own end-to-end check (`object_field_survival_check.py`'s Photon and
Muon checks both showed every requested field surviving intact) — but that
check's small scale (≤2,000 events/file, so no file was ever split into
more than one internal batch, and none of the specific files tested
happened to disagree on accessible fields) does not create the conditions
needed to trigger it either way, so a clean result there is not evidence
the hazard is gone. **Not fixed here** — out of this task's scope, and any
fix touching `_filter_accessible_branches` or `_concatenate_events` could
affect existing configs' behaviour, which needs its own explicit decision.
