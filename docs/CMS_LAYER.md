# The CMS layer on top of upstream

This branch is **upstream master `e1ce8bb` plus added files only**. Every file
that exists in upstream `e1ce8bb` is byte-identical to upstream; nothing in it
was edited, moved or deleted. Everything CMS-specific lives in the files
listed below, all copied byte-for-byte from the fork's old master `ba89791`
(archived as `archive/master-2026-10-14`), except the four documentation
files, which are new.

Check it yourself:

```bash
git diff --name-status upstream/master HEAD     # every line starts with "A"
```

"Delivery" below means the four-dataset BumpNet delivery of 7 Oct 2026
(`four_dataset_matched_vB_upstreamnames_w10p0_dr012_bumpnet_cropped.root`,
1,975 histograms, 103 final states; see
`studies/cms_datasets/electron_vB/DELIVERY_NOTES.md`).

## Added files

### Shared CMS modules and data

| file | what it is | why CMS needs it | generic / upstreamable? | used by delivery |
|---|---|---|---|---|
| `services/parsing/validated_runs.py` | Filters events to the certified-luminosity ("golden JSON") run/lumi-section list | CMS data must be restricted to certified lumi sections; ATLAS Open Data is pre-filtered | Yes — experiment-agnostic (any run/lumi JSON); only stdlib, numpy, awkward | Yes (`run_dataset_on_file.py`) |
| `services/parsing/trigger_requirements.py` | Applies an "any of these HLT bits" trigger requirement to events | CMS primary datasets overlap and each needs its own trigger decision | Yes — generic boolean-branch OR; only stdlib, numpy, awkward | Yes (`run_dataset_on_file.py`) |
| `data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt` | The official 2016 Legacy certified-run list | Read by `validated_runs.py` at its default path | Data file, CMS-specific | Yes |
| `data/cms/validated_runs/README.md` | Where the JSON came from | Provenance | — | Documentation |

### The delivery program (`studies/cms_datasets/`)

| file | what it is | used by delivery |
|---|---|---|
| `cluster/run_dataset_on_file.py` | Per-file production driver: reads one NanoAOD file, applies certified runs, trigger + trigger matching, object selection, e–μ overlap removal (dR < 0.12), de-duplication flags, and writes the invariant-mass shards + `job_metadata.json` | Yes — Step C (`--population matched4`) |
| `cluster/datasets_records.py` | The four datasets, their CERN Open Data record IDs, triggers and veto order | Yes |
| `electron_vB/cluster/pbs_matched4.sh` | PBS array launcher for the per-file driver | Yes — Step C |
| `electron_vB/gen_full_mapping.py` | Builds the 390-file mapping and `<Dataset>_index.json` files | Yes — Step C input |
| `electron_prep/__init__.py`, `electron_prep/common.py` | `record_for()` (dataset+era → record ID), used by `gen_full_mapping.py` | Yes (helper) |
| `electron_vB/__init__.py` | Package marker | Yes (import) |
| `electron_vB/check_production_complete.py` | Step C3 completeness/consistency check over all 390 job directories | Yes — Step C3 |
| `deliver/build_four_dataset_delivery.py` | The delivery builder (`--version rare4`, no extra flags) | Yes — Step D1 |
| `deliver/build_dataset_delivery.py`, `deliver/build_muon_combined_delivery.py` | Helper functions the four-dataset builder imports (naming, ROOT writing, manifests) | Yes (imported) |
| `electron_vB/cluster/pbs_delivery.sh` | PBS launcher for the delivery build | Yes — Step D1 |
| `electron_vB/verify_delivery.py` | Step D2/D3 read-back checks of the delivered ROOT file | Yes — Step D2/D3 |
| `electron_vB/make_delivery_plots.py` | Step D4 delivery plots | Yes — Step D4 |
| `electron_vB/HANDOFF.md`, `DELIVERY_NOTES.md`, `REPORT_production.md` | Documentation of the 7 Oct production and delivery | Documentation |
| `electron_vB/evidence/C3_production.json`, `D2_D3_delivery_checks.json`, `delivery_README.txt` | Small production/delivery check records (≤ 24 KB each) | Documentation |
| `electron_vB/evidence/pilot_final_states.json` | Pilot final-state list read by `tests/test_electron_datasets.py --pilot-final-states` | Test input |

None of these is meant to be upstreamed as-is: they are a self-contained CMS
study program. Parts that could become generic (e.g. the trigger-object
matching helpers) would need a separate design discussion.

### Study modules the delivery imports (kept although their studies are archived)

The delivery program imports five modules that live in older study folders.
They are kept, unchanged, because the delivery cannot run without them;
the **rest** of those study folders is archived.

| file | what the delivery uses from it |
|---|---|
| `studies/m0m1j0_cms/selection.py` | CMS object selection (`build_object_record` etc.), `MIN_EVENTS_PER_FINAL_STATE` |
| `studies/m0m1j0_cms/histograms.py` | Fixed 10 GeV grid, BumpNet naming, TH1F writing/verification |
| `studies/m0m1j0_cms/design_checks/common.py` | `fetch_file_list()` — file URLs of a CERN Open Data record |
| `studies/cms_coverage/cluster/merge_and_count.py` | `copy_shards`, `run_funnel_at_threshold`, the ≥100-events rule constants |
| `studies/cms_coverage/deliver/crop_bumpnet_root.py` | `crop_arrays` — the cropped BumpNet output |

### Tests

| file | notes |
|---|---|
| `tests/test_validated_runs.py` | Byte-identical copy. 3 of its tests exercise the fork's old `ParsingConfig.validated_runs_json` field (a fork edit to upstream `domain/config.py`, not carried over) and error on this branch; the rest pass. |
| `tests/test_trigger_requirements.py` | Byte-identical copy. Its module imports `RequiredScalarBranchMissingError` from `services/parsing/file_parser.py`, which exists only in the fork's edited `file_parser.py`, so the file does not import on this branch. |
| `studies/cms_datasets/tests/test_*.py` (4 files) | Run as scripts (`python studies/cms_datasets/tests/<name>.py`). Output identical to `ba89791` (14 Oct 2026): `test_width_suffix` and `test_upstream_names` pass; `test_exact_jet_labels` 70 pass / 14 fail and `test_electron_datasets` 108 / 109 (one "NOTED" check). All 15 failures are checks that pin the old one-digit label reading in the shared functions, which upstream PR #34 fixed (already in `ba89791` as `2734dd3`). They are test expectations, not delivery behaviour. |

### New documentation

`docs/CMS_LAYER.md` (this file), `docs/BRANCH_LAYOUT.md`,
`docs/CMS_KNOWN_LIMITATIONS.md` (carried over, predates the rebuild) and
`studies/cms_datasets/README_REBUILD.md`. Upstream `e1ce8bb` has no `docs/`
folder, so none of these shadows an upstream file.

## Paths in kept files that point at archived files

No kept code was edited. These references to archive-only paths are known and
are **not** on the delivery path:

- `studies/cms_coverage/cluster/merge_and_count.py`, inside `main()`, reads
  `studies/m0m1j0_cms/v2/data/merge_v2_summary.json` (archived). The delivery
  only imports helper functions from this file and never runs `main()`.
- The documentation files (`HANDOFF.md`, `REPORT_production.md`,
  `DELIVERY_NOTES.md`) mention scripts and evidence files that stay in the
  archive (Step B gate scripts, pilot comparisons, plots). They are records
  of what was done, not instructions that must run on this branch.
- `studies/cms_datasets/tests/test_electron_datasets.py` reads
  `services/pipelines/histograms_pipeline.py` (upstream file, present) and
  compares against `upstream/master` via `git archive`; it needs the
  `upstream` remote to be fetched.

## What was intentionally NOT carried over

All of this stays in `archive/master-2026-10-14` (= `ba89791`).

**The fork's edits inside upstream files** — the older "CMS through the main
pipeline" route. Not carried, because upstream files are never modified:

`.gitignore`, `config.yaml`, `config.cms_records_master.yaml`,
`config.cms_singleelectronsinglemuon.yaml`, `config.short_parse_btag.yaml`,
`config.short_parse_local.yaml`, `submit_mc.sh`, `domain/config.py`,
`domain/events.py`, `domain/statistics.py`,
`orchestration/handlers/{fetch_metadata,mass_calculation,parsing}_handler.py`,
`pipeline/executor.py`, `services/calculations/{consts,im_calculator,physics_calcs}.py`,
`services/metadata/fetcher.py`, `services/parsing/{event_selection,file_parser,root_io,schemas,threaded_processor}.py`,
`services/pipelines/{histograms_pipeline,im_pipeline}.py`. These carried
units handling (MeV/GeV), NanoAOD schema entries, extra fields and boolean
cuts, de-duplication wiring, MC weight reading and similar.

The delivery calls none of the functions that differ between those fork
versions and upstream (checked function by function; see the rebuild
validation branch `validate/rebuild-2026-10-14`).

**Fork-only shared modules not needed by the delivery:**
`services/parsing/mc_weights.py`, `services/parsing/event_deduplication.py`.

**Archived studies:** `studies/cms_coverage/` (except the two modules above),
`studies/hgg_cms/`, `studies/m0m1j0_cms/` (except the three modules above),
`reports/`, `logs/`, `scripts/` (fork additions), the one-off
`config.cms_*.yaml` files the fork added (upstream's own
`config.cms_records_master.yaml` and `config.cms_singleelectronsinglemuon.yaml`
are present in upstream's form), `config.atlas_scale_test.yaml` /
`configWmaxTotal_up4j_minEvt100_subleading.yaml` files,
`pbs_m0m1j0_fullscale.sh`, `pbs_m0m1j0_smoketest.sh`, and the fork's other
`tests/` files (they test fork edits to upstream files).

**From `studies/cms_datasets/` itself:** delivered and intermediate ROOT
files, PNG plots, large JSON evidence, the superseded per-dataset and
muon-only deliveries (`deliver/committed/`), the older production/preflight
scripts (`cluster/gen_*_mapping.py`, `merge_*.py`, `pbs_run_*.sh`,
`trigger_preflight_*`, `compare_regression.py`, `fetch_record_file_lists.py`),
the older delivery helpers (`deliver/aggregate_cutflow_and_resonances.py`,
`compute_manifest_breakdown.py`, `make_delivery_check_plots.py`,
`verify_with_real_root.py`, `compare_pilot_reproducibility.py`), the
`matching/` studies, `electron_prep/` except `common.py`, the electron_vB
Step A/B/E study scripts and evidence (closure, band check, radius change,
pilot comparisons), `electron_vB/REPORT.md` (the 6 Oct measurement report)
and `PREFLIGHT_REPORT.md`.

**Main-pipeline CMS runs no longer apply on this master.** `config.mac.yaml`
(local, never committed) and `config.cms_records_master.yaml` main-pipeline
runs relied on the fork's edits to upstream files; on this master `main.py`
is upstream's own, without CMS support. Use the archive branch for those.
