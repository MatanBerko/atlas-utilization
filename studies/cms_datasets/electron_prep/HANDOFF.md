# HANDOFF - electron_prep

**Status: preparation COMPLETE.** Steps 1-7 are done. Nothing is left running.
The specification, the measurements, the cost estimate, the plots and the
decision sheet are all committed and pushed. The next action is the group's
three/four decisions, then a production prompt — no further measurement is
needed first.

**This branch changes nothing in the pipeline.** `run_dataset_on_file.py`,
`studies/m0m1j0_cms/selection.py` and every delivery builder are byte-identical
to `deliver/all-datasets-bumpnet`
(`git diff origin/deliver/all-datasets-bumpnet -- <those paths>` is empty). No
histograms were produced for delivery. No production was run.

## 1. Repository

* fork (the only push target): `https://github.com/MatanBerko/atlas-utilization`
* branch: **`prep/electron-datasets`**, created from `deliver/all-datasets-bumpnet`
  at **`da140cc`** (confirmed unmoved before branching)
* no pull request was opened anywhere; nothing was pushed, filed or commented
  upstream; upstream was fetched read-only only
* `deliver/all-datasets-bumpnet`, `feature/cms-mc-weights-v2` and
  `investigate/ttbar-count-vs-atlas` were never committed to

## 2. Pinned checkouts and job provenance

Every cluster job ran from a checkout pinned to a pushed commit, left untouched
until its jobs finished.

| path | commit | used for |
|---|---|---|
| `work/electron_prep/pinned/repo` | `af5c07b` | first measurement pass (88 jobs) |
| `work/electron_prep/pinned/repo` | `2614ce8` | final measurement pass (108 jobs) |
| `work/electron_prep/pinned2/repo` | `35a1079`, then `df0663f` | Step 5 yield projection |

A second pinned checkout (`pinned2`) exists so the yield job could be submitted
while the measurement jobs were still running out of `pinned`.

Development happens in `work/electron_prep/dev`. The cluster has no GitHub
credentials, so pushes go through a mirror clone on the Windows machine that
fetches from `dev` over ssh and pushes to the fork.

## 3. Cluster jobs

| PBS id | what | count | outcome |
|---|---|---:|---|
| `5178726[]` | measurement pass 1 (superseded) | 88 | 88/88 OK |
| `5178740[]` | measurement pass 2 (**the one used**) | 108 | 108/108 OK, no failures |
| `5178742` | yield projection (failed on a path bug) | 1 | failed, superseded |
| `5178744` | yield projection (**the one used**) | 1 | OK |

All queue `N`, `#PBS -m n`, `walltime 02:00:00`, `select=1:ncpus=1:mem=8gb`,
`-l io=25`, OMP/OPENBLAS/MKL threads 1, unique `^array_index^` logs on Lustre.

## 4. Where things are

| path | what |
|---|---|
| `work/electron_prep/measurements_v2/` | 108 per-file measurement JSONs (**the ones used**) |
| `work/electron_prep/measurements/` | the superseded first pass, kept for reference |
| `studies/cms_datasets/electron_prep/evidence/` | the aggregated evidence JSONs |
| `studies/cms_datasets/electron_prep/plots/` | the four committed PNGs |
| `logs/electron_prep/` | PBS stdout/stderr |

Nothing was written outside `work/electron_prep/` and the repo. Existing
outputs were read-only throughout (SQLite via the shared helpers, which open
`mode=ro&immutable=1`; the yield funnel works on scratch **copies**).
`/storage/agrp/marybo/` was never touched.

## 5. The documents

| file | what |
|---|---|
| `ELECTRON_MATCHING_SPEC.md` | **Step 1.** Acceptance definition per dataset, every bit quoted from the real branch title, what cannot be established, the priority order, and the 5-dataset closure-test design |
| `DECISIONS_FOR_GROUP.md` | **Step 6.** One page for Shikma and Maryna: the four decisions with the measured numbers and the plot behind each |
| `HANDOFF.md` | this file |

## 6. The scripts

| script | what it does |
|---|---|
| `common.py` | shared helpers; imports the production object selection unchanged. The ONLY re-implementation is `trigobj_best_match_pt`, to take the object id as a parameter instead of the hard-coded muon 13 — and `assert_matcher_agrees_with_production` checks at runtime that it still matches the production function for id 13, so the copy cannot drift |
| `read_trigobj_titles.py` | reads `TrigObj` branch titles from the real files of all 8 (dataset, era) combinations |
| `read_cmssw_bit_definitions.py` | cross-checks those against CMSSW_10_6_26 |
| `find_common_run.py` | finds a run present in all five datasets, for the closure test |
| `measure_per_file.py` | one input file per job: turn-on probes, leg matching, bit census, dR(e,mu), threshold-loss spectrum |
| `aggregate_and_plot.py` | pools the per-file JSONs into Steps 2/3/4 results and the PNGs |
| `decompose_ele27.py` | splits the measured Ele27 efficiency into P(fired) and P(matched given fired) |
| `project_cost_and_yield.py` | Step 5 cost (`--part cost`) and yield projection (`--part yield`) |
| `pbs_measure.sh`, `submit_measurements.sh`, `pbs_yield.sh` | the job wrappers |

## 7. How to re-run anything

```bash
B=/storage/agrp/berkom/atlas-utilization/work/electron_prep
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python
cd $B/pinned/repo && git fetch origin && git checkout --detach <commit>

# the 108 measurement jobs (edit the PLAN block in submit_measurements.sh to
# change the sampling)
REPO_DIR=$B/pinned/repo OUTPUT_DIR=$B/measurements_v2 \
    bash studies/cms_datasets/electron_prep/submit_measurements.sh

# aggregate + plots (login node, ~1 min)
cd $B/dev && PYTHONPATH=. $PY studies/cms_datasets/electron_prep/aggregate_and_plot.py \
    --measurements $B/measurements_v2 \
    --evidence studies/cms_datasets/electron_prep/evidence \
    --plots studies/cms_datasets/electron_prep/plots

# Step 5
PYTHONPATH=. $PY studies/cms_datasets/electron_prep/project_cost_and_yield.py \
    --part cost --out studies/cms_datasets/electron_prep/evidence/step5_cost.json
qsub -v "REPO_DIR=$B/pinned2/repo,OUT_JSON=<path>" \
    -o <log>.out -e <log>.err studies/cms_datasets/electron_prep/pbs_yield.sh
```

## 8. What is NOT done, and is the next step

**Nothing here is a production.** When the group has decided:

1. **The three/four decisions** in `DECISIONS_FOR_GROUP.md`: the SingleElectron
   matched-electron pT threshold; whether DoubleEG needs an extra ~30 GeV
   requirement; electron-muon overlap; and confirming the priority order.
2. **Implement the acceptance** from `ELECTRON_MATCHING_SPEC.md` as a new
   `--population matched` branch for the three electron labels in
   `run_dataset_on_file.py`, with the same "data mode must not change" proof the
   muon side used.
3. **Run the 5-dataset closure test** (design in the spec Section 7, on run
   281707) before any production.
4. **Produce**: 332 files, 332 jobs, roughly 9-27 core-hours.

### Known gaps a production prompt must carry

* **The MuonEG muon leg cannot be trigger-matched** from these files. The spec
  proposes accepting it on the path decision alone. If the group disagrees, the
  only alternatives measured here are "match any trigger muon" (costs ~15% of
  events, no physics justification) or "require bit 1" (costs ~92%).
* **The endcap failed the statistics requirement** for the turn-on (>= 500
  probes per pT bin below 60 GeV) even with 60 SingleMuon files; endcap bins
  hold roughly 350-700. The barrel passes. More SingleMuon files would fix it if
  the endcap number needs to be tighter.
* **No generic SingleElectron production exists**, so its event count (and hence
  its share of the cost) is an estimate scaled from sampled files, and it is
  absent from the yield projection entirely.
* **Run 280016 was not observed in the sampled MuonEG files** (6 per record).
  Not proven absent — if the closure test wants that specific run, scan more
  MuonEG files first.
