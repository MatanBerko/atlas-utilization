"""
Background-model task, Part 2: robust background-only fitting
(multi-start MIGRAD + a second-optimizer cross-check), the F-test order
selection rule, and the goodness-of-fit check.

LESSON APPLIED (per this task's own instruction to read
`studies/lr_toys/lr_core.py`'s REPORT.md / `studies/atlas_hgg_repro`'s
"Corrections"): a single-start fit from a generic flat guess can land in
a plausible-looking but wrong local optimum (that project's own
profiled-significance bug: a null fit stuck 2.4662 NLL units above the
true minimum, silently, MIGRAD reporting "valid" anyway). The fix
applied there -- multiple starting points, keep the best VALID result,
and an explicit invariant check comparing nested models -- is applied
here: every fit in this module tries >= 10 starting points and keeps the
lowest-NLL VALID result (falling back to the lowest-NLL overall, flagged,
only if none are valid).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from iminuit import Minuit
from scipy.optimize import minimize as scipy_minimize, nnls
from scipy.stats import chi2 as chi2_dist

from studies.hgg_cms.background_model.families import FAMILIES
from studies.hgg_cms.stats.binning import poisson_nll

N_STARTS_DEFAULT = 10
RNG_SEED_STARTS = 20260918


def _analytic_linear_start(family_name: str, order: int, edges: np.ndarray,
                            counts: np.ndarray, mask: np.ndarray):
    """For the two LINEAR-in-coefficients families (Bernstein, Laurent),
    solve the masked design-matrix least-squares problem directly --
    Bernstein via non-negative least squares (respects c_i >= 0 by
    construction), Laurent via plain least squares (coefficients may be
    any sign). Returns None for the two non-linear families."""
    fam = FAMILIES[family_name]
    if family_name == "bernstein":
        M = fam.design_matrix(edges, order)[mask]
        sol, _ = nnls(M, counts[mask])
        return sol
    if family_name == "laurent":
        M = fam.design_matrix(edges, order)[mask]
        sol, *_ = np.linalg.lstsq(M, counts[mask], rcond=None)
        return sol
    return None


def _analytic_loglinear_start(family_name: str, order: int, edges: np.ndarray,
                               counts: np.ndarray, mask: np.ndarray):
    """For expsum/powersum (non-linear in b_i): a rough single-component
    guess from a weighted log-linear regression of the sideband histogram
    against the family's own x variable, then replicated/perturbed across
    `order` terms with decreasing amplitude -- a documented, simple
    analytic starting point, not claimed to be a good fit on its own."""
    centers = 0.5 * (edges[:-1] + edges[1:])
    c, m = counts[mask], centers[mask]
    pos = c > 0
    if pos.sum() < 3:
        return None
    if family_name == "expsum":
        x = (m[pos] - 105.0) / 75.0
    else:
        x = np.log(m[pos] / 105.0)
    y = np.log(c[pos])
    w = c[pos]  # weight by counts (more weight where statistics are better)
    A = np.vstack([x, np.ones_like(x)]).T
    W = np.diag(w)
    try:
        coef, *_ = np.linalg.lstsq(W @ A, W @ y, rcond=None)
    except np.linalg.LinAlgError:
        return None
    b0, log_a0 = coef[0], coef[1]
    a0 = np.exp(log_a0) * 75.0 if family_name == "expsum" else np.exp(log_a0)
    params = []
    for i in range(order):
        frac = 0.6 ** i
        params += [a0 * frac / max(sum(0.6 ** k for k in range(order)), 1e-9), b0 - 0.5 * i]
    return np.array(params)


def _random_start(family_name: str, order: int, total_count: float, rng: np.random.Generator):
    fam = FAMILIES[family_name]
    n = fam.n_params(order)
    if family_name == "bernstein":
        return rng.uniform(0.0, 2.0 * max(total_count, 1.0) / (order + 1), size=n)
    if family_name == "laurent":
        scale = max(total_count, 1.0) * 1e4
        return rng.uniform(-scale, scale, size=n)
    if family_name == "expsum":
        out = []
        for _ in range(order):
            out += [rng.uniform(-2.0, 2.0) * max(total_count, 1.0), rng.uniform(-15.0, 8.0)]
        return np.array(out)
    if family_name == "powersum":
        out = []
        for _ in range(order):
            out += [rng.uniform(-2.0, 2.0) * max(total_count, 1.0), rng.uniform(-20.0, 5.0)]
        return np.array(out)
    raise ValueError(family_name)


def starting_points(family_name: str, order: int, edges: np.ndarray, counts: np.ndarray,
                     mask: np.ndarray, n_starts: int = N_STARTS_DEFAULT,
                     seed: int = RNG_SEED_STARTS) -> list:
    rng = np.random.default_rng(seed)
    total_count = float(counts[mask].sum())
    pts = []
    analytic = _analytic_linear_start(family_name, order, edges, counts, mask)
    if analytic is None:
        analytic = _analytic_loglinear_start(family_name, order, edges, counts, mask)
    if analytic is not None and np.all(np.isfinite(analytic)):
        pts.append(np.asarray(analytic, dtype=float))
        # a couple of perturbations of the analytic point too
        for _ in range(min(2, n_starts - 1)):
            pts.append(analytic * rng.uniform(0.7, 1.3, size=len(analytic)))
    while len(pts) < n_starts:
        pts.append(_random_start(family_name, order, total_count, rng))
    return pts[:max(n_starts, len(pts) if analytic is None else n_starts)]


@dataclass
class BackgroundFitResult:
    family: str
    order: int
    params: np.ndarray
    param_names: tuple
    nll: float
    valid: bool
    n_attempts: int
    n_valid: int
    all_nlls: list
    edges: np.ndarray = field(repr=False, default=None)
    mask: np.ndarray = field(repr=False, default=None)


def fit_family_order(family_name: str, order: int, edges: np.ndarray, counts: np.ndarray,
                      mask: np.ndarray, n_starts: int = N_STARTS_DEFAULT,
                      seed: int = RNG_SEED_STARTS) -> BackgroundFitResult:
    fam = FAMILIES[family_name]
    names = fam.param_names(order)
    total_count = float(counts[mask].sum())
    bounds = fam.bounds(order, total_count)
    data = counts[mask]

    def nll_fn(*par):
        pred = fam.bin_expectation(edges, order, np.array(par))[mask]
        return poisson_nll(data, pred)

    starts = starting_points(family_name, order, edges, counts, mask, n_starts, seed)

    best = None
    all_nlls = []
    n_valid = 0
    for start in starts:
        start = np.clip(start, [b[0] for b in bounds], [b[1] for b in bounds])
        m = Minuit(nll_fn, *start, name=names)
        m.errordef = Minuit.LIKELIHOOD
        for n, b in zip(names, bounds):
            m.limits[n] = b
        m.strategy = 1
        try:
            m.migrad()
        except Exception:
            all_nlls.append(float("nan"))
            continue
        all_nlls.append(float(m.fval))
        if m.valid:
            n_valid += 1
        if best is None:
            best = m
        elif m.valid and not best.valid:
            best = m
        elif m.valid == best.valid and m.fval < best.fval:
            best = m

    if best is None:
        return BackgroundFitResult(family_name, order, np.full(len(names), np.nan), names,
                                    float("nan"), False, len(starts), 0, all_nlls, edges, mask)

    params = np.array([best.values[n] for n in names])
    return BackgroundFitResult(family_name, order, params, names, float(best.fval), bool(best.valid),
                                len(starts), n_valid, all_nlls, edges, mask)


def cross_check_second_optimizer(family_name: str, order: int, edges: np.ndarray, counts: np.ndarray,
                                  mask: np.ndarray, fit_result: BackgroundFitResult, tol_rel: float = 1e-3):
    """Re-minimizes the SAME NLL with scipy's L-BFGS-B, started from the
    already-found best point, and checks it doesn't find anything
    meaningfully lower -- a cross-check against exactly the failure mode
    documented in this module's docstring (a plausible-looking but wrong
    MIGRAD minimum)."""
    fam = FAMILIES[family_name]
    bounds = fam.bounds(order, float(counts[mask].sum()))
    data = counts[mask]

    def nll_fn(par):
        pred = fam.bin_expectation(edges, order, par)[mask]
        return poisson_nll(data, pred)

    res = scipy_minimize(nll_fn, fit_result.params, method="L-BFGS-B", bounds=bounds,
                          options={"maxiter": 2000})
    improvement = fit_result.nll - res.fun
    rel = improvement / max(abs(fit_result.nll), 1.0)
    return {
        "scipy_nll": float(res.fun), "migrad_nll": fit_result.nll,
        "improvement": float(improvement), "relative_improvement": float(rel),
        "scipy_found_better": bool(rel > tol_rel), "scipy_converged": bool(res.success),
    }


def f_test_p_value(nll_low: float, ndf_low: int, nll_high: float, ndf_high: int) -> dict:
    delta_nll = nll_low - nll_high
    delta_ndf = ndf_low - ndf_high
    stat = 2.0 * delta_nll
    if delta_ndf <= 0 or stat < 0:
        return {"delta_nll": delta_nll, "delta_ndf": delta_ndf, "stat": stat, "p_value": 1.0}
    p = float(chi2_dist.sf(stat, delta_ndf))
    return {"delta_nll": delta_nll, "delta_ndf": delta_ndf, "stat": stat, "p_value": p}


def goodness_of_fit(family_name: str, order: int, edges: np.ndarray, counts: np.ndarray,
                     mask: np.ndarray, params: np.ndarray, min_expected: float = 5.0) -> dict:
    fam = FAMILIES[family_name]
    pred_all = fam.bin_expectation(edges, order, params)
    pred, obs = pred_all[mask], counts[mask]
    use = pred >= min_expected
    chi2_stat = float(np.sum((obs[use] - pred[use]) ** 2 / pred[use]))
    ndf = int(np.sum(use)) - fam.n_params(order)
    p_value = float(chi2_dist.sf(chi2_stat, ndf)) if ndf > 0 else float("nan")
    return {
        "chi2": chi2_stat, "ndf": ndf, "p_value": p_value,
        "n_bins_used": int(np.sum(use)), "n_bins_total_sideband": int(mask.sum()),
    }
