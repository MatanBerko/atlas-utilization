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
