"""
Bias-study rerun 1: unit tests for merge_bias_results.py's multi-source
merge (combining the first run's job outputs with the rerun's) and the
REVISED selection procedure -- select_chosen_function must never
auto-apply fallback C; it only reports what fallback C would choose,
clearly marked as not applied. See BACKGROUND_MODEL_REPORT.md's
"Pre-declared selection procedure after the first bias study" section
(revised 18 Sep 2026) for the rule this enforces.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from studies.hgg_cms.background_model.cluster.merge_bias_results import (
    load_all_job_outputs, build_grid, evaluate_test_function, select_chosen_function,
    compute_fallback_c_choice,
)


def _job(category, truth_family, leakage_variant, mass, test_function_results):
    return {
        "category": category, "fit_range": "105_180", "truth_family": truth_family,
        "leakage_variant": leakage_variant, "mass": mass, "test_function_results": test_function_results,
    }


def _summary(mean_S, mean_sigma_S, n_total=300, n_failed=0, se_mean_S=None):
    n_used = n_total - n_failed
    return {
        "n_total": n_total, "n_failed": n_failed, "n_used": n_used,
        "fail_fraction": n_failed / n_total,
        "mean_S": mean_S, "mean_sigma_S": mean_sigma_S,
        "se_mean_S": se_mean_S if se_mean_S is not None else mean_sigma_S / (n_used ** 0.5),
    }


ORDER_SELECTION = {
    "EBEB": {
        "bernstein": {"per_order": {
            "4": {"n_params": 5, "fit": {"nll": -100.0}},
            "5": {"n_params": 6, "fit": {"nll": -101.0}},
            "6": {"n_params": 7, "fit": {"nll": -102.0}},
        }},
        "expsum": {"per_order": {"2": {"n_params": 4, "fit": {"nll": -99.0}}}},
    },
}


class MultiSourceMergeTests(unittest.TestCase):
    def test_load_all_job_outputs_pools_multiple_directories(self):
        with tempfile.TemporaryDirectory() as td:
            primary = Path(td) / "primary"
            extra = Path(td) / "extra"
            primary.mkdir()
            extra.mkdir()
            (primary / "a.json").write_text(json.dumps(_job("EBEB", "bernstein", "nominal", 125.0,
                                                              {"bernstein_4": _summary(1.0, 100.0)})))
            (extra / "b.json").write_text(json.dumps(_job("EBEB", "bernstein", "nominal", 125.0,
                                                            {"bernstein_6": _summary(2.0, 100.0)})))
            jobs = load_all_job_outputs(primary, extra)
            self.assertEqual(len(jobs), 2)

    def test_build_grid_merges_test_functions_for_the_same_cell(self):
        # Same (category, truth, leakage, mass) cell, different test
        # functions, from two different "sources" (simulating first run
        # + rerun both covering this cell) -- must end up in ONE cell
        # dict with both test functions present, not overwritten.
        jobs = [
            _job("EBEB", "bernstein", "nominal", 125.0, {"bernstein_4": _summary(1.0, 100.0)}),
            _job("EBEB", "bernstein", "nominal", 125.0, {"bernstein_6": _summary(2.0, 100.0)}),
        ]
        grid = build_grid(jobs)
        cell = grid["EBEB"][("bernstein", "nominal")][125.0]
        self.assertIn("bernstein_4", cell)
        self.assertIn("bernstein_6", cell)


class NoAutoFallbackTests(unittest.TestCase):
    """The core behavior this revision enforces: when nothing is both
    eligible and passing, select_chosen_function must return
    chosen=None -- NEVER the fallback-C candidate -- while still
    reporting what fallback C would pick."""

    def test_eligible_but_failing_candidate_is_not_auto_chosen(self):
        # bernstein_5: eligible, ratio 0.40 (fails 0.20 threshold).
        # This is exactly the case an OLDER version of this rule would
        # have auto-selected via fallback C -- must NOT be chosen now.
        grid = {
            ("bernstein", "nominal"): {
                115.0: {"bernstein_5": _summary(40.0, 100.0)},  # ratio = 0.40
            },
        }
        evaluations = {"bernstein_5": evaluate_test_function(grid, "bernstein_5")}
        self.assertTrue(evaluations["bernstein_5"]["eligible"])
        self.assertFalse(evaluations["bernstein_5"]["passes"])

        selection = select_chosen_function(evaluations, ORDER_SELECTION, "EBEB")
        self.assertIsNone(selection["chosen"])

    def test_fallback_c_candidate_is_reported_and_marked_not_applied(self):
        grid = {
            ("bernstein", "nominal"): {
                115.0: {
                    "bernstein_4": _summary(90.0, 100.0),   # ratio 0.90 (worse)
                    "bernstein_5": _summary(40.0, 100.0),   # ratio 0.40 (best eligible)
                },
            },
        }
        evaluations = {
            "bernstein_4": evaluate_test_function(grid, "bernstein_4"),
            "bernstein_5": evaluate_test_function(grid, "bernstein_5"),
        }
        selection = select_chosen_function(evaluations, ORDER_SELECTION, "EBEB")
        self.assertIsNone(selection["chosen"])  # still not auto-selected
        fc = selection["fallback_c_if_applied"]
        self.assertIsNotNone(fc)
        self.assertEqual(fc["would_choose"], "bernstein_5")  # smallest worst ratio among eligible
        self.assertIn("NOT APPLIED", fc["status"])
        self.assertIn("human decision", fc["status"])

    def test_candidate_summary_reports_every_candidate_including_ineligible(self):
        grid = {
            ("bernstein", "nominal"): {
                115.0: {
                    "bernstein_5": _summary(40.0, 100.0),
                    "expsum_2": _summary(5.0, 100.0, n_total=300, n_failed=150),  # 50% fail -> ineligible
                },
            },
        }
        evaluations = {
            "bernstein_5": evaluate_test_function(grid, "bernstein_5"),
            "expsum_2": evaluate_test_function(grid, "expsum_2"),
        }
        selection = select_chosen_function(evaluations, ORDER_SELECTION, "EBEB")
        self.assertIsNone(selection["chosen"])
        self.assertIn("bernstein_5", selection["candidate_summary"])
        self.assertIn("expsum_2", selection["candidate_summary"])
        self.assertFalse(selection["candidate_summary"]["expsum_2"]["eligible"])
        self.assertIn("expsum_2", selection["ineligible_functions"])
        # fallback C must only consider the ELIGIBLE one
        self.assertEqual(selection["fallback_c_if_applied"]["would_choose"], "bernstein_5")

    def test_no_eligible_candidate_at_all_gives_none_fallback(self):
        grid = {
            ("bernstein", "nominal"): {
                115.0: {"expsum_2": _summary(5.0, 100.0, n_total=300, n_failed=200)},  # ~67% fail
            },
        }
        evaluations = {"expsum_2": evaluate_test_function(grid, "expsum_2")}
        selection = select_chosen_function(evaluations, ORDER_SELECTION, "EBEB")
        self.assertIsNone(selection["chosen"])
        self.assertIsNone(selection["fallback_c_if_applied"])

    def test_fallback_c_tie_broken_by_fewer_params(self):
        # Two eligible candidates with the SAME worst ratio -- fewer
        # params must win the fallback-C ranking.
        grid = {
            ("bernstein", "nominal"): {
                115.0: {
                    "bernstein_4": _summary(40.0, 100.0),  # ratio 0.40, n_params=5
                    "bernstein_5": _summary(40.0, 100.0),  # ratio 0.40, n_params=6
                },
            },
        }
        evaluations = {
            "bernstein_4": evaluate_test_function(grid, "bernstein_4"),
            "bernstein_5": evaluate_test_function(grid, "bernstein_5"),
        }
        fc = compute_fallback_c_choice(evaluations, ORDER_SELECTION, "EBEB")
        self.assertEqual(fc["would_choose"], "bernstein_4")  # fewer params (5 < 6)

    def test_passing_candidate_is_still_auto_chosen_normally(self):
        # Sanity check: (i) is UNCHANGED -- a genuinely passing, eligible
        # candidate is still chosen automatically, same as before.
        grid = {
            ("bernstein", "nominal"): {
                115.0: {"bernstein_4": _summary(1.0, 100.0)},  # ratio 0.01, passes
            },
        }
        evaluations = {"bernstein_4": evaluate_test_function(grid, "bernstein_4")}
        selection = select_chosen_function(evaluations, ORDER_SELECTION, "EBEB")
        self.assertEqual(selection["chosen"], "bernstein_4")


if __name__ == "__main__":
    unittest.main()
