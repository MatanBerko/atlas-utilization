"""
Implementation task 6, Part E: end-to-end round trip for
studies/hgg_cms/cluster/run_selection_on_chunks.py, using a SYNTHETIC
chunk ROOT file written the exact same way
orchestration/handlers/parsing_handler.py's _save_chunk_to_root writes a
real one (a dict of top-level awkward fields, "Photons" included as a
nested/jagged record field, handed straight to uproot).

This exists because a local dry run of the full Part E pipeline on a
synthetic chunk (not exercised by any other test, since
tests/test_output_blinding.py builds its output table directly, bypassing
read_chunk/build_output_table entirely) caught two real bugs that would
otherwise have first surfaced on the actual cluster run:

  1. uproot's ROOT writer SPLITS a nested/jagged record field into flat
     "nPhotons" + "Photons_<field>" branches on disk (the same convention
     real NanoAOD files use) -- reading them back with a plain
     ``.arrays(library="ak")`` does NOT reconstruct a nested "Photons"
     field, it returns 17 flat top-level fields instead (confirmed:
     ``FieldNotFoundError: no field 'Photons' in record with 17
     fields``). run_selection_on_chunks.read_chunk must re-zip them.

  2. studies.hgg_cms.selection.leading_pair_mass's lead/sublead come from
     ak.pad_none, so every field on them carries an option ("?float64")
     type even after masking down to events that provably have no
     missing pair (has_pair=True for every selected event) -- and
     uproot's ROOT writer refuses to write an option-typed numeric branch
     at all (confirmed: ``TypeError: cannot write Awkward Array type to
     ROOT file: ?float64``). studies.hgg_cms.output.build_output_table
     must ak.drop_none() lead/sublead before writing.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

from studies.hgg_cms.cluster.run_selection_on_chunks import process_one_chunk


def _write_synthetic_chunk(path: Path, n_events: int, is_data: bool, rng) -> None:
    """Mirrors orchestration/handlers/parsing_handler.py's
    _save_chunk_to_root: a dict of top-level fields (including a nested
    jagged "Photons" record) handed straight to uproot.recreate."""
    n_photons = rng.integers(2, 4, n_events)
    pt, eta, phi, hoe, r9, sieie, iso_all, iso_chg, mvaid, eb, ee = (
        [[] for _ in range(11)]
    )
    for n in n_photons:
        good = rng.uniform() < 0.6
        if good:
            ptv = np.sort(rng.uniform(30.0, 80.0, n))[::-1].copy()
            r9v, hoev, sieiev = np.full(n, 0.95), np.full(n, 0.02), np.full(n, 0.01)
            isoallv, isochgv = np.full(n, 0.05), np.full(n, 0.01)
        else:
            ptv = rng.uniform(20.0, 40.0, n)
            r9v, hoev, sieiev = rng.uniform(0.1, 0.4, n), rng.uniform(0.1, 0.3, n), rng.uniform(0.05, 0.1, n)
            isoallv, isochgv = rng.uniform(0.5, 1.0, n), rng.uniform(0.4, 0.9, n)
        is_eb = rng.uniform(0, 1, n) < 0.5
        for lst, v in [(pt, ptv), (eta, rng.uniform(-2, 2, n)), (phi, rng.uniform(-np.pi, np.pi, n)),
                       (hoe, hoev), (r9, r9v), (sieie, sieiev), (iso_all, isoallv), (iso_chg, isochgv),
                       (mvaid, np.full(n, 0.9)), (eb, is_eb), (ee, ~is_eb)]:
            lst.append(list(v))

    photons = ak.zip({
        "pt": ak.Array(pt), "eta": ak.Array(eta), "phi": ak.Array(phi),
        "hoe": ak.Array(hoe), "r9": ak.Array(r9), "sieie": ak.Array(sieie),
        "pfRelIso03_all": ak.Array(iso_all), "pfRelIso03_chg": ak.Array(iso_chg),
        "mvaID": ak.Array(mvaid), "isScEtaEB": ak.Array(eb), "isScEtaEE": ak.Array(ee),
    })

    fields = {
        "Photons": photons,
        "run": ak.Array(np.arange(1, n_events + 1, dtype=np.int64) if is_data
                         else np.ones(n_events, dtype=np.int64)),
        "luminosityBlock": ak.Array(np.ones(n_events, dtype=np.int64)),
        "event": ak.Array(np.arange(n_events, dtype=np.int64)),
        "PV_npvsGood": ak.Array(np.full(n_events, 25, dtype=np.int64)),
        "source_record": ak.Array(np.full(n_events, 12345, dtype=np.int64)),
    }
    if not is_data:
        fields["genWeight"] = ak.Array(rng.choice([1.0, -1.0], n_events, p=[0.95, 0.05]))
        fields["Pileup_nTrueInt"] = ak.Array(rng.uniform(10.0, 40.0, n_events))

    with uproot.recreate(str(path)) as f:
        f["events"] = fields


class RunSelectionOnChunksRoundtripTests(unittest.TestCase):
    def test_data_chunk_roundtrip_no_exceptions(self):
        rng = np.random.default_rng(2024)
        with tempfile.TemporaryDirectory() as tmp:
            chunk_path = Path(tmp) / "chunk_0.root"
            _write_synthetic_chunk(chunk_path, n_events=150, is_data=True, rng=rng)
            out_dir = Path(tmp) / "selected"
            out_dir.mkdir()
            res = process_one_chunk(chunk_path, out_dir, record_id=None, is_data=True)
            self.assertGreater(res["cutflow"]["n_input_events_in_chunk"], 0)
            self.assertEqual(
                res["n_written_normal"] + res["n_written_blinded"],
                res["cutflow"]["n_selected"],
            )

    def test_signal_chunk_roundtrip_no_exceptions(self):
        rng = np.random.default_rng(7)
        with tempfile.TemporaryDirectory() as tmp:
            chunk_path = Path(tmp) / "chunk_0.root"
            _write_synthetic_chunk(chunk_path, n_events=150, is_data=False, rng=rng)
            out_dir = Path(tmp) / "selected"
            out_dir.mkdir()
            res = process_one_chunk(chunk_path, out_dir, record_id=None, is_data=False)
            self.assertGreater(res["cutflow"]["n_input_events_in_chunk"], 0)
            self.assertIn("sum_genWeight_input", res["cutflow"])
            self.assertEqual(res["n_written_blinded"], 0)  # simulation is never split


if __name__ == "__main__":
    unittest.main()
