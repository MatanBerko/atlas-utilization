"""
Cross-trigger-stream event de-duplication.

When the CMS SingleElectron and SingleMuon primary datasets from the same run
era are combined, an event that fired *both* an electron and a muon trigger is
legitimately present in both datasets. Combining the records without removing
those overlaps double-counts ~2% of events.

This keeps the FIRST copy of each real collision event seen and drops any later
copy, keyed on the CMS unique event id ``(run, luminosityBlock, event)``.
Priority is expressed by feed order: the caller processes the higher-priority
stream first (SingleMuon before SingleElectron), so the muon-stream copy of a
double-triggered event is the one that survives.

Scale note: ``_seen`` is a plain Python set of integer keys. At a few files per
record (verification scale) this is a few million entries and fine. At full
scale (~2e8 events) it would need a more memory-frugal structure (packed keys +
``np.unique`` per era); left as a follow-up.
"""

from __future__ import annotations

from typing import Tuple

import awkward as ak
import numpy as np


class EventDeduplicator:
    """Stateful across an entire parsing run. One instance per pipeline run."""

    ID_FIELDS: Tuple[str, ...] = ("run", "luminosityBlock", "event")

    def __init__(self) -> None:
        self._seen: set[int] = set()
        self.total_in = 0
        self.total_dropped = 0
        # dropped count broken down by run number (era-level reporting)
        self.dropped_by_run: dict[int, int] = {}

    def has_id_fields(self, events: ak.Array) -> bool:
        try:
            fields = set(events.fields)
        except Exception:
            return False
        return all(f in fields for f in self.ID_FIELDS)

    @staticmethod
    def _composite_keys(events: ak.Array) -> np.ndarray:
        """One exact integer key per event: run<<96 | luminosityBlock<<64 | event.

        Uses Python big-ints (object dtype) so the full 64-bit ``event`` value
        can never overflow or collide.
        """
        run = np.asarray(events["run"]).astype(object)
        lumi = np.asarray(events["luminosityBlock"]).astype(object)
        evt = np.asarray(events["event"]).astype(object)
        return (run << 96) | (lumi << 64) | evt

    def filter_new(self, events: ak.Array) -> Tuple[ak.Array, int]:
        """Return ``(events_not_seen_before, n_dropped)`` and update the seen set.

        A no-op (returns the input unchanged) when the id fields are absent, so
        it is always safe to call.
        """
        n = len(events)
        if n == 0 or not self.has_id_fields(events):
            return events, 0

        keys = self._composite_keys(events)
        seen = self._seen
        keep = np.ones(n, dtype=bool)
        # One pass: drop keys already seen in a previous batch (cross-stream
        # overlap) and keys repeated within this batch (keep first occurrence).
        batch_keys: set[int] = set()
        for i in range(n):
            k = keys[i]
            if k in seen or k in batch_keys:
                keep[i] = False
            else:
                batch_keys.add(k)
        seen.update(batch_keys)

        n_dropped = int((~keep).sum())
        self.total_in += n
        self.total_dropped += n_dropped
        if n_dropped:
            runs = np.asarray(events["run"])[~keep]
            for r in runs.tolist():
                self.dropped_by_run[int(r)] = self.dropped_by_run.get(int(r), 0) + 1

        return events[keep], n_dropped

    def summary(self) -> str:
        by_run = ", ".join(
            f"run {r}: {c}" for r, c in sorted(self.dropped_by_run.items())
        )
        return (
            f"de-duplication: {self.total_dropped} duplicate event(s) removed "
            f"of {self.total_in} seen"
            + (f" ({by_run})" if by_run else "")
        )
