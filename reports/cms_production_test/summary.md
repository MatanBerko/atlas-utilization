# CMS full-pipeline test - histogram results

- Source run: `output/cms_production_test_20260903_061350`
- Histogram file: `histograms/atlas_opendata_full_bumpnet.root` (one ROOT file, one TH1F per channel)
- BumpNet usability bar (arXiv:2501.05603): **at least 100 entries AND more than 30 bins**

## Totals

| | count |
|---|---:|
| Histograms produced | 384 |
| **Meet BumpNet bar** (>= 100 entries & > 30 bins) | **240** |
| Fall short | 144 |
| &nbsp;&nbsp;- short on bin count (<= 30 bins) | 142 |
| &nbsp;&nbsp;- short on entries (< 100) | 44 |

_(A histogram can be short on both; the two sub-rows overlap.)_

> Note: of the 240 that meet the numeric bar, **12** have 90%+ of their entries piled into a single low-mass bin (a flat spike, not a real distribution). These pass the entry/bin count but are not useful BumpNet inputs. It looks like the post-processing outlier-split is sending the real mass distribution to the discarded "outliers" side for some 2-body combinations - flagged for a later look, not touched here.

## Passing histograms (usable as BumpNet input)

Sorted by entry count, highest first. "Mass of" is which object four-vectors were added together to form the invariant mass; "Event category" is the object multiplicity of the events that fed it.

| # | Mass of | Event category | Entries | Bins | Filled bins | Shape | Mass range (GeV) | Histogram name |
|---:|---|---|---:|---:|---:|---|---|---|
| 1 | e0 + jet0 | 1e, 1jet, 1γ, 1τ | 1,808,895 | 43 | 43 | spike | -1 - 423 | `ROI_mass_e0j0_cat_1ex_0mx_1jx_1gx_1tx_0bx_width_10.0` |
| 2 | jet0 + γ0 | 1e, 1jet, 1γ, 1τ | 1,808,895 | 43 | 43 | spike | -1 - 422 | `ROI_mass_j0g0_cat_1ex_0mx_1jx_1gx_1tx_0bx_width_10.0` |
| 3 | e0 + jet0 + γ0 | 1e, 1jet, 1γ, 1τ | 1,808,865 | 47 | 47 | spike | -1 - 464 | `ROI_mass_e0j0g0_cat_1ex_0mx_1jx_1gx_1tx_0bx_width_10.0` |
| 4 | e0 + γ0 | 1e, 2jet, 1γ, 1τ | 976,849 | 58 | 58 | spike | -1 - 574 | `ROI_mass_e0g0_cat_1ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 5 | e0 + jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 1τ | 772,805 | 284 | 284 | distribution | 151 - 2989 | `ROI_mass_e0j0j1g0_cat_1ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 6 | e0 + jet0 + jet1 | 1e, 2jet, 1γ, 1τ | 766,405 | 262 | 262 | distribution | 127 - 2746 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 7 | jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 1τ | 761,757 | 228 | 228 | distribution | 127 - 2402 | `ROI_mass_j0j1g0_cat_1ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 8 | e0 + γ0 | 1e, 2jet, 1γ | 389,707 | 83 | 81 | spike | -1 - 825 | `ROI_mass_e0g0_cat_1ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 9 | e0 + jet0 + jet1 | 1e, 2jet, 1γ | 345,111 | 311 | 311 | distribution | 128 - 3231 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 10 | jet0 + jet1 + γ0 | 1e, 2jet, 1γ | 344,076 | 321 | 321 | distribution | 128 - 3331 | `ROI_mass_j0j1g0_cat_1ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 11 | e0 + jet0 + jet1 + γ0 | 1e, 2jet, 1γ | 330,995 | 347 | 347 | distribution | 162 - 3625 | `ROI_mass_e0j0j1g0_cat_1ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 12 | e0 + γ0 | 1e, 3jet, 1γ, 1τ | 288,812 | 71 | 71 | spike | -2 - 703 | `ROI_mass_e0g0_cat_1ex_0mx_3jx_1gx_1tx_0bx_width_10.0` |
| 13 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 1γ, 1τ | 237,145 | 309 | 309 | distribution | 234 - 3315 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_1gx_1tx_0bx_width_10.0` |
| 14 | jet0 + jet1 + jet2 + γ0 | 1e, 3jet, 1γ, 1τ | 236,516 | 308 | 307 | distribution | 234 - 3311 | `ROI_mass_j0j1j2g0_cat_1ex_0mx_3jx_1gx_1tx_0bx_width_10.0` |
| 15 | e0 + γ0 | 1e, 3jet, 1γ | 198,053 | 86 | 86 | spike | -2 - 855 | `ROI_mass_e0g0_cat_1ex_0mx_3jx_1gx_0tx_0bx_width_10.0` |
| 16 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 1γ | 121,551 | 352 | 352 | distribution | 524 - 4037 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_1gx_0tx_0bx_width_10.0` |
| 17 | jet0 + jet1 + jet2 + γ0 | 1e, 3jet, 1γ | 120,868 | 328 | 328 | distribution | 527 - 3805 | `ROI_mass_j0j1j2g0_cat_1ex_0mx_3jx_1gx_0tx_0bx_width_10.0` |
| 18 | jet0 + jet1 + γ0 + γ1 | 2e, 2jet, 2γ, 2τ | 114,533 | 96 | 96 | distribution | 192 - 1151 | `ROI_mass_j0j1g0g1_cat_2ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 19 | e0 + e1 + γ0 + γ1 | 2e, 2jet, 2γ, 2τ | 113,425 | 73 | 73 | peaky | 175 - 900 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 20 | e0 + jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 2τ | 105,995 | 156 | 156 | distribution | 163 - 1721 | `ROI_mass_e0j0j1g0_cat_1ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 21 | jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 2τ | 102,347 | 149 | 148 | distribution | 138 - 1619 | `ROI_mass_j0j1g0_cat_1ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 22 | e0 + jet0 + jet1 | 1e, 2jet, 1γ, 2τ | 102,174 | 143 | 143 | distribution | 139 - 1566 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 23 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 2γ, 2τ | 102,139 | 78 | 78 | peaky | 195 - 967 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 24 | e0 + γ0 | 1e, 4jet, 1γ, 1τ | 93,449 | 54 | 54 | spike | -1 - 538 | `ROI_mass_e0g0_cat_1ex_0mx_4jx_1gx_1tx_0bx_width_10.0` |
| 25 | e0 + γ0 | 1e, 4jet, 1γ | 87,250 | 71 | 71 | spike | -1 - 707 | `ROI_mass_e0g0_cat_1ex_0mx_4jx_1gx_0tx_0bx_width_10.0` |
| 26 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 1γ, 2τ | 54,876 | 195 | 195 | distribution | 231 - 2175 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_1gx_2tx_0bx_width_10.0` |
| 27 | jet0 + jet1 + jet2 + γ0 | 1e, 3jet, 1γ, 2τ | 54,810 | 189 | 189 | distribution | 231 - 2115 | `ROI_mass_j0j1j2g0_cat_1ex_0mx_3jx_1gx_2tx_0bx_width_10.0` |
| 28 | e0 + jet0 + jet1 | 1e, 2jet, 2γ, 1τ | 43,132 | 140 | 140 | distribution | 139 - 1537 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 29 | e0 + jet0 + γ0 | 1e, 1jet, 1γ, 2τ | 42,272 | 31 | 31 | spike | -0 - 306 | `ROI_mass_e0j0g0_cat_1ex_0mx_1jx_1gx_2tx_0bx_width_10.0` |
| 30 | e0 + jet0 + jet1 | 1e, 2jet, 1τ | 40,841 | 187 | 186 | distribution | 121 - 1985 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_0gx_1tx_0bx_width_10.0` |
| 31 | jet0 + jet1 + γ0 + γ1 | 1e, 2jet, 2γ, 1τ | 39,006 | 155 | 155 | distribution | 195 - 1741 | `ROI_mass_j0j1g0g1_cat_1ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 32 | e0 + γ0 + γ1 | 1e, 3jet, 2γ | 38,705 | 187 | 186 | distribution | 1 - 1871 | `ROI_mass_e0g0g1_cat_1ex_0mx_3jx_2gx_0tx_0bx_width_10.0` |
| 33 | e0 + γ0 + γ1 | 1e, 2jet, 2γ | 37,292 | 173 | 172 | distribution | 1 - 1724 | `ROI_mass_e0g0g1_cat_1ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 34 | e0 + γ0 + γ1 | 1e, 2jet, 2γ, 1τ | 36,366 | 108 | 108 | distribution | 121 - 1195 | `ROI_mass_e0g0g1_cat_1ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 35 | e0 + jet0 + jet1 | 1e, 2jet | 27,260 | 186 | 185 | distribution | 122 - 1980 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_0gx_0tx_0bx_width_10.0` |
| 36 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 2γ | 26,216 | 238 | 238 | distribution | 562 - 2933 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_2gx_0tx_0bx_width_10.0` |
| 37 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 2γ, 1τ | 26,032 | 206 | 204 | distribution | 304 - 2357 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_2gx_1tx_0bx_width_10.0` |
| 38 | e0 + γ0 + γ1 | 1e, 3jet, 2γ, 1τ | 24,759 | 102 | 102 | distribution | 121 - 1138 | `ROI_mass_e0g0g1_cat_1ex_0mx_3jx_2gx_1tx_0bx_width_10.0` |
| 39 | e0 + e1 + γ0 + γ1 | 2e, 3jet, 2γ, 2τ | 24,557 | 85 | 84 | peaky | 175 - 1020 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_3jx_2gx_2tx_0bx_width_10.0` |
| 40 | e0 + γ0 + γ1 | 1e, 4jet, 2γ | 23,553 | 168 | 167 | distribution | 1 - 1675 | `ROI_mass_e0g0g1_cat_1ex_0mx_4jx_2gx_0tx_0bx_width_10.0` |
| 41 | e0 + jet0 + jet1 | 1e, 2jet, 2γ | 22,559 | 183 | 183 | distribution | 416 - 2240 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 42 | jet0 + jet1 + γ0 + γ1 | 1e, 2jet, 2γ | 22,286 | 213 | 213 | distribution | 505 - 2633 | `ROI_mass_j0j1g0g1_cat_1ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 43 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 2γ, 1τ | 20,919 | 148 | 147 | distribution | 196 - 1675 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 44 | jet0 + jet1 + γ0 + γ1 | 2e, 2jet, 2γ, 1τ | 20,035 | 156 | 156 | distribution | 198 - 1752 | `ROI_mass_j0j1g0g1_cat_2ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 45 | e0 + e1 + γ0 + γ1 | 2e, 2jet, 2γ, 1τ | 19,713 | 126 | 126 | distribution | 175 - 1432 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 46 | e0 + γ0 | 1e, 1μ, 2jet, 1γ | 19,064 | 35 | 34 | spike | -1 - 346 | `ROI_mass_e0g0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 47 | e0 + μ0 | 1e, 1μ, 2jet, 1γ | 18,937 | 104 | 104 | distribution | -1 - 1036 | `ROI_mass_e0m0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 48 | e0 + μ0 + γ0 | 1e, 1μ, 2jet, 1γ | 18,936 | 148 | 148 | distribution | -1 - 1475 | `ROI_mass_e0m0g0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 49 | μ0 + γ0 | 1e, 1μ, 2jet, 1γ | 18,935 | 104 | 104 | distribution | -1 - 1038 | `ROI_mass_m0g0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 50 | e0 + jet0 + jet1 | 1e, 1μ, 2jet, 1γ | 16,524 | 156 | 156 | distribution | 176 - 1733 | `ROI_mass_e0j0j1_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 51 | e0 + μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 1γ | 15,057 | 198 | 198 | distribution | 320 - 2298 | `ROI_mass_e0m0j0j1_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 52 | μ0 + jet0 + jet1 + γ0 | 1e, 1μ, 2jet, 1γ | 14,963 | 157 | 157 | distribution | 322 - 1889 | `ROI_mass_m0j0j1g0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 53 | μ0 + γ0 | 1e, 1μ, 3jet, 1γ | 14,794 | 114 | 113 | distribution | -0 - 1137 | `ROI_mass_m0g0_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 54 | e0 + μ0 | 1e, 1μ, 3jet, 1γ | 14,793 | 114 | 114 | distribution | -1 - 1135 | `ROI_mass_e0m0_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 55 | e0 + μ0 + γ0 | 1e, 1μ, 3jet, 1γ | 14,723 | 125 | 124 | distribution | -1 - 1245 | `ROI_mass_e0m0g0_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 56 | e0 + jet0 + jet1 + γ0 | 1e, 1μ, 2jet, 1γ | 14,475 | 205 | 205 | distribution | 280 - 2320 | `ROI_mass_e0j0j1g0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 57 | jet0 + jet1 + γ0 | 1e, 1μ, 2jet, 1γ | 13,900 | 140 | 140 | distribution | 255 - 1654 | `ROI_mass_j0j1g0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 58 | e0 + γ0 + γ1 | 1e, 4jet, 2γ, 1τ | 13,337 | 91 | 91 | distribution | 121 - 1029 | `ROI_mass_e0g0g1_cat_1ex_0mx_4jx_2gx_1tx_0bx_width_10.0` |
| 59 | μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 1γ | 13,010 | 147 | 147 | distribution | 321 - 1790 | `ROI_mass_m0j0j1_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 60 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 1τ | 12,800 | 227 | 227 | distribution | 222 - 2488 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_0gx_1tx_0bx_width_10.0` |
| 61 | e0 + e1 + γ0 + γ1 | 2e, 2jet, 2γ | 12,794 | 194 | 194 | distribution | 176 - 2112 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 62 | e0 + e1 + γ0 + γ1 | 2e, 3jet, 2γ, 1τ | 11,547 | 140 | 140 | distribution | 175 - 1572 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_3jx_2gx_1tx_0bx_width_10.0` |
| 63 | e0 + jet0 + jet1 + jet2 | 1e, 3jet | 11,532 | 261 | 261 | distribution | 208 - 2816 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_0gx_0tx_0bx_width_10.0` |
| 64 | e0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 1γ | 10,303 | 169 | 169 | distribution | 498 - 2183 | `ROI_mass_e0j0j1j2_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 65 | μ0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 1γ | 9,954 | 185 | 185 | distribution | 514 - 2358 | `ROI_mass_m0j0j1j2_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 66 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 2γ | 9,666 | 193 | 193 | distribution | 495 - 2425 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 67 | jet0 + jet1 + jet2 + γ0 | 1e, 1μ, 3jet, 1γ | 9,569 | 193 | 193 | distribution | 545 - 2473 | `ROI_mass_j0j1j2g0_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 68 | e0 + e1 + γ0 + γ1 | 2e, 3jet, 2γ | 9,227 | 154 | 154 | distribution | 345 - 1882 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_3jx_2gx_0tx_0bx_width_10.0` |
| 69 | jet0 + jet1 + γ0 + γ1 | 2e, 2jet, 2γ | 8,609 | 173 | 173 | distribution | 561 - 2284 | `ROI_mass_j0j1g0g1_cat_2ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 70 | e0 + γ0 | 1e, 1μ, 4jet, 1γ | 8,489 | 31 | 31 | spike | -1 - 305 | `ROI_mass_e0g0_cat_1ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 71 | e0 + μ0 | 1e, 1μ, 4jet, 1γ | 8,457 | 100 | 100 | distribution | -1 - 998 | `ROI_mass_e0m0_cat_1ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 72 | μ0 + γ0 | 1e, 1μ, 4jet, 1γ | 8,443 | 94 | 92 | distribution | -0 - 935 | `ROI_mass_m0g0_cat_1ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 73 | e0 + μ0 + γ0 | 1e, 1μ, 4jet, 1γ | 8,381 | 106 | 106 | distribution | 0 - 1053 | `ROI_mass_e0m0g0_cat_1ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 74 | e0 + jet0 + jet1 | 1e, 2jet, 2γ, 2τ | 7,818 | 59 | 59 | distribution | 153 - 740 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 75 | jet0 + jet1 + γ0 + γ1 | 1e, 2jet, 2γ, 2τ | 7,644 | 96 | 96 | distribution | 200 - 1157 | `ROI_mass_j0j1g0g1_cat_1ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 76 | e0 + e1 + γ0 + γ1 | 2e, 4jet, 2γ, 2τ | 7,189 | 79 | 79 | peaky | 175 - 963 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_4jx_2gx_2tx_0bx_width_10.0` |
| 77 | e0 + γ0 + γ1 | 1e, 2jet, 2γ, 2τ | 6,908 | 53 | 53 | distribution | 122 - 647 | `ROI_mass_e0g0g1_cat_1ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 78 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 2γ, 2τ | 6,550 | 137 | 137 | distribution | 252 - 1615 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_2gx_2tx_0bx_width_10.0` |
| 79 | e0 + e1 + γ0 + γ1 | 2e, 4jet, 2γ, 1τ | 6,027 | 138 | 138 | distribution | 175 - 1552 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_4jx_2gx_1tx_0bx_width_10.0` |
| 80 | e0 + γ0 + γ1 | 1e, 3jet, 2γ, 2τ | 5,616 | 66 | 66 | distribution | 120 - 774 | `ROI_mass_e0g0g1_cat_1ex_0mx_3jx_2gx_2tx_0bx_width_10.0` |
| 81 | e0 + jet0 + jet1 | 1e, 2jet, 2τ | 5,153 | 92 | 92 | distribution | 118 - 1035 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_0gx_2tx_0bx_width_10.0` |
| 82 | jet0 + jet1 + γ0 | 2e, 2jet, 1γ, 2τ | 5,007 | 52 | 52 | distribution | 154 - 673 | `ROI_mass_j0j1g0_cat_2ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 83 | e0 + e1 + γ0 + γ1 | 2e, 4jet, 2γ | 4,878 | 146 | 144 | distribution | 365 - 1816 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_4jx_2gx_0tx_0bx_width_10.0` |
| 84 | jet0 + jet1 + jet2 + γ0 | 2e, 3jet, 1γ | 4,714 | 169 | 169 | distribution | 511 - 2196 | `ROI_mass_j0j1j2g0_cat_2ex_0mx_3jx_1gx_0tx_0bx_width_10.0` |
| 85 | jet0 + jet1 + γ0 | 2e, 2jet, 1γ, 1τ | 4,657 | 118 | 118 | distribution | 156 - 1332 | `ROI_mass_j0j1g0_cat_2ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 86 | jet0 + jet1 + jet2 + γ0 | 1e, 3jet, 1γ, 3τ | 4,498 | 105 | 105 | distribution | 220 - 1268 | `ROI_mass_j0j1j2g0_cat_1ex_0mx_3jx_1gx_3tx_0bx_width_10.0` |
| 87 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 1γ, 1τ | 4,496 | 132 | 131 | distribution | 206 - 1520 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 88 | e0 + e1 + γ0 | 2e, 3jet, 1γ | 4,407 | 96 | 96 | distribution | 175 - 1133 | `ROI_mass_e0e1g0_cat_2ex_0mx_3jx_1gx_0tx_0bx_width_10.0` |
| 89 | e0 + e1 + γ0 | 2e, 2jet, 1γ, 2τ | 4,406 | 43 | 43 | peaky | 125 - 546 | `ROI_mass_e0e1g0_cat_2ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 90 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 1γ, 3τ | 4,367 | 72 | 72 | distribution | 220 - 935 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_1gx_3tx_0bx_width_10.0` |
| 91 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 1γ | 4,112 | 148 | 147 | distribution | 511 - 1984 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 92 | e0 + e1 + γ0 | 2e, 2jet, 1γ, 1τ | 4,070 | 83 | 82 | distribution | 125 - 950 | `ROI_mass_e0e1g0_cat_2ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 93 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 1γ, 2τ | 4,007 | 48 | 48 | distribution | 208 - 679 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 94 | e0 + e1 + γ0 | 2e, 2jet, 1γ | 3,988 | 73 | 72 | distribution | 205 - 931 | `ROI_mass_e0e1g0_cat_2ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 95 | jet0 + jet1 + γ0 | 2e, 2jet, 1γ | 3,986 | 109 | 109 | distribution | 454 - 1540 | `ROI_mass_j0j1g0_cat_2ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 96 | e0 + γ0 + γ1 | 1e, 4jet, 2γ, 2τ | 3,495 | 73 | 73 | distribution | 122 - 845 | `ROI_mass_e0g0g1_cat_1ex_0mx_4jx_2gx_2tx_0bx_width_10.0` |
| 97 | e0 + μ0 | 1e, 1μ, 2jet | 3,476 | 47 | 47 | distribution | -0 - 468 | `ROI_mass_e0m0_cat_1ex_1mx_2jx_0gx_0tx_0bx_width_10.0` |
| 98 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 3γ | 3,339 | 121 | 121 | distribution | 541 - 1744 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_3gx_0tx_0bx_width_10.0` |
| 99 | e0 + μ0 | 1e, 1μ, 3jet, 2γ | 3,262 | 74 | 74 | distribution | -1 - 736 | `ROI_mass_e0m0_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 100 | e0 + γ0 + γ1 | 1e, 1μ, 3jet, 2γ | 3,245 | 96 | 94 | distribution | 0 - 954 | `ROI_mass_e0g0g1_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 101 | e0 + e1 + γ0 | 2e, 3jet, 1γ, 1τ | 3,211 | 67 | 67 | distribution | 125 - 789 | `ROI_mass_e0e1g0_cat_2ex_0mx_3jx_1gx_1tx_0bx_width_10.0` |
| 102 | e0 + μ0 | 1e, 1μ, 1jet, 1γ | 3,019 | 78 | 78 | distribution | -0 - 773 | `ROI_mass_e0m0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 103 | μ0 + γ0 | 1e, 1μ, 1jet, 1γ | 3,019 | 78 | 78 | distribution | -0 - 777 | `ROI_mass_m0g0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 104 | μ0 + jet0 | 1e, 1μ, 1jet, 1γ | 2,989 | 80 | 79 | distribution | 0 - 796 | `ROI_mass_m0j0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 105 | e0 + μ0 + γ0 | 1e, 1μ, 1jet, 1γ | 2,954 | 82 | 81 | distribution | 0 - 818 | `ROI_mass_e0m0g0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 106 | e0 + μ0 | 1e, 1μ, 3jet | 2,948 | 53 | 53 | distribution | -0 - 529 | `ROI_mass_e0m0_cat_1ex_1mx_3jx_0gx_0tx_0bx_width_10.0` |
| 107 | e0 + μ0 + jet0 | 1e, 1μ, 1jet, 1γ | 2,943 | 86 | 85 | distribution | -0 - 857 | `ROI_mass_e0m0j0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 108 | e0 + γ0 + γ1 + γ2 | 1e, 3jet, 3γ | 2,940 | 80 | 80 | distribution | 294 - 1092 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_3jx_3gx_0tx_0bx_width_10.0` |
| 109 | e0 + μ0 + jet0 + γ0 | 1e, 1μ, 1jet, 1γ | 2,894 | 86 | 86 | distribution | 1 - 857 | `ROI_mass_e0m0j0g0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 110 | μ0 + jet0 + γ0 | 1e, 1μ, 1jet, 1γ | 2,894 | 72 | 72 | distribution | 0 - 716 | `ROI_mass_m0j0g0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 111 | e0 + jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 3τ | 2,856 | 68 | 68 | distribution | 157 - 833 | `ROI_mass_e0j0j1g0_cat_1ex_0mx_2jx_1gx_3tx_0bx_width_10.0` |
| 112 | jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 3τ | 2,811 | 59 | 59 | distribution | 133 - 719 | `ROI_mass_j0j1g0_cat_1ex_0mx_2jx_1gx_3tx_0bx_width_10.0` |
| 113 | μ0 + jet0 + jet1 | 1e, 1μ, 2jet | 2,801 | 98 | 98 | distribution | 305 - 1277 | `ROI_mass_m0j0j1_cat_1ex_1mx_2jx_0gx_0tx_0bx_width_10.0` |
| 114 | jet0 + jet1 + jet2 + γ0 | 2e, 3jet, 1γ, 1τ | 2,738 | 114 | 114 | distribution | 447 - 1582 | `ROI_mass_j0j1j2g0_cat_2ex_0mx_3jx_1gx_1tx_0bx_width_10.0` |
| 115 | e0 + jet0 + jet1 | 1e, 2jet, 1γ, 3τ | 2,571 | 68 | 67 | distribution | 142 - 815 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_1gx_3tx_0bx_width_10.0` |
| 116 | e0 + μ0 | 1e, 1μ, 2jet, 2γ | 2,513 | 67 | 66 | distribution | -0 - 664 | `ROI_mass_e0m0_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 117 | e0 + γ0 + γ1 | 1e, 1μ, 2jet, 2γ | 2,498 | 80 | 80 | distribution | 1 - 798 | `ROI_mass_e0g0g1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 118 | e0 + e1 + γ0 | 2e, 4jet, 1γ | 2,436 | 67 | 67 | distribution | 175 - 840 | `ROI_mass_e0e1g0_cat_2ex_0mx_4jx_1gx_0tx_0bx_width_10.0` |
| 119 | e0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 2γ | 2,417 | 121 | 121 | distribution | 506 - 1712 | `ROI_mass_e0j0j1j2_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 120 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 2τ | 2,411 | 119 | 119 | distribution | 229 - 1418 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_0gx_2tx_0bx_width_10.0` |
| 121 | e0 + γ0 + γ1 | 1e, 1μ, 4jet, 2γ | 2,402 | 92 | 92 | distribution | 1 - 918 | `ROI_mass_e0g0g1_cat_1ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 122 | e0 + jet0 + jet1 | 1e, 1μ, 2jet | 2,389 | 85 | 85 | distribution | 318 - 1166 | `ROI_mass_e0j0j1_cat_1ex_1mx_2jx_0gx_0tx_0bx_width_10.0` |
| 123 | e0 + μ0 | 1e, 1μ, 4jet, 2γ | 2,384 | 55 | 55 | distribution | -1 - 546 | `ROI_mass_e0m0_cat_1ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 124 | e0 + γ0 + γ1 + γ2 | 1e, 4jet, 3γ | 2,337 | 76 | 76 | distribution | 294 - 1051 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_4jx_3gx_0tx_0bx_width_10.0` |
| 125 | e0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet | 2,281 | 128 | 127 | distribution | 433 - 1711 | `ROI_mass_e0j0j1j2_cat_1ex_1mx_3jx_0gx_0tx_0bx_width_10.0` |
| 126 | e0 + μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 1τ | 2,170 | 83 | 83 | distribution | 231 - 1059 | `ROI_mass_e0m0j0j1_cat_1ex_1mx_2jx_0gx_1tx_0bx_width_10.0` |
| 127 | jet0 + jet1 + jet2 + γ0 | 2e, 3jet, 1γ, 2τ | 2,164 | 99 | 99 | distribution | 212 - 1200 | `ROI_mass_j0j1j2g0_cat_2ex_0mx_3jx_1gx_2tx_0bx_width_10.0` |
| 128 | e0 + μ0 + jet0 + jet1 | 1e, 1μ, 2jet | 2,138 | 82 | 82 | distribution | 420 - 1238 | `ROI_mass_e0m0j0j1_cat_1ex_1mx_2jx_0gx_0tx_0bx_width_10.0` |
| 129 | e0 + γ0 + γ1 + γ2 | 1e, 2jet, 3γ | 2,133 | 78 | 78 | distribution | 276 - 1053 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_2jx_3gx_0tx_0bx_width_10.0` |
| 130 | e0 + jet0 + jet1 | 1e, 1μ, 2jet, 1τ | 2,118 | 70 | 70 | distribution | 167 - 865 | `ROI_mass_e0j0j1_cat_1ex_1mx_2jx_0gx_1tx_0bx_width_10.0` |
| 131 | μ0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 2γ | 2,116 | 127 | 126 | distribution | 559 - 1826 | `ROI_mass_m0j0j1j2_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 132 | e0 + μ0 | 1e, 1μ, 3jet, 1τ | 2,061 | 57 | 57 | distribution | -0 - 564 | `ROI_mass_e0m0_cat_1ex_1mx_3jx_0gx_1tx_0bx_width_10.0` |
| 133 | μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 1τ | 2,049 | 80 | 80 | distribution | 212 - 1004 | `ROI_mass_m0j0j1_cat_1ex_1mx_2jx_0gx_1tx_0bx_width_10.0` |
| 134 | μ0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet | 2,029 | 109 | 107 | distribution | 491 - 1574 | `ROI_mass_m0j0j1j2_cat_1ex_1mx_3jx_0gx_0tx_0bx_width_10.0` |
| 135 | e0 + μ0 | 1e, 1μ, 2jet, 1τ | 1,985 | 46 | 46 | distribution | 79 - 537 | `ROI_mass_e0m0_cat_1ex_1mx_2jx_0gx_1tx_0bx_width_10.0` |
| 136 | e0 + μ0 + γ0 + γ1 | 1e, 1μ, 2jet, 2γ | 1,917 | 76 | 76 | distribution | 192 - 945 | `ROI_mass_e0m0g0g1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 137 | e0 + μ0 + γ0 + γ1 | 1e, 1μ, 4jet, 2γ | 1,904 | 64 | 64 | distribution | 163 - 803 | `ROI_mass_e0m0g0g1_cat_1ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 138 | μ0 + γ0 + γ1 | 1e, 1μ, 4jet, 2γ | 1,881 | 61 | 61 | distribution | 142 - 746 | `ROI_mass_m0g0g1_cat_1ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 139 | μ0 + γ0 + γ1 | 1e, 1μ, 3jet, 2γ | 1,875 | 67 | 67 | distribution | 211 - 880 | `ROI_mass_m0g0g1_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 140 | μ0 + γ0 + γ1 | 1e, 1μ, 2jet, 2γ | 1,851 | 72 | 71 | distribution | 161 - 874 | `ROI_mass_m0g0g1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 141 | e0 + e1 + γ0 | 2e, 4jet, 1γ, 1τ | 1,822 | 70 | 70 | distribution | 125 - 822 | `ROI_mass_e0e1g0_cat_2ex_0mx_4jx_1gx_1tx_0bx_width_10.0` |
| 142 | jet0 + jet1 + γ0 + γ1 | 1e, 1μ, 2jet, 2γ | 1,817 | 94 | 94 | distribution | 417 - 1356 | `ROI_mass_j0j1g0g1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 143 | e0 + γ0 + γ1 + γ2 | 1e, 3jet, 3γ, 1τ | 1,800 | 86 | 84 | distribution | 227 - 1080 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_3jx_3gx_1tx_0bx_width_10.0` |
| 144 | e0 + γ0 + γ1 + γ2 | 1e, 4jet, 3γ, 1τ | 1,769 | 90 | 89 | distribution | 196 - 1089 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_4jx_3gx_1tx_0bx_width_10.0` |
| 145 | e0 + μ0 | 1e, 1μ, 4jet | 1,720 | 49 | 48 | distribution | 0 - 482 | `ROI_mass_e0m0_cat_1ex_1mx_4jx_0gx_0tx_0bx_width_10.0` |
| 146 | e0 + μ0 + γ0 + γ1 | 1e, 1μ, 3jet, 2γ | 1,698 | 73 | 73 | distribution | 292 - 1021 | `ROI_mass_e0m0g0g1_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 147 | e0 + jet0 + jet1 | 1e, 1μ, 2jet, 2γ | 1,696 | 61 | 61 | distribution | 359 - 967 | `ROI_mass_e0j0j1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 148 | e0 + jet0 + jet1 | 1e, 2jet, 3γ | 1,648 | 84 | 84 | distribution | 493 - 1331 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_3gx_0tx_0bx_width_10.0` |
| 149 | e0 + e1 + γ0 + γ1 | 2e, 4jet, 2γ, 3τ | 1,611 | 40 | 40 | peaky | 175 - 573 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_4jx_2gx_3tx_0bx_width_10.0` |
| 150 | e0 + μ0 + μ1 | 1e, 2μ, 3jet, 1γ | 1,599 | 80 | 80 | distribution | 135 - 933 | `ROI_mass_e0m0m1_cat_1ex_2mx_3jx_1gx_0tx_0bx_width_10.0` |
| 151 | μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 2γ | 1,593 | 79 | 79 | distribution | 397 - 1179 | `ROI_mass_m0j0j1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 152 | μ0 + μ1 + jet0 + jet1 | 1e, 2μ, 2jet, 1γ | 1,581 | 98 | 98 | distribution | 441 - 1418 | `ROI_mass_m0m1j0j1_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 153 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 3γ, 1τ | 1,553 | 107 | 107 | distribution | 473 - 1542 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_3gx_1tx_0bx_width_10.0` |
| 154 | e0 + μ0 + μ1 | 1e, 2μ, 2jet, 1γ | 1,533 | 63 | 63 | distribution | 135 - 764 | `ROI_mass_e0m0m1_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 155 | jet0 + jet1 + jet2 + γ0 | 1e, 2μ, 3jet, 1γ | 1,409 | 97 | 97 | distribution | 601 - 1565 | `ROI_mass_j0j1j2g0_cat_1ex_2mx_3jx_1gx_0tx_0bx_width_10.0` |
| 156 | e0 + jet0 + jet1 + γ0 | 1e, 2μ, 2jet, 1γ | 1,348 | 101 | 101 | distribution | 517 - 1524 | `ROI_mass_e0j0j1g0_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 157 | jet0 + jet1 + γ0 | 1e, 2μ, 2jet, 1γ | 1,336 | 105 | 105 | distribution | 479 - 1520 | `ROI_mass_j0j1g0_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 158 | e0 + jet0 + jet1 | 1e, 2μ, 2jet, 1γ | 1,333 | 83 | 83 | distribution | 449 - 1275 | `ROI_mass_e0j0j1_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 159 | μ0 + μ1 + γ0 | 1e, 2μ, 3jet, 1γ | 1,325 | 61 | 61 | distribution | 186 - 795 | `ROI_mass_m0m1g0_cat_1ex_2mx_3jx_1gx_0tx_0bx_width_10.0` |
| 160 | e0 + μ0 + μ1 + γ0 | 1e, 2μ, 3jet, 1γ | 1,294 | 77 | 77 | distribution | 255 - 1024 | `ROI_mass_e0m0m1g0_cat_1ex_2mx_3jx_1gx_0tx_0bx_width_10.0` |
| 161 | e0 + μ0 + μ1 + γ0 | 1e, 2μ, 2jet, 1γ | 1,283 | 67 | 67 | distribution | 258 - 927 | `ROI_mass_e0m0m1g0_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 162 | e0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 1τ | 1,183 | 74 | 74 | distribution | 394 - 1130 | `ROI_mass_e0j0j1j2_cat_1ex_1mx_3jx_0gx_1tx_0bx_width_10.0` |
| 163 | e0 + μ0 | 1e, 1μ, 4jet, 1τ | 1,165 | 33 | 33 | distribution | -0 - 326 | `ROI_mass_e0m0_cat_1ex_1mx_4jx_0gx_1tx_0bx_width_10.0` |
| 164 | μ0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 1τ | 1,144 | 65 | 65 | distribution | 421 - 1068 | `ROI_mass_m0j0j1j2_cat_1ex_1mx_3jx_0gx_1tx_0bx_width_10.0` |
| 165 | μ0 + μ1 + γ0 | 1e, 2μ, 2jet, 1γ | 1,057 | 62 | 61 | distribution | 236 - 851 | `ROI_mass_m0m1g0_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 166 | e0 + jet0 + jet1 + jet2 | 1e, 2μ, 3jet, 1γ | 1,055 | 122 | 122 | distribution | 762 - 1980 | `ROI_mass_e0j0j1j2_cat_1ex_2mx_3jx_1gx_0tx_0bx_width_10.0` |
| 167 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 3γ | 1,051 | 82 | 82 | distribution | 525 - 1341 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_3gx_0tx_0bx_width_10.0` |
| 168 | e0 + μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 2γ | 1,039 | 83 | 83 | distribution | 597 - 1424 | `ROI_mass_e0m0j0j1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 169 | e0 + μ0 | 1e, 1μ, 1jet, 1τ | 939 | 47 | 47 | distribution | -0 - 467 | `ROI_mass_e0m0_cat_1ex_1mx_1jx_0gx_1tx_0bx_width_10.0` |
| 170 | μ0 + jet0 | 1e, 1μ, 1jet, 1τ | 931 | 54 | 54 | distribution | -0 - 532 | `ROI_mass_m0j0_cat_1ex_1mx_1jx_0gx_1tx_0bx_width_10.0` |
| 171 | e0 + jet0 + jet1 | 1e, 2jet, 3γ, 1τ | 894 | 56 | 56 | distribution | 254 - 810 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_3gx_1tx_0bx_width_10.0` |
| 172 | μ0 + μ1 + γ0 | 1e, 2μ, 4jet, 1γ | 886 | 49 | 49 | distribution | 145 - 634 | `ROI_mass_m0m1g0_cat_1ex_2mx_4jx_1gx_0tx_0bx_width_10.0` |
| 173 | e0 + μ0 + jet0 | 1e, 1μ, 1jet, 1τ | 867 | 49 | 49 | distribution | -0 - 487 | `ROI_mass_e0m0j0_cat_1ex_1mx_1jx_0gx_1tx_0bx_width_10.0` |
| 174 | e0 + μ0 + μ1 | 1e, 2μ, 4jet, 1γ | 853 | 47 | 47 | distribution | 145 - 609 | `ROI_mass_e0m0m1_cat_1ex_2mx_4jx_1gx_0tx_0bx_width_10.0` |
| 175 | e0 + γ0 + γ1 + γ2 | 1e, 2jet, 3γ, 1τ | 802 | 57 | 56 | distribution | 246 - 806 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_2jx_3gx_1tx_0bx_width_10.0` |
| 176 | e0 + μ0 + μ1 + γ0 | 1e, 2μ, 4jet, 1γ | 782 | 63 | 63 | distribution | 236 - 864 | `ROI_mass_e0m0m1g0_cat_1ex_2mx_4jx_1gx_0tx_0bx_width_10.0` |
| 177 | e0 + e1 + γ0 | 2e, 4jet, 1γ, 2τ | 657 | 38 | 38 | distribution | 125 - 501 | `ROI_mass_e0e1g0_cat_2ex_0mx_4jx_1gx_2tx_0bx_width_10.0` |
| 178 | e0 + jet0 + jet1 | 1e, 1μ, 2jet, 2τ | 543 | 40 | 40 | distribution | 125 - 521 | `ROI_mass_e0j0j1_cat_1ex_1mx_2jx_0gx_2tx_0bx_width_10.0` |
| 179 | μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 2τ | 539 | 34 | 34 | distribution | 125 - 463 | `ROI_mass_m0j0j1_cat_1ex_1mx_2jx_0gx_2tx_0bx_width_10.0` |
| 180 | e0 + e1 + μ0 | 2e, 1μ, 3jet, 2γ | 531 | 46 | 45 | distribution | 185 - 639 | `ROI_mass_e0e1m0_cat_2ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 181 | e0 + e1 + μ0 | 2e, 1μ, 4jet, 2γ | 507 | 56 | 56 | distribution | 136 - 696 | `ROI_mass_e0e1m0_cat_2ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 182 | e0 + e1 + μ0 | 2e, 1μ, 2jet, 2γ | 494 | 52 | 52 | distribution | 116 - 635 | `ROI_mass_e0e1m0_cat_2ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 183 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 2γ, 3τ | 473 | 43 | 43 | distribution | 239 - 667 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_2gx_3tx_0bx_width_10.0` |
| 184 | μ0 + γ0 | 2e, 1μ, 3jet, 1γ | 457 | 47 | 47 | distribution | 0 - 467 | `ROI_mass_m0g0_cat_2ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 185 | e0 + γ0 + γ1 | 1e, 2μ, 3jet, 2γ | 449 | 56 | 55 | distribution | 2 - 557 | `ROI_mass_e0g0g1_cat_1ex_2mx_3jx_2gx_0tx_0bx_width_10.0` |
| 186 | μ0 + γ0 + γ1 | 2e, 1μ, 4jet, 2γ | 448 | 42 | 42 | distribution | 153 - 571 | `ROI_mass_m0g0g1_cat_2ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 187 | μ0 + jet0 + jet1 + jet2 | 2e, 1μ, 3jet, 2γ | 446 | 78 | 78 | distribution | 651 - 1427 | `ROI_mass_m0j0j1j2_cat_2ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 188 | e0 + γ0 + γ1 | 1e, 4jet, 2γ, 3τ | 445 | 32 | 32 | distribution | 113 - 428 | `ROI_mass_e0g0g1_cat_1ex_0mx_4jx_2gx_3tx_0bx_width_10.0` |
| 189 | e0 + e1 + γ0 + γ1 | 2e, 1μ, 3jet, 2γ | 433 | 56 | 54 | distribution | 287 - 841 | `ROI_mass_e0e1g0g1_cat_2ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 190 | e0 + γ0 + γ1 | 1e, 3jet, 2γ, 3τ | 425 | 38 | 37 | distribution | 124 - 500 | `ROI_mass_e0g0g1_cat_1ex_0mx_3jx_2gx_3tx_0bx_width_10.0` |
| 191 | e0 + γ0 + γ1 + γ2 | 1e, 4jet, 3γ, 2τ | 425 | 51 | 51 | distribution | 151 - 660 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_4jx_3gx_2tx_0bx_width_10.0` |
| 192 | e0 + jet0 + jet1 | 1e, 2μ, 2jet | 418 | 56 | 56 | distribution | 353 - 908 | `ROI_mass_e0j0j1_cat_1ex_2mx_2jx_0gx_0tx_0bx_width_10.0` |
| 193 | e0 + μ0 | 1e, 1μ, 3jet, 3γ | 405 | 38 | 38 | distribution | 0 - 377 | `ROI_mass_e0m0_cat_1ex_1mx_3jx_3gx_0tx_0bx_width_10.0` |
| 194 | e0 + γ0 + γ1 + γ2 | 1e, 3jet, 3γ, 2τ | 388 | 50 | 49 | distribution | 169 - 666 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_3jx_3gx_2tx_0bx_width_10.0` |
| 195 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 3γ, 2τ | 383 | 50 | 49 | distribution | 244 - 740 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_3gx_2tx_0bx_width_10.0` |
| 196 | e0 + γ0 + γ1 | 1e, 2μ, 4jet, 2γ | 359 | 46 | 46 | distribution | 2 - 461 | `ROI_mass_e0g0g1_cat_1ex_2mx_4jx_2gx_0tx_0bx_width_10.0` |
| 197 | e0 + e1 + γ0 + γ1 | 2e, 1μ, 2jet, 2γ | 350 | 58 | 58 | distribution | 216 - 790 | `ROI_mass_e0e1g0g1_cat_2ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 198 | e0 + μ0 + μ1 | 1e, 2μ, 3jet | 341 | 31 | 31 | distribution | 115 - 422 | `ROI_mass_e0m0m1_cat_1ex_2mx_3jx_0gx_0tx_0bx_width_10.0` |
| 199 | μ0 + μ1 + γ0 + γ1 | 1e, 2μ, 3jet, 2γ | 329 | 40 | 40 | distribution | 209 - 604 | `ROI_mass_m0m1g0g1_cat_1ex_2mx_3jx_2gx_0tx_0bx_width_10.0` |
| 200 | e0 + μ0 | 1e, 1μ, 1jet | 321 | 47 | 46 | distribution | 0 - 461 | `ROI_mass_e0m0_cat_1ex_1mx_1jx_0gx_0tx_0bx_width_10.0` |
| 201 | jet0 + jet1 + jet2 + γ0 | 2e, 1μ, 3jet, 1γ | 318 | 70 | 69 | distribution | 497 - 1194 | `ROI_mass_j0j1j2g0_cat_2ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 202 | μ0 + γ0 | 2e, 1μ, 4jet, 1γ | 315 | 34 | 34 | distribution | 0 - 340 | `ROI_mass_m0g0_cat_2ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 203 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 3γ, 1τ | 310 | 52 | 51 | distribution | 455 - 973 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_3gx_1tx_0bx_width_10.0` |
| 204 | μ0 + jet0 | 1e, 1μ, 1jet | 295 | 40 | 40 | distribution | 0 - 396 | `ROI_mass_m0j0_cat_1ex_1mx_1jx_0gx_0tx_0bx_width_10.0` |
| 205 | e0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 2τ | 285 | 33 | 33 | distribution | 276 - 605 | `ROI_mass_e0j0j1j2_cat_1ex_1mx_3jx_0gx_2tx_0bx_width_10.0` |
| 206 | jet0 + jet1 + γ0 + γ1 | 1e, 2μ, 2jet, 2γ | 276 | 61 | 60 | distribution | 336 - 942 | `ROI_mass_j0j1g0g1_cat_1ex_2mx_2jx_2gx_0tx_0bx_width_10.0` |
| 207 | jet0 + jet1 + γ0 + γ1 | 2e, 1μ, 2jet, 2γ | 276 | 64 | 63 | distribution | 610 - 1248 | `ROI_mass_j0j1g0g1_cat_2ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 208 | e0 + μ0 + jet0 | 1e, 1μ, 1jet | 275 | 43 | 43 | distribution | 0 - 429 | `ROI_mass_e0m0j0_cat_1ex_1mx_1jx_0gx_0tx_0bx_width_10.0` |
| 209 | e0 + μ0 + μ1 | 1e, 2μ, 3jet, 2γ | 262 | 37 | 36 | distribution | 165 - 529 | `ROI_mass_e0m0m1_cat_1ex_2mx_3jx_2gx_0tx_0bx_width_10.0` |
| 210 | e0 + e1 + μ0 + γ0 | 2e, 1μ, 3jet, 1γ | 261 | 51 | 51 | distribution | 277 - 784 | `ROI_mass_e0e1m0g0_cat_2ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 211 | μ0 + γ0 + γ1 + γ2 | 1e, 1μ, 3jet, 3γ | 259 | 40 | 39 | distribution | 245 - 639 | `ROI_mass_m0g0g1g2_cat_1ex_1mx_3jx_3gx_0tx_0bx_width_10.0` |
| 212 | e0 + jet0 + jet1 | 1e, 2μ, 2jet, 2γ | 259 | 52 | 52 | distribution | 330 - 847 | `ROI_mass_e0j0j1_cat_1ex_2mx_2jx_2gx_0tx_0bx_width_10.0` |
| 213 | e0 + e1 + μ0 | 2e, 1μ, 3jet, 1γ | 259 | 39 | 39 | distribution | 206 - 595 | `ROI_mass_e0e1m0_cat_2ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 214 | μ0 + μ1 + jet0 + jet1 | 1e, 2μ, 2jet | 257 | 46 | 44 | distribution | 531 - 985 | `ROI_mass_m0m1j0j1_cat_1ex_2mx_2jx_0gx_0tx_0bx_width_10.0` |
| 215 | μ0 + γ0 + γ1 + γ2 | 1e, 1μ, 4jet, 3γ | 255 | 45 | 45 | distribution | 217 - 663 | `ROI_mass_m0g0g1g2_cat_1ex_1mx_4jx_3gx_0tx_0bx_width_10.0` |
| 216 | e0 + γ0 + γ1 + γ2 | 1e, 1μ, 4jet, 3γ | 247 | 58 | 56 | distribution | 195 - 768 | `ROI_mass_e0g0g1g2_cat_1ex_1mx_4jx_3gx_0tx_0bx_width_10.0` |
| 217 | e0 + e1 + μ0 | 2e, 1μ, 4jet, 1γ | 245 | 42 | 40 | distribution | 145 - 560 | `ROI_mass_e0e1m0_cat_2ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 218 | e0 + e1 + jet0 + jet1 | 2e, 1μ, 2jet, 2γ | 242 | 51 | 50 | distribution | 612 - 1119 | `ROI_mass_e0e1j0j1_cat_2ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 219 | e0 + e1 + γ0 + γ1 | 2e, 1μ, 4jet, 2γ | 241 | 38 | 38 | distribution | 276 - 654 | `ROI_mass_e0e1g0g1_cat_2ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 220 | μ0 + μ1 + γ0 + γ1 | 1e, 2μ, 4jet, 2γ | 230 | 40 | 39 | distribution | 257 - 650 | `ROI_mass_m0m1g0g1_cat_1ex_2mx_4jx_2gx_0tx_0bx_width_10.0` |
| 221 | μ0 + jet0 + jet1 | 2e, 1μ, 2jet, 2γ | 227 | 32 | 32 | distribution | 486 - 803 | `ROI_mass_m0j0j1_cat_2ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 222 | e0 + μ0 + μ1 | 1e, 2μ, 4jet, 2γ | 222 | 36 | 36 | distribution | 146 - 503 | `ROI_mass_e0m0m1_cat_1ex_2mx_4jx_2gx_0tx_0bx_width_10.0` |
| 223 | μ0 + μ1 + γ0 + γ1 | 1e, 2μ, 2jet, 2γ | 221 | 36 | 35 | distribution | 218 - 576 | `ROI_mass_m0m1g0g1_cat_1ex_2mx_2jx_2gx_0tx_0bx_width_10.0` |
| 224 | μ0 + jet0 + jet1 + jet2 | 2e, 1μ, 3jet, 1γ | 217 | 38 | 38 | distribution | 535 - 913 | `ROI_mass_m0j0j1j2_cat_2ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 225 | e0 + μ0 + μ1 + μ2 | 1e, 3μ, 3jet, 1γ | 213 | 49 | 48 | distribution | 241 - 724 | `ROI_mass_e0m0m1m2_cat_1ex_3mx_3jx_1gx_0tx_0bx_width_10.0` |
| 226 | e0 + μ0 + μ1 | 1e, 2μ, 2jet, 2γ | 212 | 36 | 35 | distribution | 148 - 503 | `ROI_mass_e0m0m1_cat_1ex_2mx_2jx_2gx_0tx_0bx_width_10.0` |
| 227 | e0 + e1 + μ0 + γ0 | 2e, 1μ, 4jet, 1γ | 203 | 32 | 32 | distribution | 195 - 512 | `ROI_mass_e0e1m0g0_cat_2ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 228 | μ0 + μ1 + μ2 + γ0 | 1e, 3μ, 3jet, 1γ | 199 | 41 | 40 | distribution | 262 - 666 | `ROI_mass_m0m1m2g0_cat_1ex_3mx_3jx_1gx_0tx_0bx_width_10.0` |
| 229 | e0 + e1 + γ0 | 2e, 1μ, 2jet, 1γ | 199 | 35 | 33 | distribution | 205 - 551 | `ROI_mass_e0e1g0_cat_2ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 230 | μ0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 3γ | 185 | 31 | 31 | distribution | 558 - 862 | `ROI_mass_m0j0j1j2_cat_1ex_1mx_3jx_3gx_0tx_0bx_width_10.0` |
| 231 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 4γ | 174 | 33 | 33 | distribution | 601 - 929 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_4gx_0tx_0bx_width_10.0` |
| 232 | μ0 + jet0 + jet1 | 2e, 1μ, 2jet, 1γ | 169 | 36 | 35 | distribution | 452 - 808 | `ROI_mass_m0j0j1_cat_2ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 233 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 3τ | 158 | 40 | 39 | distribution | 197 - 593 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_0gx_3tx_0bx_width_10.0` |
| 234 | μ0 + jet0 + jet1 + γ0 | 2e, 1μ, 2jet, 1γ | 154 | 42 | 42 | distribution | 595 - 1005 | `ROI_mass_m0j0j1g0_cat_2ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 235 | e0 + jet0 + jet1 + γ0 | 1e, 3μ, 2jet, 1γ | 153 | 361 | 82 | distribution | 881 - 4486 | `ROI_mass_e0j0j1g0_cat_1ex_3mx_2jx_1gx_0tx_0bx_width_10.0` |
| 236 | e0 + μ0 + μ1 + μ2 | 1e, 3μ, 4jet, 1γ | 149 | 32 | 31 | distribution | 174 - 484 | `ROI_mass_e0m0m1m2_cat_1ex_3mx_4jx_1gx_0tx_0bx_width_10.0` |
| 237 | e0 + jet0 + jet1 | 1e, 3μ, 2jet, 1γ | 142 | 36 | 36 | distribution | 483 - 836 | `ROI_mass_e0j0j1_cat_1ex_3mx_2jx_1gx_0tx_0bx_width_10.0` |
| 238 | e0 + e1 + jet0 + jet1 | 2e, 1μ, 2jet, 1γ | 136 | 40 | 39 | distribution | 595 - 992 | `ROI_mass_e0e1j0j1_cat_2ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 239 | jet0 + jet1 + γ0 | 1e, 3μ, 2jet, 1γ | 133 | 38 | 37 | distribution | 603 - 980 | `ROI_mass_j0j1g0_cat_1ex_3mx_2jx_1gx_0tx_0bx_width_10.0` |
| 240 | e0 + jet0 + jet1 + jet2 | 1e, 3μ, 3jet, 1γ | 129 | 33 | 32 | distribution | 653 - 979 | `ROI_mass_e0j0j1j2_cat_1ex_3mx_3jx_1gx_0tx_0bx_width_10.0` |

## Plots

A representative sample is plotted under `plots/` - the highest-statistics channels plus a few smaller ones that still clear the bar.
