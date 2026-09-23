#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- selection-variants task (supervisor request),
ttbar MC per-job driver.

Same as run_m0m1j0_variants_on_file.py but for one ttbar dilepton
NanoAODSIM file (record 67801): no golden-JSON filter (simulation has no
certified-runs concept -- services.parsing.validated_runs would itself
refuse to run on it), genWeight read and carried through each variant's
mass_by_category npz. No low-mass-dimuon / V2-overlap diagnostics here --
the task's own "Diagnostics per variant" requirement is explicitly
data-only.

Writes, under --output-dir:
    job_metadata.json                    -- per-variant cutflow,
                                             sum_genWeight/negative-weight
                                             fraction (over ALL read
                                             events, same convention as
                                             the V0 ttbar driver).
    mass_by_category_<variant>.npz       -- category, m0m1j0_raw_gev,
                                             genWeight -- one per variant.
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

from studies.m0m1j0_cms import histograms, selection, variants  # noqa: E402
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
    import uproot

    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    required = set(selection.NEEDED_BRANCHES) | set(variants.ALL_TRIGGER_BRANCHES) | set(MC_BRANCHES)
    missing = sorted(required - available)
    if missing:
        raise ValueError(
            f"{file_url}: missing required branch(es): {missing}. Refusing to "
            f"proceed rather than silently treating a missing trigger path or "
            f"genWeight as 'not present'."
        )
    present_optional = [b for b in selection.OPTIONAL_MUON_DIAGNOSTIC_BRANCHES if b in available]
    branches_to_read = sorted(required | set(present_optional))
    events = tree.arrays(branches_to_read, library="ak")
    return events, present_optional


def build_mass_by_category_npz(output_path: Path, result: dict) -> int:
    _, categories = histograms.per_event_raw_and_capped_final_state(result["obj_record"])
    raw_mass = ak.to_numpy(result["raw_mass"]).astype(np.float64)
    gen_weight = ak.to_numpy(result["sel_events"]["genWeight"]).astype(np.float64)
    np.savez_compressed(output_path, category=categories, m0m1j0_raw_gev=raw_mass, genWeight=gen_weight)
    return len(raw_mass)


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

    per_variant_cutflow = {}
    per_variant_n_mass_rows = {}

    for variant_key in variants.VARIANT_ORDER:
        result = variants.run_variant(variant_key, events, muon_extra_branches=muon_extra_branches)

        npz_path = output_dir / f"mass_by_category_{variant_key}.npz"
        n_mass_rows = build_mass_by_category_npz(npz_path, result)
        per_variant_n_mass_rows[variant_key] = n_mass_rows

        per_variant_cutflow[variant_key] = {
            "n_read": n_read,
            "n_after_trigger": result["n_after_trigger"],
            "n_after_ge2mu": result["n_after_ge2mu"],
            "n_after_ge1jet_after_cleaning": result["n_after_ge1jet_after_cleaning"],
            "n_after_z_peak_and_mass_cutoff": result["n_after_z_peak_and_mass_cutoff"],
        }
        print(f"variant {variant_key}: n_after_ge1jet_after_cleaning="
              f"{result['n_after_ge1jet_after_cleaning']}, wrote {npz_path.name} ({n_mass_rows} rows)", flush=True)

    elapsed = time.time() - t0

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "is_simulation": True,
        "golden_json_applied": False,
        "n_read": n_read,
        "sum_genWeight_all_read_events": sum_gen_weight,
        "negative_weight_fraction_all_read_events": frac_negative_weight,
        "variant_order": list(variants.VARIANT_ORDER),
        "per_variant_cutflow": per_variant_cutflow,
        "per_variant_n_mass_by_category_rows": per_variant_n_mass_rows,
        "thresholds": selection_thresholds(),
        "optional_muon_diagnostic_branches_present": present_optional_branches,
        "known_limitations": [
            "no pileup reweighting", "no muon/b-tag scale factors",
            "no trigger efficiency corrections", "not scaled to luminosity by default"
            " (a separate, clearly-labelled optional plot scales V0 only -- see merge_variants.py)",
        ],
        "elapsed_sec": elapsed,
    }
    (output_dir / "job_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps(per_variant_cutflow, indent=2))
    print(f"wrote job_metadata.json and {len(variants.VARIANT_ORDER)} mass_by_category_<variant>.npz "
          f"files under {output_dir} ({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
