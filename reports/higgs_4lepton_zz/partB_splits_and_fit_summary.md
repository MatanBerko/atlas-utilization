# H -> ZZ -> 4l Part B: split-sample test and 115-135 GeV fit

Cheap verification checks on the existing 535-candidate full-scale Part B
result — no new parsing, no cluster job, no data outside what's already on
Lustre. Ran interactively on wipp-an1 with `nice` (48s total). Script:
`scripts/higgs_4lepton_partB_splits.py`, reapplying the identical Part B
selection (Part A + sip3d<4, |dxy|<0.5 cm, |dz|<1.0 cm) via
`higgs_4lepton_partB_report.py`'s `load_events`/`build_selected_leptons`/
`run_selection`. Reproduced 535 primary candidates exactly, cross-checked
against the earlier full-scale run.

## Task 1: split-sample test

Two independent splits: era (2016G: records 30521/30522/30528, 241
candidates; 2016H: records 30554/30555/30561, 294 candidates) and
event-number parity (even: 268 candidates; odd: 267 candidates).

| Half | Candidates | 70-180 GeV | 118-130 GeV | 120.5-123.5 | **123.5-126.5** | 126.5-129.5 | Z1 purity |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2016G | 241 | 79 | 17 | 5 | **9** | 1 | 75.5% |
| 2016H | 294 | 80 | 22 | 1 | **14** | 4 | 80.6% |
| even | 268 | 78 | 19 | 4 | **10** | 3 | 77.6% |
| odd | 267 | 81 | 20 | 2 | **13** | 2 | 79.0% |

Plots: `plots/partB_split_era.png`, `plots/partB_split_parity.png`.

**The 91 GeV Z peak is present, clearly, in all four halves individually**
(75.5-80.6% purity in each — consistent with the combined sample's 78.3%,
no half stands out as anomalous).

**The 123.5-126.5 GeV window shows a local excess over its immediate
neighbors in all four halves, independently, in both splits:**
2016G (5, **9**, 1), 2016H (1, **14**, 4), even (4, **10**, 3), odd (2,
**13**, 2). Stated plainly, as asked: the feature is **not** confined to
one half of either split — it appears in both halves of the era split and
both halves of the parity split. This is reported as what is observed. It
is **not** a significance statement: each half has only 20-22 candidates
in the full 115-135 window and single-bin counts this low (single digits
to low teens) carry substantial statistical noise on their own — the
consistency across four independent halves is a real, notable observation
worth recording, but nothing here computes or implies a p-value,
significance, or sigma, and none should be inferred from this table.

## Task 2: Gaussian + flat-background fit, 115-135 GeV

Unbinned extended-maximum-likelihood fit (Gaussian signal + flat local
background, 43 candidates in [115,135] GeV). A parameter-estimation fit
only. Plot: `plots/partB_115_135_fit.png`.

| Parameter | Fitted value |
|---|---:|
| mean (mu) | 124.95 ± 0.35 GeV |
| width (sigma) | 1.31 ± 0.43 GeV |
| signal yield (n_sig) | 24.0 ± 5.2 |
| background yield (n_bkg) | 19.0 |

**Mean vs. the measured Higgs mass (125.25 GeV):** difference is 0.30 GeV,
well within the fitted 1-sigma uncertainty (0.35 GeV) — **consistent.**

**Width vs. expected CMS 4-lepton mass resolution (~1-2 GeV, somewhat
worse for 4e than 4mu):** the fitted 1.31 ± 0.43 GeV sits inside that
expected band. Given the candidate mix is majority 2e2mu/4e (311 of 535),
a resolution above the pure-4mu end of the range is physically reasonable.
**The fit is not absorbing background into an artificially broad
"signal"** — had that been happening, sigma would have come out far larger
than ~2 GeV; it did not.

**Signal yield (24.0 ± 5.2) is reported as a fitted value only.** It is
not a significance, is not divided by any uncertainty to form one, and no
p-value or sigma-significance is computed anywhere in this exercise — per
instruction, none should be inferred from this number either.

## Bottom line

Both checks are consistent with (not proof of) a real, narrow feature near
125 GeV sitting on top of the four-lepton continuum: it survives an era
split and a parity split independently, and an unbinned fit to its shape
returns a mean and width both consistent with expectations for the real
Higgs mass and CMS's 4-lepton resolution, not with the fit absorbing
background. None of this is a discovery claim or a significance
statement — no such calculation was performed, per instruction, and the
sample is small (43 candidates in the fit window, ~20 per half after
splitting).
