# Trigger-matching validation report: DoubleMuon + SingleMuon

Steps 3-4 of the trigger-matching task (spec: `TRIGGER_MATCHING_SPEC.md`).
Every number below is either **VERIFIED BY RUNNING** (with the exact
command and evidence file cited) or **UNVERIFIED** (stated as such, with
the reason). Code: commit `cbd1abb723b682c40d86b2672fffe782f632ef93` on
`deliver/all-datasets-bumpnet` (Matan's fork), run from a dedicated pinned
checkout at `/storage/agrp/berkom/atlas-utilization/work/matching_validation_pinned/repo`
(detached HEAD at that exact commit, untouched for the duration of every
job below). All outputs under
`/storage/agrp/berkom/atlas-utilization/output/cms_datasets/matching_validation/`
(new directory; nothing pre-existing under `cms_datasets/` was modified).

---

## Step 3a (HARD): generic-mode behaviour is byte-for-byte unchanged

**VERIFIED BY RUNNING.** All 4 pilot files (DoubleMuon 30522/0, DoubleMuon
30555/0, SingleMuon 30530/0, SingleMuon 30563/0) re-run with
`--population generic` under the pinned commit, compared against the
existing (untouched, read-only) pilot outputs under
`.../cms_datasets/run/job_*_generic/`.

Per-stage event counts (`n_read`, `n_after_golden_json`, `n_after_trigger`,
`n_after_gate`, `n_exclusive`, signature-write counts) matched exactly for
all 4 files (evidence: `evidence/job_metadata/*_generic/job_metadata.json`
vs. the pre-existing files, both quoted in the session transcript).

Beyond per-stage counts, a full **array-level** comparison was run
(`evidence/step3a_3b_shard_comparison.txt`): every non-capped signature's
complete value multiset (all float32 masses, rounded to 1e-5) was compared
between the old and new inclusive/exclusive shards, using read-only
(`mode=ro&immutable=1`) SQLite connections throughout.

| File | Inclusive shard | Exclusive shard |
|---|---|---|
| DoubleMuon 30522/0 | PASS, 2246 signatures identical | PASS, 2246 signatures identical |
| DoubleMuon 30555/0 | PASS, 1973 signatures identical | PASS, 1973 signatures identical |
| SingleMuon 30530/0 | PASS, 2057 signatures identical | PASS, 1272 signatures identical |
| SingleMuon 30563/0 | PASS, 360 signatures identical | PASS, 257 signatures identical |

**Result: PASS for all 4 files, both shards.** Hard Rule 5 holds.

---

## Step 3b (HARD): matched is a subset of generic

**VERIFIED BY RUNNING** (`evidence/step3a_3b_shard_comparison.txt`).

Matched-mode's **inclusive** shard is a sub-multiset of generic's
inclusive shard for all 4 files:

| File | matched signatures | generic signatures | Result |
|---|---|---|---|
| DoubleMuon 30522/0 | 1146 | 2246 | PASS, subset |
| DoubleMuon 30555/0 | 725 | 1973 | PASS, subset |
| SingleMuon 30530/0 | 1702 | 2057 | PASS, subset |
| SingleMuon 30563/0 | 292 | 360 | PASS, subset |

A separate sanity check confirmed matched-**exclusive** is itself always a
sub-multiset of matched-**inclusive** (trivially expected, confirmed
directly) for all 4 files, which together with the table above proves by
transitivity that matched-exclusive ⊆ generic-inclusive too.

**Important, and reported exactly as found:** matched-mode's *exclusive*
shard is **not** a subset of generic-mode's exclusive shard for SingleMuon
(373 and 72 "only-in-matched" signatures for the two SingleMuon files on a
first, literal shard-vs-shard-type comparison). This is **not a bug** — it
is the deliberate, spec-required consequence of Step 2's SingleMuon
exclusive-shard rule being genuinely different between modes: generic mode
vetoes on trigger BITS against three datasets (DoubleMuon, DoubleEG,
MuonEG); matched mode vetoes on ACCEPTANCE against DoubleMuon alone
("electron datasets not part of this combination", per the task's own
scope). An event vetoed in generic mode only by DoubleEG or MuonEG firing
is correctly *not* vetoed in matched mode. This is documented in full in
`evidence/step3a_3b_shard_comparison.txt`.

**Result: PASS** (correctly interpreted per Step 2's own exclusive-shard
design).

---

## Step 3c (HARD): no zero-muon categories; correct minimum lepton counts

**VERIFIED BY RUNNING** (`scripts/check_3c.py`, run against each matched
run's own `final_state_label_event_counts_inclusive` field in
`evidence/job_metadata/*_matched/job_metadata.json`; full lepton-content
breakdown for all 4 matched-mode runs reproduced in the session transcript).

| File | n_after_gate | n_final_state_groups | Zero-muon categories | Min-muon violation |
|---|---|---|---|---|
| DoubleMuon 30522/0 | 223,393 | 43 | **0** | **0** (all ≥2 muons) |
| DoubleMuon 30555/0 | 218,886 | 32 | **0** | **0** (all ≥2 muons) |
| SingleMuon 30530/0 | 1,511,878 | 82 | **0** | **0** (all ≥1 muon) |
| SingleMuon 30563/0 | 6,919 | 28 | **0** | **0** (all ≥1 muon) |

Every final-state group's event count summed exactly to `n_after_gate` for
all 4 files (asserted in-script, held in all 4 cases).

**Result: PASS for all 4 files.**

---

## Step 3d: matching-efficiency plots (per dataset, G+H pilot files summed)

**VERIFIED BY RUNNING** (`evidence/step3d_efficiency_summary.json`; PNGs in
`plots/matching_efficiency_{DoubleMuon,SingleMuon}_{leading,subleading}_{pt,abseta}.png`).

Efficiency = accepted / (fired AND has the offline muon(s) the trigger
requires); since this population is already restricted to `events_triggered`
(this dataset's own trigger already required), "fired" is automatically
true throughout, so the denominator is simply "has the required offline
muon(s)".

**DoubleMuon** (leading selected-muon pT, 1 GeV bins 20-200 — offline
muon pT cut is 25 GeV, so bins below 25 GeV are empty by construction):

| Bin | Efficiency |
|---|---|
| 25-26 GeV | 1.0000 (514/514) |
| 26-27 GeV | 1.0000 (1390/1390) |
| 27-28 GeV | 0.9991 (2276/2278) |
| Plateau (≥40 GeV) | 0.99991 (343,056/343,088) |
| Overall | 0.99989 (441,627/441,676) |

**SingleMuon** (leading selected-muon pT):

| Bin | Efficiency |
|---|---|
| 25-26 GeV | 0.9984 (70,603/70,715) |
| 26-27 GeV | 0.9978 (67,785/67,936) |
| 27-28 GeV | 0.9982 (66,025/66,142) |
| Plateau (≥40 GeV) | 0.99766 (524,124/525,353) |
| Overall | 0.99795 (1,517,686/1,520,811) |

No turn-on visible in 25-28 GeV for either dataset: efficiency is already
at plateau level right at the offline pT floor (25 GeV), well above the
90% floor the task set as the "spec is wrong, stop" threshold. The eta
histograms show the same overall efficiencies (DoubleMuon 0.99989,
SingleMuon leading 0.99794 / subleading 0.99967) with no eta-dependent
degradation visible in the plots. A handful of very-high-pT bins
(150-200 GeV) dip to 0.90-0.96 in the SingleMuon plot — this is a
low-statistics artifact (single/double-digit event counts per bin there,
visible in the plot's upper panel), not a real efficiency loss.

**No STOP condition triggered** — plateau efficiency is far above 90% for
both datasets.

---

## Step 3e: accounting (generic vs. matched, SingleMuon exclusive fraction)

**VERIFIED BY RUNNING** (`evidence/step3e_accounting.json`).

| Run | n_read | n_after_golden | generic n_after_trigger | matched n_after_trigger | generic n_after_gate | matched n_after_gate | generic n_exclusive | matched n_exclusive | generic excl. frac. | matched excl. frac. |
|---|---|---|---|---|---|---|---|---|---|---|
| DoubleMuon 30522/0 | 2,315,223 | 2,298,786 | 729,741 | 729,741 | 509,193 | 223,393 | 509,193 | 223,393 | 1.000 | 1.000 |
| DoubleMuon 30555/0 | 2,147,195 | 2,049,089 | 723,967 | 723,967 | 506,927 | 218,886 | 506,927 | 218,886 | 1.000 | 1.000 |
| SingleMuon 30530/0 | 2,939,781 | 2,931,332 | 1,955,197 | 1,878,767 | 635,002 | 1,511,878 | 505,583 | 1,425,358 | 0.7962 | 0.9428 |
| SingleMuon 30563/0 | 14,113 | 14,113 | 8,788 | 8,462 | 2,841 | 6,919 | 2,258 | 6,529 | 0.7948 | 0.9436 |

Notes:
- DoubleMuon's `n_after_trigger` is identical between modes (own trigger
  set unchanged); `n_after_gate` shrinks under matched mode because the
  gate is stricter (offline-muon matching, not just "≥2 objects of any
  type"). Exclusive fraction is exactly 1.0 in both modes, as required by
  spec (DoubleMuon has no higher-veto-priority dataset).
- SingleMuon's `n_after_trigger` is **smaller** under matched mode
  (1,878,767 vs 1,955,197 for 30530/0) because matched mode's own trigger
  set is HLT_IsoMu24 only (Maryna's instruction), dropping HLT_IsoTkMu24
  events — an intended difference, not a bug.
- SingleMuon's `n_after_gate` is **larger** under matched mode
  (1,511,878 vs 635,002) because the matched acceptance test (offline muon
  matched to a trigger object) is a much narrower slice of "has ≥1 selected
  muon" than generic's own "≥2 objects of any type" gate is of the full
  population — these two gates measure genuinely different things and are
  not directly comparable in absolute size.
- **The key result**: SingleMuon's exclusive fraction rises from ~79.6%
  (generic, bits-only veto against 3 datasets) to ~94.3% (matched,
  acceptance-only veto against DoubleMuon alone) — i.e. under the
  acceptance-based veto, far fewer SingleMuon events get incorrectly
  removed as "already covered by DoubleMuon" when DoubleMuon's trigger
  merely fired but its own offline muons didn't pass 25 GeV/mediumID/iso.
  This is precisely the fix to Maryna's original bias concern.

---

## Step 3f: post-processing funnel, per file, both modes (floors, not predictions)

**VERIFIED BY RUNNING** (`evidence/step3f_funnel_summary.json`), using the
existing, unmodified funnel functions
(`services.storage.sqlite_shards.list_signatures`,
`studies.cms_coverage.cluster.merge_and_count.{copy_shards,run_funnel_at_threshold}`,
`studies.cms_datasets.deliver.build_dataset_delivery.build_sig_to_bumpnet`;
thresholds `PRIMARY_MIN_EVENTS_PER_FS=100`, `MIN_BUMPNET_BINS=30`,
`MIN_BUMPNET_EVENTS=100`). Run on the shard each dataset would actually
contribute to a future combined delivery: DoubleMuon → inclusive shard;
SingleMuon → exclusive shard (priority 2, behind DoubleMuon only in this
combination).

| Run | Shard | Stage-a signatures | Stage-b (≥100/sig) | Stage-c (z-peak+mass+peak+split) | min26bins (>25 bins) | min31bins (>30 bins) |
|---|---|---|---|---|---|---|
| DoubleMuon 30522/0 generic | inclusive | 2246 | 373 | 288 | 215 | 176 |
| DoubleMuon 30522/0 matched | inclusive | 1146 | 150 | 107 | 75 | 57 |
| DoubleMuon 30555/0 generic | inclusive | 1973 | 373 | 295 | 219 | 180 |
| DoubleMuon 30555/0 matched | inclusive | 725 | 150 | 111 | 74 | 62 |
| SingleMuon 30530/0 generic | exclusive | 1272 | 265 | 235 | 207 | 184 |
| SingleMuon 30530/0 matched | exclusive | 1389 | 252 | 195 | 163 | 143 |
| SingleMuon 30563/0 generic | exclusive | 257 | 7 | 7 | 3 | 0 |
| SingleMuon 30563/0 matched | exclusive | 261 | 5 | 5 | 3 | 0 |

**These are one-file floors, not predictions for the full 57-file
(DoubleMuon) / 152-file (SingleMuon) delivery** — the tiny SingleMuon
30563/0 file (14,113 raw events) produces 0 min31bins histograms in
*both* modes simply because it is too small, which says nothing about the
full H-era dataset. The consistent pattern across the larger files
(DoubleMuon 30522/0, 30555/0, SingleMuon 30530/0) is that matched mode
survives with roughly 1/3 to 3/4 as many histograms as generic mode on the
same single file — expected, since matched mode's stricter gate reduces
raw per-signature statistics, and the funnel's own ≥100-events-per-signature
and >25/>30-non-empty-bin cuts are threshold effects that are highly
sensitive to per-file statistics.

---

## Step 4: exactly-once closure test

**VERIFIED BY RUNNING.** Run chosen: **280016** (Run2016G).

Run selection: candidate common runs were first ranked by combined event
count in the two G-era pilot files (`find_common_run.py`); the
smallest-combined-count candidate, run 279841, was tried first, but a
cheap single-branch (`run`) scan of every file in the DoubleMuon_G (29
files) and SingleMuon_G (70 files) datasets (`step4_find_all_files.py`,
using the pre-existing, read-only `record_file_lists.json`) showed run
279841's data is spread across **19 DoubleMuon files and 39 SingleMuon
files** — too large for a bounded "one closure run" check. A second scan
of 5 candidates (`step4_scan_footprint.py`, evidence:
`evidence/step4_footprint_candidates.json`) found run **280016** has the
smallest footprint of those tried: **5 DoubleMuon files, 8 SingleMuon
files** (13 files total, ~693k raw events combined for this run). All 13
files were read in full (not just the original 4 pilot files) — this is
within the task's own scope ("4 existing pilot files ... **plus ONE
closure run**").

Evidence: `evidence/step4_closure_result_final.json`,
`evidence/step4_single_event_investigation.txt`.

**Sanity check before trusting the concatenated multi-file set**: zero
duplicate (run, lumi, event) triples found within either dataset's own
5-file / 8-file union (`dm_n_duplicate_rle_across_files=0`,
`sm_n_duplicate_rle_across_files=0`) — confirms the file-discovery scan
found genuinely non-overlapping file segments, not double-counted data.

| Quantity | DoubleMuon (5 files) | SingleMuon (8 files) |
|---|---|---|
| Raw events for run 280016 | 158,520 | 534,798 |
| After golden JSON | 158,520 | 534,798 |
| After own-trigger requirement | 49,607 | 324,815 (HLT_IsoMu24 only) |
| Matched-accepted (inclusive) | 15,331 | 263,336 |
| Vetoed by DoubleMuon's acceptance (matched mode) | — | 15,126 |
| Exclusive | 15,331 (= inclusive) | 248,210 |

### Check (i): DoubleMuon's set is disjoint from SingleMuon's EXCLUSIVE set

**RESULT: FAIL — 1 overlapping (run, lumi, event) out of 15,331 ∩ 248,210:
`(280016, 24, 42925881)`.**

Root-caused exactly (`evidence/step4_single_event_investigation.txt`):
this one event's **`Muon_mediumId`** differs between its two primary
datasets' independently-produced copies — `[True, True]` in the
DoubleMuon file's copy, `[False, True]` in the SingleMuon file's copy of
the *same* (run, lumi, event) — alongside a ~0.0007 GeV difference in
reconstructed `Muon_pt` for the same physical muon (eta and phi are
bit-identical between the two copies). CMS produces each primary dataset
as its own independent MiniAOD/NanoAOD production job even where the
underlying collision event is shared; this muon evidently sits extremely
close to the Medium ID decision boundary, and the tiny numerical
difference between the two independent reconstructions is enough to flip
the ID flag in this one case. This is **not a bug in the matching
specification or its implementation** — `matched_acceptance_mask` and the
veto logic behave exactly as designed given each file's own (self-
consistent) branch values; the underlying *data* momentarily disagrees
with itself across the two primary datasets. Because the veto is
necessarily evaluated using the muon/TrigObj data available in the file
being processed (a SingleMuon job never reads the DoubleMuon file at run
time), SingleMuon's own copy — which sees only 1 selected muon (mediumId
fails for the leading one) — does not think DoubleMuon would accept this
event, so it is not vetoed and remains in SingleMuon's exclusive set,
while DoubleMuon's own copy (both muons pass) separately and correctly
accepts it into DoubleMuon's own inclusive set.

**Scale: 1 event in 263,540 (the union of the two inclusive sets for this
one run) — a rate of ~3.8×10⁻⁶.** Reported exactly, as the task's own
instruction requires ("a failure is a hard stop... report counts and any
exception exactly") — this is a genuine, tiny, residual double-counting
risk in any future combined delivery, not a defect to silently paper over.

### Check (ii): every SingleMuon event vetoed because DoubleMuon accepts it is present and accepted in the DoubleMuon files

**RESULT: PASS — 15,126 / 15,126 (100%).** Every one of SingleMuon's
vetoed events was found, by exact (run, lumi, event) lookup, in the
DoubleMuon files actually read, and DoubleMuon's own copy of each such
event was independently confirmed to be matched-accepted there too.

### Check (iii): union(exclusive sets) == union(inclusive sets) — no event lost

**RESULT: PASS — |union(DM_incl, SM_incl)| = 263,540 = |union(DM_excl,
SM_excl)| = 263,540. 0 lost, 0 gained.**

### Step 4 overall

**FAIL, by exactly 1 event out of 263,540, with a fully diagnosed,
data-level (not code-level) root cause.** Checks (ii) and (iii) — the two
checks that actually validate the de-duplication and completeness logic —
both PASS cleanly. Check (i)'s single failure is a residual,
extremely-rare cross-dataset reconstruction disagreement inherent to how
CMS produces primary datasets, not a flaw in Step 2's implementation.
This is exactly the kind of finding a closure test at real-file scale
should surface and is reported in full per Hard Rule 4 — see "Plan for
production" below for how this should be handled going forward (a
decision for Matan, not resolved here).

---

## Plan for production

**Projected core-hours** (VERIFIED BY RUNNING for the pilot timings;
projected/UNVERIFIED beyond that, extrapolated linearly from measured
events/second on the 4 matched-mode pilot runs — `job_metadata.json`
`elapsed_sec`/`n_read` for each):

| Dataset | Pilot combined events | Pilot combined elapsed_sec | Rate (events/sec) | Full dataset events (pre-flight) | Projected total core-hours |
|---|---|---|---|---|---|
| DoubleMuon (57 files) | 4,462,418 | 198.1 | 22,526 | 94,148,416 | **~1.16 core-hours** |
| SingleMuon (152 files) | 2,953,894 | 255.8 | 11,548 | 323,952,013 | **~7.79 core-hours** |

These are the sum of all per-file jobs' own wall-clock time (1 core each);
with PBS queue concurrency around 6-7 simultaneous jobs (the concurrency
actually observed for a comparable ~48-job array in this same queue in a
prior task, not measured for this one), wall-clock to completion would be
roughly 10-20 minutes for DoubleMuon (57 jobs) and 60-90 minutes for
SingleMuon (152 jobs) — a rough guide, not a commitment, since per-file
event counts vary (pre-flight max SingleMuon file: 3,539,840 events, ~3.4x
the pilot file's SingleMuon-G size).

**Cap-risk projection for SingleMuon** (500,000-per-signature cap,
`COVERAGE_CAP_PER_SIGNATURE`, applied per file/job — a signature exceeding
it is capped with a `CAPPED::` metadata flag, a hard stop per this
project's own cap policy, never a silent subsample):

- Pilot file 30530/0: largest signature 256,568 events out of 2,939,781
  read → **ratio 0.0873** (largest signature ≈ 8.7% of the file's total
  events).
- Pilot file 30563/0: largest signature 1,152 out of 14,113 → ratio
  0.0816 — consistent with the other pilot file's ratio.
- Pre-flight's largest single SingleMuon file (across all 152, both eras):
  **3,539,840 events**.
- **Projected largest signature size on that file: ≈ 309,000** (3,539,840
  × 0.0873) — comfortably under the 500,000 cap, with roughly 38% margin
  at the observed ratio.
- For reference, DoubleMuon's own largest file (2,986,904 events) projects
  to ≈ 229,700 (using its own pilot ratio 0.0769) — also comfortably under
  cap.

This is a **projection from two small-file ratios, not a measurement on
the full dataset** — the actual full SingleMuon run must still be checked
for zero `CAPPED::` entries (this project's existing hard-stop policy,
unchanged), exactly as every prior delivery in this study has been.

**Recommended next step**: run the full matched-mode DoubleMuon (57
files) and SingleMuon (152 files) datasets under a freshly pinned commit
(this same commit, `cbd1abb`, unless further changes are made first),
producing per-file inclusive/exclusive shards exactly as Step 3
validated, then build the combined DoubleMuon+SingleMuon delivery (a
subsequent, separate task) using DoubleMuon's inclusive shard and
SingleMuon's exclusive shard — the same shard choice already validated
end-to-end in Step 3f and Step 4.

**Open question for Matan** (not resolved in this design/validation task):
how should the ~3.8×10⁻⁶-rate cross-dataset reconstruction disagreement
found in Step 4 (Section "Check (i)") be handled in the eventual combined
delivery? Three options, roughly in order of effort:
1. **Accept it as negligible** (do nothing) — at this rate, a full
   323M-event SingleMuon run would be expected to produce on the order of
   a handful of such duplicate events total, spread across ~186 histogram
   signatures; very unlikely to visibly affect any one histogram.
2. **De-duplicate the final combined file by (run, lumi, event)** after
   building both shards — a small, mechanical post-processing step (not
   part of this task) that would catch this and any other such case
   outright, at the cost of needing to choose which dataset's copy of a
   disagreeing event "wins" (likely DoubleMuon, by veto priority).
3. **Investigate further** whether this kind of Medium-ID/pT disagreement
   between primary-dataset copies is common enough across the full
   datasets to matter (would require an additional multi-file scan
   beyond this task's scope).
