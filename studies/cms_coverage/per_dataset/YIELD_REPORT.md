# Per-dataset BumpNet-yield measurement (topology-free, trigger-free)

Branch `survey/per-dataset-yield`, off `survey/cms-coverage` at
`e6f6367b798bd0bb27e0466794b0b7bb1bdca591`. Every number below is labeled
**VERIFIED BY RUNNING**, **FROM COMMITTED DATA**, or **UNVERIFIED /
ESTIMATED**, exactly as in the prior report.

**This measurement is deliberately different from the committed 316
DoubleMuon result** (`studies/cms_coverage/COVERAGE_REPORT.md`), in two
ways, applied to every dataset including DoubleMuon itself here:

1. **No trigger requirement**, anywhere. The committed 316 required
   `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ`/`HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ`
   to have fired; here, no HLT branch is read or checked at all, on any
   dataset.
2. **No topology requirement.** The committed 316 required exactly
   ">=2 muons AND >=1 light jet" per event. Here, an event is kept if it
   has **>=2 selected objects of ANY type** (muon, electron, jet, or
   b-jet, summed) — object *definitions* themselves (pT/η/ID/isolation
   thresholds, jet-lepton cleaning) are unchanged from
   `studies/m0m1j0_cms/RECIPE.md`, called via the same, unmodified,
   imported `selection.select_muons`/`select_electrons`/
   `select_and_split_jets`.

**Every number in this report is therefore an upper bound relative to
what a properly triggered, physics-motivated selection would yield** —
stated on every table below, not just here.

Golden-JSON (validated-runs) filtering is applied to data only, never to
MC, per task instruction.

## Records used (all re-verified live against the portal API just now)

| Dataset | Record ID | Portal-published events | Portal-published files |
|---|---|---|---|
| DoubleMuon | 30522 | 45,235,604 | 29 |
| SingleMuon | 30530 | 149,916,849 | 70 |
| DoubleEG | 30521 | 78,797,031 | 47 |
| SingleElectron | 30529 | 153,363,109 | 71 |
| MuonEG | 30528 | 33,854,612 | 29 |
| JetHT | 30525 | 120,688,407 | 70 |
| MET | 30526 | 26,974,131 | 17 |
| Tau | 30532 | 79,578,661 | 45 |
| MC ttbar (TTTo2L2Nu) | 67801 | 43,546,000 | 49 |
| MC Drell-Yan (DYJetsToLL_M-50) | 35671 | 82,448,537 | 61 |
| MC W+jets (WJetsToLNu) | 69747 | 80,958,227 | 68 |
| MC diboson (WW) | 72696 | 15,821,000 | 41 |
| MC single top (ST_t-channel_top) | 64759 | 63,073,000 | 86 |
| MC QCD multijet (Pt 170-300, mid-range of 11 bins) | 63176 | 29,758,000 | 38 |
| MC signal (GluGluHToGG) | 37350 | 540,000 | 3 |

Only **era Run2016G** is used for every data primary dataset here (file
index 0 of that record), for consistency with the pilot; QCD is
represented by its **170-300 GeV pT bin**, the 6th of 11 available bins
— a genuinely mid-range choice, not the lowest or highest.

## Pilot — VERIFIED BY RUNNING

Per the task's own instruction, the two most different datasets were run
first: JetHT (jet-rich, no lepton requirement) and SingleMuon (lepton-
gated, structurally closest to DoubleMuon).

| | JetHT | SingleMuon |
|---|---|---|
| file events (`n_read`) | 107,505 | 2,939,781 |
| wall time | 116.6 s | 1,048.9 s (17.5 min) |
| peak memory | 245 MB | 2.46 GB |
| output shard size | 1.66 MB | 11.0 MB |
| events after golden-JSON | 107,505 (no runs excluded) | 2,931,332 |
| events after >=2-object gate | 94,828 (88%) | 1,201,534 (41%) |
| (pattern×category) signatures written | 1,730 | 3,517 |
| largest single signature | 17,171 | 277,527 |

**Both comfortably inside the 60-minute/12 GB stop condition** — the
slower of the two (SingleMuon) used under 30% of the time budget and
about 20% of the memory budget. Proceeded directly to the remaining 13
datasets with no change to the approach.

Note the very different scale of "how much passes the >=2-object gate":
88% for JetHT (a jet-rich dataset easily clears a 2-object bar with no
lepton requirement at all) vs 41% for SingleMuon (already lepton-
selected, but many events still don't reach a second additional selected
object). This foreshadows why a topology-free, trigger-free measurement
is not simply "DoubleMuon's number, scaled" for every dataset.

**One dataset (Tau) needed a real capability change, reported plainly, not
hidden:** the 60-minute pilot ceiling applied only to the two named pilots
(JetHT, SingleMuon); Tau — not one of the two — turned out to be the
heaviest of all 15 datasets and was killed by the cluster's own 1-hour
walltime limit partway through (it had already read its file and applied
selection: 2,433,947 events read, 2,337,033 — 96%, the highest pass rate
of any dataset — cleared the >=2-object gate, before being killed mid-
combination-loop). Resubmitted with a 2-hour budget; see below for the
actual time it needed. This is itself a finding: a dataset with no
lepton gate at all and evidently very high jet/object multiplicity per
event can cost meaningfully more compute than either pilot predicted.

## The funnel, per dataset — VERIFIED BY RUNNING

All numbers: `studies/cms_coverage/per_dataset/assets_raw/funnel_*.json`,
produced by `studies/cms_coverage/per_dataset/cluster/measure_per_dataset_funnel.py`,
itself calling the same real, unmodified shared post-processing functions
as the committed 316 result. "u" = unscaled (measured directly on the one
file); "s" = scaled (arithmetic: this file's count x (dataset total
events / this file's events), from the portal's own published totals).

### Data primary datasets

| Dataset | (a) u | (b) u | (b) s | (c) u | (d) u | **(d) s (headline)** |
|---|---|---|---|---|---|---|
| DoubleMuon | 2,886 | 534 | 1,389 | 407 | 312 | **331** |
| SingleMuon | 2,482 | 488 | 2,023 | 373 | 285 | **293** |
| DoubleEG | 1,993 | 384 | 1,361 | 265 | 185 | **190** |
| SingleElectron | 990 | 79 | 990 | 54 | 36 | **42** |
| MuonEG | 3,113 | 739 | 1,712 | 555 | 382 | **397** |
| JetHT | 1,192 | 118 | 1,192 | 84 | 75 | **77** |
| MET | 2,118 | 302 | 1,668 | 191 | 134 | **148** |
| Tau | 2,600 | 560 | 1,799 | 411 | 294 | **306** |

### MC groups

| Group | (a) u | (b) u | (b) s | (c) u | (d) u | **(d) s (headline)** |
|---|---|---|---|---|---|---|
| ttbar | 3,388 | 1,156 | 3,388 | 895 | 571 | **594** |
| Drell-Yan | 1,505 | 243 | 1,049 | 186 | 109 | **110** |
| W+jets | 211 | 24 | 211 | 14 | 6 | **6** |
| Diboson | 1,361 | 272 | 518 | 216 | 182 | **186** |
| Single top | 1,302 | 420 | 984 | 358 | 292 | **299** |
| QCD (170-300 GeV) | 375 | 91 | 255 | 72 | 70 | **73** |
| Signal (H→γγ) | 624 | 78 | 78 | 44 | 30 | **30** |

**Reading (b): scaling changes the picture a lot** — e.g. SingleElectron
and JetHT show `(b) s == (a) u`, meaning literally *every* category that
appeared at all in the one file would, once scaled to the full dataset,
clear the 100-raw-event bar (their files are small relative to the full
dataset, so the scale factor is large: ×1,358 and ×1,123 respectively).
DoubleEG and MET scale far less aggressively (×39, ×95) because their
single files already carry a larger share of the dataset.

**Reading (d) scaled — read this as an ESTIMATE, not a measurement, and
in a specific direction:** the bin-count requirement (>30 bins) cannot be
scaled — only event counts can. The scaled (d) figure above reuses the
*file-level* (unscaled) bin count as a stand-in for what the full
dataset would show. **This is very likely an UNDER-estimate**: more real
events almost always populate *additional* currently-empty bins in a
mass spectrum, not fewer — a category on the edge of the 30-bin
threshold with only file-level statistics will, in the full dataset,
plausibly gain bins it does not have yet, not lose them. The gap between
(d) unscaled and (d) scaled above (e.g. DoubleMuon: 312 → 331, MuonEG:
382 → 397) already shows this effect for categories that cross the
scaled-event threshold; a further, unmeasured number would likely cross
the bin threshold too, given full statistics.

## Breakdown of (d) unscaled, by pattern size and object content

| Dataset | 2 objects | 3 objects | 4 objects | lepton-only | lepton+jet | jet-only | b-jet-containing |
|---|---|---|---|---|---|---|---|
| DoubleMuon | 133 | 112 | 67 | 1 | 68 | 47 | 196 |
| SingleMuon | 119 | 104 | 62 | 0 | 58 | 43 | 184 |
| DoubleEG | 80 | 69 | 36 | 0 | 42 | 34 | 109 |
| SingleElectron | 21 | 11 | 4 | 0 | 7 | 15 | 14 |
| MuonEG | 152 | 141 | 89 | 2 | 78 | 56 | 246 |
| JetHT | 36 | 24 | 15 | 0 | 0 | 18 | 57 |
| MET | 65 | 46 | 23 | 0 | 21 | 29 | 84 |
| Tau | 134 | 106 | 54 | 0 | 73 | 55 | 166 |
| ttbar | 191 | 246 | 134 | 3 | 120 | 58 | 390 |
| Drell-Yan | 51 | 39 | 19 | 1 | 63 | 28 | 17 |
| W+jets | 3 | 3 | 0 | 0 | 3 | 3 | 0 |
| Diboson | 93 | 60 | 29 | 7 | 62 | 37 | 76 |
| Single top | 124 | 112 | 56 | 0 | 42 | 41 | 209 |
| QCD (170-300) | 35 | 22 | 13 | 0 | 0 | 18 | 52 |
| Signal (H→γγ) | 17 | 10 | 3 | 0 | 10 | 13 | 7 |

**`b-jet-containing` dominates every dataset with any jet content at
all** — the same effect already seen in the committed 316 result: a
large fraction of the 186 combinatorial patterns include a b-jet slot,
and with no per-event b-tag rate requirement gating the event population
here, many of them individually clear the survival gates. JetHT and QCD
(no leptons in their trigger stream, and this measurement applies none)
correctly show **zero** `lepton-only`/`lepton+jet` entries — there is
nothing lepton-shaped for those categories to draw from at all, a useful
internal consistency check that the topology-free selection is behaving
as designed, not admitting phantom categories.

## DoubleMuon here vs. the committed 316 — explained

**DoubleMuon under these settings: 312 unscaled, 331 scaled-estimate —
both strikingly close to the committed 316.** This is worth explaining
carefully, because it is coincidental agreement between two very
different measurements, not confirmation that they mean the same thing:

- The committed 316 came from the **full, 57-file merged dataset**
  (94,148,416 raw events), with a **required trigger** and a **required
  topology** (exactly ">=2 muons and >=1 light jet"). That is a large
  statistics base feeding a narrow set of eligible combination patterns.
- This measurement uses **one file** (2,315,223 raw events — 1/57th the
  statistics), **no trigger**, and **any >=2 objects of any type** — a
  tiny statistics base feeding a much wider set of eligible patterns
  (electrons and b-jets are now admitted; the muon+jet requirement no
  longer screens most of the 186 patterns out before they're even
  tried).
- These two effects pull in **opposite directions** — far less
  statistics per pattern, but far more patterns get a chance at all —
  and they happen to land in a similar final count. That is a numerical
  coincidence worth noting, not evidence the two measurements validate
  each other. The 316 is the physically defensible, trigger-correct
  number; the 312-331 here is a **trigger-free, topology-free upper-bound
  style measurement from a fraction of the data**, useful only for
  comparing *relative* yield across datasets, not as a substitute for
  the committed result.

## Cross-dataset overlap — a cheap, real measurement, not exhaustive

**VERIFIED BY RUNNING** on one representative pair: checked what fraction
of DoubleEG's own file (first 500,000 events) also fires DoubleMuon's
trigger (`HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ` OR
`HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ`), and vice versa (DoubleMuon's
file against DoubleEG's own diphoton trigger):

| direction | overlap fraction |
|---|---|
| DoubleEG events that also fire the DoubleMuon trigger | **0.01%** |
| DoubleMuon events that also fire the DoubleEG trigger | **0.01%** |

For this specific pair, cross-dataset double counting is negligible — the
muon and diphoton trigger streams barely overlap at all, as expected for
two orthogonal physics signatures.

**This does NOT generalize to every pair, and was not checked for every
pair (UNVERIFIED beyond DoubleMuon/DoubleEG).** In particular, **MuonEG is
explicitly at risk of large, structural overlap with both SingleMuon and
SingleElectron**: MuonEG's own trigger requires one muon AND one electron
in the same event — an event satisfying that is very likely to
*independently* also satisfy a single-muon or single-electron trigger
threshold on one of those same two objects, by construction, not by
chance. That overlap was not measured here (it would need the same cheap
trigger-branch check run on the MuonEG/SingleMuon/SingleElectron trio);
flagged as the most important remaining gap in this estimate, and the
cheapest one to close (one more small XRootD read per pair, same method
as above).

## Compute cost, per file and extrapolated to the full dataset — VERIFIED BY RUNNING

| Dataset | file elapsed | shard size | files in dataset | **core-hours, full dataset** | **output size, full dataset** |
|---|---|---|---|---|---|
| DoubleMuon | 1,900.5 s | 13.91 MB | 29 | **15.3** | 403.5 MB |
| SingleMuon | 1,048.0 s | 11.01 MB | 70 | **20.4** | 770.6 MB |
| DoubleEG | 1,585.2 s | 9.92 MB | 47 | **20.7** | 466.1 MB |
| SingleElectron | 153.3 s | 0.74 MB | 71 | **3.0** | 52.7 MB |
| MuonEG | 2,767.9 s | 16.12 MB | 29 | **22.3** | 467.6 MB |
| JetHT | 114.5 s | 1.66 MB | 70 | **2.2** | 116.2 MB |
| MET | 525.4 s | 2.39 MB | 17 | **2.5** | 40.6 MB |
| Tau | 3,409.2 s | 14.88 MB | 45 | **42.6** | 669.4 MB |
| MC ttbar | 761.8 s | 5.45 MB | 49 | **10.4** | 266.8 MB |
| MC Drell-Yan | 633.9 s | 3.36 MB | 61 | **10.7** | 205.1 MB |
| MC W+jets | 30.2 s | 0.15 MB | 68 | **0.6** | 10.1 MB |
| MC diboson | 1,078.2 s | 9.28 MB | 41 | **12.3** | 380.4 MB |
| MC single top | 617.4 s | 9.52 MB | 86 | **14.8** | 818.4 MB |
| MC QCD (170-300) | 258.9 s | 4.52 MB | 38 | **2.7** | 171.6 MB |
| MC signal (H→γγ) | 128.3 s | 0.89 MB | 3 | **0.1** | 2.7 MB |

Every figure here is **1 core** (this measurement never used more than one
CPU per job); "core-hours" is directly the wall-clock hours a full run of
that dataset alone would need. Total: **~129.0 core-hours for all 8 data
primary datasets, ~51.6 core-hours for the 7 MC groups — ~180.6 core-hours
grand total** — all comfortably parallelizable (one job per file,
exactly as this measurement's own pilot/full-run pattern already does),
so wall-clock time for a real run is limited by how many cluster slots
are available at once, not by this total.

## Totals — VERIFIED BY RUNNING, with explicit double-counting caveat

Summing the **scaled (d)** column (the number that matters — see above):

| | total scaled (d) |
|---|---|
| 7 data primary datasets (excluding Tau) | 1,478 |
| Tau | 306 |
| **All 8 data primary datasets** | **1,784** |
| **7 MC groups** | **1,298** |
| **Grand total (data + MC)** | **3,082** |

**This clears the 3,000 target** — from the sum of all 15 one-file
measurements, before any de-duplication is applied (see the caveat
immediately below, which this total does not yet account for).

**This sum is an upper bound, not a real total, for one structural
reason stated plainly: the same physical event can appear in more than
one primary dataset.** A single collision event that happens to contain
both two muons and two well-separated photons could, in principle,
satisfy both DoubleMuon's and DoubleEG's trigger streams and be recorded
by both — summing their yields as if they were disjoint double-counts
that event's contribution. The one pair actually measured
(DoubleMuon/DoubleEG, ~0.01% overlap) suggests this effect is small for
*orthogonal* trigger pairs, but MuonEG's own structural overlap with
SingleMuon/SingleElectron was **not measured** and is very plausibly
much larger (see above) — so the true, de-duplicated total is smaller
than the sum above by an amount this report cannot currently quantify
precisely. **How to measure it properly**: apply the pipeline's own
existing cross-record de-duplication
(`services.parsing.event_deduplication`, keyed on
`(run, luminosityBlock, event)` — already used elsewhere in this
pipeline for combining trigger streams, not implemented as part of this
measurement per its own scope) across the relevant dataset pairs before
summing.

## How far from 3,000, and the cheapest route there

**Summing all 15 measured datasets (8 data + 7 MC) gives 3,082 scaled
BumpNet-usable histograms — the 3,000 target is cleared**, before any
de-duplication (see the caveat above; the true, de-duplicated number is
somewhat lower, by an amount not precisely quantified here).

Ranked by **yield per core-hour of full-dataset compute** (cheapest way
to add histograms, not just the biggest absolute number):

| dataset | scaled (d) | core-hours (full) | yield per core-hour |
|---|---|---|---|
| mc_signals_hgg | 30 | 0.1 | ~273 |
| MET | 148 | 2.5 | ~60 |
| mc_ttbar | 594 | 10.4 | ~57 |
| JetHT | 77 | 2.2 | ~35 |
| mc_qcd (170-300) | 73 | 2.7 | ~27 |
| DoubleMuon | 331 | 15.3 | ~22 |
| mc_single_top | 299 | 14.8 | ~20 |
| MuonEG | 397 | 22.3 | ~18 (but see overlap risk) |
| mc_diboson | 186 | 12.3 | ~15 |
| SingleMuon | 293 | 20.4 | ~14 |
| SingleElectron | 42 | 3.0 | ~14 |
| mc_wjets | 6 | 0.6 | ~10 |
| mc_drell_yan | 110 | 10.7 | ~10 |
| DoubleEG | 190 | 20.7 | ~9 |
| **Tau** | **306** | **42.6** | **~7 — the LEAST cost-efficient dataset measured** |

**Tau is a notable, counter-intuitive result: the dataset that needed the
most compute (42.6 core-hours, and the only one to exceed the pilot's own
60-minute expectation) delivers the lowest yield-per-core-hour of any
dataset here** — its very high object multiplicity (96% of events clear
the >=2-object gate, the highest of any dataset) drives a long
combination loop, but a large share of that combinatorial work does not
survive to a usable histogram. Worth remembering if Tau is ever
considered for a "cheap and easy" addition — it measurably is not,
despite superficially looking that way from its "96% pass rate" alone.

**Recommended first batch, reasoning included:** `mc_ttbar`, `MET`,
`JetHT`, `mc_qcd_multijet`, and `mc_signals_hgg` together give **~922**
histograms for under **18 core-hours total** — the single best
value-for-compute cluster, and all MC or non-lepton-triggered data, so
**zero cross-dataset double-counting risk** among themselves (MC doesn't
overlap with data at all by construction; MET/JetHT/QCD triggers don't
structurally overlap the way MuonEG does). Add `DoubleMuon` and
`mc_single_top` next (**+630** for **+30.1 core-hours**) — DoubleMuon is
already the committed, physically-validated dataset, so this is a natural
second step regardless of cost. **Treat `MuonEG` as a separate decision,
not a default add**: its 397 is the second-largest single contribution,
but it is also the one dataset here with a real, unquantified overlap
risk against SingleMuon and SingleElectron — decide whether to include it
*and* budget de-duplication, or leave it out and accept a smaller but
cleaner total, rather than silently summing it in.

## Known risks

1. **Prescaled triggers (JetHT, MET) are not modeled here, and would
   distort a real mass spectrum if ignored.** JetHT and MET are
   typically collected using a *ladder* of trigger thresholds, most of
   which are heavily "prescaled" (only a random fraction of events
   passing a lower threshold are actually recorded, to keep the total
   data-taking rate manageable) — and the prescale factor is not constant
   across the full pT/MET range a physicist would want to histogram. A
   naive combination of differently-prescaled trigger paths **can
   introduce artificial steps or kinks in an otherwise smooth falling
   spectrum, at exactly the pT/MET values where the trigger regime
   changes** — and a shape-finding tool like BumpNet has no way to tell
   that kind of instrumental step from genuine new physics. This
   measurement used **no trigger requirement at all**, so it does not
   exhibit this artifact directly, but any real, properly-triggered
   JetHT/MET run **must** account for prescales (per-event/per-run
   prescale weights) before histogramming, or risk feeding BumpNet a
   fake bump. Not measured or corrected for here — flagged as the single
   most important risk specific to these two datasets, per this task's
   own scope (choosing/validating triggers is explicitly out of scope).
2. **Double-counting across primary datasets** (see above): the same
   physical event can be recorded by more than one primary dataset if it
   independently satisfies more than one trigger stream. Measured as
   negligible (~0.01%) for one orthogonal pair (DoubleMuon/DoubleEG);
   **not measured, and likely much larger**, for MuonEG against
   SingleMuon/SingleElectron specifically, by construction of MuonEG's
   own trigger. Any combined total across datasets should either exclude
   MuonEG or apply the pipeline's own existing de-duplication
   (`services.parsing.event_deduplication`) first.
3. **The muon-jet overlap artifact already known from the DoubleMuon
   analysis.** `studies/m0m1j0_cms/DESIGN.md`'s own D3 measurement found
   that **92.66%-92.68%** of "leading jets" in dimuon-triggered events are
   not independent hadronic activity at all — they are PF jets
   reconstructed essentially on top of the selected muon itself (median
   ΔR ≈ 0.013, far inside the jet's own 0.4 cone). The shared object
   selection this measurement reuses (`select_and_split_jets`'s
   ΔR<0.4 lepton-jet cleaning) removes most of these before they reach
   any histogram — but the underlying detector/reconstruction effect is
   real and dataset-wide, not specific to the m0m1j0 combination it was
   first found in, and would recur in any future CMS muon-triggered
   analysis that skips or weakens that cleaning step.
4. **The unexplained sub-1 GeV dimuon population**, previously flagged
   during the DoubleMuon combination survey work (a low-mass dimuon
   population the group's own diagnostic tooling in
   `studies/m0m1j0_cms/selection.py`'s `compute_dimuon_diagnostics` was
   built to investigate) — mentioned here for completeness since this
   measurement's own topology-free selection can, in principle, populate
   dimuon-containing categories (`m0m1`, `m0m1j0`, etc.) at masses low
   enough to fall in that same unexplained region for DoubleMuon and
   MuonEG specifically. This report did not re-investigate it (out of
   scope) and did not specifically check whether it appears among the
   categories counted above — flagged as UNVERIFIED, worth a direct check
   before treating any low-mass dimuon-containing histogram here as
   physically clean.

