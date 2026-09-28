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

*(filled in after the 10 pilot jobs complete — see below)*
