"""
Implementation task 6, Part 4, item 3: electron-veto leakage estimate for
Part B's flagged low-edge excess.

Sums, ACROSS ALL 41 DY job directories, the per-job
"hgg_veto_leakage_estimate" that run_zee_selection_on_chunks.py computes
in the same pass as the Z->ee selection (electronVeto REQUIRED True,
i.e. the OPPOSITE subset from the Z->ee sample itself, run through the
REAL, unmodified main H->gamma-gamma selection.select_diphoton_events) --
see that script's own module docstring for why this is one pass, not a
separate DY-only job.

N_expected = DY_CROSS_SECTION_PB * 1000 (pb->fb) * L_fb *
             (sum_genWeight_selected_in_window / genEventSumw_over_processed_DY_files)

No branching-ratio factor (unlike the H->gamma-gamma signal normalization
formula) -- DYJetsToLL_M-50 IS the full leptonic-decay process already;
there is no further decay branching to apply.

Requires the DY run's own per-job logs/parsing_stats_batch_<i>.json
(sumw_by_record.record_35669.genEventSumw) to build the normalization
denominator, summed across all present job directories -- the SAME
per-job files merge_outputs.py's data-mode identity check already reads
for the main run, read here with the same simple JSON-load pattern (no
identity/URL checking needed for this estimate -- that's
merge_zee_outputs.py's job).

NOT run yet -- no Z->ee cluster output exists. Ready to run once the DY
array job (config.cms_hgg_zee_dy.yaml) has actually run on the cluster.

Usage:
    python hgg_leakage_estimate.py --dy-jobs-base /path/to/hgg_zee/dy_full
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from studies.hgg_cms.validation.zee import common as zc

OUT_DIR = Path(__file__).resolve().parent / "results"

# From VALIDATION_REPORT_1.md Part B: observed 100-105 GeV total (49,521)
# minus the power-law extrapolation's prediction (47,917 -- the fit with
# the much better in-range chi2/ndf, 1.10 vs the exponential's 8.07) =
# 1,604 events, "~1,600" in the task's own framing. The 105-115 window
# was not part of Part B's flagged excess (that check only extrapolated
# INTO 100-105); reported here for completeness, not compared against a
# pre-existing number.
PART_B_EXCESS_100_105 = 1604
PART_B_EXCESS_100_105_NOTE = (
    "Part B's flagged excess = observed 100-105 total (49,521) minus the "
    "power-law extrapolation's prediction (47,917 -- chi2/ndf=1.10, the "
    "better of the two fits); the exponential fit's own prediction "
    "(44,365) would give a larger, ~5,156-event 'excess' -- the power-law "
    "comparison is used here since Part B itself judged that fit more "
    "trustworthy in-range."
)


def discover_job_indices(jobs_base: Path) -> list:
    indices = []
    if not jobs_base.exists():
        return indices
    for d in jobs_base.iterdir():
        m = re.fullmatch(r"job_(\d+)", d.name)
        if d.is_dir() and m:
            indices.append(int(m.group(1)))
    return sorted(indices)


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def sum_leakage_and_sumw(jobs_base: Path):
    total_sumw = 0.0
    total_sumgw = {"100_105": 0.0, "105_115": 0.0}
    total_nsel = {"100_105": 0, "105_115": 0}
    missing_jobs, missing_sumw_jobs, missing_leakage_jobs = [], [], []

    for i in discover_job_indices(jobs_base):
        job_dir = jobs_base / f"job_{i}"
        meta = _load_json(job_dir / "selected" / "job_metadata.json")
        if meta is None:
            missing_jobs.append(i)
            continue
        leakage = meta.get("hgg_veto_leakage_estimate")
        if leakage is None:
            missing_leakage_jobs.append(i)
        else:
            for label in ("100_105", "105_115"):
                total_sumgw[label] += leakage.get(f"sum_genWeight_{label}", 0.0)
                total_nsel[label] += leakage.get(f"n_selected_{label}", 0)

        stats = _load_json(job_dir / "logs" / f"parsing_stats_batch_{i}.json")
        sw = None
        if stats is not None:
            sw = (stats.get("sumw_by_record") or {}).get("record_35669")
        if sw is None:
            missing_sumw_jobs.append(i)
        else:
            total_sumw += sw.get("genEventSumw", 0.0)

    return {
        "n_job_dirs_present": len(discover_job_indices(jobs_base)),
        "missing_jobs_no_metadata": missing_jobs,
        "missing_leakage_key_jobs": missing_leakage_jobs,
        "missing_sumw_jobs": missing_sumw_jobs,
        "total_genEventSumw_dy_processed": total_sumw,
        "total_sum_genWeight_by_window": total_sumgw,
        "total_n_selected_by_window": total_nsel,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dy-jobs-base", required=True,
                    help="e.g. /storage/.../hgg_zee/dy_full (or a local copy of it)")
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs_base = Path(args.dy_jobs_base)
    agg = sum_leakage_and_sumw(jobs_base)

    genEventSumw = agg["total_genEventSumw_dy_processed"]
    expected = {}
    if genEventSumw > 0:
        scale = zc.DY_CROSS_SECTION_PB * 1000.0 * zc.LUMI_FB / genEventSumw
        for label in ("100_105", "105_115"):
            sum_gw = agg["total_sum_genWeight_by_window"][label]
            expected[label] = {
                "N_expected": scale * sum_gw,
                "sum_genWeight": sum_gw,
                "n_selected_raw": agg["total_n_selected_by_window"][label],
            }
    else:
        expected = {"error": "genEventSumw_dy_processed is 0 or missing -- cannot normalize"}

    comparison = None
    if "100_105" in expected and isinstance(expected["100_105"], dict):
        comparison = {
            "N_expected_leakage_100_105": expected["100_105"]["N_expected"],
            "part_b_excess_100_105": PART_B_EXCESS_100_105,
            "fraction_of_part_b_excess_explained": (
                expected["100_105"]["N_expected"] / PART_B_EXCESS_100_105
                if PART_B_EXCESS_100_105 else None
            ),
            "part_b_excess_note": PART_B_EXCESS_100_105_NOTE,
        }

    result = {
        "dy_cross_section_pb": zc.DY_CROSS_SECTION_PB,
        "luminosity_fb": zc.LUMI_FB,
        "normalization_formula": (
            "N_expected = DY_CROSS_SECTION_PB * 1000 (pb->fb) * L_fb * "
            "(sum_genWeight_selected_in_window / genEventSumw_over_processed_DY_files) "
            "-- no branching-ratio factor (DYJetsToLL_M-50 is the full "
            "leptonic process already)."
        ),
        "aggregation": agg,
        "expected_leakage_by_window": expected,
        "comparison_to_part_b_excess": comparison,
    }
    out_path = OUT_DIR / "hgg_leakage_estimate_results.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
