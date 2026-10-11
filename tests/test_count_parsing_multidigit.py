"""
Multi-digit object counts in final-state labels (upstream PR #34, commit
f16768e).

A final-state label is a set of ``<count><letter>`` tokens joined by "_",
e.g. ``0e_2m_5j_1b``. Four shared functions parse those tokens. Before this
fix they read the count as ``token[0]`` and the particle letter as
``token[1]``, which is only correct while every count is a single digit. For
a two-digit token such as ``"10j"`` they read the count as ``"1"`` and the
letter as ``"0"`` -- the letter lookup then failed, so the token was skipped
entirely. Upstream reads the count as ``token[:-1]`` and the letter as
``token[-1]``, which is correct for any number of digits.

Covers, for all four functions:
 1. ``limit_particles_in_fs`` and ``IMCalculator._limit_particles_in_fs``
    cap a two-digit count down to the threshold (the pre-fix code left it
    alone, so a 10-jet label kept "10j" while a 5-jet label was capped to
    "4j" -- an inconsistency this test pins down).
 2. ``is_finalstate_contain_combination`` and
    ``IMCalculator.does_final_state_contain_combination`` compare the real
    number, so a requirement above a two-digit count fails and one at or
    below it passes (the pre-fix code skipped the token and so answered
    "satisfied" for every requirement).
 3. The particle letter is taken from the END of the token, so a two-digit
    token still maps to the right object type.
 4. Single-digit labels behave exactly as before -- this fix must not move
    them.
 5. The invariant that makes the four-dataset CMS delivery unaffected: the
    largest ``start + count`` requirement in its combination set is 4, and a
    count of 10 or more satisfies every requirement at or below 4 under both
    the old and the new parsing. Recorded as a test so the delivery's
    immunity cannot be broken silently by someone raising ``max_count``.
"""
from __future__ import annotations

import unittest

from services.calculations.combinatorics import (
    get_all_combinations,
    get_count,
    get_start,
)
from services.calculations.im_calculator import IMCalculator
from services.calculations.physics_calcs import (
    is_finalstate_contain_combination,
    limit_particles_in_fs,
)


class LimitParticlesInFsMultiDigitTests(unittest.TestCase):
    """1. and 4. -- label capping, module-level and IMCalculator copies."""

    def _both(self, label, threshold=4):
        """Both implementations must agree; return their common answer."""
        a = limit_particles_in_fs(label, threshold)
        b = IMCalculator._limit_particles_in_fs(label, threshold)
        self.assertEqual(
            a, b,
            "physics_calcs.limit_particles_in_fs and "
            "IMCalculator._limit_particles_in_fs disagree on %r" % label,
        )
        return a

    def test_two_digit_count_is_capped(self):
        self.assertEqual(self._both("0e_2m_10j_1b"), "0e_2m_4j_1b")
        self.assertEqual(self._both("0e_2m_12j_1b"), "0e_2m_4j_1b")
        self.assertEqual(self._both("0e_11m_0j_0b"), "0e_4m_0j_0b")

    def test_two_digit_count_is_capped_in_six_field_labels(self):
        # the shared physics_calcs.group_by_final_state emits six fields
        self.assertEqual(
            self._both("0e_1m_10j_0g_0t_1b"), "0e_1m_4j_0g_0t_1b")
        self.assertEqual(
            self._both("0e_0m_13j_0g_0t_0b"), "0e_0m_4j_0g_0t_0b")

    def test_single_digit_counts_are_unchanged_by_this_fix(self):
        # at or below the threshold: untouched
        self.assertEqual(self._both("0e_2m_3j_1b"), "0e_2m_3j_1b")
        self.assertEqual(self._both("0e_0m_4j_0g_0t_0b"), "0e_0m_4j_0g_0t_0b")
        # above the threshold: capped, exactly as before the fix
        self.assertEqual(self._both("0e_2m_5j_1b"), "0e_2m_4j_1b")
        self.assertEqual(self._both("0e_2m_9j_1b"), "0e_2m_4j_1b")

    def test_capping_is_consistent_across_five_to_thirteen(self):
        # the pre-fix code capped 5-9 but left 10+ alone; every count above
        # the threshold must now cap, with no gap
        for n in range(5, 14):
            self.assertEqual(
                self._both("0e_0m_%dj_0b" % n), "0e_0m_4j_0b",
                "a count of %d was not capped to 4" % n,
            )

    def test_a_non_default_threshold_also_works_on_two_digits(self):
        self.assertEqual(self._both("0e_0m_12j_0b", threshold=6), "0e_0m_6j_0b")
        self.assertEqual(self._both("0e_0m_12j_0b", threshold=12), "0e_0m_12j_0b")


class ContainsCombinationMultiDigitTests(unittest.TestCase):
    """2. and 3. -- the combination test, module-level and IMCalculator copies."""

    def _both(self, label, combination):
        a = is_finalstate_contain_combination(label, combination)
        b = IMCalculator.does_final_state_contain_combination(label, combination)
        self.assertEqual(
            a, b,
            "physics_calcs.is_finalstate_contain_combination and "
            "IMCalculator.does_final_state_contain_combination disagree on "
            "%r / %r" % (label, combination),
        )
        return a

    def test_two_digit_count_is_compared_as_a_number(self):
        # 10 jets available
        self.assertTrue(self._both("0e_2m_10j_1b", {"Jets": 4}))
        self.assertTrue(self._both("0e_2m_10j_1b", {"Jets": 10}))
        # a requirement above the real count must FAIL; the pre-fix code
        # skipped the token and wrongly answered True here
        self.assertFalse(self._both("0e_2m_10j_1b", {"Jets": 11}))
        self.assertFalse(self._both("0e_2m_10j_1b", {"Jets": 13}))

    def test_two_digit_count_maps_to_the_right_particle_type(self):
        # the letter is the LAST character, so "11m" is eleven muons and
        # must not satisfy a jet requirement
        self.assertTrue(self._both("0e_11m_0j_0b", {"Muons": 4}))
        self.assertTrue(self._both("0e_11m_0j_0b", {"Muons": 11}))
        self.assertFalse(self._both("0e_11m_0j_0b", {"Muons": 12}))
        self.assertFalse(self._both("0e_11m_0j_0b", {"Jets": 1}))

    def test_two_digit_bjet_count(self):
        self.assertTrue(self._both("0e_0m_1j_10b", {"BJets": 4}))
        self.assertFalse(self._both("0e_0m_1j_10b", {"BJets": 11}))

    def test_subleading_start_index_respected_on_two_digit_counts(self):
        # (count, start) form: needs start + count objects available
        self.assertTrue(self._both("0e_0m_10j_0b", {"Jets": (4, 1)}))    # needs 5
        self.assertFalse(self._both("0e_0m_10j_0b", {"Jets": (4, 7)}))   # needs 11

    def test_single_digit_behaviour_is_unchanged_by_this_fix(self):
        self.assertTrue(self._both("0e_2m_3j_1b", {"Jets": 2}))
        self.assertFalse(self._both("0e_2m_3j_1b", {"Jets": 4}))
        self.assertTrue(self._both("0e_2m_3j_1b", {"Jets": 3, "Muons": 2}))
        self.assertFalse(self._both("0e_2m_3j_1b", {"Jets": 3, "Muons": 3}))

    def test_six_field_labels(self):
        self.assertTrue(self._both("0e_1m_10j_0g_0t_1b", {"Jets": 4, "Muons": 1}))
        self.assertFalse(self._both("0e_1m_10j_0g_0t_1b", {"Jets": 11}))


class DeliveryImmunityInvariantTests(unittest.TestCase):
    """5. -- why the four-dataset CMS delivery is unaffected by this fix."""

    # the delivery's own parameters, studies/cms_datasets/cluster/
    # run_dataset_on_file.py:206-223
    OBJECT_TYPES = ["Electrons", "Muons", "Jets", "BJets"]

    def _delivery_combinations(self):
        combos = get_all_combinations(
            object_types=self.OBJECT_TYPES,
            min_particles=1,
            max_particles=4,
            min_count=1,
            max_count=4,
            max_total_particles=4,
            include_subleading=True,
            max_subleading_index=1,
        )
        self.assertEqual(len(combos), 186)
        return combos

    def test_largest_requirement_in_the_delivery_set_is_four(self):
        largest = 0
        for combination in self._delivery_combinations():
            for value in combination.values():
                largest = max(largest, get_start(value) + get_count(value))
        self.assertEqual(
            largest, 4,
            "the delivery's combination set now contains a requirement above "
            "4; the old and new count parsing are no longer equivalent for "
            "two-digit counts and the delivery's immunity must be re-derived",
        )

    def test_a_two_digit_count_satisfies_every_delivery_requirement(self):
        # A label with 10 or more light jets satisfies every Jets
        # requirement in this set. Whether a whole combination passes also
        # depends on the other object types, so the Jets requirement is
        # probed on its own.
        combos = self._delivery_combinations()
        for label in ("0e_1m_10j_0b", "0e_1m_11j_0b", "0e_2m_12j_1b"):
            for combination in combos:
                if "Jets" not in combination:
                    continue
                jets_only = {"Jets": combination["Jets"]}
                self.assertTrue(
                    is_finalstate_contain_combination(label, jets_only),
                    "%r failed the Jets part of %r" % (label, combination),
                )
                self.assertTrue(
                    IMCalculator.does_final_state_contain_combination(
                        label, jets_only),
                    "%r failed the Jets part of %r (IMCalculator)"
                    % (label, combination),
                )


if __name__ == "__main__":
    unittest.main()
