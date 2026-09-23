#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- selection-variants task (supervisor request), DATA
per-job driver.

One job = one input CMS DoubleMuon NanoAOD file (records 30522, 30555 --
same files as the existing V0 full run), read ONCE over XRootD, golden-JSON
filtered ONCE, then all FOUR selection variants (studies.m0m1j0_cms.variants)
are run against that SAME already-read/-filtered `events` array -- never
four separate file reads. The V0 baseline itself is untouched
(studies.m0m1j0_cms.selection's own defaults; see variants.py's own
self-check for the guarantee that V0's spec IS those defaults, not merely
equal to them).

Writes, under --output-dir (one per input file, same job-per-file
convention as run_m0m1j0_on_file.py):
    job_metadata.json           -- file URL/event count, git commit,
                                    validated-runs sha256, per-VARIANT
                                    cutflow + diagnostics, thresholds.
    mass_by_category_<variant>.npz
                                 -- one per variant: category, RAW (pre-
                                    z_peak/max_mass/peak-removal/outlier-
                                    split) m0m1j0 mass -- same role as V0's
                                    own mass_by_category.npz, one per
                                    variant. Merge-time post-processing
                                    (studies.m0m1j0_cms.postprocessing,
                                    the real pipeline functions) is applied
                                    per variant per category, exactly as
                                    the existing v2 correction does for V0.

No per-job ROOT file is written here (unlike V0's original per-job driver):
post-processing can only be run correctly on the GLOBALLY merged
population (RECIPE.md), so a per-job, pre-post-processing histogram would
not be a usable final artifact for this task and would only add Lustre
file count / job time for no benefit -- the real, post-processed TH1F
outputs are written once, by the merge script
(cluster/merge_variants.py), from these per-job npz files.

Diagnostics (task's own "Diagnostics per variant (data)" requirement),
computed per variant, over that variant's own selected-object population
(n_after_ge1jet_after_cleaning -- i.e. BEFORE the z_peak_cutoff, which acts
on the 3-body m0m1j0 mass, not the dimuon mass, so a collimated low-mass
pair can still enter the inclusive histogram if the jet alone pushes
m0m1j0 above 115 GeV -- restricting to post-z_peak-cutoff events would
therefore hide exactly the effect this diagnostic exists to show):
  - n_dimuon_lt_2gev, n_dimuon_lt_4gev, n_diagnostic_population (all
    variants): fraction with dimuon mass < 2 / < 4 GeV.
  - V2 only: n_leading_jet_dr_lt_p4_to_muon, n_leading_jet_pt_within_10pct_
    of_muon, n_diagnostic_population_v2 (same population, V2's own): the
    leading (uncleaned) light jet's overlap with the nearest selected muon.

Usage:
    python run_m0m1j0_variants_on_file.py \
        --record-id 30522 --file-index 0 \
        --output-dir /storage/.../job_1
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
from studies.m0m1j0_cms import histograms, selection, variants  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

DEFAULT_VALIDATED_RUNS_JSON = (
    "data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
)
DIMUON_LOW_MASS_THRESHOLDS_GEV = (2.0, 4.0)
V2_JET_MUON_DR_THRESHOLD = 0.4
V2_JET_MUON_PT_FRAC_THRESHOLD = 0.10

# Required plot 5 ("data: dimuon mass 0-200 GeV and a 0-10 GeV zoom, V0 vs
# V1 overlaid"): a per-job, per-variant dimuon-mass histogram, small enough
# to embed directly as bin-count lists in job_metadata.json (100+50 ints
# per variant) rather than a separate npz -- summed across jobs at merge
# time, same population as the low-mass fraction diagnostic above.
DIMUON_HIST_FULL_RANGE_GEV = (0.0, 200.0)
DIMUON_HIST_FULL_NBINS = 100  # 2 GeV/bin
DIMUON_HIST_ZOOM_RANGE_GEV = (0.0, 10.0)
DIMUON_HIST_ZOOM_NBINS = 50  # 0.2 GeV/bin


def git_commit_hash(repo_root) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception as e:  # noqa: BLE001
        return f"UNKNOWN ({type(e).__name__}: {e})"


def resolve_file_url(record_id: int, file_index: int) -> str:
    urls = fetch_file_list(record_id)
    if file_index < 0 or file_index >= len(urls):
        raise ValueError(
            f"record {record_id}'s portal file list currently has {len(urls)} "
            f"file(s); requested file-index {file_index} is out of range."
        )
    return urls[file_index]


def read_events(file_url: str):
    """Same required-branch discipline as run_m0m1j0_on_file.py, PLUS the
    V3 single-muon trigger branches (variants.ALL_TRIGGER_BRANCHES already
    includes the V0 DZ paths, so this is a strict superset of the V0
    driver's own required list -- fails loudly if EITHER trigger family is
    missing, per the task's own 'fail loudly if missing' instruction for
    V3)."""
    import uproot

    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    required = set(selection.NEEDED_BRANCHES) | set(variants.ALL_TRIGGER_BRANCHES)
    missing = sorted(required - available)
    if missing:
        raise ValueError(
            f"{file_url}: missing required branch(es): {missing}. Refusing to "
            f"proceed rather than silently treating a missing trigger branch "
            f"as 'not fired'."
        )
    present_optional = [b for b in selection.OPTIONAL_MUON_DIAGNOSTIC_BRANCHES if b in available]
    branches_to_read = sorted(required | set(present_optional))
    events = tree.arrays(branches_to_read, library="ak")
    return events, present_optional


def build_mass_by_category_npz(output_path: Path, result: dict) -> int:
    _, categories = histograms.per_event_raw_and_capped_final_state(result["obj_record"])
    raw_mass = ak.to_numpy(result["raw_mass"]).astype(np.float64)
    np.savez_compressed(output_path, category=categories, m0m1j0_raw_gev=raw_mass)
    return len(raw_mass)


def low_mass_dimuon_diagnostic(result: dict) -> dict:
    """Fraction of the diagnostic population (>=2mu, >=1 jet after this
    variant's own cleaning) with dimuon mass < 2 / < 4 GeV."""
    obj_record = result["obj_record"]
    n_pop = len(obj_record)
    if n_pop == 0:
        _, full_edges = np.histogram([], bins=DIMUON_HIST_FULL_NBINS, range=DIMUON_HIST_FULL_RANGE_GEV)
        _, zoom_edges = np.histogram([], bins=DIMUON_HIST_ZOOM_NBINS, range=DIMUON_HIST_ZOOM_RANGE_GEV)
        return {
            "n_diagnostic_population": 0,
            "n_dimuon_lt_2gev": 0, "n_dimuon_lt_4gev": 0,
            "frac_dimuon_lt_2gev": None, "frac_dimuon_lt_4gev": None,
            "dimuon_mass_hist_full_counts": [0] * DIMUON_HIST_FULL_NBINS,
            "dimuon_mass_hist_full_edges": full_edges.tolist(),
            "dimuon_mass_hist_zoom_counts": [0] * DIMUON_HIST_ZOOM_NBINS,
            "dimuon_mass_hist_zoom_edges": zoom_edges.tolist(),
        }
    dimuon_mass = ak.to_numpy(selection.compute_dimuon_mass(obj_record["Muons"]))
    n_lt = {}
    for thr in DIMUON_LOW_MASS_THRESHOLDS_GEV:
        n_lt[thr] = int(np.sum(dimuon_mass < thr))

    full_counts, full_edges = np.histogram(dimuon_mass, bins=DIMUON_HIST_FULL_NBINS, range=DIMUON_HIST_FULL_RANGE_GEV)
    zoom_counts, zoom_edges = np.histogram(dimuon_mass, bins=DIMUON_HIST_ZOOM_NBINS, range=DIMUON_HIST_ZOOM_RANGE_GEV)

    return {
        "n_diagnostic_population": n_pop,
        "n_dimuon_lt_2gev": n_lt[2.0], "n_dimuon_lt_4gev": n_lt[4.0],
        "frac_dimuon_lt_2gev": n_lt[2.0] / n_pop, "frac_dimuon_lt_4gev": n_lt[4.0] / n_pop,
        "dimuon_mass_hist_full_counts": full_counts.tolist(),
        "dimuon_mass_hist_full_edges": full_edges.tolist(),
        "dimuon_mass_hist_zoom_counts": zoom_counts.tolist(),
        "dimuon_mass_hist_zoom_edges": zoom_edges.tolist(),
    }


def v2_jet_muon_overlap_diagnostic(result: dict) -> dict:
    """V2-only: fraction of V2's own diagnostic population whose leading
    (UNCLEANED) light jet is within dR<0.4 of a selected muon, and
    separately the fraction where the leading jet's pT is within 10% of
    some selected muon's pT."""
    obj_record = result["obj_record"]
    n_pop = len(obj_record)
    if n_pop == 0:
        return {
            "n_diagnostic_population_v2": 0,
            "n_leading_jet_dr_lt_p4_to_muon": 0,
            "n_leading_jet_pt_within_10pct_of_muon": 0,
            "frac_leading_jet_dr_lt_p4_to_muon": None,
            "frac_leading_jet_pt_within_10pct_of_muon": None,
        }
    diag = selection.leading_jet_muon_overlap_diagnostics(obj_record["Jets"], obj_record["Muons"])
    min_dr = ak.to_numpy(diag["min_dr_to_muon"])
    min_pt_frac = ak.to_numpy(diag["min_pt_frac_diff_to_muon"])
    n_dr = int(np.nansum(min_dr < V2_JET_MUON_DR_THRESHOLD))
    n_pt = int(np.nansum(min_pt_frac <= V2_JET_MUON_PT_FRAC_THRESHOLD))
    return {
        "n_diagnostic_population_v2": n_pop,
        "n_leading_jet_dr_lt_p4_to_muon": n_dr,
        "n_leading_jet_pt_within_10pct_of_muon": n_pt,
        "frac_leading_jet_dr_lt_p4_to_muon": n_dr / n_pop,
        "frac_leading_jet_pt_within_10pct_of_muon": n_pt / n_pop,
    }


def selection_thresholds() -> dict:
    return {
        "muon_pt_min_gev": selection.MUON_PT_MIN_GEV,
        "muon_eta_max": selection.MUON_ETA_MAX,
        "muon_iso_max": selection.MUON_ISO_MAX,
        "electron_pt_min_gev": selection.ELECTRON_PT_MIN_GEV,
        "electron_eta_max": selection.ELECTRON_ETA_MAX,
        "electron_cutbased_min": selection.ELECTRON_CUTBASED_MIN,
        "jet_pt_min_gev": selection.JET_PT_MIN_GEV,
        "jet_eta_max": selection.JET_ETA_MAX,
        "jet_lepton_clean_dr": selection.JET_LEPTON_CLEAN_DR,
        "btag_deepflavb_medium_wp": selection.BTAG_DEEPFLAVB_MEDIUM_WP,
        "v0_trigger_branches": list(selection.TRIGGER_BRANCHES),
        "v3_trigger_branches": list(selection.SINGLE_MUON_TRIGGER_BRANCHES),
        "z_peak_cutoff_gev": selection.Z_PEAK_CUTOFF_GEV,
        "max_mass_cutoff_gev": selection.MAX_MASS_CUTOFF_GEV,
        "min_events_per_final_state": selection.MIN_EVENTS_PER_FINAL_STATE,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record-id", type=int, required=True)
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--validated-runs-json", default=DEFAULT_VALIDATED_RUNS_JSON)
    args = p.parse_args()

    t0 = time.time()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_url = resolve_file_url(args.record_id, args.file_index)
    print(f"resolved record {args.record_id} file index {args.file_index} -> {file_url}", flush=True)

    events, present_optional_branches = read_events(file_url)
    n_read = len(events)
    print(f"read {n_read} events from {file_url}; optional muon diagnostic branches present: "
          f"{present_optional_branches}", flush=True)

    validated_runs = ValidatedRunsFilter(args.validated_runs_json)
    events_golden, golden_stats = apply_validated_runs_filter(events, validated_runs)
    print(f"golden-JSON filter: {golden_stats['n_before']} -> {golden_stats['n_after']}", flush=True)

    muon_extra_branches = ["Muon_charge"] + present_optional_branches

    per_variant_cutflow = {}
    per_variant_diagnostics = {}
    per_variant_n_mass_rows = {}

    for variant_key in variants.VARIANT_ORDER:
        result = variants.run_variant(variant_key, events_golden, muon_extra_branches=muon_extra_branches)

        npz_path = output_dir / f"mass_by_category_{variant_key}.npz"
        n_mass_rows = build_mass_by_category_npz(npz_path, result)
        per_variant_n_mass_rows[variant_key] = n_mass_rows

        per_variant_cutflow[variant_key] = {
            "n_read": n_read,
            "n_after_golden_json": golden_stats["n_after"],
            "n_after_trigger": result["n_after_trigger"],
            "n_after_ge2mu": result["n_after_ge2mu"],
            "n_after_ge1jet_after_cleaning": result["n_after_ge1jet_after_cleaning"],
            "n_after_z_peak_and_mass_cutoff": result["n_after_z_peak_and_mass_cutoff"],
        }

        diag = low_mass_dimuon_diagnostic(result)
        if variant_key == "V2_no_jet_lepton_cleaning":
            diag.update(v2_jet_muon_overlap_diagnostic(result))
        per_variant_diagnostics[variant_key] = diag

        print(f"variant {variant_key}: n_after_ge1jet_after_cleaning="
              f"{result['n_after_ge1jet_after_cleaning']}, wrote {npz_path.name} ({n_mass_rows} rows)", flush=True)

    elapsed = time.time() - t0

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "validated_runs_json": args.validated_runs_json,
        "validated_runs_sha256": validated_runs.sha256,
        "golden_json_per_run": golden_stats["per_run"],
        "n_read": n_read,
        "n_after_golden_json": golden_stats["n_after"],
        "variant_order": list(variants.VARIANT_ORDER),
        "per_variant_cutflow": per_variant_cutflow,
        "per_variant_diagnostics": per_variant_diagnostics,
        "per_variant_n_mass_by_category_rows": per_variant_n_mass_rows,
        "thresholds": selection_thresholds(),
        "optional_muon_diagnostic_branches_present": present_optional_branches,
        "elapsed_sec": elapsed,
    }
    (output_dir / "job_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps(per_variant_cutflow, indent=2))
    print(f"wrote job_metadata.json and {len(variants.VARIANT_ORDER)} mass_by_category_<variant>.npz "
          f"files under {output_dir} ({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
