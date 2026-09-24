"""
Implementation task 6, Part 3A: data-sideband histograms (full statistics)
+ photon-kinematics shape comparison against ggH simulation.

Pre-set scope (do not change after seeing results): m_gg in 1 GeV bins
over [100,115) u (135,180], inclusive and per category (EBEB/notEBEB);
counts per category; lead/sublead pt, eta, r9, mvaID in data sidebands vs
ggH simulation, SHAPE-NORMALIZED (density=True) -- ggH is compared over
its full selected sample (not restricted to the sideband m_gg range),
since this is a photon-kinematics shape check, not an m_gg check. No fits
here (Part B does the one pre-set exploratory fit this task allows).
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

DATA_COLOR = "#1a1a1a"
SIGNAL_COLOR = "#0072B2"  # Okabe-Ito blue
BLIND_BAND_COLOR = "#bdbdbd"
CAT_COLORS = {"EBEB": "#0072B2", "notEBEB": "#D55E00"}  # Okabe-Ito blue/vermillion

KINEMATIC_VARS = [
    ("lead_pt", "leading photon $p_T$ [GeV]", (20, 200)),
    ("sublead_pt", "subleading photon $p_T$ [GeV]", (20, 150)),
    ("lead_eta", "leading photon $\\eta$", (-2.5, 2.5)),
    ("sublead_eta", "subleading photon $\\eta$", (-2.5, 2.5)),
    ("lead_r9", "leading photon $R_9$", (0.0, 1.1)),
    ("sublead_r9", "subleading photon $R_9$", (0.0, 1.1)),
    ("lead_mvaID", "leading photon MVA ID", (-1.0, 1.0)),
    ("sublead_mvaID", "subleading photon MVA ID", (-1.0, 1.0)),
]


def _mgg_hist(ax, mgg_lo, mgg, label, color, weights=None):
    bins = np.arange(mgg_lo[0], mgg_lo[1] + 1, 1.0)
    ax.hist(mgg, bins=bins, histtype="step", color=color, linewidth=1.3,
            label=label, weights=weights)


def make_mgg_panels(data):
    mgg = np.asarray(data["m_gg"])
    cat = np.asarray(data["category"])

    fig, axes = plt.subplots(3, 1, figsize=(8, 10), sharex=True)
    bins = np.arange(common.SIDEBAND_LO, common.SIDEBAND_HI + 1, 1.0)

    for ax, (title, sel) in zip(
        axes,
        [("Inclusive", np.ones(len(mgg), dtype=bool)),
         ("EBEB", cat == "EBEB"),
         ("notEBEB", cat != "EBEB")],
    ):
        ax.axvspan(common.BLIND_LO, common.BLIND_HI, color=BLIND_BAND_COLOR, alpha=0.6,
                   label="blinded (115-135 GeV)" if title == "Inclusive" else None)
        counts, edges = np.histogram(mgg[sel], bins=bins)
        centers = 0.5 * (edges[:-1] + edges[1:])
        ax.errorbar(centers, counts, yerr=np.sqrt(counts), fmt="o", color=DATA_COLOR,
                    markersize=2.5, elinewidth=0.8, capsize=0, label="data" if title == "Inclusive" else None)
        ax.set_ylabel("events / GeV")
        ax.set_title(f"{title} (n={int(sel.sum())})", fontsize=10, loc="left")
        ax.grid(alpha=0.25, linewidth=0.5)

    axes[-1].set_xlabel("$m_{\\gamma\\gamma}$ [GeV]")
    axes[0].legend(loc="upper right", fontsize=8, frameon=False)
    fig.suptitle("Data sidebands: $m_{\\gamma\\gamma}$, 1 GeV bins (blinded band shown empty)")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "part_a_mgg_panels.png", dpi=150)
    plt.close(fig)


def make_kinematics_grid(data, signal):
    d_sel = common.sideband_mask(np.asarray(data["m_gg"]))
    fig, axes = plt.subplots(2, 4, figsize=(18, 8))
    diffs = {}
    for ax, (field, xlabel, xrange) in zip(axes.flat, KINEMATIC_VARS):
        d_vals = np.asarray(data[field])[d_sel]
        s_vals = np.asarray(signal[field])
        s_w = np.asarray(signal["genWeight"])
        bins = np.linspace(xrange[0], xrange[1], 41)
        ax.hist(d_vals, bins=bins, density=True, histtype="step", color=DATA_COLOR,
                linewidth=1.3, label="data sidebands")
        ax.hist(s_vals, bins=bins, density=True, histtype="step", color=SIGNAL_COLOR,
                linewidth=1.3, label="ggH sim (genWeight-wtd)", weights=s_w)
        ax.set_xlabel(xlabel, fontsize=9)
        ax.set_ylabel("normalized", fontsize=9)
        ax.grid(alpha=0.25, linewidth=0.5)
        ax.tick_params(labelsize=8)

        diffs[field] = {
            "data_median": float(np.median(d_vals)), "data_mean": float(np.mean(d_vals)),
            "data_std": float(np.std(d_vals)),
            "ggh_median": float(np.median(s_vals)),
            "ggh_mean_weighted": float(np.average(s_vals, weights=s_w)),
            "ggh_std": float(np.std(s_vals)),
        }
    axes.flat[0].legend(loc="best", fontsize=8, frameon=False)
    fig.suptitle("Photon kinematics: data sidebands vs ggH simulation (shape-normalized)")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "part_a_kinematics_grid.png", dpi=150)
    plt.close(fig)
    return diffs


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data = common.load_data_sidebands()
    signal = common.load_signal("ggh")

    mgg = np.asarray(data["m_gg"])
    cat = np.asarray(data["category"])
    n_total = len(data)
    n_eb = int((cat == "EBEB").sum())
    n_not = int((cat != "EBEB").sum())

    make_mgg_panels(data)
    kin_diffs = make_kinematics_grid(data, signal)

    result = {
        "n_data_sidebands_total": n_total,
        "n_data_sidebands_EBEB": n_eb,
        "n_data_sidebands_notEBEB": n_not,
        "n_data_sidebands_100_115": int(((mgg >= 100.0) & (mgg < 115.0)).sum()),
        "n_data_sidebands_135_180": int(((mgg > 135.0) & (mgg <= 180.0)).sum()),
        "kinematics_data_vs_ggh": kin_diffs,
        "plots": ["part_a_mgg_panels.png", "part_a_kinematics_grid.png"],
    }
    (OUT_DIR / "part_a_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'part_a_results.json'} and plots to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
