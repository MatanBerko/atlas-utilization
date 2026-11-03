# HANDOFF — MC expansion, task A1 (3 Nov 2026)

Branch `feature/mc-expansion-20261103` (fork only), made from `origin/master` = `3054df3`. A1 builds and checks
the v4 registry, runs a small real-file check and prepares the full production. **It submits no full production,
builds no delivery and sends nothing.** The technical lead verifies A1 before the A2 prompt submits anything.

## Step 0 — preflight (VERIFIED BY RUNNING)

- `origin/master` = `3054df3`, `upstream/master` = `29291ae`, `origin/plan/mc-expansion-20261026` = `25d6423`
  (all as expected).
- `ssh wipp-campus`: "No route to host" (one try); `wipp-home` works.
- File count (`lfs quota -u berkom /storage`, column 6): **95,324**.
- `checkouts/mcexp_20261103` and `work/mcexp_20261103` did not exist.
- Between the 25 Oct production pin `75b399e` and `3054df3` only files under `studies/fullrun_20261025/` were
  added (`git diff --name-only`): the production code of master is the code of the 25-26 Oct full run.

## Step 1 — registry v4 (VERIFIED BY RUNNING)

- `studies/cms_mc_weights_v3/sources/v5_decisions_2026-11-03.json` (written by
  `studies/mc_expansion_20261103/make_v5_decisions.py`): Matan's final values for 58 records
  (54 in the full run, 4 ON HOLD). Each record has:
  - NanoAOD and MiniAOD IDs, the construction, every factor with its source (link + table/row) and verification
    status, the tier, `in_full_run`, and the `estimate` flag;
  - the excluded records (E2, D1, D4, D13);
  - 75567 moved out of v3's excluded list (D14).
- `studies/cms_mc_weights_v3/build_registry_v4.py` (ADDED; `build_registry.py` untouched) →
  `cms_mc_normalisation_v4.json`:
  - **73 records**: the 15 v3 records copied unchanged (13 in the full run + 35671 and 42407, not in it) + 58 new;
  - **67 in the full run**; 6 not; 24 deliberately excluded;
  - k_factor = gen_filt_eff = 1.0 everywhere; `--check` reproduces it byte for byte.
- Provenance: the saved portal records (59 NanoAOD + 59 MiniAOD, incl. 35671/35670) and the generator cards of the
  58 samples are **copied** byte for byte from the plan branch commit `25d6423` into
  `studies/cms_mc_weights_v3/sources/mcexp_20261103/{records,cards}/` (3.5 MB).
- v3: `build_registry.py --check` still OK; `cms_mc_normalisation_v3.json` and `v4_decisions_2026-10-15.json` unchanged.

## Step 2 — automatic checks (VERIFIED BY RUNNING)

Tests: `studies/cms_mc_weights_v3/tests/test_registry_v4.py` (6/6 pass). Report: `REGISTRY_CHECKS.md`
(+ `evidence/registry_v4_checks.json`), from `registry_v4_report.py`.

- (a) every σ_eff equals Matan's list exactly, and equals the product of its factors to ≤ 4.2e-5 (limit 1e-4).
- (b) 25 portal values (generator factors, the three W values, the LO DY 5396 of MiniAOD 35670): **saved copy equal
  25/25, live API equal 25/25** (read 3 Nov). Matan's own live check of the three W values is still recorded as pending.
- (c) τ check: 12 samples × card evidence × factor, **12/12 OK, no mismatch**. Also 67841 TTToHadronic:
  `topdecaymode 00022` ↔ BR(W → had)².
- (d) no record twice; full run = 13 delivered + 54 new. Overlap checks:
  - W+jets pieces only;
  - tt̄ split sums to 1.0026;
  - tribosons ext1 only;
  - qq → ZH uses 0.7612 and gg → ZH 0.1227;
  - dropped and deferred records are excluded.
- (e) all 17 CMS test files (`tests/`, `studies/cms_datasets/tests/`, `studies/cms_mc_weights_v3/tests/`) exit 0
  (`evidence/cms_tests_step2.log`). Three of the old tests write by-product files into the tree; they were moved
  out, not committed.

## Code changes (CMS files only; v3 stays the default)

- `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py`:
  - optional `--registry PATH` (default: the v3 registry, unchanged);
  - optional `--extra-runs-dir DIR` (repeatable, read only; a record found in two directories is a hard error);
    this lets one build read the 25 Oct production next to the new one;
  - `assert_in_full_run` also reads the reason from `decision_2026_11_03`;
  - the report records `registry` and `extra_runs_dirs`.

  Lines: 201-203, 642-651, 660-661, 1081-1092 (see `git diff 3054df3 -- …`).
- `studies/cms_mc_weights_v3/fullrun/pbs_fullrun.sh`: optional env `REGISTRY`, `EXTRA_RUNS_DIR` passed to the build
  stage only when set (lines 23-25, 57-58). Unset = exactly the 25 Oct command.
