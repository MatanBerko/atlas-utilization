# DeepJet b-tagging: truth-based efficiency & mistag cross-check (simulated ttbar)

**Date:** 2026-09-07
**Branch:** `analysis/ttbar-btag-truth-crosscheck`
**Script:** `scripts/ttbar_btag_truth_crosscheck.py` (run under the WSL venv
`~/btag_work/venv` - XRootD has no Windows wheel, same setup as the raw
score-distribution work)
**Raw stats:** [`stats.json`](stats.json); per-flavour bin counts:
[`hist_cache_by_flavour.json`](hist_cache_by_flavour.json)

## Why this exists

Every prior b-tagging check in this project (`config.cms_bjet_test.yaml`, the
raw `Jet_btagDeepFlavB` score-distribution work) used **real CMS collision
data**, which has no generator-level truth. We could see the score's shape and
count jets above a cut, but never know what fraction of *actual* b-jets that
cut correctly tags, because real data carries no flavour label. A **simulated**
sample does: `Jet_hadronFlavour` is the generator-level truth per jet
(**5 = true b-jet, 4 = true c-jet, 0 = true light/gluon jet**), something real
Open Data events never have. This is the first time this project measures a
real, truth-based b-tagging efficiency instead of just describing a score
distribution.

**Dataset:** CERN Open Data record **67993**,
`/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM`
- simulated ttbar (semileptonic decay), **NANOAODSIM** (not NANOAOD - this is
Monte Carlo, not collision data), 144,722,000 events across 138 files.

**Threshold:** `Jet_btagDeepFlavB > 0.25` - the project-wide standardized
value (`config.cms_bjet_test.yaml`), no discrepancy to flag this time.

## Does MC access work the same way as real data? Yes, with two small differences

Checked directly before assuming anything:

- The file-listing API is identical: `https://opendata.cern.ch/record/67993/filepage/1?group=1`
  over plain HTTPS with normal certificate verification, returning the same
  `index_files.files[*].files[*].uri` structure the real-data script already
  parses generically.
- The files themselves are read the same way: `root://eospublic.cern.ch/...`
  XRootD, same host, same protocol, no new auth, no certificate issue. First
  file opened in 4.2 s; full-file reads of ~1.2-1.4 M events completed in
  26-45 s each - comparable to the real-data timings seen before.
- Both `Jet_btagDeepFlavB` and `Jet_hadronFlavour` (and `Jet_partonFlavour`,
  unused here) are present and readable exactly like any other `Jet_*` branch.

**Two differences worth noting, neither of which needed a workaround:**

1. The MC record's file index is split into **5 groups** (41/... files each)
   instead of the single group typically seen for a real-data record; the
   existing fetch code already iterates every group generically
   (`for idx in data["index_files"]["files"]`), so this needed no code change.
2. The XRootD path carries an extra `/mc/` segment:
   `.../eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/TTToSemiLeptonic_.../NANOAODSIM/...`
   versus the real-data `.../eos/opendata/cms/Run2016H/SingleMuon/NANOAOD/...`
   pattern. Purely a path difference; access mechanics are identical.

No certificate bypass, no DNS override, no alternate protocol - none were
needed.

## Scale used

**3 of 138 files** (2.2 % of the record), matching the "2-3 files" scale used
throughout this project's other btag/score work. Not scaled up further, per
instructions.

| file | events | jets |
|---|---:|---:|
| `08FCB2ED-...` | 1,233,000 | 9,163,488 |
| `0BD60695-...` | 1,365,000 | 10,146,749 |
| `4F3C361D-...` | 1,402,000 | 10,417,706 |
| **total** | **4,000,000** | **29,727,943** |

Score sanity check (same check as the real-data work): **0** jets with
`Jet_btagDeepFlavB < 0` or `> 1` out of 29,727,943; min 0.00096, max 0.99951.
`Jet_hadronFlavour` took only the three expected values (0, 4, 5) - 0 jets
with any other value.

## The score distribution, split by TRUE flavour

![DeepJet score by true flavour](plots/btag_score_by_true_flavour.png)

This is the real per-jet truth split, log-y, no kinematic cuts, no fabricated
data. The shapes are exactly what a working b-tagger should produce: true
light/gluon jets pile up sharply near 0 and fall away fastest; true b-jets are
broadly spread and rise again toward 1; true c-jets sit consistently between
the two. This alone is a real (if qualitative) confirmation that
`Jet_btagDeepFlavB` tracks true flavour correctly in this sample.

## The real, truth-based numbers at threshold 0.25

Two versions are reported. **"No cut"** is exactly what was asked for - every
jet, no kinematic selection. **"Eligible region"** (pT > 20 GeV, |eta| < 2.4)
is added as an honest cross-check: DeepJet is only calibrated within the
tracker acceptance and above a minimum jet pT, and that is the region official
CMS b-tag POG efficiency/mistag numbers are quoted for - comparing "no cut"
numbers to an official figure that was itself measured with a pT/eta cut is
not apples-to-apples.

| | true jets | tagged (score > 0.25) | **rate** |
|---|---:|---:|---:|
| **No kinematic cut** | | | |
| b-jets (efficiency) | 7,379,260 | 5,249,019 | **71.13 %** |
| c-jets (mistag) | 2,371,551 | 348,080 | **14.68 %** |
| light/gluon jets (mistag) | 19,977,132 | 480,991 | **2.41 %** |
| **pT > 20 GeV, \|eta\| < 2.4 (eligible region)** | | | |
| b-jets (efficiency) | 6,526,050 | 5,017,244 | **76.88 %** |
| c-jets (mistag) | 1,908,811 | 307,287 | **16.10 %** |
| light/gluon jets (mistag) | 11,714,711 | 304,470 | **2.60 %** |

(The no-cut sample includes very low-pT and forward, out-of-tracker-acceptance
jets, which DeepJet is not designed to tag well - that pulls the no-cut
b-efficiency down and is exactly why the eligible-region cross-check exists.)

## Comparison to the officially expected range (~75-80 % b-efficiency, ~1 % light mistag)

Stated plainly, not rounded to fit:

- **b-tagging efficiency: MATCHES, in the correct comparison region.**
  76.88 % (eligible region) falls inside the quoted 75-80 % range. The no-cut
  figure, 71.13 %, does **not** - but that comparison isn't fair to begin with,
  since the official range is itself quoted for jets in the tracker acceptance.
- **Light-jet mistag rate: does NOT match.** 2.41 % (no cut) and 2.60 %
  (eligible region) are both roughly **2.4-2.6x the commonly quoted ~1 %**,
  in the region that should be the fairer comparison. This is the real
  measured number from this sample at this threshold - it is not being
  rounded down to claim agreement.

**Plausible contributors to the elevated mistag rate** (stated as plausible,
not proven from this check alone):

- **The project's standardized 0.25 threshold is slightly below the CMS-published
  DeepJet Medium working point, 0.2598.** A lower cut mechanically accepts more
  jets on both sides - real b-jets *and* fakes - so it should read a bit above
  the officially quoted 0.2598-based numbers on both efficiency and mistag.
  This does not by itself explain the ~2.5x gap.
- **Only 3 of 138 files (2.2 %) were read.** The measured rates come from tens
  of millions of jets, so the statistical uncertainty on 2.4-2.6 % is far too
  small (well under 0.1 pp) to explain a ~1.5 percentage-point gap - this is
  not a small-sample fluctuation.
- **Sample- and pT-shape dependence.** Official light-mistag figures are often
  quoted for a specific pT-integrated ttbar reference sample/binning; DeepJet's
  light mistag is known to rise with jet pT, and this semileptonic-ttbar sample's
  light-jet pT spectrum (extra jets from ISR/FSR and the hadronic W) may not
  match whatever spectrum the quoted ~1 % figure was averaged over.
- That the *eligible-region* mistag (2.60 %) is higher than the *no-cut*
  mistag (2.41 %) - the opposite of the b-efficiency pattern - is consistent
  with this: central, higher-pT jets have more tracks and more chances to
  reconstruct a spurious displaced vertex, while many of the no-cut sample's
  forward/soft jets have too little tracking information to ever score high
  regardless of true flavour.

None of this was tuned or adjusted to move the answer closer to ~1 % - the
measured 2.4-2.6 % stands as reported.

## Caveats

- 3 files out of 138 (2.2 % of the record) - large enough that per-flavour
  counts run into the millions and statistical error is negligible, but still
  a small slice of one MC sample. Not re-run at larger scale per instructions.
- This is one physics process (semileptonic ttbar). Official b-tag POG
  calibration numbers are typically derived from combinations of multiple
  control samples and datasets; a single-sample, 3-file check is a
  cross-check, not a full calibration measurement.
- `Jet_partonFlavour` was also available but not used; `Jet_hadronFlavour` is
  the standard truth label for b/c/light classification and is what was asked
  for.

## Bottom line

The truth-based measurement works exactly as intended and gives a real answer
that real collision data cannot: at the project's standardized 0.25 threshold,
in the correct pT/eta comparison region, **DeepJet's b-tagging efficiency
(76.9 %) lands inside the officially expected ~75-80 % range**, but its
**light-jet mistag rate (2.6 %) is about 2.5x higher than the commonly quoted
~1 %**, and that gap is real, not a rounding or statistics artifact. The
score-vs-truth plot itself is unambiguous: the tagger clearly separates b from
light, with c in between, exactly as it should - the discrepancy is in the
precise mistag *rate*, not in whether the tagger is working.
