# Combined DoubleMuon+SingleMuon BumpNet delivery: quality-gate report

Code: commit `521c31ec0085aef300cb0aa1844799f916610316` (production run) plus
`7b113a0`/`0d564b3` (delivery-build script, evidence) on
`deliver/all-datasets-bumpnet`, Matan's fork. Every number below is either
**VERIFIED BY RUNNING** (script/evidence file cited) or **UNVERIFIED**
(stated as such, with the reason).

---

## 1. Cutflows per dataset, and portal identity

**VERIFIED BY RUNNING** (`build_cutflow.py`, summed over every job's own
`job_metadata.json`; `studies/cms_datasets/matching/top4/TOP4_STEP4_IDENTITY_CHECKS.md`
for the portal-identity match).

| Stage | DoubleMuon (57 files) | SingleMuon (152 files) |
|---|---|---|
| Read | 94,148,416 | 323,952,013 |
| After golden JSON | 92,609,925 (98.37%) | 319,083,736 (98.50%) |
| After own trigger | 30,943,565 (33.41% of golden) | 203,285,172 (63.71% of golden) |
| After matched acceptance (gate) | 9,449,024 (30.54% of triggered) | 163,146,091 (80.25% of triggered) |
| Exclusive | 9,449,024 (100.00% of gate) | 153,802,672 (94.27% of gate) |

**Portal identity**: sum of raw events read matches the CMS Open Data
portal's own published totals **exactly** for both datasets
(94,148,416 and 323,952,013 -- zero difference), confirmed in Step 4.

Notes: DoubleMuon's own trigger set (two dimuon DZ paths) fires far less
often relative to golden-JSON-passing events (33%) than SingleMuon's
HLT_IsoMu24-only set (64%) -- expected, since a two-muon trigger is
inherently more selective than a single-muon one. DoubleMuon's own
matched-acceptance rate (31%) reflects Maryna's original bias concern
directly: most DZ-trigger-fired events do not have two muons passing 25
GeV/medium-ID/isolation AND matched to the trigger object. SingleMuon's
80% matched-acceptance rate is much higher since it only needs one such
muon. DoubleMuon is exclusive by construction (100%); SingleMuon's
94.27% exclusive fraction is the key result of matched-mode's
acceptance-based veto (vs. ~79.6% under the old bits-only veto, see
`TRIGGER_MATCHING_REPORT.md`).

---

## 2. Resonances on the combined raw m(mu0, mu1)

**VERIFIED BY RUNNING** (`resonance_check.json`; `plots/plots_z_peak.png`,
`plots/plots_jpsi_window.png`). Computed on the RAW (pre-post-processing)
per-event dimuon mass, pooled from every "_IM_m0m1" signature across
DoubleMuon's inclusive shards and SingleMuon's exclusive shards (57 + 152
files) -- i.e. the exact population this delivery is built from, before
the z-peak/max-mass/peak-removal cuts that would otherwise remove both
resonances entirely (Z is below the 115 GeV z-peak cutoff; J/psi is far
below it too).

- **Total raw m(mu0,mu1) entries: 10,482,831** (DoubleMuon: 9,449,024;
  SingleMuon-exclusive: 1,033,807).
- **Z peak** (Gaussian fit, 70-110 GeV window, 9,795,431 entries in
  window): **mean = 90.847 ± 0.036 GeV, sigma = 2.104 ± 0.038 GeV** --
  close to the true Z mass (91.19 GeV); the fitted sigma reflects a
  simple single-Gaussian fit to a peak that in reality has non-Gaussian
  radiative tails, not a claim of resolution.
- **J/psi**: fine-binned (10 MeV bins, 2.5-3.7 GeV window, 19,274
  entries): a clear peak bin at **3.095 GeV** (true J/psi mass 3.097
  GeV), count 897 vs. a median of 102 elsewhere in the window -- an
  ~8.8x excess exactly at the expected mass.

Both resonances are clearly visible and at the expected masses -- a
strong, independent sanity check that the trigger-matched muon
reconstruction and mass calculation are working correctly end-to-end.

---

## 3. Trigger-mixing check

**VERIFIED BY RUNNING** (`trigger_mixing_data.json`,
`trigger_mixing_2muon_supplement.json`; `plots/trigger_mixing_*.png`).
Method: for each signature, the delivery's own post-processing functions
(`_apply_z_peak_cut`, `_find_rightmost_highest_peak`,
`_split_by_first_empty_bin`, imported unmodified) are applied to the
pooled (DoubleMuon+SingleMuon) raw array to determine the exact mass
window the real delivery kept; each source's own raw values (after the
same static cuts) are then windowed by that identical range -- an EXACT
partition, not an approximation. Every one of the 13 signatures checked
passed a byte-exact cross-check: `n_dm + n_sm == n_main_arr` AND
`values_dm + values_sm == values_combined` bin-by-bin, confirming the
split is exact.

**The literal request (5 largest + 5 one-muon categories) found a
genuine, notable result**: all 10 of these signatures had **n_dm = 0**
-- ZERO DoubleMuon contribution, 100% SingleMuon. This is not a bug: the
5 largest histograms in this delivery are ALL one-muon final states
(SingleMuon-dominated topologies), and DoubleMuon's own matched
acceptance structurally requires **2** matched muons
(`DOUBLEMUON_MATCHED_MIN_MUONS = 2`) -- so DoubleMuon can *never*
contribute to any one-muon category, by construction. There is
therefore no "mixing" to see in these 10 plots (no kink, no crossover --
just SingleMuon alone).

To make this check substantively informative, **3 additional two-muon
categories** (where DoubleMuon CAN contribute) were checked as a
supplement -- e.g. `mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx`:
DoubleMuon = 1,050,972 (89.6%), SingleMuon-exclusive = 121,464 (10.4%).
Across all three two-muon examples, the SingleMuon fraction stays
**roughly flat around 10-15%** across the populated mass range (visible
in `plots/trigger_mixing_mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx.png`'s
lower panel), with increasing statistical noise (not a real trend) above ~1000 GeV where
event counts drop below ~10/bin. **No visible kink or step is seen at
any point where the two contributions might "cross over"** -- the mixing
fraction is stable, not the two curves swapping dominance at some mass.

---

## 4. Bin-count tables at both thresholds, both versions

**VERIFIED BY RUNNING** (`build_summary_table.py`,
`summary_table.json`). Every row below is its own independent funnel run
on ONLY that row's own shard(s) -- counts only, no ROOT files written for
rows 2-5, per instruction.

### >30 filled bins (min31bins)

| Row | Normal | Top-4 |
|---|---|---|
| 1. Combined (delivered) | **1025** | **147** |
| 2. DoubleMuon alone (inclusive) | 339 | 55 |
| 3. SingleMuon alone (inclusive) | 1022 | 148 |
| 4. SingleMuon exclusive part alone | 841 | 131 |
| 5a. Record 30522 (DoubleMuon G) alone | 260 | 46 |
| 5b. Record 30555 (DoubleMuon H) alone | 278 | 47 |
| 5c. Record 30530 (SingleMuon G) alone | 844 | 137 |
| 5d. Record 30563 (SingleMuon H) alone | 879 | 139 |

### >25 filled bins (min26bins)

| Row | Normal | Top-4 |
|---|---|---|
| 1. Combined (delivered) | **1097** | **161** |
| 2. DoubleMuon alone (inclusive) | 367 | 63 |
| 3. SingleMuon alone (inclusive) | 1095 | 160 |
| 4. SingleMuon exclusive part alone | 899 | 137 |
| 5a. Record 30522 (DoubleMuon G) alone | 285 | 52 |
| 5b. Record 30555 (DoubleMuon H) alone | 298 | 54 |
| 5c. Record 30530 (SingleMuon G) alone | 905 | 141 |
| 5d. Record 30563 (SingleMuon H) alone | 935 | 144 |

**The per-record and per-dataset counts above do NOT add up to the
combined count** -- the same histogram name appears in several of them,
and statistics from different files/datasets pool together into a single
histogram once combined (a histogram that fails a threshold in any one
sub-population individually can pass it once pooled, and vice versa is
impossible only in the trivial subset direction -- see the "origin"
breakdown below for the exact accounting).

### "Discard events with more than 4 objects" variant (counts only, normal version's own categories restricted to total object count <=4 -- NOT a separate production)

| Row | >30 bins | >25 bins |
|---|---|---|
| 1. Combined | 144 | 149 |
| 2. DoubleMuon alone | 50 | 55 |
| 3. SingleMuon alone | 141 | 149 |
| 4. SingleMuon exclusive alone | 125 | 129 |
| 5a. Record 30522 alone | 43 | 45 |
| 5b. Record 30555 alone | 44 | 47 |
| 5c. Record 30530 alone | 133 | 136 |
| 5d. Record 30563 alone | 137 | 140 |

(For the top-4 version, "discard >4 objects" is identical to the version
itself by construction -- every top-4 category already has <=4 objects --
so it is not repeated as a separate column; see the Top-4 table above.)

**Lepton-content breakdown** (combined, normal version; counts are
per-category classifications, not mutually exclusive -- a category can
have both muons and electrons and is counted in both columns; min31bins
values first, min26bins in parentheses): one-muon categories: **682
(720)**; two-or-more-muon categories: **343 (377)** [682+343=1025 and
720+377=1097, confirming every surviving category has either exactly one
muon or two-or-more, as required since matched acceptance always demands
>=1 muon]; categories with >=1 electron: **357 (386)** -- a substantial,
not small, fraction, since selected electrons remain objects in these
categories even though this combination's own trigger requirements are
muon-only, exactly as the design task specified ("Selected electrons
remain objects in categories as before").

**How many come purely from one dataset vs. both** (combined, normal
version, exact accounting via each sub-population's own independent
funnel):

| | >30 bins | >25 bins |
|---|---|---|
| Combined total | 1025 | 1097 |
| Survives from DoubleMuon-alone only | 172 | 184 |
| Survives from SingleMuon-exclusive-alone only | 682 | 720 |
| Survives independently in BOTH alone | 159 | 179 |
| Survives ONLY once pooled (neither alone) | 12 | 14 |

**Comparison with the earlier DoubleMuon generic delivery (910/802,
min26/min31)** and the ATLAS-side reference Maryna quoted (~800, for up
to 4 objects): this combined matched-trigger delivery's **normal**
version (1097/1025) is noticeably larger than DoubleMuon's own earlier
generic delivery -- expected, since it now also includes SingleMuon's
substantial exclusive contribution (dominated by one-muon final states
DoubleMuon's own trigger could never populate). The **top-4** version
(161/147) is smaller than both the earlier DoubleMuon generic delivery
and the ATLAS ~800 reference -- this delivery's top-4 truncation is a
much stricter final-state definition (at most 4 objects total, combined
across BOTH datasets' matched-trigger populations) than either
comparison point, so a smaller count is plausible; this report measures
the difference and does not attempt to reconcile it further (out of
scope).

---

## 5. Top-4 specifics

**VERIFIED BY RUNNING** (`studies/cms_datasets/matching/top4/TOP4_STEP2_VALIDATION.md`,
`TOP4_STEP4_IDENTITY_CHECKS.md`).

- Fraction of accepted events truncated (>4 objects before truncation):
  **DoubleMuon 1.34-1.39%** (per file: 30522/0 1.343%, 30555/0 1.388% at
  pilot scale -- full-scale per-job numbers are consistent, see the
  per-job `top4_diagnostics` in `runs_matched/`); **SingleMuon
  0.75-0.81%**. In every case, the large majority of accepted events
  already have <=4 objects and are completely unaffected.
- Categories that gained the most from truncation are, by construction,
  the SAME final-state categories that already dominate the delivery
  (0e_1m_Nj..., 0e_2m_Nj...) -- truncation redistributes a small tail of
  higher-multiplicity events DOWN into these already-large categories,
  it does not create new categories of any significant size (confirmed:
  top-4's own largest category is still the same 1-muon-1-jet topology
  as the normal version's largest, per the manifests).
- **No top-4 category exceeds 4 total objects**: confirmed directly on
  all 4 pilot files (Step 2 check (c), PASS) and structurally guaranteed
  by `build_top4_object_record`'s own construction (verified again here:
  every signature in `manifest_muon_combined_matched_top4_min31bins.json`
  and `..._min26bins.json` has a final-state category summing to <=4).

---

## 6. Low-mass collimated dimuon and electron-muon overlap

**VERIFIED BY RUNNING** (aggregated from every job's own `diagnostics`
block; same definitions as the earlier MuonEG/DoubleEG reports --
diagnostics-only, computed on the broader "own trigger + object
selection" population per file, NOT restricted to the exact
matched-and-combined population, exactly as these diagnostics have
always been defined in this study).

| | DoubleMuon | SingleMuon |
|---|---|---|
| Low-mass (< 5 GeV) opposite-sign dimuon pairs, as a fraction of events with >=2 selected muons | 80,962 / 9,450,067 = **0.857%** | 81,027 / 10,380,771 = **0.781%** |
| Electron-muon pairs with dR < 0.1 (of events with >=1 electron AND >=1 muon) | 2.14% | 0.33% |
| Electron-muon pairs with dR < 0.4 | 4.55% | 1.02% |

Both are consistent in order of magnitude with the earlier DoubleEG/MuonEG
reports' own low-mass and overlap measurements (~0.5-1.6% range,
depending on the exact threshold) -- no overlap removal is added anywhere
in this delivery, per this study's own unchanged scope.

---

## 7. Required plots

All in `plots/`, per version (`normal`/`top4`): `plot_<version>_1_largest.png`,
`plot_<version>_2_median.png`, `plot_<version>_3_near_25bin_boundary.png`,
`plot_<version>_one_muon_{1,2,3}.png`, `plot_<version>_crop_comparison.png`.
Plus `plots_z_peak.png`, `plots_jpsi_window.png` (Section 2) and
13 `trigger_mixing_*.png` (Section 3).

---

## 8. Known artifacts

- **Duplicate rate**: the design task's closure test found exactly 1
  double-counted collision in 263,540 checked (~4 per million), root-
  caused to a genuine Muon_mediumId disagreement between DoubleMuon's and
  SingleMuon's independently-produced copies of the same physical event
  (`TRIGGER_MATCHING_REPORT.md`, Step 4). Not de-duplicated in this
  delivery (Matan's explicit decision) -- disclosed here and in the
  delivery's own README.txt.
- **DoubleMuon 17/8 GeV leg approximation**: DoubleMuon's matched
  acceptance cannot distinguish which matched muon corresponds to the 17
  GeV leg vs. the 8 GeV leg of the dimuon trigger from `TrigObj_filterBits`
  alone; the approximation used (leading matched object >= 17 GeV) is
  documented in full in `TRIGGER_MATCHING_SPEC.md` Section 3 and carries
  forward unchanged into this delivery.
- **Per-run anomaly**: none was flagged during production -- all 209 jobs
  succeeded on the first attempt with zero retries, zero `CAPPED::`
  entries, and cutflow fractions consistent between the G and H eras
  within each dataset (Section 1). No dedicated per-run scan was run
  beyond the golden-JSON validation already applied to every event; this
  is stated as a scope boundary, not a claim that no such anomaly could
  exist.
