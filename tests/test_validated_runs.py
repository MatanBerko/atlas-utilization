"""
Implementation task 2 (studies/hgg_cms/DESIGN_SELECTION.md, Section 8 task
2): the CMS "golden JSON" validated-runs filter.

Covers:
 1. JSON parsing/validation (well-formed and malformed documents).
 2. Filtering on synthetic events: certified section, first/last section of
    a range, a section just outside a range, an uncertified run, and
    multiple runs mixed in one batch.
 3. Missing run/luminosityBlock fields -> error.
 4. The simulation guard (both detection paths) -> error.
 5. Config key absent -> no-op / identical output.
 6. A real-data cross-check against an independent reference
    implementation (network-marked, skipped offline).
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import awkward as ak
import numpy as np

from domain.config import ParsingConfig
from services.parsing.validated_runs import (
    ValidatedRunsFilter,
    apply_validated_runs_filter,
    is_simulation,
    _validate_and_parse,
)


def _write_json(obj) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return path


def _events(runs, lumis, extra: dict | None = None) -> ak.Array:
    fields = {
        "run": np.array(runs, dtype=np.uint32),
        "luminosityBlock": np.array(lumis, dtype=np.uint32),
    }
    if extra:
        fields.update(extra)
    return ak.zip(fields, depth_limit=1)


class JsonParsingTests(unittest.TestCase):
    """Test 1: JSON parsing/validation."""

    def test_string_run_keys_and_multiple_ranges(self):
        doc = {"273158": [[1, 1283]], "273425": [[62, 352], [354, 742]]}
        parsed = _validate_and_parse(json.dumps(doc), "test")
        self.assertEqual(parsed[273158], [(1, 1283)])
        self.assertEqual(parsed[273425], [(62, 352), (354, 742)])

    def test_single_section_range(self):
        doc = {"100": [[5, 5]]}
        parsed = _validate_and_parse(json.dumps(doc), "test")
        self.assertEqual(parsed[100], [(5, 5)])

    def test_not_json_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _validate_and_parse("not json at all {{{", "test")
        self.assertIn("not valid JSON", str(ctx.exception))

    def test_not_an_object_raises(self):
        with self.assertRaises(ValueError):
            _validate_and_parse(json.dumps([1, 2, 3]), "test")

    def test_non_numeric_run_key_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _validate_and_parse(json.dumps({"not_a_run": [[1, 2]]}), "test")
        self.assertIn("not_a_run", str(ctx.exception))

    def test_malformed_range_raises(self):
        with self.assertRaises(ValueError):
            _validate_and_parse(json.dumps({"100": [[1, 2, 3]]}), "test")

    def test_first_greater_than_last_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _validate_and_parse(json.dumps({"100": [[10, 5]]}), "test")
        self.assertIn("100", str(ctx.exception))

    def test_negative_bound_raises(self):
        with self.assertRaises(ValueError):
            _validate_and_parse(json.dumps({"100": [[-1, 5]]}), "test")

    def test_loader_computes_sha256_and_counts(self):
        doc = {"100": [[1, 10]], "200": [[5, 5], [20, 22]]}
        path = _write_json(doc)
        try:
            vrf = ValidatedRunsFilter(path)
            self.assertEqual(vrf.n_runs, 2)
            # run 100: 10 sections (1..10); run 200: 1 + 3 = 4 sections
            self.assertEqual(vrf.n_certified_lumisections, 14)
            self.assertEqual(len(vrf.sha256), 64)
        finally:
            os.remove(path)

    def test_missing_file_raises(self):
        with self.assertRaises(ValueError):
            ValidatedRunsFilter("no/such/file/here.json")


class FilteringTests(unittest.TestCase):
    """Test 2: filtering on synthetic events."""

    def setUp(self):
        doc = {"100": [[10, 20]], "200": [[5, 5], [30, 40]]}
        self.path = _write_json(doc)
        self.vrf = ValidatedRunsFilter(self.path)

    def tearDown(self):
        os.remove(self.path)

    def test_certified_section_kept(self):
        events = _events(runs=[100], lumis=[15])
        filtered, stats = apply_validated_runs_filter(events, self.vrf)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(stats["n_before"], 1)
        self.assertEqual(stats["n_after"], 1)

    def test_range_boundaries_inclusive(self):
        # first and last section of [10, 20] must both be kept
        events = _events(runs=[100, 100], lumis=[10, 20])
        filtered, _ = apply_validated_runs_filter(events, self.vrf)
        self.assertEqual(len(filtered), 2)

    def test_section_just_outside_range_dropped(self):
        events = _events(runs=[100, 100], lumis=[9, 21])
        filtered, stats = apply_validated_runs_filter(events, self.vrf)
        self.assertEqual(len(filtered), 0)
        self.assertEqual(stats["n_after"], 0)

    def test_single_section_range_boundaries(self):
        # run 200's [5,5] range: 5 is in, 4 and 6 are out
        events = _events(runs=[200, 200, 200], lumis=[4, 5, 6])
        filtered, _ = apply_validated_runs_filter(events, self.vrf)
        self.assertEqual(ak.to_list(filtered["luminosityBlock"]), [5])

    def test_run_not_in_json_all_dropped(self):
        events = _events(runs=[999], lumis=[1])
        filtered, stats = apply_validated_runs_filter(events, self.vrf)
        self.assertEqual(len(filtered), 0)
        self.assertEqual(stats["per_run"][999], {"before": 1, "after": 0})

    def test_multiple_runs_mixed_in_one_batch(self):
        events = _events(
            runs=[100, 999, 200, 100, 200],
            lumis=[15, 1, 5, 999, 35],
        )
        filtered, stats = apply_validated_runs_filter(events, self.vrf)
        # kept: (100,15), (200,5), (200,35) -- dropped: (999,1), (100,999)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(stats["n_before"], 5)
        self.assertEqual(stats["n_after"], 3)
        self.assertEqual(stats["per_run"][100], {"before": 2, "after": 1})
        self.assertEqual(stats["per_run"][999], {"before": 1, "after": 0})
        self.assertEqual(stats["per_run"][200], {"before": 2, "after": 2})


class MissingFieldsTests(unittest.TestCase):
    """Test 3: filter enabled but run/luminosityBlock absent -> error."""

    def setUp(self):
        self.path = _write_json({"100": [[1, 10]]})
        self.vrf = ValidatedRunsFilter(self.path)

    def tearDown(self):
        os.remove(self.path)

    def test_missing_both_fields_raises(self):
        events = ak.zip({"Electrons": ak.Array([[{"pt": 1.0}]])}, depth_limit=1)
        with self.assertRaises(ValueError) as ctx:
            apply_validated_runs_filter(events, self.vrf)
        self.assertIn("run", str(ctx.exception))
        self.assertIn("luminosityBlock", str(ctx.exception))

    def test_missing_luminosity_block_only_raises(self):
        events = ak.zip({"run": np.array([100], dtype=np.uint32)}, depth_limit=1)
        with self.assertRaises(ValueError) as ctx:
            apply_validated_runs_filter(events, self.vrf)
        self.assertIn("luminosityBlock", str(ctx.exception))


class SimulationGuardTests(unittest.TestCase):
    """Test 4: the simulation guard, both detection paths."""

    def setUp(self):
        self.path = _write_json({"100": [[1, 10]]})
        self.vrf = ValidatedRunsFilter(self.path)

    def tearDown(self):
        os.remove(self.path)

    def test_run_equals_one_detected_as_simulation(self):
        events = _events(runs=[1, 1, 1], lumis=[1, 2, 3])
        self.assertTrue(is_simulation(events))
        with self.assertRaises(ValueError) as ctx:
            apply_validated_runs_filter(events, self.vrf)
        self.assertIn("simulation", str(ctx.exception))

    def test_genweight_present_detected_as_simulation(self):
        # Even with a real-looking run number, a genWeight field is an
        # unambiguous simulation signal.
        events = _events(runs=[100], lumis=[5], extra={"genWeight": np.array([1.0], dtype=np.float32)})
        self.assertTrue(is_simulation(events))
        with self.assertRaises(ValueError):
            apply_validated_runs_filter(events, self.vrf)

    def test_real_data_like_events_not_flagged_as_simulation(self):
        events = _events(runs=[100, 200], lumis=[5, 6])
        self.assertFalse(is_simulation(events))
        # Should not raise for this reason (100 is certified, 200 isn't --
        # that's just ordinary filtering, not a simulation-guard error).
        filtered, _ = apply_validated_runs_filter(events, self.vrf)
        self.assertEqual(len(filtered), 1)

    def test_mixed_run_values_not_flagged_as_simulation(self):
        # Not every event has run==1 -- this is not simulation's signature.
        events = _events(runs=[1, 100], lumis=[1, 5])
        self.assertFalse(is_simulation(events))


class ConfigDefaultTests(unittest.TestCase):
    """Test 5: config key absent -> no-op."""

    def test_default_is_none(self):
        cfg = ParsingConfig(output_path="./o", file_urls_path="./f", jobs_logs_path="./l")
        self.assertIsNone(cfg.validated_runs_json)

    def test_non_string_value_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                validated_runs_json=123,
            )

    def test_string_value_accepted(self):
        cfg = ParsingConfig(
            output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
            validated_runs_json="data/cms/validated_runs/some_file.json",
        )
        self.assertEqual(cfg.validated_runs_json, "data/cms/validated_runs/some_file.json")


@unittest.skipUnless(
    os.environ.get("RUN_NETWORK_TESTS") == "1",
    "requires network access to opendata.cern.ch; set RUN_NETWORK_TESTS=1 to run",
)
class RealDataCrossCheckTests(unittest.TestCase):
    """Test 6: real DoubleEG data vs. an independent reference implementation."""

    FILES = {
        "Run2016G": (
            "https://opendata.cern.ch/eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/"
            "UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root"
        ),
        "Run2016H": (
            "https://opendata.cern.ch/eos/opendata/cms/Run2016H/DoubleEG/NANOAOD/"
            "UL2016_MiniAODv2_NanoAODv9-v1/100000/2AD46B56-E1CA-CD44-B30D-C57FE1C35D15.root"
        ),
    }
    MAX_EVENTS = 2000

    @classmethod
    def setUpClass(cls):
        repo_root = Path(__file__).resolve().parents[1]
        cls.json_path = repo_root / "data" / "cms" / "validated_runs" / \
            "Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
        cls.vrf = ValidatedRunsFilter(str(cls.json_path))
        # Independent reference: a plain Python set of (run, ls) pairs,
        # built directly from the JSON with no shared code at all.
        raw = json.loads(cls.json_path.read_text(encoding="utf-8"))
        cls.reference_set = set()
        for run_str, ranges in raw.items():
            run = int(run_str)
            for lo, hi in ranges:
                for ls in range(lo, hi + 1):
                    cls.reference_set.add((run, ls))

    def _check_one_file(self, era, url):
        import uproot

        f = uproot.open(url)
        t = f["Events"]
        arrays = t.arrays(["run", "luminosityBlock"], entry_stop=self.MAX_EVENTS, library="np")
        events = ak.zip({
            "run": arrays["run"].astype(np.uint32),
            "luminosityBlock": arrays["luminosityBlock"].astype(np.uint32),
        }, depth_limit=1)

        filtered, stats = apply_validated_runs_filter(events, self.vrf)

        reference_keep = np.array([
            (r, l) in self.reference_set
            for r, l in zip(arrays["run"].tolist(), arrays["luminosityBlock"].tolist())
        ])
        reference_kept = int(reference_keep.sum())

        self.assertEqual(stats["n_after"], reference_kept)
        # event-by-event agreement, not just the same count
        pipeline_mask = np.isin(
            (arrays["run"].astype(np.uint64) << np.uint64(32)) | arrays["luminosityBlock"].astype(np.uint64),
            self.vrf.certified_keys,
        )
        self.assertTrue(np.array_equal(pipeline_mask, reference_keep))

        frac = stats["n_after"] / stats["n_before"]
        print(f"\n[cross-check] {era}: kept {stats['n_after']}/{stats['n_before']} "
              f"({frac:.1%}) -- agrees 100% with the independent reference set")
        return frac

    def test_run2016g_matches_reference(self):
        self._check_one_file("Run2016G", self.FILES["Run2016G"])

    def test_run2016h_matches_reference(self):
        self._check_one_file("Run2016H", self.FILES["Run2016H"])


if __name__ == "__main__":
    unittest.main()
