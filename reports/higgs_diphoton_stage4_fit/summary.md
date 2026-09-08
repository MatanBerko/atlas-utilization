# H -> gamma gamma, Stage 4: signal-plus-background fit

Branch: `analysis/higgs-diphoton-stage4-fit`, off
`analysis/higgs-diphoton-stage3-resolution` (`e05b375`). Works entirely from
Stage 3's existing 1 GeV, 80-bin, 100-180 GeV BumpNet histogram
(`reports/higgs_diphoton_stage3_resolution/histograms/diphoton_stage3_1gev_bumpnet.root`,
254,173 entries) — **no re-download, no re-parse**, confirmed present before
starting. Does not use BumpNet (absent from this machine, out of scope).
Script: `scripts/higgs_diphoton_stage4_fit.py`, extends Stage 3's report
script's loading conventions rather than rewriting from scratch.

## A real bug caught before trusting any number here

The first version of the fit code got the signal yield stuck at its exact
starting value (1.0) regardless of the data — the optimizer never moved it.
Diagnosed directly (not guessed): the raw Poisson NLL's absolute magnitude
scales with the total event count (~10⁶ here), completely swamping the
O(1) sensitivity of the likelihood to the signal yield in floating point.
**Fixed** by switching to the standard Poisson-deviance form of the NLL
(subtracting the saturated-model reference per bin) — mathematically
identical for every likelihood-ratio computation in this script (it only
subtracts a data-only, parameter-independent constant), but keeps the
objective at a numerically sane O(1-100) scale.

That fix alone wasn't sufficient: the *background* parameter gradients
(particularly the poly4 leading coefficient, which multiplies m⁴ ~ 10⁸)
were still ~8 orders of magnitude larger than the signal yield's gradient,
so the same optimizer would move the background freely while leaving yield
frozen. **Fixed** by rescaling mass to x=(m-140)/40 for the poly4 and
exp_poly2 background models (power law was left on raw mass — log(m) is
already well-conditioned over this range).

Both fixes were verified with synthetic data before trusting any real
result: a pure-background histogram correctly returns yield≈0 (no
manufactured signal), and a large (3,000-event) injected Gaussian signal at
125 GeV, sigma=1.5 GeV is recovered correctly (yield 2,697-3,485 depending
on background model, fitted mass 125.00-125.02 GeV, significance 19-26
sigma) across all three background forms.

## Methodology

- **Binned Poisson maximum-likelihood fits** (not chi²-least-squares),
  standard for histograms at this scale. Model per bin = density evaluated
  at the bin center × 1 GeV bin width (same convention Stage 3's own
  polynomial fit used).
- **Signal model**: Gaussian, width **fixed** at 1.5 GeV (see F4 below),
  mean floating but bounded to [118, 132] GeV so the fit cannot wander to
  the range edges and become degenerate with the background.
- **Significance**: Z = sqrt(2×(NLL_bkg-only − NLL_signal+bkg)), the
  standard 1-degree-of-freedom asymptotic likelihood-ratio significance for
  the signal-strength parameter (mass and background parameters are
  profiled as nuisance parameters) — the same convention ATLAS/CMS call
  "local significance." **Explicitly LOCAL, not corrected for the
  look-elsewhere effect** — see F5.
- **chi²/ndf** (goodness of fit, F3) uses the standard Pearson statistic on
  the background-only fit, ndf = n_bins − n_background_params.

## F2: fit range sensitivity — tested, and it matters a lot

Three ranges tested: 100-180 GeV (Stage 3's original choice, known edge
artifact), 105-180 GeV, 110-180 GeV (both start above the low-mass turn-on
Stage 3 flagged). All three are exact sub-selections of the same 80×1 GeV
bins — no rebinning, no recomputation.

**chi²/ndf, all three background forms:**

| Range | poly4 | exp_poly2 | power_law |
|---|---:|---:|---:|
| 100-180 | 2.82 | 2.30 | 2.27 |
| 105-180 | **1.03** | **0.99** | **1.03** |
| 110-180 | **0.87** | **0.93** | **0.98** |

**The 100-180 GeV range fits poorly for every background form (chi²/ndf
2.3-2.8)** — confirming Stage 3's own observation of edge artifacts (the
positive spike at the very first bin and the negative dip around 107-113
GeV are visible directly in `plots/diphoton_stage4_fit_100_180.png`'s
residual panel). **Once the range starts at 105 or 110 GeV, every
background form fits close to ideally (chi²/ndf ≈ 0.87-1.03)** — a real,
substantial improvement, not a marginal one.

**The fitted signal result is highly sensitive to this choice** — see F5's
table below. This instability is itself an important, reported finding:
the apparent excess seen at 100-180 GeV with the poly4 background is not
robust to a reasonable, well-motivated change of fit range.

## F3: background functional forms — compared, and the spread is real

Three forms fit at each range: 4th-order polynomial (5 free parameters,
Stage 3's own choice), exp(a+bm+cm²) (3 params), power law N·m⁻ᵏ (2 params).

**At 100-180 GeV, the three forms disagree dramatically** (see the
`plots/diphoton_stage4_variation_summary.png` bar charts): poly4 gives a
yield of 701±140 (4.46σ); exp_poly2 gives 251±124 (1.81σ, and its fitted
mean hit the *upper edge* of the allowed [118,132] window at exactly 132.0
— a sign this particular fit does not have a genuine interior optimum near
125 GeV and should be treated with extra caution); power_law gives
essentially **zero** (1.0±139, 0.13σ). All three are nominally fitting the
*same data*, over the *same range* — this spread by itself demonstrates
that whichever number one might quote from the 100-180 range depends
heavily on an essentially arbitrary choice of background parametrization,
not on a robust feature of the data.

**At 105-180 and 110-180 GeV, the three forms agree much better with each
other** (yields 23-210 and 37-187 respectively, all with large,
overlapping uncertainties, all well under 2σ) — consistent with each other
and with a small or absent excess once the badly-fit edge region is
removed.

**This spread across background choices is reported as a real systematic
uncertainty on the signal yield, not resolved by picking whichever form
gives the largest or most convincing-looking number.**

## F4: the signal model — width fixed, and here's proof why that matters

Width fixed at **1.5 GeV** — the middle of CMS's quoted ~1-2 GeV diphoton
mass resolution at m=125 GeV for an inclusive selection. This project's own
selection has no photon energy-scale/resolution corrections and no
per-category splitting (explicitly out of scope, see below), so the true
achieved resolution here could differ from CMS's own tuned value in either
direction; 1.5 GeV is a reasonable, literature-anchored midpoint, not a
value tuned to this histogram.

**A free-width variant was also run, and it demonstrates exactly the
failure mode this instruction warned about, in two different directions
depending on range:**

| Range | Fixed-width (1.5 GeV) significance | Free-width fitted sigma | Free-width significance |
|---|---:|---:|---:|
| 100-180 (poly4) | 4.46σ | **5.18 GeV** (inflated ~3.5x) | **6.25σ** |
| 105-180 (poly4) | 1.72σ | **0.56 GeV** (shrunk to <1/2) | 2.57σ |
| 110-180 (poly4) | 1.47σ | **0.49 GeV** (shrunk to <1/3) | 2.28σ |

At 100-180, the free width inflates to 5.18 GeV — over 3x the physical
resolution — clearly absorbing the same edge mismodeling that inflates the
poly4 yield there, and the significance climbs further (6.25σ) as a direct
result. At 105-180 and 110-180, the free width does the *opposite* —
shrinking to less than half the physical resolution, fitting a narrow
statistical fluctuation rather than a physically broad signal, again
inflating the significance relative to the physically-constrained fit
(1.72→2.57σ, 1.47→2.28σ). **In every case tested, letting the width float
increased the apparent significance relative to the physically-constrained
fit** — direct, concrete confirmation that a free width manufactures a
larger apparent signal here, in both possible directions (too wide to eat
background structure, or too narrow to chase a fluctuation), and is not
used as the primary result for exactly this reason.

## F5: significance — full grid, and what "local" means here

**Local significance (1-dof asymptotic LRT, profiling mass and background
parameters), all 9 range × background-form combinations:**

| Range | poly4 | exp_poly2 | power_law |
|---|---:|---:|---:|
| 100-180 | **4.46σ** | 1.81σ | 0.13σ |
| 105-180 | 1.72σ | 0.53σ | 0.91σ |
| 110-180 | 1.47σ | 1.28σ | 0.84σ |

**This is LOCAL significance at whatever mass the fit landed on (fitted
mean ranged 121.9-133.0 GeV across the 9 combinations, mostly clustering
near 122-126 GeV) — NOT a global significance corrected for the
look-elsewhere effect.** Two distinct look-elsewhere considerations apply
here and neither is corrected for:

1. **The mass was allowed to float** within the fit (not fixed a priori at
   exactly 125.0 GeV), which is itself a form of scanning — a rigorous
   global significance would apply a trials-factor correction for this
   (e.g. the Gross-Vitells formula or toy-MC calibration), which this
   script does **not** compute. The local numbers above are therefore an
   overestimate of what a mass-scan-corrected global significance would be.
2. **We deliberately tried 3 fit ranges and 3 background forms** (9
   combinations) and are reporting the highest of them (4.46σ) alongside
   the rest — presenting only that one number without the other 8 would
   itself be an uncorrected multiple-comparisons problem. Reporting the
   full grid, as done here, is the honest mitigation for that, though it is
   not a formal statistical correction either.

**Bottom line on significance: every number in the table above should be
read as an upper bound on what a properly look-elsewhere-corrected,
systematics-included analysis would report, not as a final answer.**

## F6: plots

- `plots/diphoton_stage4_fit_100_180.png` — 2-panel fit, poly4 background,
  100-180 GeV (Stage 3's original range). Residual panel visibly shows the
  known edge artifacts (spike at the first bin, dip at 107-113 GeV)
  alongside the fitted Gaussian bump near 125 GeV.
- `plots/diphoton_stage4_fit_105_180.png` — same style, 105-180 GeV (edge
  excluded). Residuals are visibly cleaner; the fitted bump is smaller.
- `plots/diphoton_stage4_variation_summary.png` — fitted yield (with
  uncertainty) and local significance across all 9 range × background-form
  combinations, side by side. No third (significance-curve) panel on
  either fit plot — BumpNet inference is out of scope; local significance
  is reported numerically here, not plotted as a curve.

## F7: honest reporting

**No tuning was performed to increase significance.** The fit range,
binning (inherited from Stage 3, not re-optimized), background functional
forms, and signal width were all chosen for physical/methodological
reasons stated above (or, for fit range, explicitly scanned and all 3
results reported), not selected after seeing which gave the largest
number. The free-width variant — which *does* give a higher significance
at 100-180 GeV (6.25σ) than any fixed-width result — is explicitly flagged
as not physically justified (an inflated width absorbing background
mismodeling) and is not adopted as the reported result anywhere in this
document, exactly per instruction.

**What a real CMS H->gamma gamma analysis does that this exercise does
not:**
- **Photon energy-scale and resolution corrections** (data/MC scale
  factors, per-run/per-category calibration) — not implemented. Our
  claimed 1.5 GeV width is a literature-anchored assumption, not a
  measured value from this selection.
- **Per-category splitting** (barrel/endcap, converted/unconverted photons,
  R9-based categories) — not implemented; a real analysis fits each
  category separately (each with its own resolution and background shape)
  and combines them, which meaningfully improves sensitivity over a single
  inclusive fit like this one.
- **A multivariate photon ID** (CMS uses a BDT-based ID, not a simple
  cut-based working point) — this exercise uses the cut-based `cutBased`
  working points established in Stage 1/3.
- **A full treatment of systematic uncertainties** (photon energy scale,
  resolution, ID/isolation efficiency, luminosity, background-model choice
  treated as a nuisance parameter within the fit rather than a post-hoc
  spread) — **not implemented.** Every uncertainty quoted in this report
  (the `yield_err` values) is **statistical only**, from the local
  curvature of the likelihood. The background-function spread (F3) and
  fit-range spread (F2) are reported as informal indicators of systematic
  instability, not as a formal systematic uncertainty with its own
  statistical treatment.

**Given all of the above, any significance number in this report is an
upper bound on what a rigorous analysis would report** — real systematics
and a genuine look-elsewhere correction can only reduce a claimed
significance relative to the local, statistics-only numbers quoted here,
never increase it.

**No result in this report is described as a discovery or rediscovery of
the Higgs boson**, regardless of the number obtained, per instruction.

## Bottom line

Using Stage 3's original range and background choice (100-180 GeV, 4th-order
polynomial), the fit finds a signal-like excess near 125 GeV with a local
significance of 4.46σ. **This result is not robust**: it drops to under 2σ
for either of the two alternative background functional forms tested at
the same range (1.81σ, 0.13σ), and it drops to under 2σ for the poly4
background itself once the fit range is narrowed to exclude Stage 3's
already-known edge-modeling problem (1.72σ at 105-180, 1.47σ at 110-180) —
ranges where every background form now fits the data well (chi²/ndf ≈
0.87-1.03, versus 2.3-2.8 at 100-180). The one case that gives the largest
number (100-180, poly4) is also the range with the worst background
goodness-of-fit and coincides with the same known edge artifact Stage 3
already flagged as a modeling problem, not a physics feature — a strong
reason for skepticism about that specific number rather than confidence in
it. A free-width check, run purely as a cross-check per instruction and
explicitly not adopted as the result, further shows the width parameter
moving in physically implausible directions (inflating 3.5x at the
problematic range, shrinking to under half the assumed resolution at the
cleaner ranges) whenever it is allowed to float, always increasing the
apparent significance when it does — direct evidence that a free width
would have overstated this result at every range tested.

**Given a deliberately simplified selection (no energy-scale corrections,
no category splitting, cut-based rather than multivariate photon ID) and a
statistics-only uncertainty with no look-elsewhere correction, the honest
reading of this exercise is: a modest, range- and background-model-
dependent excess is seen near 125 GeV, most prominently in the fit-range
choice with the worst-fitting background, and consistent with a much
smaller or negligible excess once fit-range robustness is checked. This is
not evidence of a discovery, is not inconsistent with there being no real
signal in this deliberately simplified selection, and any number quoted
here should be treated as an upper bound on what a rigorous analysis with
full systematics and a proper look-elsewhere correction would report.**
