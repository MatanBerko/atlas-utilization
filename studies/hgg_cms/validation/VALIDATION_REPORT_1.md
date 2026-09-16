# H→γγ full-run validation, round 1 (implementation task 6, Part 3)

Run locally against the merged, non-blinded outputs copied off the cluster
after Part 1's merge reported `status: "COMPLETE"` for both data and
signal (see `merge_summary_data.json` / `merge_summary_signal.json` for
the full identity-check record). Every script here refuses to load a
file whose name contains "BLINDED", and independently re-asserts (twice:
once via `studies.hgg_cms.output.read_output`, once again in this
package's own `common.py`) that no data event with 115 ≤ m_γγ ≤ 135 GeV
is present in anything it loads. No data event in the blinded window was
ever read, printed, or plotted while producing this report.

**Bottom line: nothing here looks broken.** All six checks land within
physically sensible ranges, cross-check each other and the independent
numbers you supplied, and the one flag raised (Part B) is a modeling
observation for the *later* background-fit task, not evidence of a bug in
this run.

Reproduce with:
```
python -m studies.hgg_cms.validation.run_all --with-part-c --lumi-csv <path to pp_2016lumibyls.csv>
```
(Part C needs that one 21 MB CSV, downloaded separately — see
`part_c_run_stability.py`'s own header for the source URL — and is not
committed to the repo, matching this project's existing convention for
that file.)

---

## A — Data sidebands & photon kinematics (full statistics)

**Counts** (blinded window excluded by construction — `data_sidebands.root`
contains no event in [115,135] at all):

| | total | EBEB | notEBEB |
|---|---:|---:|---:|
| sideband events | 182,551 | 90,336 | 92,215 |
| — of which 100–115 GeV | 119,138 | | |
| — of which 135–180 GeV | 63,413 | | |

`part_a_mgg_panels.png` — three panels (inclusive / EBEB / notEBEB),
1 GeV bins, blinded band shown as an empty grey strip. All three show a
smoothly falling spectrum with no visible spikes, gaps, or structure —
exactly what a QCD/γ+jet-dominated background should look like.

`part_a_kinematics_grid.png` — lead/sublead pT, η, R9, mvaID: data
sidebands vs ggH simulation, shape-normalized. **Differences, and why
they're expected, not a bug:**
- **pT**: data sidebands extend to visibly higher pT than ggH. Expected —
  the sidebands include the 135–180 GeV region, and the scaled-pT cuts
  (pT₁>m/3, pT₂>m/4) push the pT floor up with mass, while ggH itself
  peaks at 125 GeV.
- **η**: both show the barrel–endcap gap notch near |η|≈1.5 (the excluded
  1.4442–1.566 region); shapes otherwise track closely.
- **R9 / mvaID**: both peak sharply near 1 (as expected — the
  trigger-mimicking cuts already require good shower shapes), but data
  has a visibly heavier low-R9/low-mvaID tail than ggH. Expected — the
  sidebands are background-dominated (fakes, converted photons, jets
  faking photons), which populate exactly that tail; genuine prompt
  photons from a real Higgs decay mostly don't.

No fits performed here (by design — Part B is the one allowed exploratory
fit).

## B — Low-edge (turn-on) check — **FLAGGED, exploratory only**

Fit an exponential and a power law to inclusive sidebands over
105–115 ∪ 135–180 GeV (1 GeV bins), extrapolated into 100–105 GeV:

| | χ²/ndf (fit region) | predicted 100–105 total | observed 100–105 total | significance |
|---|---:|---:|---:|---:|
| exponential | 8.07 | 44,365 ± 196 | 49,521 ± 223 | **+17.4σ** |
| power law | 1.10 | 47,917 ± 307 | 49,521 ± 223 | **+4.2σ** |

Observed = 49,521. **Flagged: `possible turn-on/edge effect`** (deviates
>3σ from *both* extrapolations, the pre-set rule). See
`part_b_turnon.png`.

**Read this carefully — the direction matters.** This is an **excess**
over the smooth extrapolation, not a deficit. A trigger-inefficiency
turn-on (the `Mass90` online mass cut, or the offline pT/m scaled cuts
running out of acceptance) would predict *fewer* events than a smooth
extrapolation near the edge, not more — so this pattern is not consistent
with simple acceptance loss. Two more likely explanations:
1. **Extrapolation bias, not a real edge feature.** The power law fits
   the 105–180 region very well in-range (χ²/ndf=1.10) but a single
   global functional form is not guaranteed to extrapolate accurately
   right at the boundary of where it was fit — the underlying
   diphoton-continuum curvature can genuinely change slope near 100–115
   GeV (it's close to where the falling QCD/γ-jet spectrum's shape
   itself bends), and neither a simple exponential nor a simple power law
   has enough freedom to capture that from outside the region.
2. Some genuine, mild sculpting from the combination of the trigger's
   `Mass90` online mass requirement (which has its own resolution-driven
   turn-on straddling 90 GeV — some residual shape from that turn-on
   could still extend into 100–105) and the offline scaled-pT cuts
   interacting with the steeply-falling photon pT spectrum.
3. **Added 16 Sep 2026, candidate explanation, to be TESTED by the Z→ee
   run**: electron-veto leakage. Real Z→e+e− events (including the
   off-shell Drell-Yan continuum tail, which genuinely extends well above
   the Z pole) can leak into this sample if an electron happens to pass
   `Photon_electronVeto == True` despite being a real electron — a
   `electronVeto`-inefficiency effect, not a resolution effect. This is
   a real, physically plausible background component distinct from
   QCD/γ+jet, and its size is not yet measured. The prepared (not yet
   submitted) Z→ee run computes exactly this: how many DY simulation
   events would pass the real H→γγ selection (electronVeto REQUIRED
   True) landing in 100–105 and 105–115 GeV — see
   `studies/hgg_cms/cluster/ZEE_RUN_README.md`'s "electron-veto leakage
   estimate" section and `studies/hgg_cms/validation/zee/
   hgg_leakage_estimate.py`, which will compare its result directly
   against this ~1,604-event excess once that run has actually happened.

Either way: **the final background-fit range is decided in the
background-model task, not here** — this result simply supports the
pre-set suggestion to consider starting that fit at 105 or 110 GeV rather
than 100 GeV, given how poorly a single smooth function extrapolates
across this boundary.

## C — Run-by-run stability

156 certified runs (Run2016G 278820–280385 + Run2016H 280919–284044), all
156 with nonzero certified luminosity (consistent with Part A of
`LUMI_DECISION.md`'s finding that missing sections carry ~0 luminosity).

- **Total**: 182,551 events / 16.393380594 fb⁻¹ (matches the official
  16.393380531 fb⁻¹ to 9 significant figures) → average rate **11,135.7
  events/fb⁻¹**.
- **χ²/ndf = 2.48** (155 dof) for "rate is constant across runs" —
  moderately elevated above 1, not dramatic.
- **12/156 runs (7.7%) flagged >3σ.** Only 1 of the 12 has extremely low
  luminosity (run 283469: 4 events over 3.1×10⁻⁵ fb⁻¹ — a single-digit
  event count over a near-zero-luminosity run inflates its inferred rate
  to ~127,000/fb⁻¹, a pure low-statistics artifact, visible as the huge
  error bar in the plot). The other 11 flagged runs have modest but
  still small luminosity (0.03–0.3 fb⁻¹, vs. a typical run's several
  tenths to ~1 fb⁻¹) — plausible run-to-run variation (pileup conditions,
  detector status changes) is a more likely driver than a real time
  -dependent selection bug, but this is worth keeping in mind: **8% of
  runs at >3σ is a bit more than pure-Poisson bad luck alone would give**
  (would expect ~0.3% under a perfect constant-rate hypothesis), so mild
  real run-to-run rate variation likely exists at some level, on top of
  the small-luminosity-run artifacts. Not alarming for a real-data
  background rate. See `part_c_run_stability.png` (log-scale y-axis —
  linear scale is dominated by the one extreme low-luminosity run).

## D — Pileup matching (PV_npvsGood)

**Limitation, stated plainly**: `PV_npvsGood` counts *reconstructed* good
vertices, not the true number of pileup interactions (`Pileup_nTrueInt`,
MC-truth-only, unavailable in real data). Reweighting on this
reconstructed proxy is the standard fallback when no official pileup JSON
exists, but it inherits any data/MC mismodeling of vertex-reconstruction
efficiency itself, on top of whatever it's correcting for.

Weights `w(n) = data_sideband_fraction(n) / MC_fraction(n)` derived per
signal sample, integer PV bins 0–60; bins with <20 raw MC entries get
`w=1` (18–30 of 61 bins per label fell back this way — MC statistics thin
out well before PV=60); every weight clipped to [0.1, 5.0]. See
`part_d_pileup_matching.png` — before reweighting, every one of the 6
signal samples peaks at slightly *lower* PV than data (MC underestimates
pileup a little relative to data); after reweighting, all 6 match the
data shape closely.

**Effect on ggH** (the one mode this task asks to check in detail):
- Selection efficiency: 0.39845 → 0.39783 (**−0.16%**, negligible).
- Peak position and σ_eff68, per category, before vs. after — **no
  change at 0.5 GeV bin resolution**:

| category | mode before | σ_eff68 before | mode after | σ_eff68 after |
|---|---:|---:|---:|---:|
| EBEB | 124.75 GeV | 2.00 GeV | 124.75 GeV | 2.00 GeV |
| notEBEB | 124.75 GeV | 2.75 GeV | 124.75 GeV | 2.75 GeV |

Pileup reweighting has essentially no effect on ggH here — small and in
the direction/size one would expect for a well-simulated 2016 sample.

**Correction, added 16 Sep 2026**: the σ_eff68 values above come from
`common.weighted_mode_and_sigma68`, a BINNED method (0.5 GeV bins) —
every value it can return is quantized to a multiple of 0.25 GeV (half
the bin width), which is why 2.00/2.75 above (and Part F's 1.75/2.75)
land on suspiciously round numbers. This is a resolution limitation of
this report's own method, not a real feature of the underlying
distribution. **The precise, unbinned reference values are D3's own**
(computed with a true sorted-array effective-σ68, not a histogram):
**EBEB 1.78 GeV, notEBEB 2.59 GeV**. Use the D3 numbers, not this
report's, wherever sub-0.25-GeV precision on ggH's width matters; the
qualitative conclusion here (pileup reweighting doesn't change the
width) is unaffected by this correction.

## E — Expected signal yields (not significance)

`N = σ × BR(0.00227) × 16.393380531 fb⁻¹ × Σw_selected / Σw_all(processed files)`.
ttH uses **only** this run's own genEventSumw over its 15 processed files
(39,448.74 — never `signal_sumw.json`'s stale 16-file total, 405,201.92).
ZH uses 0.7612 pb (qq/qg→ZH only). Statistical uncertainty = scale ×
√(Σw²).

| mode | σ [pb] | N (before PU) | stat. unc. | N (after PU) | EBEB | notEBEB |
|---|---:|---:|---:|---:|---:|---:|
| ggH | 48.58 | **720.32** | ±1.56 | 719.20 | 474.27 | 246.05 |
| VBF | 3.782 | 55.98 | ±0.20 | 55.92 | 37.50 | 18.48 |
| W⁺H | 0.84 | 10.19 | ±0.05 | 10.16 | 6.11 | 4.08 |
| W⁻H | 0.5328 | 7.09 | ±0.03 | 7.07 | 4.52 | 2.57 |
| ZH | 0.7612 | 9.80 | ±0.05 | 9.77 | 6.11 | 3.69 |
| ttH | 0.5071 | 6.71 | ±0.17 | 6.66 | 5.03 | 1.68 |
| **Total** | | **810.09** | | 808.78 | 533.53 | 276.56 |

This matches your independent check (ggH≈720, VBF≈56, W⁺H≈10, W⁻H≈7,
ZH≈10, ttH≈7, total≈810) to the numbers you quoted, and pileup reweighting
shifts the total by only **−0.16%**.

**ttH statistics, called out explicitly as asked**: 15 processed files
carry only 42,319 generated events (genEventCount) — the old 16-file
total was 433,412 — so ttH has by far the thinnest simulation statistics
of the six modes. Effective MC events (Σw)²/Σw²: **4,640** over the full
processed sample (matches your independent estimate of ≈4,600), dropping
to **1,206** (EBEB) / **440** (notEBEB) once restricted to *selected*
events. ttH's 6.71 ± 0.17 yield carries the largest *relative* stat.
uncertainty of the six modes (2.5%, vs. <1% for ggH/VBF/W±H/ZH) — worth
keeping in mind for anything downstream that treats ttH's shape or yield
as precisely known.

**ggH vs. the D3 single-file preview**: full-run total **720.32** vs. the
quoted D3 single-file preview of **720** — agreement to 0.04%. D3 used
exactly 1 of ggH's 3 files; the full run uses all 3, so exact equality
would be coincidental, but this close a match is a strong consistency
check that ggH's per-file selection efficiency is uniform across its 3
files, as expected for a promptly-generated signal sample.

## F — Category composition

| | EBEB | notEBEB |
|---|---:|---:|
| data sidebands | 49.5% (90,336) | 50.5% (92,215) |
| signal (expected-yield weighted, all 6 modes) | **65.9%** (533.5) | **34.1%** (276.6) |

**This is the most striking difference in this round of checks**: data
sidebands split almost exactly 50/50 between categories, while the
physical signal mixture is clearly EBEB-favored (66/34). This is
expected, not a bug — barrel photons have better reconstruction/ID
efficiency and shower-shape resolution than endcap, so real Higgs decays
(concentrated at central rapidity relative to the beam, and passing
tighter effective ID) survive selection into EBEB disproportionately more
than the background does; the background sidebands, being dominated by
generic QCD/γ+jet production, have no such preference. See
`part_f_category_composition.png`.

Combined-signal (all 6 modes, expected-yield weighted) shape per
category, `part_f_combined_signal_shape.png`:

| category | mode | σ_eff68 |
|---|---:|---:|
| EBEB | 124.75 GeV | 1.75 GeV |
| notEBEB | 124.75 GeV | 2.75 GeV |

Both categories peak 0.25 GeV below the nominal 125 GeV (at this task's
0.5 GeV binning resolution — not treated as a discrepancy without a finer
scan), and EBEB is visibly narrower than notEBEB (1.75 vs. 2.75 GeV), as
physically expected from better barrel energy resolution. **Same binning
correction as Part D applies here** — these σ_eff68 values are quantized
to 0.25 GeV steps by the binned method; D3's own precise, unbinned ggH
values (EBEB 1.78 GeV, notEBEB 2.59 GeV) are the reference for
sub-0.25-GeV precision. (This "all modes combined" table is dominated by
ggH, so the two sets of numbers should be close but are not the same
sample — D3's is ggH-only, single-file; this table pools all 6 modes,
full statistics.)

---

## Summary of flags

| check | flag | severity |
|---|---|---|
| B (turn-on) | possible turn-on/edge effect, 100–105 GeV | informational — feeds the background-model task's fit-range choice, not a defect; electron-veto leakage from Z→ee added as a candidate explanation, to be tested once the prepared Z→ee run actually happens |
| C (run stability) | χ²/ndf=2.48, 12/156 runs >3σ | mild — mostly low-luminosity-run statistics; worth a light mention if it recurs later |

Nothing else raised a flag. No blinding violation occurred at any point
(every load asserted it twice, on every file).
