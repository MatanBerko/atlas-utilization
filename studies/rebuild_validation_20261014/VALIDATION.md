# Rebuild validation, 14 Oct 2026: result

**Result: IDENTICAL.** The old code (fork master `ba89791`) and the new code
(`rebuild/master-2026-10-14` = upstream `e1ce8bb` + added CMS files,
`6a055e8`) produce exactly the same output on the same 8 files: every count,
every final-state label, every stored mass value, and every histogram bin
of a mini delivery. The new code also reproduces the original 7 Oct 2026
production outputs (commit `06778c9`) for those 8 files exactly.

Everything below is **VERIFIED BY RUNNING** on the Weizmann cluster on
14 Oct 2026, unless marked otherwise. Job IDs, directories and how to re-run
are in `HANDOFF.md`.

## What was run

- **Files:** the first 2 files of each dataset's 7 Oct production list,
  8 in total (`results/files.json`): DoubleMuon 30522/0–1, SingleMuon
  30530/0–1, DoubleEG 30521/0–1, MuonEG 30528/0–1 (all Run2016G).
- **Per-file production**, twice, with the same launcher and options as
  the 7 Oct Step C (`pbs_matched4.sh`, `POPULATION=matched4`, no extra
  options, `walltime=03:00:00`): OLD array `5223392[]`, NEW array
  `5223393[]`. 16/16 subjobs exited 0.
- **Mini delivery**, once per side with that side's own checkout and no
  extra flags (as on 7 Oct, `pbs_delivery.sh`): OLD `5223462`, NEW
  `5223463`, both exit 0.
- **Comparison**: `compare.py` (this folder). Standalone (numpy and
  uproot only, no repo imports), so the same script judges both sides.
  Self-tested on synthetic data first: it reports identical inputs as
  identical and catches a single changed count or mass value.

## 1. Per-file outputs: OLD vs NEW, and 7 Oct vs NEW

For every job, all 8 shard databases (inclusive/exclusive × generic, top4,
nonjet4, rare4) were compared table by table: every stored mass array
decoded and compared element by element (bitwise), the final-state count
table row by row, and the shard metadata. `job_metadata.json` was compared
key by key, which covers the event counts at every selection step, the
final-state labels with their event counts, and all per-file statistics.

| job | events read | after golden JSON | after trigger | accepted | exclusive | final-state labels | mass arrays | mass values | OLD vs NEW | 7 Oct vs NEW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| DoubleMuon/job_0 | 2,315,223 | 2,298,786 | 729,741 | 223,393 | 223,393 | 48 | 4,434 | 3,617,822 | IDENTICAL | IDENTICAL |
| DoubleMuon/job_1 | 2,467,200 | 2,458,556 | 789,513 | 243,417 | 243,417 | 47 | 4,710 | 3,945,024 | IDENTICAL | IDENTICAL |
| SingleMuon/job_0 | 2,939,781 | 2,931,332 | 1,878,767 | 1,511,878 | 1,425,358 | 109 | 8,360 | 7,399,932 | IDENTICAL | IDENTICAL |
| SingleMuon/job_1 | 1,090,938 | 1,051,902 | 668,199 | 537,778 | 506,789 | 89 | 7,051 | 2,632,129 | IDENTICAL | IDENTICAL |
| DoubleEG/job_0 | 2,014,154 | 1,912,413 | 219,416 | 60,201 | 60,189 | 31 | 2,443 | 953,922 | IDENTICAL | IDENTICAL |
| DoubleEG/job_1 | 1,967,602 | 1,951,463 | 229,111 | 64,044 | 64,037 | 31 | 2,646 | 1,003,684 | IDENTICAL | IDENTICAL |
| MuonEG/job_0 | 2,238,235 | 2,237,659 | 279,559 | 4,512 | 394 | 44 | 3,041 | 172,380 | IDENTICAL | IDENTICAL |
| MuonEG/job_1 | 2,170,629 | 2,158,638 | 276,331 | 4,586 | 374 | 44 | 3,338 | 176,547 | IDENTICAL | IDENTICAL |
| **total** | | | | | | | **36,023** | **19,901,440** | **IDENTICAL** | **IDENTICAL** |

78,567 metadata values were compared across the 8 jobs. The only fields that
differ are the three provenance fields, as expected: `created_utc`,
`elapsed_sec` and `git_commit` (`ba89791` / `06778c9` vs `6a055e8`). The file
URL is the same on both sides for every job.

Raw results: `results/runs_old_vs_new.json`, `results/runs_7oct_vs_new.json`.

The 7 Oct outputs were read without being touched: each shard database
(with its `-wal`/`-shm` side files, which were 0-byte leftovers dated
10–11 Oct) was copied to a temporary directory and opened there.

## 2. Mini delivery from the 8 files: OLD vs NEW

The ≥100-events-per-final-state rule leaves **698 histograms in 52
final-state categories** with only 8 files (the full 7 Oct delivery has
1,975 in 103), so the comparison covers real histograms; no pre-threshold
workaround was needed.

| file | histograms | bins compared | entries | result |
|---|---:|---:|---:|---|
| `rv8_four_dataset_bumpnet.root` (full 0–10000 GeV grid) | 698 vs 698 | 699,396 | 1,337,143 vs 1,337,143 | IDENTICAL |
| `rv8_four_dataset_bumpnet_cropped.root` | 698 vs 698 | 24,649 | 1,337,143 vs 1,337,143 | IDENTICAL |

Each histogram was compared on name, bin edges, bin contents including
under/overflow, variances, entry count and title, all exactly. The build
summary and the manifest are identical once the two sides' directory paths
are replaced by placeholders, and so is `README.txt`.

Raw result: `results/delivery_old_vs_new.json`; the NEW side's build
summary: `results/mini_delivery_new_build_summary.json`.

## 3. Plots (`results/plots/`)

Each plot overlays OLD (solid) and NEW (dashed) with a NEW/OLD ratio panel
underneath. In every one, the bins are identical and the ratio is exactly 1.

| plot | what |
|---|---|
| `delivery_1.png` | mini delivery, most populated: `ROI_mass_m0j0_cat_0ex_1mx_1jx_0bx_width_10.0` (285,244 entries) |
| `delivery_2.png` | `ROI_mass_m0j0j1_cat_0ex_1mx_2jx_0bx_width_10.0` (61,662) |
| `delivery_3.png` | `ROI_mass_j0j1_cat_0ex_1mx_2jx_0bx_width_10.0` (57,049) |
| `delivery_4.png` | `ROI_mass_m0j1_cat_0ex_1mx_2jx_0bx_width_10.0` (55,266) |
| `perfile_DoubleMuon.png` | DoubleMuon file 0, 2μ, m(μμ) (178,006 values) |
| `perfile_SingleMuon.png` | SingleMuon file 0, 1μ+1j, m(μj) (256,570) |
| `perfile_DoubleEG.png` | DoubleEG file 0, 2e, m(ee) (48,802) |
| `perfile_MuonEG.png` | MuonEG file 0, 1e+1μ, m(eμ) (998) |
| `summary_table.png` | every comparison in one table |

The delivery histograms combine all four datasets; the four per-file plots
show each dataset on its own. `results/plots/plots_info.json` has the numbers
behind each plot.

## Limits of this check

- 8 of 390 files (era G only). Because the code paths are shared, the
  function-by-function source comparison (Phase 2 of the rebuild task) is
  what covers the other files. Identity on the remaining 382 files is
  UNVERIFIED by running.
- The comparisons ran on the cluster's `atlas-pipeline` environment, the
  one the production uses. The Mac environment was not used for
  production.
