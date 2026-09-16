"""
Implementation task 6, Part 4: end-to-end round trip for
studies/hgg_cms/cluster/run_zee_selection_on_chunks.py, using a SYNTHETIC
chunk ROOT file (same construction as
tests/test_run_selection_on_chunks_roundtrip.py's for the main
H->gamma-gamma driver), extended with an "electronVeto" photon field
(needed by the inverted-veto Z->ee selection) and, for the
trigger-efficiency-sample test, a synthetic diphoton-HLT-bit scalar
branch.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

from studies.hgg_cms.cluster.run_zee_selection_on_chunks import (
    process_one_chunk, resolve_cern_input_files,
)


def _write_synthetic_zee_chunk(path: Path, n_events: int, is_data: bool, rng,
                                include_diphoton_bit: bool = False) -> None:
    n_photons = rng.integers(2, 4, n_events)
    pt, eta, phi, hoe, r9, sieie, iso_all, iso_chg, mvaid, eb, ee, evtoveto = (
        [[] for _ in range(12)]
    )
    for n in n_photons:
        good = rng.uniform() < 0.6
        if good:
            ptv = np.sort(rng.uniform(30.0, 60.0, n))[::-1].copy()
            r9v, hoev, sieiev = np.full(n, 0.95), np.full(n, 0.02), np.full(n, 0.01)
            isoallv, isochgv = np.full(n, 0.05), np.full(n, 0.01)
        else:
            ptv = rng.uniform(20.0, 40.0, n)
            r9v, hoev, sieiev = rng.uniform(0.1, 0.4, n), rng.uniform(0.1, 0.3, n), rng.uniform(0.05, 0.1, n)
            isoallv, isochgv = rng.uniform(0.5, 1.0, n), rng.uniform(0.4, 0.9, n)
        is_eb = rng.uniform(0, 1, n) < 0.5
        # Electron-like objects (electronVeto == False) mixed in, as a
        # Z->ee sample would have -- roughly half the "good" photons.
        veto = rng.uniform(0, 1, n) < 0.5
        for lst, v in [(pt, ptv), (eta, rng.uniform(-2, 2, n)), (phi, rng.uniform(-np.pi, np.pi, n)),
                       (hoe, hoev), (r9, r9v), (sieie, sieiev), (iso_all, isoallv), (iso_chg, isochgv),
                       (mvaid, np.full(n, 0.9)), (eb, is_eb), (ee, ~is_eb), (evtoveto, veto)]:
            lst.append(list(v))

    photons = ak.zip({
        "pt": ak.Array(pt), "eta": ak.Array(eta), "phi": ak.Array(phi),
        "hoe": ak.Array(hoe), "r9": ak.Array(r9), "sieie": ak.Array(sieie),
        "pfRelIso03_all": ak.Array(iso_all), "pfRelIso03_chg": ak.Array(iso_chg),
        "mvaID": ak.Array(mvaid), "isScEtaEB": ak.Array(eb), "isScEtaEE": ak.Array(ee),
        "electronVeto": ak.Array(evtoveto),
    })

    fields = {
        "Photons": photons,
        "run": ak.Array(np.arange(1, n_events + 1, dtype=np.int64) if is_data
                         else np.ones(n_events, dtype=np.int64)),
        "luminosityBlock": ak.Array(np.ones(n_events, dtype=np.int64)),
        "event": ak.Array(np.arange(n_events, dtype=np.int64)),
        "PV_npvsGood": ak.Array(np.full(n_events, 25, dtype=np.int64)),
        "source_record": ak.Array(np.full(n_events, 35669, dtype=np.int64)),
    }
    if not is_data:
        fields["genWeight"] = ak.Array(rng.choice([1.0, -1.0], n_events, p=[0.95, 0.05]))
        fields["Pileup_nTrueInt"] = ak.Array(rng.uniform(10.0, 40.0, n_events))
    if include_diphoton_bit:
        fields["HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"] = ak.Array(
            rng.uniform(0, 1, n_events) < 0.3
        )

    with uproot.recreate(str(path)) as f:
        f["events"] = fields


class RunZeeSelectionOnChunksRoundtripTests(unittest.TestCase):
    def test_data_chunk_roundtrip_no_exceptions(self):
        rng = np.random.default_rng(11)
        with tempfile.TemporaryDirectory() as tmp:
            chunk_path = Path(tmp) / "chunk_0.root"
            _write_synthetic_zee_chunk(chunk_path, n_events=400, is_data=True, rng=rng)
            out_dir = Path(tmp) / "selected"
            out_dir.mkdir()
            res = process_one_chunk(chunk_path, out_dir, record_id=None, is_data=True,
                                     mass_lo=70.0, mass_hi=110.0)
            self.assertGreater(res["cutflow"]["n_input_events_in_chunk"], 0)
            self.assertEqual(res["n_written"], res["cutflow"]["n_selected"])
            out = uproot.open(str(res["output"]))["events"].arrays(library="ak")
            if len(out) > 0:
                mgg = ak.to_numpy(out["m_ee"])
                self.assertTrue(((mgg > 70.0) & (mgg < 110.0)).all())

    def test_signal_chunk_roundtrip_no_exceptions(self):
        rng = np.random.default_rng(13)
        with tempfile.TemporaryDirectory() as tmp:
            chunk_path = Path(tmp) / "chunk_0.root"
            _write_synthetic_zee_chunk(chunk_path, n_events=400, is_data=False, rng=rng)
            out_dir = Path(tmp) / "selected"
            out_dir.mkdir()
            res = process_one_chunk(chunk_path, out_dir, record_id=None, is_data=False,
                                     mass_lo=70.0, mass_hi=110.0)
            self.assertIn("sum_genWeight_input", res["cutflow"])
            out = uproot.open(str(res["output"]))["events"].arrays(library="ak")
            self.assertIn("genWeight", out.fields)
            self.assertNotIn("m_gg", out.fields)  # renamed field, never m_gg

    def test_trigeff_sample_records_diphoton_bit_without_filtering(self):
        rng = np.random.default_rng(17)
        with tempfile.TemporaryDirectory() as tmp:
            chunk_path = Path(tmp) / "chunk_0.root"
            _write_synthetic_zee_chunk(chunk_path, n_events=500, is_data=True, rng=rng,
                                        include_diphoton_bit=True)
            out_dir = Path(tmp) / "selected"
            out_dir.mkdir()
            res = process_one_chunk(
                chunk_path, out_dir, record_id=None, is_data=True,
                mass_lo=95.0, mass_hi=None,
                diphoton_trigger_branch="HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90",
            )
            out = uproot.open(str(res["output"]))["events"].arrays(library="ak")
            self.assertIn("passes_diphoton_hlt", out.fields)
            if len(out) > 0:
                # Both True and False should be POSSIBLE (not filtered on) --
                # not asserting a specific mix (random), just that the field
                # exists and is boolean-typed.
                vals = ak.to_numpy(out["passes_diphoton_hlt"])
                self.assertEqual(vals.dtype, np.dtype(bool))
                mgg = ak.to_numpy(out["m_ee"])
                self.assertTrue((mgg > 95.0).all())

    def test_missing_diphoton_bit_raises_clear_error(self):
        rng = np.random.default_rng(19)
        with tempfile.TemporaryDirectory() as tmp:
            chunk_path = Path(tmp) / "chunk_0.root"
            _write_synthetic_zee_chunk(chunk_path, n_events=50, is_data=True, rng=rng,
                                        include_diphoton_bit=False)
            out_dir = Path(tmp) / "selected"
            out_dir.mkdir()
            with self.assertRaises(ValueError):
                process_one_chunk(
                    chunk_path, out_dir, record_id=None, is_data=True,
                    mass_lo=95.0, mass_hi=None,
                    diphoton_trigger_branch="HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90",
                )


class ResolveCernInputFilesTests(unittest.TestCase):
    def test_batched_job_returns_exactly_one_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "metadata_cache.json"
            cache_path.write_text(json.dumps({
                "record_30521": ["urlA", "urlB", "urlC"],
            }), encoding="utf-8")
            urls = resolve_cern_input_files(str(cache_path), batch_job_index=2, total_batch_jobs=3)
            self.assertEqual(urls, ["urlB"])

    def test_unbatched_job_returns_full_record_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "metadata_cache.json"
            cache_path.write_text(json.dumps({
                "record_35669": ["url1", "url2", "url3"],
            }), encoding="utf-8")
            urls = resolve_cern_input_files(str(cache_path), batch_job_index=None, total_batch_jobs=None)
            self.assertEqual(urls, ["url1", "url2", "url3"])


if __name__ == "__main__":
    unittest.main()
