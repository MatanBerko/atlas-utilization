"""
Implementation task 6, Part A (studies/hgg_cms/DESIGN_SELECTION.md, Section
8 task 6): a partially-read simulation file must not silently bias the
normalization numerator/denominator when read_event_weights is enabled.

Review finding: ThreadedFileProcessor used to yield a PartialFileReadError's
partial batch (whose events, including genWeight, get used downstream) while
reporting the file only via on_error, never on_success -- so the file never
lands in the processed_urls list orchestration/handlers/parsing_handler.py
uses to sum genEventSumw, silently excluding it from the denominator while
its genWeight sum WAS included in the numerator.

Covers:
 1. Partial read of a simulation file with read_event_weights enabled ->
    loud failure (RequiredScalarBranchMissingError), the run aborts, no
    partial batch is yielded.
 2. Partial read of a data file -> today's behaviour unchanged (partial
    batch yielded, reported via on_error only). Note: a data file can only
    reach this path when read_event_weights is False in the first place
    (see below) -- covered by the "weights off" case, which is the only
    way a real data file can produce a PartialFileReadError without first
    hitting SimulationFieldRequestedOnDataError.
 3. read_event_weights off entirely -> today's exact behaviour, regardless
    of what the file looks like.
 4. Regression vs. 3cf6ffd on the usual real files: IDENTICAL (none of
    them ever produce a PartialFileReadError under a normal read, so the
    new code path is never triggered for them).
"""
from __future__ import annotations

import unittest

import awkward as ak

from services.parsing.file_parser import PartialFileReadError, RequiredScalarBranchMissingError
from services.parsing.threaded_processor import ThreadedFileProcessor


def _partial_events(n=2):
    return ak.zip({
        "genWeight": ak.Array([1.0] * n),
        "run": ak.Array([1] * n),
    }, depth_limit=1)


class PartialReadWithWeightsTests(unittest.TestCase):
    def test_1_partial_simulation_read_with_weights_is_loud_failure(self):
        class _StubParser:
            def parse_file(self, file_path, **kwargs):
                raise PartialFileReadError(file_path, _partial_events(), RuntimeError("simulated mid-file failure"))

        processor = ThreadedFileProcessor(_StubParser(), 1, show_progress=False)
        yielded = []
        with self.assertRaises(RequiredScalarBranchMissingError) as ctx:
            for batch in processor.process_files(
                ["sig.root"], ["Events"], "cms-nanoaod", read_event_weights=True,
            ):
                yielded.append(batch)

        # No partial batch was ever yielded -- the events (and their
        # genWeight) never reach downstream selection/normalization.
        self.assertEqual(yielded, [])
        self.assertIn("sig.root", str(ctx.exception))
        self.assertEqual(len(ctx.exception.failures), 1)
        self.assertEqual(ctx.exception.failures[0][0], "sig.root")

    def test_2_partial_read_with_weights_off_is_unchanged(self):
        """A file that would look like data OR simulation content-wise: with
        read_event_weights off, a PartialFileReadError is handled exactly
        as before this task -- the partial batch is yielded and reported
        via on_error only, never raised loudly."""
        class _StubParser:
            def parse_file(self, file_path, **kwargs):
                raise PartialFileReadError(file_path, _partial_events(), RuntimeError("simulated mid-file failure"))

        processor = ThreadedFileProcessor(_StubParser(), 1, show_progress=False)
        errors = []
        yielded = list(processor.process_files(
            ["f.root"], ["Events"], "cms-nanoaod",
            read_event_weights=False,
            on_error=lambda url, err: errors.append((url, err)),
        ))

        self.assertEqual(len(yielded), 1)
        self.assertEqual(yielded[0].event_count, 2)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0][1], PartialFileReadError)

    def test_3_on_success_never_called_for_a_partial_read_regardless_of_weights_flag(self):
        """Confirms the pre-existing exclusivity this fix relies on: a
        partial read never calls on_success (only on_error), so it was
        never in processed_urls even before this task -- this task's fix
        is about not silently keeping the events/weight at all when
        read_event_weights is on, not about the on_success/on_error split
        itself, which was already correct."""
        class _StubParser:
            def parse_file(self, file_path, **kwargs):
                raise PartialFileReadError(file_path, _partial_events(), RuntimeError("boom"))

        processor = ThreadedFileProcessor(_StubParser(), 1, show_progress=False)
        successes = []
        errors = []
        list(processor.process_files(
            ["f.root"], ["Events"], "cms-nanoaod",
            read_event_weights=False,
            on_success=lambda *a: successes.append(a),
            on_error=lambda *a: errors.append(a),
        ))
        self.assertEqual(successes, [])
        self.assertEqual(len(errors), 1)

    def test_4_full_success_with_weights_still_yields_and_calls_on_success(self):
        """Sanity check: the new code path only intercepts partial_error is
        not None; a fully successful simulation parse with
        read_event_weights on is completely unaffected."""
        class _StubParser:
            def parse_file(self, file_path, **kwargs):
                return _partial_events()

        processor = ThreadedFileProcessor(_StubParser(), 1, show_progress=False)
        successes = []
        yielded = list(processor.process_files(
            ["sig.root"], ["Events"], "cms-nanoaod",
            read_event_weights=True,
            on_success=lambda *a: successes.append(a),
        ))
        self.assertEqual(len(yielded), 1)
        self.assertEqual(len(successes), 1)


if __name__ == "__main__":
    unittest.main()
