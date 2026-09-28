DoubleEG BumpNet histograms -- generic-population ROOT delivery (PER-DATASET)
=================================================================================

WHAT THIS IS
-------------
The per-dataset "generic" BumpNet delivery for the CMS Open Data DoubleEG
primary dataset, Run2016 G+H (CERN Open Data records 30521 and 30554,
133 files: 47 + 86), golden-JSON filtered, requiring the DoubleEG trigger
(HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ) and a "generic" event
population gate (>=2 selected objects of ANY type -- muons, electrons,
jets, or b-jets combined). Same object definitions, post-processing,
fixed 0-10,000 GeV / 10 GeV grid, and BumpNet thresholds (>30 or >25
filled bins, >=100 events) as the DoubleMuon generic delivery -- produced
by the exact same, dataset-parameterized scripts under
studies/cms_datasets/.

**This is the INCLUSIVE set only** (all events passing DoubleEG's own
trigger, regardless of whether they also fired a higher-veto-priority
dataset's trigger -- here, only DoubleMuon is higher priority). The
EXCLUSIVE shards (events that additionally fail DoubleMuon's own trigger)
are kept on the cluster only, for a later, separate combined/
de-duplicated delivery across all datasets -- not built in this task.

FILES IN THIS DIRECTORY
-------------------------
doubleeg_generic_bumpnet_min31bins.root          644 histograms, UNCROPPED (>30 bins).
doubleeg_generic_bumpnet_min31bins_cropped.root  644 histograms, CROPPED  (>30 bins). Use this one for BumpNet.
doubleeg_generic_bumpnet_min26bins.root          712 histograms, UNCROPPED (>25 bins).
doubleeg_generic_bumpnet_min26bins_cropped.root  712 histograms, CROPPED  (>25 bins). Use this one for BumpNet.
manifest_doubleeg_generic_min31bins.json         per-histogram detail, uncropped 644.
manifest_doubleeg_generic_min26bins.json         per-histogram detail, uncropped 712.
manifest_breakdown.json                          lepton/object-content breakdown + comparison vs. the DoubleMuon generic delivery.
build_summary.json                               identity/funnel build log.
cutflow_and_resonances.json                      cutflow, portal identity check, Z peak fit, electron pT/eta diagnostics.
real_root_verify_min31bins.json                  real-PyROOT 6.40.02 readback verification, >30-bin pair.
real_root_verify_min26bins.json                  real-PyROOT 6.40.02 readback verification, >25-bin pair.
DOUBLEEG_REPORT.md                               full quality-gate report.
plots/                                             all required PNGs.
README.txt                                         this file.

CROPPED vs UNCROPPED, SAME CONVENTION AS DOUBLEMUON
--------------------------------------------------------
CROPPED means the leading (and trailing, if present) all-empty region on
the fixed grid has been genuinely removed -- a smaller TH1F, not a
display-range restriction -- so bin 1 of every cropped histogram is
non-empty (BumpNet's loader drops any histogram whose bin 1 is zero).
Verified independently with both uproot and real PyROOT 6.40.02 for all
644 and all 712 histograms: histogram counts match, bin 1 is non-empty,
and cropped contents equal the uncropped version over the kept range
exactly (real_root_verify_min31bins.json / _min26bins.json).

VERIFICATION PERFORMED FOR THIS DELIVERY
------------------------------------------
- All 133 source files present exactly once (47 Run2016G + 86 Run2016H),
  zero CAPPED:: shard entries; total events read (164,185,704) matches
  the CMS Open Data portal's own published total exactly.
- Pilot reproducibility: the two DoubleEG files also processed by the
  earlier pre-flight pilot (record 30521 file 0, record 30554 file 0)
  reproduce that pilot's own shards and per-stage event counts EXACTLY
  (same signatures, byte-identical arrays) in this full run.
- Real ROOT 6.40.02 confirms, independently of uproot: all 644 and all
  712 histograms verified (count, non-empty bin 1, cropped contents
  match uncropped over the kept range).

A NOTE ON GIT COMMIT TRACKING (see DOUBLEEG_REPORT.md for full detail)
------------------------------------------------------------------------
During this run, 18 of the 133 jobs briefly recorded an earlier commit
hash than the other 115, because unrelated commits were pushed to
different files while the job array was still executing on the shared
cluster checkout. The actual code that determines selection, gating,
combination, and shard-writing (run_dataset_on_file.py) was verified
BYTE-IDENTICAL between the two commits (a plain `git diff` shows no
difference) -- nothing about how those 18 files were processed differs
from the other 115. To remove any ambiguity, those 18 jobs were re-run
against a single pinned commit; all 133 jobs now report the same final
commit hash, and this delivery is built entirely from that re-run state.

See DOUBLEEG_REPORT.md for the full cutflow, resonance plot (Z peak,
width), electron pT/eta distributions, the ECAL-gap fraction, the
lepton/object-content breakdown, and comparison against the DoubleMuon
generic delivery.
