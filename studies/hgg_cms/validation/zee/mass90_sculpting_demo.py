"""
Implementation task 6, Part 4, item 2(c): demonstration of the Mass90
sculpting bug that motivated this task's first revision -- NOT used for
any pre-set pass/fail criterion, just a plot + counts showing the effect
directly.

REVISED (16 Sep 2026, second revision): **DY-only now**, not data. Data's
own config (config.cms_hgg_zee_data.yaml, SingleElectron records)
filters on `HLT_Ele27_WPTight_Gsf` ALONE -- by construction, EVERY stored
data event already has Ele27 fired, so there is no "diphoton fired,
Ele27 NOT fired" data subset left to demonstrate anything with (that
subset is empty in the stored data table, always). DY's own config
deliberately keeps the BROADER "either trigger fired" filter (simulation
has no dataset-streaming bias to worry about, so there was never a
reason to narrow it there -- see config.cms_hgg_zee_dy.yaml's own
comment), so DY alone retains both populations needed for this
demonstration.

Sub-sample (DY only): events where the diphoton trigger fired but
HLT_Ele27_WPTight_Gsf did NOT, 70-110 GeV. Expected: visibly depleted
below ~90 GeV relative to the Ele27-triggered (unbiased) sample from
2(a)'s own DY population.

REVISED AGAIN (17 Sep 2026): DY weighted by genWeight * the item-1
pileup weight throughout (pileup.py must be run first).
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


def make_plot(dy_arr, pu_edges, pu_weights) -> dict:
    diph_only = zc.diphoton_only_mask(dy_arr)
    unbiased = zc.energy_scale_selection_mask(dy_arr)
    mee_d = np.asarray(dy_arr["m_ee"])[diph_only]
    mee_u = np.asarray(dy_arr["m_ee"])[unbiased]
    pv_d = np.asarray(dy_arr["PV_npvsGood"])[diph_only]
    pv_u = np.asarray(dy_arr["PV_npvsGood"])[unbiased]
    # PU weights applied to DY throughout (item 1's own instruction) --
    # this demo's own point (Mass90 sculpting) has nothing to do with
    # pileup, but the weighting is applied for consistency across every
    # Z->ee plot/number in this validation round.
    w_d = np.asarray(dy_arr["genWeight"])[diph_only] * main_common.apply_pileup_weight(pv_d, pu_edges, pu_weights)
    w_u = np.asarray(dy_arr["genWeight"])[unbiased] * main_common.apply_pileup_weight(pv_u, pu_edges, pu_weights)

    bins = np.arange(zc.ENERGY_SCALE_MASS_LO, zc.ENERGY_SCALE_MASS_HI + 1.0, 1.0)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(mee_u, bins=bins, density=True, histtype="step", color="#1a1a1a", linewidth=1.4,
            weights=w_u, label="Ele27-fired (unbiased, 2a's DY sample)")
    ax.hist(mee_d, bins=bins, density=True, histtype="step", color="#D55E00", linewidth=1.4,
            weights=w_d, label="diphoton-fired, Ele27 NOT fired\n(the biased population the first revision's bug would have used)")
    ax.axvline(90.0, color="#999999", linestyle=":", linewidth=1.0)
    ax.set_xlabel("$m_{ee}$ [GeV]")
    ax.set_ylabel("normalized")
    ax.set_title("Mass90 sculpting demonstration (DY simulation only)")
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "mass90_sculpting_demo.png", dpi=150)
    plt.close(fig)

    below_90 = int(((mee_d > zc.ENERGY_SCALE_MASS_LO) & (mee_d < 90.0)).sum())
    above_90 = int(((mee_d >= 90.0) & (mee_d < zc.ENERGY_SCALE_MASS_HI)).sum())
    return {
        "n_diphoton_only_70_90": below_90,
        "n_diphoton_only_90_110": above_90,
        "ratio_below_over_above": (below_90 / above_90) if above_90 else None,
        "n_unbiased_ele27_fired": int(unbiased.sum()),
    }


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    dy_arr = zc.load_zee_dy()
    pu = json.loads((OUT_DIR / "pileup_weights.json").read_text(encoding="utf-8"))
    pu_edges = np.array(pu["bin_edges"])
    pu_weights = np.array(pu["weights"])

    counts = make_plot(dy_arr, pu_edges, pu_weights)

    result = {
        "note": (
            "DY-only (see this module's own docstring for why data no "
            "longer has a meaningful diphoton-only sub-sample). Not a "
            "pass/fail check -- a visual + count demonstration of the bug "
            "this task's first revision fixed. Expected: the diphoton"
            "-only-triggered sample shows visibly fewer events below "
            "~90 GeV than the Ele27-triggered (unbiased) sample."
        ),
        "counts": counts,
        "plots": ["mass90_sculpting_demo.png"],
    }
    (OUT_DIR / "mass90_sculpting_demo_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'mass90_sculpting_demo_results.json'}")


if __name__ == "__main__":
    main()
