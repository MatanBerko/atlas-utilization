#!/usr/bin/env python
"""
Per-dataset BumpNet-yield measurement WITH each dataset's own trigger --
per-job driver.

Builds directly on studies/cms_coverage/per_dataset/cluster/
run_per_dataset_on_file.py (same object definitions, same 186 combination
patterns, same topology-free ">=2 selected objects of ANY type" gate, same
chunked reading). The ONE change from that script: an optional per-dataset
HLT trigger requirement, applied via the real, unmodified
services.parsing.trigger_requirements.apply_trigger_requirement (imported,
not reimplemented), inserted AFTER golden-JSON (for data) and BEFORE object
selection -- exactly where the shared pipeline itself applies it
(orchestration/handlers/parsing_handler.py's own ordering: validated-runs
filter, then trigger requirement, then kinematic/object selection).

Golden-JSON is still applied to data only, never MC (unchanged). MC files
here are run with NO trigger requirement (--trigger-paths omitted) --
matching the task's own instruction that MC's role for BumpNet is separate
and unsettled.

Usage:
    python run_per_dataset_on_file.py --record-id 30530 --file-index 0 \
        --output-dir /storage/.../job_SingleMuon --dataset-label SingleMuon \
        --trigger-paths HLT_IsoMu24,HLT_IsoTkMu24
    python run_per_dataset_on_file.py --record-id 67801 --file-index 0 \
        --output-dir /storage/.../job_mc_ttbar --dataset-label mc_ttbar --is-mc
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

from services.calculations import physics_calcs  # noqa: E402
from services.calculations.combinatorics import get_all_combinations  # noqa: E402
from services.calculations.im_calculator import IMCalculator  # noqa: E402
from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
from services.parsing.trigger_requirements import apply_trigger_requirement  # noqa: E402
from services.pipelines.im_pipeline import (  # noqa: E402
    _calculate_combination_invariant_mass,
    prepare_im_combination_name,
)
from services.storage.sqlite_shards import SqliteArrayShardWriter  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

DEFAULT_VALIDATED_RUNS_JSON = (
    "data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
)

# Object definitions UNCHANGED from RECIPE.md -- see the non-triggered
# driver's own comment. Trigger branches are added to this list PER JOB,
# from --trigger-paths, not hardcoded here (different datasets need
# different paths).
BASE_REQUIRED_BRANCHES = (
    "run", "luminosityBlock", "event",
    "nMuon", "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass",
    "Muon_mediumId", "Muon_pfRelIso04_all",
    "nElectron", "Electron_pt", "Electron_eta", "Electron_phi", "Electron_mass",
    "Electron_cutBased",
    "nJet", "Jet_pt", "Jet_eta", "Jet_phi", "Jet_mass", "Jet_jetId",
    "Jet_btagDeepFlavB",
)

OBJECT_TYPES = ["Electrons", "Muons", "Jets", "BJets"]
MIN_PARTICLES_IN_COMBINATION = 1
MAX_PARTICLES_IN_COMBINATION = 4
MIN_COUNT_PARTICLE_IN_COMBINATION = 1
MAX_COUNT_PARTICLE_IN_COMBINATION = 4
MAX_TOTAL_PARTICLES_IN_COMBINATION = 4
INCLUDE_SUBLEADING = True
MAX_SUBLEADING_INDEX = 1
FIELD_TO_SLICE_BY = "pt"

MIN_TOTAL_SELECTED_OBJECTS = 2  # dropped-topology requirement: >=2 objects of ANY type, kept from before

READ_RETRY_ATTEMPTS = 4
READ_RETRY_BACKOFF_SEC = 15
READ_CHUNK_SIZE = 300_000

COVERAGE_CAP_PER_SIGNATURE = 500_000


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


def _read_chunk_with_retry(tree, branches, entry_start, entry_stop, file_url):
    last_exc = None
    for attempt in range(1, READ_RETRY_ATTEMPTS + 1):
        try:
            return tree.arrays(branches, entry_start=entry_start, entry_stop=entry_stop, library="ak")
        except Exception as e:  # noqa: BLE001 -- transient XRootD read failure
            last_exc = e
            print(f"read attempt {attempt}/{READ_RETRY_ATTEMPTS} failed for {file_url} "
                  f"[{entry_start}:{entry_stop}]: {type(e).__name__}: {e}", flush=True)
            if attempt < READ_RETRY_ATTEMPTS:
                time.sleep(READ_RETRY_BACKOFF_SEC)
    raise RuntimeError(
        f"{file_url} [{entry_start}:{entry_stop}]: failed to read after {READ_RETRY_ATTEMPTS} attempts"
    ) from last_exc


def read_events(file_url: str, required_branches):
    """Chunked read (fix already established for this measurement: a
    single whole-file request fails reproducibly on real files)."""
    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    missing = [b for b in required_branches if b not in available]
    if missing:
        raise ValueError(
            f"{file_url}: missing required branch(es): {missing}."
        )
    branches = list(required_branches)
    n_entries = tree.num_entries
    chunks = []
    for start in range(0, n_entries, READ_CHUNK_SIZE):
        stop = min(start + READ_CHUNK_SIZE, n_entries)
        chunks.append(_read_chunk_with_retry(tree, branches, start, stop, file_url))
    return ak.concatenate(chunks) if len(chunks) > 1 else chunks[0]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record-id", type=int, required=True)
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--dataset-label", required=True)
    p.add_argument("--is-mc", action="store_true")
    p.add_argument("--trigger-paths", default="",
                    help="Comma-separated HLT branch names, OR'd together. Empty = no trigger requirement.")
    p.add_argument("--validated-runs-json", default=DEFAULT_VALIDATED_RUNS_JSON)
    args = p.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("per_dataset_job")

    trigger_paths = [p_.strip() for p_ in args.trigger_paths.split(",") if p_.strip()]
    trigger_spec = {"mode": "any", "paths": trigger_paths} if trigger_paths else None

    required_branches = list(BASE_REQUIRED_BRANCHES) + trigger_paths

    t0 = time.time()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_url = resolve_file_url(args.record_id, args.file_index)
    print(f"[{args.dataset_label}] resolved record {args.record_id} file index {args.file_index} "
          f"-> {file_url}", flush=True)

    events = read_events(file_url, required_branches)
    n_read = len(events)
    print(f"[{args.dataset_label}] read {n_read} events", flush=True)

    n_after_golden_json = n_read
    golden_json_applied = False
    if not args.is_mc:
        validated_runs = ValidatedRunsFilter(args.validated_runs_json)
        events, golden_stats = apply_validated_runs_filter(events, validated_runs)
        n_after_golden_json = golden_stats["n_after"]
        golden_json_applied = True
        print(f"[{args.dataset_label}] golden-JSON filter: {golden_stats['n_before']} -> "
              f"{golden_stats['n_after']}", flush=True)
    else:
        print(f"[{args.dataset_label}] MC file: golden-JSON filter NOT applied (task instruction)", flush=True)

    n_after_trigger = n_after_golden_json
    trigger_stats = None
    if trigger_spec is not None:
        events, trigger_stats = apply_trigger_requirement(events, trigger_spec)
        n_after_trigger = trigger_stats["n_after"]
        print(f"[{args.dataset_label}] trigger requirement ({trigger_spec['mode']}: {trigger_paths}): "
              f"{trigger_stats['n_before']} -> {trigger_stats['n_after']}, per_path={trigger_stats['per_path']}",
              flush=True)
    else:
        print(f"[{args.dataset_label}] no trigger requirement applied", flush=True)

    # UNCHANGED object definitions (RECIPE.md), imported directly.
    muons = selection.select_muons(events)
    electrons = selection.select_electrons(events)
    jets = selection.select_and_split_jets(events, muons, electrons, apply_lepton_cleaning=True)

    # UNCHANGED dropped-topology requirement: >=2 selected objects of ANY type.
    total_objects = ak.num(muons) + ak.num(electrons) + ak.num(jets["Jets"]) + ak.num(jets["BJets"])
    keep = total_objects >= MIN_TOTAL_SELECTED_OBJECTS
    n_after_object_gate = int(ak.sum(keep))
    print(f"[{args.dataset_label}] events with >={MIN_TOTAL_SELECTED_OBJECTS} selected objects "
          f"(any type): {n_after_object_gate}", flush=True)

    sel_muons = muons[keep]
    sel_electrons = electrons[keep]
    sel_jets = {"Jets": jets["Jets"][keep], "BJets": jets["BJets"][keep]}
    obj_record = selection.build_object_record(sel_muons, sel_electrons, sel_jets)

    all_combinations = get_all_combinations(
        object_types=OBJECT_TYPES,
        min_particles=MIN_PARTICLES_IN_COMBINATION,
        max_particles=MAX_PARTICLES_IN_COMBINATION,
        min_count=MIN_COUNT_PARTICLE_IN_COMBINATION,
        max_count=MAX_COUNT_PARTICLE_IN_COMBINATION,
        max_total_particles=MAX_TOTAL_PARTICLES_IN_COMBINATION,
        include_subleading=INCLUDE_SUBLEADING,
        max_subleading_index=MAX_SUBLEADING_INDEX,
    )
    assert len(all_combinations) == 186, f"expected 186 combinations, got {len(all_combinations)}"

    calculator = IMCalculator(
        events=obj_record, min_events_per_fs=1,
        min_k=MIN_COUNT_PARTICLE_IN_COMBINATION, max_k=MAX_COUNT_PARTICLE_IN_COMBINATION,
        min_n=MIN_PARTICLES_IN_COMBINATION, max_n=MAX_PARTICLES_IN_COMBINATION,
    )
    im_config = {"field_to_slice_by": FIELD_TO_SLICE_BY}

    job_tag = f"{args.dataset_label}_record{args.record_id}_file{args.file_index}"
    shard_path = output_dir / "coverage_shard.sqlite"
    if shard_path.exists():
        shard_path.unlink()
    writer = SqliteArrayShardWriter(str(shard_path))

    n_fs_groups = 0
    n_signature_writes = 0
    n_values_written = 0
    max_signature_size = 0
    n_capped_signatures = 0
    label_event_counts: dict[str, int] = {}
    skip_reason_totals: dict[str, int] = {}

    for label, fs_events in physics_calcs.group_by_final_state(obj_record):
        n_fs_groups += 1
        n_this_group = len(fs_events)
        label_event_counts[label] = label_event_counts.get(label, 0) + n_this_group
        writer.record_final_state_count(label, n_this_group)

        for combination in all_combinations:
            if not physics_calcs.is_finalstate_contain_combination(label, combination):
                continue

            inv_mass, skip_reason = _calculate_combination_invariant_mass(
                fs_events, combination, im_config, calculator, logger, label,
            )
            if inv_mass is None:
                if skip_reason:
                    skip_reason_totals[skip_reason] = skip_reason_totals.get(skip_reason, 0) + 1
                continue

            arr = ak.to_numpy(inv_mass).astype(np.float32)
            arr = arr[~np.isnan(arr)]
            if arr.size == 0:
                continue

            signature = prepare_im_combination_name(job_tag, label, combination)
            if arr.size > max_signature_size:
                max_signature_size = int(arr.size)
            if arr.size > COVERAGE_CAP_PER_SIGNATURE:
                n_capped_signatures += 1
                rng = np.random.default_rng(seed=0)
                arr = rng.choice(arr, size=COVERAGE_CAP_PER_SIGNATURE, replace=False)
                writer.set_metadata(f"CAPPED::{signature}", f"true_size={int(arr.size)}")

            writer.append_array(signature, arr)
            n_signature_writes += 1
            n_values_written += int(arr.size)

    writer.set_metadata("n_read", n_read)
    writer.set_metadata("n_after_golden_json", n_after_golden_json)
    writer.set_metadata("n_after_trigger", n_after_trigger)
    writer.set_metadata("n_after_object_gate", n_after_object_gate)
    writer.set_metadata("dataset_label", args.dataset_label)
    writer.set_metadata("record_id", args.record_id)
    writer.set_metadata("file_index", args.file_index)
    writer.set_metadata("file_url", file_url)
    writer.set_metadata("is_mc", args.is_mc)
    writer.set_metadata("golden_json_applied", golden_json_applied)
    writer.set_metadata("trigger_paths", ",".join(trigger_paths))
    writer.set_metadata("topology_required", False)
    writer.commit()
    writer.close()

    elapsed = time.time() - t0
    shard_size_mb = shard_path.stat().st_size / (1024 * 1024)

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "dataset_label": args.dataset_label,
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "is_mc": args.is_mc,
        "golden_json_applied": golden_json_applied,
        "trigger_paths": trigger_paths,
        "trigger_stats": trigger_stats,
        "topology_required": False,
        "validated_runs_json": args.validated_runs_json if golden_json_applied else None,
        "n_read": n_read,
        "n_after_golden_json": n_after_golden_json,
        "n_after_trigger": n_after_trigger,
        "n_after_object_gate": n_after_object_gate,
        "n_final_state_groups": n_fs_groups,
        "n_distinct_final_state_labels": len(label_event_counts),
        "final_state_label_event_counts": label_event_counts,
        "n_combinations_checked_per_group": len(all_combinations),
        "n_signature_writes": n_signature_writes,
        "n_values_written": n_values_written,
        "max_signature_size_this_job": max_signature_size,
        "n_capped_signatures": n_capped_signatures,
        "skip_reason_totals": skip_reason_totals,
        "shard_size_mb": round(shard_size_mb, 3),
        "elapsed_sec": elapsed,
    }
    (output_dir / "job_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps({
        "dataset_label": args.dataset_label, "n_read": n_read,
        "n_after_trigger": n_after_trigger,
        "n_after_object_gate": n_after_object_gate,
        "n_signature_writes": n_signature_writes, "n_values_written": n_values_written,
        "max_signature_size_this_job": max_signature_size,
        "shard_size_mb": round(shard_size_mb, 3), "elapsed_sec": round(elapsed, 1),
    }, indent=2))
    print(f"[{args.dataset_label}] wrote {shard_path} and job_metadata.json under {output_dir} "
          f"({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
