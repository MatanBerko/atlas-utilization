"""
Background-model task, finalization: unit tests for
`final_model.background_expectation` -- reproduces the sideband-fit
expectation in sideband bins, bin integrals are positive, and
normalization consistency (full-range total = sideband total + blinded
total, by construction of the binning/masking). All synthetic where
possible -- no dependency on real data.
"""
from __future__ import annotations

import unittest

import numpy as np

from studies.hgg_cms.background_model.families import FAMILIES
from studies.hgg_cms.background_model.common import bin_edges, sideband_bin_mask
from studies.hgg_cms.background_model.final_model import background_expectation

SYNTHETIC_PARAMS = np.array([4200.0, 1800.0, 1650.0, 480.0, 880.0, 390.0, 360.0])  # order-6 Bernstein, 7 coeffs


class BackgroundExpectationTests(unittest.TestCase):
    def test_matches_direct_family_evaluation(self):
        edges = bin_edges(105.0, 180.0, 0.25)
        via_module = background_expectation("EBEB", params=SYNTHETIC_PARAMS, family="bernstein", order=6, edges=edges)
        direct = FAMILIES["bernstein"].bin_expectation(edges, 6, SYNTHETIC_PARAMS)
        np.testing.assert_array_equal(via_module, direct)

    def test_reproduces_sideband_fit_expectation_in_sideband_bins(self):
        # Simulates what a sideband-only fit's own likelihood evaluated:
        # background_expectation restricted to sideband bins must be
        # IDENTICAL to a direct family evaluation restricted the same way
        # (this is the property finalize_background_model.py's own live
        # check enforces on the real fit; here as a standalone regression test).
        edges = bin_edges(105.0, 180.0, 0.25)
        mask = sideband_bin_mask(edges)
        full = background_expectation("notEBEB", params=SYNTHETIC_PARAMS, family="bernstein", order=6, edges=edges)
        direct = FAMILIES["bernstein"].bin_expectation(edges, 6, SYNTHETIC_PARAMS)
        np.testing.assert_array_equal(full[mask], direct[mask])

    def test_covers_the_blinded_window_too(self):
        # The whole point of evaluating over the FULL range (not just
        # sideband bins) is that the blinded 115-135 GeV window is
        # covered too -- for the later S+B fit, which needs a background
        # prediction there (never a DATA value there).
        edges = bin_edges(105.0, 180.0, 0.25)
        pred = background_expectation("EBEB", params=SYNTHETIC_PARAMS, family="bernstein", order=6, edges=edges)
        centers = 0.5 * (edges[:-1] + edges[1:])
        blind_mask = (centers >= 115.0) & (centers < 135.0)
        self.assertGreater(blind_mask.sum(), 0)
        self.assertTrue(np.all(pred[blind_mask] > 0))

    def test_bin_integrals_are_positive(self):
        edges = bin_edges(105.0, 180.0, 0.25)
        pred = background_expectation("EBEB", params=SYNTHETIC_PARAMS, family="bernstein", order=6, edges=edges)
        self.assertTrue(np.all(pred > 0))

    def test_bin_integrals_positive_for_default_full_range(self):
        # Default edges (no `edges=` passed) should still be the full
        # 105-180 GeV range at 0.25 GeV -- 300 bins, all positive.
        pred = background_expectation("EBEB", params=SYNTHETIC_PARAMS, family="bernstein", order=6)
        self.assertEqual(len(pred), 300)
        self.assertTrue(np.all(pred > 0))

    def test_normalization_consistency_full_equals_sideband_plus_blind(self):
        edges = bin_edges(105.0, 180.0, 0.25)
        mask = sideband_bin_mask(edges)
        pred = background_expectation("EBEB", params=SYNTHETIC_PARAMS, family="bernstein", order=6, edges=edges)
        total_full = pred.sum()
        total_sideband = pred[mask].sum()
        total_blind = pred[~mask].sum()
        self.assertAlmostEqual(total_full, total_sideband + total_blind, places=6)

    def test_uses_final_model_json_when_params_omitted(self):
        # Uses an explicit `model` dict (avoiding a dependency on the
        # real committed results/background_model_final.json existing
        # in every checkout) to prove the "load from model" code path
        # works, independent of `test_matches_direct_family_evaluation`'s
        # explicit-params path.
        fake_model = {
            "per_category": {
                "EBEB": {"family": "bernstein", "order": 6, "params": SYNTHETIC_PARAMS.tolist()},
            }
        }
        edges = bin_edges(105.0, 180.0, 0.25)
        pred = background_expectation("EBEB", edges=edges, model=fake_model)
        direct = FAMILIES["bernstein"].bin_expectation(edges, 6, SYNTHETIC_PARAMS)
        np.testing.assert_array_equal(pred, direct)


if __name__ == "__main__":
    unittest.main()
