#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- Step 2 FULL RUN merge.

Merges every job's output under --jobs-base (job_1..job_N, one per input
file across records 30522+30555), refusing "complete" unless ALL of the
following hold:
  - every expected index (from --mapping-file, i.e. what
    generate_job_index_map.py assigned at submission time) has a present
    job_metadata.json,
  - each job's recorded file_url matches the CURRENT portal file list at
    its (record, file_index) -- re-fetched FRESH here, not trusted from
    the submission-time mapping file (the portal can change mid-run),
  - each job's recorded file_url, re-opened over XRootD right now
    (metadata-only), has a Events-tree entry count matching that same
    job's own recorded n_read (catches a partial/corrupted read that
    still happened to exit 0),
  - no two jobs claim the same (normalized) file URL,
  - the sum of every present job's n_read equals the CURRENT portal's
    published total event count (fetch_record_number_events, summed over
    both records) -- reported as a mismatch, not silently ignored, if the
    portal's own total changed since generate_job_index_map.py ran.

Also produces the Step 2 (C) low-mass dimuon diagnostic: loads every
job's dimuon_diagnostics.npz, reports the <2 GeV / <4 GeV dimuon-mass
population's charge-product/deltaR/pT-ratio breakdown plus an m0m1j0
overlay, and writes a SEPARATE diagnostic-only ROOT file
(m0m1j0_diagnostic_variants.root) with the inclusive m0m1j0 histogram
recomputed excluding m(mumu)<4 GeV events -- built directly from the
per-job diagnostic npz's own (m0m1j0_gev, m_mumu_gev) pairs, since that
population is exactly the inclusive-histogram population. This is
diagnostic only: it does not touch, and is never written into, the main
merged histogram file.

Usage:
    python merge_full.py \
        --jobs-base /storage/agrp/berkom/atlas-utilization/output/m0m1j0_full \
        --mapping-file /storage/agrp/berkom/atlas-utilization/output/m0m1j0_full/job_index_map.txt \
        --out-dir studies/m0m1j0_cms/full
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

from studies.m0m1j0_cms.design_checks.common import (  # noqa: E402
    fetch_file_list, fetch_record_number_events,
)
from studies.m0m1j0_cms.histograms import (  # noqa: E402
    INCLUSIVE_HIST_NAME, to_writable_th1f, verify_written_th1f,
    make_fixed_grid_histogram,
)
from studies.m0m1j0_cms.selection import MIN_EVENTS_PER_FINAL_STATE, Z_PEAK_CUTOFF_GEV  # noqa: E402

RECORDS = (30522, 30555)
CUTFLOW_KEYS = [
    "n_read", "n_after_golden_json", "n_after_trigger", "n_after_ge2mu",
    "n_after_ge1jet_after_cleaning", "n_after_z_peak_and_mass_cutoff", "n_outliers_gt_1tev",
]
LOW_MASS_THRESHOLDS_GEV = (2.0, 4.0)


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_job_index_map(mapping_file: Path) -> dict:
    """{index: (record_id, file_index)} from generate_job_index_map.py's
    output -- the submission-time assignment, used to know which indices
    were EXPECTED (never assumed 1..57 -- whatever was actually
    submitted)."""
    mapping = {}
    for line in mapping_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        idx, record_id, file_index = line.split()
        mapping[int(idx)] = (int(record_id), int(file_index))
    return mapping


def _normalize_url(url: str) -> str:
    m = re.search(r"(/eos/opendata/.*)$", url)
    return m.group(1) if m else url


def check_identity_and_counts(jobs_base: Path, job_index_map: dict) -> dict:
    """Returns a dict with per-job identity/count results and an overall
    `problems` list (empty iff every check above passed)."""
    problems = []
    per_job = {}

    current_urls_by_record = {r: fetch_file_list(r) for r in RECORDS}

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

        recorded_n_read = meta["cutflow"]["n_read"]
        try:
            live_n_entries = uproot.open(recorded_url)["Events"].num_entries
        except Exception as e:  # noqa: BLE001 -- report, don't crash the merge
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
            "status": "OK",
            "record_id": record_id,
            "file_index": file_index,
            "recorded_url": recorded_url,
            "current_portal_url_at_this_index": current_url_at_index,
            "matches_current_portal": matches_portal,
            "recorded_n_read": recorded_n_read,
            "live_reopen_n_entries": live_n_entries,
            "count_matches_live_reopen": count_matches,
        }

    duplicated = {u: idxs for u, idxs in assigned_by_url.items() if len(idxs) > 1}
    if duplicated:
        problems.append(f"duplicate file URL(s) assigned to more than one job index: {duplicated}")

    present_n_read_sum = sum(
        v["recorded_n_read"] for v in per_job.values() if v.get("status") == "OK"
    )
    portal_totals = {r: fetch_record_number_events(r) for r in RECORDS}
    portal_total_events = sum(v["number_events"] for v in portal_totals.values())
    total_matches = present_n_read_sum == portal_total_events
    if not total_matches:
        problems.append(
            f"sum of n_read across present jobs ({present_n_read_sum}) != current portal total "
            f"({portal_total_events})"
        )

    # NOTE: `per_job` has an entry for EVERY expected index, including
    # missing/broken ones (status MISSING_METADATA / XROOTD_REOPEN_FAILED)
    # -- so "missing" here means specifically "no job_metadata.json at
    # all", not "not fully OK" (a count-mismatch or reopen-failure index
    # already surfaces its own problem string; conflating it into
    # missing_indices would double-report and also incorrectly imply no
    # job ran at all for that index).
    missing_indices = sorted(
        idx for idx, v in per_job.items() if v.get("status") == "MISSING_METADATA"
    )
    return {
        "per_job": per_job,
        "duplicated_urls": duplicated,
        "present_n_read_sum": present_n_read_sum,
        "current_portal_total_events": portal_total_events,
        "portal_totals_by_record": portal_totals,
        "missing_indices": missing_indices,
        "problems": problems,
    }


def _bumpnet_name_from_root_name(root_name: str) -> str:
    name = root_name[len("ROI_"):] if root_name.startswith("ROI_") else root_name
    return re.sub(r"_width_\d+$", "", name)


def merge_histograms(jobs_base: Path, present_indices: list) -> dict:
    merged: dict = {}
    for idx in present_indices:
        root_path = jobs_base / f"job_{idx}" / "all_histograms.root"
        if not root_path.exists():
            continue
        f = uproot.open(str(root_path))
        for key in f.keys(cycle=False):
            hist = f[key]
            values = hist.values()
            edges = hist.axis().edges()
            if key not in merged:
                merged[key] = (values.copy(), edges)
            else:
                prev_values, prev_edges = merged[key]
                if not np.array_equal(prev_edges, edges):
                    raise ValueError(f"job_{idx}'s histogram {key!r} has different bin edges than an earlier job")
                merged[key] = (prev_values + values, prev_edges)
    return merged


def sum_per_category_counts(jobs_base: Path, present_indices: list) -> dict:
    totals: dict = {}
    for idx in present_indices:
        meta = _load_json(jobs_base / f"job_{idx}" / "job_metadata.json")
        if meta is None:
            continue
        for name, cat_meta in meta.get("per_category", {}).items():
            if name.startswith("_"):
                continue
            totals[name] = totals.get(name, 0) + cat_meta.get("n_events_in_histogram", 0)
    return totals


def apply_merge_time_min_events_prune(merged_hists: dict, per_category_counts: dict) -> tuple:
    kept, dropped = {}, []
    for root_name, hist in merged_hists.items():
        grouping_name = _bumpnet_name_from_root_name(root_name)
        if grouping_name == INCLUSIVE_HIST_NAME:
            kept[root_name] = hist
            continue
        n_entries = int(per_category_counts.get(grouping_name, 0))
        if n_entries < MIN_EVENTS_PER_FINAL_STATE:
            dropped.append({"name": grouping_name, "n_entries": n_entries})
            continue
        kept[root_name] = hist
    return kept, dropped


def sum_cutflow(jobs_base: Path, present_indices: list) -> dict:
    total = {k: 0 for k in CUTFLOW_KEYS}
    for idx in present_indices:
        meta = _load_json(jobs_base / f"job_{idx}" / "job_metadata.json")
        if meta is None:
            continue
        cf = meta.get("cutflow", {})
        for k in CUTFLOW_KEYS:
            total[k] += cf.get(k, 0)
    return total


def merge_outliers(jobs_base: Path, present_indices: list) -> list:
    merged = []
    for idx in present_indices:
        data = _load_json(jobs_base / f"job_{idx}" / "outliers_gt_1tev.json")
        if data:
            merged.extend(data)
    return merged


def merge_sanity_arrays(jobs_base: Path, present_indices: list) -> dict:
    dimuon, jet_pt = [], []
    for idx in present_indices:
        data = _load_json(jobs_base / f"job_{idx}" / "sanity_arrays.json")
        if data:
            dimuon.extend(data.get("dimuon_mass_gev", []))
            jet_pt.extend(data.get("leading_jet_pt_gev", []))
    return {"dimuon_mass_gev": dimuon, "leading_jet_pt_gev": jet_pt}


def load_all_diagnostics(jobs_base: Path, present_indices: list) -> dict:
    """Concatenates every present job's dimuon_diagnostics.npz into one
    set of arrays. Field set is whatever the per-job npz's actually
    contain -- studies.m0m1j0_cms.selection.OPTIONAL_MUON_DIAGNOSTIC_BRANCHES
    plus the core fields, same across every job by construction."""
    chunks: dict = {}
    for idx in present_indices:
        npz_path = jobs_base / f"job_{idx}" / "dimuon_diagnostics.npz"
        if not npz_path.exists():
            continue
        with np.load(npz_path) as npz:
            for key in npz.files:
                chunks.setdefault(key, []).append(npz[key])
    return {key: np.concatenate(arrs) for key, arrs in chunks.items()}


def build_diagnostic_report(diagnostics: dict, out_dir: Path) -> dict:
    """Step 2 (C): low-mass dimuon diagnostic report. Returns a dict of
    plain numbers (fractions, breakdowns) for FULL_REPORT.md to quote,
    and writes the 4 required PNGs."""
    m_mumu = diagnostics["m_mumu_gev"]
    m0m1j0 = diagnostics["m0m1j0_gev"]
    dr = diagnostics["deltaR_mu0_mu1"]
    charge_product = diagnostics["charge_product"]
    pt_ratio = diagnostics["pt_ratio_mu1_mu0"]
    n_total = len(m_mumu)

    report = {"n_total_events_in_inclusive_histogram": int(n_total)}
    low_mass_masks = {}
    for threshold in LOW_MASS_THRESHOLDS_GEV:
        mask = m_mumu < threshold
        low_mass_masks[threshold] = mask
        n_low = int(mask.sum())
        report[f"n_events_m_mumu_lt_{threshold:g}gev"] = n_low
        report[f"fraction_m_mumu_lt_{threshold:g}gev"] = (n_low / n_total) if n_total else 0.0
        if n_low > 0:
            cp = charge_product[mask]
            report[f"m_mumu_lt_{threshold:g}gev_same_sign_fraction"] = float(np.mean(cp == 1))
            report[f"m_mumu_lt_{threshold:g}gev_opposite_sign_fraction"] = float(np.mean(cp == -1))
            report[f"m_mumu_lt_{threshold:g}gev_deltaR_median"] = float(np.nanmedian(dr[mask]))
            report[f"m_mumu_lt_{threshold:g}gev_deltaR_fraction_below_0.02"] = float(np.mean(dr[mask] < 0.02))
            report[f"m_mumu_lt_{threshold:g}gev_pt_ratio_median"] = float(np.nanmedian(pt_ratio[mask]))
            report[f"m_mumu_lt_{threshold:g}gev_pt_ratio_fraction_0.95_to_1.05"] = float(
                np.mean((pt_ratio[mask] > 0.95) & (pt_ratio[mask] < 1.05))
            )
            # Global/tracker-split pattern: classic signature of one real
            # muon reconstructed twice (once as a global-muon track, once
            # as a tracker-only track sharing the same hits) -- extra
            # evidence beyond what the task strictly required, computed
            # only if the branches were available (they were, per the
            # pilot's own environment check of a real 2016 NanoAOD file).
            if "isGlobal_mu0" in diagnostics and "isGlobal_mu1" in diagnostics:
                g0, g1 = diagnostics["isGlobal_mu0"][mask], diagnostics["isGlobal_mu1"][mask]
                valid = ~np.isnan(g0) & ~np.isnan(g1)
                if valid.any():
                    report[f"m_mumu_lt_{threshold:g}gev_global_tracker_split_fraction"] = float(
                        np.mean(g0[valid] != g1[valid])
                    )

    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # (1) charge-product breakdown
    fig, ax = plt.subplots(figsize=(7, 5))
    labels, same_frac, opp_frac = [], [], []
    for threshold in LOW_MASS_THRESHOLDS_GEV:
        mask = low_mass_masks[threshold]
        if mask.sum() == 0:
            continue
        labels.append(f"m(μμ) < {threshold:g} GeV\n(n={int(mask.sum())})")
        cp = charge_product[mask]
        same_frac.append(float(np.mean(cp == 1)))
        opp_frac.append(float(np.mean(cp == -1)))
    x = np.arange(len(labels))
    ax.bar(x - 0.2, same_frac, width=0.4, label="same-sign", color="#c44e52")
    ax.bar(x + 0.2, opp_frac, width=0.4, label="opposite-sign", color="#4c72b0")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Fraction of events")
    ax.set_title("Low-mass dimuon: charge-product breakdown")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "diagnostic_charge_product.png", dpi=150)
    plt.close(fig)

    # (2) deltaR distribution
    fig, ax = plt.subplots(figsize=(7, 5))
    for threshold, color in zip(LOW_MASS_THRESHOLDS_GEV, ("#c44e52", "#55a868")):
        mask = low_mass_masks[threshold]
        if mask.sum() == 0:
            continue
        ax.hist(dr[mask], bins=60, range=(0, 1.0), histtype="step", linewidth=1.5,
                label=f"m(μμ) < {threshold:g} GeV (n={int(mask.sum())})", color=color)
    ax.set_xlabel("ΔR(μ0, μ1)")
    ax.set_ylabel("Events")
    ax.set_title("Low-mass dimuon: ΔR distribution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "diagnostic_deltaR.png", dpi=150)
    plt.close(fig)

    # (3) pT-ratio distribution
    fig, ax = plt.subplots(figsize=(7, 5))
    for threshold, color in zip(LOW_MASS_THRESHOLDS_GEV, ("#c44e52", "#55a868")):
        mask = low_mass_masks[threshold]
        if mask.sum() == 0:
            continue
        ax.hist(pt_ratio[mask], bins=60, range=(0, 1.2), histtype="step", linewidth=1.5,
                label=f"m(μμ) < {threshold:g} GeV (n={int(mask.sum())})", color=color)
    ax.set_xlabel("pT(μ1) / pT(μ0)  (subleading / leading)")
    ax.set_ylabel("Events")
    ax.set_title("Low-mass dimuon: pT-ratio distribution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "diagnostic_pt_ratio.png", dpi=150)
    plt.close(fig)

    # (4) m0m1j0 distribution overlaid (normalized) on all events
    fig, ax = plt.subplots(figsize=(8, 5))
    bins = np.linspace(Z_PEAK_CUTOFF_GEV, 2000.0, 100)
    ax.hist(m0m1j0, bins=bins, density=True, histtype="step", linewidth=1.5, color="black", label=f"all events (n={n_total})")
    for threshold, color in zip(LOW_MASS_THRESHOLDS_GEV, ("#c44e52", "#55a868")):
        mask = low_mass_masks[threshold]
        if mask.sum() == 0:
            continue
        ax.hist(m0m1j0[mask], bins=bins, density=True, histtype="step", linewidth=1.5, color=color,
                label=f"m(μμ) < {threshold:g} GeV (n={int(mask.sum())})")
    ax.set_yscale("log")
    ax.set_xlabel("m0m1j0 [GeV]")
    ax.set_ylabel("Normalized events / bin")
    ax.set_title("m0m1j0 shape: low-mass dimuon subsets vs all events")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(plots_dir / "diagnostic_m0m1j0_overlay.png", dpi=150)
    plt.close(fig)

    return report


def write_diagnostic_variants_root(diagnostics: dict, out_path: Path) -> dict:
    """Diagnostic-only, separate file: the inclusive m0m1j0 histogram
    recomputed excluding m(mumu) < 4 GeV, built directly from the
    per-job diagnostic npz's own (m0m1j0_gev, m_mumu_gev) pairs (that
    population IS exactly the inclusive histogram's population). Never
    written into the main merged file."""
    m_mumu = diagnostics["m_mumu_gev"]
    m0m1j0 = diagnostics["m0m1j0_gev"]
    keep = m_mumu >= 4.0
    values, edges = make_fixed_grid_histogram(m0m1j0[keep].astype(np.float64))
    name = f"{INCLUSIVE_HIST_NAME}_DIAGNOSTIC_excl_mmumu_lt4gev"
    th1f = to_writable_th1f(values, edges, name)
    with uproot.recreate(str(out_path)) as f:
        f[name] = th1f
    verify_written_th1f(str(out_path), {name: values})
    return {"n_events_excluding_mmumu_lt4gev": int(keep.sum()), "n_events_total": int(len(m_mumu))}


def plot_inclusive_log(hist: tuple, out_path: Path, n_read_total: int):
    contents, edges = hist
    nonzero = np.nonzero(contents)[0]
    last_bin = int(nonzero.max()) + 1 if len(nonzero) else 10
    centers = (edges[:-1] + edges[1:]) / 2
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.step(centers[:last_bin], contents[:last_bin], where="mid", color="#c44e52",
            label=f"CMS Open Data 2016G+H, DoubleMuon (n={int(contents.sum())})")
    ax.set_yscale("log")
    ax.set_xlabel("m(μμ j) [GeV]")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_title("m0m1j0 -- CMS Open Data 2016G+H, DoubleMuon")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_inclusive_linear_zoom(hist: tuple, out_path: Path):
    contents, edges = hist
    centers = (edges[:-1] + edges[1:]) / 2
    mask = (centers >= 100.0) & (centers <= 1000.0)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.step(centers[mask], contents[mask], where="mid", color="#c44e52")
    ax.set_xlabel("m(μμ j) [GeV]")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_title("m0m1j0 -- CMS Open Data 2016G+H, DoubleMuon (100-1000 GeV, linear)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_top_categories(kept_hists: dict, per_category_counts: dict, out_path: Path, top_n: int = 5):
    scored = []
    for root_name, hist in kept_hists.items():
        grouping_name = _bumpnet_name_from_root_name(root_name)
        if grouping_name == INCLUSIVE_HIST_NAME:
            continue
        n_entries = int(per_category_counts.get(grouping_name, 0))
        scored.append((n_entries, grouping_name, hist))
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:top_n]

    fig, ax = plt.subplots(figsize=(8, 5))
    for n_entries, grouping_name, hist in top:
        contents, edges = hist
        nonzero = np.nonzero(contents)[0]
        last_bin = int(nonzero.max()) + 1 if len(nonzero) else 10
        centers = (edges[:-1] + edges[1:]) / 2
        ax.step(centers[:last_bin], contents[:last_bin], where="mid", label=f"{grouping_name} (n={n_entries})")
    ax.set_yscale("log")
    ax.set_xlabel("m0m1j0 [GeV]")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_title(f"m0m1j0 full run: top {top_n} categories by event count")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return [{"category": name, "n_entries": n} for n, name, _ in top]


def plot_dimuon_mass(dimuon_mass_gev: list, out_path_full: Path, out_path_zoom: Path):
    arr = np.array([x for x in dimuon_mass_gev if x == x])
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(arr, bins=100, range=(0, 200), histtype="stepfilled", color="#4c72b0", alpha=0.8)
    ax.axvline(91.19, color="red", linestyle="--", label="Z pole (91.19 GeV)")
    ax.set_xlabel("Dimuon mass [GeV] (leading + subleading selected muon)")
    ax.set_ylabel("Events / 2 GeV")
    ax.set_title("m0m1j0 full run: dimuon mass of the selected pair")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path_full, dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(arr, bins=100, range=(0, 10), histtype="stepfilled", color="#4c72b0", alpha=0.8)
    ax.set_xlabel("Dimuon mass [GeV] (zoom)")
    ax.set_ylabel("Events / 0.1 GeV")
    ax.set_title("m0m1j0 full run: dimuon mass, 0-10 GeV zoom")
    fig.tight_layout()
    fig.savefig(out_path_zoom, dpi=150)
    plt.close(fig)


def plot_leading_jet_pt(jet_pt_gev: list, out_path: Path):
    arr = np.array([x for x in jet_pt_gev if x == x])
    fig, ax = plt.subplots(figsize=(7, 5))
    hi = max(200.0, float(np.percentile(arr, 99)) if len(arr) else 200.0)
    ax.hist(arr, bins=60, range=(0, hi), histtype="stepfilled", color="#55a868", alpha=0.8)
    ax.axvline(30.0, color="red", linestyle="--", label="30 GeV jet pT cut")
    ax.set_xlabel("Leading (light) jet pT [GeV]")
    ax.set_ylabel(f"Events / {hi/60:.1f} GeV")
    ax.set_title("m0m1j0 full run: leading light-jet pT")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-base", required=True)
    p.add_argument("--mapping-file", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    jobs_base = Path(args.jobs_base)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    job_index_map = load_job_index_map(Path(args.mapping_file))
    identity = check_identity_and_counts(jobs_base, job_index_map)
    present_indices = sorted(i for i, v in identity["per_job"].items() if v.get("status") == "OK")

    merged_hists = merge_histograms(jobs_base, present_indices)
    per_category_counts = sum_per_category_counts(jobs_base, present_indices)
    kept_hists, dropped_categories = apply_merge_time_min_events_prune(merged_hists, per_category_counts)
    cutflow = sum_cutflow(jobs_base, present_indices)
    outliers = merge_outliers(jobs_base, present_indices)
    sanity = merge_sanity_arrays(jobs_base, present_indices)
    diagnostics = load_all_diagnostics(jobs_base, present_indices)

    # Main merged output: genuine TH1F (Step 2 requirement A), verified.
    merged_root_path = out_dir / "m0m1j0_full_merged.root"
    verify_expected = {}
    with uproot.recreate(str(merged_root_path)) as f:
        for root_name, (values, edges) in kept_hists.items():
            title = _bumpnet_name_from_root_name(root_name)
            f[root_name] = to_writable_th1f(values, edges, title)
            verify_expected[root_name] = values
    verify_written_th1f(str(merged_root_path), verify_expected)

    diagnostic_variants_path = out_dir / "m0m1j0_diagnostic_variants.root"
    diag_variant_meta = write_diagnostic_variants_root(diagnostics, diagnostic_variants_path)

    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    inclusive_root_name = next(
        (n for n in kept_hists if _bumpnet_name_from_root_name(n) == INCLUSIVE_HIST_NAME), None
    )
    top_categories = []
    if inclusive_root_name is not None:
        plot_inclusive_log(kept_hists[inclusive_root_name], plots_dir / "inclusive_m0m1j0_logy.png", cutflow["n_read"])
        plot_inclusive_linear_zoom(kept_hists[inclusive_root_name], plots_dir / "inclusive_m0m1j0_linear_100_1000.png")
        top_categories = plot_top_categories(kept_hists, per_category_counts, plots_dir / "top5_categories.png")

    plot_dimuon_mass(sanity["dimuon_mass_gev"], plots_dir / "dimuon_mass.png", plots_dir / "dimuon_mass_zoom_0_10.png")
    plot_leading_jet_pt(sanity["leading_jet_pt_gev"], plots_dir / "leading_jet_pt.png")

    diagnostic_report = build_diagnostic_report(diagnostics, out_dir)

    summary = {
        "jobs_base": str(jobs_base),
        "n_jobs_expected": len(job_index_map),
        "n_jobs_present": len(present_indices),
        "missing_indices": identity["missing_indices"],
        "identity_and_counts": identity,
        "cutflow_summed_over_present_jobs": cutflow,
        "n_histograms_before_merge_prune": len(merged_hists),
        "n_histograms_after_merge_prune": len(kept_hists),
        "dropped_categories_below_min_events_per_fs": dropped_categories,
        "top_categories_by_event_count": top_categories,
        "n_outlier_events_gt_1tev": len(outliers),
        "low_mass_dimuon_diagnostic": diagnostic_report,
        "diagnostic_variants_root": diag_variant_meta,
        "complete": not identity["problems"],
    }
    (out_dir / "merge_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "outliers_gt_1tev_merged.json").write_text(json.dumps(outliers, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in summary.items() if k != "identity_and_counts"}, indent=2))
    if summary["complete"]:
        print("\nMerge status: COMPLETE.")
    else:
        print("\nMerge status: INCOMPLETE -- see identity_and_counts.problems in merge_summary.json")
        for problem in identity["problems"]:
            print(f"  - {problem}")
        sys.exit(1)


if __name__ == "__main__":
    main()
