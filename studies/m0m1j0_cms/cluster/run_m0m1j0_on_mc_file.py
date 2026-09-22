#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- Part B: ttbar MC per-job driver.

Same selection as the data study (studies.m0m1j0_cms.selection --
UNCHANGED, no cut added/removed/changed) applied to one CMS ttbar
dilepton MC NanoAODSIM file (record 67801,
/TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM,
post-VFP UL2016, matching Run2016G+H -- RECIPE.md documents the search
for this record).

MC-specific handling (RECIPE.md documents every item):
  - NO golden-JSON filter at all -- simulation has no certified-runs
    concept (services.parsing.validated_runs.apply_validated_runs_filter
    would itself refuse to run on simulation -- not called here at all,
    rather than calling and catching that refusal).
  - Same trigger requirement (both HLT branches), fails loudly if either
    is missing from the MC file -- MC NanoAOD carries trigger-emulation
    HLT branches, same names as data.
  - Identical object selection/cleaning/b-tagging/categories/cutoffs/
    post-processing as data (post-processing itself happens at merge
    time, same as the v2 data correction -- this driver only produces
    the per-job raw inputs, mass_by_category_mc.npz, with genWeight
    riding along).
  - genWeight: read as a plain per-event scalar field on `events`, so it
    survives apply_trigger's and the final selection mask's slicing
    automatically (both operate as `events[mask]`, preserving every
    field) -- no special per-muon-style threading needed, unlike the
    optional muon diagnostic branches.
  - PRIMARY histogram output is UNWEIGHTED event counts (directly
    comparable to the data histogram's format); a SEPARATE, clearly
    named set of histograms uses genWeight as the fill weight. NOT
    scaled to luminosity -- the DoubleMuon luminosity isn't verified yet
    (task's own explicit note).
  - Known NOT applied here (RECIPE.md's own "known limitations" list):
    pileup reweighting, muon/b-tag scale factors, trigger efficiency
    corrections.

Usage:
    python run_m0m1j0_on_mc_file.py \
        --record-id 67801 --file-index 0 \
        --output-dir /storage/.../ttbar_job_1

Writes, under --output-dir:
    job_metadata.json       -- file URL/event count, cutflow, sum_genWeight
                                and negative-weight fraction (over ALL read
                                events, not just selected -- the standard MC
                                normalization convention), thresholds.
    mass_by_category.npz    -- category, m0m1j0_raw_gev, genWeight -- one
                                row per event with >=2 muons and >=1 light
                                jet (same population as the data study's
                                equivalent file); the merge step runs the
                                real pipeline post-processing on this, both
                                unweighted and genWeight-weighted.
    sanity_arrays.json      -- dimuon_mass_gev, leading_jet_pt_gev, n_bjets,
                                genWeight -- for the pilot's own sanity PNGs.
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

from studies.m0m1j0_cms import histograms, selection  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

MC_BRANCHES = ("genWeight",)


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
    """Returns (events, present_optional_muon_branches). Same required-
    branch discipline as the data driver, PLUS genWeight (required for
    MC -- fails loudly if absent, never silently treats a missing
    genWeight as weight-1)."""
    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    missing = [b for b in selection.NEEDED_BRANCHES if b not in available]
    missing += [b for b in MC_BRANCHES if b not in available]
    if missing:
        raise ValueError(
            f"{file_url}: missing required branch(es): {missing}. Refusing to "
            f"proceed rather than silently treating a missing branch (e.g. a "
            f"trigger path or genWeight) as 'not present'."
        )
    present_optional = [b for b in selection.OPTIONAL_MUON_DIAGNOSTIC_BRANCHES if b in available]
    branches_to_read = list(selection.NEEDED_BRANCHES) + present_optional + list(MC_BRANCHES)
    events = tree.arrays(branches_to_read, library="ak")
    return events, present_optional


def build_mass_by_category_npz(output_path: Path, result: dict) -> int:
    """Same as the data study's equivalent (studies.m0m1j0_cms.cluster.
    run_m0m1j0_on_file.build_mass_by_category_npz) plus a genWeight
    column -- one row per event with >=2 selected muons and >=1 selected
    light jet (n_after_ge1jet_after_cleaning), RAW mass (before z_peak/
    max_mass/peak-removal/outlier-split)."""
    _, categories = histograms.per_event_raw_and_capped_final_state(result["obj_record"])
    raw_mass = ak.to_numpy(result["raw_mass"]).astype(np.float64)
    gen_weight = ak.to_numpy(result["sel_events"]["genWeight"]).astype(np.float64)
    np.savez_compressed(output_path, category=categories, m0m1j0_raw_gev=raw_mass, genWeight=gen_weight)
    return len(raw_mass)


def build_sanity_arrays(result: dict) -> dict:
    dimuon_mass = ak.to_numpy(selection.compute_dimuon_mass(result["obj_record"]["Muons"])).tolist()
    lead_jet_pt = ak.to_numpy(selection.leading_jet_pt(result["obj_record"]["Jets"])).tolist()
    n_bjets = ak.to_numpy(ak.num(result["obj_record"]["BJets"])).tolist()
    gen_weight = ak.to_numpy(result["sel_events"]["genWeight"]).tolist()
    return {
        "dimuon_mass_gev": dimuon_mass, "leading_jet_pt_gev": lead_jet_pt,
        "n_bjets": n_bjets, "genWeight": gen_weight,
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
        "trigger_branches": list(selection.TRIGGER_BRANCHES),
        "z_peak_cutoff_gev": selection.Z_PEAK_CUTOFF_GEV,
        "max_mass_cutoff_gev": selection.MAX_MASS_CUTOFF_GEV,
        "min_events_per_final_state": selection.MIN_EVENTS_PER_FINAL_STATE,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record-id", type=int, required=True)
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--output-dir", required=True)
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

    gen_weight_all = ak.to_numpy(events["genWeight"])
    sum_gen_weight = float(np.sum(gen_weight_all))
    frac_negative_weight = float(np.mean(gen_weight_all < 0)) if n_read > 0 else 0.0
    print(f"sum_genWeight (all read events) = {sum_gen_weight:.4f}, "
          f"negative-weight fraction = {frac_negative_weight:.6f}", flush=True)

    muon_extra_branches = ["Muon_charge"] + present_optional_branches
    result = selection.select_event_selection_cutflow(events, muon_extra_branches=muon_extra_branches)

    n_mass_rows = build_mass_by_category_npz(output_dir / "mass_by_category.npz", result)

    sanity = build_sanity_arrays(result)
    (output_dir / "sanity_arrays.json").write_text(json.dumps(sanity), encoding="utf-8")

    elapsed = time.time() - t0

    cutflow = {
        "n_read": n_read,
        "n_after_trigger": result["n_after_trigger"],
        "n_after_ge2mu": result["n_after_ge2mu"],
        "n_after_ge1jet_after_cleaning": result["n_after_ge1jet_after_cleaning"],
        "n_after_z_peak_and_mass_cutoff": result["n_after_z_peak_and_mass_cutoff"],
    }

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "is_simulation": True,
        "golden_json_applied": False,
        "cutflow": cutflow,
        "sum_genWeight_all_read_events": sum_gen_weight,
        "negative_weight_fraction_all_read_events": frac_negative_weight,
        "n_mass_by_category_rows": n_mass_rows,
        "thresholds": selection_thresholds(),
        "optional_muon_diagnostic_branches_present": present_optional_branches,
        "known_limitations": [
            "no pileup reweighting", "no muon/b-tag scale factors",
            "no trigger efficiency corrections", "not scaled to luminosity",
        ],
        "elapsed_sec": elapsed,
    }
    (output_dir / "job_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps(cutflow, indent=2))
    print(f"wrote job_metadata.json, mass_by_category.npz, sanity_arrays.json under {output_dir} "
          f"({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
