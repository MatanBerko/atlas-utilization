Combined DoubleMuon+SingleMuon BumpNet histograms -- rare4 final-state version
================================================================================

WHAT THIS IS
-------------
BumpNet-ready invariant-mass histograms built from the CMS Open Data
DoubleMuon and SingleMuon primary datasets, Run2016 G+H, using the SAME
trigger-matched population as the earlier "normal", "top-4" and
"nonjet4" combined deliveries in this study (see
deliver/muon_combined/README.txt for the full dataset/trigger/matching/
priority-veto/duplicate-rate background -- none of that changed here):
  - DoubleMuon: records 30522 (29 files) + 30555 (28 files), 57 files
    total, 94,148,416 raw events.
  - SingleMuon: records 30530 (70 files) + 30563 (82 files), 152 files
    total, 323,952,013 raw events. Trigger, in this delivery: HLT_IsoMu24
    alone.

TWO CANDIDATE READINGS -- THIS IS NOT YET "THE" DELIVERY
------------------------------------------------------------
The group has not yet decided between two possible readings of the
final-state question. **Version A ("nonjet4")** is already delivered at
`deliver/muon_combined_nonjet4/`. **This file is Version B ("rare4")**.
Both use the identical N>4 rejection rule and reject the exact same
events; they differ only in what a KEPT (N<=4) event's own light jets
look like afterward. Nothing here should be treated as "the" delivery
until the group chooses one.

THE RARE4 RULE
-----------------
Trigger matching, DoubleMuon acceptance, the SingleMuon veto, and the
>=2-selected-objects gate are evaluated on the full event, exactly as
for the normal/top-4/nonjet4 versions, BEFORE this rule -- an event's
acceptance and which dataset it belongs to never depend on this rule.

  Let N = (selected electrons + selected muons + selected b-jets) for an
  already-accepted event, using the TRUE per-event counts (never a
  display-capped label).

    - If N > 4: the event is REJECTED entirely (same rule as nonjet4 --
      identical rejected-event set).
    - If N <= 4: keep EVERY selected object, INCLUDING every selected
      light jet, completely unpadded and untruncated, then proceed
      exactly as the existing NORMAL version already does: same final-
      state labelling, same combinations (at most 4 objects per
      invariant-mass combination, unchanged), and the normal version's
      own existing convention of capping each object type's DISPLAYED
      count at 4 in the histogram name (e.g. 5, 6, or more light jets
      are all shown as "4j" -- the name does not distinguish them, but
      every one of them is still used in the actual mass combinations).

  In other words: **rare4 = the normal version with events of true
  N > 4 removed.** Unlike nonjet4, rare4 never pads or truncates a kept
  event's own object list -- it is otherwise byte-for-byte the normal
  version's own final-state/combination logic.

Full validation (every hard check passed on the 4 pilot files AND on the
full 209-job production run): see
studies/cms_datasets/matching/rare4/RARE4_STEP2_VALIDATION.md and
RARE4_STEP4_IDENTITY_CHECKS.md.

DISPLAY-CAP CONVENTION (documented, not changed)
----------------------------------------------------
This is the SAME convention the normal version has always used
(services.calculations.physics_calcs.limit_particles_in_fs, unchanged):
each object type's count is capped at 4 in the HISTOGRAM NAME only --
an event with 6 light jets is labelled "...4j..." exactly the same as
an event with 4. The underlying raw event population is grouped by its
TRUE (uncapped) counts and all its genuine combinations are computed;
only the display name collapses anything above 4 to "4". This task does
NOT give jets beyond 4 their own categories (no "5j", "6j", ...) -- that
would be a change to the existing pipeline convention, out of scope.

REJECTION RATE AND HIDDEN CASES
-----------------------------------
Identical rejected-event set to nonjet4: 5,738 of 172,595,115 accepted
events (0.0033%) rejected across the full production run -- see
RARE4_REPORT.md for the full composition breakdown. A "hidden" case is a
rejected event whose DISPLAY-CAPPED label would read e+m+b<=4 (e.g. 5
muons shown as "4m"), masking the true N>4 rejection from anyone reading
only the category name. The full-dataset count of hidden cases is
**zero** -- explained in RARE4_REPORT.md (every accepted event has >=1
matched muon, so a hidden case would need >=5 muons with 0 electrons and
0 b-jets, and no rejected event in this dataset ever has more than 4
muons).

MEASURED DUPLICATE RATE
-------------------------
Unchanged from the normal/top-4/nonjet4 deliveries: the design task's
own closure test found ~4 double-counted collisions per million events
(SAME physical collision independently reconstructed in both datasets'
own separate productions, differing by a single offline-quality flag).
This delivery does NOT add event-ID-based de-duplication (Matan's
explicit decision, unchanged) -- the rate is disclosed here instead, not
hidden.

FILES IN THIS DELIVERY
-------------------------
muon_combined_matched_rare4_bumpnet_min31bins.root           rare4 version, >30 filled bins, UNCROPPED.
muon_combined_matched_rare4_bumpnet_min31bins_cropped.root   rare4 version, >30 filled bins, CROPPED. Use this one for BumpNet.
muon_combined_matched_rare4_bumpnet_min26bins.root           rare4 version, >25 filled bins, UNCROPPED.
muon_combined_matched_rare4_bumpnet_min26bins_cropped.root   rare4 version, >25 filled bins, CROPPED. Use this one for BumpNet.
manifest_muon_combined_matched_rare4_min31bins.json          per-histogram detail, uncropped, 928 entries.
manifest_muon_combined_matched_rare4_min26bins.json          per-histogram detail, uncropped, 960 entries.
build_summary.json                                             identity/funnel build log.
crop_summary.json                                              build/verification log for the 2 cropped files.
RARE4_REPORT.md                                                full quality-gate report.
plots/                                                          all required PNGs.
README.txt                                                      this file.

CROPPED vs UNCROPPED
-----------------------
CROPPED means the leading (and trailing, if present) all-empty region on
the fixed grid has been genuinely removed -- a smaller TH1F, not a
display-range restriction -- so bin 1 of every cropped histogram is
non-empty. Verified independently with both uproot and real PyROOT
6.40.02 (LCG_110, x86_64-el9-gcc13-opt) for all 928/960 histograms, in
both uncropped and both cropped files -- histogram names unique, counts
match the manifests, every histogram has more filled bins than its own
threshold and >=100 events, and cropped values equal the uncropped
values over the kept (non-empty) range exactly, by both readers
independently, agreeing with each other.

EACH HISTOGRAM NAME APPEARS EXACTLY ONCE PER FILE
----------------------------------------------------
Confirmed directly: uproot and PyROOT both report zero duplicate keys in
every one of the 4 ROOT files (verification_summary.json).

RARE4 vs. THE NAME-FILTERED NORMAL FILE
--------------------------------------------
A quick name-filter of the already-delivered normal file (removing every
final state whose label has e+m+b>4) predicted 960/928 histograms.
rare4's own build produced EXACTLY 960/928 -- zero differences at either
threshold (confirmed directly, both histogram-name sets identical; see
RARE4_REPORT.md and compare_rare4_vs_filtered_normal.py's own output).
This matches because the full-dataset hidden-case count is zero.

VERIFICATION PERFORMED FOR THIS DELIVERY
------------------------------------------
- All 57 DoubleMuon and 152 SingleMuon source files present exactly once,
  sum of raw events read matches the CMS Open Data portal's own published
  totals exactly (94,148,416 and 323,952,013), a single pinned git commit
  (635d261338b93190a4a19f5afab5ab4621be756f) used by every one of the 209
  production jobs, zero CAPPED:: shard entries anywhere (normal, top-4,
  nonjet4, AND rare4 shards) -- see
  studies/cms_datasets/matching/rare4/RARE4_STEP4_IDENTITY_CHECKS.md.
- The normal, top-4, and nonjet4 shards of every one of the 209 jobs are
  byte-for-byte identical to the already-delivered runs_matched_nonjet4/
  baseline -- Step 1's rare4 addition changed nothing else, full dataset.
- The pre-existing deliver/muon_combined/ and deliver/muon_combined_nonjet4/
  deliveries (in use by the group) are confirmed byte-identical and
  untouched: same file sizes and modification timestamps as before this
  task began, for all 12 of their ROOT files.
- See RARE4_REPORT.md for the full rejection/composition breakdown, the
  full funnel (a/a2/b/c/d/d'), the four-version count table, a plain-
  language nonjet4-vs-rare4 comparison, and the required plots.
