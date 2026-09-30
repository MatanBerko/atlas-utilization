# Phase-1 MC weights: implementation report

Branch `feature/cms-mc-weights-phase1`, off `origin/design/cms-mc-weights`
at `3930d88`. Implements DESIGN.md for exactly the 3 phase-1 samples
(42407 LQToBMu_M-400_pair, 67801 TTTo2L2Nu, 35671 DYJetsToLL_M-50
madgraphMLM), with the technical lead's binding amendments A1-A5.

---

## Trigger paths used

The DoubleMuon data production's own two HLT paths
(`studies/m0m1j0_cms/selection.py:66-69`, `TRIGGER_BRANCHES`, the V0
baseline default), imported and used **unchanged** by the new MC driver:

- `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ`
- `HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ`

Confirmed present in every one of the 3 samples' NanoAODSIM files checked
so far (both branches, every file's own `job_metadata.json
["trigger_branches_present_in_file"]`): 12/12 LQToBMu, [N]/49 TTTo2L2Nu,
[N]/61 DYJetsToLL files at report time — see the per-sample tables below
for the final count. `read_events_mc()`'s required-branch check
(`run_m0m1j0_on_mc_file_v2.py:203-210`) would have failed the job loudly,
not silently, had either been absent in any file.

## A1: shared selection, confirmed

The MC driver imports and calls `studies.m0m1j0_cms.selection
.select_event_selection_cutflow` exactly as the data driver does
(same function, same default trigger branches) — **not** a copy. No
golden-JSON filter is applied (asserted at runtime,
`run_m0m1j0_on_mc_file_v2.py:397-405`: the event count entering selection
is asserted equal to the raw read count). genWeight and
L1PreFiringWeight_Nom are required, read alongside every data-required
branch, and carried through the same event-level boolean-mask operations
`sel_events` already goes through.

The general multi-combination invariant-mass machinery (needed because
the phase-1 validation histograms are not all the single "m0m1j0"
combination) is the SAME code the actual DoubleMuon data coverage driver
used (`origin/deliver/doublemuon-bumpnet
:studies/cms_coverage/cluster/run_coverage_on_file.py`, read via `git
show`, never checked out): `get_all_combinations`, `IMCalculator`,
`physics_calcs.group_by_final_state`/`is_finalstate_contain_combination`,
`im_pipeline.prepare_im_combination_name`. One necessary adaptation is
documented in full in `run_m0m1j0_on_mc_file_v2.py`'s own module
docstring: `IMCalculator.filter_by_particle_counts(...,
is_exact_count=True)` rebuilds its output keeping only the combination's
own object-type fields, silently dropping any attached weight field — so
the MC driver keeps genWeight/L1PreFiringWeight_Nom as separate,
index-aligned numpy arrays instead, re-sliced using independently
recomputed (not re-derived-differently — literally the same formula,
same `get_start`/`get_count` helpers) copies of the masks the shared
functions compute internally, with a **runtime cross-check** at every
combination confirming the recomputed mask's population matches the
shared function's own `is_exact_count=False` output exactly (an
`AssertionError` would stop the job if they ever diverged — this never
fired across every file processed).

## A2: MC inherits data's histogram definitions

MC runs no z-peak/max-mass/peak-removal/first-empty-bin-split logic of
its own. For every produced signature matching a name in the delivered
manifest (`studies/cms_mc_weights/evidence/deliver_manifest_min26bins.json.gz`,
340 entries, `git show`n from `origin/deliver/doublemuon-bumpnet`, never
checked out), the exact recorded outcome of data's own post-processing —
that histogram's `first_filled_bin_low_edge_gev`/
`last_filled_bin_high_edge_gev` — is used as the mass window MC events
are cropped to before filling, on the identical underlying fixed grid
(0-10,000 GeV, 10 GeV bins).

### Skipped/unreproducible histograms

<!-- FILLED IN FROM merge_mc_summary.json's skipped_unreproducible per sample -->

### MC-only categories (not written this run)

<!-- FILLED IN: counts per sample, from merge_mc_summary.json -->

### Raw-count flags (< 100 raw entries in the data-derived window)

<!-- FILLED IN per sample -->

## A3: normalisation JSON + registry, no PR#23 code imported

`studies/cms_mc_weights/cms_mc_normalisation.json` (built by
`build_normalisation_json.py` from `normalisation_table_v2.csv`) and the
registry logic (`build_weights_registry.py`, PR#23's
`{"default_weight","weights"}` schema, independently reimplemented — no
`services/calculations/weights_registry.py` import). `gen_filt_eff` and
`k_factor` are both fixed at 1.0 for every record (R1: portal `sigma_eff`
already includes matching/filter; k_factor already folded into
`cross_section_pb`). An unknown record ID raises `KeyError`
(`CMSWeightsRegistry.weight_for`) — never falls back to `default_weight`
silently.

## A4: default-preserving proof

`prove_default_preserving.py`, run on the cluster:
- **Synthetic check**: PASS (bit-identical bin contents, old vs new
  function, edge-case values including NaN and the exact 10000.0 GeV
  boundary).
- **Real data check**: PASS on **29 real categories** from an actual
  DoubleMuon data job's own `mass_by_category.npz`
  (`/storage/agrp/berkom/atlas-utilization/output/m0m1j0_full_v2/job_5/mass_by_category.npz`
  — already on the cluster, never reprocessed/re-selected here) —
  bit-identical bin contents for every one.
- **OVERALL_PASS: true.** Full result committed:
  `studies/cms_mc_weights/phase1/prove_default_preserving_result.json`.

`run_m0m1j0_on_file.py` and `merge_full_v2.py` (the data driver/merge)
were not modified or re-run — this is a proof about the shared function
they call, not a re-execution of the data pipeline.

## A5: Sigma genWeight denominator

Computed via fork master's own, **unmodified**
`aggregate_sumw_for_processed_files()` (`services/parsing/mc_weights.py
:173-226`), called from `merge_full_v2_mc.py` with an **injected reader**
that returns each file's already-read Runs-tree sums from its own
`job_metadata.json` (avoiding a second network read per file — the sums
themselves come from `read_runs_tree_sums()`, also unmodified, called
once per file at per-job time). Any file whose job directory or
`job_metadata.json` is missing is a hard failure surfaced by
`aggregate_sumw_for_processed_files`'s own `RuntimeError` (listing every
such failure together) — never silently absorbed.

---

## Per-sample production summary

| Sample | Record ID | Files | Files processed | Trigger branches present | Mean job walltime | Max job walltime |
|---|---:|---:|---:|---|---:|---:|
| LQToBMu_M-400_pair | 42407 | 12 | <!--N--> | <!--Y/N--> | <!--s--> | <!--s--> |
| TTTo2L2Nu | 67801 | 49 | <!--N--> | <!--Y/N--> | <!--s--> | <!--s--> |
| DYJetsToLL_M-50 madgraphMLM | 35671 | 61 | <!--N--> | <!--Y/N--> | <!--s--> | <!--s--> |

**Test-run checkpoint (LQ, the task's own explicit first checkpoint)**:
12/12 files processed successfully, mean walltime 101s, max 159s —
comfortably within the 30-minute PBS budget; proceeded to the other two
samples on this basis.

---

## V1 -- Arithmetic closure

<!-- FILLED IN per sample from validate_v1_v2_result.json -->

## V2 -- Per-file Sigma genWeight vs Runs genEventSumw

<!-- FILLED IN: max relative difference per sample, all-pass flag -->

## V3 -- Data vs MC

**Expectation, stated in advance (task's own):**
- DY-dominated region: agreement within roughly 5-10%, given the
  luminosity uncertainty (1.2%), the DY cross-section spread (~5%, R1/R2
  from `INVESTIGATION.md`), no muon/trigger scale factors, no pileup
  reweighting.
- b-jet regions: looser agreement expected, because there are no b-tag
  scale factors, missing samples (tW, dibosons, low-mass DY) contribute a
  few % each, and jet-containing mass peaks come out narrower in MC
  without jet-energy-resolution smearing (`DESIGN.md` Sec 7).

<!-- FILLED IN: observed ratios vs expectation, 3 plots -->

## V4 -- Leptoquark overlay

Category chosen: `mass_m0m1b0b1_cat_0ex_2mx_1jx_0gx_0tx_2bx` (2 muons + 1
light jet + 2 b-jets) — the best available match to the leptoquark pair's
own b+mu, b+mu topology (both selected muons AND both selected b-jets
used in the same invariant mass), and the largest-event-count 2-b-jet bin
for the m0m1b0b1 combination in the delivered manifest (5,623 data
events). No interpretation.

<!-- FILLED IN: plot + numbers -->

---

## Deliverables

<!-- FILLED IN: file sizes / commit status per ROOT file -->

## Anything not verified

<!-- FILLED IN -->

## Next step

<!-- FILLED IN -->
