# Final MC build, 14 Nov 2026: report

Every number here is VERIFIED BY RUNNING unless it is labelled ESTIMATE or UNVERIFIED. The sources are:
- `evidence/final_build/checks_final.json`, from `post/checks_final.py` at d7fc115;
- `evidence/final_build/checks_v4.json`, from `post/checks_v4.py` at pin 6de9d3e;
- `evidence/final_build/rule_check_mc_*_20261109.json`;
- `evidence/final_build/build_report_summary.json`.

The checks ran in PBS job 5537708 and the build in job 5537436.

## In plain words

- **What was built.** The new simulated background (MC) adds up 71 samples. These are the 13 samples delivered on 25 Oct,
  reused unchanged, plus the 58 new ones. It uses the same code and options as the 25 Oct delivery and the decided
  cross sections (registry v5). The new background is much more complete than the 25 Oct one.
- **Checks.** Every technical check passes:
  - all 1,289 production jobs are OK;
  - the build has exactly the 71 samples the registry lists for the full run;
  - the seven rule checks R1–R7 pass;
  - there are no broken values (NaN, infinite or negative variances);
  - the 500,000-entry trim never triggered.
- **Z peak.** The Z peak still agrees with the data to within about 4 % (μμ data/MC 1.044, ee 0.976). This is the same as
  on 25 Oct, so the new samples did not disturb the normalisation.
- **Gaps in the data/MC comparison.** The large gaps of 25 Oct are mostly closed:
  - e + 1 jet went from 11.9 to 1.73, μ + 1 jet from 12.0 to 1.60, and μ + 2 jets from 6.8 to 1.18;
  - eμ with no jets went from 2.19 to 1.29.

  The new W+jets samples do almost all of this.
- **What is still missing.** Single lepton + jets still has about 1.2–1.9 times more data than MC. QCD multijet events
  (jets faking a lepton) are expected to fill a large part of that, and QCD is deliberately NOT in this build (Matan,
  14 Nov 2026). Photon processes are also not included. Every plot says so.
- **Spiky bins.** Many bins can be dominated by a single heavy MC event, mostly in the far tails. The worst cases are in
  the low-mass Drell-Yan sample, which was already in the 25 Oct delivery.
- **Binning — open, Matan to decide.** The MC still starts at a different mass than the delivered data in 165 of 313
  histograms (25 Oct: 185). It usually differs by one 10 GeV bin. The options are below; I have not rebuilt or forced
  anything.

## 1. Production, audit, build (VERIFIED BY RUNNING)

- **Audits:**
  - production audit: verdict OK, 1,289/1,289 jobs over 58 records, no problems, no Σw failures;
  - 25 Oct audit of the 13 reused records: OK, 497/497, with only the known Σw failure 75589 file 98, which is
    excluded as on 25 Oct.
- **Tier 6:** 107/107 OK.
- **Build job 5537436:** 1 h 15 min, 33 GB, exit 0. Its outputs are in `full/build_20261109/`:
  - 71 per-sample files;
  - the summed file with 331 histograms;
  - `fullrun_build_report.json`, sha256 b38f6687…cf812.

  All read-back assertions passed.
- **Build metadata:**
  - `git_commit` 6de9d3e6…;
  - `registry` `full/registry/cms_mc_normalisation_v5.json` (sha256 6d193c44…f01e0, equal to the git blob at 5493d0f);
  - `extra_runs_dirs` = the 25 Oct runs;
  - options as 25 Oct: weighted, combined, raw, both, 100, upstream40.
- **Samples built vs registry:** 71 built, 71 `in_full_run` in v5, none missing, none extra.
- **σ and normalisation:**
  - σ_eff is the same in the build and the registry for all 71;
  - the recomputed normalisation σ×1000×L/Σw equals the built one (maximum relative difference 0.0).
- **500k trim:** 0 capped signatures; the maximum cap scale is 1.0.

## 2. Rule checks R1–R7 (VERIFIED BY RUNNING)

`all_rules_pass: true` for 67801 (tt̄ 2ℓ), 69715 (W+0j), 67841 (tt̄ hadronic) and 64759 (t-channel top). Each sample
was built per sample with registry v5, and `studies/fullrun_20261025/rule_check.py --kind mc` was run on it (job 5537451).

## 3. NaN / variance / negative weights (VERIFIED BY RUNNING)

- **NaN, infinite values and negative variances:** 0 over the 331 summed histograms and every per-record file.
- **Negative-weight fraction of the stored events** (all the samples are in the table in `checks_final.json`):

| sample group | negative-weight fraction |
|---|---|
| W+jets | 0.08 (0j), 0.25 (1j), 0.34 (2j) |
| DY | 0.17 (M-50), 0.20 (M-10to50) |
| NLO dibosons | 0.18–0.22 |
| tZq | 0.37 |
| ttW / ttZ | 0.22–0.25 |
| four tops | 0.28 |
| POWHEG samples (tt̄, single top t-channel, Higgs) | ≤ 0.035 |

- **Negative bin contents:** some bins have negative content (the NLO weights). The build report has the per-histogram
  inventory under `summed_sm.negative_bin_inventory`.

## 4. Per-sample table (VERIFIED BY RUNNING; full table in `checks_final.json` → `samples`)

The yield is the sum over final states of the largest histogram integral in each final state, so every event is counted
once per final state. The shares therefore add up to 1.007, not exactly 1.

| record | sample | σ_eff [pb] | files | yield | share |
|---|---|---|---|---|---|
| 69717 | W+jets 1j | 8403.3 | 30 | 16,798,951 | 40.3 % |
| 69719 | W+jets 2j | 3123.8 | 63 | 9,506,786 | 22.8 % |
| 35669 | DY M-50 | 5765.4 | 41 | 8,608,840 | 20.7 % |
| 69715 | W+jets 0j | 49999.6 | 97 | 3,281,791 | 7.9 % |
| 67993 | tt̄ semileptonic | 367.86 | 138 | 1,620,523 | 3.9 % |
| 35631 | DY M-10to50 | 18610 | 25 | 697,106 | 1.7 % |
| 67801 | tt̄ 2ℓ | 89.28 | 49 | 636,974 | 1.5 % |
| 64759 / 64659 | t-channel top / antitop | 136.02 / 80.95 | 86 / 35 | 160,368 / 102,646 | 0.4 % / 0.2 % |
| 72658 | WW → ℓνqq | 52.362 | 30 | 148,429 | 0.36 % |
| 64839 / 64895 | tW | 19.56 each | 10 / 11 | ≈101,000 each | 0.24 % each |
| the other 57 | | | | ≤ 46,637 each | ≤ 0.11 % each |

- Every one of the 71 samples contributes a non-zero yield. The smallest is 74900 (Z → νν, HT > 2500) at 0.1 events,
  and 40062 (the ESTIMATE) is 0.6 events.
- 69717, which has only 30 of its 117 files published, is the largest single sample.

## 5. Data vs MC names and binning (VERIFIED BY RUNNING)

The comparison is with the delivered 25 Oct data, both the uncropped and cropped files.

- **Names:**
  - 313 are in both files, 18 only in the MC and 0 only in the data;
  - the 18 MC-only names are all four-lepton categories (3e1μ, 4e, 1e3μ, 4μ) that are not in the data file, the same 18
    as on 25 Oct;
  - the new MC has exactly the 331 names of the 25 Oct MC.
- **Axis:** identical in all 313 shared histograms (0–10,000 GeV, 10 GeV bins).
- **First filled bin:**
  - same as the data in 148 of 313 histograms (25 Oct MC: 128 of 313);
  - shift MC − data, in GeV, as number of histograms: −170: 1, −120: 1, −50: 1, −40: 1, −30: 4, −20: 13, −10: 33,
    0: 148, +10: 76, +20: 22, +30: 9, +40: 2, +50: 2;
  - 111 start later than the data and 54 earlier; 109 of the 165 mismatches are a single 10 GeV bin.
- **Mismatches by number of leptons:**
  - 1 lepton: 47 of 96 histograms;
  - 2 leptons: 52 of 126;
  - 3 leptons: 57 of 80;
  - 4 leptons: 9 of 11.
  - The per final state counts are in `checks_final.json` → `names_binning.edges.by_final_state_n_hist_n_mismatch`.
- **Inside the cropped data range:** in 259 of 313 histograms the MC starts inside the mass range of the cropped data.
- **Last filled bin:** it never coincides. The data stop where the data stop, and the MC tail extends further.
- **New MC vs 25 Oct MC:** the first bin is unchanged in 258 of 313 histograms.
- **Why:** the peak removal cuts the MC at a mass taken from the weighted sum of all MC samples, and the data at a mass
  taken from the data. Adding samples moved the MC cut in 55 histograms.

**Options for Matan (no choice made):**
- **(A) Rebuild the data** with start masses taken from the new MC. The 25 Oct data delivery stays as it is; this would be
  a new data file. I have not checked whether the data builder can take given start masses (UNVERIFIED; possibly a code
  change).
- **(B) Rebuild the MC with the data's start masses** (force the data edges on the MC). I have not checked whether the
  MC builder's options allow this (UNVERIFIED; possibly a code change, which also needs a decision).
- **(C) Deliver as is.** Both files share the same axis, and the analysis crops both to a common range (for example the
  cropped data's range, or the later of the two start masses), with the mismatch documented in the README, as now.
- **(D) Other:** for example, deliver the MC without peak removal and let the analysis apply one cut to both.

## 6. Z peaks, 76–106 GeV, 0 jets (VERIFIED BY RUNNING; from the data runs and the build scratch, checks_v4)

| | data | MC new | data/MC new | data/MC 25 Oct |
|---|---|---|---|---|
| μμ | 8,082,067 | 7,742,211 ± 4,349 | **1.0439** | 1.0453 |
| ee | 5,717,150 | 5,859,751 ± 3,795 | **0.9757** | 0.9766 |

Over 60–120 GeV the ratios are μμ 1.0436 and ee 0.9752; with all jet bins they are 1.0426 and 0.9734. Almost all of the
MC under the peak is DY M-50: 7,719,733 of 7,742,211 in μμ. The new samples add about 0.1 %.

Plots: `plots/zpeak_mumu_0j.png` and `plots/zpeak_ee_0j.png`.

## 7. Data/MC per final state, delivered histograms (VERIFIED BY RUNNING)

The "raw" ratio uses each file's own integral; the "common" ratio uses only the bins filled in both. The gap closed is
(MC new − MC old) / (data − MC old).

| final state | histogram | data | MC 25 Oct | MC new | data/MC 25 Oct | data/MC new (raw) | data/MC new (common) | gap closed |
|---|---|---|---|---|---|---|---|---|
| μμ 0j | mass_m0m1 0e2m0j0b | 208,879 | 180,251 | 190,042 | 1.159 | **1.099** | 1.099 | 34 % |
| ee 0j | mass_e0e1 2e0m0j0b | 153,549 | 144,047 | 148,348 | 1.066 | **1.035** | 1.035 | 45 % |
| eμ 0j | mass_e0m0 1e1m0j0b | 74,671 | 34,150 | 57,903 | 2.187 | **1.290** | 1.290 | 59 % |
| μμ + 1j | mass_m0m1j0 0e2m1j0b | 1,209,000 | 1,148,177 | 1,158,000 | 1.053 | **1.044** | | 16 % |
| ee + 1j | mass_e0e1j0 2e0m1j0b | 849,700 | 903,160 | 911,300 | 0.941 | **0.932** | | (MC above data) |
| eμ + 1j | mass_e0m0j0 1e1m1j0b | 33,600 | 18,744 | 27,450 | 1.792 | **1.224** | | 59 % |
| e + 1j | mass_e0j0 1e0m1j0b | 18,920,000 | 1,594,444 | 10,930,000 | 11.87 | **1.731** | 1.731 | 54 % |
| μ + 1j | mass_m0j0 0e1m1j0b | 22,840,000 | 1,904,994 | 14,240,000 | 11.99 | **1.604** | 1.191 | 59 % |
| e + 2j | mass_e0j0j1 1e0m2j0b | 4,712,000 | 567,237 | 2,871,000 | 8.31 | **1.641** | | 56 % |
| μ + 2j | mass_m0j0j1 0e1m2j0b | 4,644,000 | 679,760 | 3,920,000 | 6.83 | **1.185** | 1.106 | 82 % |
| e + 3j | mass_e0j0j1j2 | 1,384,000 | 203,018 | 740,500 | 6.82 | **1.869** | | 46 % |
| μ + 3j | mass_m0j0j1j2 | 1,362,000 | 240,641 | 968,500 | 5.66 | **1.407** | | 65 % |
| e + j + b | mass_e0j0b0 1e0m1j1b | 656,200 | 160,451 | 369,000 | 4.09 | **1.778** | | 42 % |
| μ + j + b | mass_m0j0b0 0e1m1j1b | 823,200 | 195,283 | 497,800 | 4.22 | **1.654** | 1.433 | 48 % |
| μ + 2j + b | mass_m0j0j1b0 0e1m2j1b | 584,500 | 405,135 | 526,000 | 1.443 | **1.111** | | 67 % |
| e + 2j + b | mass_e0j0j1b0 1e0m2j1b | 521,000 | 314,857 | 401,500 | 1.655 | **1.298** | | 42 % |
| 3ℓ eμμ + 1j | mass_e0m0j0 1e2m1j0b | 1,048 | 1,249 | 1,333 | 0.839 | **0.786** | 1.039 | (MC above data) |
| 3ℓ eeμ 0j | mass_e0e1 2e1m0j0b | 119 | 66.3 | 70.4 | 1.795 | **1.690** | | 8 % |
| 3ℓ eμμ 0j | mass_m0m1 1e2m0j0b | 86 | 81.8 | 92.2 | 1.051 | **0.933** | | |
| 3ℓ μμμ 0j | mass_m0m1 0e3m0j0b | 1,830 | 1,069 | 1,073 | 1.712 | **1.706** | | 1 % |
| 3ℓ eee 0j | mass_e0e1 3e0m0j0b | 476 | 447.1 | 452.6 | 1.065 | **1.052** | | 19 % |
| 4ℓ eeμμ | mass_e0e1m0m1 2e2m0j0b | 87 | 86.5 | 88.0 | 1.006 | **0.989** | | |

Values printed to 4 significant figures in the job log are rounded the same way here. The exact values are in
`checks_final.json` → `data_mc_categories`, and every histogram is in `data_mc_all`.

**Single lepton + jets.** The new W+jets samples add most of the MC:
- e + 1j: 8,710,819 of 10,930,000;
- μ + 1j: 11,816,147 of 14,240,000;
- μ + 2j: 3,290,079 of 3,920,000.

About 54–82 % of the 25 Oct gap is closed. The rest (data/MC 1.1–1.9) is where the QCD probe (`QCD_PROBE.md`, ESTIMATE)
expects QCD multijet with fake or non-prompt leptons, which is NOT in this build. The raw and common ratios differ for
μ + 1j (1.60 vs 1.19) because the MC and the data start at different masses (section 5), so the low-mass bins weigh a
lot.

**eμ 0j (the 2.19 question).** data/MC went from 2.187 to 1.290. The MC added there is mostly W+jets (23,313 of the
57,903). That is one real lepton plus a second lepton from a jet, a fake. The rest of the addition is Higgs (182),
single top (170) and dibosons (69). The stack (`plots/stack_emu_0j.png`) shows isolated W+jets spikes at high mass:
single heavy events (section 8). The QCD probe saw no QCD in eμ 0j (ESTIMATE, one file per sample).

**MISSING from every comparison:** QCD multijet and photon processes (γ + jets, Vγ, tt̄γ). Every stack says so.

## 8. Single-event dominance D3, over all histograms (VERIFIED BY RUNNING)

**Method.** A bin is flagged if, for some sample, the upper bound on one event's weight is more than 50 % of the bin's
summed MC content. The bound is min(√Σw², normalisation × max|genWeight| × cap scale). Because it uses the sample's
largest |genWeight|, it is an UPPER bound and the true count is lower.

- **Flagged bins:** 14,431, in all 331 histograms. 3,184 of them have summed MC content ≤ 0 (negative weights).
- **By sample:**

| sample | flagged bins |
|---|---|
| 35669 DY M-50 | 3,550 |
| 69719 W+2j | 2,589 |
| 67801 tt̄ 2ℓ | 1,747 |
| 72752 WZ → 3ℓν | 1,722 |
| 67993 tt̄ 1ℓ | 858 |
| 72742 WZ → 2ℓ2q | 502 |
| 64895 tW | 330 |
| 64839 tW̄ | 306 |
| 75589 ZZ → 4ℓ | 288 |
| 68187 ttZ | 280 |
| 69717 W+1j | 112 bins in 33 histograms |
| 72761 WZZ | 80 bins in 59 histograms |

  The full list is in `checks_final.json` → `d3.bins_by_sample`.
- **By final state:** the most are in 2ℓ + 2 jets and 2ℓ + j + b (μμ 2j 787, μμ 1j1b 768, ee 2j 756, ee 1j1b 702)
  (`d3.bins_by_final_state`).
- **Worst 20 by single-event weight:** all come from 35631 (DY M-10to50, reused from 25 Oct). Its bound is 8.26 events,
  in tail bins with 1.5–15.5 MC events, for example mass_e0b0 2e0m0j1b at 540 GeV, where it is ≤ 8.26 of 10.4.
- **Plots:** `plots/d3_example_1.png` … `d3_example_5.png`.
- **69717** (W+1j): 30 of 117 files published, so its MC luminosity is ≈ 0.08 × the data luminosity (ESTIMATE).
- **72761** (WZZ): 6 of 9 files.

## 9. Plots (`plots/`)

- `stack_mumu_0j`, `stack_ee_0j`, `stack_emu_0j`, `stack_mumu_1j`, `stack_e_1j`, `stack_mu_2j`, `stack_mu_1j1b` and
  `stack_3l_emm_1j`. Each has the MC stacked by group, the 25 Oct MC as a dashed line, the data and a ratio panel, and
  states "MC missing: QCD multijet, photon processes".
- `zpeak_mumu_0j` and `zpeak_ee_0j`.
- `d3_example_1` … `d3_example_5`.

## 10. Delivery draft (NOT uploaded, NOT sent)

On the cluster, `full/deliver_20261109/` holds:
- `CMS_Run2016GH_MC-summedSM-71samples_16p393invfb_build2026-11-14_mc.root`, a copy of
  `build_20261109/fullrun_summedSM_mc.root` (`cmp` OK, sha256 91beacdf…bd03);
- its `.README.txt`;
- `SHA256SUMS.txt`.

The README, MANIFEST (file:line sources at pin 6de9d3e), checksums and the generator `make_readme.py` are committed in
`delivery/`.

## Open points for Matan

1. Binning vs the delivered data: options A–D (section 5).
2. QCD multijet: excluded by decision on 14 Nov; the question to Maryna is still open.
3. Still pending from the registry:
   - Matan's live check of the three W+jets portal values;
   - the order label of 68847, which is UNVERIFIED in the registry.
4. Whether to report the unpublished 69717 / 72761 files to CERN Open Data.
