"""
Background-model task, Part 2: the four candidate background-function
families, as used by CMS H->gamma-gamma analyses for the "discrete
profiling" background-function envelope -- see S. Chatrchyan et al.
(CMS), "Observation of the diphoton decay of the Higgs boson and
measurement of its properties", Eur. Phys. J. C 74 (2014) 3076,
arXiv:1407.0558, and P. Dauncey et al., "Handling uncertainties in
background shapes: the discrete profiling method", JINST 10 (2015)
P04015, arXiv:1408.6865, for the standard set (Bernstein polynomials,
exponentials, power laws, Laurent series) and the discrete-profiling
philosophy of trying several families/orders rather than committing to
one a priori. This project's own earlier flag
(`VALIDATION_REPORT_1.md` Part B / arXiv:1804.02716 mentioned there) is
the same general CMS H->gamma-gamma diphoton-selection paper family;
the specific function forms below follow the two references just cited.

Every family here provides EXACT ANALYTIC bin integration (closed-form
antiderivatives), not numerical quadrature -- important because these
fits run inside a toy loop that needs to be fast, and because an
analytic integral has no quadrature-order choice to document/verify.

Normalized mass variables (documented, for numerical conditioning):
- Bernstein, exponential-sum: x = (m - 105) / 75  (so x in [0, 1] over
  the DEFAULT 105-180 GeV range; note this is NOT re-centered for the
  110-180 GeV robustness variant -- the same x=(m-105)/75 definition is
  reused there on purpose, so a fit's coefficients mean the same thing
  in both fit ranges; x is simply confined to [1/15, 1] instead of
  [0, 1] in that case).
- Power-law sum, Laurent series: x' = m / 105 (dimensionless, > 0,
  avoiding x'=0 since m is always >= 100 GeV; x' in [1, 180/105=1.714]
  over the default range).

Positivity: only the Bernstein family GUARANTEES non-negativity by
construction (non-negative coefficients times a non-negative basis).
The other three families are not guaranteed positive everywhere their
parameters roam during a fit; every family's `bin_expectation` clips its
OWN raw output at a tiny positive floor before it is ever handed to the
Poisson NLL (mirroring `studies/hgg_cms/stats/binning.py`'s own
`poisson_nll` clip, which floors `nu` again as a second safety net).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.special import betainc, betaln

# ----------------------------------------------------------------------------
# Shared normalization anchors (see module docstring).
# ----------------------------------------------------------------------------
BERNSTEIN_EXP_X0, BERNSTEIN_EXP_SCALE = 105.0, 75.0
POWER_LAURENT_X0 = 105.0

LAURENT_EXPONENT_SEQUENCE = (-4, -5, -3, -6)  # "the standard alternating exponent sequence"

POSITIVITY_FLOOR = 1e-8


def _to_x_bernstein_exp(m):
    return (np.asarray(m, dtype=float) - BERNSTEIN_EXP_X0) / BERNSTEIN_EXP_SCALE


def _to_xp_power_laurent(m):
    return np.asarray(m, dtype=float) / POWER_LAURENT_X0


# ----------------------------------------------------------------------------
# Bernstein polynomials
# ----------------------------------------------------------------------------

def _bernstein_bin_integral_matrix(edges: np.ndarray, order: int) -> np.ndarray:
    """(n_bins, order+1) matrix M where M[j, i] = integral of the i-th
    Bernstein basis function B_{i,order}(x) dm over bin j (mass units).
    Uses the exact identity: integral of C(n,i) x^i (1-x)^(n-i) dx over
    [x1, x2] = [I_x2(i+1, n-i+1) - I_x1(i+1, n-i+1)] / (n+1), where I is
    the regularized incomplete beta function (scipy.special.betainc) --
    derived from B_{i,n}(x) = Beta_pdf(x; i+1, n-i+1) / (n+1). Multiplied
    by BERNSTEIN_EXP_SCALE for dm = scale * dx.
    """
    x = _to_x_bernstein_exp(edges)
    M = np.empty((len(edges) - 1, order + 1))
    for i in range(order + 1):
        cdf = betainc(i + 1, order - i + 1, np.clip(x, 0.0, None))
        cdf = np.where(x < 0, 0.0, cdf)
        cdf = np.where(x > 1, 1.0, cdf)
        col = np.diff(cdf) / (order + 1) * BERNSTEIN_EXP_SCALE
        M[:, i] = col
    return M


@dataclass
class BernsteinFamily:
    name: str = "bernstein"

    def n_params(self, order: int) -> int:
        return order + 1

    def param_names(self, order: int) -> tuple:
        return tuple(f"c{i}" for i in range(order + 1))

    def bounds(self, order: int, total_count: float):
        return [(0.0, 5.0 * max(total_count, 1.0))] * self.n_params(order)

    def bin_expectation(self, edges: np.ndarray, order: int, params: np.ndarray) -> np.ndarray:
        M = _bernstein_bin_integral_matrix(edges, order)
        pred = M @ np.asarray(params, dtype=float)
        return np.clip(pred, POSITIVITY_FLOOR, None)

    def design_matrix(self, edges: np.ndarray, order: int) -> np.ndarray:
        return _bernstein_bin_integral_matrix(edges, order)


# ----------------------------------------------------------------------------
# Sums of exponentials: f(x) = sum_i a_i * exp(b_i * x)
# ----------------------------------------------------------------------------

@dataclass
class ExpSumFamily:
    name: str = "expsum"

    def n_params(self, order: int) -> int:
        return 2 * order

    def param_names(self, order: int) -> tuple:
        out = []
        for i in range(order):
            out += [f"a{i}", f"b{i}"]
        return tuple(out)

    def bounds(self, order: int, total_count: float):
        b = []
        A = 20.0 * max(total_count, 1.0)
        for _ in range(order):
            b += [(-A, A), (-40.0, 40.0)]
        return b

    def bin_expectation(self, edges: np.ndarray, order: int, params: np.ndarray) -> np.ndarray:
        x = _to_x_bernstein_exp(edges)
        x1, x2 = x[:-1], x[1:]
        pred = np.zeros(len(edges) - 1)
        params = np.asarray(params, dtype=float)
        for i in range(order):
            a, b = params[2 * i], params[2 * i + 1]
            if abs(b) < 1e-8:
                integ = a * (x2 - x1)
            else:
                integ = (a / b) * (np.exp(np.clip(b * x2, -700, 700)) - np.exp(np.clip(b * x1, -700, 700)))
            pred += integ * BERNSTEIN_EXP_SCALE
        return np.clip(pred, POSITIVITY_FLOOR, None)


# ----------------------------------------------------------------------------
# Sums of power laws: f(x') = sum_i a_i * x'^b_i
# ----------------------------------------------------------------------------

@dataclass
class PowerSumFamily:
    name: str = "powersum"

    def n_params(self, order: int) -> int:
        return 2 * order

    def param_names(self, order: int) -> tuple:
        out = []
        for i in range(order):
            out += [f"a{i}", f"b{i}"]
        return tuple(out)

    def bounds(self, order: int, total_count: float):
        b = []
        A = 50.0 * max(total_count, 1.0)
        for _ in range(order):
            b += [(-A, A), (-25.0, 10.0)]
        return b

    def bin_expectation(self, edges: np.ndarray, order: int, params: np.ndarray) -> np.ndarray:
        xp = _to_xp_power_laurent(edges)
        x1, x2 = xp[:-1], xp[1:]
        pred = np.zeros(len(edges) - 1)
        params = np.asarray(params, dtype=float)
        for i in range(order):
            a, b = params[2 * i], params[2 * i + 1]
            if abs(b + 1.0) < 1e-6:
                integ = a * np.log(x2 / x1)
            else:
                integ = a / (b + 1.0) * (x2 ** (b + 1.0) - x1 ** (b + 1.0))
            pred += integ * POWER_LAURENT_X0
        return np.clip(pred, POSITIVITY_FLOOR, None)


# ----------------------------------------------------------------------------
# Laurent series: f(x') = sum_i a_i * x'^k_i, k_i FIXED (LAURENT_EXPONENT_SEQUENCE)
# ----------------------------------------------------------------------------

@dataclass
class LaurentFamily:
    name: str = "laurent"

    def n_params(self, order: int) -> int:
        return order

    def param_names(self, order: int) -> tuple:
        return tuple(f"a{i}" for i in range(order))

    def exponents(self, order: int) -> tuple:
        return LAURENT_EXPONENT_SEQUENCE[:order]

    def bounds(self, order: int, total_count: float):
        A = 1e7 * max(total_count, 1.0)
        return [(-A, A)] * order

    def _design_matrix(self, edges: np.ndarray, order: int) -> np.ndarray:
        xp = _to_xp_power_laurent(edges)
        x1, x2 = xp[:-1], xp[1:]
        ks = self.exponents(order)
        M = np.empty((len(edges) - 1, order))
        for i, k in enumerate(ks):
            M[:, i] = (x2 ** (k + 1.0) - x1 ** (k + 1.0)) / (k + 1.0) * POWER_LAURENT_X0
        return M

    def bin_expectation(self, edges: np.ndarray, order: int, params: np.ndarray) -> np.ndarray:
        M = self._design_matrix(edges, order)
        pred = M @ np.asarray(params, dtype=float)
        return np.clip(pred, POSITIVITY_FLOOR, None)

    def design_matrix(self, edges: np.ndarray, order: int) -> np.ndarray:
        return self._design_matrix(edges, order)


FAMILIES = {
    "bernstein": BernsteinFamily(),
    "expsum": ExpSumFamily(),
    "powersum": PowerSumFamily(),
    "laurent": LaurentFamily(),
}

ORDER_RANGE = {
    "bernstein": range(1, 8),   # order 1..7 (n+1 = 2..8 coefficients)
    "expsum": range(1, 4),      # N = 1..3 terms
    "powersum": range(1, 4),    # N = 1..3 terms
    "laurent": range(1, 5),     # N = 1..4 terms
}
