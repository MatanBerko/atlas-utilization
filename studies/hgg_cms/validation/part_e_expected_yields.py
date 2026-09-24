"""
Implementation task 6, Part 3E: expected signal yields (not significance),
per production mode and category, with and without the Part D pileup
weights.

N = sigma * BR(H->gg)=0.00227 * L=16.393380531 fb^-1 *
    (Sum genWeight_selected / genEventSumw_over_processed_files)

Cross sections from signal_sumw.json except ZH (0.7612 pb, qq/qg->ZH
only -- signal_sumw_notes.md), and ttH uses ONLY the full run's own
genEventSumw over its 15 processed files (never signal_sumw.json's stale
16-file total). Requires Part D to have already run (reuses its saved
per-label pileup weights, not a re-derivation).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from studies.hgg_cms.validation import common

OUT_DIR = Path(__file__).resolve().parent / "results"

# genEventSumw_over_processed_files per label, from merge_summary_signal.json
# (the ACTUAL full run's own aggregation over exactly its processed files --
# never signal_sumw.json's "all files in record" table).
GENEVENTSUMW_PROCESSED = {
    "ggh": 11593651.336800005,
    "vbf": 8111314.056214001,
    "wplush": 140641.6404,
    "wminush": 79827.28239200002,
    "zh": 119031.62316,
    "tth": 39448.7445942,
}
GENEVENTSUMW2_PROCESSED = {
    "ggh": 254177492.05440012,
    "vbf": 337360858.4324181,
    "wplush": 136714.68724499998,
    "wminush": 48206.162714545295,
    "zh": 106148.59411180638,
    "tth": 335381.82723663,
}
D3_GGH_SINGLE_FILE_PREVIEW = 720  # quoted in this task's own instructions


def main():
    weights_path = OUT_DIR / "part_d_pileup_weights.json"
    if not weights_path.exists():
        raise SystemExit("Run part_d_pileup.py first -- part_e reuses its saved pileup weights.")
    all_weights = json.loads(weights_path.read_text(encoding="utf-8"))

    per_label = {}
    total_before, total_after = 0.0, 0.0
    for label in common.SIGNAL_LABELS:
        s = common.load_signal(label)
        gw = np.asarray(s["genWeight"])
        pv = np.asarray(s["PV_npvsGood"])
        cat = np.asarray(s["category"])
        edges = np.array(all_weights[label]["bin_edges"])
        w_pu = np.array(all_weights[label]["weights"])
        pu_weight = common.apply_pileup_weight(pv, edges, w_pu)

        genEventSumw = GENEVENTSUMW_PROCESSED[label]
        scale = common.SIGNAL_CROSS_SECTIONS_PB[label] * 1000.0 * common.BR_HGG * common.LUMI_FB / genEventSumw

        cats = {}
        for c in common.CATEGORIES:
            m = common.category_mask(cat, c)
            sum_before = float(gw[m].sum())
            sum_after = float((gw * pu_weight)[m].sum())
            N_before = scale * sum_before
            N_after = scale * sum_after
            stat_unc_before = common.stat_uncertainty_sqrt_sumw2(gw, mask=m, scale=scale)
            stat_unc_after = common.stat_uncertainty_sqrt_sumw2(gw * pu_weight, mask=m, scale=scale)
            n_eff_selected = (
                (gw[m].sum() ** 2 / np.sum(gw[m] ** 2)) if np.sum(gw[m] ** 2) > 0 else None
            )
            cats[c] = {
                "n_selected_events": int(m.sum()),
                "N_expected_before_pu": N_before,
                "N_expected_stat_unc_before_pu": stat_unc_before,
                "N_expected_after_pu": N_after,
                "N_expected_stat_unc_after_pu": stat_unc_after,
                "n_effective_MC_events_selected": float(n_eff_selected) if n_eff_selected is not None else None,
            }

        N_incl_before = scale * float(gw.sum())
        N_incl_after = scale * float((gw * pu_weight).sum())
        stat_unc_incl_before = common.stat_uncertainty_sqrt_sumw2(gw, scale=scale)
        n_eff_all_processed = GENEVENTSUMW_PROCESSED[label] ** 2 / GENEVENTSUMW2_PROCESSED[label]

        per_label[label] = {
            "cross_section_pb": common.SIGNAL_CROSS_SECTIONS_PB[label],
            "genEventSumw_over_processed_files": genEventSumw,
            "n_effective_MC_events_all_processed_files": n_eff_all_processed,
            "inclusive": {
                "N_expected_before_pu": N_incl_before,
                "N_expected_stat_unc_before_pu": stat_unc_incl_before,
                "N_expected_after_pu": N_incl_after,
            },
            "per_category": cats,
        }
        total_before += N_incl_before
        total_after += N_incl_after

    # per-category fraction of the grand total (before-PU numbers, as the headline)
    cat_totals_before = {c: sum(per_label[l]["per_category"][c]["N_expected_before_pu"] for l in common.SIGNAL_LABELS)
                          for c in common.CATEGORIES}

    result = {
        "luminosity_fb": common.LUMI_FB,
        "branching_ratio_Hgammagamma": common.BR_HGG,
        "per_label": per_label,
        "total_N_expected_before_pu": total_before,
        "total_N_expected_after_pu": total_after,
        "total_relative_pu_effect_pct": 100.0 * (total_after - total_before) / total_before,
        "category_fraction_of_total_before_pu": {
            c: {"N": cat_totals_before[c], "fraction": cat_totals_before[c] / total_before}
            for c in common.CATEGORIES
        },
        "ggh_vs_D3_single_file_preview": {
            "D3_single_file_preview": D3_GGH_SINGLE_FILE_PREVIEW,
            "full_run_ggh_total_before_pu": per_label["ggh"]["inclusive"]["N_expected_before_pu"],
            "note": (
                "D3's preview used exactly ONE of ggH's 3 files; the full run "
                "uses all 3. Close agreement is a consistency check (ggH's "
                "per-file selection efficiency is expected to be fairly "
                "uniform for a promptly-generated signal sample), not an "
                "exact-equality requirement."
            ),
        },
    }
    (OUT_DIR / "part_e_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'part_e_results.json'}")


if __name__ == "__main__":
    main()
