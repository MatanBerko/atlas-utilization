"""
Bias-study diagnosis: unit tests for the diagnostic helper functions
(worst-cell ranking, dominant-dimension grouping, the null-noise Monte
Carlo significance test, and the truth-spread-vs-signal arithmetic).
All synthetic -- no dependency on the real merged bias-study JSON,
which lives outside the repo.
"""
from __future__ import annotations

import unittest

import numpy as np

from studies.hgg_cms.background_model.diagnostics.part1_drivers import (
    worst_cells, group_means, dominant_driver,
)
from studies.hgg_cms.background_model.diagnostics.part2_significance import (
    simulate_null_max, p_value_for_function,
)
from studies.hgg_cms.background_model.diagnostics.part4_truth_spread import spread_vs_signal_summary


def _point(truth_family="bernstein", leakage_variant="nominal", mass=125.0,
           ratio=0.1, reliability_ok=True, se_ratio=0.05):
    return {
        "truth_family": truth_family, "leakage_variant": leakage_variant, "mass": mass,
        "ratio": ratio, "reliability_ok": reliability_ok, "se_ratio": se_ratio,
        "mean_S": ratio * 100.0, "mean_sigma_S": 100.0, "se_mean_S": se_ratio * 100.0,
    }


class WorstCellsTests(unittest.TestCase):
    def test_ranks_by_ratio_descending(self):
        pts = [_point(mass=m, ratio=r) for m, r in [(115, 0.5), (120, 0.9), (125, 0.1)]]
        top = worst_cells(pts, n=2)
        self.assertEqual([p["mass"] for p in top], [120, 115])

    def test_excludes_unreliable_cells(self):
        pts = [
            _point(mass=115, ratio=0.99, reliability_ok=False),
            _point(mass=120, ratio=0.3, reliability_ok=True),
        ]
        top = worst_cells(pts, n=5)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]["mass"], 120)

    def test_returns_empty_when_all_unreliable(self):
        pts = [_point(reliability_ok=False) for _ in range(5)]
        self.assertEqual(worst_cells(pts, n=5), [])


class DominantDriverTests(unittest.TestCase):
    def test_group_means_computed_correctly(self):
        pts = [
            _point(truth_family="bernstein", ratio=0.1),
            _point(truth_family="bernstein", ratio=0.3),
            _point(truth_family="expsum", ratio=0.9),
        ]
        by_fam = group_means(pts, "truth_family")
        self.assertAlmostEqual(by_fam["bernstein"], 0.2)
        self.assertAlmostEqual(by_fam["expsum"], 0.9)

    def test_dominant_dimension_picks_largest_spread(self):
        # truth_family varies a lot (0.05 vs 0.95), leakage_variant and
        # mass are held effectively constant -> truth_family must win.
        pts = []
        for fam, r in [("bernstein", 0.05), ("expsum", 0.95), ("powersum", 0.05), ("laurent", 0.05)]:
            for variant in ("nominal", "leakage_plus", "leakage_minus"):
                pts.append(_point(truth_family=fam, leakage_variant=variant, mass=125.0, ratio=r))
        dd = dominant_driver(pts)
        self.assertEqual(dd["dominant_dimension"], "truth_family")
        self.assertGreater(dd["spreads"]["truth_family"], dd["spreads"]["leakage_variant"])

    def test_unreliable_cells_excluded_from_grouping(self):
        pts = [_point(truth_family="bernstein", ratio=0.99, reliability_ok=False) for _ in range(10)]
        dd = dominant_driver(pts)
        self.assertEqual(dd["by_truth_family"], {})


class NullSignificanceTests(unittest.TestCase):
    def test_observed_at_null_mean_gives_mid_range_pvalue(self):
        # 60 cells all with the same se_ratio; the null distribution's
        # own mean-of-max should give a p-value well away from 0 or 1
        # (it's the MAX of 60, so its own mean is already an upper-tail
        # statistic -- check it's neither ~0 nor ~1).
        se = np.full(60, 0.05)
        null_max = simulate_null_max(se, n_mc=20000, seed=1)
        p = float(np.mean(null_max >= float(null_max.mean())))
        self.assertTrue(0.2 < p < 0.8)

    def test_far_below_null_gives_high_pvalue(self):
        pts = [_point(se_ratio=0.05, mass=m) for m in range(60)]
        r = p_value_for_function(pts, observed_worst_ratio=0.20, n_mc=20000, seed=2)
        self.assertGreater(r["p_value"], 0.5)

    def test_far_above_null_gives_tiny_pvalue(self):
        pts = [_point(se_ratio=0.02, mass=m) for m in range(60)]
        r = p_value_for_function(pts, observed_worst_ratio=1.0, n_mc=20000, seed=3)
        self.assertLess(r["p_value"], 0.001)

    def test_exceed_2se_count(self):
        pts = [
            _point(ratio=0.35, se_ratio=0.05),   # (0.35-0.20)/0.05 = 3.0 -> exceeds
            _point(ratio=0.22, se_ratio=0.05),   # 0.4 -> does not exceed
            _point(ratio=0.40, se_ratio=0.05),   # 4.0 -> exceeds
        ]
        r = p_value_for_function(pts, observed_worst_ratio=0.40, n_mc=5000, seed=4)
        self.assertEqual(r["n_cells_exceeding_0.20_by_gt_2se"], 2)


class TruthSpreadSummaryTests(unittest.TestCase):
    def test_spread_and_ratio_arithmetic(self):
        edges = np.array([120.0, 125.0, 130.0])  # 2 bins, both inside a [115,135) window
        curves = {
            "bernstein": {"nominal": np.array([100.0, 100.0]), "leakage_plus": None, "leakage_minus": None},
            "expsum": {"nominal": np.array([110.0, 95.0]), "leakage_plus": None, "leakage_minus": None},
        }
        sig_density = np.array([50.0, 20.0])
        s = spread_vs_signal_summary("TEST", curves, sig_density, edges)
        # bin 0: spread = |100-110| = 10; bin 1: spread = |100-95| = 5
        self.assertAlmostEqual(s["max_truth_family_spread_events_per_GeV"], 10.0)
        self.assertAlmostEqual(s["mean_truth_family_spread_events_per_GeV"], 7.5)
        self.assertAlmostEqual(s["signal_peak_density_events_per_GeV"], 50.0)
        self.assertAlmostEqual(s["spread_over_signal_peak_ratio"], 10.0 / 50.0)


if __name__ == "__main__":
    unittest.main()
