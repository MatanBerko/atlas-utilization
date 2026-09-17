"""Bias-study diagnosis: load the merged bias_study_105_180.json and
provide simple tabular access. Read-only -- this package never re-runs
the cluster toy study and never changes any pre-set criterion."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MERGED_JSON = REPO_ROOT / "studies" / "hgg_cms" / "background_model" / "results" / "bias_study_105_180.json"
ORDER_SELECTION_JSON = REPO_ROOT / "studies" / "hgg_cms" / "background_model" / "results" / "order_selection_105_180.json"
SIGNAL_MODEL_JSON = REPO_ROOT / "studies" / "hgg_cms" / "signal_model" / "results" / "signal_model.json"

CATEGORIES = ["EBEB", "notEBEB"]
TRUTH_FAMILIES = ["bernstein", "expsum", "powersum", "laurent"]
LEAKAGE_VARIANTS = ["nominal", "leakage_plus", "leakage_minus"]
MASSES = [115.0, 120.0, 125.0, 130.0, 135.0]


def load_merged() -> dict:
    return json.loads(MERGED_JSON.read_text(encoding="utf-8"))


def load_order_selection() -> dict:
    return json.loads(ORDER_SELECTION_JSON.read_text(encoding="utf-8"))


def load_signal_model() -> dict:
    return json.loads(SIGNAL_MODEL_JSON.read_text(encoding="utf-8"))


def test_functions(merged: dict, category: str) -> list:
    return sorted(merged["per_category"][category]["evaluations"].keys())


def points_table(merged: dict, category: str, test_function: str) -> list:
    """The 60 (truth_family, leakage_variant, mass) cells for one test function."""
    return merged["per_category"][category]["evaluations"][test_function]["all_points"]
