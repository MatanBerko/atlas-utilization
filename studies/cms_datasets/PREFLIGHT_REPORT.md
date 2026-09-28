# Pre-flight report: 7-dataset CMS 2016 G+H BumpNet track

Scope: this is the **preparation step only** (branch setup, trigger-only
pre-flight scan, generalized driver, regression check, small pilot). No
full-dataset runs, no deliveries, no merging into BumpNet histograms
happen in this document or its underlying jobs.

Branch: `deliver/all-datasets-bumpnet`, forked from `origin/master`
(commit `4f50b99`), with `origin/survey/full-inventory` and
`origin/deliver/doublemuon-bumpnet` merged in (both merges clean, no
conflicts). Every number below is labelled **VERIFIED BY RUNNING** (with
the evidence file or command) or **UNVERIFIED** (with the reason).

Evidence files (all committed under `studies/cms_datasets/evidence/`):
- `record_file_lists.json` — Step 0 portal file-list/count verification.
- `preflight_summary.json` — Step 1 merged pre-flight results (from 127
  PBS jobs covering all 732 files).
- `step3_regression_report.json` — Step 3 regression-check output.
- `pilot_summary.json` — Step 4 pilot results.

---

## Step 0: record verification

**VERIFIED BY RUNNING** (`fetch_record_file_lists.py`, live portal API
calls, `studies/cms_datasets/evidence/record_file_lists.json`):

| Dataset | Record G | Files G | Record H | Files H | G+H | Expected (task brief) | Match |
|---|---|---|---|---|---|---|---|
| DoubleMuon | 30522 | 29 | 30555 | 28 | 57 | 57 | ✅ |
| DoubleEG | 30521 | 47 | 30554 | 86 | 133 | 133 | ✅ |
| MuonEG | 30528 | 29 | 30561 | 19 | 48 | 48 | ✅ |
| SingleMuon | 30530 | 70 | 30563 | 82 | 152 | 152 | ✅ |
| SingleElectron | 30529 | 71 | 30562 | 80 | 151 | 151 | ✅ |
| JetHT | 30525 | 70 | 30558 | 72 | 142 | 142 | ✅ |
| MET | 30526 | 17 | 30559 | 32 | 49 | 49 | ✅ |

All 7 datasets match the task brief's expected file counts exactly, and
the filepage API's own file count matches the portal's separately-reported
`number_files` metadata field for every one of the 14 records — **0
mismatches**. Total: **732 files** across all 14 dataset×era records.

---

## Part 1: trigger-only pre-flight scan

**VERIFIED BY RUNNING**: 127 PBS array jobs (queue `N`, batches of ≤6
files each), covering all 732 files. **0 job failures** (every job's
`/usr/bin/time -v` wrapper reports `Exit status: 0`).

### (a) Path presence

All 732 files were checked for every HLT path this study needs (all 7
datasets' own trigger paths, the MuonEG non-DZ paths, all nested-reference
pairs, and the MET higher-threshold candidates).

**One path is genuinely absent from a large fraction of files:**
`HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL` (a MuonEG non-DZ
reference path — never used as an actual trigger requirement anywhere in
this study, only read for the Part 1(c) prescale test) is **missing from
367 of 732 files, all of them Run2016H**, at a consistent ~89–95% rate
within every dataset's own H-era files (MuonEG 18/19, DoubleMuon 25/28,
JetHT 65/72, MET 29/32, DoubleEG 77/86, SingleElectron 75/80, SingleMuon
78/82). This pattern — present in a small minority of H-era files,
absent from the rest, across every dataset uniformly — is the signature
of a genuine **mid-Run2016H HLT-menu change**: this path appears to have
been retired from the trigger menu partway through the H run period, so
only files from the earliest H-era runs still carry the branch. This
does not affect anything this study actually triggers on (MuonEG's own
trigger set uses only the two DZ paths); it only reduces the sample size
available for the corresponding Part 1(c) prescale test (105 usable runs
instead of ~155 — see below).

Every OTHER path this study needs (every dataset's own trigger paths, and
every other reference/nested path) is present in **100% of the 732
files** — no other gaps found.

### (b) Menu gaps

**5 (dataset, run) flags** where a dataset's own trigger path fired zero
times despite the dataset having golden events in that run — **all 5
concentrated on a single run, 283469 (Run2016H)**, and all with very
small golden-event counts for that run specifically (8–212 events,
roughly 2–3 orders of magnitude below this study's typical per-run golden
population of tens of thousands): DoubleEG's own DZ path (212 golden
events, 0 fires), DoubleMuon's both DZ paths (8 golden events, 0 fires
each), MET's `HLT_PFMET170_NotCleaned` (106 golden events, 0 fires), and
SingleMuon's `HLT_IsoMu24` (52 golden events, 0 fires). The small,
consistent golden-event counts across independently-processed datasets
for this one run number, together with zero fires for a normally
high-rate path, strongly suggest run 283469 is an unusually short/partial
run (e.g. a brief calibration or end-of-fill run) rather than a genuine
per-path menu gap — but this is **UNVERIFIED**: this study did not
cross-check run 283469 against the CMS run registry/RunSummary, which is
outside its scope. No other run showed a zero-fire flag for any of the
7 datasets' own trigger paths.

**MuonEG DZ-vs-non-DZ activity (task's explicit question):**
- `HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ` /
  `HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ` (the DZ paths): **at
  least one fires in every run of Run2016G with golden MuonEG
  events — TRUE.**
- `HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL` /
  `HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL` (the non-DZ paths): **at
  least one fires in every run of Run2016H with golden MuonEG
  events — TRUE** (this holds even though the second non-DZ path is
  absent from most H-era files per (a) above — the first non-DZ path,
  `HLT_Mu23_..._IsoVL`, is present and active in every H-run).

### (c) Prescale test

| Path pair | Source dataset | Method | Ratio min / median / max | Usable runs | Verdict |
|---|---|---|---|---|---|
| `HLT_PFJet450` vs `HLT_PFJet500` | JetHT | nested | 1.000 / 1.000 / 1.000 | 155 | **unprescaled (tested)** |
| `HLT_IsoMu24` vs `HLT_IsoMu27` | SingleMuon | nested | 0.997 / 0.998 / 0.999 | 155 | **unprescaled (tested)** |
| `HLT_IsoTkMu24` vs `HLT_IsoTkMu27` | SingleMuon | nested | 1.000 / 1.000 / 1.000 | 156 | **unprescaled (tested)** |
| `HLT_Ele27_WPTight_Gsf` vs `HLT_Ele32_eta2p1_WPTight_Gsf` | SingleElectron | nested | 1.000 / 1.000 / 1.000 | 155 | **unprescaled (tested)** |
| `HLT_PFMET170_HBHECleaned` vs `HLT_PFMET300` | MET | nested | 1.000 / 1.000 / 1.000 | 155 | **unprescaled (tested)** |
| `HLT_PFMET170_NotCleaned` vs `HLT_PFMET300` | MET | nested | 0.000 / 0.047 / 0.829 | 155 | **prescaled in the large majority of runs** (median ratio 4.7% of expectation) |
| `HLT_Mu23_..._IsoVL` (non-DZ) vs `..._IsoVL_DZ` | MuonEG | nested | 0.155 / 0.397 / 1.000 | 155 | **prescaled in the large majority of runs** (87 of 155 usable runs below the 0.95 threshold) |
| `HLT_Mu8_..._IsoVL` (non-DZ) vs `..._IsoVL_DZ` | MuonEG | nested | 0.000 / 1.000 / 1.000 | 105 (reduced — see (a)) | **prescaled in a substantial minority of runs** (35 of 105 usable runs below threshold) |

Interpretation: **`HLT_PFHT900`'s own effective rate is NOT independently
tested here** (no valid nested reference exists for it — see fallback
below); the four "unprescaled" verdicts above are as solid as this method
gets (ratio pinned to 1.000 or within half a percent, consistently, across
every one of 155–156 runs). The **`HLT_PFMET170_NotCleaned` and both
MuonEG non-DZ paths are genuinely, substantially prescaled** relative to
their nested stricter references — physically consistent with CMS's own
well-known 2016 convention of keeping a "backup"/monitoring version of a
primary path (the "NotCleaned" MET variant, the non-DZ dilepton variants)
at a heavily reduced rate once a primary "Cleaned"/DZ version exists.
**This directly supports the choice already made in this task's trigger
sets** (DZ paths for MuonEG, `HBHECleaned` implicitly favoured for MET
by using both — see Recommendations).

**Fallback method (no valid nested reference — WEAKER, cannot prove
absence of a prescale constant across every run):**

| Path | Reference (same dataset) | Ratio min / median / max | Verdict |
|---|---|---|---|
| `HLT_PFHT900` | `HLT_PFJet450` | 1.219 / 1.443 / 1.772 | **cannot be determined** (ratio >1 and drifting — expected, since PFHT900 and PFJet450 select different, only partially-overlapping event populations; this ratio cannot itself reveal a PFHT900 prescale) |
| `HLT_Mu17_..._DZ` | `HLT_Mu17_..._TkMu8_..._DZ` | 0.933 / 0.972 / 1.007 | **cannot be determined** (ratio close to 1 and stable, mildly suggestive of no large relative prescale between DoubleMuon's own two DZ paths, but not a proof) |
| `HLT_Ele23_Ele12_..._DZ` | `HLT_Ele27_WPTight_Gsf` | 1.078 / 1.252 / 1.469 | **cannot be determined** (comparing across genuinely different trigger objects/thresholds) |

### (d) Overlap matrix

**VERIFIED BY RUNNING** — fraction of dataset X's own golden+triggered
events that also pass dataset Y's own trigger set (rows = X, columns = Y;
diagonal is 1 by definition):

| X＼Y | DoubleMuon | DoubleEG | MuonEG | SingleMuon | SingleElectron | JetHT | MET |
|---|---|---|---|---|---|---|---|
| **DoubleMuon** | 1.000 | 0.000 | 0.004 | 0.495 | 0.000 | 0.001 | 0.000 |
| **DoubleEG** | 0.000 | 1.000 | 0.003 | 0.000 | 0.539 | 0.001 | 0.000 |
| **MuonEG** | 0.013 | 0.005 | 1.000 | 0.084 | 0.049 | 0.002 | 0.002 |
| **SingleMuon** | 0.072 | 0.000 | 0.004 | 1.000 | 0.001 | 0.000 | 0.001 |
| **SingleElectron** | 0.000 | 0.053 | 0.003 | 0.001 | 1.000 | 0.001 | 0.001 |
| **JetHT** | 0.001 | 0.001 | 0.001 | 0.002 | 0.003 | 1.000 | 0.012 |
| **MET** | 0.001 | 0.001 | 0.001 | 0.009 | 0.006 | 0.026 | 1.000 |

Heatmap (with numbers in cells): `plots/overlap_matrix_heatmap.png`.

**Exclusive fraction per dataset** (passes own trigger, fails every
higher-veto-priority dataset — DoubleMuon > DoubleEG > MuonEG >
SingleMuon > SingleElectron > JetHT > MET):

| Dataset | Exclusive fraction | Own-trigger total events (both eras) |
|---|---|---|
| DoubleMuon | 1.0000 | 30,943,565 |
| DoubleEG | 0.9999 | 17,599,145 |
| MuonEG | 0.9820 | 10,137,471 |
| SingleMuon | 0.9240 | 211,487,190 |
| SingleElectron | 0.9447 | 180,509,973 |
| JetHT | 0.9937 | 33,311,374 |
| MET | 0.9603 | 14,866,112 |

All numbers here are internally consistent (e.g. SingleMuon's 7.24%
overlap with DoubleMuon plus its small MuonEG overlap accounts for its
92.40% exclusive fraction) — this is a straightforward sum/ratio of the
per-run overlap counts, not a separate/re-derived quantity.

Required PNGs (all committed under `studies/cms_datasets/plots/`):
- `nested_ratio_HLT_PFJet450__vs__HLT_PFJet500.png` (JetHT)
- `nested_ratio_HLT_PFMET170_HBHECleaned__vs__HLT_PFMET300.png` and
  `nested_ratio_HLT_PFMET170_NotCleaned__vs__HLT_PFMET300.png` (MET)
- `nested_ratio_HLT_Mu23_..._vs_..._DZ.png` and
  `nested_ratio_HLT_Mu8_..._vs_..._DZ.png` (MuonEG — both fail the
  unprescaled test, so both are plotted per the task's own "any path that
  fails the test" instruction)
- `overlap_matrix_heatmap.png`

---

## Part 2: generalized per-file driver

`studies/cms_datasets/cluster/run_dataset_on_file.py`, built on
`studies/cms_coverage/per_dataset/triggered/cluster/run_per_dataset_on_file.py`'s
own conventions (imports `services.parsing.trigger_requirements.apply_trigger_requirement`,
`studies.m0m1j0_cms.selection`, `services.calculations.combinatorics.get_all_combinations`,
`services.pipelines.im_pipeline._calculate_combination_invariant_mass`,
`services.calculations.im_calculator.IMCalculator`, and
`services.storage.sqlite_shards.SqliteArrayShardWriter` — none
reimplemented). Order: chunked read (300,000-event chunks, 4 retries) →
golden JSON → own trigger (`apply_trigger_requirement`, mode `any`) →
object selection (unchanged) → population gate (`--population generic`
default, or `v0` for the regression check only) → all 186 combinations
(asserted) → raw float32 masses into two `SqliteArrayShardWriter` shards
per job (`dataset_shard_inclusive.sqlite`, `dataset_shard_exclusive.sqlite`).

**Inclusive/exclusive de-duplication without doubling the combinatorics
cost**: the (expensive) per-combination mass array is computed exactly
once per (final state, combination), via the real, unmodified
`_calculate_combination_invariant_mass`. The exclusive sub-array is then
obtained by a cheap (count-only, no vector math), independently-verified
boolean mask recomputation (`_recompute_exact_count_row_mask`, mirroring
`filter_events_by_particle_counts`'s own count-based row-reduction
formula) — every such mask is asserted to have exactly the same length as
the mass array it splits before being used, so any future divergence
between this recomputation and the shared function's own internal logic
would fail loudly rather than silently miscount events. A single boolean
`is_exclusive` array, aligned to the population-gate output via a
byte-identical copy of `physics_calcs.group_by_final_state`'s own
grouping formula (`_group_by_final_state_with_mask`, needed only because
the shared function does not itself expose its internal mask), tracks
which selected events are exclusive to this dataset for the whole job.
Veto-path branches (every higher-priority dataset's own trigger paths)
are read alongside the object-selection branches and **fail loudly** if
missing from a file — never silently treated as "did not fire" — per
this task's own instruction (distinct from Part 1's diagnostic scan,
which tolerates and reports missing paths instead of failing).

`--population v0` calls `studies.m0m1j0_cms.selection.select_event_selection_cutflow`
exactly as `run_coverage_on_file.py` does, and exists ONLY for the Step 3
regression check (meaningful only for `--dataset-label DoubleMuon`, whose
own two trigger paths are byte-identical to that function's own hardcoded
`TRIGGER_BRANCHES` — see the script's own module docstring for why this
makes the driver's "own trigger" step idempotent, not a double-filter, in
that one case).

Each job's `job_metadata.json` records: git commit, record/file
identifiers, `n_read`, counts after golden-JSON/trigger (per path)/gate,
`n_exclusive`, `n_vetoed_by_each_higher_dataset`, wall time, and (via the
PBS script's `/usr/bin/time -v` wrapper) peak memory — plus the Step 2
diagnostics (leading muon/electron pT, low-mass opposite-sign dimuon
mass/dR, raw dilepton masses) and `max_signature_size_this_job` /
`n_capped_signatures` (see Step 4 below for what these showed in
practice).

**Correctness note on a bug found and fixed during this task**: an
earlier version of this script recorded the `CAPPED::<signature>`
shard-metadata value using the array's size *after* the 500,000-event
subsample was already applied, so it always read `true_size=500000`
regardless of the real pre-cap size. This never affected the actual
written mass values (the subsampling itself was always correct — only
the diagnostic metadata string was wrong) and was fixed before any pilot
job ran (commit `952e2f8`); see Step 4 below for the real signature sizes
this affected.

---

## Part 3: regression check

**RESULT: PASS on every check, for every file.**

**VERIFIED BY RUNNING** (`studies/cms_datasets/cluster/compare_regression.py`,
`studies/cms_datasets/evidence/step3_regression_report.json`), on 3
DoubleMuon files also processed by the existing delivered coverage run
(`/storage/agrp/berkom/atlas-utilization/output/cms_coverage_full/`,
read-only): record 30522 (Run2016G) file indices 0 and 1, and record
30555 (Run2016H) file index 0.

| File | (i) v0 == old coverage_shard | (ii) generic ⊇ v0 | (iii) inclusive == exclusive (v0) | (iii) inclusive == exclusive (generic) |
|---|---|---|---|---|
| 30522 file 0 | **PASS** | **PASS** | **PASS** | **PASS** |
| 30522 file 1 | **PASS** | **PASS** | **PASS** | **PASS** |
| 30555 file 0 | **PASS** | **PASS** | **PASS** | **PASS** |

- **(i)**: every signature's mass array is exactly identical (same
  values, same count, order-insensitive) between `--population v0`'s
  output and the existing `coverage_shard.sqlite` — this also directly
  re-tests upstream master commit `b38f566`'s claim that its
  `sqlite_shards.py` reordering was behaviour-preserving, on real data,
  and confirms it. For record 30522 file 0 specifically: 42,602 selected
  events and 1,137 signatures in both the old and new outputs, byte-for-byte.
- **(ii)**: every one of v0's signatures (which, by construction, always
  has ≥2 muons and ≥1 non-b jet — that is what "final state" encodes)
  appears in `--population generic`'s inclusive shard with an identical
  array. Generic additionally contains extra final-state categories v0's
  own gate excludes entirely (e.g. zero-jet, jet-only, or single-muon
  categories) — the exact extra-category counts are in
  `step3_regression_report.json`'s own `check_ii_generic_superset_of_v0`
  block for each file.
- **(iii)**: DoubleMuon's inclusive and exclusive shards are identical in
  both population modes, confirming DoubleMuon's top veto priority means
  nothing is ever vetoed out of it — not merely assumed from the driver's
  own logic (`higher_priority` is empty for DoubleMuon), but checked
  directly against the real written shards.

---

## Part 4: pilot

**VERIFIED BY RUNNING**: 10 PBS jobs, `--population generic`, one Run2016G
and one Run2016H file (file index 0) for each of DoubleMuon, DoubleEG,
MuonEG, SingleMuon, SingleElectron. **0 job failures.** JetHT and MET were
NOT run beyond Part 1, per this task's own instruction.

### Per-job results

| Dataset | Era | n_read | n_after_gate | n_exclusive | excl. frac. | wall time (s) | peak mem (MB) | shard size (incl./excl., MB) |
|---|---|---|---|---|---|---|---|---|
| DoubleMuon | G | 2,315,223 | 509,193 | 509,193 | 1.0000 | 294.5 | 1857 | 4.375 / 4.375 |
| DoubleMuon | H | 2,147,195 | 506,927 | 506,927 | 1.0000 | 402.4 | 1740 | 4.332 / 4.332 |
| DoubleEG | G | 2,014,154 | 189,753 | 189,739 | 0.9999 | 199.6 | 1625 | 1.793 / 1.785 |
| DoubleEG | H | 843,234 | 75,882 | 75,877 | 0.9999 | 134.6 | 789 | 0.906 / 0.906 |
| MuonEG | G | 2,238,235 | 203,017 | 197,941 | 0.9750 | 549.0 | 1851 | 2.641 / 2.410 |
| MuonEG | H | 1,480,020 | 230,652 | 225,858 | 0.9792 | 393.1 | 1358 | 2.883 / 2.617 |
| SingleMuon | G | 2,939,781 | 635,002 | 505,583 | 0.7962 | 450.4 | 2067 | 5.406 / 4.129 |
| SingleMuon | H | 14,113 | 2,841 | 2,258 | 0.7948 | 35.5 | 110 | 0.152 / 0.121 |
| SingleElectron | G | 112,955 | 26,271 | 23,076 | 0.8784 | 79.6 | 183 | 0.438 / 0.309 |
| SingleElectron | H | 2,338,304 | 755,635 | 667,543 | 0.8834 | 326.6 | 1806 | 5.715 / 4.676 |

The two smallest rows above (SingleMuon H: 14,113 events; SingleElectron
G: 112,955 events) are **not representative** small files, not errors —
confirmed against Step 1's own per-file scan (see file-size variation
table below), both eras' file-index-0 file simply happened to be near the
small end of a very wide real distribution.

### Largest single-signature size vs. the 500,000-event cap

**No signature was capped in any pilot job** (`n_capped_signatures = 0`
everywhere), but two pilot jobs already reached roughly **half the cap
from a single file**: SingleMuon (G) had a signature with 266,065 events
(**53.2% of the 500,000 cap**), and SingleElectron (H) had one with
252,801 events (**50.6% of the cap**). Every other pilot job's largest
signature stayed well below the cap (11–35% of it; the two SingleMuon-H
and SingleElectron-G small-file jobs barely register at 0.2%/1.9%, again
consistent with those being unusually small files, not a different
regime). This cap is applied **per file, per job**, not per merged
dataset (see Part 2) — so it does not bound the eventual full-dataset
total for a signature, but a single SingleMuon or SingleElectron file
already reaching half the per-file cap on its own is worth the full-run
operators' attention (see Recommendations).

| Dataset | Era | Largest signature (events) | Fraction of 500,000 cap | Capped signatures |
|---|---|---|---|---|
| DoubleMuon | G | 178,018 | 0.356 | 0 |
| DoubleMuon | H | 173,559 | 0.347 | 0 |
| DoubleEG | G | 57,259 | 0.114 | 0 |
| DoubleEG | H | 25,210 | 0.050 | 0 |
| MuonEG | G | 69,629 | 0.139 | 0 |
| MuonEG | H | 80,610 | 0.161 | 0 |
| SingleMuon | G | **266,065** | **0.532** | 0 |
| SingleMuon | H | 1,186 | 0.002 | 0 |
| SingleElectron | G | 9,330 | 0.019 | 0 |
| SingleElectron | H | **252,801** | **0.506** | 0 |

(This reporting itself required a fix: an earlier version of
`run_dataset_on_file.py` recorded a capped signature's shard metadata
using its size *after* subsampling rather than before, so the metadata
string always read `true_size=500000` regardless of the real pre-cap
size. Fixed in commit `952e2f8`, before any pilot job ran — the table
above reflects the corrected code; capping never actually triggered in
this pilot in either version, so no data was ever mis-subsampled, only
the never-triggered diagnostic field would have been wrong.)

### File-size variation (real per-file event counts, from Step 1's own scan of all 732 files)

| Dataset | n files (G+H) | min events/file | median events/file | max events/file | total events (G+H) |
|---|---|---|---|---|---|
| DoubleMuon | 57 | 65,826 | 1,680,165 | 2,986,904 | 94,148,416 |
| DoubleEG | 133 | 7,084 | 1,272,688 | 2,925,390 | 164,185,704 |
| MuonEG | 48 | 610 | 1,391,231 | 2,240,429 | 63,091,128 |
| SingleMuon | 152 | 14,113 | 2,134,402 | 3,539,840 | 323,952,013 |
| SingleElectron | 151 | 26,484 | 1,862,526 | 3,146,526 | 282,385,002 |
| JetHT | 142 | 107,505 | 1,825,966 | 2,439,066 | 244,738,738 |
| MET | 49 | 101,107 | 1,461,153 | 2,696,788 | 66,747,616 |

File sizes vary by up to ~**3,700×** within a single dataset (MuonEG: 610
to 2,240,429 events). Because of this, a naive "average the 2 pilot
files' wall time and multiply by the dataset's total file count" cost
estimate is unreliable whenever a pilot file happens to land near either
end of this range (as SingleMuon's H file and SingleElectron's G file
both did here) — it would apply that one skewed per-file constant
uniformly to every file regardless of real size. **This report's cost
estimate instead scales by events, not files**: it combines the 2 pilot
files' own (events, wall-time) into one events/second rate, then
multiplies by the dataset's REAL total event count (summed directly from
Step 1's per-file reads above, not the portal's aggregate metadata).

### Per-dataset cost estimate for the full run

| Dataset | Pilot events/sec (combined) | Estimated total core-hours (event-rate method) | For comparison: naive per-file-average method |
|---|---|---|---|
| DoubleMuon | 6,404 | **4.08** | 5.52 |
| DoubleEG | 8,551 | **5.33** | 6.17 |
| MuonEG | 3,947 | **4.44** | 6.28 |
| SingleMuon | 6,079 | **14.80** | 10.26 |
| SingleElectron | 6,033 | **13.00** | 8.52 |

The two methods disagree most for SingleMuon and SingleElectron —
exactly the two datasets whose pilot sample included an outlier-sized
file — confirming the event-rate method is the more trustworthy one here.
**UNVERIFIED**: this still assumes the pilot's 2-file events/sec rate is
representative of every other file in the dataset; the fixed per-job
startup overhead (XRootD connection, golden-JSON load, imports — a few
seconds, roughly constant regardless of file size) means small files run
proportionally less efficiently than large ones, so this estimate is
biased slightly low for datasets with many small files and slightly high
for datasets dominated by large ones. Not quantifiable further without
running more pilot files.

**Proposed walltime/mem/io for the full runs** (JetHT/MET excluded, not
piloted): peak memory observed across all 10 pilot jobs was 110 MB–2,067
MB (largest for a 2.94M-event file); the current PBS request of `mem=8gb`
already has ~4× headroom over the largest file observed, including some
margin for the dataset's largest real files (up to 3.54M events,
~20% larger than the pilot's own largest). **Recommend keeping
`mem=8gb`, unchanged.** Wall time per file ranged 35.5–549.0 s (worst
case ~9.2 minutes, MuonEG); scaling MuonEG's own (slowest observed)
events/sec rate to the largest real file in any core dataset (SingleMuon,
3,539,840 events) gives an estimated worst-case single-file wall time of
~897 s (~15 minutes) — well inside the current `walltime=02:00:00`
request, which has substantial headroom and is **recommended unchanged**
(shortening it is not necessary and risks a rare, larger-than-expected
file being killed). `io=25` (MB/s) was accepted by the scheduler with no
apparent throttling in any of the 16 real-file jobs run in this task
(Step 3 + Step 4) — **recommend keeping `io=25`**; this task did not
measure actual achieved I/O throughput precisely (`/usr/bin/time -v`
reports block counts, not MB/s), so this is **UNVERIFIED** as a
precisely-tuned value, only as "sufficient in practice so far."

### Required diagnostic plots

All committed under `studies/cms_datasets/plots/`:
- `pilot_raw_dimuon_mass.png` (SingleMuon, DoubleMuon) and
  `pilot_raw_dielectron_mass.png` (DoubleEG, SingleElectron): both show a
  clean, sharp Z resonance. **Fitted/histogram peak position: 90.5 GeV**
  for all 4 dataset/era combinations that have enough dilepton statistics
  (1 GeV bins — consistent with the true Z mass, 91.19 GeV, within one
  bin's resolution). SingleMuon (H) shows negligible statistics, as
  expected from its 14,113-event pilot file.
- `pilot_leading_muon_pt.png` and `pilot_leading_electron_pt.png`, with
  the object cut (25 GeV) and trigger threshold (24 GeV muon / 27 GeV
  electron) marked: both show a clean turn-on exactly at the 25 GeV
  object cut with no events below it, and the expected trigger-threshold
  vs. object-cut relationship (trigger fires slightly below where the
  offline object cut then removes events). Fraction of events with
  leading muon pT in 25–28 GeV: **13.6% (G) / 13.3% (H)**. Fraction of
  events with leading electron pT in 25–30 GeV: **10.8% (G) / 8.5% (H)**.
- `pilot_low_mass_dimuon.png` (opposite-sign dimuon mass <5 GeV and dR,
  DoubleMuon + SingleMuon): the known collimated low-mass population is
  clearly visible and concentrated at very low dR. Fraction of these
  pairs below 2 GeV: DoubleMuon 67.1% (G) / 67.5% (H), SingleMuon 62.2%
  (G) / 60.0% (H). (This study only measures this population's size, per
  its own out-of-scope list — it does not investigate its origin.)

---

## Recommendations for the full runs

**These are recommendations, not measurements — every claim in this
section is either a direct restatement of a Part 1–4 finding above (cited)
or an explicit judgment call, marked as such.**

1. **JetHT: its own prescale test passes.** `HLT_PFJet450` vs
   `HLT_PFJet500` was tested directly (nested reference) across 155
   usable runs and came back exactly **unprescaled** (ratio 1.000 in
   every run — Part 1(c)). Recommend proceeding with JetHT's own trigger
   set (`HLT_PFHT900` OR `HLT_PFJet450`) unchanged for the full run.
   `HLT_PFHT900` itself has no valid nested reference and was only
   checked by the weaker fallback method (Part 1(c)) — **this is a real
   gap, not a pass**: recommend not treating `HLT_PFHT900` as confirmed
   unprescaled, only as "not contradicted by the (weak) evidence
   available."

2. **MET: mixed result — one of its two own paths is heavily
   prescaled.** `HLT_PFMET170_HBHECleaned` tested unprescaled (ratio
   1.000 across 155 runs), but `HLT_PFMET170_NotCleaned` tested
   **heavily prescaled** (median ratio 4.7% of expectation — Part 1(c)).
   Recommend the full run's MET trigger use `HLT_PFMET170_HBHECleaned`
   as the primary/confirmed-unprescaled path; keeping
   `HLT_PFMET170_NotCleaned` in the OR (as currently specified) does not
   hurt correctness (it can only add events, never remove them) but
   contributes disproportionately few extra events for its complexity —
   whether to keep both paths or simplify to `HBHECleaned` alone is a
   **judgment call for the group**, not something this data forces
   either way.

3. **MuonEG: use the DZ paths, not the non-DZ alternatives, for both
   eras.** Both non-DZ paths tested **substantially prescaled** relative
   to their DZ counterparts (Part 1(c): Mu23Ele12 non-DZ median ratio
   0.397, Mu8Ele23 non-DZ median ratio close to 1.0 but with 35 of 105
   usable runs below threshold and reduced statistics from the path's own
   mid-H-era menu retirement, Part 1(a)). This confirms the trigger set
   this task already specifies for MuonEG (the two DZ paths, both eras)
   is the right choice — **no change recommended**. Separately: this
   task's own Part 1(b) question is answered — the DZ paths are active
   in every run of Run2016G, and the non-DZ paths are active in every run
   of Run2016H — but that activity finding is about which paths *exist
   and fire*, not which are unprescaled; the DZ paths remain the
   recommended choice for both eras regardless.

4. **Run 283469 (Run2016H) should be treated as a known small/anomalous
   run, not investigated further here.** 5 independent (dataset, path)
   zero-fire flags all landed on this one run, all with atypically small
   golden-event counts (Part 1(b)) — plausibly a short calibration/partial
   run. **Recommend**: proceed with it included in the full run (nothing
   found here indicates its events are invalid), but flag it to the group
   if any downstream per-run diagnostic looks anomalous later, since this
   report did not cross-check it against the CMS run registry
   (UNVERIFIED, out of this task's scope).

5. **Watch SingleMuon and SingleElectron for the 500,000-event per-file
   signature cap in the full run**, even though it never triggered in
   this pilot. Two pilot jobs already reached ~50–53% of the cap from a
   single file (Part 4); since the cap is per-file (not per merged
   dataset), no single full-run file is guaranteed to exceed it, but the
   margin is real and worth monitoring once the full run actually
   executes — **this task does not recommend raising or otherwise
   changing the cap value itself** (out of scope, and not evidently
   necessary yet).

6. **Cost estimate and resource request**: proceed with `mem=8gb`,
   `walltime=02:00:00`, `io=25` unchanged for the full run of the 5 core
   datasets (Part 4) — all three have comfortable headroom over what was
   observed in the pilot. Estimated total core-hours for the 5 core
   datasets (event-rate method, Part 4): DoubleMuon 4.1, DoubleEG 5.3,
   MuonEG 4.4, SingleMuon 14.8, SingleElectron 13.0 — **total ≈ 41.6
   core-hours**, all individually well inside a single 2-hour walltime
   window per job since these are per-file, not per-dataset, job
   durations. JetHT and MET were not piloted (out of this task's scope),
   so no cost estimate is offered for them.

7. **Logical next step** (not this task's own decision to make, but the
   natural continuation): a full generic-population run of DoubleMuon
   first (cheapest, already regression-tested against the delivered
   coverage run), then the other 4 piloted core datasets, with JetHT and
   MET's own full runs deferred pending a decision on point 2 above.
