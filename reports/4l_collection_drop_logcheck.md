# Log-based check for the collection-drop bug (d488f21) -- two runs, reported separately

This follows on from `reports/4l_collection_drop_check.md`, which checked the
*surviving parsed output files* (only ~10 of ~238 for the 2216 run — about 4%
coverage) and found nothing wrong in what was left. This document instead
checks the *run logs*, which -- when they exist -- describe every file the
run touched, not just the files whose output happens to still be on disk.

Two log messages are the direct signature of a file failing to yield a
readable particle collection (`services/parsing/file_parser.py`, quoted
verbatim from the source, not paraphrased):

```
"No particles found in schema for file {file_path}"
"No accessible particles found in file {file_path}"
```

## Step 1 — could logs even exist? (checked before searching for any)

File logging (writing a copy of the run's log lines to
`<run_dir>/logs/pipeline.log`) was added in commit `c5f5bd1`, **"Add file
logging to run's logs/ directory"**, dated **2026-09-09 08:54:43**. Its own
commit message is direct about what came before it:

> "setup_logging() only attached a stdout StreamHandler, so every run's
> logs/ subdirectory was silently empty regardless of outcome"

The 2216-candidate run's directory is `cms_higgs_4lepton_fullscale_20260908_150157`
-- the timestamp encoded in that name is **2026-09-08 15:01:57**, a full day
**before** `c5f5bd1` existed. Confirmed `c5f5bd1` is an ancestor of
`analysis/higgs-4lepton-clean` (so file logging did eventually become part of
this project's history), but purely by commit timing, the code that actually
executed the 2216 run could not have contained it.

**Plain finding: file logging was not active when the 2216 run executed.**
Whatever that run's `logs/` directory contains (checked below) can only be
whatever happened to reach the terminal it was run from, if anything was
captured at all -- not a guaranteed pipeline.log.

## Step 2 — the 2216 run (`cms_higgs_4lepton_fullscale_20260908_150157`)

Searched, read-only, in every location this repo's own code and scripts use
for logs:

| Location | Result |
|---|---|
| `<run_dir>/logs/` (locally, this machine) | **Exists, but is completely empty** -- `ls -la` shows only `.` and `..`, zero files. Exactly matches the Step 1 finding: the code that ran this had no file-logging capability yet. |
| Anywhere else locally near the run directory | No `.log`, `.out`, or `.err` file of any kind found for this specific run (other, unrelated runs in the same `output/` folder do have their own `_stdout.log`/`_memlog.csv` files -- e.g. `cms_higgs_4lepton_dedup_test_stdout.log` -- showing that *when* someone redirected a run's terminal output to a file by hand, it does survive; nobody did that for this one). |
| The cluster (`wipp-an1`, `/storage/agrp/berkom/atlas-utilization/output/`) | **This run does not exist on the cluster at all** -- searched for any directory containing "150157"; none found. |
| PBS batch-job output (`/storage/agrp/berkom/atlas-utilization/logs/*.out`/`.err`) | Not applicable -- this convention only applies to jobs actually submitted via `qsub` on the cluster, and this run was never on the cluster (previous point). |

**Verdict for this run: zero surviving logs, in any location, of any kind.**
Not because anything was deleted -- because (a) the code running it did not
yet have the ability to write a log file, and (b) it was run in a way (most
likely typed directly into a local terminal, not submitted as a tracked
batch job) that left no captured record of its console output either.

**This means the question "did file X fail to yield its particle
collections during the 2216 run" cannot be answered from logs at all, for
any file, at any coverage level.** Zero percent, not a partial percentage
-- there is no log-based evidence available for this specific run, full
stop. This is a real, final constraint on what can be known about this
specific run from its logs; it is reported here plainly rather than
substituted with a different run's numbers.

## Step 3 — the Part B run (`cms_higgs_4lepton_cluster_fullscale_20260909_113726`)

This run happened one day after `c5f5bd1`, so file logging was active, and
it was a real cluster batch job, so PBS's own `-o`/`-e` stdout/stderr
capture exists too. Found and read, read-only (copied to a local scratch
location to read; the originals on the cluster were never modified):

- `<run_dir>/logs/pipeline.log` (in the run's own output directory on Lustre)
- `/storage/agrp/berkom/atlas-utilization/logs/higgs4l_partB_fullscale.out`
- `/storage/agrp/berkom/atlas-utilization/logs/higgs4l_partB_fullscale.err`

(the PBS job's `-o`/`-e` paths, per `pbs_higgs4l_partB_cluster_fullscale.sh`'s
own `#PBS -o` / `#PBS -e` lines -- confirmed these are the only other log
convention this repo's scripts/configs use, alongside the run's own
`jobs_logs_path: ./output/logs` setting in every `config.cms_higgs_4lepton_*.yaml`,
which is the same `<run_dir>/logs/` location already checked.)

### Neither warning string appears, anywhere, in any of these three files

```
grep "No particles found in schema" pipeline.log *.out *.err   -> no matches
grep "No accessible particles found" pipeline.log *.out *.err  -> no matches
```

Also searched broadly for any other skip/failure/error/exception/traceback
language. The only `WARNING` line in the entire log is unrelated to file
reading:

```
2026-09-09 11:37:26,968 - StateMachine - WARNING - Missing handlers for
states: ['MASS_CALCULATION', 'HISTOGRAM_CREATION', 'POST_PROCESSING']
```

-- this is expected and harmless: those three pipeline stages are
intentionally disabled for this analysis (it computes masses itself in a
standalone script), so the state machine correctly notes it has no handler
registered for states it will never enter. The run's own final summary
confirms a clean finish:

```
2026-09-09 14:10:41,311 - StateMachine - INFO -   has_error: False
2026-09-09 14:10:41,311 - StateMachine - INFO -   error_message: None
```

The `.err` file (PBS's captured stderr) is 7 lines long and every line is a
routine `tqdm` progress-bar update -- nothing else.

### Coverage: complete, 238 of 238 files, for all six records

```
2026-09-09 14:10:40,659 - ParsingHandler - INFO - File opens record_30521: 47/47 succeeded, 0 failed (0.0% failure)
2026-09-09 14:10:40,659 - ParsingHandler - INFO - File opens record_30554: 86/86 succeeded, 0 failed (0.0% failure)
2026-09-09 14:10:40,659 - ParsingHandler - INFO - File opens record_30522: 29/29 succeeded, 0 failed (0.0% failure)
2026-09-09 14:10:40,659 - ParsingHandler - INFO - File opens record_30555: 28/28 succeeded, 0 failed (0.0% failure)
2026-09-09 14:10:40,659 - ParsingHandler - INFO - File opens record_30528: 29/29 succeeded, 0 failed (0.0% failure)
2026-09-09 14:10:40,659 - ParsingHandler - INFO - File opens record_30561: 19/19 succeeded, 0 failed (0.0% failure)
...
2026-09-09 14:10:40,660 - ParsingHandler - INFO - Parsing complete: 238/238 files, 321425248 events, 100.0% success rate
```

47+86+29+28+29+19 = 238, matching the project's own documented file counts
for these six records exactly. **This log accounts for literally every file
this run processed -- 100% coverage, not a sample.**

**Verdict for this run: zero warnings of the kind this bug would produce,
across complete (238/238 file) coverage, confirmed by three independent log
copies (the run's own file log, and PBS's separately-captured stdout and
stderr) that all agree.**

## What this does, and does not, let you conclude

- **About the Part B run specifically**: high confidence that no input file
  failed to yield its particle collections during that run. Coverage is
  complete (238/238), the log survived in three independent copies that
  agree with each other, and neither warning string nor any other
  failure/skip language appears anywhere.
- **About the 2216-candidate run specifically**: this log check adds
  **nothing** -- no logs survive for it in any form, so its coverage from
  logs is 0%, not partial. The only evidence available for that run remains
  what the prior document already established from its surviving output
  files (~4% coverage, nothing wrong found in that ~4%).
- **These are not the same run** and their results are not combined into
  one number here, per instructions. A clean log for Part B is not evidence
  about the 2216 run -- it is evidence that, on a later date, after other
  fixes had already landed, the same six datasets could be parsed
  completely without this failure mode showing up. It says nothing
  one way or the other about what happened specifically on 2026-09-08.

## Is the question closed or still open?

**Still open, specifically for the 2216 number.** Between the two
investigations (parsed-output check: ~4% coverage, clean; log check: 0%
coverage, no logs exist), neither reaches complete coverage of the actual
run that produced 2216. Nothing found in either check points at a problem,
but "nothing found in incomplete evidence" is not the same as "confirmed
clean." The Part B run's complete, clean 238/238 log is reassuring context
-- it shows the failure mode is not somehow inevitable or common for these
datasets -- but it is evidence about a different run on a different day,
not proof about 2026-09-08 specifically.
