#!/usr/bin/env python
"""
Implementation task 6, Part E: analysis-layer driver for one cluster job.

Run AFTER the shared pipeline's parsing stage (main.py --tasks parsing) has
written its chunk ROOT files for this job to --chunks-dir. Reads every
chunk, applies studies.hgg_cms.selection's H->gamma-gamma selection, and
writes one output (+ one metadata JSON) per chunk via studies.hgg_cms.output
-- "one output per input file (or chunk), merged later" (see
studies/hgg_cms/cluster/merge_outputs.py).

Usage:
    python run_selection_on_chunks.py \
        --chunks-dir /storage/.../parsed_data_ggh \
        --output-dir /storage/.../selected_ggh \
        --record-id 37350 \
        --is-data false \
        --config config.cms_hgg_signal_ggh.yaml \
        [--genEventSumw-json /storage/.../genEventSumw_ggh.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import uproot  # noqa: E402

from domain.config import PipelineConfig  # noqa: E402
from studies.hgg_cms import selection  # noqa: E402
from studies.hgg_cms.output import (  # noqa: E402
    build_output_table, safe_output_filename, write_event_output, write_metadata,
)
import yaml  # noqa: E402


def check_dedup_never_active(config_path: str) -> int:
    """De-duplication (orchestration/handlers/parsing_handler.py) only
    activates when `selection_by_record` is set in the parsing config, and
    it must never run on simulation (see the guard added in
    orchestration/handlers/parsing_handler.py and
    tests/test_dedup_simulation_guard.py). None of this task's H->gamma-
    gamma configs set `selection_by_record` (single DoubleEG stream for
    data, one record per signal config) -- so de-duplication never runs at
    all for any of them, and "de-duplication removed N simulation events"
    is trivially N=0 by construction, not by having observed 0 collisions.
    Returns 0 on success; raises if a config unexpectedly turns dedup on,
    since that would need the simulation guard to have actually been
    exercised (and this driver doesn't re-verify that separately)."""
    raw = yaml.safe_load(open(config_path, encoding="utf-8"))
    cfg = PipelineConfig.from_dict(raw)
    sel_by_record = cfg.parsing_config.selection_by_record
    if sel_by_record is not None:
        raise RuntimeError(
            f"config {config_path} sets selection_by_record={sel_by_record!r} "
            "-- de-duplication WOULD be active for this run. This driver "
            "only knows how to certify '0 simulation events removed by "
            "dedup' for configs where dedup never turns on at all; if a "
            "future H->gamma-gamma config needs selection_by_record, this "
            "check must be revisited (and the simulation-dedup guard in "
            "orchestration/handlers/parsing_handler.py re-confirmed)."
        )
    return 0


def read_chunk(chunk_path: Path) -> ak.Array:
    """Reads a pipeline-written chunk ROOT file (tree "events", flat
    branches "Photons_pt" etc. -- see orchestration/handlers/
    parsing_handler.py's _save_chunk_to_root) back into a jagged awkward
    array with the same field structure FileParser itself produces."""
    return uproot.open(str(chunk_path))["events"].arrays(library="ak")


def process_one_chunk(chunk_path: Path, output_dir: Path, record_id, is_data: bool) -> dict:
    t0 = time.time()
    events = read_chunk(chunk_path)
    n_in = len(events)

    result = selection.select_diphoton_events(events)
    table = build_output_table(events, result, is_data=is_data, record_id=record_id)

    out_name = safe_output_filename(chunk_path.name)
    out_path = output_dir / out_name
    counts = write_event_output(table, out_path, is_data=is_data)

    elapsed = time.time() - t0

    cutflow = {
        "n_input_events_in_chunk": n_in,
        "n_with_ge2_tm_photons": int(ak.sum(result["has_pair"])),
        "n_selected": int(ak.sum(result["selected"])),
    }
    if not is_data and "genWeight" in events.fields:
        cutflow["sum_genWeight_input"] = float(ak.sum(events["genWeight"]))
        sel_w = ak.to_numpy(events["genWeight"])[ak.to_numpy(result["selected"])]
        cutflow["sum_genWeight_selected"] = float(sel_w.sum()) if len(sel_w) else 0.0

    return {
        "chunk": str(chunk_path),
        "output_normal": str(out_path),
        "n_written_normal": counts["n_written_normal"],
        "n_written_blinded": counts["n_written_blinded"],
        "cutflow": cutflow,
        "elapsed_sec": elapsed,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--chunks-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--record-id", required=False, type=int, default=None,
                    help="Fallback only -- normally read per event from the "
                         "chunk's own 'source_record' field.")
    p.add_argument("--is-data", required=True, choices=["true", "false"])
    p.add_argument("--config", required=True)
    args = p.parse_args()

    is_data = args.is_data == "true"
    chunks_dir = Path(args.chunks_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chunk_files = sorted(chunks_dir.glob("*.root"))
    if not chunk_files:
        print(f"WARNING: no chunk files found in {chunks_dir}", flush=True)

    per_chunk_results = []
    for chunk_path in chunk_files:
        print(f"processing {chunk_path.name} ...", flush=True)
        res = process_one_chunk(chunk_path, output_dir, args.record_id, is_data)
        per_chunk_results.append(res)
        print(json.dumps(res["cutflow"]), flush=True)

    total_cutflow = {
        "n_input_events": sum(r["cutflow"]["n_input_events_in_chunk"] for r in per_chunk_results),
        "n_with_ge2_tm_photons": sum(r["cutflow"]["n_with_ge2_tm_photons"] for r in per_chunk_results),
        "n_selected": sum(r["cutflow"]["n_selected"] for r in per_chunk_results),
        "n_written_normal": sum(r["n_written_normal"] for r in per_chunk_results),
        "n_written_blinded_signal_region": sum(r["n_written_blinded"] for r in per_chunk_results),
        "n_chunks_processed": len(per_chunk_results),
    }
    if not is_data:
        total_cutflow["sum_genWeight_input"] = sum(
            r["cutflow"].get("sum_genWeight_input", 0.0) for r in per_chunk_results
        )
        total_cutflow["sum_genWeight_selected"] = sum(
            r["cutflow"].get("sum_genWeight_selected", 0.0) for r in per_chunk_results
        )
        total_cutflow["dedup_removed_simulation_events"] = check_dedup_never_active(args.config)

    write_metadata(
        output_dir / "job_metadata.json",
        repo_root=REPO_ROOT,
        config_path=args.config,
        processed_files=[r["chunk"] for r in per_chunk_results],
        failed_files=[],
        cutflow=total_cutflow,
    )
    print(json.dumps(total_cutflow, indent=2))
    print(f"wrote {output_dir / 'job_metadata.json'}")


if __name__ == "__main__":
    main()
