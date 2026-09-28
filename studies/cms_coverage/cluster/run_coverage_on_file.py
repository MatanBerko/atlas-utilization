#!/usr/bin/env python
"""
CMS coverage survey -- per-job driver (Part 1).

One job = one DoubleMuon NanoAOD file, read over XRootD, exactly like
studies/m0m1j0_cms/cluster/run_m0m1j0_on_file.py (imported, unmodified event
selection -- studies.m0m1j0_cms.selection.select_event_selection_cutflow).
Where that script computes ONE combination (m0m1j0), this one computes
EVERY one of the 186 combination patterns (services.calculations.
combinatorics.get_all_combinations) against every final-state category the
selected events actually populate, using the REAL shared mass-calculation
code (services.pipelines.im_pipeline._calculate_combination_invariant_mass,
services.calculations.im_calculator.IMCalculator,
services.calculations.physics_calcs.group_by_final_state /
is_finalstate_contain_combination) -- none of that logic is reimplemented.

Storage (Part 1.2): RAW (pre-z_peak/max_mass/peak-removal/split) invariant
masses, float32, written into a per-job SQLite shard via the shared
services.storage.sqlite_shards.SqliteArrayShardWriter -- the SAME shard
format services/pipelines/post_processing_pipeline.py's SQLite path
already reads (list_signatures / iter_arrays_for_signature /
prune_final_states_below_min_events). This means the merge step (Part 1,
separate script) can call that REAL post-processing code, unmodified, on
these shards directly -- z_peak_cutoff/max_mass_cutoff/peak-removal/first-
empty-bin-split will be byte-identical to what the shared pipeline itself
would produce, not a re-derivation. Raw floats (not a histogram) are
required because _split_by_first_empty_bin anchors its bins at the data's
own min/max (see COMBINATION_RULE.md) -- no fixed-grid histogram can
reproduce that exactly.

A per-signature-per-job size cap (COVERAGE_CAP_PER_SIGNATURE) guards
against a pathological single-file blowup; the pilot run measures whether
this is ever actually reached (expected: no, see COMBINATION_RULE.md /
COVERAGE_REPORT.md for the observed maximum).

Usage:
    python run_coverage_on_file.py --record-id 30522 --file-index 0 \
        --output-dir /storage/.../job_1
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

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

from services.calculations import physics_calcs  # noqa: E402
from services.calculations.combinatorics import get_all_combinations  # noqa: E402
from services.calculations.im_calculator import IMCalculator  # noqa: E402
from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
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

# config.yaml:135-144 (mass_calculation_task_config) -- reproduced exactly,
# see COMBINATION_RULE.md.
OBJECT_TYPES = ["Electrons", "Muons", "Jets", "BJets"]
MIN_PARTICLES_IN_COMBINATION = 1
MAX_PARTICLES_IN_COMBINATION = 4
MIN_COUNT_PARTICLE_IN_COMBINATION = 1
MAX_COUNT_PARTICLE_IN_COMBINATION = 4
MAX_TOTAL_PARTICLES_IN_COMBINATION = 4
INCLUDE_SUBLEADING = True
MAX_SUBLEADING_INDEX = 1
FIELD_TO_SLICE_BY = "pt"  # config.yaml:130

# Guard, not expected to trigger -- see module docstring and
# COVERAGE_REPORT.md for the pilot's observed per-signature-per-job maximum.
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


READ_RETRY_ATTEMPTS = 4
READ_RETRY_BACKOFF_SEC = 15
READ_CHUNK_SIZE = 300_000


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


def read_events(file_url: str):
    """Read every NEEDED_BRANCHES entry from `file_url` in
    READ_CHUNK_SIZE-event chunks, retrying each chunk on a transient
    XRootD timeout.

    Chunking (not just retrying) is required, not merely helpful:
    observed directly during the full run, a SINGLE whole-file
    ``tree.arrays(...)`` call for a ~2.3-2.5M-event file failed with
    ``OSError: File did not vector_read properly: [ERROR] Operation
    expired`` on EVERY one of 4 retry attempts (with a 15s backoff) for
    at least one file, while (a) a small 1000-event/1-branch probe of
    the exact same file succeeded instantly, and (b) reading that same
    file in 300,000-event chunks succeeded end-to-end with zero errors.
    The failure is tied to REQUEST SIZE (many branches x many baskets in
    one vector-read), not file health or a fixed transient-vs-permanent
    split -- retrying the same oversized request just repeats the same
    failure. This mirrors the shared pipeline's own batched-reading
    convention (services/parsing/file_parser.py's batch_size), applied
    here for the same reason.
    """
    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    missing = [b for b in selection.NEEDED_BRANCHES if b not in available]
    if missing:
        raise ValueError(
            f"{file_url}: missing required branch(es): {missing}. Refusing "
            f"to proceed rather than silently treating a missing branch as "
            f"'not present/not fired'."
        )
    branches = list(selection.NEEDED_BRANCHES)
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
    p.add_argument("--validated-runs-json", default=DEFAULT_VALIDATED_RUNS_JSON)
    args = p.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("coverage_job")

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

    # UNCHANGED V0 selection -- imported, not reimplemented. This defines the
    # event POPULATION (>=2 muons, >=1 light jet, after golden-JSON+trigger+
    # object cuts); this survey changes only what is COMPUTED from that
    # population, not which events are in it (task scope).
    result = selection.select_event_selection_cutflow(events_golden)
    obj_record = result["obj_record"]
    n_selected = len(obj_record)
    print(f"V0-selected events (>=2mu, >=1 light jet): {n_selected}", flush=True)

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

    job_tag = f"record{args.record_id}_file{args.file_index}"
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
                writer.set_metadata(
                    f"CAPPED::{signature}",
                    f"true_size={int(arr.size)}",
                )

            writer.append_array(signature, arr)
            n_signature_writes += 1
            n_values_written += int(arr.size)

    writer.set_metadata("n_read", n_read)
    writer.set_metadata("n_after_golden_json", golden_stats["n_after"])
    writer.set_metadata("n_after_v0_selection", n_selected)
    writer.set_metadata("record_id", args.record_id)
    writer.set_metadata("file_index", args.file_index)
    writer.set_metadata("file_url", file_url)
    writer.commit()
    writer.close()

    elapsed = time.time() - t0
    shard_size_mb = shard_path.stat().st_size / (1024 * 1024)

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "validated_runs_json": args.validated_runs_json,
        "validated_runs_sha256": validated_runs.sha256,
        "n_read": n_read,
        "n_after_golden_json": golden_stats["n_after"],
        "n_after_v0_selection": n_selected,
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
        "n_read": n_read, "n_after_v0_selection": n_selected,
        "n_signature_writes": n_signature_writes, "n_values_written": n_values_written,
        "max_signature_size_this_job": max_signature_size,
        "shard_size_mb": round(shard_size_mb, 3), "elapsed_sec": round(elapsed, 1),
    }, indent=2))
    print(f"wrote {shard_path} and job_metadata.json under {output_dir} ({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
