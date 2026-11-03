# HANDOFF — MC expansion, task A1 (3 Nov 2026)

Branch `feature/mc-expansion-20261103` (fork only), made from `origin/master` = `3054df3`. A1 builds and checks
the v4 registry, runs a small real-file check and prepares the full production. **It submits no full production,
builds no delivery and sends nothing.** The technical lead verifies A1 before the A2 prompt submits anything.

## Step 0 — preflight (VERIFIED BY RUNNING)

- `origin/master` = `3054df3`, `upstream/master` = `29291ae`, `origin/plan/mc-expansion-20261026` = `25d6423`
  (all as expected).
- `ssh wipp-campus`: "No route to host" (one try); `wipp-home` works.
- File count (`lfs quota -u berkom /storage`, column 6): **95,324**.
- `checkouts/mcexp_20261103` and `work/mcexp_20261103` did not exist.
- Between the 25 Oct production pin `75b399e` and `3054df3` only files under `studies/fullrun_20261025/` were
  added (`git diff --name-only`): the production code of master is the code of the 25-26 Oct full run.

## Step 1 — registry v4 (VERIFIED BY RUNNING)

- `studies/cms_mc_weights_v3/sources/v5_decisions_2026-11-03.json` (written by
  `studies/mc_expansion_20261103/make_v5_decisions.py`): Matan's final values for 58 records
  (54 in the full run, 4 ON HOLD). Each record has:
  - NanoAOD and MiniAOD IDs, the construction, every factor with its source (link + table/row) and verification
    status, the tier, `in_full_run`, and the `estimate` flag;
  - the excluded records (E2, D1, D4, D13);
  - 75567 moved out of v3's excluded list (D14).
- `studies/cms_mc_weights_v3/build_registry_v4.py` (ADDED; `build_registry.py` untouched) →
  `cms_mc_normalisation_v4.json`:
  - **73 records**: the 15 v3 records copied unchanged (13 in the full run + 35671 and 42407, not in it) + 58 new;
  - **67 in the full run**; 6 not; 24 deliberately excluded;
  - k_factor = gen_filt_eff = 1.0 everywhere; `--check` reproduces it byte for byte.
- Provenance: the saved portal records (59 NanoAOD + 59 MiniAOD, incl. 35671/35670) and the generator cards of the
  58 samples are **copied** byte for byte from the plan branch commit `25d6423` into
  `studies/cms_mc_weights_v3/sources/mcexp_20261103/{records,cards}/` (3.5 MB).
- v3: `build_registry.py --check` still OK; `cms_mc_normalisation_v3.json` and `v4_decisions_2026-10-15.json` unchanged.

## Step 2 — automatic checks (VERIFIED BY RUNNING)

Tests: `studies/cms_mc_weights_v3/tests/test_registry_v4.py` (6/6 pass). Report: `REGISTRY_CHECKS.md`
(+ `evidence/registry_v4_checks.json`), from `registry_v4_report.py`.

- (a) every σ_eff equals Matan's list exactly, and equals the product of its factors to ≤ 4.2e-5 (limit 1e-4).
- (b) 25 portal values (generator factors, the three W values, the LO DY 5396 of MiniAOD 35670): **saved copy equal
  25/25, live API equal 25/25** (read 3 Nov). Matan's own live check of the three W values is still recorded as pending.
- (c) τ check: 12 samples × card evidence × factor, **12/12 OK, no mismatch**. Also 67841 TTToHadronic:
  `topdecaymode 00022` ↔ BR(W → had)².
- (d) no record twice; full run = 13 delivered + 54 new. Overlap checks:
  - W+jets pieces only;
  - tt̄ split sums to 1.0026;
  - tribosons ext1 only;
  - qq → ZH uses 0.7612 and gg → ZH 0.1227;
  - dropped and deferred records are excluded.
- (e) all 17 CMS test files (`tests/`, `studies/cms_datasets/tests/`, `studies/cms_mc_weights_v3/tests/`) exit 0
  (`evidence/cms_tests_step2.log`). Three of the old tests write by-product files into the tree; they were moved
  out, not committed.

## Code changes (CMS files only; v3 stays the default)

- `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py`:
  - optional `--registry PATH` (default: the v3 registry, unchanged);
  - optional `--extra-runs-dir DIR` (repeatable, read only; a record found in two directories is a hard error);
    this lets one build read the 25 Oct production next to the new one;
  - `assert_in_full_run` also reads the reason from `decision_2026_11_03`;
  - the report records `registry` and `extra_runs_dirs`.

  Lines: 201-203, 642-651, 660-661, 1081-1092 (see `git diff 3054df3 -- …`).
- `studies/cms_mc_weights_v3/fullrun/pbs_fullrun.sh`: optional env `REGISTRY`, `EXTRA_RUNS_DIR` passed to the build
  stage only when set (lines 23-25, 57-58). Unset = exactly the 25 Oct command.

## Step 3 — small real-file check: DONE (details `PRECHECK.md`)

- File 0 of the 54 new samples (5433276[]) and of the 13 delivered (5433277[]): 67/67 exit 0. No sample has
  zero selected events; Z → νν stores 1-235 events per file 0, as expected.
- The 13 re-runs are identical to the 25 Oct outputs (all 8 shards, metadata).
- Smoke builds: v3 vs v4 for the 13 delivered are identical, histogram by histogram.
- Plots: `precheck_plots/`.

Findings for the technical lead:
- W+jets roughly doubles the eμ 0-jet MC.
- Adding samples moves the builder's combined peak/split cuts, so the 13 delivered histograms change shape in the new
  build. Example: eμ 0j lower edge 60 → 80 GeV.

## Step 4 — Ready to submit: PREPARED, **BLOCKED on one decision (P1)**

### P1 — the portal file page reaches only part of 8 new records (NOT decided here; options for Matan)

The production driver gets its file list from `fetch_file_list` (`studies/cms_datasets/cluster/run_dataset_on_file.py:550`
→ `studies/m0m1j0_cms/design_checks/common.py:75`). That function reads only page 1 of the portal file page
(`https://opendata.cern.ch/record/<id>/filepage/1?group=1`; upstream `services/consts.py:1` uses the same URL). Page 1
shows at most 5 index files. Measured on 3 Nov (VERIFIED BY RUNNING, `evidence/file_index_coverage.json`):

| record | sample | tier | files reachable (page 1) | files in the record's full index | portal `number_files` | bytes reachable |
|---|---|---:|---:|---:|---:|---:|
| 64659 | t-channel antitop 4f | 1 | 27 | 35 | 35 | 77.8 % |
| 69717 | W+jets 1J | 1 | 30 | **30** | **117** | 27.2 % |
| 72761 | WZZ ext1 | 3 | 6 | **6** | **9** | 92.0 % |
| 37446 | ggF H → ττ | 5 | 35 | 40 | 40 | 98.2 % |
| 68591 | VBF H → ττ | 5 | 5 | 7 | 7 | 48.0 % |
| 68601 | VBF H → WW | 5 | 23 | 30 | 30 | 88.9 % |
| 71297 | W⁺H → ττ | 5 | 6 | 7 | 7 | 89.9 % |
| 74906 | Z → νν HT 800-1200 | 6 | 21 | 22 | 22 | 95.4 % |

None of the 13 delivered samples is affected: their page-1 lists equal their full index, as in the 17 Oct sweep. In
every case the page-1 list is an exact prefix of the full index, so a fix would only APPEND file indices.

- **Normalisation is correct either way.** Σw is measured over the files actually processed (DESIGN D4); fewer files
  only means fewer MC events.
- **69717 and 72761:** the portal's own index lists fewer files than `number_files`. Those 87 + 3 files are not
  published, so no code change reaches them. Consequence (D3), ESTIMATE: W+jets 1J MC luminosity falls from 4.72 to
  ≈ 1.3 fb⁻¹ (≈ 0.08 × data). The other two pieces are unaffected.
- Options for the 6 page-limited records (24 files):
  - **A.** Run with the unchanged code: 1,182 files. Loss: 64659 −22 % of bytes, 68591 −52 %, 68601 −11 %,
    71297 −10 %, 37446 −2 %, 74906 −5 %.
  - **B.** Change the CMS helper `fetch_file_list` (or add a CMS-only variant used by the MC driver) to read the record
    API's `_file_indices`: 1,206 files.
    - This is a production-code change (the code pin differs from 25 Oct).
    - The 13 delivered samples' file lists are unchanged (all fully on page 1), so their reuse is not affected.
    - It needs a test that the lists are identical for the 13 and a prefix-extension for the 8.
  - In both options: report the missing 69717/72761 files to CERN Open Data (Matan's call).

The mappings in `mappings/` implement **option A** (what the unchanged code can run). With option B,
`make_mcexp_mappings.py` would be re-run after the helper change.

### Can the 13 delivered samples be reused? **Yes (evidence).**

1. Production code: `75b399e` (25 Oct pin) → `3054df3` → this branch changes no production file. The registry is read
   only by the builder.
2. **File 0 of all 13, re-run on 3 Nov with this branch, is identical to the 25 Oct output**: every table of all 8
   shards, and the job metadata apart from time and commit (`evidence/precheck/compare_reruns.json`).
3. The smoke build with registry v4 equals the one with v3 for the 13 (A vs B, every histogram).
4. A build can read the 25 Oct runs read only (`--extra-runs-dir`): build D did. The 25 Oct `job_0` files were
   unchanged before and after (`old_job0_listing_*`). **C vs D (from the re-runs vs from the 25 Oct files) are
   IDENTICAL**: all 68 ROOT files, every histogram, the same σ_eff, Σw and normalisation (job 5433883,
   `evidence/precheck/compare_builds.json`).
5. The builder excludes 75589 file 98 by its Σw check, exactly as on 25 Oct.

Re-running the 13 instead would cost 497 files, ~66 CPU h and ~6,000 cluster files (25 Oct audit). Not needed.

### Mappings and cost (option A; ESTIMATES from the file-0 timings, `plan_full_production.py` → `evidence/full_production_plan.json`)

CPU per event comes from file 0. Where file 0 has fewer than 100k events, 150 s of start-up is subtracted (calibrated
on the 13 delivered: 60-170 s). Walltime is the smallest of 2/3/6/12/24 h above 1.5 × the largest estimated file; at
least 3 h for tier 4. Cluster files are 12 per input file (measured: 9 outputs + directory + 2 logs) + 2 per record.

| tier | samples | files | events | CPU h | cluster files added | cumulative (from 98,809 measured 3 Nov after A1) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 7 | 468 | 490.5 M | 30 | 5,630 | 104,439 |
| 2 | 6 | 142 | 68.1 M | 9 | 1,716 | 106,155 |
| 3 | 4 | 57 | 17.5 M | 10 | 692 | 106,847 |
| 4 | 4 | 77 | 12.0 M | 116 | 932 | 107,779 |
| 5 | 26 | 332 | 40.1 M | 22 | 4,036 | 111,815 |
| 6 | 7 | 106 | 22.7 M | 0.5 | 1,286 | 113,101 |
| build + post | | | | | ~6,130 (build + kept scratch ≈ 1,518 × 1,679 / 497 = 5,128; pinned clone ~800; checks ~200) | **~119,200** |

- **Under 125,000, with ~5,800 left.** Matan's planning figure was ~117,200; the difference is today's A1 work
  (+3,485, of which the three pinned clones are ~2,380 and could be archived, Matan's call). Option B adds ~290.
- **Walltimes:**
  - 24 h for 68045 tt̄tt̄ (file 0: 740 s for 9,000 events, about 10 × slower per event than tt̄Z; estimated
    max ~12 h per file; ESTIMATE, uncertain);
  - 6 h for 64635, 67645, 68083, 40062;
  - 3 h for 67691, 37446;
  - 2 h for all others.
  - Queue N routes ≤ 2 h → shortE, ≤ 12 h → normE, ≤ 72 h → longE.
  - **Recommended:** one timing job on the largest 68045 file before tier 4 (as the 25 Oct Part 1b).
- **MC build:** ~1.9 × the stored events of 25 Oct (ESTIMATE) → ~32 GB. Request 64 GB, 8 h as on 25 Oct (that build:
  17 GB, 37 min).

### Submission plan (A2; nothing submitted in A1)

Queue limit: 1,000 queued subjobs per user. Batch 1 = tiers 1-3 (667 subjobs). Batch 2 = tiers 4-6 (515) once fewer
than 485 subjobs of batch 1 are still queued. The post chain is submitted after batch 2; PBS drops already-finished
arrays from a dependency, as recorded on 25 Oct. Dependency pattern (tested 24 Oct, `studies/fullrun_20261025/HANDOFF.md`):
`afterany` on the arrays → audit → a gate job that exits non-zero unless the audit says OK → `afterok` on the gate
(single jobs). Seen 3 Nov: a single-job `afterok` on jobs that had already finished (5433388) or were exiting at
that moment (5433389: its dependency's log ends 16:01:51 while qstat still showed it running) stayed held for good.
So the post chain must be submitted while the arrays are still queued or running.

```bash
# Run from wipp-home in bash, after the technical lead's check, Matan's P1 decision and go.
B=/storage/agrp/berkom/atlas-utilization
C=<the A2 pin: full sha of this branch's final commit (or of the P1 option B commit)>
CK=$B/checkouts/mcexp_20261103; W=$B/work/mcexp_20261103/full; R=$CK/repo_$C; Q=/opt/pbs/bin/qsub
OLD=$B/work/fullrun_20261025/mc/runs
test ! -e $R && test ! -e $W
git clone -q --no-checkout https://github.com/MatanBerko/atlas-utilization.git $R
git -C $R checkout -q $C && test "$(git -C $R rev-parse HEAD)" = $C
mkdir -p $W/mappings $W/runs $W/evidence $W/logs/post
cp $R/studies/mc_expansion_20261103/mappings/mapping_*.txt $W/mappings/
PLAN=$R/studies/mc_expansion_20261103/evidence/full_production_plan.json
submit_tier() {   # submit_tier <tier>: one array per sample, walltime from the plan
  for rid in $($PY -c "import json,sys;d=json.load(open('$PLAN'))['samples'];print(' '.join(r for r,s in sorted(d.items()) if s['tier']==$1))"); do
    n=$(wc -l < $W/mappings/mapping_$rid.txt)
    wt=$($PY -c "import json;print(json.load(open('$PLAN'))['samples']['$rid']['walltime'])")
    mkdir -p $W/logs/$rid
    if [ "$n" -gt 1 ]; then J=$($Q -J 1-$n -N mcexp_$rid -l mem=6gb,walltime=$wt,io=25 \
        -o "$W/logs/$rid/f_^array_index^.out" -e "$W/logs/$rid/f_^array_index^.err" \
        -v WORK_DIR=$W,REPO_DIR=$R,OUTPUT_BASE=$W/runs,MAPPING_FILE=$W/mappings/mapping_$rid.txt \
        $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh)
    else J=$($Q -N mcexp_$rid -l mem=6gb,walltime=$wt,io=25 -o "$W/logs/$rid/f_1.out" -e "$W/logs/$rid/f_1.err" \
        -v WORK_DIR=$W,REPO_DIR=$R,OUTPUT_BASE=$W/runs,MAPPING_FILE=$W/mappings/mapping_$rid.txt,PILOT_ARRAY_INDEX=1 \
        $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh); fi   # OpenPBS refuses -J 1-1
    echo "$rid $J $n $wt" | tee -a $W/jobids.txt      # the format audit_production.py reads
  done; }
PY=$B/envs/atlas-pipeline/bin/python
# recommended first: timing job on the largest 68045 file (file index 18, 2.53 GB = mapping line 19), 24 h
#   $Q -N mcexp_t68045 -l mem=6gb,walltime=24:00:00,io=25 -o $W/logs/t68045.out -e $W/logs/t68045.err \
#      -v WORK_DIR=$W/timing,REPO_DIR=$R,OUTPUT_BASE=$W/timing/runs,MAPPING_FILE=$W/mappings/mapping_68045.txt,PILOT_ARRAY_INDEX=19 \
#      $R/studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh
submit_tier 1; submit_tier 2; submit_tier 3            # batch 1: 667 subjobs
# ... when fewer than 485 of them are still queued (qstat -u berkom -t | grep -c " Q "):
submit_tier 4; submit_tier 5; submit_tier 6            # batch 2: 515 subjobs
# post chain (submit while the arrays are not all finished)
ARR=$(awk '{printf ":%s", $2}' $W/jobids.txt)
F=$R/studies/cms_mc_weights_v3/fullrun/pbs_fullrun.sh; P=$R/studies/mc_expansion_20261103/cluster/pbs_mcexp_post.sh
MA=$($Q -N mcexp_audit -l select=1:ncpus=1:mem=4gb,walltime=01:00:00,io=25 -o $W/logs/post/audit.out -e $W/logs/post/audit.err \
     -v WORK_DIR=$W,REPO_DIR=$R,WHAT=audit,EXPECTED_SW_FAILURES= -W depend=afterany$ARR $F)
MG=$($Q -N mcexp_gate -l select=1:ncpus=1:mem=1gb,walltime=00:10:00,io=1 -o $W/logs/post/gate.out -e $W/logs/post/gate.err \
     -v WORK_DIR=$W,REPO_DIR=$R,WHAT=gate -W depend=afterok:$MA $P)
MB=$($Q -N mcexp_build -l select=1:ncpus=1:mem=64gb,walltime=08:00:00,io=25 -o $W/logs/post/build.out -e $W/logs/post/build.err \
     -v WORK_DIR=$W,REPO_DIR=$R,WHAT=build,REGISTRY=studies/cms_mc_weights_v3/cms_mc_normalisation_v4.json,EXTRA_RUNS_DIR=$OLD \
     -W depend=afterok:$MG $F)
MC=$($Q -N mcexp_checks -l select=1:ncpus=1:mem=32gb,walltime=04:00:00,io=25 -o $W/logs/post/checks.out -e $W/logs/post/checks.err \
     -v WORK_DIR=$W,REPO_DIR=$R,WHAT=checks -W depend=afterok:$MB $P)
MR=$($Q -N mcexp_rulebld -l select=1:ncpus=1:mem=32gb,walltime=06:00:00,io=25 -o $W/logs/post/rule_builds.out -e $W/logs/post/rule_builds.err \
     -v WORK_DIR=$W,REPO_DIR=$R,WHAT=rule_builds -W depend=afterok:$MG $P)
MK=$($Q -N mcexp_rulechk -l select=1:ncpus=1:mem=16gb,walltime=02:00:00,io=25 -o $W/logs/post/rulecheck.out -e $W/logs/post/rulecheck.err \
     -v WORK_DIR=$W,REPO_DIR=$R,WHAT=rulecheck -W depend=afterok:$MR $P)
printf "%s\n" "audit $MA" "gate $MG" "build $MB" "checks $MC" "rule_builds $MR" "rulecheck $MK" | tee $W/post_jobids.txt
```

The build is `pbs_fullrun.sh WHAT=build`: `build_mc_delivery.py --runs-dir $W/runs --extra-runs-dir <25 Oct runs>
--registry …v4.json --out-dir $W/build_default --out-prefix fullrun --scratch-dir $W/scratch_default --keep-scratch`
(all physics options default). It writes the summed-SM file `fullrun_summedSM_mc.root` and one file per process
(`fullrun_record<id>_mc.root`).

### Checks the B step must run (scripts ready; `cluster/pbs_mcexp_post.sh`)

1. **Audit + gate.** All 54 arrays complete, exit 0, metadata present, Σw self-check (no expected failures for the new
   samples; any failure stops the build for a human decision).
2. **Rule checks R1-R7** (`rule_check.py --kind mc`) on per-sample default vs exact builds of 67801 (reference),
   69715, 67841, 64759 (`RULE_RECORDS`).
3. **`post/checks_v4.py` on the v4 build:**
   - no NaN/inf/negative variances (exit 1 otherwise);
   - data/MC names;
   - Z peaks before peak removal, data/MC in 76-106 and 60-120 GeV, ee/μμ 0j, from the kept scratch with the 25 Oct
     analysis function (NOT yet exercised; check its output);
   - stacks with data;
   - **D3:** histograms where one W+jets event can be > 50 % of a bin's MC (upper bound), the worst 20 and 5 plots.
4. **Also compare MC vs data histogram ranges per name.** The combined peak/split cuts move when samples are added
   (PRECHECK.md); not in a script yet.
5. The build report: 67 samples, 75589 file 98 excluded, Σw per sample, the 40062 estimate flag in the registry.

### README items the delivery must carry

- **E1:** the diboson normalisation differs from ATLAS (CMS NNLO × k incl. gg → VV vs ATLAS Sherpa, kFactor 1);
  CMS ÷ ATLAS 0.92-1.24 by process.
- **E2:** EW V + 2 jets not included (double counting with the tier-2 dibosons).
- **D3:** W+jets MC luminosity 0.13-0.29 × data.
  - With option A / the unpublished 69717 files, the 1J piece is ≈ 0.08 × data.
  - Single W+jets events can dominate bins (the D3 count).
- **40062** σ_eff = 6.22e-5 pb is an ESTIMATE (filter efficiency not published).
- **Secondary sources:** RazorAnalyzer `xSections.dat` for DY (1921.8 × 3) and W+jets (61,526.7), and the Z → νν
  k-factor (5765.4 / 5396).
- **Missing processes:** QCD multijet, photon samples, the on-hold rare top (tZq, tWℓℓ, tt̄Z → qq, tt̄ + ℓℓ 1-10 GeV),
  the deferred Higgs extras.
- **W+jets portal values:** saved copies checked by the technical lead and equal to the live API on 3 Nov; Matan's own
  live check is pending.
- **Files not processed** (P1) per record, if option A.

### Code changes made in A1 (CMS files only; v3 remains the default)

- `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py`:
  - `--registry`, `--extra-runs-dir` (lines 201-203, 642-651, 660-661, 1081-1092);
  - why: build with v4 and read the 25 Oct outputs without copying or re-running them.
- `studies/cms_mc_weights_v3/fullrun/pbs_fullrun.sh`: `REGISTRY`, `EXTRA_RUNS_DIR`, `EXPECTED_SW_FAILURES` passed
  only when set.
- `studies/cms_mc_weights_v3/fullrun/audit_production.py`:
  - `--expected-sw-failures` (default `75589:98`, unchanged);
  - why: the new production has no expected failure.
- Added (no existing file changed):
  - `build_registry_v4.py`, `cms_mc_normalisation_v4.json`, `sources/v5_decisions_2026-11-03.json`,
    `sources/mcexp_20261103/`, `tests/test_registry_v4.py`;
  - `studies/mc_expansion_20261103/` (scripts, mappings, evidence, plots).
- All 17 CMS test files pass after the changes.

### Cluster state left by A1 (nothing deleted)

- `checkouts/mcexp_20261103/repo_{e04121d…,29fcf43…,0a335f3…}`.
- `work/mcexp_20261103/precheck/` (runs, builds A-D, logs, evidence).
- Two held jobs 5433388 / 5433389 (dependency never released). They hold no resources; deleting them needs Matan's OK.
- File count **98,821** at the end of A1 (95,324 before A1; `lfs quota`, 3 Nov 18:42).
