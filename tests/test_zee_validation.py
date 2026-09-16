"""
Implementation task 6, Z->ee validation follow-up (17 Sep 2026): unit
tests for the Z->e+e- offline analysis package
(studies/hgg_cms/validation/zee/). Tests the CORE COMPUTATIONAL
functions directly against small synthetic awkward arrays / synthetic
parsed-chunk ROOT files -- not the real-file-loading main() entrypoints
(those need the real merged/parsed cluster output).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

from studies.hgg_cms.validation.zee import common as zc
from studies.hgg_cms.validation.zee.trigger_efficiency import (
    binomial_uncertainty, weighted_efficiency,
)
from studies.hgg_cms.validation.zee.hgg_leakage_estimate import (
    discover_job_indices, process_job,
)


def _make_zee_array(n, cat, mee, ele27, diphoton, is_data, genWeight=None):
    fields = {
        "category": ak.Array(list(cat)),
        "m_ee": ak.Array(np.asarray(mee, dtype=float)),
        zc.ELE27_FIELD: ak.Array(np.asarray(ele27, dtype=bool)),
        zc.DIPHOTON_FIELD: ak.Array(np.asarray(diphoton, dtype=bool)),
    }
    if not is_data:
        fields["genWeight"] = ak.Array(np.asarray(genWeight if genWeight is not None else np.ones(n), dtype=float))
    return ak.zip(fields, depth_limit=1)


class MaskHelperTests(unittest.TestCase):
    def setUp(self):
        # 6 events: mixed category / mee / trigger-bit combinations.
        self.arr = _make_zee_array(
            6,
            cat=["EBEB", "EBEB", "notEBEB", "notEBEB", "EBEB", "notEBEB"],
            mee=[91.0, 65.0, 91.0, 96.0, 111.0, 91.0],
            ele27=[True, True, False, True, True, False],
            diphoton=[True, False, True, True, True, True],
            is_data=True,
        )

    def test_energy_scale_mask_requires_ele27_and_window(self):
        mask = zc.energy_scale_selection_mask(self.arr)
        self.assertEqual(list(mask), [True, False, False, True, False, False])

    def test_trigger_eff_probe_mask_requires_ele27_and_mass_gt_95(self):
        mask = zc.trigger_eff_probe_mask(self.arr)
        self.assertEqual(list(mask), [False, False, False, True, True, False])

    def test_diphoton_only_mask_excludes_ele27_fired_events(self):
        mask = zc.diphoton_only_mask(self.arr)
        self.assertEqual(list(mask), [False, False, True, False, False, True])

    def test_relative_difference(self):
        self.assertAlmostEqual(zc.relative_difference(91.0, 90.0), (91.0 - 90.0) / 90.0)
        self.assertTrue(np.isnan(zc.relative_difference(1.0, 0.0)))


class WeightedStatTests(unittest.TestCase):
    def test_weighted_median_unweighted_matches_numpy(self):
        rng = np.random.default_rng(1)
        v = rng.uniform(0, 100, 5001)  # odd n -> exact median well-defined
        w = np.ones_like(v)
        self.assertAlmostEqual(zc.weighted_median(v, w), float(np.median(v)), delta=0.05)

    def test_weighted_mode_recovers_histogram_peak(self):
        v = np.concatenate([np.full(100, 5.0), np.random.default_rng(2).uniform(0, 10, 50)])
        w = np.ones_like(v)
        mode = zc.weighted_mode(v, w, bin_width=0.5, lo=0, hi=10)
        self.assertAlmostEqual(mode, 5.25, delta=0.5)  # bin containing the 5.0 spike


class UnbinnedEffectiveSigma68Tests(unittest.TestCase):
    def test_gaussian_recovers_true_sigma(self):
        rng = np.random.default_rng(3)
        true_sigma = 2.0
        v = rng.normal(100.0, true_sigma, 200000)
        w = np.ones_like(v)
        res = zc.unbinned_effective_sigma68(v, w)
        # For a symmetric unimodal (Gaussian) density, the shortest
        # interval containing 68.3% IS the standard +-1 sigma interval.
        self.assertAlmostEqual(res["sigma_eff68"], true_sigma, delta=0.05)

    def test_hand_derived_case_with_negative_weight(self):
        # values 0..4, weights [1,1,-1,1,1] (sum=3, target=0.683*3=2.049).
        # Hand-derived: the ONLY (i,j) pair reaching the target is the
        # full array (i=0,j=5): prefix=[0,1,2,1,2,3], and
        # prefix[5]-prefix[0]=3 >= 2.049 is the sole crossing -- every
        # other pair's diff is < 2.049. So the shortest window IS the
        # full 5-event array: width = 4-0 = 4, sigma_eff68 = 2.0.
        v = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        w = np.array([1.0, 1.0, -1.0, 1.0, 1.0])
        res = zc.unbinned_effective_sigma68(v, w)
        self.assertAlmostEqual(res["sigma_eff68"], 2.0, places=6)
        self.assertEqual(res["window_n_events"], 5)

    def test_uniform_positive_weights_four_of_five_needed(self):
        # values 0..4, all weight 1 (sum=5, target=3.415) -- need >= 4
        # consecutive events (since any 3 sum to 3 < 3.415). Any 4-in-a-row
        # window has width 3 (e.g. 0..3 or 1..4).
        v = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        w = np.ones(5)
        res = zc.unbinned_effective_sigma68(v, w)
        self.assertAlmostEqual(res["sigma_eff68"], 1.5, places=6)
        self.assertEqual(res["window_n_events"], 4)


class CrystalBallAndFitTests(unittest.TestCase):
    def test_crystal_ball_integrates_to_one(self):
        x = np.linspace(-30, 30, 200000)
        y = zc.crystal_ball_pdf(x, mu=0.0, sigma=2.0, alpha=1.5, n=3.0)
        integral = np.trapz(y, x)
        self.assertAlmostEqual(integral, 1.0, delta=0.01)

    def test_fit_recovers_injected_smearing_on_synthetic_bw_conv_cb_sample(self):
        # Generate synthetic data by sampling true_mu/true_sigma smearing
        # convolved (numerically, via direct sampling) with the fixed BW --
        # approximate by: sample from a Gaussian approximation to BW near
        # M_Z, convolve is implicit through addition of independent
        # samples. This is a loose closure test (not exact), just checking
        # the fit converges near the injected width, not exploding.
        rng = np.random.default_rng(4)
        n = 200000
        # crude physical toy: mass = M_Z + BW-like fluctuation (Cauchy
        # with the PDG width) + Gaussian smearing (injected sigma).
        true_sigma = 1.8
        bw_sample = rng.standard_cauchy(n) * (zc.PDG_GAMMA_Z / 2.0) + zc.PDG_MZ
        smear = rng.normal(0.0, true_sigma, n)
        mass = bw_sample + smear
        mask = (mass > 80) & (mass < 100)
        fit = zc.fit_bw_conv_cb(mass[mask], np.ones(mask.sum()), lo=80.0, hi=100.0, bin_width=0.5, mc_samples=20)
        # sigma should land in the right ballpark (not a tight tolerance --
        # this toy sample isn't a perfect BW, just Cauchy-approximated).
        self.assertGreater(fit["sigma_GeV"], 0.5)
        self.assertLess(fit["sigma_GeV"], 4.0)
        self.assertGreater(fit["peak_GeV"], 85.0)
        self.assertLess(fit["peak_GeV"], 97.0)


class TriggerEfficiencyHelperTests(unittest.TestCase):
    def test_binomial_uncertainty_known_values(self):
        self.assertAlmostEqual(binomial_uncertainty(50, 100), np.sqrt(0.5 * 0.5 / 100))
        self.assertTrue(np.isnan(binomial_uncertainty(0, 0)))

    def test_weighted_efficiency_unweighted_matches_plain_fraction(self):
        mask = np.array([True, True, False, False, False])
        w = np.ones(5)
        res = weighted_efficiency(mask, w)
        self.assertAlmostEqual(res["efficiency"], 0.4)
        self.assertAlmostEqual(res["n_eff"], 5.0)


def _write_dy_chunk(path: Path, n_events: int, rng) -> None:
    """Synthetic parsed-chunk ROOT file matching the format
    orchestration/handlers/parsing_handler.py writes -- same construction
    as test_run_zee_selection_on_chunks_roundtrip.py's own fixture, kept
    small and local here so this test file has no cross-file coupling."""
    n_photons = rng.integers(2, 4, n_events)
    pt, eta, phi, hoe, r9, sieie, iso_all, iso_chg, mvaid, eb, ee, evtoveto = ([] for _ in range(12))
    for n in n_photons:
        ptv = np.sort(rng.uniform(30.0, 60.0, n))[::-1].copy()
        r9v, hoev, sieiev = np.full(n, 0.95), np.full(n, 0.02), np.full(n, 0.01)
        isoallv, isochgv = np.full(n, 0.05), np.full(n, 0.01)
        is_eb = rng.uniform(0, 1, n) < 0.5
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
        "run": ak.Array(np.ones(n_events, dtype=np.int64)),
        "luminosityBlock": ak.Array(np.ones(n_events, dtype=np.int64)),
        "event": ak.Array(np.arange(n_events, dtype=np.int64)),
        "PV_npvsGood": ak.Array(np.full(n_events, 25, dtype=np.int64)),
        "source_record": ak.Array(np.full(n_events, 35669, dtype=np.int64)),
        "genWeight": ak.Array(rng.choice([1.0, -1.0], n_events, p=[0.9, 0.1])),
        "Pileup_nTrueInt": ak.Array(rng.uniform(10.0, 40.0, n_events)),
    }
    with uproot.recreate(str(path)) as f:
        f["events"] = fields


class HggLeakageRecomputeTests(unittest.TestCase):
    def test_discover_job_indices(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "job_1").mkdir()
            (base / "job_2").mkdir()
            (base / "not_a_job").mkdir()
            self.assertEqual(discover_job_indices(base), [1, 2])

    def test_process_job_reads_parsed_chunks_and_sumw(self):
        rng = np.random.default_rng(21)
        with tempfile.TemporaryDirectory() as tmp:
            job_dir = Path(tmp) / "job_1"
            chunks_dir = job_dir / "parsed_data"
            chunks_dir.mkdir(parents=True)
            _write_dy_chunk(chunks_dir / "chunk_0.root", 3000, rng)

            logs_dir = job_dir / "logs"
            logs_dir.mkdir()
            (logs_dir / "parsing_stats_batch_1.json").write_text(json.dumps({
                "sumw_by_record": {"record_35669": {"genEventSumw": 12345.0}}
            }), encoding="utf-8")

            res = process_job(job_dir, 1)
            self.assertEqual(res["n_chunks_found"], 1)
            self.assertEqual(res["n_chunks_with_genweight"], 1)
            self.assertEqual(res["genEventSumw"], 12345.0)
            # every window/category combo present
            for window in ("100_105", "105_110", "110_115", "135_180"):
                for cat in ("inclusive", "EBEB", "notEBEB"):
                    self.assertIn(f"n_selected_{window}_{cat}", res["leakage_totals"])
                    self.assertIn(f"sum_genWeight_sq_{window}_{cat}", res["leakage_totals"])

    def test_process_job_missing_chunks_dir_returns_zero_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            job_dir = Path(tmp) / "job_1"
            job_dir.mkdir()
            res = process_job(job_dir, 1)
            self.assertEqual(res["n_chunks_found"], 0)
            self.assertEqual(res["leakage_totals"], {})
            self.assertIsNone(res["genEventSumw"])


if __name__ == "__main__":
    unittest.main()
