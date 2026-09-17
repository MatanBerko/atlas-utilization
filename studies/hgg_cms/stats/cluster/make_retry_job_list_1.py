#!/usr/bin/env python
"""
Statistical-model task: retry list #1 for the 18 Sep 2026 hgg_stats
validation run (job 5057683[], 80 subjobs, commit 15bd3a5). 72 subjobs
finished (exit 0); 8 were killed at the 02:00:00 walltime on slow
worker nodes (exit -29, "walltime 7204 exceeded limit 7200") -- same-
type jobs on faster nodes finished in 44 min to under 2h, so this is
worker-node speed variance (cluster measured up to ~5-6x slower than
the laptop timing that originally sized the batches), not a
fit-convergence problem. `run_toy_job.py` writes its output with a
single `Path.write_text(...)` call at the very end of the job (see that
script -- there is no incremental/partial write anywhere), so a killed
job leaves NO output file at all, partial or otherwise; nothing needs
excluding by content, only by which indices never produced a file (see
`FOUND_ON_DISK` below and STATS_REPORT.md for the verification command
that confirmed this for real on the actual killed indices).

Killed (original job list, logs/hgg_stats/job_list.txt):
  index 17: sig_injection mu=2.0 250 20260934
  index 18: sig_injection mu=2.0 250 20260935
  index 19: sig_injection mu=2.0 250 20260936
  index 44: mass_scan_bkg  0.0 20 20260961
  index 46: mass_scan_bkg  0.0 20 20260963
  index 47: mass_scan_bkg  0.0 20 20260964
  index 48: mass_scan_bkg  0.0 20 20260965
  index 51: mass_scan_bkg  0.0 20 20260968

Missing toy counts: sig_injection mu=2.0 lost 3 x 250 = 750 toys (index
20, seed 20260937, DID finish -- 250 of the original 1000 survive);
mass_scan_bkg lost 5 x 20 = 100 toys (900 of the original 1000
survive).

Retry batch sizes: each piece is sized to finish comfortably under 2h
even on the SLOWEST node seen so far (the killed jobs' own timing is
the worst-case evidence available -- a 250-toy sig_injection job and a
20-toy mass_scan_bkg job both exceeded 2h on a slow node, so both
batch sizes are cut roughly 4x, well past merely covering the ~5-6x
node-speed variance already observed):
  sig_injection mu=2.0: 750 toys needed -> 12 lines x 63 toys = 756
    (OVER-COUNT: 6 extra toys, from 756 not dividing evenly into a
    smaller line count at this batch size -- harmless, only helps the
    >=1000 total requirement by a hair; not trimmed to avoid a partial,
    harder-to-account-for last line).
  mass_scan_bkg: 100 toys needed -> 10 lines x 10 toys = 100 (exact).

Seeds: this run's original job list used BASE_SEED=20260918 through
20260918+79=20260997 (80 sequential values, one per line, see
make_job_list.py). This retry list starts at RETRY1_SEED_BASE =
20260918 + 10_000 = 20270918 -- an offset far larger than the 80 values
the original run could ever use, so there is no possible overlap
without needing to cross-check individual values, and increments by 1
per line exactly as the original does (22 lines -> seeds 20270918
through 20270939).

Usage:
    python studies/hgg_cms/stats/cluster/make_retry_job_list_1.py \\
        --out /storage/agrp/berkom/atlas-utilization/logs/hgg_stats/job_list_retry1.txt
"""
from __future__ import annotations

import argparse
from pathlib import Path

RETRY1_SEED_BASE = 20260918 + 10_000  # = 20270918; see module docstring


def build_lines():
    lines = []
    seed = RETRY1_SEED_BASE
    for _ in range(12):
        lines.append(f"sig_injection 2.0 63 {seed}")
        seed += 1
    for _ in range(10):
        lines.append(f"mass_scan_bkg 0.0 10 {seed}")
        seed += 1
    return lines


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()
    lines = build_lines()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_path} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
