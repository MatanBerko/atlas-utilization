# Bias-study diagnosis (why no test function passed)

**Diagnosis only.** Nothing here changes the 0.20×σ_S criterion, the
5% fit-reliability rule, or any other pre-set decision; no background
function is chosen; nothing was rerun on the cluster (Part 5's "local
sample" reruns are 50-toy runs on this laptop, using the exact same
already-fitted truth curves and warm starts as the real cluster jobs —
see that section). Blinding is unaffected: everything here is built
from sideband-fitted truth curves, synthetic Poisson toys, and the DY
leakage simulation — no signal-region data anywhere.

Input: `results/bias_study_105_180.json` (the merged 120-subjob cluster
result, `merge_bias_results.py` at commit 9683a1f, copied here from
`C:\Users\matan\hgg_bias_merged\` for reproducibility — **no test
function is eligible-and-passing in either category**, matching what
was reported). Reproduce Parts 1–4 with:
```
python -m studies.hgg_cms.background_model.diagnostics.run_diagnosis
```
Part 5's local reruns are a separate, explicit step (see that section).

---

## Part 1 — Which cells drive each function's worst ratio, and what dominates

For every test function, 60 cells (4 truth families × 3 leakage
variants × 5 masses) were ranked by ratio, and grouped three ways
(mean ratio by leakage variant / by truth family / by mass) to see
which dimension has the largest **spread** — the dimension with the
biggest spread is the one most associated with driving failures.
Heatmaps: `results/plots/bias_diagnosis/<category>_<function>_heatmap.png`
(truth family × leakage variant, one panel per mass; `*` marks a cell
excluded on fit-reliability grounds).

| category | function | eligible | worst ratio | dominant dimension |
|---|---|:---:|---:|---|
| EBEB | bernstein_4 | yes | 0.841 | **mass** |
| EBEB | bernstein_5 | yes | 0.304 | mass (small spread — see Part 2) |
| EBEB | expsum_2 | **no** | 0.876 | truth_family |
| EBEB | expsum_3 | yes | 0.827 | **truth_family** |
| EBEB | laurent_2 | yes | 1.231 | **truth_family** |
| EBEB | laurent_3 | **no** | 0.964 | *(0/60 reliable cells — see below)* |
| EBEB | powersum_1 | yes | 1.368 | **truth_family** |
| EBEB | powersum_2 | **no** | 1.065 | *(0/60 reliable cells — see below)* |
| notEBEB | bernstein_5 | yes | 0.925 | **truth_family** |
| notEBEB | bernstein_6 | yes | 0.493 | **truth_family** |
| notEBEB | expsum_2 | **no** | 1.367 | truth_family |
| notEBEB | expsum_3 | **no** | 1.439 | *(0/60 reliable cells)* |
| notEBEB | laurent_3 | **no** | 2.260 | truth_family |
| notEBEB | laurent_4 | **no** | 1.458 | *(0/60 reliable cells)* |
| notEBEB | powersum_2 | **no** | 0.871 | truth_family |
| notEBEB | powersum_3 | **no** | 0.892 | *(0/60 reliable cells)* |

**(a) leakage_plus/minus is NOT the main driver anywhere.** Across
every function, the spread in mean ratio between the three leakage
variants is small (typically 0.02–0.17) — far smaller than the
truth-family or mass spreads. The ±50% leakage systematic is a real,
non-zero contributor at the margin, but it is not what is failing these
functions.

**(b) A specific truth family — almost always Bernstein — is the main
driver, for every non-Bernstein test function.** This is the clearest
and most consistent pattern in the whole study. Example, EBEB
`expsum_2` (eligible, so the full 60-cell breakdown is meaningful): mean
ratio when the TRUTH is Bernstein = **0.624**; mean ratio when the truth
is expsum itself = **0.039**. Same pattern in `powersum_1` (Bernstein
truth 0.791 vs. powersum truth 0.098) and `laurent_2` (Bernstein truth
0.651 vs. laurent truth 0.120). **A test function fits its own family's
truth almost perfectly (same functional form) but cannot correctly
absorb Bernstein's curvature** — visible directly in the heatmaps (e.g.
`EBEB_laurent_3_heatmap.png`: the "bernstein" truth row is uniformly the
worst across every mass, reaching ratio 0.94–0.96 at 135 GeV while every
other truth row stays under ~0.3 at the same mass). This is the classic
"wrong functional form" bias mechanism (the same one
`studies/lr_toys/REPORT.md` T5 demonstrated with a too-simple
exponential).

**(c) For Bernstein test functions, mass matters more than truth family
— and specifically the 115 GeV edge.** `bernstein_4` (EBEB): mean ratio
at m=115 is 0.531 vs. 0.069 at m=125 — the edge mass closest to the
sideband boundary is the hardest point on the scan, as hypothesized.
`bernstein_5` shows the same direction (115 GeV worst at 0.123, 135 GeV
best at 0.036) but the absolute spread shrinks to 0.087 — a much milder
effect once the function has one more order of freedom.

**(d) The 5 functions with ZERO reliable cells out of 60** (EBEB
laurent_3, powersum_2; notEBEB expsum_3, laurent_4, powersum_3) have no
meaningful "dominant dimension" from this grouping at all — filtering to
`reliability_ok` cells leaves nothing to group. Their failure mode is
not really about which truth/mass is hardest; see Part 5, which shows
it is a near-universal fit-convergence problem for these functions,
essentially unrelated to which cell is being tested.

---

## Part 2 — Is this statistical noise, or real?

**Method**: under the null "the true |S|/σ_S ratio is exactly 0.20 in
every one of the 60 cells," each cell's ratio is modeled as
`|0.20 + N(0, se_ratio_cell)|` using that cell's own observed
`se_ratio` (already computed per cell — `se_mean_S / mean_sigma_S`).
200,000 Monte Carlo draws of the 60-cell grid; the p-value is the
fraction of simulated "max over 60 cells" values reaching the function's
actual observed worst ratio.

| category | function | observed worst | null mean(max) | null 95th pct | null 99th pct | **p-value** | cells exceeding 0.20 by >2 s.e. |
|---|---|---:|---:|---:|---:|---:|---:|
| EBEB | bernstein_4 | 0.841 | 0.329 | 0.377 | 0.404 | **<10⁻⁵** | 34 |
| **EBEB** | **bernstein_5** | **0.304** | 0.329 | 0.378 | 0.404 | **0.831** | **0** |
| EBEB | expsum_3 | 0.827 | 0.334 | 0.384 | 0.412 | <10⁻⁵ | 12 |
| EBEB | laurent_2 | 1.231 | 0.331 | 0.380 | 0.406 | <10⁻⁵ | 25 |
| EBEB | powersum_1 | 1.368 | 0.330 | 0.380 | 0.407 | <10⁻⁵ | 30 |
| **notEBEB** | **bernstein_5** | **0.925** | 0.330 | 0.379 | 0.406 | **<10⁻⁵** | **14** |
| **notEBEB** | **bernstein_6** | **0.493** | 0.330 | 0.379 | 0.406 | **3×10⁻⁵** | **8** |

**Requested answer, `bernstein_5` (EBEB) vs. `bernstein_6` (notEBEB)**:
these two behave completely differently. **`bernstein_5`'s failure in
EBEB is consistent with pure noise** — its observed worst ratio (0.304)
sits BELOW the null distribution's own mean (0.329), p=0.83, and not a
single one of its 60 cells exceeds 0.20 by more than 2 standard errors.
Under the pre-set (unrelaxed) 0.20 rule it still formally fails, but the
evidence does not distinguish it from a function whose TRUE bias is
already at or below threshold everywhere. **`bernstein_6`'s failure in
notEBEB is a real effect, not noise** — p=3×10⁻⁵, with 8 cells exceeding
threshold by more than 2 standard errors, and the null distribution's
own 99th percentile (0.406) is well below the observed 0.493. Every
other function in both categories is overwhelmingly significant
(p<10⁻⁵), consistent with Part 1's finding that most of them are failing
on genuine cross-family mismatch, not noise.

---

## Part 3 — Sign and size in events, for the best functions

Expected signal yield: EBEB 545.8, notEBEB 266.1 events (from
`signal_model.json`, trigger-SF-corrected central value).

**EBEB, `bernstein_5`** — worst cells are modest relative to the signal:

| truth | leakage | mass | mean S | σ_S | ratio | **% of expected signal** |
|---|---|---:|---:|---:|---:|---:|
| laurent | leak+ | 115 | −53.3 | 175.4 | 0.30 | **−9.8%** |
| laurent | nominal | 115 | −41.5 | 175.0 | 0.24 | −7.6% |
| expsum | leak+ | 115 | −31.0 | 175.2 | 0.18 | −5.7% |
| expsum | leak− | 125 | +30.0 | 133.9 | 0.22 | +5.5% |

**notEBEB, `bernstein_6`** — worst cells are large relative to the
signal, and driven consistently by one truth family (powersum) with a
sign that flips across the mass scan:

| truth | leakage | mass | mean S | σ_S | ratio | **% of expected signal** |
|---|---|---:|---:|---:|---:|---:|
| powersum | nominal | 120 | +109.3 | 221.7 | 0.49 | **+41.1%** |
| powersum | leak− | 120 | +107.1 | 220.5 | 0.49 | +40.3% |
| powersum | leak+ | 120 | +82.0 | 222.9 | 0.37 | +30.8% |
| powersum | leak− | 125 | +63.9 | 194.7 | 0.33 | +24.0% |
| powersum | leak+ | 135 | −58.2 | 157.9 | 0.37 | −21.9% |
| powersum | nominal | 135 | −53.7 | 157.2 | 0.34 | −20.2% |

**This is the single most important number in this diagnosis**:
`bernstein_6`'s worst-case fake signal in notEBEB is not just
statistically significant (Part 2) — it is over **40% the size of the
entire expected Higgs signal** in that category, with a sign that
flips from positive (m=120–125) to negative (m=135) as the scanned mass
crosses the powersum-truth shape's own curvature mismatch. A systematic
this size would materially distort a real measurement, not just pad an
uncertainty band. EBEB's worst case, by contrast, tops out under 10% of
its expected signal.

---

## Part 4 — Truth-model spread vs. the signal peak

`results/plots/bias_diagnosis/<category>_truth_spread.png`: all 4
truth families (nominal, ±0.5×leakage shaded) over 105–180 GeV, and a
zoom into 115–135 GeV comparing the truth families' own disagreement to
the expected signal density.

| category | max truth-family spread inside 115–135 (events/GeV) | signal peak density (events/GeV) | **spread ÷ signal peak** |
|---|---:|---:|---:|
| EBEB | 23.1 | 134.6 | **0.17** |
| notEBEB | 45.6 | 42.6 | **1.07** |

**EBEB: the truth families agree with each other well inside the
blinded window** — their maximum disagreement is only ~17% of the
signal peak's own height, because EBEB's signal is narrow and tall
(σ_eff≈1.8 GeV) against a comparatively flat, well-constrained
background. **notEBEB: the truth families' own disagreement with each
other EXCEEDS the entire signal peak** (ratio 1.07) — literally, if you
don't know which functional family is "true," the resulting uncertainty
on the background under the peak is at least as large as the peak
itself. This is the direct explanation for Part 1(b)/Part 3's findings:
notEBEB's signal is wider (σ_eff≈2.6 GeV, spread over more bins) sitting
on a background whose different plausible functional descriptions
genuinely diverge from each other by a comparable amount — there is no
"almost right" answer to converge toward the way there is in EBEB.

---

## Part 5 — Characterizing the highest-failure cells

**Method**: for one representative worst cell per targeted function
(the cell with the single highest fail_fraction in the real 120-job
result), reran 50 toys locally with a fixed seed (20260918800),
capturing MIGRAD's own convergence diagnostics
(`is_above_max_edm`, `has_parameters_at_limit`, `hesse_failed`) and the
fitted background parameters' correlation matrix — not just
pass/fail. Full per-toy records:
`results/bias_diagnosis_part5_local_reruns.json`.

| cell (category / test function) | targeted (truth, leakage, mass) | local fail fraction (50 toys) | dominant failure mode | mean / max \|correlation\| among background params |
|---|---|---:|---|---:|
| EBEB / powersum_2 | bernstein, leak+, m=125 | 58% | **S+B fit not at EDM target (27/29 failures)** | 0.98 / **1.000** |
| EBEB / laurent_3 | laurent, leak−, m=120 | 36% | **S+B fit not at EDM target (18/18)** | 0.96 / 1.000 |
| notEBEB / powersum_3 | laurent, nominal, m=135 | 66% (33/50 failed) | S+B EDM 13/33, bkg EDM 1/33, bkg-at-bound 2/33, bkg Hesse 1/33 (not mutually exclusive; remainder failed some other way not separately flagged) | 0.82 / 0.999 |
| notEBEB / laurent_4 | laurent, leak−, m=130 | 22% (11/50 failed) | **S+B fit not at EDM target (11/11)** | 0.90 / 0.990 |
| notEBEB / expsum_3 | bernstein, leak+, m=125 | 52% (26/50 failed) | S+B fit not at EDM target (19/26; remainder failed some other way not separately flagged) | 0.97 / 1.000 |

Reproduced local fail fractions land in the same broad range as the
real cluster run's own numbers for these exact cells, confirming this
is a real, reproducible effect and not a fluke of the 120-job run — but
the agreement is not perfect, and is reported precisely rather than
rounded to "matches": comparing each local fraction to the cluster's
own (binomial standard errors combined in quadrature), EBEB powersum_2
agrees almost exactly (58.0% vs. 58.1%, −0.01σ); notEBEB powersum_3 and
laurent_4 agree within ~1–1.5σ (66% vs. 72.3%, −0.88σ; 22% vs. 31.3%,
−1.44σ); EBEB laurent_3 and notEBEB expsum_3 run noticeably higher
locally than on the cluster (36% vs. 19.7%, +2.27σ; 52% vs. 37.3%,
+2.03σ) — a ~2σ gap, larger than pure binomial noise alone comfortably
explains at only 50 local toys, though not so large as to suggest a
different failure mechanism (the diagnostic signature — EDM-not-reached,
near-unity background-parameter correlation — is consistent across all
five cells regardless of this gap). Plausible, unconfirmed explanations
for the gap: 50 toys is a small sample for a fail-rate this noisy, or a
seed-path difference between this diagnostic script and the real
per-job cluster invocation changes which specific fluctuations get
tested. Not investigated further here, since this section's purpose is
characterizing the FAILURE MODE, not exactly reproducing the fail rate.

**Answer to "what kind of failure"**: overwhelmingly **`is_above_max_edm`
on the signal+background fit specifically** — MIGRAD converges (finds a
point better than or equal to the background-only start, so the NLL
invariant held in literally all 250 diagnostic toys, zero violations)
but cannot drive its estimated-distance-to-minimum below the precision
threshold. Parameter-at-limit and Hesse failures are rare side effects,
not the main story.

**Answer to "is it a parameterization problem"**: **yes, clearly.**
Every single targeted cell shows a MAXIMUM pairwise correlation between
background parameters of 0.99–1.00, and a MEAN of 0.82–0.98. A
correlation this close to ±1 means two (or more) parameters are nearly
redundant — the likelihood surface has a long, narrow, nearly-flat
valley instead of a clean minimum, which is exactly the condition that
makes an EDM-based stopping criterion struggle regardless of how good
the starting point is. This is the same family of problem the
`studies/atlas_hgg_repro/REPORT.md` "Corrections" section already
documented for a different background model (a plain power-series
Bernstein basis vs. an orthogonal Legendre basis) — there, switching
basis (not starting values) fixed a near-identical MIGRAD pathology.
**Better starting values alone would likely help only marginally**
(these fits already warm-start from the background-only fit's own
converged point); **reparameterizing the amplitude/exponent basis
(e.g. an orthogonal or log-amplitude parameterization for
exponential-sum and power-law-sum, analogous to the Legendre-basis fix
already used elsewhere in this project) is the more promising fix**,
though this diagnosis does not implement or test that fix — it only
identifies it as the well-evidenced next thing to try.

---

## Part 6 — What the evidence favours (no rule changed here)

**(A) Discrete profiling / envelope method** (CMS, P. Dauncey et al.,
JINST 10 (2015) P04015, arXiv:1408.6865): profile over multiple PASSING
candidate functions as a discrete nuisance parameter, letting the fit
itself pick (per toy/per dataset) whichever function in the envelope
best describes that particular fluctuation. **Cost/benefit given this
evidence**: an envelope is only as good as its members — right now,
essentially only Bernstein orders are viable at all (every other family
either fails hard on truth-family mismatch or is unreliable outright),
so an envelope built from today's candidates would be dominated by
Bernstein anyway, gaining little over just using Bernstein directly.
Real cost: added machinery (a discrete nuisance parameter profiled at
every fit), and CMS's own experience is this typically costs only a
small, well-controlled amount of expected sensitivity (a fraction of a
percent to a few percent, order-of-magnitude, from the extra profiled
freedom) — but it is not worth the added complexity until there is more
than one genuinely viable family to choose from.

**(B) Higher-order Bernstein (EBEB 6–7, notEBEB 7)**: **the evidence
most directly favours this.** Going from Bernstein order 4→5 in EBEB
took the worst ratio from 0.841 (massively significant failure) to
0.304 (statistically indistinguishable from noise around the
threshold) — a dramatic, monotonic improvement from one extra order.
notEBEB order 5→6 shows the same direction (0.925→0.493) though it
hasn't yet crossed into "noise-consistent" the way EBEB has. Pushing one
more order in each category is a small, well-motivated, and (per the
Part 3 fail-reliability pattern, which is essentially clean for every
Bernstein order tried so far) likely CHEAP extension to rerun through
the identical bias machinery. Estimated cost to expected sensitivity:
modest — one additional free background parameter in a fit already
backed by >45,000 sideband events per category typically costs a small
fraction of a percent in σ_S, not a structural loss (unlike the
non-Bernstein families, which are failing for reasons — cross-family
mismatch, near-singular parameterization — that more sideband
statistics would not fix).

**(C) Keep a function, assign spurious signal as a systematic**:
mechanically always possible, but the COST is asymmetric between
categories given Part 2/3's findings. For EBEB with `bernstein_5`,
since the excess over threshold is noise-consistent, adding its
worst-case ~53 events in quadrature to a ~175-event σ_S inflates the
total uncertainty by only ≈√(1+(53/175)²)−1 ≈ **4.5%** — a modest,
easily-affordable systematic. For notEBEB with `bernstein_6`, adding its
worst-case ~109 events (real bias, not noise) in quadrature to a
~222-event σ_S inflates the total uncertainty by
≈√(1+(109/222)²)−1 ≈ **11.6%** — directly eating into that category's
sensitivity by an amount comparable to a real, non-trivial systematic
in a mature analysis, and doing so to paper over a bias that Part 5
suggests has an identifiable, fixable cause (parameterization) rather
than an irreducible one.

**In plain terms**: EBEB looks close to solvable outright (try
Bernstein order 6 — the current "failure" may simply disappear, since
it is not statistically distinguishable from the threshold already).
notEBEB has a real, sizeable problem specifically tied to how badly a
power-law-shaped truth is described near 120–135 GeV, on top of several
candidate functions that cannot even be evaluated reliably due to a
parameterization issue in their own fits — trying Bernstein order 7
there is the natural next experiment, but option (C) (accept a
non-trivial systematic) may end up necessary regardless if a higher
Bernstein order doesn't close the gap, since option (A) offers little
extra with the current candidate set and isn't a substitute for having
at least one function that actually passes.

---

## Files

- `diagnostics/load.py`, `part1_drivers.py`, `part2_significance.py`,
  `part4_truth_spread.py`, `part5_failure_diagnosis.py`,
  `run_diagnosis.py` — this diagnosis's code (Parts 1–4 run via
  `run_diagnosis.py`; Part 5 run separately, see that section).
- `results/bias_study_105_180.json` — the merged cluster result (copied
  from `C:\Users\matan\hgg_bias_merged\` for reproducibility).
- `results/bias_diagnosis_summary.json` — Parts 1–4's numeric results.
- `results/bias_diagnosis_part5_local_reruns.json` — Part 5's full
  per-toy diagnostic records.
- `results/plots/bias_diagnosis/*_heatmap.png` (16 files, one per
  category×test-function) and `*_truth_spread.png` (2 files).
