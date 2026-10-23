"""
Implementation task 3 (studies/hgg_cms/DESIGN_SELECTION.md, Section 8 task
3): the optional HLT trigger requirement, and the loud-failure behaviour
for a required scalar branch missing from an input file.

Covers:
 1. Validation of a trigger-requirement dict (validate_trigger_requirements).
 2. Filter logic on synthetic events: any/all with 1 and 2 paths, all-fail,
    all-pass, dtype handling.
 5. Ordering with the validated-runs filter: statistics reflect
    validated-runs first, then trigger.
 6. A real-data cross-check against a direct uproot read of the HLT branch
    (network-marked, skipped offline).

Items 3 and 4 (FileParser / ThreadedFileProcessor loud-failure behaviour,
and FileParser config-key behaviour) and the ParsingConfig-level part of
item 1 were removed on 14 Oct 2026: they test fork edits to upstream files
that are kept in archive/master-2026-10-14 and are not on this master.
"""
from __future__ import annotations

import os
import unittest

import awkward as ak
import numpy as np

from services.parsing.trigger_requirements import (
    apply_trigger_requirement,
    trigger_group_branches,
    validate_trigger_requirements,
)
from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter


def _events(**fields) -> ak.Array:
    return ak.zip(fields, depth_limit=1)


class ConfigValidationTests(unittest.TestCase):
    """Test 1: validation of a trigger-requirement dict by the module's own
    helper. (The ParsingConfig-level validation tests were removed on
    14 Oct 2026: that ParsingConfig field is a fork edit to an upstream
    file, kept in archive/master-2026-10-14, not on this master.)"""

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
