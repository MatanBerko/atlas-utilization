# Branch layout — a plain-language guide

This page explains what each "branch" (a named, saved line of work — think
of it as a labeled folder holding one version of the whole project) in this
fork is for, and which one to use as a starting point for new work. Written
for a reader who does not use git. Every claim below was checked directly
against the repository, not assumed — where a check turned up something
different from what was expected, that is written down instead, in bold.

## `master`

Kept deliberately close to the original upstream project, on purpose.
Matan's decision is that `master` only ever receives changes essential to
running CMS data at all — it is not where day-to-day CMS analysis work
happens.

**As of this writing, `master` cannot run a current CMS analysis.**
Confirmed directly: `master` has none of the following that a current CMS
analysis needs — no HLT trigger-requirement filter, no certified-run
("golden JSON") data-quality filter, no simulation/Monte-Carlo weight
reading, and no way to request extra per-object fields beyond a fixed
default list. This is intentional, not an oversight, and matches what
`master` is meant to be: a lean baseline, not a working analysis branch.

## `cms/pipeline-baseline`

**New branch, created by this task.** It points at the exact same saved
version of the project as `feature/hgg-selection-and-output` (see below) —
creating it added no new changes and copied nothing; it is simply a second,
clearer name for a version of the project that already existed. Confirmed:
both branches point at the identical saved version as of this writing.

This is meant to be the starting point for any *new* CMS analysis work
going forward. It carries the shared pipeline capabilities `master` lacks:
optional extra per-object fields, generic yes/no ("boolean") cuts on object
properties, an HLT trigger-requirement filter, a certified-run/"golden
JSON" data-quality filter, simulation-weight reading, and automatic retries
for network read failures. Before this branch existed, knowing that
`feature/hgg-selection-and-output` was secretly "the real CMS starting
point" was something you'd only know by asking someone or by reading the
code closely — this name makes that fact explicit instead.

## `feature/hgg-selection-and-output`

The Higgs-to-two-photons (H→γγ) analysis. As of this writing it points at
the same saved version as `cms/pipeline-baseline` (confirmed above), but the
two will diverge over time: this branch will keep accumulating H→γγ-specific
work (its own selections, its own output plots and reports) while
`cms/pipeline-baseline` is meant to stay a shared, analysis-neutral starting
point that other CMS work can build from without inheriting H→γγ's own
specific choices.

## `analysis/m0m1j0-cms`

The m0m1j0 study (an analysis of the two leading muons plus the leading
light jet). **Checked directly, since this task specifically asked for it
to be verified rather than assumed: yes, this branch does contain the
H→γγ branch's shared pipeline work.** It was created partway along
`feature/hgg-selection-and-output`'s own history (55 saved versions after
`master`, before reaching where `feature/hgg-selection-and-output` is
today) — not directly from `master`. A direct comparison of the two
branches' shared pipeline code (outside each study's own files) shows the
exact same set of capabilities present in both. So this branch is: the
shared pipeline capabilities, *plus* the m0m1j0 study's own script and its
results, layered on top.

## `docs/upstream-divergence-map`

This documentation branch — the one this very page lives on. It holds
`docs/UPSTREAM_DIVERGENCE_MAP.md` (a full inventory of how this fork differs
from the original upstream project, and from its own `master`) and this
page. It carries no pipeline code changes of its own.

## One rule that applies to all of the above

**Nothing in this fork is ever pushed, merged, or filed as a request/issue
on the original upstream project except by Matan's own, separate, deliberate
decision.** No branch listed on this page changes that.
