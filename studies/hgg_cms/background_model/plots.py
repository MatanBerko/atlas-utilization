"""Background-model task, Part 2: sideband fit validation plots (data +
all 4 selected-order family curves, log + linear, pull panel relative to
the lowest-NLL family) per category, with the blinded band left empty."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from studies.hgg_cms.background_model.families import FAMILIES

FAMILY_COLORS = {"bernstein": "#D55E00", "expsum": "#0072B2", "powersum": "#009E73", "laurent": "#CC79A7"}
BLIND_LO, BLIND_HI = 115.0, 135.0


def plot_category_sideband_fits(cat: str, edges: np.ndarray, counts: np.ndarray, mask: np.ndarray,
                                 selected: dict, out_path: Path):
    """selected: {family: {"order": int, "params": array, "nll": float, "gof_p": float}}"""
    centers = 0.5 * (edges[:-1] + edges[1:])
    err = np.sqrt(np.maximum(counts, 1.0))

    best_family = min(selected, key=lambda f: selected[f]["nll"])
    best_pred_full = FAMILIES[best_family].bin_expectation(edges, selected[best_family]["order"],
                                                             selected[best_family]["params"])

    fig, axes = plt.subplots(3, 1, figsize=(9, 10), sharex=True,
                              gridspec_kw={"height_ratios": [3, 3, 1]})
    ax_lin, ax_log, ax_pull = axes

    for ax, logscale in ((ax_lin, False), (ax_log, True)):
        ax.errorbar(centers[mask], counts[mask], yerr=err[mask], fmt="o", color="#1a1a1a", ms=2.2,
                    elinewidth=0.6, capsize=0, label="data (sideband bins)", zorder=5)
        # blinded bins shown as empty grey band (no data point drawn there),
        # but each family's fitted CURVE is drawn across the whole range,
        # per this task's own "curve across the band is allowed" rule.
        ax.axvspan(BLIND_LO, BLIND_HI, color="#dddddd", alpha=0.6, zorder=0, label="blinded (115-135 GeV)")
        for fam_name, d in selected.items():
            pred = FAMILIES[fam_name].bin_expectation(edges, d["order"], d["params"])
            ax.plot(centers, pred, color=FAMILY_COLORS[fam_name], linewidth=1.2,
                    label=f"{fam_name} (order {d['order']}, GOF p={d['gof_p']:.2f})")
        ax.set_ylabel("events / 0.25 GeV")
        ax.grid(alpha=0.25, linewidth=0.5)
        if logscale:
            ax.set_yscale("log")
    ax_lin.legend(fontsize=7, frameon=False, loc="upper right")

    pull = np.divide(counts - best_pred_full, err, out=np.zeros_like(counts), where=err > 0)
    ax_pull.axhline(0, color="#666666", linewidth=0.8)
    ax_pull.scatter(centers[mask], pull[mask], s=5, color="#1a1a1a")
    ax_pull.axvspan(BLIND_LO, BLIND_HI, color="#dddddd", alpha=0.6, zorder=0)
    ax_pull.set_ylabel(f"pull vs.\n{best_family} (lowest NLL)")
    ax_pull.set_xlabel("m_γγ [GeV]")
    ax_pull.set_ylim(-5, 5)
    ax_pull.grid(alpha=0.25, linewidth=0.5)

    fig.suptitle(f"{cat}: sideband fits, {edges[0]:.0f}-{edges[-1]:.0f} GeV "
                 f"(blinded band shown, never fit)")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
