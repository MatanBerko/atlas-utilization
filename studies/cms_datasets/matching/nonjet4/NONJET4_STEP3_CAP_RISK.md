# nonjet4 task, Step 3: cap-risk projection (before the full run)

**VERIFIED BY RUNNING** for every number quoted (pilot `job_metadata.json`
files under `evidence/job_metadata/`, cross-checked against the top-4
task's own already-verified `TOP4_STEP3_CAP_RISK.md` projection, which
used the same 4 pilot files' `n_read` and the pre-flight per-file event
counts for the largest file in each dataset: DoubleMuon largest file
2,986,904 events, SingleMuon largest file 3,539,840 events).

## The argument: nonjet4's cap risk can never exceed top-4's

Step 2 check (b) proved, for all 4 pilot files, that every nonjet4 array
is a sub-multiset of the corresponding top-4 array (nonjet4 only ever
*removes* rows relative to top-4, from rejecting N>4 events -- it never
adds a row). A sub-multiset can never be larger than the set it is drawn
from, so for every signature and every file:

```
len(nonjet4[signature]) <= len(top4[signature])
```

In particular `max_signature_size_this_job` for nonjet4 can never exceed
top-4's own value, in any job. Since the top-4 task's own Step 3 already
showed top-4's cap risk projects well under the 400,000 (80%-of-cap)
threshold for both datasets' largest single file, nonjet4's cap risk is
bounded by the same conclusion *a fortiori* -- no new projection
arithmetic is strictly required. The table below confirms this directly
on real pilot data rather than relying on the argument alone.

## Confirmation on the 4 pilot files: nonjet4's own max_signature_size_this_job

| File | n_read | normal max | top-4 max | nonjet4 max | nonjet4 <= top-4? |
|---|---|---|---|---|---|
| DoubleMuon 30522/0 | 2,315,223 | 178,006 | 178,006 | 178,006 | yes (equal) |
| DoubleMuon 30555/0 | 2,147,195 | 173,545 | 173,545 | 173,545 | yes (equal) |
| SingleMuon 30530/0 | 2,939,781 | 256,568 | 256,568 | 256,568 | yes (equal) |
| SingleMuon 30563/0 | 14,113 | 1,152 | 1,152 | 1,152 | yes (equal) |

In all 4 pilot files, nonjet4's largest signature is EQUAL to top-4's
(not merely `<=`): the largest signature is always the simplest, most
populous topology (e.g. the 2-muon mass), whose events already have
N<=4 and are therefore never touched by the nonjet4 rejection rule
either. So the top-4 task's own projection applies to nonjet4 unchanged:

| Dataset | Ratio used (top-4 task, same pilot files) | Largest file event count | Projected largest signature | vs. 400,000 (80% of cap) | vs. 500,000 cap |
|---|---|---|---|---|---|
| DoubleMuon | 0.08084 (30555/0) | 2,986,904 | ~241,500 | 60% of threshold | 48% of cap |
| SingleMuon | 0.08728 (30530/0) | 3,539,840 | ~308,960 | 77% of threshold | 62% of cap |

**Conclusion: neither dataset's projected largest nonjet4 signature
exceeds 400,000.** No `--entry-start`/`--entry-stop` file-splitting is
required, and no split-then-merge proof needs to be built before the
full run. This will be reverified for real in Step 4's identity checks,
which require zero `CAPPED::` entries anywhere across all 209 real
production jobs (normal, top-4, AND nonjet4 shards) as a hard stop.
