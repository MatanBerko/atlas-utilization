# Branch layout — a plain-language guide

This page explains what each "branch" in this fork is for, and which one to
use as a starting point for new work. A branch is a named, saved line of
work — think of it as a labelled folder holding one complete version of the
project, so several people can work on different things without treading on
each other.

Written for a reader who does not use git. **Every branch listed here, and
every number, was checked directly against the fork on 2026-10-05 by
listing all branches and measuring each one** — nothing was carried forward
from the previous version of this page. Where a number in the previous
version turned out to be wrong, the correction is called out in bold.

At the time of this audit the fork held **62 branches in total**, i.e. 61
besides the `master` line itself. The five tables below account for all 61:
9 + 5 + 11 + 14 + 22. (A 63rd has since been added:
`feature/exact-jet-labels-z110-aligned-split`, the exact-light-jet-label
work, which is deliberately NOT merged into `master` — Matan's technical
lead verifies it first.)

## Two words you need for the rest of this page

- **"ahead"** = how many saved steps this branch has that `master` does not.
  If a branch is 0 ahead, everything on it is already in `master`.
- **"behind"** = how many saved steps `master` has that this branch does
  not. A large "behind" number just means the branch was last worked on a
  while ago; by itself it is not a problem.

## `master` — the main line, and where new work should start

`master` was moved twice on 5 Oct 2026. The two moves are described in order
below; after the second one it points at the merge commit `49bcb2f`.

### First move on 5 Oct 2026: the combined muon delivery

This first took `master` to **`da140cc`** (1 Oct 2026), the finished combined
DoubleMuon + SingleMuon delivery for BumpNet.

On 2026-10-05 the delivery line of work (`deliver/all-datasets-bumpnet`)
was merged into `master`. This was a **fast-forward**: `master` had no work
of its own that the delivery branch did not already contain, so `master`
simply slid forward to the delivery branch's own latest point. Nothing was
rewritten, nothing was discarded, and no files had to be reconciled by
hand. An undo point was saved first as
`backup/master-pre-deliver-ff-2026-10-05` (pointing at `4f50b99`, what
`master` was beforehand).

### Second merge on 5 Oct 2026: the exact light-jet labels

Later the same day, `feature/exact-jet-labels-z110-aligned-split` was also
merged into `master`. That branch carries four agreed changes: each
light-jet count now gets its own final state (5j, 6j, 7j … instead of
everything above 4 being filed under 4j); the Z-peak cut moves from 115 GeV
to 110 GeV so it lands on a bin edge; the high-mass outlier split is aligned
to the same fixed 10 GeV grid; and the delivery no longer applies a
filled-bin cut, because that one is applied on the BumpNet side during
smoothing. It was validated on the full 209-file production before merging —
the evidence is in
[`studies/cms_datasets/matching/vB_exactlabels/REPORT.md`](../studies/cms_datasets/matching/vB_exactlabels/REPORT.md).
This was a real merge rather than a fast-forward, with an undo point saved
first as `backup/master-pre-exactlabels-merge-2026-10-05` (pointing at
`75e4f37`, what `master` was beforehand).

**All new CMS production should start from `master`, including the electron
datasets** (DoubleEG, MuonEG, SingleElectron). The preparation for those
still sits unmerged on `prep/electron-datasets`, listed in section (c)
below; it should be brought in together with the electron production run
itself, on top of this `master`.

### How far `master` now sits from the original upstream project

This fork started as a copy of `Zhavi221/atlas-utilization` ("upstream").
Measured today: **1,314 files differ** between `master` and upstream's
`master` (`88d7a4b`); `master` carries **262 saved steps upstream does not
have**, and upstream has **46 that `master` does not**. The two lines last
had a point in common at `388b86cf`.

**Correction to the previous version of this page:** it reported "528 files
differ". That figure is out of date — the real number today is 1,314. The
previous page also carried a "7 files conflicted" figure from an older
trial merge against upstream, flagged there as not re-run. It is not
repeated here, because it was not re-measured today either.

This distance is an accepted consequence of the decision taken 2026-09-24 to
make `master` the place CMS work happens, rather than keeping it close to
upstream. It is not a problem to be fixed.

---

## (a) The active data line — now in `master`

This is the work that produced the real data files handed to BumpNet. All
of it is now inside `master`; the branches below are kept as the record of
how it was built, in roughly the order it happened.

| Branch | Latest saved step | Last worked on | In `master`? |
|---|---|---|---|
| `cms/pipeline-baseline` | `f33d8d4` | 2026-09-22 | yes |
| `design/m0m1j0-bumpnet` | `9e58e96` | 2026-09-21 | yes |
| `analysis/m0m1j0-cms` | `040ba67` | 2026-09-23 | yes |
| `survey/cms-coverage` | `e6f6367` | 2026-09-24 | yes |
| `survey/per-dataset-yield` | `4b4b376` | 2026-09-26 | yes |
| `survey/ceiling-yield` | `53218dd` | 2026-09-26 | yes |
| `survey/full-inventory` | `ddb6dc1` | 2026-09-26 | yes |
| `deliver/doublemuon-bumpnet` | `30c19a1` | 2026-09-27 | yes |
| `deliver/all-datasets-bumpnet` | `da140cc` | 2026-10-01 | yes — identical to `master` |

In plain terms, reading down the table: the shared data-reading machinery
was brought up to what CMS needs; a design note worked out how to turn a
study into BumpNet input; the first real study (two muons plus a light jet,
"m0m1j0") was done on it; three surveys measured how many usable histograms
the CMS data could actually yield; and then the real deliveries were built,
first for the DoubleMuon dataset alone and finally for DoubleMuon and
SingleMuon combined. That last branch is now exactly `master`.

## (b) The Monte-Carlo (simulation) line — paused, **do not merge**

These branches carry **unfinished simulation code**. They are paused on
purpose, waiting on a decision from Maryna about the final-state rule.
**None of them should be merged into `master`** — doing so would put
half-finished simulation handling into the line that produces real data
deliveries.

| Branch | Latest saved step | Last worked on | Ahead | Behind |
|---|---|---|---|---|
| `investigate/cms-mc-normalisation` | `1d4ee2a` | 2026-09-30 | 2 | 95 |
| `design/cms-mc-weights` | `3930d88` | 2026-09-30 | 3 | 95 |
| `feature/cms-mc-weights-phase1` | `8684a8c` | 2026-09-30 | 14 | 95 |
| `feature/cms-mc-weights-v2` | `c89d0f0` | 2026-09-30 | 21 | 6 |
| `investigate/ttbar-count-vs-atlas` | `f110fa0` | 2026-10-05 | 33 | 0 |

One sentence each:

- `investigate/cms-mc-normalisation` — asked whether simulated events are
  being scaled to the right size, and found a gap between the CMS and ATLAS
  treatments.
- `design/cms-mc-weights` — the written plan for how simulation weights
  should enter the BumpNet delivery; a design document, no production code.
- `feature/cms-mc-weights-phase1` — a first working attempt: three
  simulation samples processed end to end, plus a diagnosis of why the
  simulation did not match the data (the main cause identified was the
  simpler "LO" versus the more accurate "NLO" treatment of one background).
- `feature/cms-mc-weights-v2` — the second attempt, and the furthest along.
  Its own last saved step says in as many words that simulation production
  is **paused pending Maryna's confirmation on the final-state rule**. Note
  it is only 6 steps behind `master`, so it is the one that would be picked
  up first when simulation work resumes.
- `investigate/ttbar-count-vs-atlas` — the most recently touched branch in
  the whole fork (today). It compares our top-quark-pair counts against
  Maryna's ATLAS numbers. It is **blocked, not finished**: its own notes
  record that the ATLAS reference file cannot be read because of file
  permissions, and that the blocker has moved to a directory this project
  is not allowed to touch. It did establish real differences (trigger ~1%,
  overlap removal ~15%, plus a photon/tau difference nobody had noticed).

## (c) Side work not merged, kept as the record

Real work, finished or deliberately stopped, that was never merged into
`master` and is kept so the reasoning and evidence are not lost.

| Branch | Latest saved step | Last worked on | Ahead | Behind |
|---|---|---|---|---|
| `prep/electron-datasets` | `f30eb01` | 2026-10-04 | 5 | 0 |
| `investigate/bumpnet-rejection` | `ad151e6` | 2026-09-28 | 7 | 85 |
| `feature/generic-field-and-bitmask-cuts` | `28908d1` | 2026-09-24 | 2 | 95 |
| `test/upstream-trigger-cms` | `2526476` | 2026-09-24 | 2 | 146 |
| `docs/upstream-divergence-map` | `2b65ce4` | 2026-09-23 | 3 | 202 |
| `design/hgg-selection` | `16f52a0` | 2026-09-15 | 4 | 202 |
| `study/atlas-hgg-lr-reproduction` | `290ca09` | 2026-09-15 | 10 | 202 |
| `study/lr-toy-study` | `0876937` | 2026-09-15 | 2 | 202 |
| `study/hgg-cms-inventory` | `c1e4da5` | 2026-09-15 | 1 | 202 |
| `analysis/m0m1j0-mumujet` | `f5df667` | 2026-09-14 | 7 | 252 |
| `investigate/m0m1j0-spec` | `47e33fd` | 2026-09-14 | 1 | 252 |

One sentence each:

- **`prep/electron-datasets` — this one is different: it is *planned* to be
  merged later**, together with the electron production run it prepares
  for. It is 0 behind `master`, i.e. fully up to date with it. It carries
  the preparation for the electron datasets (DoubleEG, MuonEG,
  SingleElectron): measurements, a yield projection, a decision sheet and a
  handover note. Do not merge it on its own; merge it when the electron
  production happens.
- `investigate/bumpnet-rejection` — worked out why BumpNet rejected an
  earlier file we sent, settled it against an ATLAS reference file, and
  proposed fixes.
- `feature/generic-field-and-bitmask-cuts` — adds optional,
  switched-off-by-default ways to cut on arbitrary object properties; never
  turned on.
- `test/upstream-trigger-cms` — a throwaway check of whether upstream's
  trigger-matching feature, left switched off, changes anything for CMS. It
  does not.
- `docs/upstream-divergence-map` — a full written inventory of how this
  fork differs from upstream, plus the *first* version of this very page,
  kept there as history rather than deleted.
- `design/hgg-selection` — the design document for the CMS
  Higgs-to-two-photons event selection, with three follow-up physics
  checks.
- `study/atlas-hgg-lr-reproduction` — reproduces an ATLAS statistical
  result for the two-photon channel, including finding and fixing a bug
  where the fit got stuck and overstated the significance.
- `study/lr-toy-study` — a small statistics exercise on simulated toy data,
  underpinning the branch above.
- `study/hgg-cms-inventory` — a read-only inventory of what CMS two-photon
  data and simulation actually exist.
- `analysis/m0m1j0-mumujet` — the first, early version of the two-muon-plus
  -jet study, since superseded by `analysis/m0m1j0-cms` (which *is* in
  `master`).
- `investigate/m0m1j0-spec` — a read-only check of how the histograms for
  that study should be named.

## (d) Early-September branches, kept as the record

These are from the first weeks of the project. They sit far behind `master`
(around 250 steps) and predate essentially all of the current machinery.
They are kept as a record of what was measured, not as something to build
on. If any result here is wanted again, copying the relevant study folder
forward onto current `master` is a cleaner path than merging these branches
as they stand.

> ### ⚠️ One branch here carries a change that must never be merged by accident
>
> **`analysis/btag-score-distribution` (`0472c53`, 2026-09-07)** contains a
> change to the b-jet tagging threshold: **0.2598 → 0.25**, described in its
> own notes as "the project now uses 0.25 ... everywhere". That threshold
> decides which jets count as b-jets, so changing it changes the final
> states of the delivered data. **It must not be merged into `master`
> without an explicit group decision.** Everything currently in `master`,
> and every file delivered so far, uses 0.2598.
>
> (Separately noted for the group, not changed anywhere: 0.2598 is the 2016
> *pre*-VFP medium value, while the delivered Run2016G+H data is
> *post*-VFP, whose corresponding value is 0.2489. That is a question for
> the group, not a bug being fixed here.)

| Branch | Latest saved step | Last worked on | Ahead | Behind |
|---|---|---|---|---|
| `analysis/btag-score-distribution` ⚠️ | `0472c53` | 2026-09-07 | 6 | 254 |
| `analysis/4l-collection-drop-check` | `ac54748` | 2026-09-15 | 23 | 254 |
| `analysis/higgs-4lepton-clean` | `cfab8ba` | 2026-09-10 | 20 | 254 |
| `analysis/higgs-4lepton-zz` | `60de373` | 2026-09-08 | 6 | 254 |
| `analysis/ttbar-btag-truth-crosscheck` | `f380712` | 2026-09-08 | 6 | 254 |
| `analysis/higgs-diphoton-stage0-stats` | `0d5fc60` | 2026-09-07 | 1 | 254 |
| `analysis/higgs-diphoton-stage1-idveto` | `961a95c` | 2026-09-07 | 1 | 254 |
| `analysis/higgs-diphoton-stage2-fullscale` | `2964037` | 2026-09-08 | 3 | 254 |
| `analysis/higgs-diphoton-stage3-resolution` | `e05b375` | 2026-09-08 | 4 | 254 |
| `analysis/higgs-diphoton-stage4-fit` | `4bb88e4` | 2026-09-08 | 5 | 254 |
| `test/cms-mediumscale-fourrecord` | `035f98b` | 2026-09-04 | 8 | 254 |
| `test/cms-bjet-with-histograms` | `d027e09` | 2026-09-04 | 2 | 254 |
| `test/cms-full-pipeline-smallscale` | `94af282` | 2026-09-03 | 1 | 261 |
| `test/cms-zpeak-check` | `5babafe` | 2026-09-02 | 1 | 262 |

One sentence each:

- `analysis/btag-score-distribution` — plots the raw b-tagging score across
  all four CMS records; also carries the threshold change flagged above.
- `analysis/higgs-4lepton-zz`, `analysis/higgs-4lepton-clean`,
  `analysis/4l-collection-drop-check` — the Higgs-to-four-leptons study in
  three stages: first a real Z-peak validation (2,216 candidates), then a
  split-sample test and a mass fit, then a diagnostic chasing a bug where
  object collections were being dropped when files were joined.
- `analysis/ttbar-btag-truth-crosscheck` — checks the b-tagging efficiency
  against simulation truth in top-quark-pair events.
- `analysis/higgs-diphoton-stage0-stats` … `stage4-fit` — the
  Higgs-to-two-photons analysis in five successive stages: counting, photon
  identification and electron veto, a full-scale run over all 133 files (no
  signal found), resolution-matched binning, and finally a
  signal-plus-background fit.
- `test/cms-mediumscale-fourrecord`, `test/cms-bjet-with-histograms`,
  `test/cms-full-pipeline-smallscale`, `test/cms-zpeak-check` — the early
  scaling-up tests: a medium-scale run over four records with Z-peak
  numbers, b-jet tagging writing real histograms, a small full-pipeline
  run, and the very first Z-peak sanity check.

**Correction to the previous version of this page:** it said the three
4-lepton branches "sit 54 commits behind `master`". Measured today they are
**254 behind**, not 54. (The previous figure may well have been right when
it was written; `master` has moved a long way since.)

## (e) Branches fully contained in `master` — nothing of their own left

For each of these, **everything on the branch is already inside `master`**
(0 ahead). They can be read for history; there is nothing on them left to
merge. The nine branches of the active data line in section (a) are also in
this category and are not repeated here.

| Branch | Latest saved step | Last worked on |
|---|---|---|
| `backup/master-pre-deliver-ff-2026-10-05` | `4f50b99` | 2026-09-24 |
| `backup/master-pre-cms-merge-2026-09-24` | `b38f566` | 2026-09-23 |
| `backup/master-pre-merge-2026-09-15` | `9428915` | 2026-09-15 |
| `chore/align-noop-files-with-upstream` | `b38f566` | 2026-09-23 |
| `feature/hgg-selection-and-output` | `f33d8d4` | 2026-09-22 |
| `feature/cms-mc-weights-and-probe-retry` | `3cf6ffd` | 2026-09-16 |
| `feature/cms-object-fields-and-bool-cuts` | `3cedb58` | 2026-09-16 |
| `feature/cms-scalar-event-fields` | `b06ea20` | 2026-09-15 |
| `feature/cms-trigger-requirement` | `132924a` | 2026-09-15 |
| `feature/cms-validated-runs` | `c6cf6ce` | 2026-09-15 |
| `feature/cms-singlemuon-support` | `2eb2ec5` | 2026-09-03 |
| `feature/cms-singleelectron-scope` | `bd051be` | 2026-09-03 |
| `fix/collection-drop-on-concat` | `9428915` | 2026-09-15 |
| `fix/warn-on-missing-bjets-cuts` | `0ae86dc` | 2026-09-08 |
| `fix/cms-bjets-kinematic-cuts` | `e1702e3` | 2026-09-08 |
| `fix/cms-mev-gev-scaling` | `e848f4d` | 2026-09-02 |
| `investigate/cms-trigger-streams` | `bbe2eb2` | 2026-09-03 |
| `merge/sync-into-master` | `8cf737e` | 2026-09-15 |
| `sync/upstream-2026-09b` | `972741b` | 2026-09-15 |
| `sync/upstream-2026-09` | `e99e1d9` | 2026-09-14 |
| `sync/upstream-safe-16` | `236860a` | 2026-09-14 |
| `upstream/bugfix-cherrypicks-pr17` | `38b900c` | 2026-09-03 |

In plain terms: the three `backup/...` branches are undo points saved just
before each of the three times `master` was moved. The `feature/...` and
`fix/...` branches are the individual capabilities and bug fixes that were
built one at a time and then merged in — extra object fields, yes/no cuts
on object properties, the trigger filter, the certified-run filter,
single-muon and single-electron support, a unit-scaling fix, and so on. The
`sync/...`, `merge/...`, `chore/...` and `upstream/bugfix-cherrypicks-pr17`
branches are the housekeeping used to bring upstream's changes in.

Note that `feature/cms-mc-weights-and-probe-retry` belongs in this list and
not in the paused simulation section: its content is already in `master`.
All it added was the *ability to read* simulation weights. The paused,
unfinished work in section (b) is about how to *use* them, which is a
separate thing.

---

## One rule that applies to all of the above

**Nothing in this fork is ever pushed, merged, or filed as a request or an
issue on the original upstream project except by Matan's own, separate,
deliberate decision.** Reading from upstream is fine and is done routinely.
No branch listed on this page changes that, and the merge recorded above
happened entirely within Matan's own fork.
