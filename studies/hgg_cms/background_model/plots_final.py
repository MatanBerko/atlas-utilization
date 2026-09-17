"""Background-model task, Part 2 finalization: the chosen (bernstein_6)
sideband fit with pulls, and an illustrative +-S_spur band on the
signal shape at 125 GeV, per category. Blinded region left empty in
every data panel."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from studies.hgg_cms.background_model.families import FAMILIES

BLIND_LO, BLIND_HI = 115.0, 135.0


def plot_chosen_fit(cat: str, edges: np.ndarray, counts: np.ndarray, mask: np.ndarray,
                     family: str, order: int, params: np.ndarray, gof_chi2: dict, out_path: Path):
    centers = 0.5 * (edges[:-1] + edges[1:])
    err = np.sqrt(np.maximum(counts, 1.0))
    pred_full = FAMILIES[family].bin_expectation(edges, order, params)

    fig, axes = plt.subplots(3, 1, figsize=(9, 10), sharex=True,
                              gridspec_kw={"height_ratios": [3, 3, 1]})
    ax_lin, ax_log, ax_pull = axes

    for ax, logscale in ((ax_lin, False), (ax_log, True)):
        ax.errorbar(centers[mask], counts[mask], yerr=err[mask], fmt="o", color="#1a1a1a", ms=2.2,
                    elinewidth=0.6, capsize=0, label="data (sideband bins)", zorder=5)
        ax.axvspan(BLIND_LO, BLIND_HI, color="#dddddd", alpha=0.6, zorder=0, label="blinded (115-135 GeV)")
        ax.plot(centers, pred_full, color="#D55E00", linewidth=1.4,
                label=f"chosen: {family} order {order} (curve drawn across blinded band)")
        ax.set_ylabel("events / 0.25 GeV")
        ax.grid(alpha=0.25, linewidth=0.5)
        if logscale:
            ax.set_yscale("log")
    ax_lin.legend(fontsize=8, frameon=False, loc="upper right")

    pull = np.divide(counts - pred_full, err, out=np.zeros_like(counts), where=err > 0)
    ax_pull.axhline(0, color="#666666", linewidth=0.8)
    ax_pull.scatter(centers[mask], pull[mask], s=5, color="#1a1a1a")
    ax_pull.axvspan(BLIND_LO, BLIND_HI, color="#dddddd", alpha=0.6, zorder=0)
    ax_pull.set_ylabel("pull")
    ax_pull.set_xlabel("m_γγ [GeV]")
    ax_pull.set_ylim(-5, 5)
    ax_pull.grid(alpha=0.25, linewidth=0.5)

    chi2_per_ndf = gof_chi2["chi2"] / gof_chi2["ndf"] if gof_chi2["ndf"] else float("nan")
    fig.suptitle(f"{cat}: FINAL chosen background function (Fallback C), "
                 f"GOF chi2/ndf = {gof_chi2['chi2']:.1f}/{gof_chi2['ndf']} = {chi2_per_ndf:.2f} "
                 f"(p={gof_chi2['p_value']:.2f})")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_spurious_signal_band(cat: str, signal_shape, expected_yield: float, s_spur: float,
                               edges: np.ndarray, out_path: Path):
    """ILLUSTRATIVE ONLY (labeled as such on the plot): the signal
    shape's own density at 125 GeV, scaled by expected_yield, with a
    shaded band showing the shape scaled by (expected_yield +/- s_spur)
    -- a visual sense of the spurious-signal systematic's size relative
    to the signal peak itself, NOT a statement about where in mass the
    spurious signal actually appears (the bias study measures a total
    yield shift, not a shape)."""
    centers = 0.5 * (edges[:-1] + edges[1:])
    zoom = (centers >= BLIND_LO) & (centers < BLIND_HI)
    probs = signal_shape.bin_probabilities(edges) / np.diff(edges)  # density, events/GeV per unit yield

    nominal = expected_yield * probs
    plus = (expected_yield + s_spur) * probs
    minus = (expected_yield - s_spur) * probs

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(centers[zoom], nominal[zoom], color="#0072B2", linewidth=1.8,
            label=f"expected signal ({expected_yield:.1f} events)")
    ax.fill_between(centers[zoom], minus[zoom], plus[zoom], color="#0072B2", alpha=0.2,
                     label=f"±S_spur = ±{s_spur:.1f} events (illustrative — see note below)")
    ax.set_xlabel("m_γγ [GeV]")
    ax.set_ylabel("events / GeV")
    ax.set_title(f"{cat}: signal shape at m_H=125 GeV, ± spurious-signal systematic")
    ax.legend(fontsize=9, frameon=False, loc="upper right")
    ax.grid(alpha=0.25, linewidth=0.5)
    fig.text(0.02, 0.01,
              "ILLUSTRATIVE ONLY: band = signal shape rescaled by (yield ± S_spur), a size comparison, "
              "not a claim about the spurious signal's own mass shape.",
              fontsize=7, color="#555555", ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
