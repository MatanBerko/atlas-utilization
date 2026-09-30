# Phase-1 MC weights: implementation report

Branch `feature/cms-mc-weights-phase1`, off `origin/design/cms-mc-weights`
at `3930d88`. Implements DESIGN.md for exactly the 3 phase-1 samples
(42407 LQToBMu_M-400_pair, 67801 TTTo2L2Nu, 35671 DYJetsToLL_M-50
madgraphMLM), with the technical lead's binding amendments A1-A5. All 3
samples' full file sets were processed (12 + 49 + 61 = 122 files, 0
missing), merged, and validated end to end.

---

## Trigger paths used

The DoubleMuon data production's own two HLT paths
(`studies/m0m1j0_cms/selection.py:66-69`, `TRIGGER_BRANCHES`, the V0
baseline default), imported and used **unchanged** by the new MC driver:

- `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ`
- `HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ`

Confirmed present in **all 122 files across all 3 samples** (every file's
own `job_metadata.json["trigger_branches_present_in_file"]`, both
branches, no exception): 12/12 LQToBMu, 49/49 TTTo2L2Nu, 61/61
DYJetsToLL. `read_events_mc()`'s required-branch check
(`run_m0m1j0_on_mc_file_v2.py:203-210`) would have failed the job loudly,
not silently, had either been absent in any file — it never fired.

## A1: shared selection, confirmed

The MC driver imports and calls `studies.m0m1j0_cms.selection
.select_event_selection_cutflow` exactly as the data driver does — **not**
a copy. No golden-JSON filter is applied (asserted at runtime,
`run_m0m1j0_on_mc_file_v2.py:397-405`: the event count entering selection
is asserted equal to the raw read count — this assertion never failed
across 122 files). genWeight and L1PreFiringWeight_Nom are required, read
alongside every data-required branch, and carried through the same
event-level boolean-mask operations `sel_events` already goes through.

The general multi-combination invariant-mass machinery (needed because
the phase-1 validation histograms are not all the single "m0m1j0"
combination) is the SAME code the actual DoubleMuon data coverage driver
used (`origin/deliver/doublemuon-bumpnet
:studies/cms_coverage/cluster/run_coverage_on_file.py`, read via `git
show`, never checked out): `get_all_combinations`, `IMCalculator`,
`physics_calcs.group_by_final_state`/`is_finalstate_contain_combination`,
`im_pipeline.prepare_im_combination_name`. One necessary adaptation,
discovered and fixed during the LQ test run (a real bug, not
theoretical): attaching genWeight/L1PreFiringWeight_Nom as extra fields
on the object record crashes `ak.num(events)` (called with no axis by
both `group_by_final_state` and `IMCalculator`, `physics_calcs.py:64`,
`im_calculator.py:60`) the instant a non-jagged field is present —
confirmed directly (`AxisError`, first interactive test, record 42407
file 0). Fixed by keeping genWeight/L1PreFiringWeight_Nom as separate,
index-aligned numpy arrays, re-sliced using independently recomputed
copies of the masks the shared functions compute internally (same
`get_start`/`get_count` helpers, not re-derived), with a **runtime
cross-check** at every combination confirming the recomputed mask's
population matches the shared function's own `is_exact_count=False`
output exactly. This assertion ran for every (final-state, combination)
pair across all 122 files and never fired.

## A2: MC inherits data's histogram definitions

MC runs no z-peak/max-mass/peak-removal/first-empty-bin-split logic of
its own. For every produced signature matching a name in the delivered
manifest (`studies/cms_mc_weights/evidence/deliver_manifest_min26bins.json.gz`,
340 entries), the exact recorded outcome of data's own post-processing —
that histogram's `first_filled_bin_low_edge_gev`/
`last_filled_bin_high_edge_gev` — is used as the mass window MC events
are cropped to before filling, on the identical underlying fixed grid.

### Skipped/unreproducible histograms

**None.** `n_skipped_unreproducible = 0` for all 3 samples — every
manifest entry that had a corresponding non-empty MC signature carried a
recorded bin-edge window, so no histogram was skipped for lack of a
recoverable data decision.

### Histograms written (matched the delivered manifest)

**340/340 for all 3 samples** — every one of the 340 delivered BumpNet
categories had at least one matching, non-empty MC signature in each
sample (LQ's own high object-multiplicity events populate essentially
every up-to-4-object combination at some level, even where the
event-topology origin is very different from data's SM-background mix;
same for the two large SM samples).

### MC-only categories (not written this run)

Signatures the MC produced with NO matching name in the 340-entry
delivered manifest (data's own >=100-event / bin-count thresholds keep
the manifest much smaller than the full ~186-combination x
final-state-label combinatorial space; MC frequently populates that
larger space at small raw counts). Never written as a histogram this
run, per A2's own instruction.

| Sample | MC-only categories (count) |
|---|---:|
| 42407 LQToBMu_M-400_pair | 1,611 |
| 67801 TTTo2L2Nu | 2,901 |
| 35671 DYJetsToLL_M-50 madgraphMLM | 441 |

Full lists: `studies/cms_mc_weights/phase1/<recid>/merge_mc_summary.json`
`["mc_only_categories"]` (name -> raw count).

### Raw-count flags (< 100 raw entries in the data-derived window)

| Sample | Histograms flagged (of 340 written) |
|---|---:|
| 42407 LQToBMu_M-400_pair | 20 |
| 67801 TTTo2L2Nu | 0 |
| 35671 DYJetsToLL_M-50 madgraphMLM | 128 |

Full lists (name + raw count in window):
`studies/cms_mc_weights/phase1/<recid>/merge_mc_summary.json`
`["raw_count_flags_below_100"]`. These histograms exist in the output
ROOT files (per A2, not skipped for low count alone) but should be
treated as statistically unreliable shapes if used individually.

## A3: normalisation JSON + registry, no PR#23 code imported

`studies/cms_mc_weights/cms_mc_normalisation.json` (built by
`build_normalisation_json.py` from `normalisation_table_v2.csv`):

| Record | cross_section_pb (=sigma_eff) | gen_filt_eff | k_factor |
|---|---:|---:|---:|
| 42407 | 2.276 | 1.0 | 1.0 |
| 67801 | 89.28 | 1.0 | 1.0 |
| 35671 | 5765.4 | 1.0 | 1.0 |

`gen_filt_eff`/`k_factor` fixed at 1.0 for every record (R1: portal
`sigma_eff` already includes matching/filter; k_factor already folded
into `cross_section_pb`). Registry logic (`build_weights_registry.py`)
independently reimplements PR#23's schema and formula — no
`services/calculations/weights_registry.py` import anywhere in this
branch (confirmed: `git grep` for that import path in this branch's new
files returns nothing). `weight_for()` raises `KeyError` for an
unrecognized record ID.

## A4: default-preserving proof

`prove_default_preserving.py`, run on the cluster:
- **Synthetic check**: PASS (bit-identical bin contents, old vs new
  function, edge cases including NaN and the exact 10000.0 GeV boundary).
- **Real data check**: PASS on **29 real categories** from an actual
  DoubleMuon data job's own `mass_by_category.npz`
  (`/storage/agrp/berkom/atlas-utilization/output/m0m1j0_full_v2/job_5/mass_by_category.npz`
  — already on the cluster, never reprocessed/re-selected here) —
  bit-identical bin contents for every one.
- **OVERALL_PASS: true.** Full result committed:
  `studies/cms_mc_weights/phase1/prove_default_preserving_result.json`.

`run_m0m1j0_on_file.py` and `merge_full_v2.py` (the data driver/merge)
were not modified or re-run.

## A5: Sigma genWeight denominator

Computed via fork master's own, **unmodified**
`aggregate_sumw_for_processed_files()`, with an injected reader reusing
each file's already-read Runs-tree sums. No file failure occurred in any
of the 3 samples (0 missing in all 3 `merge_mc_summary.json`s); had one
occurred, `aggregate_sumw_for_processed_files`'s own `RuntimeError` would
have stopped the merge (this path was exercised structurally, not
observed live, since no real failure occurred).

---

## Per-sample production summary

| Sample | Record ID | Files | Files processed | Trigger branches present | Mean job walltime | Max job walltime |
|---|---:|---:|---:|---|---:|---:|
| LQToBMu_M-400_pair | 42407 | 12 | 12/12 | 12/12 | 101.4s | 158.9s |
| TTTo2L2Nu | 67801 | 49 | 49/49 | 49/49 | 125.5s | 201.2s |
| DYJetsToLL_M-50 madgraphMLM | 35671 | 61 | 61/61 | 61/61 | 44.4s | 87.6s |

All comfortably within the 30-minute PBS walltime budget (max observed:
201.2s, ~3.4 minutes) and the task's own <=02:00:00 cap.

**Test-run checkpoint (LQ, the task's own explicit first checkpoint)**:
12/12 files processed successfully after fixing one real bug found during
this checkpoint (the `ak.num` AxisError above) — proceeded to the other
two samples only after this checkpoint passed cleanly.

---

## V1 -- Arithmetic closure

Sigma(genWeight * sigma_eff*1000*L / Sigma_genWeight), summed over ALL
processed events (before selection), vs. sigma_eff*1000*L directly:

| Sample | Target (sigma_eff*1000*L) | Computed sum | Relative difference | PASS (<1e-6) |
|---|---:|---:|---:|---|
| 42407 | 37,310.468 | 37,310.469 | 2.82e-08 | yes |
| 67801 | 1,463,567.04 | 1,463,567.07 | 1.98e-08 | yes |
| 35671 | 94,512,202.2 | 94,512,202.2 | 0.0 (exact) | yes |

**Mean L1PreFiringWeight_Nom over selected events** (reported separately,
per the task): 42407: 0.957; 67801: 0.965; 35671: 0.977 — all consistent
with the ~2-3% typical 2016 prefiring correction size already noted in
`INVESTIGATION.md` Sec H.

## V2 -- Per-file Sigma genWeight vs Runs genEventSumw

For every one of the 122 processed files, the file's own Events-tree
genWeight sum (independently re-read, full branch, all events) vs. its
own Runs-tree genEventSumw (from `read_runs_tree_sums`, A5):

| Sample | Files checked | Max relative difference | All pass (<1e-6) |
|---|---:|---:|---|
| 42407 | 12 | 8.92e-08 | yes |
| 67801 | 49 | 1.18e-07 | yes |
| 35671 | 61 | 0.0 (exact) | yes |

Full per-file tables:
`studies/cms_mc_weights/phase1/<recid>/validate_v1_v2_result.json`.

## V3 -- Data vs MC

**Expectation, stated in advance (task's own):**
- DY-dominated region: agreement within roughly 5-10%.
- b-jet regions: looser agreement expected (no b-tag SFs; missing
  samples; narrower MC jet peaks without JER smearing).

**Observed:**

| Histogram | Data | MC (DY+TTTo2L2Nu) | Data/MC ratio |
|---|---:|---:|---:|
| `mass_m0m1_cat_0ex_2mx_1jx_0gx_0tx_0bx` (V3a) | 28,496 | 23,070.3 | **1.235** |
| `mass_m0m1b0_cat_0ex_2mx_1jx_0gx_0tx_1bx` (V3b) | 43,548 | 31,224.1 | **1.395** |
| `mass_m0m1b0_cat_0ex_2mx_2jx_0gx_0tx_1bx` (V3b) | 14,418 | 10,104.6 | **1.427** |

Plots: `studies/cms_mc_weights/phase1/plots/genweight_v3_*.png` (stacked
MC vs data, ratio panel, MC stat. band from sumw2). The V3a plot shows a
smoothly falling spectrum with data systematically ~20-35% above MC
across the well-populated low-mass region, becoming statistics-dominated
noise above ~600 GeV — no sign of a shape-breaking bug, a roughly flat
normalization offset.

**Comparison to the stated expectation, no tuning applied:**

The V3a (DY-dominated, zero-b-jet) ratio, **1.235, exceeds the stated
5-10% expectation** (would be 1.05-1.10). The two b-jet-region ratios
(1.395, 1.427) are larger still, consistent with "looser" as stated but
larger than a first guess might suggest. The most likely explanation,
stated plainly and not chased further (out of scope): **phase-1 only
includes 2 of the ~15 Tier-1 background samples** (DY M-50 madgraphMLM +
TTTo2L2Nu only — every other Tier-1 sample, including tW, TTToSemiLeptonic,
WW/WZ/ZZ, ttZ/ttW, is explicitly out of scope for phase-1). A real "2
muons + jet(s) [+ b-jet(s)]" data category also receives contributions
from processes with real jets and (for the b-jet categories) real b-quarks
that are missing from this MC stack entirely — tW and TTToSemiLeptonic in
particular are exactly the kind of single-top/semileptonic-ttbar
processes that would raise a b-jet category's MC yield, and their absence
is a completely different effect from a weight-formula bug. Since V1/V2
independently confirm the weight arithmetic itself is correct to
2e-8-1e-7 relative precision, the most parsimonious reading of the V3
gap is **missing backgrounds, not a normalization defect** — this is a
scope limitation to flag for the next round (adding the rest of Tier-1),
not something to fix by tuning phase-1's own numbers.

## V4 -- Leptoquark overlay

Category chosen: `mass_m0m1b0b1_cat_0ex_2mx_1jx_0gx_0tx_2bx` (2 muons + 1
light jet + 2 b-jets) — the best available match to the leptoquark pair's
own b+mu, b+mu topology (both selected muons AND both selected b-jets
used in the same invariant mass), and the largest-event-count 2-b-jet bin
for the m0m1b0b1 combination in the delivered manifest (5,623 data
events).

Data total in this window: 5,623. LQ weighted total (stop-pair proxy
sigma_eff = 2.276 pb, flagged): 2,926.5. Plot:
`studies/cms_mc_weights/phase1/plots/genweight_v4_leptoquark_overlay.png`
— a falling background-like data spectrum below ~500 GeV and a broad
LQ excess populating roughly 650-1000 GeV, peaking around 800-850 GeV.
**No interpretation given, per the task's own instruction** — this is a
plot, not a claim.

---

## Deliverables

- Code: `run_m0m1j0_on_mc_file_v2.py`, `merge_full_v2_mc.py`,
  `build_normalisation_json.py`, `build_weights_registry.py`,
  `pbs_m0m1j0_mc_phase1.sh`, default-preserving edits to
  `studies/m0m1j0_cms/histograms.py`, `prove_default_preserving.py`,
  `validate_v1_v2.py`, `validate_v3_v4.py`, `finalize_phase1.sh`.
- `studies/cms_mc_weights/cms_mc_normalisation.json` -- committed.
- Registry JSON: not separately written to disk as a standalone file this
  run (the registry object is built and used in-memory inside
  `merge_full_v2_mc.py` via `CMSWeightsRegistry.build(...)`, per DESIGN's
  own weights-registry schema); the resulting per-file normalization
  factor for each sample is recorded directly in that sample's own
  `merge_mc_summary.json["per_file_normalization_factor"]` (42407:
  0.15721; 67801: 0.00046609; 35671: 1.14632) — an on-disk
  `weights_registry.json` matching PR#23's exact file format can be
  produced trivially via `CMSWeightsRegistry.save()` (already
  implemented) if a persisted copy is wanted; not done this run since
  nothing downstream reads it from disk in phase-1's own pipeline.
- ROOT files, one per sample, all under 20 MB, **committed**:
  - `studies/cms_mc_weights/phase1/42407/42407_mc.root` (551,708 bytes,
    340 weighted TH1F histograms with sumw2)
  - `studies/cms_mc_weights/phase1/67801/67801_mc.root` (578,291 bytes,
    340 histograms)
  - `studies/cms_mc_weights/phase1/35671/35671_mc.root` (531,703 bytes,
    340 histograms)
- 4 PNG plots under `studies/cms_mc_weights/phase1/plots/`.
- Per-sample `merge_mc_summary.json`, `validate_v1_v2_result.json`;
  top-level `validate_v3_v4_result.json`;
  `prove_default_preserving_result.json`.

## Anything not verified

- **Why V3's data/MC ratio (1.24-1.43) exceeds the naively-stated 5-10%
  DY-dominated expectation was not independently confirmed to be
  entirely explained by missing Tier-1 samples** — this is the most
  parsimonious explanation given V1/V2's independent confirmation of the
  weight arithmetic, but adding the remaining Tier-1 samples (explicitly
  out of scope for phase-1) was not done to check whether it closes the
  gap.
- The `GluGluHToZZTo4L_M125`-style unresolved k-factor gap and the
  `ZZTo2L2Nu` 42%-discrepancy question from `INVESTIGATION.md`/DESIGN.md
  remain exactly as flagged there — untouched by phase-1 (neither sample
  is part of phase-1).
- Whether the 1,611-2,901 "MC-only" categories per sample contain any
  genuinely interesting shape (e.g. for a later signal-region study) was
  not examined — they are reported only as raw counts, per A2's own
  instruction not to write them as histograms this run.
- No qsub-level resource-usage numbers (actual PBS-reported peak memory,
  CPU) were pulled from `qstat -f`/`tracejob` for individual jobs — only
  each job's own self-reported wall-clock `elapsed_sec` is used above.

## Next step

With V1/V2 passing at the 2e-8-1e-7 level (the weight arithmetic itself
is correct) and V3 showing a real but explicable gap (missing Tier-1
backgrounds), the logical next step is **extending this same phase-1
machinery to the rest of the Tier-1 sample list** (tW top/antitop,
TTToSemiLeptonic, WW/WZ/ZZ, ttZ/ttW, ggH/VBF -- everything
`normalisation_table_v2.csv` already has a settled sigma_eff for, minus
the explicitly-excluded ZZTo2L2Nu and gg->ZZ family) to build the full
combined SM-background file DESIGN.md Sec 8 specifies, and re-running V3
on the completed stack to see whether the data/MC gap narrows toward the
originally-stated 5-10% once the missing processes are included — that
re-check is the direct way to confirm (or rule out) this report's own
"missing backgrounds, not a bug" reading of the V3 gap.
