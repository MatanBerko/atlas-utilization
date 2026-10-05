BumpNet delivery -- Version B (rare4), EXACT light-jet final states
===================================================================

WHICH FILE TO USE
-----------------
    muon_combined_matched_vB_exactlabels_bumpnet_cropped.root

That is the file for BumpNet. It is the CROPPED one: every histogram has
been trimmed to its first..last filled bin, so the first bin is never
empty, which is what BumpNet requires.

    muon_combined_matched_vB_exactlabels_bumpnet.root

is the same 1329 histograms UNCROPPED, on the full fixed
0-10000 GeV grid. It is for cross-checking and plotting only; do not feed
it to BumpNet.

WHAT IS IN IT
-------------
1329 histograms over 78 distinct final-state
categories, on the unchanged fixed grid: 0-10000 GeV in 10 GeV bins.

THREE THINGS ARE DIFFERENT FROM THE 1 OCT DELIVERY
--------------------------------------------------
1. EXACT LIGHT-JET FINAL STATES. Each light-jet multiplicity now has its
   own final state. Previously any count above 4 was written as "4", so
   events with 5, 6, 7 ... light jets were all filed under "4j" and their
   masses were merged into the 4j histograms. Now there are separate 5j,
   6j, 7j ... final states. The name format is unchanged (e.g.
   0ex_2mx_5jx_0gx_0tx_1bx); only the digits can now exceed 4.

2. Z-PEAK CUT 115 -> 110 GeV, so the cut lands on a 10 GeV bin edge
   instead of in the middle of a bin. Follows upstream commit 8120fb8
   (PR #27). It affects same-flavour dilepton channels only. The outlier
   split (the cut at the first empty bin in the high-mass tail) is
   likewise now aligned to the same fixed 10 GeV grid starting at 0.

3. NO FILLED-BIN CUT. Earlier deliveries shipped two files, one requiring
   more than 30 filled bins and one more than 25. This delivery applies NO
   filled-bin requirement at all, because that cut is applied on the
   BumpNet side during smoothing. There is therefore ONE histogram set,
   not two.

   For information only, of the 1329 delivered histograms:
     - 1243 have 25 or more filled bins (what BumpNet's own cut keeps)
     - 1233 have more than 25 filled bins (the old min26bins rule)
     - 1177 have more than 30 filled bins (the old min31bins rule)

WHAT IS UNCHANGED
-----------------
Object definitions, trigger matching, de-duplication, the golden-JSON run
filter, the Version B reject rule (reject an event if electrons + muons +
b-jets > 4, otherwise keep ALL selected light jets), the 186 combinations,
the fixed 10 GeV binning, the >=100-events-per-final-state rule, the
max-mass cut, and peak removal.

STILL OPEN, NOT DECIDED HERE
----------------------------
- The per-histogram ">=100 entries" requirement is still applied,
  unchanged. It excluded 167 histogram(s) at the post-processing
  step (fewer than 100 entries survived the chain) and 0 at the
  histogram-filling step. Whether it should stay is a question for Maryna.
- The final-state NAME FORMAT (six fields e/m/j/g/t/b) is unchanged and is
  also an open question with Maryna.

Combination rule (unchanged): per signature, DoubleMuon INCLUSIVE raw
masses pooled with SingleMuon EXCLUSIVE raw masses.

Built from 57 DoubleMuon and 152 SingleMuon per-file shards.
