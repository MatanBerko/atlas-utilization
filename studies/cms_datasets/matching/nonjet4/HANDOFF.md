# Handoff note: nonjet4 task, full production run in progress

Written right after submitting the full production run, so work can
resume cleanly after a break. This is a snapshot at the time of writing,
not a final result.

## PBS job IDs (cluster: wipp-home / wipp-an1, queue N -> routed to shortE)

| Job ID | Dataset | Array indices | Status when this note was written |
|---|---|---|---|
| `5162005[].pbs` | DoubleMuon | 0-56 | SUBMITTED, running/queued |
| `5162006[].pbs` | SingleMuon | 0-151 | SUBMITTED, running/queued |

Check current status any time with (read-only, safe to run anytime):
```
ssh wipp-home '/opt/pbs/bin/qstat -t "5162005[].pbs" "5162006[].pbs"'
```
No failures had been observed in any completed subjob as of this note.

## Pinned commit and checkout (Hard Rule 6)

- Branch: `deliver/all-datasets-bumpnet`, Matan's fork
  (`https://github.com/MatanBerko/atlas-utilization`).
- **Pinned commit for this production run: `3c7c9c9`** (Step 1 nonjet4
  implementation `3a184b7`, plus Step 2/3 evidence-only commits on top --
  the executable code `studies/cms_datasets/cluster/run_dataset_on_file.py`
  has not changed since `3a184b7`).
- **Pinned checkout** (used ONLY by these 209 jobs, untouched until every
  job including retries has finished):
  `/storage/agrp/berkom/atlas-utilization/work/nonjet4_production_pinned/repo`
  (detached HEAD at `3c7c9c9`).
- Do NOT modify this checkout, or check out anything else into it, until
  every job (including retries) has finished. Reporting/analysis work
  (Steps 4-6 below) should use a **different** checkout (e.g. a fresh dev
  worktree off `deliver/all-datasets-bumpnet`) or just read the job
  outputs directly -- it must not touch this pinned one.
- The separate `nonjet4_pilot_pinned` checkout (pinned at `3a184b7`, used
  for Step 2's 4-pilot-file validation) is done with and no longer needed,
  but was left in place (not deleted) in case it's useful for re-checking.

## Output locations

- Per-job outputs: `/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_nonjet4/DoubleMuon/job_<N>/`
  and `.../runs_matched_nonjet4/SingleMuon/job_<N>/`, each containing
  `dataset_shard_inclusive.sqlite`, `dataset_shard_exclusive.sqlite`,
  `dataset_shard_top4_inclusive.sqlite`, `dataset_shard_top4_exclusive.sqlite`,
  `dataset_shard_nonjet4_inclusive.sqlite`, `dataset_shard_nonjet4_exclusive.sqlite`,
  `job_metadata.json`.
- Job-index maps (array index N -> record_id/file_index) are REUSED,
  unmodified, read-only, from the top-4 task's own production run:
  `/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched/DoubleMuon_index.json`
  (57 entries, records 30522 [29 files] + 30555 [28 files]) and
  `.../runs_matched/SingleMuon_index.json` (152 entries, records 30530
  [70 files] + 30563 [82 files]) -- the file lists have not changed, so
  there was no need to regenerate them.
- PBS scripts: `.../runs_matched_nonjet4/run_matched_nonjet4_array_DoubleMuon.sh`
  and `.../runs_matched_nonjet4/run_matched_nonjet4_array_SingleMuon.sh`.
- PBS logs (one pair per array index): `.../runs_matched_nonjet4/logs/DoubleMuon/out.<N>.log`
  / `err.<N>.log`, same pattern under `logs/SingleMuon/`.

## How to resume

1. Check job status with the `qstat` command above. Wait until every
   subjob shows a terminal state (no more `Q`/`R`/`H`).
2. For each dataset, check every array index 0..56 (DoubleMuon) / 0..151
   (SingleMuon) has a `job_metadata.json` with `git_commit` starting
   `3c7c9c9` and no Python traceback in its `err.<N>.log`. Any index
   missing or failed: **resubmit ONLY that index** from the SAME pinned
   checkout, e.g.:
   ```
   ssh wipp-home '/opt/pbs/bin/qsub -J <N>-<N> -N nonjet4_prod_DM_retry \
     -o ".../logs/DoubleMuon/out.^array_index^.log" \
     -e ".../logs/DoubleMuon/err.^array_index^.log" \
     .../runs_matched_nonjet4/run_matched_nonjet4_array_DoubleMuon.sh'
   ```
   (swap in the SingleMuon script/paths as needed). Allow up to two retry
   rounds per this task's own instruction; if anything still fails after
   that, STOP and report to Matan -- never deliver a partial dataset.
3. Once every job has succeeded exactly once: run Step 4's identity
   checks -- every file exactly once; `n_read` sums == 94,148,416
   (DoubleMuon) and == 323,952,013 (SingleMuon); one single git commit
   (`3c7c9c9`) across every job of both datasets; zero `CAPPED::` entries
   in any shard of any version (normal, top-4, AND nonjet4); the normal
   and top-4 shards of EVERY job identical to the corresponding shards in
   `runs_matched/` (proves nothing else changed, full dataset); Step 2
   checks (b)(c)(d) hold summed over the full dataset (nonjet4 is a
   sub-multiset of top-4 per signature; nonjet4 accepted == top-4
   accepted minus rejected, inclusive+exclusive; rejected count matches
   an independent recount from the normal version).
4. Step 5: build the combined delivery (nonjet4 only, normal/top-4
   behaviour of `build_muon_combined_delivery.py` unchanged) -- pool
   DoubleMuon inclusive + SingleMuon exclusive per signature, run the
   existing unchanged post-processing, produce
   `muon_combined_matched_nonjet4_bumpnet_min31bins.root`,
   `..._min26bins.root`, and their `_cropped` versions, plus
   manifests/build_summary/crop_summary/README, under
   `/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_nonjet4/`,
   verify with uproot AND real ROOT, commit under
   `studies/cms_datasets/deliver/committed/muon_combined_nonjet4/`. ALSO
   confirm by checksum that `deliver/muon_combined/` (the top-4 task's
   own delivery, in use by Maryna) is unchanged -- it must never be
   touched by this task.
5. Step 6: write `NONJET4_REPORT.md` under
   `studies/cms_datasets/deliver/committed/muon_combined_nonjet4/` per
   this task's own spec (rule + rejected fraction/composition + dropped-
   light-jet fraction; count table at >25/>30 bins for normal/top-4/
   nonjet4 across combined + both datasets + SingleMuon-exclusive-alone +
   each of the 4 records alone, with the "rows don't add up to combined"
   caveat stated; which histogram names differ between top-4 and nonjet4
   and why; lepton-content breakdown; Z/J-psi on the combined nonjet4 raw
   m(mu0,mu1); required plots).
6. Finish with the plain-language summary to Matan per the task's own
   required structure.

## What is already done and validated (not to repeat)

- Step 1 (nonjet4 code, commit `3a184b7`), Step 2 (validation on the 4
  pilot files, checks a-f all PASS, commit `6e14a6e`), and Step 3
  (cap-risk projection -- nonjet4 <= top-4 in cap risk since it's a
  sub-multiset, confirmed on pilot data, no splitting needed, commit
  `3c7c9c9`) are complete and committed/pushed -- see
  `NONJET4_STEP2_VALIDATION.md` and `NONJET4_STEP3_CAP_RISK.md` in this
  same directory.
