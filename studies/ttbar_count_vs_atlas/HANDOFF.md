# HANDOFF - ttbar_count_vs_atlas

**Status: Steps 1-10 complete. Step 8 is BLOCKED on a file permission.** The
headline result is in `REPORT.md`; the per-variant tables are in
`STEP6_RESULTS.md`. The one thing still outstanding is Step 8's actual
comparison, which needs Maryna's ATLAS ROOT file - the tool is written and
self-tested (section 8), but as of 2026-10-04 that file is still **not
readable** - re-checked twice that day, see section 8c for the exact diagnosis
and the exact fix needed.

A second, separate question *was* answered without the ROOT file: **why Maryna's
and Ariel's own ATLAS runs disagree** (135 / 132 / 129 final states). Her run
logs and configs are world-readable even though the histogram files are not. The
answer is in `COMPARISON_WITH_ATLAS.md` section 4; the headline is that the
trigger is a ~1% effect, overlap removal is a ~15% effect, and there is a third,
previously unnoticed difference (photons and taus are uncapped in the 3 October
runs and forced to zero in all others) that makes the 135-vs-129 comparison
confounded.

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

## 8c. BLOCKED 2026-10-04: the ATLAS ROOT file is still not readable

Step 8 was attempted on 2026-10-04 and could not start. The blocker is a single
directory permission bit, not a missing file.

### What was checked, by running

Every component of the path was stat-ed as user `berkom` (groups: `watlas`):

| path component | mode | owner:group | we can read |
|---|---|---|---|
| `/storage/agrp/marybo` | `drwxr-xr-x` | `marybo:watlas` | yes |
| `.../DDP` | `drwxr-xr-x` | `marybo:watlas` | yes |
| `.../BumpNet4AtlasOpenData` | `drwxr-xr-x` | `marybo:watlas` | yes |
| `.../Test_master_atlas-utilization` | `drwxr-xr-x` | `marybo:watlas` | yes |
| `.../data` | `drwxr-xr-x` | `marybo:watlas` | yes |
| `.../atlas_mc_UnlimetedJets_test_ttbar_mc_20261003_210612` | `drwxr-xr-x` | `marybo:watlas` | yes |
| `.../histograms` | **`drwx------`** | `marybo:watlas` | **NO** |

So the run directory is world-readable, but the `histograms/` subdirectory inside
it is owner-only. `getfacl` on that directory shows `group::---` and
`other::---` with no POSIX ACL entries, so this is plain mode bits, not an ACL.

Because that directory is not even traversable (no `x` bit for group or other),
the two ROOT files inside cannot be stat-ed, let alone opened:

* `atlas_opendata_bumpnet.root` - the main post-processed file (Step 2/3/4 input)
* `atlas_btag_ttbar_test_bumpnet_nopostproc.root` - the pre-post-processing file

Both are confirmed to exist and to have been written successfully, from her own
world-readable `logs/pipeline.out`, copied into `atlas_input/run_logs/`.

The sample list is blocked separately, at file level rather than directory level:

| path | mode | we can read |
|---|---|---|
| `.../atlas-utilization/metadata_ttbar_cache.json` | `-rw-------` | **NO** |

Its parent directory is world-readable; only the file's own bits block us. It is
**not** recoverable through git: her checkout is on branch
`feature/overlap-removal` at `ba57abc`, and `git show
HEAD:metadata_ttbar_cache.json` reports "exists on disk, but not in HEAD" - it is
an untracked runtime cache. (Read with `git -C <her checkout>
--no-optional-locks -c safe.directory=<her checkout> ...`; her repository was
never written to.)

### Confirmed: there is no readable copy anywhere else

* `find /storage/agrp -maxdepth 8 -name atlas_opendata_bumpnet.root -readable`
  returns **nothing**.
* `find /storage/agrp/marybo -name "*.root" -readable -newermt 2026-10-03`
  returns **nothing**.
* The only readable `*ttbar*.root` files in her area are two ~130-byte
  FastFrames test fixtures, unrelated to BumpNet.
* The `*_nopostproc.root` files that *are* readable belong to **other** runs
  (`up4j_histograms_v2`, `up4j_histograms_minEvt10`, `maxTot4_histograms`) and
  are data or other MC, not this ttbar MC run. They are not substitutes.

### The exact fix needed

Nothing in `/storage/agrp/marybo/` may be modified by us (strictly read-only for
this study), so this has to be done by Maryna. `berkom` and `marybo` share the
group `watlas`, so **group** read is the minimal change:

```bash
R=/storage/agrp/marybo/DDP/BumpNet4AtlasOpenData/Test_master_atlas-utilization
H=$R/data/atlas_mc_UnlimetedJets_test_ttbar_mc_20261003_210612/histograms
chmod g+rx "$H"
chmod g+r  "$H"/atlas_opendata_bumpnet.root
chmod g+r  "$H"/atlas_btag_ttbar_test_bumpnet_nopostproc.root
chmod g+r  "$R"/atlas-utilization/metadata_ttbar_cache.json
```

The `g+rx` on the directory is the essential one: without it the files inside are
unreachable regardless of their own bits. The last line is optional - it only
decides whether the sample composition (Step 1) can be reported as VERIFIED
rather than unavailable.

### What Steps 0-2 could still establish without the file

From her **world-readable** `logs/config.yaml` and `logs/pipeline.out`, both
already copied into `work/ttbar_count_vs_atlas/atlas_input/run_logs/`. These are
VERIFIED BY READING those two files; they are not measurements of the ROOT file.

* `pipeline.out` states "Grouped 8052 signatures into 2684 unique histogram
  signatures", "Applied global tail display ranges to 2684 merged histogram(s)"
  and "Wrote 2684 histograms to ...nopostproc.root". This **corroborates
  Maryna's 2,684 total**, but it is her log, not our measurement. The 2,161 and
  2,146 numbers and the 135 final states are bin-cut and entry-cut quantities
  that exist only inside the ROOT file, and remain UNVERIFIED.
* Binning is **identical to ours**: `bin_width_gev: 10.0`, `max_mass_cutoff:
  10000.0` GeV, masses in **GeV**. Ours is fixed 10 GeV bins over 0-10,000 GeV
  (1,000 bins), also GeV. There is no binning difference to explain any gap.
* Her per-type caps are `electrons/muons/jets/bjets: {min: 0, max: 4}` - four
  *independent* caps, with **no** combined `electrons + muons + bjets <= 4`
  rule. This re-confirms `ATLAS_PROVENANCE.md`.
* `min_events_per_fs: 10` (ours 100), `z_peak_cutoff: 110.0` GeV (ours 115),
  `trigger_config.enabled: false`, `parse_mc: true`, `max_files_to_process: 40`,
  `DL1d: 2.51`.
* `metadata_cache_path` points at the unreadable `metadata_ttbar_cache.json`,
  which is why Step 1 cannot be answered: the DSID list, the physics names and
  the number of events processed are all inside it. **Whether the ATLAS ttbar
  sample is dilepton-only or also includes semileptonic (one-lepton) decays is
  therefore UNVERIFIED and unavailable.**

### Resuming

The moment the `chmod` above is done, resume at Step 0 with no other change:
copy the two ROOT files and the JSON into `work/ttbar_count_vs_atlas/atlas_input/`,
recording `sha256` of source and copy, then run the Step 8 command in section 8
above once per variant, with `pr31_noOR` as the main comparison. Nothing else in
the study needs to be re-run.

## 8d. Second re-check 2026-10-04 (evening): still blocked, and it is every run

Re-checked after Maryna reported having opened the folder. **It is still
`drwx------`**, and its own mtime is unchanged at 2026-10-03 21:29, so it was not
in fact re-opened. `getfacl` shows `group::---` / `other::---` with no ACL.

New facts from this pass (all **RAN**):

* The block is **not** specific to one run: all **49** run directories under her
  `data/` have `histograms/` set to `drwx------`. There is no readable
  `atlas_opendata_bumpnet.root` anywhere under `/storage/agrp`.
* `metadata_ttbar_cache.json` is still `-rw-------` and is still untracked in
  git, so the sample composition stays UNVERIFIED.
* Her checkout `HEAD` moved to `747b5d5` (4 Oct 18:25, "Remove NumTrkPt500 from
  Jets schema - mu-jet falls back to dR-only"). The final-state logic
  (`im_calculator.py`, `event_selection.py`) is byte-identical to `ba57abc`, and
  `im_calculator.py` is unchanged since 9 September.

What *is* now readable and was harvested instead: `logs/config.yaml`,
`logs/pipeline.out` and `logs/submit_mc.sh` from **49** of her run directories,
copied to `atlas_input/other_runs/` with sha256 of source and copy in
`other_runs/CHECKSUMS.tsv` (134 files, **0 mismatches**), summarised into
`atlas_input/atlas_runs_survey.json` by
`studies/ttbar_count_vs_atlas/extract_runs.py`. Only `data/` was examined;
nothing in `/storage/agrp/marybo/` was written, and her git checkout was read
with `--no-optional-locks -c safe.directory=...` only.

Confirmed **by reading her code** (previously only inferred from her config):
`_is_valid_fs` in `services/calculations/im_calculator.py` limits the number of
object **types** to 4 and each type's count to 4, with **no rule on the sum** -
so `4e_4m_4j_4b` (16 objects) is valid for her and rejected by PR #31. A grep of
her checkout finds no sum-based rule anywhere.

See `COMPARISON_WITH_ATLAS.md` for the full ATLAS-run survey and the
"Why the ATLAS runs differ" analysis.

