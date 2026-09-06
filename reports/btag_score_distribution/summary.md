# CMS raw b-tag discriminant (`Jet_btagDeepFlavB`) distribution

**Date:** 2026-09-06 (revised same day: WP-line label + ATLAS-comparison note +
explicit negative/sentinel-value check)
**Branch:** `analysis/btag-score-distribution`
**Script:** `scripts/btag_score_distribution.py` (run under the WSL venv
`~/btag_work/venv` - XRootD has no Windows wheel)
**Raw stats:** `stats.json`; cached bin counts for re-plotting: `hist_cache.json`

## Why this exists

The existing CMS b-jet work (`reports/cms_bjet_first_test/`,
branch `test/cms-bjet-with-histograms`) confirms b-tagging runs and tags
~7.69 % of jets at the DeepJet **Medium** working point
(`Jet_btagDeepFlavB > 0.2598`). Before b-tagging is considered for real
production scope, Maryna asked to see the **raw discriminant score itself** -
its shape, and where the 0.2598 cut sits in it - so it can be eyeballed against
how ATLAS defines its own operating points (efficiency-defined, e.g. "77 %";
this repo's `config.yaml` uses a DL1d threshold of 2.51 for that purpose).

The pipeline parser only ever stores the final tagged/untagged split, so the
score was re-read directly from the CERN NanoAOD source files - **the exact same
files the existing b-jet test uses**: records 30529 + 30562
(`/SingleElectron/Run2016G,H`), first 2 files each (matching
`config.cms_bjet_test.yaml`'s `max_files_to_process: 2`). No tagging cut, no
selection, no extra files fetched.

## What was read

| record | files | events | jets |
|---|---:|---:|---:|
| 30529 (SingleElectron Run2016G) | 2 | 1,195,734 | 5,207,157 |
| 30562 (SingleElectron Run2016H) | 2 | 5,197,838 | 23,446,299 |
| **total** | **4** | **6,393,572** | **28,653,456** |

(6,393,572 events matches the b-jet first test's parse exactly.)

### Negative / sentinel values

NanoAOD stores **-1** for `Jet_btagDeepFlavB` on jets where DeepJet was not
evaluated (e.g. jets outside the tracker acceptance or below the algorithm's
minimum pt). We checked for these explicitly - both `score < 0` and the
never-expected `score > 1`:

| | count |
|---|---:|
| jets with score < 0 (NanoAOD -1 sentinel) | **0** |
| jets with score > 1 | **0** |
| jets with a valid score in [0, 1] | **28,653,456 (all of them)** |

`min` = 0.00093, `max` = 0.99951. So nothing had to be excluded and the
histogram below covers the complete jet set. (`stats.json` records this per
record too; the script would annotate the plot and exclude them from the [0, 1]
histogram if any were present.)

## The distribution - all 28.65M jets

![raw discriminant, all jets, log-y](plots/btag_score_all.png)

**Where the bulk sits:** overwhelmingly near zero. Median **0.047**;
**54.6 %** of jets are below 0.05 and **87.4 %** below 0.10. Percentiles:
p75 = 0.066, p90 = 0.116, p95 = 0.201, p99 = 0.732. That low-score peak is the
light-quark and gluon jets, which dominate any inclusive jet sample.

**Shape (log-y):** a sharp peak at ~0.03-0.06, then a steep, roughly monotone
fall-off across two orders of magnitude, down to a broad shallow **minimum
around 0.70-0.85**, and then a **clear rise back up toward 1.0** with a spike in
the last bin (0.99-1.0). So it is **bimodal**, not a smooth falling tail: a big
light-jet peak at ~0 and a much smaller genuine b-jet accumulation near 1,
separated by a low-density valley. This is the textbook shape of a well-behaved
b-vs-all discriminant on real data.

**Where the Medium WP (0.2598) sits:** out on the falling tail of the light-jet
peak, between the 95th and 99th percentile of all jets. At that point the
light-jet contribution has dropped ~2 orders of magnitude from its peak but is
still well above the valley floor, so the selected region (score > 0.2598) is a
mix - the tail of the light-jet fall-off plus the rising b-jet population, with
b's only clearly dominating above ~0.85. The dashed line is labelled
"DeepJet Medium WP = 0.2598 (~75-80% b-eff in ttbar MC, per CMS BTV)" - see the
comparison note below for what that efficiency figure means.

### How the CMS Medium WP compares to ATLAS's 77% operating point

CMS and ATLAS define their "medium"-style b-tag cuts with **different design
philosophies but land in a similar practical zone**. CMS's DeepJet Medium
working point is fixed by a **target light-flavour mistag rate (~1%)**, not by a
b-jet efficiency directly; the b-jet efficiency that results from that choice,
per CMS's own published ttbar-based measurements, works out to roughly
**75-80%**. ATLAS's DL1d 77% operating point (`config.yaml`, `DL1d: 2.51`) is
instead defined **directly as a target b-efficiency of 77%**. So the two are
comparable in spirit and end up in a similar practical efficiency range, even
though one is anchored on mistag rate and the other on b-efficiency.

We **cannot** draw a matching "77%-of-true-b-jets" line on this histogram
ourselves: that requires generator-level (MC truth) flavour labels to know which
jets are really b-jets, and real CMS Open Data collision events do not carry
them. The ~75-80% figure above comes from each experiment's own
separately-published, simulation-based efficiency measurements - it is **not**
derived from this real-data plot.

**How many the cut selects:**

| | jets | above 0.2598 | below |
|---|---:|---:|---:|
| all jets (no selection) | 28,653,456 | **1,046,614 (3.65 %)** | 27,606,842 (96.35 %) |
| jets with pt > 30 GeV & \|eta\| < 4.5 | 13,077,292 | 610,932 (4.67 %) | 12,466,360 |

### Why this isn't the b-jet test's 7.69 %

The b-jet test reports 7.69 % tagged; the pt/|eta|-cut number here is 4.67 %.
That is expected, not a discrepancy: the b-jet test **additionally** applies its
event selection - `particle_counts.electrons.min: 1` (a good electron, pt > 25,
on an electron-triggered dataset) - which enriches the surviving events in
b-jet-producing processes (ttbar, single top, W+jets), lifting the b-content of
the jets in those events. This histogram deliberately includes **every** jet
regardless of the rest of the event, so its tagged fraction is lower. The
electron event selection was not re-applied here: the ask was "every jet, before
any tagging cut", and reproducing 7.69 % exactly is not the goal.

## Split by record: Run2016G vs Run2016H

The existing b-jet test scope is **SingleElectron only** (records 30529, 30562).
It contains **no SingleMuon files**, so a true SingleElectron-vs-SingleMuon
stream comparison is not possible without fetching data outside this task's
scope. The split that *is* available is the two SingleElectron run eras:

![raw discriminant, by record](plots/btag_score_by_record.png)

| | jets | median | p99 | frac > WP |
|---|---:|---:|---:|---:|
| 30529 SingleElectron Run2016G | 5,207,157 | 0.0459 | 0.717 | 3.58 % |
| 30562 SingleElectron Run2016H | 23,446,299 | 0.0467 | 0.736 | 3.67 % |

**The two shapes are indistinguishable.** Normalised, the two histogram traces
sit on top of each other across the whole 0-1 range (see plot). Median differs
by 0.0008; the fraction above the WP differs by 0.09 percentage points. There is
**no meaningful difference between the two run eras** - stated plainly, not
manufactured.

## Caveat - what this plot is and is not

This is **real collision data with no generator-level (MC truth) labels**. We
can see exactly where the CMS Medium-WP cut falls in the discriminant
distribution and what fraction of jets it selects - a useful visual and sanity
check of *where the cut sits*. It is **not** a cross-experiment calibration
proof and it does **not** show *that* the CMS and ATLAS "medium" cuts are
efficiency-equivalent. The ~75-80% b-efficiency for CMS's Medium WP and the 77%
for ATLAS's DL1d point (see the comparison note above) both come from each
experiment's own separately-published, MC-calibrated measurements - neither is
derivable from this real-data histogram, and we did not compute any new
threshold from the data (the 0.2598 cut is unchanged).

## Connectivity note

A prior attempt at this task was blocked: XRootD port 1094 to
`eospublic.cern.ch` was unreachable (socket timeout) and HTTPS separately hit a
TLS-interception (self-signed certificate in the chain), which was not bypassed.
On the last two sessions' network, TCP to `eospublic.cern.ch:1094` connects
normally and the four files read in ~15-30 s each. The earlier block was this
machine's network path, not CERN's side.
