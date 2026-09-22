#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- Step 1 per-job driver.

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
CMS object selection (studies.m0m1j0_cms.selection), m0m1j0 mass +
z_peak_cutoff/max_mass_cutoff, then builds histograms
(studies.m0m1j0_cms.histograms) and a small outlier event list. See
studies/m0m1j0_cms/RECIPE.md for the full recipe and every deviation from
the group's ATLAS config.yaml.

Usage:
    python run_m0m1j0_on_file.py \
        --record-id 30522 --file-index 0 \
        --output-dir /storage/.../job_1

Writes, under --output-dir:
    all_histograms.root   -- one TH1F per BumpNet category + one inclusive
                              (studies.m0m1j0_cms.histograms), ROI_-prefixed
                              ROOT-internal names, same fixed grid as the
                              shared pipeline.
    job_metadata.json     -- exact file URL + event count read, full
                              cutflow, per-category counts, thresholds
                              used, git commit, validated-runs file sha256.
    outliers_gt_1tev.json -- (run, luminosityBlock, event, m0m1j0_gev,
                              category) for every event with m0m1j0 > 1000
                              GeV (kept for inspection, never discarded
                              from the histograms -- RECIPE.md deviation 4).
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
import ROOT  # noqa: E402
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


def read_events(file_url: str) -> ak.Array:
    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    missing = [b for b in selection.NEEDED_BRANCHES if b not in available]
    if missing:
        raise ValueError(
            f"{file_url}: missing required branch(es): {missing}. Refusing to "
            f"proceed rather than silently treating a missing branch (e.g. a "
            f"trigger path) as 'not present/not fired'."
        )
    return tree.arrays(list(selection.NEEDED_BRANCHES), library="ak")


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

    events = read_events(file_url)
    n_read = len(events)
    print(f"read {n_read} events from {file_url}", flush=True)

    validated_runs = ValidatedRunsFilter(args.validated_runs_json)
    events_golden, golden_stats = apply_validated_runs_filter(events, validated_runs)
    print(f"golden-JSON filter: {golden_stats['n_before']} -> {golden_stats['n_after']}", flush=True)

    result = selection.select_event_selection_cutflow(events_golden)

    hists, hist_meta = histograms.build_m0m1j0_histograms(result["obj_record"], result["mass"])
    _, categories = histograms.per_event_raw_and_capped_final_state(result["obj_record"])
    outliers = build_outlier_list(result["sel_events"], result["raw_mass"], categories)

    root_path = output_dir / "all_histograms.root"
    root_file = ROOT.TFile(str(root_path), "RECREATE")
    for hist in hists.values():
        hist.Write()
    root_file.Close()

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
        "thresholds": selection_thresholds(),
        "elapsed_sec": elapsed,
    }

    (output_dir / "job_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (output_dir / "outliers_gt_1tev.json").write_text(json.dumps(outliers, indent=2), encoding="utf-8")

    print(json.dumps(cutflow, indent=2))
    print(f"wrote {root_path}, job_metadata.json, outliers_gt_1tev.json under {output_dir} "
          f"({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
