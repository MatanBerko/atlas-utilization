# rare4 task, Step 2: validation on the 4 pilot files

Code: commit `52bea52` on `deliver/all-datasets-bumpnet` (Matan's fork).
Run from a dedicated pinned checkout at
`/storage/agrp/berkom/atlas-utilization/work/rare4_pilot_pinned/repo`
(detached HEAD at `52bea52`, untouched for the duration of every job
below, per Hard Rule 6). Outputs under
`/storage/agrp/berkom/atlas-utilization/output/cms_datasets/rare4_pilot/`
(new directory; PBS jobs `5166315[0-3].pbs`, all exit 0, no tracebacks,
`job_metadata.json`'s own `git_commit` confirmed `52bea52...` for all 4).

Pilot files (same 4 as before): DoubleMuon record 30522 file 0, DoubleMuon
record 30555 file 0, SingleMuon record 30530 file 0, SingleMuon record
30563 file 0.

Every number below is **VERIFIED BY RUNNING** (script + evidence file
cited); scripts are in `scripts/`, full stdout quoted/summarized below,
raw `job_metadata.json` for all 4 jobs is under `evidence/job_metadata/`.

## Check (a) HARD: normal, top-4, nonjet4 shards + per-stage counts identical to runs_matched_nonjet4/

Script: `scripts/rare4_check_a.py`; full output: `evidence/check_a_output.txt`.
Compares, read-only (`mode=ro&immutable=1`) against the already-delivered
production shards in `runs_matched_nonjet4/{DoubleMuon,SingleMuon}/job_<N>/`
(commit `3c7c9c97...`, read-only under Hard Rule 3): every non-capped
signature's full value multiset for the normal, top-4, AND nonjet4
shards (6 shard types, inclusive+exclusive each), plus all per-stage
event counts and top4/nonjet4 diagnostics counts, for all 4 pilot files.

**Result: PASS for all 4 files, all 6 shard types, all per-stage
counts.** Confirms Step 1's rare4 addition changed nothing about the
normal, top-4, or nonjet4 code paths (Hard Rule 5).

## Check (b) HARD: rare4 array is a sub-multiset of the normal array, per signature

Script: `scripts/rare4_check_bcd.py`; full output: `evidence/check_bcd_output.txt`.
For every signature present in a job's `dataset_shard_rare4_{inclusive,exclusive}.sqlite`,
every value's multiplicity in the rare4 array is `<=` its multiplicity in
the corresponding normal array (rare4 only ever *removes* whole event
rows relative to normal -- it never adds, reorders, or alters a value).

**Result: PASS for all 4 files, both inclusive and exclusive.**

## Check (c) HARD: label>4 signatures empty in rare4; label<=4 signatures match normal exactly (or differ only by hidden cases)

Script: `scripts/rare4_check_bcd.py`. For every signature in the normal
shard, parsed its own (already display-capped) label digits (e, m, j, g,
t, b) directly from the signature string. Two sub-checks:
- Every signature whose label has `e+m+b > 4`: rare4 has **zero**
  entries. (True by construction -- see `RARE4_STEP1` docstring in
  `run_dataset_on_file.py`: an event only survives into rare4 if its
  TRUE e+m+b <= 4, and a true count <=4 per type is never display-capped,
  so its label digits are exactly its true counts -- no kept event can
  ever produce a label with digit-sum >4.)
- Every signature whose label has `e+m+b <= 4`: rare4 equals normal
  exactly, UNLESS the job had `n_hidden_cases > 0` in its
  `rare4_diagnostics`.

| File | label>4 signatures with stray rare4 entries | label<=4 exact-match | label<=4 differing | n_hidden_cases |
|---|---|---|---|---|
| DoubleMuon 30522/0 | 0 | 691 | 0 | 0 |
| DoubleMuon 30555/0 | 0 | 577 | 0 | 0 |
| SingleMuon 30530/0 | 0 | 1,296 | 0 | 0 |
| SingleMuon 30563/0 | 0 | 292 | 0 | 0 |

**Result: PASS for all 4 files.** Zero hidden cases occurred in any of
the 4 pilot files (a "hidden" case needs a single object type's TRUE
count to exceed 4 -- e.g. 5 muons -- which is rare enough that none
appeared in this small a sample; see Step 4 for the full-dataset rate).
With zero hidden cases, every label<=4 signature matched normal exactly,
the strongest form of this check.

## Check (d) HARD: rare4 rejected events == nonjet4 rejected events, per file

Script: `scripts/rare4_check_bcd.py`. Both numbers read directly from
each job's own `job_metadata.json` (not just trusted from the code --
the actual written output was checked).

| File | nonjet4 rejected | rare4 rejected | Match |
|---|---|---|---|
| DoubleMuon 30522/0 | 18 | 18 | PASS |
| DoubleMuon 30555/0 | 27 | 27 | PASS |
| SingleMuon 30530/0 | 40 | 40 | PASS |
| SingleMuon 30563/0 | 0 | 0 | PASS |

**Result: PASS for all 4 files** -- exact match, as expected (same N>4
rule, same accepted-event population).

## Check (e): 10 rejected (N>4) events + 10 kept-with->4-light-jets events, full lists

Script: `scripts/rare4_check_e.py`. Evidence: `evidence/step2e_rare4_examples.txt`.
All 20 examples were found within the first pilot file (DoubleMuon
30522/0).

Part 1 (rejected, N>4) confirms the exact same rejected events as
nonjet4's own check (f) table (same rule) -- e.g. event 5383 (2e+2m+1b=5)
and event 95164 (2m+4b=6) are both rejected regardless of how many light
jets they have (0 in both cases here).

Part 2 (kept, N<=4 but >4 light jets) confirms rare4's own distinguishing
behaviour versus nonjet4: event 13706 (2 muons, 0 b-jets, N=2, but 5
light jets) keeps **all 7 objects** -- unlike nonjet4, which would have
padded/truncated to 4 total. The display label still reads
`0e_2m_4j_0g_0t_0b` (light jets capped at "4j" in the name, the existing
normal-version convention), but all 5 light jets are used in the actual
mass combinations. Event 19825 similarly keeps all 8 objects (6 light
jets, N=2).

## Summary

All HARD checks (a)-(d) PASS on all 4 pilot files; check (e)'s example
table is written to evidence and visually confirms the rule, including
the key difference from nonjet4 (no light-jet truncation). Zero hidden
cases in the pilot sample. Step 1's code is validated and ready for the
full-dataset cap-risk projection (Step 3) and production run.
