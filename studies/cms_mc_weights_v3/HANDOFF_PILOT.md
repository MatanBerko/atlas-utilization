# HANDOFF — CMS MC weighting PILOT

**Read this first when re-pasting the pilot prompt.** It records what has been
submitted, where the output is, and exactly where to resume.

**Branch:** `feature/cms-mc-weights-v3`
**Pinned commit for every pilot job:** `cbfb837`
**Work directory (reuse this on re-paste, do not create a new one):**
`/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_pilot_20261011/`

**Session 1 ended at: JOBS SUBMITTED AND RUNNING.** See "Where to resume".

---

## Status

| Stage | State |
|---|---|
| Part 1a — delivered data timings read | **done** |
| Part 1b — timing jobs (2) | **done**, both exit 0 |
| Part 1c/1d — walltime, memory, size, quota projections | **done** |
| Part 2 — three production arrays | **SUBMITTED** — see the table below |
| Part 2 — completeness / Σw / resubmit | not started |
| Part 3 — builds (3a, 3b, 3c, 3d) | not started |
| Part 4 — data vs MC plots | not started |

## Jobs

| Job ID | Sample | Array | Files | Output |
|---|---|---|---:|---|
| `5208385` | 35669 timing (file 30, the largest in the pilot) | — | 1 | `runs_timing/record35669/job_30/` |
| `5208393` | 67801 timing (file 5, the largest of that sample) | — | 1 | `runs_timing/record67801/job_5/` |
| `5208623[1-49]` | **67801 TTTo2L2Nu** | 1-49 | 49 | `runs/record67801/job_<file_index>/` |
| `5208624[1-41]` | **35669 DYJetsToLL_M-50 amcatnloFXFX** | 1-41 | 41 | `runs/record35669/job_<file_index>/` |
| `5208625[1-8]` | **37728 GluGluHToZZTo4L_M125** | 1-8 | 8 | `runs/record37728/job_<file_index>/` |

Submitted with `-l select=1:ncpus=1:mem=6gb -l walltime=02:00:00 -l io=25`,
queue `N` (landed in `shortE`), `#PBS -m n`. Logs go to
`logs/<record>/` — **created before submission** this time.

The two timing-job outputs live under `runs_timing/`, a *different* base from
the production `runs/`, so files 35669/30 and 67801/5 are simply processed
again by the arrays. That costs about 20 minutes of duplicated work and keeps
the production set uniform; the builder reads `runs/` only.

## Work directory layout

```
work/cms_mc_v3_pilot_20261011/
    repo/            pinned checkout at cbfb837 -- DO NOT check out anything
                     else while any pilot job is running
    mappings/        PBS mapping files (one per sample, plus the timing ones)
    runs/            PRODUCTION output, one directory per file
    runs_timing/     the two Part 1b timing jobs
    logs/{timing,67801,35669,37728}/
    evidence/        pilot_inputs.json and, later, the Part 2-4 reports
    jobids_pilot.txt, jobid_timing.txt, jobid_timing_ttbar.txt
```

Read-only and untouched throughout: `output/` (including the delivered data
shards in `output/cms_datasets/runs_matched4_full_20261007`), `work/cms_mc_v2/`,
`work/cms_mc_v3_design_*`, `work/cms_mc_v3_impl_*`. `/storage/agrp/marybo/`
was never accessed. No ACL was changed. Jobs write nothing to the real `$HOME`
(the script redirects `HOME`, `MPLCONFIGDIR` and `XDG_CACHE_HOME` into the
work directory).

---

## Part 1 measurements (all VERIFIED BY RUNNING)

### 1a — the delivered DATA production, for reference

390 matched4 jobs, 645,377,261 events read.

| | |
|---|---:|
| wall seconds per file, median | 182 |
| wall seconds per file, max | 1,184 (0.33 h) |
| events/second, median | 7,204 |
| events/second, min / max | 126 / 34,111 |
| total CPU hours | 28.8 |

### 1b — two MC timing jobs

| | 35669 file 30 (DY) | 67801 file 5 (ttbar) |
|---|---:|---:|
| events read | 1,936,303 | 1,428,000 |
| after the 7-path trigger OR | 788,607 | 935,442 |
| **stored** | 698,326 (36.1%) | 825,785 (57.8%) |
| driver elapsed | 254.5 s | 976.0 s |
| PBS wall | 257 s | 979 s |
| **events/second** | **7,607** | **1,463** |
| peak memory | 2.27 GB | 3.06 GB |
| output size | 85 MB | 387 MB |
| rare4 final-state groups | 113 | 209 |
| rare4 signature writes | 1,762 | 4,689 |
| capped signatures | 0 | 0 |
| Σw self-check | passes, 6.8e-9 | passes, 4.4e-8 |
| stored only via Ele27 | 193,805 | 263,226 |
| exit status | 0 | 0 |

**ttbar is 5.2× slower per event than DY** and produces 4.5× more output,
because it has nearly twice the distinct final-state labels and 2.7× the
signature writes — the combination funnel's cost tracks labels × signatures,
not events. Measuring a second sample was worth it: sizing the whole pilot
from the DY file alone would have under-requested by a factor of five.

### 1c — requests, and why

Using the **slower** measured rate (1,463 ev/s) for every sample, plus a 300 s
fixed open/startup allowance:

* worst single file projected: 1,624 s ≈ 27 min (35669's largest)
* `walltime = 2 × projected` ⇒ 54 min ⇒ **requested 02:00:00**, uniform
* `memory = 1.5 × measured peak` = 1.5 × 3.06 GB = 4.6 GB ⇒ **requested 6gb**
  (rounded up, because jet multiplicity above the measured file's would raise
  the buffer and a memory kill costs the one allowed resubmit)

**No file is projected anywhere near the 48 h "stop and ask" threshold** — the
worst is under an hour — so the arrays were submitted without pausing.

### 1d — projected output, and the quota

| | |
|---|---:|
| projected total CPU | ~11.1 hours |
| projected total output | ~14.9 GB |
| projected new files | ~1,223 |

Space is a non-issue: 95 GB used of a 4 TB quota.

**File count needs attention.** Before the pilot the account held 148,066
files against a soft quota of 150,000 and a hard limit of 200,000. The two
timing jobs took it to **150,002 — just over the soft quota**, which started a
7-day grace period. The pilot's ~1,223 further files bring it to roughly
151,200: still ~49,000 below the hard limit, so nothing will fail, but the
account will sit above its soft quota until old output is cleared. Clearing
anything is **not** done here — every existing output directory is read-only
by instruction. Flagged for Matan.

Input file counts were re-checked against the CERN Open Data portal before
anything was submitted: 49 / 41 / 8 files and 43,546,000 / 71,839,442 /
1,000,000 events, each matching the portal exactly, and every file's Runs-tree
`genEventCount` equal to its `num_entries` (`evidence/pilot_inputs.json`).

---

## Where to resume

1. `git fetch origin && git checkout feature/cms-mc-weights-v3`.
2. **Check the arrays**:
   ```
   ssh wipp-home '/opt/pbs/bin/qstat -u berkom'
   W=/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_pilot_20261011
   ssh wipp-home "find $W/runs -name job_metadata.json | wc -l"   # expect 98
   ```
3. **Do not resubmit the arrays.** If files are missing or failed, resubmit
   only those files, **once**, with
   `make_pilot_mapping.py --record <rid> --file-indices <a,b,c>` and the same
   `qsub` line (raise `mem`/`walltime` for that resubmit if the failure was a
   kill). A file that fails twice is excluded and listed with its error; the
   Σw accounting then uses only the surviving files automatically.
4. Then Part 3 (builds) and Part 4 (data vs MC plots).
5. The pinned checkout `repo/` must not be moved off `cbfb837` while any job
   is running.

## Unchanged, by instruction

No selection, object definition, threshold, binning, Z cut, histogram name,
registry value or builder default was touched. The only new code in this round
is the pilot plumbing: `measure_pilot_inputs.py`, `make_pilot_mapping.py` and
`pbs_mc_pilot.sh`, plus one fix to the last of those (OpenPBS refuses a
one-element array, so a single-file run passes its index through
`PILOT_ARRAY_INDEX` instead of `-J`).
