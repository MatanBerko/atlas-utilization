"""
Implementation task 4 (studies/hgg_cms/DESIGN_SELECTION.md, Section 6.3 /
Section 8 task 4): opt-in extra per-object fields (extra_object_fields) and
the two generic object-level boolean cut types (bool_require, bool_any_of),
plus the generic eta_exclude cut.

Covers:
 1. extra_object_fields config validation; absent key -> identical; dedupe
    with default fields.
 2. bool_require / bool_any_of on synthetic jagged photon arrays (0, 1, 3
    photons/event; mixed flags; all-fail; all-pass), object removal +
    particle_counts interplay.
 3. Referencing an unread field -> configuration error, not a deep KeyError.
 4. Missing object branch in one of several files -> loud failure listing
    file and branch.
 5. eta_exclude boundaries.
 6. Real-file cross-check (network-marked, skipped offline): one DoubleEG
    Run2016G file and one postVFP GluGluHToGG file.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import awkward as ak
import numpy as np

from domain.config import ParsingConfig
from services.calculations import physics_calcs
from services.parsing.event_selection import apply_parsing_event_selection, normalize_yaml_kinematic_cuts
from services.parsing.file_parser import (
    FileParser,
    RequiredObjectFieldMissingError,
    RequiredScalarBranchMissingError,
)
from services.parsing.threaded_processor import ThreadedFileProcessor
from services.parsing.trigger_requirements import apply_trigger_requirement
from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter


def _photons(*event_lists) -> ak.Array:
    """Build a synthetic Photons collection: event_lists is a list of lists
    of per-photon dicts."""
    return ak.Array(list(event_lists))


class ConfigValidationTests(unittest.TestCase):
    """Test 1a: extra_object_fields config validation."""

    def test_default_is_none(self):
        cfg = ParsingConfig(output_path="./o", file_urls_path="./f", jobs_logs_path="./l")
        self.assertIsNone(cfg.extra_object_fields)

    def test_valid_config_accepted(self):
        cfg = ParsingConfig(
            output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
            extra_object_fields={"Photons": ["electronVeto", "mvaID_WP90"]},
        )
        self.assertEqual(cfg.extra_object_fields["Photons"], ["electronVeto", "mvaID_WP90"])

    def test_not_a_dict_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                extra_object_fields=["Photons"],
            )

    def test_non_string_collection_name_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                extra_object_fields={1: ["electronVeto"]},
            )

    def test_non_list_fields_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                extra_object_fields={"Photons": "electronVeto"},
            )

    def test_non_string_field_entry_rejected(self):
        with self.assertRaises(ValueError):
            ParsingConfig(
                output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
                extra_object_fields={"Photons": [123]},
            )


class ResolveObjectFieldsTests(unittest.TestCase):
    """Test 1b: _resolve_object_fields -- merge/dedupe/unknown-collection."""

    def test_absent_returns_defaults_unchanged(self):
        objects = {"Photons": ["pt", "eta", "phi", "mass"]}
        merged = FileParser._resolve_object_fields(objects, None)
        self.assertEqual(merged, {"Photons": ["pt", "eta", "phi", "mass"]})
        # Not the same dict object (no shared mutable state with the schema)
        self.assertIsNot(merged["Photons"], objects["Photons"])

    def test_extra_fields_appended(self):
        objects = {"Photons": ["pt", "eta", "phi", "mass"]}
        merged = FileParser._resolve_object_fields(
            objects, {"Photons": ["electronVeto", "mvaID_WP90"]}
        )
        self.assertEqual(merged["Photons"], ["pt", "eta", "phi", "mass", "electronVeto", "mvaID_WP90"])

    def test_duplicate_field_deduped(self):
        objects = {"Photons": ["pt", "eta", "phi", "mass"]}
        merged = FileParser._resolve_object_fields(objects, {"Photons": ["pt", "electronVeto"]})
        self.assertEqual(merged["Photons"], ["pt", "eta", "phi", "mass", "electronVeto"])

    def test_unknown_collection_raises(self):
        objects = {"Photons": ["pt", "eta", "phi", "mass"]}
        with self.assertRaises(ValueError) as ctx:
            FileParser._resolve_object_fields(objects, {"Jetz": ["pt"]})
        self.assertIn("Jetz", str(ctx.exception))
        self.assertIn("Photons", str(ctx.exception))


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


def _make_cms_tree(photon_branches=None, n_events=2):
    data = {
        "Photon_pt": ak.Array([[25.0], [30.0]][:n_events]),
        "Photon_eta": ak.Array([[0.1], [0.2]][:n_events]),
        "Photon_phi": ak.Array([[0.0], [0.1]][:n_events]),
        "Photon_mass": ak.Array([[0.0], [0.0]][:n_events]),
        "run": np.array([1, 2], dtype=np.uint32)[:n_events],
        "luminosityBlock": np.array([10, 20], dtype=np.uint32)[:n_events],
        "event": np.array([100, 200], dtype=np.uint64)[:n_events],
    }
    if photon_branches:
        data.update(photon_branches)
    return _FakeTree(data, n_events)


class DefaultBehaviourUnchangedTests(unittest.TestCase):
    """Test 1c: absent key -> identical output to today."""

    def test_no_extra_photon_fields_when_key_absent(self):
        tree = _make_cms_tree()
        result = FileParser._parse_opened_file(
            _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "fake.root", False, None,
        )
        self.assertEqual(set(result["Photons"].fields), {"pt", "eta", "phi", "mass"})


class ExtraObjectFieldRoundTripTests(unittest.TestCase):
    """Extra fields round-trip through extraction, gating, and re-zipping."""

    def test_requested_extra_fields_present_with_correct_dtype(self):
        tree = _make_cms_tree(photon_branches={
            "Photon_electronVeto": ak.Array([[True], [False]]),
            "Photon_mvaID_WP90": ak.Array([[True], [True]]),
            "Photon_isScEtaEB": ak.Array([[True], [False]]),
            "Photon_isScEtaEE": ak.Array([[False], [True]]),
            "Photon_r9": ak.Array([[0.95], [0.88]]),
        })
        result = FileParser._parse_opened_file(
            _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "fake.root", False, None,
            extra_object_fields={"Photons": [
                "electronVeto", "mvaID_WP90", "isScEtaEB", "isScEtaEE", "r9",
            ]},
        )
        photons = result["Photons"]
        self.assertEqual(
            set(photons.fields),
            {"pt", "eta", "phi", "mass", "electronVeto", "mvaID_WP90", "isScEtaEB", "isScEtaEE", "r9"},
        )
        self.assertEqual(ak.to_list(photons.electronVeto), [[True], [False]])
        self.assertEqual(str(ak.to_numpy(ak.flatten(photons.electronVeto)).dtype), "bool")
        self.assertEqual(str(ak.to_numpy(ak.flatten(photons.r9)).dtype), "float64")

    def test_missing_object_branch_in_one_file_raises_and_lists_field(self):
        good_tree = _make_cms_tree(photon_branches={"Photon_electronVeto": ak.Array([[True], [False]])})
        good_result = FileParser._parse_opened_file(
            _FakeRoot(Events=good_tree), ["Events"], "cms-nanoaod", 40_000, "good.root", False, None,
            extra_object_fields={"Photons": ["electronVeto"]},
        )
        self.assertIn("electronVeto", good_result["Photons"].fields)

        bad_tree = _make_cms_tree()  # no Photon_electronVeto branch at all
        with self.assertRaises(RequiredObjectFieldMissingError) as ctx:
            FileParser._parse_opened_file(
                _FakeRoot(Events=bad_tree), ["Events"], "cms-nanoaod", 40_000, "bad.root", False, None,
                extra_object_fields={"Photons": ["electronVeto"]},
            )
        self.assertIn("bad.root", str(ctx.exception))
        self.assertIn("electronVeto", str(ctx.exception))
        self.assertIn("Photons", str(ctx.exception))
        self.assertEqual(ctx.exception.failures, [("bad.root", "Photons", ["electronVeto"])])

    def test_threaded_processor_aborts_on_missing_object_field(self):
        # ThreadedFileProcessor.process_files aggregates every missing-
        # branch failure it sees (possibly from several different files,
        # possibly of different sub-types -- Trigger, EventIds, or here,
        # an object field) into a single RequiredScalarBranchMissingError
        # (the base type, unchanged from implementation task 3) rather than
        # trying to preserve one file's specific subclass; the specific
        # RequiredObjectFieldMissingError subclass is what's raised at the
        # single-file level, in _parse_opened_file (see the test above).
        class _StubParser:
            def parse_file(self, file_path, **kwargs):
                if file_path == "bad.root":
                    raise RequiredObjectFieldMissingError([(file_path, "Photons", ["electronVeto"])])
                return ak.Array({"run": [1]})

        processor = ThreadedFileProcessor(_StubParser(), 1, show_progress=False)
        with self.assertRaises(RequiredScalarBranchMissingError) as ctx:
            list(processor.process_files(["good.root", "bad.root"], ["Events"], "cms-nanoaod"))
        self.assertIn("bad.root", str(ctx.exception))
        self.assertIn("electronVeto", str(ctx.exception))


class BoolCutsTests(unittest.TestCase):
    """Test 2: bool_require / bool_any_of on synthetic jagged photon arrays."""

    def test_bool_require_all_pass(self):
        events = ak.zip({"Photons": _photons(
            [{"pt": 30.0, "electronVeto": True, "mvaID_WP90": True}],
            [{"pt": 30.0, "electronVeto": True, "mvaID_WP90": True}],
        )}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Photons": {"bool_require": ["electronVeto", "mvaID_WP90"]}}
        )
        self.assertEqual(ak.to_list(ak.num(out["Photons"])), [1, 1])

    def test_bool_require_all_fail(self):
        events = ak.zip({"Photons": _photons(
            [{"pt": 30.0, "electronVeto": False, "mvaID_WP90": True}],
        )}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Photons": {"bool_require": ["electronVeto", "mvaID_WP90"]}}
        )
        self.assertEqual(ak.to_list(ak.num(out["Photons"])), [0])

    def test_bool_require_mixed_flags_zero_one_three_photons(self):
        events = ak.zip({"Photons": _photons(
            [],  # 0 photons
            [{"pt": 30.0, "electronVeto": True}],  # 1 photon, passes
            [  # 3 photons, mixed
                {"pt": 30.0, "electronVeto": True},
                {"pt": 30.0, "electronVeto": False},
                {"pt": 30.0, "electronVeto": True},
            ],
        )}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Photons": {"bool_require": ["electronVeto"]}}
        )
        self.assertEqual(ak.to_list(ak.num(out["Photons"])), [0, 1, 2])

    def test_bool_any_of_union(self):
        events = ak.zip({"Photons": _photons(
            [
                {"pt": 30.0, "isScEtaEB": True, "isScEtaEE": False},   # barrel
                {"pt": 30.0, "isScEtaEB": False, "isScEtaEE": True},   # endcap
                {"pt": 30.0, "isScEtaEB": False, "isScEtaEE": False},  # gap -- excluded
            ],
        )}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Photons": {"bool_any_of": ["isScEtaEB", "isScEtaEE"]}}
        )
        self.assertEqual(ak.to_list(ak.num(out["Photons"])), [2])
        self.assertEqual(sorted(ak.to_list(out["Photons"].pt)[0]), [30.0, 30.0])

    def test_bool_require_and_bool_any_of_combined_with_particle_counts(self):
        events = ak.zip({"Photons": _photons(
            [  # 2 photons pass everything -> event survives particle_counts>=2
                {"pt": 30.0, "electronVeto": True, "isScEtaEB": True, "isScEtaEE": False},
                {"pt": 30.0, "electronVeto": True, "isScEtaEB": False, "isScEtaEE": True},
            ],
            [  # only 1 passes (second fails electronVeto) -> dropped by particle_counts
                {"pt": 30.0, "electronVeto": True, "isScEtaEB": True, "isScEtaEE": False},
                {"pt": 30.0, "electronVeto": False, "isScEtaEB": True, "isScEtaEE": False},
            ],
        )}, depth_limit=1)
        result = apply_parsing_event_selection(
            events,
            particle_counts={"photons": {"min": 2, "max": 10}},
            kinematic_cuts={"photons": {
                "bool_require": ["electronVeto"],
                "bool_any_of": ["isScEtaEB", "isScEtaEE"],
            }},
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(ak.to_list(ak.num(result["Photons"])), [2])

    def test_integer_0_1_field_accepted_as_boolean(self):
        events = ak.zip({"Photons": ak.Array([
            [{"pt": 30.0, "cutBasedBit": np.uint8(1)}, {"pt": 30.0, "cutBasedBit": np.uint8(0)}],
        ])}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Photons": {"bool_require": ["cutBasedBit"]}}
        )
        self.assertEqual(ak.to_list(ak.num(out["Photons"])), [1])

    def test_non_binary_integer_field_rejected(self):
        # cutBased is an ordinal 0-3 scale, not boolean -- must not be
        # silently truthy-cast.
        events = ak.zip({"Photons": ak.Array([
            [{"pt": 30.0, "cutBased": np.uint8(2)}, {"pt": 30.0, "cutBased": np.uint8(0)}],
        ])}, depth_limit=1)
        with self.assertRaises(ValueError) as ctx:
            physics_calcs.filter_events_by_kinematics(
                events, {"Photons": {"bool_require": ["cutBased"]}}
            )
        self.assertIn("cutBased", str(ctx.exception))

    def test_non_boolean_float_field_rejected(self):
        events = ak.zip({"Photons": ak.Array([
            [{"pt": 30.0, "r9": 0.95}],
        ])}, depth_limit=1)
        with self.assertRaises(ValueError) as ctx:
            physics_calcs.filter_events_by_kinematics(
                events, {"Photons": {"bool_require": ["r9"]}}
            )
        self.assertIn("r9", str(ctx.exception))

    def test_empty_batch_after_upstream_filter_does_not_spuriously_raise(self):
        # A batch where an earlier cut already removed every photon must
        # not trip the dtype check (regression check for the "empty flat
        # array" edge case).
        events = ak.zip({"Photons": _photons(
            [{"pt": 5.0, "electronVeto": True}],  # fails pt>20, so 0 photons survive
        )}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Photons": {"pt": {"min": 20.0}, "bool_require": ["electronVeto"]}}
        )
        self.assertEqual(ak.to_list(ak.num(out["Photons"])), [0])


class MissingFieldConfigErrorTests(unittest.TestCase):
    """Test 3: referencing an unread field -> clear configuration error."""

    def test_bool_require_missing_field_raises_value_error(self):
        events = ak.zip({"Photons": _photons(
            [{"pt": 30.0}],
        )}, depth_limit=1)
        with self.assertRaises(ValueError) as ctx:
            physics_calcs.filter_events_by_kinematics(
                events, {"Photons": {"bool_require": ["electronVeto"]}}
            )
        self.assertIn("Photons", str(ctx.exception))
        self.assertIn("electronVeto", str(ctx.exception))

    def test_bool_any_of_missing_field_raises_value_error(self):
        events = ak.zip({"Photons": _photons(
            [{"pt": 30.0, "isScEtaEB": True}],
        )}, depth_limit=1)
        with self.assertRaises(ValueError) as ctx:
            physics_calcs.filter_events_by_kinematics(
                events, {"Photons": {"bool_any_of": ["isScEtaEB", "isScEtaEE"]}}
            )
        self.assertIn("isScEtaEE", str(ctx.exception))

    def test_eta_exclude_missing_eta_raises_value_error(self):
        events = ak.zip({"Photons": ak.Array([
            [{"pt": 30.0}],
        ])}, depth_limit=1)
        with self.assertRaises(ValueError) as ctx:
            physics_calcs.filter_events_by_kinematics(
                events, {"Photons": {"eta_exclude": {"min": 1.4442, "max": 1.566}}}
            )
        self.assertIn("eta", str(ctx.exception))


class EtaExcludeTests(unittest.TestCase):
    """Test 5: eta_exclude boundaries (acts on momentum |eta|, not SC eta)."""

    def setUp(self):
        self.cuts = {"Photons": {"eta_exclude": {"min": 1.4442, "max": 1.566}}}

    def test_boundaries_inclusive_excluded(self):
        events = ak.zip({"Photons": ak.Array([
            [
                {"pt": 30.0, "eta": 1.4442},   # lower boundary -- excluded
                {"pt": 30.0, "eta": 1.566},    # upper boundary -- excluded
                {"pt": 30.0, "eta": -1.5},     # inside gap, negative side -- excluded
                {"pt": 30.0, "eta": 1.0},      # outside gap -- kept
                {"pt": 30.0, "eta": 1.4441},   # just below gap -- kept
                {"pt": 30.0, "eta": 1.5661},   # just above gap -- kept
            ],
        ])}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(events, self.cuts)
        self.assertEqual(ak.to_list(out["Photons"].eta)[0], [1.0, 1.4441, 1.5661])


@unittest.skipUnless(
    os.environ.get("RUN_NETWORK_TESTS") == "1",
    "requires network access to opendata.cern.ch; set RUN_NETWORK_TESTS=1 to run",
)
class RealDataCrossCheckTests(unittest.TestCase):
    """Test 6: real-file cross-check against an independent uproot+awkward
    reimplementation of the same selection."""

    TRIGGER = "HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"
    MAX_EVENTS = 2000
    EXTRA_FIELDS = [
        "electronVeto", "mvaID_WP90", "isScEtaEB", "isScEtaEE", "r9", "hoe",
    ]
    KINEMATIC_CUTS = {
        "Photons": {
            "pt": {"min": 20.0},
            "bool_require": ["electronVeto", "mvaID_WP90"],
            "bool_any_of": ["isScEtaEB", "isScEtaEE"],
        }
    }

    DATA_URL = (
        "https://opendata.cern.ch/eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/"
        "UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root"
    )
    SIGNAL_URL = (
        "https://opendata.cern.ch/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/"
        "GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/"
        "106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root"
    )

    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[1]
        json_path = repo_root / "data" / "cms" / "validated_runs" / \
            "Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
        cls.vrf = ValidatedRunsFilter(str(json_path))
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        cls.reference_certified = set()
        for run_str, ranges in raw.items():
            run = int(run_str)
            for lo, hi in ranges:
                for ls in range(lo, hi + 1):
                    cls.reference_certified.add((run, ls))

    def _pipeline_select(self, url, is_data):
        import uproot

        real_file = uproot.open(url)
        real_tree = real_file["Events"]

        class _CappedTree:
            def __init__(self, real_tree, max_entries):
                self._real = real_tree
                self.num_entries = min(real_tree.num_entries, max_entries)

            def keys(self):
                return self._real.keys()

            def arrays(self, branches, entry_start, entry_stop, library):
                capped_stop = min(entry_stop, self.num_entries)
                return self._real.arrays(
                    branches, entry_start=entry_start, entry_stop=capped_stop, library=library
                )

        capped = _CappedTree(real_tree, self.MAX_EVENTS)
        root = _FakeRoot(Events=capped)

        events = FileParser._parse_opened_file(
            root, ["Events"], "cms-nanoaod", self.MAX_EVENTS, url, False, None,
            extra_scalar_branches={"Trigger": [self.TRIGGER]},
            extra_object_fields={"Photons": self.EXTRA_FIELDS},
        )
        counts = {"n_read": len(events)}

        if is_data:
            events, vr_stats = apply_validated_runs_filter(events, self.vrf)
            counts["n_after_validated_runs"] = vr_stats["n_after"]

        events, tr_stats = apply_trigger_requirement(events, {"mode": "any", "paths": [self.TRIGGER]})
        counts["n_after_trigger"] = tr_stats["n_after"]

        events = apply_parsing_event_selection(
            events,
            particle_counts={"photons": {"min": 2, "max": 999}},
            kinematic_cuts=self.KINEMATIC_CUTS,
        )
        counts["n_after_particle_counts"] = len(events)

        return events, counts

    def _reference_select(self, url, is_data):
        import uproot

        branches = [
            "run", "luminosityBlock", self.TRIGGER,
            "Photon_pt", "Photon_eta", "Photon_phi", "Photon_r9", "Photon_hoe",
            "Photon_electronVeto", "Photon_mvaID_WP90",
            "Photon_isScEtaEB", "Photon_isScEtaEE",
        ]
        f = uproot.open(url)
        t = f["Events"]
        arr = t.arrays(branches, entry_stop=self.MAX_EVENTS, library="ak")
        counts = {"n_read": len(arr)}

        if is_data:
            keys = (
                ak.to_numpy(arr["run"]).astype(np.uint64) << np.uint64(32)
            ) | ak.to_numpy(arr["luminosityBlock"]).astype(np.uint64)
            keep = np.isin(keys, self.vrf.certified_keys)
            arr = arr[keep]
            counts["n_after_validated_runs"] = len(arr)

        trig = ak.to_numpy(arr[self.TRIGGER]).astype(bool)
        arr = arr[trig]
        counts["n_after_trigger"] = len(arr)

        pt = arr["Photon_pt"]
        photon_mask = (
            (pt >= 20.0)
            & arr["Photon_electronVeto"]
            & arr["Photon_mvaID_WP90"]
            & (arr["Photon_isScEtaEB"] | arr["Photon_isScEtaEE"])
        )
        n_selected = ak.num(pt[photon_mask])
        event_mask = n_selected >= 2
        arr = arr[event_mask]
        photon_mask = photon_mask[event_mask]
        counts["n_after_particle_counts"] = len(arr)

        selected = {
            "pt": arr["Photon_pt"][photon_mask],
            "eta": arr["Photon_eta"][photon_mask],
            "phi": arr["Photon_phi"][photon_mask],
            "r9": arr["Photon_r9"][photon_mask],
            "hoe": arr["Photon_hoe"][photon_mask],
        }
        return selected, counts

    def _compare(self, era, url, is_data):
        pipeline_events, pipeline_counts = self._pipeline_select(url, is_data)
        reference_selected, reference_counts = self._reference_select(url, is_data)

        print(f"\n[object-fields cross-check] {era}: pipeline={pipeline_counts} reference={reference_counts}")
        self.assertEqual(pipeline_counts, reference_counts)

        photons = pipeline_events["Photons"]
        for field in ("pt", "eta", "phi", "r9", "hoe"):
            pipeline_vals = ak.to_list(getattr(photons, field))
            reference_vals = ak.to_list(reference_selected[field])
            self.assertEqual(pipeline_vals, reference_vals, f"{era}: field '{field}' mismatch")

    def test_data_run2016g_matches_reference(self):
        self._compare("Run2016G data", self.DATA_URL, is_data=True)

    def test_signal_ggh_matches_reference(self):
        self._compare("ggH signal", self.SIGNAL_URL, is_data=False)


if __name__ == "__main__":
    unittest.main()
