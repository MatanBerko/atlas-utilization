# QCD multijet probe (7 Nov 2026)

**Every yield below is an UNREVIEWED ESTIMATE, for the decision only.** It comes from ONE file per sample, uses the
portal generator cross sections, and was not reviewed. No QCD number enters any registry. Counts of events are
VERIFIED BY RUNNING unless marked ESTIMATE. No QCD production was submitted.

## In plain words

- **Does our selection apply a lepton trigger to MC? Yes.** Every stored MC event must pass one of the delivered lepton
  triggers and have a matched, identified lepton. It must also be in the five-dataset event union the builder uses.
  **But our delivery also histograms single-lepton + jets final states** (for example one electron + one jet). Single
  lepton final states hold 249 M of the 268 M stored data events. So Maryna's argument ("killed by the single-lepton
  trigger") holds for the **two-lepton** categories, but **not for the single-lepton + jets** categories.
- **Does QCD survive?** Rarely per event, but the weights are huge.
  - In file 0 of the 10 samples, 6-769 events per file enter a histogram: 1,395 events from 5.17 M read.
  - Almost all have **one lepton plus jets**, usually a fake or non-prompt electron or muon.
  - In the full samples this would be about 32 M weighted events (HT-binned set) or 77 M (flat sample) (ESTIMATE). That
    is the same order as the single-lepton data (e.g. 1 e + 1 jet: data 25.1 M; 25 Oct MC 1.6 M; QCD estimate 11-15 M).
  - **Two-lepton categories: almost nothing.** 4 events (HT set, ≈ 216 weighted) and 24 events (flat, ≈ 1.1 × 10⁵,
    almost all μμ + jets) against 18.7 M two-or-more-lepton data events.
  - **eμ 0-jet (the open data/MC = 2.19 question): 0 events in all 10 files** (95 % upper limits in the table).
- **Would it make spikes? Yes, certainly with the flat sample, and often with the low-HT bins.**
  - One flat-sample event can weigh up to 1.9 million data events.
  - 11 of the flat sample's 20 heaviest events would each be more than half of a 25 Oct MC bin they fall in (worst 99.8 %).
  - In the HT-binned set, 10 of the 153 heaviest events checked would exceed 50 % of an occupied bin. They come from the
    low-HT samples, where one event weighs 590-86,000 data events.
  - **The statistics would be poor**: the expected number of MC events entering a histogram is ~56,000 (HT set) or
    ~9,300 (flat), against tens of millions of weighted events.
- **Cost (ESTIMATE):**
  - HT-binned set: 385 files, 319 M events, ~10 CPU h, ~5,800 cluster files (incl. the build).
    **This does not fit under 125,000** with or without tier 6 (headroom ~3,500 with, ~5,100 without).
  - Flat sample: 27 files, 19 M events, < 1 CPU h, ~400 files. **Fits either way.**
- **Options** (no recommendation; see the end): add the HT-binned set / add the flat sample / skip QCD and document it.

## B1. What the code does to an MC event (VERIFIED BY READING, pinned commit 6de9d3e)

`D` = `studies/cms_datasets/cluster/run_dataset_on_file.py`, `S` = `studies/m0m1j0_cms/selection.py`,
`B` = `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py`.

1. **Trigger gate on MC.** For `--is-mc` the own-trigger set is the union of all four matched4 datasets' paths plus
   Ele27 (`D:2178-2182`, `MATCHED4_TRIGGER_PATHS` `D:277-282`, `ELE27_PATH` `D:323`). It is applied with
   `apply_trigger_requirement(..., {"mode": "any"})` (`D:2273-2275`). The paths are:
   - single muon `HLT_IsoMu24` (`D:242`);
   - dimuon `HLT_Mu17_TrkIsoVVL_(Tk)Mu8_TrkIsoVVL_DZ`;
   - dielectron `HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ`;
   - eμ `HLT_Mu23_..._Ele12_..._DZ` / `HLT_Mu8_..._Ele23_..._DZ`;
   - single electron `HLT_Ele27_WPTight_Gsf`.

   (`studies/cms_datasets/cluster/datasets_records.py:31-40`.) Golden JSON is skipped for simulation (`D:2248-2266`).
2. **Objects** (`D:2308-2310` → `S`):
   - muon: pT > 25 GeV, |η| < 2.4, `Muon_looseId`, `pfRelIso04_all` < 0.15 (`S:56-61`, `S:176-182`);
   - electron: pT > 25 GeV, |η| < 2.5, `Electron_cutBased` ≥ 2 = Loose (`S:63-67`, `S:193-197`; the CMS cut-based
     Loose ID contains a relative-isolation cut, UNVERIFIED in this code);
   - jets: pT > 30 GeV, |η| < 2.5, cleaned ΔR 0.4 from leptons; b-tag DeepJet medium 0.2489 (`S:69-77`).
3. **Store rule** (`mc_store_mask`, `D:1484-1496`, applied `D:2451`): an MC event is stored if ANY data acceptance
   passes, or the Ele27 candidate, or the SingleElectron acceptance. Each acceptance means the path fired AND offline
   selected lepton(s) are trigger-matched with thresholds (`D:1021-1047`, `D:1049-1178`, `D:1179-1232`, `D:1315-1345`):
   - SingleMuon: ≥ 1 matched muon ≥ 24 GeV;
   - DoubleMuon: 2 matched, leading ≥ 17 GeV;
   - DoubleEG: 2 matched electrons, offline > 30 GeV (both);
   - MuonEG: ≥ 1 muon + matched electron leg;
   - SingleElectron: matched electron, online ≥ 27, offline > 32 GeV.
4. **Builder event union** (`B:601-607`): only events with one of the five delivered acceptance bits enter histograms
   (`MC_ACC_BITS_DELIVERY_UNION`, `D:382`).
5. **Histograms**: one invariant mass per combination of ≥ 2 objects of the event's final state, so an event with one
   lepton and ≥ 1 jet (or b-jet) DOES enter histograms, e.g. `ROI_mass_e0j0_cat_1ex_0mx_1jx_0bx` (25 Oct delivery,
   `studies/fullrun_20261025/evidence/final_data/delivery_plot_inputs.json`). The builder then applies its mass-range
   cuts (Z cut, combined peak/split); those are NOT applied in this probe (upper bound).

**So:** a QCD event needs a triggered, matched, identified (loose) lepton of > 24-32 GeV. That is what Maryna's argument
relies on, and it is true here too: 99.93-99.999 % of the QCD events are rejected (table below). But a fake or
non-prompt lepton plus jets is enough to enter our single-lepton + jets histograms, and the QCD cross sections are so
large that the few survivors carry a large weight.

## B2. Samples probed

- **HT-binned (madgraphMLM + Pythia8, PSWeights)**, 9 bins 50 → ∞ GeV: 63132, 63087, 63111, 63119, 63127, 63140,
  63079, 63095, 63103.
- **Flat-pT inclusive Pythia8: 63168 `QCD_Pt-15to7000_TuneCP5_Flat2018_13TeV_pythia8`.** Three flat records exist:
  63226 (pT 5-10), 63150 (10-15) and 63168 (15-7000). 63168 was taken because it is the only one that spans the full
  hard-scatter range of the ATLAS Pythia8 dijet slices JZ0-JZ12 (one Pythia8 sample instead of 13 slices; the flattening
  is undone by per-event weights). The other two are below our 30 GeV jet / 25 GeV lepton thresholds.
- **Noted, not probed:**
  - Pythia8 pT-binned inclusive slices exist too (QCD_Pt_15to30 … 3200toInf, records 63166 … 63212, 14 bins); they are
    the most literal counterpart of the JZ slices;
  - the HT-binned BGenFilter, Herwig7 (CH3) and `madgraph` (non-MLM) HT sets.
- **Lepton-enriched sets (listed only, NOT probed):** μ-enriched (12 pT bins 15 → 1000+, + inclusive Pt-20 MuPt15 and
  Pt-30 MuPt4), EM-enriched (8 bins 15 → 300+), b/c → e (6 bins 15 → 250+) — PLAN.md (plan branch) appendix j.

## B3/B4. Probe results (file 0 each; VERIFIED BY RUNNING except columns marked ESTIMATE)

Array 5469520[] (pinned code 6de9d3e, `pbs_mc_pilot.sh` unchanged, mem 8 GB, 6 h, io=25) into
`work/mcexp_20261103/qcd_probe_20261107/` (not the production tree): **10/10 exit 0, every Σw self-check passes.**
Analysis: `qcd_probe/analyze_qcd_probe.py` (job 5469585) → `evidence/qcd_probe_analysis.json`.

| record | sample | σ portal [pb] | events read | pass trigger | stored | in union | enter a histogram | e-μ 0j | typical w / MC event (ESTIMATE) | max event w (ESTIMATE) | expected events, full sample (ESTIMATE) | weighted yield, full sample (ESTIMATE) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 63132 | HT 50-100 | 1.862e+08 | 1,175,733 | 28 | 10 | 6 | 6 | 0 | 8.6e+04 | 8.6e+04 | 181 | 1.6e+07 |
| 63087 | HT 100-200 | 2.362e+07 | 504,642 | 60 | 26 | 25 | 17 | 0 | 5.3e+03 | 5.3e+03 | 2,476 | 1.3e+07 |
| 63111 | HT 200-300 | 1.553e+06 | 169,094 | 67 | 19 | 17 | 17 | 0 | 588 | 588 | 4,351 | 2.6e+06 |
| 63119 | HT 300-500 | 3.247e+05 | 309,380 | 196 | 54 | 53 | 51 | 0 | 115 | 115 | 7,638 | 8.8e+05 |
| 63127 | HT 500-700 | 3.035e+04 | 781,743 | 902 | 178 | 174 | 174 | 0 | 9.45 | 9.45 | 11,721 | 1.1e+05 |
| 63140 | HT 700-1000 | 6.425e+03 | 34,874 | 55 | 15 | 13 | 13 | 0 | 2.53 | 2.53 | 15,531 | 3.9e+04 |
| 63079 | HT 1000-1500 | 1.117e+03 | 172,139 | 472 | 84 | 81 | 81 | 0 | 1.49 | 1.49 | 5,766 | 8.6e+03 |
| 63095 | HT 1500-2000 | 1.083e+02 | 171,251 | 652 | 94 | 94 | 94 | 0 | 0.189 | 0.189 | 5,147 | 974 |
| 63103 | HT 2000-∞ | 2.194e+01 | 256,562 | 1,449 | 174 | 173 | 173 | 0 | 0.074 | 0.074 | 3,282 | 243 |
| **HT set** | | | 3,575,418 | 3,881 | 654 | 636 | 626 | **0** | | | ~56,000 | **~3.2e+07** |
| 63168 | flat pT 15-7000 | 1.371e+09 | 1,596,000 | 9,146 | 793 | 776 | 769 | **0** | (varies) | **1.9e+06** | 9,289 | **7.7e+07** |

- **By trigger stream** (stored events; an event can pass several):
  - SingleElectron acceptance: 3, 16, 13, 40, 140, 13, 66, 80, 153 (HT) and 667 (flat);
  - SingleMuon: 3, 9, 4, 13, 34, 0, 13, 14, 19 and 104;
  - DoubleMuon: 0-2 (HT) and 17 (flat);
  - DoubleEG: 0 and 3;
  - MuonEG: 0 everywhere.
- **Generator weights:** HT samples: genWeight = 1 for every stored event (no spread). Flat sample: per-event genWeight
  of stored events from 4.7e-21 to 0.0209 (Σw of file 0 = 20,262 for 1.596 M events). Full-run weights span 4e-13 to
  1.9e+06 data events; the heaviest are low-pT events.
- **By lepton count** (file 0 → full-sample weighted, ESTIMATE):

  | sample | one lepton (events, weighted) | two leptons (events, weighted) |
  |---|---|---|
  | HT set | 622 events, 3.2e+07 | 4 events, ≈ 216 (μμ + 3-6 jets) |
  | flat | 745 events, 7.7e+07 | 24 events, ≈ 1.1e+05 (21 μμ, 3 ee; mostly μμ + 1-4 jets) |

  Data (25 Oct): one lepton 249.3 M, two or more 18.66 M stored events.
- **e-μ 0 jets: 0 events in every file.** 95 % upper limit on the fraction of events: 3/N = 2.6e-06 … 8.6e-05 (HT),
  1.9e-06 (flat).
  - In weighted events (HT, 3 events × weight × N(sample)/N(file 0)): ≤ 7.8e+06 (HT 50-100), 2.3e+06, 4.5e+05, 5.2e+04,
    1.9e+03, 9.1e+03, 319, 31, 4.
  - The low-HT limits are far above the 90,002 eμ 0j data events, so one file cannot exclude a contribution from the
    low-HT bins. The three highest-HT bins are limited to ≤ 0.4 % of the eμ 0j data (HT 700-1000: ≤ 10 %).

### Per final state: QCD estimate vs 25 Oct MC and data (largest QCD final states; ESTIMATE)

`MC 25 Oct` is the summed-SM (13 samples, no W+jets) integral of one delivered histogram of that final state, inside the
builder's kept mass range. `data` is the number of stored data events in that final state (25 Oct production, all
masses). The two are not like for like; they only show the scale.

| final state | QCD HT set (file-0 events → weighted) | QCD flat (events → weighted) | MC 25 Oct | data 25 Oct |
|---|---|---|---:|---:|
| 1e + 1 jet | 64 → 1.5e+07 | 79 → 1.1e+07 | 1.6e+06 | 25,143,460 |
| 1μ + 1 jet | 15 → 6.8e+06 | 12 → 2.4e+07 | 1.9e+06 | 27,872,845 |
| 1μ + 2 jets | 19 → 5.4e+06 | 10 → 1.4e+07 | 6.8e+05 | 6,092,073 |
| 1e + 2 jets | 87 → 2.4e+06 | 148 → 7.7e+05 | 5.7e+05 | 5,941,531 |
| 1μ + 3 jets | 19 → 9.9e+05 | — | 2.7e+05 | 1,752,467 |
| 1μ + 1 b | 4 → 7.7e+05 | 3 → 2.3e+07 | 1.2e+05 | 2,252,827 |
| 1e + 3 jets | 105 → 5.0e+05 | 96 → 1.1e+05 | 2.2e+05 | 1,809,093 |
| 1e + 1 jet + 1 b | 17 → 3.4e+05 | — | 1.6e+05 | 826,837 |
| 1e + 2 jets + 1 b | 20 → 4.0e+04 | 45 → 9.6e+05 | 3.3e+05 | 669,348 |

The single-lepton data are 8-20 × the 25 Oct MC in these final states. W+jets (being added now) and QCD are the
expected missing pieces. The two QCD estimates differ by up to 30 × per final state because each rests on a handful of
events (e.g. 3 flat events → 2.3e+07 in 1μ + 1 b).

### Would single events dominate bins? (as the D3 check)

For the 20 heaviest union events of each sample: every histogram the event enters, its weight vs the 25 Oct MC
content of that 10 GeV bin. Bins with no 25 Oct MC are left out (they are mostly below the builder's kept mass range).

| sample | events checked | bins with MC content hit | bins where the one event > 50 % | events dominating ≥ 1 bin | worst case |
|---|---:|---:|---:|---:|---|
| HT 50-100 | 6 | 4 | 1 | 1 | μ + 2 jets, m = 157 GeV: 63 % |
| HT 100-200 | 17 | 26 | 4 | 2 | μ + 3 jets, 536 GeV: 90 % |
| HT 200-300 | 17 | 47 | 2 | 2 | e + 2 jets, 600 GeV: 86 % |
| HT 300-500 | 20 | 37 | 2 | 2 | e + 1 jet, 1,024 GeV: 94 % |
| HT 500-700 | 20 | 68 | 0 | 0 | 23 % |
| HT 700-1000 | 13 | 25 | 0 | 0 | 32 % |
| HT 1000-1500 | 20 | 32 | 2 | 2 | e + 1 jet, 1,335 GeV: 85 % |
| HT 1500-2000 | 20 | 54 | 1 | 1 | μ + 1 jet, 1,643 GeV: 87 % |
| HT 2000-∞ | 20 | 39 | 0 | 0 | 23 % |
| flat 15-7000 | 20 | 41 | **36** | **11** | e + 1 b, 475 GeV: **99.8 %** |

## B5. Cost of a full QCD production (ESTIMATE)

CPU from the probe walltimes (all events of a file are read; most fail the trigger at once): 11-116 s per file 0.
Cluster files: 12 per input file + 2 per record. Build + kept scratch scale as 1,518 per 497 input files (25 Oct build).

| set | records | files | events | CPU h | production files | build files | total |
|---|---:|---:|---:|---:|---:|---:|---:|
| HT-binned | 9 | 385 | 319.4 M | ~10 | 4,638 | ~1,180 | **~5,800** |
| flat 63168 | 1 | 27 | 19.3 M | ~0.4 | 326 | ~80 | **~400** |

Quota (lfs file count 113,597 right after the D15 submission, 7 Nov 23:12; ESTIMATE):
- the D15 outputs add ~1,000, so ~114,600;
- the build reserve becomes ~5,650 (+250 for the 83 D15 files);
- **with tier 6** (+1,300): ~121,500, **headroom ~3,500**;
- **without tier 6** (and its build share −330): ~119,900, **headroom ~5,100**.

| option | with tier 6 | without tier 6 |
|---|---|---|
| HT-binned (+5,800) | ~127,300: **does not fit** | ~125,700: **does not fit** |
| flat (+400) | ~121,900: fits | ~120,300: fits |

Ways to make room exist but need Matan's decision: archive the three A1 pinned clones (~2,380 files), or not keep the
build scratch.

## B6. Options (facts for the decision; no recommendation)

1. **Add the HT-binned set (9 records).** Closest to a standard CMS QCD estimate, with smaller per-event weights at high
   HT.
   - Does not fit the file quota as is (needs ~5,800 files: dropping tier 6 is not enough).
   - The low-HT bins (50-300) still give single events of 590-86,000 data events, so spikes remain (10 events above
     50 % of a bin).
   - Cross sections would need a review: LO, and the portal lists matching efficiency 0.1-0.2 separately. R1 uses
     total_value as is; if R1 did not hold here, yields would be 5-10 × smaller.
2. **Add the flat sample (63168).** Cheap (~400 files, < 1 CPU h). One Pythia8 sample like the ATLAS JZ setup.
   - Per-event weights up to 1.9 M data events: 11 of its 20 heaviest events would be > 50 % of a bin.
   - So its histograms would be dominated by a few events: smooth only after heavy statistical treatment.
3. **Skip QCD and document it.** No cost.
   - The README must then say that QCD multijet is missing.
   - It matters in the single-lepton + jets final states (where this probe estimates it at the scale of the data
     excess), and it is negligible in two-lepton final states and not seen in eμ 0j.
   - The lepton-enriched sets remain a later option for single-lepton final states.

Common caveats: one file per sample; mass-range cuts of the builder not applied (upper bound); no L1 prefiring weight;
the MC comparison is the 25 Oct build without W+jets.

## Method

- Inputs, all read only:
  - probe outputs `job_metadata.json` and the inclusive SQLite shards (decoded as the pipeline writes them:
    zlib + `numpy.save`);
  - portal values `qcd_probe/qcd_portal_20261107.json` (NanoAOD `distribution`, MiniAOD `cross_section`, read live 7 Nov);
  - 25 Oct delivered summed-SM ROOT file;
  - `studies/fullrun_20261025/evidence/analysis/analysis.json` (data per final state).
- Event weight: w = σ × 1000 × L × genWeight / Σw(sample), with L = 16.393 fb⁻¹ (`target_luminosity_fb`) and
  Σw(sample) = Σw(file 0) × N(sample) / N(file 0). Full-sample weighted yield = Σ_file 0 w × N(sample) / N(file 0).
- R1: the portal `total_value` already contains the matching efficiency (the convention of all registry values). For
  these QCD records this is UNVERIFIED; the portal lists `matching_efficiency` 0.1 or 0.2 next to it (not applied).
- The analysis was run three times. Each earlier output is kept on the cluster next to the final one:
  - `out_v1_unscaled_yield`: my bug, the full-sample yield was not scaled by N(sample)/N(file 0);
  - `out_v2`: before the bins with MC content were separated in the dominance check;
  - the final output is `out/`.
