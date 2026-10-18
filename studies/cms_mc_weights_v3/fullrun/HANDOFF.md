# HANDOFF — CMS MC FULL RUN (17 Oct 2026)

**Current step: COMPLETE (18 Oct 2026, 19:50 IDT). Nothing running. Not delivered; not merged. Next: the technical lead verifies (see `FULL_RUN_REPORT.md`).**
Not delivered to anyone; not merged into master.

**Branch:** `feature/cms-mc-fullrun-20261017` (origin only), from
`feature/cms-mc-fullrun-prep-20261017` @ `4e36bbf`.
**Pinned full-run commit: `294ee59bb562a1d6542022444e043a1c15a932e7`**
(decisions recorded; every cluster job runs from a checkout at this commit).

Decisions (Matan, 17 Oct): ZZ 75589 file 98 option A (kept; the build's Σw
check must exclude exactly it); the 98 pilot files re-run; ≤ 9,000 new
files and ≤ 125,000 total.

## Cluster

Reached over `wipp-home` (`wipp-campus` timed out).

- Production checkout: `/storage/agrp/berkom/atlas-utilization/checkouts/fullrun_20261017/repo` @ `294ee59` (do not move while jobs run)
- Post-production checkout (audit, build, reproducibility, sanity — `fullrun/pbs_fullrun.sh`):
  `checkouts/fullrun_20261017/post` @ `dbd3107`. `build_mc_delivery.py` and the per-file code
  are unchanged between 294ee59 and dbd3107 (`git diff` empty).
- Work: `/storage/agrp/berkom/atlas-utilization/work/fullrun_20261017/`
  `mappings/mapping_<rid>.txt` (497 lines, no exclusion), `runs/record<rid>/job_<i>/`,
  `logs/<rid>/f_<idx>.{out,err}`, `logs/build/`, `evidence/`,
  `jobids.txt`, `submit_production.sh` (skips records already in jobids.txt)
- File count (`lfs quota -u berkom /storage`): **110,147 before submission**

## Production arrays (pilot launcher `cluster/pbs_mc_pilot.sh`, mem=6gb, io=25)

| record | PBS array | jobs | walltime |
|---|---|---:|---|
| 67993 | `5234570[]` | 138 | 02:00:00 |
| 75589 | `5234571[]` | 99 | 02:00:00 |
| 67801 | `5234572[]` | 49 | 02:00:00 |
| 68187 | `5234573[]` | 42 | 03:00:00 |
| 35669 | `5234574[]` | 41 | 02:00:00 |
| 72752 | `5234575[]` | 31 | 02:00:00 |
| 35631 | `5234576[]` | 25 | 02:00:00 |
| 68847 | `5234577[]` | 24 | 02:00:00 |
| 68073 | `5234578[]` | 12 | 03:00:00 |
| 64895 | `5234579[]` | 11 | 02:00:00 |
| 64839 | `5234580[]` | 10 | 02:00:00 |
| 72676 | `5234581[]` | 7 | 02:00:00 |
| 37728 | `5234582[]` | 8 | 02:00:00 |

## How to resume

1. `/opt/pbs/bin/qstat -u berkom -t` and `qstat -x <array>` — never resubmit
   an array that is queued, running or finished.
2. Audit (step 3): every job exit 0, `job_metadata.json` in every
   `runs/record<rid>/job_<i>/`, Σw self-check fails for exactly 75589/98.
   Resubmit a failed file once with identical resources (single-file:
   `-v ...,PILOT_ARRAY_INDEX=<line>` without `-J`); twice → STOP.
3. Then, from `post` (all `-l io=25`, logs in `logs/build/`):
   `qsub -N mcfull_<what> -l mem=<..>,walltime=<..>,io=25 -o $W/logs/build/<what>.out -e $W/logs/build/<what>.err
    -v WORK_DIR=$W,REPO_DIR=$C/post,WHAT=<audit|build|reproduce|sanity>[,PILOT_RUNS=...] $C/post/studies/cms_mc_weights_v3/fullrun/pbs_fullrun.sh`
   audit (4gb, 2h) → build (64gb, 8h) → reproduce (16gb, 8h; PILOT_RUNS=work/cms_mc_v3_pilot_20261011/runs)
   → sanity (32gb, 4h). Then FULL_RUN_REPORT.md (step 6), archive + final HANDOFF (step 7).

Status at 11:45 IDT 17 Oct: 19 running, 478 queued (group io allowance), nothing failed.

## Production result (18 Oct, 15:13 IDT)

- 497/497 `job_metadata.json`, 497/497 `.err` with `Exit status: 0`, no resubmission (VERIFIED BY RUNNING)
- Last files (68187, 68073; normE) waited overnight on the group io limit
- File count: **116,798** (+6,651 = 6,014 in `work/fullrun_20261017` + 637 in the `post` checkout)

## Post-production jobs (from `post` @ dbd3107)

| step | PBS job | resources | state |
|---|---|---|---|
| audit | `5243008` | 4gb, 2h, io=25 | done: verdict OK, 497/497, Σw failure exactly 75589/98, 108.97 CPU h |
| reproduce | `5243009` | 16gb, 8h, io=25 | done (exit 0, 28.5 min): 98/98 files, 784/784 shards identical; only created_utc/elapsed_sec/git_commit differ |
| build | `5243011` | 64gb, 8h, io=25 | done (exit 0, 2h15): 13/13 records + summedSM; exactly 1 exclusion 75589/98 |
| sanity | `5243647` | 32gb, 4h, io=25 | done (2h15): 0 NaN/inf, 0 negative variances, yields consistent, 19 PNGs |

File count 15:46 IDT 18 Oct: 117,654 (build scratch in progress; expected final ≈118,350 < 119,147).
Evidence copied to `fullrun/evidence/` (production_audit.json, reproducibility_pilot_vs_fullrun.json).

## Final state (18 Oct 2026, 19:50 IDT)

- Report: `fullrun/FULL_RUN_REPORT.md`. PNGs: `plots/fullrun/` (19). Evidence: `fullrun/evidence/` (audit, reproducibility, sanity)
- Output (cluster only): `work/fullrun_20261017/build_default/` (13 × `fullrun_record<rid>_mc.root`, `fullrun_summedSM_mc.root`, `fullrun_build_report.json`)
- Checkouts archived, with listings verified (archive file entries == files on disk):
  - `checkouts/fullrun_20261017/checkout_repo_294ee59.tar.gz` (260 files, 63 MiB)
  - `checkouts/fullrun_20261017/checkout_post_dbd3107.tar.gz` (276 files, 63 MiB)

  The checkout directories themselves were left in place (deleting cluster data is out of scope).
- File count: **118,401** (+8,254 vs 110,147; limits 119,147 / 125,000 respected)
- Local repo switched back to `master`. master and every other branch unchanged; nothing upstream; no PR.
