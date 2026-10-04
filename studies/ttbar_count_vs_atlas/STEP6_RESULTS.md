# Step 6 - CMS ttbar study histograms, three variants

All numbers below are VERIFIED BY RUNNING unless a row says otherwise.
Histograms are RAW, unweighted counts, built with the SAME post-processing
as our delivery (fixed 10 GeV bins 0-10 TeV, 115 GeV Z-peak cutoff on
same-flavour dilepton channels, 10 TeV max-mass cutoff, peak removal,
first-empty-bin split, >= 100 events per final state and per histogram,
cropping), reusing the delivery builder functions unmodified.

## Events processed

| variant | events read | passing >= 2-object gate | rejected e+mu+b > 4 | dropped >= 5 light jets | into combinations |
|---|---:|---:|---:|---:|---:|
| rare4 | 43,546,000 | 40,947,069 | 88,738 | 0 | 40,858,331 |
| pr31 | 43,546,000 | 40,947,069 | 88,738 | 762,859 | 40,095,472 |
| pr31_noOR | 43,546,000 | 41,435,020 | 136,007 | 2,040,599 | 39,258,414 |

Sum of `genWeight` over every event in the record: **3.14013e+09** (FOR INFORMATION ONLY - it is never applied; the histograms are raw counts, as the ATLAS reference counts are).
Input files: 49.

## The funnel

| stage | rare4 | pr31 | pr31_noOR |
|---|---:|---:|---:|
| names with >= 1 event | 3987 | 2960 | 2843 |
| after >= 100 events per FINAL STATE | 2325 | 2315 | 2459 |
| after post-processing (>= 100 main events) | 2136 | 2136 | 2343 |
| >= 25 filled bins (ATLAS wording) | 2038 | 2038 | 2220 |
| > 25 filled bins (min26bins, our delivery) | 2028 | 2028 | 2203 |
| > 30 filled bins (min31bins) | 1955 | 1955 | 2101 |

## Headline: categories and histograms, against ATLAS and against our CMS data

| | categories | histograms |
|---|---:|---:|
| **ATLAS ttbar through PR #31** (reported by Maryna, >= 25 bins, >= 100 events) - NOT verified here | 135 | 2146 |
| CMS ttbar, rare4, >= 25 bins | 127 | 2038 |
| CMS ttbar, pr31, >= 25 bins | 127 | 2038 |
| CMS ttbar, pr31_noOR, >= 25 bins | 119 | 2220 |
| CMS ttbar, rare4, > 25 bins | 127 | 2028 |
| CMS ttbar, pr31, > 25 bins | 127 | 2028 |
| CMS ttbar, pr31_noOR, > 25 bins | 119 | 2203 |
| **our delivered CMS DATA** (rare4, > 25 bins, muon-triggered) | 55 | 960 |

## Categories by lepton content (>= 25 filled bins)

| variant | has >= 1 muon | electrons, no muon | no lepton | total |
|---|---:|---:|---:|---:|
| rare4 | 69 | 36 | 22 | 127 |
| pr31 | 69 | 36 | 22 | 127 |
| pr31_noOR | 62 | 35 | 22 | 119 |
| **delivered CMS data (reference)** | 55 | 0 | 0 | 55 |

## Histograms by lepton content (>= 25 filled bins)

| variant | has >= 1 muon | electrons, no muon | no lepton | total |
|---|---:|---:|---:|---:|
| rare4 | 1227 | 623 | 188 | 2038 |
| pr31 | 1227 | 623 | 188 | 2038 |
| pr31_noOR | 1406 | 626 | 188 | 2220 |
| **delivered CMS data (reference)** | 960 | 0 | 0 | 960 |

## How much of the category count the muon-trigger restriction removes

| variant | categories at >= 25 bins | of those, with >= 1 muon | lost to a muon requirement | share lost |
|---|---:|---:|---:|---:|
| rare4 | 127 | 69 | 58 | 46% |
| pr31 | 127 | 69 | 58 | 46% |
| pr31_noOR | 119 | 62 | 57 | 48% |

Every one of the delivered CMS data categories has at least one muon (55 of 55), which is what a DoubleMuon+SingleMuon trigger-matched selection must give. The rows above are therefore the part of the category space that our delivered CMS data cannot reach at all, independently of statistics.

## Per-variant object content of the surviving histograms (>= 25 bins)

| variant | b-jet-containing | lepton+jet | lepton-only | jet-only |
|---|---:|---:|---:|---:|
| rare4 | 1295 | 531 | 76 | 136 |
| pr31 | 1295 | 531 | 76 | 136 |
| pr31_noOR | 1376 | 623 | 63 | 158 |

