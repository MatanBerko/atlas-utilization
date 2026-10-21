# CMS ttbar with the PR #40 multiplicity rule — test report (21 Oct 2026)

**A TEST for Maryna, not a delivery.** Upstream PR #40 ("Fix event multiplicity", commit
`c2488b7`) is NOT merged. The CMS production code is unchanged. The rule is applied only by
the optional builder switch `--multiplicity-rule pr40`. All numbers below are **VERIFIED BY
RUNNING** (cluster jobs listed in `HANDOFF.md`) unless marked otherwise.

- Sample: CMS TTTo2L2Nu MC, CERN Open Data record **67801**, **49/49 files**, ONE fresh
  production (array `5266327[]`, commit `ecdf59c`). 43,546,000 events read; 25,076,583 events
  pass the CMS selection (leptons + b-jets ≤ 4).
- Builds from that same production. All use `--records 67801 --output-mode per-sample` with
  every other option at its default (peak-scope combined, peak-on weighted, min-events-basis
  raw, ≥ 100 events, b-tag 0.2489):
  - (a) `--multiplicity-rule exact`
  - (b) `--multiplicity-rule pr40`
  - (c) the unmodified builder at `cd22aa2`

## Result in one line

**Exact rule: 3,606 histograms in 169 final states. PR #40 rule: 302 histograms in 48 final
states. All seven rule checks pass.** The exact build is bit-for-bit identical to the
unmodified builder.

## Histogram counts

| | exact (current CMS rule) | PR #40 rule |
|---|---:|---:|
| histograms | **3,606** | **302** |
| final states with histograms | 169 | 48 |
| final states after the ≥ 100 rule (incl. single-object ones, which have no mass histogram) | 171 | 50 |
| final states before the ≥ 100 rule | 275 | 55 |
| final states removed by the ≥ 100 rule | 104 | 5 |

The two single-object final states that pass the cut but have no histogram (a mass needs ≥ 2
objects) are `0e_1m_0j_0b` and `1e_0m_0j_0b`.

(a) == (c), bit for bit: the same 3,606 names, and every bin content and variance (flow
included, 3,613,212 bins) is byte-identical, together with the edges, titles and entry counts
(`evidence/compare_exact_vs_base.json`). So the new switch, left at its default, changes nothing.

## Rule checks (`evidence/rule_check.json`, `evidence/oracle_result.json`)

| | check | result |
|---|---|---|
| R1 | every final state has e+m+b ≤ 4 and e+m+j+b ≤ 4 | **PASS** (48/48) |
| R2 | every final state equals Maryna's `limit_particles_in_fs` (c2488b7) of each exact label merged into it | **PASS** (48/48). Her own code, run separately from an archive of c2488b7, agrees with ours on **275/275** production labels, **6,657/6,657** stored (label, combination) pairs and 3,606/3,606 exact-build histogram names, plus 455/455 grid labels and 84,630/84,630 grid pairs |
| R3 | no histogram uses a jet rank ≥ its label's jet count | **PASS** (302/302) |
| R4 | every final state has ≥ 100 raw MC events after merging | **PASS** (smallest kept: 126; the removed set is exactly the states below 100) |
| R5 | names in exactly the exact build's format, e.g. `ROI_mass_m0j0j1_cat_0ex_1mx_2jx_1bx_width_10.0`; TH1D; same 1,000-bin grid | **PASS** (both builds; all 302 PR #40 names also occur in the exact build) |
| R6 | events conserved, only regrouped | **PASS**, see below |
| R7 | no NaN/inf, no negative variances | **PASS** (0 and 0 in both builds). For information only: exact has 246 negative bins and PR #40 has 36 (MC negative weights, not fixed — that choice is Maryna's) |

**R6 in numbers.** Raw events are what the ≥ 100 rule counts. The weighted yield is the sum
of the per-event weights; it is taken over each label's reference combination, so each event
is counted once.

| | final states | raw events | weighted yield | weighted yield, five-flag union |
|---|---:|---:|---:|---:|
| exact, before the ≥ 100 rule | 275 | 25,076,583 | 805,672.2086 | 788,275.6178 |
| PR #40, before the ≥ 100 rule | 55 | 25,076,583 | 805,672.2086 | 788,275.6178 |
| exact, after | 171 | 25,074,750 | 805,613.99 | 788,217.84 |
| PR #40, after | 50 | 25,076,525 | 805,670.32 | 788,273.73 |

- Before the cut the totals are identical. The weighted yields agree to a relative 4×10⁻¹⁶
  (float round-off), and every PR #40 final state equals the sum of its exact labels.
- After the cut, PR #40 keeps 1,775 more raw events: those of the 90 exact labels that were
  below 100 on their own.

## What the ≥ 100 rule does differently because of the regrouping

- **Final states gained:** none. Every PR #40 final state contains at least one exact label
  that already survives in the exact build.
- **Exact labels rescued:** **90** exact labels had < 100 events and were dropped in the exact
  build. They are now merged into a surviving PR #40 final state, carrying 1,775 raw events
  between them. They are mostly high light-jet multiplicities, e.g. `0e_1m_9j_2b` (65) and
  `0e_1m_12j_1b` (1) (list in `rule_check.json`).
- **Final states removed by the rule in PR #40:** 5, all 4-lepton states with no jets, which
  the rule does not change and which were below 100 in the exact build too: `0e_4m_0j_0b`
  (17), `1e_3m_0j_0b` (25), `2e_2m_0j_0b` (10), `3e_1m_0j_0b` (5), `4e_0m_0j_0b` (1).
- **Exact final states lost because of the regrouping:** none observed.
- **Unchanged final states** (made of one exact label only): 23 final states, 67 histograms,
  all **bit-for-bit identical** between the two builds.

## PR #40 final states (raw events before the ≥ 100 rule; the 48 with histograms)

| # | PR #40 final state | raw events | histograms | exact labels merged in (raw events; † = below 100, so no histograms in the exact build) |
|---:|---|---:|---:|---|
| 1 | `0e_1m_1j_2b` | 2,152,674 | 11 | 0e_1m_1j_2b (1,224,790), 0e_1m_2j_2b (604,337), 0e_1m_3j_2b (226,684), 0e_1m_4j_2b (70,830), 0e_1m_5j_2b (19,493), 0e_1m_6j_2b (4,942), 0e_1m_7j_2b (1,229), 0e_1m_8j_2b (286), 0e_1m_9j_2b (65 †), 0e_1m_10j_2b (16 †), 0e_1m_11j_2b (2 †) |
| 2 | `0e_1m_2j_1b` | 1,969,066 | 11 | 0e_1m_2j_1b (1,208,942), 0e_1m_3j_1b (516,348), 0e_1m_4j_1b (174,900), 0e_1m_5j_1b (51,180), 0e_1m_6j_1b (13,443), 0e_1m_7j_1b (3,269), 0e_1m_8j_1b (746), 0e_1m_9j_1b (185), 0e_1m_10j_1b (40 †), 0e_1m_11j_1b (12 †), 0e_1m_12j_1b (1 †) |
| 3 | `0e_1m_1j_1b` | 1,790,002 | 4 | itself only (unchanged) |
| 4 | `1e_0m_1j_2b` | 1,584,836 | 11 | 1e_0m_1j_2b (893,812), 1e_0m_2j_2b (448,033), 1e_0m_3j_2b (169,215), 1e_0m_4j_2b (53,630), 1e_0m_5j_2b (15,106), 1e_0m_6j_2b (3,808), 1e_0m_7j_2b (958), 1e_0m_8j_2b (230), 1e_0m_9j_2b (33 †), 1e_0m_10j_2b (5 †), 1e_0m_11j_2b (3 †), 1e_0m_12j_2b (3 †) |
| 5 | `1e_0m_2j_1b` | 1,473,000 | 11 | 1e_0m_2j_1b (899,305), 1e_0m_3j_1b (387,850), 1e_0m_4j_1b (133,058), 1e_0m_5j_1b (39,229), 1e_0m_6j_1b (10,258), 1e_0m_7j_1b (2,541), 1e_0m_8j_1b (600), 1e_0m_9j_1b (125), 1e_0m_10j_1b (29 †), 1e_0m_11j_1b (4 †), 1e_0m_12j_1b (1 †) |
| 6 | `1e_0m_1j_1b` | 1,325,813 | 4 | itself only (unchanged) |
| 7 | `0e_1m_0j_2b` | 1,218,558 | 4 | itself only (unchanged) |
| 8 | `1e_1m_1j_1b` | 1,214,892 | 11 | 1e_1m_1j_1b (703,032), 1e_1m_2j_1b (340,098), 1e_1m_3j_1b (122,527), 1e_1m_4j_1b (36,511), 1e_1m_5j_1b (9,687), 1e_1m_6j_1b (2,323), 1e_1m_7j_1b (567), 1e_1m_8j_1b (123), 1e_1m_9j_1b (18 †), 1e_1m_10j_1b (4 †), 1e_1m_11j_1b (2 †) |
| 9 | `1e_1m_0j_2b` | 1,195,406 | 11 | 1e_1m_0j_2b (615,087), 1e_1m_1j_2b (367,363), 1e_1m_2j_2b (147,515), 1e_1m_3j_2b (47,903), 1e_1m_4j_2b (13,095), 1e_1m_5j_2b (3,364), 1e_1m_6j_2b (856), 1e_1m_7j_2b (177), 1e_1m_8j_2b (37 †), 1e_1m_9j_2b (7 †), 1e_1m_10j_2b (2 †) |
| 10 | `0e_1m_0j_1b` | 1,087,675 | 1 | itself only (unchanged) |
| 11 | `1e_0m_0j_2b` | 880,332 | 4 | itself only (unchanged) |
| 12 | `1e_0m_0j_1b` | 797,233 | 1 | itself only (unchanged) |
| 13 | `0e_2m_1j_1b` | 720,391 | 11 | 0e_2m_1j_1b (418,092), 0e_2m_2j_1b (201,841), 0e_2m_3j_1b (72,025), 0e_2m_4j_1b (21,139), 0e_2m_5j_1b (5,560), 0e_2m_6j_1b (1,358), 0e_2m_7j_1b (303), 0e_2m_8j_1b (58 †), 0e_2m_9j_1b (11 †), 0e_2m_10j_1b (4 †) |
| 14 | `0e_2m_0j_2b` | 713,697 | 11 | 0e_2m_0j_2b (370,229), 0e_2m_1j_2b (217,468), 0e_2m_2j_2b (87,747), 0e_2m_3j_2b (27,953), 0e_2m_4j_2b (7,708), 0e_2m_5j_2b (2,000), 0e_2m_6j_2b (456), 0e_2m_7j_2b (111), 0e_2m_8j_2b (18 †), 0e_2m_9j_2b (5 †), 0e_2m_10j_2b (1 †), 0e_2m_11j_2b (1 †) |
| 15 | `1e_1m_0j_1b` | 582,999 | 4 | itself only (unchanged) |
| 16 | `0e_1m_1j_0b` | 566,732 | 1 | itself only (unchanged) |
| 17 | `0e_1m_2j_0b` | 528,848 | 4 | itself only (unchanged) |
| 18 | `2e_0m_1j_1b` | 509,841 | 11 | 2e_0m_1j_1b (294,725), 2e_0m_2j_1b (142,534), 2e_0m_3j_1b (51,434), 2e_0m_4j_1b (15,759), 2e_0m_5j_1b (4,087), 2e_0m_6j_1b (1,022), 2e_0m_7j_1b (220), 2e_0m_8j_1b (46 †), 2e_0m_9j_1b (10 †), 2e_0m_10j_1b (4 †) |
| 19 | `2e_0m_0j_2b` | 498,273 | 11 | 2e_0m_0j_2b (255,947), 2e_0m_1j_2b (152,043), 2e_0m_2j_2b (62,526), 2e_0m_3j_2b (20,271), 2e_0m_4j_2b (5,607), 2e_0m_5j_2b (1,453), 2e_0m_6j_2b (321), 2e_0m_7j_2b (85 †), 2e_0m_8j_2b (15 †), 2e_0m_9j_2b (3 †), 2e_0m_10j_2b (1 †), 2e_0m_11j_2b (1 †) |
| 20 | `0e_1m_3j_0b` | 438,496 | 6 | 0e_1m_3j_0b (282,918), 0e_1m_4j_0b (108,433), 0e_1m_5j_0b (34,433), 0e_1m_6j_0b (9,656), 0e_1m_7j_0b (2,324), 0e_1m_8j_0b (561), 0e_1m_9j_0b (138), 0e_1m_10j_0b (23 †), 0e_1m_11j_0b (8 †), 0e_1m_12j_0b (2 †) |
| 21 | `1e_0m_1j_0b` | 424,547 | 1 | itself only (unchanged) |
| 22 | `1e_0m_2j_0b` | 397,813 | 4 | itself only (unchanged) |
| 23 | `0e_2m_0j_1b` | 348,009 | 4 | itself only (unchanged) |
| 24 | `1e_0m_3j_0b` | 333,222 | 6 | 1e_0m_3j_0b (214,291), 1e_0m_4j_0b (82,752), 1e_0m_5j_0b (26,250), 1e_0m_6j_0b (7,364), 1e_0m_7j_0b (1,939), 1e_0m_8j_0b (467), 1e_0m_9j_0b (116), 1e_0m_10j_0b (35 †), 1e_0m_11j_0b (7 †), 1e_0m_12j_0b (1 †) |
| 25 | `1e_1m_2j_0b` | 287,708 | 11 | 1e_1m_2j_0b (178,170), 1e_1m_3j_0b (75,144), 1e_1m_4j_0b (25,007), 1e_1m_5j_0b (7,102), 1e_1m_6j_0b (1,721), 1e_1m_7j_0b (443), 1e_1m_8j_0b (91 †), 1e_1m_9j_0b (19 †), 1e_1m_10j_0b (10 †), 1e_1m_11j_0b (1 †) |
| 26 | `1e_1m_1j_0b` | 245,706 | 4 | itself only (unchanged) |
| 27 | `2e_0m_0j_1b` | 241,674 | 4 | itself only (unchanged) |
| 28 | `0e_1m_0j_3b` | 169,170 | 6 | 0e_1m_0j_3b (62,187), 0e_1m_1j_3b (56,860), 0e_1m_2j_3b (30,956), 0e_1m_3j_3b (12,917), 0e_1m_4j_3b (4,422), 0e_1m_5j_3b (1,344), 0e_1m_6j_3b (362), 0e_1m_7j_3b (89 †), 0e_1m_8j_3b (25 †), 0e_1m_9j_3b (7 †), 0e_1m_10j_3b (1 †) |
| 29 | `0e_2m_2j_0b` | 168,402 | 11 | 0e_2m_2j_0b (104,385), 0e_2m_3j_0b (44,114), 0e_2m_4j_0b (14,426), 0e_2m_5j_0b (4,090), 0e_2m_6j_0b (1,083), 0e_2m_7j_0b (235), 0e_2m_8j_0b (60 †), 0e_2m_9j_0b (9 †) |
| 30 | `0e_2m_1j_0b` | 145,188 | 4 | itself only (unchanged) |
| 31 | `1e_1m_0j_0b` | 129,471 | 1 | itself only (unchanged) |
| 32 | `1e_0m_0j_3b` | 124,985 | 6 | 1e_0m_0j_3b (45,022), 1e_0m_1j_3b (42,090), 1e_0m_2j_3b (23,144), 1e_0m_3j_3b (9,829), 1e_0m_4j_3b (3,480), 1e_0m_5j_3b (1,017), 1e_0m_6j_3b (302), 1e_0m_7j_3b (79 †), 1e_0m_8j_3b (17 †), 1e_0m_9j_3b (4 †), 1e_0m_10j_3b (1 †) |
| 33 | `2e_0m_2j_0b` | 122,244 | 11 | 2e_0m_2j_0b (75,728), 2e_0m_3j_0b (31,902), 2e_0m_4j_0b (10,668), 2e_0m_5j_0b (3,015), 2e_0m_6j_0b (708), 2e_0m_7j_0b (175), 2e_0m_8j_0b (39 †), 2e_0m_9j_0b (9 †) |
| 34 | `2e_0m_1j_0b` | 104,075 | 4 | itself only (unchanged) |
| 35 | `0e_2m_0j_0b` | 77,421 | 1 | itself only (unchanged) |
| 36 | `2e_0m_0j_0b` | 53,901 | 1 | itself only (unchanged) |
| 37 | `1e_2m_0j_1b` | 4,744 | 11 | 1e_2m_0j_1b (2,569), 1e_2m_1j_1b (1,366), 1e_2m_2j_1b (597), 1e_2m_3j_1b (158), 1e_2m_4j_1b (39 †), 1e_2m_5j_1b (9 †), 1e_2m_6j_1b (5 †), 1e_2m_8j_1b (1 †) |
| 38 | `2e_1m_0j_1b` | 3,261 | 11 | 2e_1m_0j_1b (1,668), 2e_1m_1j_1b (980), 2e_1m_2j_1b (398), 2e_1m_3j_1b (152), 2e_1m_4j_1b (48 †), 2e_1m_5j_1b (12 †), 2e_1m_6j_1b (2 †), 2e_1m_9j_1b (1 †) |
| 39 | `0e_3m_0j_1b` | 2,390 | 6 | 0e_3m_0j_1b (1,290), 0e_3m_1j_1b (755), 0e_3m_2j_1b (244), 0e_3m_3j_1b (77 †), 0e_3m_4j_1b (18 †), 0e_3m_5j_1b (5 †), 0e_3m_6j_1b (1 †) |
| 40 | `1e_2m_1j_0b` | 2,169 | 11 | 1e_2m_1j_0b (1,288), 1e_2m_2j_0b (594), 1e_2m_3j_0b (198), 1e_2m_4j_0b (65 †), 1e_2m_5j_0b (18 †), 1e_2m_6j_0b (6 †) |
| 41 | `2e_1m_1j_0b` | 1,538 | 11 | 2e_1m_1j_0b (909), 2e_1m_2j_0b (422), 2e_1m_3j_0b (140), 2e_1m_4j_0b (48 †), 2e_1m_5j_0b (14 †), 2e_1m_6j_0b (3 †), 2e_1m_7j_0b (2 †) |
| 42 | `1e_2m_0j_0b` | 1,275 | 4 | itself only (unchanged) |
| 43 | `0e_3m_1j_0b` | 1,135 | 6 | 0e_3m_1j_0b (676), 0e_3m_2j_0b (338), 0e_3m_3j_0b (75 †), 0e_3m_4j_0b (37 †), 0e_3m_5j_0b (5 †), 0e_3m_6j_0b (1 †), 0e_3m_7j_0b (2 †), 0e_3m_10j_0b (1 †) |
| 44 | `2e_1m_0j_0b` | 769 | 4 | itself only (unchanged) |
| 45 | `3e_0m_0j_1b` | 728 | 6 | 3e_0m_0j_1b (340), 3e_0m_1j_1b (229), 3e_0m_2j_1b (102), 3e_0m_3j_1b (39 †), 3e_0m_4j_1b (11 †), 3e_0m_5j_1b (6 †), 3e_0m_8j_1b (1 †) |
| 46 | `0e_3m_0j_0b` | 566 | 2 | itself only (unchanged) |
| 47 | `3e_0m_1j_0b` | 335 | 6 | 3e_0m_1j_0b (196), 3e_0m_2j_0b (93 †), 3e_0m_3j_0b (31 †), 3e_0m_4j_0b (9 †), 3e_0m_5j_0b (5 †), 3e_0m_6j_0b (1 †) |
| 48 | `3e_0m_0j_0b` | 126 | 2 | itself only (unchanged) |

## Plots (`plots/`)

1. `1_histograms_per_final_state.png`: histograms per PR #40 final state, PR #40 against the
   sum over its exact labels in the exact build.
2. `2_raw_events_per_final_state.png`: raw events per final state, PR #40 against its exact
   labels that survive in the exact build (log scale).
3. `3_merged_1.png` … `3_merged_4.png`: four PR #40 histograms where merging happened, with the
   contributing exact-label histograms stacked. Each exact histogram has its own peak cut, so
   the stack need not equal the PR #40 line exactly; exact labels below 100 events have no
   exact histogram, and their names are printed under the plot.
4. `4_unchanged.png`: `mass_m0j0b0_cat_0ex_1mx_1jx_1bx`, which the rule does not change. Exact
   and PR #40 coincide (identical bin by bin).

## How the rule is applied, and the one caveat

Upstream #40 caps the label when it is created. Here the same cap is applied when the
histograms are built, before the ≥ 100 rule:
- every exact label is mapped to its capped label;
- combinations the capped label does not contain (a jet rank ≥ the capped jet count) are dropped;
- the masses and all per-event siblings (weights included) of exact labels that land on the
  same final state + combination are merged.

Before writing the code, this was checked to be equivalent to #40, by reading the code and on
real shards:
- each event has exactly one exact label;
- every label stores every combination it allows;
- every combination holds one entry per event, built from the leading-pT objects;
- in this production no signature was subsampled and no combination was skipped.

The single difference from #40 is the **order** of the entries inside a merged array. That can
change a weighted bin sum only by float64 round-off (the sparse-peak-tie effect accepted on
17 Oct, `cms_mc_weights_v3/fullrun_prep/FINDING_PEAK_TIES.md`).

## Not comparable with ATLAS

Maryna's 366 histograms are ATLAS ttbar, so they are not directly comparable: a different
experiment, sample, luminosity, b-tag and object selection.
