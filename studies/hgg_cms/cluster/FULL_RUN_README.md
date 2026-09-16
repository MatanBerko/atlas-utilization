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

`status_full.sh` reads `submitted_jobs.txt`, queries every one of the 133
data indices and all 6 signal jobs, and reports queued / running /
finished OK / failed for each -- "finished OK" requires BOTH exit code 0
AND the expected output (`selected/job_metadata.json` + at least one
`.root` file) actually existing; an exit-0 job with no output is reported
as FAILED, not OK.

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

## Merging

Once `status_full.sh` shows everything finished OK (or you've decided to
accept a partial run), merge on the analysis node directly -- **no PBS
job needed for this step**: `merge_outputs.py` only reads the small
`job_metadata.json`/`parsing_stats.json` files already produced (about
139 small JSON files total), never opens a ROOT file itself, so it
finishes in well under a second regardless of how much data the run
actually produced. Run it with `nice` anyway, as a courtesy on a shared
node:

```bash
nice python studies/hgg_cms/cluster/merge_outputs.py --mode data \
    --jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_full/data \
    --total-jobs 133 \
    --out /storage/agrp/berkom/atlas-utilization/output/hgg_full/MERGED_DATA.json

nice python studies/hgg_cms/cluster/merge_outputs.py --mode signal \
    --record 37350=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/ggh \
    --record 68497=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/vbf \
    --record 71013=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/wplush \
    --record 70173=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/wminush \
    --record 74132=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/zh \
    --record 67611=/storage/agrp/berkom/atlas-utilization/output/hgg_full/signal/tth \
    --out /storage/agrp/berkom/atlas-utilization/output/hgg_full/MERGED_SIGNAL.json
```

Both refuse to report `status: "COMPLETE"` if anything is missing or
incomplete (a data job missing, or a signal record with fewer processed
files than `signal_sumw.json` says it has) -- add `--force` only if you
have deliberately decided to accept a partial run, which then reports
`status: "COMPLETE_FORCED_WITH_MISSING"` (never a bare `"COMPLETE"`) so
that is never confused with a genuinely full merge later. The signal
merge's per-record `genEventSumw_over_processed_files` is read from the
shared pipeline's own genEventSumw aggregation (never recomputed here),
and covers exactly the files that record's job actually, successfully
processed.

Merged output lands at the two `--out` paths above, under
`/storage/agrp/berkom/atlas-utilization/output/hgg_full/`.

## Blinding reminder

**Never open a file with `_BLINDED_SIGNAL_REGION` in its name** except
through `studies.hgg_cms.output.read_output(path, unblind=True)`, and
even then, never print or plot an individual data event's `m_gg` value
from it -- only counts. This applies to every per-file data output under
`hgg_full/data/job_*/selected/` alike. `merge_outputs.py` never opens any
`.root` file itself (data or blinded), so running the merge step carries
no blinding risk on its own -- the risk is only in what a human (or a
later analysis script, task 7) does with the individual output files
afterward.
