BumpNet delivery -- FOUR datasets, Version B (rare4)
====================================================

WHICH FILE TO USE
-----------------
    four_dataset_matched_vB_upstreamnames_w10p0_dr012_bumpnet_cropped.root

That is the file for BumpNet. It is the CROPPED one: every histogram has
been trimmed to its first..last filled bin, so the first bin is never
empty, which is what BumpNet requires.

    four_dataset_matched_vB_upstreamnames_w10p0_dr012_bumpnet.root

is the same 1975 histograms UNCROPPED, on the full fixed
0-10000 GeV grid. For cross-checking and plotting only.

WHAT IS IN IT
-------------
1975 histograms over 103 distinct final-state
categories, on the unchanged fixed grid: 0-10000 GeV in 10 GeV bins.
Every histogram is named ROI_mass_<combination>_cat_<final state>_width_10.0,
e.g. ROI_mass_m0m1_cat_0ex_2mx_5jx_1bx_width_10.0.

WHICH DATA
----------
Run2016G+H, four primary datasets, de-duplicated so every accepted
collision is counted exactly once:

  DoubleMuon   inclusive (57 per-file shards)
  SingleMuon   exclusive (152 per-file shards)
  DoubleEG     exclusive (133 per-file shards)
  MuonEG       exclusive (48 per-file shards)

De-duplication priority, highest first: DoubleMuon > SingleMuon > DoubleEG > MuonEG. An event belongs to a
dataset's exclusive set if that dataset's own acceptance (its trigger
path(s) fired AND its own trigger-matching/threshold rule passes) holds
and no higher-priority dataset's acceptance does.

Electrons within dR < 0.05 of a selected muon are removed, in all four
datasets, before trigger matching and before the final state is decided.

THRESHOLDS APPLIED
------------------
* >= 100 events per final state, applied ONCE over the combined shards of
  all 390 per-file jobs.
* per-histogram minimum entries: NONE (upstream behaviour: >= 1 entry)
* filled-bin cut: NONE (applied on the BumpNet side during smoothing)

For information only, of the 1975 delivered histograms:
  - 1601 have 25 or more filled bins (what BumpNet's own cut keeps)
  - 1586 have more than 25 filled bins
  - 1502 have more than 30 filled bins

WHAT IS UNCHANGED FROM THE MUON DELIVERY
----------------------------------------
Object definitions, the b-tag working point, the golden-JSON run filter,
the Version B reject rule (reject an event if electrons + muons + b-jets
> 4, otherwise keep ALL selected light jets), exact light-jet final
states, the 186 combinations, the fixed 10 GeV binning, the Z-peak cut at
110 GeV, the bin-aligned outlier split, the max-mass cut and peak removal.
