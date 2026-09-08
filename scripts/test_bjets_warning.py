#!/usr/bin/env python3
"""
Concrete test for the fix/warn-on-missing-bjets-cuts guard in
domain/config.py::ParsingConfig.__post_init__.

Part A: constructs ParsingConfig directly with synthetic kinematic_cuts
dicts to exercise every combination (tagging on/off x jets/bjets present).

Part B: loads REAL config files from this repo through the actual
PipelineConfig.from_dict loader (the same path main.py uses), to prove the
guard fires correctly on real, on-disk configs, not just synthetic ones --
including a real, currently-fixed config with its bjets: entry stripped
in-memory only (no file on disk is touched) to concretely simulate the
pre-fix state.

Run with -u (or PYTHONUNBUFFERED=1) and note logging is configured to write
to the SAME stream as print() (stdout) so ordering in the terminal is
truthful -- print() and logging.warning() are on separate buffered streams
by default and can otherwise appear to interleave out of true order.
"""
import copy
import logging
import sys

import yaml

from domain.config import ParsingConfig, PipelineConfig

logging.basicConfig(
    level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s", stream=sys.stdout
)

COMMON = dict(
    output_path="./output/parsed_data",
    file_urls_path="./output/metadata_cache.json",
    jobs_logs_path="./output/logs",
)


def run(label, build):
    print(f"=== {label} ===", flush=True)
    build()
    sys.stdout.flush()
    print(f"(no warning above this line means none fired for: {label})\n", flush=True)


print("################ Part A: direct ParsingConfig construction ################\n")

run(
    "Case 1: tagging enabled, jets present, bjets MISSING (the bug shape)",
    lambda: ParsingConfig(
        **COMMON,
        enable_jet_tagging=True,
        jet_btagging_thresholds={"Jet_btagDeepFlavB": 0.25},
        kinematic_cuts={
            "electrons": {"pt_min": 25.0, "eta_max": 2.47},
            "jets": {"pt_min": 30.0, "eta_max": 4.5},
        },
    ),
)

run(
    "Case 2: tagging enabled, jets AND bjets present (the fixed shape)",
    lambda: ParsingConfig(
        **COMMON,
        enable_jet_tagging=True,
        jet_btagging_thresholds={"Jet_btagDeepFlavB": 0.25},
        kinematic_cuts={
            "electrons": {"pt_min": 25.0, "eta_max": 2.47},
            "jets": {"pt_min": 30.0, "eta_max": 4.5},
            "bjets": {"pt_min": 30.0, "eta_max": 4.5},
        },
    ),
)

run(
    "Case 3: tagging DISABLED, jets present, bjets missing",
    lambda: ParsingConfig(
        **COMMON,
        enable_jet_tagging=False,
        jet_btagging_thresholds=None,
        kinematic_cuts={
            "electrons": {"pt_min": 25.0, "eta_max": 2.47},
            "jets": {"pt_min": 30.0, "eta_max": 4.5},
        },
    ),
)

run(
    "Case 4 (bonus): tagging enabled, NEITHER jets nor bjets present",
    lambda: ParsingConfig(
        **COMMON,
        enable_jet_tagging=True,
        jet_btagging_thresholds={"Jet_btagDeepFlavB": 0.25},
        kinematic_cuts={"electrons": {"pt_min": 25.0, "eta_max": 2.47}},
    ),
)

print("################ Part B: real repo configs through PipelineConfig.from_dict ################\n")


def load(path, mutate=None):
    with open(path) as f:
        d = yaml.safe_load(f)
    if mutate:
        d = copy.deepcopy(d)
        mutate(d)
    return lambda: PipelineConfig.from_dict(d)


run(
    "Case 5: REAL config.cms_bjet_test.yaml, fixed, on disk, unmodified",
    load("config.cms_bjet_test.yaml"),
)

run(
    "Case 6: SAME file, bjets: stripped in-memory only (simulated pre-fix state, no file changed)",
    load(
        "config.cms_bjet_test.yaml",
        mutate=lambda d: d["parsing_task_config"]["kinematic_cuts"].pop("bjets"),
    ),
)

run(
    "Case 7: REAL config.cms_records_master.yaml, tagging disabled",
    load("config.cms_records_master.yaml"),
)

print("Done.")
