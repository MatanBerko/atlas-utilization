#!/usr/bin/env python
"""
Background-model task, Part 3: ONE bias-study job -- fixed
(category, fit-range, truth family, leakage variant, mass), looping over
ALL test functions (each family's F-test/GOF-selected order AND one
order above, from `results/order_selection_<range>.json`) and running
`--n-toys` toy pseudo-experiments per test function.

SELF-CONTAINED: this script does NOT open `data_sidebands.root` at all.
Every family/order's already-converged sideband-fit parameters (for
every order tried, both as truth-generators and as test-function warm
starts) are already in `results/order_selection_<range>.json`
(committed to the repo, produced locally in a prior step) -- a cluster
job re-fitting the real data itself would risk drifting from the
laptop's own numbers and adds nothing (the real-data fits are fast and
already done). Only three inputs are read here: that JSON, the signal
model JSON (`studies/hgg_cms/signal_model/results/signal_model.json`,
also already in the repo), and the DY leakage mass-template JSON
(simulation, not data -- no blinding concern either way).

Usage (see cluster/submit_bias_study.sh for how these are enumerated):
    python studies/hgg_cms/background_model/cluster/run_bias_job.py \\
        --category EBEB --fit-range 105_180 \\
        --truth-family bernstein --leakage-variant nominal \\
        --mass 125 --n-toys 1000 --seed 20260918001 \\
        --order-selection-json studies/hgg_cms/background_model/results/order_selection_105_180.json \\
        --leakage-json /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/hgg_leakage_mass_template_results.json \\
        --out /storage/agrp/berkom/atlas-utilization/output/hgg_bias/EBEB_105_180_bernstein_nominal_m125.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.background_model.common import bin_edges  # noqa: E402
from studies.hgg_cms.background_model.families import FAMILIES  # noqa: E402
from studies.hgg_cms.background_model.bias_study import (  # noqa: E402
    build_truth_variants, run_one_toy, summarize_toys,
)
from studies.hgg_cms.background_model.leakage import leakage_template_fine  # noqa: E402
from studies.hgg_cms.signal_model.shapes import SignalShape  # noqa: E402

FIT_RANGES = {"105_180": (105.0, 180.0), "110_180": (110.0, 180.0)}


def load_order_selection(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_functions_for_category(config: dict, category: str) -> list:
    """[(family, order), ...] = each family's final_selected_order AND
    one order above (skipped if the family was dropped, or if the
    selected order is already the family's max declared order)."""
    out = []
    for fam_name, r in config[category].items():
        sel = r["selection"]
        order = sel["final_selected_order"]
        if order is None:
            continue
        out.append((fam_name, order))
        orders_tried = [int(o) for o in sel["orders_tried"]]
        if order < max(orders_tried):
            next_order = order + 1
            if str(next_order) in r["per_order"]:
                out.append((fam_name, next_order))
    return out


def get_params(config: dict, category: str, family: str, order: int) -> np.ndarray:
    return np.array(config[category][family]["per_order"][str(order)]["fit"]["params"])


def load_signal_shape_from_json(signal_model_json: str, category: str) -> SignalShape:
    d = json.loads(Path(signal_model_json).read_text(encoding="utf-8"))
    sp = d[category]["shape_params"]
    params = sp["params"]
    return SignalShape(params=params, use_gauss2=sp["use_gauss2"], param_names=tuple(params.keys()))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--category", required=True, choices=["EBEB", "notEBEB"])
    p.add_argument("--fit-range", required=True, choices=list(FIT_RANGES))
    p.add_argument("--truth-family", required=True, choices=list(FAMILIES))
    p.add_argument("--leakage-variant", required=True, choices=["nominal", "leakage_plus", "leakage_minus"])
    p.add_argument("--mass", required=True, type=float)
    p.add_argument("--n-toys", required=True, type=int)
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--order-selection-json", required=True)
    p.add_argument("--leakage-json", required=True)
    p.add_argument("--signal-model-json", default=str(
        REPO_ROOT / "studies" / "hgg_cms" / "signal_model" / "results" / "signal_model.json"))
    p.add_argument("--test-functions", default=None,
                    help="Optional override, comma-separated family:order pairs, e.g. "
                         "'bernstein:4,bernstein:5'. Default: all families' selected + one-above.")
    p.add_argument("--s-bound", type=float, default=None,
                    help="Symmetric bound on the fitted signal yield S. Default: 20x the "
                         "expected signal yield at this category/mass, computed from the signal model JSON.")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    t_start = time.time()
    lo, hi = FIT_RANGES[args.fit_range]
    edges = bin_edges(lo, hi, 0.25)

    config = load_order_selection(args.order_selection_json)
    if args.category not in config:
        raise SystemExit(f"category {args.category!r} not in {args.order_selection_json}")

    truth_sel = config[args.category][args.truth_family]["selection"]
    truth_order = truth_sel["final_selected_order"]
    if truth_order is None:
        raise SystemExit(f"family {args.truth_family!r} was DROPPED (fails GOF everywhere) in "
                          f"{args.category}/{args.fit_range} -- cannot use as a truth model.")
    truth_params = get_params(config, args.category, args.truth_family, truth_order)

    leak = leakage_template_fine(args.category, edges, path=args.leakage_json)
    variants = build_truth_variants(args.truth_family, truth_order, truth_params, edges, leak)
    truth = variants[args.leakage_variant]

    sig_shape_125 = load_signal_shape_from_json(args.signal_model_json, args.category)
    sig_shape = sig_shape_125.shifted_to_mass(args.mass)
    sig_probs = sig_shape.bin_probabilities(edges)

    if args.test_functions:
        test_functions = [(f.split(":")[0], int(f.split(":")[1])) for f in args.test_functions.split(",")]
    else:
        test_functions = test_functions_for_category(config, args.category)

    s_bound = args.s_bound
    if s_bound is None:
        d = json.loads(Path(args.signal_model_json).read_text(encoding="utf-8"))
        expected_yield = float(d[args.category]["yields"]["N_with_trigger_sf_central"])
        s_bound = 20.0 * max(expected_yield, 1.0)

    rng = np.random.default_rng(args.seed)
    results = {}
    for fam_name, order in test_functions:
        fam = FAMILIES[fam_name]
        warm_start = get_params(config, args.category, fam_name, order)
        bounds = fam.bounds(order, float(truth.sum()))
        toy_results = []
        for _ in range(args.n_toys):
            r = run_one_toy(rng, truth, fam_name, order, edges, sig_probs, warm_start, bounds, s_bound=s_bound)
            toy_results.append(r)
        summary = summarize_toys(toy_results)
        results[f"{fam_name}_{order}"] = summary
        print(f"  test={fam_name}:{order} mean_S={summary['mean_S']} n_failed={summary['n_failed']}/{summary['n_total']}",
              flush=True)

    out = {
        "category": args.category, "fit_range": args.fit_range,
        "truth_family": args.truth_family, "truth_order": truth_order,
        "leakage_variant": args.leakage_variant, "mass": args.mass,
        "n_toys_per_test_function": args.n_toys, "seed": args.seed,
        "s_bound": s_bound,
        "test_function_results": results,
        "elapsed_sec": time.time() - t_start,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {out_path} ({time.time() - t_start:.1f}s)")


if __name__ == "__main__":
    main()
