# HANDOFF — lean CMS branch and its proof (23 Oct 2026)

**Current step: 5–6 — proof tools pushed; tarballs and jobs next.**
Nothing merged; no existing branch changed; nothing sent; nothing upstream.

## Branches (origin only)

| branch | commit | what |
|---|---|---|
| `lean/cms-layer-20261023` | `33d77f5` | upstream master `29291ae` + 63 added files (the minimal CMS layer), no records |
| `study/lean-branch-proof-20261023` | (this branch, from the lean branch) | this proof: tools, report, evidence |
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

## How to resume

1. `git fetch origin`; this file's "Current step".
2. `/opt/pbs/bin/qstat -u berkom -t`. Never resubmit a job that is queued, running or finished.
