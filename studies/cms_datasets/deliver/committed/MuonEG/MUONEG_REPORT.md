# MuonEG full run + generic-population delivery — quality-gate report

Every number below is **VERIFIED BY RUNNING** (evidence file named) unless
marked **UNVERIFIED**. Covers the full 48-file MuonEG run
(`--population generic`) and the delivery built from it. See `README.txt`
for what the four ROOT files are.

Evidence: `build_summary.json`, `cutflow_and_resonances.json`,
`manifest_breakdown.json`, `real_root_verify_min31bins.json`,
`real_root_verify_min26bins.json`, `manifest_muoneg_generic_min31bins.json`,
`manifest_muoneg_generic_min26bins.json`, plus
`studies/cms_datasets/evidence/muoneg_pilot_reproducibility.json` and
`studies/cms_datasets/evidence/preflight_summary.json` (Part 1(d), for
the pre-flight cross-check in Section 3).

---

## 0. Code pinning (Hard Rule 6) — worked correctly this time

**VERIFIED BY RUNNING**: every change to `run_dataset_on_file.py` needed
for this task (the diagnostics-only addition, Section 1 below) was
committed and pushed *before* the job array was submitted. All 48 jobs
ran from a dedicated checkout
(`/storage/agrp/berkom/atlas-utilization/work/muoneg_run_pinned/repo`)
pinned to commit `bc1f74b`, untouched until every job finished. All
report-generation-script work (several further commits, generalizing
existing scripts) happened in the separate, already-existing shared
checkout. Confirmed directly: **all 48 jobs report the identical git
commit `bc1f74b`** — the mixed-commit problem from the DoubleEG task did
not recur.

One diagnostic (leading muon/electron pT restricted to e+mu events,
Section 5) was identified as missing only *after* the array had already
started; per this same discipline, it was **not** retroactively added to
the pinned checkout or this run — instead it was added to the shared
checkout for the *next* dataset, and this report states plainly where
MuonEG's own results fall back to a less specific substitute (Section 5).

---

## 1. Step 1 diagnostics addition

**VERIFIED BY RUNNING** (diff reviewed before commit; smoke-tested on one
real file before the full run). Added to `compute_diagnostics` — strictly
diagnostics-only, no selection/gating/combination/shard-writing code
touched (Hard Rule 5): for events with ≥1 selected electron AND ≥1
selected muon — dR(e0,mu0) and the per-event minimum dR over every
selected electron-muon pair (0–1.0, 0.01 bins, explicit overflow count);
m(e0,mu0) (0–5 GeV, 0.05 GeV bins); the e0×mu0 charge-product sign; and
selected b-jet multiplicity (0/1/2/3/≥4). Electron charge was threaded
through via `ak.with_field` on a diagnostics-only copy of the electrons
array (mirroring `selection.select_electrons`'s own selection
constants), never modifying the real `electrons` object used for
gating/shards.

---

## 2. Identity check (Step 3a) and pilot reproducibility (Step 3b)

**Both PASS — the most important results.**

| Check | Result |
|---|---|
| Jobs present | 48 / 48, each (record, file_index) pair exactly once |
| Sum of `n_read` | 63,091,128 — matches expected exactly |
| CAPPED:: entries | 0 |
| Distinct git commits | 1 (`bc1f74b`) |

Pilot reproducibility (`studies/cms_datasets/evidence/muoneg_pilot_reproducibility.json`):

| | Record 30528 file 0 | Record 30561 file 0 |
|---|---|---|
| `n_after_gate` (pilot = full run) | 203,017 = 203,017 | 230,652 = 230,652 |
| Inclusive shard | identical signatures, identical arrays | identical signatures, identical arrays |
| Exclusive shard | identical signatures, identical arrays | identical signatures, identical arrays |

---

## 3. Exclusive bookkeeping (Step 3c)

**VERIFIED BY RUNNING** (`cutflow_and_resonances.json`):

| Quantity | Value |
|---|---:|
| Total inclusive (post-gate) | 7,531,669 |
| Total exclusive (post-gate) | 7,361,191 |
| Inclusive − exclusive (post-gate vetoed) | **170,478** |
| Exclusive fraction (post-gate) | **0.9774** |

**Per-dataset veto totals** (pre-population-gate, from each job's own
`n_vetoed_by_each_higher_dataset`, reported separately as requested):

| Vetoing dataset | Pre-gate vetoed count |
|---|---:|
| DoubleMuon | 136,017 |
| DoubleEG | 47,146 |
| Sum (upper bound — double-counts events vetoed by both) | 183,163 |

**Comparison with the pre-flight**: the pre-flight's own trigger-level
exclusive fraction for MuonEG is **0.9820** (`preflight_summary.json`,
Part 1(d)) — and its own trigger-level population count,
`n_own_trigger_total["MuonEG"] = 10,137,471`, matches this full run's own
`after_trigger_OR` **exactly**, confirming the two independent
measurements (a lightweight pre-flight scan vs. the full production
driver) agree on the underlying population precisely.

**Explaining the difference (0.9820 pre-gate vs. 0.9774 post-gate)**: the
post-gate fraction is measurably lower — i.e. the *vetoed* share is
larger after the population gate is applied. This is a real, expected
selection effect, not an inconsistency: an event that fires MuonEG's own
trigger *and* also fires DoubleMuon's or DoubleEG's trigger almost by
definition contains an extra reconstructed lepton (a second muon or a
second electron) beyond the single e+mu pair MuonEG's own trigger needs
— which makes such vetoed events systematically more likely to also
clear the "≥2 selected objects of any type" population gate than a
"purely" MuonEG-triggered event with only one muon and one electron.
Vetoed events are therefore enriched, not depleted, by the gate, pulling
the post-gate exclusive fraction down slightly relative to the pre-gate
one. This is a plausible, mechanistically-grounded explanation, not
independently proven further (out of this task's scope).

---

## 4. Cutflow and portal identity

**VERIFIED BY RUNNING** (`cutflow_and_resonances.json`):

| Stage | Events | Fraction of previous stage |
|---|---:|---:|
| Read | 63,091,128 | — |
| After golden JSON | 62,385,800 | 98.88% |
| After trigger (`Mu23Ele12_DZ` OR `Mu8Ele23_DZ`) | 10,137,471 | 16.25% (of golden) |
| — `HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ` alone | 2,664,567 | — |
| — `HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ` alone | 9,032,090 | — |
| After population gate (generic) | 7,531,669 | 74.30% (of triggered) |
| Exclusive | 7,361,191 | 97.74% (of gated) |

**Portal identity check**: sum of `n_read` (63,091,128) equals the CMS
Open Data portal's own published total for records 30528 + 30561 —
**exact match**.

---

## 5. Resonance check (negative) and top-quark sanity

**VERIFIED BY RUNNING** (`raw_emu_mass_vs_same_flavor.png`,
`cutflow_and_resonances.json`).

**No Z peak in m(e0,mu0)**: window (85–97 GeV) vs. sideband-average
ratio = **0.9477** — at or slightly below 1.0, i.e. **no excess** near
the Z mass. Plotted alongside m(mu0,mu1) and m(e0,e1) "where present"
(same-flavor pairs) for direct visual comparison: both of those **do**
show a clear peak at 91.2 GeV, making the flat continuum in m(e0,mu0)
unambiguous by contrast (see the plot).

**Top-quark sanity**:
- b-jet multiplicity for e+mu events (159,675 total): 0 b-jets 70,237;
  1: 56,584; 2: 31,588; 3: 1,198; ≥4: 68. **Fraction with ≥1 selected
  b-jet: 56.0%** — substantial, consistent with a top-pair-enriched
  sample.
- **Opposite-sign vs. same-sign e-mu pairs**: 148,709 opposite-sign vs.
  10,966 same-sign — **93.1% opposite-sign**, a large excess as expected
  from top pairs and Z→ττ.

**Leading muon/electron pT for e+mu events**: **UNVERIFIED for the exact
requested population.** This diagnostic (leading pT restricted to events
with ≥1 electron and ≥1 muon) was only added to the shared checkout
*after* MuonEG's job array had already started under its pinned commit
(Section 0) — it is not present in MuonEG's own job outputs, and per this
task's own code-pinning discipline it was not retroactively applied.
`leading_muon_electron_pt_emu.png` instead shows the **unrestricted**
leading muon/electron pT (over the whole inclusive population, not just
e+mu events) as the closest available substitute, with the 25 GeV object
cut and the trigger legs (23/12 GeV electron legs, 8 GeV muon leg — the
DZ paths' own thresholds) marked; this will be available for the next
dataset run.

---

## 6. Electron-muon overlap — the key new measurement

**VERIFIED BY RUNNING** (`electron_muon_dr.png`, `emu_lowmass_mass.png`,
`cutflow_and_resonances.json`), over 159,675 events with ≥1 selected
electron and ≥1 selected muon:

| dR threshold | Fraction of e+mu events below it |
|---|---:|
| < 0.05 | **0.54%** (863 / 159,675) |
| < 0.1 | **0.78%** (1,252 / 159,675) |
| < 0.4 | **1.62%** (2,587 / 159,675) |

Both the dR(e0,mu0) and the minimum-dR-over-all-pairs distributions show
a clear "bathtub" shape: a small but genuine spike at very low dR, a
minimum around dR≈0.15–0.3, then a rise toward large dR where the large
majority of pairs sit (91.5% have min dR ≥ 1.0 — the histogram's own
overflow bucket, 146,046 of 159,675 events). The low-mass m(e0,mu0) plot
(`emu_lowmass_mass.png`) shows a corresponding excess at very low mass,
consistent with a genuine collimated population rather than noise.

**Plain statement**: a real, measurable collimated electron-muon
population exists in MuonEG, at roughly the **0.5–1.6% level** depending
on how tight a dR threshold is used to define "collimated" — small, but
not negligible, and it is not zero. This is fully consistent with the
known absence of electron-muon overlap removal in this project's object
definitions (documented, not fixed, per this task's own scope).

**How many delivered histograms are potentially affected** (i.e. involve
both an electron and a muon in their final-state category): **346** (>30
bins) and **387** (>25 bins) — see Section 7's `n_ge1_electron_and_ge1_muon`
counts. These are the histograms where the measured overlap effect above
could, in principle, be contributing some fraction of events.

**Same dR fractions for DoubleMuon and DoubleEG**: **UNVERIFIED — not
re-run.** The `dr_e0_mu0` / `min_dr_any_e_any_mu` diagnostics did not
exist when DoubleMuon and DoubleEG were processed (they were added in
this task, for MuonEG); neither dataset's own job outputs carry this
field, and per this task's own scope (no re-running of DoubleMuon or
DoubleEG), this cannot be obtained from already-existing outputs.

---

## 7. Counts: histograms, lepton content, object content, three-dataset union

**VERIFIED BY RUNNING** (`build_summary.json`, `manifest_breakdown.json`):

| Funnel stage | Count |
|---|---:|
| (b) After `min_events_per_fs=100` | 1,584 |
| (c) After full post-processing, ≥100 main events | 1,269 |
| (d) BumpNet-usable, >30 bins | **998** |
| >25 bins | **1,102** |
| Extra at >25 vs. >30 bins | 104 |

**By lepton content** (0, 1, ≥2 selected leptons):

| | >30 bins | >25 bins |
|---|---:|---:|
| 0 leptons | 138 | 141 |
| 1 lepton | 425 | 456 |
| ≥2 leptons | 435 | 505 |

**By object-content category**:

| Category | >30 bins | >25 bins |
|---|---:|---:|
| b-jet-containing | 658 | 732 |
| lepton+jet | 236 | 261 |
| lepton-only | 14 | 17 |
| jet-only | 90 | 92 |

**The conventional e+mu subset** (≥1 selected electron AND ≥1 selected
muon): **346 histograms at >30 bins, 387 at >25 bins.**

**New relative to the UNION of DoubleMuon and DoubleEG generic
deliveries** (by histogram name):

| | MuonEG | DoubleMuon | DoubleEG | Union of DM+DEG | Shared w/ union | New vs. union |
|---|---:|---:|---:|---:|---:|---:|
| >30 bins | 998 | 802 | 644 | 1,283 | 679 | **319** |
| >25 bins | 1,102 | 910 | 712 | 1,412 | 780 | **322** |

**Running distinct-name total across all three datasets delivered so far**:

| | >30 bins | >25 bins |
|---|---:|---:|
| **Union (DoubleMuon ∪ DoubleEG ∪ MuonEG)** | **1,602** | **1,734** |

---

## 8. Quality-gate plots

All committed under `plots/`:

- `plot_1_largest.png` — `mass_j0j1_cat_0ex_0mx_2jx_0gx_0tx_0bx` (1,997,513
  events, jet-jet, zero leptons — same as the largest zero-lepton
  histogram below).
- `plot_2_median.png` — `mass_e0m0b0b1_cat_1ex_1mx_2jx_0gx_0tx_2bx` (2,566 events).
- `plot_3_near_25bin_boundary.png` — `mass_b0b1_cat_1ex_0mx_3jx_0gx_0tx_3bx` (26 filled bins).
- Three categories absent from both DoubleMuon and DoubleEG generic
  deliveries (`plot_new_category_{1,2,3}.png`) — **all three are e+mu
  categories** (the task's own requirement of "at least one" is easily
  exceeded, since e+mu final states are naturally what MuonEG alone can
  produce): `mass_e0m0_cat_1ex_1mx_1jx_0gx_0tx_0bx` (14,480 events),
  `mass_e0m0_cat_1ex_1mx_0jx_0gx_0tx_1bx` (13,235 events),
  `mass_e0m0_cat_1ex_1mx_0jx_0gx_0tx_2bx` (12,165 events).
- `plot_largest_zero_lepton.png` — same as the largest overall (above).
- `plot_crop_comparison.png` — the largest histogram, uncropped vs. cropped.

---

## 9. Known artifacts

1. **Zero- and one-lepton categories**: 138 (>30 bins) / 141 (>25 bins)
   delivered histograms have zero selected leptons; 425 / 456 have
   exactly one — same mechanism as DoubleMuon/DoubleEG: trigger-level
   leptons failing the tighter offline selection, with the generic gate
   still admitting the event via jets/b-jets.
2. **Electron-muon overlap** (Section 6): a real ~0.5–1.6% collimated
   e+mu population exists, affecting up to 346–387 delivered histograms
   that have both an electron and a muon in their category. Not
   corrected — documentation only, per this task's scope.
3. **Run 283469** (Run2016H): this run's own pre-flight scan flagged
   this run as anomalous for DoubleEG, DoubleMuon, MET, and SingleMuon
   specifically — **MuonEG's own trigger paths were not among the
   flagged zero-fire cases in that scan** (`preflight_summary.json`,
   Part 1(b)). Whether MuonEG's own data in that specific run is
   otherwise unremarkable is **UNVERIFIED** (not separately
   cross-checked here, out of this task's scope) — included in this
   delivery's data as-is either way.

---

## 10. Verification summary

- Real ROOT 6.40.02: 0 problems across all 998 and all 1102 histograms
  (count, non-empty bin 1, cropped-vs-uncropped content match).
- Identity check: PASS. Pilot reproducibility: PASS. Exclusive
  bookkeeping: explained (Section 3).
- No continuity check applies (no prior MuonEG delivery); the
  three-dataset union comparison (Section 7) serves the analogous role.
