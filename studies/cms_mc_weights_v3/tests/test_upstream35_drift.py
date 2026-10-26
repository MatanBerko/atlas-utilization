"""
Drift test: the MC builder now uses upstream #35's own functions for

  * the per-dataset normalisation
      services.calculations.mc_weights.compute_normalization
      (called by build_mc_delivery.normalisation_factor with CMS's inputs:
      sigma_eff from the registry, k = eps = 1, Sigma-w measured), and
  * the weighted rightmost-highest peak
      services.pipelines.post_processing_pipeline._find_rightmost_highest_peak
      (called by build_mc_delivery.find_peak_mass, also inside
      --peak-scope combined).

Every expected value below was produced by the builder's OWN previous
implementations (MC branch 24ecb7c, before #35 was merged: the inline
normalisation formula and the CMS copy of the peak finder) on the same fixed
inputs, and reproduced unchanged by the #35 functions. So this test

  1. proves the switch to #35's functions changed no number, and
  2. FAILS as soon as upstream changes either function's behaviour, which
     must then be re-compared before the MC builder is used.

Run directly:
    python studies/cms_mc_weights_v3/tests/test_upstream35_drift.py
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from domain.metadata import MCDatasetMetadata  # noqa: E402
from services.calculations.mc_weights import compute_normalization  # noqa: E402
from services.pipelines.post_processing_pipeline import _find_rightmost_highest_peak  # noqa: E402
from studies.cms_mc_weights_v3.deliver import build_mc_delivery as B  # noqa: E402

# Produced by the pre-#35 CMS implementations (24ecb7c) on the inputs below.
EXPECTED_NORM_SWEEP_SHA256 = "ca5e601bdd148dda62c7cc615f8e2d5a492c84dd0c9535a09df9b93db8a3abbc"
EXPECTED_PEAK_SWEEP_SHA256 = "5e69d153287a469a5ec9e63ff2f8e835142ab094a294e498126447f833869873"
EXPECTED_LITERALS = {
    "norm_35631_sw1e9": "0.30507373",
    "norm_67801_sw2.5e9": "0.000585426816",
    "peak_empty": None,
    "peak_tie_rightmost": "210.0",
    "peak_weighted_moves": "90.0",
    "peak_negative_weights": "10.0",
}
SIGMA_W_VALUES = (1.0, 123456.789, 2.5e9, 7.3e12, -4.0e6)
LOGGER = logging.getLogger("test_upstream35_drift")

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))
    if not condition:
        FAILURES.append(name)


def full_run_records() -> dict:
    reg = json.loads(B.REGISTRY_PATH.read_text(encoding="utf-8"))
    recs = reg.get("records", reg)
    return {k: v for k, v in recs.items() if isinstance(v, dict) and v.get("in_full_run")}


def peak_inputs():
    """400 fixed spectra: float32 and float64, unweighted, Gaussian weights
    (some negative), +-signed weights, and constant weights."""
    rng = np.random.default_rng(20261020)
    for i in range(400):
        n = int(rng.integers(1, 4000))
        m = np.concatenate([rng.exponential(120.0, n), rng.uniform(0, 3000, n // 50)]).astype(
            np.float64 if i % 2 else np.float32)
        if i % 4 == 0:
            w = None
        elif i % 4 == 1:
            w = rng.normal(1.0, 0.6, len(m))
        elif i % 4 == 2:
            w = np.where(rng.random(len(m)) < 0.2, -1.0, 1.0) * rng.uniform(1e-4, 3.0, len(m))
        else:
            w = np.full(len(m), 0.37)
        yield m, w


def sha(lines: list) -> str:
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def test_normalisation(recs: dict):
    builder, upstream = [], []
    for rid in sorted(recs, key=int):
        r = recs[rid]
        for sw in SIGMA_W_VALUES:
            builder.append(repr(B.normalisation_factor(r, sw)))
            md = MCDatasetMetadata(dataset_number=int(rid), cross_section_pb=float(r["cross_section_pb"]),
                                   sum_of_weights=sw, k_factor=1.0, gen_filt_eff=1.0)
            upstream.append(repr(compute_normalization(md, B.TARGET_LUMINOSITY_FB)))
    check("13 full-run records in the registry", len(recs) == 13, str(len(recs)))
    check("builder normalisation_factor unchanged (65 values)", sha(builder) == EXPECTED_NORM_SWEEP_SHA256,
          sha(builder))
    check("upstream compute_normalization unchanged (65 values)", sha(upstream) == EXPECTED_NORM_SWEEP_SHA256,
          sha(upstream))


def test_peak():
    builder, upstream = [], []
    for m, w in peak_inputs():
        builder.append(repr(B.find_peak_mass(m, w)))
        p = _find_rightmost_highest_peak(m, B.BIN_WIDTH_GEV, LOGGER, weights=w)
        upstream.append(repr(None if p is None else float(p)))
    check("builder find_peak_mass unchanged (400 spectra)", sha(builder) == EXPECTED_PEAK_SWEEP_SHA256,
          sha(builder))
    check("upstream _find_rightmost_highest_peak unchanged (400 spectra)",
          sha(upstream) == EXPECTED_PEAK_SWEEP_SHA256, sha(upstream))


def test_literals(recs: dict):
    got = {
        "norm_35631_sw1e9": B.normalisation_factor(recs["35631"], 1.0e9),
        "norm_67801_sw2.5e9": B.normalisation_factor(recs["67801"], 2.5e9),
        "peak_empty": B.find_peak_mass(np.zeros(0), None),
        "peak_tie_rightmost": B.find_peak_mass(np.array([105.0, 106.0, 215.0, 216.0]), None),
        "peak_weighted_moves": B.find_peak_mass(np.array([15.0, 16.0, 17.0, 95.0]),
                                                np.array([1.0, 1.0, 1.0, 5.0])),
        "peak_negative_weights": B.find_peak_mass(np.array([15.0, 16.0, 95.0]),
                                                  np.array([1.0, 1.0, -3.0])),
    }
    for k, v in got.items():
        v = None if v is None else repr(v)
        check(f"literal {k}", v == EXPECTED_LITERALS[k], f"got {v}, expected {EXPECTED_LITERALS[k]}")


def test_guard_kept():
    recs = full_run_records()
    tampered = {**recs["35631"], "k_factor": 1.1}
    try:
        B.normalisation_factor(tampered, 1.0e9)
        raised = False
    except SystemExit:
        raised = True
    check("k != 1 is still refused (CMS guard kept)", raised)


def main() -> int:
    recs = full_run_records()
    test_normalisation(recs)
    test_peak()
    test_literals(recs)
    test_guard_kept()
    print("ALL CHECKS PASSED" if not FAILURES else f"{len(FAILURES)} FAILED: {FAILURES}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
