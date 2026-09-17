"""
Background-model task, Part 3: the electron-veto leakage mass template,
loaded from the cluster output
(`C:\\Users\\matan\\hgg_zee_merged\\hgg_leakage_mass_template_results.json`,
produced by `studies/hgg_cms/validation/zee/hgg_leakage_mass_template.py`
over all 41 DY jobs -- simulation, never data, so no blinding concern).

The JSON's `N_expected_per_bin` values are ALREADY normalized to the
DY-based absolute expected-event-count estimate (see that script's own
`normalization_formula` field) -- "normalized to the DY estimate for
that category" (this task's own wording) requires no further scaling
step; the JSON values ARE that estimate, per 1 GeV bin, 100-180 GeV.

REBINNING to the analysis's fine (0.25 GeV) grid: 0.25 evenly divides
1.0, so every original 1 GeV bin maps to EXACTLY four 0.25 GeV bins with
no partial overlap. This module assumes a FLAT (piecewise-constant)
density within each original 1 GeV bin -- i.e. each 1 GeV bin's count is
split into four equal quarters -- a simple, explicitly documented
approximation (not a smoothed/interpolated shape), since the original
template itself is not smooth (it's `hgg_leakage_mass_template.py`'s own
choice of 1 GeV bins).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

DEFAULT_LEAKAGE_JSON = os.environ.get(
    "HGG_LEAKAGE_TEMPLATE_JSON", r"C:\Users\matan\hgg_zee_merged\hgg_leakage_mass_template_results.json"
)


def load_leakage_json(path: str = DEFAULT_LEAKAGE_JSON) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"leakage mass-template JSON not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def leakage_template_fine(category: str, fine_edges: np.ndarray, path: str = DEFAULT_LEAKAGE_JSON) -> np.ndarray:
    """Returns the leakage template's expected event count in each bin of
    `fine_edges` (must be a subset of [100, 180] on a 0.25 GeV grid
    aligned with the original 1 GeV grid), for the given category
    ("EBEB", "notEBEB", or "inclusive")."""
    d = load_leakage_json(path)
    coarse_edges = np.array(d["bin_edges_GeV"])
    coarse_vals = np.array(d["template_by_category"][category]["N_expected_per_bin"])
    coarse_width = d["bin_width_GeV"]

    fine_width = float(fine_edges[1] - fine_edges[0])
    n_sub = int(round(coarse_width / fine_width))
    if not np.isclose(n_sub * fine_width, coarse_width, atol=1e-6):
        raise ValueError(
            f"leakage template rebinning only supports fine bins that evenly divide the "
            f"coarse {coarse_width} GeV bins (got fine width {fine_width})."
        )

    fine_centers = 0.5 * (fine_edges[:-1] + fine_edges[1:])
    out = np.zeros(len(fine_centers))
    for j, c in enumerate(fine_centers):
        coarse_idx = int(np.searchsorted(coarse_edges, c, side="right") - 1)
        if coarse_idx < 0 or coarse_idx >= len(coarse_vals):
            out[j] = 0.0
        else:
            out[j] = coarse_vals[coarse_idx] / n_sub
    return out
