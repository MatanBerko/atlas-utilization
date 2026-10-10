# HANDOFF — cms-mc-weights-v3 design round

**Branch:** `design/cms-mc-weights-v3`, pushed to `origin`
(`https://github.com/MatanBerko/atlas-utilization`).
**Branched from:** fork master `db1bd32` ("Prompt 2 complete: full production
of all 390 files and the four-dataset delivery"), confirmed before branching.
**Date:** 2026-10-10.
**Round type:** read-only verification + design document. **No pipeline code
was changed. No MC was produced. No batch job was submitted.**

## What is in this branch

| Commit | Contents |
|---|---|
| `74e5fe7` | The Part C probe script (`probe/probe_mc_records.py`). |
| `964bc5a` | Probe extended to record `run` / L1-prefiring / pileup **values**, not only presence. |
| `8e997e8` | The three local verification checks (A9, D3, D7), the dataset-identity probe, and the Part C evidence. |
| *(final)* | `DESIGN.md`, this `HANDOFF.md`, and the remaining evidence JSONs. |

Layout:

```
studies/cms_mc_weights_v3/
    DESIGN.md                                  <- the deliverable
    HANDOFF.md                                 <- this file
    probe/probe_mc_records.py                  <- Part C, runs on the cluster
    probe/probe_dataset_identity_branches.py   <- D3, runs on the cluster
    probe/check_a9_labels_and_rules.py         <- A9, runs anywhere
    probe/check_d3_sibling_pruning.py          <- D3, runs anywhere
    probe/check_d7_sumw2_roundtrip.py          <- D7, runs anywhere (needs uproot)
    evidence/probe_mc_records.json             <- 13 records, full detail
    evidence/probe_mc_records.txt              <- the same as a readable table
    evidence/dataset_identity_branches.json    <- MC vs data branch scan
    evidence/check_a9_labels_and_rules_out.json
    evidence/check_d3_sibling_pruning_out.json
    evidence/check_d7_sumw2_roundtrip_out.json
```

No file outside `studies/cms_mc_weights_v3/` was added, edited or deleted.

## What was run, where

### On the cluster (Weizmann analysis node)

Reached over `ssh wipp-home` (the campus alias `wipp-campus` timed out;
`wipp-home` goes through the jump host and lands on `wipp-an1`, the analysis
node). Everything ran **interactively under `nice -n 10`**, no PBS, total wall
time well under one hour.

Environment: `/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline`
(python 3.11, uproot 5.6.2, numpy 2.4.6, fsspec-xrootd and XRootD both
importable). Invoked by absolute path as
`$ENV/bin/python` — note there is **no `conda` on the PATH** of the login
shell, and the env has no `bin/activate`, so `conda activate` /
`source .../activate` both fail. Use the absolute interpreter path.

Pinned checkout: `/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_design_20261010/repo`
— a fresh clone of the fork, `git checkout <commit>` at the exact commit each
script was run from. Every script was committed **and pushed** before being
run.

| Run | Commit pinned | Command (abridged) | Output directory |
|---|---|---|---|
| smoke test, 1 record | `74e5fe7` | `probe_mc_records.py --records 37728` | `…/probe_out/` |
| Part C, 13 records | `74e5fe7` | `probe_mc_records.py` (defaults) | `…/probe_out_full/` |
| Part C re-run with scalar values | `964bc5a` | `probe_mc_records.py` (defaults) | `…/probe_out_v2/` ← **authoritative** |
| D3 branch scan | `8e997e8` | `probe_dataset_identity_branches.py` | `…/identity_out/` |

All four output directories are under the **new dated** work directory
`/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_design_20261010/`.
Nothing was written anywhere else — not to `$HOME`, not to `output/`, not to
`work/cms_mc_v2/`. `work/cms_mc_v2/` was listed at top level only (`ls -la`);
nothing in it was opened or modified. `/storage/agrp/marybo/` was never
accessed.

`probe_out_v2/` is the authoritative Part C result and is the copy committed
into `evidence/`. `probe_out/` and `probe_out_full/` are earlier runs of the
same probe at the earlier commit, kept rather than deleted.

### Locally

* `check_a9_labels_and_rules.py`, `check_d3_sibling_pruning.py`,
  `check_d7_sumw2_roundtrip.py` — all three run with no network and no cluster
  access; outputs committed under `evidence/`.
* PR #35's merge into fork master was tested in a **local throwaway branch**
  (`git merge --no-commit --no-ff fa63544`), which produced 13 conflicting
  files / 53 conflict hunks. The merge was aborted, the throwaway branch
  deleted, and `git ls-remote --heads origin` confirmed nothing of it reached
  any remote.

## Remote hygiene

* `origin` → `https://github.com/MatanBerko/atlas-utilization.git` (fetch and
  push). This is the only remote pushed to.
* `upstream` → `https://github.com/Zhavi221/atlas-utilization.git` for fetch;
  **push URL set to `DISABLED`** (`git remote set-url --push upstream DISABLED`),
  done before any fetch. Verified with `git remote -v`.
* Upstream PR heads were fetched read-only into `refs/remotes/upstream-pr/*`.
* **No pull request was opened anywhere.** No issue, comment, review or merge
  on upstream.
* No branch was force-pushed, reset, deleted or rewritten. The old MC branches
  (`feature/cms-mc-weights-v2`, `feature/cms-mc-weights-phase1`,
  `design/cms-mc-weights`, `investigate/cms-mc-normalisation`,
  `feature/cms-mc-weights-and-probe-retry`) were read only.

## Headline results

All verified by running, details and labelling in `DESIGN.md`:

* **All 8 of the lead's readings of PR #35 (A1–A8) are CONFIRMED.** A4 is worse
  than stated: one weightless file costs the *whole merged signature* its
  weights, not just that file's share.
* **PR #35 does not merge cleanly into fork master:** 13 files, 53 hunks.
* **A9:** labels and histogram names agree with upstream #34, two-digit counts
  included; the *acceptance rule* differs (271 count patterns disagree). The
  fork's single-character count parse cannot change a delivered answer, because
  the largest `start + count` requirement over the 186 combinations is 4.
* **Part C, 13 MC records, one file each:** every record is UL16 **postVFP**
  NanoAODv9 (no APV), **no branch is missing on any record**, the
  `TrigObj_filterBits` title is **byte-identical to data** (same sha256) on all
  13, and `sum(genWeight)` equals that file's `Runs.genEventSumw` on all 13
  (≤ 4.4e-8 relative). `run == 1` everywhere. Negative-weight fractions reach
  **24.8%** (TTZ), **21.9%** (TTW), **17.0%** (WZ), **16.3%** (DY NLO).
* **D3:** the fork's current prune leaves **orphan sibling arrays** behind; the
  one-line regex fix is specified and PR #35's own version only fixes `_mcw`.
* **D7:** a weighted TH1D with an explicit `fSumw2` written through uproot
  reads back with `errors() == sqrt(Σ w²)` exactly, negative weights included.
* **D3 (CMS deviation):** CMS NanoAOD carries **no** per-event dataset
  identifier — 1504 branches scanned, the only identity-pattern match was
  `LHEWeight_originalXWGTUP`. The record ID must come from the job argument.

## How to resume

1. `git fetch origin && git checkout design/cms-mc-weights-v3`.
2. Read `studies/cms_mc_weights_v3/DESIGN.md` — in particular **Open
   questions** (drafted, not sent: one list for Yuval, one for Maryna) and
   **Implementation plan for the NEXT round**.
3. Nothing needs cleaning up. No job is running, no production is part-way
   through, no output was overwritten. `qstat -u berkom` was not needed and no
   job was submitted.
4. To re-run any probe: push first, then on the cluster
   ```
   cd /storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_design_20261010/repo
   git fetch origin design/cms-mc-weights-v3 && git checkout <commit>
   nice -n 10 /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python \
       studies/cms_mc_weights_v3/probe/probe_mc_records.py --output-dir <a NEW dir>
   ```
   Use a **new** output directory rather than reusing one.
5. The implementation round's first task is Step 1 of the plan (`--is-mc` in
   `studies/cms_datasets/cluster/run_dataset_on_file.py`) together with the
   data byte-identity regression that proves the data path is untouched. Those
   two belong in the same commit.

## Decisions deliberately left open

* Everything in **Open questions** in `DESIGN.md`. Nothing there was decided
  by this round.
* The **negative/empty MC bin** problem (NLO weights vs BumpNet's need for
  positive bins) is the most likely practical blocker and is Maryna's call.
* The **b-tag WP** stays at `0.2598` on both sides. Unchanged, group decision
  pending.
* **SingleElectron** is stored but not delivered; its offline threshold
  (27 / 30 / 35 GeV) remains undecided and out of scope.
