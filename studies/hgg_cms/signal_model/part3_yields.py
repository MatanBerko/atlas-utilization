"""
Signal-model task, Part 3: expected signal yields per category, restricted
to the 105-180 GeV fit range (VALIDATION_REPORT_2's fit-range decision),
with the pre-set corrections applied exactly as specified in this task's
own instructions (not re-derived or adjusted here):

- Trigger: multiply by the per-category diphoton-trigger data/DY ratio
  from VALIDATION_REPORT_2 Part D (EBEB 1.0229, notEBEB 0.9705).
  Systematic = |1 - SF| per category.
- ID/reconstruction: NO correction to the central yield (no photon-ID
  scale factors exist in this open-data setup). A +-20% normalization
  systematic is assigned instead, justified by how far the Z->ee
  data/DY normalization ratio sits from 1 (VALIDATION_REPORT_2 Part C:
  EBEB 0.837, notEBEB 0.808). An ALTERNATIVE yield, scaled by those same
  Z->ee ratios, is reported for information only -- not adopted as the
  central value.
"""
from __future__ import annotations

import numpy as np

from studies.hgg_cms.signal_model.loader import SIGNAL_LABELS, CATEGORIES

TRIGGER_SF = {"EBEB": 1.0229, "notEBEB": 0.9705}
TRIGGER_SF_SYST = {c: abs(1.0 - TRIGGER_SF[c]) for c in TRIGGER_SF}  # |1-SF|, per category

ID_RECO_SYST_PCT = 0.20  # +-20%, flat, no central correction

# Z->ee data/DY normalization ratio (VALIDATION_REPORT_2 Part C, PU-weighted).
ZEE_DATA_DY_RATIO = {"EBEB": 0.837, "notEBEB": 0.808}

FIT_LO, FIT_HI = 105.0, 180.0


def category_yields(all_signal: dict) -> dict:
    """Per category: yield with no corrections (genWeight only), with
    pileup, with the trigger SF applied (central), the Z-ratio
    alternative, and each mode's fraction of the category total --
    ALL restricted to 105-180 GeV (this task's fit range)."""
    out = {}
    grand_total_after_pu = 0.0
    per_cat_after_pu = {}

    for cat in CATEGORIES:
        per_mode = {}
        total_no_corr = 0.0
        total_pu = 0.0
        for label in SIGNAL_LABELS:
            sig = all_signal[label]
            m = sig.category_mask(cat)
            mgg = sig.mgg[m]
            in_fit_range = (mgg >= FIT_LO) & (mgg <= FIT_HI)

            w_no_pu = sig.weight(use_pileup=False)[m][in_fit_range]
            w_pu = sig.weight(use_pileup=True)[m][in_fit_range]

            N_no_corr = float(w_no_pu.sum())
            N_pu = float(w_pu.sum())
            per_mode[label] = {"N_no_corrections": N_no_corr, "N_with_pileup": N_pu}
            total_no_corr += N_no_corr
            total_pu += N_pu

        trigger_sf = TRIGGER_SF[cat]
        total_trigger = total_pu * trigger_sf
        total_zee_alt = total_pu * ZEE_DATA_DY_RATIO[cat]

        per_cat_after_pu[cat] = total_pu
        grand_total_after_pu += total_pu

        out[cat] = {
            "per_mode": per_mode,
            "N_no_corrections": total_no_corr,
            "N_with_pileup": total_pu,
            "N_with_trigger_sf_central": total_trigger,
            "trigger_sf_applied": trigger_sf,
            "N_zee_ratio_alternative_for_info": total_zee_alt,
            "zee_ratio_applied": ZEE_DATA_DY_RATIO[cat],
        }

    for cat in CATEGORIES:
        out[cat]["fraction_of_total_signal"] = per_cat_after_pu[cat] / grand_total_after_pu

    out["_grand_total_with_pileup"] = grand_total_after_pu
    out["_fit_range_GeV"] = [FIT_LO, FIT_HI]
    return out
