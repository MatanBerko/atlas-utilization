# HANDOFF - ttbar_count_vs_atlas

**Status: Steps 1-10 complete.** The headline result is in `REPORT.md`; the
per-variant tables are in `STEP6_RESULTS.md`. The one thing still outstanding is
Step 8's actual comparison, which needs Maryna's ATLAS ROOT file - the tool is
written and self-tested, see section 8.

Result at ATLAS's own threshold (>= 25 filled bins, >= 100 events), all
VERIFIED BY RUNNING except the ATLAS row:

| | categories | histograms |
|---|---:|---:|
| ATLAS ttbar via PR #31 (reported by Maryna, NOT reproduced here) | 135 | 2,146 |
| CMS ttbar, variant (a) rare4, no trigger | 127 | 2,038 |
| CMS ttbar, variant (b) pr31, no trigger | 127 | 2,038 |
| CMS ttbar, variant (c) pr31_noOR (diagnostic) | 119 | 2,220 |
| our delivered CMS data (muon-triggered) | 55 | 960 |

Everything needed to pick this study up from a cold start: what is pinned where,
which cluster jobs ran, where the outputs live, how to resume, and how to run the
ATLAS comparison the moment Maryna's ROOT file arrives.

## 1. Repository

* fork (the only place anything is pushed): `https://github.com/MatanBerko/atlas-utilization`
* branch: **`investigate/ttbar-count-vs-atlas`**
* created from `feature/cms-mc-weights-v2` (`c89d0f0`), with
  `deliver/all-datasets-bumpnet` (`da140cc`) merged into it. Both heads were
  confirmed before branching. The merge was clean; only one file
  (`studies/cms_datasets/cluster/run_dataset_on_file.py`) was touched by both
  branches and it auto-merged inside the `--is-mc` and rare4 code paths.
* No pull request was opened anywhere, and nothing was pushed, commented or
  filed upstream. Upstream was fetched read-only only.

Read-only reference checkouts on the cluster (never written to, never committed):

| path | what |
|---|---|
| `work/ttbar_count_vs_atlas/pr31_ro` | upstream `refs/pull/31/head`, `81dd40a` |
| `work/ttbar_count_vs_atlas/master_ro` | upstream `master`, `8120fb8` |

## 2. Pinned checkout and job provenance

Cluster jobs are always run from a checkout pinned to a pushed commit and left
untouched until the jobs finish.

| path | commit | used for |
|---|---|---|
| `work/ttbar_count_vs_atlas/pinned/repo` | `cc1a039` | Step 3 proofs, Step 4 pilot |
| `work/ttbar_count_vs_atlas/pinned/repo` | `05062d0` | Step 5 full run |
| `work/ttbar_count_vs_atlas/pinned/repo` | `27a1cea` | Step 6 builds |

`run_dataset_on_file.py` is byte-identical across `cc1a039`, `05062d0` and
`27a1cea` (`git diff <a> <b> -- studies/cms_datasets/cluster/run_dataset_on_file.py`
is empty for each pair), so the Step 3/4 proofs carry over to the Step 5 run
unchanged. Each job also records its own `git_commit` in `job_metadata.json`; every
one of the 49 Step 5 jobs recorded `05062d0`.

Development happens in `work/ttbar_count_vs_atlas/dev` (a normal clone of the
fork). The cluster has no GitHub credentials, so pushes go out through a mirror
clone on the Windows machine that fetches from `dev` over ssh and pushes to the
fork.

## 3. Cluster jobs

| PBS id | what | count |
|---|---|---|
| `5177140[]` | Step 3 proof 1 - data-mode regression on the 4 pilot data files | 4 |
| `5177141` | Step 3 proof 2 - `--population matched --is-mc` on TTTo2L2Nu file 0 | 1 |
| `5177142[]` | Step 4 - notrigger pilot, record 67801 files 0 and 1 | 2 |
| `5177181[]` | Step 5 - full notrigger run, all 49 files of record 67801 | 49 |
| `5177314[]` | Step 6 - build the study histograms, one element per variant | 3 |

All finished, none failed. Step 5: 49/49, longest element 3,223 s. Step 6: 3/3.

All submitted to queue `N`, `#PBS -m n`, `walltime 02:00:00`,
`select=1:ncpus=1:mem=8gb`, `-l io=30`, OMP/OPENBLAS/MKL threads 1, with unique
`^array_index^` log names on Lustre.

## 4. Output locations

Nothing outside these paths is written. Everything under
`output/cms_datasets/` and `work/cms_mc_v2/` is read-only here and was opened
with `mode=ro&immutable=1`.

| path | what |
|---|---|
| `work/ttbar_count_vs_atlas/step3_data_regression/` | re-run data-mode shards for the regression |
| `work/ttbar_count_vs_atlas/step3_mc_identity/` | re-run matched `--is-mc` shards for the identity check |
| `work/ttbar_count_vs_atlas/step4_pilot/` | notrigger pilot, 2 files |
| `work/ttbar_count_vs_atlas/step5_full/` | notrigger full run, 49 files, `job_<0..48>/` |
| `output/cms_datasets/studies/ttbar_count_vs_atlas/<variant>/` | per-variant ROOT files + manifests + build summary + real-ROOT verification |
| `output/cms_datasets/studies/ttbar_count_vs_atlas/plots/` | the PNG plots (also committed under `studies/ttbar_count_vs_atlas/plots/`) |
| `logs/ttbar_count_vs_atlas/` | PBS stdout/stderr |

Each `step5_full/job_<i>/` holds three inclusive shards and a
`job_metadata.json` whose `notrigger_diagnostics` block carries the per-variant
event counters and the genWeight sums:

```
dataset_shard_notrigger_rare4_inclusive.sqlite
dataset_shard_notrigger_pr31_inclusive.sqlite
dataset_shard_notrigger_pr31_noOR_inclusive.sqlite
job_metadata.json
```

## 5. The three variants

All three are **raw, unweighted** counts. `genWeight` is read and summed for
information only and is never applied to a histogram, because the ATLAS numbers
being compared against are raw too.

| variant | final-state rule | overlap removal |
|---|---|---|
| **(a) `rare4`** | our delivered rule: `e + mu + b > 4` rejected; all light jets kept; `>= 5` light jets labelled `4j` | on (dR < 0.4) |
| **(b) `pr31`** | as (a), but events with `>= 5` light jets are **dropped**, reproducing PR #31's `_is_valid_fs` | on |
| **(c) `pr31_noOR`** | as (b), without the jet-lepton overlap removal. **Diagnostic only** | off |

`--population notrigger` is refused unless `--is-mc` is also given. Data mode and
`--population matched` are unchanged; this was proved, not assumed (Section 7).

## 6. How to resume / re-run

```bash
# 0. the pinned checkout (never edit it in place)
B=/storage/agrp/berkom/atlas-utilization/work/ttbar_count_vs_atlas
cd $B/pinned/repo && git fetch origin && git checkout --detach <commit>

# 1. full notrigger run (49 jobs)
REPO_DIR=$B/pinned/repo bash studies/ttbar_count_vs_atlas/submit_step5.sh 49

# 2. which array elements are missing
ls -d $B/step5_full/job_*/job_metadata.json | wc -l    # expect 49
# resubmit a single missing index i:
qsub -J "i-i" -v "REPO_DIR=$B/pinned/repo,RECORD_ID=67801,DATASET_LABEL=DoubleMuon,OUTPUT_BASE=$B/step5_full" \
     -o "/storage/agrp/berkom/atlas-utilization/logs/ttbar_count_vs_atlas/step5_^array_index^.out" \
     -e "/storage/agrp/berkom/atlas-utilization/logs/ttbar_count_vs_atlas/step5_^array_index^.err" \
     studies/ttbar_count_vs_atlas/pbs_notrigger.sh

# 3. build the study histograms (one array element per variant)
OUT=/storage/agrp/berkom/atlas-utilization/output/cms_datasets/studies/ttbar_count_vs_atlas
qsub -J 0-2 -v "REPO_DIR=$B/pinned/repo,JOBS_DIR=$B/step5_full,OUT_BASE=$OUT,EXPECTED_N_FILES=49" \
     -o "/storage/agrp/berkom/atlas-utilization/logs/ttbar_count_vs_atlas/build_^array_index^.out" \
     -e "/storage/agrp/berkom/atlas-utilization/logs/ttbar_count_vs_atlas/build_^array_index^.err" \
     studies/ttbar_count_vs_atlas/pbs_build_histograms.sh

# 4. real-ROOT readback of ALL 18 written files (CVMFS LCG view, not the conda
#    env). The wrapper sources the view itself and loops over all 9 pairs.
REPO_DIR=$B/dev bash studies/ttbar_count_vs_atlas/verify_all_with_real_root.sh $OUT

# 5. the cross-variant results table (writes STEP6_RESULTS.md)
python studies/ttbar_count_vs_atlas/step6_summary.py --study-dir $OUT \
    --cms-delivery-root studies/cms_datasets/deliver/committed/muon_combined_rare4/muon_combined_matched_rare4_bumpnet_min26bins.root \
    --out-md studies/ttbar_count_vs_atlas/STEP6_RESULTS.md \
    --out-json studies/ttbar_count_vs_atlas/evidence/step6_summary.json

# 6. the plots
python studies/ttbar_count_vs_atlas/make_plots.py --study-dir $OUT \
    --cms-delivery-root studies/cms_datasets/deliver/committed/muon_combined_rare4/muon_combined_matched_rare4_bumpnet_min26bins.root \
    --out-dir $OUT/plots
```

## 7. Re-running the two "nothing was broken" proofs

Both must pass before any change to `run_dataset_on_file.py` is trusted.

```bash
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python

# data mode unchanged -- 4 pilot data files, all 4 shard types, 32 comparisons
$PY studies/ttbar_count_vs_atlas/step3_data_regression.py \
    --new-base $B/step3_data_regression --out <report.json>

# matched --is-mc unchanged -- 1 TTTo2L2Nu file against the paused MC v2 run
$PY studies/ttbar_count_vs_atlas/step3_mc_identity.py \
    --new-dir $B/step3_mc_identity/DoubleMuon_job_0 \
    --old-dir /storage/agrp/berkom/atlas-utilization/work/cms_mc_v2/67801/DoubleMuon/job_0 \
    --out <report.json>
```

Both read their baselines read-only. **The paused MC v2 production under
`work/cms_mc_v2/` was not touched, restarted or modified in any way.**

## 8. Running Step 8 when Maryna's ATLAS ROOT file arrives

This is the one remaining piece, and it needs nothing but the file.

```bash
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python
OUT=/storage/agrp/berkom/atlas-utilization/output/cms_datasets/studies/ttbar_count_vs_atlas

$PY studies/ttbar_count_vs_atlas/compare_with_atlas.py \
    --atlas /path/to/maryna_atlas_bumpnet.root \
    --cms   $OUT/pr31/ttbar_notrigger_pr31_ge25bins.root \
    --out-json $OUT/atlas_vs_cms_pr31.json \
    --out-md   $OUT/atlas_vs_cms_pr31.md
```

Run it once per variant (`rare4`, `pr31`, `pr31_noOR`) and once against the
delivered CMS **data** file, by changing `--cms`. **Variant (b) `pr31` is the
like-for-like comparison** - it reproduces PR #31's `>= 5 light jets` behaviour,
which is the rule the ATLAS numbers were produced under.

What it does: strips our `ROI_` prefix and `_width_<N>` suffix, strips the
trailing `x` from each final-state token, and fills in the object types ATLAS
omits when their count is zero - so ATLAS's `mass_e0m0_cat_1e_2m_3j_1b` and our
`ROI_mass_e0m0_cat_1ex_2mx_3jx_0gx_0tx_1bx_width_10` both normalise to the
category `1e_2m_3j_0g_0t_1b`. It prints and writes the category and histogram
lists split into **both / ATLAS only / CMS only**, with per-category histogram
counts.

Self-test (no ATLAS file needed; both checks currently pass):

```bash
$PY studies/ttbar_count_vs_atlas/compare_with_atlas.py --self-test \
    --cms studies/cms_datasets/deliver/committed/muon_combined_rare4/muon_combined_matched_rare4_bumpnet_min26bins.root \
    --out-json <report.json>
```

Check 1 compares our delivered file against itself (960/960 matched, 0 unmatched).
Check 2 builds a synthetic ATLAS-style file by re-spelling 12 of our own names in
the ATLAS convention and adding 2 ATLAS-only categories, then confirms all 12 are
matched and exactly the 2 are reported as ATLAS-only.

If the ATLAS file turns out to use a naming convention neither branch handles,
the only thing to change is `parse_name`/`strip_root_key` in
`compare_with_atlas.py`; nothing else in the study depends on the spelling.

## 8b. What each output file is

Per variant, under `output/cms_datasets/studies/ttbar_count_vs_atlas/<variant>/`:

| file | what |
|---|---|
| `ttbar_notrigger_<v>_ge25bins.root` | histograms with **>= 25** filled bins and >= 100 entries (ATLAS's wording) |
| `ttbar_notrigger_<v>_min26bins.root` | **> 25** filled bins (what our delivery uses) |
| `ttbar_notrigger_<v>_min31bins.root` | **> 30** filled bins |
| `..._cropped.root` | the same, cropped to each histogram's first..last filled bin |
| `manifest_..._<tag>.json` | per-histogram name, combination, category, entries, filled bins, mass range |
| `build_summary_<v>.json` | event counts, the funnel, the lepton-content breakdown |
| `real_root_verify_<tag>.json` | the real-PyROOT readback result for that pair |

All 18 ROOT files were read back with real PyROOT 6.40.02 and all 9 pairs PASS.

## 9. Things deliberately NOT done

* No upstream action of any kind: no PR, issue, comment, review or push.
  Whether anything goes upstream is Matan's decision.
* No pull request on the fork either.
* The paused MC v2 production (`work/cms_mc_v2/`) was not restarted or touched.
* `feature/cms-mc-weights-v2` and `deliver/all-datasets-bumpnet` were only read
  from and merged from; neither was committed to.
* No delivered product changed: object definitions, b-tag threshold, overlap
  removal, binning, post-processing, BumpNet thresholds and the final-state rules
  are all exactly as delivered. Variants (b) and (c) are diagnostics only and are
  written to a separate study directory.
* No MC weighting, cross sections, pileup or scale factors; no other MC sample;
  no electron datasets, taus or photons; no BumpNet run and no excess
  interpretation.
