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

## Where things land

- Logs (PBS stdout/stderr): `/storage/agrp/berkom/atlas-utilization/logs/hgg_d1d2/`,
  `.../hgg_d3/`, `.../hgg_data/`, `.../hgg_signal/`
- D1/D2 results: `/storage/agrp/berkom/atlas-utilization/output/hgg_d1d2_reproduce/reproduce_check_b_and_c_results.json`
  and `timing_and_stderr.log` in the same directory.
- D3 results: `/storage/agrp/berkom/atlas-utilization/output/hgg_d3_data/`
  (`d3_data_report.json`, `d3_data_mgg_plot.png`, `timing_and_memory.log`)
  and `.../hgg_d3_signal_ggh/` (`d3_signal_report.json`,
  `d3_signal_mgg_plot.png`, `timing_and_memory.log`).
- Pilot data: `/storage/agrp/berkom/atlas-utilization/output/cms_hgg_data/job_1/`
  and `job_2/` (each with `parsed_data/`, `selected/`, `logs/`).
- Pilot signal: `/storage/agrp/berkom/atlas-utilization/output/cms_hgg_signal_<label>_pilot/`
  for `<label>` in ggh, vbf, wplush, wminush, zh, tth.

Check job status with `qstat -u $USER`; a finished job's `#PBS -o`/`-e`
files (see each script's header for the exact paths) have the run's own
`echo` progress lines plus any Python traceback if something failed.

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
- **Both**: read `timing_and_memory.log`'s `Elapsed (wall clock) time` and
  `Maximum resident set size` lines. **Use these two numbers, x2 for
  safety, to replace the placeholder `#PBS -l mem`/`walltime` values in
  `pbs_hgg_data_array.sh` and `pbs_hgg_signal.sh` before submitting the
  full run** -- this is the whole reason D3 runs before the full
  submission. `output_file_sizes_bytes` in each report tells you
  approximately how much Lustre space the full run will need (data: x133
  data files across the two records; signal: scale ggH's number to each
  record's own file count and event-rate -- ggH has by far the most
  events/file of the 6 records, see `pbs_hgg_signal.sh`'s own comment).

## 3. Pilot review (2 data files, 1 file per signal record)

- `qstat -u $USER` shows all 8 jobs finished (not held, not still queued
  after a reasonable time given D3's walltime numbers).
- Each `.../job_1/selected/job_metadata.json` and
  `.../job_2/selected/job_metadata.json` (data) and each
  `.../cms_hgg_signal_<label>_pilot/selected/job_metadata.json` (signal)
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
      --jobs-base /storage/agrp/berkom/atlas-utilization/output/cms_hgg_data \
      --total-jobs 2 --out /tmp/pilot_data_merge.json
  ```
  (note `--total-jobs 2`, not 133 -- this is only the pilot) and the
  equivalent `--mode signal` call with the 6 `_pilot` run directories,
  and confirm `status == "COMPLETE"` for both (no `--force` needed -- if
  the pilot itself needs `--force` to look complete, do not proceed to
  the full run).
- No data event anywhere in the pilot's normal (non-`_BLINDED_SIGNAL_REGION`)
  outputs falls in [115, 135] GeV -- this is actually asserted
  automatically by `studies.hgg_cms.output.read_output` on any read of a
  normal file without `unblind=True` (see
  `tests/test_output_blinding.py`), so simply reading each normal output
  file once (e.g. via that same `read_output` function in a throwaway
  script) doubles as this check.

## Resource-estimate reference numbers

The placeholder values currently in `pbs_hgg_data_array.sh`
(`mem=4gb`, `walltime=02:00:00`) and `pbs_hgg_signal.sh` (`mem=8gb`,
`walltime=04:00:00`) were NOT derived from a real measurement -- they are
starting guesses. Do not submit the full run with these placeholders
still in place; replace them using D3's `timing_and_memory.log` numbers
(x2 safety factor) as described above, and re-syntax-check
(`bash -n <script>.sh`) after editing.
