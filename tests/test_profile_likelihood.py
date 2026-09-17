"""
Statistical-model task: unit tests for `fit.profile_interval` (the
generic Delta(-2lnL)=1 root-finder, tested against EXACT analytic
answers, no model/data involved) and an integration-level sanity check
of `fit.profile_likelihood_mu_error` (the model-specific wrapper) on
the real 28-parameter model's own Asimov fit, comparing against the
already-established HESSE-based sigma_mu as a soft consistency check
-- not an exact match, since the two methods make different
assumptions (local quadratic vs full profile).
"""
from __future__ import annotations

import unittest

from studies.hgg_cms.stats import fit as F
from studies.hgg_cms.stats import model as M


class ProfileIntervalExactAnswerTests(unittest.TestCase):
    def test_symmetric_quadratic_nll_gives_exact_sigma(self):
        # nll(mu) = 0.5 * ((mu - mu0) / sigma) ** 2 -- a pure Gaussian
        # NLL. Delta(-2lnL)=1 <=> deltaNLL=0.5 crossings are EXACTLY
        # mu0 +- sigma, by construction (0.5*((mu0+-sigma - mu0)/sigma)^2
        # = 0.5*1^2 = 0.5).
        mu0, sigma = 2.0, 1.5
        nll = lambda mu: 0.5 * ((mu - mu0) / sigma) ** 2
        mu_up = F.profile_interval(nll, mu_hat=mu0, nll_hat=0.0, direction=+1, tol=1e-6)
        mu_down = F.profile_interval(nll, mu_hat=mu0, nll_hat=0.0, direction=-1, tol=1e-6)
        self.assertAlmostEqual(mu_up, mu0 + sigma, places=4)
        self.assertAlmostEqual(mu_down, mu0 - sigma, places=4)

    def test_asymmetric_piecewise_quadratic_nll_gives_exact_asymmetric_errors(self):
        # Different curvature on each side of the minimum -> different
        # exact sigma_up and sigma_down, both still exactly computable.
        sigma_up, sigma_down = 1.0, 0.4

        def nll(mu):
            if mu >= 0:
                return 0.5 * (mu / sigma_up) ** 2
            return 0.5 * (mu / sigma_down) ** 2

        mu_up = F.profile_interval(nll, mu_hat=0.0, nll_hat=0.0, direction=+1, tol=1e-6)
        mu_down = F.profile_interval(nll, mu_hat=0.0, nll_hat=0.0, direction=-1, tol=1e-6)
        self.assertAlmostEqual(mu_up, sigma_up, places=4)
        self.assertAlmostEqual(mu_down, -sigma_down, places=4)

    def test_no_crossing_within_max_search_returns_none(self):
        # A very shallow linear "NLL" that never actually reaches
        # deltaNLL=0.5 within a small search range.
        nll = lambda mu: 0.0001 * abs(mu)
        result = F.profile_interval(nll, mu_hat=0.0, nll_hat=0.0, direction=+1, max_search=5.0)
        self.assertIsNone(result)

    def test_offset_minimum_still_exact(self):
        # mu_hat/nll_hat not at the function's own true minimum (as a
        # real fit's reported "best" point might be slightly off due to
        # numerical tolerance) -- the crossing is still exactly solvable
        # relative to the GIVEN nll_hat, not the function's true min.
        mu0, sigma = -3.0, 0.7
        nll = lambda mu: 0.5 * ((mu - mu0) / sigma) ** 2
        mu_up = F.profile_interval(nll, mu_hat=mu0, nll_hat=nll(mu0), direction=+1, tol=1e-6)
        self.assertAlmostEqual(mu_up, mu0 + sigma, places=4)


class ProfileLikelihoodMuErrorIntegrationTests(unittest.TestCase):
    """A real (but cheap: n_starts=1, Asimov not toys) end-to-end check
    that `profile_likelihood_mu_error` runs against the actual model
    and gives a sigma_mu in the same ballpark as the already-established
    HESSE-based Asimov sigma_mu_full=0.328 (STATS_REPORT.md Part 3.2) --
    a soft consistency check (generous tolerance), not an exact match,
    since profile-likelihood and HESSE make different assumptions."""

    def test_profile_likelihood_matches_hesse_within_loose_tolerance_at_asimov(self):
        names = M.full_param_names()
        base = F.default_start(names, mu_start=1.0)
        asimov = F.generate_asimov(base, 125.09)
        alt_fit = F.fit_model(asimov, 125.09, names, mu_fixed=None, n_starts=3, seed=1, base_start=base)
        self.assertTrue(alt_fit.valid)

        result = F.profile_likelihood_mu_error(asimov, 125.09, names, alt_fit, n_starts=1)
        self.assertIsNotNone(result["sigma_up"])
        self.assertIsNotNone(result["sigma_down"])
        # Both sides should be positive and roughly comparable to each
        # other (the Asimov likelihood here is close to symmetric).
        self.assertGreater(result["sigma_up"], 0.0)
        self.assertGreater(result["sigma_down"], 0.0)
        hesse_sigma = 0.3280  # STATS_REPORT.md Part 3.2, sigma_mu_full at mu=1
        self.assertLess(abs(result["sigma_up"] - hesse_sigma) / hesse_sigma, 0.35)
        self.assertLess(abs(result["sigma_down"] - hesse_sigma) / hesse_sigma, 0.35)


if __name__ == "__main__":
    unittest.main()
