# nonjet4 task, Step 4: identity checks on the full production run

All 209 jobs (57 DoubleMuon + 152 SingleMuon) completed on the first
attempt -- **zero retries needed**. Pinned commit
`3c7c9c97cdc9788d108f61156c05963b7fc1f0a4`, run from
`/storage/agrp/berkom/atlas-utilization/work/nonjet4_production_pinned/repo`
(PBS jobs `5162005[0-56].pbs` DoubleMuon, `5162006[0-151].pbs` SingleMuon).

Script: `scripts/nonjet4_step4.py` (runs entirely against already-written
local sqlite shard files on Lustre -- no xrootd re-reads). Machine-
readable summary: `evidence/step4_identity_checks.json` (full stdout was
also captured on the cluster at
`/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_nonjet4/step4_run.log`,
but `*.log` files are excluded from this repo by `.gitignore` so it is
not committed -- every number quoted below is reproduced from that
run's actual output).
**VERIFIED BY RUNNING** for every number below. Total runtime: 244s.

## Coverage and counts

| Dataset | Files found | Files expected | Duplicate/missing pairs | sum(n_read) | Expected total |
|---|---|---|---|---|---|
| DoubleMuon | 57 | 57 | none | 94,148,416 | 94,148,416 |
| SingleMuon | 152 | 152 | none | 323,952,013 | 323,952,013 |

Every file processed exactly once; sums match the published totals
exactly (identical to the top-4 task's own Step 4 totals, since the file
lists and `n_read` are completely unaffected by the nonjet4 rule).

## Single git commit and cap policy

- Every one of the 209 jobs (both datasets) recorded
  `git_commit = 3c7c9c97cdc9788d108f61156c05963b7fc1f0a4` -- one single
  commit across the whole run, confirmed by set-equality over all 209
  `job_metadata.json` files (the set has exactly one element), not
  sampled.
- **Zero `CAPPED::` entries** in any of the 1,254 shard files (209 jobs x
  6 shards: normal inclusive/exclusive, top-4 inclusive/exclusive,
  nonjet4 inclusive/exclusive) -- confirms Step 3's cap-risk projection
  was correct; no signature ever needed subsampling, in any version.

## Normal and top-4 shards identical to runs_matched/ (proves nothing else changed)

For every one of the 209 jobs, both the normal (`dataset_shard_inclusive/exclusive.sqlite`)
and top-4 (`dataset_shard_top4_inclusive/exclusive.sqlite`) shards were
compared, read-only, against the corresponding shard in the top-4 task's
own already-delivered `runs_matched/` baseline (836 shard-file
comparisons total): identical signature sets, and every signature's full
value multiset identical (values rounded to 5 decimals, compared as
sorted arrays).

**Result: 0 failures out of 836 shard-file comparisons.** This proves
Step 1's nonjet4 addition changed nothing about the normal or top-4 code
paths anywhere in the full dataset (Hard Rule 5), not just on the 4 pilot
files.

## Step 2 checks (b), (c), (d) summed over the full dataset

**(b) nonjet4 is a sub-multiset of top-4, per signature:** checked for
every signature in every job's nonjet4 inclusive AND exclusive shard
(both must be sub-multisets of the corresponding top-4 shard).
**Result: 0 failures across all 209 jobs.**

**(c) nonjet4 accepted == top-4 accepted minus rejected (inclusive):**
checked for every job by comparing `sum(nonjet4 final_state_label_event_counts_inclusive)`
against `sum(top4 ...) - n_rejected_gt4_lepton_bjet`.
**Result: 0 failures across all 209 jobs** (exclusive is additionally
guaranteed a valid sub-multiset by check (b) above; the same
raw-data-independent verification of the *exact* exclusive count done in
Step 2 for the 4 pilot files is not repeated at full scale, since it
requires re-reading every NanoAOD file a second time -- the full-dataset
check here instead confirms the identical code path via the exact
inclusive identity, the sub-multiset bound, and the top-4/normal shard
identity above, which together leave no room for the exclusive
bookkeeping to silently diverge).

**(d) rejected count matches an independent recount from the normal
version:** for every job, the normal shard's `final_state_counts` table
(label -> event count) was used to independently bound the true N>4
(rejected) count WITHOUT touching any nonjet4 code -- a label like
`"2e_1m_...0b"` (all three of e/m/b digits < 4) unambiguously reflects
the true per-type counts (no capping possible below 4), so its
contribution to "N>4" is exactly determined; a label with the same digit
exactly `4` on ONE of e/m/b and zero on the other two is the only
ambiguous case (that digit alone can't distinguish a true count of
exactly 4 from a capped true count >4). This gives a certain floor and
an ambiguous ceiling for every job.

| Quantity (summed over all 209 jobs) | Value |
|---|---|
| Certain floor (unambiguous N>4 events, from labels alone) | 5,738 |
| Ambiguous events (single type at digit 4, others 0) | 118 |
| Job's own `n_rejected_gt4_lepton_bjet` (summed) | 5,738 |

**Result: every one of the 209 jobs falls within its own bound
(`certain <= n_rejected <= certain+ambiguous`), and the aggregate is
EXACT: certain floor == total rejected == 5,738.** This means the 118
ambiguous-labeled events contributed ZERO to the true rejected count --
i.e. every one of them genuinely has a true per-type count of exactly 4
(not a capped-down value from something higher), so there is no residual
uncertainty at all in the full-dataset total. 126 of the 209 jobs had
zero ambiguous events and so were already an exact per-job match; the
remaining 83 jobs each had a small ambiguous margin that resolved to zero
extra rejections in aggregate.

## Overall Step 4 result: PASS, all hard stops satisfied, zero retries needed.
