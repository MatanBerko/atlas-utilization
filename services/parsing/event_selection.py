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

    return out


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
