# HANDOFF — CMS full run with loose muon/electron IDs (25 Oct 2026 directories)

Branch `run/cms-fullrun-20261025` (origin only), made from `origin/lean/cms-layer-20261023`
@ `33d77f5` (= upstream master `29291ae` + 63 CMS files). Decision (Maryna, 24 Oct, approved
by Matan): muons CMS Loose ID (`Muon_looseId`), isolation `pfRelIso04_all < 0.15` kept;
electrons `cutBased >= 2` (Loose); jets unchanged.

Nothing is submitted for the full run. No Pull Request; nothing upstream; no message sent.

## Step 0 — preflight (24 Oct 2026) — DONE

- `upstream/master` = `29291ae` (unchanged) and `origin/lean/cms-layer-20261023` = `33d77f5`
  — VERIFIED BY RUNNING (`git rev-parse` after `git fetch`).
- File quota on /storage: **72,328** files used (soft limit 150,000; Matan's ceiling 125,000)
  — VERIFIED BY RUNNING (`quota -s` on wipp-home). Space 293.7 GB of 4 TB.
- `ssh wipp-campus`: timed out (one try). `wipp-home` is used.
- Branch `run/cms-fullrun-20261025` created from the lean branch.

## Step 1 — branch titles — DONE

PBS job `5331420` (io=1, wn001, 25 s, exit 0), from the pinned clone
`checkouts/fullrun_20261025/step1_c0ce7bd` (commit `c0ce7bd`). Script `cluster/branch_titles.py`,
launcher `cluster/pbs_titles.sh`; output `evidence/branch_titles.json`. VERIFIED BY RUNNING.
Both files (data DoubleEG Run2016G record 30521 file 0; MC TTTo2L2Nu record 67801 file 0) have
all three branches, with identical titles:

| branch | type | title (verbatim) |
|---|---|---|
| `Muon_looseId` | bool | "muon is loose muon" |
| `Muon_mediumId` | bool | "cut-based ID, medium WP" |
| `Muon_pfRelIso04_all` | float32 | "PF relative isolation dR=0.4, total (deltaBeta corrections)" |
| `Electron_cutBased` | int32 | "cut-based ID Fall17 V2 (0:fail, 1:veto, 2:loose, 3:medium, 4:tight)" |

So `cutBased >= 2` is "loose or tighter" exactly as the title defines it.

## Step 2 — code change — DONE

Every use in CMS code before the change (lean `33d77f5`, `git grep`):

| file:line (before) | what | now |
|---|---|---|
| `studies/m0m1j0_cms/selection.py:18,20` | docstring (mediumId, cutBased>=3) | looseId, cutBased>=2 (+ a dated note) |
| `studies/m0m1j0_cms/selection.py:57` | `ELECTRON_CUTBASED_MIN = 3` | `= 2` |
| `studies/m0m1j0_cms/selection.py:97` | `NEEDED_BRANCHES` "Muon_mediumId" | `MUON_ID_BRANCH` (new constant = "Muon_looseId") |
| `studies/m0m1j0_cms/selection.py:159,168` | `select_muons` reads/uses mediumId | reads `events[MUON_ID_BRANCH]`, cuts on `looseId`; iso `< MUON_ISO_MAX` (0.15) unchanged |
| `studies/m0m1j0_cms/selection.py:179,184` | `select_electrons` `cutBased >= ELECTRON_CUTBASED_MIN` | unchanged code; constant now 2 |
| `studies/cms_datasets/cluster/run_dataset_on_file.py:201` | driver branch list "Muon_mediumId" | `selection.MUON_ID_BRANCH` |
| `studies/cms_datasets/cluster/run_dataset_on_file.py:203` | driver reads "Electron_cutBased" | unchanged |
| `studies/cms_datasets/cluster/run_dataset_on_file.py:2305-2306` | `selection.select_muons` / `select_electrons` | unchanged (same functions) |
| `studies/cms_datasets/cluster/run_dataset_on_file.py:2320` | diagnostics-only electron mask, `>= selection.ELECTRON_CUTBASED_MIN` | unchanged (already the constant) |
| `studies/cms_datasets/electron_prep/common.py:132-133` | `selection.select_muons` / `select_electrons` | unchanged (same functions) |
| `studies/cms_datasets/tests/test_btag_singleelectron.py:86` | synthetic "Muon_mediumId" column | "Muon_looseId" |

No other CMS file names a muon/electron ID: every muon and electron selection (data and MC; the
MC path runs the same driver with `--is-mc`) goes through `select_muons` / `select_electrons` and
the selection.py constants. `docs/CMS_KNOWN_LIMITATIONS.md` mentions `looseId` only for the
upstream FileParser field-drop issue; the CMS driver does not use FileParser — it reads its
required branches directly and stops if one is missing (`read_events`).

New test `studies/cms_datasets/tests/test_loose_lepton_ids.py` (17 checks): looseId used (and
mediumId not) by `select_muons`, `NEEDED_BRANCHES` and the driver branch list; iso 0.15 kept
(strict `<`); `ELECTRON_CUTBASED_MIN == 2` and cutBased 2/3/4 kept, 0/1 dropped; the driver's
diagnostics mask matches `select_electrons`; jets unchanged (tight ID bit, 0.2489 b-tag).

`docs/CMS_LAYER.md`: added the line "24 Oct 2026, Maryna: loose muon and electron IDs; muon iso
< 0.15 kept". (Its "byte-identical to `de012d2`" check now also differs in the 3 changed files
and the new test, by design.)

Tests (`evidence/local_tests.txt`, Mac, `PYTHONPATH=.`): **all 16 CMS test files + the new one
pass, 0 failures — VERIFIED BY RUNNING.** The 5 skips in `tests/` are the network tests that read
real ROOT files (`RUN_NETWORK_TESTS=1`); they are skipped by design (ROOT reading only in PBS).

## Step 3 — small real-file check (in progress)

Scripts: `cluster/pbs_precheck.sh` (method of `studies/sync_42_20261023/cluster/pbs_proof.sh`),
`cluster/object_compare.py` (per-object OLD vs NEW selection on the real file),
`cluster/build_compare.py` (OLD vs NEW per-file metadata and builds), `cluster/mapping_precheck.txt`.
