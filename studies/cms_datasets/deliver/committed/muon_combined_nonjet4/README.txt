Combined DoubleMuon+SingleMuon BumpNet histograms -- nonjet4 final-state version
================================================================================

WHAT THIS IS
-------------
BumpNet-ready invariant-mass histograms built from the CMS Open Data
DoubleMuon and SingleMuon primary datasets, Run2016 G+H, using the SAME
trigger-matched population as the earlier "normal" and "top-4" combined
deliveries in this study (see deliver/muon_combined/README.txt for the
full dataset/trigger/matching/priority-veto/duplicate-rate background --
none of that changed here):
  - DoubleMuon: records 30522 (29 files) + 30555 (28 files), 57 files
    total, 94,148,416 raw events.
  - SingleMuon: records 30530 (70 files) + 30563 (82 files), 152 files
    total, 323,952,013 raw events. Trigger, in this delivery: HLT_IsoMu24
    alone.

THE NONJET4 RULE
-------------------
This is a NEW final-state definition, given to us by the group (Shikma,
from the ATLAS BumpNet analysers), built on top of the existing top-4
truncation:

  Trigger matching, DoubleMuon acceptance, the SingleMuon veto, and the
  >=2-selected-objects gate are evaluated on the full event, exactly as
  for the normal and top-4 versions, BEFORE this rule -- an event's
  acceptance and which dataset it belongs to never depend on this rule.

  Let N = (selected electrons + selected muons + selected b-jets) for an
  already-accepted event. Light jets never count toward N and never
  cause rejection.

    - If N > 4: the event is REJECTED from this version entirely (it
      contributes nothing -- no final-state category, no combinations).
    - If N <= 4: ALL selected electrons, muons and b-jets are kept, and
      selected light jets are added, in decreasing pT order, until the
      total number of kept objects reaches 4 (or there are no more light
      jets left).

  This is IDENTICAL to the existing top-4 rule for every event with
  N <= 4 (top-4's own priority order is leptons, then b-jets, then light
  jets, so whenever N<=4 every lepton/b-jet already has priority rank <4
  and is kept unconditionally, with the remaining slots filled by light-
  jet pT exactly as this rule specifies). The ONLY difference from top-4
  is that events with N > 4 are REJECTED instead of truncated to 4
  objects.

Full validation (every hard check passed on the 4 pilot files AND on the
full 209-job production run): see
studies/cms_datasets/matching/nonjet4/NONJET4_STEP2_VALIDATION.md and
NONJET4_STEP4_IDENTITY_CHECKS.md.

REJECTION RATE
-----------------
Across the full production run, 5,738 of the 172,893,893 events accepted
into the normal/top-4 population (DoubleMuon 9,449,024 + SingleMuon
163,444,869) were rejected by the N>4 rule -- about 0.0033%. See
NONJET4_REPORT.md for the per-dataset breakdown, the N-distribution and
electron/muon/b-jet composition of the rejected events, and the fraction
of KEPT events that had one or more selected light jets dropped by the
pT-ordered padding step.

FILES IN THIS DELIVERY
-------------------------
muon_combined_matched_nonjet4_bumpnet_min31bins.root           nonjet4 version, >30 filled bins, UNCROPPED.
muon_combined_matched_nonjet4_bumpnet_min31bins_cropped.root   nonjet4 version, >30 filled bins, CROPPED. Use this one for BumpNet.
muon_combined_matched_nonjet4_bumpnet_min26bins.root           nonjet4 version, >25 filled bins, UNCROPPED.
muon_combined_matched_nonjet4_bumpnet_min26bins_cropped.root   nonjet4 version, >25 filled bins, CROPPED. Use this one for BumpNet.
manifest_muon_combined_matched_nonjet4_min31bins.json          per-histogram detail, uncropped, 148 entries.
manifest_muon_combined_matched_nonjet4_min26bins.json          per-histogram detail, uncropped, 159 entries.
build_summary.json                                              identity/funnel build log.
crop_summary.json                                               build/verification log for the 2 cropped files.
NONJET4_REPORT.md                                                full quality-gate report.
plots/                                                           all required PNGs.
README.txt                                                       this file.

CROPPED vs UNCROPPED
-----------------------
CROPPED means the leading (and trailing, if present) all-empty region on
the fixed grid has been genuinely removed -- a smaller TH1F, not a
display-range restriction -- so bin 1 of every cropped histogram is
non-empty (BumpNet's loader drops any histogram whose bin 1 is zero).
Verified independently with both uproot and real PyROOT 6.40.02 (LCG_110,
x86_64-el9-gcc13-opt) for all 148/159 histograms, in both uncropped and
both cropped files -- histogram names unique, counts match the
manifests, every histogram has more filled bins than its own threshold
and >=100 events, and cropped values equal the uncropped values over the
kept (non-empty) range exactly, by both readers independently, agreeing
with each other.

EACH HISTOGRAM NAME APPEARS EXACTLY ONCE PER FILE
----------------------------------------------------
Confirmed directly: uproot and PyROOT both report zero duplicate keys in
every one of the 4 ROOT files (verification_summary.json).

VERIFICATION PERFORMED FOR THIS DELIVERY
------------------------------------------
- All 57 DoubleMuon and 152 SingleMuon source files present exactly once,
  sum of raw events read matches the CMS Open Data portal's own published
  totals exactly (94,148,416 and 323,952,013), a single pinned git commit
  (3c7c9c97cdc9788d108f61156c05963b7fc1f0a4) used by every one of the 209
  production jobs, zero CAPPED:: shard entries anywhere (normal, top-4,
  AND nonjet4 shards) -- see
  studies/cms_datasets/matching/nonjet4/NONJET4_STEP4_IDENTITY_CHECKS.md.
- The normal and top-4 shards of every one of the 209 jobs are byte-for-
  byte identical to the already-delivered runs_matched/ baseline -- Step
  1's nonjet4 addition changed nothing else, full dataset, not just the
  pilot files.
- The pre-existing deliver/muon_combined/ delivery (in use by Maryna) is
  confirmed byte-identical and untouched: same file sizes and
  modification timestamps as before this task began, for all 8 of its
  ROOT files.
- See NONJET4_REPORT.md for the full rejection/composition breakdown,
  the count table across normal/top-4/nonjet4, the Z/J-psi resonance
  check, lepton-content breakdown, and the required plots.
