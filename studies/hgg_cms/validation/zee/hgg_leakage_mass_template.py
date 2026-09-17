#!/usr/bin/env python
"""
Signal-model task, Part 0: electron-veto leakage MASS-SHAPE template.

RUNS ON THE CLUSTER (analysis node, `nice`, NOT a PBS job) against the
SAME already-parsed DY chunk files `hgg_leakage_estimate.py` reads --
same job discovery, same `read_chunk`, same photon-veto swap and
`studies.hgg_cms.selection.select_diphoton_events` call. It needs no new
CERN download, no re-parsing, and no `qsub`.

WHY THIS SCRIPT EXISTS (on top of the already-completed
`hgg_leakage_estimate.py`): that script gives four single-number yields
(100-105, 105-110, 110-115, 135-180 GeV) per category. A single
exponential fitted to those four numbers is a poor description -- see
VALIDATION_REPORT_2.md Part E's dated correction note -- because the
leaked DY population is actually (at least) two physical components: a
steep Z-tail component dominating close to the Z pole's low-mass edge,
and a flatter high-mass Drell-Yan-continuum component that dominates by
135-180 GeV. Trying to describe that with one exponential either
overshoots the 115-135 GeV extrapolation (fit dominated by the steep
part) or undershoots the measured 135-180 GeV yield (fit dominated by
the flat part) depending on which windows it is fit to -- there is no
single rate that is simultaneously right for both regimes.

The bias study that follows this signal-model task needs the ACTUAL
shape of that leakage under the blinded 115-135 GeV window, not a
guessed functional form. This script produces that: it runs the exact
same electronVeto-swapped H->gamma-gamma selection as
`compute_hgg_veto_leakage`, but instead of summing into four coarse
windows, it fills a fine (1 GeV) weighted histogram of the selected
diphoton mass over the full 100-180 GeV range, per category
(inclusive/EBEB/notEBEB), together with the sum-of-genWeight-squared in
each bin (for a per-bin statistical uncertainty). That histogram IS the
leakage template: normalized to this task's DY-based N_expected
estimate (already measured by `hgg_leakage_estimate.py`) with a +-50%
variation, it is what the next task's background-model bias study
should inject into its pseudo-data -- not a fitted exponential.

Bin choice: 1 GeV bins (80 bins over [100, 180]) -- fine enough to
capture the steep-vs-flat shape change near 105-115 GeV, coarse enough
that most bins still have a usable number of raw (unweighted) selected
DY events given the total leakage population is O(1000-4000) events
across the full range (see hgg_leakage_estimate_results.json's
n_selected_raw counts). This is a documented choice, not a validated
optimum -- if the bias study finds 1 GeV bins too coarse or too noisy
once it actually uses this template, it should feel free to rebin the
output histogram (it is a plain counts array plus bin edges, trivial to
rebin) rather than re-running this script.

Usage (paste this exact command onto the cluster):
    nice python studies/hgg_cms/validation/zee/hgg_leakage_mass_template.py \\
        --dy-jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_zee/dy_full \\
        --out /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/hgg_leakage_mass_template_results.json
Then copy just that one output JSON back to the laptop (HGG_ZEE_MERGED_DIR)
-- no need to copy the 41 job directories themselves. This was NOT run as
part of this task (no cluster access from here); it is provided ready to
run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import awkward as ak
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms import selection as hgg_selection  # noqa: E402  (REAL main-analysis selection -- template only, never applied to data here)
from studies.hgg_cms.cluster.run_selection_on_chunks import read_chunk  # noqa: E402
from studies.hgg_cms.validation.zee.hgg_leakage_estimate import discover_job_indices  # noqa: E402
from studies.hgg_cms.validation.zee import common as zc  # noqa: E402
from studies.hgg_cms.validation import common as main_common  # noqa: E402

CATS = ("inclusive", "EBEB", "notEBEB")
MASS_LO, MASS_HI, BIN_WIDTH = 100.0, 180.0, 1.0


def bin_edges() -> np.ndarray:
    n_bins = int(round((MASS_HI - MASS_LO) / BIN_WIDTH))
    return np.linspace(MASS_LO, MASS_HI, n_bins + 1)


def compute_leakage_mass_histogram(events: ak.Array, edges: np.ndarray) -> dict:
    """Same electronVeto-swap + `select_diphoton_events` call as
    `run_zee_selection_on_chunks.compute_hgg_veto_leakage` -- see that
    function's own docstring for why this is a faithful "what would the
    real H->gamma-gamma selection do to these DY events" estimate.
    Instead of four coarse window sums, fills a fine weighted mass
    histogram per category. Returns per-category dict of
    {"sum_genWeight": array, "sum_genWeight_sq": array, "n_selected_raw": array}
    each of length len(edges)-1, plus the same for "inclusive".
    """
    photons = events["Photons"]
    veto_true_photons = photons[photons.electronVeto]
    events_veto_true = ak.with_field(events, veto_true_photons, "Photons")
    result = hgg_selection.select_diphoton_events(events_veto_true)

    selected = ak.to_numpy(result["selected"])
    mgg = ak.to_numpy(ak.fill_none(result["mgg"], np.nan))
    cat = ak.to_numpy(result["category"])
    gw = ak.to_numpy(events["genWeight"])

    cat_masks = {
        "inclusive": np.ones(len(selected), dtype=bool),
        "EBEB": cat == "EBEB",
        "notEBEB": cat != "EBEB",
    }

    n_bins = len(edges) - 1
    out = {}
    for cat_label, cat_mask in cat_masks.items():
        mask = selected & cat_mask & np.isfinite(mgg)
        m = mgg[mask]
        w = gw[mask]
        sum_gw, _ = np.histogram(m, bins=edges, weights=w)
        sum_gw_sq, _ = np.histogram(m, bins=edges, weights=w ** 2)
        n_raw, _ = np.histogram(m, bins=edges)
        out[cat_label] = {
            "sum_genWeight": sum_gw.tolist(),
            "sum_genWeight_sq": sum_gw_sq.tolist(),
            "n_selected_raw": n_raw.astype(int).tolist(),
        }
    return out


def process_job(job_dir: Path, index: int, edges: np.ndarray) -> dict:
    chunks_dir = job_dir / "parsed_data"
    chunk_files = sorted(chunks_dir.glob("*.root")) if chunks_dir.exists() else []
    n_bins = len(edges) - 1
    totals = {c: {"sum_genWeight": np.zeros(n_bins), "sum_genWeight_sq": np.zeros(n_bins),
                   "n_selected_raw": np.zeros(n_bins, dtype=int)} for c in CATS}
    n_chunks_with_genweight = 0
    for chunk_path in chunk_files:
        events = read_chunk(chunk_path)
        if "genWeight" not in events.fields:
            continue
        n_chunks_with_genweight += 1
        hist = compute_leakage_mass_histogram(events, edges)
        for c in CATS:
            totals[c]["sum_genWeight"] += np.asarray(hist[c]["sum_genWeight"])
            totals[c]["sum_genWeight_sq"] += np.asarray(hist[c]["sum_genWeight_sq"])
            totals[c]["n_selected_raw"] += np.asarray(hist[c]["n_selected_raw"])

    genEventSumw = None
    stats_path = job_dir / "logs" / f"parsing_stats_batch_{index}.json"
    if stats_path.exists():
        try:
            stats = json.loads(stats_path.read_text(encoding="utf-8"))
            sw = (stats.get("sumw_by_record") or {}).get("record_35669")
            if sw is not None:
                genEventSumw = sw.get("genEventSumw")
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "n_chunks_found": len(chunk_files),
        "n_chunks_with_genweight": n_chunks_with_genweight,
        "totals": totals,
        "genEventSumw": genEventSumw,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dy-jobs-base", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    jobs_base = Path(args.dy_jobs_base)
    indices = discover_job_indices(jobs_base)
    if not indices:
        raise SystemExit(f"no job_<i> directories found under {jobs_base}")

    edges = bin_edges()
    n_bins = len(edges) - 1
    grand_totals = {c: {"sum_genWeight": np.zeros(n_bins), "sum_genWeight_sq": np.zeros(n_bins),
                         "n_selected_raw": np.zeros(n_bins, dtype=int)} for c in CATS}
    total_genEventSumw = 0.0
    missing_chunks_jobs, missing_sumw_jobs = [], []

    for i in indices:
        job_dir = jobs_base / f"job_{i}"
        print(f"processing job_{i} ...", flush=True)
        res = process_job(job_dir, i, edges)
        if res["n_chunks_found"] == 0:
            missing_chunks_jobs.append(i)
        for c in CATS:
            grand_totals[c]["sum_genWeight"] += res["totals"][c]["sum_genWeight"]
            grand_totals[c]["sum_genWeight_sq"] += res["totals"][c]["sum_genWeight_sq"]
            grand_totals[c]["n_selected_raw"] += res["totals"][c]["n_selected_raw"]
        if res["genEventSumw"] is None:
            missing_sumw_jobs.append(i)
        else:
            total_genEventSumw += res["genEventSumw"]
        print(f"  chunks={res['n_chunks_found']} genEventSumw={res['genEventSumw']}", flush=True)

    scale = None
    normalized = {}
    if total_genEventSumw > 0:
        scale = zc.DY_CROSS_SECTION_PB * 1000.0 * main_common.LUMI_FB / total_genEventSumw
        for c in CATS:
            N_expected_per_bin = (scale * grand_totals[c]["sum_genWeight"]).tolist()
            stat_unc_per_bin = (scale * np.sqrt(grand_totals[c]["sum_genWeight_sq"])).tolist()
            normalized[c] = {
                "N_expected_per_bin": N_expected_per_bin,
                "statistical_uncertainty_per_bin": stat_unc_per_bin,
                "n_selected_raw_per_bin": grand_totals[c]["n_selected_raw"].tolist(),
                "N_expected_total": float(np.sum(N_expected_per_bin)),
            }

    result = {
        "bin_edges_GeV": edges.tolist(),
        "bin_width_GeV": BIN_WIDTH,
        "mass_range_GeV": [MASS_LO, MASS_HI],
        "dy_cross_section_pb": zc.DY_CROSS_SECTION_PB,
        "luminosity_fb": main_common.LUMI_FB,
        "normalization_formula": (
            "N_expected_per_bin = DY_CROSS_SECTION_PB * 1000 (pb->fb) * L_fb * "
            "(Sum genWeight_selected_in_bin_and_category / "
            "Sum genEventSumw_over_processed_DY_files); statistical "
            "uncertainty_per_bin = same scale * sqrt(Sum genWeight^2 in bin) "
            "(correct for signed weights, since squaring removes the sign)."
        ),
        "n_jobs_processed": len(indices),
        "missing_chunks_jobs": missing_chunks_jobs,
        "missing_sumw_jobs": missing_sumw_jobs,
        "total_genEventSumw_dy_processed": total_genEventSumw,
        "template_by_category": normalized,
        "note": (
            "This is the leakage MASS-SHAPE template (fine 1 GeV binning), "
            "for the background-model bias study's pseudo-data component -- "
            "use the actual per-bin N_expected shape here, normalized with "
            "a +-50% variation, NOT a fitted exponential (see "
            "VALIDATION_REPORT_2.md Part E's dated correction note for why "
            "a single exponential is a poor description of this shape)."
        ),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
