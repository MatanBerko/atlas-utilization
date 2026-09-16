#!/usr/bin/env python
"""
Implementation task 6, Part 4 (bugfix follow-up, 16 Sep 2026): preflight
check for submit_full.sh / submit_pilot.sh / submit_zee.sh -- every
`specific_record_ids` entry in every config.cms_hgg*.yaml about to be
submitted must already be registered in
services.parsing.schemas.RECORD_ID_TO_SCHEMA, or the run fails immediately
on the cluster with "record ID ... is not registered" (exactly what
happened to the Z->ee pilot's DY jobs: record 35669 was used in
config.cms_hgg_zee_dy.yaml before being added to that mapping). Catching
this HERE, before any qsub, means a whole array job never gets submitted
and immediately fails 41+ times for the same one-line-fixable reason.

Usage:
    python check_configs_registered.py config1.yaml config2.yaml ...

Exits 0 and prints "OK" per config if every record ID used is registered;
exits 1 and prints exactly which config(s) and record ID(s) are missing
otherwise (so the fix -- add the missing record(s) to
services/parsing/schemas.py's RECORD_ID_TO_SCHEMA -- is obvious from the
output alone).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

from services.parsing.schemas import RECORD_ID_TO_SCHEMA  # noqa: E402


def record_ids_for_config(config_path: str) -> list:
    raw = yaml.safe_load(open(config_path, encoding="utf-8"))
    ids = (raw.get("parsing_task_config") or {}).get("specific_record_ids") or []
    return [int(r) for r in ids]


def main():
    config_paths = sys.argv[1:]
    if not config_paths:
        print("Usage: python check_configs_registered.py config1.yaml [config2.yaml ...]", file=sys.stderr)
        sys.exit(2)

    any_missing = False
    for path in config_paths:
        ids = record_ids_for_config(path)
        missing = [r for r in ids if r not in RECORD_ID_TO_SCHEMA]
        if missing:
            any_missing = True
            print(f"MISSING: {path} uses record ID(s) {missing} not registered in "
                  f"services/parsing/schemas.py's RECORD_ID_TO_SCHEMA")
        else:
            print(f"OK: {path} -- record ID(s) {ids} all registered")

    if any_missing:
        print("\nFIX: add the missing record ID(s) above to RECORD_ID_TO_SCHEMA in "
              "services/parsing/schemas.py (after checking that record's own file's "
              "branch naming matches the 'cms-nanoaod' schema -- see "
              "studies/hgg_cms/impl_checks/record_schema_evidence.json for the "
              "established check pattern), commit, and re-run this preflight.")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
