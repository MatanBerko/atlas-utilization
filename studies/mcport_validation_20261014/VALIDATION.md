# MC-port validation, 14 Oct 2026: result

**Result: IDENTICAL, for data and for MC.**

`feature/cms-mc-on-master-20261014` (`5906dcf`) is the MC weighting work
ported onto the rebuilt master without modifying any upstream file. Its
sibling-aware prune lives in a CMS-owned copy,
`studies/cms_mc_weights_v3/deliver/cms_shard_pruning.py`.

- **A. Data:** the port changes nothing. Per-file outputs and the mini
  delivery are bit-identical to this morning's rebuilt-master validation.
- **B. MC:** the port reproduces the 10 Oct pilot. Per-file outputs,
  including every MC weight sibling array, are bit-identical to the original
  pilot outputs. The weighted MC histograms built by the new branch are
  bit-identical to those built by the old MC branch.

Everything below is **VERIFIED BY RUNNING** on the Weizmann cluster on
14 Oct 2026, unless marked otherwise. Jobs, directories and commands are in
`HANDOFF.md`.

## A. Data unchanged by the port

The same 8 files as the rebuild validation, run with the same launcher
(`pbs_matched4.sh`, `POPULATION=matched4`, no extra options) from a checkout
pinned to `5906dcf`, and compared with this morning's NEW-side outputs
(`work/rebuild_validation_20261014/new/`, commit `6a055e8`, read-only).
The comparison used `compare.py`, copied unchanged from
`validate/rebuild-2026-10-14`.

| job | mass arrays | values | result |
|---|---:|---:|---|
| DoubleMuon/job_0 | 4,434 | 3,617,822 | IDENTICAL |
| DoubleMuon/job_1 | 4,710 | 3,945,024 | IDENTICAL |
| SingleMuon/job_0 | 8,360 | 7,399,932 | IDENTICAL |
| SingleMuon/job_1 | 7,051 | 2,632,129 | IDENTICAL |
| DoubleEG/job_0 | 2,443 | 953,922 | IDENTICAL |
| DoubleEG/job_1 | 2,646 | 1,003,684 | IDENTICAL |
| MuonEG/job_0 | 3,041 | 172,380 | IDENTICAL |
| MuonEG/job_1 | 3,338 | 176,547 | IDENTICAL |
| **total** | **36,023** | **19,901,440** | **IDENTICAL** |

The comparison covered 78,567 metadata values, including the event counts at
every selection step and every final-state label. Only `created_utc`,
`elapsed_sec` and `git_commit` differ.

**Mini delivery (8 files), compared with this morning's NEW mini delivery:**
698 vs 698 histograms in the full-grid file (699,396 bins) and in the
cropped file (24,649 bins). Every bin, edge, variance and entry count is
identical, and so are the build summary and the manifest once paths are
normalised.

Raw: `results/data_runs_rebuild_vs_mcport.json`,
`results/data_delivery_rebuild_vs_mcport.json`.

## B. MC reproduces the 10 Oct pilot

**Files:** the first 2 pilot files of each pilot process: 67801
TTTo2L2Nu files 0 and 1, 35669 DYJetsToLL_M-50 NLO files 0 and 1, and 37728
GluGluHToZZTo4L_M125 files 0 and 1. Run with the pilot's own launcher and
options (`pbs_mc_pilot.sh`: `--is-mc --dataset-label MC --population
matched4`, `mem=6gb`, `walltime=02:00:00`, `io=25`). The pilot ran from
`cbfb837`, whose `run_dataset_on_file.py` and `services/` are byte-identical
to the old branch head `68ab281`.

**Per-file, 10 Oct pilot originals vs NEW:** all 8 shards per file,
every array decoded and compared element by element.

| file | events read | accepted | labels | arrays | values | of which MC sibling arrays | result |
|---|---:|---:|---:|---:|---:|---:|---|
| 67801/job_0 | 136,000 | 78,632 | 197 | 59,773 | 19,209,477 | 42,695 | IDENTICAL |
| 67801/job_1 | 1,260,000 | 727,390 | 277 | 89,285 | 177,200,513 | 63,775 | IDENTICAL |
| 35669/job_0 | 1,933,726 | 696,604 | 120 | 30,296 | 35,205,492 | 21,640 | IDENTICAL |
| 35669/job_1 | 1,931,733 | 694,408 | 119 | 30,828 | 35,073,626 | 22,020 | IDENTICAL |
| 37728/job_0 | 4,000 | 2,076 | 73 | 16,695 | 150,745 | 11,925 | IDENTICAL |
| 37728/job_1 | 37,000 | 19,316 | 136 | 34,916 | 1,449,070 | 24,940 | IDENTICAL |
| **total** | | | | **261,793** | **268,288,923** | **186,995** (191,634,945 values) | **IDENTICAL** |

The sibling arrays are `_mcraw_genw`, `_mcraw_l1pf`, `_mcraw_puntrue`,
`_mcraw_acc` and `_mcraw_ele27pt`, in equal numbers. `_mcw` is written by
the builder, not per file. Only `created_utc`, `elapsed_sec` and
`git_commit` differ in the metadata.

The originals were never opened in place. The 6 pilot job directories were
copied into this task's work directory, and the comparison tool copies each
database again before opening it.

**Weighted MC builds, OLD MC branch (`68ab281`) vs NEW (`5906dcf`):** same
6 files, the pilot's default build (`pbs_pilot_build.sh WHAT=build_default`),
each side built by its own pinned checkout.

| file | histograms | bins | sum of weights (OLD = NEW) | result |
|---|---:|---:|---:|---|
| `pilot_record67801_mc.root` | 1,651 | 1,654,302 | 4,187,079.043 | IDENTICAL |
| `pilot_record35669_mc.root` | 1,296 | 1,298,592 | 14,921,911.947 | IDENTICAL |
| `pilot_record37728_mc.root` | 773 | 774,546 | 107.763 | IDENTICAL |
| `pilot_summedSM_mc.root` | 1,651 | 1,654,302 | 19,109,098.753 | IDENTICAL |

Names, bin edges, bin contents, variances (sumw2, present in every
histogram), entries and titles are all exactly equal. Both build reports
record the prune as 110 final states removed with 0 orphan rows. Apart from
paths, they differ only in `generated_utc` and `git_commit`.

**PR #34:** the new master contains upstream's #34 label-reading fix, which
the old MC branch predates. No difference appeared anywhere. The only #34
function on the per-file path, `is_finalstate_contain_combination`, gives the
same answer under both readings for every combination used.

Raw: `results/mc_runs_pilot_vs_new.json`, `results/mc_builds_old_vs_new.json`,
`results/mc_build_new_report.json`.

## D3 proofs (sibling-aware prune), re-run against the CMS copy

| check | result |
|---|---|
| `probe/check_d3_sibling_pruning.py` (Mac) | CMS copy: 0 orphan rows. Upstream's unmodified function on the same probe: 4 orphans, exactly the recorded pre-fix result (`evidence/check_d3_sibling_pruning_out.json`) |
| `cluster/check_prune_regex_data_neutral.py` (cluster, 8 real data shards, scratch copies) | **DATA-NEUTRAL**: upstream (`e1ce8bb`) and CMS copy both remove 88 final states, 7,996 → 2,502 signatures, 2,743,574 → 2,706,361 entries (`results/prune_regex_data_neutral.json`) |
| `tests/test_cms_shard_pruning_drift.py` (Mac) | 4/4 pass; also shown to fail when one D3 line is altered |

## Plots (`results/plots/`)

Each plot shows OLD (solid) and NEW (dashed) with a NEW/OLD ratio panel.
Every one has identical bins and a ratio of exactly 1.

| plot | what |
|---|---|
| `mc_1.png` | ttbar 67801, weighted: `ROI_mass_m0j0b0_cat_0ex_1mx_1jx_1bx_width_10.0` |
| `mc_2.png` | ttbar 67801, weighted: `ROI_mass_j0b0_cat_0ex_1mx_1jx_1bx_width_10.0` |
| `mc_3.png` | DY 35669, weighted: `ROI_mass_m0j0_cat_0ex_1mx_1jx_0bx_width_10.0` |
| `mc_4.png` | ggH→4l 37728, weighted: `ROI_mass_m0m1j0_cat_0ex_2mx_1jx_0bx_width_10.0` |
| `mc_5.png` | summed SM, weighted: `ROI_mass_m0j0_cat_0ex_1mx_1jx_0bx_width_10.0` |
| `data_1.png` | data mini delivery: `ROI_mass_m0j0_cat_0ex_1mx_1jx_0bx_width_10.0` |
| `data_2.png` | data mini delivery: `ROI_mass_m0j0j1_cat_0ex_1mx_2jx_0bx_width_10.0` |
| `summary_table.png` | every comparison in one table |

## Limits

- 8 data files and 6 MC files. Identity on the other files is UNVERIFIED by
  running; the code-level checks (byte-identical driver, function-by-function
  comparison, drift test) cover them.
- The MC builds use only 6 files, so their Σw normalisation is a
  6-file normalisation on both sides. That is fine for an old-vs-new
  comparison, but these are not physics results.
- Note, not a defect: the D3 pattern accepts lower-case sibling suffixes only
  (`_mcraw_[a-z0-9]+`). All five current suffixes are lower-case. A future
  mixed-case suffix would be missed by the prune, and the MC builder's own
  orphan check would then stop the build.
