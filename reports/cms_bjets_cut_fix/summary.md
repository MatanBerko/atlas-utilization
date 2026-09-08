# Fix: CMS configs missing a `bjets:` kinematic-cuts entry

Branch: `fix/cms-bjets-kinematic-cuts`, off `master`. Approved by Maryna as a
direct config fix — no upstream issue needed. Only remote:
`github.com/MatanBerko/atlas-utilization`; upstream
(`github.com/Zhavi221/atlas-utilization`) was not touched in any way.

## Root cause

**This is a config omission, not a code bug.** The pipeline code is correct
and behaves exactly as designed:

- `services/parsing/event_selection.py`'s `YAML_PARTICLE_KEYS` maps YAML key
  `"bjets"` → canonical collection name `"BJets"`.
- `services/calculations/physics_calcs.py`'s `filter_events_by_kinematics`
  applies a kinematic mask to a collection **only if a matching key exists**
  in the cuts dict; a collection with no matching key passes through
  completely uncut (`if cuts is None: filtered_events[obj] = particles;
  continue`).
- ATLAS's `config.yaml` already has a `bjets:` entry (line 118 pre-fix) and
  has always worked correctly.
- Every CMS config that enables jet tagging only ever had a `jets:` entry,
  never a matching `bjets:` one — so `BJets` (the tagged-jet collection
  produced by `FileParser._calculate_btagging_and_split`) has been receiving
  **no kinematic cut whatsoever**, in every CMS run to date, regardless of
  what `pt_min`/`eta_max` the config's `jets:` block specified.

## Files changed (9, exhaustive search of master's tree)

Searched every `.yaml` file at `master`'s tip containing `kinematic_cuts:`
(12 total). Of those, 9 are CMS configs (identified by CMS-scale GeV units —
`pt_min: 30.0`, not ATLAS's MeV-scale `30000.0` — and by CMS
`specific_record_ids`, not ATLAS `release_years`) that have a `jets:` entry
but no `bjets:` entry. Each got a `bjets:` block added with the **same**
`pt_min`/`eta_max` as that file's own `jets:` entry (no values invented, no
existing values changed), matching each file's existing block-style
indentation:

- `config.cms_bjet_test.yaml`
- `config.cms_fourrecord_test.yaml`
- `config.cms_partb_verify.yaml`
- `config.cms_production_test.yaml`
- `config.cms_records_master.yaml`
- `config.cms_singleelectronsinglemuon.yaml`
- `config.cms_zpeak_test.yaml`
- `config.short_parse_btag.yaml`
- `config.short_parse_local.yaml`

All 9 had the identical value, `jets: {pt_min: 30.0, eta_max: 4.5}`, so all 9
now also have `bjets: {pt_min: 30.0, eta_max: 4.5}`.

The 3 remaining `kinematic_cuts:`-bearing files (`config.yaml`,
`config.atlas_scale_test.yaml`, `configWmaxTotal_up4j_minEvt100_subleading.yaml`)
are ATLAS configs (MeV units / `release_years`) — out of scope, not touched.
`config.yaml` and `config.atlas_scale_test.yaml` already had `bjets:`;
`configWmaxTotal_up4j_minEvt100_subleading.yaml` has no `jets:`/`bjets:`
tagging setup at all and wasn't part of the reported bug.

**Important scope note — one more instance found, out of reach from this
branch:** `config.cms_ttbar_truth_crosscheck.yaml` (on the separate,
unmerged branch `analysis/ttbar-btag-truth-crosscheck`, not on `master`)
has the exact same missing-`bjets:` problem — in fact that branch's own
commit message is what first fully diagnosed this bug. Since this fix
branch is off `master` and that file does not exist on `master`, it could
not be edited here without merging/cherry-picking across branches, which
this task did not ask for. **It still needs the same fix applied, on its
own branch, separately.**

## Test: real before/after numbers on real data through real code

Per Maryna's request, this was verified concretely, not just by reading the
code. `scripts/verify_bjets_kinematic_cut_fix.py` loads the **already
on-disk** `BJets_pt`/`BJets_eta` from
`output/cms_bjet_test_20260903_124711/parsed_data/parsed_record_30562_final.root`
— real parsed output from `config.cms_bjet_test.yaml` **before** this fix —
and calls the actual production function,
`services/parsing/event_selection.py::apply_parsing_event_selection`, twice:
once with the OLD `kinematic_cuts` dict (no `bjets` key, reproducing the
pre-fix config) and once with the NEW one (this fix's `bjets` key added).
No live XRootD access was needed or used.

Results (real numbers, 2,493,471 events, 399,303 raw BJets entries):

| | n BJets | min(pT) | max(\|eta\|) | violating pt_min=30 | violating eta_max=4.5 |
|---|---:|---:|---:|---:|---:|
| Raw, as currently on disk (pre-fix run) | 399,303 | 15.000 GeV | 2.922 | 163,929 | 0 |
| **BEFORE fix** (OLD cuts applied) | 399,303 | 15.000 GeV | 2.922 | 163,929 (41.0%) | 0 |
| **AFTER fix** (NEW cuts applied) | 235,374 | **30.000 GeV** | 2.858 | **0** | **0** |

The "BEFORE fix" row is identical to the raw on-disk data, confirming the
bug precisely: applying the old config's `kinematic_cuts` left BJets
completely untouched — 41% of entries were below the configured 30 GeV
`pt_min`, some as low as 15 GeV. The "AFTER fix" row shows exactly the
163,929 sub-30-GeV entries removed (399,303 − 163,929 = 235,374, matching
exactly), with the resulting minimum pT landing exactly on the 30.0 GeV
boundary and zero remaining violations of either cut. This confirms the fix
works as intended, on real data, through the real production code path.

## What this affects — prior results with uncut BJets

- **`test/cms-bjet-with-histograms`** (the first-ever CMS b-jet
  histograms, 7.69% tag rate): ran with the pre-fix configs, so its BJets
  collection — and any histogram built from it — included jets that should
  have been excluded by the configured pt/eta window. **Not re-run as part
  of this task**, per instruction. If those results are ever used for
  anything real, that branch needs to be re-run with the fixed config first.
- **`analysis/ttbar-btag-truth-crosscheck`**: as noted above, has the same
  bug in its own config, on its own unmerged branch; its existing parsed
  output and any conclusions drawn from raw BJets kinematics there predate
  this fix too, and its own report already documents re-applying the window
  by hand at analysis time as a workaround for exactly this reason.
- Every other CMS config listed above had no prior BJets-consuming run on
  record that this investigation found, other than the two above.

## Summary

Root cause: 9 CMS configs were simply missing a `bjets:` entry in
`kinematic_cuts:` (ATLAS's config already had one; the code correctly
applies cuts only where a matching collection key is present). Fixed by
adding `bjets:` to all 9, with the same values as each file's own `jets:`
entry. Verified concretely on real parsed data through the real production
selection function: BJets went from 41% out-of-window entries (min pT 15
GeV) to zero violations (min pT exactly 30 GeV) after the fix.
