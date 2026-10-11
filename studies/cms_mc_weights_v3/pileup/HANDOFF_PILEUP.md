# HANDOFF — pileup study of the ≥3-jet data excess

**Branch:** `study/cms-mc-pileup`, from `origin/feature/cms-mc-weights-v3`
(`68ab281`, verified before branching).
**Pinned commit for every cluster job so far:** `5398ac4`
**Work directory:**
`/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_pileup_20261011/`

Diagnostic only. No selection, object definition, threshold, builder default,
registry value or delivered output is changed by anything here.

---

## The question

The MC pilot found, in Z events (dilepton mass 76–106 GeV), data/MC ≈ 1.0 at
0–2 light jets but **1.28 / 1.57 / 2.03** at 3 / 4 / 5+ jets in μμ (ee
similar: 1.17 / 1.52 / 2.11), while b-jet multiplicity stayed flat. Does
pileup explain it?

## Status

| Stage | State |
|---|---|
| A1 — find an official pileup profile | **done — one was found** |
| A2 — MC `Pileup_nTrueInt` profile over all generated events | **submitted** (`5210846/7/8`) |
| A3 — w_PU, mean and range | not started |
| A4 — redraw P1/P2/P3 with and without w_PU | not started |
| B — the fingerprint probe (60 files) | **submitted** (`5210849[1-60]`) |
| B1–B5 plots, verdicts | not started |

## Part A1 — what was found

**An official CMS source exists and is public.**

| | |
|---|---|
| what | CMS LUM POG `correctionlib` pileup weights |
| correction | `Collisions16_UltraLegacy_goldenJSON`, version 0 |
| era of the file | **2016 postVFP, Ultra-Legacy** |
| URL | `https://opendata.cern.ch/eos/opendata/cms/corrections/jsonpog-integration-2016post.tar` |
| member | `POG/LUM/2016postVFP_UL/puWeights.json.gz` |
| tarball sha256 | `113730e8bd3e72ecb9548cb158c8990579022432d202416317828f4bce3eb28a` |
| input | `NumTrueInteractions`, real, range [0, 99), `flow: clamp` |
| variations | `nominal`, `up`, `down` |
| output | event weight |
| derivation | the official golden-JSON-based LUM POG weights; taken as published |

**The approximation, stated plainly:** the file covers the **whole 2016
postVFP period**. Our data is **Run2016 G+H**, a subset of postVFP
(16.393 fb⁻¹). Using it is therefore an approximation of the G+H pileup
profile — the finest granularity published. This is exactly the case the task
brief permits, and it is labelled as such everywhere it is used.

Nothing was hand-typed, invented, or copied from a forum. The file is
downloaded on the cluster and read at run time.
`correctionlib` is not installed in the shared conda environment and this
study may not modify that environment, so `pu_weights.py` reads the JSON
directly: the only node types in it are a `category` on the variation string
and a uniform-width `binning` with `flow: clamp`, which `np.searchsorted`
plus a clip reproduces exactly. The reader refuses to run if the file's
layout is anything other than that.

**Shape of the nominal weight (VERIFIED BY RUNNING, read from the file):**

| nTrueInt | 0 | 5 | 10 | 20 | 30 | 40 | 50 | 70 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| weight | 0.278 | 0.342 | 0.232 | 0.859 | 1.483 | 2.209 | 1.721 | 0.388 |

min 0.00030, max 2.414. The weights are **well above 1 across 30–55
interactions**, i.e. this MC has **too few high-pileup events** relative to
data. That is the direction that could produce extra jets in data, so the
hypothesis is live rather than ruled out at the first step.

## Jobs

| Job ID | What | Output |
|---|---|---|
| `5210846` | A2 MC pileup profile, record 67801 (49 files) | `evidence/mc_pu_profile_67801.json` |
| `5210847` | A2 MC pileup profile, record 35669 (41 files) | `evidence/mc_pu_profile_35669.json` |
| `5210848` | A2 MC pileup profile, record 37728 (8 files) | `evidence/mc_pu_profile_37728.json` |
| `5210849[1-60]` | Part B probe, 60 files | `probe/<kind>_<label>_<record>_<fileindex>.json` |

Requests: profile jobs `mem=4gb, walltime=04:00:00, io=25`; probe array
`mem=6gb, walltime=04:00:00, io=25`. Queue `N`, `#PBS -m n`, logs into
`logs/profile/` and `logs/probe/`, **both created before submission**.

## The Part B file subset

40 data + 20 MC files (`mappings/probe_mapping.txt`, with the full list in
`mappings/probe_mapping_chosen.json`):

| source | files |
|---|---|
| DoubleMuon Run2016G / Run2016H | 10 / 10 |
| DoubleEG Run2016G / Run2016H | 10 / 10 |
| 35669 DY NLO | 10 of 41 |
| 67801 ttbar | 10 of 49 |

Chosen evenly spaced through each era's or record's own file list, so the
subset is reproducible without a stored random seed and is not biased toward
one part of a sample.

**Data de-duplication for this diagnostic:** μμ events are taken from
DoubleMuon files and ee events from DoubleEG files only. DoubleMuon is the
highest-priority dataset so it contributes its **inclusive** acceptance;
DoubleEG contributes its **exclusive** one — the delivery builder's own rule.

## File-count budget

The account is at 108,163 of a 150,000 soft limit; this study must add fewer
than 3,000 files. Expected: 3 profile JSONs + 60 probe JSONs + ~126 PBS logs
+ the pinned checkout (~1,850, archived to 1 at the end) + plots and
evidence ≈ **under 300 once the checkout is archived**. Counted and reported
at the end.

## Where to resume

1. `git fetch origin && git checkout study/cms-mc-pileup`.
2. `ssh wipp-campus '/opt/pbs/bin/qstat -u berkom'` — wait for `5210846/7/8`
   and `5210849[]`.
3. Then A3/A4 (apply the weights to the pilot shards, redraw P1/P2/P3) and
   the B1–B5 merge and plots.
4. Finally: archive the pinned checkout
   `work/cms_mc_v3_pileup_20261011/repo` into one `.tar` beside it, verify
   the entry count, then remove the original. That is the **only** removal
   this study is allowed, and only for the checkout it created.

Read-only throughout: the delivered production
`output/cms_datasets/runs_matched4_full_20261007/`, the pilot
`work/cms_mc_v3_pilot_20261011/`, and every other `output/` and `work/`
directory. `/storage/agrp/marybo/` is never accessed. No ACL is changed.
Jobs write nothing to the real `$HOME`.
