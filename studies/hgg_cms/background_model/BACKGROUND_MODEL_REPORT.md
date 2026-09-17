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

**Part 1 and Part 2 (both fit ranges) are complete, run for real, on
this laptop.** **Part 3 (the full bias study) is built, unit-tested, and
timed, but was not executed at full scale** — a direct timing test
showed the full requested grid would take ~5–6 hours on this laptop,
over the task's own 3-hour budget, so per the task's own instruction
this stopped after the timing test and cluster jobs were prepared
instead (not submitted). **Part 4's order selection is complete; its
reduced bias check is pending on Part 3's outcome** (it needs to know
the chosen function). See Part 3 below for the exact commands to finish
this.

Reproduce Parts 1–2 (and 4's order selection) with:
```
python -m studies.hgg_cms.background_model.build_background_model
```
Unit tests: `python -m pytest tests/test_background_model.py` (22 tests:
family evaluation/positivity, bin integration, the sideband mask, the
blinding-marker constant, F-test/GOF arithmetic, toy generation,
spurious-signal summary arithmetic, the NLL invariant, leakage-template
rebinning).

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

## Part 3 — Bias (spurious-signal) study — **PENDING, cluster run required**

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

---

## Part 4 — Robustness: 110–180 GeV

**Order selection: complete, see Part 2 above** — no family dropped,
same or lower orders than the default range (physically sensible).

**Reduced bias check (chosen function + 2 runners-up, nominal truths
only, m_H=125, ≥500 toys): pending**, since it needs Part 3's ranking to
know which 3 test functions to run. `cluster/make_job_list_part4.py` is
ready (8 subjobs: 4 truth families × nominal-only × m_H=125 × 500 toys,
per category) — pass `-v TEST_FUNCTIONS=<family:order,family:order,family:order>`
(the winner + 2 runners-up from the merged 105–180 result) to
`pbs_hgg_bias_array.sh` with `FIT_RANGE=110_180`. Exact command template
in the final chat message.

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
