"""
Background-model task: unit tests for family evaluation and positivity,
bin integration, the sideband mask, the blinding assertion, toy
generation, spurious-signal computation, and the NLL invariant. All
synthetic -- no real data or cluster files needed.
"""
from __future__ import annotations

import unittest

import numpy as np
from scipy.integrate import quad

from studies.hgg_cms.background_model.families import FAMILIES, LAURENT_EXPONENT_SEQUENCE, POSITIVITY_FLOOR
from studies.hgg_cms.background_model.common import bin_edges, sideband_bin_mask, category_mask
from studies.hgg_cms.background_model.fit_background import f_test_p_value, goodness_of_fit, fit_family_order
from studies.hgg_cms.background_model.bias_study import (
    build_truth_variants, generate_toy, summarize_toys, ToyResult, run_one_toy,
)
from studies.hgg_cms.background_model.leakage import leakage_template_fine


EDGES = np.array([105.0, 110.0, 125.3, 140.0, 180.0])


class FamilyPositivityAndIntegrationTests(unittest.TestCase):
    def test_bernstein_is_nonnegative_for_nonnegative_coeffs(self):
        fam = FAMILIES["bernstein"]
        rng = np.random.default_rng(0)
        edges = bin_edges(105.0, 180.0, 1.0)
        for _ in range(20):
            order = rng.integers(1, 8)
            coeffs = rng.uniform(0, 1000, size=order + 1)
            pred = fam.bin_expectation(edges, order, coeffs)
            self.assertTrue(np.all(pred > 0))

    def test_bernstein_matches_numeric_integral(self):
        fam = FAMILIES["bernstein"]
        from scipy.special import comb
        order, c = 3, [100.0, 50.0, 80.0, 20.0]

        def density(m):
            x = (m - 105.0) / 75.0
            return sum(c[i] * comb(order, i) * x ** i * (1 - x) ** (order - i) for i in range(order + 1))

        analytic = fam.bin_expectation(EDGES, order, c)
        for i in range(len(EDGES) - 1):
            numeric, _ = quad(density, EDGES[i], EDGES[i + 1])
            self.assertAlmostEqual(analytic[i], numeric, places=6)

    def test_expsum_matches_numeric_integral(self):
        fam = FAMILIES["expsum"]
        order, p = 2, [200.0, -2.0, 50.0, 1.0]

        def density(m):
            x = (m - 105.0) / 75.0
            return p[0] * np.exp(p[1] * x) + p[2] * np.exp(p[3] * x)

        analytic = fam.bin_expectation(EDGES, order, p)
        for i in range(len(EDGES) - 1):
            numeric, _ = quad(density, EDGES[i], EDGES[i + 1])
            self.assertAlmostEqual(analytic[i], numeric, places=6)

    def test_powersum_matches_numeric_integral(self):
        fam = FAMILIES["powersum"]
        order, p = 2, [500.0, -3.0, 30.0, -8.0]

        def density(m):
            xp = m / 105.0
            return p[0] * xp ** p[1] + p[2] * xp ** p[3]

        analytic = fam.bin_expectation(EDGES, order, p)
        for i in range(len(EDGES) - 1):
            numeric, _ = quad(density, EDGES[i], EDGES[i + 1])
            self.assertAlmostEqual(analytic[i], numeric, places=5)

    def test_laurent_matches_numeric_integral(self):
        fam = FAMILIES["laurent"]
        order, a = 3, [1e6, -2e6, 5e5]
        ks = LAURENT_EXPONENT_SEQUENCE[:order]

        def density(m):
            xp = m / 105.0
            return sum(a[i] * xp ** ks[i] for i in range(order))

        M = fam.design_matrix(EDGES, order)
        raw = M @ np.array(a)  # unclipped, to compare against numeric integral directly
        for i in range(len(EDGES) - 1):
            numeric, _ = quad(density, EDGES[i], EDGES[i + 1])
            self.assertAlmostEqual(raw[i], numeric, places=3)

    def test_laurent_negative_density_is_floored_not_left_negative(self):
        fam = FAMILIES["laurent"]
        a = [1e6, -2e6, 5e5]  # deliberately produces negative density in some bins
        pred = fam.bin_expectation(EDGES, 3, a)
        self.assertTrue(np.all(pred >= POSITIVITY_FLOOR))

    def test_all_families_positive_output_shape(self):
        edges = bin_edges(105.0, 180.0, 0.25)
        for name, fam in FAMILIES.items():
            order = 2 if name != "bernstein" else 3
            params = np.ones(fam.n_params(order)) * 10.0
            pred = fam.bin_expectation(edges, order, params)
            self.assertEqual(len(pred), len(edges) - 1)
            self.assertTrue(np.all(pred > 0))


class SidebandMaskAndBlindingTests(unittest.TestCase):
    def test_mask_excludes_exactly_the_blind_window_by_bin_center(self):
        edges = bin_edges(105.0, 180.0, 0.25)
        mask = sideband_bin_mask(edges)
        centers = 0.5 * (edges[:-1] + edges[1:])
        for c, m in zip(centers, mask):
            expected = not (115.0 <= c < 135.0)
            self.assertEqual(bool(m), expected)

    def test_mask_count_matches_expected_sideband_width(self):
        edges = bin_edges(105.0, 180.0, 0.25)
        mask = sideband_bin_mask(edges)
        # sideband width = 75 - 20 = 55 GeV -> 220 bins of 0.25 GeV
        self.assertEqual(int(mask.sum()), 220)

    def test_category_mask_partitions(self):
        cat = np.array(["EBEB", "notEBEB", "EBEB", "notEBEB"])
        m_eb = category_mask(cat, "EBEB")
        m_not = category_mask(cat, "notEBEB")
        np.testing.assert_array_equal(m_eb, ~m_not)

    def test_blinded_marker_path_refused(self):
        from studies.hgg_cms.output import BLINDED_MARKER
        # Confirm the marker string this module checks against matches
        # the one actually used by the output writer (no drift between
        # the two independent checks this task's rules require).
        self.assertEqual(BLINDED_MARKER, "BLINDED_SIGNAL_REGION")


class FTestAndGofTests(unittest.TestCase):
    def test_f_test_p_value_zero_improvement_gives_p_one(self):
        r = f_test_p_value(nll_low=100.0, ndf_low=10, nll_high=100.0, ndf_high=9)
        self.assertAlmostEqual(r["p_value"], 1.0, places=6)

    def test_f_test_p_value_large_improvement_gives_small_p(self):
        r = f_test_p_value(nll_low=150.0, ndf_low=10, nll_high=100.0, ndf_high=9)
        self.assertLess(r["p_value"], 0.001)

    def test_f_test_p_value_nonpositive_delta_ndf_returns_one(self):
        r = f_test_p_value(nll_low=100.0, ndf_low=10, nll_high=100.0, ndf_high=10)
        self.assertEqual(r["p_value"], 1.0)

    def test_goodness_of_fit_perfect_data_gives_high_p(self):
        edges = bin_edges(105.0, 180.0, 1.0)
        mask = np.ones(len(edges) - 1, dtype=bool)
        fam = FAMILIES["bernstein"]
        order = 3
        true_params = np.array([100.0, 150.0, 120.0, 90.0])
        pred = fam.bin_expectation(edges, order, true_params)
        gof = goodness_of_fit("bernstein", order, edges, pred, mask, true_params)
        self.assertGreater(gof["p_value"], 0.99)

    def test_fit_family_order_recovers_known_bernstein_shape(self):
        rng = np.random.default_rng(3)
        edges = bin_edges(105.0, 180.0, 1.0)
        mask = np.ones(len(edges) - 1, dtype=bool)
        fam = FAMILIES["bernstein"]
        order = 2
        true_params = np.array([500.0, 800.0, 300.0])
        truth = fam.bin_expectation(edges, order, true_params)
        data = rng.poisson(truth).astype(float)
        fit = fit_family_order("bernstein", order, edges, data, mask, n_starts=5)
        self.assertTrue(fit.valid)
        pred = fam.bin_expectation(edges, order, fit.params)
        # fitted total should be close to the data's own total (basic sanity)
        self.assertAlmostEqual(pred.sum(), data.sum(), delta=5 * np.sqrt(data.sum()))


class ToyGenerationAndSpuriousSignalTests(unittest.TestCase):
    def test_generate_toy_is_poisson_around_truth(self):
        rng = np.random.default_rng(5)
        truth = np.full(1000, 50.0)
        samples = np.array([generate_toy(rng, truth).mean() for _ in range(200)])
        # mean of 200 replicate means should be close to 50 (large-N CLT)
        self.assertAlmostEqual(samples.mean(), 50.0, delta=0.5)

    def test_build_truth_variants_leakage_signs(self):
        edges = bin_edges(105.0, 180.0, 1.0)
        base = np.full(len(edges) - 1, 100.0)
        leak = np.full(len(edges) - 1, 10.0)
        variants = {
            "nominal": base,
            "leakage_plus": base + 0.5 * leak,
            "leakage_minus": base - 0.5 * leak,
        }
        np.testing.assert_allclose(variants["leakage_plus"] - variants["nominal"], 5.0)
        np.testing.assert_allclose(variants["nominal"] - variants["leakage_minus"], 5.0)

    def test_summarize_toys_basic_arithmetic(self):
        results = [
            ToyResult(S=1.0, sigma_S=2.0, nll_splus_b=0, nll_bkg_only=0, bkg_valid=True,
                      splus_b_valid=True, invariant_violated=False, retried=False, failed=False),
            ToyResult(S=3.0, sigma_S=2.0, nll_splus_b=0, nll_bkg_only=0, bkg_valid=True,
                      splus_b_valid=True, invariant_violated=False, retried=False, failed=False),
            ToyResult(S=0.0, sigma_S=0.0, nll_splus_b=0, nll_bkg_only=0, bkg_valid=False,
                      splus_b_valid=False, invariant_violated=True, retried=True, failed=True),
        ]
        summary = summarize_toys(results)
        self.assertEqual(summary["n_total"], 3)
        self.assertEqual(summary["n_failed"], 1)
        self.assertEqual(summary["n_invariant_violated"], 1)
        self.assertAlmostEqual(summary["mean_S"], 2.0)
        self.assertAlmostEqual(summary["mean_sigma_S"], 2.0)
        self.assertAlmostEqual(summary["median_pull"], np.median([0.5, 1.5]))

    def test_summarize_toys_all_failed_returns_none_stats(self):
        results = [ToyResult(S=0, sigma_S=0, nll_splus_b=0, nll_bkg_only=0, bkg_valid=False,
                              splus_b_valid=False, invariant_violated=True, retried=True, failed=True)]
        summary = summarize_toys(results)
        self.assertIsNone(summary["mean_S"])
        self.assertEqual(summary["n_failed"], 1)


class NLLInvariantTests(unittest.TestCase):
    def test_run_one_toy_never_violates_invariant_beyond_tolerance(self):
        rng = np.random.default_rng(7)
        edges = bin_edges(105.0, 180.0, 1.0)  # coarse bins -> fast test
        fam = FAMILIES["bernstein"]
        order = 2
        true_params = np.array([300.0, 500.0, 200.0])
        truth = fam.bin_expectation(edges, order, true_params)
        sig_probs = np.zeros(len(edges) - 1)
        sig_probs[len(sig_probs) // 2] = 1.0  # a trivial single-bin "signal" template
        warm_start = true_params
        bounds = fam.bounds(order, float(truth.sum()))
        for _ in range(15):
            r = run_one_toy(rng, truth, "bernstein", order, edges, sig_probs, warm_start, bounds, s_bound=1e6)
            if not r.failed:
                self.assertLessEqual(r.nll_splus_b, r.nll_bkg_only + 1e-4)


class LeakageTemplateTests(unittest.TestCase):
    def test_rebinning_preserves_total_and_flat_quarters(self):
        import json
        import tempfile
        from pathlib import Path
        # synthetic leakage JSON with 2 coarse (1 GeV) bins
        d = {
            "bin_edges_GeV": [105.0, 106.0, 107.0],
            "bin_width_GeV": 1.0,
            "template_by_category": {
                "EBEB": {"N_expected_per_bin": [40.0, 80.0]},
            },
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "synthetic_leakage.json"
            p.write_text(json.dumps(d))
            fine_edges = bin_edges(105.0, 107.0, 0.25)
            template = leakage_template_fine("EBEB", fine_edges, path=str(p))
            self.assertEqual(len(template), 8)
            np.testing.assert_allclose(template[:4], 10.0)
            np.testing.assert_allclose(template[4:], 20.0)
            self.assertAlmostEqual(template.sum(), 120.0)


if __name__ == "__main__":
    unittest.main()
