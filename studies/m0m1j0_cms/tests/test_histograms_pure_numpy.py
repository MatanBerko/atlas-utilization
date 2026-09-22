"""
Self-checks for studies/m0m1j0_cms/histograms.py.

Replaces the earlier stub-ROOT test (test_histograms_with_stub_root.py,
removed): histograms.py no longer depends on PyROOT at all, after the
2026-09-22 pilot run discovered the cluster's own `atlas-pipeline` conda
env has no PyROOT installed at all (see histograms.py's own module
docstring for the full finding and workaround). This module is now pure
awkward/numpy and runs directly, no stubbing needed.

Run directly: python studies/m0m1j0_cms/tests/test_histograms_pure_numpy.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from studies.m0m1j0_cms import histograms  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def main():
    check(
        "FIXED_MASS grid is 0-10000 GeV",
        histograms.FIXED_MASS_MIN_GEV == 0.0 and histograms.FIXED_MASS_MAX_GEV == 10000.0,
    )
    check("bin width is 10 GeV -> 1000 bins", histograms._n_bins() == 1000)

    values, edges = histograms.make_fixed_grid_histogram(np.array([5.0, 5.0, 15.0, np.nan, 9999.9999999]))
    check("histogram has 1000 bins, 1001 edges", len(values) == 1000 and len(edges) == 1001, f"got {len(values)}/{len(edges)}")
    check("bin 0 has 2 entries (both 5.0 GeV values)", values[0] == 2.0, f"got {values[0]}")
    check("bin 1 has 1 entry (15.0 GeV)", values[1] == 1.0, f"got {values[1]}")
    check("NaN is silently skipped (only the 4 finite values are counted)", values.sum() == 4.0, f"got total {values.sum()}")

    exact_max_values, _ = histograms.make_fixed_grid_histogram(np.array([10000.0]))
    check(
        "exact max value (10000.0) is nudged into the LAST real bin, not lost to overflow",
        exact_max_values[-1] == 1.0,
        f"got last bin = {exact_max_values[-1]}, total = {exact_max_values.sum()}",
    )

    check(
        "_convert_to_bumpnet_name matches the shared pipeline's exact format",
        histograms._convert_to_bumpnet_name("0e_2m_1j_0g_0t_0b", "m0m1j0")
        == "mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx",
    )

    histograms.MIN_EVENTS_PER_FINAL_STATE = 5
    obj_record = ak.Array({
        "Electrons": [[] for _ in range(12)],
        "Muons": [[1, 2]] * 10 + [[1, 2, 3]] * 2,
        "Jets": [[1]] * 12,
        "BJets": [[] for _ in range(12)],
    })
    mass = ak.Array([200.0 + 10.0 * i for i in range(10)] + [300.0, 400.0])

    hists, meta = histograms.build_m0m1j0_histograms(obj_record, mass)
    check("inclusive histogram present", histograms.INCLUSIVE_HIST_NAME in hists)
    check(
        "inclusive histogram contains all 12 events",
        meta[histograms.INCLUSIVE_HIST_NAME]["n_events_in_histogram"] == 12,
        f"got {meta[histograms.INCLUSIVE_HIST_NAME]}",
    )

    expected_2m_name = "mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx"
    expected_3m_name = "mass_m0m1j0_cat_0ex_3mx_1jx_0gx_0tx_0bx"
    check("2-muon category (10 events, >= threshold of 5) has its own histogram", expected_2m_name in hists, f"keys: {list(hists.keys())}")
    check(
        "3-muon category (2 events, < threshold of 5) is dropped, not silently omitted",
        expected_3m_name not in hists and expected_3m_name in meta.get("_dropped_categories_below_min_events_per_fs", []),
        f"dropped: {meta.get('_dropped_categories_below_min_events_per_fs')}",
    )
    if expected_2m_name in hists:
        values2, edges2 = hists[expected_2m_name]
        check("2-muon category histogram has 10 entries filled total", values2.sum() == 10, f"got {values2.sum()}")

    hists_noprune, meta_noprune = histograms.build_m0m1j0_histograms(obj_record, mass, apply_min_events_prune=False)
    check(
        "apply_min_events_prune=False: 3-muon category IS written despite being below threshold",
        expected_3m_name in hists_noprune,
        f"keys: {list(hists_noprune.keys())}",
    )
    check(
        "apply_min_events_prune=False: no categories reported as dropped",
        meta_noprune.get("_dropped_categories_below_min_events_per_fs") == [],
        f"got {meta_noprune.get('_dropped_categories_below_min_events_per_fs')}",
    )

    empty_obj = ak.Array({"Electrons": [[]], "Muons": [[1, 2]], "Jets": [[1]], "BJets": [[]]})
    empty_mass = ak.Array([np.nan])
    hists2, meta2 = histograms.build_m0m1j0_histograms(empty_obj, empty_mass)
    check(
        "all-NaN mass array yields 0 inclusive entries without crashing",
        meta2[histograms.INCLUSIVE_HIST_NAME]["n_events_in_histogram"] == 0,
        f"got {meta2}",
    )

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All histogram self-checks passed.")


if __name__ == "__main__":
    main()
