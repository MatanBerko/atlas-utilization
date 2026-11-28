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
