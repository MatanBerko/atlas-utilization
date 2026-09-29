# Handoff note: top-4 task, full production run in progress

Written mid-task so work can resume cleanly after a break. This is a
snapshot at the time of writing, not a final result.

## PBS job IDs (cluster: wipp-an1, queue N -> routed to shortE)

| Job ID | Dataset | Array indices | Status when this note was written |
|---|---|---|---|
| `5158163[].pbs` | DoubleMuon | 0-1 | **COMPLETED, both succeeded** (exit 0, exit 0) -- this was the initial mechanics test |
| `5158165[].pbs` | DoubleMuon | 2-56 | IN PROGRESS -- ~19-22 finished, ~31 running, ~4 queued at last check |
| `5158166[].pbs` | SingleMuon | 0-151 | IN PROGRESS -- mostly still queued at last check (DoubleMuon jobs got the concurrent slots first) |

Check current status any time with (read-only, safe to run anytime):
```
ssh wipp-home '/opt/pbs/bin/qstat -t "5158165[].pbs" "5158166[].pbs"'
```
No failures had been observed in any completed subjob as of this note.

## Pinned commit and checkout (Hard Rule 6)

- Branch: `deliver/all-datasets-bumpnet`, Matan's fork
  (`https://github.com/MatanBerko/atlas-utilization`).
- **Pinned commit for this production run: `521c31e`** (contains the
  top-4 implementation from Step 1, commit `db2f5c0`, plus Step 2/3
  evidence-only commits on top -- the executable code
  `studies/cms_datasets/cluster/run_dataset_on_file.py` has not changed
  since `db2f5c0`).
- **Pinned checkout** (used ONLY by these 209 jobs, untouched until every
  job including retries has finished):
  `/storage/agrp/berkom/atlas-utilization/work/matched_top4_production_pinned/repo`
  (detached HEAD at `521c31e`).
- Do NOT modify this checkout, or check out anything else into it, until
  every job (including retries) has finished. Reporting/analysis work
  (Steps 4-6 below) should use a **different** checkout or just read the
  job outputs directly -- it must not touch this pinned one.

## Output locations

- Per-job outputs: `/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched/DoubleMuon/job_<N>/`
  and `.../runs_matched/SingleMuon/job_<N>/`, each containing
  `dataset_shard_inclusive.sqlite`, `dataset_shard_exclusive.sqlite`,
  `dataset_shard_top4_inclusive.sqlite`, `dataset_shard_top4_exclusive.sqlite`,
  `job_metadata.json`.
- Job-index maps (array index N -> record_id/file_index):
  `.../runs_matched/DoubleMuon_index.json` (57 entries, records 30522 [29
  files] + 30555 [28 files]) and `.../runs_matched/SingleMuon_index.json`
  (152 entries, records 30530 [70 files] + 30563 [82 files]).
- PBS scripts: `.../runs_matched/run_matched_array_DoubleMuon.sh` and
  `.../runs_matched/run_matched_array_SingleMuon.sh`.
- PBS logs (one pair per array index, per this task's own "unique
  ^array_index^ logs" rule): `.../runs_matched/logs/DoubleMuon/out.<N>.log`
  / `err.<N>.log`, same pattern under `logs/SingleMuon/`.

## How to resume

1. Check job status with the `qstat` command above. Wait until every
   subjob shows a terminal state (no more `Q`/`R`/`H`).
2. For each dataset, check every array index 0..56 (DoubleMuon) / 0..151
   (SingleMuon) has a `job_metadata.json` with `git_commit` == `521c31e`
   and no Python traceback in its `err.<N>.log`. Any index missing or
   failed: **resubmit ONLY that index** from the SAME pinned checkout,
   e.g.:
   ```
   ssh wipp-home '/opt/pbs/bin/qsub -J <N>-<N> -N matched_top4_retry \
     -o ".../logs/DoubleMuon/out.^array_index^.log" \
     -e ".../logs/DoubleMuon/err.^array_index^.log" \
     .../runs_matched/run_matched_array_DoubleMuon.sh'
   ```
   (swap in the SingleMuon script/paths as needed). Allow up to two retry
   rounds per this task's own instruction; if anything still fails after
   that, STOP and report to Matan -- never deliver a partial dataset.
3. Once every job has succeeded exactly once: run Step 4's identity
   checks (every file once; sum of `n_read` == 94,148,416 for DoubleMuon
   and == 323,952,013 for SingleMuon; one single git commit across every
   job of both datasets; zero `CAPPED::` entries in any shard, normal AND
   top-4; the 4 pilot files reproduce Step 2's own outputs exactly;
   DoubleMuon inclusive == exclusive; SingleMuon inclusive minus exclusive
   == events vetoed by DoubleMuon's acceptance, with the exclusive
   fraction reported).
4. Step 5: build the combined delivery (normal and top-4 versions) --
   pool DoubleMuon inclusive + SingleMuon exclusive per signature, run the
   existing unchanged post-processing, produce the 8 ROOT files plus
   manifests/build_summary/crop_summary/README under
   `.../output/cms_datasets/deliver/muon_combined/`, verify with uproot
   AND real ROOT 6.40.02, commit under
   `studies/cms_datasets/deliver/committed/muon_combined/`.
5. Step 6: write `COMBINED_MUON_REPORT.md` (cutflows, Z/J-psi resonances,
   trigger-mixing stacked-contribution check, >30/>25-bin count tables
   with lepton-content breakdown, top-4 specifics, low-mass/e-mu overlap,
   required plots, known artifacts) -- **plus** the additional
   BumpNet-ready-histogram-count table Matan asked for mid-task: combined
   / DoubleMuon alone / SingleMuon alone / SingleMuon-exclusive-alone /
   each of the 4 records alone (counts only, no new ROOT files for rows
   2-5), **and** a "discard events with >4 objects" counts-only variant of
   that same table (normal version restricted to categories with total
   object count <=4) -- for the combined file, each dataset, and each
   record, at both thresholds.
6. Finish with the plain-language summary to Matan per the task's own
   required structure.

## What is already done and validated (not to repeat)

- Step 1 (top-4 code) and Step 2 (validation on the 4 pilot files, checks
  a-e all PASS) and Step 3 (cap-risk projection, no file splitting
  needed) are complete and committed/pushed -- see
  `TOP4_STEP2_VALIDATION.md` and `TOP4_STEP3_CAP_RISK.md` in this same
  directory.
