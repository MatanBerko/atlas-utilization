MuonEG BumpNet histograms -- generic-population ROOT delivery (PER-DATASET)
================================================================================

WHAT THIS IS
-------------
The per-dataset "generic" BumpNet delivery for the CMS Open Data MuonEG
primary dataset, Run2016 G+H (CERN Open Data records 30528 and 30561,
48 files: 29 + 19), golden-JSON filtered, requiring the MuonEG trigger
(HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ OR
HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ) and a "generic" event
population gate (>=2 selected objects of ANY type). Same object
definitions, post-processing, fixed 0-10,000 GeV / 10 GeV grid, and
BumpNet thresholds as the DoubleMuon and DoubleEG generic deliveries --
produced by the exact same, dataset-parameterized scripts.

**This is the INCLUSIVE set only.** MuonEG is third in veto priority
(vetoed by both the DoubleMuon and DoubleEG trigger sets); the EXCLUSIVE
shards stay on the cluster only, for a later combined/de-duplicated
delivery -- not built here.

A KNOWN, DOCUMENTED-ONLY GAP: NO ELECTRON-MUON OVERLAP REMOVAL
--------------------------------------------------------------------
This project's object definitions do not remove overlap between selected
electrons and selected muons -- unlike jet-lepton cleaning (dR<0.4), a
single real particle (typically a muon radiating a hard bremsstrahlung
photon, or a shared/nearby track) can in principle be reconstructed as
both a selected muon and a selected electron in the same event. MuonEG,
whose trigger and physics content is dominated by genuine
electron+muon pairs, is where this would matter most. **This delivery
measures the effect and does not add any overlap removal** (out of this
task's scope). See MUONEG_REPORT.md Section on "Electron-muon overlap"
for the measurement: a small (~0.5-1.6%, depending on the dR threshold
used) but real collimated e-mu population exists; the large majority of
e+mu pairs are well-separated, as expected for genuine top-pair/W+jets
physics.

FILES IN THIS DIRECTORY
-------------------------
muoneg_generic_bumpnet_min31bins.root          998 histograms, UNCROPPED (>30 bins).
muoneg_generic_bumpnet_min31bins_cropped.root  998 histograms, CROPPED  (>30 bins). Use this one for BumpNet.
muoneg_generic_bumpnet_min26bins.root          1102 histograms, UNCROPPED (>25 bins).
muoneg_generic_bumpnet_min26bins_cropped.root  1102 histograms, CROPPED  (>25 bins). Use this one for BumpNet.
manifest_muoneg_generic_min31bins.json         per-histogram detail, uncropped 998.
manifest_muoneg_generic_min26bins.json         per-histogram detail, uncropped 1102.
manifest_breakdown.json                        lepton/object-content breakdown + comparison vs. the UNION of the DoubleMuon and DoubleEG generic deliveries.
build_summary.json                             identity/funnel build log.
cutflow_and_resonances.json                    cutflow, portal identity check, negative Z-peak check, top-quark sanity, e-mu overlap measurement.
real_root_verify_min31bins.json                real-PyROOT 6.40.02 readback verification, >30-bin pair.
real_root_verify_min26bins.json                real-PyROOT 6.40.02 readback verification, >25-bin pair.
MUONEG_REPORT.md                               full quality-gate report.
plots/                                          all required PNGs.
README.txt                                      this file.

CROPPED vs UNCROPPED, SAME CONVENTION AS BEFORE
--------------------------------------------------
CROPPED means the leading (and trailing, if present) all-empty region on
the fixed grid has been genuinely removed -- a smaller TH1F, not a
display-range restriction -- so bin 1 of every cropped histogram is
non-empty (BumpNet's loader drops any histogram whose bin 1 is zero).
Verified independently with both uproot and real PyROOT 6.40.02 for all
998 and all 1102 histograms.

VERIFICATION PERFORMED FOR THIS DELIVERY
------------------------------------------
- All 48 source files present exactly once (29 Run2016G + 19 Run2016H),
  zero CAPPED:: shard entries, ALL 48 JOBS RAN THE SAME PINNED GIT
  COMMIT (a dedicated, untouched checkout was used for the whole job
  array, per this task's own code-pinning discipline); total events
  read (63,091,128) matches the CMS Open Data portal's own published
  total exactly.
- Pilot reproducibility: the two MuonEG files also processed by the
  earlier pre-flight pilot (record 30528 file 0, record 30561 file 0)
  reproduce that pilot's own shards and per-stage event counts EXACTLY.
- Real ROOT 6.40.02 confirms, independently of uproot: all 998 and all
  1102 histograms verified (count, non-empty bin 1, cropped contents
  match uncropped over the kept range).

See MUONEG_REPORT.md for the full cutflow, the negative Z-peak check in
m(e0,mu0), top-quark sanity (b-jet multiplicity, opposite/same-sign
counts), the electron-muon overlap measurement, and the lepton/object-
content breakdown including the running distinct-histogram-name total
across all three datasets delivered so far.
