# Branch layout after the rebuild (14 Oct 2026)

A "branch" is a named, saved version of the project. This page describes the
layout introduced by the rebuild. It replaces the fork's earlier
`docs/BRANCH_LAYOUT.md` (5 Oct 2026), which is still readable in
`archive/master-2026-10-14`.

## The main line

| branch | what it is |
|---|---|
| `master` | The main line. **After the rebuild is approved** it becomes upstream master plus the CMS layer as added files only (`docs/CMS_LAYER.md`). Until Matan approves the switch, `master` stays at `ba89791`. |
| `rebuild/master-2026-10-14` | The candidate new master: upstream `e1ce8bb` + added CMS files. |
| `validate/rebuild-2026-10-14` | The candidate plus the validation evidence (old code vs new code on the same files). Kept separate so the new master stays clean. |

## Archive and backups (never delete)

| branch | what it is |
|---|---|
| `archive/master-2026-10-14` | Permanent archive of the fork's master as it was on 14 Oct 2026 (`ba89791`): every older study, the main-pipeline CMS edits, all earlier deliveries. |
| `backup/master-pre-rebuild-2026-10-14` | Safety copy of the same commit, taken before the rebuild. |
| `backup/master-pre-*` (older) | Earlier safety copies of master, one per past master move. |

## Active branches (work in progress, not on the new master)

| branch | what it is |
|---|---|
| `design/cms-mc-weights`, `design/cms-mc-weights-v3`, `design/hgg-selection`, `design/m0m1j0-bumpnet` | Design documents |
| `feature/cms-mc-weights-v3` | CMS Monte Carlo weighting, current version |
| `study/cms-mc-hist-counts`, `study/cms-mc-jet-excess`, `study/cms-mc-pileup` | The three study branches built on `feature/cms-mc-weights-v3` |
| `study/singleelectron-ele27-tnp` | SingleElectron trigger study |
| `deliver/onedrive-upload-20261013` | Upload of the delivery to OneDrive |
| `study/lumi-coverage-four-datasets` | Luminosity coverage of the four delivered datasets |
| `docs/fork-vs-upstream-map-2026-10-11` | Map of how the fork differs from upstream |
| `ops/cluster-cleanup-20261011` | Cluster file-count clean-up |

The MC and SingleElectron branches were built on the old master. Moving
them onto the new layout is a separate, later task.

All other branches on the fork are older work. They are untouched and
remain available; clean-up is a separate decision.

## Rules that keep this layout safe

- Upstream (`github.com/Zhavi221/atlas-utilization`) is fetch-only.
- On the new master, files that exist upstream are never edited; CMS work
  goes in added files.
- Replacing `master` with `rebuild/master-2026-10-14` needs a force-push and
  Matan's explicit OK.
