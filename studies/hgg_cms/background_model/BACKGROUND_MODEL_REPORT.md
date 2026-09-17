# H→γγ background model (statistical-analysis task 2)

Built on the data sidebands only (`data_sidebands.root`, 105–115 ∪
135–180 GeV) — **the blinded 115–135 GeV window was never read, plotted,
or fit anywhere in this task.** Every data-loading script (`common.py`)
refuses a path whose name contains `BLINDED`, then independently
re-asserts, on the loaded array itself, that no data event with
115 ≤ m_γγ ≤ 135 GeV is present (the same two-layer check earlier tasks
use). Every likelihood sum here uses an **explicit boolean sideband
mask** (`sideband_bin_mask`, unit-tested) on top of that — belt and
suspenders. Data plots leave the blinded band empty (grey); each
family's fitted **curve** is drawn across it, which this task's own
rules explicitly allow.

**STATUS (updated 18 Sep 2026): the background model is FINALIZED.**
Parts 1–2 (both fit ranges) ran for real on this laptop. Part 3 (the
full bias study) ran on the cluster in two rounds — the first 120-job
run (no candidate passed) and a rerun testing one higher-order Bernstein
candidate per category — see `BIAS_DIAGNOSIS.md` for why, and this
report's two dated decision sections ("Pre-declared selection
procedure" and "Human decision after rerun 1") for the full,
pre-committed selection logic and the resulting human decision:
**Fallback C applied in both categories, chosen function = `bernstein_6`**
(EBEB and notEBEB), with an explicit spurious-signal systematic per
category (32.2 events EBEB, 109.3 events notEBEB — see that section for
the full numbers and source cells). The finalized model —
parameters, covariance, the systematic, and the per-bin evaluation
function the later S+B fit will use — is in
`results/background_model_final.json` /
`studies/hgg_cms/background_model/final_model.py`.

**What remains**: the 110–180 GeV reduced robustness check (chosen
function + runner-up(s), prepared but not yet run — see Part 4 below
for the exact commands), and the expected-significance / pre-
unblinding-plan task after that.

Reproduce Parts 1–2 (and 4's order selection) with:
```
python -m studies.hgg_cms.background_model.build_background_model
```
Reproduce the finalized model (Part 2's refit-with-covariance, the
final JSON, and the plots) with:
```
python -m studies.hgg_cms.background_model.finalize_background_model
```
Unit tests: `python -m pytest tests/test_background_model.py
tests/test_bias_rerun_seed_identity.py tests/test_bias_rerun_merge.py
tests/test_final_background_model.py tests/test_pbs_scripts.py`.

---

## Part 1 — Sideband data and binning

0.25 GeV bins, 105–180 GeV (300 bins; 220 in the sideband mask). Robustness
variant: 110–180 GeV (280 bins; 200 in the sideband mask).

| category | sideband events (105–115 ∪ 135–180) | total in 105–180 selection |
|---|---:|---:|
| EBEB | 66,347 | 90,336 (full 100–180 selection) |
| notEBEB | 66,683 | 92,215 (full 100–180 selection) |

(These match `VALIDATION_REPORT_1.md` Part A's full-selection counts —
the sideband-only totals above are the subset landing in 105–180 GeV
with the 115–135 window removed.)

---

## Part 2 — Candidate families and order selection

**Families** (the standard CMS H→γγ discrete-profiling set): Bernstein
polynomials (order 1–7, non-negative coefficients — positivity
guaranteed by construction), sums of exponentials (N=1–3), sums of power
laws (N=1–3), Laurent series with fixed exponents (−4,−5,−3,−6 …,
N=1–4). See S. Chatrchyan et al. (CMS), *Observation of the diphoton
decay of the Higgs boson…*, Eur. Phys. J. C 74 (2014) 3076,
arXiv:1407.0558, and P. Dauncey et al., *Handling uncertainties in
background shapes: the discrete profiling method*, JINST 10 (2015)
P04015, arXiv:1408.6865. All four families use exact analytic bin
integration (closed-form antiderivatives — Bernstein via the
regularized incomplete beta function, the others via elementary
antiderivatives), verified against numerical quadrature in unit tests
(agreement to 5–6 decimal places). Normalized mass variables:
x=(m−105)/75 for Bernstein/exponentials, x′=m/105 for power-laws/Laurent
(documented in `families.py`).

**Fitting robustness**: every fit tries ≥10 starting points (an analytic
guess — non-negative least squares for Bernstein, plain least squares
for Laurent, weighted log-linear regression for exponentials/power-laws
— plus perturbations and random draws within documented ranges), keeps
the lowest-NLL **valid** MIGRAD result, and records how many of the 10
converged validly. **For every one of the 8 final chosen fits** (4
families × 2 categories, 105–180 GeV — and again for 110–180), a
**second optimizer** (scipy L-BFGS-B, started from MIGRAD's own best
point) was run as a cross-check: in every single case it found nothing
better (relative improvement ≤3×10⁻¹⁰, typically ≪10⁻¹²) — direct
evidence against the exact failure mode this task asked to guard
against (`studies/atlas_hgg_repro/REPORT.md`'s "Corrections": a
plausible-looking but wrong MIGRAD local optimum, off by whole NLL
units, silently reported "valid").

**Order selection** (pre-set rule, see `part2_order_selection.py`'s own
docstring for the exact algorithm, including how the one ambiguity in
the task's instructions — what to do if the F-test order fails GOF — was
resolved): F-test (2·ΔNLL vs. χ², p<0.05 to add an order) first, then a
GOF check (binned χ², bins with predicted content ≥5, p>0.01) at that
order; if GOF fails there, search upward for the first higher order that
passes GOF; if none of a family's orders pass GOF, drop it.

### Results, 105–180 GeV (default range)

| category | family | selected order | n params | NLL | GOF p-value |
|---|---|---:|---:|---:|---:|
| EBEB | bernstein | 4 | 5 | −334014.93 | 0.44 |
| EBEB | expsum | 2 | 4 | −334015.35 | 0.48 |
| EBEB | powersum | 1 | 2 | −334014.59 | 0.48 |
| EBEB | laurent | 2 | 2 | −334014.89 | 0.50 |
| notEBEB | bernstein | 5 | 6 | −337228.46 | 0.67 |
| notEBEB | expsum | 2 | 4 | −337225.42 | 0.59 |
| notEBEB | powersum | 2 | 4 | −337228.38 | 0.70 |
| notEBEB | laurent | 3 | 3 | −337225.60 | 0.62 |

**No family was dropped in either category — all four families, at
their selected order, describe the sideband data well (GOF p between
0.44 and 0.70, comfortably above the 0.01 threshold), and no GOF
override was ever needed** (the F-test order always already passed
GOF). All four families' fitted curves are visually indistinguishable
over the full 105–180 GeV range — see
`results/plots/EBEB_105_180_sideband_fits.png` /
`notEBEB_105_180_sideband_fits.png` (data, all 4 curves, pull panel
against the lowest-NLL family; blinded band shown empty, curves drawn
across it as permitted). Pulls stay within about ±3 across the full
range in both categories.

### Results, 110–180 GeV (robustness range)

| category | family | selected order | n params | NLL | GOF p-value |
|---|---|---:|---:|---:|---:|
| EBEB | bernstein | 4 | 5 | −222818.27 | 0.44 |
| EBEB | expsum | 2 | 4 | −222817.77 | 0.44 |
| EBEB | powersum | 1 | 2 | −222817.18 | 0.45 |
| EBEB | laurent | 2 | 2 | −222817.36 | 0.46 |
| notEBEB | bernstein | **3** | 4 | −221004.37 | 0.82 |
| notEBEB | expsum | 2 | 4 | −221003.94 | 0.80 |
| notEBEB | powersum | 1 | 2 | −221001.92 | 0.77 |
| notEBEB | laurent | 2 | 3 | −221002.30 | 0.78 |

Again, no family dropped, no GOF override needed. Orders are the same or
**lower** than the 105–180 selection in every case (e.g. notEBEB
Bernstein drops from order 5 to order 3, notEBEB powersum from order 2
to order 1) — physically sensible, since removing 105–110 GeV removes
some of the curvature the extra complexity in the default range was
there to capture.

---

## Part 3 — Bias (spurious-signal) study — **COMPLETE** (see the dated decision sections after Part 3 for the outcome and the resulting finalized model)

### What is built and validated

- **Truth variants**: each family's selected order (above), fit to the
  real sideband data, times 3 leakage variations — nominal (the fitted
  curve as-is), and ±0.5 × the leakage mass template (from
  `hgg_leakage_mass_template_results.json`, all 41 DY jobs, rebinned
  from its native 1 GeV bins to the analysis's 0.25 GeV grid by an
  explicit, documented flat sub-division — 0.25 evenly divides 1.0, so
  every rebinning is exact, no interpolation). = **12 truth variants per
  category** (4 families × 3 leakage variants).
- **Test functions**: each family's selected order **and one order
  above** = **8 test functions per category**.
- **Toys**: Poisson-fluctuated bin-by-bin over the full (unmasked)
  105–180 GeV range — synthetic, so filling the blinded window is not a
  blinding violation.
- **Test fits**: background-only (S fixed at 0) and signal+background (S
  free, unbounded sign, bounded magnitude at 20× the expected signal
  yield) for every toy, both **warm-started from the background-only
  fit's own converged parameters** — so the NLL invariant
  (`NLL(S free) ≤ NLL(S=0) + 1e-6`) is true by construction of the
  starting point, then explicitly re-checked per toy; a violation (or an
  invalid fit) triggers one retry from a fresh generic start before being
  counted as a failure (never silently dropped).
- **Reliability finding, worth flagging plainly**: a first attempt with
  MIGRAD strategy=0 (the faster setting) left roughly 10–70% of
  individual (truth, test-function) combinations' S+B fits formally
  invalid (`is_above_max_edm` — MIGRAD's own convergence criterion not
  met) on this problem's mixed-scale parameters. Switching to
  strategy=1 (≈2.3× slower per fit) reduced this to single digits or
  zero percent in every combination checked, at the cost of the timing
  discussed below. **Even with strategy=1, one specific combination
  (EBEB, powersum order 2 as a test function) showed a persistently
  elevated failure rate (45/100 in one check)** — reported here exactly
  as required, not hidden; the merge step (`merge_bias_results.py`)
  carries `fail_fraction` through to the final table for every
  (truth, test-function) cell, so this will be visible in context once
  the real run completes.

### Timing test and the decision to stop

A direct measurement on this laptop (100 toys × 8 test functions = 800
toy-pairs, real EBEB sideband data, strategy=1) took **39.9 s ≈
0.050 s/toy-pair**. Extrapolating to the full requested grid:

| | value |
|---|---:|
| combinations per category (12 truths × 8 test functions) | 96 |
| toy-pairs at m_H=125 (1,000 toys) | 96 × 1,000 = 96,000 |
| toy-pairs at the other 4 masses (300 toys each) | 96 × 4 × 300 = 115,200 |
| total toy-pairs, both categories | 2 × 211,200 = **422,400** |
| **extrapolated wall time** | **422,400 × 0.050 s ≈ 5.87 hours** |

This exceeds the task's own ~3-hour local budget, so — exactly as
instructed — local execution of the full grid **stopped here**. A
10-toy and a 100-toy end-to-end run of the actual job script (not a
mock) were used to validate correctness (sane spurious-S magnitudes,
correct NLL-invariant behavior, correct failure counting), but these are
explicitly **not** the real bias-study result and are not reported as
such anywhere in this document.

### Cluster jobs (prepared, not submitted)

Fully self-contained: each job reads only `order_selection_105_180.json`
(already committed — every family/order's converged sideband-fit
parameters, so no cluster job re-opens `data_sidebands.root`),
`signal_model.json` (already committed), and the leakage template JSON
(simulation, copied to Lustre already). 120 subjobs (2 categories × 4
truth families × 3 leakage variants × 5 masses), each looping over all 8
test functions internally; ~2–7 minutes measured/extrapolated per
subjob, `walltime=00:30:00` requested (>4× safety margin, still well
under the 02:00:00 `shortE`-routing boundary this cluster uses — see
`studies/hgg_cms/cluster/FULL_RUN_README.md`). **Exact commands are in
the final chat message.**

### Update — 18 Sep 2026: fit-reliability eligibility rule (added before any real result exists)

The 120-subjob cluster run is now in flight. **Before any of its results
have been merged or looked at**, the "Reliability finding" bullet above
(strategy=0 vs. strategy=1's failure rates, and the one persistently
elevated combination found in a small local check) is promoted from an
observation into a formal, pre-set SELECTION RULE, added to
`merge_bias_results.py`:

**A test function is INELIGIBLE for selection if, in ANY (truth
variant, mass) cell, its `fail_fraction` exceeds 0.05 (5%).** This is
in ADDITION to, not instead of, the existing 0.20×σ_S spurious-signal
criterion — a function must be BOTH eligible (reliable fits) AND
passing (small enough bias) in every cell to be selectable. An
ineligible function's bias numbers are still computed and reported (for
information — e.g. to distinguish "this function is unreliable" from
"this function is reliable but biased"), never hidden, just excluded
from the ranking that picks the chosen function.

**Why this had to be a separate rule, not folded into the 0.20×σ_S
check**: a spurious-signal MEAN computed from mostly-failed fits is not
a trustworthy estimate of that function's true bias, no matter how
small it happens to look — a function could show a tiny, reassuring
mean spurious S purely because most of its toy fits silently failed
and only a lucky, unrepresentative subset of fits contributed to the
average. Rejecting on reliability FIRST, independent of what the
(possibly meaningless) bias number says, is the only way to avoid that
trap. A unit test (`test_45pct_failure_with_tiny_spurious_signal_is_ineligible`,
`tests/test_background_model.py`) enforces this: a function with a
45% fail rate and a tiny, easily-passing spurious signal is checked to
be INELIGIBLE, not selected.

**Minimum successful-toy count, checked explicitly** (this follows
mathematically from the 5% fail-fraction cap — 95% success already
exceeds either floor — but is implemented as its own separate check
against each job's own reported `n_used` field, not re-derived from
`fail_fraction`, so an inconsistency between the two would itself be
caught): ≥900 of 1,000 successful toys at m_H=125 GeV, ≥270 of 300
elsewhere.

**Borderline flag**: a (truth variant, mass) cell is flagged
`"borderline"` if its ratio |mean S|/mean σ_S sits within **1 standard
error** of the 0.20 threshold — `se_ratio = se_mean_S / mean_sigma_S`
(the toy-to-toy standard error on the mean spurious signal, treating
the average fitted uncertainty `mean_sigma_S` as fixed — a documented
approximation, not a full two-term error propagation). This does not
change pass/fail on its own; it flags cells worth a second look where
the criterion's outcome could plausibly flip with different toy
statistics.

**Output location, fixed at the same time**: `merge_bias_results.py`
now writes its merged result to Lustre by default
(`<out-base>/merged/bias_study_<fit-range>.json`) — never into this git
checkout, which needs to stay clean for later preflight checks (e.g.
`submit_zee.sh`'s own `preflight_git`, which refuses to submit against
a dirty tree). The exact merge command is in the final chat message.

Because this whole section was written and committed before the
120-subjob run's results have been merged or examined, none of it was
tuned to any observed outcome.

---

## Pre-declared selection procedure after the first bias study (decided 18 Sep 2026, before any result of the rerun exists)

The first bias study (120/120 cluster jobs, merged at
`results/bias_study_105_180.json`) found no eligible-and-passing
candidate in either category (see `BIAS_DIAGNOSIS.md`). This section
records, in full, the procedure for the rerun that follows — written
and committed **before** the rerun's own code exists, let alone any of
its results, so nothing below is tuned to an outcome.

**1. Step B — one new candidate per category.** Add exactly one
higher-order Bernstein test function per category: **EBEB
`bernstein_6`**, **notEBEB `bernstein_7`**. Test them with the
IDENTICAL bias-study setup as the first run: the same truth models
(each family at its already-selected order, fitted to the real
sidebands, exactly as recorded in `results/order_selection_105_180.json`
— not refit), the same three leakage variants (nominal, ±0.5× the
leakage template), the same five masses (115, 120, 125, 130, 135 GeV),
the same toy counts (1,000 at 125 GeV, 300 at the other four), the same
per-cell seeds as the first run (so the new candidate is tested on the
same pseudo-datasets — see the rerun code's own documentation for
exactly how seed reuse is guaranteed and proven), the same fit
robustness settings (MIGRAD strategy=1, warm-started from the
background-only fit, one retry on an NLL-invariant violation or an
invalid fit), and the same `NLL(S free) ≤ NLL(S=0) + 1e-6` invariant
check.

**2. Selection, applied to the UNION of the first-run candidates and
the new one, per category:**

  **(i)** If one or more candidates are ELIGIBLE (the 5% fit-reliability
  rule, unchanged) **and** PASS (worst |mean S|/mean σ_S < 0.20 in every
  one of the 60 cells, unchanged): choose the one with the **fewest
  parameters**; a tie is broken by the **lower sideband NLL**. The
  spurious-signal systematic for this chosen function is assigned per
  (iii) below.

  **(ii)** Otherwise — **STOP, do not auto-select.** *(Revised 18 Sep
  2026, before the rerun's own code was written, superseding this same
  section's original wording — see the note at the end of this point.)*
  If no candidate is both eligible and passing, the merge step reports
  for that category and does **not** choose a function on its own. The
  report must list, for that category: **every** candidate's
  eligibility, its worst ratio, its worst |S_spur| in events, and that
  worst |S_spur| as a percentage of the expected signal yield (EBEB
  545.8, notEBEB 266.1). It must also compute and display — clearly
  marked **"not applied, human decision required"** — which candidate
  **FALLBACK C** (an ATLAS-style spurious-signal systematic: among
  ELIGIBLE candidates only, the one with the smallest worst ratio over
  the 60 cells, tie broken by fewer parameters) **would** choose, and
  what its resulting systematic would be, without applying it. The two
  standing options to decide between at that point are: adopt fallback
  C as just described (accept a function that doesn't formally pass,
  carrying its worst-case bias as an explicit nuisance parameter), or
  invest in the CMS discrete-profiling / envelope method described in
  point 4 below. Neither is applied automatically.

  *(Note on this revision: an earlier version of this section, briefly
  committed and then superseded before any rerun result existed, had
  (ii) auto-apply fallback C as part of the merge step itself. That was
  changed to the STOP-and-report behavior above at the user's explicit
  instruction, before any rerun code was written and before this
  section's own commit that the rerun code depends on — the ordering
  this whole section exists to protect was preserved throughout.)*

  **(iii)** For a function chosen under **(i)**, the category's
  spurious-signal systematic = the **maximum over all 60 cells**
  (4 truth families × 3 leakage variants × 5 masses) of |mean spurious
  S| in events, for that function. In the eventual signal-plus-
  background fit this enters as an additional yield term
  `S_spur × θ_spur`, with `θ_spur` a unit-Gaussian-constrained nuisance
  parameter, **one per category, uncorrelated between categories**.

  **(iv)** If NO candidate in a category is eligible at all: **STOP and
  report.** No further relaxation of the eligibility rule, the 0.20
  threshold, or anything else — this would be escalated as its own
  finding, not silently worked around.

**3. Why this was decided, recorded for transparency** (the diagnosis
findings that motivated adding exactly this one new candidate per
category, from `BIAS_DIAGNOSIS.md`): EBEB's best existing candidate,
`bernstein_5`, has worst ratio 0.304 — statistically **indistinguishable
from noise** around the 0.20 threshold (Monte Carlo null p=0.83, zero of
its 60 cells exceed 0.20 by more than 2 standard errors) — going one
Bernstein order higher is the direct, evidence-driven next step, since
order 4→5 already took the worst ratio from a hugely significant 0.841
down to noise level. notEBEB's best existing candidate, `bernstein_6`,
has worst ratio 0.493 — a **statistically real effect** (p=3×10⁻⁵),
worst |S_spur| ≈ 109 events, ≈41% of the expected notEBEB signal yield
(266.1 events) — and the truth-family spread inside 115–135 GeV in
notEBEB is ≈1.07× the signal peak's own density (it exceeds the signal
peak), so a meaningfully larger notEBEB residual than EBEB's is
expected even after adding flexibility; `bernstein_7` is tried there
because the same order-increase mechanism (4→5 already roughly halved
the worst ratio, 5→6 continued in the same direction: 0.925→0.493) is
the best-evidenced lever available, not because the diagnosis proved it
will be enough — fallback C exists precisely in case it isn't.

**4. The principled alternative, not adopted here.** CMS's own
"discrete profiling" / envelope method (P. Dauncey et al., JINST 10
(2015) P04015, arXiv:1408.6865) — profiling over multiple PASSING
candidate functions as a discrete nuisance parameter at fit time — is
the standard, more rigorous solution to exactly this problem. It is
**not adopted in this rerun** because it requires new fitting
machinery (a discrete-nuisance-parameter profiled likelihood) beyond
what this project's already-validated tools
(`studies/hgg_cms/background_model/`, `studies/hgg_cms/stats/`)
currently implement, and because — per `BIAS_DIAGNOSIS.md` — an
envelope built from the CURRENT candidate set would be dominated by
Bernstein alone anyway (every non-Bernstein family either fails on
cross-family truth mismatch or is unreliable outright), so it would add
implementation cost without changing today's outcome. Recorded here as
a possible future improvement, e.g. once more than one family is
genuinely viable.

**5. Robustness plan, unchanged.** After a function is selected under
(2) above, the already-planned 110–180 GeV reduced bias check (the
chosen function plus its two runners-up, nominal truths only, m_H=125,
≥500 toys — `cluster/make_job_list_part4.py`, already prepared) proceeds
exactly as originally scoped in Part 4 below; this rerun does not change
that plan.

---

## Human decision after rerun 1: Fallback C applied in both categories (decided 18 Sep 2026, before any significance calculation and before unblinding)

### 1. Rerun-1 outcome

The rerun ran on the cluster as job `5056179[]` (120 subjobs: EBEB
`bernstein_6`, notEBEB `bernstein_7`, same 60 cells and same per-cell
seeds as the first run — see `tests/test_bias_rerun_seed_identity.py`
for the proof). 112/120 subjobs finished on the first attempt; **8
notEBEB, m_H=125 GeV, `bernstein_7` subjobs (array indices 61, 66, 71,
76, 81, 86, 111, 116) were killed by the original 15-minute walltime
(exit −29)** — this project's own quick local check had already flagged
`bernstein_7` as slow/unreliable in notEBEB (30–42% fit-failure rates
on 5 sample cells, `results/rerun1_local_convergence_check.json`), so a
1000-toy `bernstein_7` cell running past 15 minutes is consistent with
that same finding, not a new problem. Those 8 were resubmitted
**unchanged** — identical job-list lines and seeds, only `walltime`
raised to `01:00:00` — as job `5056206[]`, all 8 exiting 0. Final: 120/120
output files present. **This does not alter the pre-set test in any
way**: no seed, toy count, truth model, leakage variant, or criterion
was touched — only the wall-clock budget given to already-defined jobs
that needed more time to finish the identical computation.

Merged result (`results/bias_study_105_180_with_rerun1.json`, 240 job
outputs = 120 first-run + 120 rerun):

| category | chosen (auto) | ineligible (fit reliability) | fallback C would choose | worst ratio | worst \|S_spur\| |
|---|---|---|---|---:|---:|
| EBEB | **None** | expsum_2, laurent_3, powersum_2 | bernstein_6 | 0.217 | 32.2 events (5.9% of 545.8) |
| notEBEB | **None** | bernstein_7, expsum_2, expsum_3, laurent_3, laurent_4, powersum_2, powersum_3 | bernstein_6 | 0.493 | 109.3 events (41.1% of 266.1) |

**`bernstein_7` itself is ineligible in notEBEB** (fit reliability) —
the quick local check's red flag was correct: the extra order didn't
just fail to help, it made convergence worse, not better.

### 2. The decision

**Fallback C is applied in both categories. The chosen background
function is `bernstein_6` (EBEB and notEBEB)** — the pre-declared
Fallback C rule (`BACKGROUND_MODEL_REPORT.md`'s "Pre-declared selection
procedure", point 2(ii)/(iv)): among eligible candidates, the smallest
worst ratio, ties broken by fewer parameters. This is a **human
decision**, made here, not an automatic one — the merge script itself
still only *reports* what fallback C would choose (see the STOP-and-
report behavior recorded in this same report's revised point 2(ii));
applying it is this section's own act.

**Why**: no candidate passed the 0.20 criterion in either category, so
(i) never triggers. Between the two options this report's point 2(ii)
laid out (fallback C, or the CMS envelope method):
- **EBEB's `bernstein_6` sits close to the threshold** (worst ratio
  0.217 vs. 0.20 — within the noise-level territory `BIAS_DIAGNOSIS.md`
  Part 2 already found for `bernstein_5`), and its worst spurious
  signal is a modest 5.9% of the expected signal yield — a function
  this close to passing, carrying a small systematic, is a reasonable,
  conservative choice.
- **notEBEB does not have that luxury.** `BIAS_DIAGNOSIS.md` Part 4
  found the truth-family spread inside 115–135 GeV in notEBEB is
  **≈1.07× the signal peak's own density** — genuinely different
  plausible background shapes disagree with each other by about as
  much as the whole signal, a structural feature of this category, not
  a fixable fitting artifact — and the one candidate that might have
  done better, `bernstein_7`, is **itself unreliable** (ineligible on
  fit-reliability grounds, consistent with the local check's own red
  flag). With the principled alternative (CMS discrete profiling) not
  implemented (this report's earlier point 4) and no eligible
  candidate closer to passing, `bernstein_6` — carrying an honestly
  large, explicit systematic — is the least-bad available choice.

### 3. Spurious-signal systematic per category

Per this report's own point 2(iii): the systematic = the **maximum
over all 60 cells** of |mean spurious S| in events, for the chosen
function — **verified directly against the merged JSON**
(`worst_abs_mean_S_events` / `worst_abs_mean_S_detail` in each
category's `bernstein_6` evaluation), which is **not always the same
cell as the worst RATIO** (ratio also divides by that cell's own
σ_S, which varies cell to cell):

| category | S_spur (events) | source cell (truth / leakage / mass) | mean_S (signed) | mean σ_S there |
|---|---:|---|---:|---:|
| EBEB | **32.2** | expsum / leakage_plus / m=120 GeV | +32.16 | 157.36 |
| notEBEB | **109.3** | powersum / nominal / m=120 GeV | +109.26 | 221.68 |

(EBEB's worst-*ratio* cell is a different one — powersum / leakage_plus
/ m=130 GeV, ratio 0.217, mean_S=−28.4 — smaller in events than the
expsum/120 cell above but a larger fraction of that cell's own, smaller
σ_S; notEBEB's worst-ratio and worst-|S_spur| cells coincide.)

In the eventual signal-plus-background fit, this enters as an
additional yield term **`S_spur,c × θ_spur,c`**, with `θ_spur,c` a
unit-Gaussian-constrained nuisance parameter, **one per category,
uncorrelated between categories** (`c` ∈ {EBEB, notEBEB}). **The term
is independent of the hypothesized mass** — the maximum over the whole
5-mass scan is used at every mass point, not a mass-dependent value,
per this report's own point 2(iii) wording ("maximum over all 60
cells").

### 4. Alternatives considered, and a rough cost estimate for option C

**(A) CMS discrete profiling / envelope** (arXiv:1408.6865): remains
the principled alternative, not adopted for the reasons already
recorded in this report's point 4 (needs new fitting machinery this
project hasn't built) — kept as a possible future cross-check,
particularly worth revisiting for notEBEB given how large its
systematic is.

**(D) Dropping notEBEB entirely**: considered and rejected. notEBEB
contributes 32.8% of the total expected signal (266.1 of 811.9 events,
`signal_model.json`) — dropping it is a much larger, structural
sensitivity loss than carrying an explicit ~14.6% yield-uncertainty
penalty (below) in exchange for keeping it.

**Rough expected cost of option C**, `√(1 + (S_spur/σ_S)²)` using the
mean fitted σ_S at m_H=125 GeV from the bias study (averaged over the
12 truth×leakage cells at that mass, for `bernstein_6`):

| category | S_spur | mean σ_S (125 GeV) | S_spur / σ_S | **signal-yield uncertainty growth** |
|---|---:|---:|---:|---:|
| EBEB | 32.2 | 140.7 | 0.229 | **√1.052 ≈ 1.026 → +2.6%** |
| notEBEB | 109.3 | 195.5 | 0.559 | **√1.313 ≈ 1.146 → +14.6%** |

**Flagged explicitly as rough**: this is a simple quadrature-sum
estimate using only the statistical σ_S from the bias-study toys at one
mass point, not a real profiled-likelihood calculation — the actual
cost to expected significance is computed properly in the next
(expected-significance) task, which also folds in the other systematics
already tabulated in `SIGNAL_MODEL_REPORT.md`.

### 5. Citation status for the ATLAS spurious-signal convention

This is published ATLAS practice, not an invented convention: G. Aad et
al. (ATLAS), *Observation of a new particle in the search for the
Standard Model Higgs boson...*, Phys. Lett. B 716 (2012) 1,
**arXiv:1207.7214**, established the general approach for this
channel; later ATLAS H→γγ **mass** measurements state the criterion
explicitly — G. Aad et al. (ATLAS), *Measurement of the Higgs boson
mass from the H→γγ and H→ZZ*→4ℓ channels...*, **arXiv:1406.3827**, and
the more recent G. Aad et al. (ATLAS), *Measurement of the Higgs boson
mass with H→γγ decays in 140 fb⁻¹...*, **arXiv:2308.07216**, both
select background functions by requiring the fitted spurious signal be
below a fixed fraction of the expected signal yield (retrieved via web
search summaries 18 Sep 2026, not by opening the primary PDF tables
myself — **UNVERIFIED to the exact wording/equation**, but the
methodology match is clear from multiple independent summaries).
**Their own published threshold is 10% of the expected yield — a
factor of 2 tighter than this project's own 20%×σ_S convention**
(a *different* quantity: theirs is spurious-S ÷ expected-signal-yield,
ours is spurious-S ÷ statistical-uncertainty-σ_S — not directly
comparable without also knowing their S/σ_S ratio, so this is noted as
a discrepancy worth being aware of, not proof our threshold is
wrong or right). This project's own 20%×σ_S choice was already recorded
as **our own documented choice** (not ATLAS's specific number) in
`merge_bias_results.py`'s module docstring and earlier in this report —
unchanged by this citation check.

---

## Part 4 — Robustness: 110–180 GeV

**Order selection: complete, see Part 2 above** — no family dropped,
same or lower orders than the default range (physically sensible).

**Reduced bias check (chosen function + 2 runners-up, nominal truths
only, m_H=125, ≥500 toys): pending**, since it needs Part 3's ranking to
know which 3 test functions to run. `cluster/make_job_list_part4.py` is
ready (8 subjobs: 4 truth families × nominal-only × m_H=125 × 500 toys,
per category) — pass `-v TEST_FUNCTIONS=<family:order,family:order,family:order>`
(the winner + 2 runners-up, read from the merged 105–180 result's
`per_category.<cat>.selection.passing_functions_ranked` — which already
reflects BOTH the fit-reliability eligibility rule and the 0.20×σ_S
criterion above, not just the latter) to `pbs_hgg_bias_array.sh` with
`FIT_RANGE=110_180`. Exact command template in the final chat message.
That script (used for both Part 3 and this reduced Part 4 run) now also
pins `OMP_NUM_THREADS`/`OPENBLAS_NUM_THREADS`/`MKL_NUM_THREADS` to 1
before running Python, added 18 Sep 2026 so a 1-CPU job request can't
use more than 1 CPU's worth of BLAS/OpenMP threads — the already-running
Part 3 array is unaffected (PBS reads a script at submission time).

---

## Output files

- `common.py` — blinded sideband loading, binning, sideband mask.
- `families.py` — the 4 function families (analytic PDF/bin-integration, positivity).
- `fit_background.py` — multi-start robust fitting, second-optimizer cross-check, F-test, GOF.
- `part2_order_selection.py` — the order-selection algorithm.
- `leakage.py` — leakage-template loading and rebinning.
- `signal_shape.py` — loads the signal model (prior task's output).
- `bias_study.py` — truth variants, toy generation, test fits, spurious-signal summary, NLL invariant.
- `serialize.py` — order-selection → JSON (also the cluster jobs' input config).
- `plots.py` — sideband-fit validation plots.
- `build_background_model.py` — orchestrator for Parts 1/2/4-order-selection.
- `cluster/` — `run_bias_job.py`, `make_job_list.py`, `make_job_list_part4.py`, `pbs_hgg_bias_array.sh`, `submit_bias_study.sh`, `status_bias_study.sh`, `merge_bias_results.py`, `plot_bias_heatmap.py` — all prepared, none run.
- `results/order_selection_105_180.json`, `results/order_selection_110_180.json` — full per-family, per-order fit/GOF detail (also the cluster jobs' config).
- `results/background_model.json` — top-level summary, including Part 3/4's documented pending status and the timing test.
- `results/plots/*_sideband_fits.png` — Part 2 validation plots.
- `../../../tests/test_background_model.py` — 22 unit tests.
