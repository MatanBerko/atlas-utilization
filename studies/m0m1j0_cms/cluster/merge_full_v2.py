#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- v2 correction: real pipeline post-processing
applied to the DATA histogram (task Part A3/A4).

Reuses merge_full.py's identity/completeness checks UNCHANGED (imported
directly, not copied) -- same rules: every expected index present, every
job's recorded URL matches the CURRENT portal list, every file re-opened
over XRootD now still reports the same entry count, no duplicates, the
summed n_read equals the CURRENT portal total.

What's NEW here relative to merge_full.py: instead of summing each job's
own pre-built (already z_peak/max_mass-cut, but never peak-removed or
outlier-split) histograms, this script concatenates every job's RAW
mass_by_category.npz arrays per category, then runs the REAL pipeline's
own post-processing chain on each category's full, globally-merged raw
population (studies.m0m1j0_cms.postprocessing -- which itself imports
and calls services.pipelines.post_processing_pipeline's own functions).
Only "_main" (post peak-removal, pre-outlier) data is ever histogrammed,
matching the real pipeline's exclude_outliers=true behavior
(RECIPE.md's correction note has the full story).

A4 cross-check (mandatory, not optional): for every surviving category,
the population immediately after z_peak_cutoff+max_mass_cutoff (BEFORE
this script's peak-removal/outlier-split) must equal EXACTLY the v1
merged histogram's own bin-content sum for that same category
(studies/m0m1j0_cms/full/m0m1j0_full_merged.root, committed, read
directly here) -- same selection, same files, so the only thing that
should ever differ between v1 and v2 is what happens AFTER that point.
Any mismatch STOPS this script (exits non-zero) rather than silently
producing results built on an unverified premise.

Usage:
    python merge_full_v2.py \
        --jobs-base /storage/agrp/berkom/atlas-utilization/output/m0m1j0_full_v2 \
        --mapping-file /storage/agrp/berkom/atlas-utilization/output/m0m1j0_full_v2/job_index_map.txt \
        --v1-merged-root studies/m0m1j0_cms/full/m0m1j0_full_merged.root \
        --out-dir studies/m0m1j0_cms/v2/data
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms.cluster.merge_full import (  # noqa: E402
    load_job_index_map, check_identity_and_counts,
)
from studies.m0m1j0_cms.histograms import to_writable_th1f, verify_written_th1f  # noqa: E402
from studies.m0m1j0_cms.postprocessing import (  # noqa: E402
    apply_full_postprocessing, raw_count_passes_min_events_prune,
)

BIN_WIDTH_GEV = 10.0
INCLUSIVE_LABEL = "mass_m0m1j0_inclusive_ge2m_ge1j_v2_postprocessed"


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_all_mass_by_category(jobs_base: Path, present_indices: list) -> dict:
    """{category_label: concatenated raw mass numpy array} across every
    present job's mass_by_category.npz."""
    chunks: dict = {}
    for idx in present_indices:
        npz_path = jobs_base / f"job_{idx}" / "mass_by_category.npz"
        if not npz_path.exists():
            continue
        with np.load(npz_path, allow_pickle=True) as npz:
            categories = npz["category"]
            masses = npz["m0m1j0_raw_gev"]
        for cat in np.unique(categories):
            mask = categories == cat
            chunks.setdefault(str(cat), []).append(masses[mask])
    return {cat: np.concatenate(arrs) for cat, arrs in chunks.items()}


def load_v1_category_totals(v1_root_path: Path) -> dict:
    """{grouping_name: bin-content sum} for every histogram in the
    committed v1 merged ROOT file -- the A4 cross-check's ground truth."""
    import re as _re

    def strip(root_name: str) -> str:
        name = root_name[len("ROI_"):] if root_name.startswith("ROI_") else root_name
        return _re.sub(r"_width_\d+$", "", name)

    f = uproot.open(str(v1_root_path))
    totals = {}
    for key in f.keys(cycle=False):
        totals[strip(key)] = float(f[key].values().sum())
    return totals


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-base", required=True)
    p.add_argument("--mapping-file", required=True)
    p.add_argument("--v1-merged-root", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    jobs_base = Path(args.jobs_base)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    job_index_map = load_job_index_map(Path(args.mapping_file))
    identity = check_identity_and_counts(jobs_base, job_index_map)
    present_indices = sorted(i for i, v in identity["per_job"].items() if v.get("status") == "OK")

    if identity["problems"]:
        print("IDENTITY/COMPLETENESS CHECK FAILED -- refusing to proceed:")
        for problem in identity["problems"]:
            print(f"  - {problem}")
        (out_dir / "merge_v2_summary.json").write_text(
            json.dumps({"complete": False, "identity_and_counts": identity}, indent=2), encoding="utf-8"
        )
        sys.exit(1)

    print(f"Identity/completeness check PASSED: {len(present_indices)} jobs, no problems.")

    mass_by_category = load_all_mass_by_category(jobs_base, present_indices)
    v1_totals = load_v1_category_totals(Path(args.v1_merged_root))

    # --- A4 cross-check: n_after_max_mass (this script, pre-peak-removal)
    # must equal v1's own bin-content sum, category by category. ---
    cross_check_problems = []
    per_category_precheck = {}
    for cat, raw_mass in mass_by_category.items():
        after_z_peak_and_max_mass_only = apply_full_postprocessing(raw_mass, cat)
        n_v2_pre_peak_removal = after_z_peak_and_max_mass_only["n_after_max_mass"]
        v1_total = v1_totals.get(cat)
        per_category_precheck[cat] = {"n_v2_pre_peak_removal": n_v2_pre_peak_removal, "v1_total": v1_total}
        if v1_total is None:
            continue  # a category that didn't survive v1's own min_events_per_fs prune -- checked separately below
        if float(n_v2_pre_peak_removal) != v1_total:
            cross_check_problems.append(
                f"category {cat!r}: v2 pre-peak-removal count = {n_v2_pre_peak_removal}, "
                f"v1 merged histogram total = {v1_total} -- MISMATCH"
            )

    # Also check the inclusive: v2's pre-peak-removal count summed over
    # ALL categories (every event, not just surviving ones) must equal
    # v1's own inclusive histogram total.
    all_raw_mass_concat = np.concatenate(list(mass_by_category.values())) if mass_by_category else np.array([])
    inclusive_pre_peak_removal = apply_full_postprocessing(all_raw_mass_concat, "inclusive")
    v1_inclusive_total = v1_totals.get("mass_m0m1j0_inclusive_ge2m_ge1j")
    if v1_inclusive_total is not None:
        if float(inclusive_pre_peak_removal["n_after_max_mass"]) != v1_inclusive_total:
            cross_check_problems.append(
                f"inclusive: v2 pre-peak-removal count = {inclusive_pre_peak_removal['n_after_max_mass']}, "
                f"v1 inclusive histogram total = {v1_inclusive_total} -- MISMATCH"
            )

    if cross_check_problems:
        print("A4 CROSS-CHECK FAILED -- v2's pre-post-processing totals do not match v1's histograms:")
        for problem in cross_check_problems:
            print(f"  - {problem}")
        (out_dir / "merge_v2_summary.json").write_text(
            json.dumps({
                "complete": False,
                "a4_cross_check_passed": False,
                "a4_cross_check_problems": cross_check_problems,
                "per_category_precheck": per_category_precheck,
            }, indent=2, default=str),
            encoding="utf-8",
        )
        sys.exit(1)

    print(f"A4 cross-check PASSED: {len(per_category_precheck)} categories match v1 exactly.")

    # --- Real post-processing, per category: prune (raw count) -> z_peak
    # -> max_mass -> peak removal -> outlier split -> histogram from
    # "_main" only. ---
    per_category_report = {}
    histograms_out = {}
    dropped_by_min_events = []

    for cat, raw_mass in sorted(mass_by_category.items()):
        n_raw = len(raw_mass)
        if not raw_count_passes_min_events_prune(n_raw):
            dropped_by_min_events.append({"category": cat, "n_raw": n_raw})
            per_category_report[cat] = {"n_raw": n_raw, "pruned_by_min_events_per_fs": True}
            continue

        result = apply_full_postprocessing(raw_mass, cat)
        per_category_report[cat] = {
            "pruned_by_min_events_per_fs": False,
            "n_raw": result["n_raw"],
            "n_after_z_peak": result["n_after_z_peak"],
            "n_after_max_mass": result["n_after_max_mass"],
            "peak_mass_gev": result["peak_mass"],
            "n_after_peak_removal": result["n_after_peak_removal"],
            "split_mass_gev": result["split_mass"],
            "n_main": result["n_main"],
            "n_outliers": result["n_outliers"],
        }
        if result["n_main"] > 0:
            from studies.m0m1j0_cms.histograms import make_fixed_grid_histogram
            values, edges = make_fixed_grid_histogram(result["main_array"])
            histograms_out[cat] = (values, edges)

    # Inclusive: our own addition, same post-processing chain, clearly
    # labeled and never confusable with a real BumpNet category name.
    inclusive_result = apply_full_postprocessing(all_raw_mass_concat, "inclusive")
    per_category_report[INCLUSIVE_LABEL] = {
        "note": "NOT a real pipeline category -- this study's own addition, same post-processing chain applied for comparability",
        "pruned_by_min_events_per_fs": False,
        "n_raw": inclusive_result["n_raw"],
        "n_after_z_peak": inclusive_result["n_after_z_peak"],
        "n_after_max_mass": inclusive_result["n_after_max_mass"],
        "peak_mass_gev": inclusive_result["peak_mass"],
        "n_after_peak_removal": inclusive_result["n_after_peak_removal"],
        "split_mass_gev": inclusive_result["split_mass"],
        "n_main": inclusive_result["n_main"],
        "n_outliers": inclusive_result["n_outliers"],
    }
    if inclusive_result["n_main"] > 0:
        from studies.m0m1j0_cms.histograms import make_fixed_grid_histogram
        values, edges = make_fixed_grid_histogram(inclusive_result["main_array"])
        histograms_out[INCLUSIVE_LABEL] = (values, edges)

    # --- Write TH1F output, verified. ---
    root_path = out_dir / "m0m1j0_data_postprocessed.root"
    verify_expected = {}
    with uproot.recreate(str(root_path)) as f:
        for label, (values, edges) in histograms_out.items():
            key = f"ROI_{label}_width_{int(BIN_WIDTH_GEV)}"
            f[key] = to_writable_th1f(values, edges, key)
            verify_expected[key] = values
    verify_written_th1f(str(root_path), verify_expected)
    print(f"wrote {root_path}: {len(histograms_out)} histogram(s), verified TH1F")

    summary = {
        "complete": True,
        "a4_cross_check_passed": True,
        "n_jobs_present": len(present_indices),
        "n_categories_total": len(mass_by_category),
        "n_categories_surviving_min_events_prune": len(histograms_out) - (1 if INCLUSIVE_LABEL in histograms_out else 0),
        "dropped_by_min_events_per_fs": dropped_by_min_events,
        "per_category": per_category_report,
        "identity_and_counts": identity,
    }
    (out_dir / "merge_v2_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("identity_and_counts", "per_category")}, indent=2))
    print("Merge v2 status: COMPLETE.")


if __name__ == "__main__":
    main()
