"""
Implementation task 6, Part 4 (REVISED 16 Sep 2026): unit tests for the
Z->e+e- offline analysis package (studies/hgg_cms/validation/zee/). No
real merged Z->ee output exists (no cluster run has happened), so these
test the CORE COMPUTATIONAL functions directly against small synthetic
awkward arrays / synthetic job_metadata.json files -- not the file-
loading main() entrypoints, which need real merged ROOT output.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import awkward as ak
import numpy as np

from studies.hgg_cms.validation.zee import common as zc
from studies.hgg_cms.validation.zee.energy_scale import compare_peak_and_width
from studies.hgg_cms.validation.zee.trigger_efficiency import (
    binomial_uncertainty, trigger_efficiency_per_category,
)
from studies.hgg_cms.validation.zee.hgg_leakage_estimate import sum_leakage_and_sumw


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
        # event0: ele27 T, mee 91 in (70,110) -> True
        # event1: ele27 T, mee 65 NOT in window -> False
        # event2: ele27 F -> False
        # event3: ele27 T, mee 96 in window -> True
        # event4: ele27 T, mee 111 NOT in window -> False
        # event5: ele27 F -> False
        self.assertEqual(list(mask), [True, False, False, True, False, False])

    def test_trigger_eff_probe_mask_requires_ele27_and_mass_gt_95(self):
        mask = zc.trigger_eff_probe_mask(self.arr)
        # only event3 (ele27 T, mee=96>95); event4 has ele27 T mee=111>95 too
        self.assertEqual(list(mask), [False, False, False, True, True, False])

    def test_diphoton_only_mask_excludes_ele27_fired_events(self):
        mask = zc.diphoton_only_mask(self.arr)
        # needs diphoton T, ele27 F, mee in (70,110): event2 (91, ele27 F,
        # diphoton T) and event5 (91, ele27 F, diphoton T) both qualify.
        self.assertEqual(list(mask), [False, False, True, False, False, True])

    def test_relative_difference(self):
        self.assertAlmostEqual(zc.relative_difference(91.0, 90.0), (91.0 - 90.0) / 90.0)
        self.assertTrue(np.isnan(zc.relative_difference(1.0, 0.0)))


class PeakAndWidthTests(unittest.TestCase):
    def test_narrow_gaussian_like_peak_recovered(self):
        rng = np.random.default_rng(5)
        values = rng.normal(91.19, 2.0, 5000)
        mode, sigma = zc.peak_and_width(values)
        self.assertAlmostEqual(mode, 91.19, delta=1.0)
        self.assertGreater(sigma, 0.5)
        self.assertLess(sigma, 4.0)


class EnergyScaleComparisonTests(unittest.TestCase):
    def test_identical_data_and_dy_pass_both_criteria(self):
        rng = np.random.default_rng(11)
        n = 4000
        mee = rng.normal(91.19, 2.0, n)
        cat = rng.choice(["EBEB", "notEBEB"], n)
        ele27 = np.ones(n, dtype=bool)
        diphoton = np.zeros(n, dtype=bool)

        data_arr = _make_zee_array(n, cat, mee, ele27, diphoton, is_data=True)
        dy_arr = _make_zee_array(n, cat, mee, ele27, diphoton, is_data=False,
                                  genWeight=np.ones(n))

        per_cat = compare_peak_and_width(data_arr, dy_arr)
        for c in zc.CATEGORIES:
            self.assertTrue(per_cat[c]["overall_pass"], msg=f"{c}: {per_cat[c]}")
            self.assertLess(abs(per_cat[c]["peak_relative_difference"]), zc.PEAK_POSITION_AGREEMENT_REL_TOL)

    def test_shifted_dy_peak_fails_criterion(self):
        rng = np.random.default_rng(13)
        n = 4000
        cat = rng.choice(["EBEB", "notEBEB"], n)
        ele27 = np.ones(n, dtype=bool)
        diphoton = np.zeros(n, dtype=bool)

        data_mee = rng.normal(91.19, 2.0, n)
        # DY shifted by 3 GeV -- far more than 0.5% of 91 GeV (~0.46 GeV)
        dy_mee = rng.normal(94.19, 2.0, n)

        data_arr = _make_zee_array(n, cat, data_mee, ele27, diphoton, is_data=True)
        dy_arr = _make_zee_array(n, cat, dy_mee, ele27, diphoton, is_data=False, genWeight=np.ones(n))

        per_cat = compare_peak_and_width(data_arr, dy_arr)
        for c in zc.CATEGORIES:
            self.assertFalse(per_cat[c]["peak_agreement_pass"], msg=f"{c}: {per_cat[c]}")


class TriggerEfficiencyTests(unittest.TestCase):
    def test_binomial_uncertainty_known_values(self):
        self.assertAlmostEqual(binomial_uncertainty(50, 100), np.sqrt(0.5 * 0.5 / 100))
        self.assertTrue(np.isnan(binomial_uncertainty(0, 0)))

    def test_trigger_efficiency_per_category_counts_correctly(self):
        n = 10
        cat = ["EBEB"] * 5 + ["notEBEB"] * 5
        mee = [96.0] * n  # all pass the >95 probe window
        ele27 = [True] * n
        diphoton = [True, True, True, False, False,   # EBEB: 3/5 fired
                    True, False, False, False, False]  # notEBEB: 1/5 fired
        arr = _make_zee_array(n, cat, mee, ele27, diphoton, is_data=True)
        eff = trigger_efficiency_per_category(arr)
        self.assertEqual(eff["EBEB"]["n_probe"], 5)
        self.assertEqual(eff["EBEB"]["n_diphoton_fired"], 3)
        self.assertAlmostEqual(eff["EBEB"]["efficiency"], 0.6)
        self.assertEqual(eff["notEBEB"]["n_diphoton_fired"], 1)
        self.assertAlmostEqual(eff["notEBEB"]["efficiency"], 0.2)


class LeakageEstimateAggregationTests(unittest.TestCase):
    def _make_job(self, jobs_base: Path, index: int, n_100_105: int, sumgw_100_105: float,
                   n_105_115: int, sumgw_105_115: float, genEventSumw: float) -> None:
        job_dir = jobs_base / f"job_{index}"
        sel = job_dir / "selected"
        logs = job_dir / "logs"
        sel.mkdir(parents=True, exist_ok=True)
        logs.mkdir(parents=True, exist_ok=True)
        (sel / "job_metadata.json").write_text(json.dumps({
            "cutflow": {"n_selected": 5},
            "hgg_veto_leakage_estimate": {
                "n_selected_100_105": n_100_105, "sum_genWeight_100_105": sumgw_100_105,
                "n_selected_105_115": n_105_115, "sum_genWeight_105_115": sumgw_105_115,
            },
        }), encoding="utf-8")
        (logs / f"parsing_stats_batch_{index}.json").write_text(json.dumps({
            "sumw_by_record": {"record_35669": {"genEventSumw": genEventSumw}}
        }), encoding="utf-8")

    def test_sums_across_all_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs_base = Path(tmp) / "dy_full"
            for i in range(1, 4):
                self._make_job(jobs_base, i, n_100_105=2, sumgw_100_105=2.0,
                                n_105_115=1, sumgw_105_115=1.0, genEventSumw=1000.0)
            agg = sum_leakage_and_sumw(jobs_base)
            self.assertEqual(agg["n_job_dirs_present"], 3)
            self.assertEqual(agg["missing_jobs_no_metadata"], [])
            self.assertEqual(agg["missing_leakage_key_jobs"], [])
            self.assertEqual(agg["missing_sumw_jobs"], [])
            self.assertAlmostEqual(agg["total_genEventSumw_dy_processed"], 3000.0)
            self.assertAlmostEqual(agg["total_sum_genWeight_by_window"]["100_105"], 6.0)
            self.assertEqual(agg["total_n_selected_by_window"]["100_105"], 6)

    def test_missing_leakage_key_flagged_not_silently_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs_base = Path(tmp) / "dy_full"
            job_dir = jobs_base / "job_1"
            (job_dir / "selected").mkdir(parents=True)
            (job_dir / "selected" / "job_metadata.json").write_text(
                json.dumps({"cutflow": {"n_selected": 1}}), encoding="utf-8"  # no leakage key
            )
            agg = sum_leakage_and_sumw(jobs_base)
            self.assertEqual(agg["missing_leakage_key_jobs"], [1])


if __name__ == "__main__":
    unittest.main()
