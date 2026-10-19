# Upstream #35 sync: real-file proof (step B), 19 Oct 2026

**Result: every output is identical between OLD and NEW code — VERIFIED BY RUNNING.**

- **Jobs:** per-file array `5251334[]` and build/compare job `5251335`, on
  wipp-home, 19 Oct 2026 18:44–19:43. All exited with status 0.
- **Evidence:** the comparison JSONs and the build log are in
  `evidence/proof_B/`; the originals are in `work/sync35b_20261020/evidence/`.
- **Comparison scripts:** the unchanged
  `studies/mcport_validation_20261014/compare.py` and `mc_compare.py`. The
  data per-file comparison goes through `cluster/compare_data_runs.py`, which
  only narrows compare.py's dataset list to DoubleMuon and DoubleEG.

## What was compared

| side | data code | MC code |
|---|---|---|
| OLD | fork master `45a7e06` (pre-#35) | `feature/cms-mc-peakfix-20261018` `24ecb7c` (pre-#35) |
| NEW | `sync/upstream-35-20261019` `85c6ba8` (#35 + CMS fix) | `sync/mc-upstream-35-20261020` `0e98075` (#35 + CMS fix + MC builder on #35's functions) |

How the code was run:

- Each commit was exported with `git archive` to `checkouts/sync35b_20261020/<side>_<kind>.tar`.
  The job unpacked it into node-local scratch, and OLD then NEW ran from the
  same path in the same job.
- `git_commit` in the job metadata therefore reads "UNKNOWN" on both sides.
  The commit is recorded by the tar header (`git get-tar-commit-id`) in the
  logs instead.

Options used:

- **Data per-file:** `--dataset-label <DS> --record-id <R> --file-index 0 --population matched4`
  (the 7 Oct options).
- **MC per-file:** `--is-mc --dataset-label MC --record-id <R> --file-index 0 --population matched4`
  (`pbs_mc_pilot.sh`).
- **Data delivery:** `build_four_dataset_delivery.py --datasets DoubleMuon,DoubleEG`
  (the rest are defaults).
- **MC build:** `build_mc_delivery.py --smoke-test` with all defaults
  (`--peak-scope combined`, `--peak-on weighted`, `--min-events-basis raw`,
  `--output-mode both`).

## Per-file outputs

| file | shards compared | shards identical | job_metadata physics differences | provenance differences |
|---|---:|---:|---:|---|
| DoubleMuon 30522 / 0 | 8 | 8 | 0 | created_utc, elapsed_sec |
| DoubleEG 30521 / 0 | 8 | 8 | 0 | created_utc, elapsed_sec |
| MC 67801 / 0 (TTTo2L2Nu) | 8 | 8 (every mass array and every `_mcraw_*` sibling, element by element) | 0 | created_utc, elapsed_sec |
| MC 72752 / 0 | 8 | 8 (same) | 0 | created_utc, elapsed_sec |

The new driver's guard `assert mc_event_weights is None` held on all four
files, data and MC. A failure would have stopped the job. So #35's new middle
return value is None for CMS files: VERIFIED BY RUNNING.

## Delivery builds

| output | histograms OLD / NEW | bins compared | identical (names, edges, contents, variances, entries, titles) | totals OLD = NEW |
|---|---|---:|---|---|
| data `proof_bumpnet.root` | 220 / 220 | 220,440 | yes | 216,498 entries |
| data `proof_bumpnet_cropped.root` | 220 / 220 | 6,830 | yes | 216,498 entries |
| data `build_summary_rare4_four_dataset.json`, `manifest_proof.json` | — | — | yes (apart from 2 normalised directory paths) | — |
| MC `proof_record67801_mc.root` | 982 / 982 | 983,964 | yes (Sumw2 present) | Σw = 3,810,426.992146938 |
| MC `proof_record72752_mc.root` | 937 / 937 | 938,874 | yes (Sumw2 present) | Σw = 42,561.36420682676 |
| MC `proof_summedSM_mc.root` | 1,059 / 1,059 | 1,061,118 | yes (Sumw2 present) | Σw = 3,852,988.35635377 |
| MC `proof_build_report.json` | — | — | yes; only `generated_utc` differs | — |

The MC build is a **smoke test**: Σw comes from one file per sample, so the
yields are not physics. The point is that the NEW builder, now running
#35's `compute_normalization` and `_find_rightmost_highest_peak` inside
`--peak-scope combined`, produces bit-identical histograms and an identical
report.

## Files

- New in `checkouts/sync35b_20261020/`:
  - the 4 pinned tarballs;
  - `pinned_code_20261019.tar.gz`, which holds all four. Verified: gzip OK,
    4 entries, each byte-identical (sha256) to its original.
- New in `work/sync35b_20261020/`: runs, deliveries, logs, evidence, the
  mapping, the script copy, and the `code` link.
- 147 entries in total. Cluster file count 120,539 → 120,686 (19 Oct 20:30),
  within ≤ 300 new and ≤ 125,000 total.
