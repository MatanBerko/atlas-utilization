# DoubleMuon full run + generic-population delivery — quality-gate report

Every number below is **VERIFIED BY RUNNING** (evidence file named) unless
marked **UNVERIFIED**. This report covers the full 57-file DoubleMuon run
(`--population generic`) and the delivery build from it — see
`README.txt` for what the four ROOT files are and how this delivery
differs from the earlier one.

Evidence files (all in this directory): `build_summary.json`,
`continuity_check.json`, `cutflow_and_resonances.json`,
`real_root_verify_min31bins.json`, `real_root_verify_min26bins.json`,
`manifest_doublemuon_generic_min31bins.json`,
`manifest_doublemuon_generic_min26bins.json`.

---

## 1. Cutflow (all 57 files) and portal identity check

**VERIFIED BY RUNNING** (`cutflow_and_resonances.json`, summed directly
from all 57 jobs' own `job_metadata.json`):

| Stage | Events | Fraction of previous stage |
|---|---:|---:|
| Read | 94,148,416 | — |
| After golden JSON | 92,609,925 | 98.37% |
| After trigger, `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ` alone | 27,457,432 | 29.65% (of golden) |
| After trigger, `HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ` alone | 28,094,076 | 30.34% (of golden) |
| After trigger, **OR of both** | 30,943,565 | 33.42% (of golden) |
| After population gate (generic: ≥2 selected objects of any type) | 21,608,716 | 69.84% (of triggered) |
| Exclusive (fails every higher-veto-priority dataset — there are none above DoubleMuon) | 21,608,716 | **= inclusive, exactly**, as expected (DoubleMuon is top veto priority) |

**Portal identity check**: sum of `n_read` across all 57 files
(94,148,416) equals the CERN Open Data portal's own published
`number_events` total for records 30522 + 30555 (94,148,416) —
**exact match**.

---

## 2. Resonances: raw (pre-post-processing) dimuon mass

**VERIFIED BY RUNNING** — the raw `m(mu0,mu1)` histograms from all 57
jobs' own diagnostics, summed (`cutflow_and_resonances.json`).

- **Z peak**: Gaussian fit over 75–107 GeV → **90.85 ± 0.05 GeV**
  (`raw_dimuon_mass_full_range.png`). This sits below the true Z mass
  (91.19 GeV) by about 0.3 GeV, consistent with CMS Open Data's own
  uncalibrated raw reconstruction (no energy-scale corrections are
  applied anywhere in this pipeline) — **not investigated further, out
  of this task's scope.**
- **J/ψ peak**: a dedicated fine-binned (20 MeV) histogram was added to
  the diagnostics specifically because the standard 1 GeV binning cannot
  resolve it at all. Gaussian fit over 2.8–3.4 GeV → **3.094 ± 0.001 GeV**
  (true PDG value: 3.0969 GeV — matches to within 3 MeV) with a fitted
  width of 37 MeV, consistent with CMS's own dimuon mass resolution at
  this mass. See `raw_dimuon_mass_lowmass_region.png`: the J/ψ peak is
  sharp and unambiguous, with a visible secondary bump near 3.6–3.7 GeV
  (consistent with ψ(2S)) and a rise starting near 9.4 GeV (consistent
  with the Υ family) — genuine dimuon resonance structure, not
  investigated further here (out of scope).

---

## 3. Leading and subleading selected muon pT

**VERIFIED BY RUNNING** (`leading_subleading_muon_pt.png`, summed from
all 57 jobs). Both distributions show a sharp turn-on exactly at the
25 GeV object cut (no events below it, confirming the cut is correctly
enforced), with the two DoubleMuon trigger legs (17 GeV and 8 GeV) both
correctly falling below the object cut — the trigger is looser than the
offline selection, as expected. The leading-muon distribution peaks
around 45–47 GeV; the subleading peaks earlier, around 40–43 GeV.

---

## 4. The collimated low-mass dimuon population

**VERIFIED BY RUNNING** (`cutflow_and_resonances.json`,
`low_mass_dimuon_population.png`): opposite-sign muon pairs with
m(μμ) < 2 GeV, summed across all 57 jobs:

| Quantity | Value |
|---|---:|
| Opposite-sign pairs, m < 2 GeV | 53,444 |
| All population-gated events (denominator i) | 21,608,716 |
| **Fraction of (i)** | **0.247%** |
| Events with ≥2 selected muons (denominator ii) | 9,450,067 |
| **Fraction of (ii)** | **0.566%** |

**Is this comparable to the earlier "~2%" figure?** The earlier figure
was found in `studies/m0m1j0_cms/v3_variants/REPORT.md`: the "V0
baseline" fraction with m(μμ) < 2 GeV is **2.47%**, computed over a
**different, more restrictive population** — events with ≥2 selected
muons **AND ≥1 selected light jet** (the m0m1j0 study's own baseline
population). A closely related figure, **2.18%**, appears in the earlier
DoubleMuon delivery's own `README.txt`, for the inclusive m0m1j0
histogram's own population (1,772,095 events, same ≥2mu-and-≥1jet
requirement).

**These are NOT directly comparable to either of this report's two
fractions.** Both earlier figures are computed over a *jet-conditioned*
population (every event already has a jet, which is exactly the
topology that produces a nearby, collimated reconstructed object), while
this report's denominators are either the full "generic" gated
population (any ≥2 objects of any type — most of which have no jet at
all) or plain "≥2 selected muons" with no jet requirement. Diluting the
denominator with events that have no jet nearby to cause the collimation
effect at all plausibly explains why this report's fractions (0.25%,
0.57%) are 4–10× smaller than the earlier, jet-conditioned 2.18–2.47%.
This is a **plausible explanation, not independently proven here** — no
new investigation into the low-mass population's origin was performed,
per this task's own out-of-scope instruction.

---

## 5. Funnel and delivered-histogram counts

**VERIFIED BY RUNNING** (`build_summary.json`):

| Funnel stage | Count |
|---|---:|
| (a) All (pattern × category) signatures, ≥1 event | *(not separately re-counted here — see stage b)* |
| (b) After `min_events_per_fs=100` | 1,284 |
| (c) After full post-processing (z-peak, max-mass, peak removal, outlier split), ≥100 main events | 1,053 |
| (d) BumpNet-usable, >30 filled bins, ≥100 events | **802** |
| >25 filled bins, ≥100 events | **910** |

**New relative to the earlier delivery** (VERIFIED BY RUNNING, the
continuity check confirms every old histogram is unchanged and present):

| | Earlier delivery | This delivery | New |
|---|---:|---:|---:|
| >30 bins | 316 | 802 | **486** |
| >25 bins | 340 | 910 | **570** |

**By object-content category** (`object_content_category`, from
`services.cms_coverage.cluster.merge_and_count`, imported unmodified):

| Category | >30 bins | >25 bins |
|---|---:|---:|
| b-jet-containing | 553 | 621 |
| lepton+jet | 170 | 190 |
| lepton-only | 14 | 23 |
| jet-only | 65 | 76 |

**By final-state type** (informal tags, not a strict partition — a
category can match more than one; "zero-jet" means zero light jets AND
zero b-jets):

| Type | >30 bins | >25 bins |
|---|---:|---:|
| zero-jet | 4 | 5 |
| one-lepton (exactly 1 electron or muon total) | 266 | 305 |
| with-electrons (≥1 electron) | 82 | 139 |

---

## 6. Quality-gate plots

All committed under `plots/`:

- `plot_1_largest.png` — largest by event count: `mass_j0b0_cat_0ex_0mx_1jx_0gx_0tx_1bx`
  (2,176,164 events — a pure jet+b-jet combination). **Note**: this
  histogram is itself one of the 486 categories new relative to the
  earlier delivery (a jet+b-jet-only final state has 0 muons, so it was
  never reachable under the old ≥2mu-and-≥1jet gate) — the single
  largest histogram in this whole delivery did not exist in the earlier
  one at all.
- `plot_2_median.png` — median by event count: `mass_m1j1_cat_0ex_2mx_2jx_0gx_0tx_2bx`
  (2,260 events).
- `plot_3_near_25bin_boundary.png` — `mass_b0b1_cat_0ex_1mx_3jx_0gx_0tx_3bx`
  (26 filled bins, just clears the looser cut).
- Three NEW-relative-to-the-earlier-delivery categories
  (`plot_new_category_{1,2,3}.png`):
  - `mass_m0m1_cat_0ex_2mx_0jx_0gx_0tx_0bx` — **107,400 events, a
    zero-jet dimuon category** (pure dimuon, no jet at all — could never
    exist in the earlier delivery, which required ≥1 jet).
  - `mass_j0b0_cat_0ex_0mx_1jx_0gx_0tx_1bx` (same as the largest, above).
  - `mass_j0j1_cat_0ex_0mx_2jx_0gx_0tx_0bx` (1,908,392 events, jet-only).
- `plot_crop_comparison.png` — the largest histogram, uncropped vs.
  cropped, side by side.

---

## 7. Known artifacts

1. **The collimated low-mass dimuon population** — measured in Section 4
   above (53,444 opposite-sign pairs below 2 GeV; 0.25%/0.57% of the two
   denominators). Not investigated further, per this task's scope.

2. **Muon-jet overlap, handled by the ΔR<0.4 jet-lepton cleaning** —
   **UNVERIFIED by this task** (not re-measured here): a prior task
   (`studies/m0m1j0_cms/DESIGN.md`) measured that 92.66% (Run2016G) /
   92.68% (Run2016H) of raw jets are within ΔR<0.4 of a selected muon —
   exactly why the jet selection's own cleaning step exists. This
   report's own selection is unchanged and still applies that cleaning;
   the figure itself was not re-derived in this task.

3. **Zero-lepton categories in a dilepton-triggered dataset**: **148** of
   the 802 delivered (>30-bin) histograms, and **156** of the 910
   (>25-bin), have zero selected electrons AND zero selected muons in
   their final-state category, despite every event in this delivery
   having fired a dimuon trigger. This happens because the generic
   population gate only requires ≥2 selected objects of *any* type — an
   event where both triggering muons fail the *offline* selection (pT>25
   GeV, medium ID, isolation<0.15 — all tighter than the trigger's own
   17/8 GeV legs) can still pass the gate on jets/b-jets alone, landing
   in a final-state category with 0 reconstructed leptons even though a
   dimuon trigger fired it into the dataset.

4. **Run 283469** (Run2016H): flagged in this track's own pre-flight
   scan (`studies/cms_datasets/PREFLIGHT_REPORT.md`, Part 1(b)) as an
   anomalously small/partial run (multiple datasets independently showed
   very low golden-event counts and zero fires for normally high-rate
   trigger paths in this one run). Not re-investigated here, per this
   task's own scope — included in this delivery's data as-is.

---

## 8. Verification summary

- Real ROOT 6.40.02 (independent of uproot, via CVMFS
  `LCG_110/x86_64-el9-gcc13-opt`) confirms, for both the >30-bin and
  >25-bin cropped/uncropped pairs: histogram counts match, every cropped
  histogram's bin 1 is non-empty, and cropped contents equal the
  uncropped version over the kept range exactly — **0 problems found**,
  802 and 910 histograms respectively (`real_root_verify_min31bins.json`,
  `real_root_verify_min26bins.json`).
- Continuity check: **316/316 and 340/340 identical, 0 problems** —
  the single most important result of this task (`continuity_check.json`).
