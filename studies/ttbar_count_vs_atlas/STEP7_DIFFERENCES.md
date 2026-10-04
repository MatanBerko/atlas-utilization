# Step 7 - selection, binning and post-processing: our CMS pipeline vs upstream PR #31

Two codebases are compared:

* **ours** - this branch, `investigate/ttbar-count-vs-atlas`, the CMS pipeline
  that produced `studies/cms_datasets/deliver/committed/muon_combined_rare4/`
  (960 histograms, 55 categories).
* **PR #31** - upstream `Zhavi221/atlas-utilization` `refs/pull/31/head`, head
  `81dd40a`, in a **read-only** checkout. Its `config.yaml` is the ATLAS
  configuration (`release_years: 2024r-pp`, cuts in MeV), i.e. the configuration
  behind Maryna's 2,146-histogram / 135-category ATLAS ttbar number.

Every row says whether the statement was established by **RUNNING** code or by
**READING** it. "RUNNING" means a script in this directory executed that
codebase's own function, imported from its own checkout, and the result is in
`evidence/`.

---

## 1. Object selection

| | ours | PR #31 | how established |
|---|---|---|---|
| muon pT | > 25 GeV | > 25 GeV (25000 MeV) | RUNNING (`step7_findings_check.py`, values read out of the modules/config that apply them) |
| muon \|eta\| | < 2.4 | < 2.5 | RUNNING |
| muon isolation | `pfRelIso04_all` < 0.15 | none configured | RUNNING |
| muon ID | `mediumId` | none configured | READ (`selection.select_muons` vs PR #31 `kinematic_cuts`) |
| electron pT | > 25 GeV | > 25 GeV | RUNNING |
| electron \|eta\| | < 2.5 | < 2.47 | RUNNING |
| electron ID / isolation | `cutBased >= 3` (medium) | `rel_isolation_max` 0.06 on the ATLAS `ptvarcone30...` field | RUNNING |
| jet pT | > 30 GeV | > 30 GeV | RUNNING |
| jet \|eta\| | < 2.5 | < 2.5 | RUNNING |
| jet ID | `jetId` tight | none configured | READ |
| photons, taus | **not read at all** | configured (`photons` pT > 25 GeV, `taus` pT > 20 GeV) but not in `objects_to_calculate` | READ |

The eta and ID differences are small and are the expected ATLAS-vs-CMS detector
differences; none of them is a plausible source of a 2x histogram-count gap.

## 2. b-tagging

| | ours | PR #31 | how established |
|---|---|---|---|
| discriminant | `Jet_btagDeepFlavB` | `Jet_btagDeepFlavB` (CMS branch) or DL1d (ATLAS) | READ |
| threshold | **0.2598** (DeepJet medium WP, UL2016 postVFP) | **0.5** for `btagDeepFlavB`; 2.51 for DL1d | RUNNING |
| split order | b/light split on RAW jets first, then pT/eta/ID cuts and cleaning on both | split after the kinematic cuts | READ |

Our threshold is looser, so on the same CMS events we would tag **more** b-jets
than PR #31's CMS setting would. For the ATLAS run that Maryna's number comes
from, the DL1d threshold is the one in force, not either `btagDeepFlavB` value.
**Confirms finding (iii)** on the b-tag threshold.

## 3. Overlap removal - **the clearest selection difference**

| | ours | PR #31 | how established |
|---|---|---|---|
| jet-lepton overlap removal | jets within dR < 0.4 of a selected lepton are removed | **none** | RUNNING |

Probe: one muon at (eta 0, phi 0) and one light jet at (eta 0, phi 0.1), dR = 0.1.
Our `selection.select_and_split_jets(..., apply_lepton_cleaning=True)` removes the
jet (1 -> 0 light jets); with `apply_lepton_cleaning=False` it keeps it. PR #31's
whole parse-and-select path keeps it (1 -> 1). There is no deltaR or overlap code
anywhere in PR #31's `services/`, `pipeline/`, `orchestration/` or `domain/`.
**Confirms finding (ii).** Its size on real CMS ttbar is measured by variant (c).

## 4. How many objects of a type an event may have - **the decisive difference**

| | ours | PR #31 | how established |
|---|---|---|---|
| cap on non-light-jet objects | e + mu + b <= 4, event rejected otherwise (the rare4 rule) | > 4 retained non-light-jet objects -> event rejected at parsing | RUNNING |
| cap on light jets at parsing | none | **none** - `apply_parsing_event_selection` explicitly overrides the configured light-jet `max: 4` to infinity, with the comment "Additional light jets must not reject an otherwise valid final state" | RUNNING |
| what happens to >= 5 light jets later | kept; the final-state label is display-capped to `4j`, so the event lands in the 4j category | **the event is dropped entirely**: `IMCalculator._is_valid_fs`, with `max_count_particle_in_combination = 4`, marks any final state with a per-type count above 4 invalid, and such events never enter a final-state group | RUNNING |

Probes run on both sides with 3, 4, 5 and 6 light jets plus 1 muon and 1 b-jet:

* PR #31 parsing: all four survive, with all their light jets retained.
* PR #31 parsing with 1 muon + 4 b-jets (5 non-light-jet objects): rejected.
  With 1 muon + 3 b-jets (4): kept.
* PR #31 `IMCalculator.final_state_counts()`: 3j -> `0e_1m_3j_1b`, 4j ->
  `0e_1m_4j_1b`, **5j -> no final state at all**, **6j -> no final state at all**.
* our driver's own `_group_by_final_state_with_mask` (the function the driver
  really uses - we inherit `IMCalculator._is_valid_fs` but never call it):
  3j, 4j, 5j and 6j all survive, with 5j and 6j labelled `0e_1m_4j_0g_0t_1b`.

**Confirms finding (i)**, including its internal-inconsistency character: PR #31
goes out of its way to preserve high-light-jet events at parsing and then discards
them at mass-calculation time.

Measured on real CMS ttbar (Step 4 pilot, 1,396,000 events, VERIFIED BY RUNNING):
dropping the >= 5-light-jet events costs **1.9% of events** but **44% of
final-state groups** (256 -> 144 on the larger pilot file), because the whole
5j / 6j / 7j... tail vanishes rather than folding into 4j.

## 5. Trigger

| | ours | PR #31 | how established |
|---|---|---|---|
| HLT requirement | yes - per-dataset HLT paths; the delivery additionally requires CMS TrigObj trigger-object matching to a muon leg | `trigger_config: enabled: false` | RUNNING (read out of the config that applies it) |
| dataset de-duplication | yes - inclusive/exclusive shards on a veto-priority order | none | READ |

**Confirms finding (iii)** on the trigger. This is the single largest driver of
the category gap: our delivered CMS numbers come from a **muon-triggered,
trigger-matched** sample, so categories with no muon are essentially absent from
them, while ATLAS's PR #31 run has no trigger requirement at all. The study's
`--population notrigger` mode exists precisely to remove this difference.

## 6. Combinations

| | ours | PR #31 | how established |
|---|---|---|---|
| object types | Electrons, Muons, Jets, BJets | Electrons, Muons, Jets, BJets | RUNNING |
| min/max types per combination | 1 / 4 | 1 / 4 | RUNNING |
| min/max count per type | 1 / 4 | 1 / 4 | RUNNING |
| max total particles | 4 | 4 | RUNNING |
| sub-leading | on, max index 1 | on, max index 1 | RUNNING |
| **combination patterns produced** | **186** | **186**, and the two sets are identical | RUNNING (`step2_enumerate.py` on each side) |
| per-category combination lists | identical for all 170 categories | identical | RUNNING (`step2_compare.py`) |

`services/calculations/combinatorics.py` is byte-identical between the two
checkouts, and so is the final-state containment test. **The combinatorics
contribute nothing to the gap.** Full table: `STEP2_COMBINATIONS.md`.

## 7. The ">= 100 events" rule - asked explicitly in the task

It is applied **twice, at two different granularities**, on our side:

1. **per FINAL STATE, globally.** `prune_final_states_below_min_events(shards, 100)`
   sums the `final_state_counts` rows across every shard and deletes every
   signature belonging to a final state whose global population is below 100.
   This is a per-final-state cut, not a per-histogram one.
2. **per HISTOGRAM, twice more.** After post-processing, a histogram is kept only
   if its main array still has >= 100 entries (`main_arr.size >= threshold`), and
   again only if the filled histogram holds >= 100 events (`MIN_BUMPNET_EVENTS`).

PR #31 has the same `min_events_per_fs: 100` in its config, applied through the
same shared pruning function. READ for PR #31, RUNNING for ours (it is the chain
`build_study_histograms.py` executes).

## 8. Binning and post-processing

| | ours | PR #31 | how established |
|---|---|---|---|
| histogram bins | fixed 10 GeV bins, 0 - 10,000 GeV (1,000 bins) | `bin_width_gev: 10.0` | RUNNING |
| Z-peak cutoff | 115 GeV, applied **only** to same-flavour dilepton channels (`_dilepton_flavor`) | 115 GeV, same function | RUNNING / READ |
| max-mass cutoff | 10,000 GeV | 10,000 GeV | RUNNING |
| peak removal | `_find_rightmost_highest_peak` on 10 GeV grid-aligned bins, then keep mass >= peak. **Data-driven; `KNOWN_MASSES` plays no part in it** | identical function | RUNNING |
| `KNOWN_MASSES` | GeV values, and **never used on CMS objects**: `get_particle_known_mass` returns the array's own `mass` field when present, which NanoAOD always has | MeV values (ATLAS convention) | READ |
| outlier / first-empty-bin split | `_split_by_first_empty_bin`, edges from `linspace(min, max, nbins+1)` - **not** grid-aligned | **identical** | RUNNING |
| upstream #27 (`_aligned_bin_edges`) | **absent** | **absent** (present on upstream master) | RUNNING |
| cropping | each histogram cropped to its first..last filled bin, written as a second `_cropped.root` | `exclude_outliers: true`, with its own in-code note that it misbehaves during merging | READ |
| bin-count threshold | delivery uses > 25 (`min26bins`) and > 30 (`min31bins`); this study additionally reports >= 25, the ATLAS wording | `use_bumpnet_naming: true`; the >= 25 figure is Maryna's | RUNNING |
| histogram naming | `ROI_mass_<combo>_cat_<fs>_width_10`, `<fs>` with a trailing `x` per type and all six types written | `mass_<combo>_cat_<fs>`, `<fs>` with the trailing `x` but only the types present in the record | RUNNING (the naming function is byte-identical; the inputs differ) |

### Finding (iv) in detail

`_split_by_first_empty_bin` was RUN on the same probe arrays in all three
codebases (`step7_split_probe.py`). On the decisive probe - 40 values at 205 GeV,
40 at 210 GeV, 40 at 250 GeV - the empty 10 GeV bin [220, 230) is the first empty
bin at index >= 2:

| | `_aligned_bin_edges` present | split happened | main | outliers |
|---|---|---|---|---|
| upstream master (`8120fb8`) | yes | **yes** | 80 | 40 |
| PR #31 (`81dd40a`) | no | no | 120 | 0 |
| ours | no | no | 120 | 0 |

**Finding (iv) is confirmed** - #27 is not in PR #31 - **but it cannot explain any
part of the ATLAS/CMS difference**, because `post_processing_pipeline.py` is
md5-identical between our branch and PR #31 (`c0adb88047e6c1e1ea5477eaaed5f024`
both; upstream master `1fb76582af997acfed186a233c56f3b0`). Both sides of the
comparison are missing #27 in exactly the same way.

---

## Summary: which differences can actually move the histogram count

| difference | direction | plausible size |
|---|---|---|
| **trigger** (ours muon-triggered + trigger-matched; PR #31 none) | ours loses every category without a muon | **large** - the main effect |
| **>= 5 light jets dropped** (PR #31 only) | PR #31 loses final-state groups | **large for ATLAS**: measured at -44% of groups on CMS ttbar |
| **jet-lepton overlap removal** (ours only) | changes jet multiplicity, so moves events between categories | moderate - measured by variant (c) |
| b-tag threshold | moves events between `j` and `b` | moderate |
| eta / ID / isolation details | small shifts in object counts | small |
| combinatorics | **none** - identical | zero |
| binning, Z-peak, max-mass, peak removal, outlier split, #27 | **none** - identical code | zero |
