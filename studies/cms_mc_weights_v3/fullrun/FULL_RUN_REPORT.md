# CMS MC FULL RUN — REPORT (17–18 Oct 2026)

Executed per `FULL_RUN_PLAN.md` §6 with Matan's decisions of 17 Oct (§7).
**Not delivered to anyone. Not merged into master.** Branch
`feature/cms-mc-fullrun-20261017` (origin only).

Every number below is **VERIFIED BY RUNNING** unless marked UNVERIFIED.
Sources: `fullrun/evidence/production_audit.json`,
`fullrun/evidence/reproducibility_pilot_vs_fullrun.json`,
`fullrun/evidence/sanity_report.json`, the PBS logs in
`work/fullrun_20261017/logs/`, and `lfs quota -u berkom /storage`.

## 1. What ran

| step | commit | PBS job(s) | resources | result |
|---|---|---|---|---|
| production, 497 files, 13 records | **`294ee59`** (pinned) | arrays `5234570[]`–`5234582[]` | 6gb, 2h (68187/68073: 3h), io=25 | 497/497 exit 0, no resubmission |
| audit | `dbd3107` | `5243008` | 4gb, 2h, io=25 | verdict OK |
| reproducibility (98 pilot files) | `dbd3107` | `5243009` | 16gb, 8h, io=25 | ALL IDENTICAL |
| build | `dbd3107` | `5243011` | 64gb, 8h, io=25 | exit 0, exactly 1 exclusion (75589/98) |
| sanity + plots | `dbd3107` | `5243647` | 32gb, 4h, io=25 | all checks pass |

- **Pinned commit:** `294ee59bb562a1d6542022444e043a1c15a932e7`. Every production job ran from the checkout `checkouts/fullrun_20261017/repo` at this commit.
- **Post-production commit:** `dbd3107`. It differs from `294ee59` only by additions:
  - the audit script
  - the post-production PBS script
  - the sanity/plots script
  - the HANDOFF
  - `compare.py`/`mc_compare.py`, copied unchanged from `validate/mc-port-20261014`

  `build_mc_delivery.py`, the registry and the per-file code are byte-identical between the two commits (`git diff --name-only 294ee59 dbd3107` lists only the six added files).
- **Build command:** the pilot's default build, with all options at their defaults (`peak_on=weighted`, `min_events_basis=raw`, `min_events_per_fs=100`, `output_mode=both`):
  `build_mc_delivery.py --runs-dir runs --out-dir build_default --out-prefix fullrun --scratch-dir scratch_default --keep-scratch`
- **No physics or convention change:** no `--exclude` and no edit to the mapping. The only exclusion was made by the builder's existing per-file Σw check (D4, tolerance 1e-6), as decided.

## 2. Time, disk, files

### CPU time: actual vs projected

| record | sample | files | projected CPU h | actual CPU h | worst file, projected envelope (s) | worst file, actual (s) |
|---|---|---:|---:|---:|---:|---:|
| 67993 | TTToSemiLeptonic | 138 | 30.18 | 32.17 | 1956 | 1394 |
| 75589 | ZZTo4L | 99 | 21.82 | 15.82 | 2462 | 1471 |
| 67801 | TTTo2L2Nu | 49 | 14.90 | 20.45 | 3065 | 3023 |
| 68187 | TTZToLLNuNu_M-10 | 42 | 16.17 | 18.09 | 4445 | 3793 |
| 35669 | DYJetsToLL_M-50 | 41 | 5.91 | 6.20 | 1357 | 944 |
| 72752 | WZTo3LNu | 31 | 6.42 | 3.49 | 2201 | 900 |
| 35631 | DYJetsToLL_M-10to50 | 25 | 1.69 | 1.01 | 594 | 233 |
| 68847 | VBF H→ZZ→4ℓ | 24 | 3.91 | 2.48 | 2286 | 698 |
| 68073 | TTWJetsToLNu | 12 | 3.97 | 4.38 | 3730 | 3359 |
| 64895 | ST_tW_top | 11 | 2.45 | 1.50 | 2024 | 1173 |
| 64839 | ST_tW_antitop | 10 | 1.97 | 1.71 | 2355 | 1430 |
| 72676 | WWTo2L2Nu | 7 | 1.16 | 0.66 | 2111 | 754 |
| 37728 | ggH H→ZZ→4ℓ | 8 | 1.35 | 1.00 | 2301 | 809 |
| **total** | | **497** | **111.9** | **108.97** | | max **3793** |

- "Actual CPU h" is the sum of the driver's `elapsed_sec` over files (single-threaded jobs).
- **Total: 108.97 h actual vs 111.9 h projected (−2.6%).** The literal projection was 962.1 h, for reference only.
- **Worst files:** every record's slowest file stayed below the projected envelope. The slowest overall was 3,793 s (63 min, 68187), against its 3 h request. Projection and actual were closest for 67801: 3,023 s vs 3,065 s.
- **Peak memory:** 2.93 GB per file, against the 6 GB request.

### Post-production jobs

| job | wall time | CPU | peak memory |
|---|---|---|---|
| audit | 6 s | — | — |
| reproduce | 28 min 35 s | 23 min | 11.9 GB |
| build | 2 h 14 min 59 s | 1 h 12 min (user 3,430 s + sys 910 s) | 10.2 GB RSS (`/usr/bin/time`), 23.1 GB per PBS |
| sanity + plots | 2 h 15 min 18 s | 4 min | 1.5 GB |

The sanity job was I/O-bound: it reads all 50,411 histograms with uproot. Together, the post-production jobs took about 5 h of wall time (each on one core).

### Elapsed time

- **Production arrays:** submitted 17 Oct 11:36 IDT (the time stamp of `jobids.txt`). The first file finished at 11:43 and the last file's `job_metadata.json` was written 18 Oct 07:31, so about 20 h elapsed for 109 CPU h.
- **Why it took that long:** the group io limit (`Server per-group limit reached on resource io`) held the last 44 normE subjobs (68187, 68073) for many hours.
- **Post-production:** 15:13–19:46 IDT, 18 Oct.

### Disk (apparent size)

| area | size |
|---|---|
| `runs/` | 55.3 GB (52 GiB); projected 67.8 GB |
| `scratch_default/` (kept, `--keep-scratch`) | 18 GiB |
| `build_default/` | 206 MiB |
| **total `work/fullrun_20261017/`** | **69 GiB** |

### File count (`lfs quota -u berkom /storage`)

| when | files | Δ vs before |
|---|---:|---:|
| before submission (17 Oct) | 110,147 | — |
| after production + audit (18 Oct 15:13) | 116,798 | +6,651 (6,014 in work dir + 637 in the `post` checkout) |
| after build (18 Oct 17:30) | 118,374 | +8,227 |
| after sanity/plots (18 Oct 19:47) | 118,399 | **+8,252** |
| after the step-7 archives | see HANDOFF | |

- Limits: ≤ 9,000 new files (that is, ≤ 119,147) and ≤ 125,000 in total. Both were respected.
- Production created 6,014 files, against a projection of 5,990.
- The build's kept scratch accounts for 1,502 files: 496 shards × (db + `-shm` + `-wal`), plus directories.

## 3. Validation

### 3a. Production audit (`production_audit.json`)

- 497/497 jobs: `.err` says `Exit status: 0`, and `job_metadata.json` is present.
- **Σw self-check** (tolerance 1e-6): it fails for exactly one file, **75589 file 98**. There are no unexpected failures and the expected one is not missing.
- **Events:** 392,680,763 read and 128,724,189 stored.

### 3b. Reproducibility: 98 re-run pilot files vs the 10 Oct originals

`mc_compare.py runs --a work/cms_mc_v3_pilot_20261011/runs --b work/fullrun_20261017/runs` (job `5243009`):

| | |
|---|---|
| files compared | 98: 67801 (49), 35669 (41), 37728 (8) |
| input URLs identical | 98/98 |
| shards compared | 784 (8 per file) |
| shards identical (every signature, every array, every value, every metadata key) | **784/784** |
| physics-metadata differences | **0** |
| provenance differences | only `created_utc`, `elapsed_sec`, `git_commit` (cbfb837 → 294ee59) — all 98 files |

**Result: bit-identical.** The pilot's per-file outputs are fully reproduced by the pinned full-run code.

### 3c. Build report

- **13/13 records** are in the build.
- **Excluded files: exactly one, `[75589, 98]`**, by the D4 Σw check. ZZ is normalised with 98 of its 99 files.
- **The MC delivery note must state: "ZZ uses 98 of 99 files".**
- **Prune:** applied once over the 496 surviving shards. 93 final states were removed (min 100 raw events) and 0 orphan rows remained.
- The `audit_sigma_w_matches_build` check in the sanity report is True for all 13 records.

Per-record normalisation (`norm` = σ_eff·1000·L/Σw, L = 16.393 fb⁻¹):

| record | sample | σ_eff (pb) | files used | excluded | Σw | norm |
|---|---|---:|---:|---:|---:|---:|
| 35631 | DYJetsToLL_M-10to50 | 18610 | 25 | 0 | 1.664773e+12 | 1.832525e-04 |
| 35669 | DYJetsToLL_M-50 | 5765.4 | 41 | 0 | 1.220935e+12 | 7.740972e-05 |
| 37728 | GluGluHToZZTo4L | 0.013335 | 8 | 0 | 2.886964e+07 | 7.571990e-06 |
| 64839 | ST_tW_antitop | 19.56 | 10 | 0 | 1.187993e+08 | 2.699064e-03 |
| 64895 | ST_tW_top | 19.56 | 11 | 0 | 1.092902e+08 | 2.933905e-03 |
| 67801 | TTTo2L2Nu | 89.28 | 49 | 0 | 3.140127e+09 | 4.660853e-04 |
| 67993 | TTToSemiLeptonic | 367.86 | 138 | 0 | 4.354825e+10 | 1.384746e-04 |
| 68073 | TTWJetsToLNu | 0.2151 | 12 | 0 | 1.113150e+06 | 3.167707e-03 |
| 68187 | TTZToLLNuNu_M-10 | 0.2439 | 42 | 0 | 1.468242e+06 | 2.723156e-03 |
| 68847 | VBF_HToZZTo4L | 0.0010382 | 24 | 0 | 1.959725e+06 | 8.684488e-06 |
| 72676 | WWTo2L2Nu | 12.708 | 7 | 0 | 3.214708e+07 | 6.480285e-03 |
| 72752 | WZTo3LNu | 5.789 | 31 | 0 | 8.836850e+07 | 1.073902e-03 |
| 75589 | ZZTo4L | 1.544 | **98** | **1** | 6.787643e+07 | 3.728951e-04 |

**Known effect: peak ties (`XSEC_DECISIONS.md` "Known effects" 1).** This run had no rescaled build to compare against, so the effect cannot show up here and was not tested. It is still not seen: no comparison was in scope.

### 3d. Sanity: histograms

Every ROOT file was read back completely by job `5243647`. Every histogram is a TH1D, and the build's own read-back assertions passed for all 14 files.

| file | histograms | NaN/inf | negative variance | histograms with ≥1 negative bin | negative-weight fraction (stored) |
|---|---:|---:|---:|---:|---:|
| 35631 | 1,089 | 0 | 0 | 701 | 0.2016 |
| 35669 | 2,725 | 0 | 0 | 1,826 | 0.1660 |
| 37728 | 3,310 | 0 | 0 | 7 | 0.0030 |
| 64839 | 3,132 | 0 | 0 | 1 | 0.00002 |
| 64895 | 2,902 | 0 | 0 | 1 | 0.00002 |
| 67801 | 4,672 | 0 | 0 | 228 | 0.0038 |
| 67993 | 4,133 | 0 | 0 | 214 | 0.0038 |
| 68073 | 4,777 | 0 | 0 | 4,031 | 0.2255 |
| 68187 | 4,977 | 0 | 0 | 4,613 | 0.2531 |
| 68847 | 3,242 | 0 | 0 | 13 | 0.0006 |
| 72676 | 2,186 | 0 | 0 | 15 | 0.0017 |
| 72752 | 3,987 | 0 | 0 | 2,142 | 0.1928 |
| 75589 | 4,302 | 0 | 0 | 66 | 0.0032 |
| summedSM | 4,977 | 0 | 0 | 3,535 | — |

- **NaN/inf and negative variance:** none anywhere.
- **Negative bins:** these are the expected consequence of negative generator weights in sparsely populated bins. They are frequent exactly in the NLO samples with 17–25% negative weights: the two DY samples, WZ, ttW and ttZ. Per the plan, they are reported and not altered.

### 3e. Sanity: yields vs σ_eff × L

The table compares each record's total weighted stored events, σ·1000·L·(Σ genWeight of stored events)/Σw, with σ_eff × L for all generated events. The ratio is the weighted storage efficiency. It should match the raw fraction of events stored, up to the effect of negative weights.

| record | σ_eff × L (all generated) | weighted stored | weighted efficiency | raw stored fraction |
|---|---:|---:|---:|---:|
| 35631 | 305,073,730 | 2,130,438 | 0.0070 | 0.0088 |
| 35669 | 94,512,202 | 33,813,784 | 0.3578 | 0.3604 |
| 37728 | 218.6 | 114.8 | 0.5250 | 0.5227 |
| 64839 | 320,647 | 133,713 | 0.4170 | 0.4170 |
| 64895 | 320,647 | 133,711 | 0.4170 | 0.4170 |
| 67801 | 1,463,567 | 846,182 | 0.5782 | 0.5779 |
| 67993 | 6,030,329 | 2,067,814 | 0.3429 | 0.3428 |
| 68073 | 3,526 | 1,670 | 0.4735 | 0.4675 |
| 68187 | 3,998 | 1,512 | 0.3781 | 0.3770 |
| 68847 | 17.0 | 10.1 | 0.5947 | 0.5946 |
| 72676 | 208,322 | 102,442 | 0.4918 | 0.4916 |
| 72752 | 94,899 | 31,602 | 0.3330 | 0.3577 |
| 75589 | 25,311 | 7,267 | 0.2871 | 0.2861 |

- **Consistent for all 13 records.** The weighted and raw fractions agree to ≤ 0.3% for the samples with few negative weights.
- **Where they differ:** 35631, 72752 and 68073, by up to 7% relative. These are NLO samples with large negative-weight fractions, so a difference is expected there.
- **Plot closure:** in every stacked plot, the sum of the 8 process groups reproduces the summed-SM file to ≤ 2×10⁻¹⁶ relative.

## 4. Plots (committed)

Location: `studies/cms_mc_weights_v3/plots/fullrun/`, 19 PNGs.

**Stacked summed-SM plots.** Processes are grouped into 8 groups because the palette has 8 hues: tt̄, Drell-Yan, single top tW, WW, WZ, ZZ, tt̄W/tt̄Z and Higgs → ZZ → 4ℓ.

| PNG | category | histogram | total weighted |
|---|---|---|---:|
| `stack_1.png` | μμ, 0 jets | `ROI_mass_m0m1_cat_0ex_2mx_0jx_0bx_width_10.0` | 177,271 |
| `stack_2.png` | ee, 0 jets | `ROI_mass_e0e1_cat_2ex_0mx_0jx_0bx_width_10.0` | 116,342 |
| `stack_3.png` | eμ, 0 jets | `ROI_mass_e0m0_cat_1ex_1mx_0jx_0bx_width_10.0` | 24,856 |
| `stack_4.png` | μμ, ≥3 jets | `ROI_mass_m0m1j0_cat_0ex_2mx_3jx_0bx_width_10.0` | 44,129 |
| `stack_5.png` | 4 leptons (2e2μ) | `ROI_mass_e0e1m0m1_cat_2ex_2mx_0jx_0bx_width_10.0` | 54.0 (ZZ 53.7) |
| `stack_6.png` | μ + 2 jets + b | `ROI_mass_j0j1b0_cat_0ex_1mx_2jx_1bx_width_10.0` | 208,117 |

**One plot per record:** `record_<rid>.png` for each of the 13 records. Each shows the record's most-populated histogram, with weighted content and Sumw2 errors.

## 5. Output location (cluster; not copied anywhere else)

`/storage/agrp/berkom/atlas-utilization/work/fullrun_20261017/`:

- **`build_default/`** — the deliverable candidate:
  - `fullrun_record<rid>_mc.root` ×13
  - `fullrun_summedSM_mc.root`
  - `fullrun_build_report.json`
- **`runs/record<rid>/job_<i>/`** — per-file shards plus `job_metadata.json` (497).
- **`scratch_default/`** — the kept weighted scratch shards.
- **`evidence/`** — the audit, reproducibility and sanity JSONs, plus the plots.
- **`logs/`** — the PBS logs.

## 6. Decisions needed / notes for the technical lead

1. **The run is ready for verification.** Nothing was delivered or merged.
2. **The delivery note must say "ZZ uses 98 of 99 files"** (`XSEC_DECISIONS.md`, Data quality).
3. **The build ran from `dbd3107`, not from `294ee59`.** `dbd3107` only adds tools; the builder is byte-identical (§1). If the lead wants the build itself to run from a checkout at the exact pinned commit, it can be re-run as a PBS job (about 2¼ h).
4. **`scratch_default/` was kept, as the plan requires (`--keep-scratch`).** It holds 18 GiB and 1,502 files. Removing it is a cluster-data deletion and is out of scope here; that is the lead's call.

**Next step:** the technical lead verifies. After that come delivery to Maryna and merging MC into master.
