"""
Signal-model task, Part 4: signal systematic-uncertainty table, per
category. Every number here is either (a) taken verbatim from a cited
external source, (b) taken verbatim from an earlier validation report in
this repo, or (c) derived here from the loaded signal samples -- marked
accordingly. Nothing is independently re-derived from first principles
(e.g. no NNLO cross-section recomputation).

SOURCES
-------
Luminosity: 1.2% for the CMS 2016 (13 TeV) dataset -- L. Sirunyan et al.
(CMS Collaboration), "Precision luminosity measurement in proton-proton
collisions at sqrt(s)=13 TeV in 2015 and 2016 at CMS", Eur. Phys. J. C
81 (2021) 800, arXiv:2104.01927. (This task's own instructions already
state 1.2% for this dataset; cited here for completeness.)

Theory (production cross sections): LHC Higgs Cross Section Working
Group, "Handbook of LHC Higgs Cross Sections: 4. Deciphering the Nature
of the Higgs Sector", arXiv:1610.07922 ("YR4"), 13 TeV, mH=125 GeV
values as tabulated on the LHCHXSWG twiki
(https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV,
retrieved 17 Sep 2026):
  ggH:  48.52 pb, QCD scale +4.6%/-6.7%, PDF+alphas_s +-3.2%
  VBF:   3.779 pb, QCD scale +0.4%/-0.3%, PDF+alphas_s +-2.1%
  WH:    QCD scale +0.5%/-0.7%, PDF+alphas_s +-1.9% (applied to both
         W+H and W-H -- YR4 quotes this uncertainty for combined WH)
  ZH:    QCD scale +3.8%/-3.0%, PDF+alphas_s +-1.6% (applied here to the
         qq/qg-only 0.7612 pb cross section used throughout this
         project -- see signal_sumw_notes.md; using the COMBINED
         qq+gg ZH sample's fractional uncertainty on the qq-only piece
         is an approximation, not independently re-derived for the
         qq-only process alone -- flagged explicitly)
  ttH:   QCD scale +5.8%/-9.2%, PDF+alphas_s +-3.6%
Each mode's scale+PDF is combined in quadrature per mode using the
SYMMETRIZED scale uncertainty ((|+|+|-|)/2) -- a documented
simplification; the asymmetry is not propagated further. Modes are then
combined per category in quadrature, weighted by each mode's fraction of
that category's total yield (assumes production-mode theory
uncertainties are uncorrelated between modes, the standard LHCHXSWG
treatment for scale uncertainties; PDF+alphas_s uncertainties are in
reality partly correlated between modes via common PDF sets, which this
simple combination does not model -- documented, not corrected for).

BR(H->gamma gamma) uncertainty: ~3% relative (from the LHCHXSWG Higgs
branching-ratio tables, "BR(H->gg) = (0.227 +- 0.007)%" ballpark,
retrieved via web search summarization of
https://twiki.cern.ch/twiki/bin/view/LHCPhysics/LHCHWGBRs, 17 Sep 2026
-- UNVERIFIED at the level of the exact tabulated decimal: this project
did not independently open BR.central.dat itself, only a secondary
summary of the twiki page). Treated as 100% correlated across all six
production modes (a common multiplicative factor), so combined with the
production-cross-section theory uncertainty IN QUADRATURE (independent
source) rather than folded into the per-mode weighting above.

Z->ee energy-scale/resolution and trigger-efficiency numbers: verbatim
from VALIDATION_REPORT_2.md Parts B and D (already-completed validation
task, not re-measured here).

Pileup-weight effect: derived HERE from this task's own loaded/weighted
samples (before vs. after applying Part D's pileup weights, restricted
to the 105-180 GeV fit range, ALL SIX MODES combined -- not just ggH,
unlike VALIDATION_REPORT_1 Part D's own ggH-only demonstration). "Full
size of the effect" per this task's instruction means the raw observed
relative shift is used directly as the systematic, with no shrinking.

Simulation-statistics uncertainty: derived here directly from the
loaded, corrected (scale x genWeight x pileup) per-category weight
arrays restricted to 105-180 GeV: relative stat. uncertainty =
sqrt(sum w_i^2) / sum(w_i) (identical formula to
VALIDATION_REPORT_1 Part E's stat_uncertainty_sqrt_sumw2, expressed as a
fraction of the yield instead of an absolute count).
"""
from __future__ import annotations

import numpy as np

from studies.hgg_cms.signal_model.loader import SIGNAL_LABELS, CATEGORIES, LUMI_UNCERTAINTY_PCT
from studies.hgg_cms.signal_model.part3_yields import TRIGGER_SF, TRIGGER_SF_SYST, FIT_LO, FIT_HI

LUMI_SYST_PCT = LUMI_UNCERTAINTY_PCT  # 1.2%, arXiv:2104.01927
LUMI_SOURCE = "arXiv:2104.01927 (CMS 2016 13 TeV luminosity, precision 1.2%)"

# YR4 (arXiv:1610.07922) 13 TeV, mH=125 GeV, per the twiki table cited in the module docstring.
YR4_THEORY_PCT = {
    "ggh":    {"scale_up": 4.6, "scale_down": 6.7, "pdf_as": 3.2},
    "vbf":    {"scale_up": 0.4, "scale_down": 0.3, "pdf_as": 2.1},
    "wplush": {"scale_up": 0.5, "scale_down": 0.7, "pdf_as": 1.9},
    "wminush":{"scale_up": 0.5, "scale_down": 0.7, "pdf_as": 1.9},
    "zh":     {"scale_up": 3.8, "scale_down": 3.0, "pdf_as": 1.6},
    "tth":    {"scale_up": 5.8, "scale_down": 9.2, "pdf_as": 3.6},
}
BR_HGG_SYST_PCT = 3.0  # ~3% relative, LHCHXSWG BR tables -- see module docstring, UNVERIFIED to exact decimal
BR_HGG_SOURCE = ("~3% relative, LHCHXSWG Higgs branching-ratio twiki "
                  "(https://twiki.cern.ch/twiki/bin/view/LHCPhysics/LHCHWGBRs), "
                  "retrieved via secondary web summary 17 Sep 2026 -- UNVERIFIED "
                  "to the exact tabulated decimal")

# VALIDATION_REPORT_2 Part B (Z->ee energy scale/resolution).
ZEE_DELTA_PEAK_OVER_PEAK_PCT = {"inclusive": 0.037, "EBEB": 0.055, "notEBEB": -0.037}
ZEE_DELTA_SIGMAEFF_OVER_SIGMAEFF_PCT = {"inclusive": -0.95, "EBEB": -0.59, "notEBEB": -1.75}

ENERGY_SCALE_SYST_PCT = max(0.1, max(abs(v) for v in ZEE_DELTA_PEAK_OVER_PEAK_PCT.values()))
ENERGY_RESOLUTION_SYST_PCT = max(5.0, 2.0 * max(abs(v) for v in ZEE_DELTA_SIGMAEFF_OVER_SIGMAEFF_PCT.values()))


def _mode_theory_pct(label: str) -> float:
    t = YR4_THEORY_PCT[label]
    scale_sym = 0.5 * (t["scale_up"] + t["scale_down"])
    return float(np.sqrt(scale_sym ** 2 + t["pdf_as"] ** 2))


def combined_theory_systematic(mode_fractions: dict) -> dict:
    """mode_fractions: {label: fraction of category total yield}.
    Returns the per-mode theory %, the quadrature-weighted combination
    across modes, and the total after adding BR(Hgg) in quadrature."""
    per_mode_pct = {label: _mode_theory_pct(label) for label in SIGNAL_LABELS}
    production_combined = float(np.sqrt(sum(
        (mode_fractions[label] * per_mode_pct[label]) ** 2 for label in SIGNAL_LABELS
    )))
    total = float(np.sqrt(production_combined ** 2 + BR_HGG_SYST_PCT ** 2))
    return {
        "per_mode_theory_pct": per_mode_pct,
        "production_combined_pct": production_combined,
        "br_hgg_pct": BR_HGG_SYST_PCT,
        "total_theory_pct": total,
    }


def pileup_effect(all_signal: dict) -> dict:
    """All six modes combined, 105-180 GeV, per category: relative yield
    shift before vs. after Part D's pileup weights (full size of the
    effect, no shrinking)."""
    out = {}
    for cat in CATEGORIES:
        no_pu_total, pu_total = 0.0, 0.0
        for label in SIGNAL_LABELS:
            sig = all_signal[label]
            m = sig.category_mask(cat)
            mgg = sig.mgg[m]
            in_range = (mgg >= FIT_LO) & (mgg <= FIT_HI)
            no_pu_total += float(sig.weight(use_pileup=False)[m][in_range].sum())
            pu_total += float(sig.weight(use_pileup=True)[m][in_range].sum())
        rel_pct = 100.0 * (pu_total - no_pu_total) / no_pu_total
        out[cat] = {
            "N_no_pileup": no_pu_total, "N_with_pileup": pu_total,
            "relative_yield_effect_pct": rel_pct,
            "abs_relative_yield_effect_pct": abs(rel_pct),
        }
    return out


def simulation_stat_uncertainty(all_signal: dict) -> dict:
    """Relative MC-statistical uncertainty on the combined (all modes,
    with pileup) yield per category, 105-180 GeV: sqrt(sum w^2)/sum(w)."""
    out = {}
    for cat in CATEGORIES:
        w_parts = []
        for label in SIGNAL_LABELS:
            sig = all_signal[label]
            m = sig.category_mask(cat)
            mgg = sig.mgg[m]
            in_range = (mgg >= FIT_LO) & (mgg <= FIT_HI)
            w_parts.append(sig.weight(use_pileup=True)[m][in_range])
        w = np.concatenate(w_parts)
        total = float(w.sum())
        stat_abs = float(np.sqrt(np.sum(w ** 2)))
        out[cat] = {
            "N_total": total, "stat_uncertainty_abs": stat_abs,
            "stat_uncertainty_relative_pct": 100.0 * stat_abs / total if total else float("nan"),
        }
    return out


def build_systematics_table(all_signal: dict, yields: dict) -> dict:
    out = {}
    pu = pileup_effect(all_signal)
    stat = simulation_stat_uncertainty(all_signal)
    for cat in CATEGORIES:
        cat_yield = yields[cat]
        total_pu = cat_yield["N_with_pileup"]
        mode_fractions = {
            label: cat_yield["per_mode"][label]["N_with_pileup"] / total_pu
            for label in SIGNAL_LABELS
        }
        theory = combined_theory_systematic(mode_fractions)
        out[cat] = {
            "mode_fractions_used_for_theory_weighting": mode_fractions,
            "luminosity_pct": {"value": LUMI_SYST_PCT, "type": "normalization", "source": LUMI_SOURCE},
            "theory_pct": {
                "value": theory["total_theory_pct"], "type": "normalization (affects mu interpretation, not observed significance)",
                "source": "LHCHXSWG YR4 (arXiv:1610.07922) production x-sec scale+PDF, combined per mode, "
                          "weighted by category mode-fractions, plus BR(Hgg)~3% in quadrature -- see module docstring",
                "breakdown": theory,
            },
            "trigger_sf_pct": {
                "value": 100.0 * TRIGGER_SF_SYST[cat], "type": "normalization",
                "source": f"|1-SF|, VALIDATION_REPORT_2 Part D trigger data/DY ratio SF={TRIGGER_SF[cat]}",
            },
            "id_reco_pct": {
                "value": 20.0, "type": "normalization",
                "source": "No photon-ID scale factors available; +-20% assigned, justified by the "
                           "Z->ee data/DY normalization ratios' distance from 1 (VALIDATION_REPORT_2 Part C: "
                           "EBEB 0.837, notEBEB 0.808). Affects expected significance / mu interpretation, "
                           "not the observed significance.",
            },
            "pileup_pct": {
                "value_yield": pu[cat]["abs_relative_yield_effect_pct"],
                "value_shape": 0.0,
                "type": "normalization (yield) + shape (negligible)",
                "source": "This task's own before/after-pileup-weight comparison, all 6 modes, 105-180 GeV "
                           "(cf. VALIDATION_REPORT_1 Part D's ggH-only demonstration, which found no "
                           "measurable shape change at its 0.25 GeV binning resolution -- shape effect "
                           "taken as negligible/zero here on that basis).",
                "detail": pu[cat],
            },
            "energy_scale_pct": {
                "value": ENERGY_SCALE_SYST_PCT, "type": "shape (mean shift)",
                "value_GeV_at_125": ENERGY_SCALE_SYST_PCT / 100.0 * 125.0,
                "source": "max over categories of Z->ee |Delta peak|/peak (VALIDATION_REPORT_2 Part B), "
                          "rounded up to >= 0.1%",
            },
            "energy_resolution_pct": {
                "value": ENERGY_RESOLUTION_SYST_PCT, "type": "shape (width)",
                "source": "2x max over categories of |Delta sigma_eff/sigma_eff| from Z->ee "
                          "(VALIDATION_REPORT_2 Part B), factor 2 for electron->photon extrapolation "
                          "(documented choice, not independently validated), rounded up to >= 5%",
            },
            "simulation_stat_pct": {
                "value": stat[cat]["stat_uncertainty_relative_pct"], "type": "normalization (statistical)",
                "source": "sqrt(Sum w^2)/Sum(w), all 6 modes combined, 105-180 GeV, from this task's own "
                          "effective-event-count calculation (Part 1)",
                "detail": stat[cat],
            },
        }
    return out
