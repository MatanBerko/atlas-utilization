"""
Implementation task 6, Part 4, item 2(a): energy-scale/resolution check.

Sub-sample: HLT_Ele27_WPTight_Gsf-fired events, 70-110 GeV, per category
(EBEB/notEBEB) -- clean of the Mass90-sculpting bug by construction (see
zee/common.py's energy_scale_selection_mask docstring).

PRE-SET agreement criteria (stated here AND in ZEE_RUN_README.md BEFORE
any pilot has run -- do not change after seeing results):
  - peak position: data vs DY within 0.5% relative
  - sigma_eff68 (width): data vs DY within 10% relative

NOT run yet -- no Z->ee cluster output exists. Ready to run once
merge_zee_outputs.py's output is copied locally (HGG_ZEE_MERGED_DIR).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from studies.hgg_cms.validation.zee import common as zc

OUT_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = OUT_DIR / "plots"


def compare_peak_and_width(data_arr, dy_arr) -> dict:
    data_mask = zc.energy_scale_selection_mask(data_arr)
    dy_mask = zc.energy_scale_selection_mask(dy_arr)

    data_cat = np.asarray(data_arr["category"])[data_mask]
    data_mee = np.asarray(data_arr["m_ee"])[data_mask]
    dy_cat = np.asarray(dy_arr["category"])[dy_mask]
    dy_mee = np.asarray(dy_arr["m_ee"])[dy_mask]
    dy_gw = np.asarray(dy_arr["genWeight"])[dy_mask]

    per_category = {}
    for cat in zc.CATEGORIES:
        d_sel = zc.category_mask(data_cat, cat)
        s_sel = zc.category_mask(dy_cat, cat)

        d_mode, d_sigma = zc.peak_and_width(data_mee[d_sel])
        s_mode, s_sigma = zc.peak_and_width(dy_mee[s_sel], dy_gw[s_sel])

        peak_rel_diff = zc.relative_difference(d_mode, s_mode) if (d_mode and s_mode) else None
        sigma_rel_diff = zc.relative_difference(d_sigma, s_sigma) if (d_sigma and s_sigma) else None

        peak_ok = (peak_rel_diff is not None) and (abs(peak_rel_diff) <= zc.PEAK_POSITION_AGREEMENT_REL_TOL)
        sigma_ok = (sigma_rel_diff is not None) and (abs(sigma_rel_diff) <= zc.SIGMA_EFF_AGREEMENT_REL_TOL)

        per_category[cat] = {
            "n_data": int(d_sel.sum()), "n_dy": int(s_sel.sum()),
            "data_peak_GeV": d_mode, "data_sigma_eff68_GeV": d_sigma,
            "dy_peak_GeV": s_mode, "dy_sigma_eff68_GeV": s_sigma,
            "peak_relative_difference": peak_rel_diff,
            "sigma_eff68_relative_difference": sigma_rel_diff,
            "peak_agreement_pass": peak_ok,
            "sigma_eff68_agreement_pass": sigma_ok,
            "overall_pass": bool(peak_ok and sigma_ok),
        }
    return per_category


def make_plot(data_arr, dy_arr, per_category: dict):
    data_mask = zc.energy_scale_selection_mask(data_arr)
    dy_mask = zc.energy_scale_selection_mask(dy_arr)
    data_cat = np.asarray(data_arr["category"])[data_mask]
    data_mee = np.asarray(data_arr["m_ee"])[data_mask]
    dy_cat = np.asarray(dy_arr["category"])[dy_mask]
    dy_mee = np.asarray(dy_arr["m_ee"])[dy_mask]
    dy_gw = np.asarray(dy_arr["genWeight"])[dy_mask]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    bins = np.arange(zc.ENERGY_SCALE_MASS_LO, zc.ENERGY_SCALE_MASS_HI + 0.5, 0.5)
    for ax, cat in zip(axes, zc.CATEGORIES):
        d_sel = zc.category_mask(data_cat, cat)
        s_sel = zc.category_mask(dy_cat, cat)
        ax.hist(data_mee[d_sel], bins=bins, density=True, histtype="step", color="#1a1a1a",
                linewidth=1.3, label="data (Ele27)")
        ax.hist(dy_mee[s_sel], bins=bins, density=True, histtype="step", color="#0072B2",
                linewidth=1.3, weights=dy_gw[s_sel], label="DY sim (Ele27, genWeight-wtd)")
        info = per_category[cat]
        ax.set_title(f"{cat}: peak {info['data_peak_GeV']:.2f}/{info['dy_peak_GeV']:.2f} GeV, "
                     f"$\\sigma_{{eff68}}$ {info['data_sigma_eff68_GeV']:.2f}/"
                     f"{info['dy_sigma_eff68_GeV']:.2f} GeV", fontsize=9)
        ax.set_xlabel("$m_{ee}$ [GeV]")
        ax.set_ylabel("normalized")
        ax.grid(alpha=0.25, linewidth=0.5)
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle("Energy scale/resolution: data vs DY, Ele27-fired, 70-110 GeV")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "energy_scale.png", dpi=150)
    plt.close(fig)


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data_arr = zc.load_zee_data()
    dy_arr = zc.load_zee_dy()

    per_category = compare_peak_and_width(data_arr, dy_arr)
    make_plot(data_arr, dy_arr, per_category)

    result = {
        "pre_set_criteria": {
            "peak_position_agreement_rel_tol": zc.PEAK_POSITION_AGREEMENT_REL_TOL,
            "sigma_eff_agreement_rel_tol": zc.SIGMA_EFF_AGREEMENT_REL_TOL,
        },
        "selection": "HLT_Ele27_WPTight_Gsf fired, 70 < m_ee < 110 GeV",
        "per_category": per_category,
        "overall_pass": all(v["overall_pass"] for v in per_category.values()),
        "plots": ["energy_scale.png"],
    }
    (OUT_DIR / "energy_scale_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'energy_scale_results.json'}")


if __name__ == "__main__":
    main()
