"""
Statistical-model task, Part 5.1 fix (18 Sep 2026): unit tests for
`studies.hgg_cms.stats.unblind.merge_full_range.write_full_range_root`.

Written after a real crash on the actual gated merge: `f["events"] =
full` (a single zipped awkward record array) failed with `TypeError:
fields of a record must be NumPy types... field 'category' has type
string`, since `category` is a string field ("EBEB"/"notEBEB", see
`studies/hgg_cms/selection.py`). No data had been read for analysis and
no result had been produced or seen at the time -- only the write step
crashed, after the approval gate had already passed. Fixed by writing
a dict of per-field arrays instead (matching
`studies.hgg_cms.output._write_root_table`'s already-working
convention), not by changing what data is read or how it is selected.

These tests use only synthetic, fully-fabricated events -- never a
real or blinded data file.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import awkward as ak
import numpy as np
import uproot

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.stats.unblind.merge_full_range import write_full_range_root  # noqa: E402


def make_synthetic_table(n_ebeb: int, n_noteb: int) -> ak.Array:
    n = n_ebeb + n_noteb
    rng = np.random.default_rng(0)
    category = np.array(["EBEB"] * n_ebeb + ["notEBEB"] * n_noteb)
    m_gg = rng.uniform(105.0, 180.0, size=n)
    run = np.arange(1, n + 1, dtype=np.int64)
    event = rng.integers(0, 10_000_000, size=n, dtype=np.int64)
    is_data = np.ones(n, dtype=bool)
    return ak.zip({
        "m_gg": ak.Array(m_gg),
        "category": ak.Array(category),
        "run": ak.Array(run),
        "event": ak.Array(event),
        "is_data": ak.Array(is_data),
    }, depth_limit=1)


class WriteFullRangeRootTests(unittest.TestCase):
    def test_round_trip_preserves_every_field_value_and_order(self):
        table = make_synthetic_table(n_ebeb=37, n_noteb=53)
        with TemporaryDirectory() as d:
            out_path = Path(d) / "full_range.root"
            write_full_range_root(table, out_path)
            self.assertTrue(out_path.exists())

            read_back = uproot.open(str(out_path))["events"].arrays(library="ak")

            self.assertEqual(set(read_back.fields), set(table.fields))
            self.assertEqual(len(read_back), len(table))
            for field in table.fields:
                original = ak.to_list(table[field])
                roundtripped = ak.to_list(read_back[field])
                self.assertEqual(roundtripped, original, f"field {field!r} did not round-trip exactly")

    def test_category_values_and_counts_preserved(self):
        table = make_synthetic_table(n_ebeb=10, n_noteb=25)
        with TemporaryDirectory() as d:
            out_path = Path(d) / "full_range.root"
            write_full_range_root(table, out_path)
            read_back = uproot.open(str(out_path))["events"].arrays(library="ak")
            cats = ak.to_list(read_back["category"])
            self.assertEqual(cats.count("EBEB"), 10)
            self.assertEqual(cats.count("notEBEB"), 25)
            # order preserved exactly (not just counts)
            self.assertEqual(cats, ak.to_list(table["category"]))

    def test_concatenated_arrays_still_round_trip(self):
        """Mirrors the real usage: several small arrays (one per
        blinded job file) concatenated with a larger sideband array
        before writing -- concatenation can itself produce a layout
        (e.g. an IndexedArray) that the naive zipped-record write
        cannot handle even after packing a single source array."""
        parts = [make_synthetic_table(n_ebeb=3, n_noteb=2) for _ in range(5)]
        parts.append(make_synthetic_table(n_ebeb=100, n_noteb=150))
        full = ak.concatenate(parts)
        with TemporaryDirectory() as d:
            out_path = Path(d) / "full_range.root"
            write_full_range_root(full, out_path)
            read_back = uproot.open(str(out_path))["events"].arrays(library="ak")
            self.assertEqual(len(read_back), len(full))
            self.assertEqual(ak.to_list(read_back["category"]), ak.to_list(full["category"]))
            self.assertEqual(ak.to_list(read_back["m_gg"]), ak.to_list(full["m_gg"]))

    def test_this_is_the_bug_that_was_fixed(self):
        """Regression guard: the OLD approach (a single zipped record
        array passed directly to uproot) must still fail the way it
        did on the real cluster -- if some future uproot/awkward
        upgrade silently "fixes" this, this test starts failing and
        flags that the workaround might no longer be needed (not
        removed silently)."""
        table = make_synthetic_table(n_ebeb=2, n_noteb=2)
        with TemporaryDirectory() as d:
            out_path = Path(d) / "broken.root"
            with self.assertRaises(TypeError):
                with uproot.recreate(str(out_path)) as f:
                    f["events"] = table


if __name__ == "__main__":
    unittest.main()
