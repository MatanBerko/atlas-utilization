"""Bias-study diagnosis, Part 4: plot every truth model (each family at
its selected order, nominal and +-0.5x leakage) over 105-180 GeV, and
compare their spread inside 115-135 GeV (events/GeV) against the
expected signal peak's own density."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from studies.hgg_cms.background_model.families import FAMILIES
from studies.hgg_cms.background_model.common import bin_edges
from studies.hgg_cms.background_model.leakage import leakage_template_fine
from studies.hgg_cms.background_model.diagnostics.load import (
    TRUTH_FAMILIES, load_order_selection, load_signal_model,
)
from studies.hgg_cms.signal_model.shapes import SignalShape

BLIND_LO, BLIND_HI = 115.0, 135.0


def build_truth_curves(category: str, order_selection: dict, leakage_json_path: str) -> dict:
    """{family: {"nominal": (edges, density_events_per_GeV), "leakage_plus":..., "leakage_minus":...}}"""
    edges = bin_edges(105.0, 180.0, 0.25)
    leak = leakage_template_fine(category, edges, path=leakage_json_path)
    out = {}
    for fam_name in TRUTH_FAMILIES:
        sel = order_selection[category][fam_name]["selection"]
        order = sel["final_selected_order"]
        if order is None:
            continue
        params = np.array(order_selection[category][fam_name]["per_order"][str(order)]["fit"]["params"])
        fam = FAMILIES[fam_name]
        base = fam.bin_expectation(edges, order, params)
        out[fam_name] = {
            "edges": edges,
            "nominal": base / 0.25,
            "leakage_plus": (base + 0.5 * leak) / 0.25,
            "leakage_minus": (base - 0.5 * leak) / 0.25,
        }
    return out


def signal_density(category: str, signal_model: dict, edges: np.ndarray) -> np.ndarray:
    sp = signal_model[category]["shape_params"]
    shape = SignalShape(params=sp["params"], use_gauss2=sp["use_gauss2"], param_names=tuple(sp["params"].keys()))
    expected_yield = signal_model[category]["yields"]["N_with_trigger_sf_central"]
    probs = shape.bin_probabilities(edges)
    return expected_yield * probs / np.diff(edges)  # events/GeV


def plot_truth_spread(category: str, curves: dict, sig_density: np.ndarray, edges: np.ndarray, out_path: Path):
    centers = 0.5 * (edges[:-1] + edges[1:])
    fig, (ax_full, ax_zoom) = plt.subplots(2, 1, figsize=(9, 8))

    colors = {"bernstein": "#D55E00", "expsum": "#0072B2", "powersum": "#009E73", "laurent": "#CC79A7"}
    for fam_name, variants in curves.items():
        ax_full.plot(centers, variants["nominal"], color=colors[fam_name], linewidth=1.3, label=fam_name)
        ax_full.fill_between(centers, variants["leakage_minus"], variants["leakage_plus"],
                              color=colors[fam_name], alpha=0.15)
    ax_full.axvspan(BLIND_LO, BLIND_HI, color="#dddddd", alpha=0.5, zorder=0)
    ax_full.set_ylabel("events / GeV")
    ax_full.set_xlabel("m_γγ [GeV]")
    ax_full.set_title(f"{category}: truth-model curves (nominal, shaded = ±0.5×leakage), 105-180 GeV")
    ax_full.legend(fontsize=8, frameon=False)
    ax_full.grid(alpha=0.25, linewidth=0.5)

    zoom_mask = (centers >= BLIND_LO) & (centers < BLIND_HI)
    for fam_name, variants in curves.items():
        ax_zoom.plot(centers[zoom_mask], variants["nominal"][zoom_mask], color=colors[fam_name],
                     linewidth=1.5, label=f"{fam_name} (nominal)")
    ax_zoom2 = ax_zoom.twinx()
    ax_zoom2.plot(centers[zoom_mask], sig_density[zoom_mask], color="black", linewidth=1.8,
                  linestyle="--", label="expected H→γγ signal")
    ax_zoom.set_xlabel("m_γγ [GeV]")
    ax_zoom.set_ylabel("truth background density [events/GeV]")
    ax_zoom2.set_ylabel("signal density [events/GeV]", color="black")
    ax_zoom.set_title(f"{category}: truth-family spread inside the blinded window (115-135 GeV) vs. signal peak")
    lines1, labels1 = ax_zoom.get_legend_handles_labels()
    lines2, labels2 = ax_zoom2.get_legend_handles_labels()
    ax_zoom.legend(lines1 + lines2, labels1 + labels2, fontsize=8, frameon=False, loc="upper right")
    ax_zoom.grid(alpha=0.25, linewidth=0.5)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def spread_vs_signal_summary(category: str, curves: dict, sig_density: np.ndarray, edges: np.ndarray) -> dict:
    centers = 0.5 * (edges[:-1] + edges[1:])
    zoom_mask = (centers >= BLIND_LO) & (centers < BLIND_HI)
    fam_nominal = {fam: variants["nominal"][zoom_mask] for fam, variants in curves.items()}
    stacked = np.array(list(fam_nominal.values()))  # (n_families, n_bins_in_window)
    spread_per_bin = stacked.max(axis=0) - stacked.min(axis=0)
    sig_in_window = sig_density[zoom_mask]
    return {
        "max_truth_family_spread_events_per_GeV": float(spread_per_bin.max()),
        "mean_truth_family_spread_events_per_GeV": float(spread_per_bin.mean()),
        "signal_peak_density_events_per_GeV": float(sig_in_window.max()),
        "mean_signal_density_events_per_GeV": float(sig_in_window.mean()),
        "spread_over_signal_peak_ratio": float(spread_per_bin.max() / sig_in_window.max()),
    }
