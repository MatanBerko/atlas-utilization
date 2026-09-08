# H -> ZZ -> 4l, Part A: cheap background-rejection cuts (existing data, no re-parse)

Branch: `analysis/higgs-4lepton-clean`, off `analysis/higgs-4lepton-zz`
(`60de373`). Run over the existing full-scale parsed output
(`output/cms_higgs_4lepton_fullscale_20260908_150157`) — **no re-download,
no re-parse**, per instruction. Script: `scripts/higgs_4lepton_clean_report.py`
(extends `scripts/higgs_4lepton_zz_report.py`, reusing its
`load_events`/`find_z1_z2`/`four_vector_mass` rather than rewriting them).

## Diagnosis recap

392 candidates in 115-135 GeV vs. CMS's published 8 events in 118-130 GeV at
13 TeV, with less integrated luminosity than this dataset — a
background-rejection problem, not a statistics problem. Part A applies the
cuts possible with data already on disk (no impact-parameter variables
available yet — that's Part B).

## A1 + A2: cut-flow, showing each cut's individual effect

| Stage | Combined (all 6 records) |
|---|---:|
| after parse-time selection | 13,579,052 |
| >=4 quality leptons | 24,253 |
| exactly 4, charge 0 | 13,265 |
| **A1: low-mass veto (every OS pair > 4 GeV)** | **4,835** |
| A2: ghost removal (deltaR > 0.02, every pair) | 4,757 |
| pT thresholds (20/10 GeV) | 3,692 |
| **final candidates (valid Z1/Z2)** | **1,702** |

Plot: `plots/partA_cutflow.png` (per-record + combined).

**A1 does almost all of the work; A2 is minor.** The low-mass resonance veto
alone removes 63.5% of the "exactly 4, charge 0" population (13,265 →
4,835) — a huge effect, meaning a large fraction of raw 4-lepton
combinations at this stage contain a spurious near-zero/low-mass
opposite-sign pair (photon conversions, soft QCD, or genuine low-mass
resonances faking part of a "Z" pair). Ghost removal on top removes only a
further 1.6% (4,835 → 4,757) — a real but small additional effect, since
duplicate/split-track reconstruction is comparatively rare once the
low-mass veto has already cleaned up the sample.

**Net effect on the two headline numbers:**

| | Baseline (no A1/A2) | Cleaned (+A1 +A2) | Change |
|---|---:|---:|---:|
| Final candidates | 2,216 | 1,702 | −23.2% |
| 115-135 GeV | 392 | 311 | −20.7% |
| 118-130 GeV | 251 | 202 | −19.5% |
| m_Z1 in [85,97] GeV (validation peak) | 1,255/2,216 (56.6%) | 1,168/1,702 (**68.6%**) | **purity improved** |

The Z1 validation peak's **fraction increased** with cleaning (56.6% →
68.6%), not decreased — a good sign these cuts remove background rather
than genuine Z-pair candidates. Plot: `plots/partA_z1_validation.png`
(peak clearly survives, sharp and undiminished in shape).

Mass-spectrum comparison: `plots/partA_mass_baseline_vs_cleaned.png` — the
cleaned (blue) spectrum sits uniformly below the baseline (red) across the
*entire* 70-180 GeV range, roughly proportionally, not concentrated at any
particular mass. This is consistent with A1/A2 removing a fairly uniform
background admixture rather than sculpting the mass shape.

Channel breakdown after cleaning: `plots/partA_channel_breakdown.png` —
925 4mu, 630 2e2mu, 147 4e (total 1,702).

## A3: isolation working-point scan (A1+A2 applied, electron cutBased>=2 fixed)

| Isolation WP | Final candidates | 115-135 GeV | 118-130 GeV | Z-peak purity |
|---|---:|---:|---:|---:|
| < 0.35 (current) | 1,702 | 311 | 202 | 68.6% |
| < 0.20 | 1,283 | 218 | 144 | 72.6% |
| < 0.15 | 1,116 | 184 | 124 | 73.3% |

Tightening isolation from 0.35 → 0.15 removes a further 34.4% of candidates
(1,702 → 1,116) and steadily improves Z-peak purity (68.6% → 73.3%) — a
real, physically-motivated effect: heavy-flavor-decay leptons sit inside
jets and preferentially fail tight isolation.

## A4: electron ID scan (A1+A2 applied, isolation < 0.35 fixed)

| Electron cutBased | Final candidates | 115-135 GeV | 118-130 GeV | Z-peak purity |
|---|---:|---:|---:|---:|
| >= 2 (loose, current) | 1,702 | 311 | 202 | 68.6% |
| >= 3 (medium) | 1,443 | 282 | 185 | 70.5% |

Tightening electron ID from loose to medium removes 15.2% of candidates
(1,702 → 1,443) — a smaller effect than the isolation scan. This makes
sense: cutBased loose-vs-medium mostly differs in shower-shape/track-match
quality cuts, which are less directly tied to heavy-flavor rejection than
isolation is.

**Isolation is the more effective lever of the two scanned here**, but
neither closes the gap to CMS's published figure on its own (see below).

## The two mass histograms (Part A cleaned selection)

| Binning | Entries in [70,180] | Bins | Meets >30 bins? | Meets >=100 entries? |
|---|---:|---:|---|---|
| 3 GeV (37 bins) | 1,084 | 37 | **PASS** | **PASS** |
| 4 GeV (28 bins) | 1,084 | 28 | **FAIL** | PASS |

**The 4 GeV variant does not meet BumpNet's bin-count bar.** `(180-70)/4 =
27.5`, rounding to 28 bins — below the required >30. Even though a coarser
binning might look visually smoother, it is not a valid choice against
BumpNet's own stated usability threshold, so the 3 GeV binning remains the
one to use going forward; the 4 GeV histogram is reported here for
completeness (as asked) but is not recommended.

## Does 392→311 (or 251→202) close the gap to CMS's 8? No — not close.

Even at the most aggressive individual working point examined (isolation
< 0.15, still with electron cutBased >= 2), **118-130 GeV still has 124
candidates — about 15.5x CMS's published 8**, with less luminosity. **The
cheap cuts alone materially reduce the background (roughly 20-35% depending
on which knob is pushed) but do not come close to closing a >10x gap.**
This confirms the diagnosis: the missing ingredient is genuinely the
impact-parameter suppression of heavy-flavor-decay leptons (Part B), not
something reachable by tightening the cuts already available in the parsed
data. No cut combination examined here was pushed to try to manufacture a
smaller number artificially — these are the real counts at each stated
working point.

## Recommendation for Part B's working point

Given A3 shows isolation is the stronger lever and A4 shows electron ID
medium helps less, but Part B's own new cut (impact parameter) is expected
to be the dominant remaining suppression — **recommend carrying forward the
current, already-used working points (isolation < 0.35, electron
cutBased >= 2) plus A1 and A2 into Part B**, rather than also tightening
isolation/ID further at this stage. Reasoning: stacking multiple
independent tightenings at once (isolation, electron ID, AND impact
parameter) would make it hard to attribute Part B's effect cleanly to the
impact-parameter cut specifically, which is the new physics ingredient this
exercise is actually testing. If the impact-parameter cut alone does not
close the gap, tightening isolation/ID further remains available as a
follow-up, now that its individual effect size is known from this scan.

## Bottom line for Part A

The cheap cuts helped, materially but not decisively: low-mass veto (A1) is
doing real, substantial work (removing well over half of the naive
"exactly-4/charge-0" combinatoric background), ghost removal (A2) is a
small additional refinement, and the Z1 validation peak survives and even
sharpens under cleaning — confirming these cuts are removing background,
not signal-like content. But the fundamental >10x excess over CMS's
published result remains after Part A, exactly as diagnosed: the missing
ingredient is the impact-parameter cut, which requires data not currently
in the parsed output. Proceeding to Part B as planned.
