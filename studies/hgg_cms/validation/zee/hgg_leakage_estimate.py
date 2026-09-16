#!/usr/bin/env python
"""
Implementation task 6, Z->ee validation follow-up (17 Sep 2026), item 5:
electron-veto leakage into the H->gamma-gamma sample.

REVISED -- RUNS ON THE CLUSTER (analysis node, `nice`, NOT a PBS job),
against the ALREADY-COMPLETED DY run's OWN parsed_data chunks. Not run
yet in this task; see the final chat message for the exact command.

Why this script exists, and why it reads raw parsed chunks instead of
job_metadata.json: the completed DY run's 41 jobs each computed
"hgg_veto_leakage_estimate" INLINE, at cluster runtime
(run_zee_selection_on_chunks.py's compute_hgg_veto_leakage()), but only
for TWO windows (100-105, 105-115 combined) and with NO category split --
the windows and split this task's item 5 actually needs (100-105,
105-110, 110-115, 135-180, EACH per category) were added to that
function's own LEAKAGE_WINDOWS AFTER the DY run already completed. The
electronVeto==True population itself was never written to any output
file (by design -- see that function's own docstring: it exists only in
memory, once, during each job's own run), so there is no way to get the
finer windows from anything already local. BUT the underlying
already-PARSED chunk files (job_<i>/parsed_data/*.root) are still sitting
on Lustre from the completed run (nothing in this pipeline deletes them),
so recomputing compute_hgg_veto_leakage() -- now with the full window/
category set -- against those same already-parsed chunks needs NO new
CERN download, NO re-parsing, and NO qsub: just one quick script reading
already-local files, the same "must run on the analysis node in a few
minutes with nice" category as merge_outputs.py.

Usage (see studies/hgg_cms/cluster/pbs_hgg_zee_array.sh /
config.cms_hgg_zee_dy.yaml for OUTPUT_BASE's real value):
    nice python studies/hgg_cms/validation/zee/hgg_leakage_estimate.py \
        --dy-jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_zee/dy_full \
        --out /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/hgg_leakage_estimate_results.json
Then copy the one output JSON to the laptop (HGG_ZEE_MERGED_DIR) --
no need to copy the 41 job directories themselves.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.cluster.run_selection_on_chunks import read_chunk  # noqa: E402
from studies.hgg_cms.cluster.run_zee_selection_on_chunks import (  # noqa: E402
    LEAKAGE_WINDOWS, compute_hgg_veto_leakage,
)
from studies.hgg_cms.validation.zee import common as zc  # noqa: E402
from studies.hgg_cms.validation import common as main_common  # noqa: E402

CATS = ("inclusive", "EBEB", "notEBEB")

# From Part B (VALIDATION_REPORT_1.md): observed 100-105 GeV total
# (49,521) minus the power-law extrapolation's prediction (47,917 -- the
# fit with the much better in-range chi2/ndf, 1.10 vs the exponential's
# 8.07) = 1,604 events, "~1,600" in this task's own framing.
PART_B_EXCESS_100_105 = 1604
PART_B_EXCESS_100_105_NOTE = (
    "Part B's flagged excess = observed 100-105 total (49,521) minus the "
    "power-law extrapolation's prediction (47,917 -- chi2/ndf=1.10, the "
    "better of the two fits)."
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


def process_job(job_dir: Path, index: int) -> dict:
    chunks_dir = job_dir / "parsed_data"
    chunk_files = sorted(chunks_dir.glob("*.root")) if chunks_dir.exists() else []
    totals = {}
    n_chunks_with_genweight = 0
    for chunk_path in chunk_files:
        events = read_chunk(chunk_path)
        if "genWeight" not in events.fields:
            continue
        n_chunks_with_genweight += 1
        leak = compute_hgg_veto_leakage(events)
        for k, v in leak.items():
            totals[k] = totals.get(k, 0) + v

    genEventSumw = None
    stats = _load_json(job_dir / "logs" / f"parsing_stats_batch_{index}.json")
    if stats is not None:
        sw = (stats.get("sumw_by_record") or {}).get("record_35669")
        if sw is not None:
            genEventSumw = sw.get("genEventSumw")

    return {
        "n_chunks_found": len(chunk_files),
        "n_chunks_with_genweight": n_chunks_with_genweight,
        "leakage_totals": totals,
        "genEventSumw": genEventSumw,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dy-jobs-base", required=True,
                    help="e.g. /storage/.../hgg_zee/dy_full")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    jobs_base = Path(args.dy_jobs_base)
    indices = discover_job_indices(jobs_base)
    if not indices:
        raise SystemExit(f"no job_<i> directories found under {jobs_base}")

    grand_totals = {}
    total_genEventSumw = 0.0
    missing_chunks_jobs, missing_sumw_jobs = [], []

    for i in indices:
        job_dir = jobs_base / f"job_{i}"
        print(f"processing job_{i} ...", flush=True)
        res = process_job(job_dir, i)
        if res["n_chunks_found"] == 0:
            missing_chunks_jobs.append(i)
        for k, v in res["leakage_totals"].items():
            grand_totals[k] = grand_totals.get(k, 0.0) + v
        if res["genEventSumw"] is None:
            missing_sumw_jobs.append(i)
        else:
            total_genEventSumw += res["genEventSumw"]
        print(f"  chunks={res['n_chunks_found']} genEventSumw={res['genEventSumw']}", flush=True)

    expected = {}
    if total_genEventSumw > 0:
        scale = zc.DY_CROSS_SECTION_PB * 1000.0 * main_common.LUMI_FB / total_genEventSumw
        for label in LEAKAGE_WINDOWS:
            expected[label] = {}
            for cat in CATS:
                key = f"{label}_{cat}"
                sum_gw = grand_totals.get(f"sum_genWeight_{key}", 0.0)
                sum_gw_sq = grand_totals.get(f"sum_genWeight_sq_{key}", 0.0)
                N = scale * sum_gw
                stat_unc = scale * (sum_gw_sq ** 0.5)
                expected[label][cat] = {
                    "N_expected": N,
                    "statistical_uncertainty": stat_unc,
                    "n_selected_raw": grand_totals.get(f"n_selected_{key}", 0),
                    "sum_genWeight": sum_gw,
                }
    else:
        expected = {"error": "total_genEventSumw is 0 or missing -- cannot normalize"}

    comparison = None
    if "100_105" in expected and "inclusive" in expected.get("100_105", {}):
        n_exp = expected["100_105"]["inclusive"]["N_expected"]
        n_unc = expected["100_105"]["inclusive"]["statistical_uncertainty"]
        frac = n_exp / PART_B_EXCESS_100_105 if PART_B_EXCESS_100_105 else None
        if frac is None:
            verdict = "unknown"
        elif frac >= 0.9:
            verdict = "fully"
        elif frac >= 0.1:
            verdict = "partly"
        else:
            verdict = "no"
        comparison = {
            "N_expected_leakage_100_105_inclusive": n_exp,
            "N_expected_leakage_100_105_inclusive_stat_unc": n_unc,
            "part_b_excess_100_105": PART_B_EXCESS_100_105,
            "fraction_of_part_b_excess_explained": frac,
            "verdict_fully_partly_no": verdict,
            "part_b_excess_note": PART_B_EXCESS_100_105_NOTE,
        }

    result = {
        "dy_cross_section_pb": zc.DY_CROSS_SECTION_PB,
        "luminosity_fb": main_common.LUMI_FB,
        "normalization_formula": (
            "N_expected = DY_CROSS_SECTION_PB * 1000 (pb->fb) * L_fb * "
            "(Sum genWeight_selected_in_window_and_category / "
            "Sum genEventSumw_over_processed_DY_files); statistical "
            "uncertainty = same scale * sqrt(Sum genWeight^2) (correct "
            "for signed weights, since squaring removes the sign)."
        ),
        "n_jobs_processed": len(indices),
        "missing_chunks_jobs": missing_chunks_jobs,
        "missing_sumw_jobs": missing_sumw_jobs,
        "total_genEventSumw_dy_processed": total_genEventSumw,
        "expected_leakage_by_window_and_category": expected,
        "comparison_to_part_b_excess": comparison,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
