# HANDOFF — four-dataset luminosity-coverage check

## What was asked

Do our CMS Open Data files contain every certified (golden JSON)
lumisection of Run2016G+H, and how much recorded luminosity sits in
certified lumisections absent from each of the four delivered datasets
(DoubleMuon, SingleMuon, DoubleEG, MuonEG; 390 files)?

The earlier task answered this for DoubleEG alone
(`studies/hgg_cms/impl_checks/lumi_coverage/LUMI_DECISION.md`: 682 missing
sections, 0.000688616 fb⁻¹, 0.0042% of the official total, so the official
16.393380531 fb⁻¹ was adopted unchanged). DoubleMuon, SingleMuon and MuonEG
were never checked, and `studies/m0m1j0_cms/cluster/make_variants_plots.py`
labels the value explicitly "UNVERIFIED for DoubleMuon specifically".

## Decision rule (approved by Matan BEFORE the measurement)

* Every dataset misses **< 0.1%** of the luminosity **and** the DoubleEG
  re-derivation reproduces 0.0042% → keep **16.393380531 fb⁻¹ (± 1.2%)**
  unchanged for both delivery files, and update the two delivery READMEs.
* Any dataset ≥ 0.1%, or DoubleEG does not reproduce → **STOP** after the
  measurement, report the numbers, change no README.

`aggregate_coverage.py` evaluates this rule itself and records the verdict
in `decision.passed` of the summary JSON — it is not a judgement made by
hand afterwards.

## Pinned commit and branch

| | |
|---|---|
| branch | `study/lumi-coverage-four-datasets` (fork `MatanBerko/atlas-utilization`) |
| code commit the jobs ran from | **`56b3db394e80040124b1a642b7352b8ba55a05a2`** (`56b3db3`) |
| base | `origin/master` `2734dd3` |

The cluster checkout was a shallow clone of exactly that branch, verified by
the submit script's preflight to be clean and identical to
`origin/study/lumi-coverage-four-datasets` before any job was submitted.

## Where everything ran and landed

Work directory (new, dated, nothing else on the cluster was written to):

```
/storage/agrp/berkom/atlas-utilization/work/lumi_coverage_four_20261013/
    repo/            pinned checkout (tarred to repo.tar and removed at the end)
    data/            pp_2016lumibyls.csv, 21,137,550 bytes, downloaded from
                     https://opendata.cern.ch/record/1059/files/pp_2016lumibyls.csv
    out/             present_<Dataset>_<G|H>.json   (8 files, one per record)
                     coverage_summary.json          (aggregation + decision)
                     missing_lumi_per_dataset.png   (the figure)
    logs/            lumi_cov_<index>.out / .err    (16 files)
    record_keys.txt  array index -> record key mapping
    job_id.txt       the submitted array job id
```

Nothing was written to `$HOME`. No existing directory under `output/` was
read from, written to, moved or renamed. `/storage/agrp/marybo/` was never
accessed. No ACL or permission was changed.

## Jobs

| | |
|---|---|
| array job id | **`5220621[].pbs`** |
| subjobs | 8 — one per (dataset, era) record, covering all 390 files |
| queue | `N`, `#PBS -m n`, `select=1:ncpus=1:mem=4gb`, `walltime=04:00:00`, `io=30` |
| logs | `-o`/`-e` into `logs/`, which the submit script creates **before** `qsub` (PBS silently discards logs if the directory does not exist) |

Array index → record:

```
1 DoubleMuon_G   2 DoubleMuon_H   3 SingleMuon_G   4 SingleMuon_H
5 DoubleEG_G     6 DoubleEG_H     7 MuonEG_G       8 MuonEG_H
```

File-count quota at submission: **110,708 used of 150,000** (39,292 of
headroom); this run adds about 25 files.

## Method

Per file, only the small `LuminosityBlocks` tree is opened, and only its
`run` and `luminosityBlock` branches — no event content is read. This is the
method of `recompute_missing_sections.py` from the earlier DoubleEG task,
changed only in that the file list comes from the repository's own committed
`studies/cms_datasets/evidence/record_file_lists.json` rather than a live
portal fetch, that files are opened over xrootd (this runs on the cluster),
and that one record is handled per process so the work can be an array.

Ground truths, both the earlier task's:

* certified list — 2016 golden JSON, CERN Open Data record 14220, committed
  at `data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt`;
* per-lumisection recorded luminosity — `pp_2016lumibyls.csv`, CERN Open
  Data record 1059, CMS's own `brilcalc --byls` over the certified list with
  `normtag_PHYSICS_pp_2016`. Not committed (21 MB intermediate); re-download
  it from the URL above.

A subjob that cannot read one of its files **fails** rather than reporting
fewer lumisections, and `aggregate_coverage.py` refuses to aggregate any
record whose JSON reports a failed or short read — a transient xrootd error
must never be mistaken for a genuinely absent lumisection.

## How to resume

Everything below runs from the pinned checkout (untar `repo.tar` if the
directory has already been archived).

```bash
W=/storage/agrp/berkom/atlas-utilization/work/lumi_coverage_four_20261013

# 1. Is the array still running?
/opt/pbs/bin/qstat -t 5220621[] | tail -20

# 2. All eight outputs present, none reporting a failed file?
ls -l $W/out/present_*.json | wc -l          # expect 8
grep -l '"n_files_failed": [^0]' $W/out/present_*.json   # expect nothing

# 3. Re-run one record only (e.g. index 4, SingleMuon_H)
cd $W/repo
source /usr/wipp/conda/24.5.0/etc/profile.d/conda.sh
conda activate /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
python studies/lumi_coverage_four_datasets/read_lumisections_for_record.py \
    --record-key SingleMuon_H --output-dir $W/out

# 4. Aggregate + plot (cheap; run on the analysis node under nice)
nice -n 10 python studies/lumi_coverage_four_datasets/aggregate_coverage.py \
    --inputs-dir $W/out --lumi-csv $W/data/pp_2016lumibyls.csv \
    --out-json $W/out/coverage_summary.json
nice -n 10 python studies/lumi_coverage_four_datasets/make_coverage_plot.py \
    --summary $W/out/coverage_summary.json \
    --out $W/out/missing_lumi_per_dataset.png
```

The whole array can be resubmitted from scratch with

```bash
WORK_DIR=$W bash $W/repo/studies/lumi_coverage_four_datasets/cluster/submit_lumi_coverage.sh
```

but note its preflight refuses to submit into a non-empty `out/`, so clear
or move the previous outputs first — deliberately, so a partial rerun cannot
silently mix with an earlier one.

## Results

Committed to this branch alongside the code once the array finished:
`LUMI_COVERAGE_REPORT.md`, `coverage_summary.json` and
`missing_lumi_per_dataset.png` in this directory.
