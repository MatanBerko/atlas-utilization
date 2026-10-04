# rare4 task, Step 3: cap-risk projection (before the full run)

**VERIFIED BY RUNNING** for every number quoted (pilot `job_metadata.json`
files under `evidence/job_metadata/`, cross-checked against the top-4
task's own already-verified `TOP4_STEP3_CAP_RISK.md` projection, which
used these same 4 pilot files).

## The argument: rare4's cap risk can never exceed normal's

Step 2 check (b) proved, for all 4 pilot files, that every rare4 array is
a sub-multiset of the corresponding NORMAL array (rare4 only ever
*removes* whole event rows relative to normal, from rejecting N>4
events -- it never adds a row). A sub-multiset can never be larger than
the set it is drawn from, so for every signature and every file:

```
len(rare4[signature]) <= len(normal[signature])
```

In particular `max_signature_size_this_job` for rare4 can never exceed
normal's own value, in any job. Since the largest signature is always
the simplest, most populous topology (e.g. the 2-muon mass), whose
events already have N<=4 and are therefore never touched by the rare4
rejection rule either, rare4's largest signature is expected to equal
normal's exactly -- confirmed directly below.

## Confirmation on the 4 pilot files

| File | n_read | normal max | rare4 max | rare4 <= normal? |
|---|---|---|---|---|
| DoubleMuon 30522/0 | 2,315,223 | 178,006 | 178,006 | yes (equal) |
| DoubleMuon 30555/0 | 2,147,195 | 173,545 | 173,545 | yes (equal) |
| SingleMuon 30530/0 | 2,939,781 | 256,568 | 256,568 | yes (equal) |
| SingleMuon 30563/0 | 14,113 | 1,152 | 1,152 | yes (equal) |

In all 4 pilot files, rare4's largest signature is EQUAL to normal's,
exactly as with nonjet4 and top-4 before it. The existing projection
(from the top-4 task's own Step 3, using the same pilot files and the
same ratio method) therefore applies to rare4 unchanged:

| Dataset | Ratio used | Largest file event count | Projected largest signature | vs. 400,000 (80% of cap) | vs. 500,000 cap |
|---|---|---|---|---|---|
| DoubleMuon | 0.08084 (30555/0) | 2,986,904 | ~241,500 | 60% of threshold | 48% of cap |
| SingleMuon | 0.08728 (30530/0) | 3,539,840 | ~308,960 | 77% of threshold | 62% of cap |

**Conclusion: neither dataset's projected largest rare4 signature
exceeds 400,000.** No file-splitting is required, and no split-then-
merge proof needs to be built before the full run. This will be
reverified for real in Step 4's identity checks, which require zero
`CAPPED::` entries anywhere across all 209 real production jobs (normal,
top-4, nonjet4, AND rare4 shards) as a hard stop.
