BumpNet delivery -- 5 datasets, Version B (rare4)
=================================================

WHICH FILE TO USE
-----------------
    fullrun_bumpnet_cropped.root

That is the file for BumpNet. It is the CROPPED one: every histogram has
been trimmed to its first..last filled bin, so the first bin is never
empty, which is what BumpNet requires.

    fullrun_bumpnet.root

is the same 313 histograms UNCROPPED, on the full fixed
0-10000 GeV grid. For cross-checking and plotting only.

WHAT IS IN IT
-------------
313 histograms over 49 distinct final-state
categories, on the unchanged fixed grid: 0-10000 GeV in 10 GeV bins.
Every histogram is named ROI_mass_<combination>_cat_<final state>_width_10.0,
e.g. ROI_mass_m0m1_cat_0ex_2mx_1jx_1bx_width_10.0.

WHICH DATA
----------
Run2016G+H, 5 primary datasets, de-duplicated so every accepted
collision is counted exactly once:

  DoubleMuon   inclusive (57 per-file shards)
  SingleMuon   exclusive (152 per-file shards)
  DoubleEG     exclusive (133 per-file shards)
  MuonEG       exclusive (48 per-file shards)
  SingleElectron exclusive (151 per-file shards)

De-duplication priority, highest first: DoubleMuon > SingleMuon > DoubleEG > MuonEG > SingleElectron. An event belongs to a
dataset's exclusive set if that dataset's own acceptance (its trigger
path(s) fired AND its own trigger-matching/threshold rule passes) holds
and no higher-priority dataset's acceptance does.

Electrons within dR < 0.12 of a selected muon are removed, in every
dataset, before trigger matching and before the final state is decided.

FINAL STATES (multiplicity rule: upstream40)
------------
At most 4 objects per final state (upstream #40, 5fbf1ef):
electrons + muons + b-jets > 4 is rejected; light jets fill the free
slots, i.e. light jets in the name = min(selected light jets,
4 - (e + m + b)). Extra jets are ignored and the event is kept; the
masses use only the kept leading-pT jets. Example: 1 muon + 5 light
jets is final state 0ex_1mx_3jx_0bx. The >=100-events rule counts
the merged final states.

THRESHOLDS APPLIED
------------------
* >= 100 events per final state, applied ONCE over the combined shards of
  all 541 per-file jobs.
* per-histogram minimum entries: NONE (upstream behaviour: >= 1 entry)
* filled-bin cut: NONE (applied on the BumpNet side during smoothing)

For information only, of the 313 delivered histograms:
  - 279 have 25 or more filled bins (what BumpNet's own cut keeps)
  - 278 have more than 25 filled bins
  - 268 have more than 30 filled bins

WHAT IS UNCHANGED FROM THE MUON DELIVERY
----------------------------------------
Object definitions, the b-tag working point, the golden-JSON run filter,
the Version B reject rule (reject an event if electrons + muons + b-jets
> 4), the 186 combinations, the fixed 10 GeV binning, the Z-peak cut at
110 GeV, the bin-aligned outlier split, the max-mass cut and peak removal.
