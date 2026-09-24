#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- Part B: ttbar MC merge (used for BOTH the 2-file
pilot and the full 49-file run -- which one only depends on --jobs-base/
--mapping-file).

Identity/completeness checks: same rules as the data study's merge_full.py
(every expected index present, each job's recorded URL matches the
CURRENT portal list, each file re-opened over XRootD now still reports
the same entry count, no duplicates, summed n_read equals the current
portal total) -- reimplemented here for a SINGLE record (67801) rather
than importing merge_full.py's check_identity_and_counts, which is
hardwired to the two DATA records via a module-level RECORDS constant;
monkeypatching that from production code would be fragile, so this is a
small, deliberately parallel copy for one record instead.

Real post-processing: same studies.m0m1j0_cms.postprocessing chain as
the data v2 correction (prune on raw count, z_peak_cutoff, max_mass_cutoff,
peak removal, first-empty-bin split, histogram from "_main" only) --
applied to EVERY job's concatenated raw mass_by_category.npz per
category. No A4-style cross-check here (there is no prior ttbar
histogram to cross-check against -- this is the only ttbar run).

Two ROOT outputs: m0m1j0_ttbar_postprocessed.root (UNWEIGHTED event
counts -- the primary output, directly comparable in format to the data
histogram) and m0m1j0_ttbar_postprocessed_weighted.root (genWeight-
weighted sums in each bin) -- built from the SAME main_mask
(studies.m0m1j0_cms.postprocessing.apply_full_postprocessing's own
returned mask) applied to both the mass array and the aligned genWeight
array, so both histograms describe exactly the same selected events.

Also builds the sanity-check PNGs (dimuon mass, b-tagged-jet count,
leading-jet pT, genWeight distribution, inclusive m0m1j0 AFTER real
post-processing, top-5 categories) -- used for the pilot's own go/no-go
review AND as the final Part B plots for the full run.

Usage:
    python merge_ttbar.py \
        --jobs-base /storage/agrp/berkom/atlas-utilization/output/m0m1j0_ttbar_pilot \
        --mapping-file /storage/agrp/berkom/atlas-utilization/output/m0m1j0_ttbar_pilot/job_index_map.txt \
        --out-dir studies/m0m1j0_cms/v2/ttbar_pilot_check
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms.cluster.merge_full import load_job_index_map, _normalize_url  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import (  # noqa: E402
    fetch_file_list, fetch_record_number_events,
)
from studies.m0m1j0_cms.histograms import INCLUSIVE_HIST_NAME, make_fixed_grid_histogram, to_writable_th1f, verify_written_th1f  # noqa: E402
from studies.m0m1j0_cms.postprocessing import apply_full_postprocessing, raw_count_passes_min_events_prune  # noqa: E402

TTBAR_RECORD_ID = 67801
BIN_WIDTH_GEV = 10.0
INCLUSIVE_LABEL = "mass_m0m1j0_inclusive_ge2m_ge1j_ttbar_postprocessed"


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def check_identity_and_counts_single_record(jobs_base: Path, job_index_map: dict) -> dict:
    problems = []
    per_job = {}
    current_urls = fetch_file_list(TTBAR_RECORD_ID)
    assigned_by_url = {}

    for idx, (record_id, file_index) in sorted(job_index_map.items()):
        job_dir = jobs_base / f"job_{idx}"
        meta = _load_json(job_dir / "job_metadata.json")
        if meta is None:
            per_job[idx] = {"status": "MISSING_METADATA", "record_id": record_id, "file_index": file_index}
            problems.append(f"job_{idx}: missing job_metadata.json")
            continue

        recorded_url = meta["file_url"]
        current_url_at_index = current_urls[file_index] if file_index < len(current_urls) else None
        matches_portal = recorded_url == current_url_at_index
        if not matches_portal:
            problems.append(
                f"job_{idx} (file-index {file_index}): recorded URL {recorded_url!r} != "
                f"portal's CURRENT file at that index ({current_url_at_index!r})"
            )

        norm = _normalize_url(recorded_url)
        assigned_by_url.setdefault(norm, []).append(idx)

        recorded_n_read = meta["cutflow"]["n_read"]
        try:
            live_n_entries = uproot.open(recorded_url)["Events"].num_entries
        except Exception as e:  # noqa: BLE001
            per_job[idx] = {
                "status": "XROOTD_REOPEN_FAILED", "record_id": record_id, "file_index": file_index,
                "recorded_url": recorded_url, "error": f"{type(e).__name__}: {e}",
            }
            problems.append(f"job_{idx}: could not re-open {recorded_url!r} -- {e}")
            continue

        count_matches = live_n_entries == recorded_n_read
        if not count_matches:
            problems.append(
                f"job_{idx}: recorded n_read={recorded_n_read} but re-opening now reports {live_n_entries}"
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
    portal_meta = fetch_record_number_events(TTBAR_RECORD_ID)
    # Only meaningful as an exact-total check for a FULL run (all files);
    # a pilot deliberately reads a subset, so this is reported, not
    # treated as a "problem", when jobs_expected < the portal's own file count.
    is_full_coverage = len(job_index_map) == portal_meta["number_files"]
    total_matches = (present_n_read_sum == portal_meta["number_events"]) if is_full_coverage else None
    if is_full_coverage and not total_matches:
        problems.append(
            f"sum of n_read across present jobs ({present_n_read_sum}) != current portal total "
            f"({portal_meta['number_events']})"
        )

    missing_indices = sorted(idx for idx, v in per_job.items() if v.get("status") == "MISSING_METADATA")
    return {
        "per_job": per_job, "duplicated_urls": duplicated,
        "present_n_read_sum": present_n_read_sum,
        "portal_total_events": portal_meta["number_events"],
        "portal_total_files": portal_meta["number_files"],
        "is_full_coverage_submission": is_full_coverage,
        "total_matches_portal": total_matches,
        "missing_indices": missing_indices, "problems": problems,
    }


def _bumpnet_name_from_root_name(root_name: str) -> str:
    name = root_name[len("ROI_"):] if root_name.startswith("ROI_") else root_name
    return re.sub(r"_width_\d+$", "", name)


def load_all_mass_by_category(jobs_base: Path, present_indices: list) -> dict:
    """{category_label: (concatenated raw mass array, concatenated genWeight array)}."""
    chunks: dict = {}
    for idx in present_indices:
        npz_path = jobs_base / f"job_{idx}" / "mass_by_category.npz"
        if not npz_path.exists():
            continue
        with np.load(npz_path, allow_pickle=True) as npz:
            categories = npz["category"]
            masses = npz["m0m1j0_raw_gev"]
            weights = npz["genWeight"]
        for cat in np.unique(categories):
            mask = categories == cat
            chunks.setdefault(str(cat), {"mass": [], "weight": []})
            chunks[str(cat)]["mass"].append(masses[mask])
            chunks[str(cat)]["weight"].append(weights[mask])
    return {
        cat: (np.concatenate(v["mass"]), np.concatenate(v["weight"]))
        for cat, v in chunks.items()
    }


def load_all_sanity_arrays(jobs_base: Path, present_indices: list) -> dict:
    dimuon, jet_pt, n_bjets, gen_weight = [], [], [], []
    for idx in present_indices:
        data = _load_json(jobs_base / f"job_{idx}" / "sanity_arrays.json")
        if data:
            dimuon.extend(data.get("dimuon_mass_gev", []))
            jet_pt.extend(data.get("leading_jet_pt_gev", []))
            n_bjets.extend(data.get("n_bjets", []))
            gen_weight.extend(data.get("genWeight", []))
    return {"dimuon_mass_gev": dimuon, "leading_jet_pt_gev": jet_pt, "n_bjets": n_bjets, "genWeight": gen_weight}


def sum_metadata_genweight(jobs_base: Path, present_indices: list) -> dict:
    total_sum_genweight = 0.0
    total_n_read = 0
    n_negative_weighted_estimate = 0.0
    for idx in present_indices:
        meta = _load_json(jobs_base / f"job_{idx}" / "job_metadata.json")
        if meta is None:
            continue
        total_sum_genweight += meta.get("sum_genWeight_all_read_events", 0.0)
        n_read = meta["cutflow"]["n_read"]
        total_n_read += n_read
        n_negative_weighted_estimate += meta.get("negative_weight_fraction_all_read_events", 0.0) * n_read
    overall_negative_fraction = (n_negative_weighted_estimate / total_n_read) if total_n_read else 0.0
    return {
        "sum_genWeight_all_read_events": total_sum_genweight,
        "n_read_total": total_n_read,
        "negative_weight_fraction_all_read_events": overall_negative_fraction,
    }


def plot_dimuon_mass(dimuon_mass_gev: list, out_path: Path):
    arr = np.array([x for x in dimuon_mass_gev if x == x])
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(arr, bins=100, range=(0, 400), histtype="stepfilled", color="#8172b3", alpha=0.8)
    ax.set_xlabel("Dimuon mass [GeV] (leading + subleading selected muon)")
    ax.set_ylabel("Events / 4 GeV")
    ax.set_title("ttbar MC: dimuon mass of the selected pair (expect NO dominant Z peak)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_n_bjets(n_bjets: list, out_path: Path) -> float:
    arr = np.array(n_bjets)
    frac_ge1 = float(np.mean(arr >= 1)) if len(arr) else 0.0
    fig, ax = plt.subplots(figsize=(6, 5))
    counts = np.bincount(arr, minlength=5)[:5]
    ax.bar(range(len(counts)), counts, color="#55a868")
    ax.set_xlabel("Number of selected b-tagged jets")
    ax.set_ylabel("Events")
    ax.set_title(f"ttbar MC: b-jet multiplicity ({frac_ge1*100:.1f}% have >=1 b-jet)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return frac_ge1


def plot_leading_jet_pt(jet_pt_gev: list, out_path: Path):
    arr = np.array([x for x in jet_pt_gev if x == x])
    fig, ax = plt.subplots(figsize=(7, 5))
    hi = max(200.0, float(np.percentile(arr, 99)) if len(arr) else 200.0)
    ax.hist(arr, bins=60, range=(0, hi), histtype="stepfilled", color="#55a868", alpha=0.8)
    ax.axvline(30.0, color="red", linestyle="--", label="30 GeV jet pT cut")
    ax.set_xlabel("Leading (light) jet pT [GeV]")
    ax.set_ylabel(f"Events / {hi/60:.1f} GeV")
    ax.set_title("ttbar MC: leading light-jet pT")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_genweight(gen_weight: list, out_path: Path):
    arr = np.array(gen_weight)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(arr, bins=60, histtype="stepfilled", color="#c44e52", alpha=0.8)
    ax.set_xlabel("genWeight (selected events)")
    ax.set_ylabel("Events")
    ax.set_title("ttbar MC: genWeight distribution (selected events)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_inclusive_log(values: np.ndarray, edges: np.ndarray, out_path: Path):
    nonzero = np.nonzero(values)[0]
    last_bin = int(nonzero.max()) + 1 if len(nonzero) else 10
    centers = (edges[:-1] + edges[1:]) / 2
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.step(centers[:last_bin], values[:last_bin], where="mid", color="#8172b3",
            label=f"ttbar MC, TTTo2L2Nu (record 67801), unweighted (n={int(values.sum())})")
    ax.set_yscale("log")
    ax.set_xlabel("m(μμ j) [GeV]")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_title("m0m1j0 -- ttbar MC (TTTo2L2Nu)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_top_categories(kept_hists: dict, out_path: Path, top_n: int = 5):
    scored = []
    for label, (values, edges, n_main) in kept_hists.items():
        if label == INCLUSIVE_LABEL:
            continue
        scored.append((n_main, label, values, edges))
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:top_n]

    fig, ax = plt.subplots(figsize=(8, 5))
    for n_main, label, values, edges in top:
        nonzero = np.nonzero(values)[0]
        last_bin = int(nonzero.max()) + 1 if len(nonzero) else 10
        centers = (edges[:-1] + edges[1:]) / 2
        ax.step(centers[:last_bin], values[:last_bin], where="mid", label=f"{label} (n={n_main})")
    ax.set_yscale("log")
    ax.set_xlabel("m0m1j0 [GeV]")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_title(f"ttbar MC: top {top_n} categories by event count")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return [{"category": label, "n_main": n_main} for n_main, label, _, _ in top]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-base", required=True)
    p.add_argument("--mapping-file", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    jobs_base = Path(args.jobs_base)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    job_index_map = load_job_index_map(Path(args.mapping_file))
    identity = check_identity_and_counts_single_record(jobs_base, job_index_map)
    present_indices = sorted(i for i, v in identity["per_job"].items() if v.get("status") == "OK")

    if identity["problems"]:
        print("IDENTITY/COMPLETENESS CHECK FAILED:")
        for problem in identity["problems"]:
            print(f"  - {problem}")
        (out_dir / "merge_ttbar_summary.json").write_text(
            json.dumps({"complete": False, "identity_and_counts": identity}, indent=2), encoding="utf-8"
        )
        sys.exit(1)

    print(f"Identity/completeness check PASSED: {len(present_indices)} jobs, no problems.")

    mass_by_category = load_all_mass_by_category(jobs_base, present_indices)
    sanity = load_all_sanity_arrays(jobs_base, present_indices)
    genweight_totals = sum_metadata_genweight(jobs_base, present_indices)

    per_category_report = {}
    hists_unweighted = {}
    hists_weighted = {}
    dropped_by_min_events = []

    all_raw_mass = np.concatenate([m for m, _ in mass_by_category.values()]) if mass_by_category else np.array([])
    all_gen_weight = np.concatenate([w for _, w in mass_by_category.values()]) if mass_by_category else np.array([])

    for cat, (raw_mass, gen_weight) in sorted(mass_by_category.items()):
        n_raw = len(raw_mass)
        if not raw_count_passes_min_events_prune(n_raw):
            dropped_by_min_events.append({"category": cat, "n_raw": n_raw})
            per_category_report[cat] = {"n_raw": n_raw, "pruned_by_min_events_per_fs": True}
            continue

        result = apply_full_postprocessing(raw_mass, cat)
        per_category_report[cat] = {
            "pruned_by_min_events_per_fs": False,
            "n_raw": result["n_raw"], "n_after_z_peak": result["n_after_z_peak"],
            "n_after_max_mass": result["n_after_max_mass"], "peak_mass_gev": result["peak_mass"],
            "n_after_peak_removal": result["n_after_peak_removal"], "split_mass_gev": result["split_mass"],
            "n_main": result["n_main"], "n_outliers": result["n_outliers"],
        }
        if result["n_main"] > 0:
            values, edges = make_fixed_grid_histogram(result["main_array"])
            hists_unweighted[cat] = (values, edges, result["n_main"])
            weighted_main = gen_weight[result["main_mask"]]
            w_values, _ = np.histogram(result["main_array"], bins=edges, weights=weighted_main)
            hists_weighted[cat] = (w_values, edges, result["n_main"])
            per_category_report[cat]["sum_genWeight_main"] = float(weighted_main.sum())

    inclusive_result = apply_full_postprocessing(all_raw_mass, "inclusive")
    per_category_report[INCLUSIVE_LABEL] = {
        "note": "NOT a real pipeline category -- this study's own addition",
        "pruned_by_min_events_per_fs": False,
        "n_raw": inclusive_result["n_raw"], "n_after_z_peak": inclusive_result["n_after_z_peak"],
        "n_after_max_mass": inclusive_result["n_after_max_mass"], "peak_mass_gev": inclusive_result["peak_mass"],
        "n_after_peak_removal": inclusive_result["n_after_peak_removal"], "split_mass_gev": inclusive_result["split_mass"],
        "n_main": inclusive_result["n_main"], "n_outliers": inclusive_result["n_outliers"],
    }
    if inclusive_result["n_main"] > 0:
        values, edges = make_fixed_grid_histogram(inclusive_result["main_array"])
        hists_unweighted[INCLUSIVE_LABEL] = (values, edges, inclusive_result["n_main"])
        weighted_main = all_gen_weight[inclusive_result["main_mask"]]
        w_values, _ = np.histogram(inclusive_result["main_array"], bins=edges, weights=weighted_main)
        hists_weighted[INCLUSIVE_LABEL] = (w_values, edges, inclusive_result["n_main"])
        per_category_report[INCLUSIVE_LABEL]["sum_genWeight_main"] = float(weighted_main.sum())

    root_path = out_dir / "m0m1j0_ttbar_postprocessed.root"
    verify_expected = {}
    with uproot.recreate(str(root_path)) as f:
        for label, (values, edges, _n) in hists_unweighted.items():
            key = f"ROI_{label}_width_{int(BIN_WIDTH_GEV)}"
            f[key] = to_writable_th1f(values, edges, key)
            verify_expected[key] = values
    verify_written_th1f(str(root_path), verify_expected)
    print(f"wrote {root_path}: {len(hists_unweighted)} histogram(s), verified TH1F")

    weighted_root_path = out_dir / "m0m1j0_ttbar_postprocessed_weighted.root"
    verify_expected_w = {}
    with uproot.recreate(str(weighted_root_path)) as f:
        for label, (values, edges, _n) in hists_weighted.items():
            key = f"ROI_{label}_width_{int(BIN_WIDTH_GEV)}_genWeightSum"
            f[key] = to_writable_th1f(values, edges, key)
            verify_expected_w[key] = values
    verify_written_th1f(str(weighted_root_path), verify_expected_w)
    print(f"wrote {weighted_root_path}: {len(hists_weighted)} histogram(s), verified TH1F")

    plot_dimuon_mass(sanity["dimuon_mass_gev"], plots_dir / "dimuon_mass.png")
    frac_ge1_bjet = plot_n_bjets(sanity["n_bjets"], plots_dir / "n_bjets.png")
    plot_leading_jet_pt(sanity["leading_jet_pt_gev"], plots_dir / "leading_jet_pt.png")
    plot_genweight(sanity["genWeight"], plots_dir / "genweight.png")

    top_categories = []
    if INCLUSIVE_LABEL in hists_unweighted:
        values, edges, _n = hists_unweighted[INCLUSIVE_LABEL]
        plot_inclusive_log(values, edges, plots_dir / "inclusive_m0m1j0_logy.png")
        top_categories = plot_top_categories(hists_unweighted, plots_dir / "top5_categories.png")

    summary = {
        "complete": True,
        "n_jobs_present": len(present_indices),
        "n_categories_total": len(mass_by_category),
        "n_categories_surviving_min_events_prune": len(hists_unweighted) - (1 if INCLUSIVE_LABEL in hists_unweighted else 0),
        "dropped_by_min_events_per_fs": dropped_by_min_events,
        "per_category": per_category_report,
        "genweight_totals": genweight_totals,
        "sanity_summary": {
            "n_selected_events": len(sanity["dimuon_mass_gev"]),
            "fraction_with_ge1_bjet": frac_ge1_bjet,
        },
        "top_categories_by_event_count": top_categories,
        "identity_and_counts": identity,
    }
    (out_dir / "merge_ttbar_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("identity_and_counts", "per_category")}, indent=2))
    print("Merge ttbar status: COMPLETE.")


if __name__ == "__main__":
    main()
