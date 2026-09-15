"""
Implementation task 3 (studies/hgg_cms/DESIGN_SELECTION.md, Section 8 task
3): the optional HLT trigger requirement, and the loud-failure behaviour
for a required scalar branch missing from an input file.

Covers:
 1. Config validation (mode, empty list, bad types).
 2. Filter logic on synthetic events: any/all with 1 and 2 paths, all-fail,
    all-pass, dtype handling.
 3. A missing required branch in one of several files -> the specific
    error, with file and branch listed, and the run stops; a network-style
    parse error -> today's behaviour unchanged.
 4. Config key absent -> identical output; duplicate listing in
    extra_scalar_branches -> no collision error.
 5. Ordering with the validated-runs filter: statistics reflect
    validated-runs first, then trigger.
 6. A real-data cross-check against a direct uproot read of the HLT branch
    (network-marked, skipped offline).
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import awkward as ak
import numpy as np

from domain.config import ParsingConfig
from services.parsing.file_parser import FileParser, RequiredScalarBranchMissingError
from services.parsing.threaded_processor import ThreadedFileProcessor
from services.parsing.trigger_requirements import (
    apply_trigger_requirement,
    trigger_group_branches,
    validate_trigger_requirements,
)
from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter
import services.parsing.file_parser as file_parser_module


def _events(**fields) -> ak.Array:
    return ak.zip(fields, depth_limit=1)


class ConfigValidationTests(unittest.TestCase):
    """Test 1: config validation (mode, empty list, bad types)."""

    def test_default_is_none(self):
        cfg = ParsingConfig(output_path="./o", file_urls_path="./f", jobs_logs_path="./l")
        self.assertIsNone(cfg.trigger_requirements)

    def test_valid_config_accepted(self):
        cfg = ParsingConfig(
            output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
            trigger_requirements={"mode": "any", "paths": ["HLT_X"]},
        )
        self.assertEqual(cfg.trigger_requirements["mode"], "any")

    def test_default_mode_omitted_is_fine_at_config_level(self):
        # mode is optional in the dict itself (defaults to "any" when used);
        # ParsingConfig only rejects an explicitly *invalid* mode.
        cfg = ParsingConfig(
            output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
            trigger_requirements={"paths": ["HLT_X"]},
        )
        self.assertEqual(cfg.trigger_requirements["paths"], ["HLT_X"])

    def test_not_a_dict_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                trigger_requirements=["HLT_X"],
            )

    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                trigger_requirements={"mode": "every", "paths": ["HLT_X"]},
            )
        self.assertIn("mode", str(ctx.exception))

    def test_empty_paths_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                trigger_requirements={"mode": "any", "paths": []},
            )

    def test_missing_paths_key_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                trigger_requirements={"mode": "any"},
            )

    def test_non_string_path_entry_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                trigger_requirements={"mode": "any", "paths": ["HLT_X", 123]},
            )

    def test_paths_not_a_list_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                trigger_requirements={"mode": "any", "paths": "HLT_X"},
            )

    def test_validate_helper_matches_config_validation(self):
        # Used for the per-record selection_by_record override, which is a
        # freeform dict not covered by ParsingConfig's own validation.
        validate_trigger_requirements({"mode": "all", "paths": ["HLT_X", "HLT_Y"]})
        with self.assertRaises(ValueError):
            validate_trigger_requirements({"mode": "all", "paths": []})


class FilterLogicTests(unittest.TestCase):
    """Test 2: filter logic on synthetic events."""

    def test_any_mode_one_path(self):
        events = _events(HLT_X=np.array([True, False, True]))
        filtered, stats = apply_trigger_requirement(events, {"mode": "any", "paths": ["HLT_X"]})
        self.assertEqual(len(filtered), 2)
        self.assertEqual(stats["n_before"], 3)
        self.assertEqual(stats["n_after"], 2)
        self.assertEqual(stats["per_path"]["HLT_X"], 2)

    def test_all_mode_one_path_same_as_any_for_single_path(self):
        events = _events(HLT_X=np.array([True, False, True]))
        filtered_any, _ = apply_trigger_requirement(events, {"mode": "any", "paths": ["HLT_X"]})
        filtered_all, _ = apply_trigger_requirement(events, {"mode": "all", "paths": ["HLT_X"]})
        self.assertEqual(ak.to_list(filtered_any["HLT_X"]), ak.to_list(filtered_all["HLT_X"]))

    def test_any_mode_two_paths_union(self):
        events = _events(
            HLT_X=np.array([True, False, False, False]),
            HLT_Y=np.array([False, True, False, False]),
        )
        filtered, stats = apply_trigger_requirement(
            events, {"mode": "any", "paths": ["HLT_X", "HLT_Y"]}
        )
        self.assertEqual(len(filtered), 2)
        self.assertEqual(stats["per_path"], {"HLT_X": 1, "HLT_Y": 1})

    def test_all_mode_two_paths_intersection(self):
        events = _events(
            HLT_X=np.array([True, True, False, True]),
            HLT_Y=np.array([True, False, False, True]),
        )
        filtered, stats = apply_trigger_requirement(
            events, {"mode": "all", "paths": ["HLT_X", "HLT_Y"]}
        )
        self.assertEqual(len(filtered), 2)  # events 0 and 3
        self.assertEqual(stats["n_after"], 2)

    def test_all_fail(self):
        events = _events(HLT_X=np.array([False, False]))
        filtered, stats = apply_trigger_requirement(events, {"mode": "any", "paths": ["HLT_X"]})
        self.assertEqual(len(filtered), 0)
        self.assertEqual(stats["n_after"], 0)

    def test_all_pass(self):
        events = _events(HLT_X=np.array([True, True, True]))
        filtered, stats = apply_trigger_requirement(events, {"mode": "any", "paths": ["HLT_X"]})
        self.assertEqual(len(filtered), 3)
        self.assertEqual(stats["n_after"], 3)

    def test_dtype_handling_native_bool_and_defensive_int_cast(self):
        # NanoAOD stores these as genuine booleans (confirmed on a real file
        # in tests/test_scalar_event_fields.py's RealFileDemoTests, and again
        # in this file's own real-data cross-check below); this also checks
        # the defensive astype(bool) handles an integer 0/1 array the same way.
        bool_events = _events(HLT_X=np.array([True, False], dtype=bool))
        int_events = _events(HLT_X=np.array([1, 0], dtype=np.int32))
        _, bool_stats = apply_trigger_requirement(bool_events, {"mode": "any", "paths": ["HLT_X"]})
        _, int_stats = apply_trigger_requirement(int_events, {"mode": "any", "paths": ["HLT_X"]})
        self.assertEqual(bool_stats["per_path"], int_stats["per_path"])

    def test_missing_trigger_branch_raises(self):
        events = _events(SomethingElse=np.array([True]))
        with self.assertRaises(ValueError) as ctx:
            apply_trigger_requirement(events, {"mode": "any", "paths": ["HLT_X"]})
        self.assertIn("HLT_X", str(ctx.exception))

    def test_trigger_group_branches_deduplicates(self):
        self.assertEqual(
            trigger_group_branches({"paths": ["HLT_X", "HLT_Y", "HLT_X"]}),
            ["HLT_X", "HLT_Y"],
        )


class _FakeTree:
    """Minimal stand-in for an uproot TTree, keyed on branch name."""

    def __init__(self, data: dict, num_entries: int):
        self._data = data
        self.num_entries = num_entries

    def keys(self):
        return list(self._data.keys())

    def arrays(self, branches, entry_start, entry_stop, library):
        if isinstance(branches, str):
            branches = [branches]
        missing = [b for b in branches if b not in self._data]
        if missing:
            raise KeyError(f"no such branch(es): {missing}")
        return ak.Array({b: self._data[b][entry_start:entry_stop] for b in branches})


class _FakeRoot(dict):
    def keys(self):
        return ["Events;1"]


class _CtxRoot:
    """Wraps a fake root object so it satisfies FileParser.parse_file's
    ``with open_root_file(file_path) as root_file:`` usage."""

    def __init__(self, root):
        self._root = root

    def __enter__(self):
        return self._root

    def __exit__(self, *exc_info):
        return False


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
    return _FakeTree(data, n_events)


class MissingBranchLoudFailureTests(unittest.TestCase):
    """Test 3: missing required branch -> specific error, run stops;
    other parse failures -> unchanged behaviour."""

    def test_parse_opened_file_raises_specific_type_for_missing_trigger_branch(self):
        tree = _make_cms_tree()  # no HLT_X branch
        root = _FakeRoot(Events=tree)
        with self.assertRaises(RequiredScalarBranchMissingError) as ctx:
            FileParser._parse_opened_file(
                root, ["Events"], "cms-nanoaod", 40_000, "bad.root", False, None,
                extra_scalar_branches={"Trigger": ["HLT_X"]},
            )
        self.assertIn("bad.root", str(ctx.exception))
        self.assertIn("HLT_X", str(ctx.exception))
        self.assertIn("Trigger", str(ctx.exception))
        self.assertEqual(ctx.exception.failures, [("bad.root", "Trigger", ["HLT_X"])])

    def test_parse_file_reraises_missing_branch_error_not_swallowed(self):
        """FileParser.parse_file's own broad except must NOT swallow this,
        unlike an ordinary parse failure (see the next test)."""
        tree = _make_cms_tree()
        root = _FakeRoot(Events=tree)
        with patch.object(file_parser_module, "open_root_file", return_value=_CtxRoot(root)):
            with self.assertRaises(RequiredScalarBranchMissingError):
                FileParser.parse_file(
                    "bad.root", ["Events"], "cms-nanoaod",
                    extra_scalar_branches={"Trigger": ["HLT_X"]},
                )

    def test_parse_file_swallows_generic_exception_as_before(self):
        """A network-style error keeps today's exact behaviour: logged,
        parse_file returns None, no exception propagates."""
        with patch.object(
            file_parser_module, "open_root_file", side_effect=ConnectionError("timeout")
        ):
            result = FileParser.parse_file("bad.root", ["Events"], "cms-nanoaod")
        self.assertIsNone(result)

    def test_threaded_processor_aborts_the_run_on_one_bad_file(self):
        """One file among several is missing a required branch -> the whole
        process_files() run raises (rather than silently yielding batches
        for only the good files and finishing 'successfully')."""

        class _StubParser:
            def parse_file(self, file_path, **kwargs):
                if file_path == "bad.root":
                    raise RequiredScalarBranchMissingError(
                        [(file_path, "Trigger", ["HLT_X"])]
                    )
                return ak.Array({"run": [1, 2]})

        processor = ThreadedFileProcessor(_StubParser(), 1, show_progress=False)
        with self.assertRaises(RequiredScalarBranchMissingError) as ctx:
            list(processor.process_files(
                ["good.root", "bad.root"], ["Events"], "cms-nanoaod",
            ))
        self.assertIn("bad.root", str(ctx.exception))
        self.assertIn("HLT_X", str(ctx.exception))

    def test_threaded_processor_aggregates_multiple_bad_files_in_one_error(self):
        class _StubParser:
            def parse_file(self, file_path, **kwargs):
                if file_path.startswith("bad"):
                    return_group = "Trigger"
                    raise RequiredScalarBranchMissingError(
                        [(file_path, return_group, ["HLT_X"])]
                    )
                return ak.Array({"run": [1]})

        processor = ThreadedFileProcessor(_StubParser(), 1, show_progress=False)
        with self.assertRaises(RequiredScalarBranchMissingError) as ctx:
            list(processor.process_files(
                ["bad1.root", "good.root", "bad2.root"], ["Events"], "cms-nanoaod",
            ))
        self.assertEqual(len(ctx.exception.failures), 2)
        self.assertIn("bad1.root", str(ctx.exception))
        self.assertIn("bad2.root", str(ctx.exception))

    def test_threaded_processor_keeps_processing_good_files_before_aborting(self):
        """Behind the scenes, other files' batches were produced -- the
        method just never lets the generator finish 'clean'. We assert the
        raise happens only after exhausting the generator (StopIteration
        would otherwise be silently swallowed by list())."""

        class _StubParser:
            def parse_file(self, file_path, **kwargs):
                if file_path == "bad.root":
                    raise RequiredScalarBranchMissingError(
                        [(file_path, "Trigger", ["HLT_X"])]
                    )
                return ak.Array({"run": [1]})

        processor = ThreadedFileProcessor(_StubParser(), 2, show_progress=False)
        yielded = []
        gen = processor.process_files(["good1.root", "bad.root", "good2.root"], ["Events"], "cms-nanoaod")
        with self.assertRaises(RequiredScalarBranchMissingError):
            for batch in gen:
                yielded.append(batch)
        # Both good files' batches were produced before the aggregate error.
        self.assertEqual(len(yielded), 2)

    def test_network_style_error_in_threaded_processor_keeps_todays_behaviour(self):
        class _StubParser:
            def parse_file(self, file_path, **kwargs):
                if file_path == "bad.root":
                    raise ConnectionError("timeout")
                return ak.Array({"run": [1]})

        processor = ThreadedFileProcessor(_StubParser(), 1, show_progress=False)
        failures = []
        batches = list(processor.process_files(
            ["good.root", "bad.root"], ["Events"], "cms-nanoaod",
            on_error=lambda url, err: failures.append((url, err)),
        ))
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(failures), 1)
        self.assertNotIsInstance(failures[0][1], RequiredScalarBranchMissingError)


class DefaultBehaviourAndCollisionTests(unittest.TestCase):
    """Test 4: key absent -> identical output; duplicate listing in
    extra_scalar_branches -> no collision error."""

    def test_no_trigger_group_when_key_absent(self):
        tree = _make_cms_tree()
        result = FileParser._parse_opened_file(
            _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "fake.root", False, None,
        )
        self.assertEqual(set(result.fields), {"Electrons", "run", "luminosityBlock", "event"})

    def test_duplicate_listing_in_extra_scalar_branches_no_collision(self):
        """The same trigger path requested both via the 'Trigger' group
        (as parsing_handler.py does automatically) and by the caller's own
        extra_scalar_branches['Trigger'] entry (e.g. a user who also listed
        it manually) must not raise -- same group name, so the merge just
        deduplicates."""
        tree = _make_cms_tree(extra_branches={"HLT_X": np.array([True, False])})
        result = FileParser._parse_opened_file(
            _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "fake.root", False, None,
            extra_scalar_branches={"Trigger": ["HLT_X", "HLT_X"]},
        )
        self.assertEqual(ak.to_list(result["HLT_X"]), [True, False])


class OrderingWithValidatedRunsTests(unittest.TestCase):
    """Test 5: with both filters enabled, statistics reflect validated-runs
    first, then trigger -- matching orchestration/handlers/parsing_handler.py's
    application order."""

    def test_uncertified_run_never_reaches_trigger_stage(self):
        import json
        import tempfile

        doc = {"100": [[1, 10]]}
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(doc, f)
            vrf = ValidatedRunsFilter(path)

            events = _events(
                run=np.array([100, 999], dtype=np.uint32),
                luminosityBlock=np.array([5, 5], dtype=np.uint32),
                HLT_X=np.array([True, True]),
            )
            vr_filtered, vr_stats = apply_validated_runs_filter(events, vrf)
            self.assertEqual(vr_stats["n_after"], 1)

            tr_filtered, tr_stats = apply_trigger_requirement(
                vr_filtered, {"mode": "any", "paths": ["HLT_X"]}
            )
            # Only the certified (run=100) event ever reaches the trigger
            # stage -- run 999 was already dropped, so it can't inflate
            # HLT_X's pass count even though its own HLT_X bit was True.
            self.assertEqual(tr_stats["n_before"], 1)
            self.assertEqual(tr_stats["per_path"]["HLT_X"], 1)
            self.assertEqual(len(tr_filtered), 1)
        finally:
            os.remove(path)


@unittest.skipUnless(
    os.environ.get("RUN_NETWORK_TESTS") == "1",
    "requires network access to opendata.cern.ch; set RUN_NETWORK_TESTS=1 to run",
)
class RealDataCrossCheckTests(unittest.TestCase):
    """Test 6: real DoubleEG (data) and real ggH (simulation) files vs. a
    direct uproot read of the HLT branch."""

    TRIGGER = "HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"
    MAX_EVENTS = 2000

    DATA_FILES = {
        "Run2016G": (
            "https://opendata.cern.ch/eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/"
            "UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root"
        ),
        "Run2016H": (
            "https://opendata.cern.ch/eos/opendata/cms/Run2016H/DoubleEG/NANOAOD/"
            "UL2016_MiniAODv2_NanoAODv9-v1/100000/2AD46B56-E1CA-CD44-B30D-C57FE1C35D15.root"
        ),
    }

    def _check_data_file(self, era, url):
        import uproot

        f = uproot.open(url)
        t = f["Events"]
        arr = t.arrays([self.TRIGGER], entry_stop=self.MAX_EVENTS, library="np")
        raw = arr[self.TRIGGER]
        self.assertEqual(str(raw.dtype), "bool")

        events = _events(**{self.TRIGGER: raw})
        filtered, stats = apply_trigger_requirement(
            events, {"mode": "any", "paths": [self.TRIGGER]}
        )
        reference_kept = int(raw.sum())
        self.assertEqual(stats["n_after"], reference_kept)
        self.assertTrue(np.array_equal(np.asarray(filtered[self.TRIGGER]), raw[raw]))

        frac = stats["n_after"] / stats["n_before"]
        print(f"\n[trigger cross-check] {era} data: kept {stats['n_after']}/{stats['n_before']} "
              f"({frac:.1%}) HLT-pass fraction -- agrees 100% with a direct uproot read")
        return frac

    def test_run2016g_data_matches_direct_read(self):
        frac = self._check_data_file("Run2016G", self.DATA_FILES["Run2016G"])
        # Design doc's own order-of-magnitude reference: ~24.6% on DoubleEG
        # (studies/hgg_cms/INVENTORY.md A.4 / C.2).
        self.assertGreater(frac, 0.05)
        self.assertLess(frac, 0.60)

    def test_run2016h_data_matches_direct_read(self):
        frac = self._check_data_file("Run2016H", self.DATA_FILES["Run2016H"])
        self.assertGreater(frac, 0.05)
        self.assertLess(frac, 0.60)

    def test_ggh_signal_matches_direct_read(self):
        import uproot

        # ggH postVFP signal, record 37350 (studies/hgg_cms/records.json,
        # study/hgg-cms-inventory branch) -- not registered in
        # RECORD_ID_TO_SCHEMA (out of scope for this task to add), so this
        # reads the raw branch directly with uproot, exactly like the data
        # cross-check above, rather than going through FileParser/schema
        # resolution.
        # Resolved via the portal's own file list (kept local to this one
        # test, to avoid a network call in tests that don't need it, and to
        # avoid hardcoding a specific file name).
        import requests

        r = requests.get(
            "https://opendata.cern.ch/api/records/37350", headers={"Accept": "application/json"}
        )
        r.raise_for_status()
        md = r.json()["metadata"]
        file_url = None
        for grp in md.get("_file_indices", []):
            for f in grp["files"]:
                file_url = f["uri"].replace(
                    "root://eospublic.cern.ch//eos/opendata/",
                    "https://opendata.cern.ch/eos/opendata/",
                )
                break
            if file_url:
                break
        self.assertIsNotNone(file_url, "could not resolve a ggH file URL from record 37350")

        f = uproot.open(file_url)
        t = f["Events"]
        raw = t.arrays([self.TRIGGER], entry_stop=self.MAX_EVENTS, library="np")[self.TRIGGER]
        self.assertEqual(str(raw.dtype), "bool")

        events = _events(**{self.TRIGGER: raw})
        filtered, stats = apply_trigger_requirement(
            events, {"mode": "any", "paths": [self.TRIGGER]}
        )
        self.assertEqual(stats["n_after"], int(raw.sum()))
        frac = stats["n_after"] / stats["n_before"]
        print(f"\n[trigger cross-check] ggH signal: kept {stats['n_after']}/{stats['n_before']} "
              f"({frac:.1%}) HLT-pass fraction -- agrees 100% with a direct uproot read")


if __name__ == "__main__":
    unittest.main()
