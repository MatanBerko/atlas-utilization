#!/usr/bin/env python
"""
Statistical-model task, Parts 2 and 3.3/3.5: builds the job list for
`pbs_hgg_stats_array.sh`. Each line: `job_type mu_true n_toys seed`.

Batch sizes below were chosen from a laptop timing measurement (see
STATS_REPORT.md): ~2.9 s/toy for bkg_only and sig_injection (single-
start, warm-started, retry-on-failure -- `fit.toy_q0`), ~13 s/toy for
spurious_check (its own retry logic, similar cost), ~127 s/toy for
mass_scan_bkg (one null fit + 81 single-start alt fits per toy). Each
line's `n_toys` is sized to a comfortable fraction of the 2h walltime
cap (well under it, to leave margin for a slower cluster CPU), and the
total across all lines of one job_type meets or exceeds this task's
required minimum toy count.

  bkg_only:       8 lines x 250 toys = 2000  (>= 2000 required, Part 2.1)
  sig_injection:  4 lines x 250 toys = 1000 per mu_true in {0.5, 1, 2}
                  (>= 1000 required each, Part 2.2 -- the mu_true=1 set
                  doubles as Part 3.3's expected-band toy set)
  spurious_check: 10 lines x 100 toys = 1000  (Part 2.3)
  mass_scan_bkg:  50 lines x 20 toys  = 1000  (>= 1000 required, Part 3.5)

Usage:
    python studies/hgg_cms/stats/cluster/make_job_list.py \\
        --out /storage/agrp/berkom/atlas-utilization/logs/hgg_stats/job_list.txt
"""
from __future__ import annotations

import argparse
from pathlib import Path

BASE_SEED = 20260918  # date-derived, arbitrary but fixed/reproducible


def build_lines():
    lines = []
    seed = BASE_SEED
    for i in range(8):
        lines.append(f"bkg_only 0.0 250 {seed}")
        seed += 1
    for mu_true in (0.5, 1.0, 2.0):
        for i in range(4):
            lines.append(f"sig_injection {mu_true} 250 {seed}")
            seed += 1
    for i in range(10):
        lines.append(f"spurious_check 0.0 100 {seed}")
        seed += 1
    for i in range(50):
        lines.append(f"mass_scan_bkg 0.0 20 {seed}")
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
