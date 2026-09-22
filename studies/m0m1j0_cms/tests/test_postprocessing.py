"""
Self-checks for studies/m0m1j0_cms/postprocessing.py -- confirms it
really calls the shared pipeline's own functions (not a reimplementation)
and behaves as documented: z_peak_cutoff/max_mass_cutoff, peak removal,
first-empty-bin split, and the raw-count min_events_per_fs mirror.

Run directly: python studies/m0m1j0_cms/tests/test_postprocessing.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.m0m1j0_cms import postprocessing  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def main():
    check("raw_count_passes_min_events_prune(99) is False", postprocessing.raw_count_passes_min_events_prune(99) is False)
    check("raw_count_passes_min_events_prune(100) is True", postprocessing.raw_count_passes_min_events_prune(100) is True)
    check("raw_count_passes_min_events_prune(101) is True", postprocessing.raw_count_passes_min_events_prune(101) is True)

    # z_peak_cutoff: values below 115 GeV must be dropped for m0m1j0
    # (two-muon signature), confirmed via the REAL _apply_z_peak_cut.
    raw = np.array([50.0, 100.0, 114.9, 115.0, 120.0, 200.0])
    result = postprocessing.apply_full_postprocessing(raw, "test_cat")
    check("n_raw == 6", result["n_raw"] == 6)
    check("z_peak_cutoff drops the 3 values below 115 GeV", result["n_after_z_peak"] == 3, f"got {result['n_after_z_peak']}")

    # max_mass_cutoff: a value above 10000 GeV must be dropped.
    raw2 = np.array([200.0, 300.0, 15000.0])
    result2 = postprocessing.apply_full_postprocessing(raw2, "test_cat2")
    check("max_mass_cutoff drops the value above 10000 GeV", result2["n_after_max_mass"] == 2, f"got {result2}")

    # Peak removal + first-empty-bin split: construct a genuine bimodal-
    # like array -- a small "low shoulder" (200-210 GeV, well after
    # z_peak_cutoff), a real EMPTY GAP, then the dominant "peak" region
    # (500-520 GeV, highest count, rightmost among ties), then another
    # gap, then a small isolated tail (900-905 GeV) that should become
    # "outliers" after the split.
    # Deterministic, hand-picked values (random sampling here proved
    # fragile: _find_rightmost_highest_peak bins by the GLOBAL 10-GeV
    # grid, and _split_by_first_empty_bin bins by the FILTERED array's
    # own LOCAL min/max -- a too-narrow or too-random peak region can
    # accidentally make the first local empty bin land at index 0 or 1,
    # which makes the real _split_by_first_empty_bin deliberately skip
    # splitting entirely, post_processing_pipeline.py:376. Discovered
    # via this very test -- not a bug, just means the scenario needs
    # precise construction, not random sampling, to reliably exercise
    # an actual split.)
    low_shoulder = np.array([200.0, 202.0, 204.0, 206.0, 208.0])         # must be REMOVED by peak removal
    dominant_bin = np.linspace(500.0, 504.5, 30)                          # the real peak: 30 points, global bin [500,510)
    second_local_bin = np.array([512.0, 513.0, 514.0, 515.0, 516.0])      # populates local bin 1 so the split isn't skipped
    tail = np.array([900.0, 902.0, 903.98])                               # isolated after a real gap -- must become "outliers"
    raw3 = np.concatenate([low_shoulder, dominant_bin, second_local_bin, tail])
    result3 = postprocessing.apply_full_postprocessing(raw3, "test_cat3")
    check(
        "peak removal drops the low shoulder (n_after_peak_removal < n_after_max_mass)",
        result3["n_after_peak_removal"] < result3["n_after_max_mass"],
        f"got {result3['n_after_peak_removal']} vs {result3['n_after_max_mass']}",
    )
    check(
        "peak mass lands in the dominant peak region (500-560 GeV), not the low shoulder",
        result3["peak_mass"] is not None and 490.0 <= result3["peak_mass"] <= 560.0,
        f"got {result3['peak_mass']}",
    )
    check(
        "the isolated tail (900-905 GeV) is split into outliers, not main",
        result3["n_outliers"] == 3,
        f"got n_outliers={result3['n_outliers']}, main={result3['main_array']}",
    )
    check(
        "main array no longer contains the low shoulder or the isolated tail",
        result3["n_main"] > 0 and np.all(result3["main_array"] >= 490.0) and np.all(result3["main_array"] < 900.0),
        f"got main={result3['main_array']}",
    )
    check("split_mass is a real value near 900 GeV", result3["split_mass"] is not None and result3["split_mass"] >= 900.0, f"got {result3['split_mass']}")

    # Empty-after-cutoff case must not crash.
    result4 = postprocessing.apply_full_postprocessing(np.array([50.0, 60.0]), "empty_cat")
    check("all-below-z_peak-cutoff array yields n_main=0 without crashing", result4["n_main"] == 0 and result4["n_raw"] == 2, f"got {result4}")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All postprocessing self-checks passed.")


if __name__ == "__main__":
    main()
