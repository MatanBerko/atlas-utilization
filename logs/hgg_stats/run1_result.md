# hgg_stats validation run 1: result and killed indices

**Job**: `5057683[]`, 80 subjobs, submitted from commit `15bd3a5`
(`submit_hgg_stats.sh`, per the cluster commands given in the previous
chat message). **Reported by the user on 18 Sep 2026.**

- 72/80 subjobs finished with exit code 0.
- 8/80 subjobs were killed at the `walltime=02:00:00` limit (exit -29,
  "walltime 7204 exceeded limit 7200") on slow worker nodes. Same-type
  jobs on other nodes finished in 44 minutes to just under 2h, so this
  is worker-node speed variance (the cluster measured up to ~5-6x
  slower than the laptop timing that originally sized the batches in
  `make_job_list.py`), not a fit-convergence problem -- no NLL-invariant
  or MIGRAD-validity failures were reported for any of the 8.

## Killed indices (job_list.txt, this directory)

| index | job_type | mu_true | n_toys | seed |
|---|---|---|---|---|
| 17 | sig_injection | 2.0 | 250 | 20260934 |
| 18 | sig_injection | 2.0 | 250 | 20260935 |
| 19 | sig_injection | 2.0 | 250 | 20260936 |
| 44 | mass_scan_bkg | 0.0 | 20 | 20260961 |
| 46 | mass_scan_bkg | 0.0 | 20 | 20260963 |
| 47 | mass_scan_bkg | 0.0 | 20 | 20260964 |
| 48 | mass_scan_bkg | 0.0 | 20 | 20260965 |
| 51 | mass_scan_bkg | 0.0 | 20 | 20260968 |

Index 20 (sig_injection mu=2.0, seed 20260937) finished OK in 44 min.
Indices 45 (seed 20260962) and 49 (seed 20260966), both mass_scan_bkg,
finished OK in 1:55 and 1:52 respectively -- close to the 2h limit,
consistent with the same node-speed variance rather than a fluke.

## Missing toy counts

- `sig_injection` mu=2.0: 3 x 250 = **750 toys lost** (1000 required,
  250 survive from index 20).
- `mass_scan_bkg`: 5 x 20 = **100 toys lost** (1000 required, 900
  survive from the other 45 indices).
- All other job types (`bkg_only`, `sig_injection` mu=0.5/1.0,
  `spurious_check`) had every subjob finish OK -- no retry needed for
  those.

## Partial output from the killed indices: none, by construction

`run_toy_job.py` writes its output with exactly ONE `Path.write_text(...)`
call, at the very end of the job, after the full toy loop completes --
there is no incremental or partial write anywhere in that script (see
its own module docstring). A job killed mid-run at the walltime limit
therefore leaves **no output JSON file at all** for its index, partial
or otherwise -- there is nothing to exclude from the merge by content;
only "does the file exist" matters, and `merge_hgg_stats.py`'s glob
naturally never sees a file that was never written. This was
double-checked against the real killed indices with the command in the
final chat message (`ls`-based, not just this code-reading argument).

## Retry list 1 (`job_list_retry1.txt`, this directory)

22 lines, seeds `20270918`-`20270939` (see `make_retry_job_list_1.py`'s
own docstring for the full seed-non-overlap reasoning: the original run
used seeds `20260918`-`20260997`, and retry1's base seed is offset by
+10,000, far larger than the 80 values the original run could ever
use):

- 12 x `sig_injection mu=2.0 63 toys` = 756 toys (750 needed; 6-toy
  over-count, stated here rather than trimmed to a smaller, harder-to-
  account-for last line).
- 10 x `mass_scan_bkg 10 toys` = 100 toys (exact).

Batch sizes are cut to roughly 1/4 of the original per-job toy count
(63 vs 250 for sig_injection, 10 vs 20 for mass_scan_bkg) so each
subjob comfortably finishes under 2h even on the slowest node observed
so far in run 1, rather than raising walltime past the shortE-queue cap.
