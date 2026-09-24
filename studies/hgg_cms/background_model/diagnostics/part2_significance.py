"""Bias-study diagnosis, Part 2: is a function's observed worst-ratio-
over-60-cells statistically significant given the per-cell standard
errors, or consistent with pure noise around the 0.20 threshold?

METHOD: under the null "the true |S|/sigma_S ratio is EXACTLY 0.20 in
every one of the 60 cells", each cell's OBSERVED ratio is modeled as
|0.20 + N(0, se_ratio_cell)| (se_ratio_cell = se_mean_S/mean_sigma_S,
already computed by merge_bias_results.py, per cell). Monte Carlo: draw
one simulated ratio per cell (using that cell's own se_ratio), take the
max over the 60 cells, repeat N_MC times. The p-value is the fraction of
simulated maxima >= the function's ACTUAL observed worst_ratio (from the
merged JSON, computed over all 60 cells the same way, reliability
notwithstanding -- this is a check of NOISE, not of reliability, which
Part 1 covers separately).
"""
from __future__ import annotations

import numpy as np

N_MC_DEFAULT = 200_000
SEED = 20260918700


def simulate_null_max(se_ratios: np.ndarray, n_mc: int = N_MC_DEFAULT, seed: int = SEED,
                       null_ratio: float = 0.20) -> np.ndarray:
    """Returns an array of length n_mc: the simulated max-over-cells
    ratio under the null that the true ratio is `null_ratio` everywhere,
    using EACH cell's own se_ratio for its noise."""
    rng = np.random.default_rng(seed)
    n_cells = len(se_ratios)
    draws = null_ratio + rng.normal(0.0, 1.0, size=(n_mc, n_cells)) * se_ratios[None, :]
    sim_ratio = np.abs(draws)
    return sim_ratio.max(axis=1)


def p_value_for_function(points: list, observed_worst_ratio: float, n_mc: int = N_MC_DEFAULT,
                          seed: int = SEED) -> dict:
    se_ratios = np.array([p["se_ratio"] for p in points if p["se_ratio"] is not None])
    if len(se_ratios) == 0:
        return {"p_value": None, "n_cells": 0, "null_mean_max": None, "null_std_max": None}
    null_max = simulate_null_max(se_ratios, n_mc=n_mc, seed=seed)
    p = float(np.mean(null_max >= observed_worst_ratio))
    n_exceed_2se = int(sum(
        1 for p_ in points
        if p_["se_ratio"] is not None and p_["ratio"] is not None
        and (p_["ratio"] - 0.20) > 2 * p_["se_ratio"]
    ))
    return {
        "p_value": p, "n_cells": len(se_ratios),
        "null_mean_max": float(null_max.mean()), "null_std_max": float(null_max.std()),
        "null_p95_max": float(np.percentile(null_max, 95)),
        "null_p99_max": float(np.percentile(null_max, 99)),
        "observed_worst_ratio": observed_worst_ratio,
        "n_cells_exceeding_0.20_by_gt_2se": n_exceed_2se,
    }
