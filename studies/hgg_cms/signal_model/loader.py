"""
Signal-model task, Part 1: load the six signal samples and build each
event's total weight = genWeight * pileup_weight * normalization, where
normalization = cross_section_pb * 1000 (pb->fb) * BR(H->gg) * L_fb /
genEventSumw_over_processed_files.

Pileup weights are NOT re-derived here: they are REUSED, unchanged, from
`studies/hgg_cms/validation/results/part_d_pileup_weights.json` (already
committed to the repo from the prior validation task) via the identical
`apply_pileup_weight` bin-lookup used there. Deriving them requires the
data-sideband PV_npvsGood distribution -- this task's rules forbid
opening any data file, so re-deriving from scratch is not an option here
even though the underlying method is the same; reusing the already-saved
weights is both compliant and, by construction, numerically identical to
Part D (verified below by reproducing Part E's total yield).

All cross sections, genEventSumw values, and the ZH/ttH normalization
caveats are taken verbatim from
`studies/hgg_cms/validation/common.py` (SIGNAL_CROSS_SECTIONS_PB) and
`merge_summary_signal.json` / `part_e_expected_yields.py`
(GENEVENTSUMW_PROCESSED), not re-fetched or re-derived.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from studies.hgg_cms.validation import common as vcommon

REPO_ROOT = Path(__file__).resolve().parents[3]
VALIDATION_RESULTS = REPO_ROOT / "studies" / "hgg_cms" / "validation" / "results"

SIGNAL_LABELS = vcommon.SIGNAL_LABELS
CATEGORIES = vcommon.CATEGORIES
SIGNAL_CROSS_SECTIONS_PB = vcommon.SIGNAL_CROSS_SECTIONS_PB
BR_HGG = vcommon.BR_HGG
LUMI_FB = vcommon.LUMI_FB
LUMI_UNCERTAINTY_PCT = vcommon.LUMI_UNCERTAINTY_PCT

# genEventSumw_over_processed_files per label -- from merge_summary_signal.json,
# identical to validation/part_e_expected_yields.py's GENEVENTSUMW_PROCESSED.
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


def load_pileup_weights() -> dict:
    path = VALIDATION_RESULTS / "part_d_pileup_weights.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found -- this task reuses Part D's already-derived "
            f"pileup weights (see this module's docstring); it does not "
            f"re-derive them (that needs data_sidebands.root, out of scope "
            f"for this task)."
        )
    return json.loads(path.read_text(encoding="utf-8"))


class SignalEvents:
    """One production mode's selected events with every per-event weight
    component kept separate, so downstream code can combine them however
    it needs (e.g. with/without pileup, with/without a trigger SF)."""

    def __init__(self, label: str, mgg, category, genWeight, pileup_weight, scale):
        self.label = label
        self.mgg = np.asarray(mgg, dtype=float)
        self.category = np.asarray(category)
        self.genWeight = np.asarray(genWeight, dtype=float)
        self.pileup_weight = np.asarray(pileup_weight, dtype=float)
        self.scale = float(scale)  # sigma * BR * L / genEventSumw (pb->fb already applied)

    def weight(self, use_pileup: bool = True) -> np.ndarray:
        if use_pileup:
            return self.scale * self.genWeight * self.pileup_weight
        return self.scale * self.genWeight

    def n_effective(self, mask=None) -> float:
        """(Sum genWeight)^2 / Sum genWeight^2 -- the effective number of
        simulated events (no pileup weight, no normalization scale, matching
        VALIDATION_REPORT_1 Part E's own definition)."""
        gw = self.genWeight if mask is None else self.genWeight[mask]
        denom = float(np.sum(gw ** 2))
        if denom <= 0:
            return 0.0
        return float(np.sum(gw) ** 2 / denom)

    def category_mask(self, cat: str) -> np.ndarray:
        return vcommon.category_mask(self.category, cat)


def load_all_signal_events() -> dict:
    """Returns {label: SignalEvents}, one per production mode, with
    genWeight/pileup_weight/scale all populated and ready to combine."""
    all_weights = load_pileup_weights()
    out = {}
    for label in SIGNAL_LABELS:
        arr = vcommon.load_signal(label)
        import awkward as ak
        mgg = ak.to_numpy(arr["m_gg"])
        category = ak.to_numpy(arr["category"])
        genWeight = ak.to_numpy(arr["genWeight"])
        pv = ak.to_numpy(arr["PV_npvsGood"])

        edges = np.array(all_weights[label]["bin_edges"])
        w_pu = np.array(all_weights[label]["weights"])
        pileup_weight = vcommon.apply_pileup_weight(pv, edges, w_pu)

        genEventSumw = GENEVENTSUMW_PROCESSED[label]
        scale = SIGNAL_CROSS_SECTIONS_PB[label] * 1000.0 * BR_HGG * LUMI_FB / genEventSumw

        out[label] = SignalEvents(label, mgg, category, genWeight, pileup_weight, scale)
    return out


def reproduce_part_e(all_signal: dict) -> dict:
    """Part 1.2: reproduce VALIDATION_REPORT_1 Part E's yields (total
    before-PU ~810.09, after-PU ~808.78, per mode/category) as a
    consistency check on this module's own weight construction. Returns a
    dict with the reproduced numbers and their relative difference from
    the report's own saved JSON."""
    ref_path = VALIDATION_RESULTS / "part_e_results.json"
    ref = json.loads(ref_path.read_text(encoding="utf-8")) if ref_path.exists() else None

    per_label = {}
    total_before, total_after = 0.0, 0.0
    for label, sig in all_signal.items():
        before = sig.weight(use_pileup=False)
        after = sig.weight(use_pileup=True)
        cats = {}
        for cat in CATEGORIES:
            m = sig.category_mask(cat)
            cats[cat] = {
                "N_before_pu": float(before[m].sum()),
                "N_after_pu": float(after[m].sum()),
            }
        N_before_incl = float(before.sum())
        N_after_incl = float(after.sum())
        per_label[label] = {
            "inclusive_before_pu": N_before_incl,
            "inclusive_after_pu": N_after_incl,
            "per_category": cats,
        }
        total_before += N_before_incl
        total_after += N_after_incl

    result = {
        "per_label": per_label,
        "total_before_pu": total_before,
        "total_after_pu": total_after,
    }

    if ref is not None:
        comparisons = {}
        max_rel_diff = 0.0
        for label in SIGNAL_LABELS:
            ref_before = ref["per_label"][label]["inclusive"]["N_expected_before_pu"]
            ref_after = ref["per_label"][label]["inclusive"]["N_expected_after_pu"]
            got_before = per_label[label]["inclusive_before_pu"]
            got_after = per_label[label]["inclusive_after_pu"]
            rel_before = abs(got_before - ref_before) / ref_before if ref_before else 0.0
            rel_after = abs(got_after - ref_after) / ref_after if ref_after else 0.0
            comparisons[label] = {
                "ref_before_pu": ref_before, "got_before_pu": got_before, "rel_diff_before_pu": rel_before,
                "ref_after_pu": ref_after, "got_after_pu": got_after, "rel_diff_after_pu": rel_after,
            }
            max_rel_diff = max(max_rel_diff, rel_before, rel_after)
        rel_total_before = abs(total_before - ref["total_N_expected_before_pu"]) / ref["total_N_expected_before_pu"]
        rel_total_after = abs(total_after - ref["total_N_expected_after_pu"]) / ref["total_N_expected_after_pu"]
        result["comparison_to_part_e"] = {
            "per_label": comparisons,
            "ref_total_before_pu": ref["total_N_expected_before_pu"],
            "ref_total_after_pu": ref["total_N_expected_after_pu"],
            "rel_diff_total_before_pu": rel_total_before,
            "rel_diff_total_after_pu": rel_total_after,
            "max_rel_diff_any_label": max_rel_diff,
            "all_within_0.1pct": bool(max_rel_diff < 0.001 and rel_total_before < 0.001 and rel_total_after < 0.001),
        }
    return result


def effective_mc_counts(all_signal: dict) -> dict:
    """Part 1.3: (Sum w)^2 / Sum w^2 per mode and category, using the raw
    genWeight (no pileup, no normalization scale -- matching
    VALIDATION_REPORT_1 Part E's own n_effective_MC_events definition)."""
    out = {}
    for label, sig in all_signal.items():
        cats = {}
        for cat in CATEGORIES:
            m = sig.category_mask(cat)
            cats[cat] = sig.n_effective(mask=m)
        out[label] = {
            "inclusive": sig.n_effective(),
            "per_category": cats,
        }
    return out
