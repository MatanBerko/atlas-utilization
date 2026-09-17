#!/usr/bin/env python
"""
Statistical-model task: job list for the DECISIVE pull-width diagnostic
-- ~500 toys at mu_true=1, job_type `sig_injection_randnuis`
(`run_toy_job.run_sig_injection_randomized_nuisance`), where each toy's
TRUE nuisance values are drawn from their own unit-Gaussian constraint
instead of being fixed at nominal. Pre-set expectation, stated here
BEFORE this is run: if the hypothesis in STATS_REPORT.md (the FIXED-
nuisance toy design mechanically produces pull width < 1, since mu_hat
spread only reflects statistical fluctuation while mu_err reflects the
full systematic model) is correct, this run's pull width should come
out at 1.00+-0.05. This is an ADDED diagnostic -- the existing
sig_injection toys and their results are untouched by this run.

Timing: measured locally at ~11.4 s/toy on a tiny (n=4) sample --
similar order to the fixed-nuisance sig_injection toys at the same
mu_true (~20.6 s/toy from the pull-width rerun). Batch size below uses
the more conservative (slower) of the two figures and the same up to
~6x worker-node slowdown margin as prior batches on this job:
  20.6 s/toy * 6 = 123.6 s/toy worst case -> 25 toys/job (3090s=52min
  worst case, well under the 02:00:00 cap).
  20 lines x 25 toys = 500 (exact).

Seeds: 20260918 + 30_000 = 20290918 -- disjoint from the original run
(20260918-20260997), retry1 (20270918-20270939), and the sig-pull
rerun (20280918-20281041).

Usage:
    python studies/hgg_cms/stats/cluster/make_job_list_randnuis.py \\
        --out /storage/agrp/berkom/atlas-utilization/logs/hgg_stats/job_list_randnuis.txt
"""
from __future__ import annotations

import argparse
from pathlib import Path

SEED_BASE = 20260918 + 30_000  # = 20290918
N_LINES = 20
N_TOYS_PER_LINE = 25
MU_TRUE = 1.0


def build_lines():
    lines = []
    seed = SEED_BASE
    for _ in range(N_LINES):
        lines.append(f"sig_injection_randnuis {MU_TRUE} {N_TOYS_PER_LINE} {seed}")
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
    print(f"wrote {out_path} ({len(lines)} lines, {N_LINES * N_TOYS_PER_LINE} toys total)")


if __name__ == "__main__":
    main()
