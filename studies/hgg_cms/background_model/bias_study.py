"""
Background-model task, Part 3: the spurious-signal (bias) study.

TRUTH VARIANTS: for each family's F-test/GOF-selected order (Part 2),
fitted to the real sideband data, three pseudo-data-generating truth
shapes: nominal (the fitted curve as-is -- any real leakage already
present in the sideband data is already absorbed into it), and
truth +/- 0.5 x leakage_template (the leakage template is already
normalized to the DY-based absolute estimate -- see `leakage.py`).

TOYS: Poisson-fluctuated bin-by-bin over the FULL 105-180 GeV range (no
mask -- synthetic pseudo-data carries no real information, so filling
the blinded window is not a blinding violation).

TEST FITS: each candidate test function (a family/order pair) fit to
each toy, twice -- background-only (S fixed at 0, for the NLL
invariant), and signal+background (S free, unbounded, may go negative).
Both are WARM-STARTED from the background-only fit's own converged
parameters (S+B starts at [S=0, background-only's own optimum]) --
i.e. check (i) from `studies/atlas_hgg_repro/REPORT.md`'s "Corrections"
(the alternative model at mu=0, using the null's own background
parameters, must reproduce the null's own NLL) is true by CONSTRUCTION
of the starting point here, not just checked after the fact -- the
S+B fit can only match or improve on that starting NLL if MIGRAD
searches correctly. The NLL invariant
(NLL(S free) <= NLL(S=0) + 1e-6) is checked per toy regardless; a
violation triggers one retry from a perturbed start before being
counted as a fit failure (never silently dropped).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from iminuit import Minuit

from studies.hgg_cms.background_model.families import FAMILIES
from studies.hgg_cms.background_model.fit_background import fit_family_order
from studies.hgg_cms.stats.binning import poisson_nll

NLL_INVARIANT_TOL = 1e-6


def truth_curve(family_name: str, order: int, params: np.ndarray, edges: np.ndarray) -> np.ndarray:
    fam = FAMILIES[family_name]
    return fam.bin_expectation(edges, order, params)


def build_truth_variants(family_name: str, order: int, params: np.ndarray, edges: np.ndarray,
                          leakage_template: np.ndarray) -> dict:
    base = truth_curve(family_name, order, params, edges)
    return {
        "nominal": np.clip(base, 1e-8, None),
        "leakage_plus": np.clip(base + 0.5 * leakage_template, 1e-8, None),
        "leakage_minus": np.clip(base - 0.5 * leakage_template, 1e-8, None),
    }


def generate_toy(rng: np.random.Generator, truth: np.ndarray) -> np.ndarray:
    return rng.poisson(truth).astype(float)


def _bkg_nll_fn(family_name: str, order: int, edges: np.ndarray, data: np.ndarray):
    fam = FAMILIES[family_name]

    def nll(*par):
        pred = fam.bin_expectation(edges, order, np.array(par))
        return poisson_nll(data, pred)
    return nll


def fit_toy_bkg_only(family_name: str, order: int, edges: np.ndarray, data: np.ndarray,
                      warm_start: np.ndarray, bounds: list):
    fam = FAMILIES[family_name]
    names = fam.param_names(order)
    nll_fn = _bkg_nll_fn(family_name, order, edges, data)
    m = Minuit(nll_fn, *warm_start, name=names)
    m.errordef = Minuit.LIKELIHOOD
    for n, b in zip(names, bounds):
        m.limits[n] = b
    # strategy=1, not 0: a timing test on real data (30 toys) found
    # strategy=0 left ~70% of S+B fits "not valid" (is_above_max_edm) on
    # this problem's mixed-scale parameters; strategy=1 gave 0/30
    # failures at ~2.3x the per-toy cost. Reliability was judged more
    # important than the 2.3x speed loss for a study whose entire point
    # is measuring fit bias correctly.
    m.strategy = 1
    m.migrad()
    return m


def fit_toy_splus_b(family_name: str, order: int, edges: np.ndarray, data: np.ndarray,
                     bkg_warm_start: np.ndarray, bounds: list, signal_probs: np.ndarray,
                     s_start: float = 0.0, s_bound: float = None):
    fam = FAMILIES[family_name]
    names = ("S",) + fam.param_names(order)

    def nll_fn(*par):
        S = par[0]
        bkg_par = np.array(par[1:])
        pred = fam.bin_expectation(edges, order, bkg_par) + S * signal_probs
        return poisson_nll(data, pred)

    start = [s_start] + list(bkg_warm_start)
    m = Minuit(nll_fn, *start, name=names)
    m.errordef = Minuit.LIKELIHOOD
    if s_bound is not None:
        m.limits["S"] = (-s_bound, s_bound)
    for n, b in zip(fam.param_names(order), bounds):
        m.limits[n] = b
    m.strategy = 1
    m.migrad()
    m.hesse()
    return m


@dataclass
class ToyResult:
    S: float
    sigma_S: float
    nll_splus_b: float
    nll_bkg_only: float
    bkg_valid: bool
    splus_b_valid: bool
    invariant_violated: bool
    retried: bool
    failed: bool


def run_one_toy(rng: np.random.Generator, truth: np.ndarray, family_name: str, order: int,
                 edges: np.ndarray, signal_probs: np.ndarray, warm_start_bkg_params: np.ndarray,
                 bounds: list, s_bound: float) -> ToyResult:
    data = generate_toy(rng, truth)

    m_bkg = fit_toy_bkg_only(family_name, order, edges, data, warm_start_bkg_params, bounds)
    nll_bkg = float(m_bkg.fval)
    bkg_params = np.array([m_bkg.values[n] for n in m_bkg.parameters])

    m_sb = fit_toy_splus_b(family_name, order, edges, data, bkg_params, bounds, signal_probs,
                            s_start=0.0, s_bound=s_bound)
    nll_sb = float(m_sb.fval)

    violated = nll_sb > nll_bkg + NLL_INVARIANT_TOL
    retried = False
    if violated or not m_sb.valid:
        retried = True
        # Retry from the ORIGINAL (pre-warm-start) generic starting point,
        # in case the bkg-only optimum itself was a bad local minimum.
        m_sb2 = fit_toy_splus_b(family_name, order, edges, data, warm_start_bkg_params, bounds,
                                 signal_probs, s_start=0.0, s_bound=s_bound)
        if float(m_sb2.fval) < nll_sb or (m_sb2.valid and not m_sb.valid):
            m_sb, nll_sb = m_sb2, float(m_sb2.fval)
        violated = nll_sb > nll_bkg + NLL_INVARIANT_TOL

    failed = violated or not (m_bkg.valid and m_sb.valid)
    S = float(m_sb.values["S"])
    sigma_S = float(m_sb.errors["S"])
    return ToyResult(S=S, sigma_S=sigma_S, nll_splus_b=nll_sb, nll_bkg_only=nll_bkg,
                      bkg_valid=bool(m_bkg.valid), splus_b_valid=bool(m_sb.valid),
                      invariant_violated=violated, retried=retried, failed=failed)


def summarize_toys(results: list) -> dict:
    ok = [r for r in results if not r.failed]
    n_total = len(results)
    n_failed = n_total - len(ok)
    n_invariant_violated = sum(1 for r in results if r.invariant_violated)
    if not ok:
        return {
            "n_total": n_total, "n_failed": n_failed, "n_invariant_violated": n_invariant_violated,
            "mean_S": None, "se_mean_S": None, "mean_sigma_S": None, "median_pull": None,
        }
    S = np.array([r.S for r in ok])
    sigma_S = np.array([r.sigma_S for r in ok])
    valid_sigma = sigma_S[np.isfinite(sigma_S) & (sigma_S > 0)]
    pulls = S[np.isfinite(sigma_S) & (sigma_S > 0)] / valid_sigma if len(valid_sigma) else np.array([])
    return {
        "n_total": n_total, "n_failed": n_failed, "n_invariant_violated": n_invariant_violated,
        "fail_fraction": n_failed / n_total if n_total else None,
        "mean_S": float(np.mean(S)), "se_mean_S": float(np.std(S, ddof=1) / np.sqrt(len(S))) if len(S) > 1 else None,
        "std_S": float(np.std(S, ddof=1)) if len(S) > 1 else None,
        "mean_sigma_S": float(np.mean(valid_sigma)) if len(valid_sigma) else None,
        "median_pull": float(np.median(pulls)) if len(pulls) else None,
        "n_used": len(ok),
    }
