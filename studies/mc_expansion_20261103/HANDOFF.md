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
  (`evidence/cms_tests_step2.txt`). Three of the old tests write by-product files into the tree; they were moved
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

## Step 4 — Ready to submit: PREPARED (P1 decided 3 Nov 18:49: **option B**, implemented in A2, see below)

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


## A2 (3 Nov 2026): P1 option B implemented, data coverage checked

Matan's decisions (3 Nov 18:49):
- P1 = option B;
- the files CERN does not publish (69717: 30 of 117; 72761: 6 of 9) stay missing and go in the README;
- delete the held jobs 5433388 / 5433389.

**Code (CMS files only; upstream files untouched, `services/consts.py` unchanged):**
- `studies/m0m1j0_cms/design_checks/common.py`: new `fetch_file_list_complete(record_id)`. It reads every index file
  listed in the record API's `_file_indices`, in that order, and fetches an index file directly if its entry lists
  fewer files than its `number_files`. `fetch_file_list` itself is unchanged.
- `studies/cms_datasets/cluster/run_dataset_on_file.py`:
  - `resolve_file_url(record_id, file_index, complete=False)`;
  - `main()` calls it with `complete=bool(args.is_mc)`;
  - so **MC uses the complete list and data keeps the page-1 list**. Data behaviour is unchanged.
- `studies/mc_expansion_20261103/make_mcexp_mappings.py` now writes the mappings from the complete list.

**Tests (VERIFIED BY RUNNING; `studies/cms_mc_weights_v3/tests/test_file_list_complete.py`, network):**
- **13 delivered MC records:** the complete list is identical (same files, same order) to the 25 Oct input lists.
  This is the 17 Oct sweep that the 25 Oct mappings were checked against.
- **54 new records:** page 1 is always a prefix of the complete list (only appends). **Total 1,206 files.** Per
  affected record (page 1 → complete):

  | record | sample | before | after |
  |---|---|---:|---:|
  | 64659 | t-channel antitop | 27 | 35 |
  | 37446 | ggF H → ττ | 35 | 40 |
  | 68591 | VBF H → ττ | 5 | 7 |
  | 68601 | VBF H → WW | 23 | 30 |
  | 71297 | W⁺H → ττ | 6 | 7 |
  | 74906 | Z → νν HT 800-1200 | 21 | 22 |
  | 69717 | W+jets 1J (unpublished files) | 30 | 30 |
  | 72761 | WZZ (unpublished files) | 6 | 6 |

- The data path still calls `resolve_file_url` without `complete` (asserted).
- **All 18 CMS test files pass** (`evidence/cms_tests_A2.txt`).
- **Reuse of the 13 delivered samples still holds:**
  - their complete file lists equal the 25 Oct lists, so every (record, file index) resolves to the same URL;
  - the only code change is in how the URL list is obtained;
  - selection, weights and outputs are untouched.

**Mappings and cost (option B; ESTIMATES as before, `evidence/full_production_plan.json`):**

| tier | samples | files | events | CPU h | cluster files added | cumulative (from 98,821, 3 Nov) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 7 | 476 | 497.3 M | 30 | 5,726 | 104,547 |
| 2 | 6 | 142 | 68.1 M | 9 | 1,716 | 106,263 |
| 3 | 4 | 57 | 17.5 M | 10 | 692 | 106,955 |
| 4 | 4 | 77 | 12.0 M | 116 | 932 | 107,887 |
| 5 | 26 | 347 | 41.6 M | 23 | 4,216 | 112,103 |
| 6 | 7 | 107 | 22.8 M | 0.5 | 1,298 | 113,401 |
| build + post | | | | | ~6,200 | **~119,600** (< 125,000) |

- Batch 1 (tiers 1-3) = 675 subjobs; batch 2 (tiers 4-6) = 531 subjobs.
- Walltimes are unchanged: 24 h 68045; 6 h 64635, 67645, 68083, 40062; 3 h 67691, 37446; 2 h the rest.

**Data coverage (`DATA_COVERAGE.md`): all 541 files of the 10 data records were used on 25 Oct; nothing missed.**

## A2 submitted (3 Nov 2026, 19:05 IST)

VERIFIED BY RUNNING (submission log `evidence/submit_A2_batch1.txt`).
- Pinned sha: **`6de9d3e605900a628bae372bdba4ea3308e9750f`**, checkout
  `/storage/agrp/berkom/atlas-utilization/checkouts/mcexp_20261103/repo_6de9d3e605900a628bae372bdba4ea3308e9750f`
  (HEAD asserted).
- Work dir: `W=/storage/agrp/berkom/atlas-utilization/work/mcexp_20261103/full`. It holds `mappings/` (54 files,
  1,206 lines), `runs/`, `logs/<record>/`, `jobids.txt`, `timing/`, `timing_jobid.txt`.
- Held jobs 5433388 and 5433389 deleted (`qdel`, Matan's approval). Both were still in state H with names
  mcexp_cmpb / mcexp_chk.
- **Four-top timing job: 5434328** (68045 file index 18 = mapping line 19, 2.53 GB, 24 h, io=25). Outputs go to
  `$W/timing/runs/record68045/job_18/`, log `$W/logs/t68045.{out,err}`. Its id is in `$W/timing_jobid.txt`. It is NOT
  in `jobids.txt` and NOT part of the audit.
- **Batch 1 = tiers 1-3: 17 arrays, 675 subjobs**, all written to `$W/jobids.txt` (format `<record> <job> <n> <walltime>`):

| record | job | files | walltime | | record | job | files | walltime |
|---|---|---:|---|---|---|---|---:|---|
| 64635 | 5434329[] | 19 | 06:00:00 | | 72738 | 5434337[] | 23 | 02:00:00 |
| 64659 | 5434330[] | 35 | 02:00:00 | | 72740 | 5434338[] | 21 | 02:00:00 |
| 64759 | 5434331[] | 86 | 02:00:00 | | 72742 | 5434339[] | 39 | 02:00:00 |
| 67841 | 5434332[] | 146 | 02:00:00 | | 75567 | 5434340[] | 15 | 02:00:00 |
| 69715 | 5434333[] | 97 | 02:00:00 | | 75573 | 5434341[] | 14 | 02:00:00 |
| 69717 | 5434334[] | 30 | 02:00:00 | | 72701 | 5434342[] | 24 | 02:00:00 |
| 69719 | 5434335[] | 63 | 02:00:00 | | 72711 | 5434343[] | 7 | 02:00:00 |
| 72658 | 5434336[] | 30 | 02:00:00 | | 72761 | 5434344[] | 6 | 02:00:00 |
| | | | | | 75600 | 5434345[] | 20 | 02:00:00 |

- Queued subjobs: 0 before, 649 right after submission.
- **File count (`lfs quota`): 98,821 before, 99,726 after** submission (the clone + the work layout). Projection after
  all six tiers + build ≈ 119,600 (ESTIMATE, table above).
- Not submitted (by design): batch 2 (tiers 4-6, 531 subjobs) and the post chain. Everything submitted runs on its
  own; nothing needs the laptop.

### What the follow-up prompt A2b must do

0. **Preflight.**
   - `git fetch`; the branch head is the commit that holds this section (it only adds documentation on top of
     `6de9d3e`).
   - **Use the same pin `6de9d3e…` and the same `R`, `W` as above.** Do NOT clone again, and do NOT change the code
     between the batches: the audit and build must see one code version.
   - Measure the quota.
1. **When to run it:** when fewer than **469** (= 1,000 − 531) of berkom's subjobs are queued, ideally < 450. Check:

       ssh wipp-home 'bash -l -c "/opt/pbs/bin/qstat -u berkom -t | awk \"\\\$10==\\\"Q\\\"\" | wc -l"'

   (on 3 Nov this printed 649 right after batch 1). If it is still too high, stop and try later.
2. **Four-top walltime.** Look at the timing job: `/opt/pbs/bin/qstat -x 5434328`.
   - If finished: read `Elapsed (wall clock)` in `$W/logs/t68045.err` (and `elapsed_sec` in
     `$W/timing/runs/record68045/job_18/job_metadata.json`). Set the 68045 walltime to the smallest of
     03/06/12/24/48 h that is ≥ 1.5 × that elapsed time; this file is the largest of the record.
   - If it failed on walltime: use 48 h (longE allows ≤ 72 h) and report.
   - If still running: keep 24 h.
3. **Batch 2.** In bash on wipp-home, define `B, C, CK, W, R, Q, PY, PLAN` and the `submit_tier` function exactly as in
   the script that submitted batch 1, `evidence/submit_A2_batch1.sh` (definitions and `submit_tier` only; not its clone, mkdir, cp or timing-job lines), then:
   - `submit_tier 4; submit_tier 5; submit_tier 6`, appending to `$W/jobids.txt`;
   - for 68045, replace the walltime from step 2 (e.g. submit 68045 by hand with that walltime and skip it in the loop);
   - check: 54 lines in `jobids.txt`, subjobs summing to 1,206.
4. **Post chain, immediately after batch 2, while its arrays are still queued or running.** Use the "Ready to
   submit" chain (audit → gate → build → checks; gate → rule_builds → rulecheck), with ONE change: build the
   dependency list only from jobs still in state Q, R or H:

       ARR=""; while read rid job n wt; do st=$(/opt/pbs/bin/qstat -x "$job" 2>/dev/null | tail -1 | awk '{print $5}'); \
         case "$st" in Q|R|H|B) ARR="$ARR:$job";; esac; done < $W/jobids.txt; echo "$ARR"

   Reason (seen 3 Nov): a single-job `afterok`/`afterany` on a job that has already finished, or is exiting, stays
   held forever. Six tier-5 samples are single files and are submitted as plain jobs, not arrays: 37432, 68571,
   70451, 71145, 71295, 74682. PBS dropped finished ARRAYS from dependencies on 25 Oct, but do not rely on it for
   single jobs. The audit itself still checks every line of every mapping, so nothing is skipped.
   - Audit: `pbs_fullrun.sh WHAT=audit` with `WORK_DIR=$W,EXPECTED_SW_FAILURES=` (no expected Σw failure).
   - Gate, checks, rule builds: `studies/mc_expansion_20261103/cluster/pbs_mcexp_post.sh`.
   - Build: `pbs_fullrun.sh WHAT=build` with
     `REGISTRY=studies/cms_mc_weights_v3/cms_mc_normalisation_v4.json` and
     `EXTRA_RUNS_DIR=/storage/agrp/berkom/atlas-utilization/work/fullrun_20261025/mc/runs` (read only), 64 GB, 8 h.
   - Record every id in `$W/post_jobids.txt` and in this file.
5. **If batch-1 jobs failed** (exit ≠ 0, e.g. walltime): do NOT resubmit in A2b without reporting. The audit will
   list them and the gate will stop the build, as designed. Report the failures (record, file index, reason) for a
   decision.
6. Commit the job ids to this file, gate, push, switch to master, finish without waiting.

## Status check (4 Nov 2026, 19:41; read-only)

VERIFIED BY RUNNING:
- Batch 1 (tiers 1-3) finished: **675 of 675 jobs exit 0**, 675 job directories with 8 shards each (5,400), no Σw
  self-check failure. The longest job took 1,070 s.
- Timing job 5434328: exit 0. 68045 file 18 (682,000 events) took **45 min wall** (2,719 s in the driver), 2.3 GB.
- 0 jobs queued; file count 107,898.

## A2b-1 submitted (4 Nov 2026, 19:47 IST): tiers 4 and 5

Matan's decision (4 Nov 19:44): submit tiers 4 and 5 now. **Tier 6 (Z → νν) and the post chain wait for Maryna's
answer on QCD multijet**, which may require dropping tier 6 for file space.

VERIFIED BY RUNNING (log `evidence/submit_A2b1_tiers45.txt`):
- Same pinned checkout `repo_6de9d3e605900a628bae372bdba4ea3308e9750f` (HEAD asserted, `git status` clean), same work
  dir `W=/storage/agrp/berkom/atlas-utilization/work/mcexp_20261103/full`. Before submitting, the script checked that
  no output directory or `jobids.txt` line existed for any of the 30 records.
- No code, registry, mapping or selection change.
- **Walltimes:** 68045 four-top **03:00:00** (timing job: 45 min for the largest file; × 1.5 rounds up to the tier-4
  standard 3 h). All others as in `full_production_plan.json`.
- **Tier 4: 4 arrays, 77 subjobs.** The 4 ON-HOLD samples (68325, 64873, 68206, 68185) are not submitted.
- **Tier 5: 26 samples, 347 subjobs** (20 arrays + 6 single-file plain jobs).
- **Total 424 subjobs**, appended to `$W/jobids.txt`, which now holds **47 lines, 1,099 subjobs** (tiers 1-5).

| record | job | files | walltime | | record | job | files | walltime |
|---|---|---:|---|---|---|---|---:|---|
| 67645 | 5439038[] | 26 | 06:00:00 | | 68571 | 5439052 (single) | 1 | 02:00:00 |
| 67691 | 5439039[] | 20 | 03:00:00 | | 68591 | 5439053[] | 7 | 02:00:00 |
| 68045 | 5439040[] | 23 | 03:00:00 | | 68601 | 5439054[] | 30 | 02:00:00 |
| 68083 | 5439041[] | 8 | 06:00:00 | | 68731 | 5439055[] | 4 | 02:00:00 |
| 37432 | 5439042 (single) | 1 | 02:00:00 | | 68741 | 5439056[] | 21 | 02:00:00 |
| 37446 | 5439043[] | 40 | 03:00:00 | | 70301 | 5439057[] | 9 | 02:00:00 |
| 37474 | 5439044[] | 10 | 02:00:00 | | 70383 | 5439058[] | 7 | 02:00:00 |
| 37604 | 5439045[] | 19 | 02:00:00 | | 70451 | 5439059 (single) | 1 | 02:00:00 |
| 37616 | 5439046[] | 2 | 02:00:00 | | 70453 | 5439060[] | 3 | 02:00:00 |
| 40062 | 5439047[] | 21 | 06:00:00 | | 71145 | 5439061 (single) | 1 | 02:00:00 |
| 40095 | 5439048[] | 5 | 02:00:00 | | 71227 | 5439062[] | 12 | 02:00:00 |
| 41873 | 5439049[] | 66 | 02:00:00 | | 71295 | 5439063 (single) | 1 | 02:00:00 |
| 41877 | 5439050[] | 58 | 02:00:00 | | 71297 | 5439064[] | 7 | 02:00:00 |
| 41914 | 5439051[] | 6 | 02:00:00 | | 74292 | 5439065[] | 8 | 02:00:00 |
| | | | | | 74682 | 5439066 (single) | 1 | 02:00:00 |
| | | | | | 74684 | 5439067[] | 6 | 02:00:00 |

- Queue right after submission: 397 queued, 27 running (berkom).
- **File count: 107,898 before, 107,928 right after submission.** Outputs appear as the jobs run.
- **Projection (ESTIMATE, 12 files per input file + 2 per record):**
  - tiers 4-5 add ~5,150 → ~113,050;
  - tier 6 would add ~1,300 → ~114,350;
  - the build + kept scratch (≈ 1,518 × 1,703 / 497 ≈ 5,200, scaled from the 25 Oct build) + checks (~200) bring the
    total to **~119,750 with tier 6, ~118,450 without**;
  - both under 125,000.

### What remains (the final prompt, after Maryna's QCD answer)

1. **Status check first.** Every line of `$W/jobids.txt` finished; count exit codes in `$W/logs/<record>/f_*.err`
   (tier 4/5 failures: report, do not resubmit without a decision).
2. **Tier 6: submit or drop (Matan / Maryna).**
   - If submitted: use the same definitions and `submit_tier` as in `evidence/submit_A2_batch1.sh` (pin 6de9d3e, same
     `R`, `W`), then `submit_tier 6` (7 arrays, 107 subjobs, 2 h).
   - If dropped: no new production. The post chain must not expect it: the audit reads only `jobids.txt`, so do not add
     tier 6 there. The v4 registry still lists the 7 records with `in_full_run: true`. That is harmless for the build,
     which only builds records it finds, but the delivery README must then say Z → νν is not included.
3. **Post chain**, submitted right after tier 6 (or right away if tier 6 is dropped).
   - Dependencies: `afterany` only on jobs still in state Q, R, H or B. If everything has finished, submit the audit
     with NO dependency, then use `afterok` on the audit job id, which will still be queued.
   - Commands, in bash on wipp-home, from the same pinned checkout:

```bash
B=/storage/agrp/berkom/atlas-utilization; C=6de9d3e605900a628bae372bdba4ea3308e9750f
R=$B/checkouts/mcexp_20261103/repo_$C; W=$B/work/mcexp_20261103/full; Q=/opt/pbs/bin/qsub
OLD=$B/work/fullrun_20261025/mc/runs
ARR=""; while read rid job n wt; do st=$(/opt/pbs/bin/qstat -x "$job" 2>/dev/null | tail -1 | awk '{print $5}'); \
  case "$st" in Q|R|H|B) ARR="$ARR:$job";; esac; done < $W/jobids.txt
DEP=(); [ -n "$ARR" ] && DEP=(-W depend=afterany$ARR)
F=$R/studies/cms_mc_weights_v3/fullrun/pbs_fullrun.sh; P=$R/studies/mc_expansion_20261103/cluster/pbs_mcexp_post.sh
MA=$($Q -N mcexp_audit -l select=1:ncpus=1:mem=4gb,walltime=01:00:00,io=25 -o $W/logs/post/audit.out -e $W/logs/post/audit.err \
     -v WORK_DIR=$W,REPO_DIR=$R,WHAT=audit,EXPECTED_SW_FAILURES= "${DEP[@]}" $F)
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

   - What the chain does:
     - audit: every mapping line of tiers 1-5 (+6), exit 0, Σw self-check, no expected failures;
     - gate: stops the chain unless the audit says OK;
     - build: v4 registry, the new runs + the 25 Oct runs read only, summed + per-process files, kept scratch;
     - checks: `post/checks_v4.py`, including D3 and the Z peaks, whose code has NOT yet been exercised (check its output
       first);
     - rule builds and checks R1-R7.
   - The build writes `$W/build_default`. `pbs_fullrun.sh` refuses to overwrite it.
4. Then the checks review and the delivery (separate prompts). The README items are listed under "README items" above.

## Status check (5 Nov 2026, 20:05; read-only)

VERIFIED BY RUNNING: of the 424 tier-4/5 subjobs (5439038-5439067), **331 exit 0** (8 shards + metadata each, no Σw
self-check failure) and **93 failed**, 0 queued/running. Longest OK jobs: tier 4 20 min (67691, 3 h limit), tier 5
25 min (40095, 2 h); 40062 11.5 min (6 h); no walltime/memory kill. File count 112,209.

## Retry of 93 portal-504 failures (5 Nov 2026, 20:12 IST)

Matan's decision (5 Nov): re-run exactly the 93 failed subjobs with the same pin, settings and walltimes; the 93
empty output folders may be MOVED (not deleted) out of `runs/`.

VERIFIED BY RUNNING (exact commands: `evidence/retry_20261105_submit.sh`):
- **Cause.** All 93 failed within ~1.5 min, before reading any data, with
  `requests.exceptions.HTTPError: 504 Server Error: Gateway Time-out for url: https://opendata.cern.ch/api/records/<recid>`
  → `RuntimeError: record <recid>: record API not reachable` (`fetch_file_list_complete`). The CERN portal was down
  4 Nov 20:03-20:33 IST; jobs starting before/after ran normally. Not a code or physics problem.
- **Preflight.** Branch head bc6b12d, upstream 29291ae; pinned checkout at 6de9d3e and clean; 0 jobs of mine; file
  count 112,209. Portal reachable on 5 Nov from wipp-an1: `fetch_file_list_complete` succeeded for all 12 affected
  records and each file count equals its mapping's line count.
- **The 93 pairs** (`evidence/retry_20261105_list.txt`: record, array index, file index, files in folder), from the logs
  (exit ≠ 0 AND the 504 message; no other failure type exists). Every folder existed and was empty (0 entries,
  recursively). Per record: 68045 23, 68083 7, 67691 15, 71295 1, 71297 7, 74292 8, 74682 1, 74684 6, 37446 17,
  71227 5, 40062 2, 41877 1 = 93, identical to the status check.
- **Moved, not deleted:** the 93 empty folders `runs/record<r>/job_<f>` → `$W/failed_20261104_portal504/<r>/job_<f>`
  (`evidence/retry_20261105_moved_folders.txt`; 93 folders, 0 files there).
- **Submitted 93 single jobs, 5449537-5449629** (contiguous), `pbs_mc_pilot.sh` with `PILOT_ARRAY_INDEX=<array index>`
  and the record's own mapping file, so each output lands at the original `runs/record<r>/job_<f>`. Walltimes from the
  A2b-1 lines of `jobids.txt`: 55 × 3 h (68045, 67691, 37446), 9 × 6 h (68083, 40062), 29 × 2 h; mem 6 gb, io=25.
  Logs: `$W/logs/<r>/f_<idx>_retry1.{out,err}`; the failed attempts' `f_<idx>.{out,err}` are untouched.
- **Job ids** in `$W/jobids_retry1.txt` and `evidence/retry_20261105_submitted.txt`, format
  `<record> <job> 1 <walltime> retry1 array_index=<i> file_index=<f>`. **Deliberately NOT appended to `jobids.txt`:**
  the pinned `audit_production.py` does `rid, jid, n, wt = line.split()` (a 5-field line crashes it) and keeps one
  entry per record (a 4-field retry line would replace the array's entry and its expected count).
- Right after submission: 76 queued, 17 running. **File count 112,209 before, 112,226 after.** Projection
  (ESTIMATE): +~1,050 for the 93 outputs/logs → ~113,300; + build/checks ~5,400 → ~118,700 without tier 6, ~120,000
  with it; under 125,000.

### Before the post chain (decision needed; not done)

The pinned audit reads `logs/<r>/f_<idx>.err` for every mapping line, so for the 93 it would still see the failed
attempt (exit 1) and the gate would stop the build. With no code change, one option is: after all 93 retries are
OK, MOVE the 93 failed `f_<idx>.{out,err}` into `$W/failed_20261104_portal504/logs/<r>/` and COPY each
`f_<idx>_retry1.{out,err}` to `f_<idx>.{out,err}` (needs Matan's approval: it moves logs). Also, the dependency loop in
"What remains" reads only `jobids.txt`; if the post chain is submitted while retries still run, add the Q/R/H
retry jobs from `jobids_retry1.txt` to `ARR`.

Idea only (not implemented, no code change now): a retry with back-off in `fetch_file_list_complete` for HTTP 5xx.

**Next status check must confirm 424/424 tier-4/5 outputs:** all 93 retry jobs exit 0 (`f_<idx>_retry1.err`), and
every `runs/record<r>/job_<f>` for the 30 records has 8 shards + `job_metadata.json` with a passing Σw self-check.

## Status check 7 Nov 2026 (read-only)

VERIFIED BY RUNNING (7 Nov 09:52 IST, wipp-home; per-record table `evidence/status_20261107_tiers45.txt`):
- Branch head 3d0800a, upstream 29291ae. 0 jobs of mine queued or running.
- **The 93 retries (5449537-5449629): 93/93 exit 0** (PBS history and `_retry1.err`), all `_retry1.out` end normally,
  each `runs/record<r>/job_<f>` has the standard 9 files (8 shards + `job_metadata.json`) and a passing Σw self-check.
- **Tiers 4-5: 424/424 OK** (331 original + 93 retry), 0 failed, 0 missing outputs, 0 Σw failures, against the
  mapping line counts (30 records).
- **Tiers 1-3 intact:** 675/675 folders with the standard 9 files. **So tiers 1-5 = 1,099/1,099 complete.**
- Longest job: four-top 68045 file 18 (retry), 2,434 s = 23 % of 3 h. Highest memory: 40095, 3.67 GB = 61 % of 6 GB.
  No job above 80 % of walltime or memory.
- `failed_20261104_portal504/`: 93 empty folders, untouched (same set as the moved list).
- File count 113,342 (112,226 on 5 Nov; estimate ~113,300).
- Still to do before the audit: the log swap from "Before the post chain" (needs Matan's OK); not done here.
