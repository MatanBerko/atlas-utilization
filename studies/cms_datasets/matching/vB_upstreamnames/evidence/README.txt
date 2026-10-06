BumpNet delivery -- Version B (rare4), EXACT light-jet final states
===================================================================

WHICH FILE TO USE
-----------------
    muon_combined_matched_vB_upstreamnames_bumpnet_cropped.root

That is the file for BumpNet. It is the CROPPED one: every histogram has
been trimmed to its first..last filled bin, so the first bin is never
empty, which is what BumpNet requires.

    muon_combined_matched_vB_upstreamnames_bumpnet.root

is the same 1496 histograms UNCROPPED, on the full fixed
0-10000 GeV grid. It is for cross-checking and plotting only; do not feed
it to BumpNet.

WHAT IS IN IT
-------------
1496 histograms over 81 distinct final-state
categories, on the unchanged fixed grid: 0-10000 GeV in 10 GeV bins.

THREE THINGS ARE DIFFERENT FROM THE 1 OCT DELIVERY
--------------------------------------------------
1. EXACT LIGHT-JET FINAL STATES. Each light-jet multiplicity has its own
   final state. Before 5 Oct any count above 4 was written as "4", so
   events with 5, 6, 7 ... light jets were all filed under "4j" and their
   masses were merged into the 4j histograms. There are now separate 5j,
   6j, 7j ... final states.

1b. NAME FORMAT: names now contain ONLY the configured object types --
   electrons, muons, light jets and b-jets -- in the upstream pipeline's
   own order, e.g. 0ex_2mx_5jx_1bx. The always-zero photon and tau fields
   (0gx, 0tx) are gone. This matches exactly what the main upstream
   pipeline produces for this configuration. Old name -> new name:
   mass_m0m1_cat_0ex_2mx_5jx_0gx_0tx_1bx -> mass_m0m1_cat_0ex_2mx_5jx_1bx.

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

   For information only, of the 1496 delivered histograms:
     - 1258 have 25 or more filled bins (what BumpNet's own cut keeps)
     - 1247 have more than 25 filled bins (the old min26bins rule)
     - 1188 have more than 30 filled bins (the old min31bins rule)

WHAT IS UNCHANGED
-----------------
Object definitions, trigger matching, de-duplication, the golden-JSON run
filter, the Version B reject rule (reject an event if electrons + muons +
b-jets > 4, otherwise keep ALL selected light jets), the 186 combinations,
the fixed 10 GeV binning, the >=100-events-per-final-state rule, the
max-mass cut, and peak removal.

PER-HISTOGRAM MINIMUM
---------------------
This delivery applies NO per-histogram minimum entry count. That
matches what the main upstream pipeline's own histogram stage does:
it writes a histogram whenever at least one value exists and writes
nothing when none does. BumpNet re-checks this during smoothing.
0 histogram(s) had no entries left after the processing chain and
so were not written, exactly as upstream would also not write them.

Combination rule (unchanged): per signature, DoubleMuon INCLUSIVE raw
masses pooled with SingleMuon EXCLUSIVE raw masses.

Built from 57 DoubleMuon and 152 SingleMuon per-file shards.
