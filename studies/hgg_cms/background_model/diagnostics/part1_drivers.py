"""Bias-study diagnosis, Part 1: which cells drive each test function's
worst ratio, and which dimension (leakage variant, truth family, mass)
the failure is concentrated in."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from studies.hgg_cms.background_model.diagnostics.load import (
    TRUTH_FAMILIES, LEAKAGE_VARIANTS, MASSES,
)


def worst_cells(points: list, n: int = 5) -> list:
    """Top-n cells by ratio (ties broken by mass then truth_family for
    determinism), ineligible (unreliable) cells excluded -- an unreliable
    cell's ratio number is not a trustworthy 'worst' driver."""
    reliable = [p for p in points if p["reliability_ok"]]
    return sorted(reliable, key=lambda p: -p["ratio"])[:n]


def group_means(points: list, key: str) -> dict:
    """Mean ratio (reliable cells only) grouped by `key`
    ('leakage_variant', 'truth_family', or 'mass')."""
    out = {}
    for p in points:
        if not p["reliability_ok"]:
            continue
        out.setdefault(p[key], []).append(p["ratio"])
    return {k: float(np.mean(v)) for k, v in out.items()}


def dominant_driver(points: list) -> dict:
    """Which dimension has the largest SPREAD (max-min of group means)
    -- the dimension with the biggest spread is the one most associated
    with driving the worst ratios."""
    by_leak = group_means(points, "leakage_variant")
    by_fam = group_means(points, "truth_family")
    by_mass = group_means(points, "mass")
    spreads = {
        "leakage_variant": (max(by_leak.values()) - min(by_leak.values())) if by_leak else 0.0,
        "truth_family": (max(by_fam.values()) - min(by_fam.values())) if by_fam else 0.0,
        "mass": (max(by_mass.values()) - min(by_mass.values())) if by_mass else 0.0,
    }
    dominant = max(spreads, key=spreads.get)
    return {
        "by_leakage_variant": by_leak, "by_truth_family": by_fam, "by_mass": by_mass,
        "spreads": spreads, "dominant_dimension": dominant,
    }


def plot_heatmap(cat: str, test_function: str, points: list, out_path: Path):
    fig, axes = plt.subplots(1, len(MASSES), figsize=(3.0 * len(MASSES), 3.2), sharey=True)
    grid_by_mass = {m: np.full((len(TRUTH_FAMILIES), len(LEAKAGE_VARIANTS)), np.nan) for m in MASSES}
    reliability_by_mass = {m: np.zeros((len(TRUTH_FAMILIES), len(LEAKAGE_VARIANTS)), dtype=bool) for m in MASSES}
    for p in points:
        i = TRUTH_FAMILIES.index(p["truth_family"])
        j = LEAKAGE_VARIANTS.index(p["leakage_variant"])
        grid_by_mass[p["mass"]][i, j] = p["ratio"]
        reliability_by_mass[p["mass"]][i, j] = p["reliability_ok"]

    vmax = max(1.0, np.nanmax([np.nanmax(g) for g in grid_by_mass.values()]))
    im = None
    for ax, m in zip(axes, MASSES):
        grid = grid_by_mass[m]
        im = ax.imshow(grid, cmap="RdYlGn_r", vmin=0.0, vmax=vmax, aspect="auto")
        for i in range(len(TRUTH_FAMILIES)):
            for j in range(len(LEAKAGE_VARIANTS)):
                val = grid[i, j]
                if np.isnan(val):
                    continue
                marker = "" if reliability_by_mass[m][i, j] else "*"
                ax.text(j, i, f"{val:.2f}{marker}", ha="center", va="center", fontsize=7,
                        color="black")
        ax.set_xticks(range(len(LEAKAGE_VARIANTS)))
        ax.set_xticklabels(["nom", "leak+", "leak-"], fontsize=7, rotation=45)
        ax.set_title(f"m={m:.0f}", fontsize=9)
    axes[0].set_yticks(range(len(TRUTH_FAMILIES)))
    axes[0].set_yticklabels(TRUTH_FAMILIES, fontsize=8)
    fig.colorbar(im, ax=axes, label="|mean S| / mean sigma_S", fraction=0.02, pad=0.02)
    fig.suptitle(f"{cat} — {test_function}: spurious-signal ratio per cell "
                 f"(* = ineligible on fit reliability)")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
