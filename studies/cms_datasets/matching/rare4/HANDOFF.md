# Handoff note: rare4 task, full production run in progress

Written right after submitting the full production run, so work can
resume cleanly after any interruption. This is a snapshot at the time of
writing, not a final result. Matan is asleep; this session is working
through the task autonomously per the task's own instruction.

## PBS job IDs (cluster: wipp-home / wipp-an1, queue N -> routed to shortE)

| Job ID | Dataset | Array indices | Status when this note was written |
|---|---|---|---|
| `5166354[].pbs` | DoubleMuon | 0-56 | SUBMITTED, running |
| `5166355[].pbs` | SingleMuon | 0-151 | SUBMITTED, queued/running |

Check current status any time with (read-only, safe to run anytime):
```
ssh wipp-home '/opt/pbs/bin/qstat -t "5166354[].pbs" "5166355[].pbs"'
```
No failures had been observed in any completed subjob as of this note.

## Pinned commit and checkout (Hard Rule 6)

- Branch: `deliver/all-datasets-bumpnet`, Matan's fork
  (`https://github.com/MatanBerko/atlas-utilization`).
- **Pinned commit for this production run: `635d261`** (Step 1 rare4
  implementation `52bea52`, plus Step 2/3 evidence-only commits on top --
  the executable code `studies/cms_datasets/cluster/run_dataset_on_file.py`
  has not changed since `52bea52`).
- **Pinned checkout** (used ONLY by these 209 jobs, untouched until every
  job including retries has finished):
  `/storage/agrp/berkom/atlas-utilization/work/rare4_production_pinned/repo`
  (detached HEAD at `635d261`).
- Do NOT modify this checkout, or check out anything else into it, until
  every job (including retries) has finished. Reporting/analysis work
  (Steps 4-6 below) should use a **different** checkout.
- `rare4_pilot_pinned` (pinned at `52bea52`, used for Step 2's pilot
  validation) is done with and no longer needed, but was left in place.

## Output locations

- Per-job outputs: `/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_rare4/DoubleMuon/job_<N>/`
  and `.../runs_matched_rare4/SingleMuon/job_<N>/`, each containing
  `dataset_shard_inclusive.sqlite`, `dataset_shard_exclusive.sqlite`,
  `dataset_shard_top4_inclusive.sqlite`, `dataset_shard_top4_exclusive.sqlite`,
  `dataset_shard_nonjet4_inclusive.sqlite`, `dataset_shard_nonjet4_exclusive.sqlite`,
  `dataset_shard_rare4_inclusive.sqlite`, `dataset_shard_rare4_exclusive.sqlite`,
  `job_metadata.json`.
- Job-index maps REUSED, unmodified, read-only, from `runs_matched/`:
  `.../runs_matched/DoubleMuon_index.json` (57 entries) and
  `.../runs_matched/SingleMuon_index.json` (152 entries).
- PBS scripts: `.../runs_matched_rare4/run_matched_rare4_array_DoubleMuon.sh`
  and `.../runs_matched_rare4/run_matched_rare4_array_SingleMuon.sh`.
- PBS logs: `.../runs_matched_rare4/logs/DoubleMuon/out.<N>.log` /
  `err.<N>.log`, same pattern under `logs/SingleMuon/`.

## How to resume

1. Check job status with the `qstat` command above. Wait until every
   subjob shows a terminal state (no more `Q`/`R`/`H`).
2. For each dataset, check every array index 0..56 (DoubleMuon) /
   0..151 (SingleMuon) has a `job_metadata.json` with `git_commit`
   starting `635d261` and no Python traceback in its `err.<N>.log`. Any
   index missing or failed: **resubmit ONLY that index** from the SAME
   pinned checkout, e.g.:
   ```
   ssh wipp-home '/opt/pbs/bin/qsub -J <N>-<N> -N rare4_prod_DM_retry \
     -o ".../logs/DoubleMuon/out.^array_index^.log" \
     -e ".../logs/DoubleMuon/err.^array_index^.log" \
     .../runs_matched_rare4/run_matched_rare4_array_DoubleMuon.sh'
   ```
   (swap in the SingleMuon script/paths as needed). Allow up to two
   retry rounds; if anything still fails after that, STOP and record it
   here -- never deliver a partial dataset.
3. Once every job has succeeded exactly once, run Step 4's identity
   checks: every file exactly once; `n_read` sums == 94,148,416
   (DoubleMuon) and == 323,952,013 (SingleMuon); one single git commit
   (`635d261`) across every job; zero `CAPPED::` entries in any shard of
   any version (normal, top-4, nonjet4, rare4); normal/top-4/nonjet4
   shards of EVERY job identical to `runs_matched_nonjet4/`; total rare4
   rejected events == 5,738 (nonjet4's own total, summed over all 209
   jobs); Step 2 checks (b)-(c) hold over the full dataset; report the
   total number of "hidden" cases across the full dataset.
4. Step 5: extend the existing `build_muon_combined_delivery.py` with a
   `rare4` version (pool DoubleMuon inclusive + SingleMuon exclusive per
   signature, unchanged post-processing/thresholds/cropping). Outputs
   under `/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_rare4/`:
   `muon_combined_matched_rare4_bumpnet_min31bins.root`,
   `..._min26bins.root`, and their `_cropped` versions, plus
   manifests/build_summary/crop_summary/README (rule stated exactly,
   noting this is one of two candidate readings pending the group's
   decision, the display-cap convention, and the known duplicate rate).
   Verify with uproot AND real ROOT. Compare the rare4 histogram list
   with a name-filtered normal file (expect ~960/928, with differences
   explained by hidden cases). Commit under
   `studies/cms_datasets/deliver/committed/muon_combined_rare4/`. Confirm
   by checksum/mtime that `deliver/muon_combined/` and
   `deliver/muon_combined_nonjet4/` are unchanged.
5. Step 6: write `RARE4_REPORT.md` per the task's own spec (rule +
   rejected/hidden cases; full funnel a/a2/b/c/d/d'; the >25/>30-bin
   count table across all FOUR versions -- normal/top-4/nonjet4/rare4 --
   for combined + both datasets + each of the 4 records; a plain-
   language nonjet4-vs-rare4 side-by-side with the "2mu1b+4j" example;
   required plots including a Z-peak check).
6. Finish with the plain-language summary to Matan per the task's own
   required structure, covering BOTH candidate files side by side.

## What is already done and validated (not to repeat)

- Step 1 (rare4 code, commit `52bea52`) and Step 2 (validation on the 4
  pilot files, checks a-e all PASS, zero hidden cases in the pilot
  sample) and Step 3 (cap-risk projection -- rare4 <= normal in cap risk
  since it's a sub-multiset, confirmed equal to normal on pilot data, no
  splitting needed) are complete and committed/pushed at `635d261` -- see
  `RARE4_STEP2_VALIDATION.md` and `RARE4_STEP3_CAP_RISK.md` in this same
  directory.
