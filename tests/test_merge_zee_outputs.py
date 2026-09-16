"""
Implementation task 6, Part 4: unit tests for
studies/hgg_cms/cluster/merge_zee_outputs.py's identity checks -- same
synthetic-fixture style as tests/test_merge_outputs.py's data-mode tests.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from studies.hgg_cms.cluster import merge_zee_outputs as mz

URLS = [
    "root://eospublic.cern.ch//eos/opendata/cms/mc/x/A.root",
    "root://eospublic.cern.ch//eos/opendata/cms/mc/x/B.root",
    "root://eospublic.cern.ch//eos/opendata/cms/mc/x/C.root",
]


def _make_job(jobs_base: Path, index: int, cache_urls: list, n_selected: int = 5) -> None:
    job_dir = jobs_base / f"job_{index}"
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "metadata_cache.json").write_text(
        json.dumps({"record_x": cache_urls}), encoding="utf-8"
    )
    sel = job_dir / "selected"
    sel.mkdir(parents=True, exist_ok=True)
    (sel / "job_metadata.json").write_text(json.dumps({
        "cutflow": {"n_input_events": 100, "n_selected": n_selected, "n_written": n_selected},
    }), encoding="utf-8")


class MergeZeeIdentityChecksTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.jobs_base = self.tmp / "data_full"
        self.expected_json = self.tmp / "expected.json"
        self.expected_json.write_text(json.dumps({"record_x": URLS}), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, force=False):
        out = self.tmp / "summary.json"
        rc = mz.merge(self.jobs_base, total_batches=3, expected_json=self.expected_json,
                       out_path=out, force=force, merged_out=None)
        return rc, json.loads(out.read_text(encoding="utf-8"))

    def test_complete_when_everything_matches(self):
        for i in range(1, 4):
            _make_job(self.jobs_base, i, URLS)
        rc, summary = self._run()
        self.assertEqual(rc, 0)
        self.assertEqual(summary["status"], "COMPLETE")
        self.assertEqual(summary["total_cutflow"]["n_selected"], 15)

    def test_missing_job_detected(self):
        _make_job(self.jobs_base, 1, URLS)
        _make_job(self.jobs_base, 2, URLS)
        rc, summary = self._run()
        self.assertEqual(rc, 1)
        self.assertEqual(summary["status"], "INCOMPLETE")
        self.assertIn(mz.normalize_url(URLS[2]), summary["missing_files"])

    def test_duplicate_file_detected(self):
        _make_job(self.jobs_base, 1, URLS)
        rotated = [URLS[2], URLS[0], URLS[1]]
        _make_job(self.jobs_base, 2, rotated)
        _make_job(self.jobs_base, 3, URLS)
        rc, summary = self._run()
        self.assertEqual(rc, 1)
        self.assertEqual(summary["status"], "INCOMPLETE")
        self.assertEqual(len(summary["duplicated_files"]), 1)


if __name__ == "__main__":
    unittest.main()
