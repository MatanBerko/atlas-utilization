# rare4 task, Step 4: identity checks on the full production run

All 209 jobs (57 DoubleMuon + 152 SingleMuon) completed on the first
attempt -- **zero retries needed**. Pinned commit
`635d261338b93190a4a19f5afab5ab4621be756f`, run from
`/storage/agrp/berkom/atlas-utilization/work/rare4_production_pinned/repo`
(PBS jobs `5166354[0-56].pbs` DoubleMuon, `5166355[0-151].pbs` SingleMuon).

Script: `scripts/rare4_step4.py` (runs entirely against already-written
local sqlite shard files on Lustre -- no xrootd re-reads). Machine-
readable summary: `evidence/step4_identity_checks.json`. **VERIFIED BY
RUNNING** for every number below. Total runtime: 425s.

## Coverage and counts

| Dataset | Files found | Files expected | Duplicate/missing pairs | sum(n_read) | Expected total |
|---|---|---|---|---|---|
| DoubleMuon | 57 | 57 | none | 94,148,416 | 94,148,416 |
| SingleMuon | 152 | 152 | none | 323,952,013 | 323,952,013 |

Every file processed exactly once; sums match the published totals
exactly.

## Single git commit and cap policy

- Every one of the 209 jobs recorded
  `git_commit = 635d261338b93190a4a19f5afab5ab4621be756f` -- one single
  commit across the whole run.
- **Zero `CAPPED::` entries** in any of the 1,672 shard files (209 jobs
  x 8 shards: normal, top-4, nonjet4, rare4, inclusive+exclusive each) --
  confirms Step 3's cap-risk projection was correct in every version.

## Normal, top-4 and nonjet4 shards identical to runs_matched_nonjet4/

For every one of the 209 jobs, the normal, top-4, AND nonjet4 shards (6
shard files per job, 1,254 total) were compared, read-only, against the
corresponding shard in the already-delivered `runs_matched_nonjet4/`
baseline: identical signature sets, every signature's full value
multiset identical.

**Result: 0 failures out of 1,254 shard-file comparisons.** This proves
Step 1's rare4 addition changed nothing about the normal, top-4, or
nonjet4 code paths anywhere in the full dataset (Hard Rule 5).

## Total rare4 rejected events == nonjet4's total (5,738)

Summed `rare4_diagnostics.n_rejected_gt4_lepton_bjet` over all 209 jobs:

**5,738 == 5,738 -- exact match.** Both rules use the identical N>4
definition and the identical accepted-event population, so this is
expected by construction; confirmed here from the actual written output
of all 209 jobs, not just trusted from the code.

## Step 2 checks (b), (c) over the full dataset

**(b) rare4 is a sub-multiset of normal, per signature:** checked for
every signature in every job's rare4 inclusive AND exclusive shard.
**Result: 0 failures across all 209 jobs.**

**(c) label>4 signatures empty in rare4; label<=4 signatures match
normal exactly (when no hidden cases):** checked for every signature in
every job's normal inclusive shard. **Result: 0 failures** -- no
signature with a capped-label digit sum >4 ever had a rare4 entry, and
every job with `n_hidden_cases == 0` had its label<=4 signatures match
normal exactly.

## Total "hidden" cases: 0

Summed `rare4_diagnostics.n_hidden_cases` over all 209 jobs: **zero**.

This is not a coincidence, but a direct consequence of this dataset's
own trigger-matching requirement: **every accepted event has at least 1
selected matched muon** (DoubleMuon needs >=2, SingleMuon needs >=1), so
the muon count can never be 0. A "hidden" case needs the capped e+m+b
digit-sum to read <=4 while the true sum is >4 -- which requires exactly
one of the three types to be capped at 4 (true count >4) while the
*other two* types are BOTH exactly 0. Since the muon count is never 0,
this can only happen via true muon count >=5 with 0 electrons and 0
b-jets (an electron- or b-jet-heavy capped case is impossible here,
since the ever-present >=1 muon alone already pushes the capped sum past
4 the moment either of those types is capped). And the nonjet4 task's
own full-dataset aggregate (`nonjet4_full_dataset_aggregate.json`) already
showed the rejected-event muon-count distribution tops out at 4 (10
events) -- **no rejected event in this dataset ever has 5 or more
muons** -- so the one scenario that could produce a hidden case simply
never occurs here.

## Overall Step 4 result: PASS, all hard stops satisfied, zero retries needed.
