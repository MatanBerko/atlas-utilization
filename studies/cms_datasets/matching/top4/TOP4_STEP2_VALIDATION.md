# Top-4 task, Step 2: validation on the 4 pilot files

Code: commit `db2f5c0` on `deliver/all-datasets-bumpnet`. Run from a
dedicated pinned checkout at
`/storage/agrp/berkom/atlas-utilization/work/top4_pilot_pinned/repo`
(detached HEAD at that commit, untouched for the duration of every job
below). Outputs under
`/storage/agrp/berkom/atlas-utilization/output/cms_datasets/top4_pilot/`
(new directory).

Every number below is **VERIFIED BY RUNNING** (script + evidence file
cited).

## Check (a) HARD: normal matched shards identical to matching_validation/ (commit cbd1abb)

Script: `scripts/top4_check_a.py`. Compared every non-capped signature's
full value multiset, read-only, between the new pinned-commit run and the
pre-existing (untouched) `matching_validation/` shards, for both
inclusive and exclusive shards, all 4 pilot files, plus all per-stage
event counts.

**Result: PASS for all 4 files, both shards, all per-stage counts.** The
refactor that extracted the shard-writing loop into `run_combination_funnel()`
did not change normal-mode behaviour at all.

## Check (b) HARD: accepted-event counts identical between normal and top-4

Script: `scripts/top4_check_bce.py`.

| File | normal inclusive | normal exclusive | top-4 inclusive | top-4 exclusive |
|---|---|---|---|---|
| DoubleMuon 30522/0 | 223,393 | 223,393 | 223,393 | 223,393 |
| DoubleMuon 30555/0 | 218,886 | 218,886 | 218,886 | 218,886 |
| SingleMuon 30530/0 | 1,511,878 | 1,425,358 | 1,511,878 | 1,425,358 |
| SingleMuon 30563/0 | 6,919 | 6,529 | 6,919 | 6,529 |

**Result: PASS for all 4 files** — truncation never changes which events
are accepted or which dataset they belong to, exactly as required.

## Check (c) HARD: every top-4 category has total object count <=4; normal is a sub-multiset of top-4

Script: `scripts/top4_check_bce.py`.

| File | top-4 signatures (all total<=4) | inclusive subset check | exclusive subset check |
|---|---|---|---|
| DoubleMuon 30522/0 | 102, all <=4 | 93 shared signatures, 0 failed | 93 shared signatures, 0 failed |
| DoubleMuon 30555/0 | 82, all <=4 | 82 shared signatures, 0 failed | 82 shared signatures, 0 failed |
| SingleMuon 30530/0 | 198, all <=4 | 181 shared signatures, 0 failed | 162 shared signatures, 0 failed |
| SingleMuon 30563/0 | 86, all <=4 | 75 shared signatures, 0 failed | 73 shared signatures, 0 failed |

**Result: PASS for all 4 files.**

## Check (d): 10 accepted events with >4 objects, full list vs. kept 4

Script: `scripts/top4_check_d.py`. Evidence: `evidence/step2d_top4_examples.txt`
(DoubleMuon 30522/0, 10 real accepted events, 5-6 original objects each).
Visually confirms the priority rule (leptons regardless of pT rank among
jets, then b-jets by pT, then light jets by pT) in every example — e.g.
event index 224 keeps both muons (130.9, 95.4 GeV) over two much
higher-pT jets (269.0, 183.75 GeV), and event index 762 keeps both b-jets
over a higher-pT light jet, exactly as specified.

## Check (e): top-4 categories with zero selected muons

| File | Zero-muon top-4 categories | Events |
|---|---|---|
| DoubleMuon 30522/0 | 0 | 0 |
| DoubleMuon 30555/0 | 0 | 0 |
| SingleMuon 30530/0 | 0 | 0 |
| SingleMuon 30563/0 | 0 | 0 |

**Result: exactly 0 in all 4 pilot files** — no exception to explain. This
makes sense: an event only loses its matched muon(s) from the top-4 if it
has >=4 leptons ALL of higher pT than that muon; in these datasets, events
with that many leptons are rare enough that none appeared in the pilot
files.

## Object-count distribution and truncation rate (diagnostics, not a hard check)

From each file's own `job_metadata.json` `top4_diagnostics` block
(`evidence/job_metadata/*/job_metadata.json`):

| File | n_accepted_events | n_accepted_events_gt4_objects | Truncated fraction |
|---|---|---|---|
| DoubleMuon 30522/0 | 223,393 | 3,000 | 1.343% |
| DoubleMuon 30555/0 | 218,886 | 3,037 | 1.388% |
| SingleMuon 30530/0 | 1,511,878 | 11,358 | 0.751% |
| SingleMuon 30563/0 | 6,919 | 56 | 0.809% |

Original-object-count distributions (`{n_objects: n_events}`):
- DoubleMuon 30522/0: `{2: 178006, 3: 33805, 4: 8582, 5: 2212, 6: 595, 7: 153, 8: 33, 9: 5, 10: 2}`
- DoubleMuon 30555/0: `{2: 173545, 3: 33519, 4: 8785, 5: 2277, 6: 552, 7: 153, 8: 40, 9: 10, 10: 4, 11: 1}`
- SingleMuon 30530/0: `{1: 1042868, 2: 353051, 3: 81379, 4: 23222, 5: 7701, 6: 2544, 7: 803, 8: 231, 9: 55, 10: 16, 11: 5, 12: 2, 13: 1}`
- SingleMuon 30563/0: `{1: 4761, 2: 1608, 3: 399, 4: 95, 5: 32, 6: 12, 7: 10, 9: 2}`

In every file, the large majority of accepted events already have <=4
objects and are completely unaffected by top-4; only a small (~0.75-1.4%),
long tail is truncated.

## How the NORMAL version treats events with more than 4 objects of one type

Read directly from `services.calculations.physics_calcs.limit_particles_in_fs`
(unchanged, not part of this task's edits): the normal version does NOT
exclude such events. It groups events by their raw (uncapped) per-type
object counts, computes masses on that raw population, but the **display
label** (and hence the BumpNet signature name) caps each type's count at 4
(e.g. a raw "5m" group is labelled "4m..." in its signature name) — so an
event with, say, 5 muons is kept, contributes to combinations exactly as
any other event in that raw group would, and is filed under the same
signature name as a 4-muon event, NOT excluded and NOT given a distinct
"5m" category of its own. Confirmed on data: DoubleMuon 30522/0's normal
inclusive shard's `final_state_label_event_counts_inclusive` already shows
capped labels (e.g. `4m` appears, no `5m`/`6m`/etc. label exists) even
though the object-count distribution above proves events with up to 10
objects exist in the accepted population.
