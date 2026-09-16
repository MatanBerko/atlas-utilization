#!/usr/bin/env python
"""
Implementation task 6, Part 4 (REVISED 16 Sep 2026): analysis-layer driver
for one Z->e+e- control-region cluster job. Run AFTER the shared
pipeline's parsing stage (main.py --tasks parsing) has written its chunk
ROOT files to --chunks-dir. Mirrors
studies/hgg_cms/cluster/run_selection_on_chunks.py's structure (same
chunk-reading, same one-output-per-chunk pattern), but applies
studies.hgg_cms.zee_selection instead, with NO blinding split
(studies.hgg_cms.zee_output).

ONE run variant per dataset now (data, DY) -- not four. Both configs
(config.cms_hgg_zee_data.yaml / config.cms_hgg_zee_dy.yaml) filter on
EITHER HLT_Ele27_WPTight_Gsf or the diphoton trigger firing (the earlier
diphoton-trigger-only design biased the peak-position/width comparison
via the online Mass90 cut sculpting the Z peak -- see zee_selection.py's
own module docstring for the full reasoning) and store BOTH trigger bits
per selected event; offline analysis (studies/hgg_cms/validation/zee/)
then carves out the energy-scale, trigger-efficiency, and Mass90
-sculpting-demonstration sub-samples from this ONE stored 60-180 GeV
table -- no separate "trigger-efficiency" cluster job variant anymore.

For DY (--is-data false) ONLY, this driver ALSO computes a completely
SEPARATE quantity in the same pass over the same already-in-memory chunk:
how many DY events would pass the REAL, UNMODIFIED main H->gamma-gamma
selection (studies.hgg_cms.selection, electronVeto REQUIRED True) in the
100-105 and 105-115 GeV windows -- the "electron-veto leakage" estimate
for Part B's flagged low-edge excess (see compute_hgg_veto_leakage()).
This reuses the SAME already-fetched, already-parsed chunk a second time
in-memory (electronVeto is available on every photon regardless of its
value, since config.cms_hgg_zee_dy.yaml deliberately omits electronVeto
from parsing-level bool_require) rather than submitting a second cluster
job that would re-read the same 41 files again for no benefit -- see
ZEE_RUN_README.md's "why one pass, not a second job" section for the
full justification the task asked for.

Also implements this task's Part 1 fact-5 improvement for these NEW jobs
(not retroactive on the already-completed H->gamma-gamma full run): logs
the exact CERN input file URL(s) this job actually fetched, read directly
from THIS job's own metadata_cache.json (--metadata-cache-json), into
job_metadata.json's "cern_input_files" key.

Usage:
    python run_zee_selection_on_chunks.py \
        --chunks-dir /storage/.../parsed_data --output-dir /storage/.../selected \
        --is-data true --config config.cms_hgg_zee_data.yaml \
        --metadata-cache-json /storage/.../metadata_cache.json \
        --batch-job-index 7 --total-batch-jobs 133
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

from studies.hgg_cms import selection as hgg_selection  # noqa: E402  (REAL main-analysis selection -- leakage estimate only)
from studies.hgg_cms import zee_selection  # noqa: E402
from studies.hgg_cms.cluster.run_selection_on_chunks import read_chunk  # noqa: E402
from studies.hgg_cms.zee_output import (  # noqa: E402
    build_zee_output_table, write_zee_event_output, write_metadata,
)
from utils.batching import get_batch_slice_by_year  # noqa: E402
import yaml  # noqa: E402

# Both trigger bits are always attached (both are listed in
# trigger_requirements.paths in both configs) -- recorded per selected
# event under these output field names.
TRIGGER_BIT_OUTPUT_FIELDS = {
    "HLT_Ele27_WPTight_Gsf": "passes_ele27_hlt",
    "HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90": "passes_diphoton_hlt",
}

# Part B's flagged low-edge excess windows -- see
# studies/hgg_cms/validation/zee/hgg_leakage_estimate.py, which sums
# these across all 41 DY jobs and normalizes to an expected event count.
LEAKAGE_WINDOWS = {"100_105": (100.0, 105.0), "105_115": (105.0, 115.0)}


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


def compute_hgg_veto_leakage(events: ak.Array) -> dict:
    """DY-only: how many events would pass the REAL, unmodified main
    H->gamma-gamma selection (electronVeto REQUIRED True -- the OPPOSITE
    subset from this job's own Z->ee output) in the two windows Part B
    flagged. Builds a photon collection restricted to electronVeto==True
    (available because config.cms_hgg_zee_dy.yaml, like the data config,
    deliberately does NOT filter on electronVeto at parsing time), swaps
    it in for "Photons" via ak.with_field, and calls
    studies.hgg_cms.selection.select_diphoton_events UNMODIFIED -- the
    exact same function (same TM cuts, same scaled-pT cuts, same 100-180
    GeV window) the real production H->gamma-gamma signal jobs call, so
    this is a faithful "what would the real selection do to these DY
    events" estimate, not a re-derived approximation.

    Requires "genWeight" on `events` (DY only -- never called for data).
    """
    photons = events["Photons"]
    veto_true_photons = photons[photons.electronVeto]
    events_veto_true = ak.with_field(events, veto_true_photons, "Photons")
    result = hgg_selection.select_diphoton_events(events_veto_true)

    selected = ak.to_numpy(result["selected"])
    mgg = ak.to_numpy(ak.fill_none(result["mgg"], np.nan))
    gw = ak.to_numpy(events["genWeight"])

    out = {}
    for label, (lo, hi) in LEAKAGE_WINDOWS.items():
        mask = selected & (mgg >= lo) & (mgg < hi)
        out[f"n_selected_{label}"] = int(mask.sum())
        out[f"sum_genWeight_{label}"] = float(gw[mask].sum()) if mask.any() else 0.0
    return out


def process_one_chunk(chunk_path: Path, output_dir: Path, record_id, is_data: bool,
                       mass_lo: float, mass_hi) -> dict:
    t0 = time.time()
    events = read_chunk(chunk_path)
    n_in = len(events)

    result = zee_selection.select_zee_events(events, mass_lo=mass_lo, mass_hi=mass_hi)

    selected_np = ak.to_numpy(result["selected"])
    extra_scalar_fields = {}
    for branch, out_field in TRIGGER_BIT_OUTPUT_FIELDS.items():
        if branch not in events.fields:
            raise ValueError(
                f"expected trigger branch {branch!r} not found among parsed "
                f"fields {events.fields} -- check the config's "
                f"trigger_requirements.paths includes it."
            )
        bit = ak.to_numpy(events[branch]).astype(bool)[selected_np]
        extra_scalar_fields[out_field] = ak.Array(bit)

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
    leakage = None
    if not is_data and "genWeight" in events.fields:
        cutflow["sum_genWeight_input"] = float(ak.sum(events["genWeight"]))
        sel_w = ak.to_numpy(events["genWeight"])[selected_np]
        cutflow["sum_genWeight_selected"] = float(sel_w.sum()) if len(sel_w) else 0.0
        leakage = compute_hgg_veto_leakage(events)

    return {
        "chunk": str(chunk_path), "output": str(out_path),
        "n_written": n_written, "cutflow": cutflow, "elapsed_sec": elapsed,
        "hgg_veto_leakage": leakage,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--chunks-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--record-id", required=False, type=int, default=None)
    p.add_argument("--is-data", required=True, choices=["true", "false"])
    p.add_argument("--config", required=True)
    p.add_argument("--mass-lo", type=float, default=zee_selection.DEFAULT_MASS_LO)
    p.add_argument("--mass-hi", type=float, default=zee_selection.DEFAULT_MASS_HI)
    p.add_argument("--metadata-cache-json", required=True,
                    help="This job's own metadata_cache.json -- used to log "
                         "cern_input_files (Part 1 fact-5 improvement).")
    p.add_argument("--batch-job-index", type=int, default=None)
    p.add_argument("--total-batch-jobs", type=int, default=None)
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
        res = process_one_chunk(
            chunk_path, output_dir, args.record_id, is_data,
            mass_lo=args.mass_lo, mass_hi=args.mass_hi,
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
    hgg_veto_leakage_total = None
    if not is_data:
        total_cutflow["sum_genWeight_input"] = sum(
            r["cutflow"].get("sum_genWeight_input", 0.0) for r in per_chunk_results
        )
        total_cutflow["sum_genWeight_selected"] = sum(
            r["cutflow"].get("sum_genWeight_selected", 0.0) for r in per_chunk_results
        )
        total_cutflow["dedup_removed_simulation_events"] = check_dedup_never_active(args.config)

        hgg_veto_leakage_total = {}
        for label in LEAKAGE_WINDOWS:
            hgg_veto_leakage_total[f"n_selected_{label}"] = sum(
                (r["hgg_veto_leakage"] or {}).get(f"n_selected_{label}", 0) for r in per_chunk_results
            )
            hgg_veto_leakage_total[f"sum_genWeight_{label}"] = sum(
                (r["hgg_veto_leakage"] or {}).get(f"sum_genWeight_{label}", 0.0) for r in per_chunk_results
            )

    cern_input_files = resolve_cern_input_files(
        args.metadata_cache_json, args.batch_job_index, args.total_batch_jobs
    )

    metadata_kwargs = dict(
        repo_root=REPO_ROOT,
        config_path=args.config,
        processed_files=[r["chunk"] for r in per_chunk_results],
        failed_files=[],
        cutflow=total_cutflow,
        cern_input_files=cern_input_files,
    )
    write_metadata(output_dir / "job_metadata.json", **metadata_kwargs)

    if hgg_veto_leakage_total is not None:
        # Written into the SAME metadata file, as an additional top-level
        # key -- write_metadata doesn't know about this key, so add it
        # directly and re-save (small file, negligible cost).
        meta_path = output_dir / "job_metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["hgg_veto_leakage_estimate"] = hgg_veto_leakage_total
        meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

    print(json.dumps(total_cutflow, indent=2))
    if hgg_veto_leakage_total is not None:
        print(f"hgg_veto_leakage_estimate: {json.dumps(hgg_veto_leakage_total, indent=2)}")
    print(f"cern_input_files ({len(cern_input_files)}): {cern_input_files}")
    print(f"wrote {output_dir / 'job_metadata.json'}")


if __name__ == "__main__":
    main()
