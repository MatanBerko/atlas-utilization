# HANDOFF — CMS MC full-run preparation (17 Oct 2026)

**Status (17 Oct, resumed ~10:00 IDT after Matan's decisions):** peak-tie
effect ACCEPTED and documented (no code change); C2/C3 done (497 files read,
only 75589/98 inconsistent); FULL_RUN_PLAN.md written; smoke builds `5234304`
RUNNING since 10:27 (io lowered 25 → 0.5 with `qalter` because the group io
allowance was full; nothing else changed). Remaining: C1 report + PNGs,
archive, final HANDOFF.

**Earlier status (17 Oct, ~10:30 IDT... superseded): STOPPED in Part B, waiting for Matan.**
The pilot re-build differs from expectation in 4 sparse ggH histograms
(round-off decides peak ties) — see `FINDING_PEAK_TIES.md`. Per the task
("any other difference: STOP after documenting it") Parts C (report) and D
(plan) were NOT finished. Everything already measured is kept for resume.

## State at the stop (all VERIFIED BY RUNNING)

| part | state |
|---|---|
| A | done, pushed (`29d09ee`): merge clean, WZ 5.789, builder refuses in_full_run=false, tests 0 failures |
| B | rebuild `5234302` exit 0 (31 min, 4.0 GB peak). ttbar, DY bit-identical; ggH 2,455/2,459 histograms ×0.9916710 to 3e-14; **4 histograms differ** (FINDING_PEAK_TIES.md). PNGs `plots/fullrun_prep/B3_*.png` |
| C | production `5234303[1-10]`: **10/10 exit 0**, every Σw self-check passed. Per-sample builds `5234304` were still QUEUED at the stop (not cancelled; they write only into `smoke_builds/`) |
| D | input sweep `5234305` done: 497 files, 392,680,763 events, all 13 records = portal. 75589 file 98: genEventCount != num_entries (to check). Pilot per-file timings collected (`evidence/pilot_per_file.json` in the work dir) |

File count of `/storage/agrp/berkom`: 109,634 before, **110,397** at the stop
(+763). The checkout is NOT archived yet: job `5234304` still needs it.

**Branch:** `feature/cms-mc-fullrun-prep-20261017` (origin only), branched
from `origin/feature/cms-mc-xsec-update-20261015` (`0fcab6d`).

## Commits

| Commit | What |
|---|---|
| `0e9d4e5` | A1: merge of `origin/master` (2460978) — only the two test files of 2460978 came in, no conflict |
| `d400538` | A2: WZ 72752 σ_eff 5.789 pb (exact k-factor), registry regenerated, `--check` passes |
| `29d09ee` | A3/A4: builder refuses `in_full_run = false` records; +4 test checks; XSEC_DECISIONS.md |
| `61c307c` | `fullrun_prep/pbs_prep.sh`, `fullrun_prep/measure_fullrun_inputs.py` — **all cluster jobs run from this commit** |

## Cluster

Reached over `wipp-home` (`wipp-campus` timed out). Queue `N` now requires an
`io` request on every job (a job without one is refused with "violates queue
and/or server resource limits"), so the builds carry `io=25` too.

- Checkout (pinned, do not move while jobs run):
  `/storage/agrp/berkom/atlas-utilization/checkouts/mcprep_20261017/repo` at `61c307c`
- Work dir: `/storage/agrp/berkom/atlas-utilization/work/mcprep_20261017/`
  - `build_default/`, `scratch_default/` — B1 re-build
  - `runs_smoke/record<ID>/job_0/` — C production
  - `smoke_builds/record<ID>/` — C per-sample builds
  - `evidence/fullrun_inputs.json` — D input sweep
  - `mappings/smoke.txt`, `logs/{rebuild,smoke,smoke_builds,sweep}/`, `jobids.txt`
- Read-only input: the 10 Oct pilot per-file outputs,
  `work/cms_mc_v3_pilot_20261011/runs/` (the builder copies each shard to
  `scratch_default/` before touching it) and the 10 Oct build 3a,
  `work/cms_mc_v3_pilot_20261011/build_default/`.
- File count of `/storage/agrp/berkom` before this task: **109,634**
  (`lfs quota`; soft quota 150,000, hard 200,000).

## Jobs

| Job ID | What | Resources |
|---|---|---|
| `5234302` | B1 rebuild (`WHAT=rebuild_default`, pilot build 3a options) | mem=64gb, walltime=08:00:00, io=25 |
| `5234303[1-10]` | C smoke production, file 0 of 67993 64895 64839 72676 72752 75589 68187 68073 35631 68847 (`cluster/pbs_mc_pilot.sh`, unchanged) | mem=6gb, walltime=02:00:00, io=25 (pilot) |
| `5234304` | C per-sample builds, after `5234303[]` (`WHAT=smoke_builds`) | mem=16gb, walltime=04:00:00, io=25 |
| `5234305` | D input sweep (`WHAT=sweep`) | mem=4gb, walltime=04:00:00, io=25 |

## How to resume

0. After Matan's decision on FINDING_PEAK_TIES.md: let `5234304` finish (or
   check `logs/smoke_builds/sb.out`), then steps 2–3 below. Local copies used
   so far were in a temporary directory; re-copy from the work dir.

1. `/opt/pbs/bin/qstat -u berkom -t`; logs in `work/mcprep_20261017/logs/`.
2. When done: copy `build_default/*.root` and the 10 Oct
   `build_default/*.root` locally and run
   `fullrun_prep/compare_rebuild.py` (B2/B3); copy `runs_smoke/*/job_0/job_metadata.json`,
   `logs/smoke/`, `smoke_builds/` and run `fullrun_prep/smoke_report.py` (C);
   copy `evidence/fullrun_inputs.json` and write `FULL_RUN_PLAN.md` (D).
3. At the end: tar.gz + verify the checkout into
   `checkouts/mcprep_20261017/repo_61c307c.tar.gz`, remove the checkout dir,
   re-measure the file count.

Nothing launched beyond the jobs above. No full run.
