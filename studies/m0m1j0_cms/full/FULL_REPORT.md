# m0m1j0 CMS histogram — full run report

Full run over **all** files of CMS DoubleMuon records 30522 (Run2016G,
29 files) and 30555 (Run2016H, 28 files) — 57 files total, run on the
Weizmann cluster (`wipp-an1`), branch `analysis/m0m1j0-cms`. Same
selection as the pilot, byte-for-byte — see `studies/m0m1j0_cms/RECIPE.md`
for the full recipe and `studies/m0m1j0_cms/pilot/PILOT_REPORT.md` for
the earlier 4-file pilot this was validated against. Every number below
is quoted from the committed `merge_summary.json` in this same directory.

## Completeness — every check passed

- All 57 expected jobs present (none missing).
- Every job's recorded input-file URL matches the CERN Open Data
  portal's **current** file list at its (record, file-index) — re-checked
  fresh at merge time, not assumed from submission time.
- Every job's file was **re-opened over XRootD at merge time** and its
  Events-tree entry count still matches what that job originally
  recorded reading (catches a partial/corrupted read that happened to
  exit cleanly) — all 57 matched.
- No file was assigned to more than one job.
- **Sum of events read across all 57 jobs: 94,148,416 — exactly equal**
  to the portal's own current published total (45,235,604 for 30522 +
  48,912,812 for 30555), re-fetched fresh at merge time.
- `merge_summary.json`'s `identity_and_counts.problems` list is **empty**.

## What ran

57 jobs, one PBS array (`5102887[].pbs`), each one input file. (An
earlier submission of this same array, `5102849[].pbs`, failed on all 57
jobs due to a real bug found and fixed before resubmitting — see
"Problems found and fixed" below; no partial output was ever produced by
that failed attempt, and it required no cleanup.)

## Cutflow (all 57 files, 94,148,416 events read)

| Step | Events | Fraction of previous step |
|---|---|---|
| Read | 94,148,416 | — |
| After golden JSON | 92,609,925 | 98.4% |
| After trigger (either DZ path) | 30,943,565 | 33.4% |
| After ≥2 selected muons | 9,450,067 | 30.5% |
| After ≥1 selected light jet (post cleaning) | 1,806,652 | 19.1% |
| After z_peak_cutoff (115 GeV) + max_mass_cutoff (10 TeV) | 1,772,095 | 98.1% |
| Events with m0m1j0 > 1 TeV (kept for inspection, not discarded) | 3,152 | — |

**Every one of these step-to-step fractions matches the pilot's own
cutflow (RECIPE.md/PILOT_REPORT.md: 98.5%, 33.3%, 30.6%, 19.1%, 98.1%) to
within a few tenths of a percent** — a strong independent cross-check
that the full run and the pilot are measuring the same thing, at ~10x
the statistics.

## Categories

62 exact final-state categories appeared across the 57 files; **19
survive the merge-time `min_events_per_fs` (≥100) prune** — the
inclusive histogram plus 18 real categories (43 smaller categories, from
65 events down to 1, were dropped — full list in `merge_summary.json`).
The category structure is identical in shape to the pilot's, just with
more categories now clearing the 100-event bar thanks to ~10x the data:

| Category | Events |
|---|---|
| `mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx` | 1,296,214 |
| `mass_m0m1j0_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 298,716 |
| `mass_m0m1j0_cat_0ex_2mx_3jx_0gx_0tx_0bx` | 66,955 |
| `mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_1bx` | 50,813 |
| `mass_m0m1j0_cat_0ex_2mx_4jx_0gx_0tx_0bx` | 19,045 |

Same dominant category as the pilot (plain 2-muon + 1-light-jet, no
b-tag), same ordering, same relative proportions.

## Sanity plots — all consistent with the pilot, higher statistics

- `plots/dimuon_mass.png` / `plots/dimuon_mass_zoom_0_10.png` — sharp
  Z→μμ peak at 91.19 GeV; the low-mass shoulder below ~5 GeV is now
  investigated explicitly below (it is real, not a plotting artifact).
- `plots/leading_jet_pt.png` — clean, hard edge exactly at the 30 GeV
  jet-pT cut.
- `plots/inclusive_m0m1j0_logy.png` — the main plot: smooth falling
  spectrum from the 115 GeV `z_peak_cutoff` edge out to ~4 TeV, single
  events visible in the tail out to ~3,850 GeV.
- `plots/inclusive_m0m1j0_linear_100_1000.png` — same histogram, linear
  y, 100-1000 GeV window, for a group-meeting-style close-up of the bulk
  of the distribution.
- `plots/top5_categories.png` — all 5 overlaid spectra have the same
  smooth falling shape, correctly ordered by size.

## Low-mass dimuon diagnostic — conclusion

**The evidence points away from "duplicate reconstruction of one
muon" and toward genuine, independently-reconstructed low-mass muon
pairs**, for the large majority of this population. Specifically, of the
1,772,095 events in the inclusive histogram:

| | m(μμ) < 2 GeV | m(μμ) < 4 GeV |
|---|---|---|
| Events | 38,567 (2.18%) | 53,683 (3.03%) |
| Same-sign fraction | 0.09% | 0.12% |
| Opposite-sign fraction | **99.91%** | **99.88%** |
| Median ΔR(μ0, μ1) | 0.013 | 0.021 |
| Fraction with ΔR < 0.02 | 67.0% | 48.2% |
| Median pT ratio (sub/lead) | 0.72 | 0.73 |
| Fraction with pT ratio in [0.95, 1.05] | 9.0% | 9.6% |
| Global/tracker-ID-split fraction | 6.1% | 7.3% |

The duplicate-reconstruction hypothesis predicts: overwhelmingly
**same**-sign pairs (it's the same physical charge counted twice), a pT
ratio clustered **near 1** (the same momentum measured twice), and often
a global/tracker split (the classic CMS "same track, reconstructed once
as a global muon and once as a tracker-only muon" duplication pattern).
**None of these hold here**: the pairs are overwhelmingly
*opposite*-sign, the pT ratio is broadly spread (peaking around 0.8-0.9,
not 1 — see `plots/diagnostic_pt_ratio.png`) with only ~9% near 1, and
94% of pairs have the *same* global/tracker status (i.e. no split). The
ΔR is smaller than a typical back-to-back pair, but its distribution
(`plots/diagnostic_deltaR.png`) is a smooth, physically-shaped falloff
from ~0, not a sharp delta-function spike at exactly zero — and the
overlay in `plots/diagnostic_m0m1j0_overlay.png` shows this low-mass
population's own m0m1j0 shape tracks the *entire* sample's m0m1j0 shape
essentially exactly, i.e. these events are not concentrated in some
separate, anomalous part of the spectrum.

**Honest uncertainty**: this is diagnostic evidence, not a proof. A
small minority (6-7%) does show the global/tracker-split pattern
associated with duplicates, so a small subset of true duplicates cannot
be ruled out. The dominant, large-majority pattern, though, is
consistent with genuine collimated low-mass opposite-sign muon pairs
(e.g. from heavy-flavor decays inside or near the selected jet, or
low-mass Drell-Yan/quarkonium-like production with a moderate boost) —
not a reconstruction artifact. **No cut was applied based on this
finding** (out of scope, per the task); a diagnostic-only variant
histogram excluding m(μμ) < 4 GeV is provided separately in
`m0m1j0_diagnostic_variants.root` (1,718,412 of 1,772,095 events survive
that exclusion) for anyone who wants to see its effect, but the main
merged histogram (`m0m1j0_full_merged.root`) is untouched by it.

## Problems found and fixed during this task

1. **Histogram class**: switched from TH1D to genuine TH1F (float32 bin
   contents), matching the shared pipeline's own output class — verified
   directly after every write (class == TH1F, contents match) via
   `histograms.verify_written_th1f`, both per-job and in this merge.
2. **A real crash affecting every one of the first 57 submitted jobs**:
   the per-job driver built the low-mass-dimuon diagnostic's extra muon
   fields (charge, quality flags) from the events *before* the trigger
   cut, then tried to combine them with muon arrays built *after* the
   trigger cut — a length mismatch that crashed instantly on real data
   (event counts differ before/after the trigger cut; the pilot's own
   test fixtures had happened to have every synthetic event pass the
   trigger, which is exactly what hid this). Fixed by having the
   selection code extract those extra fields itself, from the correct
   (post-trigger) array, rather than trusting a pre-sliced array from the
   caller — confirmed on a real file before resubmitting, and the array
   was then resubmitted and completed cleanly with the numbers shown
   above. No change to any physics cut.

## Outputs

- `m0m1j0_full_merged.root` — 19 TH1F histograms (18 categories +
  inclusive), verified.
- `m0m1j0_diagnostic_variants.root` — one diagnostic-only TH1F: the
  inclusive m0m1j0 histogram excluding m(μμ) < 4 GeV. Not used in, and
  never merged into, the main file above.
- `merge_summary.json` — full identity/completeness checks, cutflow,
  per-category counts, dropped categories, low-mass diagnostic numbers.
- `outliers_gt_1tev_merged.json` — all 3,152 events with m0m1j0 > 1 TeV
  (run, luminosityBlock, event, mass, category), for manual inspection.
- `plots/` — the 10 PNGs referenced above.

## UNVERIFIED / not done here

- No physics conclusion is drawn from the low-mass dimuon population
  beyond the diagnostic finding above — whether/how to act on it (a cut,
  a correction, further study) is explicitly a later decision, not made
  here.
- The `Electron_cutBased` branch's own NanoAOD title string was not
  independently quoted verbatim from a file in this run either (same
  UNVERIFIED item as the pilot) — the task's given meaning (medium,
  includes isolation) was used as specified.
