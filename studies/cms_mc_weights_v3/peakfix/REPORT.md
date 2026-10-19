# REPORT — CMS MC peak fix (18–19 Oct 2026)

Not delivered; not merged into master. Only the agreed change (option A,
`--peak-scope combined`) was made; option B was not implemented and nothing
was tuned. Every number below is **VERIFIED BY RUNNING** (PBS jobs on the
cluster) unless marked UNVERIFIED.

## What changed

Before: peak removal ran per sample, so each MC sample was cut at its own
peak and the summed SM was a sum of differently-cut pieces (step 0 found
different peak masses in 4,976 of 4,977 summed names).
Now (`--peak-scope combined`, default): for each histogram name the peak and
the outlier split are found ONCE on the combined spectrum of all samples, and
every sample is cut at that same mass. Builder commit `88d30ac`.

## Jobs

| step | job | code | result |
|---|---|---|---|
| 0 verify finding | 5244611 | `1611209` | done |
| 3 rebuild | 5244700 | `88d30ac` | exit 0; 2h07m; peak RSS 18.9 GB (PBS 28.5 GB) of 64 GB |
| 6 Z peak | 5244701 | `88d30ac` | exit 0; 13 min |
| 4 old vs new | 5248340 | `4a72294` | exit 0; 3 min |
| 5–6 data vs MC | 5248341 | `4a72294` | exit 0; 1 min |

`4a72294` only adds checks to `compare_old_new.py` (excluded files,
final-state set, NaN/inf) and stages the build reports in the compare job;
the builder is unchanged from `88d30ac`.

## Step 4 — old (per-sample) vs new (combined) build

Evidence: `evidence/compare_old_new_summary.json`; full per-name table
`evidence/compare_old_new.json` (copy of the cluster's
`work/peakfix_20261018/evidence/compare/compare_old_new.json`).

- **Same names:** 4,977 summed histograms in both, none only in one.
- **Final states:** 205 in both, identical sets.
- **Excluded files:** exactly 1 in each build, record 75589 file 98
  (Σw check: possible pre-skim). Same as before.
- **NaN/inf:** none in any histogram of either build.
- **Closure (sum of per-sample files vs summed-SM file, bin by bin):**
  max relative difference 6.2e-16 (new), 4.9e-16 (old), i.e. equal to
  floating-point rounding (not bit-identical, because of summation order).
- **One cut per name (new):** no per-sample histogram starts before the
  summed SM's first filled bin (0 of 4,977 names). The number of per-sample
  histograms that start *later* than the summed SM drops from 39,191 to
  11,833. These are samples with no entries right at the cut, not a second cut.
- **How many changed:** all 4,977 summed histograms differ (expected: the
  cut moved in nearly every name). Total weight over all histograms:
  33,001,234 → 32,770,159 (−0.70%). 3,013 histograms went up, 1,964 down;
  median relative change +1.5%.

| \|relative change of total\| | histograms |
|---|---|
| < 0.1% | 76 |
| 0.1–1% | 446 |
| 1–5% | 920 |
| 5–10% | 685 |
| 10–25% | 1,053 |
| 25–50% | 881 |
| 50–100% | 700 |
| > 100% | 216 |

  First filled bin: unchanged in 633, moved up in 4,261, moved down in 83.
  Shifts (bins of 10 GeV): 1: 253, 2: 312, 3–5: 995, 6–10: 1,065,
  11–20: 833, 21–50: 593, >50: 210.

- **Per-sample files:** each sample now has fewer histograms (23–405 fewer;
  names whose whole spectrum in that sample lies below the common cut), and
  none gained a name.

**10 largest changes by relative total** (all sparse high-jet categories with
tiny totals; the old per-sample cut removed most of each name):

| name | first bin old → new [GeV] | total old → new |
|---|---|---|
| j0b0b1 0e2m 6j 2b | 320 → 550 | 0.108 → 8.78 |
| m1b0 0e2m 6j 2b | 50 → 110 | 0.335 → 9.58 |
| j0j1j2j3 0e2m 7j 0b | 210 → 630 | 3.06 → 53.3 |
| m0j0b0b1 0e2m 6j 2b | 430 → 860 | −0.434 → 6.29 |
| m0m1j0j1 0e2m 7j 0b | 190 → 500 | 3.77 → 60.2 |
| e0m0j0j1 1e1m 7j 0b | 450 → 510 | −0.680 → 9.16 |
| j0j1j2 0e2m 7j 0b | 180 → 460 | 4.74 → 65.3 |
| e0j0j1j2 2e0m 7j 0b | 410 → 570 | 1.43 → 18.8 |
| e0m1j0b0 1e2m 3j 1b | 190 → 340 | 0.531 → 6.55 |
| m0m1j0 0e2m 7j 0b | 130 → 240 | 5.65 → 63.0 |

**10 largest first-bin shifts:** all move from 170–770 GeV to 2,150–2,850 GeV,
totals 2.3–5.5 → ~1.93 (e.g. `m1j0b0` 0e2m 7j 2b: 170 → 2,150 GeV). See the
decision item below.

**Plots** (`plots/peakfix/`): `new_stack_1.png` … `new_stack_6.png` (the 6
categories, new build) and `stack_5_old_vs_new.png` (4 leptons, 2e2μ 0j: old
first bin 120 GeV from the Higgs sample's own cut, new 190 GeV for every
sample; total 54.01 → 54.03). Old plots: `plots/fullrun/`.

| category | histogram | new total | first bin |
|---|---|---|---|
| μμ, 0 jets | m0m1 0e2m 0j 0b | 177,338 | 110 |
| ee, 0 jets | e0e1 2e0m 0j 0b | 116,519 | 110 |
| eμ, 0 jets | e0m0 1e1m 0j 0b | 26,607 | 60 |
| μμ + ≥3 jets | m0m1j0 0e2m 3j 0b | 45,607 | 180 |
| 4 leptons | e0e1m0m1 2e2m 0j 0b | 54.03 | 190 |
| μ + jet + b | j0j1b0 0e1m 2j 1b | 210,224 | 170 |

## Step 5 — names vs the data delivery

Data: `four_dataset_vB_upstreamnames_w10p0_dr012_20261007`, uncropped
`*_bumpnet.root` (read-only). Evidence: `evidence/data_vs_mc.json`.

- Data 1,975 names, MC 4,977. **In both: 1,975; data-only: 0; MC-only: 3,002.**
  Bin edges identical for every common name.
- MC-only names are the sparse high-multiplicity final states (many jets/b,
  3–4 leptons with jets). Largest groups: 56 names each in 17 final states
  (e.g. 1e1m 7j 2b, 0e2m 7j 2b, 2e0m 6j 2b); full list by final state in
  the JSON. 2e2μ 0j (the 4-lepton plot) is MC-only: 11 names.
- **First filled bin, data vs MC (1,975 names):** agree 425, differ 1,550.
  MC starts later in 800, earlier in 750.

| MC − data [bins of 10 GeV] | names |
|---|---|
| ≤ −10 | 88 |
| −9 … −3 | 225 |
| −2 | 212 |
| −1 | 225 |
| +1 | 270 |
| +2 … +3 | 238 |
| +4 … +10 | 205 |
| ≥ +11 | 87 |

  Largest: e0j0j1j2 2e0m 6j 0b, data 430 vs MC 1,510 GeV (+108 bins).

## Step 6 — data vs MC (absolute, L = 16.393 fb⁻¹, nothing rescaled)

Plots `plots/peakfix/datamc_<i>_lin.png` / `_log.png`, with data/MC ratio panel.

| category | data | MC | data/MC | first bin data / MC [GeV] |
|---|---|---|---|---|
| μμ, 0 jets | 187,476 | 177,338 | 1.057 | 110 / 110 |
| ee, 0 jets | 115,118 | 116,519 | 0.988 | 110 / 110 |
| eμ, 0 jets | 33,752 | 26,607 | 1.268 | 60 / 60 |
| μμ + ≥3 jets | 62,101 | 45,607 | 1.362 (1.280 in common bins) | 170 / 180 |
| 4 leptons (2e2μ 0j) | — not in data delivery — | 54.0 | — | — / 190 |
| μ + jet + b | 386,856 | 210,224 | 1.840 | 170 / 170 |

The μ + jet + b ratio rises with mass from ~1.5 to >2. This is consistent with
the known b-tag difference, which is out of scope here (not investigated).

**Z peak** (stored events before the Z cut, all 13 MC records,
`evidence/z_peak_ratio.json`, `plots/peakfix/zpeak_mumu_0j.png`,
`zpeak_ee_0j.png`):

| | data | MC | data/MC | pilot |
|---|---|---|---|---|
| μμ 0j, 76–106 GeV | 7,883,847 | 7,624,706 | 1.0340 ± 0.0004 | 1.035 |
| ee 0j, 76–106 GeV | 4,016,425 | 4,212,804 | 0.9534 ± 0.0005 | 0.954 |
| μμ all jets, 60–120 | 10,020,867 | 9,705,886 | 1.0325 | 1.0337 |
| ee all jets, 60–120 | 5,003,572 | 5,253,784 | 0.9524 | 0.9534 |

These match the pilot within 0.1%. They are computed from the stored events
before any peak removal, so they do not depend on this fix.

## For decision (not acted on)

1. **20 sparse names now start above 2,000 GeV.** In e.g. 0e2m 7j 2b (922
   events, 5 samples), the weighted "rightmost highest bin" of the combined
   spectrum lands at 2,000+ GeV. One event of weight ~1.93 outweighs the low-mass
   bins, where positive and negative NLO weights cancel. The rule behaves as
   specified; whether such names should use the unweighted peak
   (`--peak-on unweighted` exists) or be dropped is a convention question.
2. **3,002 MC names have no data counterpart** (including the 4-lepton 0-jet
   category); data names are all in MC.
3. **First-bin agreement with data is 425 / 1,975.** Data and MC each cut at
   their own peak; option B (cutting MC at the data's start) was not
   implemented, as agreed.

## Housekeeping

- Cluster: build `work/peakfix_20261018/build_combined/`, evidence in
  `work/peakfix_20261018/evidence/{compare,data_mc,zpeak}/`.
- Checkouts archived (listing entries == files on disk; directories left in place):
  `checkouts/peakfix_20261018/checkout_step0_1611209.tar.gz` (264 files, 65 MB),
  `checkout_repo_4a72294.tar.gz` (328 files, 65 MB).
- File count: 118,401 at start of the full task → **119,243** (+842; limits
  121,901 / 125,000 respected).
