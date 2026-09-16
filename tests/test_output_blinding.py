"""
Implementation task 6, Part C/D4: per-event output writer and its blinding
guard.

Covers:
 - Data events with 115 <= m_gg <= 135 are written ONLY to the
   BLINDED_SIGNAL_REGION sibling file, never the normal output.
 - Simulation is never split (no blinding).
 - read_output refuses a BLINDED_SIGNAL_REGION file without unblind=True.
 - read_output asserts no data event in [115, 135] slipped into a file
   opened without unblind=True, even if the file weren't named with the
   marker (a second, independent check beyond the filename convention).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

from studies.hgg_cms.output import BLINDED_MARKER, read_output, write_event_output


def _make_table(is_data_flag, masses, run_offset=1):
    n = len(masses)
    table = {
        "record_id": ak.Array(np.full(n, 12345, dtype=np.int64)),
        "is_data": ak.Array(np.full(n, is_data_flag, dtype=bool)),
        "run": ak.Array(np.arange(run_offset, run_offset + n, dtype=np.int64)),
        "luminosityBlock": ak.Array(np.ones(n, dtype=np.int64)),
        "event": ak.Array(np.arange(n, dtype=np.int64)),
        "m_gg": ak.Array(np.array(masses, dtype=np.float64)),
        "category": ak.Array(["EBEB"] * n),
        "PV_npvsGood": ak.Array(np.full(n, 20, dtype=np.int64)),
    }
    return ak.zip(table, depth_limit=1)


class BlindingSplitTests(unittest.TestCase):
    def test_data_events_in_window_go_only_to_blinded_file(self):
        table = _make_table(True, [100.5, 120.0, 130.0, 150.0, 179.0])
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "output_run1.root"
            counts = write_event_output(table, out_path, is_data=True)

            self.assertEqual(counts["n_written_normal"], 3)  # 100.5, 150.0, 179.0
            self.assertEqual(counts["n_written_blinded"], 2)  # 120.0, 130.0

            normal = read_output(out_path)
            self.assertEqual(len(normal), 3)
            masses = sorted(ak.to_list(normal["m_gg"]))
            self.assertEqual(masses, [100.5, 150.0, 179.0])

            blinded_path = out_path.with_name(f"{out_path.stem}_{BLINDED_MARKER}{out_path.suffix}")
            self.assertTrue(blinded_path.exists())
            blinded = read_output(blinded_path, unblind=True)
            self.assertEqual(sorted(ak.to_list(blinded["m_gg"])), [120.0, 130.0])

    def test_simulation_never_split(self):
        table = _make_table(False, [100.5, 120.0, 130.0, 150.0])
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "output_sig.root"
            counts = write_event_output(table, out_path, is_data=False)
            self.assertEqual(counts["n_written_normal"], 4)
            self.assertEqual(counts["n_written_blinded"], 0)
            blinded_path = out_path.with_name(f"{out_path.stem}_{BLINDED_MARKER}{out_path.suffix}")
            self.assertFalse(blinded_path.exists())

            result = read_output(out_path)
            self.assertEqual(len(result), 4)
            self.assertEqual(sorted(ak.to_list(result["m_gg"])), [100.5, 120.0, 130.0, 150.0])


class BlindingGuardTests(unittest.TestCase):
    def test_refuses_blinded_file_without_unblind(self):
        table = _make_table(True, [120.0, 125.0])
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "data_run1.root"
            write_event_output(table, out_path, is_data=True)
            blinded_path = out_path.with_name(f"{out_path.stem}_{BLINDED_MARKER}{out_path.suffix}")

            with self.assertRaises(PermissionError):
                read_output(blinded_path)  # unblind defaults to False

            # Explicit unblind=True works.
            result = read_output(blinded_path, unblind=True)
            self.assertEqual(len(result), 2)

    def test_assertion_fires_even_without_the_filename_marker(self):
        """A data event with 115<=m_gg<=135 that somehow ended up in a
        normally-named file (not just the wrong filename) must still be
        caught -- the check is on CONTENT, not just the name."""
        table = _make_table(True, [120.0, 100.0])
        with tempfile.TemporaryDirectory() as tmp:
            # Write directly with uproot, bypassing write_event_output's own
            # split, to simulate a file that was (incorrectly) assembled
            # without going through the blinding split.
            sneaky_path = Path(tmp) / "sneaky_normal_name.root"
            with uproot.recreate(str(sneaky_path)) as f:
                f["events"] = {field: table[field] for field in table.fields}

            with self.assertRaises(AssertionError):
                read_output(sneaky_path)  # unblind=False (default)

            # With unblind=True, no assertion is raised (caller takes
            # responsibility).
            result = read_output(sneaky_path, unblind=True)
            self.assertEqual(len(result), 2)

    def test_simulation_only_file_never_triggers_blinding_assertion(self):
        table = _make_table(False, [120.0, 125.0])
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "sig_output.root"
            write_event_output(table, out_path, is_data=False)
            # No exception -- is_data is all False.
            result = read_output(out_path)
            self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
