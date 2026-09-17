#!/usr/bin/env python
"""
Bias-study rerun 1, quick local convergence check (<=50 toys per cell,
a few cells per category including the first bias study's own worst
cell for the one-order-lower candidate): does the new higher-order
Bernstein candidate (EBEB bernstein_6, notEBEB bernstein_7) converge
reliably BEFORE committing to a 120-subjob cluster run?

This is a SMALL-SAMPLE CHECK ONLY -- per this task's own instruction,
it reports failure fractions and does not draw any conclusion about
BIAS from 50 toys (the real bias study needs the full 300-1000 toy
grid, run on the cluster). Fixed seeds, reproducible.

Run with (needs the real leakage-template JSON, outside the repo --
see leakage.py's own default path / HGG_LEAKAGE_TEMPLATE_JSON):
    python studies/hgg_cms/background_model/cluster/rerun1_local_convergence_check.py \\
        --out studies/hgg_cms/background_model/results/rerun1_local_convergence_check.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import subprocess

CELLS = {
    "EBEB": {
        "test_function": "bernstein:6",
        "cells": [
            ("bernstein", "nominal", 125.0),      # baseline
            ("laurent", "leakage_plus", 115.0),   # first study's bernstein_5 worst cell
            ("expsum", "nominal", 125.0),
        ],
    },
    "notEBEB": {
        "test_function": "bernstein:7",
        "cells": [
            ("bernstein", "nominal", 125.0),      # baseline
            ("powersum", "nominal", 120.0),       # first study's bernstein_6 worst cell
            ("expsum", "nominal", 125.0),
            ("laurent", "leakage_minus", 130.0),
            ("powersum", "nominal", 135.0),
        ],
    },
}
SEED_BASE = 20260918500  # documented, fixed -- reproducible


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--order-selection-json", default=str(
        REPO_ROOT / "studies/hgg_cms/background_model/results/order_selection_105_180.json"))
    p.add_argument("--leakage-json", default=None,
                    help="Default: leakage.py's own DEFAULT_LEAKAGE_JSON (HGG_LEAKAGE_TEMPLATE_JSON env "
                         "var or C:\\Users\\matan\\hgg_zee_merged\\hgg_leakage_mass_template_results.json).")
    p.add_argument("--n-toys", type=int, default=50)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    from studies.hgg_cms.background_model.leakage import DEFAULT_LEAKAGE_JSON
    leakage_json = args.leakage_json or DEFAULT_LEAKAGE_JSON

    results = {}
    idx = 0
    for category, spec in CELLS.items():
        tf = spec["test_function"]
        for fam, variant, mass in spec["cells"]:
            idx += 1
            seed = SEED_BASE + idx
            key = f"{category}_{fam}_{variant}_m{mass}"
            out_file = Path(args.out).parent / f"_tmp_{key}.json"
            cmd = [
                sys.executable, str(REPO_ROOT / "studies/hgg_cms/background_model/cluster/run_bias_job.py"),
                "--category", category, "--fit-range", "105_180",
                "--truth-family", fam, "--leakage-variant", variant, "--mass", str(mass),
                "--n-toys", str(args.n_toys), "--seed", str(seed),
                "--order-selection-json", args.order_selection_json,
                "--leakage-json", leakage_json,
                "--test-functions", tf,
                "--out", str(out_file),
            ]
            print(f"running {key} (test_function={tf}, seed={seed}) ...", flush=True)
            proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
            if proc.returncode != 0:
                results[key] = {"error": proc.stderr[-2000:]}
                continue
            job_out = json.loads(out_file.read_text(encoding="utf-8"))
            summary = job_out["test_function_results"][tf.replace(":", "_")]
            results[key] = {
                "category": category, "test_function": tf, "truth_family": fam,
                "leakage_variant": variant, "mass": mass, "seed": seed, "n_toys": args.n_toys,
                "n_failed": summary["n_failed"], "fail_fraction": summary.get("fail_fraction"),
                "mean_S": summary["mean_S"], "mean_sigma_S": summary.get("mean_sigma_S"),
            }
            out_file.unlink()
            print(f"  fail_fraction={results[key]['fail_fraction']}", flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({
        "note": "SMALL-SAMPLE CHECK ONLY (<=50 toys/cell) -- do not draw bias conclusions from this; "
                "only for pre-cluster-run convergence sanity-checking.",
        "results": results,
    }, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
