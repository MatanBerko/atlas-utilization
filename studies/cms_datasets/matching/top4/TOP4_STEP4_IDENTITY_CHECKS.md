# Top-4 task, Step 4: identity checks on the full production run

All 209 jobs (57 DoubleMuon + 152 SingleMuon) completed on the first
attempt -- **zero retries needed**. Pinned commit
`521c31ec0085aef300cb0aa1844799f916610316`, run from
`/storage/agrp/berkom/atlas-utilization/work/matched_top4_production_pinned/repo`.
Evidence: `evidence/step4/step4_identity_checks.json`,
`evidence/step4/step4_pilot_repro_and_veto.json`.

**VERIFIED BY RUNNING** for every number below.

## Coverage and counts

| Dataset | Files found | Files expected | Duplicate/missing pairs | sum(n_read) | Expected total |
|---|---|---|---|---|---|
| DoubleMuon | 57 | 57 | none | 94,148,416 | 94,148,416 |
| SingleMuon | 152 | 152 | none | 323,952,013 | 323,952,013 |

Every file processed exactly once; sums match the published totals
exactly.

## Single git commit and cap policy

- Every one of the 209 jobs (both datasets) recorded
  `git_commit = 521c31ec0085aef300cb0aa1844799f916610316` -- one single
  commit across the whole run, confirmed by set-equality over all 209
  `job_metadata.json` files, not sampled.
- **Zero `CAPPED::` entries** in any of the 836 shard files (209 jobs x 4
  shards: normal inclusive/exclusive, top-4 inclusive/exclusive) --
  confirms Step 3's cap-risk projection was correct; no signature ever
  needed subsampling.

## The 4 pilot files reproduce Step 2's outputs exactly

All 4 shard types (normal inclusive, normal exclusive, top-4 inclusive,
top-4 exclusive) compared array-for-array (full value multiset, read-only)
between the full-run job and Step 2's own pilot output, for all 4 pilot
files (DoubleMuon 30522/0 = job_0, DoubleMuon 30555/0 = job_29, SingleMuon
30530/0 = job_0, SingleMuon 30563/0 = job_70): **PASS, all 16 comparisons,
byte-for-byte identical.**

## DoubleMuon inclusive == exclusive

Aggregated over all 57 files: inclusive (sum of `n_after_gate`) =
**9,449,024**; exclusive (sum of `n_exclusive`) = **9,449,024** -- exactly
equal, per-job and in total, exactly as the spec requires (DoubleMuon has
no higher-veto-priority dataset in this combination).

## SingleMuon: inclusive - exclusive == vetoed by DoubleMuon's acceptance

Aggregated over all 152 files:

| Quantity | Value |
|---|---|
| Total inclusive (`n_after_gate`) | 163,146,091 |
| Total exclusive (`n_exclusive`) | 153,802,672 |
| Vetoed by DoubleMuon's acceptance (inclusive - exclusive) | 9,343,419 |
| **Exclusive fraction** | **94.273%** |

This matches almost exactly the ~94.3% seen on the 2 SingleMuon pilot
files in the earlier trigger-matching task (Step 3e of
`TRIGGER_MATCHING_REPORT.md`) -- a strong cross-check that the pilot-scale
result generalizes to the full dataset.

## Overall Step 4 result: PASS, all hard stops satisfied, zero retries needed.
