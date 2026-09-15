"""
Optional HLT trigger requirement filter.

Implementation task 3 (studies/hgg_cms/DESIGN_SELECTION.md, Section 6.2 /
Section 8 task 3): keep only events where one or more configured trigger
bits fired. Config key ``parsing_task_config.trigger_requirements`` (or a
per-record override under ``selection_by_record[record]["trigger_requirements"]``,
see orchestration/handlers/parsing_handler.py), e.g.::

    trigger_requirements:
      mode: any            # "any": at least one path fired. "all": every path fired.
      paths:
        - HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90

Absent/None (the default, and every current config) is a complete no-op.

Unlike ``validated_runs.py``, this has NO simulation guard: the design
requires the same trigger bit in simulation as in data (Section 2 step 1),
so this filter is meant to run on both.

The listed paths are attached to parsed events via the general scalar-branch-
group mechanism from implementation task 1 (see
``services.parsing.file_parser.FileParser._resolve_scalar_groups``), under
the group name ``"Trigger"`` -- callers should not need to also list them in
``extra_scalar_branches``. Booleans in NanoAOD are read back as numpy
``bool_`` by uproot/awkward; ``apply_trigger_requirement`` coerces
defensively with ``astype(bool)`` in case a caller feeds it a differently
typed array (e.g. from a non-NanoAOD source), which is a no-op for an
already-boolean array.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import awkward as ak
import numpy as np

VALID_MODES = ("any", "all")


def validate_trigger_requirements(spec: Dict[str, Any]) -> None:
    """Raise ValueError on a malformed ``trigger_requirements`` config block.

    Used both for the global ``parsing_task_config.trigger_requirements`` key
    and for a per-record ``selection_by_record[...]["trigger_requirements"]``
    override (the latter is not covered by ``ParsingConfig``'s own
    ``__post_init__`` validation, since ``selection_by_record`` profiles are
    freeform dicts -- see orchestration/handlers/parsing_handler.py).
    """
    if not isinstance(spec, dict):
        raise ValueError(f"trigger_requirements must be a dict, got {spec!r}")
    mode = spec.get("mode", "any")
    if mode not in VALID_MODES:
        raise ValueError(
            f"trigger_requirements['mode'] must be one of {VALID_MODES}, got {mode!r}"
        )
    paths = spec.get("paths")
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError(
            "trigger_requirements['paths'] must be a non-empty list of branch name strings"
        )
    if not all(isinstance(p, str) and p for p in paths):
        raise ValueError(
            f"trigger_requirements['paths'] entries must be non-empty strings, got {paths!r}"
        )


def trigger_group_branches(spec: Dict[str, Any]) -> List[str]:
    """De-duplicated branch list for the ``"Trigger"`` scalar branch group."""
    return list(dict.fromkeys(spec["paths"]))


def apply_trigger_requirement(
    events: ak.Array, spec: Dict[str, Any]
) -> Tuple[ak.Array, Dict[str, Any]]:
    """
    Keep only events passing the configured trigger requirement.

    ``mode == "any"``: at least one of ``paths`` is True.
    ``mode == "all"``: every one of ``paths`` is True.

    Applies to data AND simulation alike -- no simulation guard (contrast
    with ``services.parsing.validated_runs.apply_validated_runs_filter``).

    Returns ``(filtered_events, stats)`` where ``stats`` has ``"n_before"``,
    ``"n_after"``, ``"mode"``, and ``"per_path"`` (``{path: n_passed}``,
    counted within this batch, before the combined mode is applied).

    Raises:
        ValueError: any listed path is not present as a top-level field on
            ``events`` (e.g. the "Trigger" scalar branch group was not
            attached -- normally this cannot happen when the pipeline itself
            resolves the group, since ``FileParser`` raises a loud,
            non-swallowed error earlier for a file missing a declared
            branch; this check exists for direct/unit-test callers of this
            function and as a defensive backstop).
    """
    paths = trigger_group_branches(spec)
    mode = spec.get("mode", "any")

    missing = [p for p in paths if p not in events.fields]
    if missing:
        raise ValueError(
            f"trigger_requirements is set but the parsed events are missing "
            f"trigger branch(es) {missing}; expected these to already be "
            f"attached via the 'Trigger' scalar branch group"
        )

    per_path: Dict[str, int] = {}
    masks = []
    for p in paths:
        arr = ak.to_numpy(events[p]).astype(bool)
        per_path[p] = int(arr.sum())
        masks.append(arr)

    combined = masks[0]
    for m in masks[1:]:
        combined = (combined | m) if mode == "any" else (combined & m)

    n_before = len(events)
    filtered = events[combined]
    n_after = len(filtered)

    return filtered, {
        "n_before": n_before,
        "n_after": n_after,
        "mode": mode,
        "per_path": per_path,
    }
