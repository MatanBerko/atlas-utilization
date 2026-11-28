# HANDOFF — Nominal-6 additions, preparation (27 Nov 2026)

Branch `prep/nominal6-additions-20261127` (fork only), made from `origin/analysis/nominal6-correspondence-20261124`
(14cd426). Folder `studies/nominal6_additions_20261127/`. Results: `REPORT.md`.

## What was done

- **Part A:**
  - Matan's decision of 27 Nov ("Option A") recorded verbatim in
    `studies/cms_mc_weights_v3/sources/v8_decisions_2026-11-27.json` (DECISION RECORD ONLY; written by
    `tools/make_v8_decisions.py`);
  - README text in `DOCUMENTED_EXCEPTIONS.md`.
- **Part B (Mac, read only):**
  - McM fragments and requests (`evidence/mcm/`);
  - genproductions cards;
  - ATLAS job options (`evidence/atlas_joboptions/`);
  - YR4 pages and paper extracts (`evidence/theory/`);
  - cross-section options (`tools/xsec_options.py` → `evidence/xsec_options.json`, `evidence/xsec_tables.md`);
  - complete file lists (`tools/make_mappings.py` → `precheck/mappings/`, `evidence/inputs_20261127.json`).
- **Part C (cluster, wipp-home; wipp-campus "No route to host", one try):**
  - work dir `/storage/agrp/berkom/atlas-utilization/work/mcexp_20261103/nominal6_precheck_20261127/` (new);
  - code: pinned checkout `checkouts/mcexp_20261103/repo_6de9d3e605900a628bae372bdba4ea3308e9750f`
    (HEAD + clean status asserted);
  - helper scripts in `$W/scripts/` (copies of `precheck/` at commit fd84538, sha256 in `$W/scripts.sha256`;
    `gen_check_v2.py` / `pbs_gen_check_v2.sh` = the fixed `precheck/gen_check.py` / `pbs_gen_check_v2.sh`,
    sha256 in `$W/scripts_v2.sha256`).

  | job | id | result |
  |---|---|---|
  | precheck array, file 0 of the 14 (`pbs_mc_pilot.sh`, unchanged) | 5662736[] | 14/14 exit 0, Σw check pass |
  | generator check, attempt 1 | 5662737 | exit 1 after 9 s (no aiohttp for HTTPS); logs `logs/gen_check.{out,err}` kept |
  | generator check, retry (root:// as the driver) | 5662743 | exit 0, `gen_check/gen_check.json` |
  | gridpack cards | 5662738 | exit 0, `gridpack_cards/` (see the file count below) |
  | analysis (`afterany` on the array) | 5662739 | exit 0, `evidence/precheck_analysis.json` |

  - Ids are in `$W/jobids.txt` and `$W/jobid_gen_retry1.txt`; copies are in `evidence/precheck/`.
- **File count** (`lfs quota -u berkom /storage`, column 6): 122,540 before, 133,497 after. About 10,710 of that is
  `$W/gridpack_cards/` (the tar wildcards also matched card files in every MadGraph `SubProcesses/` folder). The
  needed 143 files are copied to `evidence/gridpack_cards/`.
- **28 Nov 2026, Matan's OK** ("Yes, delete only .../nominal6_precheck_20261127/gridpack_cards/ and nothing else; measure
  the file count before and after"): `$W/gridpack_cards/` (10,710 entries, a plain directory, not a link) deleted with
  `rm -rf` on wipp-home; nothing else touched. File count **133,497 before, 122,787 after** (−10,710, VERIFIED BY
  RUNNING).

## Commits

- 870961a: Parts A/B.
- fd84538: precheck scripts.
- The final commit (REPORT, HANDOFF, results): see `git log` on this branch.

All are pushed to origin only; the upstream gate printed nothing before every push; no Pull Request.

## How to resume

- Re-read results: `ssh wipp-home`, `W=` the work dir above. Everything there is read only; never write into
  `work/mcexp_20261103/full/`.
- Re-run the precheck analysis: `qsub ... -v WORK_DIR=$W $W/scripts/pbs_analysis.sh`. It writes
  `$W/evidence/precheck_analysis.json`, so use a new `--out` to avoid overwriting.
- The full-production mappings of the 14 records are ready in `precheck/mappings/mapping_<rid>.txt` (complete
  lists, 187 lines). They are not submitted.

## What remains (in order)

1. The technical lead verifies `REPORT.md` on GitHub.
2. **Matan decides the N3 overlap** (`REPORT.md` section 2, options 1–4). N3 is blocked until then. Options 1–2 need
   a generator-level m_ℓℓ veto that does not exist yet (a code change and a new pin).
3. **Matan hand-checks every cross section** of the 14 (`REPORT.md` section 3.5, decisions 1–6). Also for him:
   - 69771's top content;
   - the 40062 observation (×1.49 under the N4 reading; a delivered value).
4. Done 28 Nov: `$W/gridpack_cards/` removed (122,787 after). Projection production + rebuild ≈ 131,285 (ESTIMATE),
   below 140,000.
5. Registry v6 (new builder script; v3–v5 untouched) with Matan's values, and its tests.
6. Production of the 14 (187 files, ~2,272 cluster files ESTIMATE), same pin unless the N3 veto needs new code.
7. A full rebuild with v6 into a new directory (~6,226 cluster files ESTIMATE), then the checks (as on 14 Nov:
   rule checks, `checks_v4.py`, `checks_final.py`).
8. Delivery: README with `DOCUMENTED_EXCEPTIONS.md`, per-sample files, checksums. Nothing is sent before Matan's go.

## Nominal-6 production (28 Nov 2026)

Branch `feature/nominal6-additions-20261128` (fork only), made from `origin/prep/nominal6-additions-20261127` @ 5197b43.
Decisions: Matan, 28 Nov 2026 ("approve all"), verbatim in `studies/cms_mc_weights_v3/sources/v9_decisions_2026-11-28.json`
(written by `production_20261128/make_v9_decisions.py`).

### Cleanup and quota (VERIFIED BY RUNNING)
- D-clean: `nominal6_precheck_20261127/gridpack_cards/` is gone (`ls`: "No such file or directory", 28 Nov). Nothing
  else was deleted.
- File count (`lfs quota -u berkom /storage`, column 6):
  - 122,787 at the start;
  - 122,794 after the D-WZ check was submitted;
  - 122,810 after it finished.

### D-WZ: WZjj replacement found (`evidence/wzjj/`)
- Portal search: `portal_search_wzjj.json`. Check job **5669916**, output in `work/mcexp_20261103/nominal6_wzcheck_20261128/`:
  - cards are listed first, then only exact paths are streamed out with `tar -xO`, so no folders are created;
  - `gen_check.py` runs on file 0.
- **72728** WZJJ_EWK_InclusivePolarization: no `$ t t~`; a top quark in 1,575 of 100,000 file-0 events (1.6 %). Not used.
- **72720** WZ2JetsTo3LNu_MJJ-100toInf_EWKnotop:
  - `p p > w± z j j $ t t~ QED=4 QCD=0, z > l+ l-, w > l v` (ℓ = e μ τ);
  - cuts m_jj > 100, |η_ℓ| < 3;
  - **0 of 5,586** file-0 events with a top.
  - It **replaces 69771**. Portal 0.01370 pb (MiniAOD 72719), a PROPOSAL pending Matan's hand check.
  - The portal lists 1,149,069 events, the same number as 75561. Its 20 files (2.73 GB) differ from 75561's, so the
    number is UNVERIFIED; production measures it.
- Summary: `evidence/wzjj/wzjj_outcome.json`.

### Registry v6 (no build)
- `studies/cms_mc_weights_v3/build_registry_v6.py` → `cms_mc_normalisation_v6.json` (`--check` OK). v3/v4/v5 are
  untouched and the builder default is still v3.
- v5 → v6 (`production_20261128/v5_to_v6_diff.txt`):
  - **+6 records**: 75561, 72648, 71636, 71640, 72720, 74314;
  - **40062 changed**, 6.22392e-5 → 9.27518e-5 pb (×1.4902);
  - every other record is identical;
  - excluded: +69681, 69699, 69771 (the other 6 Dalitz records were already excluded; their reason is now D-N3);
    74314 leaves the excluded list;
  - 79 records, 77 in the full run.
- 7 values carry `"matan_hand_check": "PENDING"`; see `production_20261128/HAND_CHECK_SHEET.md`.
- Tests:
  - `studies/cms_mc_weights_v3/tests/test_registry_v6.py`: 7/7 pass (incl. the live portal values);
  - **all 20 CMS test files exit 0** (`production_20261128/cms_tests_v6.txt`; three by-product files the old tests
    write were moved out, not committed).

### Production (submitted 28 Nov 2026, 20:23 IST, `production_20261128/submit_production_20261128.sh`)
- Mappings: `production_20261128/mappings/`, from `make_mappings_20261128.py` with `fetch_file_list_complete` (pin).
  - 75561: 9 files; 72648: 5; 71636: 22; 71640: 22; 74314: 4; 72720: 20.
  - **82 files**, 5,246,205 events (portal).
  - Page 1 equals the complete list for all six, and no file is listed but unpublished.
- Pin 6de9d3e (HEAD and a clean status asserted); `pbs_mc_pilot.sh` unchanged; mem 6 GB, io=25.
- Walltimes (`production_20261128/walltimes.txt`, ESTIMATE): ≥ 4 × the 27 Nov file-0 time scaled to the largest file.
  - 75561 6 h; 72648 2 h; 71636 6 h; 71640 6 h; 74314 24 h;
  - 72720 48 h (no precheck; scaled from 69771).
- New work dir `work/mcexp_20261103/nominal6_runs_20261128/`, holding `mappings/`, `runs/`, `logs/<record>/` and
  `jobids.txt` (`<record> <job> <n> <walltime>`).
- Projection (ESTIMATE): +996 cluster files (82 × 12 + 2 × 6) → ~123,800 after production. Then ~+6,200 for the
  later full rebuild + checks → **~130,000** (ceiling 140,000).

**Submitted (VERIFIED BY RUNNING).** The script asserted pin 6de9d3e, a clean checkout, and new `runs/` and
`jobids.txt`. Job ids are in `production_20261128/jobids.txt`, a copy of `$W/jobids.txt`:

| record | job | files | walltime |
|---|---|---:|---|
| 75561 ZZJJTo4L_EWKnotop | 5670109[] | 9 | 06:00:00 |
| 72648 WWJJToLNuLNu_EWK_noTop | 5670110[] | 5 | 02:00:00 |
| 71636 WpWpJJ_EWKnotop | 5670112[] | 22 | 06:00:00 |
| 71640 WpWpJJ_QCDnotop | 5670113[] | 22 | 06:00:00 |
| 74314 ZH_HToZZ_4LFilter | 5670114[] | 4 | 24:00:00 |
| 72720 WZ2JetsTo3LNu_MJJ-100toInf_EWKnotop | 5670115[] | 20 | 48:00:00 |

- 82 subjobs; right after submission 32 running and 50 queued (0 of mine queued before).
- File count: 122,813 before, 122,830 right after.
- Expected finish (ESTIMATE): most within a few hours (27 Nov file-0 walls were 2–13 min; on 9 Nov the size-scaled
  estimates were 2–15 × too high). At the latest by the walltimes above (72720: 48 h).
- Outputs go to `$W/runs/record<rid>/job_<file_index>/` (9 files each); logs to `$W/logs/<rid>/f_<i>.{out,err}`.

**How to check the status** (read only):

    ssh wipp-home 'bash -l -c "/opt/pbs/bin/qstat -u berkom -t | grep n6_ | awk \"{print \\\$10}\" | sort | uniq -c"'
    # per subjob exit status after the end: qstat -xf <id>[<i>] | grep Exit_status; or grep "Exit status" $W/logs/*/f_*.err
    # the pinned audit (as 9 Nov): studies/cms_mc_weights_v3/fullrun/audit_production.py on $W/jobids.txt, expected 82/82 OK

### What remains (in order)
1. **Status check of the six arrays**: 82/82 exit 0, 9 files per job, Σw self-check, no failures. 72720's real event
   count is measured there (the portal's 1,149,069 is UNVERIFIED). If any job fails, report it; do not resubmit
   without reporting.
2. **Matan's hand check** of the 7 PENDING values (`production_20261128/HAND_CHECK_SHEET.md`), then **a separate
   commit** setting `matan_hand_check` to "VERIFIED BY MATAN" in v6. Do it through a builder change and `--check`; never
   edit the JSON by hand.
3. **Full MC build** with `--registry studies/cms_mc_weights_v3/cms_mc_normalisation_v6.json` given explicitly, and
   `--runs-dir work/mcexp_20261103/full/runs` (as on 14 Nov), `--extra-runs-dir work/fullrun_20261025/mc/runs` AND
   `--extra-runs-dir work/mcexp_20261103/nominal6_runs_20261128/runs` (the option is repeatable). Into a NEW
   directory.
   ~6,200 cluster files (ESTIMATE).
4. **Checks** as for the 14 Nov final build:
   - audit;
   - rule checks R1–R7;
   - Z peaks;
   - data/MC;
   - D3 single-event dominance;
   - names and edges vs the data delivery (start masses will shift).
5. **README update**, including `DOCUMENTED_EXCEPTIONS.md` (N3 documented, 69771 → 72720, 40062 corrected) and the
   new samples.
6. **Delivery**, only after Matan's go.
