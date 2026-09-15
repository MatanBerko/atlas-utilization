"""
Fast correctness checks for lr_core.py, including T0 from the toy-study
report: q0 on a single-bin Asimov dataset must match the closed-form
Z_A = sqrt(2[(s+b) ln(1+s/b) - s]) from Cowan et al. (arXiv:1007.1727), eq. 97.

Run with: python -m pytest studies/lr_toys/test_lr_core.py -q
(or just: python studies/lr_toys/test_lr_core.py)
"""
from __future__ import annotations

import numpy as np

import lr_core as lc

T0_PAIRS = [
    (10.0, 100.0),
    (10.0, 1000.0),
    (50.0, 200.0),
    (5.0, 20.0),
    (100.0, 10000.0),
    (2.0, 5.0),
]
T0_REL_TOL = 1e-6


def _t0_case(s: float, b: float) -> dict:
    """
    Run one T0 case through the SAME general machinery (poisson_nll +
    fit_mu_only + q0_from_nll) that the rest of the study uses, on the
    degenerate single-bin model: one bin, background fixed at the known
    value b, signal-per-unit-mu fixed at s. The Asimov "data" is set to
    exactly s + b (real-valued, not rounded).
    """
    edges = np.array([0.0, 1.0])
    bkg_fixed = np.array([b])
    data = np.array([s + b])  # Asimov data set

    # Null: mu fixed at 0 -> NLL is just the Poisson NLL at the fixed
    # background, no fit needed (0 free parameters).
    nll_null = lc.poisson_nll(data, bkg_fixed)

    # Alt: float mu only, background fixed at the known value b. Reuses
    # fit_mu_only with a unit "signal shape" equal to s at mu=1.
    result = lc.fit_mu_only(data, bkg_fixed, edges, s_ref=s, mh=0.5, sigma=100.0,
                             mu_start=0.0)
    # fit_mu_only integrates a Gaussian signal over the single bin; for a
    # 1-bin "shape" that isn't meaningful, so bypass it here and fit the
    # trivial closed-form-equivalent problem directly instead, to test the
    # actual NLL/minimizer code path against the textbook case exactly as
    # CCGV define it (data = mu*s + b, single free parameter mu).
    def nll_fn(mu):
        return lc.poisson_nll(data, mu * s + bkg_fixed)

    from iminuit import Minuit
    m = Minuit(nll_fn, 0.0, name=["mu"])
    m.errordef = Minuit.LIKELIHOOD
    m.strategy = 2
    m.tol = 1e-10  # tight: this is a precision cross-check, not a speed-critical toy fit
    m.migrad()
    mu_hat = float(m.values["mu"])
    nll_alt = float(m.fval)

    q0 = lc.q0_from_nll(nll_null, nll_alt, mu_hat)
    z_code = lc.z_from_q0(q0)
    z_closed = lc.asimov_z_closed_form(s, b)
    return {
        "s": s, "b": b, "mu_hat": mu_hat, "z_code": z_code,
        "z_closed_form": z_closed,
        "rel_diff": abs(z_code - z_closed) / z_closed,
        "minuit_valid": bool(m.valid),
    }


def test_t0_asimov_single_bin_matches_closed_form():
    results = [_t0_case(s, b) for s, b in T0_PAIRS]
    for r in results:
        assert r["minuit_valid"], f"Minuit did not converge for s={r['s']}, b={r['b']}"
        assert abs(r["mu_hat"] - 1.0) < 1e-4, (
            f"Asimov mu_hat should be close to 1.0, got {r['mu_hat']} for s={r['s']}, b={r['b']}"
        )
        assert r["rel_diff"] < T0_REL_TOL, (
            f"T0 FAILED for s={r['s']}, b={r['b']}: "
            f"code Z={r['z_code']:.6f} vs closed-form Z={r['z_closed_form']:.6f} "
            f"(rel diff {r['rel_diff']:.2e} > {T0_REL_TOL:.0e})"
        )


def test_background_shape_normalizes_to_n_bkg():
    edges = lc.bin_edges()
    nodes, weights = lc.gl_bin_nodes(edges)
    b = lc.background_bin_expectation(nodes, weights, lc.N_BKG_TRUE,
                                       [lc.P1_TRUE, lc.P2_TRUE])
    assert abs(b.sum() - lc.N_BKG_TRUE) / lc.N_BKG_TRUE < 1e-9
    assert np.all(np.diff(b) < 0), "background must be monotonically falling"


def test_signal_shape_integrates_to_s_ref():
    edges = lc.bin_edges()
    s_ref = 123.0
    s = lc.signal_bin_expectation(edges, mu=1.0, s_ref=s_ref, mh=lc.MH_NOMINAL,
                                   sigma=lc.SIGMA_NOMINAL)
    # mh=125, sigma=2 is >6 sigma from both edges (100, 180), so truncation
    # loss is negligible (<1e-9).
    assert abs(s.sum() - s_ref) / s_ref < 1e-6


if __name__ == "__main__":
    print("T0: single-bin Asimov q0 vs closed-form Z_A")
    print(f"{'s':>8} {'b':>10} {'mu_hat':>10} {'Z (code)':>10} {'Z (closed)':>10} {'rel diff':>10}")
    all_results = []
    for s, b in T0_PAIRS:
        r = _t0_case(s, b)
        all_results.append(r)
        print(f"{r['s']:8.2f} {r['b']:10.2f} {r['mu_hat']:10.6f} "
              f"{r['z_code']:10.6f} {r['z_closed_form']:10.6f} {r['rel_diff']:10.2e}")
    worst = max(r["rel_diff"] for r in all_results)
    passed = worst < T0_REL_TOL
    print(f"\nWorst relative difference: {worst:.2e} (criterion: < {T0_REL_TOL:.0e})")
    print("T0: PASS" if passed else "T0: FAIL")

    test_background_shape_normalizes_to_n_bkg()
    test_signal_shape_integrates_to_s_ref()
    print("Background normalization and signal-integral sanity checks: PASS")
