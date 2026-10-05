# Handoff note: exact-jet-labels task, full production run

Written immediately before submitting the 209 production jobs, so the work
can be resumed cleanly in a new session if this one is interrupted. This is
a snapshot at submission time, not a final result. The final results go in
`REPORT.md` in this same directory.

## What this production run is

Version B (rare4) of the combined DoubleMuon + SingleMuon BumpNet delivery,
re-produced with three changes the group decided:

- **B1** each light-jet multiplicity gets its own final-state label
  (5j, 6j, 7j, ...) instead of everything above 4 being filed under 4j;
- **B2** the Z-peak cut moves from 115 GeV to 110 GeV (upstream `8120fb8`,
  upstream PR #27), so it lands on a 10 GeV bin edge;
- **B3** the outlier split uses bin edges aligned to the fixed 10 GeV grid
  starting at 0 (same upstream commit);
- **B4** the delivery applies NO filled-bin cut; that cut is applied by
  Maryna on the BumpNet side during smoothing. One histogram set, not two.

## Pinned commit and checkouts (Hard Rule 7)

- Branch: `feature/exact-jet-labels-z110-aligned-split`, Matan's fork
  (`https://github.com/MatanBerko/atlas-utilization`). Never pushed to
  upstream.
- **Pinned commit for this production run: `2666684`**
  (`26666844debb374bf3872831320a79a6c8d7ea22`) — the commit that carries
  B1/B2/B4 and the tests. Later commits on the branch only add validation
  and reporting scripts; the executable driver
  `studies/cms_datasets/cluster/run_dataset_on_file.py` has not changed
  since `2666684`.
- **Pinned production checkout** (used ONLY by these 209 jobs; do not modify
  it or check anything else out into it until every job, including any
  retries, has finished):
  `/storage/agrp/berkom/atlas-utilization/checkouts/2666684/repo`
  (detached HEAD at `2666684`, clean working tree, confirmed).
- **Separate analysis checkout**, for validation/reporting only — use this
  one, never the pinned one:
  `/storage/agrp/berkom/atlas-utilization/checkouts/analysis_944afe5/repo`
  (move it to any later commit freely with `git fetch && git checkout --detach <hash>`).
- Conda env for everything:
  `/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python`

## Output locations (all NEW directories; nothing existing is touched)

- Per-job outputs:
  `/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_vB_exactlabels_20261005/DoubleMuon/job_<N>/`
  (N = 0..56) and `.../SingleMuon/job_<N>/` (N = 0..151). Each holds
  `dataset_shard_inclusive.sqlite`, `dataset_shard_exclusive.sqlite`, the
  `top4`, `nonjet4` and `rare4` inclusive/exclusive shards, and
  `job_metadata.json`. Only the **rare4** shards are delivered.
- Job-index maps: COPIED (not symlinked) from `runs_matched/` into
  `.../runs_matched_vB_exactlabels_20261005/DoubleMuon_index.json` (57
  entries, verified) and `SingleMuon_index.json` (152 entries, verified).
  The originals under `runs_matched/` were read only, never modified.
- PBS array scripts:
  `.../runs_matched_vB_exactlabels_20261005/run_vB_exactlabels_array_DoubleMuon.sh`
  and `..._SingleMuon.sh`
- PBS logs: `.../runs_matched_vB_exactlabels_20261005/logs/DoubleMuon/out.<N>.log`
  and `err.<N>.log`, same pattern under `logs/SingleMuon/`.
- Delivery output directory (created empty, ready):
  `/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_vB_exactlabels_20261005/`
- Pilot run (already complete, Step 3):
  `.../output/cms_datasets/vB_exactlabels_pilot/`, including
  `step3_validation.json`, a pilot delivery under `delivery_pilot/`, and a
  default-flags control build under `delivery_pilot_defaultflags/`.

## PBS job IDs

| Job ID | Dataset | Array indices | Status when this note was written |
|---|---|---|---|
| `5184640[].pbs` | DoubleMuon | 0-56 (57 jobs) | SUBMITTED 2026-10-05 ~21:25 local |
| `5184641[].pbs` | SingleMuon | 0-151 (152 jobs) | SUBMITTED 2026-10-05 ~21:25 local |

Both were submitted to queue `N`, which routes to `shortE`. Confirmed
before submitting that both per-job output directories were still
completely empty.

The exact submission commands used (run from `wipp-home`, which lands on
`wipp-an1`):

```
P=/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_vB_exactlabels_20261005

/opt/pbs/bin/qsub -J 0-56 -N vBexact_DM \
  -o "$P/logs/DoubleMuon/out.^array_index^.log" \
  -e "$P/logs/DoubleMuon/err.^array_index^.log" \
  "$P/run_vB_exactlabels_array_DoubleMuon.sh"

/opt/pbs/bin/qsub -J 0-151 -N vBexact_SM \
  -o "$P/logs/SingleMuon/out.^array_index^.log" \
  -e "$P/logs/SingleMuon/err.^array_index^.log" \
  "$P/run_vB_exactlabels_array_SingleMuon.sh"
```

Each job asks for `-l mem=8gb`, `-l io=25`, `walltime=01:30:00`, queue `N`,
`#PBS -m n` (no mail). On the pilot files the new code ran in 42-500 s per
file, well inside that walltime; the 1 Oct run of the same files took
121-1357 s, also inside it.

## How to check job status (read-only, safe any time)

```
ssh wipp-home '/opt/pbs/bin/qstat -t "5184640[]" "5184641[]"'
```
Note the `[]` — without it PBS reports "Unknown Job Id" for an array job.
A status of `R` is running, `Q` queued, `X` finished (exited). When no
subjob is left in `Q`, `R` or `H`, the run is done.

Count finished outputs:
```
ssh wipp-home 'P=/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_vB_exactlabels_20261005
 echo "DoubleMuon: $(ls -d $P/DoubleMuon/job_*/job_metadata.json 2>/dev/null | wc -l) / 57"
 echo "SingleMuon: $(ls -d $P/SingleMuon/job_*/job_metadata.json 2>/dev/null | wc -l) / 152"'
```

A line like `Plugin No such file or directory loading sec.protocol
libXrdSeckrb5-5.so` in an `err.<N>.log` is harmless, pre-existing XRootD
noise — it appears identically in the 1 Oct logs. Only a Python traceback
counts as a failure.

## Exactly how to resume

**Step 1 — wait for every subjob to reach a terminal state** using the
`qstat` command above.

**Step 2 — verify every job succeeded exactly once.** For each dataset,
check every array index (0..56 DoubleMuon, 0..151 SingleMuon) has a
`job_metadata.json` whose `git_commit` starts with `2666684`, and no Python
traceback in its `err.<N>.log`. Any index missing or failed: **resubmit ONLY
that index**, and into its own NEW output directory (never overwrite a
partial one). E.g. for DoubleMuon index 12:

```
ssh wipp-home 'P=/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_vB_exactlabels_20261005
 /opt/pbs/bin/qsub -J 12-12 -N vBexact_DM_retry \
   -o "$P/logs/DoubleMuon/out.^array_index^.log" \
   -e "$P/logs/DoubleMuon/err.^array_index^.log" \
   "$P/run_vB_exactlabels_array_DoubleMuon.sh"'
```
(swap in the SingleMuon script and paths for SingleMuon.) Allow up to two
retry rounds. If anything still fails after that, STOP, record it here, and
do not deliver a partial dataset.

**Step 3 — run the full-scale identity checks** (Step 3 checks (a) and (b)
at production scale, against the 1 Oct rare4 production, read-only):

```
ssh wipp-home 'cd /storage/agrp/berkom/atlas-utilization/checkouts/analysis_944afe5/repo
 git fetch -q origin && git checkout -q --detach origin/feature/exact-jet-labels-z110-aligned-split
 nice -n 10 /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python \
   studies/cms_datasets/matching/vB_exactlabels/scripts/vB_check_step4.py'
```

**Step 4 — build the delivery** (B4: one histogram set, no filled-bin cut):

```
ssh wipp-home 'cd /storage/agrp/berkom/atlas-utilization/checkouts/analysis_944afe5/repo
 R=/storage/agrp/berkom/atlas-utilization/output/cms_datasets
 nice -n 10 /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python \
   studies/cms_datasets/deliver/build_muon_combined_delivery.py \
   --version rare4 --no-filled-bin-cut \
   --runs-matched-dir "$R/runs_matched_vB_exactlabels_20261005" \
   --out-dir "$R/deliver/muon_combined_vB_exactlabels_20261005" \
   --out-prefix muon_combined_matched_vB_exactlabels'
```
This writes `muon_combined_matched_vB_exactlabels_bumpnet.root` (uncropped),
`..._cropped.root` (**the file for BumpNet**), a manifest, a build summary
and a `README.txt`. It refuses to overwrite an existing ROOT file.

**Step 5 — make the five report plots:**

```
ssh wipp-home 'cd /storage/agrp/berkom/atlas-utilization/checkouts/analysis_944afe5/repo
 R=/storage/agrp/berkom/atlas-utilization/output/cms_datasets
 nice -n 10 /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python \
   studies/cms_datasets/matching/vB_exactlabels/scripts/vB_make_report_plots.py \
   --old-root "$R/deliver/muon_combined_rare4/muon_combined_matched_rare4_bumpnet_min26bins.root" \
   --new-root "$R/deliver/muon_combined_vB_exactlabels_20261005/muon_combined_matched_vB_exactlabels_bumpnet.root" \
   --runs-dir "$R/runs_matched_vB_exactlabels_20261005" \
   --out-dir "$R/deliver/muon_combined_vB_exactlabels_20261005/plots"'
```
Then copy the PNGs into `studies/cms_datasets/matching/vB_exactlabels/plots/`
in the repo and commit them.

**Step 6 — write `REPORT.md`** in this directory per the task spec, and push.

## What is already done and validated (do not repeat)

- **Part A** — `master` fast-forwarded to the delivery work and pushed
  (`4f50b99` -> `da140cc`), undo point `backup/master-pre-deliver-ff-2026-10-05`
  at `4f50b99`; then `docs/BRANCH_LAYOUT.md` rewritten from a fresh audit of
  all 62 branches (`f3d1d9b`).
- **Step 2 (B1-B4)** — implemented and committed at `2666684`, including
  `studies/cms_datasets/tests/test_exact_jet_labels.py` (all checks pass),
  the cherry-pick of upstream `8120fb8` (`9fd4bbc`), and the study-local
  `Z_PEAK_CUTOFF` 115 -> 110.
- **Step 3 (pilot validation)** — complete and PASSED: 103 checks, 0
  failures, on the same 4 pilot files the rare4 task used. Full output is
  committed at `evidence/step3_pilot_validation_output.txt`; machine-readable
  detail at `.../vB_exactlabels_pilot/step3_validation.json`. Headlines:
  selection byte-identical file by file; event counts conserved; all 870/697/
  516/402/225/209 `<=3`-light-jet raw arrays identical; every
  post-processing difference proven to be a move of the Z cut, the peak
  boundary or the outlier split and nothing else, with every moved split
  landing on a 10 GeV edge.
- **Pilot delivery build** — the B4 path runs end to end: 347 histograms, no
  bin cut, of which 277 have `>=25` filled bins; 129 histograms excluded by
  the unchanged per-histogram `>=100`-entries rule.
- **Default-behaviour control** — the same builder WITHOUT
  `--no-filled-bin-cut` still writes the four old files with the old key
  names and the same counts (230 min31bins / 273 min26bins), confirming old
  invocations are unaffected.
