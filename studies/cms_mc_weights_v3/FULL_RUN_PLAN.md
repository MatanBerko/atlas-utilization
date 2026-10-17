# CMS MC full run — plan (17 Oct 2026)

**Nothing has been submitted.** This plan is executed by the NEXT prompt.
Numbers are **VERIFIED BY RUNNING** (measured on 17 Oct or in the 10 Oct
pilot) unless marked **UNVERIFIED** (a projection is by nature unverified
until the run happens; its inputs are measured).

Sources: `evidence/fullrun_inputs_20261017.json` (portal + file headers),
`evidence/input_file_check_20261017.json` (all 497 files read),
`evidence/pilot_per_file_20261017.json` (98 pilot files),
`evidence/smoke_production_20261017.json` (10 smoke files),
`evidence/fullrun_projection_20261017.json` (the arithmetic, from
`fullrun_prep/project_full_run.py`).

## 1. Inputs

13 records, **497 files, 392,680,763 events** — every record's file count and
event total equal the CERN portal's (VERIFIED). All 497 files were opened and
their `genWeight` branch read in full on 17 Oct: 496 are consistent (event
count = Runs `genEventCount`, Σ genWeight = Runs `genEventSumw` to ≤ 4.4e-8,
size = portal size).

**One exception: 75589 (ZZTo4L) file 98** (VERIFIED):

| | value |
|---|---:|
| Events entries (= what the portal's record total counts) | 871,000 |
| Runs `genEventCount` | 904,000 |
| Σ genWeight over all events / Runs `genEventSumw` | 1,154,337.9 / 1,198,138.4 (−3.66%) |
| size on EOS = portal size | 1,193,133,570 B |
| adler32 on EOS = portal checksum | `36099d1e` = `36099d1e` |

The file is **not truncated or corrupt**: it is byte-for-byte the published
file and reads completely. Its Runs header counts 33,000 events (3.7%) that
are not in its Events tree — **inconsistently labelled**. The builder's
existing per-file Σw check (tolerance 1e-6) will therefore **exclude it
automatically** and normalise 75589 with the Σw of the other 98 files; it
costs 871,000 of 52,104,000 ZZ events (1.7%). See §7 for the options.

## 1b. Smoke test of the 10 never-run records (17 Oct, VERIFIED)

File 0 of each never-run record went through production (pilot launcher,
`5234303[1-10]`, all exit 0) and a per-sample build (builder defaults,
`--output-mode per-sample --smoke-test`): **10/10 built**, every per-file Σw
check included its file, every histogram passed the TH1D/Sumw2 read-back.
Table and PNGs: `fullrun_prep/HANDOFF.md`, `plots/fullrun_prep/smoke/`.

## 2. Run-time model (Matan's decision, 17 Oct)

* **Realistic (used for the requests).** Per-file wall time fitted over all
  108 measured MC files (98 pilot + 10 smoke) with non-negative coefficients:
  **t ≈ 4.34 s × (number of final states the file fills)**; event count adds
  nothing once final states are known. The **envelope** = fit × 2.44 lies above
  every measured file (it is set by the slowest node seen: ttbar file 30,
  3,022 s, while identical files took 984 s). Final states of a record's
  largest file are extrapolated from its measured file(s) at the steepest
  pilot growth, **78 final states per tenfold increase in events**.
  Check against reality: the model gives 14.9 / 5.9 / 1.3 CPU h for the three
  pilot records, measured 15.2 / 4.4 / 0.6 CPU h.
* **Literal (reference only).** The record's slowest measured events/s for
  every file. Records measured only on a tiny first file (68073: 9,451 events;
  64839, 68187, 72676, 68847, 37728) get absurd projections, because a fixed
  start-up cost of 100–900 s dominates small files.
* **Requests.** Walltime = max(2 × envelope worst file, 2 × the largest wall
  time ever measured = 2 × 3,022 s), rounded up to the hour. Memory = 1.5 ×
  the largest measured peak (3.06 GB, pilot timing job), rounded up to an even
  GB as in the pilot ⇒ **6 GB** for every record (per-record peaks from tiny
  files are not representative; the largest measured production peak is
  2.91 GB).

## 3. Per record (projections UNVERIFIED; inputs VERIFIED)

| record | sample | files | events | largest file | realistic CPU h | realistic worst file h (envelope) | literal CPU h | literal worst file h | walltime | mem | disk GB | new files |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|
| 67801 | TTTo2L2Nu | 49 | 43,546,000 | 1,428,000 | 14.9 | 0.85 | 664.1 | 21.8 | 02:00:00 | 6 GB | 12.7 | 590 |
| 67993 | TTToSemiLeptonic | 138 | 144,722,000 | 1,406,000 | 30.2 | 0.54 | 26.9 | 0.3 | 02:00:00 | 6 GB | 28.7 | 1,658 |
| 35669 | DYJetsToLL_M-50 NLO | 41 | 71,839,442 | 1,936,303 | 5.9 | 0.38 | 11.3 | 0.3 | 02:00:00 | 6 GB | 2.7 | 494 |
| 35631 | DYJetsToLL_M-10to50 NLO | 25 | 49,267,069 | 2,444,741 | 1.7 | 0.16 | 0.7 | 0.0 | 02:00:00 | 6 GB | 0.1 | 302 |
| 64895 | ST_tW_top | 11 | 3,368,375 | 799,406 | 2.5 | 0.56 | 2.0 | 0.5 | 02:00:00 | 6 GB | 0.6 | 134 |
| 64839 | ST_tW_antitop | 10 | 3,654,510 | 1,048,507 | 2.0 | 0.65 | 18.9 | 5.4 | 02:00:00 | 6 GB | 1.2 | 122 |
| 72676 | WWTo2L2Nu | 7 | 2,900,000 | 1,135,000 | 1.2 | 0.59 | 9.8 | 3.8 | 02:00:00 | 6 GB | 0.6 | 86 |
| 72752 | WZTo3LNu | 31 | 10,441,724 | 1,521,547 | 6.4 | 0.61 | 3.5 | 0.5 | 02:00:00 | 6 GB | 1.0 | 374 |
| 75589 | ZZTo4L | 99 | 52,104,000 | 1,702,000 | 21.8 | 0.68 | 54.8 | 1.8 | 02:00:00 | 6 GB | 5.2 | 1,190 |
| 68187 | TTZToLLNuNu | 42 | 6,017,000 | 1,180,000 | 16.2 | 1.23 | 69.1 | 13.6 | **03:00:00** | 6 GB | 7.8 | 506 |
| 68073 | TTWJetsToLNu | 12 | 3,322,643 | 1,008,689 | 4.0 | 1.04 | 84.0 | 25.5 | **03:00:00** | 6 GB | 6.4 | 146 |
| 37728 | GluGluHToZZTo4L | 8 | 1,000,000 | 611,000 | 1.3 | 0.64 | 7.4 | 4.5 | 02:00:00 | 6 GB | 0.2 | 98 |
| 68847 | VBF_HToZZTo4L | 24 | 498,000 | 142,000 | 3.9 | 0.63 | 9.6 | 2.7 | 02:00:00 | 6 GB | 0.7 | 290 |
| **total** | | **497** | **392,680,763** | | **111.9** | max 1.23 | **962.1** | max 25.5 | | | **67.8** | **5,990** |

* Disk = events × the record's measured output bytes/event (exact for the
  pilot records; an upper bound for records measured on one small file).
  Space is not a constraint: 156 GB used of 4 TB today.
* New files = per job 9 outputs + job dir + 2 PBS logs, + 2 per record.
  Walltime ≤ 2 h routes to queue shortE; 3 h routes to normE.

## 4. File count vs quota

| | files |
|---|---:|
| `/storage/agrp/berkom` now (17 Oct, end of prep, `lfs quota`) | 110,147 |
| + production, all 497 files re-run | +5,990 |
| + default build with `--keep-scratch` (≈3 per job, as the pilot's 298 for 98 jobs) | +≈1,500 |
| **after the run** | **≈117,600** |
| soft quota / hard limit | 150,000 / 200,000 |

≈32,400 under the soft quota. (Reusing the pilot files would save 1,182
production files: ≈116,500.) The task-level 5,000-new-files stop rule must
be lifted explicitly by the full-run prompt: the run needs ≈7,500.

## 5. The 98 pilot files (67801, 35669, 37728): **re-run** (recommended)

* They were produced on 10 Oct at **`cbfb837`** (old branch
  `feature/cms-mc-weights-v3`), every one of the 98 (`git_commit` in each
  job_metadata.json, VERIFIED). The full run would use the head of
  `feature/cms-mc-fullrun-prep-20261017` (the commit holding this plan).
* The 14 Oct mc-port validation (`validate/mc-port-20261014`,
  `studies/mcport_validation_20261014/VALIDATION.md`) showed `cbfb837`'s
  driver and `services/` byte-identical to old-branch head `68ab281`, and
  per-file outputs of the ported code (`5906dcf`) **bit-identical** to the
  pilot originals on 6 of the 98 files (2 per record, 268 M values incl. every
  MC weight array). From `5906dcf` to today's head the per-file path is
  unchanged (`git diff 5906dcf HEAD` touches only two test files outside this
  study). So reuse is technically sound.
* **Recommendation: re-run them anyway.** Reasons: (1) one commit for the
  whole delivery — no cross-commit provenance to explain later; (2) it is
  cheap: ≈22 CPU h, 1,182 files, 15.6 GB; (3) the builder takes a single
  `--runs-dir`, so reuse would need copying or linking 98 directories out of
  a read-only pilot area; (4) the re-run doubles as a free 98-file
  reproducibility check against the pilot (instead of 6), with the existing
  `mcport_validation_20261014/mc_compare.py runs`.
  Reuse remains a valid fallback if cluster time becomes scarce.

## 6. Submission plan for the next prompt

Cluster rules as before (queue N, `#PBS -m n`, logs dir created first,
nothing in `$HOME`, HANDOFF pushed before waiting).

1. **New** dirs: `checkouts/<fullrun_tag>/repo` cloned from origin and pinned
   to the plan's commit; `work/<fullrun_tag>/` with `mappings/`, `runs/`,
   `logs/<record>/` for all 13 records, `logs/build/`.
2. Mappings (re-checks the portal lists against the 17 Oct sweep, stops on
   any change):
   `python studies/cms_mc_weights_v3/fullrun_prep/make_fullrun_mappings.py --out-dir $W/mappings`
   (add `--exclude 75589:98` only if Matan chooses option B in §7).
3. Production: **13 arrays**, the pilot launcher unchanged, longest records
   first so the tail is short:
   order 67993, 75589, 67801, 68187, 35669, 72752, 35631, 68847, 68073,
   64895, 64839, 72676, 37728.
   ```
   cd $R && /opt/pbs/bin/qsub -J 1-<n> -N mcfull_<rid> \
     -l mem=6gb,walltime=<02:00:00 | 03:00:00 for 68187 and 68073>,io=25 \
     -o $W/logs/<rid>/f_^array_index^.out -e $W/logs/<rid>/f_^array_index^.err \
     -v WORK_DIR=$W,REPO_DIR=$R,OUTPUT_BASE=$W/runs,MAPPING_FILE=$W/mappings/mapping_<rid>.txt \
     $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh
   ```
4. Audit: every job exit 0, every `job_metadata.json` present, per-file Σw
   self-check (expect exactly one failure: 75589/98, §1); resubmit failures
   one by one with the same resources (a file that fails twice: stop and
   report).
5. Build, after all 13 arrays: the pilot's default build over `$W/runs`
   (`build_mc_delivery.py --runs-dir $W/runs --out-dir $W/build_default
   --out-prefix fullrun --scratch-dir $W/scratch_default --keep-scratch`),
   `-l mem=64gb,walltime=08:00:00,io=25`. Expected ≈2 h and ≈15 GB
   (UNVERIFIED: the pilot build took 31 min and 4.2 GB for 116 M events).
   The builder refuses any record with `in_full_run = false`, so the runs
   directory must hold only the 13 records (it will).
   **Lesson from 17 Oct:** the smoke-build job, started only after its `io`
   request was cut to 0.5 to fit the full group allowance, stalled for 30 min
   with 14 s of CPU while reading back its first ROOT file (job `5234304`,
   cancelled). The same builds then ran in 1–8 s each on the login node from
   the same pinned checkout. Do NOT cut the build's `io` request below the
   pilot's 25; if the group allowance is full, wait.

**Cluster I/O cap — expect queueing (VERIFIED on 17 Oct).** The server
limits `io` to 800 per user and 1,000 per group (`watlas`). At `io=25` at
most 32 of our jobs run at once; ≈112 CPU h then needs ≥3.5 h of wall clock
(UNVERIFIED). On 17 Oct the group's allowance was fully used by other
users (server `resources_assigned.io` = 999.1 of 1,000): our one-core smoke
build waited ≈1.5 h with "Server per-group limit reached on resource io",
still waited at `io=2`, started at once when lowered to `io=0.5` — and then
stalled. The
full run may sit in the queue similarly; that is a scheduling delay, not a
failure. Keep `io=25` for production and the build (the pilot's validated request).
Do not lower it to jump the queue: the one job that ran at `io=0.5` stalled
(see step 5). A queue wait is a delay, not a failure.

## 7. Decisions for Matan

1. **75589 file 98** (intact file, header counts 33,000 events it does not
   contain):
   - **A. Keep it in production; the builder's existing Σw check excludes it
     automatically** and normalises ZZ with the other 98 files (−1.7% of ZZ
     statistics, correct normalisation, exclusion recorded in the build
     report). No code change. *Recommended.*
   - B. Leave it out of production (`--exclude 75589:98`); same physics
     result as A, saves one job, but the exclusion then lives in the mapping
     instead of the build report.
   - C. Use it, normalised by its own Σ genWeight instead of its header:
     needs a change to the builder's Σw rule — a convention change, not
     recommended without Maryna/Yuval.
   - (Re-fetching is pointless: the checksum proves we already have exactly
     the published file.)
2. Re-run vs reuse the 98 pilot files (§5): recommended re-run.
3. The next prompt must allow ≈7,500 new files (§4).

**Decisions taken, Matan, 17 Oct 2026:**
1. **75589 file 98 → option A**: kept in production; the builder's Σw check
   excludes it automatically (histograms and Σw); ZZ uses 98 of 99 files
   (−1.7% statistics, normalisation unaffected). B and C rejected (B: same
   physics, less visible record; C: Σw-convention change needing
   Maryna/Yuval). The build must report exactly this one exclusion. Full
   entry: `XSEC_DECISIONS.md`, "Data quality". The MC delivery note must
   state "ZZ uses 98 of 99 files".
2. **The 98 pilot files → RE-RUN** with everything else; the pilot area is
   neither reused nor touched.
3. **New-file allowance for the full-run task: up to 9,000 new files**, and
   never beyond 125,000 in total; the file count is measured before
   submission, after production and after the build.
