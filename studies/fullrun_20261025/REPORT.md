# CMS full run with loose lepton IDs (25–26 Oct 2026) — REPORT

## In plain words

- **The run is complete.** All 541 data files and 497 simulation (MC) files were processed. One
  data file failed once because the CERN Open Data website did not answer in time; it was re-run
  once and worked. Every completeness check now passes.
- **Delivered histograms:** data **313** (49 final states), MC **331** in the summed file (53 final
  states). Every one of the 313 data histograms also exists in the MC.
- **Every rule check passed:** the 7 rules of the multiplicity check (R1–R7) for data and for MC; no
  broken numbers (NaN/inf), no negative uncertainties, no file hit the 500,000-entry limit.
- **Z peak (data ÷ MC, 0 jets, 76–106 GeV):** μμ **1.045**, ee **0.977**. On 18 Oct, with the old
  medium IDs, they were 1.034 and 0.953. Both moved by 1–2 percentage points; ee is now closer to 1.
- **Surprising:** in the delivered e-μ histogram with no jets, data is **2.2 ×** the MC. On 18 Oct
  it was 1.27 ×. The data more than doubled with the loose IDs (33,752 → 74,671 events), the MC
  rose by 28 %. The MC is missing W+jets and QCD multijet, which can fake an extra lepton, but this
  was **not checked**; the technical lead should look at it.
- **Compared with the 7 Oct delivery (1,975 histograms):** the new run, built the old way, would
  have 2,779 histograms, and all 1,975 old names are still there. The extra 804 come mainly from the
  5th dataset, SingleElectron (561 histograms with one electron and nothing else, which only that
  dataset can give), and the rest from the loose IDs and the new b-tag cut together (these two
  cannot be separated with what we have). The upstream #40 rule (at most 4 objects per final state)
  then merges them into **313** — that rule alone explains the big drop in the number of histograms.
- **Home folder:** the run left nothing there (no new, removed or changed entries).
- **Delivery drafts** (nothing uploaded or sent): `work/fullrun_20261025/deliver/` on the cluster,
  16 files with READMEs and checksums; the READMEs, MANIFEST and checksums are also in
  `studies/fullrun_20261025/delivery/`.
- **Next:** the technical lead verifies; then Matan uploads and writes to Maryna.

Every number below is VERIFIED BY RUNNING unless marked UNVERIFIED.

## 1. Production

| side | expected | finished with exit 0 | notes |
|---|---:|---:|---|
| DoubleMuon | 57 | 57 | |
| SingleMuon | 152 | 152 | |
| DoubleEG | 133 | 133 | |
| MuonEG | 48 | 48 | |
| SingleElectron | 151 | 151 | job 73 (record 30562 file 2) failed once (CERN portal `ReadTimeout`, before reading data), re-run `5363447[73]` exit 0 |
| **data** | **541** | **541** | `data_check` 2nd run: 541/541 complete, 0 guard violations (`evidence/status_20261026/data_check_second_run.out`) |
| MC, 13 records | 497 | 497 | audit verdict **OK**, problems [], the only Σw failure 75589 file 98 (expected; excluded from the build) |

Data events (from `data_check`): read 927.8 M; accepted DoubleMuon 9.63 M, SingleMuon 165.4 M,
DoubleEG 6.16 M, MuonEG 0.19 M, SingleElectron 102.0 M. MC: 392.7 M events read, 131.3 M stored.

## 2. Builds and checks

| output | histograms | final states | job |
|---|---:|---:|---|
| data default (#40) `datachain2/data/deliver/default/fullrun_bumpnet{,_cropped}.root` | 313 | 49 | `5363449` exit 0 |
| data exact (rule-check input) `datachain2/data/deliver/exact/` | 2,779 | 148 | `5363450` exit 0 |
| MC `mc/build_default/fullrun_summedSM_mc.root` | 331 | 53 | `5341396` exit 0 |
| MC per sample (13 files) | 249–331 each | | read-back assertions all passed |
| MC rule builds (67801, default / exact) | 302 / 3,843 | 48 / 176 | `5341398` exit 0 |

- **Rule checks:** data `all_rules_pass: true`, MC `all_rules_pass: true`; R1–R7 each `pass: true`
  with 0 violations (`evidence/final_data/rule_check_data.json`, `evidence/final_mc/rule_check_mc.json`).
  R6: events conserved by the rule (data 268,000,242 before the ≥ 100 rule in both builds).
- **NaN/inf and variances** (analysis job, every delivered file): data 0 / 0, MC summed 0 / 0, all 13
  per-sample files 0 / 0. Negative bin contents: data 0; MC summed file 288 of 331 histograms have at
  least one negative bin (negative generator weights of the NLO samples; information, not an error).
- **500,000-entry cap:** 0 capped signatures in all 541 data files (job metadata); 0 in every MC
  sample (build report); no build log mentions the cap or a STOP.

## 3. Data vs MC

### Names (`evidence/analysis/analysis.json`, `names`)

- in both: **313**; data-only: **0**; MC-only: **18**, all four-lepton final states
  (`0e_4m_0j_0b` 3, `1e_3m_0j_0b` 6, `3e_1m_0j_0b` 6, `4e_0m_0j_0b` 3);
- first filled bin: same in **128**, different in **185** — by 10 GeV (113), 20 (42), 30 (22),
  40 (3), 50 (3), 120 (1), 170 (1). Peak removal is done separately for data and for MC, so the
  starting bin can differ by design;
- **MC names whose first filled bin is above 2,000 GeV: none** (re-test from 17 Oct: closed).

### Z peak, before peak removal (method of the 18 Oct `peakfix/z_peak_ratio.py`)

Stored events of both sides before any post-processing; data = DoubleMuon inclusive + the other
four datasets exclusive (541 shards); MC = all 13 records (496 weighted scratch shards), restricted
to the five delivered acceptances; absolute normalisation, nothing rescaled.

| | data | MC | data/MC | 18 Oct (medium IDs) |
|---|---:|---:|---:|---:|
| μμ, 0 jets, 76–106 GeV | 8,082,067 | 7,732,105 | **1.0453 ± 0.0004** | 1.0340 |
| ee, 0 jets, 76–106 GeV | 5,717,150 | 5,853,921 | **0.9766 ± 0.0004** | 0.9534 |
| μμ, 0 jets, 60–120 | 8,465,053 | 8,094,910 | 1.0457 | |
| ee, 0 jets, 60–120 | 5,954,643 | 6,097,790 | 0.9765 | |
| μμ, all jets, 60–120 | 10,281,027 | 9,830,716 | 1.0458 | |
| ee, all jets, 60–120 | 7,309,607 | 7,489,380 | 0.9760 | |

The change from 18 Oct is reported, not explained (the loose IDs change both data and MC; other
differences: five datasets instead of four in the data, the SingleElectron acceptance in the MC union).

### Delivered histograms, data vs MC (absolute, L = 16.393 fb⁻¹; `plots/stack_*.png`)

| category (histogram) | data | MC | data/MC | 18 Oct |
|---|---:|---:|---:|---:|
| μμ, 0 jets (`m0m1`, 0ex_2mx_0jx_0bx) | 208,879 | 180,251 | 1.159 | 1.057 |
| ee, 0 jets (`e0e1`, 2ex_0mx_0jx_0bx) | 153,549 | 144,047 | 1.066 | 0.988 |
| **eμ, 0 jets** (`e0m0`, 1ex_1mx_0jx_0bx) | 74,671 | 34,150 | **2.187** | 1.268 |
| μμ + jets (`m0m1j0`, 0ex_2mx_1jx_0bx) | 1,208,805 | 1,148,177 | 1.053 | (18 Oct used ≥ 3 jets: 1.362) |
| μ + jet + b (`m0j0j1b0`, 0ex_1mx_2jx_1bx) | 584,495 | 405,135 | 1.443 | 1.840 |
| 3 leptons (`e0m0j0`, 1ex_2mx_1jx_0bx) | 1,048 | 1,249 | 0.839 | — |

These are after the Z cut (110 GeV) and peak removal. The MC lacks W+jets, QCD multijet, single top
t/s-channel and fully hadronic tt̄ (written on every plot), so data above MC is expected where those
contribute. **The eμ 0-jet ratio of 2.2 is the main open question** (UNVERIFIED cause).

## 4. Compared with the 7 Oct data delivery

| | 7 Oct | this run, exact rule | this run, #40 (delivered) |
|---|---:|---:|---:|
| datasets | 4 | 5 | 5 |
| histograms | 1,975 | 2,779 | **313** |
| final states | 103 | 148 | 49 |
| entries | 82,956,881 | 147,706,148 | 137,641,202 |

(Manifests: 7 Oct `output/cms_datasets/deliver/four_dataset_vB_upstreamnames_w10p0_dr012_20261007/`,
read-only; this run `datachain2/data/deliver/{exact,default}/`.)

What explains the change, as far as the outputs allow:
1. **#40 rule:** 2,779 → 313 histograms and 148 → 49 final states, with the same events (rule check
   R6). This is the whole drop. Fully separated (exact vs default build of the same inputs).
2. **5th dataset, SingleElectron:** of the 804 names the exact build adds to the 1,975 of 7 Oct (all
   1,975 are still present), **561** are in final states with exactly one electron and no muon,
   which only SingleElectron can produce (60.9 M histogram entries). Separated.
3. **Loose IDs and b-tag 0.2489 (was 0.2598):** the other **243** new names (in 44 new final states)
   and the higher counts in the old names (median × 1.14: × 1.04 in final states without electrons,
   × 1.51 with electrons, × 1.10 with b-jets). SingleElectron's extra events also add to these.
   **These causes cannot be separated** with the outputs at hand (no build with only one of them
   changed); no extra builds were run.

## 5. Plots (`plots/`, made by PBS job `5364861`, io=25)

- `stack_1.png` μμ 0j, `stack_2.png` ee 0j, `stack_3.png` eμ 0j, `stack_4.png` μμ + jets,
  `stack_5.png` μ + jet + b, `stack_6.png` 3 leptons — data vs MC stacks with ratio panel and the
  missing-MC note;
- `zpeak_mumu_0j.png`, `zpeak_ee_0j.png` — Z peaks before peak removal;
- `histograms_per_final_state.png` — delivered histograms per final state, data vs MC;
- `dataset_examples.png` — two example histograms for each of the five datasets (the final states
  each dataset dominates; SingleElectron: `e0j0` and `e0j0j1` in 1e+jets, 100 % SingleElectron).

## 6. Delivery drafts (nothing uploaded or sent)

Folder `work/fullrun_20261025/deliver/` (new; copies, the originals are untouched; `cmp` identical):
`data/` 2 files (cropped = for BumpNet, uncropped), `mc/` 14 files (summed SM + 13 samples), names
`CMS_Run2016GH_<datasets or sample>_16p393invfb_prod2026-10-25_….root`; `SHA256SUMS.txt`;
`docs/` = 16 READMEs + `MANIFEST.md`. In git: `delivery/` (READMEs, MANIFEST with file:line at
75b399e, checksums, and `make_readmes.py`).

## 7. Evidence and housekeeping

- `evidence/final_data/`, `evidence/final_mc/`: the chain's summaries (build summaries, manifest,
  rule checks, audit, sanity, trimmed MC build report).
- `evidence/analysis/analysis.json` and `analysis_job.out`: this report's analysis
  (`analysis/analyze_fullrun.py`, run from the pinned clone `checkouts/fullrun_20261025/analysis_faf7be2`;
  its production code is identical to 75b399e).
- `evidence/status_20261026/`: the re-run of SingleElectron job 73.
- The pinned clone `repo_75b399e` is archived as `checkouts/fullrun_20261025/repo_75b399e.tar.gz`
  (65 MB, 235 files = the clone's 235; the clone is kept).
- File quota: see HANDOFF (final count).
- The MC sanity job's own plots and report: `work/fullrun_20261025/mc/evidence/plots/`.
