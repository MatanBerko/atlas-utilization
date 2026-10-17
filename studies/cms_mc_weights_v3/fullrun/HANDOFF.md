# HANDOFF — CMS MC FULL RUN (17 Oct 2026)

**Current step: 3 — production submitted, waiting/monitoring.**
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

- Checkout: `/storage/agrp/berkom/atlas-utilization/checkouts/fullrun_20261017/repo` @ `294ee59` (do not move while jobs run)
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
3. Then: build (step 4), validation (step 5), FULL_RUN_REPORT.md (step 6),
   archive + final HANDOFF (step 7).
