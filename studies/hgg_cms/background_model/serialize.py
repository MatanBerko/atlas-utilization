"""Background-model task: JSON-serialization helpers for Part 2's
per-category, per-family order-selection results -- used both for this
task's own `results/*.json` output and as the SELF-CONTAINED config the
cluster bias-study jobs read (so a cluster job needs no local re-fit of
the sideband data: every family/order's already-converged parameters,
for every order tried, are in this one file)."""
from __future__ import annotations

import numpy as np


def _fit_to_json(fit) -> dict:
    return {
        "family": fit.family, "order": fit.order,
        "params": fit.params.tolist(), "param_names": list(fit.param_names),
        "nll": fit.nll, "valid": fit.valid,
        "n_attempts": fit.n_attempts, "n_valid": fit.n_valid,
    }


def order_selection_to_json(category_results: dict) -> dict:
    """category_results: {category: {family: {"per_order":..., "selection":..., "cross_check_final_order":...}}}"""
    out = {}
    for cat, fam_results in category_results.items():
        out[cat] = {}
        for fam_name, r in fam_results.items():
            per_order_json = {}
            for order, d in r["per_order"].items():
                per_order_json[str(order)] = {
                    "fit": _fit_to_json(d["fit"]),
                    "gof": d["gof"],
                    "n_params": d["n_params"],
                }
            out[cat][fam_name] = {
                "per_order": per_order_json,
                "selection": {k: v for k, v in r["selection"].items()},
                "cross_check_final_order": r["cross_check_final_order"],
            }
    return out
