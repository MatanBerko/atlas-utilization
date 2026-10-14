"""
CMS "golden JSON" validated-runs filtering.

A validated-runs (a.k.a. "golden JSON") file records which
(run, luminosity section) pairs were certified good for physics analysis
by CMS's Data Quality Monitoring group -- see
``data/cms/validated_runs/README.md`` for the specific file this project
ships, its source, and its checksum.

This module is deliberately separate from ``event_selection.py``: the
kinematic/particle-count cuts there are physics-analysis choices made per
config; this filter is a data-quality gate that either applies in full or
not at all, is loaded once from a fixed file, and -- critically -- must
never be silently applied to simulation (which has no real run number to
certify). Keeping it in its own module makes that distinction explicit
and keeps ``event_selection.py`` free of the golden-JSON-specific loading
and simulation-guard logic.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

import awkward as ak
import numpy as np

# services/parsing/validated_runs.py -> services/parsing -> services -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Composite (run, luminosityBlock) keys are packed as run << 32 | lumi into
# a single unsigned 64-bit integer for a fully vectorized membership test.
# CMS run numbers (~6 digits) and lumisection numbers (typically well under
# 100,000) both fit comfortably in 32 bits each, with no realistic risk of
# collision.
_LUMI_KEY_SHIFT = np.uint64(32)


def resolve_validated_runs_path(path: str) -> Path:
    """Resolve ``path`` as given (absolute) or relative to the repository root."""
    p = Path(path)
    return p if p.is_absolute() else (_REPO_ROOT / p)


def _validate_and_parse(raw_text: str, source: str) -> dict[int, list[tuple[int, int]]]:
    """
    Parse and validate a golden-JSON document's text.

    Expected format: a JSON object whose keys are run numbers written as
    strings, and whose values are lists of ``[first, last]`` two-element
    lists -- inclusive lumisection-number ranges for that run.

    Raises:
        ValueError: the text is not valid JSON, or does not match the
            expected shape, with a message identifying the specific
            problem (which run/entry) rather than a generic parse error.
    """
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"{source}: not valid JSON ({e})") from e

    if not isinstance(raw, dict):
        raise ValueError(f"{source}: expected a JSON object mapping run -> ranges, got {type(raw).__name__}")

    parsed: dict[int, list[tuple[int, int]]] = {}
    for run_key, ranges in raw.items():
        if not isinstance(run_key, str) or not run_key.isdigit():
            raise ValueError(f"{source}: run key {run_key!r} is not a run number written as a string")
        run = int(run_key)

        if not isinstance(ranges, list) or not ranges:
            raise ValueError(f"{source}: run {run}'s value must be a non-empty list of [first, last] ranges, got {ranges!r}")

        parsed_ranges = []
        for entry in ranges:
            if (
                not isinstance(entry, list)
                or len(entry) != 2
                or not all(isinstance(x, int) and not isinstance(x, bool) for x in entry)
            ):
                raise ValueError(f"{source}: run {run} has a malformed range entry {entry!r} (expected [first, last] integers)")
            first, last = entry
            if first < 0 or last < 0:
                raise ValueError(f"{source}: run {run} has a negative lumisection bound in {entry!r}")
            if first > last:
                raise ValueError(f"{source}: run {run} has first > last in range {entry!r}")
            parsed_ranges.append((first, last))
        parsed[run] = parsed_ranges

    return parsed


class ValidatedRunsFilter:
    """
    A loaded, validated golden-JSON file, ready for a fast vectorized
    (run, luminosityBlock) membership test.

    Load once per pipeline run (not once per file) and reuse across every
    file/batch -- construction reads and parses the whole JSON and builds
    a sorted array of certified composite keys, which is then cheap to
    query repeatedly.
    """

    def __init__(self, json_path: str):
        self.source_path = resolve_validated_runs_path(json_path)
        if not self.source_path.is_file():
            raise ValueError(
                f"validated_runs_json points at a file that does not exist: "
                f"{self.source_path} (given as {json_path!r})"
            )

        raw_bytes = self.source_path.read_bytes()
        self.sha256 = hashlib.sha256(raw_bytes).hexdigest()

        self.certified_ranges = _validate_and_parse(raw_bytes.decode("utf-8"), str(self.source_path))

        keys: list[int] = []
        for run, ranges in self.certified_ranges.items():
            run64 = np.uint64(run)
            for first, last in ranges:
                lumis = np.arange(first, last + 1, dtype=np.uint64)
                keys.append((run64 << _LUMI_KEY_SHIFT) | lumis)
        self.certified_keys = np.unique(np.concatenate(keys)) if keys else np.array([], dtype=np.uint64)

        self.n_runs = len(self.certified_ranges)
        self.n_certified_lumisections = int(len(self.certified_keys))

        logging.info(
            "Loaded validated-runs file %s (sha256=%s): %d runs, %d certified lumisections",
            self.source_path, self.sha256, self.n_runs, self.n_certified_lumisections,
        )

    def __repr__(self) -> str:
        return (
            f"ValidatedRunsFilter({self.source_path}, sha256={self.sha256[:12]}..., "
            f"{self.n_runs} runs, {self.n_certified_lumisections} certified lumisections)"
        )


def is_simulation(events: ak.Array) -> bool:
    """
    Best-effort detection of simulated (not real collision) events, used
    by the validated-runs filter's simulation guard.

    Two independent signals, either one sufficient:

    - a ``genWeight`` field is present. Unambiguous: only simulation has
      generator event weights. Not read by any default schema as of this
      task, but checked here in case a caller requested it via the
      general scalar-branch-group mechanism (see
      ``schemas.get_scalar_branch_groups`` / ``extra_scalar_branches``).
    - every event's ``run`` field equals 1. CMS's own convention:
      simulated NanoAOD always sets ``run=1`` for every event, since a
      simulated sample has no real accelerator run to record. This is the
      path actually exercised today, since ``genWeight`` isn't read by
      default.

    Returns ``False`` (i.e. "assume real data, let the caller's own
    missing-fields check fire instead") when ``run`` isn't present at all
    -- this function's job is only the simulation guard, not validating
    that the required fields exist.
    """
    if "genWeight" in events.fields:
        return True
    if "run" not in events.fields:
        return False
    run = ak.to_numpy(events["run"])
    if len(run) == 0:
        return False
    return bool(np.all(run == 1))


def apply_validated_runs_filter(
    events: ak.Array, validated_runs: ValidatedRunsFilter
) -> tuple[ak.Array, dict]:
    """
    Keep only events whose (run, luminosityBlock) falls inside a
    certified range in ``validated_runs``. Both range endpoints are
    inclusive, matching the golden-JSON format itself.

    Args:
        events: Already-parsed events with top-level ``run`` and
            ``luminosityBlock`` scalar fields (see
            ``schemas.get_scalar_branch_groups`` -- the built-in
            ``"EventIds"`` group provides these for CMS NanoAOD).
        validated_runs: A loaded ``ValidatedRunsFilter``.

    Returns:
        ``(filtered_events, stats)`` where ``stats`` has ``n_before``,
        ``n_after``, and ``per_run`` (``{run: {"before": n, "after": n}}``
        for every run present in ``events``).

    Raises:
        ValueError: ``events`` is missing ``run``/``luminosityBlock``
            (the filter would otherwise silently pass everything through
            unfiltered for a schema/release that doesn't expose per-event
            run identity, e.g. today's ATLAS schemas); or ``events`` looks
            like simulation (see ``is_simulation``) -- simulated NanoAOD
            has ``run == 1`` for every event, none of which is a real
            certified run, so applying this filter to simulation would
            silently discard the entire sample.
    """
    missing = [f for f in ("run", "luminosityBlock") if f not in events.fields]
    if missing:
        raise ValueError(
            f"validated_runs_json is set but the parsed events are missing "
            f"{missing}; this schema/release does not expose per-event "
            f"run/luminosityBlock identity, so the validated-runs filter "
            f"cannot be applied. Refusing to parse rather than silently "
            f"passing every event through unfiltered."
        )

    if is_simulation(events):
        raise ValueError(
            "validated_runs_json is set, but these events look like "
            "simulation: either a 'genWeight' field is present, or every "
            "event has run==1 (CMS's convention for simulated NanoAOD, "
            "which has no real accelerator run). The validated-runs "
            "filter is a data-quality concept for real collision data "
            "only -- applying it to simulation would silently discard "
            "every single event. Do not set validated_runs_json for a "
            "simulated input."
        )

    run = ak.to_numpy(events["run"]).astype(np.uint64)
    lumi = ak.to_numpy(events["luminosityBlock"]).astype(np.uint64)
    keys = (run << _LUMI_KEY_SHIFT) | lumi
    mask = np.isin(keys, validated_runs.certified_keys)

    n_before = len(events)
    filtered = events[mask]
    n_after = len(filtered)

    per_run: dict[int, dict[str, int]] = {}
    if n_before:
        runs_before, counts_before = np.unique(run, return_counts=True)
        for r, c in zip(runs_before.tolist(), counts_before.tolist()):
            per_run[r] = {"before": c, "after": 0}
        if n_after:
            runs_after, counts_after = np.unique(run[mask], return_counts=True)
            for r, c in zip(runs_after.tolist(), counts_after.tolist()):
                per_run[r]["after"] = c

    return filtered, {"n_before": n_before, "n_after": n_after, "per_run": per_run}
