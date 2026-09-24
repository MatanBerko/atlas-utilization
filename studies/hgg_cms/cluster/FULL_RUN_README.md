# H->gamma-gamma full cluster run: how to launch, monitor, and merge

## When to submit

**Not before D3's results (still queued as of this writing) have been
reviewed against `PILOT_CHECKLIST.md`.** D1/D2 already passed (all 6
comparisons true) and the pilot's 8 jobs already ran successfully with
real timing/memory numbers, which is what let this task set real
resource requests below -- but D3 is the last outstanding check, and
`submit_full.sh` refuses to run without an explicit
`--i-reviewed-pilot-and-d3` flag specifically because of this.

Also worth reading before submitting: `studies/hgg_cms/impl_checks/mapping_check/`'s
writeup on the data array's index<->file mapping (it relies on the CERN
Open Data portal returning a stable file order across 133 independently
-fetched jobs -- checked, with real evidence, but not something this
project controls or can fully guarantee; see that writeup and this
task's final report for the details).

**Prefer submitting when the cluster is quiet** (e.g. evening) -- the
pilot observed jobs requesting <=02:00 walltime routed to the `shortE`
queue (empty at the time) while jobs requesting 03:00-04:00 walltime
routed to `normE` (busy, "Not enough free nodes available"). The full
run's data array (`walltime=01:00:00`) should route to `shortE` the same
way; the 6 signal jobs (`walltime=02:00:00`) are borderline -- if `normE`
is busy when you submit, they may queue for a while. This is an
observation from the pilot run, not a documented site guarantee -- if
routing behavior seems to have changed, that's worth noting.

## Every PBS job must request `-l io=<value>`

**Added 18 Sep 2026, after a real submission failure**: this cluster's
scheduler rejects a job outright at submission time (`qsub` error "Job
violates queue and/or server resource limits") if it has no `-l io=...`
resource request, REGARDLESS of walltime, mem, or anything else about
the job -- diagnosed with small test jobs (`pbs_hgg_bias_array.sh`,
`studies/hgg_cms/background_model/cluster/`, was submitted without one
and rejected; adding `-l io=5` alone, with nothing else changed, was
accepted). This is not documented anywhere on this project's side
before now, so every new PBS script must include an explicit `-l io=`
line (the existing scripts already have one, at various values 5-30 --
match the I/O this task's job actually does; a small value like `io=5`
is fine for a job that reads a few small JSON/config files rather than
streaming ROOT files). `tests/test_pbs_scripts.py` enforces this: every
`pbs_*.sh` file under `studies/hgg_cms/` must contain an `#PBS -l io=`
line, or the test fails and names the offending file.

## Launch commands

```bash
ssh wipp-home
cd ~/atlas-utilization
git status              # confirm clean, and see what's there before pulling
git fetch origin && git checkout feature/hgg-selection-and-output && git pull

# Read the lfs quota output submit_full.sh will print, decide it's OK, then:
bash studies/hgg_cms/cluster/submit_full.sh --i-reviewed-pilot-and-d3 --quota-checked-manually
```

If `submit_full.sh` refuses at the quota step because `lfs` isn't
available or its output doesn't clearly show enough free space, it will
tell you so and print the exact `lfs quota -u $USER /storage/agrp/berkom`
command to run and read yourself first.

This submits 1 data array job (133 subjobs) and 6 signal jobs (133 + 6 =
139 total scheduler entries), prints every job ID, and saves them to
`/storage/agrp/berkom/atlas-utilization/logs/hgg_full/submitted_jobs.txt`.

## Monitoring

```bash
qstat -u $USER                                        # quick raw view
bash studies/hgg_cms/cluster/status_full.sh            # summarized view (fast, run with nice automatically for its own checks)
```

`status_full.sh` reads `submitted_jobs.txt`, queries all 133 data
subjobs in ONE bulk `qstat -xft "<array-id>"` call (fixed 16 Sep 2026 --
the previous version queried each subjob individually and, due to a
job-id-format bug, misreported every finished subjob as "unknown"; see
that script's own header comment) plus the 6 signal jobs individually,
and reports queued / running / finished OK / failed for each -- "finished
OK" requires BOTH exit code 0 AND the expected output
(`selected/job_metadata.json` + at least one `.root` file) actually
existing; an exit-0 job with no output is reported as FAILED, not OK. It
also prints, for every data job directory that exists, its reconstructed
CERN input file (same method the merge uses -- see "Merging" below) and
flags any file assigned to more than one job index.

## Resubmitting failures

Re-run `status_full.sh` -- if anything failed, it prints, at the bottom,
the exact commands to (a) move that failed attempt's output and logs
aside with a `_failed1_<timestamp>` suffix (never deletes anything), and
(b) resubmit just that data index or signal record. Run those printed
commands as-is.

For a failed data index specifically: the printed command uses
`qsub -J i-i` (a single-element array range) to resubmit just that one
index -- this is expected to work on OpenPBS but was **not verified on
this specific cluster** (no way to test `qsub` from this task). If it's
rejected, `status_full.sh` also prints a commented-out fallback command
using `-v PBS_ARRAY_INDEX=i` instead, which achieves the same thing
without depending on that OpenPBS feature at all -- uncomment and use
that one instead if `-J i-i` fails.

## Merging (implementation task 6, Part 1 -- now includes file-identity checks)

Once `status_full.sh` shows everything finished OK (or you've decided to
accept a partial run), merge on the analysis node directly. This version
of `merge_outputs.py` does two things the earlier pilot-only tool did
not: (1) it reconstructs and cross-checks EVERY processed file's real
CERN identity (data: from each job's own `metadata_cache.json` + its
array index, using the real `utils.batching.get_batch_slice_by_year`,
against the frozen list in `studies/hgg_cms/impl_checks/mapping_check/
cms_hgg_data_file_lists.json`, plus per-record event totals against the
portal's published counts in that same directory's `records.json`;
signal: from each job's own `parsing_stats.json`
`sumw_by_record.processed_files`, against
`cms_hgg_signal_file_lists.json`) and REFUSES `"COMPLETE"` if anything is
duplicated, missing, unexpected, or event-total-mismatched; (2) unless
`--no-merge-root` is passed, it reads every job's own normal (never
blinded) selected-event ROOT file(s) through
`studies.hgg_cms.output.read_output(unblind=False)` (which independently
re-asserts no blinded data event is present, regardless of filename) and
writes ONE merged ROOT file per mode/record under `--merged-dir`. This
does open ROOT files (unlike the old JSON-only tool) but they are small
(selected events only); still comfortably a "few minutes" job -- run with
`nice`, or as a small PBS job (queue N, `#PBS -m n`, walltime 00:30:00,
mem 4gb) if it turns out to be slower than that on the day.

```bash
nice python studies/hgg_cms/cluster/merge_outputs.py --mode data \
    --jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_full/data \
    --merged-dir /storage/agrp/berkom/atlas-utilization/output/hgg_full/merged \
    --out /storage/agrp/berkom/atlas-utilization/output/hgg_full/merged/merge_summary_data.json

nice python studies/hgg_cms/cluster/merge_outputs.py --mode signal \
    --record ggh=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/ggh \
    --record vbf=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/vbf \
    --record wplush=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/wplush \
    --record wminush=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/wminush \
    --record zh=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/zh \
    --record tth=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/tth \
    --merged-dir /storage/agrp/berkom/atlas-utilization/output/hgg_full/merged \
    --out /storage/agrp/berkom/atlas-utilization/output/hgg_full/merged/merge_summary_signal.json
```

(Note `--record LABEL=RUN_DIR`, e.g. `ggh=...`, not the record id --
changed from the pilot-only tool's `--record RECORD_ID=RUN_DIR`.)

Both refuse to report `status: "COMPLETE"` if anything above is missing,
duplicated, unexpected, or mismatched -- add `--force` only if you have
deliberately decided to accept a partial run, which then reports
`status: "COMPLETE_FORCED_WITH_MISSING"` (never a bare `"COMPLETE"`, and
merged ROOT output is still written even when forced) so that is never
confused with a genuinely full/verified merge later. The signal merge's
per-record `genEventSumw_over_processed_files` is read from the shared
pipeline's own genEventSumw aggregation (never recomputed here), and
covers exactly the files that record's job actually, successfully
processed -- for ttH (record 67611) this is over the CURRENT 15-file
portal list, never `signal_sumw.json`'s stale 16-file total (see
`signal_sumw_notes.md`).

Merged output lands under `--merged-dir`:
`data_sidebands.root` + `data_merge_metadata.json`, `signal_<label>.root`
per record, and the two `merge_summary_*.json` files above.

## Blinding reminder

**Never open a file with `_BLINDED_SIGNAL_REGION` in its name** except
through `studies.hgg_cms.output.read_output(path, unblind=True)`, and
even then, never print or plot an individual data event's `m_gg` value
from it -- only counts. This applies to every per-file data output under
`hgg_full/data/job_*/selected/` alike. `merge_outputs.py` NEVER reads a
`_BLINDED_SIGNAL_REGION`-named file, and independently re-asserts (via
`read_output(unblind=False)`) that no blinded event slipped into a
normally-named file either, on every single file it merges -- if that
assertion ever fires, the merge aborts with an exception rather than
writing a contaminated merged file. No merged file containing individual
blinded events is ever produced by this script; only the blinded COUNT is
carried into `data_merge_metadata.json` / `merge_summary_data.json`.
