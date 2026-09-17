"""
Background-model task, Part 2 (finalization): the function-evaluation
module the eventual signal-plus-background fit will use. Given a
category, returns the chosen background function's expected count per
0.25 GeV bin over the FULL 105-180 GeV range (including the still-
blinded 115-135 GeV window -- needed later for the S+B fit, which fits
that window; nothing here ever reads a data value there, it only
evaluates a background-only FUNCTION shape across it, exactly as
`plots.py`'s sideband-fit figures already draw the fitted curve across
the blinded band).

Reads `results/background_model_final.json` (produced by
`finalize_background_model.py`) -- the chosen family/order/parameters
per category, NOT a re-fit.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from studies.hgg_cms.background_model.families import FAMILIES
from studies.hgg_cms.background_model.common import bin_edges, DEFAULT_FIT_LO, DEFAULT_FIT_HI, BIN_WIDTH

REPO_ROOT = Path(__file__).resolve().parents[3]
FINAL_MODEL_JSON = REPO_ROOT / "studies" / "hgg_cms" / "background_model" / "results" / "background_model_final.json"


def load_final_model(path: Path = FINAL_MODEL_JSON) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def background_expectation(category: str, params: np.ndarray = None, family: str = None, order: int = None,
                            edges: np.ndarray = None, model: dict = None) -> np.ndarray:
    """Expected background count in every bin of `edges` (default: the
    full 105-180 GeV range, 0.25 GeV bins) for `category`'s chosen
    function. Pass `params`/`family`/`order` directly (e.g. for a
    profiled fit that floats them), or omit all three to use the
    fixed, already-fitted values from `results/background_model_final.json`
    (loaded fresh, or pass an already-loaded `model` dict to avoid
    re-reading the file)."""
    if edges is None:
        edges = bin_edges(DEFAULT_FIT_LO, DEFAULT_FIT_HI, BIN_WIDTH)
    if params is None:
        model = model if model is not None else load_final_model()
        entry = model["per_category"][category]
        family = entry["family"]
        order = entry["order"]
        params = np.array(entry["params"])
    fam = FAMILIES[family]
    return fam.bin_expectation(edges, order, np.asarray(params))
