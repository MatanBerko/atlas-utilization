"""
Implementation task 6, Part 3D: pileup matching (data vs each signal
sample's PV_npvsGood), and the effect of the derived weights on ggH.

LIMITATION, stated explicitly (also in the JSON output and the report):
`PV_npvsGood` is the number of RECONSTRUCTED good primary vertices, not
the true number of pileup interactions (`Pileup_nTrueInt`, MC truth
only, not available in real data at all) -- reweighting on this
reconstructed proxy is the standard fallback when no official pileup JSON
exists for a dataset (design doc Section 4), but it inherits any data/MC
mismodeling of vertex-reconstruction efficiency itself, on top of
whatever it is correcting for.

Writes the derived per-signal-label weights to
output/part_d_pileup_weights.json so Part E reuses the IDENTICAL weights
(not a re-derivation) for the "with vs without pileup weights" yield
comparison.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from studies.hgg_cms.validation import common

OUT_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = OUT_DIR / "plots"
PV_MAX = 60


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data = common.load_data_sidebands()
    data_pv = np.asarray(data["PV_npvsGood"])

    signals = common.load_all_signal()

    all_weights = {}
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True)
    for ax, label in zip(axes.flat, common.SIGNAL_LABELS):
        s = signals[label]
        s_pv = np.asarray(s["PV_npvsGood"])
        s_w = np.asarray(s["genWeight"])
        edges, weights, diag = common.derive_pileup_weights(data_pv, s_pv, s_w, pv_max=PV_MAX)
        all_weights[label] = {
            "bin_edges": edges.tolist(), "weights": weights.tolist(), "diagnostics": diag,
        }

        centers = 0.5 * (edges[:-1] + edges[1:])
        data_hist, _ = np.histogram(data_pv, bins=edges)
        data_hist = data_hist / data_hist.sum()
        mc_hist, _ = np.histogram(s_pv, bins=edges, weights=s_w)
        mc_hist = mc_hist / mc_hist.sum()
        mc_hist_rw, _ = np.histogram(s_pv, bins=edges, weights=s_w * common.apply_pileup_weight(s_pv, edges, weights))
        mc_hist_rw = mc_hist_rw / mc_hist_rw.sum()

        ax.step(centers, data_hist, where="mid", color="#1a1a1a", linewidth=1.3, label="data sidebands")
        ax.step(centers, mc_hist, where="mid", color="#D55E00", linewidth=1.1, linestyle="--", label=f"{label} MC (raw)")
        ax.step(centers, mc_hist_rw, where="mid", color="#0072B2", linewidth=1.3, label=f"{label} MC (PU-reweighted)")
        ax.set_title(label, fontsize=10)
        ax.grid(alpha=0.25, linewidth=0.5)
    axes.flat[0].legend(loc="upper right", fontsize=7, frameon=False)
    for ax in axes[-1, :]:
        ax.set_xlabel("PV_npvsGood")
    fig.suptitle("Pileup (PV_npvsGood) matching: data sidebands vs each signal sample, before/after reweighting")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "part_d_pileup_matching.png", dpi=150)
    plt.close(fig)

    (OUT_DIR / "part_d_pileup_weights.json").write_text(json.dumps(all_weights, indent=2), encoding="utf-8")

    # ---- ggH-specific before/after effect (efficiency + peak/sigma_eff per category) ----
    ggh = signals["ggh"]
    ggh_pv = np.asarray(ggh["PV_npvsGood"])
    ggh_gw = np.asarray(ggh["genWeight"])
    ggh_mgg = np.asarray(ggh["m_gg"])
    ggh_cat = np.asarray(ggh["category"])
    edges, weights = np.array(all_weights["ggh"]["bin_edges"]), np.array(all_weights["ggh"]["weights"])
    pu_w = common.apply_pileup_weight(ggh_pv, edges, weights)

    genEventSumw_ggh = 11593651.336800005  # merge_summary_signal.json, per-record genEventSumw_over_processed_files

    sum_gw_before = float(ggh_gw.sum())
    sum_gw_after = float((ggh_gw * pu_w).sum())
    eff_before = sum_gw_before / genEventSumw_ggh
    eff_after = sum_gw_after / genEventSumw_ggh

    per_category = {}
    for cat in common.CATEGORIES:
        mask = common.category_mask(ggh_cat, cat)
        mode_before, sigma_before = common.weighted_mode_and_sigma68(ggh_mgg[mask], ggh_gw[mask])
        mode_after, sigma_after = common.weighted_mode_and_sigma68(ggh_mgg[mask], (ggh_gw * pu_w)[mask])
        per_category[cat] = {
            "n_events": int(mask.sum()),
            "mode_before_GeV": mode_before, "sigma_eff68_before_GeV": sigma_before,
            "mode_after_GeV": mode_after, "sigma_eff68_after_GeV": sigma_after,
            "mode_shift_GeV": (mode_after - mode_before) if (mode_before is not None and mode_after is not None) else None,
            "sigma_eff68_relative_change_pct": (
                100.0 * (sigma_after - sigma_before) / sigma_before
                if sigma_before not in (None, 0) and sigma_after is not None else None
            ),
        }

    result = {
        "limitation": (
            "PV_npvsGood is the number of RECONSTRUCTED good primary vertices, "
            "not the true number of pileup interactions (Pileup_nTrueInt, MC "
            "truth only). Reweighting on this reconstructed proxy is the "
            "standard fallback when no official pileup JSON exists for a "
            "dataset, but it inherits any data/MC mismodeling of vertex-"
            "reconstruction efficiency itself."
        ),
        "weight_derivation": (
            "w(n) = normalized_data_sideband_fraction(n) / normalized_MC_fraction(n), "
            "integer PV_npvsGood bins 0..60, per signal label separately. Bins "
            "with <20 raw (unweighted) MC entries get weight=1.0 (no "
            "reweighting -- not enough MC statistics to trust a ratio there); "
            "every weight is clipped to [0.1, 5.0]."
        ),
        "ggh_selection_efficiency_effect": {
            "genEventSumw_over_processed_files": genEventSumw_ggh,
            "sum_genWeight_selected_before": sum_gw_before,
            "sum_genWeight_selected_after_pu_reweight": sum_gw_after,
            "efficiency_before": eff_before,
            "efficiency_after_pu_reweight": eff_after,
            "relative_change_pct": 100.0 * (eff_after - eff_before) / eff_before,
        },
        "ggh_peak_and_sigma_eff_per_category_before_vs_after": per_category,
        "per_label_low_stat_fallback_bin_counts": {
            label: all_weights[label]["diagnostics"]["n_low_stat_fallback_bins"]
            for label in common.SIGNAL_LABELS
        },
        "plots": ["part_d_pileup_matching.png"],
    }
    (OUT_DIR / "part_d_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'part_d_results.json'}, {OUT_DIR / 'part_d_pileup_weights.json'}, and plot to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
