# nonjet4 task, Step 6: full quality-gate report

Combined DoubleMuon+SingleMuon trigger-matched BumpNet delivery, nonjet4
final-state version. Every number below is **VERIFIED BY RUNNING** (script
+ evidence file cited); see `scripts/` for every script used to produce
this report and `README.txt` for the delivered files themselves.

## The rule

Given to us by the group (Shikma, from the ATLAS BumpNet analysers), built
on top of the existing top-4 truncation. Trigger matching, DoubleMuon
acceptance, the SingleMuon veto and the >=2-selected-objects gate are
evaluated on the full event, exactly as for the normal and top-4
versions, BEFORE this rule. Let N = (selected electrons + selected muons
+ selected b-jets) for an already-accepted event -- light jets never
count toward N and never cause rejection.

- If N > 4: the event is **REJECTED** entirely (no final-state category,
  no combinations).
- If N <= 4: ALL selected electrons, muons and b-jets are kept, and
  selected light jets are added, in decreasing pT order, until the total
  kept-object count reaches 4 (or there are no more light jets).

This is identical to top-4 for every event with N<=4; the only difference
is that N>4 events are rejected instead of truncated. Full validation:
`studies/cms_datasets/matching/nonjet4/NONJET4_STEP2_VALIDATION.md` (4
pilot files) and `NONJET4_STEP4_IDENTITY_CHECKS.md` (full 209-job
production run).

## Rejected-event fraction and composition (full production run)

Script: `scripts/aggregate_nonjet4_stats.py`, reading every one of the
209 jobs' own `nonjet4_diagnostics`. Evidence:
`nonjet4_full_dataset_aggregate.json`.

| Dataset | Accepted (pre-rule) | Rejected (N>4) | Rejected fraction | Kept events with light jets dropped | Dropped fraction (of kept) |
|---|---|---|---|---|---|
| DoubleMuon | 9,449,024 | 1,113 | 0.01178% | 127,000 | 1.3442% |
| SingleMuon | 163,146,091 | 4,625 | 0.00283% | 1,223,059 | 0.7497% |
| **Combined** | **172,595,115** | **5,738** | **0.00332%** | **1,350,059** | **0.7822%** |

Rejected-event composition, summed across all 209 jobs:

| N (e+m+b) | Events | | Electrons | Events | | Muons | Events | | B-jets | Events |
|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 5,455 | | 0 | 4,353 | | 1 | 3,441 | | 1 | 31 |
| 6 | 273 | | 1 | 1,335 | | 2 | 2,215 | | 2 | 152 |
| 7 | 9 | | 2 | 49 | | 3 | 72 | | 3 | 3,233 |
| 8 | 1 | | 3 | 1 | | 4 | 10 | | 4 | 2,226 |
| | | | | | | | | | 5 | 94 |
| | | | | | | | | | 6 | 1 |
| | | | | | | | | | 7 | 1 |

The overwhelming majority of rejections (5,455/5,738 = 95.1%) are the
minimal N=5 case; rejections driven by b-jet multiplicity (3+ b-jets in
5,555/5,738 = 96.8% of rejected events) dominate over lepton multiplicity
-- consistent with this being a b-tagging-rich control region rather than
a high-lepton-multiplicity one. Full distributions in
`nonjet4_full_dataset_aggregate.json`.

The rejection rate (0.0033% combined) is far smaller than top-4's own
truncation rate (~0.75-1.4%, see the top-4 task's own
`TOP4_STEP2_VALIDATION.md`) -- expected, since N excludes light jets
entirely (the most common "extra" object), so only the rarer lepton/
b-jet-heavy tail is removed. The light-jet-drop rate among KEPT nonjet4
events (0.78% combined) is essentially top-4's own truncation rate,
since the two rules are identical for N<=4 events.

## Count table: histograms at >25 and >30 filled bins

Script: `scripts/build_summary_table_nonjet4.py`. Counts only for rows
2-5 (no new ROOT files) -- funnel run independently per row, same
thresholds/post-processing as the real delivery.

**>30 bins (min31bins):**

| Row | normal | top-4 | nonjet4 |
|---|---|---|---|
| Combined (delivered) | 1,025 | 147 | **148** |
| DoubleMuon alone | 339 | 55 | 55 |
| SingleMuon alone | 1,022 | 148 | 148 |
| SingleMuon exclusive alone | 841 | 131 | 131 |
| Record 30522 alone | 260 | 46 | 46 |
| Record 30555 alone | 278 | 47 | 47 |
| Record 30530 alone | 844 | 137 | 137 |
| Record 30563 alone | 879 | 139 | 139 |

**>25 bins (min26bins):**

| Row | normal | top-4 | nonjet4 |
|---|---|---|---|
| Combined (delivered) | 1,097 | 161 | **159** |
| DoubleMuon alone | 367 | 63 | 61 |
| SingleMuon alone | 1,095 | 160 | 159 |
| SingleMuon exclusive alone | 899 | 137 | 137 |
| Record 30522 alone | 285 | 52 | 52 |
| Record 30555 alone | 298 | 54 | 54 |
| Record 30530 alone | 905 | 141 | 141 |
| Record 30563 alone | 935 | 144 | 144 |

**Rows do not add up to the Combined row** -- DoubleMuon-alone +
SingleMuon-exclusive-alone (or the two records of either dataset) is NOT
expected to equal Combined, since each row is its own independently-run
funnel (different post-processing peak-selection/thresholds per
population) -- this is the same caveat the top-4 task's own table
carried, unchanged here.

## Which histogram names differ between top-4 and nonjet4, and why

Combined row only (the only row a real ROOT file exists for); full name
lists in `summary_table_names.json`.

**>30 bins:** nonjet4 has ONE histogram top-4 does not:
`mass_m0m1b0_cat_1ex_2mx_0jx_0gx_0tx_1bx` (top-4: 172 events, 27 filled
bins -- below the >30 threshold; nonjet4: 202 events, 31 filled bins --
above it).

**>25 bins:** top-4 has TWO histograms nonjet4 does not:
`mass_e0m1b0_cat_1ex_2mx_0jx_0gx_0tx_1bx` (top-4: 179 events, 26 bins)
and `mass_m0m1m2_cat_0ex_3mx_0jx_0gx_0tx_1bx` (top-4: 169 events, 26
bins) -- both absent from nonjet4's own survivor set entirely.

**Why nonjet4 can have MORE bins/events than top-4 for the SAME
signature, even though nonjet4's raw array is always a sub-multiset of
top-4's (proven in Step 2/4 checks (b)):** the post-processing chain
(Z-peak cut, rightmost-highest-peak selection, first-empty-bin split)
is applied to the FULL raw pooled array for a signature and is not a
monotonic function of that array's contents -- it picks out one
contiguous "main" mass island and discards the rest as outliers. The
handful of extra events top-4 keeps (truncated, from N>4 events that
nonjet4 rejects) can sit in a different part of the mass spectrum and
shift which island the peak-finder selects as "main," occasionally
producing a WORSE (fewer bins/events) result for top-4 than for nonjet4
on the same signature, or vice versa. All 3 signatures above are exactly
at their respective boundary (26/27/31 bins against a 25/25/30
threshold) -- borderline cases are the ones most sensitive to this
effect; no non-borderline signature changed classification.

## Lepton-content breakdown (combined row)

| | one-muon | 2+ muons | with electron(s) |
|---|---|---|---|
| normal, >30 bins | 682 | 343 | 357 |
| normal, >25 bins | 720 | 377 | 386 |
| top-4, >30 bins | 92 | 55 | 53 |
| top-4, >25 bins | 95 | 66 | 63 |
| nonjet4, >30 bins | 92 | 56 | 54 |
| nonjet4, >25 bins | 95 | 64 | 62 |

nonjet4's breakdown tracks top-4's closely (as expected, since the two
rules agree for the vast majority of events) with small shifts of +/-1-2
histograms per category from the handful of borderline signatures
discussed above.

## Z and J/psi resonance check, combined nonjet4 raw m(mu0,mu1)

Script: `scripts/build_resonance_check_nonjet4.py`. Read directly from
the RAW per-event masses in the nonjet4 shards (DoubleMuon inclusive +
SingleMuon exclusive), BEFORE post-processing (which would otherwise
remove the Z peak, below the 115 GeV z-peak cutoff, and the J/psi
entirely). Evidence: `resonance_check.json`, `plots/plots_z_peak.png`,
`plots/plots_jpsi_window.png`.

- Total combined raw m(mu0,mu1) entries: 10,481,628 (DoubleMuon:
  9,447,911; SingleMuon exclusive: 1,033,717).
- **Z peak:** Gaussian fit in the 70-110 GeV window (9,794,988 entries):
  mean = 90.847 +/- 0.036 GeV, sigma = 2.104 +/- 0.038 GeV -- consistent
  with the PDG Z mass (91.19 GeV) given the analysis's own mass
  resolution.
- **J/psi:** in the 2.5-3.7 GeV window (19,270 entries, 10 MeV bins),
  the peak bin is at 3.095 GeV with 897 entries against a median of 102
  elsewhere in the window -- a clear, unambiguous excess at the PDG
  J/psi mass (3.097 GeV).

Both resonances land at essentially the same masses as the top-4 and
normal versions' own resonance checks (unsurprising, since removing
~5,738 rare N>4 events out of ~172.6M has no visible effect on the bulk
dimuon mass spectrum).

## The two trigger-mixing checks (mass_m0j0, 2-muon-1-jet and 1-muon-1-jet)

Script: `scripts/build_trigger_mixing_nonjet4.py`. Same exact-partition
method used before (real post-processing functions, not an
approximation): pools DoubleMuon-inclusive and SingleMuon-exclusive raw
values for each named signature, applies the SAME cuts the real delivery
applied to determine the delivered [min,max] mass window, then re-applies
those same cuts to each source separately and windows by that range --
an exact partition (verified: DM contribution + SM contribution
reproduces the delivered histogram's bin contents exactly). Evidence:
`trigger_mixing_data.json`, `plots/trigger_mixing_mass_m0j0_cat_0ex_1mx_1jx_0gx_0tx_0bx.png`,
`plots/trigger_mixing_mass_m0j0_cat_0ex_2mx_1jx_0gx_0tx_0bx.png`.

| Signature | n(DoubleMuon) | n(SingleMuon excl.) | n(delivered) | Partition check |
|---|---|---|---|---|
| mass_m0j0, 1 muon + 1 jet | 0 | 22,634,851 | 22,634,851 | PASS (count and histogram both exact) |
| mass_m0j0, 2 muons + 1 jet | 1,006,079 | 117,387 | 1,123,466 | PASS (count and histogram both exact) |

The 1-muon-1-jet category is, as expected, 100% SingleMuon -- DoubleMuon's
own matched-trigger acceptance requires 2 matched muons, so it can never
contribute to a 1-muon final state at all. The 2-muon-1-jet category is
dominated by DoubleMuon (89.6%) with a genuine 10.4% SingleMuon-exclusive
contribution -- events DoubleMuon's own path/matching did not accept but
SingleMuon's did -- exactly the trigger-mixing behaviour this check
exists to confirm, unchanged from the top-4/normal versions' own results.

## Required plots (all committed under `plots/`)

- `plot_nonjet4_1_largest.png` -- largest histogram by event count.
- `plot_nonjet4_2_median.png` -- median histogram by event count.
- `plot_nonjet4_3_near_25bin_boundary.png` -- near the 25-bin boundary.
- `plot_nonjet4_one_muon_1.png`, `_2.png`, `_3.png` -- the 3 largest
  one-muon categories.
- `plot_nonjet4_crop_comparison.png` -- uncropped vs. cropped, same
  histogram.
- `plots_z_peak.png`, `plots_jpsi_window.png` -- the resonance checks.
- `trigger_mixing_mass_m0j0_cat_0ex_1mx_1jx_0gx_0tx_0bx.png`,
  `trigger_mixing_mass_m0j0_cat_0ex_2mx_1jx_0gx_0tx_0bx.png` -- the two
  trigger-mixing checks.

## Overall result: PASS, full delivery verified, ready for BumpNet.
