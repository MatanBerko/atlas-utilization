# Branch layout — a plain-language guide

This page explains what each "branch" (a named, saved line of work — think
of it as a labeled folder holding one version of the whole project) in this
fork is for, and which one to use as a starting point for new work. Written
for a reader who does not use git. Every claim below was checked directly
against the repository as of 2026-09-24, not assumed — where a check turned
up something different from what was expected, that is written down
instead, in bold.

**Note on this page's history:** an earlier version of this same page (still
readable on the `docs/upstream-divergence-map` branch) said `master` was
deliberately kept close to upstream and was *not* where CMS work happens.
That was Matan's decision at the time. It has since been reversed,
consciously and explicitly — see "Why this changed" below. This page is
kept up to date with the current decision; the earlier version is left in
place on that other branch as a record of what was decided before, not
deleted or silently rewritten.

## `master`

**As of 2026-09-24, `master` now carries the current CMS work.** Two
branches were merged into it: `cms/pipeline-baseline` (the shared-pipeline
capabilities) and `analysis/m0m1j0-cms` (the m0m1j0 study, including its
V0-V3 selection-variant comparison). Confirmed directly: `master` now has
all of the following that a current CMS analysis needs — optional extra
per-object fields, generic yes/no ("boolean") cuts on object properties
(`bool_require`/`bool_any_of`), an HLT trigger-requirement filter
(`services/parsing/trigger_requirements.py`), a certified-run/"golden JSON"
data-quality filter (`services/parsing/validated_runs.py`), and
simulation/Monte-Carlo weight reading (`services/parsing/mc_weights.py`).
Both `studies/hgg_cms/` (the Higgs-to-two-photons analysis) and
`studies/m0m1j0_cms/` (including `studies/m0m1j0_cms/v3_variants/`) are
present on `master` with their existing results and plots carried across
unchanged.

**New CMS analysis work should now start from `master`.**

### Why this changed

This is a reversal of the earlier decision (recorded above and preserved on
`docs/upstream-divergence-map`) to keep `master` lean and close to
upstream. Two reasons, both real:

1. **`master` could not run a current CMS analysis at all.** Before this
   merge it had none of the five capabilities listed above — a hard block
   for anyone wanting to start new CMS work from `master` as intended.
2. **The H→γγ analysis is the only CMS analysis that exercises the shared
   pipeline end-to-end**, rather than working from already-parsed files.
   With it on `master`, running it acts as a regression check: if a future
   change to the shared pipeline breaks something CMS depends on, H→γγ is
   positioned to catch it, on the same branch other CMS work will build
   from.

### The accepted cost

`master` now diverges further from the original upstream project than it
did before — as of this merge, 528 files differ between `master` and
upstream's `master` (`bea982d`), up from 11 before. This is an accepted
consequence of the decision above, not a problem to fix, and nothing was
"aligned" back toward upstream as part of this work.

One further consequence: this fork's own work will conflict more when
later re-synced against upstream's ongoing changes. **Reported (from an
earlier trial of that sync, not independently re-run while writing this
page — the tooling available in this session would not permit re-running a
merge trial against the upstream repository to reproduce the exact number):
merging upstream's current `master` into this line of work conflicted in 7
files.** Treat this number as carried over from that trial rather than
freshly confirmed today.

## `cms/pipeline-baseline`

Still exists, still points at `f33d8d47a060082d70c4dd1451e81ad29cd0950d` —
unchanged by this merge. Its content (the shared-pipeline capabilities) is
now also on `master`, reached there by merging this branch in. This branch
remains available as a narrower, analysis-neutral starting point alongside
`master` if that distinction is ever useful again.

## `feature/hgg-selection-and-output`

Still exists, still points at `f33d8d47a060082d70c4dd1451e81ad29cd0950d`
(the same saved version as `cms/pipeline-baseline`) — unchanged by this
merge. The H→γγ analysis it carries is now also on `master`, via
`cms/pipeline-baseline`.

## `analysis/m0m1j0-cms`

The m0m1j0 study (an analysis of the two leading muons plus the leading
light jet), including its V0-V3 selection-variant comparison added on
2026-09-23. Its content is now also on `master`, reached by merging this
branch in as the second of the two merges. This branch itself is
unchanged by that merge — it still exists at its own commit, separately
from `master`.

## `backup/master-pre-cms-merge-2026-09-24`

**New branch**, created immediately before this merge, pointing at exactly
what `master` was beforehand: `b38f566d3503820b8d968f388f18a1450896d284`.
It exists purely as an undo point — if this merge ever needs to be
reversed, `master` can be moved back to point at this commit, rather than
anything needing to be recovered or reconstructed. It carries no changes of
its own.

## The three 4-lepton branches — deliberately not merged

`analysis/higgs-4lepton-clean`, `analysis/higgs-4lepton-zz`, and
`analysis/4l-collection-drop-check` were **not** merged into `master` and
were not touched at all by this work. They date from early September, sit
54 commits behind `master`, and each conflicts in 4-5 files with the
September pipeline work that has since superseded the machinery they
touch. They remain exactly where they were, available for later use. If
their results are wanted later, porting the relevant study folder forward
onto current `master` is likely a cleaner path than merging these branches
as they stand.

## `test/upstream-trigger-cms`

Unchanged by this work, still at its own commit. A throwaway test branch
from an earlier task (testing whether upstream's trigger-matching feature,
switched off, changes anything for CMS — it doesn't). Not merged anywhere,
per that task's own instructions.

## `docs/upstream-divergence-map`

Unchanged by this work, still at its own commit. Holds
`docs/UPSTREAM_DIVERGENCE_MAP.md` (a full inventory of how this fork
differs from the original upstream project) and an earlier version of this
very page, kept there as history rather than deleted. Not merged into
`master` — the content relevant to `master`'s branch layout was rewritten
here by hand, current as of this merge, rather than by merging that branch
in.

## `chore/align-noop-files-with-upstream`

Unchanged by this work, still at its own commit (currently the same saved
version as `master` was *before* this merge). Not merged, not touched.

## One rule that applies to all of the above

**Nothing in this fork is ever pushed, merged, or filed as a request/issue
on the original upstream project except by Matan's own, separate,
deliberate decision.** No branch listed on this page changes that, and this
merge did not either — everything above happened only within Matan's own
fork.
