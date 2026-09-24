"""
Signal-model task, Part 2.6: shared binning/likelihood utilities, reused
(not re-derived) from the validated bump-search toy study so that this
task's binned-probability functions plug directly into the same
machinery the later background-model / S+B tasks will use.

SOURCE: `studies/lr_toys/lr_core.py` on branch
`study/atlas-hgg-lr-reproduction`, commit `290ca09` ("Fix profiled LR
bug: null fit stuck at bad local optimum, inflating V3/V4 Z") -- that
branch/file is not present on this branch, per this task's own
instructions, so the relevant pieces are copied here rather than
imported across branches.

WHAT WAS COPIED, AND WHAT WAS CHANGED:
- `bin_edges`/`bin_centers`/`gl_bin_nodes`: copied verbatim in
  structure, but GENERALIZED from lr_core's hardcoded module-level
  `MASS_MIN=100.0, MASS_MAX=180.0, N_BINS=80` globals into explicit
  `lo`/`hi`/`n_bins` parameters -- this task's own fit range (105-180
  GeV, 0.25 GeV bins, per VALIDATION_REPORT_2.md's Part E fit-range
  decision) differs from the toy study's (100-180 GeV, 1 GeV bins), and
  a future background-model task may pick yet another range/binning.
  This is a documented adaptation, not a silent behavior change --
  nothing about the numerical algorithm itself was altered.
- `poisson_nll`: copied verbatim, unchanged (mass-window-agnostic
  already).
- Everything else in the original module (the exponential-of-polynomial
  and Legendre-polynomial BACKGROUND shapes, the Gaussian SIGNAL shape,
  the profiled-likelihood test-statistic machinery) is NOT copied here.
  This task is signal-model-only (no background model, no S+B fit, no
  significance -- explicitly out of scope); copying that machinery now,
  unused, would just be dead code that could go stale before the
  background-model task actually needs it. That task should read
  `lr_core.py` itself (same source branch/commit) when it needs it.
"""
from __future__ import annotations

import numpy as np

# 5-point Gauss-Legendre nodes/weights on [-1, 1] -- identical to
# lr_core.py's module-level `_GL_NODES, _GL_WEIGHTS`.
_GL_NODES, _GL_WEIGHTS = np.polynomial.legendre.leggauss(5)


def bin_edges(lo: float, hi: float, n_bins: int) -> np.ndarray:
    """The (n_bins + 1) bin edges in GeV, from lo to hi."""
    return np.linspace(lo, hi, n_bins + 1)


def bin_centers(edges: np.ndarray) -> np.ndarray:
    return 0.5 * (edges[:-1] + edges[1:])


def gl_bin_nodes(edges: np.ndarray):
    """
    Precompute Gauss-Legendre integration nodes and weights for every bin
    defined by `edges` -- identical algorithm to lr_core.py's
    `gl_bin_nodes`, just taking `edges` directly instead of defaulting to
    the module-global fixed range.

    Returns
    -------
    nodes : ndarray, shape (n_bins, 5)
        Mass values (GeV) at which to evaluate a density.
    weights : ndarray, shape (n_bins, 5)
        Physical (GeV) weights such that weights[i].sum() == bin width,
        and sum_j weights[i, j] * f(nodes[i, j]) approximates the
        integral of f over bin i.
    """
    lo = edges[:-1][:, None]
    hi = edges[1:][:, None]
    half = 0.5 * (hi - lo)
    mid = 0.5 * (hi + lo)
    nodes = mid + half * _GL_NODES[None, :]
    weights = half * _GL_WEIGHTS[None, :]
    return nodes, weights


def poisson_nll(n: np.ndarray, nu: np.ndarray) -> float:
    """
    Binned Poisson negative log-likelihood, up to an additive constant
    (sum of log(n_i!)) that is the same for every hypothesis fitted to
    the same data and therefore cancels exactly in any likelihood-ratio
    test statistic computed from two NLL values returned by this
    function. Copied verbatim from lr_core.py.
    """
    nu_safe = np.clip(nu, 1e-12, None)
    return float(np.sum(nu_safe - n * np.log(nu_safe)))
