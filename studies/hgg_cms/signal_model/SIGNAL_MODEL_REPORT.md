# H→γγ signal model from simulation (statistical-analysis task 1)

Built entirely from the six signal simulation samples
(`signal_ggh.root`, `signal_vbf.root`, `signal_wplush.root`,
`signal_wminush.root`, `signal_zh.root`, `signal_tth.root` in
`C:\Users\matan\hgg_full_merged\`) and already-committed prior results
(pileup weights, cross sections, genEventSumw values). **No data file was
opened at any point** — `data_sidebands.root` is never read by any script
in this package, and no file with `BLINDED` in its name was opened.
No background model, S+B fit, or significance estimate is computed here
— those are later tasks.

Reproduce with:
```
python -m studies.hgg_cms.signal_model.build_signal_model
```
Writes `results/signal_model.json`, `results/plots/<category>_fit.png`,
and this report's numbers. Unit tests: `python -m pytest tests/test_signal_model.py`.

---

## Part 1 — Signal events and weights

Per-event weight = `genWeight × pileup_weight × (σ_mode × BR(H→γγ) × L / Σ genEventSumw_mode)`.
Pileup weights are **reused verbatim** from
`studies/hgg_cms/validation/results/part_d_pileup_weights.json` (the
already-derived, already-committed Part D weights) — not re-derived,
since re-deriving them needs the data-sideband `PV_npvsGood` distribution,
and this task is not permitted to open any data file. ZH uses 0.7612 pb
(qq/qg→ZH only, `signal_sumw_notes.md`); ttH uses only this run's own
15-file `genEventSumw` (never the stale 16-file total) — both identical
to `VALIDATION_REPORT_1.md` Part E's conventions.

**Reproduction check (Part 1.2):** every one of the six modes' before-PU
and after-PU inclusive yields reproduces `VALIDATION_REPORT_1.md` Part
E's own saved numbers to **better than 3×10⁻⁵ %** (max relative
difference across all six modes: 2.5×10⁻⁷), and the two grand totals
(810.09 before PU, 808.78 after PU) reproduce to floating-point
precision (~10⁻⁷–10⁻¹⁶ relative). The tiny residual differences are
floating-point summation-order noise, not a modeling discrepancy — well
inside the ≤0.1% threshold this check was held to.

**Effective simulated event counts** (Σw)²/Σw², selected events, per
mode and category:

| mode | EBEB | notEBEB |
|---|---:|---:|
| ggH | 140,137 | 72,120 |
| VBF | 51,639 | 25,917 |
| W⁺H | 29,029 | 18,999 |
| W⁻H | 30,749 | 17,074 |
| ZH | 29,508 | 17,354 |
| ttH | **1,206** | **440** |

ttH has by far the thinnest simulated statistics of the six modes in
both categories (same finding as `VALIDATION_REPORT_1.md` Part E) — its
contribution to the combined shape fit and yield carries the largest
relative statistical uncertainty, though its ~1% yield share (below)
means this has little effect on the combined result.

---

## Part 2 — Signal shape per category

**Pre-set model-selection rule** (stated before any fit was run): fit a
pure double-sided Crystal Ball (DCB) first; also fit DCB + an extra
Gaussian. Adopt the DCB+Gaussian mixture **only if** it improves the
binned χ² (0.25 GeV bins, 105–180 GeV, bins with model-predicted content
≥ 5) by more than 10 units **and** the pure-DCB fit has χ²/ndf > 1.5.
Otherwise keep the pure DCB.

**Fit method**: weighted unbinned maximum-likelihood (minimizing
`-Σ wᵢ ln f(mᵢ; θ)` via MIGRAD), fit over the full simulated range
(100–180 GeV — all events already satisfy this from selection) so the
DCB tails are best constrained; the 105–180 GeV / 0.25 GeV binning is
used only for the goodness-of-fit check, matching this task's own
instruction. **Uncertainty method for signed weights**: the sandwich
(robust) covariance `V = H⁻¹CH⁻¹`, with `H` the weighted Hessian and `C`
built from `Σ wᵢ² · (score vector)(score vector)ᵀ` — the general solution
to exactly the problem Langenbruch (arXiv:1911.01303, "Parameter
uncertainties in weighted unbinned maximum likelihood fits") studies and
validates. This project's `H`/`C` are computed independently here via
numerical differentiation of the analytic DCB/mixture log-density, not
copied from that paper's own code or matched to its exact equation
numbers — **UNVERIFIED at that level of precision**, though the general
method is the same. A bootstrap-of-events alternative was **not** used,
to avoid refitting the largest (~780,000-event EBEB) sample ~100+ times.

### Results

| category | model chosen | mode (GeV) | σ_eff68 (GeV) | χ²/ndf (n bins) |
|---|---|---:|---:|---|
| EBEB | **DCB** (Gaussian not added) | 124.815 | 1.770 | 72.3/20 = 3.62 (26 bins) |
| notEBEB | **DCB + Gaussian** | 124.768 | 2.608 | 20.0/14 = 1.43 (23 bins) |

**Why the Gaussian was added in notEBEB but not EBEB**, per the pre-set
rule: in EBEB, adding the Gaussian did not improve χ² at all (change of
−0.4, i.e. slightly *worse* after accounting for fewer degrees of
freedom) — the rule's first condition fails, so the pure DCB stands even
though its own χ²/ndf (3.62) exceeds 1.5. In notEBEB, the pure DCB's
χ²/ndf is 4.27 (> 1.5) **and** adding the Gaussian improves χ² by 56.8
units (≫ 10) — both conditions hold, so the mixture is adopted there.

**Validation against the independent D3 reference** (ggH-only, unbinned,
sorted-array σ_eff68 — `EBEB 1.78 GeV, notEBEB 2.59 GeV`, from
`VALIDATION_REPORT_1.md` Part D's correction note): this task's own
recomputation of that exact ggH-only unbinned number reproduces it
almost exactly (EBEB 1.7766, notEBEB 2.5940 — confirms this project's
data loading matches D3's). The **combined-signal model's own** σ_eff68
(fit to all six modes, expected-yield-weighted — dominated ~89% by ggH
in both categories) sits **0.56% (EBEB) and 0.68% (notEBEB)** from that
same D3 reference — comfortably inside the pre-set 3% band.

**How well the fit describes the simulation**: visually good in both
categories (see `results/plots/EBEB_fit.png` / `notEBEB_fit.png`,
log+linear+pull) — the model tracks the peak and both tails down to
the ~10⁻⁴-events/0.25 GeV level. Quantitatively, the χ²/ndf values above
(3.62 EBEB, 1.43 notEBEB) mean the EBEB fit is **not a formally good
fit** at the level a single analytic shape should achieve given the very
large effective MC statistics near the peak (order 10⁴–10⁵ effective
events per active bin) — small, few-percent-level residual shape
mismatch is statistically resolvable at that precision even though the
fit looks good by eye. This most likely reflects genuine sub-structure
from combining several production modes with slightly different
underlying widths under one shared shape (see the VBF check below) —
adding a second Gaussian did **not** resolve it in EBEB (the improvement
was negative), so no combination of these two functional families closes
that residual there. This is reported as an honest limitation, not
papered over; it does not by itself indicate a bug (the pull pattern is
a smooth few-σ wave near the peak, not a discontinuity or gross
mismodeling).

**Per-mode check (ggH alone, VBF alone) — VBF flag**:

| category | combined σ_eff68 | VBF-alone σ_eff68 | relative difference | flagged (>10%)? |
|---|---:|---:|---:|:---:|
| EBEB | 1.770 | 1.647 | 6.9% | No |
| notEBEB | 2.608 | 2.406 | 7.7% | No |

VBF's own diphoton-mass resolution is **narrower** than the combined
(ggH-dominated) shape in both categories, by a consistent 7–8% — below
the pre-set 10% flag threshold, so no separate VBF shape is split out,
but the pattern is consistent across both categories and worth noting:
plausibly related to VBF's distinct photon kinematics (different pT/η
population than ggH) correlating with a different mix of well- vs.
poorly-reconstructed photons, rather than a fit artifact (VBF has ample
effective statistics — 51,639/25,917 — so this is not a small-sample
fluctuation).

**Mass dependence (Part 2.5)**: only mH=125 GeV simulation exists, so
the shape at a hypothesized mH is built by rigidly translating the
*whole* fitted shape (every mean parameter, including the extra
Gaussian's own mean where present) by `mH − 125 GeV`, keeping every
width/tail/mixture parameter fixed. This reproduces the fitted mode
exactly at every mH tested (verified: shifted mode = fitted mode +
(mH−125) to <10⁻⁸ GeV at mH = 110–140 GeV). This is the standard
approach used when signal MC exists at only one mass point (e.g. CMS/ATLAS
diphoton analyses' own signal-model sections use this same
"mean floats with mH, other parameters fixed" convention) —
**UNVERIFIED against one specific citable equation number** in this
project's own check. **Limitation, quantified**: this neglects any
change in resolution with mH. Estimating the size from σ_eff/m (treating
σ_eff as if it scaled linearly with mH, which it does NOT here — this is
only a rough estimate of the neglected effect's scale): σ_eff68/125 ≈
1.4% (EBEB) / 2.1% (notEBEB); over the physically relevant 110–150 GeV
range that would correspond to at most a ±20% swing in mH relative to
125, i.e. a possible width mismodeling of very roughly 0.3–0.4% (EBEB)
/ 0.4–0.5% (notEBEB) of the total width at the extremes of that range —
small next to the ~5% energy-resolution systematic already carried in
Part 4, but not zero.

**Bin-integration functions (Part 2.6)**: `SignalShape.bin_probabilities(edges)`
returns exact CDF differences (not midpoint approximations) — verified
by unit test that the sum of fine (0.25 GeV) bins over 105–180 GeV
equals the shape's own analytic in-range fraction to machine precision
in both categories (0.9989 EBEB, 0.9985 notEBEB — the ~0.1–0.15% outside
[105,180] is the shape's own tail probability below 105 GeV, expected).

---

## Part 3 — Expected yields and corrections

Central yield = Σ over the six modes of normalized (genWeight × pileup)
weights inside **105–180 GeV** (this task's fit range).

| category | no corrections | with pileup | **with trigger SF (central)** | Z→ee-ratio alternative (info only) | fraction of total |
|---|---:|---:|---:|---:|---:|
| EBEB | 533.01 | 533.58 | **545.80** | 446.61 | 66.1% |
| notEBEB | 276.10 | 274.22 | **266.13** | 221.57 | 33.9% |
| **Total** | 809.11 | 807.80 | **811.93** | 668.17 | |

- **Trigger SF** (pre-set, applied): EBEB ×1.0229, notEBEB ×0.9705
  (`VALIDATION_REPORT_2.md` Part D). Pushes EBEB up, notEBEB down — net
  effect on the total is small (807.80 → 811.93, +0.5%) since the two
  categories' corrections partly cancel.
- **ID/reconstruction**: **no correction applied to the central yield**
  (no photon-ID scale factors exist in this open-data setup) — a ±20%
  normalization systematic is carried instead (Part 4). This mainly
  affects the *expected* significance and the interpretation of a fitted
  signal strength μ, **not** the significance actually observed in real
  data.
- **Z→ee-ratio alternative** (reported for information only, not
  adopted): scaling the central (with-pileup) yield by the Z→ee
  data/DY ratios instead of the trigger SF gives markedly lower yields
  (446.6 EBEB, 221.6 notEBEB) — a reminder that these ratios reflect
  *overall* data/DY mismodeling (of which the diphoton trigger is only
  one piece), not a trigger-only correction; they are not double-applied
  on top of the trigger SF anywhere in this task's central numbers.

---

## Part 4 — Systematic uncertainty table (signal)

| source | EBEB | notEBEB | type |
|---|---:|---:|---|
| Luminosity | 1.2% | 1.2% | normalization |
| Theory (production σ ⊕ BR) | 6.51% | 6.51% | normalization (μ interpretation only) |
| Trigger SF | 2.29% | 2.95% | normalization |
| ID/reconstruction | 20% | 20% | normalization (μ interpretation / expected significance) |
| Pileup — yield | 0.10% | 0.68% | normalization |
| Pileup — shape | ~0 (negligible) | ~0 (negligible) | shape |
| Photon energy scale | 0.1% (= 0.125 GeV at 125 GeV) | 0.1% (= 0.125 GeV) | shape (mean shift) |
| Photon energy resolution | 5% | 5% | shape (width) |
| Simulation statistics | 0.26% | 0.36% | normalization (statistical) |

**Largest uncertainties: ID/reconstruction (±20%) and theory (±6.5%)** —
both dominate over everything else by a wide margin, and both are
explicitly *normalization/interpretation* uncertainties (they affect how
a fitted μ is interpreted and the *expected* discovery/exclusion
sensitivity), not the statistical significance of whatever excess or
deficit is actually observed in real data. The photon energy-resolution
shape uncertainty (5%, a documented, doubled extrapolation from the
Z→ee electron measurement, not independently validated for photons) is
the largest *shape* systematic — larger than the mean-shift energy-scale
uncertainty by a factor of 50, consistent with the resolution channel
carrying inherently more electron-vs-photon extrapolation risk than a
simple peak-position shift.

**Sourcing detail**:
- Luminosity 1.2%: L. Sirunyan et al. (CMS), *Precision luminosity
  measurement in pp collisions at √s=13 TeV in 2015 and 2016 at CMS*,
  Eur. Phys. J. C 81 (2021) 800, **arXiv:2104.01927**.
- Theory: LHC Higgs Cross Section Working Group, *Handbook of LHC Higgs
  Cross Sections: 4. Deciphering the Nature of the Higgs Sector*,
  **arXiv:1610.07922** ("YR4"), 13 TeV / mH=125 GeV values from the
  LHCHXSWG twiki (per-mode scale+PDF, combined per mode then across
  modes weighted by each category's mode fractions — see
  `part4_systematics.py`'s own docstring for the exact numbers and the
  documented simplifications: symmetrized scale uncertainty, and
  assumed-uncorrelated combination across modes). ZH's fractional
  uncertainty is applied to the qq/qg-only 0.7612 pb cross section this
  project actually uses, not independently re-derived for the qq-only
  process alone — an approximation, flagged. BR(H→γγ) ≈ 3% relative,
  from the LHCHXSWG branching-ratio twiki — **UNVERIFIED to the exact
  tabulated decimal** (retrieved via a secondary web summary, not by
  opening the primary data table myself); treated as fully correlated
  across all six modes and combined in quadrature with the production
  uncertainty.
- Trigger SF / ID-reco / pileup / energy-scale / energy-resolution: all
  from this project's own prior validation reports
  (`VALIDATION_REPORT_2.md` Parts B, C, D and `VALIDATION_REPORT_1.md`
  Part D) or derived directly here from the loaded samples (pileup
  effect, simulation statistics) — see `part4_systematics.py`'s module
  docstring for the exact formulas.

---

## Part 0 — Leakage-shape correction and template export (recorded in VALIDATION_REPORT_2.md)

Handled directly in `VALIDATION_REPORT_2.md` Part E (dated 17 Sep 2026
update): the single exponential fitted to the four leakage windows is
confirmed to be a poor description (steep-only extrapolation ≈730 events
in 115–135 GeV vs. the single-exponential's ≈1,790 — a factor ~2.5
bracket, not a precise number). A new script,
`studies/hgg_cms/validation/zee/hgg_leakage_mass_template.py`, is ready
to export the actual fine-binned (1 GeV) leakage mass template from the
same already-parsed DY chunks — see the final chat message for the exact
cluster command (not run as part of this task).

---

## Files

- `loader.py` — Part 1 (event loading, weights, yield reproduction, effective counts).
- `shapes.py` — DCB / DCB+Gaussian analytic PDF/CDF, mode, σ_eff68, mass-shift.
- `fit.py` — weighted unbinned ML fit, sandwich covariance, binned χ², Gaussian decision rule.
- `part2_shape.py`, `part3_yields.py`, `part4_systematics.py` — Parts 2–4 drivers.
- `plots.py` — fit-validation plots.
- `build_signal_model.py` — top-level orchestrator (`results/signal_model.json` + plots).
- `../../../tests/test_signal_model.py` — unit tests (shape evaluation, bin integration, mass shifting, yield-reproduction arithmetic).
