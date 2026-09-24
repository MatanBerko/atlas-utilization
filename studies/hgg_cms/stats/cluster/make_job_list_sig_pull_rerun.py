#!/usr/bin/env python
"""
Statistical-model task: job list for a full-statistics rerun of
sig_injection (mu_true in {0.5, 1.0, 2.0}, 1000 toys each) with the
fixed code (`toy_q0` now captures `mu_err` via an explicit HESSE call
plus MIGRAD's own fmin diagnostics -- see fit.py's and
run_toy_job.py's own change notes, 18 Sep 2026). This is the ONLY way
to get a real pull_width at the required sample size: the
already-collected sig_injection toys (job 5057683[] + its retry) have
no mu_err field at all, so pull_width could not be computed at any
scale from them -- see STATS_REPORT.md's "NOT YET EVALUABLE" entry.

NOT the same job_type as the original run's sig_injection lines --
this uses the SAME job_type string ("sig_injection") so
`run_toy_job.py` needs no changes, but a dedicated OUT_PREFIX
(pullrerun_) and a seed range disjoint from BOTH the original run
(20260918-20260997) and retry1 (20270918-20270939) keeps every file
and every toy's random stream unambiguous.

COST: an explicit HESSE call roughly 5-7x's the per-toy cost versus
the original (pre-fix) sig_injection toys -- measured locally (this
laptop) on a small diagnostic sample:
  mu_true=0.5: 17.8 s/toy   mu_true=1.0: 20.6 s/toy   mu_true=2.0: 29.2 s/toy
(cost rises with mu_true -- plausibly more retry-driven extra fits at
larger injected signal, since fit-failure rates were also higher there
in the original run). Batch sizes below assume the SAME up-to-~6x
worker-node slowdown observed in the original hgg_stats run (job
5057683[], 8/80 subjobs walltime-killed on slow nodes), i.e. worst-case
per-toy cost = laptop timing x6, sized to use at most half of the
02:00:00 walltime cap even at that worst case:

  mu_true=0.5: 17.8*6=106.8 s/toy worst-case -> 30 toys/job (3204s=53min worst case)
  mu_true=1.0: 20.6*6=123.6 s/toy worst-case -> 25 toys/job (3090s=52min worst case)
  mu_true=2.0: 29.2*6=175.2 s/toy worst-case -> 20 toys/job (3504s=58min worst case)

  mu_true=0.5: 34 lines x 30 toys = 1020  (>=1000 required; 20-toy over-count)
  mu_true=1.0: 40 lines x 25 toys = 1000  (exact)
  mu_true=2.0: 50 lines x 20 toys = 1000  (exact)
  Total: 124 lines/subjobs.

Usage:
    python studies/hgg_cms/stats/cluster/make_job_list_sig_pull_rerun.py \\
        --out /storage/agrp/berkom/atlas-utilization/logs/hgg_stats/job_list_sig_pull_rerun.txt
"""
from __future__ import annotations

import argparse
from pathlib import Path

SEED_BASE = 20260918 + 20_000  # = 20280918; disjoint from the original (+0) and retry1 (+10000) ranges

BATCHES = [
    (0.5, 30, 34),
    (1.0, 25, 40),
    (2.0, 20, 50),
]


def build_lines():
    lines = []
    seed = SEED_BASE
    for mu_true, n_toys, n_lines in BATCHES:
        for _ in range(n_lines):
            lines.append(f"sig_injection {mu_true} {n_toys} {seed}")
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
