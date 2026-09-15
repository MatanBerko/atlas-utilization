"""
Core model and profiled likelihood-ratio (LR) machinery for bump-search toy
studies, built to be reused later on real CMS H->gamma-gamma data.

Reference: Cowan, Cranmer, Gross, Vitells, "Asymptotic formulae for
likelihood-based tests of new physics", Eur. Phys. J. C 71 (2011) 1554,
arXiv:1007.1727 ("CCGV" below). Equation numbers refer to that paper.

Model
-----
- Mass range [MASS_MIN, MASS_MAX), binned histogram, BIN_WIDTH-GeV bins.
- Background: an exponential-of-polynomial shape in x = (m - MASS_MIN) / (MASS_MAX - MASS_MIN),
  b(m) ~ exp(sum_k coeffs[k] * x**(k+1)), normalized so the *sum over all bins*
  equals a free total-yield parameter n_bkg. The number of coefficients sets
  the shape's flexibility (1 = single exponential, 2 = the "true" quadratic
  shape used to generate toys, 3 = a cubic-in-exponent alternative).
- Signal: a Gaussian at mass mh with width sigma, integrated exactly over each
  bin (via the normal CDF), scaled by a signal-strength parameter mu times a
  reference yield s_ref. mu is allowed to float negative in fits; nothing in
  this module clips it -- the discovery test statistic q0 does that.

All "bin expectation" functions return an array of shape (n_bins,): the mean
Poisson count expected in each bin. Likelihood fits work directly on binned
Poisson data via `poisson_nll`.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm
from iminuit import Minuit

# ----------------------------------------------------------------------------
# Fixed analysis window
# ----------------------------------------------------------------------------
MASS_MIN = 100.0
MASS_MAX = 180.0
N_BINS = 80
BIN_WIDTH = (MASS_MAX - MASS_MIN) / N_BINS  # 1.0 GeV

# "True" generator settings used throughout this study (see REPORT.md for
# why these numbers were chosen).
P1_TRUE = -4.0
P2_TRUE = 0.8
N_BKG_TRUE = 250_000.0
MH_NOMINAL = 125.0
SIGMA_NOMINAL = 2.0

# 5-point Gauss-Legendre nodes/weights on [-1, 1] (used to integrate the
# background shape over each bin to high accuracy without repeated calls to
# a slow numerical-quadrature routine -- this runs inside every likelihood
# evaluation, so it has to be fast as well as accurate).
_GL_NODES, _GL_WEIGHTS = np.polynomial.legendre.leggauss(5)


def bin_edges() -> np.ndarray:
    """The (N_BINS + 1) bin edges in GeV, from MASS_MIN to MASS_MAX."""
    return np.linspace(MASS_MIN, MASS_MAX, N_BINS + 1)


def bin_centers(edges: np.ndarray | None = None) -> np.ndarray:
    if edges is None:
        edges = bin_edges()
    return 0.5 * (edges[:-1] + edges[1:])


def to_x(m: np.ndarray) -> np.ndarray:
    """Map a mass (GeV) to the dimensionless x used in the background shape."""
    return (m - MASS_MIN) / (MASS_MAX - MASS_MIN)


def gl_bin_nodes(edges: np.ndarray | None = None):
    """
    Precompute Gauss-Legendre integration nodes and weights for every bin.

    Returns
    -------
    nodes : ndarray, shape (n_bins, 5)
        Mass values (GeV) at which to evaluate the background density.
    weights : ndarray, shape (n_bins, 5)
        Physical (GeV) weights such that weights[i].sum() == bin width,
        and sum_j weights[i, j] * f(nodes[i, j]) approximates
        integral of f over bin i.
    """
    if edges is None:
        edges = bin_edges()
    lo = edges[:-1][:, None]
    hi = edges[1:][:, None]
    half = 0.5 * (hi - lo)
    mid = 0.5 * (hi + lo)
    nodes = mid + half * _GL_NODES[None, :]
    weights = half * _GL_WEIGHTS[None, :]
    return nodes, weights


def background_shape_density(x: np.ndarray, coeffs: np.ndarray) -> np.ndarray:
    """Unnormalized background density exp(sum_k coeffs[k] * x**(k+1))."""
    coeffs = np.asarray(coeffs, dtype=float)
    exponent = np.zeros_like(x, dtype=float)
    for k, c in enumerate(coeffs):
        exponent = exponent + c * x ** (k + 1)
    # MIGRAD transiently probes wild coefficient values while searching;
    # clip the exponent (not the physics result -- the minimum is always
    # far from this range) so that stays numerically finite instead of
    # producing inf/nan that could derail the minimizer.
    return np.exp(np.clip(exponent, -50.0, 50.0))


def background_bin_expectation(nodes: np.ndarray, weights: np.ndarray,
                                n_bkg: float, coeffs: np.ndarray,
                                norm_nodes: np.ndarray | None = None,
                                norm_weights: np.ndarray | None = None) -> np.ndarray:
    """
    Mean background count in every bin in `nodes`, for shape coefficients
    `coeffs`, normalized so that n_bkg means "total over `norm_nodes`"
    (defaulting to `nodes` itself when not given).

    The `norm_nodes`/`norm_weights` split matters for a sideband-only fit
    (T3b): evaluating the Poisson likelihood only over sideband bins, but
    always normalizing n_bkg against the FULL mass range, means the fitted
    n_bkg and shape can be plugged straight into a full-range prediction
    afterwards, with no separate rescaling step.
    """
    if norm_nodes is None:
        norm_nodes, norm_weights = nodes, weights
    x = to_x(nodes)
    raw = np.sum(weights * background_shape_density(x, coeffs), axis=1)
    x_norm = to_x(norm_nodes)
    raw_norm_total = np.sum(norm_weights * background_shape_density(x_norm, coeffs))
    return n_bkg * raw / raw_norm_total


def signal_bin_expectation(edges: np.ndarray, mu: float, s_ref: float,
                            mh: float, sigma: float) -> np.ndarray:
    """
    Mean signal count in every bin: mu * s_ref * (Gaussian(mh, sigma)
    integrated exactly over the bin via the normal CDF, not evaluated at
    bin centres -- important because sigma is comparable to the bin width).
    """
    cdf = norm.cdf(edges, loc=mh, scale=sigma)
    frac = np.diff(cdf)
    return mu * s_ref * frac


def poisson_nll(n: np.ndarray, nu: np.ndarray) -> float:
    """
    Binned Poisson negative log-likelihood, up to an additive constant
    (sum of log(n_i!)) that is the same for every hypothesis fitted to the
    same data and therefore cancels exactly in any likelihood-ratio test
    statistic computed from two NLL values returned by this function.
    """
    nu_safe = np.clip(nu, 1e-12, None)
    return float(np.sum(nu_safe - n * np.log(nu_safe)))


def asimov_expectation(mu: float, s_ref: float, mh: float, sigma: float,
                        n_bkg: float, coeffs: np.ndarray,
                        edges: np.ndarray | None = None,
                        nodes: np.ndarray | None = None,
                        weights: np.ndarray | None = None) -> np.ndarray:
    """
    The Asimov data set (CCGV Sec. 3.2): per-bin expectation values used
    directly as if they were data. Fitting the Asimov set recovers the
    median expected result exactly (no statistical fluctuation).
    """
    if edges is None:
        edges = bin_edges()
    if nodes is None or weights is None:
        nodes, weights = gl_bin_nodes(edges)
    b = background_bin_expectation(nodes, weights, n_bkg, coeffs)
    s = signal_bin_expectation(edges, mu, s_ref, mh, sigma)
    return s + b


def generate_toy(rng: np.random.Generator, true_expectation: np.ndarray) -> np.ndarray:
    """One Poisson-fluctuated pseudo-experiment around `true_expectation`."""
    return rng.poisson(true_expectation)


# ----------------------------------------------------------------------------
# Fits
# ----------------------------------------------------------------------------

def _bkg_start(n_coeffs: int) -> list[float]:
    defaults = [N_BKG_TRUE, P1_TRUE, P2_TRUE, 0.0, 0.0]
    return defaults[: 1 + n_coeffs]


def fit_bkg_only(data: np.ndarray, nodes: np.ndarray, weights: np.ndarray,
                  n_coeffs: int = 2, start: list[float] | None = None,
                  norm_nodes: np.ndarray | None = None,
                  norm_weights: np.ndarray | None = None):
    """
    Background-only fit (mu implicitly fixed at 0): floats n_bkg and
    `n_coeffs` shape coefficients. Used for the null hypothesis in q0, and
    (with `nodes`/`weights`/`data` restricted to sideband bins, and
    `norm_nodes`/`norm_weights` left at the full range) for the
    sideband-only background estimate used in T3(b).

    Returns a dict with keys: nll, n_bkg, coeffs (ndarray), valid, minuit.
    """
    if start is None:
        start = _bkg_start(n_coeffs)

    def nll_fn(par):
        n_bkg = par[0]
        coeffs = par[1:]
        b = background_bin_expectation(nodes, weights, n_bkg, coeffs,
                                        norm_nodes, norm_weights)
        return poisson_nll(data, b)

    names = ["n_bkg"] + [f"c{k+1}" for k in range(n_coeffs)]
    m = Minuit(nll_fn, start, name=names)
    m.errordef = Minuit.LIKELIHOOD
    m.limits["n_bkg"] = (0.0, None)
    m.strategy = 0
    m.migrad()
    return {
        "nll": float(m.fval),
        "n_bkg": float(m.values["n_bkg"]),
        "coeffs": np.array([m.values[f"c{k+1}"] for k in range(n_coeffs)]),
        "valid": bool(m.valid),
        "minuit": m,
    }


def fit_full(data: np.ndarray, edges: np.ndarray, nodes: np.ndarray,
             weights: np.ndarray, s_ref: float, mh: float, sigma: float,
             n_coeffs: int = 2, mu_start: float = 0.0,
             bkg_start: list[float] | None = None, hesse: bool = False):
    """
    Free (alternative-hypothesis) fit: floats mu (unbounded, may go
    negative), n_bkg, and `n_coeffs` shape coefficients.

    Returns a dict with keys: nll, mu_hat, mu_err (nan unless hesse=True),
    n_bkg, coeffs, valid, minuit.
    """
    if bkg_start is None:
        bkg_start = _bkg_start(n_coeffs)
    start = [mu_start] + bkg_start

    def nll_fn(par):
        mu = par[0]
        n_bkg = par[1]
        coeffs = par[2:]
        b = background_bin_expectation(nodes, weights, n_bkg, coeffs)
        s = signal_bin_expectation(edges, mu, s_ref, mh, sigma)
        return poisson_nll(data, s + b)

    names = ["mu", "n_bkg"] + [f"c{k+1}" for k in range(n_coeffs)]
    m = Minuit(nll_fn, start, name=names)
    m.errordef = Minuit.LIKELIHOOD
    m.limits["n_bkg"] = (0.0, None)
    # mu is deliberately left unbounded (may go negative); q0 handles the sign.
    m.strategy = 0
    m.migrad()
    if hesse:
        m.hesse()
    mu_err = float(m.errors["mu"]) if hesse else float("nan")
    return {
        "nll": float(m.fval),
        "mu_hat": float(m.values["mu"]),
        "mu_err": mu_err,
        "n_bkg": float(m.values["n_bkg"]),
        "coeffs": np.array([m.values[f"c{k+1}"] for k in range(n_coeffs)]),
        "valid": bool(m.valid),
        "minuit": m,
    }


def fit_full_floating_width(data: np.ndarray, edges: np.ndarray, nodes: np.ndarray,
                             weights: np.ndarray, s_ref: float, mh: float,
                             n_coeffs: int = 1, mu_start: float = 0.0,
                             sigma_start: float = SIGMA_NOMINAL,
                             sigma_bounds: tuple[float, float] = (0.5, 15.0),
                             bkg_start: list[float] | None = None):
    """
    Like `fit_full`, but also floats the signal width sigma (bounded).
    Used only for T6 (the floating-width trap).
    """
    if bkg_start is None:
        bkg_start = _bkg_start(n_coeffs)
    start = [mu_start, sigma_start] + bkg_start

    def nll_fn(par):
        mu, sigma = par[0], par[1]
        n_bkg = par[2]
        coeffs = par[3:]
        b = background_bin_expectation(nodes, weights, n_bkg, coeffs)
        s = signal_bin_expectation(edges, mu, s_ref, mh, sigma)
        return poisson_nll(data, s + b)

    names = ["mu", "sigma", "n_bkg"] + [f"c{k+1}" for k in range(n_coeffs)]
    m = Minuit(nll_fn, start, name=names)
    m.errordef = Minuit.LIKELIHOOD
    m.limits["n_bkg"] = (0.0, None)
    m.limits["sigma"] = sigma_bounds
    m.strategy = 0
    m.migrad()
    return {
        "nll": float(m.fval),
        "mu_hat": float(m.values["mu"]),
        "sigma_hat": float(m.values["sigma"]),
        "n_bkg": float(m.values["n_bkg"]),
        "coeffs": np.array([m.values[f"c{k+1}"] for k in range(n_coeffs)]),
        "valid": bool(m.valid),
        "minuit": m,
    }


def fit_mu_only(data: np.ndarray, bkg_fixed: np.ndarray, edges: np.ndarray,
                 s_ref: float, mh: float, sigma: float, mu_start: float = 0.0):
    """
    Fit only mu, with the background's per-bin expectation completely
    fixed to `bkg_fixed` (no shape refit). Used for T3(b)'s second stage
    (background fixed to a sideband-only estimate) and T3(c) (background
    fixed to the true generating shape) -- and, in the degenerate 1-bin
    case, for the T0 closed-form cross-check.
    """
    s_unit = signal_bin_expectation(edges, 1.0, s_ref, mh, sigma)

    def nll_fn(mu):
        return poisson_nll(data, mu * s_unit + bkg_fixed)

    m = Minuit(nll_fn, mu_start, name=["mu"])
    m.errordef = Minuit.LIKELIHOOD
    m.strategy = 0
    m.migrad()
    return {
        "nll": float(m.fval),
        "mu_hat": float(m.values["mu"]),
        "valid": bool(m.valid),
        "minuit": m,
    }


# ----------------------------------------------------------------------------
# Test statistic
# ----------------------------------------------------------------------------

def q0_from_nll(nll_null: float, nll_alt: float, mu_hat: float) -> float:
    """
    Discovery test statistic (CCGV eq. 12):
        q0 = 2 (NLL_null - NLL_alt)   if mu_hat >= 0
        q0 = 0                        if mu_hat <  0
    NLL_null/NLL_alt must come from `poisson_nll`-based fits on the SAME
    data, so their additive constants cancel exactly.
    """
    if mu_hat < 0:
        return 0.0
    q0 = 2.0 * (nll_null - nll_alt)
    # Should be >= 0 up to fit-precision noise (the alt fit is a superset
    # of the null fit's parameter space); floor tiny negative noise at 0.
    return max(q0, 0.0)


def z_from_q0(q0: float) -> float:
    """Z = sqrt(q0), the asymptotic discovery significance (CCGV eq. 13)."""
    return float(np.sqrt(q0))


def signed_z_from_nll(nll_null: float, nll_alt: float, mu_hat: float) -> float:
    """
    Signed significance Z_signed = sign(mu_hat) * sqrt(-2 ln lambda(0)),
    with NO zeroing for mu_hat < 0 -- used by BumpNet so that a deficit
    and an excess are both reported, on the same scale, at the same mass.
    """
    twice_dnll = 2.0 * (nll_null - nll_alt)
    magnitude = np.sqrt(max(twice_dnll, 0.0))
    sign = 1.0 if mu_hat >= 0 else -1.0
    return float(sign * magnitude)


def asimov_z_closed_form(s: float, b: float) -> float:
    """
    Closed-form Asimov discovery significance for a single-bin counting
    experiment with known background b (CCGV eq. 97):
        Z_A = sqrt(2[(s+b) ln(1 + s/b) - s])
    """
    return float(np.sqrt(2.0 * ((s + b) * np.log(1.0 + s / b) - s)))


# ----------------------------------------------------------------------------
# Plain-polynomial background model (added for studies/atlas_hgg_repro; does
# not alter any function above it). Unlike the exp-of-polynomial background
# used elsewhere in this module, ATLAS's and BumpNet's H->gamma-gamma fits
# use a plain (e.g. 4th-order) polynomial in a rescaled mass variable
# directly as the background density -- which is not guaranteed positive
# everywhere, so it is floored at a tiny positive value wherever the fit's
# parameter search explores an unphysical region.
# ----------------------------------------------------------------------------

def polynomial_shape_density(x: np.ndarray, coeffs) -> np.ndarray:
    """Plain polynomial density sum_k coeffs[k] * x**k, floored at a tiny
    positive value to guard against negative predicted counts."""
    coeffs = np.asarray(coeffs, dtype=float)
    density = np.zeros_like(x, dtype=float)
    for k, c in enumerate(coeffs):
        density = density + c * x ** k
    return np.clip(density, 1e-8, None)


def polynomial_bin_expectation(nodes: np.ndarray, weights: np.ndarray,
                                n_bkg: float, coeffs, x_min: float, x_scale: float,
                                norm_nodes: np.ndarray | None = None,
                                norm_weights: np.ndarray | None = None) -> np.ndarray:
    """
    Mean background count per bin for a plain-polynomial shape in
    x = (m - x_min) / x_scale, normalized so n_bkg means "total over
    norm_nodes" (defaulting to `nodes` itself -- see
    `background_bin_expectation`'s docstring for why this split exists).
    """
    if norm_nodes is None:
        norm_nodes, norm_weights = nodes, weights
    x = (nodes - x_min) / x_scale
    raw = np.sum(weights * polynomial_shape_density(x, coeffs), axis=1)
    x_norm = (norm_nodes - x_min) / x_scale
    raw_norm_total = np.sum(norm_weights * polynomial_shape_density(x_norm, coeffs))
    return n_bkg * raw / raw_norm_total


def _poly_bkg_start(n_coeffs: int) -> list[float]:
    # c0 = 1 (flat shape as a neutral starting point), higher orders at 0.
    return [1.0] + [0.0] * (n_coeffs - 1)


def fit_bkg_only_poly(data: np.ndarray, nodes: np.ndarray, weights: np.ndarray,
                       x_min: float, x_scale: float, n_coeffs: int = 5,
                       start: list[float] | None = None,
                       n_bkg_start: float = N_BKG_TRUE,
                       norm_nodes: np.ndarray | None = None,
                       norm_weights: np.ndarray | None = None):
    """Background-only (mu=0) fit with a plain polynomial background.
    Mirrors `fit_bkg_only`'s contract exactly, for the polynomial shape.

    `n_bkg_start` defaults to N_BKG_TRUE (the toy-study constant, 250,000)
    to keep existing callers' behaviour identical; pass a data-driven value
    (e.g. the observed total event count) for a real dataset whose scale
    differs -- starting MIGRAD far from the true minimum was found to make
    fits far slower (sometimes markedly so across a large toy loop)."""
    if start is None:
        start = [n_bkg_start] + _poly_bkg_start(n_coeffs)

    def nll_fn(par):
        n_bkg = par[0]
        coeffs = par[1:]
        b = polynomial_bin_expectation(nodes, weights, n_bkg, coeffs, x_min, x_scale,
                                        norm_nodes, norm_weights)
        return poisson_nll(data, b)

    names = ["n_bkg"] + [f"c{k}" for k in range(n_coeffs)]
    m = Minuit(nll_fn, start, name=names)
    m.errordef = Minuit.LIKELIHOOD
    m.limits["n_bkg"] = (0.0, None)
    # strategy=0: this function is the hot loop's null fit (called once per
    # toy, thousands of times); strategy=1's extra Hessian evaluations were
    # a large part of why the mass-scan toy loop was too slow to finish --
    # timed directly (see studies/atlas_hgg_repro/REPORT.md), not guessed.
    m.strategy = 0
    m.migrad()
    return {
        "nll": float(m.fval),
        "n_bkg": float(m.values["n_bkg"]),
        "coeffs": np.array([m.values[f"c{k}"] for k in range(n_coeffs)]),
        "valid": bool(m.valid),
        "minuit": m,
    }


def fit_full_poly(data: np.ndarray, edges: np.ndarray, nodes: np.ndarray,
                   weights: np.ndarray, s_ref: float, mh: float, sigma: float,
                   x_min: float, x_scale: float, n_coeffs: int = 5,
                   mu_start: float = 0.0, bkg_start: list[float] | None = None,
                   n_bkg_start: float = N_BKG_TRUE,
                   hesse: bool = False):
    """Free (mu, background) fit with mh/sigma FIXED and a plain
    polynomial background. Mirrors `fit_full`'s contract exactly.
    See `fit_bkg_only_poly` for why `n_bkg_start` exists."""
    if bkg_start is None:
        bkg_start = [n_bkg_start] + _poly_bkg_start(n_coeffs)
    start = [mu_start] + bkg_start

    def nll_fn(par):
        mu = par[0]
        n_bkg = par[1]
        coeffs = par[2:]
        b = polynomial_bin_expectation(nodes, weights, n_bkg, coeffs, x_min, x_scale)
        s = signal_bin_expectation(edges, mu, s_ref, mh, sigma)
        return poisson_nll(data, s + b)

    names = ["mu", "n_bkg"] + [f"c{k}" for k in range(n_coeffs)]
    m = Minuit(nll_fn, start, name=names)
    m.errordef = Minuit.LIKELIHOOD
    m.limits["n_bkg"] = (0.0, None)
    # strategy=0: this function is the hot loop's alt fit (called at every
    # scanned mass, for every toy -- tens of thousands of calls); see
    # fit_bkg_only_poly's comment for why. hesse=True below still forces a
    # proper Hessian when actually asked for uncertainties.
    m.strategy = 0
    m.migrad()
    if hesse:
        m.hesse()
    mu_err = float(m.errors["mu"]) if hesse else float("nan")
    return {
        "nll": float(m.fval),
        "mu_hat": float(m.values["mu"]),
        "mu_err": mu_err,
        "n_bkg": float(m.values["n_bkg"]),
        "coeffs": np.array([m.values[f"c{k}"] for k in range(n_coeffs)]),
        "valid": bool(m.valid),
        "minuit": m,
    }


def fit_full_poly_floating_mass_width(data: np.ndarray, edges: np.ndarray, nodes: np.ndarray,
                                       weights: np.ndarray, s_ref: float,
                                       x_min: float, x_scale: float, n_coeffs: int = 5,
                                       mu_start: float = 0.0,
                                       mh_start: float = 125.0,
                                       mh_bounds: tuple[float, float] = (110.0, 150.0),
                                       sigma_start: float = 2.0,
                                       sigma_bounds: tuple[float, float] = (0.5, 6.0),
                                       bkg_start: list[float] | None = None,
                                       n_bkg_start: float = N_BKG_TRUE,
                                       hesse: bool = False):
    """Free (mu, mh, sigma, background) fit, all floating, with a plain
    polynomial background -- the main "Fit 2" of studies/atlas_hgg_repro.
    See `fit_bkg_only_poly` for why `n_bkg_start` exists."""
    if bkg_start is None:
        bkg_start = [n_bkg_start] + _poly_bkg_start(n_coeffs)
    start = [mu_start, mh_start, sigma_start] + bkg_start

    def nll_fn(par):
        mu, mh, sigma = par[0], par[1], par[2]
        n_bkg = par[3]
        coeffs = par[4:]
        b = polynomial_bin_expectation(nodes, weights, n_bkg, coeffs, x_min, x_scale)
        s = signal_bin_expectation(edges, mu, s_ref, mh, sigma)
        return poisson_nll(data, s + b)

    names = ["mu", "mh", "sigma", "n_bkg"] + [f"c{k}" for k in range(n_coeffs)]
    m = Minuit(nll_fn, start, name=names)
    m.errordef = Minuit.LIKELIHOOD
    m.limits["n_bkg"] = (0.0, None)
    m.limits["mh"] = mh_bounds
    m.limits["sigma"] = sigma_bounds
    # NOTE (see REPORT.md "Fit 2 convergence flag"): on the real ATLAS
    # dataset, this fit reliably reports fmin.is_valid=False, specifically
    # fmin.is_above_max_edm=True (edm~0.002 vs goal 0.0001) -- everything
    # else (posdef covariance, no parameter at a limit, hesse not failed)
    # is fine, and the fitted values are stable and physically sensible
    # (mh matches ATLAS's own published 126.5 GeV closely). Three attempted
    # fixes were tried and rejected because each made the RESULT worse, not
    # just the flag: strategy=2 converges to a different, clearly spurious
    # minimum (mh~116 GeV, mu<0); a second migrad() call is a no-op (edm/
    # nfcn identical -- MIGRAD already regards this stationary); loosening
    # tol also moved to a markedly worse, far-less-constrained point
    # (mu error tripled). Left at strategy=1, default tol: the numbers are
    # trusted, the flag is reported honestly as False rather than chased.
    m.strategy = 1
    m.migrad()
    if hesse:
        m.hesse()

    def err(name):
        return float(m.errors[name]) if hesse else float("nan")

    return {
        "nll": float(m.fval),
        "mu_hat": float(m.values["mu"]), "mu_err": err("mu"),
        "mh_hat": float(m.values["mh"]), "mh_err": err("mh"),
        "sigma_hat": float(m.values["sigma"]), "sigma_err": err("sigma"),
        "n_bkg": float(m.values["n_bkg"]),
        "coeffs": np.array([m.values[f"c{k}"] for k in range(n_coeffs)]),
        "valid": bool(m.valid),
        "minuit": m,
    }


def fit_full_poly_floating_width(data: np.ndarray, edges: np.ndarray, nodes: np.ndarray,
                                  weights: np.ndarray, s_ref: float, mh: float,
                                  x_min: float, x_scale: float, n_coeffs: int = 5,
                                  mu_start: float = 0.0, sigma_start: float = 2.0,
                                  sigma_bounds: tuple[float, float] = (0.5, 6.0),
                                  bkg_start: list[float] | None = None,
                                  n_bkg_start: float = N_BKG_TRUE):
    """
    Like `fit_full_poly`, but mh is FIXED (given) and sigma floats. Used
    for "profiled local significance at the best-fit mass, width
    floating" -- as opposed to `fit_full_poly_floating_mass_width`, which
    also re-floats mh itself. See `fit_bkg_only_poly` for why
    `n_bkg_start` exists.
    """
    if bkg_start is None:
        bkg_start = [N_BKG_TRUE] + _poly_bkg_start(n_coeffs)
    start = [mu_start, sigma_start] + bkg_start

    def nll_fn(par):
        mu, sigma = par[0], par[1]
        n_bkg = par[2]
        coeffs = par[3:]
        b = polynomial_bin_expectation(nodes, weights, n_bkg, coeffs, x_min, x_scale)
        s = signal_bin_expectation(edges, mu, s_ref, mh, sigma)
        return poisson_nll(data, s + b)

    names = ["mu", "sigma", "n_bkg"] + [f"c{k}" for k in range(n_coeffs)]
    m = Minuit(nll_fn, start, name=names)
    m.errordef = Minuit.LIKELIHOOD
    m.limits["n_bkg"] = (0.0, None)
    m.limits["sigma"] = sigma_bounds
    m.strategy = 1
    m.migrad()
    return {
        "nll": float(m.fval),
        "mu_hat": float(m.values["mu"]),
        "sigma_hat": float(m.values["sigma"]),
        "n_bkg": float(m.values["n_bkg"]),
        "coeffs": np.array([m.values[f"c{k}"] for k in range(n_coeffs)]),
        "valid": bool(m.valid),
        "minuit": m,
    }
