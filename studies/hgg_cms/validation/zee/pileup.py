"""
Implementation task 6, Z->ee validation follow-up (17 Sep 2026), item 1:
data/DY PV_npvsGood pileup weights for THIS sample, same method as
VALIDATION_REPORT_1 Part D (studies.hgg_cms.validation.common.
derive_pileup_weights, reused unchanged).

data side: ALL stored data events (Ele27-fired by construction, 60-180
GeV -- no "signal-free" subselection needed here, unlike the H->gamma-gamma
sidebands, since there is no blinded region in this sample at all).
DY side: DY's own Ele27-fired subset ONLY (not the broader "either
trigger" stored population) -- an apples-to-apples match to data's own
trigger condition, so the derived PV profile isn't contaminated by the
diphoton-only-triggered DY events, which are a different (and,
per the Mass90-sculpting finding, differently-shaped) trigger population.

Writes results/pileup_weights.json (bin edges + weights, reused by every
other zee/ script that needs "DY with PU applied") and a comparison plot.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from studies.hgg_cms.validation import common as main_common
from studies.hgg_cms.validation.zee import common as zc

OUT_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = OUT_DIR / "plots"
PV_MAX = 60


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data_arr = zc.load_zee_data()
    dy_arr = zc.load_zee_dy()

    data_pv = np.asarray(data_arr["PV_npvsGood"])

    dy_ele27 = np.asarray(dy_arr[zc.ELE27_FIELD]).astype(bool)
    dy_pv = np.asarray(dy_arr["PV_npvsGood"])[dy_ele27]
    dy_gw = np.asarray(dy_arr["genWeight"])[dy_ele27]

    edges, weights, diag = main_common.derive_pileup_weights(data_pv, dy_pv, dy_gw, pv_max=PV_MAX)

    result = {
        "pv_max": PV_MAX,
        "n_data": int(len(data_pv)),
        "n_dy_ele27_fired": int(dy_ele27.sum()),
        "bin_edges": edges.tolist(),
        "weights": weights.tolist(),
        "diagnostics": diag,
        "weight_derivation": (
            "w(n) = normalized_data_fraction(n) / normalized_DY_fraction(n), "
            "integer PV_npvsGood bins 0..60. data = ALL stored data events "
            "(Ele27-fired by construction). DY = DY's own Ele27-fired "
            "subset only (matches data's trigger condition -- excludes "
            "the diphoton-only-triggered DY population, a different, "
            "differently-shaped trigger population per the Mass90-"
            "sculpting finding). Bins with <20 raw DY entries get w=1 "
            "(no reweighting); every weight clipped to [0.1, 5.0]."
        ),
    }
    (OUT_DIR / "pileup_weights.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    # ---- Plot ----
    centers = 0.5 * (edges[:-1] + edges[1:])
    data_hist, _ = np.histogram(data_pv, bins=edges)
    data_hist = data_hist / data_hist.sum()
    dy_hist, _ = np.histogram(dy_pv, bins=edges, weights=dy_gw)
    dy_hist = dy_hist / dy_hist.sum()
    dy_w = main_common.apply_pileup_weight(dy_pv, edges, weights)
    dy_hist_rw, _ = np.histogram(dy_pv, bins=edges, weights=dy_gw * dy_w)
    dy_hist_rw = dy_hist_rw / dy_hist_rw.sum()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.step(centers, data_hist, where="mid", color="#1a1a1a", linewidth=1.4, label="data (Ele27)")
    ax.step(centers, dy_hist, where="mid", color="#D55E00", linewidth=1.1, linestyle="--", label="DY (Ele27), raw")
    ax.step(centers, dy_hist_rw, where="mid", color="#0072B2", linewidth=1.4, label="DY (Ele27), PU-reweighted")
    ax.set_xlabel("PV_npvsGood")
    ax.set_ylabel("normalized")
    ax.set_title("Z->ee pileup matching: data vs DY (Ele27-fired)")
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "pileup_matching.png", dpi=150)
    plt.close(fig)

    print(json.dumps({k: v for k, v in result.items() if k != "bin_edges" and k != "weights"}, indent=2))
    print(f"\nwrote {OUT_DIR / 'pileup_weights.json'} and plot to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
