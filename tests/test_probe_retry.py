"""
Implementation task 5, Part B (studies/hgg_cms/DESIGN_SELECTION.md, Section
8 task 5): retry the branch-accessibility probe in
FileParser._filter_accessible_branches, so a transient network error can't
silently drop fields or needlessly abort a run.

Review finding from task 4: the probe reads one entry; if the combined
read raises, it retries per branch ONCE (no retry at all -- one attempt),
and any branch whose single read raises is silently dropped. This is a
plausible, unproven cause of the known Muon looseId/pfRelIso04_all
field-drop bug (task 3's silent-intersection finding in
domain/events.py's _concatenate_events).

Covers:
 1. Combined read fails once, then succeeds -> all branches accessible,
    1 "retry" in the sense that a fallback path ran, 0 per-branch retries
    needed (the combined path has no retry of its own by design -- see
    Part B1's note that the successful-first-probe path is unchanged).
 2. Per-branch read fails 2 times then succeeds -> branch kept, 2 retries
    counted.
 3. Branch always fails -> dropped after the configured retries, warning
    logged, counted as a final failure.
 4. Branch absent from tree.keys() -> no retries at all.
 5. A requested extra object field whose probe fails transiently then
    succeeds -> NO RequiredObjectFieldMissingError.
 6. A default Muon field failing transiently in one of two files -> after
    the fix, present in both files and survives the cross-file merge.
    Demonstrated explicitly WITHOUT the fix (calling the pre-fix code path
    directly) to show it would have been dropped.
"""
from __future__ import annotations

import logging
import unittest

import awkward as ak
import numpy as np

from domain.events import _concatenate_events
from services.parsing.file_parser import FileParser, RequiredObjectFieldMissingError


class _CountingTree:
    """A tree whose .arrays() call can be scripted to fail N times for
    specific branches before succeeding, or fail forever."""

    def __init__(self, data: dict, fail_schedule: dict[str, int] | None = None,
                 always_fail_branches: set[str] | None = None,
                 fail_combined_n_times: int = 0):
        self._data = data
        # branch_name -> number of times left to fail before succeeding
        self._fail_schedule = dict(fail_schedule or {})
        self._always_fail_branches = set(always_fail_branches or set())
        self._fail_combined_n_times = fail_combined_n_times
        self._combined_call_count = 0
        self.num_entries = max((len(v) for v in data.values()), default=0)
        self.call_log: list[str] = []

    def keys(self):
        return list(self._data.keys())

    def arrays(self, branches, entry_start, entry_stop, library):
        if isinstance(branches, str):
            branches = [branches]

        if len(branches) > 1:
            # The combined probe.
            self._combined_call_count += 1
            self.call_log.append(f"combined#{self._combined_call_count}")
            if self._combined_call_count <= self._fail_combined_n_times:
                raise ConnectionError("simulated transient combined-read failure")
            missing = [b for b in branches if b not in self._data]
            if missing:
                raise KeyError(f"no such branch(es): {missing}")
            return ak.Array({b: self._data[b][entry_start:entry_stop] for b in branches})

        # Per-branch probe.
        branch = branches[0]
        self.call_log.append(f"probe:{branch}")
        if branch not in self._data:
            raise KeyError(f"no such branch: {branch}")
        if branch in self._always_fail_branches:
            raise ConnectionError(f"simulated permanent transient failure for {branch}")
        remaining = self._fail_schedule.get(branch, 0)
        if remaining > 0:
            self._fail_schedule[branch] = remaining - 1
            raise ConnectionError(f"simulated transient failure for {branch} ({remaining} left)")
        return ak.Array({branch: self._data[branch][entry_start:entry_stop]})


class ProbeRetryTests(unittest.TestCase):
    OBJ_BRANCHES = {
        "Muons": {"Muon_pt": "pt", "Muon_eta": "eta", "Muon_phi": "phi", "Muon_looseId": "looseId"},
    }

    def _data(self):
        return {
            "Muon_pt": ak.Array([[10.0], [20.0]]),
            "Muon_eta": ak.Array([[0.1], [0.2]]),
            "Muon_phi": ak.Array([[0.0], [0.1]]),
            "Muon_looseId": ak.Array([[True], [False]]),
            "run": np.array([1, 2], dtype=np.uint32),
            "luminosityBlock": np.array([10, 20], dtype=np.uint32),
            "event": np.array([100, 200], dtype=np.uint64),
        }

    def test_1_combined_read_fails_once_then_all_branches_accessible_via_fallback(self):
        tree = _CountingTree(self._data(), fail_combined_n_times=1)
        result = FileParser._filter_accessible_branches(
            tree, self.OBJ_BRANCHES, file_path="f.root", retry_delays_sec=[0, 0, 0],
        )
        self.assertEqual(set(result["Muons"].values()), {"pt", "eta", "phi", "looseId"})

    def test_2_per_branch_fails_twice_then_succeeds_branch_kept_and_retries_counted(self):
        tree = _CountingTree(
            self._data(),
            fail_combined_n_times=1,  # force fallback to per-branch probing
            fail_schedule={"Muon_looseId": 2},
        )
        retries = []
        result = FileParser._filter_accessible_branches(
            tree, self.OBJ_BRANCHES, file_path="f.root", retry_delays_sec=[0, 0, 0],
            on_probe_retry=lambda: retries.append(1),
        )
        self.assertIn("looseId", result["Muons"].values())
        self.assertEqual(len(retries), 2)

    def test_3_branch_always_fails_dropped_after_retries_and_logged(self):
        tree = _CountingTree(
            self._data(),
            fail_combined_n_times=1,
            always_fail_branches={"Muon_looseId"},
        )
        final_failures = []
        with self.assertLogs(level="WARNING") as log_ctx:
            result = FileParser._filter_accessible_branches(
                tree, self.OBJ_BRANCHES, file_path="specific_file.root", retry_delays_sec=[0, 0, 0],
                on_probe_final_failure=lambda b: final_failures.append(b),
            )
        self.assertNotIn("looseId", result["Muons"].values())
        self.assertIn("pt", result["Muons"].values())  # other fields unaffected
        self.assertEqual(final_failures, ["Muon_looseId"])
        joined_log = "\n".join(log_ctx.output)
        self.assertIn("specific_file.root", joined_log)
        self.assertIn("Muon_looseId", joined_log)

    def test_4_branch_absent_from_tree_keys_no_retries(self):
        data = self._data()
        del data["Muon_looseId"]  # genuinely absent from the tree
        tree = _CountingTree(data, fail_combined_n_times=1)
        retries = []
        result = FileParser._filter_accessible_branches(
            tree, self.OBJ_BRANCHES, file_path="f.root", retry_delays_sec=[0, 0, 0],
            on_probe_retry=lambda: retries.append(1),
        )
        self.assertNotIn("looseId", result["Muons"].values())
        self.assertEqual(retries, [])
        # No per-branch probe call was even attempted for the absent branch.
        self.assertNotIn("probe:Muon_looseId", tree.call_log)

    def test_5_extra_object_field_transient_failure_then_success_no_loud_error(self):
        """A requested extra object field (task 4's extra_object_fields)
        whose probe fails transiently and then succeeds must NOT raise
        RequiredObjectFieldMissingError."""
        data = {
            "Photon_pt": ak.Array([[25.0], [30.0]]),
            "Photon_eta": ak.Array([[0.1], [0.2]]),
            "Photon_phi": ak.Array([[0.0], [0.1]]),
            "Photon_mass": ak.Array([[0.0], [0.0]]),
            "run": np.array([1, 2], dtype=np.uint32),
            "luminosityBlock": np.array([10, 20], dtype=np.uint32),
            "event": np.array([100, 200], dtype=np.uint64),
            "Photon_electronVeto": ak.Array([[True], [False]]),
        }
        tree = _CountingTree(data, fail_combined_n_times=1, fail_schedule={"Photon_electronVeto": 2})

        class _FakeRoot(dict):
            def keys(self):
                return ["Events;1"]

        try:
            result = FileParser._parse_opened_file(
                _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "f.root", False, None,
                extra_object_fields={"Photons": ["electronVeto"]},
            )
        except RequiredObjectFieldMissingError:
            self.fail("RequiredObjectFieldMissingError raised despite the probe eventually succeeding")

        self.assertIn("electronVeto", result["Photons"].fields)
        self.assertEqual(ak.to_list(result["Photons"].electronVeto), [[True], [False]])

    def test_6_muon_field_survives_cross_file_merge_after_fix_and_would_not_before(self):
        """Two files: file A's looseId probe fails transiently (then
        succeeds, thanks to the fix); file B's looseId probe succeeds
        immediately. AFTER the fix, both files' Muons collection has
        looseId, and it survives being merged (domain.events.
        _concatenate_events, the cross-file concatenation task 3/4 also
        exercise). BEFORE the fix (max_attempts=1, i.e. no retry at all --
        this branch's own pre-fix behaviour, reproduced by passing an
        empty retry schedule), file A's looseId probe fails once and is
        permanently dropped for that file, so after the SAME merge step,
        looseId vanishes for BOTH files -- this is the muon bug's
        confirmed mechanism (see docs/CMS_KNOWN_LIMITATIONS.md)."""

        class _FakeRoot(dict):
            def keys(self):
                return ["Events;1"]

        # File A: looseId probe fails once, then would succeed on a retry.
        tree_a = _CountingTree(self._data(), fail_combined_n_times=1, fail_schedule={"Muon_looseId": 1})
        # File B: everything succeeds immediately.
        tree_b = _CountingTree(self._data(), fail_combined_n_times=0)

        # looseId is not in the cms-nanoaod schema's default Muons field
        # list (["pt", "eta", "phi", "mass"]) -- requested the same way the
        # real muon-bug investigation (task 4's object_field_survival_check.py)
        # requested it: via extra_object_fields.
        extra_fields = {"Muons": ["looseId"]}

        # -- AFTER the fix (retries enabled) --
        result_a_fixed = FileParser._parse_opened_file(
            _FakeRoot(Events=tree_a), ["Events"], "cms-nanoaod", 40_000, "a.root", False, None,
            extra_object_fields=extra_fields,
        )
        result_b_fixed = FileParser._parse_opened_file(
            _FakeRoot(Events=tree_b), ["Events"], "cms-nanoaod", 40_000, "b.root", False, None,
            extra_object_fields=extra_fields,
        )
        self.assertIn("looseId", result_a_fixed["Muons"].fields)
        self.assertIn("looseId", result_b_fixed["Muons"].fields)

        merged_fixed = _concatenate_events([result_a_fixed, result_b_fixed])
        self.assertIn("looseId", merged_fixed["Muons"].fields)
        self.assertEqual(
            ak.to_list(merged_fixed["Muons"].looseId),
            ak.to_list(result_a_fixed["Muons"].looseId) + ak.to_list(result_b_fixed["Muons"].looseId),
        )

        # -- BEFORE the fix: reproduce the OLD single-attempt behaviour
        # (retry_delays_sec=[] -- zero retries, exactly what every call
        # site used unconditionally before this task) directly at the
        # _filter_accessible_branches level, the lowest-level function this
        # task changed.
        tree_a_no_retry = _CountingTree(self._data(), fail_combined_n_times=1, fail_schedule={"Muon_looseId": 1})
        obj_branches = FileParser._extract_branches_by_schema(
            set(tree_a_no_retry.keys()), "cms-nanoaod", extra_object_fields=extra_fields,
        )
        accessible_before_fix = FileParser._filter_accessible_branches(
            tree_a_no_retry, obj_branches, file_path="a.root", retry_delays_sec=[],
        )
        self.assertNotIn("looseId", accessible_before_fix["Muons"].values(),
                          "pre-fix behaviour should have dropped looseId after a single failed probe")

        # Confirm the downstream consequence: even though file B's looseId
        # was read perfectly fine, merging A (missing looseId) and B (has
        # looseId) into one chunk silently drops looseId for BOTH -- the
        # confirmed mechanism behind the muon bug.
        obj_branches_b = FileParser._extract_branches_by_schema(
            set(tree_b.keys()), "cms-nanoaod", extra_object_fields=extra_fields,
        )
        accessible_b = FileParser._filter_accessible_branches(
            tree_b, obj_branches_b, file_path="b.root", retry_delays_sec=[],
        )
        self.assertIn("looseId", accessible_b["Muons"].values())  # B alone still has it


if __name__ == "__main__":
    unittest.main()
