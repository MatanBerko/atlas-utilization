# nonjet4 task, Step 2: validation on the 4 pilot files

Code: commit `3a184b7` on `deliver/all-datasets-bumpnet` (Matan's fork,
`https://github.com/MatanBerko/atlas-utilization`). Run from a dedicated
pinned checkout at
`/storage/agrp/berkom/atlas-utilization/work/nonjet4_pilot_pinned/repo`
(detached HEAD at `3a184b7`, untouched for the duration of every job
below, per Hard Rule 6). Outputs under
`/storage/agrp/berkom/atlas-utilization/output/cms_datasets/nonjet4_pilot/`
(new directory; the 4 array jobs were `5161533[0-3].pbs`, all exit 0, no
tracebacks, `job_metadata.json`'s own `git_commit` confirmed
`3a184b7add5c0436548ce18e41e9c61c898dd89b` for all 4).

Pilot files (same 4 as the top-4 task): DoubleMuon record 30522 file 0,
DoubleMuon record 30555 file 0, SingleMuon record 30530 file 0, SingleMuon
record 30563 file 0.

Every number below is **VERIFIED BY RUNNING** (script + evidence file
cited); scripts are in `scripts/`, their full stdout is quoted or
summarized below, raw `job_metadata.json` for all 4 jobs is under
`evidence/job_metadata/`.

## Check (a) HARD: normal and top-4 shards + per-stage counts identical to runs_matched/ (commit 521c31e)

Script: `scripts/nonjet4_check_a.py`. Compares, read-only
(`mode=ro&immutable=1`) against the already-delivered production shards
in `runs_matched/{DoubleMuon,SingleMuon}/job_<N>/` (commit `521c31e`,
listed read-only under Hard Rule 3): every non-capped signature's full
value multiset for BOTH the normal (`dataset_shard_inclusive/exclusive`)
and the top-4 (`dataset_shard_top4_inclusive/exclusive`) shards, plus all
per-stage event counts and `top4_diagnostics` counts, for all 4 pilot
files. (Job-index mapping: DoubleMuon 30522/0 = `runs_matched/DoubleMuon/job_0`,
30555/0 = `job_29`; SingleMuon 30530/0 = `runs_matched/SingleMuon/job_0`,
30563/0 = `job_70`.)

**Result: PASS for all 4 files, all 4 shard types (normal incl/excl,
top-4 incl/excl), all per-stage counts.** Confirms Step 1's nonjet4
addition changed nothing about the normal or top-4 code paths (Hard
Rule 5) -- byte-for-byte identical to the untouched production baseline.

## Check (b) HARD: nonjet4 array is a sub-multiset of the top-4 array, per signature

Script: `scripts/nonjet4_check_bce.py`. For every signature present in a
job's `dataset_shard_nonjet4_{inclusive,exclusive}.sqlite`, every value's
multiplicity in the nonjet4 array is `<=` its multiplicity in the
corresponding top-4 array (nonjet4 only ever *removes* rows relative to
top-4, from rejecting N>4 events -- it never adds, reorders, or alters a
value).

**Result: PASS for all 4 files, both inclusive and exclusive.**

## Check (c) HARD: nonjet4 accepted == top-4 accepted minus rejected (inclusive and exclusive, separately)

Script: `scripts/nonjet4_check_bce.py` (inclusive identity, using this
run's own `nonjet4_diagnostics.n_rejected_gt4_lepton_bjet`) plus
`scripts/nonjet4_check_d_f.py` (exclusive identity, using an
INDEPENDENTLY re-derived rejected-and-exclusive count -- see check (d)
below for what "independent" means here).

| File | top-4 incl | rejected | nonjet4 incl (expected) | nonjet4 incl (actual) | top-4 excl | rejected&excl (independent) | nonjet4 excl (expected) | nonjet4 excl (actual) |
|---|---|---|---|---|---|---|---|---|
| DoubleMuon 30522/0 | 223,393 | 18 | 223,375 | 223,375 | 223,393 | 18 | 223,375 | 223,375 |
| DoubleMuon 30555/0 | 218,886 | 27 | 218,859 | 218,859 | 218,886 | 27 | 218,859 | 218,859 |
| SingleMuon 30530/0 | 1,511,878 | 40 | 1,511,838 | 1,511,838 | 1,425,358 | 31 | 1,425,327 | 1,425,327 |
| SingleMuon 30563/0 | 6,919 | 0 | 6,919 | 6,919 | 6,529 | 0 | 6,529 | 6,529 |

**Result: PASS for all 4 files, inclusive and exclusive both exact.**
(SingleMuon 30530/0's rejected-and-exclusive count, 31, is less than its
total rejected count, 40 -- 9 of the 40 rejected events are vetoed by
DoubleMuon's acceptance and were never exclusive to begin with, which is
expected and not a bug.)

## Check (d) HARD: rejected-event count matches an independent recount from the normal version

Script: `scripts/nonjet4_check_d_f.py`. Re-reads all 4 pilot files
directly from the CMS open-data portal (own xrootd read, own golden-JSON
filter, own trigger requirement, own object selection, own matched-mode
acceptance gate -- importing only PRE-EXISTING shared functions from
`run_dataset_on_file.py`, i.e. `matched_acceptance_mask`,
`TRIGGER_PATHS_BY_DATASET`, etc. -- never the new nonjet4-specific code
added in Step 1), then independently counts accepted events with
`N = selected electrons + selected muons + selected b-jets > 4`.

| File | independent N>4 count | job's own `n_rejected_gt4_lepton_bjet` |
|---|---|---|
| DoubleMuon 30522/0 | 18 | 18 |
| DoubleMuon 30555/0 | 27 | 27 |
| SingleMuon 30530/0 | 40 | 40 |
| SingleMuon 30563/0 | 0 | 0 |

**Result: PASS for all 4 files** -- exact match between the independently
re-derived count and the pinned-commit job's own diagnostic.

## Check (e) HARD: no nonjet4 category has electrons+muons+bjets > 4 or more than 4 objects in total

Script: `scripts/nonjet4_check_bce.py`. Parses every signature actually
written to each job's `dataset_shard_nonjet4_inclusive.sqlite`.

| File | nonjet4 signatures checked | e+m+b>4? | total>4? |
|---|---|---|---|
| DoubleMuon 30522/0 | 96 | none | none |
| DoubleMuon 30555/0 | 82 | none | none |
| SingleMuon 30530/0 | 198 | none | none |
| SingleMuon 30563/0 | 86 | none | none |

**Result: PASS for all 4 files** -- zero violations.

## Check (f): 10 rejected (N>4) events + 10 kept-but-truncated (N<=4, total>4) events, full lists

Script: `scripts/nonjet4_check_d_f.py`. Evidence:
`evidence/step2f_nonjet4_examples.txt`. All 20 examples were found within
the first pilot file (DoubleMuon 30522/0), pooling across files only if a
file runs short (not needed here).

Part 1 (rejected, N>4) confirms light jets never rescue a rejected event
regardless of how few total objects it has -- e.g. event index 5383
(2m+2e+1b = 5 objects total, N=5) and event index 101515 (3m+2b+4j = 9
objects total, but N=3m+0e+2b=5) are both rejected outright, with no
light-jet padding attempted.

Part 2 (kept, N<=4 but total>4) confirms the padding rule visually --
e.g. event index 224 (2 muons + 2 jets = 4 objects total... actually 2
muons + several jets) keeps both muons over much higher-pT jets (269.0,
183.75 GeV) exactly as top-4 already did, and event index 762 (2 muons +
2 b-jets + 2 jets = 6 objects, N=4) keeps both b-jets over a higher-pT
light jet -- identical priority behaviour to top-4, since N<=4 here.

## Rejection rate and light-jet-drop rate (diagnostics, not a hard check)

From each file's own `job_metadata.json` `nonjet4_diagnostics` block
(`evidence/job_metadata/*/job_metadata.json`):

| File | accepted (pre-rule) | rejected (N>4) | rejected fraction | kept events w/ light jets dropped | dropped fraction (of kept) |
|---|---|---|---|---|---|
| DoubleMuon 30522/0 | 223,393 | 18 | 0.0081% | 2,982 | 1.335% |
| DoubleMuon 30555/0 | 218,886 | 27 | 0.0123% | 3,010 | 1.375% |
| SingleMuon 30530/0 | 1,511,878 | 40 | 0.0026% | 11,318 | 0.749% |
| SingleMuon 30563/0 | 6,919 | 0 | 0% | 56 | 0.810% |

The N>4 rejection rate is far smaller than the top-4 truncation rate
(~0.75-1.4%, see the top-4 task's own `TOP4_STEP2_VALIDATION.md`) --
expected, since N only counts leptons+b-jets (light jets, the most common
"extra" object, never push N over 4), so only the rarer lepton/b-jet-heavy
tail is actually removed. The light-jet-drop rate among KEPT nonjet4
events is essentially the same as top-4's own truncation rate (both rules
are identical for N<=4 events, and the vast majority of top-4's truncated
events already have N<=4 -- only the tiny N>4 slice is now excluded
instead of truncated, which is why the "dropped" counts here are just
slightly below top-4's own truncated-event counts, e.g. 2,982 vs. 3,000
for DoubleMuon 30522/0).

## Summary

All HARD checks (a)-(e) PASS on all 4 pilot files; check (f)'s example
table is written to evidence and visually confirms the rule. Step 1's
code is validated and ready for the full-dataset cap-risk projection
(Step 3) and production run.
