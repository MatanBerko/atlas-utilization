#!/usr/bin/env python
"""
Ceiling-measurement per-job driver: same real, unmodified funnel as
studies/cms_coverage/per_dataset/triggered/cluster/run_per_dataset_on_file.py
(chunked reads, golden-JSON for data only, per-dataset trigger requirement,
topology-free ">=2 selected objects of ANY type" gate, get_all_combinations
+ IMCalculator + _calculate_combination_invariant_mass + SqliteArrayShardWriter),
GENERALIZED along the two axes this task's C1-C5 grid needs:

  --object-set {4type,6type}   Electrons/Muons/Jets/BJets, or +Photons/+Taus
                                (studies/cms_coverage/ceiling/objects.py --
                                see DEFINITIONS.md for the photon/tau cuts
                                and their sources).
  --max-total-objects N        max_particles / max_total_particles passed to
                                get_all_combinations (C1/C2=4, C3=5, C4=6).
  --with-met                   C5 only: adds a MET pseudo-object field and
                                doubles every combination with a "+MET"
                                variant (objects.py's build_met_pseudo_object
                                / add_met_variants). Requires 6type.

Electron/muon/jet/b-jet definitions, golden JSON, per-dataset trigger,
10 GeV/0-10 TeV grid and BumpNet thresholds are UNCHANGED -- imported from
studies.m0m1j0_cms.selection, not reimplemented. C1 (4type, max-total=4)
MUST reproduce the already-committed 186-combination / 339-distinct-data /
682-distinct-MC result from the triggered run exactly; this script asserts
the combination count and the calling driver/report checks the rest.

Usage:
    python run_ceiling_on_file.py --record-id 30530 --file-index 0 \
        --output-dir /storage/.../job_SingleMuon_C1 --dataset-label SingleMuon \
        --trigger-paths HLT_IsoMu24,HLT_IsoTkMu24 \
        --object-set 4type --max-total-objects 4
    python run_ceiling_on_file.py --record-id 30532 --file-index 0 \
        --output-dir /storage/.../job_Tau_C2 --dataset-label Tau \
        --trigger-paths HLT_DoubleMediumIsoPFTau35_Trk1_eta2p1_Reg,HLT_DoubleMediumIsoPFTau40_Trk1_eta2p1_Reg \
        --object-set 6type --max-total-objects 4
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
from studies.cms_coverage.ceiling import objects as ceiling_objects  # noqa: E402

DEFAULT_VALIDATED_RUNS_JSON = (
    "data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
)

BASE_REQUIRED_BRANCHES = (
    "run", "luminosityBlock", "event",
    "nMuon", "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass",
    "Muon_mediumId", "Muon_pfRelIso04_all",
    "nElectron", "Electron_pt", "Electron_eta", "Electron_phi", "Electron_mass",
    "Electron_cutBased",
    "nJet", "Jet_pt", "Jet_eta", "Jet_phi", "Jet_mass", "Jet_jetId",
    "Jet_btagDeepFlavB",
)

OBJECT_SETS = {
    "4type": ["Electrons", "Muons", "Jets", "BJets"],
    "6type": ["Electrons", "Muons", "Jets", "BJets", "Photons", "Taus"],
}
EXPECTED_N_COMBINATIONS = {
    ("4type", 4): 186,
    ("6type", 4): 853,
    ("6type", 5): 1975,
    ("6type", 6): 3904,
}

MIN_PARTICLES_IN_COMBINATION = 1
MIN_COUNT_PARTICLE_IN_COMBINATION = 1
MAX_COUNT_PARTICLE_IN_COMBINATION = 4
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
    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    missing = [b for b in required_branches if b not in available]
    if missing:
        raise ValueError(f"{file_url}: missing required branch(es): {missing}.")
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
    p.add_argument("--object-set", choices=list(OBJECT_SETS), required=True)
    p.add_argument("--max-total-objects", type=int, required=True)
    p.add_argument("--with-met", action="store_true")
    args = p.parse_args()

    if args.with_met and args.object_set != "6type":
        raise ValueError("--with-met requires --object-set 6type")

    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("ceiling_job")

    object_types = OBJECT_SETS[args.object_set]
    max_particles = len(object_types)
    max_total = args.max_total_objects

    trigger_paths = [p_.strip() for p_ in args.trigger_paths.split(",") if p_.strip()]
    trigger_spec = {"mode": "any", "paths": trigger_paths} if trigger_paths else None

    required_branches = list(BASE_REQUIRED_BRANCHES) + trigger_paths
    if args.object_set == "6type":
        required_branches += list(ceiling_objects.PHOTON_REQUIRED_BRANCHES)
        required_branches += list(ceiling_objects.TAU_REQUIRED_BRANCHES)
    if args.with_met:
        required_branches += list(ceiling_objects.MET_REQUIRED_BRANCHES)
    required_branches = list(dict.fromkeys(required_branches))  # de-dup, keep order

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

    overlap_diagnostics = {}
    if args.object_set == "6type":
        leptons = ak.concatenate([muons, electrons], axis=1)
        all_jets = ak.concatenate([jets["Jets"], jets["BJets"]], axis=1)

        photons_precln = ceiling_objects.select_photons_precleaning(events)
        photons, photon_overlap = ceiling_objects.overlap_removal(photons_precln, leptons, all_jets)
        overlap_diagnostics["photons"] = photon_overlap
        print(f"[{args.dataset_label}] photon overlap: {photon_overlap}", flush=True)

        taus_precln = ceiling_objects.select_taus_precleaning(events)
        taus, tau_overlap = ceiling_objects.overlap_removal(taus_precln, leptons, all_jets)
        overlap_diagnostics["taus"] = tau_overlap
        print(f"[{args.dataset_label}] tau overlap: {tau_overlap}", flush=True)

    total_objects = ak.num(muons) + ak.num(electrons) + ak.num(jets["Jets"]) + ak.num(jets["BJets"])
    if args.object_set == "6type":
        total_objects = total_objects + ak.num(photons) + ak.num(taus)
    keep = total_objects >= MIN_TOTAL_SELECTED_OBJECTS
    n_after_object_gate = int(ak.sum(keep))
    print(f"[{args.dataset_label}] events with >={MIN_TOTAL_SELECTED_OBJECTS} selected objects "
          f"(any type): {n_after_object_gate}", flush=True)

    sel_muons = muons[keep]
    sel_electrons = electrons[keep]
    sel_jets = {"Jets": jets["Jets"][keep], "BJets": jets["BJets"][keep]}

    if args.object_set == "6type":
        sel_photons = photons[keep]
        sel_taus = taus[keep]
        obj_record = ceiling_objects.build_object_record_6type(
            sel_muons, sel_electrons, sel_jets, sel_photons, sel_taus,
        )
    else:
        obj_record = selection.build_object_record(sel_muons, sel_electrons, sel_jets)

    if args.with_met:
        sel_events_for_met = events[keep]
        met_obj = ceiling_objects.build_met_pseudo_object(sel_events_for_met)
        fields_with_met = {f: obj_record[f] for f in obj_record.fields}
        fields_with_met["METObject"] = met_obj
        obj_record = ak.zip(fields_with_met, depth_limit=1)

    all_combinations = get_all_combinations(
        object_types=object_types,
        min_particles=MIN_PARTICLES_IN_COMBINATION,
        max_particles=max_particles,
        min_count=MIN_COUNT_PARTICLE_IN_COMBINATION,
        max_count=MAX_COUNT_PARTICLE_IN_COMBINATION,
        max_total_particles=max_total,
        include_subleading=INCLUDE_SUBLEADING,
        max_subleading_index=MAX_SUBLEADING_INDEX,
    )
    expected_n = EXPECTED_N_COMBINATIONS.get((args.object_set, max_total))
    if expected_n is not None:
        assert len(all_combinations) == expected_n, (
            f"expected {expected_n} combinations for object-set={args.object_set} "
            f"max-total-objects={max_total}, got {len(all_combinations)}"
        )
    n_base_combinations = len(all_combinations)
    if args.with_met:
        all_combinations = ceiling_objects.add_met_variants(all_combinations)

    calculator = IMCalculator(
        events=obj_record, min_events_per_fs=1,
        min_k=MIN_COUNT_PARTICLE_IN_COMBINATION, max_k=MAX_COUNT_PARTICLE_IN_COMBINATION,
        min_n=MIN_PARTICLES_IN_COMBINATION, max_n=max_particles,
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
            if "METObject" in combination:
                # prepare_im_combination_name's PARTICLE_ORDER has no entry
                # for "METObject" (it's new here, not a shared-code type),
                # so it silently drops it from the name -- without this,
                # a +MET variant would collide with its non-MET base
                # combination's signature (same fs, same im_str) and
                # overwrite it in the shard. "met" cannot occur naturally
                # in an im_str (always strict letter+digit pairs), so this
                # is a safe, unambiguous, regex-compatible ([0-9a-z]+)
                # suffix -- kept INSIDE the IM_ part (appended at the very
                # end of the whole string) so SIG_PATTERN's anchored
                # "_IM_([0-9a-z]+)$" still matches it.
                signature = f"{signature}met"
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
    writer.set_metadata("object_set", args.object_set)
    writer.set_metadata("max_total_objects", max_total)
    writer.set_metadata("with_met", args.with_met)
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
        "object_set": args.object_set,
        "max_total_objects": max_total,
        "with_met": args.with_met,
        "n_base_combinations": n_base_combinations,
        "n_combinations_checked_per_group": len(all_combinations),
        "overlap_diagnostics": overlap_diagnostics,
        "n_read": n_read,
        "n_after_golden_json": n_after_golden_json,
        "n_after_trigger": n_after_trigger,
        "n_after_object_gate": n_after_object_gate,
        "n_final_state_groups": n_fs_groups,
        "n_distinct_final_state_labels": len(label_event_counts),
        "final_state_label_event_counts": label_event_counts,
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
