DoubleMuon BumpNet histograms -- GENERIC-population ROOT delivery
====================================================================

HOW THIS DIFFERS FROM THE EARLIER DELIVERY
--------------------------------------------
The earlier delivery (studies/cms_coverage/deliver/committed/, on the
cluster at /storage/agrp/berkom/atlas-utilization/output/deliver_doublemuon_bumpnet/)
required every selected event to have >=2 selected muons AND >=1 selected
non-b jet (studies/m0m1j0_cms/selection.py's own V0 population). This
delivery uses a BROADER event selection: any event with >=2 selected
objects of ANY type (muons, electrons, jets, or b-jets combined) --
"generic" population, studies/cms_datasets/cluster/run_dataset_on_file.py.
Same 57 files, same golden JSON, same DoubleMuon trigger, same object
definitions, same post-processing, same fixed grid, same BumpNet
thresholds -- ONLY the population gate is broader.

CONTINUITY WITH THE EARLIER DELIVERY -- VERIFIED, NOT ASSUMED
-----------------------------------------------------------------
Every one of the earlier delivery's 316 (>30-bin) and 340 (>25-bin)
histograms was checked against this delivery's own output: ALL 316 and
ALL 340 are present here with IDENTICAL bin contents and edges (0
differences, both files) -- because every one of those final states
already has >=2 muons and >=1 non-b jet by definition (that's what a
"final state" encodes), so the broader generic population contains
exactly the same underlying events for them. See continuity_check.json
for the full comparison log.

WHAT THIS DELIVERY ADDS
-------------------------
  >30-bin file: 802 histograms total (316 old + 486 new).
  >25-bin file: 910 histograms total (340 old + 570 new).
The new histograms are final states the old, jet+dimuon-required
population could never populate at all -- pure jet/b-jet combinations
with zero leptons, single-muon or single-electron categories, and
zero-jet dimuon categories (e.g. mass_m0m1_cat_0ex_2mx_0jx_0gx_0tx_0bx,
107,400 events -- see DOUBLEMUON_REPORT.md for the full breakdown by
object content and final-state type).

WHAT THESE FILES ARE
---------------------
Four ROOT files, same TH1F/grid/naming convention as the earlier
delivery (0-10,000 GeV fixed grid, 10 GeV bins, ROOT key
ROI_<bumpnet-name>_width_10), differing in the minimum-filled-bins
threshold and in uncropped vs. cropped:

  doublemuon_generic_bumpnet_min31bins.root          802 histograms, UNCROPPED (>30 bins).
  doublemuon_generic_bumpnet_min31bins_cropped.root  802 histograms, CROPPED  (>30 bins). Use this one for BumpNet.
  doublemuon_generic_bumpnet_min26bins.root          910 histograms, UNCROPPED (>25 bins).
  doublemuon_generic_bumpnet_min26bins_cropped.root  910 histograms, CROPPED  (>25 bins). Use this one for BumpNet.

Both also require >=100 events per histogram, unchanged. CROPPED means
the leading (and trailing, if present) all-empty region on the fixed
grid has been genuinely removed -- a smaller TH1F, not a display-range
restriction -- so bin 1 of every cropped histogram is non-empty
(BumpNet's loader drops any histogram whose bin 1 is zero). Verified for
all 802 and all 910 histograms, independently, with BOTH uproot and real
PyROOT 6.40.02 (real_root_verify_min31bins.json / _min26bins.json).

SELECTION AND POST-PROCESSING -- UNCHANGED FROM THE SHARED PIPELINE
------------------------------------------------------------------------
Object definitions, golden JSON, DoubleMuon trigger (the two DZ paths,
OR'd), z_peak_cutoff (115 GeV), max_mass_cutoff (10 TeV), peak removal,
first-empty-bin outlier split, min_events_per_fs (100), and the BumpNet
bin/event thresholds (>30 or >25 filled bins, >=100 events) are all
identical to the earlier delivery and to the shared pipeline's own
values -- nothing about them was touched for this delivery. Only the
population GATE (which events are eligible for the 186-combination
funnel in the first place) is broader, as described above.

VERIFICATION PERFORMED FOR THIS DELIVERY
------------------------------------------
- All 57 source shards present exactly once (29 Run2016G + 28
  Run2016H), single git commit across every job, zero CAPPED:: shard
  entries (the 500,000-per-signature-per-file cap never triggered);
  total events read (94,148,416) matches the CMS Open Data portal's own
  published total for these two records exactly.
- Continuity check: 316/316 and 340/340 of the earlier delivery's
  histograms reproduced bin-for-bin exactly in this delivery's own
  stage-c survivors (see continuity_check.json).
- Real ROOT 6.40.02 (independent of uproot) confirms: histogram counts
  match between uncropped/cropped pairs, every cropped histogram's bin 1
  is non-empty, and cropped contents match the uncropped version over the
  kept range exactly, for all 802 and all 910 histograms.

See DOUBLEMUON_REPORT.md for the full cutflow, resonance plots (Z peak,
J/psi), muon pT distributions, the collimated low-mass dimuon
measurement, the funnel/breakdown tables, and known artifacts.

FILES IN THIS DIRECTORY
-------------------------
doublemuon_generic_bumpnet_min31bins.root          802 histograms, UNCROPPED (>30 bins).
doublemuon_generic_bumpnet_min31bins_cropped.root  802 histograms, CROPPED  (>30 bins). Use this one for BumpNet.
doublemuon_generic_bumpnet_min26bins.root          910 histograms, UNCROPPED (>25 bins).
doublemuon_generic_bumpnet_min26bins_cropped.root  910 histograms, CROPPED  (>25 bins). Use this one for BumpNet.
manifest_doublemuon_generic_min31bins.json         per-histogram detail, uncropped 802.
manifest_doublemuon_generic_min26bins.json         per-histogram detail, uncropped 910.
build_summary.json                                 build/verification log (identity, funnel, thresholds).
continuity_check.json                              full per-histogram comparison vs. the earlier delivery.
cutflow_and_resonances.json                         cutflow, portal identity check, Z/J-psi peak fits, low-mass population.
real_root_verify_min31bins.json                    real-PyROOT 6.40.02 readback verification, >30-bin pair.
real_root_verify_min26bins.json                    real-PyROOT 6.40.02 readback verification, >25-bin pair.
DOUBLEMUON_REPORT.md                               full quality-gate report.
plots/                                              all required PNGs (see DOUBLEMUON_REPORT.md).
README.txt                                          this file.

Produced by studies/cms_datasets/cluster/run_dataset_on_file.py (the
57-file full run), studies/cms_datasets/deliver/build_dataset_delivery.py,
aggregate_cutflow_and_resonances.py, make_delivery_check_plots.py, and
verify_with_real_root.py (branch deliver/all-datasets-bumpnet). The
earlier delivery and its own scripts were read-only inputs (for the
continuity check) and were never modified.
