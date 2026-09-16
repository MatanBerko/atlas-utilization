"""
Implementation task 6, Part 4, item 2(b): diphoton-trigger efficiency,
measured with an orthogonal probe.

Sub-sample: HLT_Ele27_WPTight_Gsf-fired events with offline m_ee > 95 GeV
(comfortably above the diphoton trigger's own online Mass90 turn-on
region). Reports the fraction of these events for which the diphoton
trigger bit ALSO fired -- data vs DY, per category -- with a binomial
uncertainty on each fraction.

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


def binomial_uncertainty(k: int, n: int) -> float:
    if n == 0:
        return float("nan")
    p = k / n
    return float(np.sqrt(p * (1 - p) / n))


def trigger_efficiency_per_category(arr, weights=None) -> dict:
    mask = zc.trigger_eff_probe_mask(arr)
    cat = np.asarray(arr["category"])[mask]
    diphoton = np.asarray(arr[zc.DIPHOTON_FIELD])[mask].astype(bool)
    w = np.asarray(weights)[mask] if weights is not None else np.ones(mask.sum())

    out = {}
    for c in zc.CATEGORIES:
        sel = zc.category_mask(cat, c)
        n = int(sel.sum())
        n_pass = int(diphoton[sel].sum())
        # Weighted efficiency (weights=1 for data -- plain binomial; DY
        # uses genWeight so a weighted fraction + a raw-count-based
        # binomial uncertainty as an approximation, noted explicitly).
        eff = float(w[sel][diphoton[sel]].sum() / w[sel].sum()) if n > 0 and w[sel].sum() != 0 else None
        out[c] = {
            "n_probe": n, "n_diphoton_fired": n_pass,
            "efficiency": eff,
            "efficiency_binomial_uncertainty_unweighted_approx": binomial_uncertainty(n_pass, n),
        }
    return out


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data_arr = zc.load_zee_data()
    dy_arr = zc.load_zee_dy()

    data_eff = trigger_efficiency_per_category(data_arr)
    dy_eff = trigger_efficiency_per_category(dy_arr, weights=np.asarray(dy_arr["genWeight"]))

    fig, ax = plt.subplots(figsize=(6, 5))
    x = np.arange(len(zc.CATEGORIES))
    width = 0.35
    data_vals = [data_eff[c]["efficiency"] or 0.0 for c in zc.CATEGORIES]
    data_errs = [data_eff[c]["efficiency_binomial_uncertainty_unweighted_approx"] for c in zc.CATEGORIES]
    dy_vals = [dy_eff[c]["efficiency"] or 0.0 for c in zc.CATEGORIES]
    dy_errs = [dy_eff[c]["efficiency_binomial_uncertainty_unweighted_approx"] for c in zc.CATEGORIES]
    ax.bar(x - width / 2, data_vals, width, yerr=data_errs, label="data", color="#1a1a1a", capsize=3)
    ax.bar(x + width / 2, dy_vals, width, yerr=dy_errs, label="DY sim", color="#0072B2", capsize=3)
    ax.set_xticks(x)
    ax.set_xticklabels(zc.CATEGORIES)
    ax.set_ylabel("diphoton trigger efficiency (Ele27 probe, $m_{ee}$>95 GeV)")
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5, axis="y")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "trigger_efficiency.png", dpi=150)
    plt.close(fig)

    result = {
        "selection": "HLT_Ele27_WPTight_Gsf fired, m_ee > 95 GeV; reports fraction with diphoton bit also fired",
        "data": data_eff, "dy": dy_eff,
        "plots": ["trigger_efficiency.png"],
    }
    (OUT_DIR / "trigger_efficiency_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'trigger_efficiency_results.json'}")


if __name__ == "__main__":
    main()
