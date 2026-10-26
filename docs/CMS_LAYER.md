# The CMS layer on top of upstream (lean branch)

This branch, `lean/cms-layer-20261023`, is **upstream master `29291ae` plus added files only**:
the minimal CMS layer needed to run the CMS production and build the deliveries. Every file
that exists upstream is byte-identical to upstream; nothing upstream was edited, moved or
deleted. Every added file is byte-identical to the same path on
`feature/cms-mc-multiplicity40-20261023` @ `de012d2`, except this document.

Check it yourself:

```bash
git diff --name-status upstream/master HEAD      # every line starts with "A"
git diff de012d2 HEAD -- $(git diff --name-only upstream/master HEAD) ':!docs/CMS_LAYER.md'   # empty
```

24 Oct 2026, Maryna: loose muon and electron IDs; muon iso < 0.15 kept

The folder names are historical (`m0m1j0_cms`, `cms_coverage`, `electron_vB`,
`cms_mc_weights_v3`) and were kept, so that nothing had to be moved or edited.

## A. Run code, inputs and launchers

Shared modules and data:
- `services/parsing/validated_runs.py`: keeps only events in certified ("golden JSON") run/lumi sections.
- `services/parsing/trigger_requirements.py`: an "any of these HLT bits fired" trigger requirement.
- `data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt`: the official 2016 certified-run list, read by `validated_runs.py`.
- `data/cms/validated_runs/README.md`: where that list came from.

Per-file production (data and MC):
- `studies/cms_datasets/cluster/run_dataset_on_file.py`: the per-file driver. It reads one NanoAOD file and applies certified runs, triggers and trigger matching, object selection, e–μ overlap removal, de-duplication and the rare4 rule. It writes the mass shards and `job_metadata.json` (`--is-mc` for MC).
- `studies/cms_datasets/cluster/datasets_records.py`: the datasets, their record IDs, triggers and priority order.
- `studies/m0m1j0_cms/selection.py`: CMS object selection (electrons, muons, jets, b-tag).
- `studies/m0m1j0_cms/histograms.py`: the fixed 10 GeV grid, BumpNet naming, ROOT writing and checks.
- `studies/m0m1j0_cms/design_checks/common.py`: `fetch_file_list()`, the file URLs of a CERN Open Data record.
- `studies/cms_datasets/electron_vB/gen_full_mapping.py`: writes the data file mapping and the `<Dataset>_index.json` files.
- `studies/cms_datasets/electron_prep/__init__.py`: package marker.
- `studies/cms_datasets/electron_prep/common.py`: `record_for()` (dataset + era → record ID), imported by `gen_full_mapping.py`. *(Added beyond the original list: needed by an import.)*
- `studies/cms_datasets/electron_vB/__init__.py`: package marker.
- `studies/cms_datasets/electron_vB/cluster/pbs_matched4.sh`: PBS array launcher for the data per-file driver.
- `studies/cms_datasets/electron_vB/check_production_complete.py`: completeness check over every data job directory.
- `studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh`: PBS launcher for the MC per-file driver.
- `studies/cms_mc_weights_v3/fullrun_prep/make_fullrun_mappings.py`: writes the MC full-run mappings.
- `studies/cms_mc_weights_v3/evidence/fullrun_inputs_20261017.json`: the MC input-file sweep that `make_fullrun_mappings.py` reads. *(Added beyond the original list: a program input.)*
- `studies/cms_mc_weights_v3/fullrun_prep/check_input_files.py`: checks that the MC input files are readable (it produces such a sweep).
- `studies/cms_mc_weights_v3/fullrun/pbs_fullrun.sh`: PBS launcher for the MC full run.
- `studies/cms_mc_weights_v3/fullrun/audit_production.py`: audit of the MC full-run job directories.

Delivery builders:
- `studies/cms_datasets/common/multiplicity.py`: the upstream #40 max-4-objects rule applied at build time (calls upstream's functions), shared by both builders.
- `studies/cms_datasets/deliver/build_four_dataset_delivery.py`: the data delivery builder. Five datasets, matched5, `--multiplicity-rule upstream40` by default.
- `studies/cms_datasets/deliver/build_dataset_delivery.py`: helpers the data builder imports (naming, ROOT writing, manifests).
- `studies/cms_datasets/deliver/build_muon_combined_delivery.py`: more helpers the data builder imports.
- `studies/cms_coverage/cluster/merge_and_count.py`: `copy_shards`, the shared post-processing funnel and the ≥100-events rule.
- `studies/cms_coverage/deliver/crop_bumpnet_root.py`: crops histograms to their filled range (the BumpNet file).
- `studies/cms_datasets/electron_vB/cluster/pbs_delivery.sh`: PBS launcher for the data delivery build. It passes no flags, so it uses the #40 rule.
- `studies/cms_datasets/electron_vB/verify_delivery.py`: read-back checks of a delivered ROOT file.
- `studies/cms_datasets/electron_vB/make_delivery_plots.py`: delivery plots.
- `studies/cms_datasets/electron_vB/evidence/delivery_README.txt`: the README shipped with a delivery.
- `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py`: the MC builder. Weights, the #40 rule by default, the ≥100 rule, peak/outlier cuts, TH1D + Sumw2.
- `studies/cms_mc_weights_v3/deliver/cms_shard_pruning.py`: upstream's ≥100-events pruning plus removal of the MC sibling rows.
- `studies/cms_mc_weights_v3/deliver/weighted_histograms.py`: weighted fixed-grid histograms and the negative-bin inventory.
- `studies/cms_mc_weights_v3/fullrun/sanity_and_plots.py`: sanity checks and plots of an MC build.

MC normalisation:
- `studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json`: the MC registry (cross sections, records, Σw rules) that the builder reads.
- `studies/cms_mc_weights_v3/build_registry.py`: regenerates and `--check`s that registry from `sources/`.
- `studies/cms_mc_weights_v3/evidence/probe_mc_records.json`: portal dataset titles that `build_registry.py` reads. *(Added beyond the original list: a program input.)*

## B. Tests

- `tests/test_trigger_requirements.py`, `tests/test_validated_runs.py`: the shared modules above.
- `studies/cms_datasets/tests/`: b-tag/SingleElectron, electron datasets, exact jet labels, #35 funnel, the #40 rule, upstream names, width suffix.
- `studies/cms_mc_weights_v3/tests/`: MC builder end to end, shard pruning drift, the SingleElectron flag, weights, peak scope, #35 drift.

Run each as a script from the repo root: `PYTHONPATH=. python <test file>`.
`test_electron_datasets.py` compares against `upstream/master`, so the `upstream` remote must be fetched.
Some tests write a small result JSON into an `evidence/` folder. That output is not part of the branch.

## C. Documentation and provenance

- `docs/CMS_LAYER.md`: this file.
- `docs/CMS_KNOWN_LIMITATIONS.md`: known CMS limitations.
- `docs/BRANCH_LAYOUT.md`: the fork's branch layout (written for an earlier master).
- `studies/cms_datasets/README_REBUILD.md`: how to run the data production and delivery.
- `studies/cms_mc_weights_v3/XSEC_DECISIONS.md`: the cross-section decisions behind the registry.
- `studies/cms_mc_weights_v3/DESIGN.md`: the MC weighting design (D1–D8).
- `studies/cms_mc_weights_v3/sources/`: the inputs of `build_registry.py`: `README.md`, `v2_cms_mc_normalisation.json`, `v2_normalisation_table_v2.csv`, `v4_decisions_2026-10-15.json`.

## Known references to files not on this branch (not on the run path)

- `studies/cms_coverage/cluster/merge_and_count.py`, inside its own `main()` self-check, reads
  `studies/m0m1j0_cms/v2/data/merge_v2_summary.json`, a past-study record. The builders only
  import functions from this file and never run its `main()`.
- Comments and docstrings in the code mention study scripts, reports and evidence (for
  example `electron_vB/REPORT.md`, `cms_ttbar_pr40_20261021/REPORT.md`). These are references
  for readers, not files the code opens.
- `test_electron_datasets.py --pilot-final-states <json>` is an optional argument. The pilot
  file is a record and is not here; the test runs without it.

## Where the records live

The study records (reports, handoffs, evidence, plots, past checks) were not copied here. They
stay, unchanged, on the existing branches:
- `feature/cms-mc-multiplicity40-20261023` (@ `de012d2`): everything up to 23 Oct 2026,
  including `studies/multiplicity40_20261023/`, `studies/sync_42_20261023/`, `studies/btag_se_20261020/`,
  the electron_vB production and delivery records, and the MC weights v3 studies;
- `feature/cms-btag-singleelectron-20261020`, `feature/cms-mc-btag-singleelectron-20261020`,
  `master`: the same history up to the 23 Oct sync;
- `study/cms-ttbar-pr40-20261021`: the ttbar test of #40;
- `archive/master-2026-10-14`: the fork's old master, including the older CMS-through-main-pipeline route;
- `study/lean-branch-proof-20261023`: the proof that this branch gives the same outputs as `de012d2`.
