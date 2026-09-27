DoubleMuon BumpNet histograms -- ROOT delivery
================================================

WHAT THESE FILES ARE
---------------------
Two ROOT files, each holding the DoubleMuon coverage-run's BumpNet-ready
mass histograms as genuine TH1F objects on the shared fixed grid
(0-10,000 GeV, 10 GeV bins), differing ONLY in the minimum-filled-bins
threshold applied to the SAME already-post-processed mass distributions:

  doublemuon_bumpnet_min31bins.root  -- filled bins >  30 (i.e. >= 31).
                                         Exactly the 316 histograms already
                                         counted in the committed coverage
                                         measurement.
  doublemuon_bumpnet_min26bins.root  -- filled bins >  25 (i.e. >= 26).
                                         A strict superset of the file
                                         above: all 316, plus 24 more that
                                         clear the looser cut. Bin
                                         contents for every shared
                                         histogram are identical between
                                         the two files (re-verified by
                                         reading both back from disk).

Both also require >=100 events per histogram, unchanged from the
coverage run's own criterion. Every histogram's ROOT-internal key is
ROI_<bumpnet-name>_width_10, e.g.
ROI_mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx_width_10.

UNCROPPED vs CROPPED -- FOUR FILES, TWO PAIRS
------------------------------------------------
There are now FOUR ROOT files, two "uncropped" and two "cropped":

  doublemuon_bumpnet_min31bins.root          (uncropped, 316 histograms)
  doublemuon_bumpnet_min31bins_cropped.root  (cropped,   316 histograms)
  doublemuon_bumpnet_min26bins.root          (uncropped, 340 histograms)
  doublemuon_bumpnet_min26bins_cropped.root  (cropped,   340 histograms)

UNCROPPED means every histogram spans the shared pipeline's full fixed
grid, 0-10,000 GeV in 10 GeV bins (1,000 bins total,
FIXED_MASS_MIN_GEV/FIXED_MASS_MAX_GEV in
services/pipelines/histograms_pipeline.py) -- this is the shared
pipeline's own convention, used everywhere else in this project, and is
what "same grid, same edges, comparable across categories" means. Because
post-processing's peak-removal step always drops everything below the
per-category peak mass, bin 1 (0-10 GeV) is empty in every one of these
histograms by construction -- the pipeline's own trim_empty_tail sets a
cosmetic axis DISPLAY range that hides this in a plot, but the underlying
bin CONTENT is still there, still zero. A reader that inspects bin
contents directly (rather than the display range) sees an empty bin 1
regardless.

CROPPED means the leading (and, if it occurs, trailing) all-empty region
has been genuinely REMOVED -- a smaller TH1F, built by slicing the
uncropped histogram's own values/edges array down to the window from its
first to its last non-zero bin (any zero-content bins in between are kept
untouched -- only the empty edges are cut). Bin width stays exactly 10
GeV and every remaining bin edge stays aligned to the original grid (a
bin that ran 140-150 GeV in the uncropped file still runs 140-150 GeV in
the cropped one -- only the bin's INDEX changes). Name, title, and the
ROI_ internal key are identical to the uncropped version. Bin 1 of every
cropped histogram is non-empty by construction, and this was independently
verified for all 316 and all 340 histograms, re-reading the written files
from disk (build_summary.json / crop_summary.json have the full logs).
**Use the _cropped files for BumpNet** -- that is what its reader needs.

DATASET AND RUN RANGE
----------------------
CMS Open Data, DoubleMuon primary dataset, NanoAODv9 (UL2016),
Run2016G + Run2016H (CERN Open Data records 30522 and 30555), all 57
files across both records (29 + 28), golden-JSON data-quality filtered.
No HLT trigger requirement was applied in this measurement (that is a
separate, later survey's own addition, not part of this run).

SELECTION (unchanged from studies/m0m1j0_cms/selection.py; nothing about
it was touched or re-derived for this delivery)
------------------------------------------------
Events are required to have >=2 selected muons (pT>25 GeV, |eta|<2.4,
medium ID, relative isolation<0.15) and >=1 selected light jet (pT>30 GeV,
|eta|<2.5, tight ID, delta-R>=0.4 from every selected muon and electron).
Jets are split into b-tagged and light via the DeepJet DeepFlavB
discriminant (medium working point, 0.2598) before that pT/eta/ID/cleaning
cut is applied to both. Electrons (pT>25 GeV, |eta|<2.5, cutBased medium)
are selected and counted for the final-state category label but are not
required. Leptons + jets + b-jets only -- no taus, no photons, per the
group's current decision to hold those out until a consistent
overlap-removal prescription is settled; nothing about that changes here.
The 316 (and 340) histograms cover every one of the 186 object
combinations (1-4 objects from Electrons/Muons/Jets/BJets,
services.calculations.combinatorics.get_all_combinations) that CMS
Open Data DoubleMuon actually populates, not just m0m1j0.

POST-PROCESSING (the real, shared pipeline's own functions, unmodified,
same order the pipeline itself uses)
------------------------------------
1. min_events_per_fs=100: a global population cut, per exact final-state
   category, applied before anything below.
2. z_peak_cutoff (115 GeV): removed from any combination whose object
   letters contain two of the same lepton flavor.
3. max_mass_cutoff (10,000 GeV): a hard cap.
4. Peak removal: the rightmost highest-bin peak is found and everything
   below it is dropped.
5. First-empty-bin outlier split: the first gap after the peak splits the
   remaining population into "main" (histogrammed) and "outliers"
   (dropped -- exclude_outliers=true, unconditional).
Only the "main" population of each surviving category is histogrammed.
The BumpNet acceptance criterion (arXiv:2501.05603 Sec 2.2.2) is then
applied to that histogram: >30 filled bins (or >25, for the looser file)
AND >=100 events.

TWO KNOWN ARTIFACTS (not corrected here, not this delivery's job to fix)
-------------------------------------------------------------------------
1. Muon-jet overlap: in CMS NanoAOD, a selected muon is very often ALSO
   reconstructed inside a nearby jet (measured directly on this same
   dataset: 92.66% of jets in the Run2016G file, 92.68% in Run2016H, are
   within delta-R<0.4 of a selected muon -- studies/m0m1j0_cms/DESIGN.md).
   This is exactly why the jet selection above includes delta-R cleaning
   against selected muons/electrons in the first place -- without it,
   muon+jet combinations would be dominated by near-zero-mass self-pairs.
2. An unexplained low-mass dimuon population: of the 1,772,095 events in
   the inclusive m0m1j0 histogram, 2.18% have m(mu,mu) < 2 GeV (3.03% for
   < 4 GeV). Diagnostic checks (charge, delta-R, pT-ratio, global/tracker
   ID split -- studies/m0m1j0_cms/full/FULL_REPORT.md) point toward
   genuine, independently-reconstructed low-mass muon pairs for the large
   majority of this population, not duplicate reconstruction of one muon
   -- but this is diagnostic evidence, not a proof, and no cut has been
   applied for it anywhere in this delivery.

VERIFICATION PERFORMED FOR THIS DELIVERY
------------------------------------------
- All 57 source shards present and intact; total events read
  (94,148,416) matches the CMS Open Data portal's own published total
  for these two records exactly.
- The >30-bin file's 316 histograms are IDENTICAL (as a set of names) to
  an independent re-run of the coverage measurement's own funnel
  function on these same shards.
- Every m0m1j0-combination histogram in the >30-bin file matches the
  committed studies/m0m1j0_cms/v2 ROOT file bin-for-bin, exactly.
- The >25-bin file's 24 extra histograms range from 26-30 filled bins and
  105-2,276 events (median 28 bins / 245 events) -- see
  manifest_min26bins.json for the full list.

FILES IN THIS DIRECTORY
-------------------------
doublemuon_bumpnet_min31bins.root                  316 histograms, UNCROPPED (>30 bins).
doublemuon_bumpnet_min31bins_cropped.root          316 histograms, CROPPED  (>30 bins). Use this one for BumpNet.
doublemuon_bumpnet_min26bins.root                  340 histograms, UNCROPPED (>25 bins).
doublemuon_bumpnet_min26bins_cropped.root          340 histograms, CROPPED  (>25 bins). Use this one for BumpNet.
manifest_min31bins.json                            per-histogram detail, uncropped 316.
manifest_min26bins.json                            per-histogram detail, uncropped 340.
manifest_doublemuon_bumpnet_min31bins_cropped.json per-histogram detail, cropped 316 (bins now count only the cropped window).
manifest_doublemuon_bumpnet_min26bins_cropped.json per-histogram detail, cropped 340.
build_summary.json                                 build/verification log for the two uncropped files.
crop_summary.json                                  build/verification log for the two cropped files.
plot_1_largest.png                                 largest histogram by event count (uncropped file).
plot_2_median.png                                  median histogram by event count (uncropped file).
plot_3_near_25bin_boundary.png                     a histogram near the 25-bin cut.
plot_4_crop_comparison.png                         the same histogram, uncropped vs cropped, side by side.
README.txt                                         this file.

Produced by studies/cms_coverage/deliver/build_bumpnet_root.py,
make_check_plots.py, crop_bumpnet_root.py, and
make_crop_comparison_plot.py (branch deliver/doublemuon-bumpnet). The
uncropped files come from the existing coverage-run SQLite shards only;
the cropped files come only from re-reading the uncropped files above --
no CMS data file was re-read, no selection, combination, or threshold
was re-run or changed, for either pair.
