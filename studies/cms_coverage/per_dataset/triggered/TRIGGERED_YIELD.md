# Triggered per-dataset yield: how many DISTINCT BumpNet-ready histograms exist

Branch `survey/per-dataset-yield`, tip before this task: `71d878d1ca54e2f16273f1fa2a8bbd5c02cab251`.
Every number below is **VERIFIED BY RUNNING** (an actual command was
executed, output quoted or in a committed JSON) or **UNVERIFIED**
(explicitly flagged).

## What changed from the trigger-free measurement

Object definitions, the 186 combination patterns, categories, naming, the
10 GeV / 0–10 TeV grid, and post-processing are **all unchanged** —
imported and called from the same shared code as every previous
measurement in this branch. The dropped-topology gate is also unchanged
(an event is kept if it has ≥2 selected objects of **any** type). The
**one** real change: each data primary dataset now has its own HLT trigger
requirement, applied via the real, unmodified
`services.parsing.trigger_requirements.apply_trigger_requirement`
(imported, not reimplemented), inserted exactly where the shared pipeline
itself applies it — after the golden-JSON filter, before object selection.
MC keeps no trigger requirement and no golden-JSON filter, as before.

## Trigger verification — VERIFIED BY RUNNING

Every requested HLT path was checked directly against each dataset's
actual file before running anything:

| Dataset | Requested paths | Present? |
|---|---|---|
| SingleMuon | `HLT_IsoMu24`, `HLT_IsoTkMu24` | both present |
| DoubleMuon | `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ`, `HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ` | both present |
| SingleElectron | `HLT_Ele27_WPTight_Gsf` | present |
| DoubleEG | `HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ` | present |
| MuonEG | `HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ`, `HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ` | both present (the DZ variants — no fallback to non-DZ needed) |
| JetHT | `HLT_PFHT900`, `HLT_PFJet450` | both present |

**No substitutions were needed anywhere** — every path named in the task
brief exists exactly as named in the actual file used.

## Why Tau and MET are excluded

Neither is measured here. Our object set is muons, electrons, jets, and
b-jets — no taus, no photons, no missing energy. A Tau- or MET-triggered
event's own *characteristic* physics (a tau pair, a MET-recoiling jet
system) is invisible to this object set entirely; whatever it contributes
through our four object types is generic lepton/jet combinations that
SingleMuon, DoubleMuon, SingleElectron, DoubleEG, MuonEG, and JetHT already
cover between them. Including Tau/MET would add compute (Tau alone needed
42.6 core-hours in the trigger-free measurement, the most of any dataset)
without adding a genuinely new capability to the distinct-histogram count.

## Per-dataset table — VERIFIED BY RUNNING

| Dataset | events read | after trigger | after ≥2-object gate | (a) | (b) unscaled | (b) scaled | (c) | **(d) unscaled** | (d) scaled est. | elapsed |
|---|---|---|---|---|---|---|---|---|---|---|
| SingleMuon | 2,939,781 | 1,955,197 | 635,002 | 2,057 | 399 | 1,755 | 303 | **217** | 221 | 820.4 s |
| DoubleMuon | 2,315,223 | 729,741 | 509,193 | 2,246 | 373 | 906 | 288 | **176** | 188 | 526.8 s |
| SingleElectron | 112,955 | 62,554 | 26,271 | 787 | 56 | 787 | 30 | **18** | 18 | 68.4 s |
| DoubleEG | 2,014,154 | 219,416 | 189,753 | 1,430 | 228 | 821 | 120 | **76** | 78 | 235.7 s |
| MuonEG | 2,238,235 | 279,559 | 203,017 | 2,304 | 499 | 1,167 | 326 | **136** | 146 | 377.5 s |
| JetHT | 107,505 | 14,010 | 13,832 | 537 | 64 | 537 | 31 | **28** | 31 | 96.4 s |

MC (no trigger, unchanged from the trigger-free measurement — same files,
same numbers, reproduced here for completeness):

| Group | (a) | (b) unscaled | (b) scaled | (c) | **(d) unscaled** | (d) scaled est. |
|---|---|---|---|---|---|---|
| ttbar | 3,388 | 1,156 | 3,388 | 895 | **571** | 594 |
| Drell-Yan | 1,505 | 243 | 1,049 | 186 | **109** | 110 |
| W+jets | 211 | 24 | 211 | 14 | **6** | 6 |
| Diboson | 1,361 | 272 | 518 | 216 | **182** | 186 |
| Single top | 1,302 | 420 | 984 | 358 | **292** | 299 |
| QCD (170-300 GeV) | 375 | 91 | 255 | 72 | **70** | 73 |
| Signal (H→γγ) | 624 | 78 | 78 | 44 | **30** | 30 |

## The headline: distinct BumpNet-ready histograms — VERIFIED BY RUNNING

Computed from the **complete** stage-(d) name lists saved per dataset
(`studies/cms_coverage/per_dataset/triggered/assets_raw/names_*.json`), by
`compute_union.py`, over the union of all datasets in each group:

| | distinct count |
|---|---|
| **6 data primary datasets, union** | **339** |
| **7 MC groups, union** | **682** |
| **Combined union (data ∪ MC)** | **709** |

Compare this to the **sum** of the per-dataset (d) unscaled counts:
217+176+18+76+136+28 = 651 for data, 571+109+6+182+292+70+30 = 1,260 for MC.
**The union is dramatically smaller than the sum** — 339 vs. 651 for data
(48% smaller), 682 vs. 1,260 for MC (46% smaller) — confirming directly
that the same histogram name recurs across datasets on a large scale, and
that a naive per-dataset sum (as the earlier trigger-free measurement did)
substantially over-counts the true number of distinct BumpNet inputs.

**Data-vs-MC name matching**: of the 339 distinct data histograms, **312
(92%) have a same-named MC counterpart.** At stage (b) it is starker
still: **all 816 distinct data names (100%) also appear among MC's 1,204.**
MC's own union is both larger and, at the name level, very nearly a
superset of what data alone produces — worth keeping in mind given MC's
role for BumpNet training is explicitly unsettled (task scope).

## Overlap structure

### How many datasets does each distinct name appear in

At stage (d):

| appears in exactly N datasets | data-only (of 6) | MC-only (of 7) | combined (of 13) |
|---|---|---|---|
| 1 | 174 | 409 | 331 |
| 2 | 78 | 115 | 139 |
| 3 | 56 | 61 | 73 |
| 4 | 8 | 68 | 32 |
| 5 | 17 | 11 | 26 |
| 6 | 6 | 15 | 36 |
| 7 | — | 3 | 34 |
| 8+ | — | — | 30 (spread across 8–13) |

Most names (174/339 ≈ 51% for data, 409/682 ≈ 60% for MC) appear in
**exactly one** dataset — genuinely dataset-specific. But a real tail is
shared across most or all datasets: 6 data names appear in **all 6** data
datasets, and 34 combined names appear in exactly 7 of the 13 (a
mix of "in every data dataset, and some MC" patterns) with a further 30
appearing in 8 or more of the 13.

### Per-dataset: unique vs. shared (stage d)

| Dataset | total (d) | unique to it | shared with ≥1 other |
|---|---|---|---|
| SingleMuon | 217 | 85 | 132 |
| DoubleMuon | 176 | 35 | 141 |
| SingleElectron | 18 | 0 | 18 |
| DoubleEG | 76 | 30 | 46 |
| MuonEG | 136 | 24 | 112 |
| JetHT | 28 | 0 | 28 |

**SingleElectron and JetHT have zero histograms unique to them** — every
single one of their surviving categories is also produced by at least one
other dataset. This is a real, notable finding: even with a real trigger
applied, these two datasets contribute **nothing** to the distinct count
that isn't already covered elsewhere among the six.

### The 20 most-shared names (stage d)

Across the 6 data datasets, the top of the list is a clean sweep of
**generic, zero-lepton jet categories** — e.g. `mass_j0j1_cat_0ex_0mx_2jx_0gx_0tx_0bx`,
`mass_j0j1j2_cat_0ex_0mx_3jx_0gx_0tx_0bx`, `mass_j0j1j2j3_cat_0ex_0mx_4jx_0gx_0tx_0bx`
— each appearing in **all 6** data datasets. Across all 13 (data + MC), the
top names again start with the same zero-lepton jet categories (up to 13/13),
followed closely by single-b-tag jet categories (`mass_j0b0_cat_...`,
`mass_j0j1b0_cat_...`, up to 11/13) — exactly the categories Matan's
technical lead originally flagged (DoubleEG's largest histograms being
`mass_j0j1` with zero leptons required).

### Split by object content — **jet-only confirmed as the most duplicated, verified directly**

| content category | distinct names (combined union) | average number of datasets containing each name |
|---|---|---|
| **jet-only** | 75 | **4.52** |
| lepton+jet | 179 | 2.65 |
| b-jet-containing | 445 | 2.44 |
| lepton-only | 10 | 1.30 |

**Confirmed, not assumed**: `jet-only` categories are shared across nearly
4.5 datasets on average (one even reaches all 13), almost double the next
category. `lepton-only` categories are the *least* duplicated (1.30 on
average) — sensible, since a category requiring specific lepton content is
inherently tied to the dataset(s) whose object selection can actually
populate it. `b-jet-containing` is the largest category by raw count (445
distinct names) but not the most duplicated *per name* — there are simply
many more distinct b-jet-containing combinatorial patterns available (the
186-pattern set includes many b-jet slots), each individually less likely
to be shared than a jet-only one.

## Sensitivity: the same union at stage (b) (≥100 events, no bin requirement)

| | distinct count at (b) |
|---|---|
| 6 data primary datasets, union | 816 |
| 7 MC groups, union | 1,204 |
| Combined union | 1,204 (data union is fully contained in MC's) |

The bin requirement (stage d) costs **58% of the stage-(b) data union**
(816 → 339) and **43% of the MC union** (1,204 → 682) — a substantial
further narrowing on top of the raw event-count bar, consistent with
`>30 filled bins` being a genuinely restrictive, shape-based requirement
rather than a formality once ≥100 events is already satisfied.

## The saturation finding — CONFIRMED AGAIN under real triggers

Carried forward from the trigger-free measurement and independently
re-verified here, now with real per-dataset event populations that differ
by orders of magnitude after triggering:

| Dataset | scale factor | (b) unscaled → scaled | (d) unscaled → scaled |
|---|---|---|---|
| SingleElectron | ×1,357.7 | 56 → 787 (14.1×) | 18 → 18 (**1.00×, completely flat**) |
| JetHT | ×1,122.6 | 64 → 537 (8.4×) | 28 → 31 (1.11×) |
| DoubleMuon | ×19.5 | 373 → 906 (2.4×) | 176 → 188 (1.07×) |

**The same pattern holds under triggers as without them**: stage (b) —
a pure event-count bar — responds strongly to how much more data a full
dataset has; stage (d) — which *also* requires >30 filled bins — barely
moves, in one case (SingleElectron) not at all. **The practical
consequence stated plainly, again: processing more files of a given
dataset overwhelmingly fills in histograms that already exist rather than
creating new ones.** This holds regardless of whether a trigger is
applied — it is a property of the bin-count requirement itself, not of the
trigger-free selection that first surfaced it.

## What changed vs. the trigger-free run

| Dataset | (d) unscaled, trigger-free | (d) unscaled, triggered | change |
|---|---|---|---|
| SingleMuon | 285 | 217 | −24% |
| DoubleMuon | 312 | 176 | −44% |
| SingleElectron | 36 | 18 | −50% |
| DoubleEG | 185 | 76 | −59% |
| MuonEG | 382 | 136 | −64% |
| JetHT | 75 | 28 | −63% |

**Every dataset's own count went down substantially with a real trigger —
the opposite of "triggers reveal more dataset-specific structure" in
absolute terms.** The reasoning behind why this happens (not separately
re-measured, but directly visible in the numbers above): a trigger
requirement is, first and foremost, an event-count cut — DoubleMuon lost
68% of its golden-JSON-passing events to the trigger requirement alone
(2,315,223 → 729,741) — and per the saturation finding just above, fewer
events costs histograms almost one-for-one at the margin (stage (b) is
event-count-sensitive), while the topology-free "≥2 objects of any type"
gate was never removed, so the *kind* of category a surviving event can
populate is unchanged. The brief's own anticipated mechanism — "each
dataset's characteristic final states enhanced, generic jet events
suppressed" — was **not measured as a comparable overlap-fraction shift
here** (the trigger-free run only saved top-10 names, so its true overlap
fraction is unknown for comparison); what **is** directly measured is that
the *generic* categories remain the most shared even after triggering
(the top-20-most-shared list above is still dominated by zero-lepton jet
categories) — triggering shrank every dataset's total, but did not visibly
displace jet-only categories from the top of the sharing list.

## Known risks

1. **Prescaled triggers.** `HLT_PFHT900` and `HLT_PFJet450` are the two
   high-threshold JetHT paths generally expected to run unprescaled in
   2016 — but **NanoAOD itself carries no prescale information, so this
   cannot be confirmed from the file alone.** If either path was in fact
   prescaled for some run range within Run2016G, this measurement's JetHT
   event count (and therefore its stage-b/d histogram counts) would be
   biased in a way this task cannot detect or correct. Not measured or
   corrected for here — explicitly out of scope, per the task's own
   instruction.
2. **The muon-jet overlap artifact** (already known from the DoubleMuon
   combination survey, `studies/m0m1j0_cms/DESIGN.md`'s own measurement):
   92.66%–92.68% of "leading jets" in dimuon-triggered events are PF jets
   reconstructed essentially on top of the selected muon itself (median
   ΔR ≈ 0.013). The shared object selection's own ΔR<0.4 lepton-jet
   cleaning (reused here unmodified) removes most of these before they
   reach any histogram, but the underlying detector effect is real and
   would recur in any muon-triggered dataset that skipped or weakened
   that cleaning step.
3. **The unexplained sub-1 GeV dimuon population**, flagged previously
   during the DoubleMuon combination survey and not re-investigated here
   (out of scope). This measurement's dimuon-containing categories
   (`m0m1`, `m0m1j0`, etc., for DoubleMuon and MuonEG specifically) could
   in principle include masses in that unexplained low-mass region —
   **UNVERIFIED** whether any counted histogram here is affected; would
   need a direct check against the same diagnostic tooling
   (`studies/m0m1j0_cms/selection.py`'s `compute_dimuon_diagnostics`)
   before treating any such histogram as physically clean.
4. **Event-level double-counting across primary datasets is a separate
   problem from this name-level union, not addressed here.** This report
   counts distinct *histogram names* — it says nothing about whether the
   same physical *event* contributes to more than one dataset's version of
   a shared name (e.g. an event satisfying both DoubleMuon's and MuonEG's
   triggers would contribute to `mass_j0j1_cat_...` under both). That is
   an event-level de-duplication question (`services.parsing.event_deduplication`),
   entirely separate from, and not resolved by, the name-level counting
   done in this report.

## What this means for the 3,000 target

The honest, distinct-histogram number today, from a real (if minimal,
one-file-per-dataset) measurement with real triggers, is **339 for data,
682 for MC, 709 combined** — far below the earlier 3,082 sum, because that
sum counted the same shared categories once per dataset rather than once
overall. Whether MC belongs in a BumpNet-facing total at all is unsettled
(task scope) — if it does not, the honest number is 339, not thousands.

Getting a **trustworthy production number** would need, at minimum: (a)
running each dataset's full file set (not one file) so stage-(b)-type
counts reflect the dataset's true statistics — though the saturation
finding above means this mostly fills existing histograms rather than
creating new ones, so the distinct-count impact of more files is likely
small; (b) resolving MC's actual role (included, excluded, or counted
separately) before deciding what the "total" even means; (c) the
event-level de-duplication step noted above, if datasets are ever combined
rather than reported side by side; and (d) a decision on the trigger
prescale risk for JetHT/MET-like datasets, which this task did not
attempt to resolve.
