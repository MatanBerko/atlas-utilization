# H->gamma-gamma cluster pilot: what to check before the full submission

`submit_pilot.sh` submits, together, everything that must pass before the
full run (133 data files + all files of 6 signal records) is even
considered:

1. **D1/D2** (`pbs_hgg_d1d2_reproduce.sh`) -- exact reproduction of
   `check_c_trigger_mimicking.py` / `check_b_vertex.py`.
2. **D3** (`pbs_hgg_d3_data.sh`, `pbs_hgg_d3_signal.sh`) -- one full
   DoubleEG Run2016G file, one full ggH file, through the real production
   configs.
3. **A small pilot of the full run itself**: 2 data files (array indices
   1-2) + 1 file per signal record.

Do not submit the full run until every item below is checked and you have
explicitly decided to proceed. `submit_pilot.sh` does not auto-continue.

`submit_pilot.sh` runs a preflight (conda activation, python/XRootD
package check, an XRootD metadata-only open of both D3 files, a
branch/commit/clean-tree check on `$HOME/atlas-utilization`, directory
writability, and a check that no pilot output directory is already
populated) **before submitting anything** -- if any of it fails, nothing
is submitted. See that script's own header comment for exactly what it
checks, and `DRY_RUN=1 bash submit_pilot.sh` to see the exact `qsub`
commands and log paths it would use without submitting anything.

## Where things land

Everything the pilot and D1-D3 produce lives under one tree, entirely
separate from where the full run will write:

- Logs: `/storage/agrp/berkom/atlas-utilization/logs/hgg_pilot/{d1d2,d3,data,signal}/`
- Output: `/storage/agrp/berkom/atlas-utilization/output/hgg_pilot/`
  - D1/D2: `.../hgg_pilot/d1d2_reproduce/reproduce_check_b_and_c_results.json`,
    `timing_and_stderr.log`
  - D3 data: `.../hgg_pilot/d3_data/` (`d3_data_report.json`,
    `d3_data_mgg_plot.png`, `timing_and_memory.log`)
  - D3 signal: `.../hgg_pilot/d3_signal_ggh/` (`d3_signal_report.json`,
    `d3_signal_mgg_plot.png`, `timing_and_memory.log`)
  - Pilot data: `.../hgg_pilot/data/job_1/` and `job_2/` (each with
    `parsed_data/`, `selected/`, `logs/`)
  - Pilot signal: `.../hgg_pilot/signal/<label>/` for `<label>` in ggh,
    vbf, wplush, wminush, zh, tth

The full run's own directories (`.../output/cms_hgg_data/`,
`.../output/cms_hgg_signal_<label>/`) are never touched by any of the
above and should still be empty/nonexistent at this point -- if they are
not, something submitted outside this checklist's process.

Check job status with `qstat -u $USER`; a finished job's `#PBS -o`/`-e`
files (paths above) have the run's own `echo` progress lines plus any
Python traceback if something failed.

## 1. D1/D2 acceptance criteria (PRE-SET -- do not change these numbers after seeing results)

Open `reproduce_check_b_and_c_results.json`'s `"comparison"` dict. Every
one of these must be `true`:

| field | must equal |
|---|---|
| `signal_n_offline_selected_match` | `n_offline_selected == 19986` |
| `signal_hlt_given_offline_match` | `n_hlt_pass_given_offline == 19792` |
| `data_n_candidates_match` | total `n_candidates_100_180 == 92` |
| `data_n_sideband_match` | total `n_sideband == 70` |
| `data_n_blinded_match` | total blinded COUNT `== 22` |
| `signal_shape_n_match` | shape sample size `== 19792` |

If ANY of these is `false`: **do not edit either implementation to force
agreement.** Investigate the root cause (the `signal`/`data` sub-dicts in
the same JSON have the raw numbers) and report it. A plausible, already
-understood source of a difference is the trigger-application-order
distinction documented in `reproduce_check_b_and_c.py`'s own module
docstring -- confirm that reasoning still holds before assuming anything
else.

Also sanity-check `timing_and_stderr.log` (the `/usr/bin/time -v` output)
finished within the job's requested walltime with headroom, and that the
job did not need to exhaust all 10 retry attempts on the ggH read (if it
did, note it -- it would suggest the CERN Open Data portal read is still
flaky even over XRootD, which was this task's working hypothesis for
switching transport but was NOT verified locally, see
`reproduce_check_b_and_c.py`'s own SIGNAL_URL/DATA_FILES comments).

## 2. D3 review

Open `d3_data_report.json` and `d3_signal_report.json`.

- **Data**: `cutflow` counts look sane (non-zero, monotonically
  decreasing through the selection stages); `n_blinded_115_135_count_only`
  is a small integer (not the whole sample, not zero if there's genuine
  Higgs-mass-adjacent background -- compare its rough order of magnitude
  to `check_c_trigger_mimicking.py`'s own numbers if unsure); open
  `d3_data_mgg_plot.png` and confirm the shown sidebands look like a
  falling background shape with the blinded band visibly empty and
  labeled with its count.
- **Signal**: `efficiency_unweighted`/`efficiency_weighted` are both in
  (0, 1) and reasonably close to each other (a large gap suggests
  negative-weight events are doing something unexpected); `shape.inclusive`
  and the two per-category shapes have `mode`/`median` near 125 GeV and a
  plausible `effective_sigma68` (a few GeV, not tens); open
  `d3_signal_mgg_plot.png` and confirm a visible peak near 125 GeV;
  `preview_expected_ggH_yield_SINGLE_FILE_ONLY` is a small positive number
  (it is explicitly NOT the full-record yield -- see its own
  `preview_yield_caveat` field).
- **Both -- resources (see "Resource requests" section below for the
  full procedure)**: read `timing_and_memory.log`'s peak memory, and
  cross-check the job's PBS-accounted walltime with
  `qstat -fx <jobid>` once the job has finished (`resources_used.walltime`,
  `resources_used.mem`) -- these are two independently-measured numbers
  for the same job and should roughly agree; if they don't, prefer the
  larger one when sizing the full run's requests.
  `output_file_sizes_bytes` in each report gives the first REAL per-file
  output size -- compare it against the estimate in "Storage estimate"
  below and correct that estimate if it's off by more than a factor of a
  few.

## 3. Pilot review (2 data files, 1 file per signal record)

- `qstat -u $USER` shows all 8 jobs finished (not held, not still queued
  after a reasonable time given D3's walltime numbers).
- Each `.../hgg_pilot/data/job_1/selected/job_metadata.json` and
  `.../job_2/selected/job_metadata.json` (data) and each
  `.../hgg_pilot/signal/<label>/selected/job_metadata.json` (signal)
  exists and its `cutflow` has non-zero `n_input_events`.
- For signal pilots: `cutflow.dedup_removed_simulation_events == 0` in
  every record's `job_metadata.json` (this task's own guarantee -- see
  `run_selection_on_chunks.py`'s `check_dedup_never_active`; a value other
  than exactly `0`, or an exception instead, means something is
  unexpectedly different from every H->gamma-gamma config this task wrote
  and must be understood before proceeding).
- Run a local (not on the cluster) sanity pass over the pilot's outputs
  once copied off Lustre, e.g.:
  ```
  python studies/hgg_cms/cluster/merge_outputs.py --mode data \
      --jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_pilot/data \
      --out /tmp/pilot_data_merge.json
  ```
  (note `--jobs-base .../hgg_pilot/data`, not the full run's
  `.../hgg_full/data`; `--total-batches` defaults to 133 either way --
  see merge_outputs.py's own module docstring for why that must stay 133
  even for a 2-job pilot: PBS_ARRAY_INDEX values 1 and 2 are still drawn
  from the SAME 133-way split pbs_hgg_data_array.sh's TOTAL_FILES always
  uses, so the file-list reconstruction math must match it) and the
  equivalent `--mode signal` call with the 6 `.../hgg_pilot/signal/<label>`
  run directories. **The pilot is EXPECTED to report `status ==
  "INCOMPLETE"`** for data (only 2 of 133 expected files were ever
  processed -- every other one is correctly listed under `missing_files`)
  -- this is the full-run version of merge_outputs.py's own file-identity
  checks now included by default (implementation task 6, Part 1), not a
  regression from an earlier pilot-only tool. Read the summary and confirm
  the ONLY problems reported are "133 expected files, 2 present" (never a
  duplicate, an unexpected file, or an event-total mismatch on the two
  files that WERE processed) before proceeding to the full run.
- No data event anywhere in the pilot's normal (non-`_BLINDED_SIGNAL_REGION`)
  outputs falls in [115, 135] GeV -- this is actually asserted
  automatically by `studies.hgg_cms.output.read_output` on any read of a
  normal file without `unblind=True` (see
  `tests/test_output_blinding.py`), so simply reading each normal output
  file once (e.g. via that same `read_output` function in a throwaway
  script) doubles as this check.

## 4. Resource requests: basis and how to set them for real

Every `#PBS -l mem`/`walltime` value currently in `pbs_hgg_data_array.sh`
(`mem=4gb`, `walltime=02:00:00`), `pbs_hgg_signal.sh` (`mem=8gb`,
`walltime=04:00:00`), `pbs_hgg_d1d2_reproduce.sh` (`mem=4gb`,
`walltime=03:00:00`), `pbs_hgg_d3_data.sh` (`mem=4gb`,
`walltime=03:00:00`) and `pbs_hgg_d3_signal.sh` (`mem=8gb`,
`walltime=04:00:00`) is a **placeholder guess, not a measurement** --
no local run of the equivalent job ever completed (local remote reads
were too unreliable, which is exactly why D1-D3 moved to the cluster).
The signal jobs' guesses are deliberately larger than the data jobs'
because ggH -- used for D3's own signal measurement -- has by far the
most events/file of the 6 signal records (~178k/file average vs a few
thousand for the smaller modes, see `signal_sumw.json`), so it is treated
as the worst case for `pbs_hgg_signal.sh`'s single template.

**After the pilot (and D1-D3) finish, for each job:**
1. Read `/usr/bin/time -v`'s "Maximum resident set size" from that job's
   own timing log (D1/D2, D3) or add an equivalent wrapper before
   re-running the data/signal pilot jobs a second time if you want a
   directly comparable number for them too.
2. Cross-check with PBS's own accounting: `qstat -fx <jobid>` (after the
   job has finished) reports `resources_used.mem` and
   `resources_used.walltime` independently of `/usr/bin/time`.
3. Set the full run's `#PBS -l mem`/`walltime` to **about 2x the larger
   of the two measured numbers**, and re-run `bash -n <script>.sh` after
   editing. Keep walltime at or under the site's 72h hard maximum
   (default 12h if you have no strong reason to request more).

## 5. Storage estimate (re-check with real pilot numbers)

This is a rough, explicitly-labeled order-of-magnitude estimate for the
FULL run, computed from the output schema and existing metadata -- NOT
from a real measurement (the pilot is what supplies that). Re-derive it
once `output_file_sizes_bytes` is available from the pilot and D3 reports,
and update this section.

**Per-event output row** (`studies/hgg_cms/output.py`'s
`build_output_table`): 8 event-level fields + 2x11 per-photon fields
(lead+sublead), mostly `float64`/`int64` (8 bytes) plus a couple of
`bool`s and one short string ("EBEB"/"notEBEB") -- roughly **205 bytes/
event (data), ~221 bytes/event (simulation, +genWeight+Pileup_nTrueInt)**,
uncompressed. (uproot's default ROOT compression, if any is actually
applied by this uproot version's `recreate()` default, was not verified
in this task -- so this is a conservative, not-smaller-than-reality,
planning number.)

**Signal** (uses real numbers from `signal_sumw.json`): summed
`genEventCount` over all 6 records' 71 total files = 3,433,898 events.
Using ggH's own real measured selection efficiency from `check_c1`
(19986/50000 ~ 40%, the only per-record efficiency actually measured so
far -- applied here as a common rough approximation for all 6 records,
since a precise per-record number would need running the selection on
each) gives ~1.37M selected events across all signal output -> **~300 MB
total**, in 71 output files (one per input file, one per record's own
`selected/` directory -- max 20 files in one directory, for ZH -- well
under the 1000-files-per-directory rule).

**Data**: no total event count across the 133 DoubleEG files is known
locally (would need reading Runs/Events metadata for all 133 files, a
remote-read cost this task does not spend). Using the two file sizes
actually queried this session (1.93 GB and 0.84 GB, for two of the 133
files) as a rough per-file scale, ~1.5 GB/file average, and a raw
NanoAOD events/byte ratio benchmarked from the one file whose event count
IS known precisely (ggH: 533,000 events / 629,014,638 bytes ~ 1180
bytes/event) as a very rough stand-in, points to somewhere in the range
of 1-2 million events per data file, i.e. roughly 150-260 million events
total across 133 files. Applying `check_c2`'s real measured data
selection efficiency (92/50,000 ~ 0.18%) gives on the order of
300,000-500,000 selected data events -> **on the order of 100 MB total**,
in up to 266 output files (133 data jobs x up to 2 files each,
normal+blinded -- one job's own `job_N/selected/` directory has at most 2
files, well under 1000/directory).

**Bottom line (rough, pending real numbers)**: total full-run output on
the order of a few hundred MB to ~1 GB, and a few hundred output files
total -- both far under the site defaults (2 TB, 150,000 files) and the
1000-files-per-directory rule, with no restructuring needed given the
current one-output-per-input-file layout. **Re-check this against the
pilot's own `output_file_sizes_bytes` and `job_metadata.json` counts
before the full submission** -- if the real per-event size or selection
efficiency differs from the rough numbers above by an order of magnitude,
revisit this conclusion.
