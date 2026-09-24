"""Signal-model task, Part 2.4: fit-validation plots (log + linear +
pull panel) per category."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PLOT_LO, PLOT_HI, PLOT_BIN_WIDTH = 105.0, 180.0, 0.25


def plot_category_fit(cat: str, mgg: np.ndarray, w: np.ndarray, shape, out_path: Path,
                       chi2_info: dict, model_label: str):
    edges = np.arange(PLOT_LO, PLOT_HI + PLOT_BIN_WIDTH, PLOT_BIN_WIDTH)
    centers = 0.5 * (edges[:-1] + edges[1:])
    in_range = (mgg >= PLOT_LO) & (mgg <= PLOT_HI)
    m, ww = mgg[in_range], w[in_range]

    obs, _ = np.histogram(m, bins=edges, weights=ww)
    obs_w2, _ = np.histogram(m, bins=edges, weights=ww ** 2)
    err = np.sqrt(np.maximum(obs_w2, 0.0))

    total = float(ww.sum())
    probs = shape.bin_probabilities(edges)
    pred = total * probs

    pull = np.divide(obs - pred, err, out=np.zeros_like(obs), where=err > 0)

    fig, axes = plt.subplots(3, 1, figsize=(8, 9), sharex=True,
                              gridspec_kw={"height_ratios": [3, 3, 1]})
    ax_lin, ax_log, ax_pull = axes

    for ax, logscale in ((ax_lin, False), (ax_log, True)):
        ax.errorbar(centers, obs, yerr=err, fmt="o", color="#1a1a1a", ms=2.5,
                    elinewidth=0.8, capsize=0, label="combined signal MC (weighted)")
        ax.plot(centers, pred, color="#D55E00", linewidth=1.4, label=f"{model_label} fit")
        ax.set_ylabel("events / 0.25 GeV")
        ax.legend(fontsize=8, frameon=False)
        ax.grid(alpha=0.25, linewidth=0.5)
        if logscale:
            ax.set_yscale("log")
            ax.set_ylim(bottom=max(1e-4, np.min(obs[obs > 0]) * 0.3) if np.any(obs > 0) else 1e-4)

    ax_pull.axhline(0, color="#666666", linewidth=0.8)
    ax_pull.scatter(centers, pull, s=6, color="#0072B2")
    ax_pull.set_ylabel("pull")
    ax_pull.set_xlabel("m_γγ [GeV]")
    ax_pull.set_ylim(-6, 6)
    ax_pull.grid(alpha=0.25, linewidth=0.5)

    fig.suptitle(f"{cat}: {model_label} fit, chi2/ndf = {chi2_info['chi2']:.1f}/{chi2_info['ndf']} "
                 f"= {chi2_info['chi2_per_ndf']:.2f} (n_bins_used={chi2_info['n_bins_used']})")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
