#!/usr/bin/env python
"""
Background-model task, Part 3: bias-summary heatmap(s) -- one per
category, test function (rows) x (truth family, leakage variant, mass)
(columns), colored by |mean spurious S| / mean sigma_S, from the merged
bias-study JSON (`merge_bias_results.py`'s output). NOT run as part of
this task (the underlying bias study has not been run yet -- see
BACKGROUND_MODEL_REPORT.md Part 3). Ready to run once that JSON exists:

    python studies/hgg_cms/background_model/cluster/plot_bias_heatmap.py \\
        --merged-json studies/hgg_cms/background_model/results/bias_study_105_180.json \\
        --out-dir studies/hgg_cms/background_model/results/plots
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_category(cat: str, evaluations: dict, out_path: Path):
    test_functions = sorted(evaluations.keys())
    columns = set()
    for tf, ev in evaluations.items():
        for pt in ev["all_points"]:
            columns.add((pt["truth_family"], pt["leakage_variant"], pt["mass"]))
    columns = sorted(columns)

    grid = np.full((len(test_functions), len(columns)), np.nan)
    for i, tf in enumerate(test_functions):
        by_col = {(p["truth_family"], p["leakage_variant"], p["mass"]): p["ratio"]
                  for p in evaluations[tf]["all_points"]}
        for j, col in enumerate(columns):
            v = by_col.get(col)
            if v is not None:
                grid[i, j] = v

    fig, ax = plt.subplots(figsize=(max(8, 0.35 * len(columns)), max(4, 0.4 * len(test_functions))))
    im = ax.imshow(grid, aspect="auto", cmap="RdBu_r", vmin=-0.5, vmax=0.5)
    ax.set_xticks(range(len(columns)))
    ax.set_xticklabels([f"{c[0][:4]}/{c[1][:4]}/m{c[2]:.0f}" for c in columns], rotation=90, fontsize=6)
    ax.set_yticks(range(len(test_functions)))
    ax.set_yticklabels(test_functions, fontsize=8)
    ax.set_title(f"{cat}: |mean spurious S| / mean sigma_S (signed), pass band = [-0.20, 0.20]")
    fig.colorbar(im, ax=ax, label="spurious S / sigma_S")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--merged-json", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    d = json.loads(Path(args.merged_json).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    fit_range = d["fit_range"]
    for cat, r in d["per_category"].items():
        out_path = out_dir / f"{cat}_{fit_range}_bias_heatmap.png"
        plot_category(cat, r["evaluations"], out_path)
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
