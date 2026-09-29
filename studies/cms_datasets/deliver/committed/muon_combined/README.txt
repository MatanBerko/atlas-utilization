Combined DoubleMuon+SingleMuon BumpNet histograms -- trigger-matched delivery
================================================================================

WHAT THIS IS
-------------
BumpNet-ready invariant-mass histograms built from the CMS Open Data
DoubleMuon and SingleMuon primary datasets, Run2016 G+H:
  - DoubleMuon: CERN Open Data records 30522 (Run2016G, 29 files) and
    30555 (Run2016H, 28 files), 57 files total, 94,148,416 raw events.
    Trigger: HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ OR
    HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ.
  - SingleMuon: records 30530 (Run2016G, 70 files) and 30563 (Run2016H,
    82 files), 152 files total, 323,952,013 raw events. Trigger, in this
    delivery ONLY: HLT_IsoMu24 alone (HLT_IsoTkMu24 excluded -- a
    deliberate choice, see TRIGGER MATCHING below).

TRIGGER MATCHING
-----------------
Unlike this study's earlier, purely trigger-BIT-based deliveries, this
one requires that the muon(s) which actually caused the trigger to fire
also pass this analysis's own offline selection (pT > 25 GeV, medium ID,
isolation) and be spatially matched (dR < 0.1) to the specific HLT
trigger object that fired the path. This fixes a bias flagged by Maryna:
without matching, an event could be counted as "DoubleMuon" purely
because the trigger fired, even if neither muon that fired it survives
offline selection. Full derivation, evidence, and the residual
approximations (documented, not hidden) are in
studies/cms_datasets/matching/TRIGGER_MATCHING_SPEC.md and
TRIGGER_MATCHING_REPORT.md in this repository.

THE PRIORITY-VETO COMBINATION
-------------------------------
BumpNet needs ONE ROOT file with each histogram name appearing exactly
once. DoubleMuon is veto priority 1 (its own "exclusive" set equals its
own "inclusive" set -- nothing outranks it here); SingleMuon is priority
2, so its own EXCLUSIVE shard already contains every SingleMuon-accepted
event that DoubleMuon did NOT also accept (checked using DoubleMuon's own
matched-trigger acceptance, not just its trigger bit). In plain terms:
each collision is taken from DoubleMuon if DoubleMuon accepts it,
otherwise from SingleMuon. Per signature, DoubleMuon's inclusive raw
masses and SingleMuon's exclusive raw masses are pooled together, then
the existing, unchanged post-processing (Z-peak cut, 10 TeV max-mass cut,
peak-removal, first-empty-bin split, >=100-event floor, fixed 10 GeV /
0-10,000 GeV grid, >25/>30-filled-bin thresholds, cropping) is run on the
pooled arrays -- exactly the same functions used by every earlier
per-dataset delivery in this study.

MEASURED DUPLICATE RATE
-------------------------
The design task's own closure test (one real run, 280016, spanning 13
real files of both datasets) found exactly 1 double-counted collision out
of 263,540 checked -- a rate of about 4 events per million. Root-caused
exactly: the SAME physical collision event, reconstructed independently
in DoubleMuon's own copy and SingleMuon's own copy (CMS produces each
primary dataset as its own separate production), had a muon whose
offline-quality flag (Medium ID) came out true in one copy and false in
the other -- a tiny, genuine numerical difference at the reconstruction
level, not a flaw in the combination logic. This delivery does NOT add
event-ID-based de-duplication (Matan's explicit decision) -- the rate is
disclosed here instead. At ~4-per-million, a handful of collisions in the
full ~478M-event combined population may in principle be counted twice;
this is not expected to be visible in any individual histogram.

THE TOP-4 VERSION
-------------------
In addition to the normal version (every selected object contributes),
this delivery includes a second, "top-4" version requested by Shikma and
Maryna: each ACCEPTED event's selected objects are truncated to at most 4
before the final-state category and combinations are built, using this
priority: (1) leptons -- electrons and muons together, ordered by pT,
highest first; (2) b-jets, by pT; (3) light jets, by pT -- until 4 objects
are kept. Trigger matching, the acceptance gate, and the DoubleMuon-veto
decision are all evaluated on the FULL event, BEFORE truncation -- an
event's acceptance and which dataset it belongs to never depend on
truncation. Events with <=4 objects are completely unchanged. See
studies/cms_datasets/matching/top4/ for the full validation (every hard
check passed: truncation never changes accepted-event counts; every
top-4 category has <=4 total objects; the normal version's arrays are a
sub-multiset of the top-4 version's for every shared low-object-count
category).

The normal version already keeps (never discards) events with more than
4 objects of one type -- it groups by the RAW, uncapped object counts,
computes masses on that full population, and only caps the DISPLAY LABEL
(and hence the histogram name) at 4 per type. A separate "discard events
with more than 4 objects entirely" variant would just be the normal
version's own categories restricted to a total object count of <=4 --
this delivery does not build that as a separate file; its histogram
counts are reported alongside the others in COMBINED_MUON_REPORT.md's own
summary table, computed from the existing shards, no new production.

FILES IN THIS DELIVERY
-------------------------
muon_combined_matched_bumpnet_min31bins.root            normal version, >30 filled bins, UNCROPPED.
muon_combined_matched_bumpnet_min31bins_cropped.root    normal version, >30 filled bins, CROPPED. Use this one for BumpNet.
muon_combined_matched_bumpnet_min26bins.root            normal version, >25 filled bins, UNCROPPED.
muon_combined_matched_bumpnet_min26bins_cropped.root    normal version, >25 filled bins, CROPPED. Use this one for BumpNet.
muon_combined_matched_top4_bumpnet_min31bins.root       top-4 version, >30 filled bins, UNCROPPED.
muon_combined_matched_top4_bumpnet_min31bins_cropped.root  top-4 version, >30 filled bins, CROPPED. Use this one for BumpNet.
muon_combined_matched_top4_bumpnet_min26bins.root       top-4 version, >25 filled bins, UNCROPPED.
muon_combined_matched_top4_bumpnet_min26bins_cropped.root  top-4 version, >25 filled bins, CROPPED. Use this one for BumpNet.
manifest_muon_combined_matched_min31bins.json           per-histogram detail, normal, uncropped 1025.
manifest_muon_combined_matched_min26bins.json           per-histogram detail, normal, uncropped 1097.
manifest_muon_combined_matched_top4_min31bins.json      per-histogram detail, top-4, uncropped 147.
manifest_muon_combined_matched_top4_min26bins.json      per-histogram detail, top-4, uncropped 161.
build_summary.json                                      identity/funnel build log, both versions.
crop_summary.json                                       build/verification log for the 4 cropped files.
COMBINED_MUON_REPORT.md                                 full quality-gate report.
plots/                                                   all required PNGs.
README.txt                                               this file.

CROPPED vs UNCROPPED
-----------------------
CROPPED means the leading (and trailing, if present) all-empty region on
the fixed grid has been genuinely removed -- a smaller TH1F, not a
display-range restriction -- so bin 1 of every cropped histogram is
non-empty (BumpNet's loader drops any histogram whose bin 1 is zero).
Verified independently with both uproot and real PyROOT 6.40.02 (LCG_110,
x86_64-el9-gcc15-opt) for all 1025/1097/147/161 histograms, in all 4
uncropped and all 4 cropped files -- histogram names unique, counts match
the manifests, every histogram has more filled bins than its own
threshold and >=100 events, and cropped values equal the uncropped
values over the kept (non-empty) range exactly, in every file, by both
readers independently, agreeing with each other.

EACH HISTOGRAM NAME APPEARS EXACTLY ONCE PER FILE
----------------------------------------------------
Confirmed directly: uproot and PyROOT both report zero duplicate keys in
every one of the 8 ROOT files (verification_summary.json).

VERIFICATION PERFORMED FOR THIS DELIVERY
------------------------------------------
- All 57 DoubleMuon and 152 SingleMuon source files present exactly once,
  sum of raw events read matches the CMS Open Data portal's own published
  totals exactly (94,148,416 and 323,952,013), a single pinned git commit
  used by every one of the 209 production jobs, zero CAPPED:: shard
  entries anywhere (normal and top-4 shards both) -- see
  studies/cms_datasets/matching/top4/TOP4_STEP4_IDENTITY_CHECKS.md.
- The 4 original pilot files reproduce their own earlier (smaller-scale)
  outputs exactly, at full-dataset scale.
- DoubleMuon inclusive == exclusive exactly (9,449,024 == 9,449,024,
  summed over all 57 files). SingleMuon's exclusive fraction at full
  scale is 94.273% -- matching the ~94.3% already seen at pilot scale.
- See COMBINED_MUON_REPORT.md for the full cutflow, Z/J-psi resonance
  checks, the trigger-mixing (DoubleMuon vs. SingleMuon-exclusive
  contribution) check, lepton-content breakdowns, and the low-mass/
  electron-muon-overlap diagnostics.
