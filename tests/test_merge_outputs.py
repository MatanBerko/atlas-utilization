"""
Implementation task 6, Part 1: unit tests for
studies/hgg_cms/cluster/merge_outputs.py's file-identity checks and the
merged-ROOT blinding safety net.

Every test builds a small, SYNTHETIC set of job directories (metadata_cache
.json + selected/job_metadata.json + logs/parsing_stats_batch_<i>.json) in a
tempdir -- no cluster, no network, no real CERN files -- and patches the
module's expected-file-list / portal-event-count JSON paths to point at
small synthetic fixtures instead of the real 133/71-file lists, so each
test's "total_batches" can be a small number (3) instead of 133.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import awkward as ak
import uproot

from studies.hgg_cms.cluster import merge_outputs as mo

RECORD_X_URLS_ROOT = [
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/x/A.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/x/B.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/x/C.root",
]
# Same 3 files, expressed with the OTHER scheme/host -- used by the
# normalization test.
RECORD_X_URLS_HTTPS = [
    u.replace("root://eospublic.cern.ch//eos/opendata/", "https://opendata.cern.ch/eos/opendata/")
    for u in RECORD_X_URLS_ROOT
]


def _write_job_metadata(sel_dir: Path, cutflow: dict) -> None:
    sel_dir.mkdir(parents=True, exist_ok=True)
    (sel_dir / "job_metadata.json").write_text(json.dumps({
        "git_commit": "deadbeef",
        "config_sha256": "cafef00d",
        "input_files_processed": ["parsed_record_x_batch1_final.root"],
        "input_files_failed": [],
        "cutflow": cutflow,
    }), encoding="utf-8")


def _write_parsing_stats(logs_dir: Path, index: int, total_events: int) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / f"parsing_stats_batch_{index}.json").write_text(
        json.dumps({"total_events": total_events}), encoding="utf-8"
    )


def _make_job(jobs_base: Path, index: int, cache_urls: list, cutflow: dict, total_events: int) -> None:
    job_dir = jobs_base / f"job_{index}"
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "metadata_cache.json").write_text(
        json.dumps({"record_x": cache_urls}), encoding="utf-8"
    )
    _write_job_metadata(job_dir / "selected", cutflow)
    _write_parsing_stats(job_dir / "logs", index, total_events)


def _default_cutflow(n=100):
    return {
        "n_input_events": n, "n_with_ge2_tm_photons": n // 2, "n_selected": n // 10,
        "n_written_normal": n // 10, "n_written_blinded_signal_region": 0,
    }


class MergeDataIdentityChecksTests(unittest.TestCase):
    """Every test patches DATA_EXPECTED_JSON/RECORDS_JSON to small synthetic
    fixtures (3 files, one record 'record_x' / id 'x') so total_batches=3
    exercises the same reconstruction math the real 133-file run uses."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.jobs_base = self.tmp / "data"
        self.expected_json = self.tmp / "expected.json"
        self.records_json = self.tmp / "records.json"
        self.expected_json.write_text(
            json.dumps({"record_x": RECORD_X_URLS_ROOT}), encoding="utf-8"
        )
        self.records_json.write_text(json.dumps({
            "records": {"x": {"number_events": 300, "title": "synthetic"}}
        }), encoding="utf-8")
        self._patches = [
            patch.object(mo, "DATA_EXPECTED_JSON", self.expected_json),
            patch.object(mo, "RECORDS_JSON", self.records_json),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def _run(self, force=False):
        out = self.tmp / "summary.json"
        rc = mo.merge_data(self.jobs_base, total_batches=3, out_path=out, force=force, merged_dir=None)
        return rc, json.loads(out.read_text(encoding="utf-8"))

    def test_complete_when_everything_matches(self):
        for i in range(1, 4):
            _make_job(self.jobs_base, i, RECORD_X_URLS_ROOT, _default_cutflow(), total_events=100)
        rc, summary = self._run()
        self.assertEqual(rc, 0)
        self.assertEqual(summary["status"], "COMPLETE")
        self.assertEqual(summary["duplicated_files"], {})
        self.assertEqual(summary["missing_files"], [])
        self.assertEqual(summary["unexpected_files"], [])
        self.assertTrue(summary["per_record_event_totals_vs_portal"]["record_x"]["match"])

    def test_duplicate_file_detected(self):
        # job_1 gets A (slot 0 of its own cache). job_2's OWN cache is
        # rotated so ITS slot 1 (index=2 -> position 1) is also A --
        # simulating two jobs whose independently-fetched file lists
        # disagree in order such that the same real file ends up assigned
        # to two different array indices.
        _make_job(self.jobs_base, 1, RECORD_X_URLS_ROOT, _default_cutflow(), total_events=100)
        rotated = [RECORD_X_URLS_ROOT[2], RECORD_X_URLS_ROOT[0], RECORD_X_URLS_ROOT[1]]
        _make_job(self.jobs_base, 2, rotated, _default_cutflow(), total_events=100)
        _make_job(self.jobs_base, 3, RECORD_X_URLS_ROOT, _default_cutflow(), total_events=100)
        rc, summary = self._run()
        self.assertEqual(rc, 1)
        self.assertEqual(summary["status"], "INCOMPLETE")
        dup_urls = summary["duplicated_files"]
        self.assertEqual(len(dup_urls), 1)
        (job_indices,) = dup_urls.values()
        self.assertEqual(sorted(job_indices), [1, 2])

    def test_missing_file_detected(self):
        # Only 2 of the 3 expected files are ever processed (job_3's
        # directory never gets created -- e.g. that array index never ran).
        _make_job(self.jobs_base, 1, RECORD_X_URLS_ROOT, _default_cutflow(), total_events=100)
        _make_job(self.jobs_base, 2, RECORD_X_URLS_ROOT, _default_cutflow(), total_events=100)
        rc, summary = self._run()
        self.assertEqual(rc, 1)
        self.assertEqual(summary["status"], "INCOMPLETE")
        self.assertIn(mo.normalize_url(RECORD_X_URLS_ROOT[2]), summary["missing_files"])
        self.assertIn(3, summary["array_indices_with_no_job_dir"])

    def test_unexpected_file_detected(self):
        # job_2 actually fetched/processed a file that is NOT in the frozen
        # expected list at all (portal file list changed underneath us).
        unexpected = "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/x/D.root"
        cache_with_extra = [RECORD_X_URLS_ROOT[0], unexpected, RECORD_X_URLS_ROOT[2]]
        _make_job(self.jobs_base, 1, cache_with_extra, _default_cutflow(), total_events=100)
        _make_job(self.jobs_base, 2, cache_with_extra, _default_cutflow(), total_events=100)
        _make_job(self.jobs_base, 3, cache_with_extra, _default_cutflow(), total_events=100)
        rc, summary = self._run()
        self.assertEqual(rc, 1)
        self.assertEqual(summary["status"], "INCOMPLETE")
        self.assertIn(mo.normalize_url(unexpected), summary["unexpected_files"])
        self.assertIn(mo.normalize_url(RECORD_X_URLS_ROOT[1]), summary["missing_files"])

    def test_scheme_and_host_normalization_does_not_false_flag(self):
        # Every job's OWN metadata_cache.json happens to use the https://
        # redirector form, while the frozen expected list uses root://
        # -- these must compare EQUAL, not show up as missing+unexpected.
        for i in range(1, 4):
            _make_job(self.jobs_base, i, RECORD_X_URLS_HTTPS, _default_cutflow(), total_events=100)
        rc, summary = self._run()
        self.assertEqual(rc, 0)
        self.assertEqual(summary["status"], "COMPLETE")
        self.assertEqual(summary["missing_files"], [])
        self.assertEqual(summary["unexpected_files"], [])

    def test_event_total_mismatch_detected(self):
        # File identity is perfect, but the summed parsing-stats event
        # count for record_x (297) does not match the portal's published
        # total (300, from records.json above) -- e.g. a corrupted/short
        # file was silently mis-recorded.
        _make_job(self.jobs_base, 1, RECORD_X_URLS_ROOT, _default_cutflow(), total_events=100)
        _make_job(self.jobs_base, 2, RECORD_X_URLS_ROOT, _default_cutflow(), total_events=100)
        _make_job(self.jobs_base, 3, RECORD_X_URLS_ROOT, _default_cutflow(), total_events=97)
        rc, summary = self._run()
        self.assertEqual(rc, 1)
        self.assertEqual(summary["status"], "INCOMPLETE")
        mismatch = summary["per_record_event_totals_vs_portal"]["record_x"]
        self.assertFalse(mismatch["match"])
        self.assertEqual(mismatch["summed_from_parsing_stats"], 297)
        self.assertEqual(mismatch["expected_from_portal"], 300)
        # File-identity itself was fine -- only the event-total check fails.
        self.assertEqual(summary["missing_files"], [])
        self.assertEqual(summary["unexpected_files"], [])

    def test_force_marks_forced_not_silently_complete(self):
        _make_job(self.jobs_base, 1, RECORD_X_URLS_ROOT, _default_cutflow(), total_events=100)
        rc, summary = self._run(force=True)
        self.assertEqual(rc, 0)
        self.assertEqual(summary["status"], "COMPLETE_FORCED_WITH_MISSING")


GGH_URLS = [
    "root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/GluGluHToGG/x/1.root",
    "root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/GluGluHToGG/x/2.root",
]


class MergeSignalIdentityChecksTests(unittest.TestCase):
    """Uses the real label 'ggh' -> record 37350 mapping (hardcoded in
    SIGNAL_LABEL_TO_RECORD) but patches the expected file list / sumw
    table to a small synthetic 2-file fixture."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.run_dir = self.tmp / "signal" / "ggh"
        self.expected_json = self.tmp / "signal_expected.json"
        self.sumw_json = self.tmp / "signal_sumw.json"
        self.expected_json.write_text(
            json.dumps({"record_37350": GGH_URLS}), encoding="utf-8"
        )
        self.sumw_json.write_text(json.dumps({"records": {
            "37350": {"cross_section_pb": 48.58, "branching_ratio_Hgammagamma": 0.00227}
        }}), encoding="utf-8")
        self._patches = [
            patch.object(mo, "SIGNAL_EXPECTED_JSON", self.expected_json),
            patch.object(mo, "SIGNAL_SUMW_JSON", self.sumw_json),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def _write_run(self, processed_urls, n_failed=0, sum_gw_sel=40.0):
        (self.run_dir / "logs").mkdir(parents=True, exist_ok=True)
        (self.run_dir / "selected").mkdir(parents=True, exist_ok=True)
        (self.run_dir / "logs" / "parsing_stats.json").write_text(json.dumps({
            "sumw_by_record": {
                "record_37350": {
                    "n_files_processed": len(processed_urls),
                    "n_files_failed": n_failed,
                    "processed_files": processed_urls,
                    "genEventSumw": 100.0,
                    "genEventCount": 1000,
                    "genEventSumw2": 50.0,
                }
            }
        }), encoding="utf-8")
        (self.run_dir / "selected" / "job_metadata.json").write_text(json.dumps({
            "cutflow": {"sum_genWeight_selected": sum_gw_sel, "n_selected": 400},
        }), encoding="utf-8")

    def _run(self, force=False):
        out = self.tmp / "signal_summary.json"
        rc = mo.merge_signal({"ggh": str(self.run_dir)}, out, force, merged_dir=None)
        return rc, json.loads(out.read_text(encoding="utf-8"))

    def test_complete_when_all_files_processed(self):
        self._write_run(GGH_URLS)
        rc, summary = self._run()
        self.assertEqual(rc, 0)
        self.assertEqual(summary["status"], "COMPLETE")
        self.assertTrue(summary["per_record"]["ggh"]["record_ok"])

    def test_missing_file_detected(self):
        self._write_run([GGH_URLS[0]], n_failed=0)
        rc, summary = self._run()
        self.assertEqual(rc, 1)
        self.assertEqual(summary["status"], "INCOMPLETE")
        self.assertIn(mo.normalize_url(GGH_URLS[1]), summary["per_record"]["ggh"]["missing_files"])

    def test_failed_file_prevents_complete(self):
        # All expected files are IN processed_files, but n_files_failed > 0
        # means some OTHER file (of the record's fetched list) failed to
        # parse -- must not be silently treated as COMPLETE.
        self._write_run(GGH_URLS, n_failed=1)
        rc, summary = self._run()
        self.assertEqual(rc, 1)
        self.assertEqual(summary["status"], "INCOMPLETE")
        self.assertFalse(summary["per_record"]["ggh"]["record_ok"])

    def test_unexpected_file_detected(self):
        extra = "root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/GluGluHToGG/x/3.root"
        self._write_run(GGH_URLS + [extra])
        rc, summary = self._run()
        self.assertEqual(rc, 1)
        self.assertIn(mo.normalize_url(extra), summary["per_record"]["ggh"]["unexpected_files"])


class MergedRootBlindingSafetyTests(unittest.TestCase):
    """The merge's ROOT-writing helper must never silently include a
    blinded (115<=m_gg<=135) data event, even if it somehow ended up in a
    normally-named file (a bug elsewhere, not just a naming convention)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_raw_events_file(self, path: Path, m_gg_values, is_data=True):
        n = len(m_gg_values)
        with uproot.recreate(str(path)) as f:
            f["events"] = {
                "record_id": ak.Array([12345] * n),
                "is_data": ak.Array([is_data] * n),
                "run": ak.Array(list(range(1, n + 1))),
                "luminosityBlock": ak.Array([1] * n),
                "event": ak.Array(list(range(n))),
                "m_gg": ak.Array(m_gg_values),
                "category": ak.Array(["EBEB"] * n),
                "PV_npvsGood": ak.Array([25] * n),
            }

    def test_normal_sideband_files_merge_cleanly(self):
        f1 = self.tmp / "job1.root"
        f2 = self.tmp / "job2.root"
        self._write_raw_events_file(f1, [105.0, 110.0])
        self._write_raw_events_file(f2, [140.0, 150.0, 160.0])
        out = self.tmp / "merged.root"
        n = mo._write_merged_data_root([f1, f2], out)
        self.assertEqual(n, 5)
        self.assertTrue(out.exists())

    def test_blinded_event_in_normally_named_file_raises_not_merged(self):
        # This file's NAME does not contain BLINDED_SIGNAL_REGION, but it
        # wrongly contains one event at m_gg=120 (inside 115-135) --
        # read_output's second, filename-independent check must catch it.
        bad = self.tmp / "job_bad.root"
        self._write_raw_events_file(bad, [105.0, 120.0, 150.0])
        out = self.tmp / "merged.root"
        with self.assertRaises(AssertionError):
            mo._write_merged_data_root([bad], out)
        self.assertFalse(out.exists())

    def test_no_input_files_writes_nothing(self):
        out = self.tmp / "merged.root"
        n = mo._write_merged_data_root([], out)
        self.assertEqual(n, 0)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
