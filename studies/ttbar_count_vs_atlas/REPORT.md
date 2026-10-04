# Why our CMS histogram count looked so much smaller than ATLAS's

**Study:** run our own histogram-building pipeline on CMS simulated top-quark-pair
events (TTTo2L2Nu, CERN Open Data record 67801) with the trigger switched off, and
compare the result against ATLAS's 2,146 histograms in 135 categories.

Every number is marked **VERIFIED BY RUNNING** (with the file or command that
produced it) or **UNVERIFIED**.

---

## 1. The plain-language answer

**Our pipeline is not losing histograms. The sample we delivered was.**

When we run the exact same pipeline on CMS top-quark simulation with no trigger
requirement, we get **2,038 histograms in 127 categories** — against ATLAS's
**2,146 in 135**. That is 5% fewer histograms and 6% fewer categories: the same
ballpark, not the 2x shortfall that prompted the question.

The delivered CMS result that looked small — **960 histograms in 55 categories** —
is small for one dominant reason: it comes from a **muon-triggered** sample. To be
recorded at all, those events had to contain a muon. So every single one of its 55
categories contains a muon (**VERIFIED BY RUNNING**: all 55 of 55), and the whole
electron-only and no-lepton half of the category space is simply unreachable.

Breaking the gap down, at ATLAS's own counting threshold of 25 or more filled bins:

| | categories | histograms |
|---|---:|---:|
| ATLAS ttbar (Maryna's number — **UNVERIFIED**, reported not reproduced) | 135 | 2,146 |
| **CMS ttbar, no trigger, our rule** | **127** | **2,038** |
| our delivered CMS data (muon-triggered) | 55 | 960 |

Of the 127 categories CMS top simulation can populate, only **69 contain a muon**.
Requiring a muon therefore removes **58 of 127 categories — 46%** before any
question of statistics arises. The remaining step from 69 categories down to the
delivered 55, and from 1,227 muon-category histograms down to 960, is the ordinary
difference between a large simulated sample and a real triggered dataset.

Three secondary findings are worth stating because two of them were expected to
matter and turned out not to:

* **The combination machinery is identical.** Both codebases generate exactly the
  same 186 invariant-mass combinations over exactly the same 170 categories, with
  **zero** differences anywhere.
* **PR #31's dropping of events with 5 or more ordinary jets changes no histogram
  count at all.** It removes 762,859 events (1.9%), but the surviving histogram
  list is *identical* — same 2,038 names. It only changes what is inside 537 of
  them.
* **Overlap removal is the one selection choice that does move the count**, and it
  moves it in the direction of *fewer*: switching our jet-lepton cleaning off adds
  182 histograms. But the plot shows why we keep it — without it, a muon that is
  also reconstructed as a jet right beside itself creates a large spike of
  near-zero-mass "pairs" that is a reconstruction artefact, not physics.

**One open question, for Maryna.** PR #31 ships six configuration files. I used
`config.yaml`, because both of its submit scripts hardcode it and it is the only
one capable of an MC run. A second file writes into Maryna's own directory, but it
sets `parse_mc: false`, reads only 3 files, and uses photons instead of b-jets —
so it cannot be the one behind an ATLAS ttbar MC run. This is **UNVERIFIED** and
worth one confirming question, because if the 2,146 came from different settings,
the category comparison would not be like-for-like.

---

## 2. What was done, step by step

### Step 1 — branch

Created `investigate/ttbar-count-vs-atlas` from `feature/cms-mc-weights-v2`
(`c89d0f0`) and merged `deliver/all-datasets-bumpnet` (`da140cc`) into it. Both
heads were exactly as expected. **VERIFIED BY RUNNING** (`git rev-parse`,
`git rev-list --parents -n 1 4e9e089`). The merge was clean; only
`run_dataset_on_file.py` was touched by both branches and it auto-merged inside
the `--is-mc` and rare4 code paths. Neither source branch was written to — both
are still at their original SHAs on the fork.

### Step 2 — are the combinations the same? Yes, exactly

`step2_enumerate.py` was executed twice, once with our checkout on `PYTHONPATH`
and once with a read-only checkout of upstream `refs/pull/31/head` (`81dd40a`);
each run imports only its own `services.calculations.*` and hard-fails if it
resolves the wrong repository. Each side read its own configuration source — ours
the constants the production driver passes, PR #31 its own `config.yaml`.

**VERIFIED BY RUNNING** (`evidence/step2_comparison.json`, `STEP2_COMBINATIONS.md`):

* **186** combination patterns on both sides, and the two sets are **identical**
* **170** categories under the rule (e, mu, j, b each 0-4; e+mu+b <= 4; >= 2 objects)
* **3,258** (category, combination) pairs allowed on each side
* **0** categories where the combination sets differ

The combinatorics are therefore ruled out as a cause. The only naming difference is
cosmetic: we always write all six object types (`1e_2m_3j_0g_0t_1b`), PR #31 writes
only the types present (`1e_2m_3j_1b`).

### Step 3 — the new study mode, and proof it broke nothing

Added `--population notrigger` to `run_dataset_on_file.py`. It is **refused unless
`--is-mc` is also given** (**VERIFIED BY RUNNING** — both error paths were
exercised), because it removes the HLT requirement, the golden-JSON filter and the
dataset de-duplication, none of which is acceptable on real data. It makes one
pass per file with the unchanged object definitions and the same ">= 2 selected
objects" gate, and writes three raw, unweighted variants:

| variant | final-state rule | overlap removal |
|---|---|---|
| (a) `rare4` | our delivered rule: e+mu+b > 4 rejected, all light jets kept, >= 5 labelled `4j` | on |
| (b) `pr31` | as (a) but events with >= 5 light jets **dropped**, reproducing PR #31 | on |
| (c) `pr31_noOR` | as (b) without jet-lepton dR < 0.4 cleaning — **diagnostic only** | off |

**Proof 1 — data mode is unchanged. PASS.** The 4 data pilot files were re-run
from a pinned checkout and compared against the delivered production output:
**32 shard comparisons** (4 files x 4 shard types x inclusive/exclusive), **0
mismatched signatures, 0 metadata mismatches**, and no notrigger shard or
diagnostics block appears in a data-mode run. **VERIFIED BY RUNNING**
(`evidence/step3_data_regression_result.json`). The baseline was produced at
`635d261`, and `git diff 635d261 da140cc -- run_dataset_on_file.py` is empty, so
it is what `da140cc` produces.

**Proof 2 — matched MC mode is unchanged. PASS.** One TTTo2L2Nu file was re-run
with `--population matched --is-mc` and compared against the paused MC v2 run's own
output for that file: **12 shard comparisons** (6 mass, 6 weight), **0 mismatched
signatures, 0 metadata mismatches**, including the Runs-tree sums and the genWeight
sum. **VERIFIED BY RUNNING** (`evidence/step3_mc_identity_result.json`). The paused
run was opened read-only throughout and never modified.

### Step 4 — pilot on 2 files. All checks PASS

**VERIFIED BY RUNNING** (`evidence/step4_pilot_checks.json`):

* (a) Restricted to final states with <= 3 light jets — the region where variants
  (a) and (b) must agree — they match **row for row**: 1,649 and 1,906 signatures
  compared, **0 mismatched, 0 unmatched**.
* (b) Variant (b) has **no final state with more than 4 of any type**. Proved from
  the shards, not the label text: the writer inserts one `final_state_counts` row
  per *raw* final state, so a label carrying more than one row is one that
  something was capped onto. Variant (b) has **zero** such labels; variant (a) has
  21 and 26, and **every one of them is a `4j` label** — exactly the pooling the
  rare4 rule is meant to do.
* (c) The counter arithmetic holds for every variant in both files.

### Step 5 — the full run

All **49** files of record 67801 (count **VERIFIED BY RUNNING**:
`fetch_file_list(67801)` returns 49), one PBS job each, from a checkout pinned to
the pushed commit `05062d0`. **49/49 finished, 0 failed**, no traceback, OOM or
assertion in any log; every `job_metadata.json` records that same commit.

**VERIFIED BY RUNNING** (aggregated over the 49 `job_metadata.json` files):

| | |
|---|---:|
| events read | **43,546,000** |
| sum of `genWeight`, all events (information only, never applied) | 3,140,127,233.69 |
| sum of `genWeight`, gate-passing events | 2,953,566,089.71 |

| variant | passing the >= 2-object gate | rejected e+mu+b > 4 | dropped >= 5 light jets | into combinations |
|---|---:|---:|---:|---:|
| rare4 | 40,947,069 | 88,738 | 0 | 40,858,331 |
| pr31 | 40,947,069 | 88,738 | 762,859 | 40,095,472 |
| pr31_noOR | 41,435,020 | 136,007 | 2,040,599 | 39,258,414 |

94% of simulated events pass the >= 2-object gate once the trigger is removed,
against roughly 5% under the DoubleMuon trigger-matched selection.

### Step 6 — the histograms

Built with the delivery's own post-processing chain, imported unmodified: fixed
10 GeV bins over 0-10 TeV, the 115 GeV Z-peak cutoff on same-flavour dilepton
channels, the 10 TeV max-mass cutoff, peak removal, the first-empty-bin split, the
>= 100-events rules, and cropping. The only addition is a third reporting threshold,
">= 25 filled bins", which is the wording ATLAS's number uses; the delivery's own
thresholds (> 25 and > 30) are reported alongside and are untouched.

**VERIFIED BY RUNNING** (`STEP6_RESULTS.md`, `evidence/step6_summary.json`):

| funnel stage | rare4 | pr31 | pr31_noOR |
|---|---:|---:|---:|
| names with >= 1 event | 3,987 | 2,960 | 2,843 |
| after >= 100 events per final state | 2,325 | 2,315 | 2,459 |
| after post-processing (>= 100 main events) | 2,136 | 2,136 | 2,343 |
| **>= 25 filled bins** | **2,038** | **2,038** | **2,220** |
| > 25 filled bins | 2,028 | 2,028 | 2,203 |
| > 30 filled bins | 1,955 | 1,955 | 2,101 |

| categories at >= 25 bins | has >= 1 muon | electrons, no muon | no lepton | total |
|---|---:|---:|---:|---:|
| rare4 | 69 | 36 | 22 | **127** |
| pr31 | 69 | 36 | 22 | **127** |
| pr31_noOR | 62 | 35 | 22 | **119** |
| delivered CMS data | 55 | 0 | 0 | **55** |

All **18** ROOT files (3 variants x 3 thresholds x uncropped/cropped) were read back
with **real PyROOT 6.40.02** from the CVMFS LCG view — not the uproot that wrote
them. All 9 pairs PASS. **VERIFIED BY RUNNING**
(`evidence/real_root_verify_<variant>_<threshold>.json`).

### Step 7 — the difference table

Full table in `STEP7_DIFFERENCES.md`, every row marked RAN or READ. Findings
(i)-(iv) are resolved in section 4 below.

### Step 8 — the ATLAS comparison tool

`compare_with_atlas.py` normalises the two naming conventions — our `ROI_` prefix
and `_width_10` suffix, our trailing `x`, and our habit of writing zero-count object
types that ATLAS omits — so `mass_e0m0_cat_1e_2m_3j_1b` and
`ROI_mass_e0m0_cat_1ex_2mx_3jx_0gx_0tx_1bx_width_10` both land on the same category.
It emits the both / ATLAS-only / CMS-only category and histogram lists with
per-category counts.

Both self-tests PASS. **VERIFIED BY RUNNING** (`evidence/step8_selftest.json`):
our delivered file against itself matches 960/960 with 0 unmatched; a synthetic
ATLAS-style file built by re-spelling 12 of our names plus 2 ATLAS-only categories
matches all 12 and correctly reports exactly the 2 as ATLAS-only. It also
independently confirms the delivered CMS file is 960 histograms in 55 categories.

How to run it when the ATLAS file arrives: `HANDOFF.md`, section 8.

### Step 9 — plots

In `plots/`, committed:

1. `1_categories_by_lepton_content.png` — categories per variant split by lepton
   content, with the 55-category CMS data delivery as a reference bar.
2. `2_per_category_pr31_vs_cms_data.png` — per-category histogram counts, variant
   (b) against the CMS data delivery, for all 54 shared categories.
3. `3_example_histograms.png` — the largest, the median, and one right at the
   25-bin boundary.
4. `4_overlap_removal_effect.png` — one category with and without overlap removal,
   on a log scale.

---

## 3. The headline numbers, and what explains the gap

At ATLAS's own threshold (>= 25 filled bins and >= 100 events):

| | categories | histograms |
|---|---:|---:|
| ATLAS ttbar, PR #31 (reported, **UNVERIFIED**) | 135 | 2,146 |
| CMS ttbar (a) rare4 — no trigger | 127 | 2,038 |
| CMS ttbar (b) pr31 — no trigger | 127 | 2,038 |
| CMS ttbar (c) pr31_noOR — diagnostic | 119 | 2,220 |
| our delivered CMS **data** | 55 | 960 |

**CMS ttbar reaches 95% of ATLAS's histogram count and 94% of its category count.**
There is no large unexplained deficit in our pipeline.

How much of the 960 -> 2,038 gap each cause explains, **VERIFIED BY RUNNING**:

| cause | effect on categories | effect on histograms |
|---|---|---|
| **muon trigger** (delivered data needs a muon; the study does not) | **58 of 127 categories, 46%**, are structurally unreachable | **811 of 2,038 histograms, 40%**, live in those categories |
| sample size and type (large simulated sample vs real triggered data) within muon categories | 69 -> 55 | 1,227 -> 960 |
| PR #31's >= 5-light-jet drop | **none** | **none** — identical 2,038-name list |
| our overlap removal | +8 categories when switched off (127 vs 119) | +182 histograms when switched off (2,220 vs 2,038) |
| combinatorics, binning, Z-peak, max-mass, peak removal, outlier split | **none** — identical code | **none** |

The residual 2,038 vs 2,146 (5%) is not attributed here. It is the size one would
expect from the remaining object-level differences (eta ranges, lepton ID and
isolation, b-tag working point, ATLAS vs CMS detector acceptance) plus whatever
difference there is in sample size — **UNVERIFIED**, since the ATLAS side was not
re-run.

### The >= 5-light-jet result, in detail

This is the most surprising outcome. Variants (a) and (b) differ by 762,859 dropped
events, yet **VERIFIED BY RUNNING**:

* the two produce the **identical set of 2,038 histogram names**;
* **1,501 of the 2,038 have identical contents**; only **537 differ**;
* every large difference is in a `4j` category — e.g.
  `mass_j0j1b0_cat_0e_0m_4j_0g_0t_1b` has 165,551 more entries in (a);
* variant (a) keeps 2.94% more entries overall (244,091,224 vs 237,116,299).

So PR #31's bug changes *how much data lands in the 4-jet categories*, not *which
histograms exist*. For a BumpNet search that means slightly reduced statistics in
the busiest categories, not missing search channels.

---

## 4. Findings (i)-(iv): confirmed or refuted by running

All four were checked by **executing PR #31's own code** from the read-only
checkout, not by reading it.

**(i) >= 5 light jets kept at parsing but dropped at mass calculation — CONFIRMED.**
PR #31's `apply_parsing_event_selection` keeps events with 5 and 6 light jets, with
all their jets, and explicitly overrides the configured light-jet maximum to
infinity ("Additional light jets must not reject an otherwise valid final state").
It rejects events with more than 4 non-light-jet objects (1 muon + 4 b-jets is
dropped; 1 muon + 3 b-jets is kept). Its `IMCalculator.final_state_counts()` then
returns a final state for 3 and 4 light jets but **nothing at all** for 5 or 6. Our
driver's own grouping function keeps all four and labels 5j and 6j as `4j`.
**VERIFIED BY RUNNING** (`evidence/step7_pr31.json`, `evidence/step7_ours.json`).
Measured cost on real CMS ttbar: 762,859 events (1.9%), 0 histograms.

**(ii) No jet-lepton overlap removal in PR #31 — CONFIRMED.** A light jet 0.1 away
in dR from a selected muon survives PR #31's whole parse-and-select path untouched
(1 -> 1 jets); the same jet is removed by our `select_and_split_jets` with cleaning
on (1 -> 0) and kept with it off. No deltaR or overlap code exists anywhere in PR
#31. **VERIFIED BY RUNNING.**

**(iii) `trigger_config: enabled: false`; btagDeepFlavB 0.5 vs our 0.2598; e/mu/b
capped at 4 — CONFIRMED**, read out of the config that applies them, with two
clarifications. PR #31's `particle_counts` also lists `jets: max 4`, but that bound
is overridden to infinity in code (see (i)), so it is not in force. And for the
ATLAS run itself the b-tag threshold in force is the DL1d one (2.51), not either
`btagDeepFlavB` value. **VERIFIED BY RUNNING.**

**(iv) Upstream #27 (grid-aligned outlier split) missing from PR #31 — CONFIRMED,
with a correction that matters.** `_split_by_first_empty_bin` was run on identical
probe arrays in all three codebases. On the decisive probe (40 values at 205, 40 at
210, 40 at 250 GeV): upstream master splits into 80 main + 40 outliers; **PR #31
does not split at all** (120 main, 0 outliers); **and neither do we** (120, 0).
`post_processing_pipeline.py` is md5-identical between our branch and PR #31
(`c0adb880...` both; upstream master `1fb76582...`). **So #27 is missing from PR
#31, but it is missing from our side in exactly the same way and cannot explain any
part of the ATLAS/CMS difference.** **VERIFIED BY RUNNING**
(`evidence/step7_split_{ours,pr31,upstream_master}.json`).

---

## 5. Current state

* branch `investigate/ttbar-count-vs-atlas` on `github.com/MatanBerko/atlas-utilization`
* study code, evidence and plots: `studies/ttbar_count_vs_atlas/`
* ROOT files and manifests:
  `output/cms_datasets/studies/ttbar_count_vs_atlas/<variant>/`
* per-file shards: `work/ttbar_count_vs_atlas/step5_full/job_<0..48>/`
* nothing was pushed, filed or commented upstream; no pull request was opened
  anywhere; the paused MC v2 production was not touched; no delivered product
  changed.

## 6. The logical next step

Run `compare_with_atlas.py` against Maryna's ATLAS BumpNet ROOT file, once per
variant — **variant (b) `pr31` is the like-for-like comparison**, since it
reproduces PR #31's >= 5-light-jet behaviour. That turns the aggregate "127 vs 135
categories" into a named list of which categories each side has and the other does
not, which is the question actually worth answering next. Everything needed is
written and self-tested; the command is in `HANDOFF.md` section 8.

Worth asking Maryna at the same time: which of PR #31's six config files produced
the 2,146 (see the caveat in section 1), and whether the ATLAS ttbar sample is
dilepton-only like our TTTo2L2Nu or also includes one-lepton decays — the latter
would populate different categories and would be a cleaner explanation of the
residual 5% than object-level cut differences.
