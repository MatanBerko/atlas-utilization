"""
Apply parsing-stage event filters from YAML (particle count ranges + kinematic cuts).

Maps YAML keys (e.g. ``electrons``) to awkward record fields (``Electrons``).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import awkward as ak
import numpy as np

from services.calculations import physics_calcs

YAML_PARTICLE_KEYS: Dict[str, str] = {
    "electrons": "Electrons",
    "muons": "Muons",
    "jets": "Jets",
    "bjets": "BJets",
    "photons": "Photons",
    "taus": "Taus",
}


def canonical_particle_field_name(key: str) -> str:
    return YAML_PARTICLE_KEYS.get(key.lower(), key)


def normalize_yaml_kinematic_cuts(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Turn ``pt_min`` / ``eta_max`` / ``rel_isolation_max`` into internal cut dict."""
    out: Dict[str, Any] = {}
    if "pt" in raw and isinstance(raw["pt"], dict):
        out["pt"] = dict(raw["pt"])
    elif "pt_min" in raw:
        out["pt"] = {"min": float(raw["pt_min"])}

    if "eta" in raw and isinstance(raw["eta"], dict):
        out["eta"] = dict(raw["eta"])
    elif "eta_max" in raw:
        em = float(raw["eta_max"])
        out["eta"] = {"min": -em, "max": em}

    if "phi" in raw and isinstance(raw["phi"], dict):
        out["phi"] = dict(raw["phi"])
    elif "phi_min" in raw or "phi_max" in raw:
        out["phi"] = {
            "min": float(raw.get("phi_min", -np.pi)),
            "max": float(raw.get("phi_max", np.pi)),
        }

    if "rel_isolation_max" in raw:
        out["rel_isolation_max"] = float(raw["rel_isolation_max"])

    # Generic object-level boolean cuts (implementation task 4): "all of
    # these must be True" / "at least one of these must be True". Passed
    # through as plain lists -- validated where they're applied
    # (services.calculations.physics_calcs.filter_events_by_kinematics),
    # not here, matching pt/eta/phi's own existing validate-at-apply-time
    # style rather than a separate up-front schema check.
    if "bool_require" in raw:
        out["bool_require"] = list(raw["bool_require"])
    if "bool_any_of" in raw:
        out["bool_any_of"] = list(raw["bool_any_of"])

    # Generic momentum-|eta| exclusion window -- NOT the CMS supercluster-eta
    # acceptance gap. See docs/CMS_KNOWN_LIMITATIONS.md.
    if "eta_exclude" in raw:
        out["eta_exclude"] = dict(raw["eta_exclude"])

    # Generic numeric cut on an ARBITRARY per-object field, e.g. CMS muon
    # isolation: {"field_cuts": {"pfRelIso04_all": {"max": 0.15}}}. Passed
    # through as-is (validated at config-load time in
    # domain.config.ParsingConfig.__post_init__, not here) -- see
    # docs/GENERIC_CUTS_DESIGN.md. Deliberately separate from
    # rel_isolation_max (see physics_calcs.filter_events_by_kinematics for
    # why): field_cuts never divides, rel_isolation_max always does.
    if "field_cuts" in raw and isinstance(raw["field_cuts"], dict):
        out["field_cuts"] = {
            field_name: dict(bounds) for field_name, bounds in raw["field_cuts"].items()
        }

    # Integer bit-mask cut, e.g. CMS tight jet ID: {"bit_cuts": {"jetId":
    # {"bits_all": 2}}}. Passed through as-is (validated at config-load
    # time, not here) -- see docs/GENERIC_CUTS_DESIGN.md.
    if "bit_cuts" in raw and isinstance(raw["bit_cuts"], dict):
        out["bit_cuts"] = {
            field_name: dict(spec) for field_name, spec in raw["bit_cuts"].items()
        }

    return out


def collect_extra_object_fields_from_kinematic_cuts(
    kinematic_cuts: Optional[Dict[str, Any]],
) -> Dict[str, list]:
    """Return ``{canonical_object_name: [field_name, ...]}`` for every field
    referenced by a ``field_cuts`` or ``bit_cuts`` block anywhere in
    ``kinematic_cuts`` (raw YAML shape, keyed by ``electrons``/``muons``/…).

    Used by the parsing handler to fold these fields into
    ``extra_object_fields`` so they are auto-requested from the file --
    requesting a cut on a field must never silently do nothing just because
    that field wasn't already being read. Absent ``field_cuts``/``bit_cuts``
    (every existing config) returns ``{}``, a complete no-op.
    """
    result: Dict[str, list] = {}
    if not kinematic_cuts:
        return result
    for key, val in kinematic_cuts.items():
        if not isinstance(val, dict):
            continue
        fields: list = []
        for sub_key in ("field_cuts", "bit_cuts"):
            sub = val.get(sub_key)
            if isinstance(sub, dict):
                fields.extend(sub.keys())
        if fields:
            cname = canonical_particle_field_name(key)
            existing = result.setdefault(cname, [])
            result[cname] = list(dict.fromkeys(existing + fields))
    return result


def merge_auto_requested_object_fields(
    extra_object_fields: Optional[Dict[str, list]],
    auto_requested: Dict[str, list],
):
    """Merge ``auto_requested`` (from
    :func:`collect_extra_object_fields_from_kinematic_cuts`) into
    ``extra_object_fields``, de-duplicating fields already requested.

    Returns ``(merged, newly_added)``: ``merged`` is the dict to actually
    pass on to ``FileParser``/``ThreadedFileProcessor``; ``newly_added``
    lists, per object, only the fields that were not already present in
    ``extra_object_fields`` -- the caller (the parsing handler) logs these
    at INFO, so a field auto-requested because of a ``field_cuts``/
    ``bit_cuts`` block is never invisible (see
    docs/GENERIC_CUTS_DESIGN.md).

    If ``auto_requested`` is empty (no ``field_cuts``/``bit_cuts`` anywhere
    in ``kinematic_cuts`` -- every existing config), returns
    ``(extra_object_fields, {})`` with ``merged`` being the exact same
    object passed in, unchanged: a complete no-op, nothing to log.
    """
    if not auto_requested:
        return extra_object_fields, {}
    merged = {name: list(fields) for name, fields in (extra_object_fields or {}).items()}
    newly_added: Dict[str, list] = {}
    for obj_name, fields in auto_requested.items():
        already_requested = merged.get(obj_name, [])
        added = [f for f in fields if f not in already_requested]
        if added:
            newly_added[obj_name] = added
        merged[obj_name] = list(dict.fromkeys(already_requested + fields))
    return merged, newly_added


def apply_parsing_event_selection(
    events: ak.Array,
    particle_counts: Optional[Dict[str, Any]] = None,
    kinematic_cuts: Optional[Dict[str, Any]] = None,
) -> ak.Array:
    """
    Kinematic cuts are applied per particle type first, then event-level count ranges.
    """
    if kinematic_cuts:
        by_obj: Dict[str, Dict[str, Any]] = {}
        for key, val in kinematic_cuts.items():
            if not isinstance(val, dict):
                continue
            cname = canonical_particle_field_name(key)
            by_obj[cname] = normalize_yaml_kinematic_cuts(val)
        events = physics_calcs.filter_events_by_kinematics(events, by_obj)

    if particle_counts:
        mapped: Dict[str, Any] = {}
        for key, val in particle_counts.items():
            cname = canonical_particle_field_name(key)
            mapped[cname] = val
        events = physics_calcs.filter_events_by_particle_counts(
            events,
            mapped,
            is_exact_count=False,
            is_particle_counts_range=True,
        )

    return events
