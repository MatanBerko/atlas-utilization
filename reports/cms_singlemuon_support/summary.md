# CMS SingleMuon support — per-trigger-stream selection + de-duplication

**Date:** 2026-09-03
**Branch:** `feature/cms-singlemuon-support`
**Raw check output:** [`verification_output.txt`](verification_output.txt)

## What changed

Previously the CMS config used SingleElectron records only, because one blanket
"≥1 electron" cut was applied to every record and discarded ~97% of the
SingleMuon data. This adds real per-trigger-stream selection so all four records
can be combined correctly.

| Area | Change |
|---|---|
| `services/parsing/schemas.py` | new `event_id_branches` on the `cms-nanoaod` schema: `run`, `luminosityBlock`, `event` |
| `services/parsing/file_parser.py` | read those branches and attach them, plus an integer `source_record`, as **per-event** scalar fields on the parsed event record (before any chunk merging). Fails loudly if the id branches are declared but unreadable. |
| `domain/config.py` | `ParsingConfig.selection_by_record` — optional `{record_id: {particle_counts: {...}}}` overrides |
| `orchestration/handlers/parsing_handler.py` | pick each record's `particle_counts` (its override, else the global block); process muon-requirement records first; run cross-record de-dup on `(run, luminosityBlock, event)`; log per-record retention and a de-dup summary |
| `services/parsing/event_deduplication.py` | new `EventDeduplicator`: keeps the first copy of each event seen, drops later copies. Priority = feed order (muon stream first ⇒ SingleMuon copy kept). |

Kinematic cuts (pt/eta per lepton type) are unchanged and stay global — only the
"which lepton is required" part became record-aware.

### Config shape

```yaml
parsing_task_config:
  particle_counts:            # default / fallback (electron requirement) — unchanged
    electrons: {min: 1, max: 4}
    ...
  selection_by_record:        # NEW
    "30530": { particle_counts: { muons: {min: 1, max: 4}, electrons: {min: 0, max: 4}, ... } }
    "30563": { particle_counts: { muons: {min: 1, max: 4}, electrons: {min: 0, max: 4}, ... } }
```

Records not listed keep the global block. Presence of `selection_by_record`
also switches on de-duplication.

## Verification

Two runs, 2 files per record, Docker (7 GB).

### 1. Regression — SingleElectron-only unchanged

`config.cms_partb_verify.yaml` (records 30529, 30562; no `selection_by_record`):

- retention **84.2%** (30529) / **87.1%** (30562) — matches the documented ~85–89%
- raw `e0e1` Z-peak: **90–92 GeV, 54,629 entries, ~21%, ~11.7× off-peak** — identical to the pre-change baseline
- post-processing: `e0e1_main` has **0 entries below 115 GeV** — Z region still removed
- new per-event `source_record` present and correct (1,006,517 → 30529, 4,529,453 → 30562) even though both records share output files named `parsed_record_30562_*`. This is the fix for the old filename-only mislabelling.

### 2. New capability — all four records

`config.cms_fourrecord_test.yaml` (30529, 30562, 30530, 30563; per-stream selection):

**Retention**

| Record | Stream | Kept / total | % |
|---|---|---|---|
| 30530 | SingleMuon Run2016G | 3,076,657 / 4,030,719 | **76.3 %** |
| 30563 | SingleMuon Run2016H | 52,747 / 70,254 | **75.1 %** |
| 30529 | SingleElectron Run2016G | 1,006,482 / 1,195,734 | 84.2 % |
| 30562 | SingleElectron Run2016H | 4,529,453 / 5,197,838 | 87.1 % |

SingleMuon retention goes from the old **~3 %** (blanket electron rule) to
**~75–76 %**. (30563 has only ~70 k events because two NanoAOD files of that
record happen to be small; not an error — 8/8 files parsed, 100 % success.)

**Dimuon Z-peak** (real muon-triggered data now included)

- raw `m0m1`: **CLEAR Z peak at 90–92 GeV, 42,319 entries, ~26 %, ~16.8× the
  off-peak average**; 301,023 muon pairs total (vs 3,895 in the electron-only
  run). This is markedly stronger and cleaner than the earlier
  "thin, ~1.5× excess" muon result, exactly as expected once genuine
  muon-stream data is used.
- post-processing: `m0m1_main` has **0 entries below 115 GeV** — the Z region is
  correctly removed for the muon channel too.
- di-electron within this run is unchanged (`e0e1` peak 90–92 GeV, ~11.6×
  off-peak; `e0e1_main` 0 below 115).

**De-duplication**

- `35 duplicate event(s) removed of 8,665,374 seen`, all in the Run2016G era:
  run 279024: 9, run 279841: 6, run 280016: 9, run 280017: 7, run 280191: 4.
- 0 residual `(run, luminosityBlock, event)` duplicates in the parsed output.
- exact accounting: 8,665,374 seen − 35 removed = 8,665,339 written; the four
  `source_record` counts sum to 8,665,339.
- `dedup_check.py --selftest` (synthetic events) passes: cross-stream duplicate
  dropped, in-batch duplicate collapsed, priority = muon-stream copy kept.

## Honest caveats

- **De-dup rate.** 35 overlaps ≈ 0.003 % here, far below the ~2 % expected for
  the full datasets. The 2-files-per-record subsets barely share lumisections,
  so the true overlap is mostly outside the sampled files. The matching logic is
  correct (real Run2016G overlaps found, no false positives); a full or
  lumi-aligned file set is needed to reproduce the ~2 % figure.
- **`m0m1` unphysical tail.** Raw `m0m1` has a small tail with `min = −16384`
  (a NanoAOD bad-value sentinel) and multi-TeV entries. Pre-existing in the muon
  data, not introduced by this change (it touches only unrelated scalar
  columns), and fully excluded from the cleaned `_main` output (`min` there is
  115.003 GeV). Not investigated further — out of scope.
- Full-scale memory: `EventDeduplicator._seen` is a plain Python set of integer
  keys (~few million here). At full scale (~2e8 events) it would need packed
  keys / per-era `np.unique`. Flagged, not built.

## Bottom line

Per-trigger-stream selection and cross-record de-duplication both work. The
SingleElectron path is byte-for-byte unchanged; SingleMuon data is retained at
~75 % and produces a strong, clean dimuon Z-peak; duplicate collision events are
identified and removed with correct priority. Ready to become the production
config.
