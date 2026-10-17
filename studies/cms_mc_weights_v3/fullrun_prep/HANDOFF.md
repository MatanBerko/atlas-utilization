# HANDOFF — CMS MC full-run preparation (17 Oct 2026)

**Status: COMPLETE. Nothing is running. The full run was NOT launched.**
Next: the technical lead verifies; then the full-run prompt executes
`../FULL_RUN_PLAN.md` §6. All numbers VERIFIED BY RUNNING unless marked
UNVERIFIED.

**Branch:** `feature/cms-mc-fullrun-prep-20261017` (origin only), from
`origin/feature/cms-mc-xsec-update-20261015` (`0fcab6d`). master (2460978)
and every other branch untouched; nothing sent to upstream; no Pull Request.

## Commits

| Commit | What |
|---|---|
| `0e9d4e5` | A1: merge of `origin/master` (2460978): only its two test files came in, no conflict |
| `d400538` | A2: WZ 72752 σ_eff 5.789 pb (exact k-factor 51.11/46.068), registry regenerated, `--check` passes |
| `29d09ee` | A3/A4: builder refuses `in_full_run = false` records (+4 test checks); XSEC_DECISIONS.md |
| `61c307c` | PBS runner + input sweep — **every cluster job and build ran from this commit** |
| `0603ae3` | HANDOFF before waiting |
| `ca3fb4c` | STOP in Part B: 4 sparse ggH histograms (peak ties), documented |
| `0dd38f7` | Matan's decisions applied; input-file check; projection; FULL_RUN_PLAN.md |
| `e186f38` | C1 smoke builds, plan final |
| *(this)* | final HANDOFF |

## Matan's decisions (17 Oct)

1. Peak-tie effect: **accepted and documented**, no code change
   (`FINDING_PEAK_TIES.md`, `../XSEC_DECISIONS.md` "Known effects").
2. Run-time sizing: realistic model (final states), literal rule shown for
   reference; walltime = max(2 × realistic, 2 × largest measured).

## Results

**A.** Merge clean; WZ 5.789 pb; safeguard tested (35671 refused with record
and reason, nothing written; 37728 accepted); tests: builder 24/24,
self-checks 46/46, drift 4/4, `tests/` 38 OK (5 network skips),
`studies/cms_datasets/tests` all pass; gate empty on every push.

**B.** Rebuild `5234302` (exit 0, 31 min): ttbar and DY bit-identical; ggH
2,455/2,459 histograms × 0.9916710047 to 3e-14; 4 sparse ggH histograms moved
(peak ties, accepted); summed SM differs only by the ggH change. PNGs
`../plots/fullrun_prep/B3_*.png`; `pilot_rebuild_comparison.json`.

**C1.** Production `5234303[1-10]` 10/10 exit 0. Builds: job `5234304`
stalled (see below) and was cancelled; the same 10 builds, same pinned
checkout and options, ran on the login node: **10/10 exit 0**.

| record | events read / stored | prod. wall | prod. peak | output (9 files) | final states | Σw check (rel. diff) | neg. weights (stored) | build: histograms, wall, peak | Σw verdict |
|---|---|---:|---:|---:|---:|---|---:|---|---|
| 67993 TTToSemiLeptonic | 1,233,000 / 422,195 | 824 s | 2.03 GB | 244 MB | 180 | pass (5.6e-9) | 0.37% | 474, 8 s, 385 MB | included |
| 64895 ST_tW_top | 651,757 / 272,318 | 1,403 s | 1.13 GB | 112 MB | 184 | pass (1.3e-9) | 0.001% | 701, 6 s, 186 MB | included |
| 64839 ST_tW_antitop | 45,342 / 18,879 | 843 s | 0.16 GB | 15 MB | 116 | pass (3.2e-8) | 0% | 156, 2 s, 81 MB | included |
| 72676 WWTo2L2Nu | 15,000 / 7,398 | 182 s | 0.11 GB | 3 MB | 53 | pass (1.3e-8) | 0.16% | 20, 2 s, 65 MB | included |
| 72752 WZTo3LNu | 457,263 / 163,294 | 560 s | 0.76 GB | 42 MB | 167 | pass (1.8e-8) | 19.3% | 430, 4 s, 106 MB | included |
| 75589 ZZTo4L | 168,000 / 47,946 | 636 s | 0.29 GB | 17 MB | 154 | pass (4.7e-9) | 0.37% | 223, 2 s, 86 MB | included |
| 68187 TTZToLLNuNu | 25,000 / 9,427 | 1,034 s | 0.15 GB | 32 MB | 289 | pass (1.6e-9) | 25.2% | 414, 4 s, 104 MB | included |
| 68073 TTWJetsToLNu | 9,451 / 4,437 | 860 s | 0.12 GB | 18 MB | 194 | pass (3.2e-8) | 21.5% | 139, 3 s, 80 MB | included |
| 35631 DYJetsToLL_M-10to50 | 2,444,741 / 21,433 | 123 s | 1.67 GB | 4.5 MB | 56 | pass (1.7e-8) | 20.1% | 32, 1 s, 70 MB | included |
| 68847 VBF_HToZZTo4L | 4,000 / 2,434 | 277 s | 0.10 GB | 6 MB | 95 | pass (1.4e-8) | 0.12% | 21, 1 s, 73 MB | included |

No warnings in any production or build log; every histogram passed the
TH1D/Sumw2 read-back. PNGs (most-populated weighted histogram, 1-file
normalisation, sanity only): `../plots/fullrun_prep/smoke/C_<record>.png`;
table `../evidence/smoke_test_report_20261017.json`.

**C2/C3.** All 497 files read (`check_input_files.py`,
`../evidence/input_file_check_20261017.json`). Only **75589 file 98** is
inconsistent: 871,000 events vs Runs genEventCount 904,000, Σ genWeight
−3.66% vs Runs genEventSumw; size and adler32 = portal ⇒ intact,
**mislabelled**, not truncated. The builder's Σw check would exclude it
automatically. Options in FULL_RUN_PLAN.md §7.

**D.** `../FULL_RUN_PLAN.md`: 497 files, 392,680,763 events; realistic 111.9
CPU h (literal 962.1); walltime 2 h (3 h for 68187, 68073); 6 GB; 67.8 GB;
+5,990 production files (+≈1,500 build) ⇒ ≈117,600 vs 150,000 soft quota;
recommendation: re-run the 98 pilot files.

## Two cluster lessons

* Queue N requires an `io` request on every job.
* The group `io` allowance (1,000) was full all morning. Job `5234304`
  waited ≈1.5 h; `qalter -l io=0.5` let it start, then it stalled 30 min
  with 14 s CPU reading back its first ROOT file and was cancelled
  (exit 271). Do not cut `io` below 25 for the full run.

## Cluster state

* Work dir (kept, 11 GB, 511 entries):
  `/storage/agrp/berkom/atlas-utilization/work/mcprep_20261017/`
  (`build_default/`, `scratch_default/`, `runs_smoke/`, `smoke_builds/`,
  `evidence/`, `logs/` incl. `smoke_builds_login/`, `mappings/`, `jobids.txt`).
* Checkout archived and verified (306 entries, extraction identical), folder
  removed: `checkouts/mcprep_20261017/repo_61c307c.tar.gz`.
* Read-only throughout: the 10 Oct pilot area and every other existing dir;
  `/storage/agrp/marybo/` never accessed; no ACL changes; nothing in `$HOME`.
* File count of `/storage/agrp/berkom` (`lfs quota`): **109,634 before,
  110,147 after (+513)**.
