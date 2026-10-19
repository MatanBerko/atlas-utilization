# HANDOFF — CMS MC PEAK FIX (18–19 Oct 2026)

**Current step: COMPLETE (19 Oct 2026, 11:05 IDT). Report: `peakfix/REPORT.md`. Next: technical lead verifies; then delivery.**
Not delivered; not merged into master. Option B not implemented (question for Maryna).

**Branch:** `feature/cms-mc-peakfix-20261018` (origin only), from
`feature/cms-mc-fullrun-20261017` @ `289c4f2`.
**Pinned commit (rebuild and steps 4–6): `88d30aca0fccb0875fa3346afb4d3ee38b09a52c`.**

**Cluster freeze:** admins replace $HOME on Wed 21 Oct 17:30. No job may be
submitted whose walltime could end after Wed 21 Oct 15:00; by then
`qstat -u berkom` must be empty and nobody connects.

## Done

- **19 Oct, resume (VERIFIED BY RUNNING):** both jobs exit 0. Build output `work/peakfix_20261018/build_combined/` (13 per-sample + summed SM + report), scratch removed. Z-peak in `work/peakfix_20261018/evidence/zpeak/`.
- **19 Oct:** `compare_old_new.py` gained exclusion / final-state / NaN-inf checks (the PBS compare stage now also stages both build reports). This is analysis-only; the builder is unchanged from `88d30ac`. Steps 4–6 run from the new pin (see below); the build itself stays pinned at `88d30ac`. Tests 12 + 24 + 46 + drift pass.

- **Step 0, finding confirmed (VERIFIED BY RUNNING).** In the code, `histograms_for_shards` runs `postprocess_in_lockstep` per sample, and `sum_histograms` adds the already-cut histograms.
  - Job `5244611` (checkout `step0` @ `1611209`): in 4,976 of 4,977 summed names the kept samples have different peak masses.
  - 2e2μ 0j: ggH and VBF start at 120 GeV, ZZ at 190, ttZ at 290; the summed SM starts at 120.
  - Evidence: `peakfix/evidence/step0_verify_finding.json`.
- **Step 1.** `--peak-scope {combined,per-sample}` added, default combined. `tests/test_peak_scope.py` has 12/12 passing. The existing tests (24 + 46 + drift) still pass.
- **Step 2, $HOME backup:** `/storage/agrp/berkom/atlas-utilization/home_backup_20261018/`, permissions preserved, every file `cmp`-identical to its original.
  - Files copied: `.ssh/authorized_keys` (600), `.ssh/known_hosts` (600), `.ssh/known_hosts.old`, `.zshrc`, `.bashrc`, `.bash_profile`, `.bash_logout`, `.emacs`, `.conda/environments.txt`, `untracked_backup/_check_branch_units.py`.
  - Not present in $HOME: `~/.ssh/config`, `.zprofile`, `.profile`, `.gitconfig`, `.condarc`. There is no private key in `~/.ssh`.
  - Other contents of $HOME, not copied:
    - `~/atlas-utilization`: a clone, clean, HEAD `78ec465`, which is on origin.
    - `~/.conda`: 1.2 GB, mostly `pkgs/` cache, plus `aau_token*`.
    - `~/.cache`: 184 MB.
  - The pipeline env lives on /storage (`envs/atlas-pipeline`), on another filesystem, so it does not depend on $HOME.

## Cluster

Reached over `wipp-home`; `wipp-campus` timed out.

- Checkouts: `checkouts/peakfix_20261018/step0` @ `1611209` (step 0 only), `checkouts/peakfix_20261018/repo` @ `88d30ac` for the build; moved to `4a72294` on 19 Oct for steps 4–6 (analysis scripts only; builder unchanged)
- Work: `work/peakfix_20261018/` — `logs/`, `evidence/`, `build_combined/` (step 3)
- Read-only inputs:
  - `work/fullrun_20261017/runs` (build input)
  - `work/fullrun_20261017/build_default` (old build)
  - `work/fullrun_20261017/scratch_default` (Z-peak MC weights)
  - `output/cms_datasets/deliver/four_dataset_vB_upstreamnames_w10p0_dr012_20261007/` (data delivery)
  - `output/cms_datasets/runs_matched4_full_20261007` (data shards for the Z peak; read via private copies)
- File count (`lfs quota -u berkom /storage`): **118,401 at start**; 119,101 after the checkouts and backup; 119,180 on 19 Oct after the build + Z-peak. Budget ≤ 121,901 (+3,500) and ≤ 125,000 in total.

## Jobs

| step | PBS job | resources | state |
|---|---|---|---|
| 0 verify | `5244611` | 16gb, 2h | done |
| 3 build | `5244700` | 64gb, 8h | done, exit 0, 2h07m wall, peak RSS 18.9 GB (PBS mem 28.5 GB) of 64 GB; 1 excluded file (75589); 4,977 summed names |
| 4 compare | `5248340` | 32gb, 4h | done, exit 0, 3 min |
| 5–6 datamc | `5248341` | 32gb, 4h | done, exit 0, 1 min |
| 6 zpeak | `5244701` | 32gb, 8h | done, exit 0, 13 min; 0-jet 76–106: μμ 1.0340, ee 0.9534 (pilot 1.035 / 0.954) |

## How to resume

`qstat -u berkom` / `qstat -x <id>`. Never resubmit a job that is queued, running or finished. Submit from `repo`:

```
qsub -N mcpeak_<what> -l mem=..,walltime=..,io=25 -o $W/logs/<what>.out -e $W/logs/<what>.err \
     -v WORK_DIR=$W,REPO_DIR=$C/repo,WHAT=<build|compare|datamc|zpeak> $C/repo/studies/cms_mc_weights_v3/peakfix/pbs_peakfix.sh
```

Then: copy the evidence JSONs and PNGs into `peakfix/evidence/` and `plots/peakfix/`, write `peakfix/REPORT.md`, archive `repo` (tar.gz + verify), measure the file count, push the final HANDOFF, and switch the local repo to master.

## Final state (19 Oct 2026, 11:05 IDT)

- Report: `peakfix/REPORT.md`. PNGs: `plots/peakfix/` (21). Evidence: `peakfix/evidence/` (`compare_old_new_summary.json`, `data_vs_mc.json`, `z_peak_ratio.json`, step 0, tests).
- Cluster output: `work/peakfix_20261018/build_combined/` (13 per-sample + summed SM + report); evidence in `work/peakfix_20261018/evidence/`.
- Checkouts archived, listings verified (archive entries == files on disk); directories left in place:
  - `checkouts/peakfix_20261018/checkout_step0_1611209.tar.gz` (264 files, 65 MB)
  - `checkouts/peakfix_20261018/checkout_repo_4a72294.tar.gz` (328 files, 65 MB)
- File count: **119,243** (+842 vs 118,401; limits 121,901 / 125,000 respected).
- `qstat -u berkom` empty at 11:01. No more cluster connections needed before the freeze.
- **Push gate resolved (19 Oct, Matan approved):** fork master merged upstream/master `b9f6ea3` (#38, only `services/parsing/event_selection.py`) as merge `45a7e06` (0 behind upstream, gate empty), pushed; master then merged into this branch (`1a1767b`, no file under `studies/` changed), pushed. CMS entry modules (dataset runner, m0m1j0 selection, MC builder) do not import `services.parsing.event_selection` (sys.modules check), and all test suites pass identically before/after on master and on this branch, so #38 cannot affect any CMS output.
- Local repo switched back to `master`. No other branch touched; nothing upstream; no PR.
