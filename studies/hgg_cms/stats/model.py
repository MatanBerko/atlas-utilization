"""
Statistical-analysis task: the full H->gamma-gamma statistical model.
Binned Poisson likelihood, 0.25 GeV bins over 105-180 GeV, two
categories (EBEB, notEBEB), simultaneous fit.

Expected events per bin i, category c:
    nu_ci = mu * N_s,c * K_c(theta) * f_s,c(i; m_H, theta_scale, theta_res)
            + theta_spur,c * S_spur,c * f_s,c(i; m_H, theta_scale, theta_res)
            + f_b,c(i; bernstein_6 params_c)

- mu: signal strength, SHARED across categories, unbounded (may go negative).
- N_s,c: central expected signal yield (trigger-SF-corrected), from
  `signal_model.json`: EBEB 545.80, notEBEB 266.13 -- loaded from the
  file, not hardcoded, and asserted to match these values.
- f_b,c(i; ...): the chosen background function (Bernstein order 6,
  7 free coefficients per category, `background_model_final.json`) --
  the coefficients themselves ARE "B_c * (normalized shape)" (the
  Bernstein basis's own scale IS the yield, by construction -- see
  `families.py`'s own module docstring); there is no separate B_c
  parameter distinct from these 7 coefficients, consistent with every
  earlier background-model script in this project (`bias_study.py`,
  `finalize_background_model.py`).
- theta_spur,c * S_spur,c: the spurious-signal nuisance terms, EBEB 32.16
  and notEBEB 109.26 events (`background_model_final.json`, loaded and
  asserted to match) -- unit-Gaussian constrained, UNCORRELATED between
  categories (each measured from an independent bias study per
  category), NOT multiplied by mu (a spurious signal is a background
  mismodeling effect, not a real signal that scales with signal
  strength), and the SAME at every m_H (BACKGROUND_MODEL_REPORT.md's own
  "Human decision after rerun 1" section: "the maximum over the scan is
  used at every mass").
- K_c(theta): product of log-normal (kappa^theta) normalization factors:
    - luminosity (1.2%, arXiv:2104.01927): SHARED (theta_lumi) -- the
      same physical measurement affects both categories identically.
    - theory (per-category value from signal_model.json, ~6.5%): SHARED
      (theta_theory) -- both categories' numbers come from the SAME
      LHCHXSWG YR4 cross-section/PDF/BR uncertainties, combined with
      slightly different per-category mode-fraction weights; the
      difference in VALUE between categories is real, but the
      underlying uncertain quantity (the true cross sections) is one
      shared unknown, not two independent ones.
    - ID/reconstruction (20% flat, both categories): SHARED (theta_ID)
      -- the SAME missing-calibration policy choice (no photon-ID scale
      factors available) was applied identically to both categories
      from the same reasoning (signal_model.json's own justification);
      treated as one shared unknown. (A genuine barrel/endcap
      difference in real photon-ID performance could argue for treating
      part of this as uncorrelated -- not done here; flagged as a
      modeling simplification, not a measured differential.)
    - trigger SF (per-category, independently measured tag-and-probe
      ratios): THETA PER CATEGORY (theta_trigger_c) -- independent
      measurements.
    - pileup (per-category yield effect): THETA PER CATEGORY
      (theta_pileup_c) -- independently derived per category (not
      explicitly listed in this task's own correlation instruction, but
      follows the same "independently derived per category" logic as
      trigger SF and MC statistics).
    - MC statistics (per-category effective-event-count driven):
      THETA PER CATEGORY (theta_mcstat_c) -- manifestly independent
      (different Monte Carlo samples/effective counts per category).
- f_s,c: the signal shape from `signal_model.json` (DCB or DCB+Gaussian,
  already fit per category), evaluated at hypothesized m_H (the
  recorded fit's own mean already encodes delta = fitted_mean - 125;
  shifting to m_H adds (m_H - 125) on top, per `SignalShape.shifted_to_mass`),
  with an ADDITIONAL energy-scale nuisance theta_scale (an absolute GeV
  mean shift, SHARED -- same Z->ee-based calibration source for both
  categories) and energy-resolution nuisance theta_res (a relative width
  scale, SHARED -- same "electron->photon extrapolation factor of 2"
  documented choice for both categories), both unit-Gaussian constrained.
  Bin probabilities via the shape's own analytic CDF (`bin_probabilities`).

FIT ROBUSTNESS (per this task's own instruction to read
`studies/lr_toys/lr_core.py`'s REPORT.md / `studies/atlas_hgg_repro`'s
"Corrections"): >=10 starting points, best VALID NLL kept, MIGRAD
validity recorded, a second-optimizer (scipy L-BFGS-B) cross-check for
headline fits, and the invariant NLL(mu free) <= NLL(mu=0) + 1e-6
asserted (see `q0_from_fits`).

DISCOVERY TEST STATISTIC (Cowan, Cranmer, Gross, Vitells, "Asymptotic
formulae for likelihood-based tests of new physics", Eur. Phys. J. C 71
(2011) 1554, arXiv:1007.1727, "CCGV"): q0 = -2 ln[L(mu=0, theta-hat-hat) /
L(mu-hat, theta-hat)] for mu-hat >= 0, else 0 (CCGV eq. 12); Z = sqrt(q0)
(eq. 13). Also the signed version (no zeroing) for reporting, matching
`studies/lr_toys/lr_core.py`'s own `signed_z_from_nll` convention.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from iminuit import Minuit
from scipy.optimize import minimize as scipy_minimize

from studies.hgg_cms.background_model.families import FAMILIES
from studies.hgg_cms.background_model.common import bin_edges as _bin_edges
from studies.hgg_cms.signal_model.shapes import SignalShape
from studies.hgg_cms.stats.binning import poisson_nll

REPO_ROOT = Path(__file__).resolve().parents[3]
SIGNAL_MODEL_JSON = REPO_ROOT / "studies" / "hgg_cms" / "signal_model" / "results" / "signal_model.json"
BACKGROUND_MODEL_JSON = REPO_ROOT / "studies" / "hgg_cms" / "background_model" / "results" / "background_model_final.json"

CATEGORIES = ("EBEB", "notEBEB")
FIT_LO, FIT_HI, BIN_WIDTH = 105.0, 180.0, 0.25
BLIND_LO, BLIND_HI = 115.0, 135.0
N_BINS = int(round((FIT_HI - FIT_LO) / BIN_WIDTH))
NLL_INVARIANT_TOL = 1e-6

# Expected central values, verified against the JSONs at import time (see _load_and_verify).
EXPECTED_N_S = {"EBEB": 545.8, "notEBEB": 266.1}
EXPECTED_S_SPUR = {"EBEB": 32.2, "notEBEB": 109.3}
_VERIFY_TOL_REL = 1e-2  # 1% -- catches a wrong file, not float round-trip noise


def edges() -> np.ndarray:
    return _bin_edges(FIT_LO, FIT_HI, BIN_WIDTH)


@dataclass
class CategoryInputs:
    N_s: float
    signal_params: dict
    signal_use_gauss2: bool
    signal_param_names: tuple
    S_spur: float
    bkg_family: str
    bkg_order: int
    bkg_start_params: np.ndarray
    theory_pct: float
    trigger_sf_pct: float
    pileup_pct: float
    mcstat_pct: float
    energy_scale_pct: float
    energy_resolution_pct: float


@dataclass
class ModelInputs:
    categories: dict  # {cat: CategoryInputs}
    lumi_pct: float
    id_reco_pct: float


def load_model_inputs(signal_model_json: Path = SIGNAL_MODEL_JSON,
                       background_model_json: Path = BACKGROUND_MODEL_JSON) -> ModelInputs:
    sm = json.loads(Path(signal_model_json).read_text(encoding="utf-8"))
    bm = json.loads(Path(background_model_json).read_text(encoding="utf-8"))

    cats = {}
    lumi_pct = None
    id_reco_pct = None
    for cat in CATEGORIES:
        sp = sm[cat]["shape_params"]
        syst = sm[cat]["systematics"]
        N_s = float(sm[cat]["yields"]["N_with_trigger_sf_central"])
        if abs(N_s - EXPECTED_N_S[cat]) / EXPECTED_N_S[cat] > _VERIFY_TOL_REL:
            raise ValueError(f"{cat}: N_s in signal_model.json ({N_s}) does not match the task's "
                              f"stated value ({EXPECTED_N_S[cat]}) within {_VERIFY_TOL_REL:.0%}")

        bc = bm["per_category"][cat]
        S_spur = float(bc["spurious_signal_systematic"]["value_events"])
        if abs(S_spur - EXPECTED_S_SPUR[cat]) / EXPECTED_S_SPUR[cat] > _VERIFY_TOL_REL:
            raise ValueError(f"{cat}: S_spur in background_model_final.json ({S_spur}) does not match "
                              f"the task's stated value ({EXPECTED_S_SPUR[cat]}) within {_VERIFY_TOL_REL:.0%}")

        this_lumi = float(syst["luminosity_pct"]["value"])
        this_id = float(syst["id_reco_pct"]["value"])
        if lumi_pct is None:
            lumi_pct = this_lumi
        elif abs(lumi_pct - this_lumi) > 1e-9:
            raise ValueError("luminosity_pct differs between categories -- expected a shared value")
        if id_reco_pct is None:
            id_reco_pct = this_id
        elif abs(id_reco_pct - this_id) > 1e-9:
            raise ValueError("id_reco_pct differs between categories -- expected a shared value")

        cats[cat] = CategoryInputs(
            N_s=N_s,
            signal_params=dict(sp["params"]), signal_use_gauss2=bool(sp["use_gauss2"]),
            signal_param_names=tuple(sp["params"].keys()),
            S_spur=S_spur,
            bkg_family=bc["chosen_function"]["family"], bkg_order=int(bc["chosen_function"]["order"]),
            bkg_start_params=np.array(bc["sideband_fit"]["params"]),
            theory_pct=float(syst["theory_pct"]["value"]),
            trigger_sf_pct=float(syst["trigger_sf_pct"]["value"]),
            pileup_pct=float(syst["pileup_pct"]["value_yield"]),
            mcstat_pct=float(syst["simulation_stat_pct"]["value"]),
            energy_scale_pct=float(syst["energy_scale_pct"]["value"]),
            energy_resolution_pct=float(syst["energy_resolution_pct"]["value"]),
        )

    return ModelInputs(categories=cats, lumi_pct=lumi_pct, id_reco_pct=id_reco_pct)


# Parameter ordering for the full 28-parameter joint model.
SHARED_PARAM_NAMES = ("mu", "theta_lumi", "theta_theory", "theta_ID", "theta_scale", "theta_res")
PER_CATEGORY_NUISANCE_NAMES = ("theta_trigger", "theta_pileup", "theta_mcstat", "theta_spur")


def full_param_names() -> tuple:
    mi = get_model_inputs()
    names = list(SHARED_PARAM_NAMES)
    for cat in CATEGORIES:
        for n in PER_CATEGORY_NUISANCE_NAMES:
            names.append(f"{n}_{cat}")
    for cat in CATEGORIES:
        ci = mi.categories[cat]
        fam = FAMILIES[ci.bkg_family]
        for pn in fam.param_names(ci.bkg_order):
            names.append(f"bkg_{cat}_{pn}")
    return tuple(names)


def signal_shape_for(cat_inputs: CategoryInputs, mH: float, theta_scale: float, theta_res: float) -> SignalShape:
    base = SignalShape(params=cat_inputs.signal_params, use_gauss2=cat_inputs.signal_use_gauss2,
                        param_names=cat_inputs.signal_param_names)
    shifted = base.shifted_to_mass(mH)
    new_params = dict(shifted.params)
    scale_shift_GeV = theta_scale * (cat_inputs.energy_scale_pct / 100.0) * 125.0
    width_factor = 1.0 + theta_res * (cat_inputs.energy_resolution_pct / 100.0)
    new_params["mu"] = new_params["mu"] + scale_shift_GeV
    new_params["sigma"] = new_params["sigma"] * width_factor
    if shifted.use_gauss2:
        new_params["mu2"] = new_params["mu2"] + scale_shift_GeV
        new_params["sigma2"] = new_params["sigma2"] * width_factor
    return SignalShape(params=new_params, use_gauss2=shifted.use_gauss2, param_names=shifted.param_names)


# Module-level cache of the (immutable, file-backed) model inputs.
_MODEL_INPUTS: Optional[ModelInputs] = None


def get_model_inputs() -> ModelInputs:
    global _MODEL_INPUTS
    if _MODEL_INPUTS is None:
        _MODEL_INPUTS = load_model_inputs()
    return _MODEL_INPUTS


def K_factor(cat: str, cat_inputs: CategoryInputs, theta_lumi: float, theta_theory: float, theta_ID: float,
             theta_trigger: float, theta_pileup: float, theta_mcstat: float) -> float:
    mi = get_model_inputs()

    def kappa(pct: float, theta: float) -> float:
        sigma = pct / 100.0
        return (1.0 + sigma) ** theta
    return (kappa(mi.lumi_pct, theta_lumi)
            * kappa(cat_inputs.theory_pct, theta_theory)
            * kappa(mi.id_reco_pct, theta_ID)
            * kappa(cat_inputs.trigger_sf_pct, theta_trigger)
            * kappa(cat_inputs.pileup_pct, theta_pileup)
            * kappa(cat_inputs.mcstat_pct, theta_mcstat))


def unpack_params(param_vec, names: tuple) -> dict:
    return dict(zip(names, param_vec))


def expected_counts(cat: str, par: dict, mH: float, edges_arr: np.ndarray = None) -> np.ndarray:
    """nu_ci over `edges_arr` (default: the full 105-180 GeV range) for
    category `cat`, given a dict of ALL parameter values (as returned by
    `unpack_params`)."""
    mi = get_model_inputs()
    ci = mi.categories[cat]
    if edges_arr is None:
        edges_arr = edges()

    theta_scale = par["theta_scale"]
    theta_res = par["theta_res"]
    shape = signal_shape_for(ci, mH, theta_scale, theta_res)
    sig_probs = shape.bin_probabilities(edges_arr)

    K = K_factor(cat, ci, par["theta_lumi"], par["theta_theory"], par["theta_ID"],
                 par[f"theta_trigger_{cat}"], par[f"theta_pileup_{cat}"], par[f"theta_mcstat_{cat}"])

    mu = par["mu"]
    theta_spur = par[f"theta_spur_{cat}"]
    signal_term = mu * ci.N_s * K * sig_probs
    spurious_term = theta_spur * ci.S_spur * sig_probs

    fam = FAMILIES[ci.bkg_family]
    bkg_names = fam.param_names(ci.bkg_order)
    bkg_params = np.array([par[f"bkg_{cat}_{n}"] for n in bkg_names])
    bkg_term = fam.bin_expectation(edges_arr, ci.bkg_order, bkg_params)

    return signal_term + spurious_term + bkg_term


def gaussian_constraint_nll(par: dict) -> float:
    """-ln of the product of unit-Gaussian auxiliary constraint terms for
    every constrained nuisance parameter (up to an additive constant,
    same convention as `poisson_nll` -- 0.5*theta^2 per nuisance)."""
    names = ["theta_lumi", "theta_theory", "theta_ID", "theta_scale", "theta_res"]
    for cat in CATEGORIES:
        for n in ("theta_trigger", "theta_pileup", "theta_mcstat", "theta_spur"):
            names.append(f"{n}_{cat}")
    return 0.5 * sum(par[n] ** 2 for n in names)


def full_nll(data: dict, par: dict, mH: float, edges_arr: np.ndarray = None) -> float:
    """data: {cat: array of observed counts per bin}. Sums the binned
    Poisson NLL over both categories (full 105-180 GeV range -- data
    here is ALWAYS either an Asimov dataset or a toy, both synthetic;
    this function is never handed real unblinded data by anything in
    this task) plus the Gaussian nuisance-constraint penalty."""
    total = gaussian_constraint_nll(par)
    for cat in CATEGORIES:
        nu = expected_counts(cat, par, mH, edges_arr)
        total += poisson_nll(data[cat], nu)
    return total
