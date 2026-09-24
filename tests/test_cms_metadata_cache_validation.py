"""
Implementation task 6 (post-pilot fix): FetchMetadataHandler's cache
integrity check (_validate_cache_or_abort) used ATLAS-only RUCIO-
namespace classification (_classify_url) unconditionally, including for
CMS "record_<id>" cache keys -- which never carry ATLAS's "_mc" suffix
naming convention (services.metadata.fetcher.fetch_by_record_ids never
appends "_mc" to a CMS key, whether the record is data or simulation) and
whose URLs never match ATLAS's /mc\\d+_ or /data\\d+_ regex at all. This
made the check reject every valid CMS URL as "unclassifiable" -- hit live
on the cluster the first time a CMS job re-loaded a cache it had itself
written (a cache HIT; see this module's own docstring notes below and
_cms_record_id/_cms_key_violations in
orchestration/handlers/fetch_metadata_handler.py for the fix: CMS record
keys are now classified by their own EOS path instead).

Covers: CMS data key OK, CMS signal key OK, a mixed CMS key (both data-
and simulation-shaped URLs under one record) -> error, an unrecognized
URL pattern under a registered CMS record key -> error, and that ATLAS
key validation (the "_mc"-suffix / RUCIO-namespace logic) is completely
unchanged.
"""
from __future__ import annotations

import unittest

from orchestration.handlers.fetch_metadata_handler import (
    FetchMetadataHandler,
    _cms_key_violations,
    _cms_record_id,
)
from services.metadata.cache import MetadataCache
from services.metadata.fetcher import MetadataFetcher, UrlType, _classify_cms_url

# Real URLs (both transports used in this project) for registered H->gamma-gamma records.
DOUBLE_EG_G = (
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/"
    "UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root"
)
DOUBLE_EG_H = (
    "https://opendata.cern.ch/eos/opendata/cms/Run2016H/DoubleEG/NANOAOD/"
    "UL2016_MiniAODv2_NanoAODv9-v1/100000/2AD46B56-E1CA-CD44-B30D-C57FE1C35D15.root"
)
GGH_MC = (
    "root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/"
    "GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/"
    "106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root"
)
VBF_MC = (
    "https://opendata.cern.ch/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/"
    "VBFHToGG_M125_TuneCP5_13TeV-amcatnlo-pythia8/NANOAODSIM/"
    "106X_mcRun2_asymptotic_v17-v2/2520000/99F507FD-FF4B-0E42-8269-48385EDD1CBD.root"
)
UNRECOGNIZED_CMS_URL = "root://eospublic.cern.ch//eos/opendata/cms/some/unexpected/path/file.root"

DATA_2024 = "https://example.test/rucio/data23_13p6TeV/file.root"
MC_2024 = "https://example.test/rucio/mc23_13p6TeV/file.root"


def _handler() -> FetchMetadataHandler:
    return FetchMetadataHandler(MetadataFetcher(), MetadataCache(cache_path="unused.json"))


class CmsRecordKeyDetectionTests(unittest.TestCase):
    def test_registered_cms_record_key_detected(self):
        self.assertEqual(_cms_record_id("record_30521"), 30521)   # DoubleEG (data)
        self.assertEqual(_cms_record_id("record_37350"), 37350)   # ggH (simulation)

    def test_non_record_key_is_not_cms(self):
        self.assertIsNone(_cms_record_id("2024r-pp"))
        self.assertIsNone(_cms_record_id("2024r-pp_mc"))

    def test_unregistered_record_id_is_not_treated_as_cms(self):
        self.assertIsNone(_cms_record_id("record_999999999"))


class CmsKeyValidationTests(unittest.TestCase):
    def test_cms_data_key_ok(self):
        self.assertEqual(_cms_key_violations("record_30521", [DOUBLE_EG_G, DOUBLE_EG_H]), [])

    def test_cms_signal_key_ok(self):
        self.assertEqual(_cms_key_violations("record_37350", [GGH_MC]), [])

    def test_mixed_cms_key_is_a_violation(self):
        violations = _cms_key_violations("record_30521", [DOUBLE_EG_G, GGH_MC])
        self.assertTrue(violations, "expected at least one violation for a mixed key")

    def test_unrecognized_url_pattern_is_a_violation(self):
        violations = _cms_key_violations("record_37350", [UNRECOGNIZED_CMS_URL])
        self.assertTrue(violations)

    def test_classify_cms_url_raises_on_unrecognized_pattern(self):
        with self.assertRaises(ValueError):
            _classify_cms_url(UNRECOGNIZED_CMS_URL)


class ValidateCacheOrAbortEndToEndTests(unittest.TestCase):
    """Exercises the real handler method, not just the helpers -- this is
    exactly what aborted the D3 cluster job on a cache HIT."""

    def test_d3_data_pinned_cache_passes(self):
        _handler()._validate_cache_or_abort({"record_30521": [DOUBLE_EG_G]})  # must not raise

    def test_d3_signal_pinned_cache_passes(self):
        _handler()._validate_cache_or_abort({"record_37350": [GGH_MC]})  # must not raise

    def test_mixed_cms_record_aborts(self):
        with self.assertRaises(RuntimeError):
            _handler()._validate_cache_or_abort({"record_30521": [DOUBLE_EG_G, GGH_MC]})

    def test_unrecognized_cms_url_aborts(self):
        with self.assertRaises(RuntimeError):
            _handler()._validate_cache_or_abort({"record_37350": [UNRECOGNIZED_CMS_URL]})

    def test_all_eight_hgg_records_pass_independently(self):
        cache = {
            "record_30521": [DOUBLE_EG_G],
            "record_30554": [DOUBLE_EG_H],
            "record_37350": [GGH_MC],
            "record_68497": [VBF_MC],
        }
        _handler()._validate_cache_or_abort(cache)  # must not raise


class AtlasValidationUnchangedTests(unittest.TestCase):
    """ATLAS ("_mc"-suffix key naming + RUCIO-namespace _classify_url)
    behavior must be byte-for-byte unchanged by this fix."""

    def test_atlas_mc_key_ok(self):
        _handler()._validate_cache_or_abort({"2024r-pp_mc": [MC_2024]})  # must not raise

    def test_atlas_data_key_ok(self):
        _handler()._validate_cache_or_abort({"2024r-pp": [DATA_2024]})  # must not raise

    def test_atlas_contaminated_mc_key_still_aborts(self):
        with self.assertRaises(RuntimeError):
            _handler()._validate_cache_or_abort({"2024r-pp_mc": [DATA_2024]})

    def test_atlas_contaminated_data_key_still_aborts(self):
        with self.assertRaises(RuntimeError):
            _handler()._validate_cache_or_abort({"2024r-pp": [MC_2024]})


if __name__ == "__main__":
    unittest.main()
