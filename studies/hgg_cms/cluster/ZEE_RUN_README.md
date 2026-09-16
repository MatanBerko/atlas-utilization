# Z->e+e- control-region run: what it is, what it costs, how to launch it

**Implementation task 6, Part 4. NOT SUBMITTED. This task does not run
`submit_zee.sh` -- prepared only, per its own instruction.**

## What this measures

Validates the photon-energy modeling used everywhere in the H->gamma-gamma
analysis, by reconstructing Z->e+e- decays THROUGH THE SAME photon object
collection -- the identical method the reference paper itself uses
(arXiv:1804.02716, Table 2): take the normal photon selection, but invert
the electron veto (`Photon_electronVeto == False`, so electrons ARE let
through as "photon" objects), keep the same trigger-mimicking cuts, and
look for a pair mass near the Z boson (91.19 GeV, PDG) instead of the
Higgs. See `DESIGN_SELECTION.md` Section 5.2 for the pre-set acceptance
criterion this feeds (data peak within +-1 GeV of DY simulation's peak;
widths within 30% relative) -- that comparison itself happens in a LATER
task, once this run's output exists; this task only prepares the run.

A second, separate sample (the "trigger-efficiency sample") measures how
efficient the diphoton trigger itself is, using an ORTHOGONAL trigger
(`HLT_Ele27_WPTight_Gsf`, confirmed present in both the DoubleEG data and
the DY simulation, 16 Sep 2026, metadata-only branch check) to select
events without any dependence on the diphoton trigger, then checks
(records, doesn't filter on) whether the diphoton trigger ALSO fired for
each. This feeds Part 3B's flagged low-edge check -- whether the
`Mass90` online mass requirement is sculpting the 100-105 GeV region.

## The four jobs

| variant | dataset | files | mass window | what it's for |
|---|---|---:|---|---|
| `data_<mode>` | DoubleEG (30521+30554) | 133 | 70-110 GeV | main Z peak, data side |
| `dy_<mode>` | DYJetsToLL_M-50 (record 35669) | 41 | 70-110 GeV | main Z peak, simulation side |
| `data_trigeff_<mode>` | DoubleEG | 133 | >95 GeV | trigger-eff probe, data |
| `dy_trigeff_<mode>` | DYJetsToLL_M-50 | 41 | >95 GeV | trigger-eff probe, simulation |

(`<mode>` is `pilot` for a 2-file-per-variant sanity check, or `full` for
the real 133/41-file run -- see "Launch steps" below.)

Every job is one file per job (a PBS array, same proven pattern as the
main run's `pbs_hgg_data_array.sh`) -- not one job per record like the
H->gamma-gamma signal jobs, because DY (record 35669, 41 files, 71.8M
events -- confirmed postVFP UL16 NanoAODv9, re-verified 16 Sep 2026, see
`studies/hgg_cms/impl_checks/mapping_check/cms_zee_dy_file_list.json`) is
far bigger than any single H->gamma-gamma signal record and bundling it
into one job risks an unmeasured, possibly large walltime -- see
`pbs_hgg_zee_array.sh`'s own header for the full reasoning.

## What the shared pipeline supports here, without any shared-code change

Checked directly against `services/calculations/physics_calcs.py` and
`domain/config.py` before writing any of this:

- **Electron-veto inversion**: NOT a shared-code change. The parsing
  config's `kinematic_cuts.bool_require` only supports "must be True" (no
  "must be False" cut type exists) -- so `electronVeto` is simply OMITTED
  from `bool_require` in the four new configs (both True and False
  photons survive parsing), and `studies/hgg_cms/zee_selection.py` (new,
  analysis-layer) applies the actual inversion.
- **Recording the diphoton trigger bit without filtering on it**: NOT a
  shared-code change either. `parsing_task_config.extra_scalar_branches`
  (an existing, generic "attach this branch, don't filter on it"
  mechanism, `domain/config.py`) attaches the diphoton HLT bit as a plain
  output field while `trigger_requirements` filters on
  `HLT_Ele27_WPTight_Gsf` alone -- confirmed this combination is exactly
  what's needed and requires zero pipeline changes.
- **cern_input_files logging** (task 1's fact-5 improvement): implemented
  for every Z->ee job (`run_zee_selection_on_chunks.py` -- see its own
  docstring), via a new OPTIONAL parameter on
  `studies.hgg_cms.output.write_metadata` (backward compatible, existing
  callers unaffected -- confirmed the existing test suite still passes).

**Nothing here needed a shared-pipeline change or required stopping to
ask.**

## Resource estimate (UNVERIFIED -- no Z->ee-specific pilot has run)

`pbs_hgg_zee_array.sh` reuses the main run's own MEASURED per-file data-
job numbers (mem=5gb, walltime=01:00:00 -- 16 Sep 2026, worst observed
~3 min wall / 2.37 GB peak on a ~2M-event DoubleEG file) for every one of
the 348 subjobs, reasoning that DY's own per-file event count (~1.75M
average) is the same order of magnitude and no per-file step here does
more work than the main run's equivalent step. This is a REASONED
estimate, not a measurement -- **strongly recommend `--pilot` first** (8
subjobs, 2 files per variant) and re-check real `qstat -fx` numbers
against these before `--full`.

**Job count**: 348 scheduler entries (133+41+133+41) for `--full`, 8 for
`--pilot`.

**Runtime**: if the main run's own per-file walltime (worst observed ~3
min) holds, and enough free `shortE`-queue slots are available to run
most of the 348 subjobs concurrently (as the main run's 133-job array
did), wall-clock completion in well under an hour is plausible; if queue
-limited, up to ~348 x 3 min = ~17.4 hours of CUMULATIVE compute (not
necessarily wall-clock) in the worst case.

**Output size**: rough, labeled UNVERIFIED. `DESIGN_SELECTION.md` Section
5.1's 1,000-raw-event single-file check (electron veto inverted, no
golden-JSON filter, wider 50-130 GeV window, TM cuts not yet applied
there) found ~21 candidate pairs/1,000 raw events -- scaling that crude
rate to the full 133-file data statistics (~164.2M raw events, from the
main run's own merge) gives an order-of-magnitude "a few million raw
candidates before the narrower 70-110 window and full TM cuts cut that
down substantially" -- i.e. very likely landing in the same "a few
hundred MB, well under any per-directory or quota limit" range as the
main run's own data output (`PILOT_CHECKLIST.md`'s own estimate, ~100
MB). DY's simulated-Z-peak selection efficiency is expected to be much
HIGHER than data's generic-background rate (real Z decays are literally
what's being reconstructed), but 71.8M raw events is >100x ggH's own
540,000 -- re-check this against the `--pilot` run's real
`job_metadata.json` cutflow numbers before trusting it.

## Launch steps (when you decide to actually run this)

```bash
ssh wipp-home
cd ~/atlas-utilization
git fetch origin && git checkout feature/hgg-selection-and-output && git pull

# 1. Pilot first (8 subjobs) -- strongly recommended before --full.
bash studies/hgg_cms/cluster/submit_zee.sh --pilot
bash studies/hgg_cms/cluster/status_zee.sh --mode pilot
# once all 8 show finished_ok: inspect real walltime/mem with
#   qstat -fx <jobid> for a couple of the pilot subjobs
# and re-check pbs_hgg_zee_array.sh's mem/walltime against them (edit +
# commit + push if they need raising, same as the main run's own D3
# -> full-run resource-sizing step).

# 2. The real run (348 subjobs) -- only after the pilot looks right.
bash studies/hgg_cms/cluster/submit_zee.sh --full
bash studies/hgg_cms/cluster/status_zee.sh --mode full

# 3. Merge each of the 4 variants (once status_zee.sh shows everything
#    finished OK):
mkdir -p /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged
python studies/hgg_cms/cluster/merge_zee_outputs.py \
    --jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_zee/data_full \
    --total-batches 133 \
    --expected-json studies/hgg_cms/impl_checks/mapping_check/cms_hgg_data_file_lists.json \
    --merged-out /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/zee_data.root \
    --out /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/merge_summary_zee_data.json

python studies/hgg_cms/cluster/merge_zee_outputs.py \
    --jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_zee/dy_full \
    --total-batches 41 \
    --expected-json studies/hgg_cms/impl_checks/mapping_check/cms_zee_dy_file_list.json \
    --merged-out /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/zee_dy.root \
    --out /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/merge_summary_zee_dy.json

# (repeat the same two calls with data_trigeff_full / dy_trigeff_full and
#  133/41 -- unchanged expected-json paths, since it's the same 2
#  datasets, just a different analysis-layer selection)
```

DRY_RUN=1 works the same way as `submit_full.sh` (prints every `qsub`
command instead of submitting) for either `--pilot` or `--full`.
