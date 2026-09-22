#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- per-job driver (Step 1 pilot, Step 2 full run).

One job = one input CMS NanoAOD file, read directly over XRootD (works on
the Weizmann cluster; NOT on this repo's own Windows dev machine, which
has no XRootD python bindings -- see
studies/m0m1j0_cms/design_checks/common.py's own docstring). The exact
file this job reads is resolved from the CERN Open Data portal's own file
list for the given record (studies.m0m1j0_cms.design_checks.common
.fetch_file_list -- the same portal API the shared pipeline's own fetcher
uses), by a 0-based index into that list -- NOT sorted/re-ordered here, so
which file a given index means depends on the portal's own current
ordering (recorded explicitly in this job's own metadata JSON, per the
task's "record for every job the exact file URL read" requirement, so a
merge step can verify it rather than assume it).

Applies, in order: golden-JSON (validated-runs) filter, trigger OR,
CMS object selection (studies.m0m1j0_cms.selection -- UNCHANGED from the
pilot; Step 2 does not add, remove, or change any cut), m0m1j0 mass +
z_peak_cutoff/max_mass_cutoff, then builds histograms
(studies.m0m1j0_cms.histograms) and a small outlier event list. See
studies/m0m1j0_cms/RECIPE.md for the full recipe and every deviation from
the group's ATLAS config.yaml, and studies/m0m1j0_cms/pilot/PILOT_REPORT.md
for the pilot this was validated against.

Step 2 additions (output-format/diagnostic only, no selection change):
  (A) Histograms are written as genuine TH1F (float32 bin contents),
      matching the shared pipeline's own histogram class -- previously
      TH1D (uproot's plain tuple-write shortcut always produces TH1D
      regardless of dtype; see histograms.py's to_writable_th1f). Every
      write is immediately re-opened and verified (class == TH1F, bin
      contents match) via histograms.verify_written_th1f -- an
      AssertionError here fails the job loudly rather than shipping a
      silently-wrong file.
  (B) A low-mass dimuon diagnostic: for every event entering the
      inclusive histogram (i.e. surviving z_peak_cutoff/max_mass_cutoff),
      saves a small .npz with (run, luminosityBlock, event, dimuon mass,
      deltaR(mu0,mu1), charge product, pT ratio, m0m1j0, and whichever of
      Muon_isGlobal/isTracker/isPFcand/nStations/nTrackerLayers this file
      has -- NaN for any that are absent). This is purely diagnostic
      (studies.m0m1j0_cms.selection.compute_dimuon_diagnostics) -- it
      does not read into, or affect, the m0m1j0 selection or histograms
      in any way.

Usage:
    python run_m0m1j0_on_file.py \
        --record-id 30522 --file-index 0 \
        --output-dir /storage/.../job_1

Writes, under --output-dir:
    all_histograms.root   -- one TH1F per BumpNet category + one inclusive
                              (studies.m0m1j0_cms.histograms), ROI_-prefixed
                              ROOT-internal names, same fixed grid as the
                              shared pipeline. Written via uproot (this
                              cluster account's own atlas-pipeline conda
                              env has no PyROOT installed at all -- see
                              histograms.py's module docstring), using
                              uproot.writing.identify.to_TH1x directly so
                              the on-disk class is a genuine TH1F, not
                              TH1D.
    job_metadata.json     -- exact file URL + event count read, full
                              cutflow, per-category counts, thresholds
                              used, git commit, validated-runs file sha256,
                              which optional muon diagnostic branches this
                              file has, and the TH1F-write verification
                              outcome.
    outliers_gt_1tev.json -- (run, luminosityBlock, event, m0m1j0_gev,
                              category) for every event with m0m1j0 > 1000
                              GeV (kept for inspection, never discarded
                              from the histograms -- RECIPE.md deviation 4).
    sanity_arrays.json    -- dimuon mass / leading-jet pT arrays for the
                              pilot-style sanity plots.
    dimuon_diagnostics.npz -- Step 2 (B): the low-mass dimuon diagnostic
                              arrays, one row per event entering the
                              inclusive histogram.
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
import uproot  # noqa: E402

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
from studies.m0m1j0_cms import histograms, selection  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

DEFAULT_VALIDATED_RUNS_JSON = (
    "data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
)
OUTLIER_MASS_THRESHOLD_GEV = 1000.0


def git_commit_hash(repo_root) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception as e:  # noqa: BLE001 -- report, never crash metadata writing
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
    """Returns (events, present_optional_muon_branches). The required
    branches (selection.NEEDED_BRANCHES) must ALL be present or this
    raises; the optional diagnostic branches
    (selection.OPTIONAL_MUON_DIAGNOSTIC_BRANCHES) are read only if
    present in this specific file -- absence is recorded, never fatal."""
    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    missing = [b for b in selection.NEEDED_BRANCHES if b not in available]
    if missing:
        raise ValueError(
            f"{file_url}: missing required branch(es): {missing}. Refusing to "
            f"proceed rather than silently treating a missing branch (e.g. a "
            f"trigger path) as 'not present/not fired'."
        )
    present_optional = [b for b in selection.OPTIONAL_MUON_DIAGNOSTIC_BRANCHES if b in available]
    branches_to_read = list(selection.NEEDED_BRANCHES) + present_optional
    events = tree.arrays(branches_to_read, library="ak")
    return events, present_optional


def build_outlier_list(sel_events: ak.Array, raw_mass: ak.Array, categories) -> list:
    """(run, luminosityBlock, event, m0m1j0_gev, category) for every
    already-selected event with m0m1j0 > OUTLIER_MASS_THRESHOLD_GEV, using
    the RAW mass (before z_peak_cutoff/max_mass_cutoff) so a mass above
    the 10 TeV cutoff is still visible here for inspection -- it is only
    excluded from the histograms, never from this list."""
    mass_np = ak.to_numpy(raw_mass)
    keep = mass_np > OUTLIER_MASS_THRESHOLD_GEV
    if not keep.any():
        return []
    runs = ak.to_numpy(sel_events["run"])[keep]
    lumis = ak.to_numpy(sel_events["luminosityBlock"])[keep]
    events_nr = ak.to_numpy(sel_events["event"])[keep]
    masses = mass_np[keep]
    cats = categories[keep]
    return [
        {
            "run": int(r), "luminosityBlock": int(lu), "event": int(ev),
            "m0m1j0_gev": float(m), "category": str(c),
        }
        for r, lu, ev, m, c in zip(runs, lumis, events_nr, masses, cats)
    ]


def build_dimuon_diagnostics_npz(output_path: Path, result: dict) -> int:
    """Step 2 (B): saves one row per event entering the inclusive
    histogram (mass not NaN after z_peak_cutoff/max_mass_cutoff) --
    diagnostic only, does not affect the selection or histograms.
    Returns the number of rows written."""
    mass_np = ak.to_numpy(result["mass"])
    keep = ~np.isnan(mass_np)
    n_kept = int(keep.sum())

    sel_events = result["sel_events"]
    sel_muons = result["sel_muons"]
    diagnostics = selection.compute_dimuon_diagnostics(sel_muons)
    dimuon_mass = selection.compute_dimuon_mass(sel_muons)

    fields = {
        "run": ak.to_numpy(sel_events["run"])[keep].astype(np.int32),
        "luminosityBlock": ak.to_numpy(sel_events["luminosityBlock"])[keep].astype(np.int32),
        "event": ak.to_numpy(sel_events["event"])[keep].astype(np.int64),
        "m_mumu_gev": ak.to_numpy(dimuon_mass)[keep].astype(np.float32),
        "deltaR_mu0_mu1": ak.to_numpy(diagnostics["dr"])[keep].astype(np.float32),
        "charge_product": ak.to_numpy(diagnostics["charge_product"])[keep].astype(np.int8),
        "pt_ratio_mu1_mu0": ak.to_numpy(diagnostics["pt_ratio"])[keep].astype(np.float32),
        "m0m1j0_gev": mass_np[keep].astype(np.float32),
    }
    for branch in selection.OPTIONAL_MUON_DIAGNOSTIC_BRANCHES:
        field = branch[len("Muon_"):]
        for suffix in ("mu0", "mu1"):
            key = f"{field}_{suffix}"
            fields[key] = ak.to_numpy(diagnostics[key])[keep].astype(np.float32)

    np.savez_compressed(output_path, **fields)
    return n_kept


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
        "trigger_branches": list(selection.TRIGGER_BRANCHES),
        "z_peak_cutoff_gev": selection.Z_PEAK_CUTOFF_GEV,
        "max_mass_cutoff_gev": selection.MAX_MASS_CUTOFF_GEV,
        "min_events_per_final_state": selection.MIN_EVENTS_PER_FINAL_STATE,
        "outlier_mass_threshold_gev": OUTLIER_MASS_THRESHOLD_GEV,
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

    # Branch NAMES, not pre-sliced arrays: select_event_selection_cutflow
    # extracts these itself from its own post-trigger-cut `triggered`
    # array -- passing pre-sliced arrays from events_golden here crashed
    # every job of the first full-run submission (2026-09-22), since the
    # trigger cut removes events and events_golden's own length no longer
    # matches by the time selection code tries to zip them together. See
    # selection.select_event_selection_cutflow's docstring for the full
    # story.
    muon_extra_branches = ["Muon_charge"] + present_optional_branches

    result = selection.select_event_selection_cutflow(events_golden, muon_extra_branches=muon_extra_branches)

    # apply_min_events_prune=False: min_events_per_fs is a GLOBAL
    # population count taken after merging every job (RECIPE.md section
    # 5/6.5) -- a single file's own per-category count is not the
    # population to prune on. This job writes every category it sees, no
    # matter how small; the merge step applies the real prune once, after
    # summing every job's histograms by category name.
    hists, hist_meta = histograms.build_m0m1j0_histograms(
        result["obj_record"], result["mass"], apply_min_events_prune=False
    )
    _, categories = histograms.per_event_raw_and_capped_final_state(result["obj_record"])
    outliers = build_outlier_list(result["sel_events"], result["raw_mass"], categories)

    # Pilot-style sanity-check inputs (not part of the m0m1j0 selection
    # itself): dimuon mass of the selected pair and leading-jet pT, over
    # the same already-selected (>=2mu, >=1 light jet) event population.
    dimuon_mass = ak.to_numpy(
        selection.compute_dimuon_mass(result["obj_record"]["Muons"])
    ).tolist()
    lead_jet_pt = ak.to_numpy(
        selection.leading_jet_pt(result["obj_record"]["Jets"])
    ).tolist()

    # Step 2 (A): write genuine TH1F (float32), not TH1D, then verify.
    root_path = output_dir / "all_histograms.root"
    verify_expected = {}
    with uproot.recreate(str(root_path)) as f:
        for bumpnet_name, (values, edges) in hists.items():
            key = f"ROI_{bumpnet_name}_width_{int(histograms.BIN_WIDTH_GEV)}"
            f[key] = histograms.to_writable_th1f(values, edges, key)
            verify_expected[key] = values
    histograms.verify_written_th1f(str(root_path), verify_expected)
    print(f"verified {len(verify_expected)} histogram(s) in {root_path}: all TH1F, bin contents match", flush=True)

    # Step 2 (B): low-mass dimuon diagnostic npz.
    npz_path = output_dir / "dimuon_diagnostics.npz"
    n_diag_rows = build_dimuon_diagnostics_npz(npz_path, result)
    npz_size_mb = npz_path.stat().st_size / (1024 * 1024)
    print(f"wrote {npz_path}: {n_diag_rows} rows, {npz_size_mb:.2f} MB", flush=True)

    elapsed = time.time() - t0

    cutflow = {
        "n_read": n_read,
        "n_after_golden_json": golden_stats["n_after"],
        "n_after_trigger": result["n_after_trigger"],
        "n_after_ge2mu": result["n_after_ge2mu"],
        "n_after_ge1jet_after_cleaning": result["n_after_ge1jet_after_cleaning"],
        "n_after_z_peak_and_mass_cutoff": result["n_after_z_peak_and_mass_cutoff"],
        "n_outliers_gt_1tev": len(outliers),
    }

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "validated_runs_json": args.validated_runs_json,
        "validated_runs_sha256": validated_runs.sha256,
        "golden_json_per_run": golden_stats["per_run"],
        "cutflow": cutflow,
        "per_category": hist_meta,
        "n_histograms_written": len(hists),
        "histograms_verified_th1f": True,
        "thresholds": selection_thresholds(),
        "optional_muon_diagnostic_branches_present": present_optional_branches,
        "n_dimuon_diagnostic_rows": n_diag_rows,
        "dimuon_diagnostics_npz_size_mb": round(npz_size_mb, 3),
        "elapsed_sec": elapsed,
    }

    (output_dir / "job_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (output_dir / "outliers_gt_1tev.json").write_text(json.dumps(outliers, indent=2), encoding="utf-8")
    (output_dir / "sanity_arrays.json").write_text(
        json.dumps({"dimuon_mass_gev": dimuon_mass, "leading_jet_pt_gev": lead_jet_pt}), encoding="utf-8"
    )

    print(json.dumps(cutflow, indent=2))
    print(f"wrote {root_path}, job_metadata.json, outliers_gt_1tev.json, sanity_arrays.json, "
          f"dimuon_diagnostics.npz under {output_dir} ({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
