# rare4 task, Step 6: full quality-gate report

Combined DoubleMuon+SingleMuon trigger-matched BumpNet delivery, rare4
final-state version -- **Version B** of the group's two candidate
readings (the other, already delivered, is nonjet4/Version A). Every
number below is **VERIFIED BY RUNNING** (script + evidence file cited);
see `scripts/` for every script used to produce this report and
`README.txt` for the delivered files themselves. This is NOT a decision
between the two readings -- both are presented ready for the group to
choose.

## The rule

Trigger matching, DoubleMuon acceptance, the SingleMuon veto and the
>=2-selected-objects gate are evaluated on the full event, exactly as
for normal/top-4/nonjet4, BEFORE this rule. Let N = (selected electrons
+ selected muons + selected b-jets), using the TRUE per-event counts
(never a display-capped label).

- If N > 4: the event is **REJECTED** entirely -- the identical rule and
  identical rejected-event set as nonjet4.
- If N <= 4: keep EVERY selected object, INCLUDING every light jet,
  completely unpadded/untruncated, then proceed exactly as the existing
  NORMAL version already does (same final-state labelling with its own
  existing display-cap-at-4 convention, same combinations).

**rare4 = the normal version with true-N>4 events removed.** Full
validation: `RARE4_STEP2_VALIDATION.md` (4 pilot files) and
`RARE4_STEP4_IDENTITY_CHECKS.md` (full 209-job production run).

## Rejected events and their composition (full production run)

Since rare4 shares nonjet4's identical N>4 rule and identical accepted-
event population, the rejected-event set and its composition are
IDENTICAL to nonjet4's own already-published numbers (confirmed directly
in Step 4: total rare4 rejected == total nonjet4 rejected == 5,738,
exact match).

| Dataset | Accepted (pre-rule) | Rejected (N>4) | Rejected fraction |
|---|---|---|---|
| DoubleMuon | 9,449,024 | 1,113 | 0.01178% |
| SingleMuon | 163,146,091 | 4,625 | 0.00283% |
| **Combined** | **172,595,115** | **5,738** | **0.00332%** |

Composition of the 5,738 rejected events (identical to nonjet4's, see
`studies/cms_datasets/deliver/committed/muon_combined_nonjet4/nonjet4_full_dataset_aggregate.json`):
N=5 in 5,455/5,738 (95.1%) of cases; driven mostly by b-jet multiplicity
(3+ b-jets in 5,555/5,738 = 96.8% of rejected events) rather than lepton
multiplicity.

## Hidden cases: zero

A "hidden" case is a rejected event whose DISPLAY-CAPPED label would
read e+m+b<=4 (e.g. 5 muons shown as "4m"), which would make rare4's own
histogram-name comparison against a name-filtered normal file diverge
from the true rejection. **Full-dataset count: 0** (confirmed in Step 4,
summed over all 209 jobs). Why this is exactly zero, not just small:
every accepted event in this dataset has **at least 1 selected matched
muon** (DoubleMuon requires >=2, SingleMuon requires >=1), so a hidden
case -- which needs the OTHER two object types to both be exactly 0
while one type is capped at 4 -- can only arise from a rejected event
with >=5 muons, 0 electrons, 0 b-jets. The rejected-event muon-count
distribution tops out at 4 muons (10 such events) -- no rejected event
in this entire 209-file dataset ever has 5 or more muons -- so this
scenario simply never occurs here.

## Full funnel for rare4

Script: `scripts/rare4_funnel_breakdown.py`; evidence:
`funnel_breakdown_readonly.json`. Same read-only methodology as the
nonjet4 task's own `FUNNEL_BREAKDOWN.md` (the per-final-state prune runs
only on scratch copies, never the real shards).

| Stage | Description | Combined (delivered) |
|---|---|---|
| (a) | Distinct histogram names with >=1 pooled raw event, before any cut | **2,280** |
| (a2) | Of those, names whose OWN pooled raw array has >=100 entries | **1,048** |
| (b) | After the real >=100-events-per-final-state prune | **1,048** |
| (c) | After post-processing (>=100 events in the main range) | **1,004** |
| (d) | Of (c), >25 filled bins (min26bins) | **960** |
| (d') | Of (c), >30 filled bins (min31bins) | **928** |

**(b), (c), (d), (d') exactly match `build_summary_rare4.json`'s own
1,048/1,004/960/928** -- confirmed by re-running the same shared funnel
code on the same pooled shards, not reimplementing it. As with nonjet4, (a2) and
(b) are not just equal in count (1,048) but were confirmed to be the
exact same 1,048-strong set of histogram names (same reasoning: every
final-state category in this dataset has every combination computable
for every one of its own events, so a per-name raw-entry threshold and a
per-final-state threshold agree exactly).

## Count table: histograms at >25 and >30 filled bins, all four versions

Script: `scripts/build_summary_table_rare4.py`. Counts only for rows
2-5 (no new ROOT files) -- funnel run independently per row.

**>30 bins (min31bins):**

| Row | normal | top-4 | nonjet4 | rare4 |
|---|---|---|---|---|
| Combined (delivered) | 1,025 | 147 | 148 | **928** |
| DoubleMuon alone | 339 | 55 | 55 | 322 |
| SingleMuon alone | 1,022 | 148 | 148 | 923 |
| Record 30522 alone | 260 | 46 | 46 | 260 |
| Record 30555 alone | 278 | 47 | 47 | 278 |
| Record 30530 alone | 844 | 137 | 137 | 816 |
| Record 30563 alone | 879 | 139 | 139 | 856 |

**>25 bins (min26bins):**

| Row | normal | top-4 | nonjet4 | rare4 |
|---|---|---|---|---|
| Combined (delivered) | 1,097 | 161 | 159 | **960** |
| DoubleMuon alone | 367 | 63 | 61 | 341 |
| SingleMuon alone | 1,095 | 160 | 159 | 959 |
| Record 30522 alone | 285 | 52 | 52 | 284 |
| Record 30555 alone | 298 | 54 | 54 | 290 |
| Record 30530 alone | 905 | 141 | 141 | 855 |
| Record 30563 alone | 935 | 144 | 144 | 891 |

Rows do not add up to the Combined row (each row is its own
independently-run funnel, same caveat as the earlier reports). rare4
sits, as expected, between normal (which keeps every event) and top-4/
nonjet4 (which both cap total objects at 4) -- rare4 keeps far more
objects per event than top-4/nonjet4 (hence far more histograms survive
than those two), but strictly fewer raw events than normal per category
(hence somewhat fewer histograms than normal, from the 5,738 events it
alone removes).

## rare4 vs. the name-filtered normal file

A quick name-filter of the already-delivered normal file (removing every
final state whose label shows e+m+b>4) predicted **960 histograms at
>25 bins and 928 at >30 bins**. rare4's own build produced **exactly**
960 and 928 -- **zero differences** at either threshold (script:
`scripts/compare_rare4_vs_filtered_normal.py`):

```
min31bins: name-filtered normal = 928, rare4 = 928, differences = 0
min26bins: name-filtered normal = 960, rare4 = 960, differences = 0
```

This exact match (not just "very few") follows directly from the zero
hidden-case count above -- with no hidden cases anywhere in the full
dataset, rare4's own histogram-name set is guaranteed identical to the
name-filtered normal set, with no exceptions to explain.

## nonjet4 vs. rare4: a plain-language side-by-side

Both versions reject the SAME events (true N>4). They differ only in
what a KEPT event's light jets look like. Concrete example, both
genuinely delivered histograms (real data, not illustrative):

**"2 muons + 1 b-jet + 1 light jet" (nonjet4's own category:
`..._cat_0ex_2mx_1jx_0gx_0tx_1bx`)** -- nonjet4 pads every kept event up
to 4 total objects, so an event with 2 muons + 1 b-jet + (any number of)
light jets is truncated down to exactly 1 light jet (2+1+1=4). 11
combinations survive in this category, e.g. `mass_m0m1j0` with 75,402
events (107 filled bins).

**"2 muons + 1 b-jet + 4(+) light jets" (rare4's own category:
`..._cat_0ex_2mx_4jx_0gx_0tx_1bx`)** -- rare4 keeps ALL of that same
event's light jets (2+1+4-or-more = 7+ total objects), so this is a
genuinely DIFFERENT, smaller population (only events with >=4 light
jets, not every 2mu+1b event) with MORE object slots available for
combinations -- 30 combinations survive here (vs. 11 for nonjet4's
version), including ones nonjet4 can never build at all, like
`mass_m0j0j1b0` (2 jets combined with a muon and a b-jet, 2,104 events,
133 filled bins) since nonjet4 only ever keeps 1 light jet in this
composition. In short: nonjet4's category groups together ALL 2mu+1b
events regardless of extra jets (and only shows you 1 jet's worth of
combinations); rare4's category is the SPECIFIC, genuinely jet-rich
subset (>=4 light jets), with the full jet-jet combinatorics intact.

## Z peak check, combined rare4 raw m(mu0,mu1)

Script: `scripts/build_resonance_check_rare4.py`. Read directly from the
RAW per-event masses in the rare4 shards, BEFORE post-processing.
Evidence: `resonance_check.json`, `plots/plots_z_peak.png`.

- Total combined raw m(mu0,mu1) entries: 10,481,628 (DoubleMuon:
  9,447,911; SingleMuon exclusive: 1,033,717) -- identical to nonjet4's
  own numbers (the rejected events are far too rare to move this).
- Gaussian fit in the 70-110 GeV window (9,794,988 entries): mean =
  90.847 +/- 0.036 GeV, sigma = 2.104 +/- 0.038 GeV -- consistent with
  the PDG Z mass, and identical (to displayed precision) to nonjet4's
  own fit.

## Required plots (all committed under `plots/`)

- `plot_rare4_1_largest.png` -- largest histogram by event count.
- `plot_rare4_2_median.png` -- median histogram by event count.
- `plot_rare4_3_near_25bin_boundary.png` -- near the 25-bin boundary.
- `plot_rare4_one_muon_4j_1.png`, `_2.png`, `_3.png` -- the 3 largest
  one-muon categories that ALSO show 4(+) light jets (172 such
  categories exist at the >30-bin threshold) -- a rare4-specific
  showcase, since nonjet4 never produces a genuine ">=4 light jets"
  category at all.
- `plot_rare4_crop_comparison.png` -- uncropped vs. cropped, same
  histogram.
- `plots_z_peak.png` -- the Z-peak check.

## Overall result: PASS, full delivery verified, ready for the group's decision.
