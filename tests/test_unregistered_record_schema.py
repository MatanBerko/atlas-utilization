"""
Implementation task 6, Part B1: an unregistered CMS record ID must raise a
clear, loud error instead of silently falling back to auto-detection
(known broken for NanoAOD's flat branch naming).
"""
from __future__ import annotations

import unittest

from services.parsing.file_parser import FileParser, UnregisteredRecordSchemaError


class UnregisteredRecordSchemaTests(unittest.TestCase):
    def test_unregistered_record_id_raises_loudly(self):
        with self.assertRaises(UnregisteredRecordSchemaError) as ctx:
            FileParser._extract_branches_by_schema(
                {"Photon_pt"}, "record_99999999", file_path="somefile.root",
            )
        self.assertIn("somefile.root", str(ctx.exception))
        self.assertIn("99999999", str(ctx.exception))

    def test_registered_record_id_unaffected(self):
        # 30529 is registered -- must resolve normally, no error.
        result = FileParser._extract_branches_by_schema({"Electron_pt"}, "record_30529")
        self.assertIsInstance(result, dict)

    def test_non_record_unknown_release_year_still_auto_detects(self):
        """Only the CMS-record-ID case is now a loud error; a non-record
        release_year with no schema still falls back to auto-detection,
        unchanged."""
        result = FileParser._extract_branches_by_schema(
            {"AnalysisElectronsAuxDyn.pt", "AnalysisElectronsAuxDyn.eta",
             "AnalysisElectronsAuxDyn.phi"},
            "some-totally-unknown-release-year",
        )
        self.assertIsInstance(result, dict)  # no exception raised


if __name__ == "__main__":
    unittest.main()
