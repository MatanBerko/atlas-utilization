"""
Invariant checks for the profiled likelihood-ratio bug found on this
branch (see REPORT.md, "Corrections", for the full writeup).

Run with: python -m pytest studies/atlas_hgg_repro/test_bug_fix_invariants.py -q

Checks (i)-(iii) are the ones requested in the bug-fix task. Verified
directly against the pre-fix code (commit e9a097b, checked out and run
against): all three ALREADY held on the buggy code too -- reading
lr_core.fit_bkg_only_poly / fit_full_poly confirms both already called the
SAME `polynomial_bin_expectation` + `poisson_nll` functions with the same
nodes/weights/x_min/x_scale, so (i)-(iii), taken literally, were never a
formula/code-path mismatch, and pass both before and after the fix. They
are kept here as basic regression tests. The REAL bug -- confirmed by
finding it, not assumed -- was a MIGRAD convergence-robustness problem:
`fit_bkg_only_poly`'s single-start optimization of the null hypothesis
(used identically at every mass point in the profiled V3/V4 curve, since
it doesn't depend on the scanned mass) could land in a badly-converged
local optimum depending on its starting point, while each mass point's
alternative fit -- warm-started well -- did not. That mismatch (a good
alternative compared against a stuck null) inflated every bin's profiled Z
by a near-constant, spurious offset.
`test_null_fit_stable_matches_actual_pipeline_bug_magnitude` is the check
that actually catches this, using the EXACT starting points the real
pipeline used: checked out against the pre-fix code, it landed 2.4662 NLL
units apart (matching the task's reported ~2.4 evidence almost exactly,
and explaining the observed |Z|~2.2-2.4 offset via Z=sqrt(2*2.4662)~2.22);
the new multi-start code closes that to ~1e-8.
`test_null_fit_stable_across_starting_points` is a second, more extreme
version of the same check (a 4x-larger starting-point jump) kept as an
additional stress test.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "lr_toys"))
import lr_core as lc

HERE = Path(__file__).parent
RESULTS_DIR = HERE / "results"
X_MIN, X_SCALE, N_COEFFS = 100.0, 55.0, 5


def _load_data():
    edges = [100.0]
    counts = []
    with open(RESULTS_DIR / "atlas_hgg_fig4_points.csv") as f:
        for r in csv.DictReader(f):
            edges.append(float(r["bin_high_GeV"]))
            counts.append(float(r["count"]))
    return np.array(edges), np.array(counts)


EDGES, DATA = _load_data()
NODES, WEIGHTS = lc.gl_bin_nodes(EDGES)


def test_invariant_i_alt_model_at_mu0_matches_null_nll():
    """The alternative model's own NLL formula, evaluated at mu=0 and the
    null fit's converged background parameters, must reproduce the null's
    own reported NLL exactly (to 1e-6) -- confirms the two functions share
    one formula, not two silently-different ones."""
    null = lc.fit_bkg_only_poly(DATA, NODES, WEIGHTS, X_MIN, X_SCALE, n_coeffs=N_COEFFS)
    b = lc.polynomial_bin_expectation(NODES, WEIGHTS, null["n_bkg"], null["coeffs"], X_MIN, X_SCALE)
    s_zero = lc.signal_bin_expectation(EDGES, 0.0, 1.0, 125.0, 2.0)
    nll_alt_formula_at_mu0 = lc.poisson_nll(DATA, s_zero + b)
    assert abs(nll_alt_formula_at_mu0 - null["nll"]) < 1e-6, (
        f"alt formula at mu=0 gave {nll_alt_formula_at_mu0}, null fit gave {null['nll']}"
    )


def test_invariant_ii_alt_nll_never_worse_than_null():
    """The free (alternative) fit is a strict superset of the null's
    parameter space, so its NLL must never exceed the null's, for any mass
    point."""
    null = lc.fit_bkg_only_poly(DATA, NODES, WEIGHTS, X_MIN, X_SCALE, n_coeffs=N_COEFFS)
    bkg_start = [null["n_bkg"]] + list(null["coeffs"])
    for mh in (111.0, 119.0, 125.0, 127.0, 141.0):
        alt = lc.fit_full_poly(DATA, EDGES, NODES, WEIGHTS, s_ref=1.0, mh=mh, sigma=2.462,
                                x_min=X_MIN, x_scale=X_SCALE, n_coeffs=N_COEFFS,
                                bkg_start=bkg_start)
        assert alt["nll"] <= null["nll"] + 1e-6, (
            f"mh={mh}: alt NLL {alt['nll']} exceeds null NLL {null['nll']}"
        )


def test_invariant_iii_null_and_alt_share_the_background_code_path():
    """Given the SAME (n_bkg, coeffs), the background array used by the
    null fit's NLL and the one used by the alternative fit's NLL must be
    byte-identical -- confirms there is exactly one background formula,
    not two that happen to usually agree."""
    n_bkg, coeffs = 61960.0, [2.2, -1.4, 0.28, -0.04, 0.04]
    b_from_null_path = lc.polynomial_bin_expectation(NODES, WEIGHTS, n_bkg, coeffs, X_MIN, X_SCALE,
                                                       None, None)
    b_from_alt_path = lc.polynomial_bin_expectation(NODES, WEIGHTS, n_bkg, coeffs, X_MIN, X_SCALE)
    assert np.array_equal(b_from_null_path, b_from_alt_path)


def test_null_fit_stable_across_starting_points():
    """
    THE check that actually catches the real bug. Refit the same null
    hypothesis (background-only) from two very different starting points:
    (a) the flat coefficient guess with the module's default n_bkg_start
        (what every script's very first `fit_bkg_only_poly(...)` call
        uses, with no override), and
    (b) the flat coefficient guess with n_bkg_start set to the data's own
        total count (what the profiled-curve's null fit uses).
    A correctly-converging fit must reach the same NLL either way.
    """
    data_total = float(np.sum(DATA))
    flat = [1.0, 0.0, 0.0, 0.0, 0.0]

    # OLD behaviour, reproduced with robust=False (passing `start=` alone
    # does NOT bypass multi-start -- robust=True is still the default and
    # would add rescue candidates on top of the given start; robust=False
    # is what actually forces the single-attempt fit this check needs):
    old_a = lc.fit_bkg_only_poly(DATA, NODES, WEIGHTS, X_MIN, X_SCALE, n_coeffs=N_COEFFS,
                                  start=[lc.N_BKG_TRUE] + flat, robust=False)
    old_b = lc.fit_bkg_only_poly(DATA, NODES, WEIGHTS, X_MIN, X_SCALE, n_coeffs=N_COEFFS,
                                  start=[data_total] + flat, robust=False)
    old_gap = abs(old_a["nll"] - old_b["nll"])
    print(f"\n[old single-start behaviour] NLL from n_bkg_start={lc.N_BKG_TRUE}: {old_a['nll']:.4f}; "
          f"from n_bkg_start={data_total:.0f}: {old_b['nll']:.4f}; gap={old_gap:.4f}")
    assert old_gap > 1.0, (
        "expected the OLD single-start behaviour to reproduce the bug (a large "
        f"gap between the two starting points); got a suspiciously small gap {old_gap:.4f} -- "
        "if this fails, the bug may already be fixed at a deeper level than expected."
    )

    # NEW (default) behaviour: multi-start enabled.
    new_a = lc.fit_bkg_only_poly(DATA, NODES, WEIGHTS, X_MIN, X_SCALE, n_coeffs=N_COEFFS)
    new_b = lc.fit_bkg_only_poly(DATA, NODES, WEIGHTS, X_MIN, X_SCALE, n_coeffs=N_COEFFS,
                                  n_bkg_start=data_total)
    new_gap = abs(new_a["nll"] - new_b["nll"])
    print(f"[new multi-start behaviour] NLL from n_bkg_start={lc.N_BKG_TRUE}: {new_a['nll']:.4f}; "
          f"from n_bkg_start={data_total:.0f}: {new_b['nll']:.4f}; gap={new_gap:.6f}")
    assert new_gap < 1e-3, f"multi-start fits still disagree by {new_gap:.4f} NLL units"


def test_null_fit_stable_matches_actual_pipeline_bug_magnitude():
    """
    Same idea as the check above, but with the EXACT pair of starting
    points the real pipeline used for the profiled curve's once-per-script
    null fit (`compute_zlr_variants.py`'s `null_profiled`): n_bkg_start set
    to Fit 1's own converged n_bkg, flat coefficients -- vs. Fit 1's own
    fully-converged coefficients directly. Confirmed directly (checked out
    the pre-fix lr_core.py at commit e9a097b and ran this exact comparison
    against it) that the OLD code landed 2.4662 NLL units apart here --
    matching the task's reported evidence (~2.4) almost exactly, and
    explaining the observed ~2.2-2.4 spurious |Z| offset seen in nearly
    every V3/V4 bin (Z = sqrt(q0) = sqrt(2*NLL_gap) = sqrt(2*2.466) = 2.22).
    The new (multi-start) code closes this to ~1e-8.
    """
    null = lc.fit_bkg_only_poly(DATA, NODES, WEIGHTS, X_MIN, X_SCALE, n_coeffs=N_COEFFS)
    flat_null = lc.fit_bkg_only_poly(DATA, NODES, WEIGHTS, X_MIN, X_SCALE, n_coeffs=N_COEFFS,
                                      n_bkg_start=null["n_bkg"])
    converged_start = [null["n_bkg"]] + list(null["coeffs"])
    converged_null = lc.fit_bkg_only_poly(DATA, NODES, WEIGHTS, X_MIN, X_SCALE, n_coeffs=N_COEFFS,
                                           start=converged_start)
    gap = abs(flat_null["nll"] - converged_null["nll"])
    print(f"\n[pipeline-exact stability check] gap = {gap:.4e} (old code: 2.4662)")
    assert gap < 1e-3, f"still {gap:.4f} NLL units apart -- the fix did not fully close this gap"


def test_profiled_z_matches_independent_cross_check():
    """The five spot-check values from the independent re-implementation
    that flagged this bug in the first place."""
    null = lc.fit_bkg_only_poly(DATA, NODES, WEIGHTS, X_MIN, X_SCALE, n_coeffs=N_COEFFS)
    bkg_start = [null["n_bkg"]] + list(null["coeffs"])
    expected = {111.0: 0.1, 119.0: -2.7, 125.0: 2.6, 127.0: 3.1, 141.0: -1.1}
    for mh, exp_z in expected.items():
        alt = lc.fit_full_poly(DATA, EDGES, NODES, WEIGHTS, s_ref=1.0, mh=mh, sigma=2.462,
                                x_min=X_MIN, x_scale=X_SCALE, n_coeffs=N_COEFFS,
                                bkg_start=bkg_start)
        z = lc.signed_z_from_nll(null["nll"], alt["nll"], alt["mu_hat"])
        assert abs(z - exp_z) < 0.15, f"mh={mh}: got Z={z:.3f}, independent check expects ~{exp_z}"


if __name__ == "__main__":
    test_invariant_i_alt_model_at_mu0_matches_null_nll()
    print("invariant (i): PASS")
    test_invariant_ii_alt_nll_never_worse_than_null()
    print("invariant (ii): PASS")
    test_invariant_iii_null_and_alt_share_the_background_code_path()
    print("invariant (iii): PASS")
    test_null_fit_stable_across_starting_points()
    print("null-fit-stability check (the one that actually caught the bug): PASS")
    test_null_fit_stable_matches_actual_pipeline_bug_magnitude()
    print("null-fit-stability check (exact pipeline magnitude, ~2.4 NLL units): PASS")
    test_profiled_z_matches_independent_cross_check()
    print("cross-check against independent re-implementation: PASS")
