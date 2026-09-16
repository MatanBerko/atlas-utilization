"""
Implementation task 6, Z->ee validation follow-up (17 Sep 2026), item 4:
diphoton-trigger efficiency, measured with the Ele27 orthogonal probe.

Sub-sample: HLT_Ele27_WPTight_Gsf-fired events with offline m_ee > 95 GeV.
Reports the fraction of these events for which the diphoton trigger bit
ALSO fired -- data vs DY (both without and with the item-1 pileup
weights), per category and inclusive, with binomial uncertainties and
the data/DY ratio.

Report only -- no pass/fail (per this task's own instruction).
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


def binomial_uncertainty(k: int, n: int) -> float:
    if n == 0:
        return float("nan")
    p = k / n
    return float(np.sqrt(p * (1 - p) / n))


def weighted_efficiency(diphoton_mask: np.ndarray, weights: np.ndarray) -> dict:
    """Weighted "fraction fired" plus its uncertainty computed by
    treating the weighted numerator/denominator as an effective binomial
    with N_eff = (Sum w)^2 / Sum w^2 (standard effective-sample-size
    approximation for a weighted efficiency)."""
    w = np.asarray(weights)
    total_w = w.sum()
    if total_w == 0:
        return {"efficiency": None, "uncertainty": None, "n_eff": None}
    eff = float(w[diphoton_mask].sum() / total_w)
    sumw2 = float(np.sum(w ** 2))
    n_eff = float(total_w ** 2 / sumw2) if sumw2 > 0 else None
    unc = float(np.sqrt(eff * (1 - eff) / n_eff)) if n_eff else None
    return {"efficiency": eff, "uncertainty": unc, "n_eff": n_eff}


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data_arr = zc.load_zee_data()
    dy_arr = zc.load_zee_dy()

    pu = json.loads((OUT_DIR / "pileup_weights.json").read_text(encoding="utf-8"))
    pu_edges = np.array(pu["bin_edges"])
    pu_weights = np.array(pu["weights"])

    data_probe = zc.trigger_eff_probe_mask(data_arr)
    dy_probe = zc.trigger_eff_probe_mask(dy_arr)

    data_cat = np.asarray(data_arr["category"])[data_probe]
    data_diphoton = np.asarray(data_arr[zc.DIPHOTON_FIELD])[data_probe].astype(bool)

    dy_cat = np.asarray(dy_arr["category"])[dy_probe]
    dy_diphoton = np.asarray(dy_arr[zc.DIPHOTON_FIELD])[dy_probe].astype(bool)
    dy_gw = np.asarray(dy_arr["genWeight"])[dy_probe]
    dy_pv = np.asarray(dy_arr["PV_npvsGood"])[dy_probe]
    dy_puw = main_common.apply_pileup_weight(dy_pv, pu_edges, pu_weights)

    cats = ["inclusive"] + zc.CATEGORIES
    per_category = {}
    for cat in cats:
        if cat == "inclusive":
            d_sel = np.ones(len(data_cat), dtype=bool)
            s_sel = np.ones(len(dy_cat), dtype=bool)
        else:
            d_sel = zc.category_mask(data_cat, cat)
            s_sel = zc.category_mask(dy_cat, cat)

        n_data = int(d_sel.sum())
        n_data_fired = int(data_diphoton[d_sel].sum())
        eff_data = n_data_fired / n_data if n_data else None
        unc_data = binomial_uncertainty(n_data_fired, n_data)

        eff_dy_nopu = weighted_efficiency(dy_diphoton[s_sel], dy_gw[s_sel])
        eff_dy_pu = weighted_efficiency(dy_diphoton[s_sel], (dy_gw * dy_puw)[s_sel])

        def ratio_with_unc(e_num, u_num, e_den, u_den):
            if not e_den:
                return None, None
            ratio = e_num / e_den
            rel_unc = np.sqrt((u_num / e_num) ** 2 + (u_den / e_den) ** 2) if e_num and u_num and u_den else None
            return float(ratio), (float(ratio * rel_unc) if rel_unc is not None else None)

        ratio_pu, ratio_pu_unc = ratio_with_unc(eff_data, unc_data, eff_dy_pu["efficiency"], eff_dy_pu["uncertainty"])
        ratio_nopu, ratio_nopu_unc = ratio_with_unc(eff_data, unc_data, eff_dy_nopu["efficiency"], eff_dy_nopu["uncertainty"])

        per_category[cat] = {
            "n_probe_data": n_data, "n_diphoton_fired_data": n_data_fired,
            "efficiency_data": eff_data, "efficiency_data_uncertainty": unc_data,
            "efficiency_dy_no_pu": eff_dy_nopu["efficiency"], "efficiency_dy_no_pu_uncertainty": eff_dy_nopu["uncertainty"],
            "efficiency_dy_with_pu": eff_dy_pu["efficiency"], "efficiency_dy_with_pu_uncertainty": eff_dy_pu["uncertainty"],
            "ratio_data_over_dy_no_pu": ratio_nopu, "ratio_data_over_dy_no_pu_uncertainty": ratio_nopu_unc,
            "ratio_data_over_dy_with_pu": ratio_pu, "ratio_data_over_dy_with_pu_uncertainty": ratio_pu_unc,
        }

    fig, ax = plt.subplots(figsize=(7, 5))
    x = np.arange(len(cats))
    width = 0.3
    data_vals = [per_category[c]["efficiency_data"] for c in cats]
    data_errs = [per_category[c]["efficiency_data_uncertainty"] for c in cats]
    dy_vals = [per_category[c]["efficiency_dy_with_pu"] for c in cats]
    dy_errs = [per_category[c]["efficiency_dy_with_pu_uncertainty"] for c in cats]
    ax.bar(x - width / 2, data_vals, width, yerr=data_errs, label="data", color="#1a1a1a", capsize=3)
    ax.bar(x + width / 2, dy_vals, width, yerr=dy_errs, label="DY (PU-wtd)", color="#0072B2", capsize=3)
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    ax.set_ylabel("diphoton trigger efficiency\n(Ele27 probe, $m_{ee}$>95 GeV)")
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5, axis="y")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "trigger_efficiency.png", dpi=150)
    plt.close(fig)

    result = {
        "selection": "HLT_Ele27_WPTight_Gsf fired, m_ee > 95 GeV; reports fraction with diphoton bit also fired",
        "implication_for_hgg_expected_yield": (
            "The H->gamma-gamma analysis's own selection REQUIRES this same "
            "diphoton trigger to fire (config.cms_hgg_data.yaml / "
            "config.cms_hgg_signal*.yaml's trigger_requirements). The "
            "signal MC's own expected-yield calculation (VALIDATION_REPORT_1 "
            "Part E) implicitly trusts that MC's own simulated trigger "
            "response matches real data's. If the data/DY ratio measured "
            "here is not 1, that is direct evidence MC over- or under-"
            "estimates the diphoton trigger's real efficiency by "
            "approximately that same fractional amount -- exactly the kind "
            "of trigger scale factor real CMS analyses derive from this "
            "type of tag-and-probe measurement and apply multiplicatively "
            "to the signal MC's expected yield. This task does not apply "
            "any such correction (per its own scope); the ratio below is "
            "the number the signal-model task would need."
        ),
        "per_category": per_category,
        "plots": ["trigger_efficiency.png"],
    }
    (OUT_DIR / "trigger_efficiency_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'trigger_efficiency_results.json'} and plot to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
