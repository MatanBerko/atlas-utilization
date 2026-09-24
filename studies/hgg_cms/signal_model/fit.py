"""
Signal-model task, Part 2: weighted unbinned maximum-likelihood shape
fits, with an asymptotically-correct covariance for signed (negative +
positive) event weights, and a pre-set binned goodness-of-fit / model-
selection rule.

METHOD CHOSEN for signed-weight uncertainties: the SANDWICH (robust)
covariance estimator, V = H^-1 C H^-1, where
  H_jk = sum_i w_i * (-d^2 ln f(x_i;theta) / dtheta_j dtheta_k)   (weighted Hessian)
  C_jk = sum_i w_i^2 * (d ln f(x_i;theta)/dtheta_j) * (d ln f(x_i;theta)/dtheta_k)
This is the standard general solution to "parameter uncertainties in a
weighted unbinned maximum-likelihood fit" -- the exact problem studied by
Langenbruch, arXiv:1911.01303 ("Parameter uncertainties in weighted
unbinned maximum likelihood fits"), which derives and validates
asymptotically-correct expressions of this sandwich form. This module's
H/C are computed independently here (via numerical differentiation of
the analytic DCB/mixture log-density, not copied from the paper's own
code or exact equation numbers), so treat this as "the same general
method the paper validates," not a verbatim reproduction of its
formulas -- UNVERIFIED at that level of precision. The alternative
offered by this task (event bootstrap) was NOT used, to avoid the extra
runtime of refitting the shape ~100+ times over the largest (EBEB,
~7.8x10^5-event) combined sample; the sandwich estimator needs only one
fit plus O(n_params^2) vectorized array evaluations.

Numerical derivatives are computed with central finite differences on
the analytic log-density, vectorized over all events at once per
parameter (perturb one parameter, evaluate log f(x) for every event in
one array call) -- O(n_params) gradient evaluations and O(n_params^2)
Hessian evaluations, each a cheap vectorized numpy pass, never a
per-event Python loop.

Pre-set model-selection rule (stated BEFORE any fit was run, per this
task's own instructions): fit a pure DCB first. Additionally fit
DCB + extra Gaussian. Adopt the DCB+Gaussian mixture ONLY IF both:
  (a) it improves the binned chi^2 (0.25 GeV bins, 105-180 GeV, bins
      with model-predicted content >= 5) by more than 10 units, AND
  (b) the pure-DCB fit has chi^2/ndf > 1.5.
Otherwise keep the pure DCB as the final model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from iminuit import Minuit

from studies.hgg_cms.signal_model.shapes import (
    SignalShape, DCB_PARAM_NAMES, GAUSS_EXTRA_PARAM_NAMES,
)

# Finite-difference step sizes per parameter (absolute, chosen relative
# to each parameter's typical scale -- these are NOT the fit step sizes
# Minuit uses internally, only the step used to numerically differentiate
# the analytic log-density afterwards for the sandwich covariance).
FD_STEP = {
    "mu": 1e-3, "sigma": 1e-4, "alphaL": 1e-4, "nL": 1e-3,
    "alphaR": 1e-4, "nR": 1e-3, "frac2": 1e-5, "mu2": 1e-3, "sigma2": 1e-4,
}

DCB_BOUNDS = {
    "mu": (100.0, 150.0), "sigma": (0.3, 15.0),
    "alphaL": (0.3, 8.0), "nL": (1.05, 100.0),
    "alphaR": (0.3, 8.0), "nR": (1.05, 100.0),
}
GAUSS2_BOUNDS = {"frac2": (0.001, 0.6), "mu2": (100.0, 150.0), "sigma2": (0.3, 30.0)}


def _log_pdf(x: np.ndarray, param_vec: np.ndarray, names: tuple, use_gauss2: bool) -> np.ndarray:
    params = dict(zip(names, param_vec))
    shape = SignalShape(params=params, use_gauss2=use_gauss2)
    pdf = shape.pdf(x)
    return np.log(np.clip(pdf, 1e-300, None))


def _weighted_nll(x: np.ndarray, w: np.ndarray, param_vec: np.ndarray, names: tuple, use_gauss2: bool) -> float:
    return -float(np.sum(w * _log_pdf(x, param_vec, names, use_gauss2)))


@dataclass
class FitResult:
    shape: SignalShape
    nll: float
    valid: bool
    n_events: int
    sum_weights: float


def _initial_guess(mgg: np.ndarray, w: np.ndarray, use_gauss2: bool):
    mu0 = float(np.average(mgg, weights=w))
    sigma0 = float(np.sqrt(np.average((mgg - mu0) ** 2, weights=np.abs(w))))
    sigma0 = max(sigma0, 1.0)
    start = {"mu": mu0, "sigma": sigma0, "alphaL": 1.5, "nL": 5.0, "alphaR": 1.5, "nR": 5.0}
    if use_gauss2:
        start.update({"frac2": 0.15, "mu2": mu0, "sigma2": sigma0 * 2.0})
    return start


def fit_signal_shape(mgg: np.ndarray, w: np.ndarray, use_gauss2: bool = False,
                      start: Optional[dict] = None) -> FitResult:
    """Weighted unbinned ML fit of the DCB (or DCB+Gaussian) shape to
    `mgg`, event weights `w` (may be negative). Minimizes
    -sum_i w_i * ln f(x_i; theta) via iminuit/MIGRAD. Does not compute
    the covariance here -- see `sandwich_covariance` for that (kept
    separate since it is only needed for the final adopted model, not
    every trial fit)."""
    mgg = np.asarray(mgg, dtype=float)
    w = np.asarray(w, dtype=float)
    names = DCB_PARAM_NAMES + (GAUSS_EXTRA_PARAM_NAMES if use_gauss2 else ())
    bounds = dict(DCB_BOUNDS)
    if use_gauss2:
        bounds.update(GAUSS2_BOUNDS)
    start = start or _initial_guess(mgg, w, use_gauss2)
    start_vec = [start[n] for n in names]

    def nll_fn(*par):
        return _weighted_nll(mgg, w, np.array(par), names, use_gauss2)

    m = Minuit(nll_fn, *start_vec, name=names)
    m.errordef = Minuit.LIKELIHOOD
    for n in names:
        m.limits[n] = bounds[n]
    m.strategy = 1
    m.migrad()

    params = {n: float(m.values[n]) for n in names}
    shape = SignalShape(params=params, use_gauss2=use_gauss2, param_names=names)
    return FitResult(shape=shape, nll=float(m.fval), valid=bool(m.valid),
                      n_events=len(mgg), sum_weights=float(w.sum()))


def sandwich_covariance(mgg: np.ndarray, w: np.ndarray, shape: SignalShape) -> np.ndarray:
    """V = H^-1 C H^-1 (see module docstring) at the fitted `shape`'s own
    parameters. Returns an (n_params, n_params) array in the order of
    `shape.param_names`."""
    mgg = np.asarray(mgg, dtype=float)
    w = np.asarray(w, dtype=float)
    names = shape.param_names
    theta = np.array([shape.params[n] for n in names])
    n_par = len(names)
    steps = np.array([FD_STEP[n] for n in names])

    def ll(theta_vec):
        return _log_pdf(mgg, theta_vec, names, shape.use_gauss2)

    ll0 = ll(theta)

    # Gradient per event (N, n_par): central differences.
    grad = np.empty((len(mgg), n_par))
    ll_plus = {}
    ll_minus = {}
    for j in range(n_par):
        tp = theta.copy(); tp[j] += steps[j]
        tm = theta.copy(); tm[j] -= steps[j]
        ll_plus[j] = ll(tp)
        ll_minus[j] = ll(tm)
        grad[:, j] = (ll_plus[j] - ll_minus[j]) / (2 * steps[j])

    # Hessian per event, summed with weight w_i (not w_i^2), via 4-point
    # central differences using the same +/- evaluations where possible.
    H = np.zeros((n_par, n_par))
    for j in range(n_par):
        for k in range(j, n_par):
            if j == k:
                d2 = (ll_plus[j] - 2 * ll0 + ll_minus[j]) / (steps[j] ** 2)
            else:
                tpp = theta.copy(); tpp[j] += steps[j]; tpp[k] += steps[k]
                tpm = theta.copy(); tpm[j] += steps[j]; tpm[k] -= steps[k]
                tmp = theta.copy(); tmp[j] -= steps[j]; tmp[k] += steps[k]
                tmm = theta.copy(); tmm[j] -= steps[j]; tmm[k] -= steps[k]
                d2 = (ll(tpp) - ll(tpm) - ll(tmp) + ll(tmm)) / (4 * steps[j] * steps[k])
            val = -float(np.sum(w * d2))
            H[j, k] = val
            H[k, j] = val

    C = grad.T @ (w[:, None] ** 2 * grad)

    try:
        Hinv = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        return np.full((n_par, n_par), np.nan)
    return Hinv @ C @ Hinv


def binned_chi2(mgg: np.ndarray, w: np.ndarray, shape: SignalShape, edges: np.ndarray,
                 n_free_params: int, min_expected: float = 5.0) -> dict:
    """Binned chi^2 goodness-of-fit: observed weighted histogram vs. the
    shape's predicted counts (total observed weight in-range times the
    shape's own bin probabilities). Per-bin variance = sum(w_i^2) in that
    bin (proper weighted-histogram variance, valid for signed weights).
    Only bins with model-PREDICTED content >= `min_expected` are
    included, per this task's pre-set rule."""
    mgg = np.asarray(mgg, dtype=float)
    w = np.asarray(w, dtype=float)
    in_range = (mgg >= edges[0]) & (mgg <= edges[-1])
    m, ww = mgg[in_range], w[in_range]

    obs, _ = np.histogram(m, bins=edges, weights=ww)
    obs_w2, _ = np.histogram(m, bins=edges, weights=ww ** 2)

    total_obs = float(ww.sum())
    probs = shape.bin_probabilities(edges)
    pred = total_obs * probs

    use = pred >= min_expected
    var = np.clip(obs_w2, np.finfo(float).tiny, None)
    chi2 = float(np.sum((obs[use] - pred[use]) ** 2 / var[use]))
    ndf = int(np.sum(use)) - n_free_params
    return {
        "chi2": chi2, "ndf": ndf, "chi2_per_ndf": chi2 / ndf if ndf > 0 else float("nan"),
        "n_bins_used": int(np.sum(use)), "n_bins_total": len(edges) - 1,
    }


def decide_use_gauss2(chi2_dcb: dict, chi2_dcb_gauss: dict,
                       chi2_improvement_threshold: float = 10.0,
                       chi2_per_ndf_threshold: float = 1.5) -> dict:
    """Pre-set rule (module docstring): add the extra Gaussian only if it
    improves chi2 by > `chi2_improvement_threshold` AND the pure-DCB
    chi2/ndf > `chi2_per_ndf_threshold`."""
    improvement = chi2_dcb["chi2"] - chi2_dcb_gauss["chi2"]
    dcb_poor = chi2_dcb["chi2_per_ndf"] > chi2_per_ndf_threshold
    use_gauss2 = bool(improvement > chi2_improvement_threshold and dcb_poor)
    return {
        "chi2_improvement": improvement,
        "dcb_chi2_per_ndf": chi2_dcb["chi2_per_ndf"],
        "dcb_chi2_per_ndf_exceeds_threshold": dcb_poor,
        "improvement_exceeds_threshold": improvement > chi2_improvement_threshold,
        "use_gauss2": use_gauss2,
    }
