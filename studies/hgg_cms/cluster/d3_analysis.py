#!/usr/bin/env python
"""
Implementation task 6, Part D3: full-file analysis, run AFTER
run_selection_on_chunks.py has already produced this run's per-event
output (+ job_metadata.json) under --run-dir/selected/. Runs entirely on
already-produced LOCAL output -- no remote reads here.

Two modes:

  --mode data: run on the one full DoubleEG Run2016G file. Produces:
    - the cutflow (from job_metadata.json)
    - a sideband-ONLY m_gg plot (100-115 and 135-180 GeV); the blinded
      115-135 GeV window is drawn as a visibly empty, labeled gray band --
      never filled with data, since read_output() on the NORMAL file
      cannot contain a blinded-window event in the first place (asserted
      by output.read_output itself)
    - the blinded-window COUNT ONLY (never individual masses -- read via
      unblind=True purely to call len(), the mass column is never
      inspected or printed)

  --mode signal: run on the one full ggH file. Produces:
    - the cutflow (from job_metadata.json), including sum_genWeight
      input/selected and "dedup_removed_simulation_events"
    - signal efficiency, weighted (sum_genWeight_selected /
      sum_genWeight_input) and unweighted (n_selected / n_input_events)
    - mode / median / effective sigma_68 of m_gg, inclusive and per
      category (EBEB / notEBEB), via the SAME functions
      (studies.hgg_cms.physics_checks.common) used for check_b -- so
      task 6's own D2 comparison and this D3 report use identical shape
      math
    - a fine-bin m_gg plot (signal is never blinded)
    - a "preview expected ggH yield" for JUST this one processed file:
        sigma(ggH) * BR(H->gg) * L * (sum_genWeight_selected /
        genEventSumw_of_this_one_file)
      genEventSumw_of_this_one_file is read from THIS run's own
      <run-dir>/logs/parsing_stats*.json ("sumw_by_record" -- the
      shared pipeline's own Part-A-fixed aggregation), not recomputed
      here, and not read_event_weights-of-the-full-record cross section
      table (which would be for a different, larger file set). sigma and
      BR come from studies/hgg_cms/impl_checks/signal_sumw.json (the
      single already-established source of truth for those two numbers)
      -- never hardcoded here.
      LABELED EXPLICITLY as a single-file preview -- NOT the full-record
      expected yield (that needs every file of the record processed and
      merged; see studies/hgg_cms/cluster/merge_outputs.py).

Both modes also record: wall-clock time for THIS analysis step, and the
output file size(s) on disk. Total pipeline wall time / peak memory are
measured by the calling PBS script wrapping the whole
parsing+selection+analysis chain in `/usr/bin/time -v` -- see
pbs_hgg_d3_data.sh / pbs_hgg_d3_signal.sh.

BLINDING: this script never prints, plots, or histograms an individual
data m_gg value in [115, 135]. Only a count crosses that line.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import matplotlib

matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from studies.hgg_cms.output import BLINDED_MARKER, read_output  # noqa: E402
from studies.hgg_cms.physics_checks.common import (  # noqa: E402
    effective_sigma_68,
    histogram_mode,
)

SIGNAL_SUMW_JSON = REPO_ROOT / "studies" / "hgg_cms" / "impl_checks" / "signal_sumw.json"
LUMINOSITY_FB = 16.393  # Run2016 legacy dataset total, as fixed by this task's spec


def _find_job_metadata(run_dir: Path) -> dict:
    path = run_dir / "selected" / "job_metadata.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found -- run run_selection_on_chunks.py against "
            f"{run_dir}/parsed_data first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _find_parsing_stats(run_dir: Path) -> dict | None:
    """The shared pipeline's own genEventSumw aggregation (implementation
    task 5, Part A) -- see orchestration/handlers/parsing_handler.py's
    `sumw_by_record` / pipeline/executor.py's save_stage_stats(). None for
    data (never enabled -- data configs don't set read_event_weights)."""
    candidates = sorted(glob.glob(str(run_dir / "logs" / "parsing_stats*.json")))
    if not candidates:
        return None
    return json.loads(Path(candidates[-1]).read_text(encoding="utf-8"))


def _output_file_sizes(run_dir: Path) -> dict:
    sizes = {}
    for p in sorted((run_dir / "selected").glob("*.root")):
        sizes[p.name] = p.stat().st_size
    return sizes


def analyze_data(run_dir: Path, out_json: Path, out_plot: Path) -> dict:
    t0 = time.time()
    metadata = _find_job_metadata(run_dir)
    cutflow = metadata["cutflow"]

    normal_paths = [
        p for p in sorted((run_dir / "selected").glob("*.root"))
        if BLINDED_MARKER not in p.name
    ]
    blinded_paths = [
        p for p in sorted((run_dir / "selected").glob("*.root"))
        if BLINDED_MARKER in p.name
    ]

    sideband_mgg = []
    for p in normal_paths:
        table = read_output(p)  # unblind=False (default) -- asserts no [115,135] content
        if len(table) > 0:
            sideband_mgg.append(ak.to_numpy(table["m_gg"]))
    sideband_mgg = np.concatenate(sideband_mgg) if sideband_mgg else np.array([])

    n_blinded_count_only = 0
    for p in blinded_paths:
        table = read_output(p, unblind=True)  # count only -- masses never inspected below
        n_blinded_count_only += len(table)

    # ---- sideband-only plot: fine bins in [100,115] and [135,180], the
    # [115,135] window drawn as an empty, clearly labeled gray band ----
    fig, ax = plt.subplots(figsize=(7, 5))
    bin_width = 1.0
    bins_lo = np.arange(100.0, 115.0 + bin_width, bin_width)
    bins_hi = np.arange(135.0, 180.0 + bin_width, bin_width)
    lo_vals = sideband_mgg[(sideband_mgg >= 100.0) & (sideband_mgg < 115.0)]
    hi_vals = sideband_mgg[(sideband_mgg > 135.0) & (sideband_mgg <= 180.0)]
    ax.hist(lo_vals, bins=bins_lo, histtype="step", color="k")
    ax.hist(hi_vals, bins=bins_hi, histtype="step", color="k")
    ax.axvspan(115.0, 135.0, color="0.85", label=f"BLINDED (count only: {n_blinded_count_only})")
    ax.set_xlabel("m_gg [GeV]")
    ax.set_ylabel("events / GeV")
    ax.set_title("DoubleEG Run2016G, full file -- sideband only (D3)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_plot, dpi=150)
    plt.close(fig)

    result = {
        "mode": "data",
        "cutflow": cutflow,
        "n_sideband_events_plotted": int(len(sideband_mgg)),
        "n_blinded_115_135_count_only": int(n_blinded_count_only),
        "output_file_sizes_bytes": _output_file_sizes(run_dir),
        "plot_path": str(out_plot),
        "analysis_step_elapsed_sec": time.time() - t0,
    }
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def analyze_signal(run_dir: Path, out_json: Path, out_plot: Path) -> dict:
    t0 = time.time()
    metadata = _find_job_metadata(run_dir)
    cutflow = metadata["cutflow"]

    normal_paths = sorted((run_dir / "selected").glob("*.root"))
    if any(BLINDED_MARKER in p.name for p in normal_paths):
        raise AssertionError("simulation output must never be blinding-split")

    tables = [read_output(p) for p in normal_paths]
    table = ak.concatenate(tables) if len(tables) > 1 else (tables[0] if tables else None)

    n_input = cutflow["n_input_events_in_chunk"] if "n_input_events_in_chunk" in cutflow else cutflow.get("n_input_events")
    n_selected = cutflow["n_selected"]
    sum_gw_in = cutflow.get("sum_genWeight_input", 0.0)
    sum_gw_sel = cutflow.get("sum_genWeight_selected", 0.0)

    efficiency_unweighted = (n_selected / n_input) if n_input else None
    efficiency_weighted = (sum_gw_sel / sum_gw_in) if sum_gw_in else None

    def _shape(mgg_arr):
        if len(mgg_arr) == 0:
            return None
        return {
            "n": int(len(mgg_arr)),
            "mean": float(np.mean(mgg_arr)),
            "median": float(np.median(mgg_arr)),
            "mode": histogram_mode(mgg_arr, bin_width=0.5, lo=100, hi=180),
            "effective_sigma68": effective_sigma_68(mgg_arr),
        }

    shapes = {}
    if table is not None and len(table) > 0:
        mgg_all = ak.to_numpy(table["m_gg"])
        cat_all = ak.to_list(table["category"])
        cat_np = np.array(cat_all)
        shapes["inclusive"] = _shape(mgg_all)
        shapes["EBEB"] = _shape(mgg_all[cat_np == "EBEB"])
        shapes["notEBEB"] = _shape(mgg_all[cat_np == "notEBEB"])

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.hist(mgg_all, bins=np.arange(100.0, 180.5, 0.5), histtype="step", color="k", label="inclusive")
        ax.hist(mgg_all[cat_np == "EBEB"], bins=np.arange(100.0, 180.5, 0.5), histtype="step", color="C0", label="EBEB")
        ax.hist(mgg_all[cat_np == "notEBEB"], bins=np.arange(100.0, 180.5, 0.5), histtype="step", color="C1", label="notEBEB")
        ax.set_xlabel("m_gg [GeV]")
        ax.set_ylabel("events / 0.5 GeV")
        ax.set_title("ggH, full file -- fine-bin m_gg (D3, unblinded, simulation)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_plot, dpi=150)
        plt.close(fig)
    else:
        shapes = {"inclusive": None, "EBEB": None, "notEBEB": None}

    # ---- preview expected yield for THIS ONE FILE ONLY ----
    sumw_info = _find_parsing_stats(run_dir)
    genEventSumw_this_file = None
    if sumw_info and sumw_info.get("sumw_by_record"):
        # exactly one record key expected for a single-record, single-file D3 run
        (_, sumw_entry), = sumw_info["sumw_by_record"].items()
        genEventSumw_this_file = sumw_entry["genEventSumw"]

    signal_meta = json.loads(SIGNAL_SUMW_JSON.read_text(encoding="utf-8"))["records"]["37350"]
    cross_section_pb = signal_meta["cross_section_pb"]
    br = signal_meta["branching_ratio_Hgammagamma"]

    preview_yield = None
    if genEventSumw_this_file:
        preview_yield = (
            cross_section_pb * 1000.0  # pb -> fb
            * br
            * LUMINOSITY_FB
            * (sum_gw_sel / genEventSumw_this_file)
        )

    result = {
        "mode": "signal",
        "cutflow": cutflow,
        "efficiency_unweighted": efficiency_unweighted,
        "efficiency_weighted": efficiency_weighted,
        "shape": shapes,
        "genEventSumw_this_processed_file": genEventSumw_this_file,
        "cross_section_pb_ggH": cross_section_pb,
        "branching_ratio_Hgammagamma": br,
        "luminosity_fb_used": LUMINOSITY_FB,
        "preview_expected_ggH_yield_SINGLE_FILE_ONLY": preview_yield,
        "preview_yield_caveat": (
            "This is NOT the full-record expected ggH yield -- it uses "
            "genEventSumw from only the one file processed in this D3 "
            "run, not the full record's genEventSumw "
            f"({signal_meta['sum_genEventSumw_all_files']:.6g} over "
            f"{signal_meta['n_files']} files). See merge_outputs.py for "
            "the full-record computation once all files are processed."
        ),
        "output_file_sizes_bytes": _output_file_sizes(run_dir),
        "plot_path": str(out_plot) if table is not None and len(table) > 0 else None,
        "analysis_step_elapsed_sec": time.time() - t0,
    }
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", required=True, choices=["data", "signal"])
    p.add_argument("--run-dir", required=True)
    args = p.parse_args()

    run_dir = Path(args.run_dir)
    out_json = run_dir / f"d3_{args.mode}_report.json"
    out_plot = run_dir / f"d3_{args.mode}_mgg_plot.png"

    if args.mode == "data":
        result = analyze_data(run_dir, out_json, out_plot)
    else:
        result = analyze_signal(run_dir, out_json, out_plot)

    print(json.dumps(result, indent=2, default=str))
    print(f"wrote {out_json}")


if __name__ == "__main__":
    main()
