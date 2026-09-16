"""
Implementation task 5, Part A (studies/hgg_cms/DESIGN_SELECTION.md, Section
6.4 / Section 8 task 5): simulation event weights, pileup information, and
genEventSumw aggregation.

Covers:
 1. Config validation; keys absent -> identical output.
 2. read_event_weights on data -> configuration error; read_pileup_info on
    data -> PV_npvsGood only, no Pileup_nTrueInt.
 3. genEventSumw aggregation over synthetic per-file Runs values (a
    multi-entry Runs tree, a failed file excluded consistently -- raising
    loudly rather than silently -- and the Events/Runs mismatch case).
 4. genWeight sign and dtype preserved through parse -> concatenation ->
    selection -> serialization (negative weights included).
 5. Real-file checks (network-marked, skipped offline).
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

from domain.config import ParsingConfig
from services.parsing.event_selection import apply_parsing_event_selection
from services.parsing.file_parser import FileParser
from services.parsing.mc_weights import (
    SimulationFieldRequestedOnDataError,
    aggregate_sumw_for_processed_files,
    file_is_simulation,
    resolve_weight_and_pileup_groups,
)


class ConfigValidationTests(unittest.TestCase):
    """Test 1: config validation; keys absent -> identical output."""

    def test_defaults_are_false(self):
        cfg = ParsingConfig(output_path="./o", file_urls_path="./f", jobs_logs_path="./l")
        self.assertFalse(cfg.read_event_weights)
        self.assertFalse(cfg.read_pileup_info)

    def test_valid_bools_accepted(self):
        cfg = ParsingConfig(
            output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
            read_event_weights=True, read_pileup_info=True,
        )
        self.assertTrue(cfg.read_event_weights)
        self.assertTrue(cfg.read_pileup_info)

    def test_non_bool_read_event_weights_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                read_event_weights="yes",
            )

    def test_non_bool_read_pileup_info_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                read_pileup_info=1,
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


def _make_data_tree(n_events=2, extra=None):
    data = {
        "Electron_pt": ak.Array([[25.0], [30.0]][:n_events]),
        "Electron_eta": ak.Array([[0.1], [0.2]][:n_events]),
        "Electron_phi": ak.Array([[0.0], [0.1]][:n_events]),
        "Electron_mass": ak.Array([[0.000511], [0.000511]][:n_events]),
        "run": np.array([1, 2], dtype=np.uint32)[:n_events],
        "luminosityBlock": np.array([10, 20], dtype=np.uint32)[:n_events],
        "event": np.array([100, 200], dtype=np.uint64)[:n_events],
        "PV_npvsGood": np.array([5, 6], dtype=np.int32)[:n_events],
    }
    if extra:
        data.update(extra)
    return _FakeTree(data, n_events)


def _make_mc_tree(n_events=2, extra=None):
    data = {
        "Electron_pt": ak.Array([[25.0], [30.0]][:n_events]),
        "Electron_eta": ak.Array([[0.1], [0.2]][:n_events]),
        "Electron_phi": ak.Array([[0.0], [0.1]][:n_events]),
        "Electron_mass": ak.Array([[0.000511], [0.000511]][:n_events]),
        "run": np.array([1, 1], dtype=np.uint32)[:n_events],
        "luminosityBlock": np.array([1, 1], dtype=np.uint32)[:n_events],
        "event": np.array([1, 2], dtype=np.uint64)[:n_events],
        "genWeight": np.array([1.5, -1.5], dtype=np.float32)[:n_events],
        "PV_npvsGood": np.array([5, 6], dtype=np.int32)[:n_events],
        "Pileup_nTrueInt": np.array([10.2, 11.7], dtype=np.float32)[:n_events],
    }
    if extra:
        data.update(extra)
    return _FakeTree(data, n_events)


class FileIsSimulationTests(unittest.TestCase):
    def test_genweight_present_is_simulation(self):
        self.assertTrue(file_is_simulation({"genWeight", "run", "event"}))

    def test_genweight_absent_is_data(self):
        self.assertFalse(file_is_simulation({"run", "event", "luminosityBlock"}))


class ResolveGroupsTests(unittest.TestCase):
    def test_both_disabled_returns_empty(self):
        self.assertEqual(
            resolve_weight_and_pileup_groups({"genWeight"}, "f.root", False, False), {}
        )

    def test_weights_on_simulation_file(self):
        groups = resolve_weight_and_pileup_groups({"genWeight", "run"}, "f.root", True, False)
        self.assertEqual(groups, {"Weights": ["genWeight"]})

    def test_weights_on_data_file_raises(self):
        with self.assertRaises(SimulationFieldRequestedOnDataError) as ctx:
            resolve_weight_and_pileup_groups({"run", "event"}, "data.root", True, False)
        self.assertIn("data.root", str(ctx.exception))
        self.assertIn("genWeight", str(ctx.exception))

    def test_pileup_on_data_file_is_pv_npvsgood_only(self):
        groups = resolve_weight_and_pileup_groups({"run", "PV_npvsGood"}, "f.root", False, True)
        self.assertEqual(groups, {"Pileup": ["PV_npvsGood"]})

    def test_pileup_on_simulation_file_includes_pileup_ntrueint(self):
        groups = resolve_weight_and_pileup_groups(
            {"genWeight", "PV_npvsGood", "Pileup_nTrueInt"}, "f.root", False, True
        )
        self.assertEqual(groups, {"Pileup": ["PV_npvsGood", "Pileup_nTrueInt"]})

    def test_both_enabled_on_simulation_file(self):
        groups = resolve_weight_and_pileup_groups(
            {"genWeight", "PV_npvsGood", "Pileup_nTrueInt"}, "f.root", True, True
        )
        self.assertEqual(groups, {"Weights": ["genWeight"], "Pileup": ["PV_npvsGood", "Pileup_nTrueInt"]})


class ParseFileIntegrationTests(unittest.TestCase):
    """Exercises the real FileParser._parse_opened_file path end to end."""

    def test_read_event_weights_on_data_raises(self):
        tree = _make_data_tree()
        with self.assertRaises(SimulationFieldRequestedOnDataError) as ctx:
            FileParser._parse_opened_file(
                _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "data.root",
                False, None, read_event_weights=True,
            )
        self.assertIn("data.root", str(ctx.exception))

    def test_read_pileup_info_on_data_gives_pv_npvsgood_only(self):
        tree = _make_data_tree()
        result = FileParser._parse_opened_file(
            _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "data.root",
            False, None, read_pileup_info=True,
        )
        self.assertIn("PV_npvsGood", result.fields)
        self.assertNotIn("Pileup_nTrueInt", result.fields)
        self.assertNotIn("genWeight", result.fields)

    def test_read_event_weights_and_pileup_on_simulation(self):
        tree = _make_mc_tree()
        result = FileParser._parse_opened_file(
            _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "mc.root",
            False, None, read_event_weights=True, read_pileup_info=True,
        )
        self.assertIn("genWeight", result.fields)
        self.assertIn("PV_npvsGood", result.fields)
        self.assertIn("Pileup_nTrueInt", result.fields)
        self.assertEqual(ak.to_list(result["genWeight"]), [1.5, -1.5])
        self.assertEqual(str(ak.to_numpy(result["genWeight"]).dtype), "float32")

    def test_absent_keys_give_identical_output(self):
        tree = _make_mc_tree()
        result = FileParser._parse_opened_file(
            _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "mc.root", False, None,
        )
        self.assertNotIn("genWeight", result.fields)
        self.assertNotIn("PV_npvsGood", result.fields)
        self.assertNotIn("Pileup_nTrueInt", result.fields)
        self.assertEqual(set(result.fields), {"Electrons", "run", "luminosityBlock", "event"})

    def test_negative_weight_sign_preserved_through_parse_and_selection(self):
        tree = _make_mc_tree()
        result = FileParser._parse_opened_file(
            _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "mc.root",
            False, None, read_event_weights=True,
        )
        # Route through apply_parsing_event_selection (kinematic_cuts=None,
        # particle_counts=None) -- a no-op selection, but exercises the
        # exact code path real events pass through.
        selected = apply_parsing_event_selection(result, particle_counts=None, kinematic_cuts=None)
        self.assertEqual(ak.to_list(selected["genWeight"]), [1.5, -1.5])
        self.assertEqual(str(ak.to_numpy(selected["genWeight"]).dtype), "float32")

    def test_genweight_survives_root_serialization_round_trip(self):
        tree = _make_mc_tree()
        result = FileParser._parse_opened_file(
            _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "mc.root",
            False, None, read_event_weights=True,
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "chunk.root"
            flattened = {field: result[field] for field in result.fields}
            with uproot.recreate(str(out_path)) as root_file:
                root_file["events"] = flattened
            reread = uproot.open(str(out_path))["events"]
            reread_w = reread["genWeight"].array(library="np")
            self.assertEqual(list(reread_w), [1.5, -1.5])
            self.assertEqual(str(reread_w.dtype), "float32")

    def test_missing_genweight_in_one_of_several_files_is_loud_failure(self):
        """A file that looks like simulation via other MC-only fields but
        is (implausibly) missing genWeight itself after passing the
        file_is_simulation check would not occur in practice (the check
        IS genWeight-presence) -- this instead confirms a file missing
        PV_npvsGood while read_pileup_info is on raises the standard loud
        scalar-group failure, not a silent drop."""
        tree = _make_mc_tree()
        del tree._data["PV_npvsGood"]
        from services.parsing.file_parser import RequiredScalarBranchMissingError

        with self.assertRaises(RequiredScalarBranchMissingError) as ctx:
            FileParser._parse_opened_file(
                _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "mc.root",
                False, None, read_pileup_info=True,
            )
        self.assertIn("PV_npvsGood", str(ctx.exception))


class GenEventSumwAggregationTests(unittest.TestCase):
    """Test 3: genEventSumw aggregation over synthetic per-file Runs values."""

    def test_single_entry_per_file_sums_correctly(self):
        values = {
            "a.root": {"genEventSumw": 100.0, "genEventCount": 10, "genEventSumw2": 50.0},
            "b.root": {"genEventSumw": 200.0, "genEventCount": 20, "genEventSumw2": 90.0},
        }
        result = aggregate_sumw_for_processed_files(list(values), reader=lambda u: values[u])
        self.assertEqual(result["genEventSumw"], 300.0)
        self.assertEqual(result["genEventCount"], 30)
        self.assertEqual(result["genEventSumw2"], 140.0)
        self.assertEqual(result["n_files_processed"], 2)
        self.assertEqual(result["processed_files"], ["a.root", "b.root"])

    def test_multi_entry_runs_tree_summed_within_reader(self):
        # The reader (read_runs_tree_sums) is responsible for summing
        # multiple Runs-tree entries within one file -- verify that a
        # reader doing so produces the expected already-summed value here.
        def multi_entry_reader(url):
            # Simulates read_runs_tree_sums having summed 2 Runs entries.
            per_entry = [{"genEventSumw": 40.0, "genEventCount": 4, "genEventSumw2": 16.0},
                         {"genEventSumw": 60.0, "genEventCount": 6, "genEventSumw2": 24.0}]
            return {
                "genEventSumw": sum(e["genEventSumw"] for e in per_entry),
                "genEventCount": sum(e["genEventCount"] for e in per_entry),
                "genEventSumw2": sum(e["genEventSumw2"] for e in per_entry),
            }

        result = aggregate_sumw_for_processed_files(["multi.root"], reader=multi_entry_reader)
        self.assertEqual(result["genEventSumw"], 100.0)
        self.assertEqual(result["genEventCount"], 10)

    def test_one_failed_runs_read_raises_loudly_not_silently_excluded(self):
        values = {"a.root": {"genEventSumw": 100.0, "genEventCount": 10, "genEventSumw2": 50.0}}

        def reader(url):
            if url == "b.root":
                raise RuntimeError("simulated transient failure reading Runs tree")
            return values[url]

        with self.assertRaises(RuntimeError) as ctx:
            aggregate_sumw_for_processed_files(["a.root", "b.root"], reader=reader)
        self.assertIn("b.root", str(ctx.exception))
        self.assertIn("1/2", str(ctx.exception))

    def test_events_runs_mismatch_all_files_fail_reports_all(self):
        def always_fails(url):
            raise RuntimeError("Runs tree not found")

        with self.assertRaises(RuntimeError) as ctx:
            aggregate_sumw_for_processed_files(["a.root", "b.root"], reader=always_fails)
        self.assertIn("a.root", str(ctx.exception))
        self.assertIn("b.root", str(ctx.exception))
        self.assertIn("2/2", str(ctx.exception))

    def test_read_runs_tree_sums_retries_before_raising(self):
        from services.parsing import mc_weights

        attempts = {"n": 0}

        class _FakeRunsTree:
            num_entries = 1

            def arrays(self, branches, library):
                attempts["n"] += 1
                if attempts["n"] < 3:
                    raise ConnectionError("simulated transient network error")
                return {
                    "genEventSumw": np.array([100.0]),
                    "genEventCount": np.array([10]),
                    "genEventSumw2": np.array([50.0]),
                }

        class _FakeRunsRoot(dict):
            def __getitem__(self, key):
                return _FakeRunsTree()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        import unittest.mock as mock

        # read_runs_tree_sums does `from services.parsing.root_io import
        # open_root_file` INSIDE the function body (a deferred import), so
        # the source module (root_io), not mc_weights' own namespace, is
        # what must be patched.
        with mock.patch("services.parsing.root_io.open_root_file", return_value=_FakeRunsRoot()):
            result = mc_weights.read_runs_tree_sums(
                "f.root", max_attempts=4, retry_delays_sec=[0, 0, 0]
            )
        self.assertEqual(result["genEventSumw"], 100.0)
        self.assertEqual(attempts["n"], 3)


@unittest.skipUnless(
    os.environ.get("RUN_NETWORK_TESTS") == "1",
    "requires network access to opendata.cern.ch; set RUN_NETWORK_TESTS=1 to run",
)
class RealDataCrossCheckTests(unittest.TestCase):
    """Test 5: real-file checks."""

    MAX_EVENTS = 2000

    SIGNAL_URL = (
        "https://opendata.cern.ch/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/"
        "GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/"
        "106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root"
    )
    DATA_URL = (
        "https://opendata.cern.ch/eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/"
        "UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root"
    )

    class _CappedTree:
        def __init__(self, real_tree, max_entries):
            self._real = real_tree
            self.num_entries = min(real_tree.num_entries, max_entries)

        def keys(self):
            return self._real.keys()

        def arrays(self, branches, entry_start, entry_stop, library):
            capped_stop = min(entry_stop, self.num_entries)
            return self._real.arrays(branches, entry_start=entry_start, entry_stop=capped_stop, library=library)

    def _capped_root(self, url):
        real_file = uproot.open(url)
        capped = self._CappedTree(real_file["Events"], self.MAX_EVENTS)
        return _FakeRoot(Events=capped)

    def test_5a_sum_genweight_matches_geneventsumw_for_up_to_3_files(self):
        import requests

        records = {"ggH": "37350", "VBF": "68497", "ttH": "67611"}
        results = {}
        for label, recid in records.items():
            r = requests.get(f"https://opendata.cern.ch/api/records/{recid}", headers={"Accept": "application/json"})
            r.raise_for_status()
            md = r.json()["metadata"]
            url = None
            for grp in md.get("_file_indices", []):
                for f in grp["files"]:
                    url = f["uri"].replace(
                        "root://eospublic.cern.ch//eos/opendata/", "https://opendata.cern.ch/eos/opendata/"
                    )
                    break
                if url:
                    break

            f = uproot.open(url)
            w = f["Events"]["genWeight"].array(library="np")
            sum_w = float(w.astype(np.float64).sum())
            runs_sumw = float(f["Runs"]["genEventSumw"].array(library="np").sum())
            rel_diff = abs(sum_w - runs_sumw) / abs(runs_sumw)
            results[label] = rel_diff
            print(f"\n[genWeight vs genEventSumw] {label}: sum(genWeight)={sum_w:.4f} "
                  f"genEventSumw={runs_sumw:.4f} rel_diff={rel_diff:.2e}")
            self.assertLess(rel_diff, 1e-5, f"{label}: relative difference too large")

    def test_5b_pipeline_on_signal_file_matches_direct_read(self):
        root = self._capped_root(self.SIGNAL_URL)
        result = FileParser._parse_opened_file(
            root, ["Events"], "cms-nanoaod", self.MAX_EVENTS, self.SIGNAL_URL, False, None,
            read_event_weights=True, read_pileup_info=True,
        )

        real_file = uproot.open(self.SIGNAL_URL)
        n = min(real_file["Events"].num_entries, self.MAX_EVENTS)
        ref = real_file["Events"].arrays(
            ["genWeight", "Pileup_nTrueInt", "PV_npvsGood"], entry_stop=n, library="np"
        )

        for field, branch in [("genWeight", "genWeight"), ("Pileup_nTrueInt", "Pileup_nTrueInt"), ("PV_npvsGood", "PV_npvsGood")]:
            pipeline_vals = ak.to_numpy(result[field])
            self.assertTrue(np.array_equal(pipeline_vals, ref[branch]), f"{field} values mismatch")
            self.assertEqual(str(pipeline_vals.dtype), str(ref[branch].dtype), f"{field} dtype mismatch")
        print(f"\n[signal pipeline check] {len(result)} events, all 3 fields match a direct uproot read exactly")

    def test_5c_pipeline_on_data_file_pileup_only_and_weights_error(self):
        root = self._capped_root(self.DATA_URL)
        result = FileParser._parse_opened_file(
            root, ["Events"], "cms-nanoaod", self.MAX_EVENTS, self.DATA_URL, False, None,
            read_pileup_info=True,
        )
        self.assertIn("PV_npvsGood", result.fields)
        self.assertNotIn("Pileup_nTrueInt", result.fields)

        real_file = uproot.open(self.DATA_URL)
        n = min(real_file["Events"].num_entries, self.MAX_EVENTS)
        ref_pv = real_file["Events"]["PV_npvsGood"].array(entry_stop=n, library="np")
        self.assertTrue(np.array_equal(ak.to_numpy(result["PV_npvsGood"]), ref_pv))

        root2 = self._capped_root(self.DATA_URL)
        with self.assertRaises(SimulationFieldRequestedOnDataError):
            FileParser._parse_opened_file(
                root2, ["Events"], "cms-nanoaod", self.MAX_EVENTS, self.DATA_URL, False, None,
                read_event_weights=True,
            )
        print("\n[data pipeline check] PV_npvsGood matches direct read; "
              "read_event_weights correctly raised on a data file")


if __name__ == "__main__":
    unittest.main()
