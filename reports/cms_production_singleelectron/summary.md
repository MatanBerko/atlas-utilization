# CMS SingleElectron production run - histogram results

- Source run: `output/cms_production_singleelectron_20260903_084242`
- Histogram file: `histograms/atlas_opendata_full_bumpnet.root` (one ROOT file, one TH1F per channel)
- BumpNet usability bar (arXiv:2501.05603): **at least 100 entries AND more than 30 bins**

## Run parameters

- **Data**: SingleElectron records 30529 (Run2016G) + 30562 (Run2016H)
- **Files processed**: 8 NANOAOD files (`max_files_to_process: 4` per record; 71 + 80 available)
- **Events**: 15,109,941 read → 13,028,843 kept after the electron selection (~86%)
- **Runtime (single 7 GB Docker container)**: ~43 min total — fetch 18 s, parse 5.6 min, mass-calc 30.3 min (1204 raw signatures), post-processing 5.3 min, histogram creation 1.5 min
- Histogram creation ran as a normal single invocation (no manual `--scan-only`): the ranges file was auto-computed in-process (the Part B fix).

## Totals

| | count |
|---|---:|
| Histograms produced | 327 |
| **Meet BumpNet bar** (>= 100 entries & > 30 bins) | **236** |
| Fall short | 91 |
| &nbsp;&nbsp;- short on bin count (<= 30 bins) | 91 |
| &nbsp;&nbsp;- short on entries (< 100) | 22 |

_(A histogram can be short on both; the two sub-rows overlap.)_

### Shape of the passing histograms

| | count |
|---|---:|
| real distribution (tallest bin < 50% of entries) | 209 |
| peaky (tallest bin 50-90%) | 8 |
| **single-bin spike** (tallest bin >= 90%, ~0 GeV) | **19** |

> The 19 spike histograms are **still present** in this run. Cause (now understood): in CMS NanoAOD an electron is normally also reconstructed as a photon and often as a jet (same calorimeter cluster), so 2-body combinations like electron+photon or electron+jet are dominated by ~0 GeV "self-pairs". This is an **upstream reconstruction/object-overlap issue, not a post-processing bug** - post-processing keeps essentially all the real (>15 GeV) signal in the histogrammed "main" array; it is just swamped by the self-pair spike. Fixing it needs overlap removal (delta-R cleaning between the electron/photon/jet collections), which is a physics-analysis design decision - see docs/CMS_KNOWN_LIMITATIONS.md.

## Passing histograms (usable as BumpNet input)

Sorted by entry count, highest first. "Mass of" is which object four-vectors were added together to form the invariant mass; "Event category" is the object multiplicity of the events that fed it.

| # | Mass of | Event category | Entries | Bins | Filled bins | Shape | Mass range (GeV) | Histogram name |
|---:|---|---|---:|---:|---:|---|---|---|
| 1 | jet0 + γ0 | 1e, 1jet, 1γ, 1τ | 4,202,868 | 52 | 52 | spike | -1 - 516 | `ROI_mass_j0g0_cat_1ex_0mx_1jx_1gx_1tx_0bx_width_10.0` |
| 2 | e0 + jet0 | 1e, 1jet, 1γ, 1τ | 4,202,863 | 49 | 49 | spike | -1 - 486 | `ROI_mass_e0j0_cat_1ex_0mx_1jx_1gx_1tx_0bx_width_10.0` |
| 3 | e0 + jet0 + γ0 | 1e, 1jet, 1γ, 1τ | 4,202,862 | 70 | 70 | spike | -1 - 695 | `ROI_mass_e0j0g0_cat_1ex_0mx_1jx_1gx_1tx_0bx_width_10.0` |
| 4 | e0 + γ0 | 1e, 2jet, 1γ, 1τ | 2,316,225 | 82 | 82 | spike | -1 - 814 | `ROI_mass_e0g0_cat_1ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 5 | e0 + jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 1τ | 1,828,920 | 325 | 325 | distribution | 151 - 3397 | `ROI_mass_e0j0j1g0_cat_1ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 6 | e0 + jet0 + jet1 | 1e, 2jet, 1γ, 1τ | 1,814,273 | 269 | 269 | distribution | 127 - 2811 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 7 | jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 1τ | 1,804,461 | 290 | 290 | distribution | 127 - 3020 | `ROI_mass_j0j1g0_cat_1ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 8 | e0 + γ0 | 1e, 2jet, 1γ | 968,272 | 97 | 97 | spike | -2 - 961 | `ROI_mass_e0g0_cat_1ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 9 | e0 + jet0 + jet1 | 1e, 2jet, 1γ | 851,484 | 378 | 378 | distribution | 128 - 3901 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 10 | e0 + jet0 + jet1 + γ0 | 1e, 2jet, 1γ | 851,262 | 406 | 406 | distribution | 152 - 4204 | `ROI_mass_e0j0j1g0_cat_1ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 11 | jet0 + jet1 + γ0 | 1e, 2jet, 1γ | 848,877 | 376 | 376 | distribution | 128 - 3884 | `ROI_mass_j0j1g0_cat_1ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 12 | e0 + γ0 | 1e, 3jet, 1γ, 1τ | 674,754 | 84 | 83 | spike | -2 - 834 | `ROI_mass_e0g0_cat_1ex_0mx_3jx_1gx_1tx_0bx_width_10.0` |
| 13 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 1γ, 1τ | 552,485 | 366 | 366 | distribution | 233 - 3888 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_1gx_1tx_0bx_width_10.0` |
| 14 | jet0 + jet1 + jet2 + γ0 | 1e, 3jet, 1γ, 1τ | 550,980 | 382 | 381 | distribution | 234 - 4048 | `ROI_mass_j0j1j2g0_cat_1ex_0mx_3jx_1gx_1tx_0bx_width_10.0` |
| 15 | e0 + jet0 | 1e, 1jet, 1γ | 495,648 | 40 | 39 | spike | -0 - 396 | `ROI_mass_e0j0_cat_1ex_0mx_1jx_1gx_0tx_0bx_width_10.0` |
| 16 | jet0 + γ0 | 1e, 1jet, 1γ | 495,636 | 33 | 33 | spike | -1 - 323 | `ROI_mass_j0g0_cat_1ex_0mx_1jx_1gx_0tx_0bx_width_10.0` |
| 17 | e0 + jet0 + γ0 | 1e, 1jet, 1γ | 495,606 | 33 | 33 | spike | -1 - 328 | `ROI_mass_e0j0g0_cat_1ex_0mx_1jx_1gx_0tx_0bx_width_10.0` |
| 18 | e0 + γ0 | 1e, 3jet, 1γ | 468,759 | 86 | 86 | spike | -2 - 855 | `ROI_mass_e0g0_cat_1ex_0mx_3jx_1gx_0tx_0bx_width_10.0` |
| 19 | e0 + γ0 | 1e, 2jet, 1γ, 2τ | 364,027 | 36 | 36 | spike | -1 - 354 | `ROI_mass_e0g0_cat_1ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 20 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 1γ | 283,367 | 377 | 377 | distribution | 524 - 4290 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_1gx_0tx_0bx_width_10.0` |
| 21 | jet0 + jet1 + jet2 + γ0 | 1e, 3jet, 1γ | 281,877 | 379 | 379 | distribution | 527 - 4316 | `ROI_mass_j0j1j2g0_cat_1ex_0mx_3jx_1gx_0tx_0bx_width_10.0` |
| 22 | e0 + e1 + γ0 + γ1 | 2e, 2jet, 2γ, 2τ | 254,080 | 96 | 95 | peaky | 175 - 1128 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 23 | e0 + jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 2τ | 246,372 | 165 | 165 | distribution | 161 - 1807 | `ROI_mass_e0j0j1g0_cat_1ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 24 | e0 + jet0 + jet1 | 1e, 2jet, 1γ, 2τ | 236,303 | 172 | 172 | distribution | 138 - 1854 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 25 | jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 2τ | 236,035 | 157 | 155 | distribution | 138 - 1701 | `ROI_mass_j0j1g0_cat_1ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 26 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 2γ, 2τ | 231,718 | 102 | 102 | distribution | 195 - 1210 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 27 | jet0 + jet1 + γ0 + γ1 | 2e, 2jet, 2γ, 2τ | 228,773 | 107 | 107 | peaky | 194 - 1263 | `ROI_mass_j0j1g0g1_cat_2ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 28 | e0 + γ0 | 1e, 4jet, 1γ, 1τ | 212,890 | 80 | 80 | spike | -1 - 794 | `ROI_mass_e0g0_cat_1ex_0mx_4jx_1gx_1tx_0bx_width_10.0` |
| 29 | e0 + γ0 | 1e, 4jet, 1γ | 199,536 | 82 | 82 | spike | -2 - 811 | `ROI_mass_e0g0_cat_1ex_0mx_4jx_1gx_0tx_0bx_width_10.0` |
| 30 | e0 + γ0 | 1e, 3jet, 1γ, 2τ | 161,445 | 51 | 49 | spike | -1 - 501 | `ROI_mass_e0g0_cat_1ex_0mx_3jx_1gx_2tx_0bx_width_10.0` |
| 31 | e0 + jet0 | 1e, 1jet, 1τ | 158,487 | 34 | 34 | spike | -1 - 330 | `ROI_mass_e0j0_cat_1ex_0mx_1jx_0gx_1tx_0bx_width_10.0` |
| 32 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 1γ, 2τ | 126,147 | 219 | 219 | distribution | 228 - 2417 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_1gx_2tx_0bx_width_10.0` |
| 33 | jet0 + jet1 + jet2 + γ0 | 1e, 3jet, 1γ, 2τ | 125,975 | 237 | 237 | distribution | 228 - 2595 | `ROI_mass_j0j1j2g0_cat_1ex_0mx_3jx_1gx_2tx_0bx_width_10.0` |
| 34 | e0 + jet0 + jet1 | 1e, 2jet, 1τ | 102,373 | 243 | 242 | distribution | 118 - 2548 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_0gx_1tx_0bx_width_10.0` |
| 35 | e0 + jet0 + jet1 | 1e, 2jet, 2γ, 1τ | 99,129 | 178 | 178 | distribution | 139 - 1918 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 36 | e0 + jet0 + γ0 | 1e, 1jet, 1γ, 2τ | 97,305 | 35 | 35 | spike | -0 - 344 | `ROI_mass_e0j0g0_cat_1ex_0mx_1jx_1gx_2tx_0bx_width_10.0` |
| 37 | jet0 + jet1 + γ0 + γ1 | 1e, 2jet, 2γ, 1τ | 89,529 | 219 | 219 | distribution | 195 - 2379 | `ROI_mass_j0j1g0g1_cat_1ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 38 | e0 + γ0 + γ1 | 1e, 3jet, 2γ | 88,778 | 189 | 189 | distribution | 1 - 1889 | `ROI_mass_e0g0g1_cat_1ex_0mx_3jx_2gx_0tx_0bx_width_10.0` |
| 39 | e0 + γ0 + γ1 | 1e, 2jet, 2γ | 87,580 | 189 | 188 | distribution | 1 - 1889 | `ROI_mass_e0g0g1_cat_1ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 40 | e0 + γ0 + γ1 | 1e, 2jet, 2γ, 1τ | 83,521 | 140 | 140 | distribution | 121 - 1521 | `ROI_mass_e0g0g1_cat_1ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 41 | e0 + jet0 + jet1 | 1e, 2jet | 66,087 | 229 | 229 | distribution | 132 - 2416 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_0gx_0tx_0bx_width_10.0` |
| 42 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 2γ | 64,455 | 310 | 310 | distribution | 530 - 3628 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_2gx_0tx_0bx_width_10.0` |
| 43 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 2γ, 1τ | 63,854 | 266 | 264 | distribution | 271 - 2923 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_2gx_1tx_0bx_width_10.0` |
| 44 | e0 + γ0 | 1e, 4jet, 1γ, 2τ | 61,656 | 45 | 45 | spike | -1 - 446 | `ROI_mass_e0g0_cat_1ex_0mx_4jx_1gx_2tx_0bx_width_10.0` |
| 45 | e0 + γ0 + γ1 | 1e, 3jet, 2γ, 1τ | 55,914 | 137 | 137 | distribution | 122 - 1487 | `ROI_mass_e0g0g1_cat_1ex_0mx_3jx_2gx_1tx_0bx_width_10.0` |
| 46 | e0 + e1 + γ0 + γ1 | 2e, 3jet, 2γ, 2τ | 55,206 | 116 | 116 | peaky | 175 - 1334 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_3jx_2gx_2tx_0bx_width_10.0` |
| 47 | e0 + γ0 + γ1 | 1e, 4jet, 2γ | 53,364 | 168 | 168 | distribution | 1 - 1678 | `ROI_mass_e0g0g1_cat_1ex_0mx_4jx_2gx_0tx_0bx_width_10.0` |
| 48 | jet0 + jet1 + γ0 + γ1 | 1e, 2jet, 2γ | 52,031 | 256 | 256 | distribution | 501 - 3056 | `ROI_mass_j0j1g0g1_cat_1ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 49 | e0 + jet0 + jet1 | 1e, 2jet, 2γ | 50,603 | 221 | 221 | distribution | 424 - 2629 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 50 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 2γ, 1τ | 48,066 | 174 | 174 | distribution | 196 - 1935 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 51 | jet0 + jet1 + γ0 + γ1 | 2e, 2jet, 2γ, 1τ | 45,670 | 189 | 189 | distribution | 198 - 2087 | `ROI_mass_j0j1g0g1_cat_2ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 52 | e0 + e1 + γ0 + γ1 | 2e, 2jet, 2γ, 1τ | 44,839 | 166 | 165 | distribution | 175 - 1829 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_2jx_2gx_1tx_0bx_width_10.0` |
| 53 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 1τ | 31,307 | 259 | 259 | distribution | 218 - 2803 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_0gx_1tx_0bx_width_10.0` |
| 54 | e0 + γ0 + γ1 | 1e, 4jet, 2γ, 1τ | 30,470 | 140 | 140 | distribution | 121 - 1513 | `ROI_mass_e0g0g1_cat_1ex_0mx_4jx_2gx_1tx_0bx_width_10.0` |
| 55 | e0 + e1 + γ0 + γ1 | 2e, 2jet, 2γ | 29,977 | 221 | 219 | distribution | 175 - 2378 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 56 | e0 + jet0 + jet1 + jet2 | 1e, 3jet | 27,067 | 314 | 314 | distribution | 237 - 3374 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_0gx_0tx_0bx_width_10.0` |
| 57 | e0 + e1 + γ0 + γ1 | 2e, 3jet, 2γ, 1τ | 26,258 | 190 | 190 | distribution | 175 - 2075 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_3jx_2gx_1tx_0bx_width_10.0` |
| 58 | μ0 + γ0 | 1e, 1μ, 2jet, 1γ | 26,222 | 178 | 176 | distribution | -1 - 1776 | `ROI_mass_m0g0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 59 | e0 + μ0 | 1e, 1μ, 2jet, 1γ | 26,154 | 150 | 150 | distribution | -2 - 1493 | `ROI_mass_e0m0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 60 | e0 + μ0 + γ0 | 1e, 1μ, 2jet, 1γ | 26,140 | 205 | 203 | distribution | -1 - 2042 | `ROI_mass_e0m0g0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 61 | e0 + e1 + γ0 + γ1 | 2e, 3jet, 2γ | 23,505 | 219 | 219 | distribution | 305 - 2488 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_3jx_2gx_0tx_0bx_width_10.0` |
| 62 | e0 + jet0 + jet1 + γ0 | 1e, 1μ, 2jet, 1γ | 23,208 | 251 | 251 | distribution | 169 - 2675 | `ROI_mass_e0j0j1g0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 63 | jet0 + jet1 + γ0 | 1e, 1μ, 2jet, 1γ | 23,140 | 228 | 228 | distribution | 144 - 2418 | `ROI_mass_j0j1g0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 64 | e0 + jet0 + jet1 | 1e, 1μ, 2jet, 1γ | 23,082 | 217 | 217 | distribution | 144 - 2314 | `ROI_mass_e0j0j1_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 65 | e0 + μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 1γ | 22,624 | 272 | 272 | distribution | 261 - 2977 | `ROI_mass_e0m0j0j1_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 66 | μ0 + jet0 + jet1 + γ0 | 1e, 1μ, 2jet, 1γ | 22,482 | 234 | 234 | distribution | 260 - 2594 | `ROI_mass_m0j0j1g0_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 67 | jet0 + jet1 + γ0 + γ1 | 2e, 2jet, 2γ | 19,995 | 212 | 212 | distribution | 562 - 2680 | `ROI_mass_j0j1g0g1_cat_2ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 68 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 2γ | 19,419 | 207 | 207 | distribution | 556 - 2621 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_2gx_0tx_0bx_width_10.0` |
| 69 | e0 + γ0 | 1e, 1μ, 3jet, 1γ | 18,144 | 41 | 41 | spike | -1 - 406 | `ROI_mass_e0g0_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 70 | e0 + μ0 | 1e, 1μ, 3jet, 1γ | 17,988 | 125 | 125 | distribution | -1 - 1247 | `ROI_mass_e0m0_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 71 | e0 + μ0 + γ0 | 1e, 1μ, 3jet, 1γ | 17,969 | 169 | 169 | distribution | -1 - 1683 | `ROI_mass_e0m0g0_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 72 | μ0 + γ0 | 1e, 1μ, 3jet, 1γ | 17,965 | 118 | 118 | distribution | -0 - 1177 | `ROI_mass_m0g0_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 73 | e0 + jet0 + jet1 | 1e, 2jet, 2γ, 2τ | 17,827 | 93 | 93 | distribution | 153 - 1081 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 74 | jet0 + jet1 + γ0 + γ1 | 1e, 2jet, 2γ, 2τ | 17,332 | 112 | 112 | distribution | 200 - 1319 | `ROI_mass_j0j1g0g1_cat_1ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 75 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 2γ, 2τ | 16,258 | 169 | 168 | distribution | 230 - 1917 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_2gx_2tx_0bx_width_10.0` |
| 76 | e0 + e1 + γ0 + γ1 | 2e, 4jet, 2γ, 2τ | 16,169 | 111 | 111 | peaky | 175 - 1283 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_4jx_2gx_2tx_0bx_width_10.0` |
| 77 | e0 + γ0 + γ1 | 1e, 2jet, 2γ, 2τ | 15,583 | 78 | 78 | distribution | 122 - 893 | `ROI_mass_e0g0g1_cat_1ex_0mx_2jx_2gx_2tx_0bx_width_10.0` |
| 78 | μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 1γ | 15,037 | 218 | 217 | distribution | 403 - 2579 | `ROI_mass_m0j0j1_cat_1ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 79 | e0 + e1 + γ0 + γ1 | 2e, 4jet, 2γ, 1τ | 13,724 | 159 | 159 | distribution | 175 - 1761 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_4jx_2gx_1tx_0bx_width_10.0` |
| 80 | e0 + e1 + γ0 + γ1 | 2e, 4jet, 2γ | 13,562 | 205 | 205 | distribution | 295 - 2338 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_4jx_2gx_0tx_0bx_width_10.0` |
| 81 | μ0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 1γ | 13,446 | 255 | 255 | distribution | 509 - 3057 | `ROI_mass_m0j0j1j2_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 82 | e0 + jet0 + jet1 | 1e, 2jet, 2τ | 13,243 | 104 | 102 | distribution | 108 - 1146 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_0gx_2tx_0bx_width_10.0` |
| 83 | e0 + γ0 + γ1 | 1e, 3jet, 2γ, 2τ | 12,884 | 100 | 100 | distribution | 120 - 1120 | `ROI_mass_e0g0g1_cat_1ex_0mx_3jx_2gx_2tx_0bx_width_10.0` |
| 84 | jet0 + jet1 + γ0 | 2e, 2jet, 1γ, 2τ | 11,672 | 74 | 73 | distribution | 154 - 892 | `ROI_mass_j0j1g0_cat_2ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 85 | jet0 + jet1 + γ0 | 2e, 2jet, 1γ, 1τ | 11,568 | 139 | 139 | distribution | 150 - 1540 | `ROI_mass_j0j1g0_cat_2ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 86 | jet0 + jet1 + jet2 + γ0 | 2e, 3jet, 1γ | 11,118 | 233 | 233 | distribution | 511 - 2836 | `ROI_mass_j0j1j2g0_cat_2ex_0mx_3jx_1gx_0tx_0bx_width_10.0` |
| 87 | jet0 + jet1 + jet2 + γ0 | 1e, 1μ, 3jet, 1γ | 11,027 | 226 | 226 | distribution | 613 - 2868 | `ROI_mass_j0j1j2g0_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 88 | e0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 1γ | 10,965 | 227 | 227 | distribution | 614 - 2881 | `ROI_mass_e0j0j1j2_cat_1ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 89 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 1γ, 1τ | 10,657 | 156 | 156 | distribution | 205 - 1764 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 90 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 1γ, 2τ | 10,558 | 96 | 95 | distribution | 205 - 1163 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 91 | e0 + e1 + γ0 | 2e, 2jet, 1γ | 10,533 | 75 | 75 | distribution | 185 - 933 | `ROI_mass_e0e1g0_cat_2ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 92 | e0 + e1 + γ0 | 2e, 2jet, 1γ, 2τ | 10,250 | 58 | 58 | peaky | 125 - 702 | `ROI_mass_e0e1g0_cat_2ex_0mx_2jx_1gx_2tx_0bx_width_10.0` |
| 93 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 1γ, 3τ | 10,159 | 117 | 117 | distribution | 219 - 1382 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_1gx_3tx_0bx_width_10.0` |
| 94 | jet0 + jet1 + jet2 + γ0 | 1e, 3jet, 1γ, 3τ | 10,158 | 133 | 133 | distribution | 220 - 1544 | `ROI_mass_j0j1j2g0_cat_1ex_0mx_3jx_1gx_3tx_0bx_width_10.0` |
| 95 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 1γ | 10,037 | 171 | 171 | distribution | 498 - 2203 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 96 | jet0 + jet1 + γ0 | 2e, 2jet, 1γ | 10,021 | 153 | 152 | distribution | 439 - 1965 | `ROI_mass_j0j1g0_cat_2ex_0mx_2jx_1gx_0tx_0bx_width_10.0` |
| 97 | e0 + e1 + γ0 | 2e, 3jet, 1γ | 9,729 | 95 | 95 | distribution | 185 - 1134 | `ROI_mass_e0e1g0_cat_2ex_0mx_3jx_1gx_0tx_0bx_width_10.0` |
| 98 | e0 + e1 + γ0 | 2e, 2jet, 1γ, 1τ | 9,571 | 100 | 98 | distribution | 125 - 1125 | `ROI_mass_e0e1g0_cat_2ex_0mx_2jx_1gx_1tx_0bx_width_10.0` |
| 99 | e0 + γ0 | 1e, 1μ, 4jet, 1γ | 9,479 | 32 | 31 | spike | -1 - 316 | `ROI_mass_e0g0_cat_1ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 100 | e0 + μ0 | 1e, 1μ, 4jet, 1γ | 9,434 | 124 | 121 | distribution | -1 - 1236 | `ROI_mass_e0m0_cat_1ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 101 | μ0 + γ0 | 1e, 1μ, 4jet, 1γ | 9,410 | 114 | 114 | distribution | -0 - 1137 | `ROI_mass_m0g0_cat_1ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 102 | e0 + μ0 + γ0 | 1e, 1μ, 4jet, 1γ | 9,366 | 141 | 140 | distribution | -0 - 1402 | `ROI_mass_e0m0g0_cat_1ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 103 | jet0 + jet1 + jet2 + γ0 | 2e, 3jet, 1γ, 1τ | 8,076 | 194 | 193 | distribution | 350 - 2287 | `ROI_mass_j0j1j2g0_cat_2ex_0mx_3jx_1gx_1tx_0bx_width_10.0` |
| 104 | e0 + e1 + γ0 + γ1 | 2e, 3jet, 2γ, 3τ | 8,070 | 55 | 54 | peaky | 175 - 718 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_3jx_2gx_3tx_0bx_width_10.0` |
| 105 | e0 + μ0 | 1e, 1μ, 1jet, 1γ | 7,781 | 115 | 114 | distribution | -0 - 1146 | `ROI_mass_e0m0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 106 | e0 + γ0 + γ1 | 1e, 4jet, 2γ, 2τ | 7,768 | 90 | 90 | distribution | 121 - 1011 | `ROI_mass_e0g0g1_cat_1ex_0mx_4jx_2gx_2tx_0bx_width_10.0` |
| 107 | μ0 + jet0 | 1e, 1μ, 1jet, 1γ | 7,758 | 124 | 124 | distribution | 0 - 1239 | `ROI_mass_m0j0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 108 | μ0 + γ0 | 1e, 1μ, 1jet, 1γ | 7,754 | 100 | 99 | distribution | -0 - 994 | `ROI_mass_m0g0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 109 | e0 + μ0 + γ0 | 1e, 1μ, 1jet, 1γ | 7,744 | 137 | 135 | distribution | 0 - 1365 | `ROI_mass_e0m0g0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 110 | e0 + μ0 + jet0 + γ0 | 1e, 1μ, 1jet, 1γ | 7,709 | 160 | 156 | distribution | 0 - 1597 | `ROI_mass_e0m0j0g0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 111 | e0 + μ0 + jet0 | 1e, 1μ, 1jet, 1γ | 7,653 | 119 | 119 | distribution | 0 - 1188 | `ROI_mass_e0m0j0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 112 | e0 + e1 + γ0 | 2e, 3jet, 1γ, 1τ | 7,618 | 100 | 100 | distribution | 125 - 1122 | `ROI_mass_e0e1g0_cat_2ex_0mx_3jx_1gx_1tx_0bx_width_10.0` |
| 113 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 3γ | 7,617 | 185 | 184 | distribution | 560 - 2403 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_3gx_0tx_0bx_width_10.0` |
| 114 | μ0 + jet0 + γ0 | 1e, 1μ, 1jet, 1γ | 7,592 | 105 | 105 | distribution | 0 - 1049 | `ROI_mass_m0j0g0_cat_1ex_1mx_1jx_1gx_0tx_0bx_width_10.0` |
| 115 | e0 + γ0 + γ1 + γ2 | 1e, 3jet, 3γ | 6,973 | 116 | 115 | distribution | 295 - 1450 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_3jx_3gx_0tx_0bx_width_10.0` |
| 116 | e0 + jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 3τ | 6,462 | 86 | 86 | distribution | 156 - 1015 | `ROI_mass_e0j0j1g0_cat_1ex_0mx_2jx_1gx_3tx_0bx_width_10.0` |
| 117 | e0 + jet0 + jet1 | 1e, 2jet, 1γ, 3τ | 6,404 | 72 | 72 | distribution | 131 - 851 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_1gx_3tx_0bx_width_10.0` |
| 118 | jet0 + jet1 + γ0 | 1e, 2jet, 1γ, 3τ | 6,336 | 72 | 72 | distribution | 132 - 850 | `ROI_mass_j0j1g0_cat_1ex_0mx_2jx_1gx_3tx_0bx_width_10.0` |
| 119 | e0 + e1 + γ0 | 2e, 4jet, 1γ | 5,928 | 111 | 111 | distribution | 165 - 1267 | `ROI_mass_e0e1g0_cat_2ex_0mx_4jx_1gx_0tx_0bx_width_10.0` |
| 120 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 2τ | 5,777 | 160 | 160 | distribution | 228 - 1826 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_0gx_2tx_0bx_width_10.0` |
| 121 | e0 + γ0 + γ1 + γ2 | 1e, 4jet, 3γ | 5,412 | 112 | 112 | distribution | 293 - 1410 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_4jx_3gx_0tx_0bx_width_10.0` |
| 122 | jet0 + jet1 + jet2 + γ0 | 2e, 3jet, 1γ, 2τ | 4,925 | 106 | 106 | distribution | 218 - 1274 | `ROI_mass_j0j1j2g0_cat_2ex_0mx_3jx_1gx_2tx_0bx_width_10.0` |
| 123 | e0 + γ0 + γ1 + γ2 | 1e, 3jet, 3γ, 1τ | 4,801 | 116 | 114 | distribution | 184 - 1336 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_3jx_3gx_1tx_0bx_width_10.0` |
| 124 | jet0 + jet1 + γ0 + γ1 | 2e, 2jet, 2γ, 3τ | 4,706 | 38 | 36 | distribution | 188 - 563 | `ROI_mass_j0j1g0g1_cat_2ex_0mx_2jx_2gx_3tx_0bx_width_10.0` |
| 125 | e0 + γ0 + γ1 + γ2 | 1e, 2jet, 3γ | 4,599 | 89 | 89 | distribution | 295 - 1183 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_2jx_3gx_0tx_0bx_width_10.0` |
| 126 | e0 + jet0 + jet1 | 1e, 2jet, 3γ | 4,427 | 113 | 112 | distribution | 463 - 1589 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_3gx_0tx_0bx_width_10.0` |
| 127 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 3γ, 1τ | 4,369 | 116 | 116 | distribution | 384 - 1542 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_3gx_1tx_0bx_width_10.0` |
| 128 | e0 + e1 + γ0 | 2e, 4jet, 1γ, 1τ | 4,307 | 96 | 96 | distribution | 125 - 1083 | `ROI_mass_e0e1g0_cat_2ex_0mx_4jx_1gx_1tx_0bx_width_10.0` |
| 129 | e0 + γ0 + γ1 + γ2 | 1e, 4jet, 3γ, 1τ | 3,898 | 90 | 90 | distribution | 193 - 1089 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_4jx_3gx_1tx_0bx_width_10.0` |
| 130 | e0 + e1 + γ0 + γ1 | 2e, 2jet, 2γ, 3τ | 3,886 | 33 | 32 | peaky | 175 - 503 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_2jx_2gx_3tx_0bx_width_10.0` |
| 131 | e0 + e1 + γ0 + γ1 | 2e, 4jet, 2γ, 3τ | 3,571 | 50 | 49 | peaky | 175 - 672 | `ROI_mass_e0e1g0g1_cat_2ex_0mx_4jx_2gx_3tx_0bx_width_10.0` |
| 132 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 2γ, 3τ | 3,564 | 35 | 34 | distribution | 196 - 541 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_2gx_3tx_0bx_width_10.0` |
| 133 | e0 + e1 + γ0 | 2e, 3jet, 1γ, 2τ | 3,529 | 66 | 66 | distribution | 125 - 784 | `ROI_mass_e0e1g0_cat_2ex_0mx_3jx_1gx_2tx_0bx_width_10.0` |
| 134 | e0 + γ0 + γ1 | 1e, 1μ, 3jet, 2γ | 3,306 | 105 | 105 | distribution | 2 - 1047 | `ROI_mass_e0g0g1_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 135 | e0 + μ0 | 1e, 1μ, 3jet, 2γ | 3,294 | 80 | 80 | distribution | -1 - 790 | `ROI_mass_e0m0_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 136 | μ0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 2γ | 2,581 | 149 | 147 | distribution | 528 - 2014 | `ROI_mass_m0j0j1j2_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 137 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 3γ | 2,570 | 140 | 140 | distribution | 541 - 1939 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_3gx_0tx_0bx_width_10.0` |
| 138 | μ0 + γ0 + γ1 | 1e, 1μ, 3jet, 2γ | 2,562 | 113 | 113 | distribution | 203 - 1330 | `ROI_mass_m0g0g1_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 139 | e0 + μ0 | 1e, 1μ, 2jet, 2γ | 2,481 | 83 | 82 | distribution | -0 - 827 | `ROI_mass_e0m0_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 140 | e0 + γ0 + γ1 | 1e, 1μ, 2jet, 2γ | 2,452 | 86 | 86 | distribution | 2 - 856 | `ROI_mass_e0g0g1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 141 | e0 + μ0 | 1e, 1μ, 4jet, 2γ | 2,444 | 79 | 78 | distribution | -1 - 784 | `ROI_mass_e0m0_cat_1ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 142 | e0 + μ0 + γ0 + γ1 | 1e, 1μ, 3jet, 2γ | 2,407 | 95 | 95 | distribution | 275 - 1219 | `ROI_mass_e0m0g0g1_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 143 | e0 + μ0 | 1e, 1μ, 2jet, 1τ | 2,393 | 78 | 78 | distribution | -1 - 777 | `ROI_mass_e0m0_cat_1ex_1mx_2jx_0gx_1tx_0bx_width_10.0` |
| 144 | e0 + γ0 + γ1 | 1e, 1μ, 4jet, 2γ | 2,384 | 80 | 80 | distribution | 2 - 795 | `ROI_mass_e0g0g1_cat_1ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 145 | μ0 + jet0 | 1e, 1μ, 1jet, 1τ | 2,279 | 84 | 84 | distribution | -0 - 837 | `ROI_mass_m0j0_cat_1ex_1mx_1jx_0gx_1tx_0bx_width_10.0` |
| 146 | e0 + jet0 + jet1 | 1e, 2jet, 3γ, 1τ | 2,250 | 103 | 102 | distribution | 256 - 1281 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_3gx_1tx_0bx_width_10.0` |
| 147 | e0 + μ0 | 1e, 1μ, 1jet, 1τ | 2,243 | 57 | 57 | distribution | -0 - 567 | `ROI_mass_e0m0_cat_1ex_1mx_1jx_0gx_1tx_0bx_width_10.0` |
| 148 | e0 + μ0 + jet0 | 1e, 1μ, 1jet, 1τ | 2,239 | 87 | 87 | distribution | -0 - 869 | `ROI_mass_e0m0j0_cat_1ex_1mx_1jx_0gx_1tx_0bx_width_10.0` |
| 149 | e0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 2γ | 2,170 | 127 | 127 | distribution | 620 - 1889 | `ROI_mass_e0j0j1j2_cat_1ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 150 | μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 1τ | 1,875 | 80 | 80 | distribution | 170 - 969 | `ROI_mass_m0j0j1_cat_1ex_1mx_2jx_0gx_1tx_0bx_width_10.0` |
| 151 | e0 + μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 1τ | 1,828 | 76 | 76 | distribution | 196 - 951 | `ROI_mass_e0m0j0j1_cat_1ex_1mx_2jx_0gx_1tx_0bx_width_10.0` |
| 152 | e0 + γ0 + γ1 + γ2 | 1e, 2jet, 3γ, 1τ | 1,773 | 72 | 72 | distribution | 256 - 973 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_2jx_3gx_1tx_0bx_width_10.0` |
| 153 | μ0 + γ0 + γ1 | 1e, 1μ, 2jet, 2γ | 1,773 | 72 | 71 | distribution | 213 - 930 | `ROI_mass_m0g0g1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 154 | μ0 + γ0 + γ1 | 1e, 1μ, 4jet, 2γ | 1,718 | 88 | 88 | distribution | 223 - 1095 | `ROI_mass_m0g0g1_cat_1ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 155 | e0 + μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 2γ | 1,671 | 123 | 121 | distribution | 539 - 1763 | `ROI_mass_e0m0j0j1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 156 | e0 + μ0 | 1e, 1μ, 2jet | 1,623 | 83 | 83 | distribution | -0 - 829 | `ROI_mass_e0m0_cat_1ex_1mx_2jx_0gx_0tx_0bx_width_10.0` |
| 157 | e0 + μ0 + γ0 + γ1 | 1e, 1μ, 4jet, 2γ | 1,593 | 87 | 87 | distribution | 303 - 1171 | `ROI_mass_e0m0g0g1_cat_1ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 158 | jet0 + jet1 + γ0 + γ1 | 1e, 1μ, 2jet, 2γ | 1,546 | 112 | 110 | distribution | 547 - 1664 | `ROI_mass_j0j1g0g1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 159 | e0 + e1 + γ0 | 2e, 4jet, 1γ, 2τ | 1,539 | 56 | 56 | distribution | 125 - 677 | `ROI_mass_e0e1g0_cat_2ex_0mx_4jx_1gx_2tx_0bx_width_10.0` |
| 160 | μ0 + jet0 + jet1 | 1e, 1μ, 2jet, 2γ | 1,531 | 74 | 74 | distribution | 445 - 1183 | `ROI_mass_m0j0j1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 161 | e0 + jet0 + jet1 | 1e, 1μ, 2jet, 2γ | 1,521 | 99 | 99 | distribution | 469 - 1455 | `ROI_mass_e0j0j1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 162 | e0 + jet0 + jet1 | 1e, 1μ, 2jet, 1τ | 1,480 | 68 | 68 | distribution | 159 - 834 | `ROI_mass_e0j0j1_cat_1ex_1mx_2jx_0gx_1tx_0bx_width_10.0` |
| 163 | e0 + jet0 + jet1 + jet2 | 1e, 2μ, 3jet, 1γ | 1,397 | 137 | 136 | distribution | 627 - 1995 | `ROI_mass_e0j0j1j2_cat_1ex_2mx_3jx_1gx_0tx_0bx_width_10.0` |
| 164 | μ0 + μ1 + γ0 | 1e, 2μ, 2jet, 1γ | 1,356 | 73 | 73 | distribution | 225 - 954 | `ROI_mass_m0m1g0_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 165 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 2γ, 3τ | 1,336 | 68 | 67 | distribution | 219 - 896 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_2gx_3tx_0bx_width_10.0` |
| 166 | e0 + μ0 + μ1 | 1e, 2μ, 2jet, 1γ | 1,336 | 71 | 71 | distribution | 226 - 935 | `ROI_mass_e0m0m1_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 167 | μ0 + jet0 + jet1 | 1e, 1μ, 2jet | 1,332 | 112 | 112 | distribution | 213 - 1332 | `ROI_mass_m0j0j1_cat_1ex_1mx_2jx_0gx_0tx_0bx_width_10.0` |
| 168 | jet0 + jet1 + γ0 | 1e, 2μ, 2jet, 1γ | 1,299 | 103 | 103 | distribution | 503 - 1529 | `ROI_mass_j0j1g0_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 169 | e0 + jet0 + jet1 + γ0 | 1e, 2μ, 2jet, 1γ | 1,283 | 117 | 116 | distribution | 590 - 1750 | `ROI_mass_e0j0j1g0_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 170 | μ0 + μ1 + jet0 + jet1 | 1e, 2μ, 2jet, 1γ | 1,263 | 104 | 104 | distribution | 560 - 1593 | `ROI_mass_m0m1j0j1_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 171 | e0 + μ0 + γ0 + γ1 | 1e, 1μ, 2jet, 2γ | 1,258 | 77 | 77 | distribution | 384 - 1153 | `ROI_mass_e0m0g0g1_cat_1ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 172 | e0 + jet0 + jet1 | 1e, 1μ, 2jet | 1,249 | 104 | 102 | distribution | 158 - 1195 | `ROI_mass_e0j0j1_cat_1ex_1mx_2jx_0gx_0tx_0bx_width_10.0` |
| 173 | e0 + jet0 + jet1 | 1e, 2μ, 2jet, 1γ | 1,244 | 89 | 89 | distribution | 503 - 1390 | `ROI_mass_e0j0j1_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 174 | jet0 + jet1 + jet2 + γ0 | 1e, 2μ, 3jet, 1γ | 1,215 | 92 | 92 | distribution | 636 - 1553 | `ROI_mass_j0j1j2g0_cat_1ex_2mx_3jx_1gx_0tx_0bx_width_10.0` |
| 175 | e0 + μ0 + jet0 + jet1 | 1e, 1μ, 2jet | 1,162 | 85 | 85 | distribution | 273 - 1123 | `ROI_mass_e0m0j0j1_cat_1ex_1mx_2jx_0gx_0tx_0bx_width_10.0` |
| 176 | μ0 + μ1 + γ0 | 1e, 2μ, 3jet, 1γ | 1,126 | 69 | 69 | distribution | 256 - 944 | `ROI_mass_m0m1g0_cat_1ex_2mx_3jx_1gx_0tx_0bx_width_10.0` |
| 177 | e0 + μ0 + μ1 | 1e, 2μ, 3jet, 1γ | 1,121 | 69 | 69 | distribution | 255 - 941 | `ROI_mass_e0m0m1_cat_1ex_2mx_3jx_1gx_0tx_0bx_width_10.0` |
| 178 | e0 + μ0 + μ1 + γ0 | 1e, 2μ, 3jet, 1γ | 1,064 | 78 | 78 | distribution | 365 - 1141 | `ROI_mass_e0m0m1g0_cat_1ex_2mx_3jx_1gx_0tx_0bx_width_10.0` |
| 179 | e0 + μ0 + μ1 + γ0 | 1e, 2μ, 2jet, 1γ | 1,009 | 70 | 70 | distribution | 393 - 1091 | `ROI_mass_e0m0m1g0_cat_1ex_2mx_2jx_1gx_0tx_0bx_width_10.0` |
| 180 | e0 + μ0 | 1e, 1μ, 3jet, 1τ | 1,000 | 63 | 62 | distribution | -0 - 626 | `ROI_mass_e0m0_cat_1ex_1mx_3jx_0gx_1tx_0bx_width_10.0` |
| 181 | μ0 + γ0 + γ1 | 2e, 1μ, 3jet, 2γ | 979 | 76 | 75 | distribution | 213 - 968 | `ROI_mass_m0g0g1_cat_2ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 182 | e0 + γ0 + γ1 | 1e, 3jet, 2γ, 3τ | 966 | 38 | 38 | distribution | 124 - 500 | `ROI_mass_e0g0g1_cat_1ex_0mx_3jx_2gx_3tx_0bx_width_10.0` |
| 183 | e0 + γ0 + γ1 + γ2 | 1e, 4jet, 3γ, 2τ | 958 | 58 | 58 | distribution | 151 - 729 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_4jx_3gx_2tx_0bx_width_10.0` |
| 184 | e0 + γ0 + γ1 | 1e, 4jet, 2γ, 3τ | 927 | 42 | 42 | distribution | 123 - 537 | `ROI_mass_e0g0g1_cat_1ex_0mx_4jx_2gx_3tx_0bx_width_10.0` |
| 185 | μ0 + jet0 + jet1 + jet2 | 2e, 1μ, 3jet, 2γ | 915 | 115 | 115 | distribution | 574 - 1722 | `ROI_mass_m0j0j1j2_cat_2ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 186 | e0 + μ0 | 1e, 1μ, 3jet | 890 | 61 | 60 | distribution | -0 - 603 | `ROI_mass_e0m0_cat_1ex_1mx_3jx_0gx_0tx_0bx_width_10.0` |
| 187 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 3γ, 2τ | 873 | 59 | 59 | distribution | 255 - 842 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_3gx_2tx_0bx_width_10.0` |
| 188 | e0 + e1 + μ0 | 2e, 1μ, 3jet, 2γ | 796 | 61 | 60 | distribution | 245 - 853 | `ROI_mass_e0e1m0_cat_2ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 189 | e0 + μ0 | 1e, 1μ, 1jet | 777 | 48 | 47 | distribution | -0 - 477 | `ROI_mass_e0m0_cat_1ex_1mx_1jx_0gx_0tx_0bx_width_10.0` |
| 190 | e0 + μ0 + jet0 | 1e, 1μ, 1jet | 775 | 72 | 72 | distribution | 0 - 712 | `ROI_mass_e0m0j0_cat_1ex_1mx_1jx_0gx_0tx_0bx_width_10.0` |
| 191 | e0 + γ0 + γ1 + γ2 | 1e, 3jet, 3γ, 2τ | 774 | 54 | 53 | distribution | 189 - 725 | `ROI_mass_e0g0g1g2_cat_1ex_0mx_3jx_3gx_2tx_0bx_width_10.0` |
| 192 | μ0 + jet0 | 1e, 1μ, 1jet | 772 | 53 | 53 | distribution | 0 - 530 | `ROI_mass_m0j0_cat_1ex_1mx_1jx_0gx_0tx_0bx_width_10.0` |
| 193 | μ0 + μ1 + γ0 | 1e, 2μ, 4jet, 1γ | 734 | 55 | 55 | distribution | 195 - 741 | `ROI_mass_m0m1g0_cat_1ex_2mx_4jx_1gx_0tx_0bx_width_10.0` |
| 194 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 3γ, 1τ | 733 | 69 | 69 | distribution | 455 - 1142 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_3gx_1tx_0bx_width_10.0` |
| 195 | e0 + μ0 + μ1 + γ0 | 1e, 2μ, 4jet, 1γ | 729 | 61 | 61 | distribution | 256 - 864 | `ROI_mass_e0m0m1g0_cat_1ex_2mx_4jx_1gx_0tx_0bx_width_10.0` |
| 196 | e0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 1τ | 726 | 88 | 88 | distribution | 266 - 1144 | `ROI_mass_e0j0j1j2_cat_1ex_1mx_3jx_0gx_1tx_0bx_width_10.0` |
| 197 | e0 + e1 + γ0 + γ1 | 2e, 1μ, 3jet, 2γ | 700 | 90 | 88 | distribution | 356 - 1247 | `ROI_mass_e0e1g0g1_cat_2ex_1mx_3jx_2gx_0tx_0bx_width_10.0` |
| 198 | e0 + e1 + μ0 | 2e, 1μ, 2jet, 2γ | 684 | 70 | 69 | distribution | 219 - 918 | `ROI_mass_e0e1m0_cat_2ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 199 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 4γ | 657 | 76 | 76 | distribution | 544 - 1301 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_4gx_0tx_0bx_width_10.0` |
| 200 | μ0 + γ0 + γ1 | 2e, 1μ, 4jet, 2γ | 640 | 62 | 62 | distribution | 234 - 847 | `ROI_mass_m0g0g1_cat_2ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 201 | μ0 + γ0 + γ1 | 2e, 1μ, 2jet, 2γ | 627 | 58 | 58 | distribution | 244 - 821 | `ROI_mass_m0g0g1_cat_2ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 202 | e0 + μ0 + μ1 | 1e, 2μ, 4jet, 1γ | 618 | 50 | 50 | distribution | 235 - 731 | `ROI_mass_e0m0m1_cat_1ex_2mx_4jx_1gx_0tx_0bx_width_10.0` |
| 203 | e0 + e1 + γ0 + γ1 | 2e, 1μ, 4jet, 2γ | 586 | 67 | 67 | distribution | 255 - 924 | `ROI_mass_e0e1g0g1_cat_2ex_1mx_4jx_2gx_0tx_0bx_width_10.0` |
| 204 | μ0 + γ0 | 2e, 1μ, 3jet, 1γ | 566 | 47 | 47 | distribution | 0 - 467 | `ROI_mass_m0g0_cat_2ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 205 | μ0 + γ0 | 2e, 1μ, 2jet, 1γ | 542 | 47 | 47 | distribution | -0 - 467 | `ROI_mass_m0g0_cat_2ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 206 | μ0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet, 1τ | 540 | 71 | 71 | distribution | 481 - 1189 | `ROI_mass_m0j0j1j2_cat_1ex_1mx_3jx_0gx_1tx_0bx_width_10.0` |
| 207 | jet0 + jet1 + jet2 + γ0 | 2e, 3jet, 1γ, 3τ | 537 | 43 | 43 | distribution | 218 - 646 | `ROI_mass_j0j1j2g0_cat_2ex_0mx_3jx_1gx_3tx_0bx_width_10.0` |
| 208 | μ0 + jet0 + jet1 | 2e, 1μ, 2jet, 2γ | 523 | 77 | 77 | distribution | 486 - 1253 | `ROI_mass_m0j0j1_cat_2ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 209 | μ0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet | 514 | 68 | 68 | distribution | 482 - 1161 | `ROI_mass_m0j0j1j2_cat_1ex_1mx_3jx_0gx_0tx_0bx_width_10.0` |
| 210 | e0 + jet0 + jet1 | 1e, 2jet, 2γ, 3τ | 496 | 37 | 36 | distribution | 148 - 510 | `ROI_mass_e0j0j1_cat_1ex_0mx_2jx_2gx_3tx_0bx_width_10.0` |
| 211 | jet0 + jet1 + γ0 + γ1 | 2e, 1μ, 2jet, 2γ | 472 | 68 | 68 | distribution | 600 - 1280 | `ROI_mass_j0j1g0g1_cat_2ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 212 | jet0 + jet1 + γ0 + γ1 | 1e, 2jet, 2γ, 3τ | 466 | 33 | 33 | distribution | 190 - 519 | `ROI_mass_j0j1g0g1_cat_1ex_0mx_2jx_2gx_3tx_0bx_width_10.0` |
| 213 | e0 + jet0 + jet1 + jet2 | 1e, 1μ, 3jet | 441 | 84 | 84 | distribution | 573 - 1411 | `ROI_mass_e0j0j1j2_cat_1ex_1mx_3jx_0gx_0tx_0bx_width_10.0` |
| 214 | e0 + e1 + μ0 | 2e, 1μ, 3jet, 1γ | 437 | 41 | 41 | distribution | 165 - 574 | `ROI_mass_e0e1m0_cat_2ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 215 | μ0 + γ0 | 1e, 1μ, 1γ, 1τ | 410 | 36 | 35 | distribution | 51 - 409 | `ROI_mass_m0g0_cat_1ex_1mx_0jx_1gx_1tx_0bx_width_10.0` |
| 216 | e0 + e1 + μ0 | 2e, 1μ, 2jet, 1γ | 383 | 34 | 34 | distribution | 196 - 534 | `ROI_mass_e0e1m0_cat_2ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 217 | e0 + e1 + γ0 + γ1 | 2e, 1μ, 2jet, 2γ | 381 | 62 | 62 | distribution | 472 - 1090 | `ROI_mass_e0e1g0g1_cat_2ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 218 | μ0 + jet0 + jet1 + jet2 | 2e, 1μ, 3jet, 1γ | 377 | 65 | 65 | distribution | 502 - 1147 | `ROI_mass_m0j0j1j2_cat_2ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 219 | e0 + e1 + γ0 | 2e, 1μ, 2jet, 1γ | 367 | 36 | 36 | distribution | 195 - 551 | `ROI_mass_e0e1g0_cat_2ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 220 | e0 + e1 + jet0 + jet1 | 2e, 2jet, 1τ | 360 | 54 | 54 | distribution | 203 - 743 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_0gx_1tx_0bx_width_10.0` |
| 221 | μ0 + jet0 + jet1 | 2e, 1μ, 2jet, 1γ | 350 | 42 | 42 | distribution | 392 - 808 | `ROI_mass_m0j0j1_cat_2ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 222 | jet0 + jet1 + jet2 + γ0 | 2e, 1μ, 3jet, 1γ | 346 | 62 | 62 | distribution | 579 - 1198 | `ROI_mass_j0j1j2g0_cat_2ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 223 | e0 + e1 + μ0 + γ0 | 2e, 1μ, 2jet, 1γ | 335 | 48 | 47 | distribution | 307 - 779 | `ROI_mass_e0e1m0g0_cat_2ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 224 | e0 + e1 + γ0 | 2e, 1μ, 3jet, 1γ | 309 | 42 | 42 | distribution | 225 - 641 | `ROI_mass_e0e1g0_cat_2ex_1mx_3jx_1gx_0tx_0bx_width_10.0` |
| 225 | e0 + e1 + jet0 + jet1 | 2e, 1μ, 2jet, 2γ | 308 | 43 | 43 | distribution | 691 - 1119 | `ROI_mass_e0e1j0j1_cat_2ex_1mx_2jx_2gx_0tx_0bx_width_10.0` |
| 226 | e0 + e1 + jet0 + jet1 | 2e, 1μ, 2jet, 1γ | 305 | 55 | 55 | distribution | 535 - 1083 | `ROI_mass_e0e1j0j1_cat_2ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 227 | jet0 + jet1 + γ0 | 2e, 1μ, 2jet, 1γ | 292 | 47 | 47 | distribution | 488 - 955 | `ROI_mass_j0j1g0_cat_2ex_1mx_2jx_1gx_0tx_0bx_width_10.0` |
| 228 | e0 + e1 + jet0 + jet1 | 2e, 2jet | 251 | 36 | 36 | distribution | 560 - 918 | `ROI_mass_e0e1j0j1_cat_2ex_0mx_2jx_0gx_0tx_0bx_width_10.0` |
| 229 | e0 + μ0 | 1e, 1μ, 4jet | 244 | 40 | 40 | distribution | 0 - 397 | `ROI_mass_e0m0_cat_1ex_1mx_4jx_0gx_0tx_0bx_width_10.0` |
| 230 | e0 + μ0 | 1e, 1μ, 4jet, 1τ | 238 | 38 | 36 | distribution | -1 - 378 | `ROI_mass_e0m0_cat_1ex_1mx_4jx_0gx_1tx_0bx_width_10.0` |
| 231 | e0 + μ0 | 1e, 1μ, 4jet, 3γ | 222 | 34 | 34 | distribution | -0 - 339 | `ROI_mass_e0m0_cat_1ex_1mx_4jx_3gx_0tx_0bx_width_10.0` |
| 232 | e0 + μ0 | 1e, 1μ, 3jet, 3γ | 207 | 35 | 34 | distribution | 0 - 345 | `ROI_mass_e0m0_cat_1ex_1mx_3jx_3gx_0tx_0bx_width_10.0` |
| 233 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 3τ | 185 | 38 | 37 | distribution | 299 - 676 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_0gx_3tx_0bx_width_10.0` |
| 234 | e0 + jet0 + jet1 + jet2 | 1e, 3jet, 1γ, 4τ | 175 | 32 | 32 | distribution | 219 - 537 | `ROI_mass_e0j0j1j2_cat_1ex_0mx_3jx_1gx_4tx_0bx_width_10.0` |
| 235 | e0 + e1 + μ0 + γ0 | 2e, 1μ, 4jet, 1γ | 142 | 35 | 35 | distribution | 219 - 569 | `ROI_mass_e0e1m0g0_cat_2ex_1mx_4jx_1gx_0tx_0bx_width_10.0` |
| 236 | μ0 + γ0 + γ1 + γ2 | 1e, 1μ, 4jet, 3γ | 142 | 33 | 32 | distribution | 252 - 575 | `ROI_mass_m0g0g1g2_cat_1ex_1mx_4jx_3gx_0tx_0bx_width_10.0` |

## Plots

A representative sample is plotted under `plots/` - the highest-statistics channels plus a few smaller ones that still clear the bar.
