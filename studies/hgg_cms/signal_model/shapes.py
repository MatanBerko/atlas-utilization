"""
Signal-model task, Part 2: the diphoton-mass shape model.

Default shape: a double-sided Crystal Ball (DCB/DSCB) -- a Gaussian core
with independent power-law tails on both sides, parameters
(mu, sigma, alphaL, nL, alphaR, nR). This is the standard empirical
signal-mass model used by both CMS and ATLAS H->gamma-gamma analyses
(Gaussian core + power-law tails on both sides, capturing the
non-Gaussian resolution tails from photon conversions / bremsstrahlung
losses in tracker material) -- see e.g. ATLAS-CONF/CMS-HIG public
diphoton papers' signal-model sections (general technique, not a single
pinned equation number; this project has not independently re-derived
the functional form, only implemented the standard one below).

Optional extension: DCB + an extra Gaussian (a 2-component mixture),
added only if the pre-set rule in `fit.py`'s module docstring is
satisfied.

All PDFs/CDFs here are ANALYTIC (no numerical integration), so bin
probabilities (`bin_probabilities`) are exact CDF differences, not
midpoint approximations -- important because sigma is only ~2-3 GeV
against a bin width down to 0.25 GeV, i.e. not always >> bin width.

DCB normalization / CDF derivation (standard result, re-derived here
directly by integrating the piecewise density -- not copied from a
citable closed-form reference, so treat the algebra as this project's
own, checked against a numerical CDF in the unit tests):

  t = (x - mu) / sigma
  Core (-alphaL <= t <= alphaR):      exp(-t^2/2)
  Left tail   (t < -alphaL):          A_L * (B_L - t)^(-nL)
  Right tail  (t > alphaR):           A_R * (B_R + t)^(-nR)

  A_L = (nL/alphaL)^nL * exp(-alphaL^2/2),  B_L = nL/alphaL - alphaL
  A_R = (nR/alphaR)^nR * exp(-alphaR^2/2),  B_R = nR/alphaR - alphaR

Integrating each piece over its own domain gives the (unnormalized)
total mass  I_left + I_core + I_right  with
  I_core  = sqrt(2*pi) * (Phi(alphaR) - Phi(-alphaL))
  I_left  = exp(-alphaL^2/2) / (nL - 1) * (nL / alphaL)
  I_right = exp(-alphaR^2/2) / (nR - 1) * (nR / alphaR)
and the overall normalization is `sigma * (I_left + I_core + I_right)`.
Requires alphaL, alphaR > 0 and nL, nR > 1 (else the tail is not
normalizable) -- enforced via fit bounds in `fit.py`, not inside this
module (this module trusts its inputs; `fit.py` is where bounds live).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq, minimize_scalar

DCB_PARAM_NAMES = ("mu", "sigma", "alphaL", "nL", "alphaR", "nR")
GAUSS_EXTRA_PARAM_NAMES = ("frac2", "mu2", "sigma2")


def _dcb_pieces(alphaL, nL, alphaR, nR):
    A_L = (nL / alphaL) ** nL * np.exp(-0.5 * alphaL ** 2)
    B_L = nL / alphaL - alphaL
    A_R = (nR / alphaR) ** nR * np.exp(-0.5 * alphaR ** 2)
    B_R = nR / alphaR - alphaR
    I_core = np.sqrt(2 * np.pi) * (norm.cdf(alphaR) - norm.cdf(-alphaL))
    I_left = np.exp(-0.5 * alphaL ** 2) / (nL - 1.0) * (nL / alphaL)
    I_right = np.exp(-0.5 * alphaR ** 2) / (nR - 1.0) * (nR / alphaR)
    return A_L, B_L, A_R, B_R, I_left, I_core, I_right


def dcb_pdf(x, mu, sigma, alphaL, nL, alphaR, nR):
    """Normalized double-sided Crystal Ball PDF, vectorized over x."""
    x = np.asarray(x, dtype=float)
    t = (x - mu) / sigma
    A_L, B_L, A_R, B_R, I_left, I_core, I_right = _dcb_pieces(alphaL, nL, alphaR, nR)
    norm_const = sigma * (I_left + I_core + I_right)

    out = np.empty_like(t)
    core = (t >= -alphaL) & (t <= alphaR)
    left = t < -alphaL
    right = t > alphaR

    out[core] = np.exp(-0.5 * t[core] ** 2)
    left_base = np.maximum(B_L - t[left], 1e-300)
    out[left] = A_L * left_base ** (-nL)
    right_base = np.maximum(B_R + t[right], 1e-300)
    out[right] = A_R * right_base ** (-nR)
    return out / norm_const


def dcb_cdf(x, mu, sigma, alphaL, nL, alphaR, nR):
    """Analytic CDF of the double-sided Crystal Ball, vectorized over x."""
    x = np.asarray(x, dtype=float)
    t = (x - mu) / sigma
    A_L, B_L, A_R, B_R, I_left, I_core, I_right = _dcb_pieces(alphaL, nL, alphaR, nR)
    norm_const = I_left + I_core + I_right

    out = np.empty_like(t)
    core = (t >= -alphaL) & (t <= alphaR)
    left = t < -alphaL
    right = t > alphaR

    left_base = np.maximum(B_L - t[left], 1e-300)
    out[left] = (A_L / (nL - 1.0)) * left_base ** (1.0 - nL) / norm_const

    out[core] = (I_left + np.sqrt(2 * np.pi) * (norm.cdf(t[core]) - norm.cdf(-alphaL))) / norm_const

    right_base = np.maximum(B_R + t[right], 1e-300)
    out[right] = 1.0 - (A_R / (nR - 1.0)) * right_base ** (1.0 - nR) / norm_const
    return out


@dataclass
class SignalShape:
    """A fitted signal shape: a DCB, or a DCB + extra-Gaussian mixture.

    Parameters are held in a flat dict `params` with keys
    `DCB_PARAM_NAMES` and, if `use_gauss2` is True, also
    `GAUSS_EXTRA_PARAM_NAMES` (frac2 = fraction of the total in the
    extra Gaussian component, 0 < frac2 < 1).
    """
    params: dict
    use_gauss2: bool = False
    covariance: Optional[np.ndarray] = None  # order: param_names below
    param_names: tuple = field(default_factory=tuple)

    def pdf(self, x):
        x = np.asarray(x, dtype=float)
        p = self.params
        dcb = dcb_pdf(x, p["mu"], p["sigma"], p["alphaL"], p["nL"], p["alphaR"], p["nR"])
        if not self.use_gauss2:
            return dcb
        gauss = norm.pdf(x, loc=p["mu2"], scale=p["sigma2"])
        return (1.0 - p["frac2"]) * dcb + p["frac2"] * gauss

    def cdf(self, x):
        x = np.asarray(x, dtype=float)
        p = self.params
        dcb = dcb_cdf(x, p["mu"], p["sigma"], p["alphaL"], p["nL"], p["alphaR"], p["nR"])
        if not self.use_gauss2:
            return dcb
        gauss = norm.cdf(x, loc=p["mu2"], scale=p["sigma2"])
        return (1.0 - p["frac2"]) * dcb + p["frac2"] * gauss

    def bin_probabilities(self, edges: np.ndarray) -> np.ndarray:
        """P(event falls in each bin of `edges`) = CDF difference at the
        edges -- exact, not a midpoint approximation. Sums to
        `in_range_fraction(edges[0], edges[-1])`, NOT to 1, unless the
        edges span (-inf, inf)."""
        c = self.cdf(edges)
        return np.diff(c)

    def in_range_fraction(self, lo: float, hi: float) -> float:
        c = self.cdf(np.array([lo, hi]))
        return float(c[1] - c[0])

    def mode(self, search_lo: float = None, search_hi: float = None) -> float:
        """Peak of the PDF. For a pure DCB the mode is exactly `mu` (the
        Gaussian core's own peak, since the tails are monotonically
        falling by construction and the core dominates the true peak for
        the physically-relevant alpha>~1 fits here); for the mixture,
        found numerically (bounded scalar search) since the extra
        Gaussian can shift the maximum slightly."""
        if not self.use_gauss2:
            return float(self.params["mu"])
        mu = self.params["mu"]
        sigma = self.params["sigma"]
        lo = search_lo if search_lo is not None else mu - 5 * sigma
        hi = search_hi if search_hi is not None else mu + 5 * sigma
        res = minimize_scalar(lambda x: -self.pdf(np.array([x]))[0], bounds=(lo, hi), method="bounded",
                               options={"xatol": 1e-4})
        return float(res.x)

    def sigma_eff68(self, search_lo: float = None, search_hi: float = None) -> float:
        """Half-width of the shortest interval [a, b] with
        CDF(b) - CDF(a) = 0.683, found by a bounded scan over `a` (for
        each candidate `a`, `b` is solved exactly via `brentq` on the
        analytic CDF) -- the continuous-model analogue of
        `physics_checks/common.py`'s `effective_sigma_68` (which works on
        a finite sorted sample instead of an analytic CDF)."""
        mu = self.params["mu"]
        sigma = self.params["sigma"]
        lo = search_lo if search_lo is not None else mu - 15 * sigma
        hi = search_hi if search_hi is not None else mu + 15 * sigma
        target = 0.683

        def b_of_a(a):
            c_a = self.cdf(np.array([a]))[0]
            target_cdf = c_a + target
            if target_cdf >= 1.0:
                return hi
            return brentq(lambda b: self.cdf(np.array([b]))[0] - target_cdf, a, hi, xtol=1e-6)

        def width(a):
            return b_of_a(a) - a

        # `a` must leave room for b <= hi; search a in [lo, hi - epsilon]
        res = minimize_scalar(width, bounds=(lo, mu), method="bounded", options={"xatol": 1e-4})
        return float(width(res.x) / 2.0)

    def shifted_to_mass(self, mH: float, mu_ref: float = 125.0) -> "SignalShape":
        """Standard 'mass-shift' approximation for a hypothesized Higgs
        mass mH, using only the mH=125 GeV simulation available: shift
        the model's mean(s) by delta = mH - mu_ref, keeping every other
        shape parameter (widths, tail parameters, mixture fraction)
        FIXED. This is the conventional approach when signal MC exists
        at only one mass point (mean floats linearly with mH, resolution
        parameters are treated as mass-independent over the scanned
        range) -- see this module's docstring and
        SIGNAL_MODEL_REPORT.md's "Mass dependence" section for the
        citation status (UNVERIFIED against a specific CMS/ATLAS
        equation number) and the limitation (neglects width scaling with
        mass) with a quantitative estimate of its size.
        """
        delta = mH - mu_ref
        new_params = dict(self.params)
        new_params["mu"] = self.params["mu"] + delta
        if self.use_gauss2:
            new_params["mu2"] = self.params["mu2"] + delta
        return SignalShape(params=new_params, use_gauss2=self.use_gauss2,
                            covariance=self.covariance, param_names=self.param_names)

    def to_json(self) -> dict:
        return {
            "use_gauss2": self.use_gauss2,
            "params": {k: float(v) for k, v in self.params.items()},
            "param_names": list(self.param_names),
            "covariance": self.covariance.tolist() if self.covariance is not None else None,
        }
