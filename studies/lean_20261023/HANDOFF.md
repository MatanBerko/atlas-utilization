# HANDOFF — lean CMS branch and its proof (23 Oct 2026)

**Current step: COMPLETE (24 Oct 2026, ~00:20 IDT). Nothing running. Result: `REPORT.md`.** Next (needs Matan): the full run from the lean branch.
Nothing merged; no existing branch changed; nothing sent; nothing upstream.

## Branches (origin only)

| branch | commit | what |
|---|---|---|
| `lean/cms-layer-20261023` | `33d77f5` | upstream master `29291ae` + 63 added files (the minimal CMS layer), no records |
| `study/lean-branch-proof-20261023` | this branch (from `33d77f5`) | this proof: tools, report, evidence |
| `feature/cms-mc-multiplicity40-20261023` | `de012d2` | the OLD side of the proof (unchanged) |

## Steps 1–4 (VERIFIED BY RUNNING, Mac)

1. Preflight: `upstream/master` = `29291ae`; `origin/feature/cms-mc-multiplicity40-20261023` = `de012d2`
   (264 added files on top of upstream).
2. The lean branch: the 60 listed files checked out from `de012d2`, plus 3 more (below);
   `docs/CMS_LAYER.md` rewritten. One commit, `33d77f5`.
3. Static checks:
   - (a) `git diff de012d2 lean -- <every file except docs/CMS_LAYER.md>` is empty;
   - (b) the gate is empty;
   - (c) `git diff --name-status upstream/master lean` is 63 lines, all `A`, and the set equals the list;
   - (d) every repo module imported by and every repo path written in the 63 files was checked. The missing
     ones led to the 3 additions. The rest are comments/docstrings or one non-run-path read (see below);
   - (e) all 28 Python entry points run `--help` (or import) with exit 0. `build_registry.py --check` passes
     (15 records). `make_fullrun_mappings.py` writes its 13 mapping files from the lean tree.
4. Tests: all 15 group-B test files, on the lean branch and on a `de012d2` worktree: exit 0 on both,
   and identical output. The one textual difference is a file path that the test cuts at
   90 characters (the `de012d2` copy ran in a longer scratch path). The check itself passes on both.

Added beyond the given list (all exist on `de012d2`; none is a record of a past study):
- `studies/cms_datasets/electron_prep/common.py`: code, imported by `electron_vB/gen_full_mapping.py`.
- `studies/cms_mc_weights_v3/evidence/fullrun_inputs_20261017.json`: an input, read by
  `fullrun_prep/make_fullrun_mappings.py` (the MC full-run mapping maker).
- `studies/cms_mc_weights_v3/evidence/probe_mc_records.json`: an input, read by `build_registry.py`,
  which `test_mc_weights_v3.py` runs (`--check`).

Not added (a record, not on the run path): `studies/m0m1j0_cms/v2/data/merge_v2_summary.json`, read only
by `merge_and_count.py`'s own `main()` self-check, which no launcher or builder runs.

## Steps 5–6 plan (cluster)

- Tools on this branch: `studies/lean_20261023/cluster/pbs_proof.sh` (method of sync_42; MODE=perfile /
  build / precheck), `cluster/compare_data_runs.py` (sync_42's wrapper), `cluster/mapping.txt`
  (the sync_42 data and MC lines: 5 data files, MC 67801:0 and 72752:0), `precheck_capped.py`.
- Checkouts: `checkouts/lean_20261023/{old,new,tools}.tar` (`git archive` of `de012d2`, the lean tip,
  this branch). Work: `work/lean_20261023/`.

## Steps 5–6: submitted (VERIFIED BY RUNNING)

- File count before: **123,602**. `wipp-campus` timed out once; `wipp-home` used.
- `checkouts/lean_20261023/`: `old.tar` (de012d2, sha256 60a00644…), `new.tar` (33d77f5, fae6b20a…),
  `tools.tar` (cf73f87, fb789565…). The commit IDs and checksums were checked on the Mac and on the cluster.
- `work/lean_20261023/`: `mapping.txt`, `tools/` (the launcher, from tools.tar), `logs/`, `evidence/`, `jobids.txt`.
- Jobs (queue N, `-m n`):
  - `5311724[]` perfile 0–6 (8gb, 4h, io=25);
  - `5311725` build + compare (afterok, 16gb, 4h, io=25);
  - `5311726` precheck (2gb, 1h, io=1).
- File count after submission: 123,617.

## Steps 5–7 result (VERIFIED BY RUNNING)

- `5311724[]` 0–6 all exit 0; `5311725` exit 0 (comparison rc=0); `5311726` exit 0.
- OLD == NEW: data per-file 40/40 databases, MC per-file 16/16 (siblings included), data delivery
  201/201 histograms (both ROOT files), MC smoke build 290 + 292 + 296 histograms; 0 physics
  metadata differences. Evidence: `evidence/cluster/`.
- Pre-check: 0 trimmed lists in 390 data and 497 MC files; largest lists 292,176 (data) and 142,407 (MC).
- `checkouts/lean_20261023/lean_20261023_code_tarballs.tar.gz`: verified (the three tarballs
  inside are byte-identical). The tarballs and every output were left in place.
- **Final file count: 123,867** (+265 vs 123,602).

## How to resume

1. `git fetch origin`; this file's "Current step".
2. `/opt/pbs/bin/qstat -u berkom -t`. Never resubmit a job that is queued, running or finished.
