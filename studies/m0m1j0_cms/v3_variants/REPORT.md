# m0m1j0 CMS histogram — selection variants (supervisor request)

Report for the supervisor. Every number below comes from
`studies/m0m1j0_cms/v3_variants/comparison_summary.json` (built by
`cluster/merge_variants.py` + `cluster/make_variants_plots.py`), which is
itself built from every job's own committed-format output on the cluster.
Full recipe and every deviation is in `studies/m0m1j0_cms/RECIPE.md`; this
document only covers the four variants and what changed.

## What was run

All four selections below were computed **in one pass per file** (one file
read, one golden-JSON filter for data, then all four selections applied to
the same in-memory events) — never four separate file reads.

| Variant | What changes relative to V0 |
|---|---|
| **V0** baseline | Nothing — this is the existing, already-published recipe (RECIPE.md), unchanged. |
| **V1** no muon isolation | Drops `Muon_pfRelIso04_all < 0.15`. Everything else identical. |
| **V2** no jet-lepton overlap removal | Drops the ΔR<0.4 jet-lepton cleaning step entirely. Everything else (pt/eta/tight-ID cuts, b-tag split) identical. Because the leading jet can change, the mass is **recomputed from scratch** for every event under this variant, never reweighted from V0's histogram. |
| **V3** single-muon trigger | Requires `HLT_IsoMu24 OR HLT_IsoTkMu24` instead of the two double-muon DZ paths. **Caveat, repeated on every V3 plot**: these are DoubleMuon primary-dataset files, so V3 selects events that fired BOTH a double-muon path (that's why the event is in this file at all) and a single-muon path — a cross-check, not a true single-muon selection, which would need the SingleMuon primary dataset (out of scope here). |

Applied to both samples: data (all 57 files, 94,148,416 events — the CMS
Open Data portal's own published total, matching exactly) and ttbar MC (all
49 files, 43,546,000 events, no golden JSON).

## V0 cross-check — mandatory, and it passed

Before trusting any variant number, this run's own V0_baseline result was
checked, category by category, against the **existing, already-committed**
v2 results (`studies/m0m1j0_cms/v2/data/merge_v2_summary.json`,
`.../v2/ttbar/merge_ttbar_summary.json`) — same files, same selection, so
every field (raw count, peak bin, split point, main/outlier counts) had to
match exactly, or the merge script would refuse to produce any output at
all. **Both samples passed, with zero mismatches**
(`merge_variants_data_summary.json`/`merge_variants_ttbar_summary.json`,
`v0_cross_check_passed: true`).

## Results table

| Sample | Variant | Events in inclusive histogram | Ratio to V0 | Histogram starts (peak bin) | Histogram ends (first-empty-bin cut) | Outliers excluded |
|---|---|---:|---:|---:|---:|---:|
| data | V0 baseline | 1,488,310 | 1.000 | 140 GeV | 1,993 GeV | 96 |
| data | V1 no muon iso | 1,789,386 | 1.202 | 140 GeV | 2,079 GeV | 85 |
| data | V2 no jet-lepton cleaning | 7,763,905 | 5.217 | 130 GeV | 1,752 GeV | 136 |
| data | V3 single-muon trigger | 1,599,196 | 1.075 | 140 GeV | 1,993 GeV | 102 |
| ttbar | V0 baseline | 1,028,993 | 1.000 | 170 GeV | 2,211 GeV | 71 |
| ttbar | V1 no muon iso | 1,351,310 | 1.313 | 170 GeV | 2,470 GeV | 56 |
| ttbar | V2 no jet-lepton cleaning | 1,399,486 | 1.360 | 150 GeV | 2,211 GeV | 72 |
| ttbar | V3 single-muon trigger | 1,092,198 | 1.061 | 170 GeV | 2,312 GeV | 55 |

## Diagnostics (data only, per the task's own spec)

Population: events with ≥2 selected muons and ≥1 selected light jet under
that variant's own selection (the same population the sanity-check dimuon
mass plot uses) — deliberately **before** the 115 GeV mass-window cut,
since that cut acts on the 3-body m0m1j0 mass, not the dimuon mass, so a
collimated pair can still enter the inclusive histogram if the jet alone
pushes m0m1j0 above the floor.

| | V0 baseline | V1 no muon iso |
|---|---:|---:|
| fraction with m(μμ) < 2 GeV | 2.47% | 3.52% |
| fraction with m(μμ) < 4 GeV | 3.47% | 6.58% |

**Removing the isolation cut increases the collimated low-mass pair
fraction** — about 42% more (relative) below 2 GeV, and about 90% more
(relative) below 4 GeV. See `plots/data_dimuon_lowmass_V0_vs_V1.png`: the
Z peak (~91 GeV), and both the J/ψ (~3.1 GeV) and the low-mass excess below
~1 GeV, are all visibly taller for V1 than V0.

**V2 diagnostic** — same population, V2's own (uncleaned) selection:

| | Value |
|---|---:|
| fraction whose leading jet is within ΔR<0.4 of a selected muon | 95.3% |
| fraction whose leading jet's pT is within 10% of a selected muon's pT | 9.9% |

## What each variant does to the histogram, in plain words

- **V1 (no isolation)** admits noticeably more events everywhere (+20%
  data, +31% ttbar) — a simple, expected "removing a cut lets more events
  through" effect, with no change in shape (`plots/data_V0_vs_V1.png`,
  `plots/ttbar_V0_vs_V1.png`: the ratio panel sits close to a flat ~1.1-1.3
  across the whole mass range for data, closer to flat for ttbar).

- **V2 (no jet-lepton overlap removal)** has by far the biggest effect:
  **5.2× more events in data**, 1.36× in ttbar. This is not spread evenly —
  95.3% of V2's own selected events have their "leading jet" sitting within
  ΔR<0.4 of a selected muon (the exact overlap the cleaning step exists to
  remove), and one in ten of those has a pT close enough to the muon's own
  to look like the same object reconstructed twice. Looking at the shape
  (`plots/data_V0_vs_V2.png`), the huge increase is concentrated right at
  the mass-window threshold (the peak bin moves from 140 to 130 GeV, and
  the ratio panel actually drops *below* 1 at higher masses, down to
  roughly 0.5-0.8) — meaning without cleaning, the extra "jets" are mostly
  low-momentum, muon-adjacent objects that pull the reconstructed mass
  down, not genuine additional jet activity that would push it up. ttbar's
  version of this effect is much smaller (1.36× vs 5.2×) and the shape
  stays much closer to V0's, consistent with ttbar's jets coming from
  genuine top-quark decays rather than muon-jet confusion.

- **V3 (single-muon trigger)** admits a modestly different event population
  (+7.5% data, +6.1% ttbar) with a shape close to V0's
  (`plots/data_V0_vs_V3.png`). As stated on every V3 plot: this is a
  cross-check on events firing both trigger families, not a genuine
  single-muon-dataset selection.

## Optional extra: ttbar scaled to the data's luminosity

`plots/OPTIONAL_data_vs_ttbar_lumi_scaled.png` — ttbar's V0 histogram
scaled by `sigma(TTTo2L2Nu) x L / N_generated = 88.29 pb x 16.393 fb⁻¹ /
43,546,000 = 0.033237`, numbers recorded in `comparison_summary.json`.
**Caveat, on the plot itself**: cross section not published on the CERN
Open Data portal (a standard value was used instead); the DoubleMuon
dataset's luminosity has not been independently verified (it is established
for DoubleEG); ~10% uncertainty should be assumed; no pileup reweighting or
scale factors are applied. This is a shape/scale illustration, not a
background prediction.

## Retries

Data: 13 of 57 jobs failed on the first submission, all with the identical
transient error (`OSError: File did not vector_read properly: [ERROR]
Operation expired` — an XRootD read timeout, the same failure mode already
documented elsewhere in this project's history, not a bug in this task's
code — confirmed by successfully re-reading one of the same files with the
existing, unmodified V0 driver moments after the variants driver failed on
it). Retried with a larger walltime (40 minutes, the task's own cap): 10
succeeded immediately, a 2nd retry cleared 2 more, and the last one needed
a 3rd retry. All 57 data jobs and all 49 ttbar jobs (zero ttbar failures on
the first attempt) are present in the final merge.

## Anything unverified

- The ttbar cross-section (88.29 pb) and the DoubleMuon luminosity (16.393
  fb⁻¹) are both task-supplied numbers, not independently derived here —
  see the caveat above and in the plot itself.
- Whether V2's low-mass excess is entirely muon-duplication (as the 95.3%/
  9.9% diagnostic suggests) or partly genuine soft jet activity near a
  muon is not separated further here — the diagnostic quantifies overlap,
  it does not classify individual events.

## Out of scope, as instructed

The baseline selection and every existing v2/pilot/full output are
unchanged. No pileup reweighting, scale factors, background fit, or
significance calculation was performed. The SingleMuon primary dataset was
not touched. Nothing was proposed or changed in the shared pipeline.
