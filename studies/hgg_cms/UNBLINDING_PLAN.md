# H→γγ unblinding plan

**Status: pre-registered, NOT executed.** This document is committed
before any unblinding code runs, and before the signal region (115 ≤
m_γγ ≤ 135 GeV) is opened. It fixes, in advance, exactly what will be
computed, how it will be reported, and what counts as "evidence" or
"observation" -- so that no choice made after seeing the data can change
the primary conclusion. Everything below was written using only
sideband-derived and synthetic (Asimov/toy) inputs; see
`studies/hgg_cms/stats/STATS_REPORT.md` for the validation and expected-
significance results that this plan is based on.

## 1. Primary result

The primary result is the **local, one-sided discovery significance**
(the CCGV test statistic q0, Cowan, Cranmer, Gross, Vitells, "Asymptotic
formulae for likelihood-based tests of new physics", Eur.Phys.J.C 71
(2011) 1554, arXiv:1011.1554, and its discovery-specific form in
arXiv:1007.1727) of the combined two-category (EBEB, notEBEB)
simultaneous fit, evaluated at a single, externally fixed mass:

**m_H = 125.09 GeV**, the ATLAS+CMS Run 1 combined measurement (Aad et
al., "Combined Measurement of the Higgs Boson Mass in pp Collisions at
√s = 7 and 8 TeV with the ATLAS and CMS Experiments", Phys. Rev. Lett.
114 (2015) 191803).

**No look-elsewhere correction is applied to the primary result.** The
mass is fixed from an external, independent measurement, not chosen
from this analysis's own data -- so there is no "where in the spectrum"
trials factor to correct for the primary number. (The look-elsewhere
effect IS estimated as a secondary/robustness item, section 2 and 3,
for the separate question "how surprising is the largest excess
anywhere in 110-150 GeV".)

Z = √q0 is reported both as the primary headline number and compared
against the pre-computed expected (Asimov, μ=1) value and the expected
1σ/2σ band from background-only and μ=1 signal-injection toys (see
STATS_REPORT.md Part 3).

## 2. Secondary results (reported regardless of outcome)

All of the following are reported alongside the primary result, whether
or not the primary result crosses any threshold in section 4:

1. Best-fit signal strength μ̂ at m_H = 125.09 GeV, with its total
   uncertainty and the same four-component breakdown computed on the
   expected (Asimov) dataset in STATS_REPORT.md Part 3.2: statistical,
   spurious-signal, signal-normalization (theory+lumi+ID+trigger),
   energy-scale/resolution.
2. Per-category best-fit μ̂ (EBEB alone, notEBEB alone), each with its
   own uncertainty, fit with the shared nuisances left free (not
   re-fixed to the combined best fit).
3. Best-fit m_H with μ and m_H both floated freely, with its
   uncertainty.
4. The local p-value / Z curve over 110-150 GeV in 0.5 GeV steps (the
   same grid as the pre-registered expected curve).
5. The global significance of the largest excess anywhere in that
   110-150 GeV curve, from the pre-registered background-only toy
   ensemble (STATS_REPORT.md Part 3.5), with a Gross-Vitells upcrossing
   estimate (reference level Z0 = 1) reported alongside for comparison
   -- both numbers reported, not just one.
6. Observed Z compared against the pre-registered expected Z and its
   16/84% toy band (STATS_REPORT.md Part 3.3), stating explicitly where
   the observation falls relative to that band (inside 1σ, inside 2σ,
   or outside).

## 3. Pre-declared robustness checks (reported regardless of outcome)

Each of the following is computed and reported as **information**, not
as grounds to revise the primary result. If any robustness check
disagrees noticeably with the primary result, that disagreement itself
is reported -- the primary result is not silently replaced by whichever
variant looks most significant.

  i.   Fit range 110-180 GeV with bernstein_6 in place of 105-180 GeV
       (statistical-only interpretation, per the background-model
       robustness check already on record in
       `background_model/BACKGROUND_MODEL_REPORT.md`'s 18 Sep 2026
       update -- no spurious-signal values exist for the 60-cell grid at
       110-180 GeV).
  ii.  bernstein_5 (the runner-up) as the background function, both
       categories.
  iii. The fit repeated with the spurious-signal terms (θ_spur,c)
       removed entirely.
  iv.  Each category fit alone (EBEB only, notEBEB only) -- same numbers
       as secondary result 2, repeated here as a robustness cross-check
       framing.
  v.   Run2016G and Run2016H data fit separately, each with its own
       luminosity-scaled expected signal yield (7.653 fb⁻¹ and 8.740
       fb⁻¹ respectively -- see `studies/hgg_cms/selection`/metadata for
       the source of these two run-period luminosities).
  vi.  The energy-scale (θ_scale) and resolution (θ_res) nuisances fixed
       at their nominal (0) values instead of profiled, both categories.

## 4. Pre-declared wording

Fixed **before** any data is examined, applied only to the **primary**
result (section 1):

| Primary local Z | Wording |
|---|---|
| Z ≥ 5 | "observation of a signal consistent with H→γγ" |
| 3 ≤ Z < 5 | "evidence for a signal consistent with H→γγ" |
| Z < 3 | Report the significance and μ̂ with its uncertainty; do **not** claim evidence. |

In every case, the result is compared explicitly against the Standard
Model expectation (μ = 1) -- both the observed μ̂ and its distance (in
σ) from μ = 1, and from μ = 0, are stated regardless of which row above
applies.

## 5. Frozen inputs

The following are fixed at the commit this plan is part of, and
recorded here so that any later change is visible as a **post-hoc**
change rather than silently folded into the "pre-registered" result.

- Git commit hash (this plan, the statistical model code, and the
  unblinding gate, as pushed): `5e2e84ffb1c9308914684be101886df763ef04bb`
  -- the commit that fixed a real bug in the gate itself (a regex that
  could not parse this very file's multi-line hash line -- see that
  commit's own message), found while filling in this line. `gate.py`'s
  own ancestor-based check (not exact-HEAD-equality) is what makes this
  line, and the purely-documentary commit that records it, both
  possible: a commit can never contain its own resulting hash, so this
  value was necessarily written down one commit AFTER `5e2e84f...`
  itself -- the ONLY commit hash that matters for approval is
  `5e2e84f...`, not whatever commit happens to contain this sentence.
- SHA-256 of `studies/hgg_cms/signal_model/results/signal_model.json`:
  `c1183f375e87b947335eaec014bd94ccd949b2de578e12183b1d0841c11b5f82`
- SHA-256 of
  `studies/hgg_cms/background_model/results/background_model_final.json`:
  `af17b2cdcaa58929f5018c9b18cd94b501c493bcda13ccb02f93daa1fa1a605b`
- SHA-256 of `studies/hgg_cms/stats/model.py` (the statistical model
  code): `366e361925e5bb197432835c5a0e3ac1d7f1932399c2f8cc510bfed325a58aab`
- SHA-256 of every script under `studies/hgg_cms/stats/unblind/` (the
  gated unblinding scripts, Part 5):
  - `gate.py`: `d809d4f7283e7fe7618b8ce295b4ba661607b4f74acd2190244c2f35747335b6`
  - `merge_full_range.py`: `593e6b0228bc7df5535a6b87b738ab38550c5681ce3e5832fe6ed961dba533f8`
  - `run_unblinded_analysis.py`: `87363080c4ac9c10a8eeee94216486cdff63197a953250cfb8b7ef5b3659e3c0`

If, after unblinding, any of these files needs to change (a bug found,
a decision revisited), the change is reported explicitly as a
**post-unblinding change**, alongside -- never in place of -- the
originally pre-registered result computed with the frozen commit above.

### Post-approval change #1 (18 Sep 2026): `merge_full_range.py` write bug

**What happened**: after explicit approval was given and the gate
correctly passed (flag + `HGG_UNBLIND_APPROVED` + frozen commit
`5e2e84f...` all verified), the gated merge script crashed while
WRITING its output file -- `f["events"] = full` (passing uproot a
single zipped awkward record array) raised `TypeError: fields of a
record must be NumPy types... field 'category' has type string`. This
is a pure file-I/O bug in how the merge script serializes its output,
not in the gate, the selection, or any analysis logic.

**No data had been read for analysis and no result had been produced
or seen at the time of the crash.** Only a 1,698-byte, header-only,
zero-event partial file existed on disk (moved aside as
`data_full_range.root.failed1`, never used); the 133 per-job blinded
files and the sideband file were both untouched (the merge script only
ever reads them). The gate itself is unmodified by this fix.

**What changed**: `write_full_range_root` in `merge_full_range.py` now
writes the output as a dict of per-field awkward arrays (matching the
convention `studies/hgg_cms/output.py`'s `_write_root_table` already
uses successfully for every other ROOT file in this pipeline), instead
of passing a single zipped record array to uproot. No event, field
value, or ordering changes -- confirmed by a new round-trip unit test
(`tests/test_merge_full_range_write.py`, synthetic data only). No
reader-side change was needed or made (`read_output` opens either
representation identically). No selection, statistical-model, or
analysis-procedure logic was touched.

**Commit**: see `STATS_REPORT.md`'s own frozen-inputs section / the git
log for this fix's exact commit hash (recorded there rather than
duplicated here, so there is one place this can go stale). New SHA-256
of `merge_full_range.py` as of this fix:
`fa83d2211839cd93e8c39c9d5d7801c439e3e885ef4e26c2b34f23766bf09de6`
(was `593e6b0228bc7df5535a6b87b738ab38550c5681ce3e5832fe6ed961dba533f8`
at the original frozen commit `5e2e84f...` above -- that original hash
is kept unchanged in section 5 as the historical record of what was
frozen; this is the current, fixed value).

## 6. Stop conditions (technical, not outcome-based)

These are conditions under which the analysis stops and is diagnosed
BEFORE any interpretation of the result is attempted -- they do not
depend on whether the result looks interesting:

- MIGRAD reports the fit as invalid (not `m.valid`) for either the null
  or the alternative fit on the real data, after the full multi-start +
  second-optimizer cross-check procedure in `stats/fit.py`.
- The NLL invariant (NLL(μ free) ≤ NLL(μ=0) + 1e-6) is violated on the
  real-data fit.
- The scipy L-BFGS-B cross-check finds a materially better minimum than
  MIGRAD's (see `fit.cross_check_fit`'s `scipy_found_better` flag) and
  the two do not agree after re-fitting from the better point.

If any of these fire, the result is not reported as a discovery
significance until the fit issue is understood and fixed -- exactly the
"stuck-null-fit" lesson from `studies/atlas_hgg_repro/REPORT.md`'s
"Corrections" section that this task's own statistical model was built
to guard against (see `stats/fit.py`'s module docstring).
