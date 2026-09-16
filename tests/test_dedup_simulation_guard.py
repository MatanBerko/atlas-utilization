"""
Implementation task 6 (review addition): de-duplication must never run on
simulation events.

De-duplication is switched on run-wide by the presence of ANY
selection_by_record entry (orchestration/handlers/parsing_handler.py:244:
``deduplicator = EventDeduplicator() if sel_by_record else None``), then
applied unconditionally to EVERY record's batches in that same run
(parsing_handler.py's per-batch loop checks only ``deduplicator is not
None``, not "is this specific record the one selection_by_record is
about"). So a run that combined a trigger-stream-combined data record
(needing selection_by_record) with a simulation record would otherwise
silently apply cross-trigger-stream de-duplication to the simulation too
-- simulated NanoAOD sets run==1 for every event and (luminosityBlock,
event) can repeat across different samples/files, so dedup's assumption
that this triple is a genuine unique event identifier is false for
simulation, and it would silently delete real signal events.
"""
from __future__ import annotations

import tempfile
import unittest

import awkward as ak

from domain.config import ParsingConfig, PipelineConfig, TaskConfig
from domain.events import EventBatch
from orchestration.context import PipelineContext
from orchestration.handlers.parsing_handler import ParsingHandler
from orchestration.states import PipelineState
from services.parsing.event_accumulator import EventAccumulator


class _StubProcessor:
    """Yields one fixed batch of events, calling on_success once, mimicking
    ThreadedFileProcessor.process_files's interface just enough for
    ParsingHandler.handle() to run its own logic against real events."""

    def __init__(self, events):
        self._events = events

    def process_files(self, file_urls, tree_names, release_year, **kwargs):
        on_success = kwargs.get("on_success")
        batch = EventBatch(
            events=self._events, file_id=1, release_year=release_year,
            size_bytes=0, event_count=len(self._events), processing_time_sec=0.1,
        )
        if on_success:
            on_success(file_urls[0], batch.event_count, 0.1)
        yield batch


def _make_config(tmp_dir, selection_by_record):
    return PipelineConfig(
        tasks=TaskConfig(do_parsing=True),
        parsing_config=ParsingConfig(
            output_path=tmp_dir,
            file_urls_path=tmp_dir,
            jobs_logs_path=tmp_dir,
            specific_record_ids=(12345,),
            selection_by_record=selection_by_record,
            show_progress_bar=False,
        ),
    )


class DedupSimulationGuardTests(unittest.TestCase):
    def _run(self, events, selection_by_record):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = _make_config(tmp_dir, selection_by_record)
            context = PipelineContext(
                config=config,
                current_state=PipelineState.PARSING,
                metadata={"record_12345": ["fake.root"]},
            )
            handler = ParsingHandler(
                file_parser=None,
                threaded_processor=_StubProcessor(events),
                event_accumulator=EventAccumulator(chunk_threshold_bytes=10 ** 9),
            )
            return handler.handle(context)

    def test_dedup_on_simulation_events_raises(self):
        sim_events = ak.zip({
            "Photons": ak.Array([[{"pt": 30.0}], [{"pt": 25.0}]]),
            "run": ak.Array([1, 1]),
            "luminosityBlock": ak.Array([1, 1]),
            "event": ak.Array([100, 200]),
            "genWeight": ak.Array([1.0, 1.0]),
        }, depth_limit=1)

        with self.assertRaises(RuntimeError) as ctx:
            self._run(sim_events, selection_by_record={"12345": {"particle_counts": {"photons": {"min": 1, "max": 10}}}})
        self.assertIn("simulation", str(ctx.exception).lower())
        self.assertIn("12345", str(ctx.exception))

    def test_dedup_on_real_data_events_unaffected(self):
        data_events = ak.zip({
            "Photons": ak.Array([[{"pt": 30.0}], [{"pt": 25.0}]]),
            "run": ak.Array([278820, 278820]),
            "luminosityBlock": ak.Array([1, 2]),
            "event": ak.Array([100, 200]),
        }, depth_limit=1)

        # Should NOT raise -- dedup runs normally on real data.
        updated_context, _ = self._run(
            data_events, selection_by_record={"12345": {"particle_counts": {"photons": {"min": 1, "max": 10}}}}
        )
        self.assertIsNotNone(updated_context.parsing_stats)

    def test_dedup_off_entirely_when_no_selection_by_record(self):
        """Sanity: the H->gamma-gamma configs (neither uses
        selection_by_record) never even reach the guard -- dedup is simply
        never constructed."""
        sim_events = ak.zip({
            "Photons": ak.Array([[{"pt": 30.0}], [{"pt": 25.0}]]),
            "run": ak.Array([1, 1]),
            "luminosityBlock": ak.Array([1, 1]),
            "event": ak.Array([100, 200]),
            "genWeight": ak.Array([1.0, 1.0]),
        }, depth_limit=1)

        # No selection_by_record at all -> deduplicator is None -> no raise,
        # even though these events look like simulation.
        updated_context, _ = self._run(sim_events, selection_by_record=None)
        self.assertIsNotNone(updated_context.parsing_stats)


if __name__ == "__main__":
    unittest.main()
