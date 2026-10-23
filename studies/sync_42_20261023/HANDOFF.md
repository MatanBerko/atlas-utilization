# HANDOFF — sync with upstream #39 #40 #42 (23 Oct 2026)

**Current step: steps 1–6 DONE — every CMS output identical OLD vs NEW (`PROOF.md`); the #42
trigger check is written (`TRIGGER_42_CHECK.md`). STOPPED before step 7: master and the two
feature branches have NOT been moved. Step 7 waits for Matan's "go ahead with step 7".**
Nothing upstream; no Pull Request; no message sent.

## Branches (origin only)

| sync branch | made from | merge commit | head now | what is on top of the merge |
|---|---|---|---|---|
| `sync/master-upstream-42-20261023` | `origin/master` `aaf945a` | `91dfa13` | (this commit) | CMS test update `dc1da07`; this study (static check, proof scripts, evidence, reports) |
| `sync/data-upstream-42-20261023` | `origin/feature/cms-btag-singleelectron-20261020` `b6b441c` | `5bc5f3a` | `c0e734b` | CMS test update (cherry-pick of `dc1da07`) |
| `sync/mc-upstream-42-20261023` | `origin/feature/cms-mc-btag-singleelectron-20261020` `cd22aa2` | `6785a97` | `dc760da` | CMS test update (cherry-pick of `dc1da07`) |

- Upstream at merge time: `29291ae` (#42), which includes `9af30d2` (#39) and `5fbf1ef`
  (#40). All three merges were clean (no conflicts).
- Gate (`git diff --name-status $(git merge-base upstream/master HEAD) HEAD -- <upstream
  files>`) printed nothing on every branch before every push. BASE = `29291ae`.
- Each branch is 0 commits behind upstream.

## Step 2 — static check (`static_check.py` → `evidence/static_check.json`)

The #35 tool was updated: BEFORE 7f2da5d / AFTER 29291ae; all CMS files on the three NEW
branches; per-method diffs; module-attribute use; a name-based reachability graph; and
hand-written verdicts with file:line.
- Changed upstream definitions CMS can reach by name: `IMCalculator._get_all_events_fs`,
  `IMCalculator._limit_particles_in_fs`, `physics_calcs.limit_particles_in_fs`,
  `physics_calcs.filter_events_by_kinematics`, `consts.MUON_REL_ISOLATION_FIELD`.
- **None is executed by CMS production** (verdicts in the JSON). The only live callers of
  `limit_particles_in_fs` are CMS tests and the finished m0m1j0 study (not re-run).

## Step 3 — local tests (`evidence/local_tests.txt`)

- The tests ran in git worktrees (one CMS test reads `upstream/master` with git), as scripts
  with `PYTHONPATH=.` (the Mac has no pytest).
- **All CMS test files pass on the three NEW branches.**
- Changed: `test_exact_jet_labels.py` (19 checks) and `test_electron_datasets.py` (3 checks).
  Both pinned the OLD capping and now state #40's; details are in `PROOF.md`. No production
  code changed.

## Step 4 — real-file proof (cluster, `PROOF.md`)

- Checkouts: `/storage/agrp/berkom/atlas-utilization/checkouts/sync42_20261023/`. It holds
  6 tarballs (old_/new_ × master, data, mc) and `pinned_code_20261023.tar.gz` (verified).
- Work: `/storage/agrp/berkom/atlas-utilization/work/sync42_20261023/`, with `mapping.txt`
  (9 lines), `pbs_proof.sh` (a copy, from the new_master tarball), `jobids.txt`, `runs/`,
  `deliver/`, `logs/`, `evidence/` and `code → checkouts/sync42_20261023`.
- Jobs: `5305468[]` (perfile, 0–8, 8gb, 4h, io=25) and `5305469` (build+compare, 16gb, 4h,
  io=25, afterok). All exited 0.
- **Result: 72/72 shards identical, 0 physics metadata differences; the master delivery
  (220 histograms), the data matched5 delivery (548) and the MC build (1,217 + 1,118 + 1,292,
  Sumw2) are bit-identical.**
- File count 122,579 → **122,878** (+299). Nothing is queued or running.
- Connection: `wipp-campus` timed out (tried once). `wipp-home` was used; it dropped briefly
  once at 16:47, without effect.

## Step 5 — `TRIGGER_42_CHECK.md`

- CMS matches the **selected** leptons (after pT/η, ID, isolation and e–μ overlap removal). It
  decides before the ≤ 4 non-jet rule and the labelling, and MC uses the identical functions
  as data.
- Differences from ATLAS after #42 are listed in the file: dataset-specific dilepton and
  single-lepton triggers; ΔR matching; ≥ 2 matched leptons for the dilepton datasets; the
  MuonEG muon leg is unmatched; CMS data is checked per selected lepton (ATLAS data is
  event-level). Nothing was changed.

## Step 7 (NOT done — waits for Matan's "go ahead with step 7")

Fast-forward only, gate before each push:

```
git fetch origin upstream
git push origin sync/master-upstream-42-20261023:master
git push origin sync/data-upstream-42-20261023:feature/cms-btag-singleelectron-20261020
git push origin sync/mc-upstream-42-20261023:feature/cms-mc-btag-singleelectron-20261020
```

Each is a fast-forward today (each sync branch descends from its target's current head). If
any target has moved, or a push is refused as non-fast-forward, STOP. Then report the new
hashes.

## Out of scope (untouched)

- implementing #39, #40 or #42 for CMS;
- every other branch, including `study/cms-ttbar-pr40-20261021`;
- the m0m1j0 study;
- any production, delivery or message.
