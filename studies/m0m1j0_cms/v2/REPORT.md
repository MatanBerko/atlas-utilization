# m0m1j0 CMS histogram — v2: real post-processing + ttbar MC comparison

Short report for the supervisor and technical lead. Every number below
comes from a committed JSON or ROOT file in this branch — see the file
path noted next to each one. Full technical detail is in
`studies/m0m1j0_cms/RECIPE.md`.

## The correction (Part A)

The supervisor was right: **Step 1/2 of this study never applied the
shared pipeline's own post-processing.** That post-processing is not
optional or config-gated — for every category, the pipeline always (1)
applies the 115 GeV / 10 TeV mass-window cuts, (2) finds that category's
own dominant 10-GeV-wide bin and throws away everything below it ("peak
removal"), and (3) looks for the first real gap in what's left and drops
everything past that gap as "outliers" (`exclude_outliers: true` in the
group's config). My earlier document (`RECIPE.md`) wrongly read a
different, unrelated switch (`apply_peak_removal_at_histogram_level:
false`) as meaning peak removal was switched off — it isn't; that switch
controls a second, additional step, not the one described above. This
is now corrected and cited precisely in `RECIPE.md`'s "CORRECTION"
section, and the real pipeline's own code
(`services/pipelines/post_processing_pipeline.py`) is now called
directly rather than re-implemented, so there is no room for this study
to drift from it again.

**Before producing any new number, the corrected code was cross-checked
against the original (uncorrected) histogram**: for all 61 categories,
the population immediately before peak-removal was required to match
the original histogram's own total exactly. It did, for every single
one — confirming the same events, the same selection, the same files;
only what happens after that point is new. (`studies/m0m1j0_cms/v2/data/merge_v2_summary.json`,
`a4_cross_check_passed: true`)

## Kinematic cuts (unchanged throughout this whole project)

| Object | Cut |
|---|---|
| Muons (used in the mass) | pT > 25 GeV, \|η\| < 2.4, medium ID, isolation < 0.15 |
| Electrons (counted only, not in the mass) | pT > 25 GeV, \|η\| < 2.5, "medium" quality |
| Jets | pT > 30 GeV, \|η\| < 2.5, tight ID, kept only if ≥0.4 away from any selected muon/electron |
| b-tagged jets | same jet cuts, plus a b-tag score above the standard "Medium" working point |
| Trigger | one of two standard CMS double-muon triggers must have fired |
| Data quality (data only) | only certified "golden" runs/luminosity-sections |
| Mass window | 115 GeV to 10,000 GeV |

Nothing in this table changed for this task — only what happens to the
mass values *after* these cuts (the post-processing above) was corrected.

## Data results (Part A)

- **All 57 files, 94,148,416 events** — matches the CMS Open Data portal's
  own published total exactly. (`studies/m0m1j0_cms/v2/data/merge_v2_summary.json`)
- 61 categories exist; **18 categories plus one combined ("inclusive")
  histogram** have enough events (≥100) to survive.
- The combined histogram: **1,806,652** events enter it before the new
  correction; the correction's own "biggest bin" is at **140 GeV**
  (everything below that is now dropped); after that, the histogram runs
  smoothly until **1,993 GeV**, past which **96 events** are excluded as
  outliers under the group's own rule. **1,488,310 events** remain in
  the final histogram.
- Biggest category (as before): plain 2-muon + 1-jet, no b-tag —
  **1,051,110** events survive the correction.

## ttbar simulation results (Part B)

- **Sample found**: record **67801**,
  `TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8`, the 2016 post-VFP simulation
  matching the data era exactly — 49 files, 43,546,000 simulated events
  published by the portal. (The portal does not publish a cross-section
  for this record — checked directly, genuinely absent, not something
  this study needed anyway since nothing here is scaled to luminosity.)
- **Pilot (2 files) passed every sanity check** before the full run was
  started: the dimuon mass has no dominant Z peak (a broad hump, unlike
  data — `studies/m0m1j0_cms/v2/ttbar_pilot_check/dimuon_mass.png`);
  77% of selected events have at least one b-tagged jet, as expected for
  real top-quark pairs; the jet-pT and simulation-weight distributions
  both look sensible.
- **Full run: all 49 files, 43,546,000 events read** — matches the
  portal exactly. 73 categories exist; 29 plus the combined histogram
  survive. 77.1% of the **1,321,341** selected events have ≥1 b-tagged
  jet (same as the pilot — stable).
- The combined ttbar histogram, after the same correction: biggest bin
  at **170 GeV**, running smoothly to **2,211 GeV** (71 events excluded
  beyond that), **1,028,993** events in the final histogram.
- Two versions were produced: the main one counts every simulated event
  equally ("unweighted" — the one used for the plots below, so it's
  directly comparable in format to the data histogram); a second, clearly
  separate file additionally weights each event by its own simulation
  weight. **Neither is scaled to real-world luminosity** — this
  dataset's own luminosity hasn't been independently verified yet, so no
  "events per fb⁻¹" number is produced here. Also not applied (recorded
  as known limitations, not fixed): pileup reweighting, muon/b-tag
  correction factors, trigger-efficiency corrections.

## What the comparison plots show

`studies/m0m1j0_cms/v2/plots/` has 6 PNGs: the data and ttbar combined
histograms on their own, two shape-only overlays (combined, and the
single biggest category) with data and ttbar each scaled to the same
total area so their *shapes* can be compared side by side, and a top-5
list for each sample. **The overlays are explicitly not a background
prediction** — they show shape only, with no attempt to scale the
simulation to how much of it we'd actually expect in the real data.
Visually, ttbar's mass distribution falls off more gently at high mass
than data's does — expected, since top-quark pairs tend to produce
higher-momentum objects than the light-flavor processes that dominate
the plain DoubleMuon data sample.

## Anything unverified

- The ttbar sample's cross-section (not published by the portal for
  this record).
- Whether the small set of categories that flipped from "kept" to
  "dropped" (or vice versa) between the old and new min-events rule
  ordering would matter for any specific category — not individually
  cross-checked beyond the mandatory pre-peak-removal totals check,
  which passed for every category that exists in both versions.

## Next step

This is a data-vs-simulation *shape* comparison only, exactly as scoped.
A real background estimate (scaling ttbar to a predicted yield) would
need the DoubleMuon luminosity, ttbar's cross-section, and the
corrections listed above as "not applied" — all explicitly out of scope
here and left for a future task.
