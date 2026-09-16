"""
Implementation task 6, Part 4 (bugfix follow-up, 16 Sep 2026): every
config.cms_hgg*.yaml's specific_record_ids must be registered in
services.parsing.schemas.RECORD_ID_TO_SCHEMA. This is the unit-test
counterpart of studies/hgg_cms/cluster/check_configs_registered.py's
preflight check (now wired into submit_full.sh / submit_pilot.sh /
submit_zee.sh) -- added after the Z->ee pilot's DY jobs failed
immediately on the cluster because record 35669 was used in
config.cms_hgg_zee_dy.yaml before being added to that mapping. Catches
the same class of mistake locally, before any config is even written for
a new record, let alone submitted.
"""
from __future__ import annotations

import glob
import unittest
from pathlib import Path

import yaml

from services.parsing.schemas import RECORD_ID_TO_SCHEMA

REPO_ROOT = Path(__file__).resolve().parents[1]


def _config_paths():
    return sorted(REPO_ROOT.glob("config.cms_hgg*.yaml"))


class ConfigRecordsRegisteredTests(unittest.TestCase):
    def test_at_least_one_hgg_config_found(self):
        # Guards against a silently-empty test (e.g. a future rename of
        # the "config.cms_hgg*" naming convention breaking glob() above
        # without anyone noticing this test stopped checking anything).
        self.assertGreater(len(_config_paths()), 0)

    def test_every_config_records_are_registered(self):
        unregistered = {}
        for path in _config_paths():
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            ids = (raw.get("parsing_task_config") or {}).get("specific_record_ids") or []
            missing = [int(r) for r in ids if int(r) not in RECORD_ID_TO_SCHEMA]
            if missing:
                unregistered[path.name] = missing
        self.assertEqual(
            unregistered, {},
            msg=(
                f"config(s) reference record ID(s) not in "
                f"RECORD_ID_TO_SCHEMA: {unregistered} -- register them in "
                f"services/parsing/schemas.py (see "
                f"studies/hgg_cms/impl_checks/record_schema_evidence.json "
                f"for the established branch-format-check pattern) before "
                f"submitting any job using that config."
            ),
        )


if __name__ == "__main__":
    unittest.main()
