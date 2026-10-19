# HANDOFF — sync with upstream #35 (19–20 Oct 2026)

**Current step (20 Oct task, started 19 Oct evening): A DONE; B SUBMITTED — per-file array `5251334[]` + build/compare `5251335` (afterok), 19 Oct 18:44, wipp-home. Master NOT yet updated (C waits for B to be fully identical).**

## 20 Oct task — make CMS compatible with #35, adopt #35 functions, prove, sync

**Branch layout.** Master and the sync branch hold no MC code; the MC driver, the MC builder and the MC tests exist only on the MC branch. So:

- `sync/upstream-35-20261019` → master gets the data-driver fix only.
- The MC changes live on a NEW branch, `sync/mc-upstream-35-20261020`. It was made from `feature/cms-mc-peakfix-20261018` (`24ecb7c`) and merged with the sync branch. It is not merged into master; `feature/cms-mc-peakfix-20261018` itself is untouched.

**A (done, all tests pass, gate empty on both branches).**

- **Data driver** (`studies/cms_datasets/cluster/run_dataset_on_file.py`, sync branch `69b10cb`): it unpacks #35's 3-value return and asserts the middle value (MC weights) is None. Only the new form is supported; a 2/3 dual form was judged not worth the complexity.
- **New test** `studies/cms_datasets/tests/test_funnel_upstream35.py`: the real funnel on a fixed synthetic sample (200 events, 186 combinations). It hashes every written value and stat to `5c43cbc0…`, the same hash the pre-#35 code (master `45a7e06`) gives. VERIFIED BY RUNNING, under hash seeds 0 and 1.
- **MC driver** (same call, now line 1789): fixed by the merge.
- **MC builder** (`studies/cms_mc_weights_v3/deliver/build_mc_delivery.py`, MC branch `6b22872`):
  - `normalisation_factor` now calls #35's `compute_normalization`, with `MCDatasetMetadata` built from σ_eff (registry), k = ε = 1 (the guard is kept) and the measured Σw.
  - `find_peak_mass` now calls #35's `_find_rightmost_highest_peak(weights=)`, returned as a float. `--peak-scope combined` is unchanged and calls it.
- **New drift test** `studies/cms_mc_weights_v3/tests/test_upstream35_drift.py`. Its expected values were produced by the builder's previous own code (`24ecb7c`) and are reproduced exactly (VERIFIED BY RUNNING):
  - normalisation over 13 records × 5 Σw;
  - peak over 400 fixed spectra (unweighted, Gaussian, ± and constant weights; float32 and float64);
  - 6 literal cases;
  - the k ≠ 1 guard.
- **Pruning drift test** `test_cms_shard_pruning_drift.py`: the reference was moved from `e1ce8bb` to #35 (`7f2da5d`, sha256 `3a0add92…`). The CMS copy still differs only in the 3 D3 code lines (plus #35's 2 comment lines); `cms_shard_pruning.py` is unchanged.
- **Tests:** CMS 5 files pass; MC 12 + 24 + 46 checks + pruning drift + the new drift test pass; upstream `tests/` 14 + 24 pass.

**B (submitted).** OLD / NEW are pinned `git archive` tarballs in `checkouts/sync35b_20261020/` (`work/sync35b_20261020/code` links to it):

| tarball | commit | sha256 prefix |
|---|---|---|
| `old_data.tar` | master `45a7e06` | `a11f0c7309022f63` |
| `new_data.tar` | sync `85c6ba8` | `4d50b28ef71e6335` |
| `old_mc.tar` | MC peak-fix `24ecb7c` | `0ebcfac06e860639` |
| `new_mc.tar` | MC sync `0e98075` | `4fe6627f10243aab` |

How the jobs run:

- Each job unpacks into node-local `$TMPDIR`, and OLD then NEW run from the same path.
- `perfile` covers DoubleMuon 30522/0, DoubleEG 30521/0, MC 67801/0 and 72752/0. Data uses the 7 Oct options (`--population matched4`); MC uses the `pbs_mc_pilot.sh` options.
- `build` runs the data four-dataset builder (`--datasets DoubleMuon,DoubleEG`) and the MC builder (defaults, `--peak-scope combined`, `--smoke-test`), then runs the unchanged `mcport_validation_20261014/compare.py` / `mc_compare.py` (data runs via `cluster/compare_data_runs.py`, which only narrows compare.py's dataset list). Results go to `work/sync35b_20261020/evidence/`.
- Script: `studies/sync_35_20261019/cluster/pbs_proof.sh`.

**Do not resubmit.** Each per-file output is skipped if it already exists.


## Branch

`sync/upstream-35-20261019` (origin only), from master `45a7e06`, merged with
`upstream/master` = `7f2da5d` (#35) as `09de053`. No conflicts; the gate is empty;
0 commits behind upstream. This branch is NOT merged into master, and must not
be until the CMS driver is adapted (Matan's decision; out of scope here).

## Part 1 result

**1a.** `upstream/master` = `7f2da5d` (19 Oct 13:18), the only commit after
`b9f6ea3`. It changes 20 files: README.md, config.yaml, domain/{config,events,metadata}.py,
orchestration/handlers/{mass_calculation,parsing}_handler.py, pipeline/executor.py,
services/calculations/{im_calculator,physics_calcs}.py, services/calculations/mc_weights.py (new),
services/metadata/fetcher.py, services/parsing/{event_selection,file_parser,schemas,threaded_processor}.py,
services/pipelines/{histograms,im,post_processing}_pipeline.py, services/storage/sqlite_shards.py.

**1b.** The merge is clean and the gate is empty.

**1c. Static check** (`static_check.py` → `evidence/static_check.json`).
It covers all CMS modules on master `45a7e06` and on the MC branch `24ecb7c`.

**BREAKING:** `services.pipelines.im_pipeline._calculate_combination_invariant_mass`
now returns 3 values `(inv_mass, mc_event_weights, skip_reason)` instead of 2.
The CMS driver unpacks two:

- `studies/cms_datasets/cluster/run_dataset_on_file.py:1451` (master);
- line 1786 on the MC branch.

So every CMS per-file job, data and MC, would stop with `ValueError` at the
first mass combination.

**1d. Runtime proof — VERIFIED BY RUNNING, locally, not on the cluster**
(`arity_probe.py`, `equiv_probe.py` → `evidence/runtime_probes_local.txt`).
The exact CMS call:

- with the old code returns 2 values, and the CMS unpacking works;
- with the new code returns 3, and the CMS unpacking fails with
  `ValueError: too many values to unpack (expected 2)`;
- gives the same mass in both.

Every other #35-changed function the CMS code uses gives identical outputs on
fixed random inputs (same hash, old vs new):

- the Z-peak cut, peak finding and outlier split;
- `count_particles`;
- the mass calculation and the exact-count filter;
- `group_by_final_state` (not called by CMS).

The only difference is the dtype of empty arrays, which are never written.

The cluster jobs were **not submitted**. The new driver cannot finish a single
file, so OLD vs NEW shards cannot be compared. Per the brief ("If ANYTHING
differs: STOP, do not touch master"), master was not touched.

## What would unblock the sync (Matan / technical lead to decide; not done here)

A CMS-side adaptation, not an upstream edit. In `studies/cms_datasets/cluster/run_dataset_on_file.py`,
accept both return shapes, e.g. `res = _calculate_combination_invariant_mass(...)`,
`inv_mass, skip_reason = res[0], res[-1]`, at both call sites. The CMS
`im_config` has no `mc_weighting_enabled`, so the new middle value is
always `None` for CMS. Then repeat 1d (cluster) before merging into master.

## Part 2

`MC_CONVENTIONS_35_vs_CMS.md`: 12-row comparison, row 7 in detail, reuse table, recommendations. Local probes (VERIFIED BY RUNNING) in `evidence/part2_probes_local.txt`:

- `norm_probe.py`: #35 `compute_normalization` vs the CMS normalisation, 13,000 / 13,000 bit-identical.
- CMS `test_cms_shard_pruning_drift.py`: passes on `24ecb7c`; 2 of 4 checks fail on `24ecb7c` + #35, as designed.

## Cluster

Not used for jobs: no checkouts, no outputs, no submissions, so there is nothing to archive. `checkouts/sync35_20261019/` and `work/sync35_20261019/` were never created. File count 120,539 (19 Oct, unchanged; 0 new). `qstat -u berkom` empty.

## Resume

Both parts are finished. Do not update master until the CMS driver is adapted and 1d is repeated on the cluster.
