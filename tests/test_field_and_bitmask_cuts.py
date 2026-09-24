"""
Generic numeric field cuts (``field_cuts``) and integer bit-mask cuts
(``bit_cuts``) -- see docs/GENERIC_CUTS_DESIGN.md.

Covers:
 1. field_cuts config validation at load time (unknown sub-keys, non-numeric
    bounds, min > max, empty block).
 2. bit_cuts config validation at load time (unknown sub-keys, non-integer/
    non-positive masks, empty block).
 3. field_cuts application: min-only, max-only, both, inclusive boundaries
    (matching the existing pt/eta convention), no-division independence
    from rel_isolation_max.
 4. bit_cuts application: bits_all, bits_any, both together, non-integer
    field rejected.
 5. Missing-field error, at both the physics_calcs layer (direct callers)
    and the file-parsing layer (RequiredObjectFieldMissingError, naming
    file/object/field), for both field_cuts and bit_cuts.
 6. collect_extra_object_fields_from_kinematic_cuts / auto-field merging
    (A3): absent field_cuts/bit_cuts is a complete no-op; present ones are
    collected under the canonical object name and merged/deduped against
    any already-requested extra_object_fields, without ever losing an
    already-requested field.
 7. Task C2: a config with neither key produces identical output to the
    pre-change code (normalize_yaml_kinematic_cuts never adds field_cuts/
    bit_cuts keys when absent; filter_events_by_kinematics output is
    unaffected).
"""
from __future__ import annotations

import unittest

import awkward as ak
import numpy as np

from domain.config import ParsingConfig
from services.calculations import consts, physics_calcs
from services.parsing.event_selection import (
    apply_parsing_event_selection,
    collect_extra_object_fields_from_kinematic_cuts,
    merge_auto_requested_object_fields,
    normalize_yaml_kinematic_cuts,
)
from services.parsing.file_parser import FileParser, RequiredObjectFieldMissingError


def _muons(*event_lists) -> ak.Array:
    return ak.Array(list(event_lists))


class FieldCutsConfigValidationTests(unittest.TestCase):
    """A5: field_cuts validated at config-load time."""

    def _cfg(self, kinematic_cuts):
        return ParsingConfig(
            output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
            kinematic_cuts=kinematic_cuts,
        )

    def test_absent_field_cuts_is_a_no_op(self):
        cfg = self._cfg({"muons": {"pt_min": 20.0, "eta_max": 2.4}})
        self.assertNotIn("field_cuts", cfg.kinematic_cuts["muons"])

    def test_valid_min_only_accepted(self):
        cfg = self._cfg({"muons": {"field_cuts": {"dxy": {"min": -0.2}}}})
        self.assertEqual(cfg.kinematic_cuts["muons"]["field_cuts"]["dxy"], {"min": -0.2})

    def test_valid_max_only_accepted(self):
        cfg = self._cfg({"muons": {"field_cuts": {"pfRelIso04_all": {"max": 0.15}}}})
        self.assertEqual(cfg.kinematic_cuts["muons"]["field_cuts"]["pfRelIso04_all"], {"max": 0.15})

    def test_valid_min_and_max_accepted(self):
        cfg = self._cfg({"muons": {"field_cuts": {"dxy": {"min": -0.2, "max": 0.2}}}})
        self.assertEqual(cfg.kinematic_cuts["muons"]["field_cuts"]["dxy"], {"min": -0.2, "max": 0.2})

    def test_empty_field_cuts_block_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._cfg({"muons": {"field_cuts": {}}})
        self.assertIn("muons", str(ctx.exception))
        self.assertIn("field_cuts", str(ctx.exception))

    def test_empty_bounds_for_a_field_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._cfg({"muons": {"field_cuts": {"dxy": {}}}})
        self.assertIn("dxy", str(ctx.exception))

    def test_unknown_subkey_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._cfg({"muons": {"field_cuts": {"dxy": {"mean": 0.0}}}})
        self.assertIn("mean", str(ctx.exception))

    def test_non_numeric_bound_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._cfg({"muons": {"field_cuts": {"dxy": {"min": "close"}}}})
        self.assertIn("dxy", str(ctx.exception))

    def test_bool_bound_rejected(self):
        # bool is a Python int subclass -- must not silently pass as 0/1.
        with self.assertRaises(ValueError):
            self._cfg({"muons": {"field_cuts": {"dxy": {"min": True}}}})

    def test_min_greater_than_max_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._cfg({"muons": {"field_cuts": {"dxy": {"min": 0.5, "max": 0.1}}}})
        self.assertIn("min", str(ctx.exception))
        self.assertIn("max", str(ctx.exception))

    def test_non_string_field_name_rejected(self):
        with self.assertRaises(ValueError):
            self._cfg({"muons": {"field_cuts": {123: {"min": 0.0}}}})


class BitCutsConfigValidationTests(unittest.TestCase):
    """B4 (validation part): bit_cuts validated at config-load time."""

    def _cfg(self, kinematic_cuts):
        return ParsingConfig(
            output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
            kinematic_cuts=kinematic_cuts,
        )

    def test_absent_bit_cuts_is_a_no_op(self):
        cfg = self._cfg({"jets": {"pt_min": 30.0}})
        self.assertNotIn("bit_cuts", cfg.kinematic_cuts["jets"])

    def test_valid_bits_all_accepted(self):
        cfg = self._cfg({"jets": {"bit_cuts": {"jetId": {"bits_all": 2}}}})
        self.assertEqual(cfg.kinematic_cuts["jets"]["bit_cuts"]["jetId"], {"bits_all": 2})

    def test_valid_bits_any_accepted(self):
        cfg = self._cfg({"jets": {"bit_cuts": {"puId": {"bits_any": 4}}}})
        self.assertEqual(cfg.kinematic_cuts["jets"]["bit_cuts"]["puId"], {"bits_any": 4})

    def test_valid_both_together_accepted(self):
        cfg = self._cfg({"jets": {"bit_cuts": {"jetId": {"bits_all": 2, "bits_any": 4}}}})
        self.assertEqual(
            cfg.kinematic_cuts["jets"]["bit_cuts"]["jetId"], {"bits_all": 2, "bits_any": 4}
        )

    def test_empty_bit_cuts_block_rejected(self):
        with self.assertRaises(ValueError):
            self._cfg({"jets": {"bit_cuts": {}}})

    def test_empty_spec_for_a_field_rejected(self):
        with self.assertRaises(ValueError):
            self._cfg({"jets": {"bit_cuts": {"jetId": {}}}})

    def test_unknown_subkey_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._cfg({"jets": {"bit_cuts": {"jetId": {"bit_index": 1}}}})
        self.assertIn("bit_index", str(ctx.exception))

    def test_float_mask_rejected(self):
        with self.assertRaises(ValueError):
            self._cfg({"jets": {"bit_cuts": {"jetId": {"bits_all": 2.0}}}})

    def test_bool_mask_rejected(self):
        with self.assertRaises(ValueError):
            self._cfg({"jets": {"bit_cuts": {"jetId": {"bits_all": True}}}})

    def test_zero_mask_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._cfg({"jets": {"bit_cuts": {"jetId": {"bits_all": 0}}}})
        self.assertIn("positive", str(ctx.exception))

    def test_negative_mask_rejected(self):
        with self.assertRaises(ValueError):
            self._cfg({"jets": {"bit_cuts": {"jetId": {"bits_all": -2}}}})


class FieldCutsApplicationTests(unittest.TestCase):
    """A2/A6: field_cuts application, bound semantics, no-division independence."""

    def test_max_only(self):
        events = ak.zip({"Muons": _muons(
            [{"pt": 30.0, "pfRelIso04_all": 0.10}, {"pt": 25.0, "pfRelIso04_all": 0.20}],
        )}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Muons": {"field_cuts": {"pfRelIso04_all": {"max": 0.15}}}}
        )
        self.assertEqual(ak.to_list(out["Muons"].pt)[0], [30.0])

    def test_min_only(self):
        events = ak.zip({"Muons": _muons(
            [{"pt": 30.0, "dxy": -0.5}, {"pt": 25.0, "dxy": 0.1}],
        )}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Muons": {"field_cuts": {"dxy": {"min": -0.2}}}}
        )
        self.assertEqual(ak.to_list(out["Muons"].pt)[0], [25.0])

    def test_min_and_max(self):
        events = ak.zip({"Muons": _muons(
            [{"pt": 1.0, "dxy": -0.5}, {"pt": 2.0, "dxy": 0.1}, {"pt": 3.0, "dxy": 0.5}],
        )}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Muons": {"field_cuts": {"dxy": {"min": -0.2, "max": 0.2}}}}
        )
        self.assertEqual(ak.to_list(out["Muons"].pt)[0], [2.0])

    def test_bounds_are_inclusive_matching_pt_eta_convention(self):
        # Existing pt_min uses pt >= min; existing eta_max uses
        # min <= eta <= max (both inclusive) -- see
        # services/calculations/physics_calcs.py's pt/eta blocks. field_cuts
        # must match this exactly: min is ">=", max is "<=".
        events = ak.zip({"Muons": _muons(
            [{"pt": 1.0, "dxy": -0.2}, {"pt": 2.0, "dxy": 0.2}, {"pt": 3.0, "dxy": 0.20001}],
        )}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Muons": {"field_cuts": {"dxy": {"min": -0.2, "max": 0.2}}}}
        )
        self.assertEqual(ak.to_list(out["Muons"].pt)[0], [1.0, 2.0])

    def test_multiple_fields_combined(self):
        events = ak.zip({"Muons": _muons(
            [
                {"pt": 1.0, "pfRelIso04_all": 0.05, "dxy": 0.0},   # passes both
                {"pt": 2.0, "pfRelIso04_all": 0.30, "dxy": 0.0},   # fails iso
                {"pt": 3.0, "pfRelIso04_all": 0.05, "dxy": 1.0},   # fails dxy
            ],
        )}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Muons": {"field_cuts": {
                "pfRelIso04_all": {"max": 0.15},
                "dxy": {"min": -0.2, "max": 0.2},
            }}}
        )
        self.assertEqual(ak.to_list(out["Muons"].pt)[0], [1.0])

    def test_no_division_independence_from_rel_isolation_max(self):
        # rel_isolation_max divides consts.ELECTRON_REL_ISOLATION_FIELD by pT
        # (see the handling just above field_cuts in physics_calcs.py) -- an
        # absolute isolation-energy field would need a huge value to pass a
        # small rel_isolation_max threshold once divided by a tiny pT.
        # field_cuts must perform a PLAIN comparison instead: the same
        # absolute value, compared directly against max, must pass a max
        # large enough for the raw value, with no dependence on pT at all.
        iso_field = consts.ELECTRON_REL_ISOLATION_FIELD
        events = ak.zip({"Electrons": ak.Array([
            [{"pt": 0.001, iso_field: 50.0}],  # tiny pT: rel_isolation_max would explode
        ])}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Electrons": {"field_cuts": {iso_field: {"max": 100.0}}}}
        )
        self.assertEqual(ak.to_list(out["Electrons"][iso_field])[0], [50.0])

    def test_field_cuts_and_rel_isolation_max_are_independent_cuts(self):
        # Both configured together on Electrons must each apply on their
        # own terms (rel_isolation_max divides, field_cuts does not), not
        # interact or override one another.
        iso_field = consts.ELECTRON_REL_ISOLATION_FIELD
        events = ak.zip({"Electrons": ak.Array([
            [{"pt": 50.0, iso_field: 2.5, "dxy": 0.01}],  # rel iso = 0.05, passes both
            [{"pt": 50.0, iso_field: 10.0, "dxy": 0.01}],  # rel iso = 0.20, fails rel_isolation_max
        ])}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Electrons": {
                "rel_isolation_max": 0.15,
                "field_cuts": {"dxy": {"max": 0.2}},
            }}
        )
        self.assertEqual(ak.to_list(ak.num(out["Electrons"])), [1, 0])


class FieldCutsMissingFieldTests(unittest.TestCase):
    """A4: missing field is a loud error, never a silent no-op."""

    def test_physics_calcs_layer_raises_for_missing_field(self):
        events = ak.zip({"Muons": _muons([{"pt": 30.0}])}, depth_limit=1)
        with self.assertRaises(ValueError) as ctx:
            physics_calcs.filter_events_by_kinematics(
                events, {"Muons": {"field_cuts": {"pfRelIso04_all": {"max": 0.15}}}}
            )
        self.assertIn("Muons", str(ctx.exception))
        self.assertIn("pfRelIso04_all", str(ctx.exception))

    def test_file_parsing_layer_raises_and_names_file_object_field(self):
        # This is the layer A4 actually describes ("naming the object, the
        # field, and the file"): a field_cuts-referenced field that
        # collect_extra_object_fields_from_kinematic_cuts folds into
        # extra_object_fields, then FileParser discovers is genuinely absent
        # from this specific file.
        class _FakeTree:
            def __init__(self, data, num_entries):
                self._data = data
                self.num_entries = num_entries

            def keys(self):
                return list(self._data.keys())

            def arrays(self, branches, entry_start, entry_stop, library):
                if isinstance(branches, str):
                    branches = [branches]
                return ak.Array({b: self._data[b][entry_start:entry_stop] for b in branches})

        class _FakeRoot(dict):
            def keys(self):
                return ["Events;1"]

        tree = _FakeTree({
            "Muon_pt": ak.Array([[30.0]]),
            "Muon_eta": ak.Array([[0.1]]),
            "Muon_phi": ak.Array([[0.0]]),
            "Muon_mass": ak.Array([[0.105]]),
            "run": np.array([1], dtype=np.uint32),
            "luminosityBlock": np.array([1], dtype=np.uint32),
            "event": np.array([1], dtype=np.uint64),
        }, num_entries=1)

        kinematic_cuts = {"muons": {"field_cuts": {"pfRelIso04_all": {"max": 0.15}}}}
        extra_object_fields = collect_extra_object_fields_from_kinematic_cuts(kinematic_cuts)
        self.assertEqual(extra_object_fields, {"Muons": ["pfRelIso04_all"]})

        with self.assertRaises(RequiredObjectFieldMissingError) as ctx:
            FileParser._parse_opened_file(
                _FakeRoot(Events=tree), ["Events"], "cms-nanoaod", 40_000, "bad_file.root", False, None,
                extra_object_fields=extra_object_fields,
            )
        self.assertIn("bad_file.root", str(ctx.exception))
        self.assertIn("Muons", str(ctx.exception))
        self.assertIn("pfRelIso04_all", str(ctx.exception))


class BitCutsApplicationTests(unittest.TestCase):
    """B2/B5: bit_cuts application, bits_all vs bits_any, integer-type check."""

    def _jets(self, ids):
        return ak.zip({"Jets": ak.Array([
            [{"pt": 40.0, "jetId": jid} for jid in ids],
        ])}, depth_limit=1)

    def test_bits_all(self):
        # jetId=6 (110b) has bit 2 set; jetId=4 (100b) does not.
        events = self._jets([6, 4, 0])
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Jets": {"bit_cuts": {"jetId": {"bits_all": 2}}}}
        )
        self.assertEqual(ak.to_list(out["Jets"].jetId)[0], [6])

    def test_bits_any(self):
        # jetId=6 (110b) and jetId=4 (100b) both have bit 4 set; jetId=1 (001b) doesn't.
        events = self._jets([6, 4, 1])
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Jets": {"bit_cuts": {"jetId": {"bits_any": 4}}}}
        )
        self.assertEqual(sorted(ak.to_list(out["Jets"].jetId)[0]), [4, 6])

    def test_bits_all_and_bits_any_together(self):
        # Must satisfy BOTH: bit 2 set (bits_all=2) AND at least one of bit 4 (bits_any=4).
        events = self._jets([6, 2, 4])  # 6=110b (both), 2=010b (bits_all only), 4=100b (bits_any only)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Jets": {"bit_cuts": {"jetId": {"bits_all": 2, "bits_any": 4}}}}
        )
        self.assertEqual(ak.to_list(out["Jets"].jetId)[0], [6])

    def test_multi_bit_mask_bits_all_requires_every_bit(self):
        # bits_all=6 (110b) requires BOTH bit 2 and bit 4 set.
        events = self._jets([6, 2, 4, 7])
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Jets": {"bit_cuts": {"jetId": {"bits_all": 6}}}}
        )
        self.assertEqual(sorted(ak.to_list(out["Jets"].jetId)[0]), [6, 7])

    def test_float_field_rejected(self):
        events = ak.zip({"Jets": ak.Array([
            [{"pt": 40.0, "jetId": 6.0}],
        ])}, depth_limit=1)
        with self.assertRaises(ValueError) as ctx:
            physics_calcs.filter_events_by_kinematics(
                events, {"Jets": {"bit_cuts": {"jetId": {"bits_all": 2}}}}
            )
        self.assertIn("Jets", str(ctx.exception))
        self.assertIn("jetId", str(ctx.exception))
        self.assertIn("float", str(ctx.exception).lower() + str(ctx.exception.args))

    def test_missing_field_raises(self):
        events = ak.zip({"Jets": ak.Array([[{"pt": 40.0}]])}, depth_limit=1)
        with self.assertRaises(ValueError) as ctx:
            physics_calcs.filter_events_by_kinematics(
                events, {"Jets": {"bit_cuts": {"jetId": {"bits_all": 2}}}}
            )
        self.assertIn("Jets", str(ctx.exception))
        self.assertIn("jetId", str(ctx.exception))

    def test_empty_batch_does_not_spuriously_raise_on_dtype_check(self):
        # Mirrors the existing bool_require empty-batch regression test --
        # an earlier cut removing every jet must not trip the integer-dtype
        # check on a now-empty (but still typed) flat array.
        events = ak.zip({"Jets": ak.Array([
            [{"pt": 5.0, "jetId": np.int32(6)}],  # fails pt>=30, so 0 jets survive
        ])}, depth_limit=1)
        out = physics_calcs.filter_events_by_kinematics(
            events, {"Jets": {"pt": {"min": 30.0}, "bit_cuts": {"jetId": {"bits_all": 2}}}}
        )
        self.assertEqual(ak.to_list(ak.num(out["Jets"])), [0])


class AutoObjectFieldCollectionTests(unittest.TestCase):
    """A3: requesting a cut on a field auto-adds it to the branches read."""

    def test_absent_field_cuts_and_bit_cuts_collects_nothing(self):
        self.assertEqual(collect_extra_object_fields_from_kinematic_cuts(None), {})
        self.assertEqual(collect_extra_object_fields_from_kinematic_cuts({}), {})
        self.assertEqual(
            collect_extra_object_fields_from_kinematic_cuts({"muons": {"pt_min": 20.0}}), {}
        )

    def test_field_cuts_collected_under_canonical_object_name(self):
        result = collect_extra_object_fields_from_kinematic_cuts(
            {"muons": {"field_cuts": {"pfRelIso04_all": {"max": 0.15}, "dxy": {"min": -0.2}}}}
        )
        self.assertEqual(set(result["Muons"]), {"pfRelIso04_all", "dxy"})

    def test_bit_cuts_collected_under_canonical_object_name(self):
        result = collect_extra_object_fields_from_kinematic_cuts(
            {"jets": {"bit_cuts": {"jetId": {"bits_all": 2}}}}
        )
        self.assertEqual(result, {"Jets": ["jetId"]})

    def test_both_field_cuts_and_bit_cuts_on_same_object_collected(self):
        result = collect_extra_object_fields_from_kinematic_cuts(
            {"jets": {"field_cuts": {"pt_raw": {"min": 0.0}}, "bit_cuts": {"jetId": {"bits_all": 2}}}}
        )
        self.assertEqual(set(result["Jets"]), {"pt_raw", "jetId"})

    def test_merge_dedupes_and_reports_only_newly_added_fields(self):
        merged, newly_added = merge_auto_requested_object_fields(
            {"Muons": ["charge"]}, {"Muons": ["pfRelIso04_all", "charge"], "Jets": ["jetId"]}
        )
        self.assertEqual(set(merged["Muons"]), {"charge", "pfRelIso04_all"})
        self.assertEqual(merged["Jets"], ["jetId"])
        # "charge" was already requested -> not reported as newly added.
        self.assertEqual(newly_added["Muons"], ["pfRelIso04_all"])
        self.assertEqual(newly_added["Jets"], ["jetId"])

    def test_merge_with_no_auto_requested_fields_is_exact_identity_no_op(self):
        existing = {"Photons": ["r9"]}
        merged, newly_added = merge_auto_requested_object_fields(existing, {})
        self.assertIs(merged, existing)  # same object, not a copy
        self.assertEqual(newly_added, {})


class DefaultOffCompleteNoOpTests(unittest.TestCase):
    """Task C2: a config with NEITHER field_cuts nor bit_cuts produces
    output identical to the pre-change code."""

    def test_normalize_yaml_kinematic_cuts_never_adds_the_new_keys_when_absent(self):
        out = normalize_yaml_kinematic_cuts({"pt_min": 20.0, "eta_max": 2.4})
        self.assertNotIn("field_cuts", out)
        self.assertNotIn("bit_cuts", out)
        self.assertEqual(out, {"pt": {"min": 20.0}, "eta": {"min": -2.4, "max": 2.4}})

    def test_filter_events_by_kinematics_output_unaffected_when_absent(self):
        events = ak.zip({"Muons": _muons(
            [{"pt": 30.0, "eta": 1.0}, {"pt": 10.0, "eta": 1.0}],
        )}, depth_limit=1)
        cuts = {"Muons": normalize_yaml_kinematic_cuts({"pt_min": 20.0, "eta_max": 2.4})}
        out = physics_calcs.filter_events_by_kinematics(events, cuts)
        self.assertEqual(ak.to_list(out["Muons"].pt)[0], [30.0])

    def test_apply_parsing_event_selection_unaffected_when_absent(self):
        events = ak.zip({"Muons": _muons(
            [{"pt": 30.0, "eta": 1.0}, {"pt": 10.0, "eta": 1.0}],
        )}, depth_limit=1)
        out = apply_parsing_event_selection(
            events, kinematic_cuts={"muons": {"pt_min": 20.0, "eta_max": 2.4}}
        )
        self.assertEqual(ak.to_list(out["Muons"].pt)[0], [30.0])

    def test_config_construction_unaffected_when_absent(self):
        cfg = ParsingConfig(
            output_path="./o", file_urls_path="./f", jobs_logs_path="./l",
            kinematic_cuts={"muons": {"pt_min": 20.0, "eta_max": 2.4}},
        )
        # No exception raised, and the dict is exactly what was passed in.
        self.assertEqual(cfg.kinematic_cuts, {"muons": {"pt_min": 20.0, "eta_max": 2.4}})


if __name__ == "__main__":
    unittest.main()
