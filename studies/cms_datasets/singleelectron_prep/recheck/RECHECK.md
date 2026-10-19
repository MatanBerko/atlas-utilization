# SingleElectron re-check and b-tag 0.2598 → 0.25 measurement (19 Oct 2026)

**Measurement only.** Nothing in production was changed, no default was
changed, no threshold or working point was chosen, nothing was delivered.
Every number is labelled **VERIFIED BY RUNNING** (it comes from a job or
script that was run here, and the evidence file is named) or **UNVERIFIED**
(a projection or an inference).

Branch `study/singleelectron-btag-recheck-20261019`. Jobs ran from the pinned
checkout `checkouts/serecheck_20261019/study` @ `0796e98` (MC driver:
`checkouts/serecheck_20261019/mcdriver` @ `294ee59`, the MC full-run commit).

---

## 0. In plain words

**Did 7 Oct reproduce? Yes, exactly.** All 151 SingleElectron files were
measured again with the same script and options. Every per-file result is
identical to 7 Oct, and the threshold table is byte-identical.

**What lowering the b-tag cut from 0.2598 to 0.25 changes, in 5 lines:**

1. About **2% more jets are called b-jets** in data (9.93% → 10.15% of jets), about 1% more in MC (34.5% → 34.8%).
2. Events move **up one b-group, almost never two**. Groups with b-jets grow by 1–5%, and the 0-b group shrinks by about 0.1%.
3. **No final state appears or disappears** at the ≥100-event rule, in data, MC or SingleElectron (projected; one data final state sits exactly at the edge).
4. **The histogram count does not move.** The projection gives the same count at both cuts: data ≈1,975, MC ≈4,977–5,049, SingleElectron 561.
5. **Data and MC move in the same direction.** Data's 1b share rises a little more (+2.3%) than MC's (+1.1%).

---

## 1. Part 1A — SingleElectron at 0.2598, repeated

**What was run.** `measure_singleelectron.py` was run with the same options as
7 Oct on all 151 files: job `5249721[]`, 16 subjobs of 10 files, exit 0.
It was followed by the unchanged 7 Oct `aggregate_tnp.py` (Step B) and
`aggregate_threshold.py` (Step D), run on the login node with `nice`, the same
way as on 7 Oct.

**Result — VERIFIED BY RUNNING** (`evidence/part1A_compare_with_7oct.json`):

| check | result |
|---|---|
| per-file JSONs | **151 / 151 identical** to 7 Oct. Every key was compared; only `elapsed_sec` and `git_commit` differ, as expected. |
| Step D (`stepD_thresholds.json`) | **identical**, key by key, to the 7 Oct evidence |
| Step B (`stepB_tnp.json`) | identical, except one key: `/old_measurement_reference/file`. That key is the path of the old-measurement input file. The file is the same, but it was given from a different place, so this is not a difference in any result. |

The 7 Oct threshold table, reproduced (VERIFIED BY RUNNING):

| T (GeV) | accepted | gain (no existing dataset takes it) | FS ≥100 | new categories | projected new histograms | guard violations |
|---|---:|---:|---:|---:|---:|---:|
| 27 | 111,511,917 | 106,514,265 | 64 | 35 | 561 | 0 |
| 30 | 101,715,829 | 96,723,260 | 63 | 35 | 561 | 0 |
| 32 | 92,523,205 | 87,617,464 | 63 | 35 | 561 | 0 |
| 35 | 77,115,261 | 72,446,044 | 62 | 35 | 561 | 0 |

The efficiencies (Step B, and Step D columns (d)) are also unchanged: the
same file, key by key.

**Why Step C was not re-run.** Step C asks whether the Ele27 trigger was
prescaled. It was answered on 7 Oct in two independent ways, from the trigger
documentation and from an empirical test on the data. Nothing it depends on
has changed since then: the trigger menu, the data files and the run list are
the same. It does not depend on the b-tag either.

**Code since 7 Oct.** Fork master was rebuilt on 14 Oct, and upstream #32,
#34 and #38 (b-jets in the overlap removal) have been merged into it since.
The measurement script and its helpers are unchanged since `8670f8f`. Some
shared modules did change, but the results are identical, so none of those
changes touch the code path used here. This is verified empirically, by the
identical outputs.

## 2. Part 1B — SingleElectron's b-dependent columns at 0.25

**What was run.** The same measurement through the study-only override (see §4)
at DeepJet 0.25, on all 151 files: job `5249809[]`, exit 0. Every log shows
`0.2598 -> 0.25`. The trigger efficiency was not recomputed, as asked.

**Result — VERIFIED BY RUNNING** (`evidence/part1B_btag_0p2598_vs_0p25.json`,
`evidence/part1B_stepD_thresholds_0p25.json`). As a check, the columns that
cannot depend on b-tag (accepted, gain, efficiencies) were asserted identical,
and they are: 0 differences.

| T | FS ≥100 | new categories | projected new histograms | Version B kept | 0b | 1b | 2b | 3b+ |
|---|---|---|---|---|---|---|---|---|
| 27 | 64 → 64 | 35 → 35 | 561 → 561 | 106,512,236 → 106,512,105 | 103,137,320 → 103,043,154 (−0.09%) | 2,918,321 → 3,003,100 (+2.9%) | 425,225 → 432,797 (+1.8%) | 31,370 → 33,054 (+5.4%) |
| 30 | 63 → 63 | 35 → 35 | 561 → 561 | 96,721,294 → 96,721,167 | 93,545,199 → 93,456,845 | 2,735,914 → 2,815,251 | 409,817 → 417,083 | 30,364 → 31,988 |
| 32 | 63 → 63 | 35 → 35 | 561 → 561 | 87,615,560 → 87,615,435 | 84,615,562 → 84,532,525 | 2,575,118 → 2,649,510 | 395,435 → 402,374 | 29,445 → 31,026 |
| 35 | 62 → 62 | 35 → 35 | 561 → 561 | 72,444,249 → 72,444,129 | 69,720,524 → 69,646,193 | 2,324,255 → 2,390,525 | 371,640 → 378,097 | 27,830 → 29,314 |

(0b … 3b+ are events of the gain, by number of b-jets, before the Version B
rule. At every T, no final state enters or leaves the ≥100 list.)

In plain words, 0.25 does not change any decision column of the threshold
table. It only moves about 94,000 of the 106.5 million new events (T=27) from
0b to 1b or more. Version B, which drops events with e+μ+b > 4, rejects
131 more events.

## 3. Part 2 — b-tag 0.2598 vs 0.25 on a sample of the deliveries

### Sample

Every 10th file by index (index % 10 == 0), with at least 1 per group:
**97 files** (`evidence/sample_files.json`).

- Data: 41 files (job `5249807[]`).
- MC: 56 files over all 13 records (job `5249808[]`).

All exited 0. Each file was run twice with the existing driver, at 0.2598 and
at 0.25.

VERIFIED BY RUNNING:

| group | files | events read | scale to full |
|---|---:|---:|---:|
| DoubleMuon | 6 / 57 | 10.7% | 9.34 |
| SingleMuon | 16 / 152 | 10.6% | 9.40 |
| DoubleEG | 14 / 133 | 9.9% | 10.09 |
| MuonEG | 5 / 48 | 14.2% | 7.04 |
| MC, 13 records | 56 / 496 (ZZ 98 of 99) | 0.4% – 23% per record | 4.3 – 252 |

The two smallest-fraction MC records are 37728 (1 of 8 files, 0.4% of its
events) and 72676 (1 of 7, 0.5%). Their scale factors are large, so their
projected numbers are the least certain.

**Validation — VERIFIED BY RUNNING.** Every sampled file's 0.2598 run
reproduces the production numbers of that same file: events after the gate,
Version B kept, and every final-state count. That is **0 failures in 97
files**. The two runs of each file contain the same events in the same order
(event-id hash), and the same e/μ/jet counts. Only the b-jet split differs.

### 3a. Fraction of jets b-tagged (VERIFIED BY RUNNING; raw)

| group | 0.2598 | 0.25 | change |
|---|---:|---:|---:|
| DoubleMuon | 9.36% | 9.57% | +2.3% |
| SingleMuon | 9.80% | 10.02% | +2.3% |
| DoubleEG | 9.33% | 9.52% | +2.0% |
| MuonEG | 46.60% | 46.92% | +0.7% |
| SingleElectron (all 151 files, Part 1B) | — | — | events 1b +2.9%, 2b +1.8% |
| MC 35631 / 35669 (DY) | 5.63% / 5.64% | 5.83% / 5.83% | +3.6% / +3.4% |
| MC 37728 / 68847 / 72676 / 72752 / 75589 (dibosons) | 4.4–6.1% | 4.6–6.4% | +2.8% … +5.3% |
| MC 64839 / 64895 (single top) | 33.2% / 33.1% | 33.5% / 33.4% | +0.9% |
| MC 67801 / 67993 (ttbar) | 48.0% / 35.1% | 48.3% / 35.4% | +0.7% / +0.8% |
| MC 68073 / 68187 (ttW / ttZ) | 30.7% / 31.5% | 30.9% / 31.8% | +0.9% |

Where real b-jets are common (ttbar, MuonEG), the extra tags are a small
relative addition. Where they are rare (Z+jets, dibosons, the muon/electron
datasets), the extra tags are mostly light jets near the cut, and the
relative change is larger. Plot: `plots/btag_fraction_jets_tagged.png`.

### 3b. Migration of events between b-groups (VERIFIED BY RUNNING, scaled to full statistics; row = at 0.2598, column = at 0.25)

Data, all 4 datasets:

| at 0.2598 \ at 0.25 | 0b | 1b | 2b | 3b+ | rejected (e+μ+b>4) |
|---|---:|---:|---:|---:|---:|
| 0b | 99.93% | 0.07% | 0.00% | 0 | 0 |
| 1b | 0 | 99.68% | 0.32% | 0.00% | 0 |
| 2b | 0 | 0 | 99.59% | 0.38% | 0.03% |
| 3b+ | 0 | 0 | 0 | 99.68% | 0.32% |

MC, all 13 records, weighted:

| at 0.2598 \ at 0.25 | 0b | 1b | 2b | 3b+ | rejected |
|---|---:|---:|---:|---:|---:|
| 0b | 99.88% | 0.12% | 0.00% | 0 | 0.00% |
| 1b | 0 | 99.31% | 0.69% | 0.00% | 0.00% |
| 2b | 0 | 0 | 99.62% | 0.37% | 0.01% |
| 3b+ | 0 | 0 | 0 | 99.69% | 0.31% |

Events only move up, almost always by one b-jet. The per-group matrices are
in `evidence/part2_btag_sample.json` (`groups.<g>.migration_raw`). Plot:
`plots/btag_migration_data_vs_mc.png`.

### 3c. Yield change per b-group (Version B kept events; VERIFIED BY RUNNING on the sample)

| group | 0b | 1b | 2b | 3b+ |
|---|---:|---:|---:|---:|
| DoubleMuon | −0.05% | +2.35% | +1.96% | — |
| SingleMuon | −0.07% | +2.31% | +1.75% | +5.37% |
| DoubleEG | −0.04% | +1.91% | +2.34% | — |
| MuonEG | −0.28% | +0.00% * | +1.08% | — |
| **data, all 4 (scaled)** | 163,330,914 → 163,215,751 (−0.07%) | 4,387,563 → 4,488,502 (+2.30%) | 651,181 → 662,707 (+1.77%) | 43,582 → 45,922 (+5.37%) |
| **MC, weighted (scaled)** | 35,842,652 → 35,800,997 (−0.12%) | 2,286,750 → 2,312,531 (+1.13%) | 1,032,449 → 1,044,317 (+1.15%) | 70,771 → 74,442 (+5.19%) |
| SingleElectron gain, T=27 (all files) | −0.09% | +2.9% | +1.8% | +5.4% |

"—" means the group is empty by construction: in the dilepton datasets, 3b+
always gives e+μ+b > 4, so Version B drops it.

\* MuonEG 1b: 3 events go in from 0b and 3 go out to 2b, in a small
sample (1,909 events). The +0.00% is real, not a missing number.

Per MC record, the yield changes are in the JSON. The large-b samples
(ttbar, single top, ttW, ttZ) lose 1–2% in 0b. Plot:
`plots/btag_yield_change_by_group.png`.

### 3d. Final states that gain or lose most (UNVERIFIED projection, sample × scale)

| | final state | 0.2598 | 0.25 | change |
|---|---|---:|---:|---:|
| data, gain | 0e_1m_0j_1b | 2,151,192 | 2,216,203 | +65,011 (+3.0%) |
| | 0e_1m_1j_1b | 1,042,696 | 1,067,189 | +24,493 (+2.3%) |
| | 0e_1m_2j_1b | 498,340 | 503,622 | +5,282 (+1.1%) |
| data, lose | 0e_1m_1j_0b | 27,612,054 | 27,547,043 | −65,011 (−0.24%) |
| | 0e_1m_2j_0b | 6,075,991 | 6,048,114 | −27,877 (−0.46%) |
| | 0e_1m_3j_0b | 1,360,044 | 1,350,401 | −9,643 (−0.71%) |
| MC, gain | 0e_1m_1j_2b | 4,415,695 | 4,470,448 | +54,753 (+1.2%) |
| | 1e_0m_1j_2b | 3,237,577 | 3,278,597 | +41,020 (+1.3%) |
| | 0e_1m_2j_2b | 4,127,754 | 4,167,521 | +39,766 (+1.0%) |
| MC, lose | 0e_1m_3j_0b | 2,199,929 | 2,158,059 | −41,870 (−1.9%) |
| | 0e_1m_2j_0b | 3,590,824 | 3,552,838 | −37,986 (−1.1%) |
| | 1e_0m_2j_0b | 3,062,020 | 3,027,902 | −34,118 (−1.1%) |

A light jet becoming a b-jet keeps the total number of jets, so the event
moves from `…Nj_0b` to `…(N−1)j_1b`. The data pair 0e_1m_1j_0b → 0e_1m_0j_1b
(±65,011) is exactly that move. Top 10 in the JSON. MC yields are weighted.

### 3e. Data vs MC: fraction of events with 1 and 2 b-jets (VERIFIED BY RUNNING on the sample, scaled)

| | data 0.2598 | data 0.25 | MC 0.2598 | MC 0.25 |
|---|---:|---:|---:|---:|
| 1b | 2.605% | 2.665% (+2.3%) | 5.829% | 5.894% (+1.1%) |
| 2b | 0.387% | 0.394% (+1.8%) | 2.632% | 2.662% (+1.2%) |
| 1b, 1 lepton | 2.641% | 2.703% | 8.640% | 8.730% |
| 1b, 2 leptons | 2.256% | 2.296% | 2.218% | 2.253% |
| 2b, 1 lepton | 0.375% | 0.381% | 4.250% | 4.299% |
| 2b, 2 leptons | 0.504% | 0.513% | 0.555% | 0.562% |

The data/MC ratio barely moves (1b: 0.447 → 0.452). 0.25 does not open or
close a data/MC gap. The large 1-lepton difference exists at both cuts. It is
mostly population: the MC numbers are all events after the MC gate, while the
data is the trigger-accepted delivery (see §3f). Plot:
`plots/btag_nb_multiplicity_data_vs_mc.png`.

### 3f. PROJECTION (UNVERIFIED): final states ≥100 and histogram counts

How it is made. Each group's final-state counts from the sample are scaled to
full statistics. Then the ≥100 raw-event rule is applied, and the 186 mass
combinations are counted per final state, with the production's own
functions. That count is an upper bound, because the real build then applies
the Z cut, the max-mass cut and peak removal. To see how good this is, the
same counting was done on the **exact** per-file counts of the real
production (VERIFIED, from production metadata) and compared with the real
deliveries.

| | FS ≥100 | histograms |
|---|---:|---:|
| **data, real delivery** | **103** | **1,975** |
| data, exact from production metadata (0.2598) | 103 (same list as delivered) | 1,975 (upper bound = real) |
| data, sample projection 0.2598 | 103 (3 borderline FS swapped) | 1,991 |
| data, sample projection **0.25** | **103** (none gained or lost) | **1,991** → calibrated **≈1,975** |
| **MC, real delivery** | **205** | **4,977** |
| MC, exact from production metadata (0.2598) | 247 | 5,718 |
| MC, sample projection 0.2598 | 247 (4 borderline FS swapped) | 5,801 |
| MC, sample projection **0.25** | **247** (none gained or lost) | **5,801** → calibrated **≈5,049** |

**How good is the projection?**

- **Data: good.** The method, applied to the exact counts, gives exactly the
  real delivery (103 / 1,975). The sample gets the number of final states
  right, but swaps 3 final states that sit near 100 events. Its histogram
  count is 0.8% high (sampling noise).
- **Data borderline (VERIFIED from production metadata).** One delivered
  final state, 3e_0m_2j_0b, has **101** events at 0.2598. A 0b final state
  loses roughly 0.1–0.5% at 0.25, so it could drop to 100 (still in) or 99
  (out); expect at most one change.

  Of the other final states near the edge, 0e_2m_5j_2b (96) and 1e_1m_6j_1b
  (90) would need +4% and +11%; the measured shifts are about 2%. So at most
  ±1 final state changes, and the histogram count stays within a few of
  1,975. UNVERIFIED.
- **MC: the final-state count cannot be compared one-to-one.** The real MC
  build keeps only events that pass one of the four data acceptance flags
  (`build_mc_delivery.py`, `event_union_mask`). The per-file metadata, and
  this sample, count all events after the MC gate, which is a larger
  population. Hence 247 instead of 205.

  The histogram calibration (real ÷ exact = 0.870) brings the sample
  projection to ≈5,049, 1.5% above the real 4,977 (sampling noise). What the
  projection does show is that 0.25 moves **no** final state across 100 in
  that larger population. The flags are about triggers and leptons, not
  b-tags. Expected effect on the real 205 / 4,977: none or ±1 final state.
  UNVERIFIED. The MC build report does not keep per-final-state counts, so
  the MC borderline could not be checked.

**Bottom line (UNVERIFIED):** at 0.25 the deliveries would keep ≈103 data
final states / ≈1,975 histograms and ≈205 MC final states / ≈4,977
histograms, each within about ±1 final state. Only a full re-run would make
these exact.

## 4. How the b-tag override works, and the proof (study only)

`recheck/btag_override_run.py` is a wrapper. It runs inside the job process,
and production code on disk is not touched:

1. It imports `studies.m0m1j0_cms.selection` and sets
   `selection.BTAG_DEEPFLAVB_MEDIUM_WP` (0.2598 or 0.25).
2. It runs the target's `main()` in the same process. The target is the
   delivery driver `run_dataset_on_file.py` or `measure_singleelectron.py`.

Why this is valid: the constant is read at call time by
`select_and_split_jets`, which applies the only b-tag cut, and no other module
copies the value. After the run, the wrapper asserts the constant still has
the requested value.

For the driver, it also observes the first `run_combination_funnel` call (all
accepted events, passed through unchanged) to save each event's e/μ/jet/b
counts and genWeight. `merge_pair.py` then lines up the two runs of a file and
stops on any mismatch.

**Proof — VERIFIED BY RUNNING** (job `5249720`,
`evidence/override_proof_{data,mc}.json`). Two files were tested, data
DoubleMuon 30522/0 and MC 35631/0. Each was run once normally and once
through the wrapper at 0.2598:

- **all 8 output shards are bit-identical**;
- `job_metadata.json` differs only in `created_utc` and `elapsed_sec`;
- the only extra file is the debug event list the study asks for.

## 5. The three questions for Maryna (REPORT §5), with today's numbers

1. **Which offline threshold?** The table in §1 is unchanged: it was
   reproduced exactly today. At T=27/30/32/35 the gain is 106.5 / 96.7 /
   87.6 / 72.4 million events.

   - Every threshold gives 35 new categories and 561 projected histograms.
   - The efficiency just above the cut is barrel 0.35 / 0.62 / 0.70 / 0.76 and endcap 0.15 / 0.37 / 0.45 / 0.55.
   - **New today:** the answer does not depend on the b-tag choice. At 0.25 the categories, final states and projected histograms are identical at every T.
2. **Confirm SingleElectron goes LAST in the priority order**
   (DoubleMuon > SingleMuon > DoubleEG > MuonEG > SingleElectron). The gain
   column still assumes it. At T=27, 106,514,265 of the 111,511,917 accepted
   events (95.5%) are taken by no existing dataset. That is unchanged.
3. **Is a never-flat, 72–83% efficient trigger acceptable for BumpNet at
   all?** This is unchanged: the trigger efficiencies were reproduced exactly,
   and they do not depend on b-tagging. It is still a physics-judgement call,
   not a measurement.

## 6. What changed since 7 Oct

- **Code.** Fork master was rebuilt (14 Oct) and synced with upstream: #32
  overlap removal, #34 high-multiplicity light jets, and #38 b-jets in the
  overlap removal. The SingleElectron measurement script is unchanged. All
  SingleElectron outputs reproduce exactly, and so do the 97 sampled delivery
  files (data: the 7 Oct production; MC: the 17 Oct full run). So nothing
  merged since affects these numbers. VERIFIED BY RUNNING.
- **Deliveries that now exist.** The data delivery has 103 final states and
  1,975 histograms (`electron_vB/evidence/D2_D3_delivery_checks.json`). The
  MC delivery (full run 17 Oct, peak fix 18 Oct) has 205 final states and
  4,977 summed histograms; ZZ uses 98 of 99 files.
- **New question: b-tag 0.25.** Measured here (Part 1B and Part 2). No
  working point is chosen.
- **The SingleElectron answers are unchanged.** The trigger is unprescaled
  (Step C, not re-run, see §1), the old measurement understated the
  efficiency, and the threshold table is unchanged.

## 7. Where everything is

- Evidence: `recheck/evidence/` — `override_proof_*.json`, `part1A_*.json`,
  `part1B_*.json`, `part2_btag_sample.json`, `sample_files.json`, and
  `production_totals.json.gz`, the per-file production numbers that were
  read (read-only).
- Plots: `recheck/plots/btag_fraction_jets_tagged.png`,
  `btag_migration_data_vs_mc.png`, `btag_nb_multiplicity_data_vs_mc.png`,
  `btag_yield_change_by_group.png`.
- Scripts: `btag_override_run.py`, `merge_pair.py`, `compare_runs.py`,
  `compare_7oct.py`, `compare_se_btag.py`, `make_sample_mapping.py`,
  `production_totals.py`, `aggregate_btag.py`, `cluster/pbs_recheck.sh`.
- Cluster outputs: `/storage/agrp/berkom/atlas-utilization/work/serecheck_20261019/`.
  The checkouts are archived as tar.gz next to themselves (see HANDOFF).
