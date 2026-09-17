"""
Signal-model task: unit tests for shape evaluation, bin integration, mass
shifting, and yield-reproduction arithmetic. These test the CORE
COMPUTATIONAL functions directly against synthetic inputs -- not the
real-file-loading entrypoints (those need the real merged signal ROOT
files on this laptop, HGG_MERGED_DIR).
"""
from __future__ import annotations

import unittest

import numpy as np
from scipy.integrate import quad

from studies.hgg_cms.signal_model.shapes import dcb_pdf, dcb_cdf, SignalShape
from studies.hgg_cms.signal_model.loader import SignalEvents, reproduce_part_e
from studies.hgg_cms.stats.binning import bin_edges, bin_centers, poisson_nll


DCB_PARAMS = dict(mu=125.0, sigma=2.0, alphaL=1.4, nL=5.0, alphaR=1.7, nR=6.0)


class DCBShapeTests(unittest.TestCase):
    def test_pdf_integrates_to_one(self):
        xs = np.linspace(50, 250, 400_001)
        pdf = dcb_pdf(xs, **DCB_PARAMS)
        integral = np.trapezoid(pdf, xs)
        self.assertAlmostEqual(integral, 1.0, places=4)

    def test_cdf_matches_numeric_integral(self):
        test_points = [100.0, 115.0, 122.0, 125.0, 128.0, 135.0, 160.0]
        analytic = dcb_cdf(np.array(test_points), **DCB_PARAMS)

        def f(x):
            return dcb_pdf(np.array([x]), **DCB_PARAMS)[0]

        for x, a in zip(test_points, analytic):
            numeric, _ = quad(f, -80.0, x, limit=300)
            self.assertAlmostEqual(a, numeric, places=5)

    def test_cdf_is_monotonic_and_bounded(self):
        xs = np.linspace(-50, 300, 2000)
        c = dcb_cdf(xs, **DCB_PARAMS)
        self.assertTrue(np.all(np.diff(c) >= -1e-12))
        self.assertGreaterEqual(c.min(), 0.0)
        self.assertLessEqual(c.max(), 1.0 + 1e-9)

    def test_pure_dcb_mode_equals_mu(self):
        shape = SignalShape(params=DCB_PARAMS, use_gauss2=False,
                             param_names=tuple(DCB_PARAMS.keys()))
        self.assertAlmostEqual(shape.mode(), DCB_PARAMS["mu"], places=6)

    def test_sigma_eff68_recovers_known_gaussian_limit(self):
        # A very peaked-core, high-alpha/high-n DCB is nearly Gaussian;
        # sigma_eff68 for a Gaussian is sigma * z_0.6835 ~= 1.033*sigma.
        params = dict(mu=125.0, sigma=2.0, alphaL=6.0, nL=50.0, alphaR=6.0, nR=50.0)
        shape = SignalShape(params=params, use_gauss2=False, param_names=tuple(params.keys()))
        sigma_eff = shape.sigma_eff68()
        self.assertAlmostEqual(sigma_eff / 2.0, 1.0, delta=0.05)


class BinIntegrationTests(unittest.TestCase):
    def test_fine_bins_sum_to_in_range_fraction(self):
        shape = SignalShape(params=DCB_PARAMS, use_gauss2=False,
                             param_names=tuple(DCB_PARAMS.keys()))
        edges = np.arange(105.0, 180.0 + 0.25, 0.25)
        total = np.sum(shape.bin_probabilities(edges))
        expected = shape.in_range_fraction(105.0, 180.0)
        self.assertAlmostEqual(total, expected, places=10)

    def test_full_real_line_bins_sum_to_one(self):
        shape = SignalShape(params=DCB_PARAMS, use_gauss2=False,
                             param_names=tuple(DCB_PARAMS.keys()))
        edges = np.linspace(-500.0, 750.0, 20001)
        total = np.sum(shape.bin_probabilities(edges))
        self.assertAlmostEqual(total, 1.0, places=4)

    def test_bin_probability_matches_direct_cdf_difference(self):
        shape = SignalShape(params=DCB_PARAMS, use_gauss2=False,
                             param_names=tuple(DCB_PARAMS.keys()))
        edges = np.array([120.0, 122.5, 125.0, 127.5, 130.0])
        probs = shape.bin_probabilities(edges)
        c = shape.cdf(edges)
        np.testing.assert_allclose(probs, np.diff(c))

    def test_dcb_gauss_mixture_bin_probabilities_sum_correctly(self):
        params = dict(DCB_PARAMS)
        params.update(frac2=0.3, mu2=124.0, sigma2=4.0)
        shape = SignalShape(params=params, use_gauss2=True,
                             param_names=tuple(params.keys()))
        edges = np.arange(105.0, 180.0 + 0.25, 0.25)
        total = np.sum(shape.bin_probabilities(edges))
        expected = shape.in_range_fraction(105.0, 180.0)
        self.assertAlmostEqual(total, expected, places=10)


class MassShiftTests(unittest.TestCase):
    def test_shift_to_same_mass_is_identity(self):
        shape = SignalShape(params=DCB_PARAMS, use_gauss2=False,
                             param_names=tuple(DCB_PARAMS.keys()))
        shifted = shape.shifted_to_mass(125.0, mu_ref=125.0)
        self.assertAlmostEqual(shifted.params["mu"], shape.params["mu"])

    def test_shift_moves_mean_by_delta(self):
        # mean(mH) = mH + delta, delta = fitted_mean - 125
        params = dict(DCB_PARAMS)
        params["mu"] = 124.8  # fitted mean != 125, so delta = -0.2
        shape = SignalShape(params=params, use_gauss2=False,
                             param_names=tuple(params.keys()))
        delta = params["mu"] - 125.0
        for mH in (110.0, 120.0, 130.0, 140.0):
            shifted = shape.shifted_to_mass(mH, mu_ref=125.0)
            self.assertAlmostEqual(shifted.params["mu"], mH + delta, places=8)

    def test_shift_leaves_other_shape_params_fixed(self):
        shape = SignalShape(params=DCB_PARAMS, use_gauss2=False,
                             param_names=tuple(DCB_PARAMS.keys()))
        shifted = shape.shifted_to_mass(140.0)
        for key in ("sigma", "alphaL", "nL", "alphaR", "nR"):
            self.assertEqual(shifted.params[key], shape.params[key])

    def test_shift_moves_both_means_in_mixture(self):
        params = dict(DCB_PARAMS)
        params.update(frac2=0.3, mu2=124.5, sigma2=4.0)
        shape = SignalShape(params=params, use_gauss2=True,
                             param_names=tuple(params.keys()))
        delta = params["mu"] - 125.0
        delta2 = params["mu2"] - 125.0
        shifted = shape.shifted_to_mass(132.0)
        self.assertAlmostEqual(shifted.params["mu"], 132.0 + delta, places=8)
        self.assertAlmostEqual(shifted.params["mu2"], 132.0 + delta2, places=8)


class YieldReproductionTests(unittest.TestCase):
    def _make_synthetic_signal(self, seed=0, n=1000):
        rng = np.random.default_rng(seed)
        mgg = rng.normal(125.0, 2.0, size=n)
        category = np.where(rng.random(n) < 0.6, "EBEB", "EEEB")
        genWeight = rng.normal(1.0, 0.1, size=n)
        pileup_weight = np.clip(rng.normal(1.0, 0.05, size=n), 0.1, 5.0)
        return SignalEvents("synthetic", mgg, category, genWeight, pileup_weight, scale=0.01)

    def test_weight_with_and_without_pileup(self):
        sig = self._make_synthetic_signal()
        w_no_pu = sig.weight(use_pileup=False)
        w_pu = sig.weight(use_pileup=True)
        np.testing.assert_allclose(w_no_pu, sig.scale * sig.genWeight)
        np.testing.assert_allclose(w_pu, sig.scale * sig.genWeight * sig.pileup_weight)

    def test_category_mask_partitions_events(self):
        sig = self._make_synthetic_signal()
        m_eb = sig.category_mask("EBEB")
        m_not = sig.category_mask("notEBEB")
        # every event is in exactly one of the two masks
        np.testing.assert_array_equal(m_eb, ~m_not)

    def test_n_effective_known_case(self):
        # all weights equal -> n_effective == n_events exactly
        n = 500
        sig = SignalEvents("x", np.full(n, 125.0), np.full(n, "EBEB"),
                            genWeight=np.full(n, 2.0), pileup_weight=np.ones(n), scale=1.0)
        self.assertAlmostEqual(sig.n_effective(), n, places=6)

    def test_n_effective_with_mixed_weights_by_hand(self):
        gw = np.array([1.0, 1.0, 2.0, -0.5])
        sig = SignalEvents("x", np.full(4, 125.0), np.full(4, "EBEB"),
                            genWeight=gw, pileup_weight=np.ones(4), scale=1.0)
        expected = gw.sum() ** 2 / np.sum(gw ** 2)
        self.assertAlmostEqual(sig.n_effective(), expected, places=10)

    def test_reproduce_part_e_arithmetic_self_consistent(self):
        # Build a synthetic all_signal dict covering the labels reproduce_part_e
        # expects, and check its own total_before_pu / total_after_pu are the
        # exact sums of the per-label per-category numbers it also returns
        # (a pure arithmetic self-consistency check, no external reference file).
        from studies.hgg_cms.signal_model.loader import SIGNAL_LABELS
        rng = np.random.default_rng(1)
        all_signal = {}
        for label in SIGNAL_LABELS:
            n = 200
            mgg = rng.normal(125.0, 2.0, size=n)
            category = np.where(rng.random(n) < 0.5, "EBEB", "EEEB")
            genWeight = rng.normal(1.0, 0.2, size=n)
            pileup_weight = np.clip(rng.normal(1.0, 0.1, size=n), 0.1, 5.0)
            all_signal[label] = SignalEvents(label, mgg, category, genWeight, pileup_weight, scale=0.5)

        result = reproduce_part_e(all_signal)
        recomputed_total_before = sum(v["inclusive_before_pu"] for v in result["per_label"].values())
        recomputed_total_after = sum(v["inclusive_after_pu"] for v in result["per_label"].values())
        self.assertAlmostEqual(result["total_before_pu"], recomputed_total_before, places=8)
        self.assertAlmostEqual(result["total_after_pu"], recomputed_total_after, places=8)

        for label, sig in all_signal.items():
            per_cat = result["per_label"][label]["per_category"]
            cat_sum_before = sum(per_cat[c]["N_before_pu"] for c in ("EBEB", "notEBEB"))
            self.assertAlmostEqual(cat_sum_before, result["per_label"][label]["inclusive_before_pu"], places=8)


class BinningUtilTests(unittest.TestCase):
    def test_bin_edges_and_centers(self):
        edges = bin_edges(105.0, 180.0, 300)
        self.assertEqual(len(edges), 301)
        self.assertAlmostEqual(edges[0], 105.0)
        self.assertAlmostEqual(edges[-1], 180.0)
        centers = bin_centers(edges)
        self.assertEqual(len(centers), 300)
        self.assertAlmostEqual(centers[0], 105.125)

    def test_poisson_nll_minimized_at_truth(self):
        rng = np.random.default_rng(2)
        nu_true = np.full(50, 100.0)
        n = rng.poisson(nu_true)
        nll_true = poisson_nll(n, nu_true)
        nll_off = poisson_nll(n, nu_true * 1.5)
        self.assertLess(nll_true, nll_off)


if __name__ == "__main__":
    unittest.main()
