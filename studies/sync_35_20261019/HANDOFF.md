# HANDOFF — sync with upstream #35 (19–20 Oct 2026)

**Current step: PART 1 STOPPED at 1c/1d — #35 breaks the CMS per-file driver;
fork master NOT updated (still `45a7e06`). Part 2 (read-only convention
comparison) in progress.**

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

## Cluster

Not used: no checkouts, no outputs, no jobs. File count unchanged (~120,539).

## Resume

If this file is on origin: Part 1 is finished (STOPPED); do not update master.
Continue with Part 2 if `MC_CONVENTIONS_35_vs_CMS.md` is missing.
