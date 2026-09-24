"""
Implementation task 6, Part 4 (REVISED 16 Sep 2026): end-to-end round trip
for studies/hgg_cms/cluster/run_zee_selection_on_chunks.py's REVISED
design -- one stored 60-180 GeV window, both trigger bits always
recorded, and (DY only) the electron-veto-leakage estimate against the
REAL main H->gamma-gamma selection.
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
    compute_hgg_veto_leakage, process_one_chunk, resolve_cern_input_files,
)

ELE27 = "HLT_Ele27_WPTight_Gsf"
DIPHOTON = "HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"


def _write_synthetic_zee_chunk(path: Path, n_events: int, is_data: bool, rng) -> None:
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
        veto = rng.uniform(0, 1, n) < 0.5  # mixed electronVeto True/False, as real chunks are now
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
        "source_record": ak.Array(np.full(n_events, (30529 if is_data else 35669), dtype=np.int64)),
        # Both trigger bits, as both new configs always attach them.
        ELE27: ak.Array(rng.uniform(0, 1, n_events) < 0.5),
        DIPHOTON: ak.Array(rng.uniform(0, 1, n_events) < 0.3),
    }
    if not is_data:
        fields["genWeight"] = ak.Array(rng.choice([1.0, -1.0], n_events, p=[0.95, 0.05]))
        fields["Pileup_nTrueInt"] = ak.Array(rng.uniform(10.0, 40.0, n_events))

    with uproot.recreate(str(path)) as f:
        f["events"] = fields


class RunZeeSelectionOnChunksRoundtripTests(unittest.TestCase):
    def test_data_chunk_stores_full_60_180_window_and_both_trigger_bits(self):
        rng = np.random.default_rng(101)
        with tempfile.TemporaryDirectory() as tmp:
            chunk_path = Path(tmp) / "chunk_0.root"
            _write_synthetic_zee_chunk(chunk_path, n_events=500, is_data=True, rng=rng)
            out_dir = Path(tmp) / "selected"
            out_dir.mkdir()
            res = process_one_chunk(chunk_path, out_dir, record_id=None, is_data=True,
                                     mass_lo=60.0, mass_hi=180.0)
            self.assertEqual(res["n_written"], res["cutflow"]["n_selected"])
            out = uproot.open(str(res["output"]))["events"].arrays(library="ak")
            if len(out) > 0:
                mgg = ak.to_numpy(out["m_ee"])
                self.assertTrue(((mgg > 60.0) & (mgg < 180.0)).all())
                self.assertIn("passes_ele27_hlt", out.fields)
                self.assertIn("passes_diphoton_hlt", out.fields)
                self.assertEqual(ak.to_numpy(out["passes_ele27_hlt"]).dtype, np.dtype(bool))
                self.assertEqual(ak.to_numpy(out["passes_diphoton_hlt"]).dtype, np.dtype(bool))
            self.assertIsNone(res["hgg_veto_leakage"])  # data -- leakage is DY-only

    def test_missing_trigger_branch_raises_clear_error(self):
        rng = np.random.default_rng(103)
        with tempfile.TemporaryDirectory() as tmp:
            chunk_path = Path(tmp) / "chunk_0.root"
            # Write a chunk WITHOUT the diphoton bit -- simulates a
            # misconfigured run (trigger_requirements.paths missing an
            # entry) rather than the real, correctly-configured case.
            n = 50
            photons = ak.zip({
                "pt": ak.Array([[40.0, 35.0]] * n), "eta": ak.Array([[0.1, -0.1]] * n),
                "phi": ak.Array([[0.0, 1.0]] * n), "hoe": ak.Array([[0.01, 0.01]] * n),
                "r9": ak.Array([[0.95, 0.95]] * n), "sieie": ak.Array([[0.01, 0.01]] * n),
                "pfRelIso03_all": ak.Array([[0.05, 0.05]] * n), "pfRelIso03_chg": ak.Array([[0.01, 0.01]] * n),
                "mvaID": ak.Array([[0.9, 0.9]] * n), "isScEtaEB": ak.Array([[True, True]] * n),
                "isScEtaEE": ak.Array([[False, False]] * n), "electronVeto": ak.Array([[False, False]] * n),
            })
            with uproot.recreate(str(chunk_path)) as f:
                f["events"] = {
                    "Photons": photons,
                    "run": ak.Array(np.ones(n, dtype=np.int64)),
                    "luminosityBlock": ak.Array(np.ones(n, dtype=np.int64)),
                    "event": ak.Array(np.arange(n, dtype=np.int64)),
                    "PV_npvsGood": ak.Array(np.full(n, 25, dtype=np.int64)),
                    "source_record": ak.Array(np.full(n, 30529, dtype=np.int64)),
                    ELE27: ak.Array(np.ones(n, dtype=bool)),
                    # DIPHOTON deliberately omitted
                }
            out_dir = Path(tmp) / "selected"
            out_dir.mkdir()
            with self.assertRaises(ValueError):
                process_one_chunk(chunk_path, out_dir, record_id=None, is_data=True,
                                   mass_lo=60.0, mass_hi=180.0)

    def test_dy_chunk_computes_veto_leakage_estimate(self):
        rng = np.random.default_rng(107)
        with tempfile.TemporaryDirectory() as tmp:
            chunk_path = Path(tmp) / "chunk_0.root"
            _write_synthetic_zee_chunk(chunk_path, n_events=2000, is_data=False, rng=rng)
            out_dir = Path(tmp) / "selected"
            out_dir.mkdir()
            res = process_one_chunk(chunk_path, out_dir, record_id=None, is_data=False,
                                     mass_lo=60.0, mass_hi=180.0)
            self.assertIsNotNone(res["hgg_veto_leakage"])
            leakage = res["hgg_veto_leakage"]
            for window in ("100_105", "105_110", "110_115", "135_180"):
                for cat in ("inclusive", "EBEB", "notEBEB"):
                    key = f"{window}_{cat}"
                    self.assertIn(f"n_selected_{key}", leakage)
                    self.assertIn(f"sum_genWeight_{key}", leakage)
                    self.assertIn(f"sum_genWeight_sq_{key}", leakage)
                    self.assertGreaterEqual(leakage[f"n_selected_{key}"], 0)
                    self.assertGreaterEqual(leakage[f"sum_genWeight_sq_{key}"], 0)
            # inclusive must equal EBEB + notEBEB for every window (a pure
            # partition of the same selected events)
            for window in ("100_105", "105_110", "110_115", "135_180"):
                incl = leakage[f"n_selected_{window}_inclusive"]
                eb = leakage[f"n_selected_{window}_EBEB"]
                noteb = leakage[f"n_selected_{window}_notEBEB"]
                self.assertEqual(incl, eb + noteb)

    def test_dy_job_metadata_has_leakage_key_data_job_does_not(self):
        rng = np.random.default_rng(109)
        with tempfile.TemporaryDirectory() as tmp:
            # DY
            dy_chunk = Path(tmp) / "dy" / "chunk_0.root"
            dy_chunk.parent.mkdir(parents=True)
            _write_synthetic_zee_chunk(dy_chunk, n_events=300, is_data=False, rng=rng)
            dy_out = Path(tmp) / "dy" / "selected"
            dy_out.mkdir()
            dy_cache = Path(tmp) / "dy" / "metadata_cache.json"
            dy_cache.write_text(json.dumps({"record_35669": ["urlA"]}), encoding="utf-8")

            import sys
            from studies.hgg_cms.cluster import run_zee_selection_on_chunks as mod
            argv_backup = sys.argv
            try:
                sys.argv = [
                    "run_zee_selection_on_chunks.py",
                    "--chunks-dir", str(dy_chunk.parent),
                    "--output-dir", str(dy_out),
                    "--is-data", "false",
                    "--config", "config.cms_hgg_zee_dy.yaml",
                    "--metadata-cache-json", str(dy_cache),
                ]
                mod.main()
            finally:
                sys.argv = argv_backup

            meta = json.loads((dy_out / "job_metadata.json").read_text(encoding="utf-8"))
            self.assertIn("hgg_veto_leakage_estimate", meta)
            self.assertIn("cern_input_files", meta)
            self.assertEqual(meta["cern_input_files"], ["urlA"])


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
