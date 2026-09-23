#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- selection-variants task (supervisor request).
Merge step: combines every job's per-variant mass_by_category_<variant>.npz
(written by run_m0m1j0_variants_on_file.py / _on_mc_file.py) into, per
sample (data/ttbar) and per variant (V0/V1/V2/V3):
  - the real pipeline post-processing chain applied per category, via
    studies.m0m1j0_cms.postprocessing (the same functions/order as the
    committed v2 correction -- NOT re-derived),
  - a written, verified TH1F ROOT file (post-processed, "_main" only,
    same convention as merge_full_v2.py/merge_ttbar.py),
  - one shared comparison_summary.json across every sample x variant.

V0 CROSS-CHECK (mandatory, not optional): for BOTH samples, this script's
own V0_baseline per-category post-processing result (n_raw, n_after_z_peak,
n_after_max_mass, peak_mass_gev, n_main, n_outliers, split_mass_gev) must
match the EXISTING, ALREADY-COMMITTED v2 result
(studies/m0m1j0_cms/v2/data/merge_v2_summary.json,
studies/m0m1j0_cms/v2/ttbar/merge_ttbar_summary.json) EXACTLY, category by
category -- same files, same selection (V0 IS the same selection as the
original v2 run; this script's V0_baseline spec is
select_event_selection_cutflow's own bare defaults, see variants.py's own
self-check). Any mismatch STOPS this script (exits non-zero) before any
output is written, rather than proceeding on an unverified premise.

Usage:
    python merge_variants.py \
        --sample data \
        --jobs-base /storage/agrp/berkom/atlas-utilization/output/m0m1j0_variants_data \
        --mapping-file .../job_index_map.txt \
        --v0-cross-check-json studies/m0m1j0_cms/v2/data/merge_v2_summary.json \
        --out-dir studies/m0m1j0_cms/v3_variants
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms.cluster.merge_full import load_job_index_map, _normalize_url  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list, fetch_record_number_events  # noqa: E402
from studies.m0m1j0_cms.histograms import make_fixed_grid_histogram, to_writable_th1f, verify_written_th1f  # noqa: E402
from studies.m0m1j0_cms.postprocessing import apply_full_postprocessing, raw_count_passes_min_events_prune  # noqa: E402
from studies.m0m1j0_cms import variants  # noqa: E402

BIN_WIDTH_GEV = 10.0
INCLUSIVE_LABEL_TEMPLATE = "mass_m0m1j0_inclusive_ge2m_ge1j_{variant}_postprocessed"

SAMPLE_RECORDS = {"data": (30522, 30555), "ttbar": (67801,)}


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def check_identity_and_counts(jobs_base: Path, job_index_map: dict, records) -> dict:
    """Generalized version of merge_full.check_identity_and_counts /
    merge_ttbar.check_identity_and_counts_single_record: parameterized by
    `records` (works for both data's two records and ttbar's one), and
    reads THIS task's own job_metadata.json shape (`n_read` at the top
    level, not nested under "cutflow" -- the variants drivers report one
    n_read shared by all 4 variants, since all 4 are computed from the
    SAME file read, so there is exactly one n_read per job, not one per
    variant)."""
    problems = []
    per_job = {}

    current_urls_by_record = {r: fetch_file_list(r) for r in records}

    assigned_by_url = {}
    for idx, (record_id, file_index) in sorted(job_index_map.items()):
        job_dir = jobs_base / f"job_{idx}"
        meta = _load_json(job_dir / "job_metadata.json")
        if meta is None:
            per_job[idx] = {"status": "MISSING_METADATA", "record_id": record_id, "file_index": file_index}
            problems.append(f"job_{idx}: missing job_metadata.json")
            continue

        recorded_url = meta["file_url"]
        current_urls = current_urls_by_record.get(record_id, [])
        current_url_at_index = current_urls[file_index] if file_index < len(current_urls) else None
        matches_portal = recorded_url == current_url_at_index
        if not matches_portal:
            problems.append(
                f"job_{idx} (record {record_id}, file-index {file_index}): recorded URL "
                f"{recorded_url!r} != portal's CURRENT file at that index ({current_url_at_index!r})"
            )

        norm = _normalize_url(recorded_url)
        assigned_by_url.setdefault(norm, []).append(idx)

        recorded_n_read = meta["n_read"]
        try:
            live_n_entries = uproot.open(recorded_url)["Events"].num_entries
        except Exception as e:  # noqa: BLE001
            per_job[idx] = {
                "status": "XROOTD_REOPEN_FAILED", "record_id": record_id, "file_index": file_index,
                "recorded_url": recorded_url, "error": f"{type(e).__name__}: {e}",
            }
            problems.append(f"job_{idx}: could not re-open {recorded_url!r} to verify entry count -- {e}")
            continue

        count_matches = live_n_entries == recorded_n_read
        if not count_matches:
            problems.append(
                f"job_{idx}: recorded n_read={recorded_n_read} but re-opening the same file now "
                f"reports {live_n_entries} entries"
            )

        per_job[idx] = {
            "status": "OK", "record_id": record_id, "file_index": file_index,
            "recorded_url": recorded_url, "current_portal_url_at_this_index": current_url_at_index,
            "matches_current_portal": matches_portal, "recorded_n_read": recorded_n_read,
            "live_reopen_n_entries": live_n_entries, "count_matches_live_reopen": count_matches,
        }

    duplicated = {u: idxs for u, idxs in assigned_by_url.items() if len(idxs) > 1}
    if duplicated:
        problems.append(f"duplicate file URL(s) assigned to more than one job index: {duplicated}")

    present_n_read_sum = sum(v["recorded_n_read"] for v in per_job.values() if v.get("status") == "OK")
    portal_totals = {r: fetch_record_number_events(r) for r in records}
    portal_total_events = sum(v["number_events"] for v in portal_totals.values())
    total_matches = present_n_read_sum == portal_total_events
    if not total_matches:
        problems.append(
            f"sum of n_read across present jobs ({present_n_read_sum}) != current portal total "
            f"({portal_total_events})"
        )

    missing_indices = sorted(idx for idx, v in per_job.items() if v.get("status") == "MISSING_METADATA")
    return {
        "per_job": per_job, "duplicated_urls": duplicated,
        "present_n_read_sum": present_n_read_sum, "current_portal_total_events": portal_total_events,
        "portal_totals_by_record": portal_totals, "missing_indices": missing_indices, "problems": problems,
    }


def load_all_mass_by_category(jobs_base: Path, present_indices: list, variant_key: str, need_genweight: bool) -> dict:
    chunks: dict = {}
    weight_chunks: dict = {}
    for idx in present_indices:
        npz_path = jobs_base / f"job_{idx}" / f"mass_by_category_{variant_key}.npz"
        if not npz_path.exists():
            continue
        with np.load(npz_path, allow_pickle=True) as npz:
            categories = npz["category"]
            masses = npz["m0m1j0_raw_gev"]
            weights = npz["genWeight"] if (need_genweight and "genWeight" in npz.files) else None
        for cat in np.unique(categories):
            mask = categories == cat
            chunks.setdefault(str(cat), []).append(masses[mask])
            if weights is not None:
                weight_chunks.setdefault(str(cat), []).append(weights[mask])
    out = {cat: np.concatenate(arrs) for cat, arrs in chunks.items()}
    out_w = {cat: np.concatenate(arrs) for cat, arrs in weight_chunks.items()} if need_genweight else None
    return out, out_w


def load_per_variant_diagnostics(jobs_base: Path, present_indices: list) -> dict:
    """Sums, ACROSS ALL PRESENT JOBS, the per-variant diagnostic counters
    each data job reports in its own job_metadata.json. ttbar jobs report
    none of this (data-only per the task), so callers for ttbar simply
    never call this."""
    totals = {v: {
        "n_diagnostic_population": 0, "n_dimuon_lt_2gev": 0, "n_dimuon_lt_4gev": 0,
        "dimuon_mass_hist_full_counts": None, "dimuon_mass_hist_full_edges": None,
        "dimuon_mass_hist_zoom_counts": None, "dimuon_mass_hist_zoom_edges": None,
    } for v in variants.VARIANT_ORDER}
    v2_totals = {
        "n_diagnostic_population_v2": 0,
        "n_leading_jet_dr_lt_p4_to_muon": 0, "n_leading_jet_pt_within_10pct_of_muon": 0,
    }
    for idx in present_indices:
        meta = _load_json(jobs_base / f"job_{idx}" / "job_metadata.json")
        if meta is None or "per_variant_diagnostics" not in meta:
            continue
        for v in variants.VARIANT_ORDER:
            d = meta["per_variant_diagnostics"].get(v, {})
            totals[v]["n_diagnostic_population"] += d.get("n_diagnostic_population", 0)
            totals[v]["n_dimuon_lt_2gev"] += d.get("n_dimuon_lt_2gev", 0)
            totals[v]["n_dimuon_lt_4gev"] += d.get("n_dimuon_lt_4gev", 0)
            for hist_key, edges_key in (
                ("dimuon_mass_hist_full_counts", "dimuon_mass_hist_full_edges"),
                ("dimuon_mass_hist_zoom_counts", "dimuon_mass_hist_zoom_edges"),
            ):
                counts = d.get(hist_key)
                if counts is None:
                    continue
                if totals[v][hist_key] is None:
                    totals[v][hist_key] = list(counts)
                    totals[v][edges_key] = d.get(edges_key)
                else:
                    totals[v][hist_key] = [a + b for a, b in zip(totals[v][hist_key], counts)]
        v2d = meta["per_variant_diagnostics"].get("V2_no_jet_lepton_cleaning", {})
        v2_totals["n_diagnostic_population_v2"] += v2d.get("n_diagnostic_population_v2", 0)
        v2_totals["n_leading_jet_dr_lt_p4_to_muon"] += v2d.get("n_leading_jet_dr_lt_p4_to_muon", 0)
        v2_totals["n_leading_jet_pt_within_10pct_of_muon"] += v2d.get("n_leading_jet_pt_within_10pct_of_muon", 0)

    for v in variants.VARIANT_ORDER:
        n = totals[v]["n_diagnostic_population"]
        totals[v]["frac_dimuon_lt_2gev"] = (totals[v]["n_dimuon_lt_2gev"] / n) if n else None
        totals[v]["frac_dimuon_lt_4gev"] = (totals[v]["n_dimuon_lt_4gev"] / n) if n else None
    n2 = v2_totals["n_diagnostic_population_v2"]
    v2_totals["frac_leading_jet_dr_lt_p4_to_muon"] = (v2_totals["n_leading_jet_dr_lt_p4_to_muon"] / n2) if n2 else None
    v2_totals["frac_leading_jet_pt_within_10pct_of_muon"] = (
        v2_totals["n_leading_jet_pt_within_10pct_of_muon"] / n2
    ) if n2 else None
    totals["V2_no_jet_lepton_cleaning"].update(v2_totals)
    return totals


def sum_cutflow(jobs_base: Path, present_indices: list) -> dict:
    """{variant: {cutflow_field: summed_value}} across all present jobs."""
    out = {v: {} for v in variants.VARIANT_ORDER}
    for idx in present_indices:
        meta = _load_json(jobs_base / f"job_{idx}" / "job_metadata.json")
        if meta is None:
            continue
        for v in variants.VARIANT_ORDER:
            cf = meta["per_variant_cutflow"].get(v, {})
            for k, val in cf.items():
                out[v][k] = out[v].get(k, 0) + val
    return out


def run_postprocessing_all_categories(mass_by_category: dict, variant_key: str) -> dict:
    """{category: apply_full_postprocessing(...) result dict} + the
    inclusive pseudo-category, same pattern as merge_full_v2.py."""
    per_category = {}
    for cat, raw_mass in sorted(mass_by_category.items()):
        n_raw = len(raw_mass)
        if not raw_count_passes_min_events_prune(n_raw):
            per_category[cat] = {"n_raw": n_raw, "pruned_by_min_events_per_fs": True}
            continue
        result = apply_full_postprocessing(raw_mass, cat)
        per_category[cat] = {"pruned_by_min_events_per_fs": False, **{
            k: result[k] for k in (
                "n_raw", "n_after_z_peak", "n_after_max_mass", "peak_mass",
                "n_after_peak_removal", "split_mass", "n_main", "n_outliers",
            )
        }, "_main_array": result["main_array"]}

    all_raw = np.concatenate(list(mass_by_category.values())) if mass_by_category else np.array([])
    inclusive_label = INCLUSIVE_LABEL_TEMPLATE.format(variant=variant_key)
    inclusive_result = apply_full_postprocessing(all_raw, "inclusive")
    per_category[inclusive_label] = {"pruned_by_min_events_per_fs": False, **{
        k: inclusive_result[k] for k in (
            "n_raw", "n_after_z_peak", "n_after_max_mass", "peak_mass",
            "n_after_peak_removal", "split_mass", "n_main", "n_outliers",
        )
    }, "_main_array": inclusive_result["main_array"], "_is_inclusive": True}
    return per_category


# The two EXISTING, already-committed v2 reference files (predating this
# task) picked different literal names for "the inclusive pseudo-category"
# -- merge_full_v2.py used "..._v2_postprocessed", merge_ttbar.py used
# "..._ttbar_postprocessed". This task's OWN inclusive label
# (INCLUSIVE_LABEL_TEMPLATE, e.g. "..._V0_baseline_postprocessed") is
# necessarily a third, different string (it's per-variant) -- so the
# cross-check must map "my inclusive label" -> "the reference file's own
# inclusive label" explicitly, per sample, rather than guess a shared
# convention that doesn't actually exist between the two pre-existing
# reference files.
V0_REFERENCE_INCLUSIVE_LABEL = {
    "data": "mass_m0m1j0_inclusive_ge2m_ge1j_v2_postprocessed",
    "ttbar": "mass_m0m1j0_inclusive_ge2m_ge1j_ttbar_postprocessed",
}


def cross_check_against_v0(per_category: dict, v0_reference_summary: dict, sample: str) -> list:
    """Compares this run's V0_baseline per-category post-processing result
    against the EXISTING, already-committed v2 result, field by field,
    for every category present in BOTH. Returns a list of mismatch
    description strings (empty iff every shared category matches
    exactly)."""
    problems = []
    ref = v0_reference_summary["per_category"]
    fields = ("n_raw", "n_after_z_peak", "n_after_max_mass", "peak_mass", "n_main", "n_outliers", "split_mass")
    field_to_ref_key = {
        "n_raw": "n_raw", "n_after_z_peak": "n_after_z_peak", "n_after_max_mass": "n_after_max_mass",
        "peak_mass": "peak_mass_gev", "n_main": "n_main", "n_outliers": "n_outliers", "split_mass": "split_mass_gev",
    }
    checked = 0
    for cat, mine in per_category.items():
        cat_for_lookup = cat
        if mine.get("_is_inclusive"):
            cat_for_lookup = V0_REFERENCE_INCLUSIVE_LABEL[sample]
        theirs = ref.get(cat_for_lookup)
        if theirs is None:
            continue  # category didn't exist (or was pruned) in one of the two runs -- not a mismatch by itself
        if mine.get("pruned_by_min_events_per_fs") or theirs.get("pruned_by_min_events_per_fs"):
            if bool(mine.get("pruned_by_min_events_per_fs")) != bool(theirs.get("pruned_by_min_events_per_fs")):
                problems.append(f"category {cat!r}: pruned_by_min_events_per_fs differs (mine={mine.get('pruned_by_min_events_per_fs')}, v2={theirs.get('pruned_by_min_events_per_fs')})")
            continue
        checked += 1
        for field in fields:
            mine_val = mine.get(field)
            their_val = theirs.get(field_to_ref_key[field])
            if mine_val != their_val:
                problems.append(f"category {cat!r} field {field!r}: mine={mine_val!r} v2={their_val!r} -- MISMATCH")
    if checked == 0:
        problems.append("V0 cross-check found ZERO categories in common with the reference v2 summary -- refusing to treat an empty comparison as a pass")
    return problems


def write_th1f_root(per_category: dict, out_path: Path) -> dict:
    verify_expected = {}
    with uproot.recreate(str(out_path)) as f:
        for cat, result in per_category.items():
            if result.get("pruned_by_min_events_per_fs") or result.get("n_main", 0) == 0:
                continue
            values, edges = make_fixed_grid_histogram(result["_main_array"])
            key = f"ROI_{cat}_width_{int(BIN_WIDTH_GEV)}"
            f[key] = to_writable_th1f(values, edges, key)
            verify_expected[key] = values
    verify_written_th1f(str(out_path), verify_expected)
    return verify_expected


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sample", required=True, choices=["data", "ttbar"])
    p.add_argument("--jobs-base", required=True)
    p.add_argument("--mapping-file", required=True)
    p.add_argument("--v0-cross-check-json", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    jobs_base = Path(args.jobs_base)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    job_index_map = load_job_index_map(Path(args.mapping_file))
    records = SAMPLE_RECORDS[args.sample]
    identity = check_identity_and_counts(jobs_base, job_index_map, records)
    present_indices = sorted(i for i, v in identity["per_job"].items() if v.get("status") == "OK")

    result_summary = {"sample": args.sample, "identity_and_counts": identity}
    if identity["problems"]:
        print(f"[{args.sample}] IDENTITY/COMPLETENESS CHECK FAILED -- refusing to proceed:")
        for problem in identity["problems"]:
            print(f"  - {problem}")
        result_summary["complete"] = False
        (out_dir / f"merge_variants_{args.sample}_summary.json").write_text(
            json.dumps(result_summary, indent=2, default=str), encoding="utf-8"
        )
        sys.exit(1)
    print(f"[{args.sample}] Identity/completeness check PASSED: {len(present_indices)} jobs, no problems.")

    v0_reference = _load_json(Path(args.v0_cross_check_json))
    if v0_reference is None:
        print(f"[{args.sample}] Could not load V0 cross-check reference {args.v0_cross_check_json} -- refusing to proceed.")
        sys.exit(1)

    cutflow_sums = sum_cutflow(jobs_base, present_indices)
    need_genweight = args.sample == "ttbar"
    diagnostics = load_per_variant_diagnostics(jobs_base, present_indices) if args.sample == "data" else None

    per_variant_report = {}
    per_variant_histograms = {}
    v0_n_main_by_category = None

    for variant_key in variants.VARIANT_ORDER:
        mass_by_category, weight_by_category = load_all_mass_by_category(
            jobs_base, present_indices, variant_key, need_genweight
        )
        per_category = run_postprocessing_all_categories(mass_by_category, variant_key)

        if variant_key == "V0_baseline":
            cross_check_problems = cross_check_against_v0(per_category, v0_reference, args.sample)
            if cross_check_problems:
                print(f"[{args.sample}] V0 CROSS-CHECK FAILED -- refusing to proceed:")
                for problem in cross_check_problems:
                    print(f"  - {problem}")
                result_summary["complete"] = False
                result_summary["v0_cross_check_passed"] = False
                result_summary["v0_cross_check_problems"] = cross_check_problems
                (out_dir / f"merge_variants_{args.sample}_summary.json").write_text(
                    json.dumps(result_summary, indent=2, default=str), encoding="utf-8"
                )
                sys.exit(1)
            print(f"[{args.sample}] V0 cross-check PASSED against {args.v0_cross_check_json}.")
            result_summary["v0_cross_check_passed"] = True
            v0_n_main_by_category = {cat: r.get("n_main", 0) for cat, r in per_category.items()}

        root_path = out_dir / f"{args.sample}_{variant_key}.root"
        written = write_th1f_root(per_category, root_path)
        print(f"[{args.sample}] {variant_key}: wrote {root_path} ({len(written)} histogram(s))")

        inclusive_label = INCLUSIVE_LABEL_TEMPLATE.format(variant=variant_key)
        inclusive = per_category.get(inclusive_label, {})
        report = {
            "cutflow": cutflow_sums.get(variant_key, {}),
            "n_events_in_inclusive_histogram": inclusive.get("n_main"),
            "peak_bin_gev": inclusive.get("peak_mass"),
            "first_empty_bin_cut_gev": inclusive.get("split_mass"),
            "n_outliers_excluded": inclusive.get("n_outliers"),
            "n_categories_total": len([c for c in per_category if not per_category[c].get("_is_inclusive")]),
            "n_categories_surviving_min_events_prune": len([
                c for c, r in per_category.items()
                if not r.get("_is_inclusive") and not r.get("pruned_by_min_events_per_fs") and r.get("n_main", 0) > 0
            ]),
            "per_category": {
                cat: {k: v for k, v in r.items() if not k.startswith("_")}
                for cat, r in per_category.items()
            },
        }
        if v0_n_main_by_category is not None:
            my_n_main_by_category = {cat: r.get("n_main", 0) for cat, r in per_category.items()}
            report["ratio_to_v0"] = {
                "inclusive": (
                    (inclusive.get("n_main") / v0_n_main_by_category.get(INCLUSIVE_LABEL_TEMPLATE.format(variant="V0_baseline")))
                    if v0_n_main_by_category.get(INCLUSIVE_LABEL_TEMPLATE.format(variant="V0_baseline"))
                    else None
                ),
                "per_category": {
                    cat: (my_n_main_by_category[cat] / v0_n_main_by_category[cat])
                    for cat in my_n_main_by_category
                    if cat in v0_n_main_by_category and v0_n_main_by_category[cat] > 0
                },
            }
        if diagnostics is not None:
            report["diagnostics"] = diagnostics[variant_key]

        per_variant_report[variant_key] = report
        per_variant_histograms[variant_key] = per_category

    result_summary["complete"] = True
    result_summary["n_jobs_present"] = len(present_indices)
    result_summary["per_variant"] = per_variant_report
    (out_dir / f"merge_variants_{args.sample}_summary.json").write_text(
        json.dumps(result_summary, indent=2, default=str), encoding="utf-8"
    )
    print(f"[{args.sample}] wrote merge_variants_{args.sample}_summary.json")
    print(f"[{args.sample}] Merge status: COMPLETE.")

    return per_variant_histograms, result_summary


if __name__ == "__main__":
    main()
