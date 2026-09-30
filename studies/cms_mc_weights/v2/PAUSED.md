# v2 MC production -- PAUSED

**Date/time:** 2026-09-30, ~16:53 IDT.

**Reason:** Matan is checking with Maryna whether the final-state rule
(the nonjet4 rule, `--population matched`) is being applied correctly.
No further MC processing (no new jobs, no delivery build, no
validation) should run until he confirms it is safe to continue.

## What was cancelled

19 PBS array job IDs, submitted earlier this session via
`studies/cms_mc_weights/v2/submit_mc_v2.sh`, all under jobname `mc_v2`,
all owned by `berkom` (confirmed via `qstat -u` before deleting -- no
other user's or other task's jobs were touched):

```
5165403  5165404  5165405  5165406  5165407  5165408  5165409  5165410
5165411  5165412  5165413  5165414  5165415  5165416  5165417  5165418
5165419  5165420  5165421
```

Cancelled with `qdel` (each `<id>[].pbs`). Confirmed: `qstat -u berkom`
now returns nothing at all -- zero running or queued jobs remain for
this user.

Two other array IDs from the same submission (5165400 DoubleMuon/42407,
5165401 SingleMuon/42407, 5165402 DoubleMuon/67801) had **already
finished completely** before this pause and were never touched.

## Per-sample status at the moment of cancellation

| Record | Sample | Files expected | DoubleMuon done | SingleMuon done | Status |
|---|---|---:|---:|---:|---|
| 42407 | LQToBMu_M-400_pair | 12 | 12 | 12 | **complete** |
| 67801 | TTTo2L2Nu | 49 | 49 | 29 | **partial** (SingleMuon in progress) |
| 35669 | DYJetsToLL_M-50_amcatnloFXFX (nominal) | 41 | 0 | 0 | not started |
| 35671 | DYJetsToLL_M-50_madgraphMLM (alt) | 61 | 0 | 0 | not started |
| 64895 | ST_tW_top | 11 | 0 | 0 | not started |
| 64839 | ST_tW_antitop | 10 | 0 | 0 | not started |
| 72676 | WWTo2L2Nu | 7 | 0 | 0 | not started |
| 72752 | WZTo3LNu | 31 | 0 | 0 | not started |
| 75589 | ZZTo4L | 99 | 0 | 0 | not started |
| 68187 | TTZToLLNuNu | 42 | 0 | 0 | not started |
| 68073 | TTWJetsToLNu | 12 | 0 | 0 | not started |

"Done" = a complete `job_metadata.json` exists for that file (the
driver writes this file only as its very last step, so its presence
means that one file's job ran to completion cleanly).

**Jobs killed mid-write** (qdel'd while actively running -- these left
partial shard files with no `job_metadata.json`, which is the expected,
harmless signature of an interrupted-but-never-finished job, not
corruption of anything that had completed):
- `67801/SingleMuon/job_{20,27,28,29,30,31,33,35,36,37,38,39,40,41,43,44,45,46,47,48}`
  (20 job directories)
- `35669/DoubleMuon/job_0` (1 job directory, had barely started)

**Nothing was deleted, moved, or overwritten.** Every one of these
partial directories, and every completed job directory, is left exactly
as PBS/the driver left it.

## Where everything is kept

All output remains under, untouched:
```
/storage/agrp/berkom/atlas-utilization/work/cms_mc_v2/
    42407/{DoubleMuon,SingleMuon}/job_0..11/      -- complete (12+12 files)
    67801/DoubleMuon/job_0..48/                    -- complete (49 files)
    67801/SingleMuon/job_0..48/                    -- 29 complete, 20 partial
    35669/DoubleMuon/job_0/                        -- 1 partial, nothing else
    (35669/SingleMuon, 35671, 64895, 64839, 72676, 72752, 75589, 68187,
     68073: no output directories were created for these -- their PBS
     arrays never reached the point of writing anything before being
     cancelled while still queued)
```
The cluster git checkout at
`/storage/agrp/berkom/atlas-utilization/work/cms_mc_v2/repo` is also
untouched, at commit `57bd055` (the last commit fetched before this
pause).

## Resuming later

Nothing needs to be cleaned up or redone for 42407 and 67801/DoubleMuon
-- they are complete and can be used as-is. 67801/SingleMuon needs the
remaining ~20 files re-run (the partial job directories can simply be
overwritten by re-running those file indices; the driver always
`unlink()`s and recreates its shard files at the start of each job, so
re-running a partial index is safe). Every other sample needs its full
array resubmitted from scratch. No code changes are needed to resume --
`studies/cms_mc_weights/v2/submit_mc_v2.sh` is unchanged and ready.
