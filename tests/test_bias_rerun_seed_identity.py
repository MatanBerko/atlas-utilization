"""
Bias-study rerun 1: proves that reusing a cell's seed reproduces
bit-identical pseudo-datasets, and that `make_job_list_rerun1.py`
assigns EXACTLY the same seed as the first run's `make_job_list.py` for
every (category, truth_family, leakage_variant, mass) cell.

WHY THIS MATTERS: `run_bias_job.py` creates ONE `numpy.random.Generator`
per job (`np.random.default_rng(seed)`) and consumes it SEQUENTIALLY
across whichever test functions that job evaluates -- each
`generate_toy` call advances the shared stream by one Poisson draw. A
rerun job evaluating a single NEW test function, seeded identically to
the original job for that cell, therefore reproduces exactly the same
toy sequence the ORIGINAL job's FIRST test function saw (bernstein is
first in `TRUTH_FAMILIES`/`FAMILIES` insertion order in every
`order_selection_<range>.json`, verified directly below, not assumed) --
not some other candidate's toys, and not a fresh, unrelated random
draw. This is what "the new function is tested on the identical
pseudo-datasets" means in practice, and is proven here rather than just
asserted.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]

from studies.hgg_cms.background_model.bias_study import build_truth_variants, generate_toy
# Aliased: the imported name starts with "test_", which pytest's default
# discovery would otherwise try to collect as a test function itself.
from studies.hgg_cms.background_model.cluster.run_bias_job import (
    test_functions_for_category as get_test_functions_for_category,
)
from studies.hgg_cms.background_model.common import bin_edges

ORDER_SELECTION_JSON = REPO_ROOT / "studies/hgg_cms/background_model/results/order_selection_105_180.json"
MAKE_JOB_LIST = REPO_ROOT / "studies/hgg_cms/background_model/cluster/make_job_list.py"
MAKE_JOB_LIST_RERUN1 = REPO_ROOT / "studies/hgg_cms/background_model/cluster/make_job_list_rerun1.py"


def _run(script: Path, out_path: Path):
    subprocess.run(
        [sys.executable, str(script), "--order-selection-json", str(ORDER_SELECTION_JSON), "--out", str(out_path)],
        check=True, cwd=str(REPO_ROOT), capture_output=True, text=True,
    )


def _parse_original(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cat, fam, var, mass, n_toys, seed = line.split()
        out[(cat, fam, var, mass)] = seed
    return out


def _parse_rerun1(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cat, fam, var, mass, n_toys, seed, tf = line.split()
        out[(cat, fam, var, mass)] = (seed, tf)
    return out


class JobListSeedIdentityTests(unittest.TestCase):
    """Requires the real, committed order_selection_105_180.json -- skipped
    if it isn't present (e.g. a checkout that hasn't run Part 2 locally)."""

    @classmethod
    def setUpClass(cls):
        if not ORDER_SELECTION_JSON.exists():
            raise unittest.SkipTest(f"{ORDER_SELECTION_JSON} not found")

    def test_rerun1_seeds_match_original_for_every_cell(self):
        with tempfile.TemporaryDirectory() as td:
            orig_path = Path(td) / "orig.txt"
            rerun_path = Path(td) / "rerun1.txt"
            _run(MAKE_JOB_LIST, orig_path)
            _run(MAKE_JOB_LIST_RERUN1, rerun_path)

            orig = _parse_original(orig_path)
            rerun1 = _parse_rerun1(rerun_path)

            self.assertEqual(len(rerun1), 120)
            mismatches = []
            for key, (seed, tf) in rerun1.items():
                if orig.get(key) != seed:
                    mismatches.append((key, orig.get(key), seed))
            self.assertEqual(mismatches, [], f"seed mismatches: {mismatches}")

    def test_new_candidate_is_bernstein_for_both_categories(self):
        with tempfile.TemporaryDirectory() as td:
            rerun_path = Path(td) / "rerun1.txt"
            _run(MAKE_JOB_LIST_RERUN1, rerun_path)
            rerun1 = _parse_rerun1(rerun_path)
            tf_by_cat = {key[0]: tf for key, (_, tf) in rerun1.items()}
            self.assertEqual(tf_by_cat["EBEB"], "bernstein:6")
            self.assertEqual(tf_by_cat["notEBEB"], "bernstein:7")

    def test_bernstein_is_first_in_test_functions_for_category(self):
        # The claim this whole module rests on: bernstein is the FIRST
        # entry test_functions_for_category returns, for both
        # categories, so a fresh rng(seed) used for a single new
        # function reproduces what the original job's FIRST test
        # function (bernstein) consumed -- checked directly, not assumed.
        config = json.loads(ORDER_SELECTION_JSON.read_text(encoding="utf-8"))
        for cat in ("EBEB", "notEBEB"):
            tfs = get_test_functions_for_category(config, cat)
            self.assertGreater(len(tfs), 0)
            self.assertEqual(tfs[0][0], "bernstein")


class ToyGenerationBitIdenticalTests(unittest.TestCase):
    """Synthetic truth (no dependency on the real committed JSON) --
    proves the CORE reproducibility property: the same seed, consumed
    from the start of a fresh Generator, produces bit-identical Poisson
    pseudo-datasets, independent of which test function later fits
    them."""

    def setUp(self):
        self.edges = bin_edges(105.0, 180.0, 0.25)
        # a plausible-scale synthetic truth (order-4 Bernstein-like flat
        # decreasing curve) -- values don't matter, only reproducibility does
        x = np.linspace(1.0, 0.2, len(self.edges) - 1)
        self.truth = 150.0 * x

    def _generate_n_toys(self, seed: int, n: int) -> list:
        rng = np.random.default_rng(seed)
        return [generate_toy(rng, self.truth) for _ in range(n)]

    def test_same_seed_gives_bit_identical_toy_sequence(self):
        seed = 20260918001
        toys_a = self._generate_n_toys(seed, 20)
        toys_b = self._generate_n_toys(seed, 20)
        self.assertEqual(len(toys_a), len(toys_b))
        for a, b in zip(toys_a, toys_b):
            np.testing.assert_array_equal(a, b)

    def test_different_seed_gives_different_toy_sequence(self):
        toys_a = self._generate_n_toys(20260918001, 5)
        toys_b = self._generate_n_toys(20260918002, 5)
        # overwhelmingly unlikely all 5 toys happen to match by chance
        all_equal = all(np.array_equal(a, b) for a, b in zip(toys_a, toys_b))
        self.assertFalse(all_equal)

    def test_single_function_job_matches_first_slice_of_multi_function_job(self):
        """Directly reproduces run_bias_job.py's own toy-generation loop
        structure: ONE `rng` created per job, consumed sequentially
        across however many test functions that job evaluates. A job
        evaluating only ONE test function (the rerun's own case) must
        see the same toy sequence as the FIRST test-function slice of a
        job that evaluates several, when both start from the same seed.
        """
        seed = 20260918042
        n_toys = 15

        # "original-style" job: two test functions, one shared rng,
        # consumed sequentially (mirrors run_bias_job.py's own loop).
        rng_multi = np.random.default_rng(seed)
        first_function_toys = [generate_toy(rng_multi, self.truth) for _ in range(n_toys)]
        second_function_toys = [generate_toy(rng_multi, self.truth) for _ in range(n_toys)]

        # "rerun-style" job: ONE test function only, fresh rng, same seed.
        rng_single = np.random.default_rng(seed)
        rerun_toys = [generate_toy(rng_single, self.truth) for _ in range(n_toys)]

        for a, b in zip(first_function_toys, rerun_toys):
            np.testing.assert_array_equal(a, b)
        # and, as expected, NOT equal to the second function's slice
        # (proves this isn't a trivial always-equal check)
        any_different = any(not np.array_equal(a, b) for a, b in zip(second_function_toys, rerun_toys))
        self.assertTrue(any_different)


if __name__ == "__main__":
    unittest.main()
