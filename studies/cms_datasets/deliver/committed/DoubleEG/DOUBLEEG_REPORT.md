# DoubleEG full run + generic-population delivery — quality-gate report

Every number below is **VERIFIED BY RUNNING** (evidence file named) unless
marked **UNVERIFIED**. Covers the full 133-file DoubleEG run
(`--population generic`) and the delivery built from it. See `README.txt`
for what the four ROOT files are.

Evidence files (all in this directory unless noted):
`build_summary.json`, `cutflow_and_resonances.json`, `manifest_breakdown.json`,
`real_root_verify_min31bins.json`, `real_root_verify_min26bins.json`,
`manifest_doubleeg_generic_min31bins.json`, `manifest_doubleeg_generic_min26bins.json`,
plus `studies/cms_datasets/evidence/doubleeg_pilot_reproducibility.json`.

---

## 0. A note on git commit tracking (process issue, not a data problem)

**VERIFIED BY RUNNING.** During the 133-job array, 18 jobs (array indices
1–15, 17, 18, 20) recorded git commit `1ff119c`, while the other 115
recorded `823f91e`. This happened because unrelated commits (to
`studies/cms_datasets/deliver/` report-generation scripts, not to
`run_dataset_on_file.py`) were pushed and pulled into the shared cluster
checkout while the array was still running — a process mistake on my
part (I should not have touched the shared checkout mid-run). **The
actual code that governs selection, gating, combination, and
shard-writing was verified unaffected**: `git diff 1ff119c 823f91e --
studies/cms_datasets/cluster/run_dataset_on_file.py` produces **zero
output** — the file is byte-for-byte identical between the two commits.
To remove any ambiguity, the 18 affected jobs (and 2 already-correct
neighbors, 16 and 19, harmlessly re-run alongside them) were re-submitted
against a single pinned commit (`823f91e`, via a detached-HEAD checkout
of the shared clone). **All 133 jobs now report `823f91e`** — confirmed
directly, and this is the commit the delivery below is built from. The
pilot-reproducibility check (Section 2) was re-run after this fix and
still passes exactly, including for job 1 (one of the two re-run pilot
comparison files).

---

## 1. Identity check (Step 2a)

**PASS.** (`build_summary.json`'s own `identity_check` block):

| Check | Result |
|---|---|
| Jobs present | 133 / 133, each (record, file_index) pair exactly once |
| Sum of `n_read` | 164,185,704 — matches the expected total exactly |
| CAPPED:: entries found | 0 |
| Distinct git commits | 1 (`823f91e`, after the fix in Section 0) |

---

## 2. Pilot reproducibility (Step 2b) — the most important result

**PASS**, for both pilot files (`studies/cms_datasets/evidence/doubleeg_pilot_reproducibility.json`):

| | Record 30521 file 0 | Record 30554 file 0 |
|---|---|---|
| `n_after_gate` (pilot vs. full run) | 189,753 = 189,753 | 75,882 = 75,882 |
| `n_exclusive` (pilot vs. full run) | matches | matches |
| Inclusive shard | identical signatures, identical arrays | identical signatures, identical arrays |
| Exclusive shard | identical signatures, identical arrays | identical signatures, identical arrays |

The pilot ran an earlier commit (`952e2f8`) that, per this task's own
brief, differed from the full run only in diagnostics fields — this
result confirms that claim: every actual selection/shard output is
byte-for-byte reproduced.

---

## 3. Exclusive bookkeeping (Step 2c)

**VERIFIED BY RUNNING** (`cutflow_and_resonances.json`):

| Quantity | Value |
|---|---:|
| Total inclusive (`n_after_gate`, post-population-gate) | 15,289,956 |
| Total exclusive (`n_exclusive`, post-population-gate) | 15,288,986 |
| Inclusive − exclusive | **970** |
| Exclusive fraction (exclusive / inclusive, both post-gate) | **0.999937** ≈ 0.9999 |

This matches the pre-flight's own stated exclusive fraction (0.9999)
exactly. **On "the total vetoed by the DoubleMuon trigger set"**: the
970 figure above is the post-gate vetoed count, and it is *tautologically*
equal to inclusive − exclusive by how the driver computes `n_exclusive`
(a direct sub-mask of the gate-passing population) — not an independent
cross-check. A genuinely independent number exists in each job's own
`n_vetoed_by_each_higher_dataset["DoubleMuon"]` field, but that one is
measured *before* the population gate — summed across all 133 jobs, it
totals **982**, i.e. 12 more than 970. Those 12 events fired both
DoubleEG's and DoubleMuon's triggers but had fewer than 2 selected
objects of any type, so they never entered the gated population at all.
This is not a discrepancy in the exclusive bookkeeping itself — it is two
genuinely different populations (pre-gate vs. post-gate) being counted,
and both numbers are reported here rather than only the one that looks
like a clean match. (An earlier version of the aggregation script divided
by the pre-gate population instead of the post-gate one for the
exclusive-fraction calculation, producing an incorrect 86.9% — caught
and fixed before this number was used in this report; see the script's
own commit history.)

---

## 4. Cutflow and portal identity (Step 4)

**VERIFIED BY RUNNING** (`cutflow_and_resonances.json`, summed from all
133 jobs):

| Stage | Events | Fraction of previous stage |
|---|---:|---:|
| Read | 164,185,704 | — |
| After golden JSON | 159,107,970 | 96.91% |
| After trigger (`HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ`) | 17,599,145 | 11.06% (of golden) |
| After population gate (generic) | 15,289,956 | 86.88% (of triggered) |
| Exclusive | 15,288,986 | 99.99% (of gated) |

**Portal identity check**: sum of `n_read` (164,185,704) equals the CMS
Open Data portal's own published total for records 30521 + 30554
(164,185,704) — **exact match**.

---

## 5. Resonance: raw dielectron mass — Z peak

**VERIFIED BY RUNNING** (`raw_dielectron_mass_full_range.png`,
`cutflow_and_resonances.json`). Gaussian fit over 70–112 GeV:

- **Position**: 90.52 ± 0.06 GeV.
- **Width (σ)**: **2.66 ± 0.06 GeV.**

As expected, this is **noticeably wider than the DoubleMuon delivery's
own Z fit** (90.85 ± 0.05 GeV, σ = 2.09 GeV) — consistent with ECAL
electron energy resolution being coarser than muon momentum resolution
from the tracker. Nothing was tuned to produce this; it is a direct fit
to the raw histogram.

---

## 6. Leading/subleading electron pT and eta

**VERIFIED BY RUNNING** (`leading_subleading_electron_pt.png`,
`selected_electron_eta.png`, `cutflow_and_resonances.json`).

- Both leading and subleading electron pT distributions show a sharp
  turn-on exactly at the 25 GeV object cut, with the two DoubleEG trigger
  legs (23 GeV and 12 GeV) correctly falling below it.
- **Fraction of events with leading electron pT in 25–28 GeV: 4.75%**
  (520,322 of 10,956,271).
- **Electron eta / ECAL gap region**: of 17,134,693 selected electrons
  (across the whole inclusive population), **396,513 (2.31%)** fall in
  the barrel-endcap transition region 1.4442 < |η| < 1.566. The plot
  shows a clear, expected dip in both gap regions — object definitions
  were not changed; this is documentation only, per this task's own
  instruction.

---

## 7. Counts: histograms, lepton content, object content, overlap with DoubleMuon

**VERIFIED BY RUNNING** (`build_summary.json`, `manifest_breakdown.json`):

| Funnel stage | Count |
|---|---:|
| (b) After `min_events_per_fs=100` | 1,042 |
| (c) After full post-processing, ≥100 main events | 838 |
| (d) BumpNet-usable, >30 bins | **644** |
| >25 bins | **712** |
| Extra at >25 vs. >30 bins | 68 |

**By lepton content** (0, 1, ≥2 selected leptons — electrons + muons combined):

| | >30 bins | >25 bins |
|---|---:|---:|
| 0 leptons | 123 | 126 |
| 1 lepton | 209 | 225 |
| ≥2 leptons | 312 | 361 |

**By object-content category**:

| Category | >30 bins | >25 bins |
|---|---:|---:|
| b-jet-containing | 432 | 472 |
| lepton+jet | 142 | 159 |
| lepton-only | 11 | 14 |
| jet-only | 59 | 67 |

**≥2-selected-electrons subset** (the conventional dielectron-dataset
subset, requested alongside the full counts): **303 histograms at >30
bins, 333 at >25 bins.**

**Cross-check requested for the DoubleMuon generic delivery**: running
the same count with `lepton_letter=m` on the already-committed DoubleMuon
manifests gives **339 at >30 bins and 368 at >25 bins**
(`studies/cms_datasets/deliver/committed/DoubleMuon/manifest_breakdown_crosscheck.json`)
— **matches the expected 339/368 exactly.**

**Overlap with the DoubleMuon generic delivery** (by histogram NAME —
these are two different datasets, so shared names do not imply shared
events, only that both datasets happen to populate a final state with
the same combination and category label):

| | DoubleEG | DoubleMuon | Shared | DoubleEG-only | DoubleMuon-only |
|---|---:|---:|---:|---:|---:|
| >30 bins | 644 | 802 | 163 | 481 | 639 |
| >25 bins | 712 | 910 | 210 | 502 | 700 |

---

## 8. Quality-gate plots

All committed under `plots/`:

- `plot_1_largest.png` — `mass_j0j1_cat_0ex_0mx_2jx_0gx_0tx_0bx` (2,090,562
  events, pure jet-jet, zero leptons). This is the same histogram as the
  largest zero-lepton one below — the single largest category in this
  delivery has no leptons at all.
- `plot_2_median.png` — `mass_e0j1b0b1_cat_1ex_0mx_3jx_0gx_0tx_2bx` (2,624 events).
- `plot_3_near_25bin_boundary.png` — `mass_b0b1_cat_1ex_1mx_0jx_0gx_0tx_2bx` (26 filled bins).
- Three categories absent from the DoubleMuon generic delivery
  (`plot_new_category_{1,2,3}.png`):
  - `mass_e0e1_cat_2ex_0mx_0jx_0gx_0tx_0bx` — **79,214 events, a
    zero-jet DIELECTRON category** (pure dielectron pair, no jet).
  - `mass_e0e1j0_cat_2ex_0mx_1jx_0gx_0tx_0bx` (685,122 events).
  - `mass_e0j0_cat_2ex_0mx_1jx_0gx_0tx_0bx` (651,901 events).
- `plot_largest_zero_lepton.png` — same as the largest overall (above);
  no distinct zero-lepton category exceeds it.
- `plot_crop_comparison.png` — the largest histogram, uncropped vs. cropped.

---

## 9. Known artifacts

1. **Zero- and one-lepton categories in a dielectron-triggered dataset**:
   **123** (>30 bins) / **126** (>25 bins) delivered histograms have zero
   selected electrons AND zero selected muons; **209** / **225** have
   exactly one. Same mechanism as documented for DoubleMuon: the trigger
   requires two *online* electrons, but the *offline* selection (pT>25
   GeV, cutBased medium) is tighter than the trigger's own 23/12 GeV
   legs — an event can fire the trigger and still end up with 0 or 1
   selected electrons offline, landing in a jet/b-jet-dominated final
   state via the generic ≥2-any-object gate.
2. **Electron ECAL gap region**: 2.31% of selected electrons fall in
   1.4442 < |η| < 1.566 (Section 6) — documented, not filtered; object
   definitions are unchanged.
3. **Run 283469** (Run2016H): this task's own pre-flight scan
   (`studies/cms_datasets/PREFLIGHT_REPORT.md`, Part 1(b)) flagged this
   run as anomalously small — and DoubleEG was one of the datasets
   directly affected: its own trigger path fired zero times in that run
   despite 212 golden events being present. Not re-investigated here,
   per this task's scope; included in this delivery's data as-is.

---

## 10. Verification summary

- Real ROOT 6.40.02 (independent of uproot): 0 problems found across all
  644 and all 712 histograms — counts match, every cropped histogram's
  bin 1 is non-empty, cropped contents equal the uncropped version over
  the kept range exactly (`real_root_verify_min31bins.json`,
  `real_root_verify_min26bins.json`).
- Identity check: PASS (Section 1). Pilot reproducibility: PASS (Section 2).
- No continuity check applies here (no prior DoubleEG delivery exists);
  the overlap-with-DoubleMuon comparison (Section 7) serves the analogous
  "how does this relate to what's already delivered" purpose for a new
  dataset.
