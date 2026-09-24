"""
Implementation task 6, Z->ee validation follow-up (17 Sep 2026), item 3:
normalization sanity check.

N_expected(DY) = DY_CROSS_SECTION_PB * 1000 (pb->fb) * L_fb *
                 (Sum genWeight_selected, Ele27-fired, 70-110 GeV, PU
                 -weighted) / Sum(genEventSumw over the 41 processed DY
                 files)
compared against the OBSERVED data count in the identical selection
(Ele27-fired, 70-110 GeV), per category. Ratio = N_data / N_DY.

Expected near 1 but NOT exactly -- no electron/photon-ID or trigger
scale factors are applied anywhere in this task (those are normally
derived FROM exactly this kind of comparison, in a later task). Flagged
only if the ratio falls outside [0.7, 1.3] (pre-set, not tuned to the
result).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from studies.hgg_cms.validation import common as main_common
from studies.hgg_cms.validation.zee import common as zc

OUT_DIR = Path(__file__).resolve().parent / "results"

# Sum of genEventSumw over the 41 processed DY files (parsing_stats'
# sumw_by_record.record_35669.genEventSumw, summed across jobs) --
# VERIFIED fact from this task's own instructions, not re-derived here.
GENEVENTSUMW_DY_PROCESSED = 1_220_934_627_963.07

FLAG_LO, FLAG_HI = 0.7, 1.3


def main():
    data_arr = zc.load_zee_data()
    dy_arr = zc.load_zee_dy()

    pu = json.loads((OUT_DIR / "pileup_weights.json").read_text(encoding="utf-8"))
    pu_edges = np.array(pu["bin_edges"])
    pu_weights = np.array(pu["weights"])

    data_mask = zc.energy_scale_selection_mask(data_arr)
    dy_mask = zc.energy_scale_selection_mask(dy_arr)

    data_cat = np.asarray(data_arr["category"])[data_mask]
    dy_cat = np.asarray(dy_arr["category"])[dy_mask]
    dy_gw = np.asarray(dy_arr["genWeight"])[dy_mask]
    dy_pv = np.asarray(dy_arr["PV_npvsGood"])[dy_mask]
    dy_puw = main_common.apply_pileup_weight(dy_pv, pu_edges, pu_weights)

    scale = zc.DY_CROSS_SECTION_PB * 1000.0 * main_common.LUMI_FB / GENEVENTSUMW_DY_PROCESSED

    per_category = {}
    cats = ["inclusive"] + zc.CATEGORIES
    for cat in cats:
        if cat == "inclusive":
            d_sel = np.ones(len(data_cat), dtype=bool)
            s_sel = np.ones(len(dy_cat), dtype=bool)
        else:
            d_sel = zc.category_mask(data_cat, cat)
            s_sel = zc.category_mask(dy_cat, cat)

        n_data = int(d_sel.sum())
        sum_gw_nopu = float(dy_gw[s_sel].sum())
        sum_gw_pu = float((dy_gw * dy_puw)[s_sel].sum())
        N_dy_nopu = scale * sum_gw_nopu
        N_dy_pu = scale * sum_gw_pu

        ratio_pu = n_data / N_dy_pu if N_dy_pu else None
        ratio_nopu = n_data / N_dy_nopu if N_dy_nopu else None

        per_category[cat] = {
            "n_data_observed": n_data,
            "N_dy_expected_no_pu": N_dy_nopu,
            "N_dy_expected_with_pu": N_dy_pu,
            "ratio_data_over_dy_no_pu": ratio_nopu,
            "ratio_data_over_dy_with_pu": ratio_pu,
            "flagged_outside_0p7_1p3": bool(ratio_pu is not None and not (FLAG_LO <= ratio_pu <= FLAG_HI)),
        }

    result = {
        "selection": "Ele27-fired, 70 < m_ee < 110 GeV",
        "dy_cross_section_pb": zc.DY_CROSS_SECTION_PB,
        "luminosity_fb": main_common.LUMI_FB,
        "genEventSumw_dy_processed": GENEVENTSUMW_DY_PROCESSED,
        "flag_range": [FLAG_LO, FLAG_HI],
        "note": (
            "Ratio expected near 1 but not exactly -- no electron/photon-ID "
            "or trigger scale factors are applied anywhere in this task "
            "(normally derived FROM comparisons like this one, in a later "
            "task). Flagged only if outside [0.7, 1.3], a pre-set range, "
            "not tuned to the result."
        ),
        "per_category": per_category,
    }
    (OUT_DIR / "normalization_check_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'normalization_check_results.json'}")


if __name__ == "__main__":
    main()
