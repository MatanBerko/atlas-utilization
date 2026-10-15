# Jet–lepton overlap: CMS one-step vs ATLAS #32 two-step

*Read-only measurement, 15 Oct 2026, on the 8 files of the 14 Oct rebuild
validation (2 each of DoubleMuon, SingleMuon, DoubleEG and MuonEG,
17,203,762 events read). Nothing in the production path changed. All numbers
below are VERIFIED BY RUNNING. The source for each is
`results/overlap_results.json`.*

## In plain words

When CMS reconstructs a muon or an electron, the same particle is very often
*also* reconstructed as a "jet" sitting right on top of it. Some rule must
remove the duplicate.

- **Today (CMS one-step, "V1")** removes every jet within 0.4 of a selected
  lepton. Leptons are never removed.
- **The ATLAS convention of upstream #32 ("V2")** works in two steps. It
  removes jets within 0.2 of a lepton. Then it removes any *lepton* within 0.4
  of a jet that survived.

**For light jets, the two rules give practically the same result on CMS
data.**
- Almost every duplicate jet sits within 0.2 of its lepton, and is removed by
  both rules. The median distance is 0.012.
- The zone the rules disagree about, between 0.2 and 0.4, is almost empty:
  98 jets out of 4,056,370. The lepton isolation already in the CMS selection
  rejects leptons with a real jet that close.
- So V2 changes the category of **75 of 2,523,951** delivered events (0.003%).
- It removes **107 leptons** out of 3.38 million. Every one of them passed the
  full CMS selection and was matched to the trigger.

**The difference that matters is the b-jets.** #32 does not clean b-jets at
all. If CMS followed that ("V2u"), b-tagged copies of the leptons would stay
in the event:
- **79,597 events (3.2%)** would change category;
- categories with b-jets would grow 1.3× to 2.9×. For example `0e_1m_1j_1b`
  would go from 12,983 to 37,785 events.

That is a b-jet policy question (Maryna is looking at it), not a 0.2-vs-0.4
question.

## Method

- **Same events as production.** Golden JSON, own trigger, muons, electrons,
  the CMS e–μ rule and the four-dataset trigger-matched acceptance are all
  the production's own functions (`run_dataset_on_file.py`, `selection.py`),
  imported, not copied.
- **The variants:**
  - **V0** is `select_and_split_jets(..., apply_lepton_cleaning=False)`.
  - **V1** is the production call exactly. It cleans against the electrons
    *before* the e–μ rule, as production does.
  - **V2** is upstream's unmodified `apply_overlap_removal(cuts={"e_mu_dr": 0.0})`,
    applied to Electrons (after our e–μ rule), Muons and Jets (the V0 light
    jets). b-jets are taken CMS-cleaned (V2) or uncleaned (V2u).
  - NanoAOD has no `NumTrkPt500`, so the μ–jet step falls back to the
    distance-only rule, as upstream documents.
- **Check against production.** For all 8 files, V1's per-category event
  counts (inclusive and exclusive) are **identical** to the production output
  for the same files (`production_check_V1`).
- **Order relative to trigger matching.** Upstream applies trigger matching
  first, then overlap removal (`parsing_handler.py`). That is order A, used
  throughout. With the order reversed (order B, acceptance re-evaluated after
  #32), **97** of 2,649,809 accepted events lose their acceptance.

## a. The September number (V0, leading jet)

Population: golden JSON plus own trigger, with ≥ 2 selected leptons of the
flavour shown and ≥ 1 V0 jet.

| dataset | population | events | lead jet within 0.4 of a muon | lead jet within 0.4 of an electron | median ΔR |
|---|---|---:|---:|---:|---:|
| DoubleMuon | ≥ 2 μ | 464,060 | **94.9%** | 0.01% | 0.0116 (to μ) |
| SingleMuon | ≥ 2 μ | 129,822 | 94.9% | 0.01% | 0.0116 (to μ) |
| DoubleEG | ≥ 2 e | 147,274 | 0.0% | **94.6%** | 0.0114 (to e) |
| MuonEG | ≥ 2 μ | 1,608 | 72.7% | 1.7% | 0.0147 (to μ) |
| MuonEG | ≥ 2 e | 499 | 3.2% | 75.8% | 0.0132 (to e) |
| all accepted | ≥ 2 leptons, any flavour | 728,328 | 77.8% | 16.6% | 0.0118 (to nearest lepton) |

- **September reference for DoubleMuon:** 92.7%, median 0.013. We get 94.9%
  and 0.0116.
- **Why the difference is likely small and expected (UNVERIFIED):**
  - September used the whole of records 30522 and 30555; this study uses 2
    files.
  - Jet |η| < 2.5 here (the production cut).
- Light jets only: 95.3% for DoubleMuon.

## b. ΔR(jet, nearest selected lepton), all V0 jets, accepted events

| dataset | V0 jets | ΔR < 0.2 | 0.2 ≤ ΔR < 0.4 |
|---|---:|---:|---:|
| DoubleMuon | 996,901 | 869,500 | 8 |
| SingleMuon | 2,762,694 | 2,032,854 | 51 |
| DoubleEG | 264,572 | 232,762 | 21 |
| MuonEG | 32,203 | 17,255 | 18 |
| **combined** | **4,056,370** | **3,152,371** | **98** |

- In the combined row, the 98 jets in 0.2–0.4 split into 59 nearest a muon
  and 39 nearest an electron.
- Light jets: 3,071,664 below 0.2 and 76 in 0.2–0.4.
- b-jets: 80,707 below 0.2 and 22 in 0.2–0.4.
- Histogram (0–1.0 in 0.02 bins): `per_group.<dataset>.b.all.hist_dr_nearest_lepton`, and Plot 1.

## c. What V2 removes (accepted events, all 8 files)

| | count | of |
|---|---:|---:|
| light jets removed by the 0.2 steps | 3,071,664 (79.1%) | 3,882,596 V0 light jets |
| … of which within 0.2 of a muon / an electron | 2,830,139 / 241,551 | (26 within 0.2 of both) |
| muons removed by the 0.4 step | **50** | 3,123,170 |
| electrons removed by the 0.4 step | **57** | 259,843 |
| events losing ≥ 1 lepton | **107 (0.004%)** | 2,649,809 |

Leptons removed per dataset:

| dataset | muons | electrons | events affected |
|---|---:|---:|---|
| DoubleMuon | 6 | 0 | 6 of 466,810 |
| SingleMuon | 44 | 8 | 52 of 2,049,656 |
| DoubleEG | 0 | 17 | 17 of 124,245 |
| MuonEG | 0 | 32 | 32 of 9,098 (0.35%) |

**Are these good leptons? Yes, all of them, by construction.** #32 only
removes leptons that already passed the full CMS selection (ID and
isolation). In addition:
- all 107 are matched to a trigger object;
- of the muons, 34 have isolation below 0.06 and 16 between 0.06 and 0.15;
- of the electrons, 43 pass the *tight* cut-based ID and 14 medium.

Plot 3 shows them against pT: they sit at low pT, mostly 25–60 GeV.

## d. Residual contamination (accepted events, leading jet)

| variant | events with a jet | lead jet within 0.4 of a surviving lepton | … of an originally selected lepton |
|---|---:|---:|---:|
| V0 | 2,542,269 | 2,265,515 (89.1%) | 2,265,515 |
| V1 | 656,390 | **0 (confirmed)** | 0 |
| V2 | 656,417 | **0** | 57 |
| V2u | 693,683 | **57,019 (8.2%)** | 57,076 |

- **V1 is 0 by construction, as expected.**
- **V2's 57** are jets whose lepton was removed instead of the jet.
- **V2u's 57,019** are uncleaned b-jets that are the lepton itself.

## e. Categories (delivered set: DoubleMuon inclusive + the other three exclusive, 2,523,951 events)

**Events changing category, V1 → V2:** **75** in order A, 76 in order B.
The most common moves are a lepton turning into a jet:
- `0e_1m_0j_0b → 0e_0m_1j_0b` (16);
- `0e_1m_1j_0b → 0e_0m_2j_0b` (15).

**Events changing category, V1 → V2u:** **79,597**, almost all gaining a b-jet:
- `0e_1m_0j_0b → 0e_1m_0j_1b` (32,925);
- `0e_1m_1j_0b → 0e_1m_1j_1b` (26,701).

The 20 most-populated categories:

| category | V1 | V2 | V2u | V2/V1 | V2u/V1 |
|---|---:|---:|---:|---:|---:|
| 0e_1m_0j_0b | 1,413,821 | 1,413,806 | 1,380,881 | 1.0000 | 0.977 |
| 0e_2m_0j_0b | 382,280 | 382,275 | 379,947 | 1.0000 | 0.994 |
| 0e_1m_1j_0b | 347,422 | 347,412 | 320,711 | 1.0000 | 0.923 |
| 2e_0m_0j_0b | 100,971 | 100,968 | 99,740 | 1.0000 | 0.988 |
| 0e_1m_2j_0b | 75,704 | 75,697 | 70,719 | 0.9999 | 0.934 |
| 0e_2m_1j_0b | 67,244 | 67,244 | 66,680 | 1.0000 | 0.992 |
| 0e_1m_0j_1b | 26,845 | 26,845 | 54,173 | 1.0000 | 2.018 |
| 0e_1m_3j_0b | 17,083 | 17,083 | 16,054 | 1.0000 | 0.940 |
| 2e_0m_1j_0b | 15,792 | 15,787 | 15,620 | 0.9997 | 0.989 |
| 0e_2m_2j_0b | 15,137 | 15,137 | 15,004 | 1.0000 | 0.991 |
| 0e_1m_1j_1b | 12,983 | 12,984 | 37,785 | 1.0001 | 2.910 |
| 0e_1m_2j_1b | 6,141 | 6,144 | 10,552 | 1.0005 | 1.718 |
| 0e_2m_0j_1b | 5,234 | 5,234 | 7,424 | 1.0000 | 1.418 |
| 0e_1m_4j_0b | 3,895 | 3,895 | 3,673 | 1.0000 | 0.943 |
| 2e_0m_2j_0b | 3,756 | 3,752 | 3,702 | 0.9989 | 0.986 |
| 0e_2m_3j_0b | 3,335 | 3,335 | 3,283 | 1.0000 | 0.984 |
| 0e_1m_3j_1b | 2,759 | 2,759 | 3,649 | 1.0000 | 1.323 |
| 0e_2m_1j_1b | 2,685 | 2,684 | 3,186 | 0.9996 | 1.187 |
| 0e_1m_1j_2b | 2,356 | 2,356 | 4,179 | 1.0000 | 1.774 |
| 0e_1m_2j_2b | 2,003 | 2,004 | 2,536 | 1.0005 | 1.266 |

## Plots

| file | what it shows |
|---|---|
| `results/plots/plot1_dr_jet_nearest_lepton_V0.png` | ΔR distribution per channel, lines at 0.2 and 0.4 |
| `results/plots/plot2_jet_multiplicity_V0_V1_V2.png` | light-jet multiplicity V0 / V1 / V2 |
| `results/plots/plot3_leptons_removed_vs_pt.png` | leptons removed by the 0.4 step vs pT |
| `results/plots/plot4_category_yields_V1_vs_V2.png` | top-20 categories V1 vs V2 (and V2u), ratio panel |

## Caveats and choices

- **The production's own ordering.** It cleans jets against the electrons
  *before* the e–μ rule. V1 keeps that. V2 uses the electrons after the e–μ
  rule, as the task specified.
- **"Combined"** in parts a–d is the sum of the 8 files, each with its own
  accepted events. Part e uses the de-duplicated delivered set.
- **Statistics.** These are 2 files per dataset, a small part of the full
  delivery. The counts of removed leptons (tens) carry about 10–15%
  statistical uncertainty.
- **The μ–jet track condition** of #32 cannot be applied to NanoAOD, which has
  no `NumTrkPt500`. That condition would only *keep* more jets near muons.
