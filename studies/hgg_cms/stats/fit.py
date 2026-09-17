"""
Statistical-analysis task: fitting the full model (multi-start MIGRAD,
a second-optimizer cross-check for headline fits), the CCGV discovery
test statistic q0, and Asimov/toy dataset generation.

ROBUSTNESS LESSON APPLIED (per this task's own instruction to read
`studies/lr_toys/lr_core.py`'s REPORT.md / `studies/atlas_hgg_repro`'s
"Corrections" -- the stuck-null-fit bug: a plausible-looking but wrong
MIGRAD local optimum, off by whole NLL units, silently reported
"valid"): every fit here tries multiple starting points and keeps the
lowest-NLL VALID result; `cross_check_fit` re-minimizes the same NLL
with scipy's L-BFGS-B from the found optimum as an independent check;
`q0_from_fits` asserts the invariant NLL(mu free) <= NLL(mu=0) + 1e-6
(the exact check that caught that bug's symptom there).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from iminuit import Minuit
from scipy.optimize import minimize as scipy_minimize

from studies.hgg_cms.background_model.families import FAMILIES
from studies.hgg_cms.stats.model import (
    CATEGORIES, get_model_inputs, full_param_names, full_nll, expected_counts,
    unpack_params, edges as model_edges, NLL_INVARIANT_TOL,
)

N_STARTS_DEFAULT = 10
NUISANCE_BOUND = 6.0  # +-6 sigma, generous but numerically safe


def default_bounds(names: tuple) -> dict:
    mi = get_model_inputs()
    bounds = {}
    for n in names:
        if n == "mu":
            bounds[n] = (-20.0, 20.0)
        elif n.startswith("theta_"):
            bounds[n] = (-NUISANCE_BOUND, NUISANCE_BOUND)
        elif n.startswith("bkg_"):
            _, cat, pname = n.split("_", 2)
            fam = FAMILIES[mi.categories[cat].bkg_family]
            order = mi.categories[cat].bkg_order
            idx = fam.param_names(order).index(pname)
            total = float(mi.categories[cat].bkg_start_params.sum())
            bounds[n] = fam.bounds(order, total)[idx]
        else:
            raise ValueError(f"unknown parameter {n!r}")
    return bounds


def default_start(names: tuple, mu_start: float = 0.0) -> dict:
    mi = get_model_inputs()
    start = {}
    for n in names:
        if n == "mu":
            start[n] = mu_start
        elif n.startswith("theta_"):
            start[n] = 0.0
        elif n.startswith("bkg_"):
            _, cat, pname = n.split("_", 2)
            fam = FAMILIES[mi.categories[cat].bkg_family]
            order = mi.categories[cat].bkg_order
            idx = fam.param_names(order).index(pname)
            start[n] = float(mi.categories[cat].bkg_start_params[idx])
        else:
            raise ValueError(f"unknown parameter {n!r}")
    return start


def random_starts(names: tuple, rng: np.random.Generator, n_starts: int, mu_start: float = 0.0,
                   base_start: dict = None) -> list:
    """Analytic/nominal start first, then perturbations of it -- nuisances
    perturbed within +-1 sigma, mu within +-2 of its start, background
    coefficients perturbed by a modest multiplicative factor (mirrors
    `fit_background.py`'s own perturbation strategy)."""
    base = base_start or default_start(names, mu_start=mu_start)
    starts = [dict(base)]
    for _ in range(n_starts - 1):
        s = dict(base)
        for n in names:
            if n == "mu":
                s[n] = base[n] + rng.uniform(-2.0, 2.0)
            elif n.startswith("theta_"):
                s[n] = base[n] + rng.normal(0.0, 1.0)
            elif n.startswith("bkg_"):
                s[n] = base[n] * rng.uniform(0.7, 1.3)
        starts.append(s)
    return starts


@dataclass
class FitResult:
    nll: float
    params: dict
    valid: bool
    n_attempts: int
    n_valid: int
    minuit: object = None


def fit_model(data: dict, mH: float, names: tuple, mu_fixed: Optional[float] = None,
              n_starts: int = N_STARTS_DEFAULT, seed: int = 0, base_start: dict = None,
              strategy: int = 1) -> FitResult:
    """Fits the full model to `data` ({cat: counts array}). If
    `mu_fixed` is not None, mu is fixed at that value (the null
    hypothesis fit); otherwise mu floats (the alternative fit)."""
    bounds = default_bounds(names)
    rng = np.random.default_rng(seed)
    starts = random_starts(names, rng, n_starts, mu_start=(mu_fixed if mu_fixed is not None else 0.0),
                            base_start=base_start)

    free_names = [n for n in names if not (n == "mu" and mu_fixed is not None)]

    def nll_fn(*par):
        full = dict(zip(free_names, par))
        if mu_fixed is not None:
            full["mu"] = mu_fixed
        return full_nll(data, full, mH)

    best_m, n_valid = None, 0
    for start in starts:
        start_vec = [start[n] for n in free_names]
        m = Minuit(nll_fn, *start_vec, name=free_names)
        m.errordef = Minuit.LIKELIHOOD
        for n in free_names:
            m.limits[n] = bounds[n]
        m.strategy = strategy
        try:
            m.migrad()
        except Exception:
            continue
        if m.valid:
            n_valid += 1
        if best_m is None:
            best_m = m
        elif m.valid and not best_m.valid:
            best_m = m
        elif m.valid == best_m.valid and m.fval < best_m.fval:
            best_m = m

    if best_m is None:
        return FitResult(nll=float("nan"), params={}, valid=False, n_attempts=len(starts), n_valid=0)

    params = {n: float(best_m.values[n]) for n in free_names}
    if mu_fixed is not None:
        params["mu"] = mu_fixed
    return FitResult(nll=float(best_m.fval), params=params, valid=bool(best_m.valid),
                      n_attempts=len(starts), n_valid=n_valid, minuit=best_m)


def cross_check_fit(data: dict, mH: float, fit_result: FitResult, mu_fixed: Optional[float] = None,
                     tol_rel: float = 1e-3) -> dict:
    names = tuple(fit_result.params.keys())
    free_names = [n for n in names if not (n == "mu" and mu_fixed is not None)]
    bounds = default_bounds(names)

    def nll_fn(par_vec):
        full = dict(zip(free_names, par_vec))
        if mu_fixed is not None:
            full["mu"] = mu_fixed
        return full_nll(data, full, mH)

    x0 = [fit_result.params[n] for n in free_names]
    bnds = [bounds[n] for n in free_names]
    res = scipy_minimize(nll_fn, x0, method="L-BFGS-B", bounds=bnds, options={"maxiter": 3000})
    improvement = fit_result.nll - res.fun
    rel = improvement / max(abs(fit_result.nll), 1.0)
    return {
        "scipy_nll": float(res.fun), "migrad_nll": fit_result.nll,
        "improvement": float(improvement), "relative_improvement": float(rel),
        "scipy_found_better": bool(rel > tol_rel), "scipy_converged": bool(res.success),
    }


def q0_from_fits(null_fit: FitResult, alt_fit: FitResult) -> dict:
    mu_hat = alt_fit.params.get("mu", 0.0)
    invariant_ok = alt_fit.nll <= null_fit.nll + NLL_INVARIANT_TOL
    if mu_hat < 0:
        q0 = 0.0
    else:
        q0 = max(2.0 * (null_fit.nll - alt_fit.nll), 0.0)
    z = float(np.sqrt(q0))
    twice_dnll = 2.0 * (null_fit.nll - alt_fit.nll)
    signed_z = float(np.sign(mu_hat if mu_hat != 0 else 1.0) * np.sqrt(max(twice_dnll, 0.0)))
    return {
        "q0": q0, "Z": z, "signed_Z": signed_z, "mu_hat": mu_hat,
        "nll_null": null_fit.nll, "nll_alt": alt_fit.nll,
        "invariant_ok": invariant_ok,
        "both_valid": bool(null_fit.valid and alt_fit.valid),
    }


def mu_hesse_error(fit_result: FitResult) -> float:
    """An explicit HESSE call on the fit's own minimized point --
    MIGRAD's automatic covariance estimate (available without calling
    HESSE) is not as reliable, per iminuit's own documentation. Returns
    nan if mu is fixed (nothing to report) or HESSE itself fails (e.g.
    on an already-pathological fit); never raises."""
    if fit_result.minuit is None or "mu" not in fit_result.params:
        return float("nan")
    try:
        if fit_result.minuit.fixed["mu"]:
            return float("nan")
    except KeyError:
        return float("nan")
    try:
        fit_result.minuit.hesse()
        return float(fit_result.minuit.errors["mu"])
    except Exception:
        return float("nan")


def fmin_diagnostics(fit_result: FitResult) -> dict:
    """MIGRAD's own detailed convergence diagnostics for this fit --
    which of these is set (if any) explains WHY `fit_result.valid` is
    False, rather than just that it is. Empty dict if no Minuit object
    is attached.

    IMPORTANT (found diagnosing the 18 Sep 2026 validation run's fit-
    failure rates): `fit_result.valid` (iminuit's `Minuit.valid`, i.e.
    `fmin.is_valid`) is a WEAKER condition than "the uncertainty is
    trustworthy" -- per iminuit's own docs, `is_valid` requires only
    `not has_reached_call_limit` and `not is_above_max_edm`. It does
    NOT require `has_accurate_covar`, `has_posdef_covar`, or
    `not has_parameters_at_limit` -- a fit can be `valid=True` with an
    untrustworthy covariance (and therefore an untrustworthy mu_err).
    A STRICT validity check for "this toy's mu_err can be trusted"
    should additionally require `has_accurate_covar` and
    `has_posdef_covar` (added here) and a finite, positive mu_err --
    see `strict_valid` below and `mu_hesse_error`'s callers."""
    if fit_result.minuit is None:
        return {}
    fm = fit_result.minuit.fmin
    return {
        "edm": float(fm.edm),
        "has_parameters_at_limit": bool(fm.has_parameters_at_limit),
        "has_accurate_covar": bool(fm.has_accurate_covar),
        "has_posdef_covar": bool(fm.has_posdef_covar),
        "has_made_posdef_covar": bool(fm.has_made_posdef_covar),
        "has_valid_parameters": bool(fm.has_valid_parameters),
        "hesse_failed": bool(fm.hesse_failed),
        "has_reached_call_limit": bool(fm.has_reached_call_limit),
        "is_above_max_edm": bool(fm.is_above_max_edm),
    }


def strict_valid(fmin: dict, mu_err: float = None) -> bool:
    """The stricter validity check described in `fmin_diagnostics`'s
    own docstring: MIGRAD's cheap `valid` plus an accurate, genuinely
    positive-definite covariance (not forced positive-definite), and
    -- if `mu_err` is given -- a finite, positive uncertainty on mu.
    `fmin` should be a POST-HESSE snapshot (e.g. `alt_fmin_post_hesse`)
    for this to mean anything about mu_err's own trustworthiness."""
    if not fmin:
        return False
    ok = (fmin.get("has_valid_parameters") and fmin.get("has_accurate_covar")
          and fmin.get("has_posdef_covar") and not fmin.get("has_made_posdef_covar")
          and not fmin.get("hesse_failed") and not fmin.get("is_above_max_edm"))
    if mu_err is not None:
        ok = ok and np.isfinite(mu_err) and mu_err > 0
    return bool(ok)


def toy_q0(rng: np.random.Generator, par_true: dict, mH: float, names: tuple, seed_base: int) -> dict:
    """ONE toy: generate, fit null (mu=0, warm-started at par_true) and
    alt (mu free, warm-started at the null's own converged point --
    guarantees NLL(alt start) == NLL(null optimum), matching check (i)
    in `studies/atlas_hgg_repro/REPORT.md`'s "Corrections"), check the
    NLL invariant, and retry once from a fresh generic start if it's
    violated or either fit is invalid -- mirrors
    `background_model/bias_study.py`'s own toy-retry pattern. Returns a
    dict with q0 info plus `failed` (never silently dropped), the
    alt fit's HESSE uncertainty on mu (`mu_err` -- needed to compute a
    genuine pull, (mu_hat - mu_true) / mu_err, rather than just the raw
    residual mu_hat - mu_true; this field did not exist before 18 Sep
    2026's validation-run pull-width review, which found "pull_width"
    had been computed without it), and MIGRAD's own convergence
    diagnostics for both fits (`null_fmin`, `alt_fmin`)."""
    toy = generate_toy(rng, par_true, mH)
    null_fit = fit_model(toy, mH, names, mu_fixed=0.0, n_starts=1, seed=seed_base, base_start=par_true)
    alt_fit = fit_model(toy, mH, names, mu_fixed=None, n_starts=1, seed=seed_base + 1,
                         base_start=null_fit.params if null_fit.valid else par_true)
    info = q0_from_fits(null_fit, alt_fit)
    retried = False
    if not (info["invariant_ok"] and info["both_valid"]):
        retried = True
        alt_fit2 = fit_model(toy, mH, names, mu_fixed=None, n_starts=1, seed=seed_base + 2, base_start=par_true)
        info2 = q0_from_fits(null_fit, alt_fit2)
        if info2["nll_alt"] < info["nll_alt"] or (info2["invariant_ok"] and not info["invariant_ok"]):
            alt_fit, info = alt_fit2, info2
    info["failed"] = not (info["invariant_ok"] and info["both_valid"])
    info["retried"] = retried
    info["null_valid"] = null_fit.valid
    info["alt_valid"] = alt_fit.valid
    # fmin snapshots MUST be taken before mu_hesse_error() below: calling
    # .hesse() explicitly recomputes the covariance and can change fmin's
    # flags (e.g. reveal a large post-Hesse EDM MIGRAD's own cheaper
    # automatic estimate didn't catch) -- capturing fmin afterwards would
    # silently describe a DIFFERENT fit state than the one `valid`/
    # `failed` above were actually decided from (caught while diagnosing
    # the 18 Sep 2026 validation run's fit-failure rates).
    info["null_fmin"] = fmin_diagnostics(null_fit)
    info["alt_fmin"] = fmin_diagnostics(alt_fit)
    info["mu_err"] = mu_hesse_error(alt_fit)
    info["alt_fmin_post_hesse"] = fmin_diagnostics(alt_fit)
    info["n_obs_total"] = float(sum(toy[cat].sum() for cat in toy))
    return info


def generate_asimov(par: dict, mH: float) -> dict:
    e = model_edges()
    return {cat: expected_counts(cat, par, mH, e) for cat in CATEGORIES}


def generate_toy(rng: np.random.Generator, par: dict, mH: float) -> dict:
    e = model_edges()
    return {cat: rng.poisson(expected_counts(cat, par, mH, e)).astype(float) for cat in CATEGORIES}
