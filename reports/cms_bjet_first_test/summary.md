# CMS b-jet tagging — first test

**Date:** 2026-09-03
**Branch:** `upstream/bugfix-cherrypicks-pr17`
**Config:** `config.cms_bjet_test.yaml`
**Run dir:** `output/cms_bjet_test_20260903_124711/` (not committed — pipeline output)
**Raw check output:** [`bjet_check_output.txt`](bjet_check_output.txt) (from `scripts/bjet_check.py`)

## What this is

The CMS b-tagging code path (`FileParser._calculate_btagging_and_split`, which
splits the `Jets` collection into `Jets` + `BJets` using the per-jet DeepJet
discriminant `Jet_btagDeepFlavB`) had **never been enabled in any CMS config**
before this. This run turns it on for the first time and checks the output is
physically sensible — not whether it is analysis-grade.

## Setup

| | |
|---|---|
| Records | 30529 + 30562 (`/SingleElectron/Run2016G,H`), 2 files each |
| Events parsed | 6,393,572 (4/4 files, 100% success) |
| Events into mass-calc | 5,536,060 |
| b-tag algorithm | `Jet_btagDeepFlavB` (DeepJet / DeepFlavour, precomputed in NanoAOD) |
| b-tag threshold | **0.2598** — DeepJet *Medium* working point, UL2016 post-VFP |
| `objects_to_calculate` | Electrons, Muons, Jets, **BJets** |
| Stages | parsing + mass-calculation only (no post-processing / histograms) |
| Wall time | ~28 min (parsing ~3.5, mass-calc ~24.5) on one 7 GB container |

## Results

### 1. Some jets get tagged — a plausible fraction

| | count |
|---|---|
| non-b jets (`Jets` after split) | 10,583,754 |
| b-tagged jets (`BJets`) | 881,692 |
| **b-tag fraction** | **7.69%** of all reconstructed jets |

Not zero, not all. ~8% is the right order for a SingleElectron primary dataset
at the Medium WP: the sample is dominated by light-quark / gluon jets, with a
real-b minority from ttbar, single-top and heavy-flavour QCD.

### 2. b-jet combinations are produced

4,434 distinct `..._<Nb>b_..._IM_...` final-state/combination signatures with a
non-zero b count, **1,618,653 invariant-mass entries** in total. Channels seen
include `e0b0`, `j0b0`, `e0b0b1`, `e0j0b0`, `j0j1b0`, `j0b0b1b2`, `e0e1b0`,
`m0b0`, `m0j0j1b0`, etc. — i.e. the combinatorics enumerator treats `BJets` as a
first-class collection.

### 3. The invariant masses are physical

Broad continua that scale sensibly with the number of bodies combined:

| combination | n | median [GeV] | p05–p95 [GeV] |
|---|---:|---:|---:|
| `e0b0` | 260,358 | 59.8 | 6–435 |
| `j0b0` | 203,835 | 219.9 | 58–793 |
| `e0b0b1` | 42,775 | 193.2 | 64–747 |
| `e0j0b0` | 203,835 | 313.5 | 80–1044 |
| `j0j1b0` | 137,123 | 489.9 | 163–1326 |
| `j0j1j2b0` | 66,616 | 712.0 | 302–1802 |

- Overall b-jet mass: min −0.71, p01 = 5.5, median 308, p99 = 1978, max 7541 GeV.
- Only 23 negative values in 1.6M entries — normal float noise, no sign error.
- **Not an overlap spike.** The `<5 GeV` fraction is ~0 for essentially every
  b-jet channel (`e0b0`: 2.2%, most others 0%). Contrast the plain `e0j0`
  channel in the same run: median ~15–23 GeV, min ~0, dominated by ~0 GeV
  "self-pairs" (the known electron/jet reco-overlap artifact). Requiring a b-tag
  preferentially removes the electron-fake jets, so b-jet channels are much
  cleaner — a small extra sanity signal that the tag is doing something real.

## Confidence / caveats

Reported as **"looks like real physics, not noise or garbage"**, not as
validated:

- Small sample (4 files, ~5.5M events).
- No clean known-resonance cross-check — no visible top or W→jj peak at this
  statistics / 10 GeV binning, so we can't yet point at a mass and say "correct".
- Pure `b0b1` di-b-jet pairs were **not** produced: every event carries the
  required SingleElectron electron (`particle_counts.electrons.min = 1`), so a
  0-lepton di-b-jet final state cannot form. `b0b1` inside larger final states
  wasn't emitted either at this config's `min_events_per_fs`; multi-b channels
  like `e0b0b1` / `j0b0b1b2` are present and sane.
- Threshold 0.2598 is the standard Medium WP but was not tuned against a CMS
  b-tag efficiency measurement for these specific open-data files.

## Bottom line

The CMS b-tagging path runs end to end, tags a believable ~8% of jets, feeds
`BJets` through the combinatorics, and yields invariant-mass spectra with the
right shape and scale. Good enough to enable for exploratory work; a resonance
cross-check and a WP decision are still needed before it is analysis-grade.
