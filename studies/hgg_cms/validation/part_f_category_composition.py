"""
Implementation task 6, Part 3F: category composition (EBEB vs notEBEB),
data sidebands vs signal; and signal per-category mode/sigma_eff68 with
ALL SIX modes combined, weighted by each event's actual contribution to
the expected yield (genWeight * sigma*1000*BR*L/genEventSumw_processed --
i.e. the SAME per-event weight Part E sums to get N_expected -- so ggH,
being by far the largest expected contribution, dominates the combined
shape, as it physically should).

Requires Part E to have already run (reuses GENEVENTSUMW_PROCESSED from
it, not a re-derivation).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from studies.hgg_cms.validation import common
from studies.hgg_cms.validation.part_e_expected_yields import GENEVENTSUMW_PROCESSED

OUT_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = OUT_DIR / "plots"


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data = common.load_data_sidebands()
    data_cat = np.asarray(data["category"])
    n_data_total = len(data)
    data_frac = {
        c: {"n": int(common.category_mask(data_cat, c).sum()),
            "fraction": float(common.category_mask(data_cat, c).sum()) / n_data_total}
        for c in common.CATEGORIES
    }

    all_mgg = {c: [] for c in common.CATEGORIES}
    all_w = {c: [] for c in common.CATEGORIES}
    per_label_n = {}

    for label in common.SIGNAL_LABELS:
        s = common.load_signal(label)
        gw = np.asarray(s["genWeight"])
        mgg = np.asarray(s["m_gg"])
        cat = np.asarray(s["category"])
        scale = common.SIGNAL_CROSS_SECTIONS_PB[label] * 1000.0 * common.BR_HGG * common.LUMI_FB / GENEVENTSUMW_PROCESSED[label]
        w = gw * scale
        per_label_n[label] = int(len(s))
        for c in common.CATEGORIES:
            m = common.category_mask(cat, c)
            all_mgg[c].append(mgg[m])
            all_w[c].append(w[m])

    signal_yield_per_cat = {c: float(np.sum(np.concatenate(all_w[c]))) for c in common.CATEGORIES}
    total_signal_yield = sum(signal_yield_per_cat.values())
    signal_frac = {c: {"N_expected": signal_yield_per_cat[c], "fraction": signal_yield_per_cat[c] / total_signal_yield}
                   for c in common.CATEGORIES}

    combined_shape = {}
    for c in common.CATEGORIES:
        mgg_c = np.concatenate(all_mgg[c])
        w_c = np.concatenate(all_w[c])
        mode, sigma68 = common.weighted_mode_and_sigma68(mgg_c, w_c)
        combined_shape[c] = {
            "n_events_pooled_all_modes": int(len(mgg_c)),
            "mode_GeV": mode, "sigma_eff68_GeV": sigma68,
        }

    # ---- Plot 1: category composition, data vs signal ----
    fig, ax = plt.subplots(figsize=(6, 5))
    x = np.arange(2)
    width = 0.35
    ax.bar(x - width / 2, [data_frac[c]["fraction"] for c in common.CATEGORIES], width,
           label="data sidebands", color="#1a1a1a")
    ax.bar(x + width / 2, [signal_frac[c]["fraction"] for c in common.CATEGORIES], width,
           label="signal (expected-yield wtd)", color="#0072B2")
    ax.set_xticks(x)
    ax.set_xticklabels(common.CATEGORIES)
    ax.set_ylabel("fraction")
    ax.set_title("Category composition: data sidebands vs signal")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5, axis="y")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "part_f_category_composition.png", dpi=150)
    plt.close(fig)

    # ---- Plot 2: combined-signal (all modes, expected-yield weighted) m_gg shape per category ----
    fig, ax = plt.subplots(figsize=(8, 5))
    bins = np.arange(110, 140.5, 0.5)
    for c, color in zip(common.CATEGORIES, ["#0072B2", "#D55E00"]):
        mgg_c = np.concatenate(all_mgg[c])
        w_c = np.concatenate(all_w[c])
        ax.hist(mgg_c, bins=bins, weights=w_c, histtype="step", linewidth=1.4, color=color,
                label=f"{c} (mode={combined_shape[c]['mode_GeV']:.2f}, "
                      f"$\\sigma_{{eff68}}$={combined_shape[c]['sigma_eff68_GeV']:.2f} GeV)")
    ax.set_xlabel("$m_{\\gamma\\gamma}$ [GeV]")
    ax.set_ylabel("expected events / 0.5 GeV")
    ax.set_title("Combined signal (all 6 modes, expected-yield weighted) shape per category")
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "part_f_combined_signal_shape.png", dpi=150)
    plt.close(fig)

    result = {
        "n_data_sidebands_total": n_data_total,
        "data_category_composition": data_frac,
        "signal_category_composition_expected_yield_weighted": signal_frac,
        "note_signal_composition": (
            "Signal composition is weighted by each event's contribution to "
            "the expected yield (genWeight * sigma*1000*BR*L/genEventSumw), "
            "not raw event counts -- so it reflects the physical mixture of "
            "the 6 production modes, dominated by ggH, not this run's "
            "arbitrary per-mode statistics."
        ),
        "signal_combined_all_modes_mode_and_sigma_eff68_per_category": combined_shape,
        "per_label_n_selected": per_label_n,
    }
    (OUT_DIR / "part_f_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'part_f_results.json'}")


if __name__ == "__main__":
    main()
