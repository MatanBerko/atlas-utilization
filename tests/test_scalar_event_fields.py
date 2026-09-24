"""
Implementation task 1 (studies/hgg_cms/DESIGN_SELECTION.md, Section 8): the
general scalar-per-event-field mechanism.

Covers:
 1. The existing EventIds (run/luminosityBlock/event) behaviour is
    reproduced exactly by the generalized mechanism.
 2. A synthetic second scalar group round-trips through extraction, the
    accessibility gate, re-attachment, and multi-file concatenation --
    including one file missing a declared branch, exercising the
    raise-on-missing behaviour chosen for this mechanism (see
    FileParser._parse_opened_file's docstring/comments).
 3. Name-collision errors (group name vs. object collection name; branch
    name requested by two different groups).
 4. Absent extra_scalar_branches -> identical output to today.
 5. A real-file demo (network-marked, skipped offline) requesting two real
    NanoAOD scalar branches from one DoubleEG Run2016G file.
"""
from __future__ import annotations

import os
import unittest

import awkward as ak
import numpy as np

from domain.events import _concatenate_events
from services.parsing.file_parser import FileParser
from services.parsing import schemas


class FakeTree:
    """Minimal stand-in for an uproot TTree, keyed on branch name."""

    def __init__(self, data: dict, num_entries: int):
        self._data = data
        self.num_entries = num_entries

    def keys(self):
        return list(self._data.keys())

    def arrays(self, branches, entry_start, entry_stop, library):
        if isinstance(branches, str):
            branches = [branches]  # mirrors uproot accepting a bare branch name
        missing = [b for b in branches if b not in self._data]
        if missing:
            # Mirrors uproot's behaviour of raising when asked for a branch
            # that doesn't exist, which is what makes
            # FileParser._filter_accessible_branches fall back to testing
            # branches one at a time (see its `except Exception:` path).
            raise KeyError(f"no such branch(es): {missing}")
        return ak.Array({b: self._data[b][entry_start:entry_stop] for b in branches})


class FakeRoot(dict):
    def keys(self):
        return ["Events;1"]


def _make_cms_tree(extra_branches=None, n_events=2):
    data = {
        "Electron_pt": ak.Array([[25.0], [30.0]][:n_events]),
        "Electron_eta": ak.Array([[0.1], [0.2]][:n_events]),
        "Electron_phi": ak.Array([[0.0], [0.1]][:n_events]),
        "Electron_mass": ak.Array([[0.000511], [0.000511]][:n_events]),
        "run": np.array([1, 2], dtype=np.uint32)[:n_events],
        "luminosityBlock": np.array([10, 20], dtype=np.uint32)[:n_events],
        "event": np.array([100, 200], dtype=np.uint64)[:n_events],
    }
    if extra_branches:
        data.update(extra_branches)
    return FakeTree(data, n_events)


class EventIdsReproducedTests(unittest.TestCase):
    """Test 1: existing EventIds behaviour, reproduced by the general mechanism."""

    def test_run_lumi_event_fields_unchanged(self):
        tree = _make_cms_tree()
        root = FakeRoot(Events=tree)
        result = FileParser._parse_opened_file(
            root, ["Events"], "cms-nanoaod", 40_000, "fake.root", False, None,
        )
        self.assertIn("run", result.fields)
        self.assertIn("luminosityBlock", result.fields)
        self.assertIn("event", result.fields)
        self.assertIn("Electrons", result.fields)
        # Values
        self.assertEqual(ak.to_list(result["run"]), [1, 2])
        self.assertEqual(ak.to_list(result["luminosityBlock"]), [10, 20])
        self.assertEqual(ak.to_list(result["event"]), [100, 200])
        # Dtypes preserved
        self.assertEqual(str(ak.to_numpy(result["run"]).dtype), "uint32")
        self.assertEqual(str(ak.to_numpy(result["luminosityBlock"]).dtype), "uint32")
        self.assertEqual(str(ak.to_numpy(result["event"]).dtype), "uint64")
        # Physics-object field still first (downstream selection code relies on this)
        self.assertEqual(result.fields[0], "Electrons")

    def test_missing_event_id_branch_raises(self):
        """Unchanged behaviour: if run/luminosityBlock/event aren't all
        readable, parsing must raise rather than silently continue."""
        tree = _make_cms_tree()
        del tree._data["event"]  # simulate a file missing one id branch
        root = FakeRoot(Events=tree)
        with self.assertRaises(ValueError) as ctx:
            FileParser._parse_opened_file(
                root, ["Events"], "cms-nanoaod", 40_000, "fake.root", False, None,
            )
        self.assertIn("EventIds", str(ctx.exception))
        self.assertIn("event", str(ctx.exception))


class SecondScalarGroupTests(unittest.TestCase):
    """Test 2: a synthetic extra scalar group."""

    def test_round_trips_through_extraction_gate_and_reattachment(self):
        extra = {
            "myBool": np.array([True, False]),
            "myFloat": np.array([1.5, 2.5], dtype=np.float32),
        }
        tree = _make_cms_tree(extra_branches=extra)
        root = FakeRoot(Events=tree)
        result = FileParser._parse_opened_file(
            root, ["Events"], "cms-nanoaod", 40_000, "fake.root", False, None,
            extra_scalar_branches={"Demo": ["myBool", "myFloat"]},
        )
        self.assertIn("myBool", result.fields)
        self.assertIn("myFloat", result.fields)
        self.assertEqual(ak.to_list(result["myBool"]), [True, False])
        self.assertEqual(ak.to_list(result["myFloat"]), [1.5, 2.5])
        self.assertEqual(str(ak.to_numpy(result["myFloat"]).dtype), "float32")
        # Still get the built-in group too -- the two coexist.
        self.assertEqual(ak.to_list(result["run"]), [1, 2])

    def test_missing_branch_in_one_file_raises_informatively(self):
        """One 'file' has both extra branches; another is missing one of
        them. The mechanism must raise, not silently drop or pad -- the
        chosen behaviour (see FileParser._parse_opened_file), matching the
        existing EventIds precedent rather than silently continuing with a
        different field set per file (which domain.events._concatenate_events'
        union-of-fields logic cannot safely pad for a *scalar* field -- it
        is designed for jagged particle collections, see its docstring)."""
        good_tree = _make_cms_tree(extra_branches={
            "myBool": np.array([True, False]),
            "myFloat": np.array([1.5, 2.5], dtype=np.float32),
        })
        good_result = FileParser._parse_opened_file(
            FakeRoot(Events=good_tree), ["Events"], "cms-nanoaod", 40_000,
            "good.root", False, None,
            extra_scalar_branches={"Demo": ["myBool", "myFloat"]},
        )
        self.assertIn("myFloat", good_result.fields)

        bad_tree = _make_cms_tree(extra_branches={
            "myBool": np.array([True, False]),
            # myFloat deliberately absent
        })
        with self.assertRaises(ValueError) as ctx:
            FileParser._parse_opened_file(
                FakeRoot(Events=bad_tree), ["Events"], "cms-nanoaod", 40_000,
                "bad.root", False, None,
                extra_scalar_branches={"Demo": ["myBool", "myFloat"]},
            )
        self.assertIn("Demo", str(ctx.exception))
        self.assertIn("myFloat", str(ctx.exception))

    def test_multi_file_concatenation_preserves_scalar_group(self):
        """Two per-file results (both complete -- see the raise-on-missing
        test above for why a partial one never reaches this stage) combine
        cleanly through the same union-of-fields concatenation used for a
        real multi-file chunk."""
        extra_a = {"myBool": np.array([True]), "myFloat": np.array([1.5], dtype=np.float32)}
        extra_b = {"myBool": np.array([False]), "myFloat": np.array([2.5], dtype=np.float32)}
        result_a = FileParser._parse_opened_file(
            FakeRoot(Events=_make_cms_tree(extra_branches=extra_a, n_events=1)),
            ["Events"], "cms-nanoaod", 40_000, "a.root", False, None,
            extra_scalar_branches={"Demo": ["myBool", "myFloat"]},
        )
        result_b = FileParser._parse_opened_file(
            FakeRoot(Events=_make_cms_tree(extra_branches=extra_b, n_events=1)),
            ["Events"], "cms-nanoaod", 40_000, "b.root", False, None,
            extra_scalar_branches={"Demo": ["myBool", "myFloat"]},
        )
        combined = _concatenate_events([result_a, result_b])
        self.assertEqual(ak.to_list(combined["myBool"]), [True, False])
        self.assertEqual(ak.to_list(combined["myFloat"]), [1.5, 2.5])
        self.assertEqual(ak.to_list(combined["run"]), [1, 1])


class CollisionTests(unittest.TestCase):
    """Test 3: name-collision errors."""

    def test_group_name_colliding_with_object_collection_raises(self):
        with self.assertRaises(ValueError) as ctx:
            FileParser._resolve_scalar_groups(
                "cms-nanoaod", {"Electrons": ["someBranch"]},
            )
        self.assertIn("Electrons", str(ctx.exception))

    def test_branch_name_colliding_across_groups_raises(self):
        # "run" is already claimed by the built-in EventIds group.
        with self.assertRaises(ValueError) as ctx:
            FileParser._resolve_scalar_groups(
                "cms-nanoaod", {"MyGroup": ["run"]},
            )
        self.assertIn("run", str(ctx.exception))
        self.assertIn("EventIds", str(ctx.exception))
        self.assertIn("MyGroup", str(ctx.exception))

    def test_branch_name_colliding_with_direct_objects_raises(self):
        with self.assertRaises(ValueError) as ctx:
            FileParser._resolve_scalar_groups(
                "cms-nanoaod", {"MyGroup": ["source_record"]},
            )
        self.assertIn("source_record", str(ctx.exception))


class DefaultBehaviourUnchangedTests(unittest.TestCase):
    """Test 4: extra_scalar_branches absent -> identical output to today."""

    def test_no_extra_fields_when_key_absent(self):
        tree = _make_cms_tree()
        no_arg_result = FileParser._parse_opened_file(
            FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "fake.root", False, None,
        )
        tree2 = _make_cms_tree()
        none_result = FileParser._parse_opened_file(
            FakeRoot(Events=tree2), ["Events"], "cms-nanoaod", 40_000, "fake.root", False, None,
            extra_scalar_branches=None,
        )
        tree3 = _make_cms_tree()
        empty_result = FileParser._parse_opened_file(
            FakeRoot(Events=tree3), ["Events"], "cms-nanoaod", 40_000, "fake.root", False, None,
            extra_scalar_branches={},
        )
        expected_fields = {"Electrons", "run", "luminosityBlock", "event"}
        self.assertEqual(set(no_arg_result.fields), expected_fields)
        self.assertEqual(set(none_result.fields), expected_fields)
        self.assertEqual(set(empty_result.fields), expected_fields)

    def test_scalar_branch_groups_empty_for_atlas_schema(self):
        """ATLAS schemas declare no scalar groups at all -- schema-agnostic,
        no CMS-specific special case."""
        self.assertEqual(schemas.get_scalar_branch_groups("2024r-pp"), {})
        self.assertEqual(
            FileParser._resolve_scalar_groups("2024r-pp", None), {}
        )


class _CappedTree:
    """Wraps a real uproot tree, capping ``num_entries`` and every
    ``arrays()`` call to at most ``max_entries``.

    ``FileParser.parse_file`` has no "max events" parameter -- it always
    reads an entire file in ``batch_size``-sized chunks (``batch_size``
    only controls chunk size, not a total cap). This wrapper is what keeps
    this demo's real, remote read within the task's 2,000-event budget
    while still exercising the real parsing code path (schema resolution,
    the accessibility gate, batching, the scalar-group mechanism) against
    genuine file data -- rather than skipping straight past
    ``FileParser.parse_file`` for a lighter but less representative test.
    """

    def __init__(self, real_tree, max_entries: int):
        self._real = real_tree
        self.num_entries = min(real_tree.num_entries, max_entries)

    def keys(self):
        return self._real.keys()

    def arrays(self, branches, entry_start, entry_stop, library):
        capped_stop = min(entry_stop, self.num_entries)
        return self._real.arrays(
            branches, entry_start=entry_start, entry_stop=capped_stop, library=library
        )


@unittest.skipUnless(
    os.environ.get("RUN_NETWORK_TESTS") == "1",
    "requires network access to opendata.cern.ch; set RUN_NETWORK_TESTS=1 to run",
)
class RealFileDemoTests(unittest.TestCase):
    """Test 5: real-file demo, not part of any default schema/config --
    proves the mechanism against a genuine NanoAOD file. Two thousand
    events from one Run2016G DoubleEG file, over HTTPS (no XRootD client
    needed/installed on this machine)."""

    URL = (
        "https://opendata.cern.ch/eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/"
        "UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root"
    )
    TRIGGER = "HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"
    MAX_EVENTS = 2_000

    def test_two_real_scalar_branches_from_one_file(self):
        import uproot

        real_file = uproot.open(self.URL)
        capped_tree = _CappedTree(real_file["Events"], self.MAX_EVENTS)
        root = FakeRoot(Events=capped_tree)

        result = FileParser._parse_opened_file(
            root, ["Events"], "cms-nanoaod", self.MAX_EVENTS, self.URL, False, None,
            extra_scalar_branches={"CMSHggDemo": [self.TRIGGER, "PV_npvsGood"]},
        )
        self.assertIsNotNone(result)
        self.assertLessEqual(len(result), self.MAX_EVENTS)
        self.assertIn(self.TRIGGER, result.fields)
        self.assertIn("PV_npvsGood", result.fields)
        # dtypes
        self.assertEqual(str(ak.to_numpy(result[self.TRIGGER]).dtype), "bool")
        self.assertTrue(str(ak.to_numpy(result["PV_npvsGood"]).dtype).startswith("int"))
        # Trigger pass fraction, consistent with the earlier design check's
        # ~25% of raw DoubleEG events (studies/hgg_cms/INVENTORY.md C.2,
        # studies/hgg_cms/physics_checks/check_c_results.json).
        frac = float(np.mean(ak.to_numpy(result[self.TRIGGER])))
        print(f"\n[demo] {self.TRIGGER} pass fraction on {len(result)} events: {frac:.3f}")
        self.assertGreater(frac, 0.10)
        self.assertLess(frac, 0.45)


if __name__ == "__main__":
    unittest.main()
