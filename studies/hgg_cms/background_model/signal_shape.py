"""Background-model task, Part 3: load the already-fitted signal shape
per category from `studies/hgg_cms/signal_model/results/signal_model.json`
(prior task's output) -- not refit here."""
from __future__ import annotations

import json
from pathlib import Path

from studies.hgg_cms.signal_model.shapes import SignalShape

REPO_ROOT = Path(__file__).resolve().parents[3]
SIGNAL_MODEL_JSON = REPO_ROOT / "studies" / "hgg_cms" / "signal_model" / "results" / "signal_model.json"


def load_signal_shape(category: str) -> SignalShape:
    d = json.loads(SIGNAL_MODEL_JSON.read_text(encoding="utf-8"))
    sp = d[category]["shape_params"]
    params = sp["params"]
    return SignalShape(params=params, use_gauss2=sp["use_gauss2"], param_names=tuple(params.keys()))


def load_expected_signal_yield(category: str) -> float:
    d = json.loads(SIGNAL_MODEL_JSON.read_text(encoding="utf-8"))
    return float(d[category]["yields"]["N_with_trigger_sf_central"])
