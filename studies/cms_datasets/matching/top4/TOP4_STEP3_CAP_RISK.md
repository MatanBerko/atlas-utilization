# Top-4 task, Step 3: cap-risk projection (before the full run)

**VERIFIED BY RUNNING** for every number quoted (pilot `job_metadata.json`
files under `evidence/job_metadata/`, and the pre-existing, already-quoted
pre-flight per-file event counts from the trigger-matching task: DoubleMuon
largest file 2,986,904 events, SingleMuon largest file 3,539,840 events,
both out of the pre-flight scan covering all 57 + 152 files).

## Pilot files' own largest-signature ratios (normal and top-4 are identical)

| File | n_read | normal max_signature_size_this_job | top4 max_signature_size_this_job | ratio (max_sig / n_read) |
|---|---|---|---|---|
| DoubleMuon 30522/0 | 2,315,223 | 178,006 | 178,006 | 0.07688 |
| DoubleMuon 30555/0 | 2,147,195 | 173,545 | 173,545 | 0.08084 |
| SingleMuon 30530/0 | 2,939,781 | 256,568 | 256,568 | 0.08728 |
| SingleMuon 30563/0 | 14,113 | 1,152 | 1,152 | 0.08164 |

Normal and top-4 give the IDENTICAL largest-signature size in all 4 pilot
files. This is expected: the largest signature in every file is always the
simplest, most populous topology (e.g. the 2-muon or 1-muon mass), and
events with that few objects already have <=4 objects and are completely
untouched by top-4 truncation — so top-4's cap risk is the same as
normal's.

## Projection onto each dataset's largest single file (of 57 / 152)

Using each dataset's own HIGHER observed ratio (the more conservative
choice) applied to that dataset's largest single file's event count
(pre-flight, both eras):

| Dataset | Ratio used | Largest file event count | Projected largest signature | vs. 400,000 (80% of cap) | vs. 500,000 cap |
|---|---|---|---|---|---|
| DoubleMuon | 0.08084 (30555/0) | 2,986,904 | **≈241,500** | 60% of threshold | 48% of cap |
| SingleMuon | 0.08728 (30530/0) | 3,539,840 | **≈308,960** | 77% of threshold | 62% of cap |

**Conclusion: neither dataset's projected largest signature exceeds
400,000 (80% of the 500,000 cap).** Per this task's own instruction, no
`--entry-start`/`--entry-stop` file-splitting is required, and no split-
then-merge proof needs to be built before the full run.

This is a **projection from two small-file ratios per dataset, not a
measurement on the full dataset**. It will be reverified for real in Step
4's identity checks, which require zero `CAPPED::` entries anywhere across
all 209 real production jobs (both normal and top-4 shards) as a hard
stop, exactly as this project's existing cap policy has always required.
