#!/usr/bin/env python
"""
Implementation task 6, Part 4: analysis-layer driver for one Z->e+e-
control-region cluster job. Run AFTER the shared pipeline's parsing stage
(main.py --tasks parsing) has written its chunk ROOT files to
--chunks-dir. Mirrors studies/hgg_cms/cluster/run_selection_on_chunks.py's
structure exactly (same chunk-reading, same one-output-per-chunk pattern),
but applies studies.hgg_cms.zee_selection instead, with NO blinding split
(studies.hgg_cms.zee_output).

Also implements this task's Part 1 fact-5 improvement for these NEW jobs
(not retroactive on the already-completed H->gamma-gamma full run): logs
the exact CERN input file URL(s) this job actually fetched, read directly
from THIS job's own metadata_cache.json (--metadata-cache-json), into
job_metadata.json's "cern_input_files" key -- computed here the SAME way
merge_outputs.py's data-mode identity check reconstructs it (via
utils.batching.get_batch_slice_by_year, when --batch-job-index/
--total-batch-jobs are given, for the data array job), or the full
per-record file list straight from metadata_cache.json otherwise (the DY
job, which -- like the H->gamma-gamma signal jobs -- has no batching at
all: one job, every file in the record).

Usage (main Z->ee sample, data array job):
    python run_zee_selection_on_chunks.py \
        --chunks-dir /storage/.../parsed_data --output-dir /storage/.../selected \
        --is-data true --config config.cms_hgg_zee_data.yaml \
        --metadata-cache-json /storage/.../metadata_cache.json \
        --batch-job-index 7 --total-batch-jobs 133 \
        --mass-lo 70 --mass-hi 110

Usage (trigger-efficiency sample, records the diphoton HLT bit but does
NOT filter on it -- see config.cms_hgg_zee_trigeff_*.yaml, which requests
it via extra_scalar_branches, not trigger_requirements):
    python run_zee_selection_on_chunks.py \
        --chunks-dir ... --output-dir ... --is-data true \
        --config config.cms_hgg_zee_trigeff_data.yaml \
        --metadata-cache-json ... \
        --mass-lo 95 \
        --record-diphoton-trigger-bit HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90
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
import numpy as np  # noqa: E402

from studies.hgg_cms import zee_selection  # noqa: E402
from studies.hgg_cms.cluster.run_selection_on_chunks import read_chunk  # noqa: E402
from studies.hgg_cms.zee_output import (  # noqa: E402
    build_zee_output_table, write_zee_event_output, write_metadata,
)
from utils.batching import get_batch_slice_by_year  # noqa: E402
import yaml  # noqa: E402


def resolve_cern_input_files(metadata_cache_json: str, batch_job_index, total_batch_jobs) -> list:
    """Reads THIS job's own metadata_cache.json and returns the exact URL
    list it corresponds to: the single sliced file for a batched (array)
    job, or the full per-record file list for an unbatched (one-job,
    every-file) job. Never falls back to job_metadata.json's own
    "input_files_processed" (the intermediate parsed-chunk path -- see
    this module's own docstring)."""
    cache = json.loads(Path(metadata_cache_json).read_text(encoding="utf-8"))
    if batch_job_index is not None and total_batch_jobs is not None:
        sliced = get_batch_slice_by_year(cache, int(batch_job_index), int(total_batch_jobs))
        return [u for urls in sliced.values() for u in urls]
    return [u for urls in cache.values() for u in urls]


def check_dedup_never_active(config_path: str) -> int:
    """Same guarantee as run_selection_on_chunks.py's own check (verbatim
    reasoning -- neither the main H->gamma-gamma configs nor these Z->ee
    configs ever set selection_by_record)."""
    from domain.config import PipelineConfig
    raw = yaml.safe_load(open(config_path, encoding="utf-8"))
    cfg = PipelineConfig.from_dict(raw)
    sel_by_record = cfg.parsing_config.selection_by_record
    if sel_by_record is not None:
        raise RuntimeError(
            f"config {config_path} sets selection_by_record={sel_by_record!r} -- "
            f"de-duplication WOULD be active; this driver only certifies '0 "
            f"simulation events removed by dedup' for configs where dedup "
            f"never turns on at all."
        )
    return 0


def process_one_chunk(chunk_path: Path, output_dir: Path, record_id, is_data: bool,
                       mass_lo: float, mass_hi, diphoton_trigger_branch: str = None) -> dict:
    t0 = time.time()
    events = read_chunk(chunk_path)
    n_in = len(events)

    result = zee_selection.select_zee_events(events, mass_lo=mass_lo, mass_hi=mass_hi)

    extra_scalar_fields = None
    if diphoton_trigger_branch is not None:
        if diphoton_trigger_branch not in events.fields:
            raise ValueError(
                f"--record-diphoton-trigger-bit {diphoton_trigger_branch!r} not found "
                f"among parsed fields {events.fields} -- check the config's "
                f"extra_scalar_branches includes it."
            )
        bit = ak.to_numpy(events[diphoton_trigger_branch]).astype(bool)[ak.to_numpy(result["selected"])]
        extra_scalar_fields = {"passes_diphoton_hlt": ak.Array(bit)}

    table = build_zee_output_table(events, result, is_data=is_data, record_id=record_id,
                                    extra_scalar_fields=extra_scalar_fields)

    out_name = chunk_path.stem.replace(" ", "_").replace("+", "plus").replace("=", "_") + ".root"
    out_path = output_dir / out_name
    n_written = write_zee_event_output(table, out_path)

    elapsed = time.time() - t0

    cutflow = {
        "n_input_events_in_chunk": n_in,
        "n_with_ge2_tm_photons": int(ak.sum(result["has_pair"])),
        "n_selected": int(ak.sum(result["selected"])),
        "n_written": n_written,
    }
    if not is_data and "genWeight" in events.fields:
        cutflow["sum_genWeight_input"] = float(ak.sum(events["genWeight"]))
        sel_w = ak.to_numpy(events["genWeight"])[ak.to_numpy(result["selected"])]
        cutflow["sum_genWeight_selected"] = float(sel_w.sum()) if len(sel_w) else 0.0

    return {
        "chunk": str(chunk_path), "output": str(out_path),
        "n_written": n_written, "cutflow": cutflow, "elapsed_sec": elapsed,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--chunks-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--record-id", required=False, type=int, default=None)
    p.add_argument("--is-data", required=True, choices=["true", "false"])
    p.add_argument("--config", required=True)
    p.add_argument("--mass-lo", type=float, default=zee_selection.DEFAULT_MASS_LO)
    p.add_argument("--mass-hi", type=float, default=zee_selection.DEFAULT_MASS_HI,
                    help="Pass a very large number (e.g. 1e6) for 'no upper bound' "
                         "(the trigger-efficiency sample's '>~95 GeV' window).")
    p.add_argument("--metadata-cache-json", required=True,
                    help="This job's own metadata_cache.json -- used to log "
                         "cern_input_files (Part 1 fact-5 improvement).")
    p.add_argument("--batch-job-index", type=int, default=None)
    p.add_argument("--total-batch-jobs", type=int, default=None)
    p.add_argument("--record-diphoton-trigger-bit", default=None,
                    help="If given, that branch (already attached via the "
                         "config's extra_scalar_branches, NOT filtered on) "
                         "is recorded per selected event as "
                         "'passes_diphoton_hlt' -- the trigger-efficiency "
                         "sample's use case.")
    args = p.parse_args()

    is_data = args.is_data == "true"
    chunks_dir = Path(args.chunks_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    mass_hi = None if args.mass_hi >= 1e5 else args.mass_hi

    chunk_files = sorted(chunks_dir.glob("*.root"))
    if not chunk_files:
        print(f"WARNING: no chunk files found in {chunks_dir}", flush=True)

    per_chunk_results = []
    for chunk_path in chunk_files:
        print(f"processing {chunk_path.name} ...", flush=True)
        res = process_one_chunk(
            chunk_path, output_dir, args.record_id, is_data,
            mass_lo=args.mass_lo, mass_hi=mass_hi,
            diphoton_trigger_branch=args.record_diphoton_trigger_bit,
        )
        per_chunk_results.append(res)
        print(json.dumps(res["cutflow"]), flush=True)

    total_cutflow = {
        "n_input_events": sum(r["cutflow"]["n_input_events_in_chunk"] for r in per_chunk_results),
        "n_with_ge2_tm_photons": sum(r["cutflow"]["n_with_ge2_tm_photons"] for r in per_chunk_results),
        "n_selected": sum(r["cutflow"]["n_selected"] for r in per_chunk_results),
        "n_written": sum(r["cutflow"]["n_written"] for r in per_chunk_results),
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

    cern_input_files = resolve_cern_input_files(
        args.metadata_cache_json, args.batch_job_index, args.total_batch_jobs
    )

    write_metadata(
        output_dir / "job_metadata.json",
        repo_root=REPO_ROOT,
        config_path=args.config,
        processed_files=[r["chunk"] for r in per_chunk_results],
        failed_files=[],
        cutflow=total_cutflow,
        cern_input_files=cern_input_files,
    )
    print(json.dumps(total_cutflow, indent=2))
    print(f"cern_input_files ({len(cern_input_files)}): {cern_input_files}")
    print(f"wrote {output_dir / 'job_metadata.json'}")


if __name__ == "__main__":
    main()
