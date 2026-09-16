"""
Implementation task 6, Part 4, item 2(c): demonstration of the Mass90
sculpting bug that motivated this revision -- NOT used for any pre-set
pass/fail criterion, just a plot + counts showing the effect directly.

Sub-sample: events where the diphoton trigger fired but
HLT_Ele27_WPTight_Gsf did NOT, 70-110 GeV (exactly the population the
earlier, buggy diphoton-trigger-only design would have used for the
energy-scale comparison). Expected: visibly depleted below ~90 GeV
relative to the Ele27-triggered (unbiased) sample from 2(a).

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


def make_plot(data_arr, dy_arr) -> dict:
    diphoton_only_mask_data = zc.diphoton_only_mask(data_arr)
    unbiased_mask_data = zc.energy_scale_selection_mask(data_arr)  # Ele27-fired, 70-110

    mee_diphoton_only = np.asarray(data_arr["m_ee"])[diphoton_only_mask_data]
    mee_unbiased = np.asarray(data_arr["m_ee"])[unbiased_mask_data]

    bins = np.arange(zc.ENERGY_SCALE_MASS_LO, zc.ENERGY_SCALE_MASS_HI + 1.0, 1.0)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, (arr, title) in zip(axes, [(data_arr, "data"), (dy_arr, "DY sim")]):
        diph_only = zc.diphoton_only_mask(arr)
        unbiased = zc.energy_scale_selection_mask(arr)
        mee_d = np.asarray(arr["m_ee"])[diph_only]
        mee_u = np.asarray(arr["m_ee"])[unbiased]
        w_d = np.ones(diph_only.sum()) if title == "data" else np.asarray(arr["genWeight"])[diph_only]
        w_u = np.ones(unbiased.sum()) if title == "data" else np.asarray(arr["genWeight"])[unbiased]

        ax.hist(mee_u, bins=bins, density=True, histtype="step", color="#1a1a1a", linewidth=1.3,
                weights=w_u, label="Ele27-fired (unbiased, 2a's sample)")
        ax.hist(mee_d, bins=bins, density=True, histtype="step", color="#D55E00", linewidth=1.3,
                weights=w_d, label="diphoton-fired, Ele27 NOT fired\n(would have been used by the buggy design)")
        ax.axvline(90.0, color="#999999", linestyle=":", linewidth=1.0)
        ax.set_title(title)
        ax.set_xlabel("$m_{ee}$ [GeV]")
        ax.set_ylabel("normalized")
        ax.grid(alpha=0.25, linewidth=0.5)
    axes[0].legend(fontsize=7, frameon=False)
    fig.suptitle("Mass90 sculpting demonstration: diphoton-only-triggered vs Ele27-triggered, 70-110 GeV")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "mass90_sculpting_demo.png", dpi=150)
    plt.close(fig)

    counts = {}
    for label, arr in [("data", data_arr), ("dy", dy_arr)]:
        diph_only = zc.diphoton_only_mask(arr)
        mee = np.asarray(arr["m_ee"])[diph_only]
        below_90 = int(((mee > zc.ENERGY_SCALE_MASS_LO) & (mee < 90.0)).sum())
        above_90 = int(((mee >= 90.0) & (mee < zc.ENERGY_SCALE_MASS_HI)).sum())
        counts[label] = {
            "n_diphoton_only_70_90": below_90,
            "n_diphoton_only_90_110": above_90,
            "ratio_below_over_above": (below_90 / above_90) if above_90 else None,
        }
    return counts


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data_arr = zc.load_zee_data()
    dy_arr = zc.load_zee_dy()

    counts = make_plot(data_arr, dy_arr)

    result = {
        "note": (
            "Not a pass/fail check -- a visual + count demonstration of "
            "the bug this task's revision fixed. Expected: the diphoton"
            "-only-triggered sample shows visibly fewer events below "
            "~90 GeV than the Ele27-triggered (unbiased) sample, i.e. "
            "ratio_below_over_above should be LOWER for the diphoton-only "
            "sample than a comparable ratio computed from the unbiased "
            "2(a) sample would be."
        ),
        "counts": counts,
        "plots": ["mass90_sculpting_demo.png"],
    }
    (OUT_DIR / "mass90_sculpting_demo_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'mass90_sculpting_demo_results.json'}")


if __name__ == "__main__":
    main()
