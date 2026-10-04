#!/usr/bin/env python
"""
Step 5: cost estimate for a full matched electron-dataset production, and an
APPROXIMATE projection of the histogram/category gain.

READ-ONLY. Every existing output it reads is opened read-only; SQLite shards
are opened with mode=ro&immutable=1 inside the shared helpers, and the funnel
works on scratch COPIES, never on the delivered files.

Two parts:

  cost  -- from the existing generic-mode job metadata (and, for the ratio,
           DoubleMuon's generic AND matched runs, the only dataset that has
           both), estimate files, jobs and core-hours for a matched
           production of DoubleEG + MuonEG + SingleElectron.

  yield -- pool the existing GENERIC (unmatched, older) DoubleEG + MuonEG
           shards through the SAME post-processing funnel the delivery uses,
           and compare the resulting categories against the delivered rare4
           muon file. This is an UNMATCHED APPROXIMATE PROJECTION, not a
           result: the real matched production will accept FEWER events (the
           matching requirement only ever removes events), so these numbers
           are an upper bound on the category reach and a rough indication of
           the histogram count.

Usage:
    python project_cost_and_yield.py --part cost  --out evidence/step5_cost.json
    python project_cost_and_yield.py --part yield --out evidence/step5_yield.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

OUT_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets"
DELIVERED_RARE4 = (f"{OUT_BASE}/deliver/committed/muon_combined_rare4/"
                   "muon_combined_matched_rare4_bumpnet_min26bins.root")
MEASUREMENTS_DEFAULT = ("/storage/agrp/berkom/atlas-utilization/work/electron_prep/"
                        "measurements_v2")

TOTAL_FILES = {"DoubleEG": 133, "MuonEG": 48, "SingleElectron": 151}


def read_run(pattern):
    """(n_jobs, sum_elapsed_sec, sum_n_read) from job_metadata.json files."""
    n, s, ev = 0, 0.0, 0
    for d in sorted(glob.glob(pattern)):
        f = os.path.join(d, "job_metadata.json")
        if not os.path.exists(f):
            continue
        m = json.load(open(f))
        n += 1
        s += float(m["elapsed_sec"])
        ev += int(m["n_read"])
    return n, s, ev


def part_cost(args):
    runs = {}
    for name, pat in (
        ("DoubleMuon_generic", f"{OUT_BASE}/runs/DoubleMuon/job_*"),
        ("DoubleMuon_matched", f"{OUT_BASE}/runs_matched/DoubleMuon/job_*"),
        ("SingleMuon_matched", f"{OUT_BASE}/runs_matched/SingleMuon/job_*"),
        ("DoubleEG_generic", f"{OUT_BASE}/runs/DoubleEG/job_*"),
        ("MuonEG_generic", f"{OUT_BASE}/runs/MuonEG/job_*"),
    ):
        n, s, ev = read_run(pat)
        runs[name] = {"n_jobs": n, "core_hours": s / 3600.0, "n_events_read": ev,
                      "sec_per_Mevent": (s / (ev / 1e6)) if ev else None}

    # SingleElectron has no generic production: estimate its event count from
    # the files this study sampled.
    se_files = sorted(glob.glob(os.path.join(args.measurements, "SingleElectron_*.json")))
    se_events = [json.load(open(f))["n_read"] for f in se_files]
    se_mean = float(np.mean(se_events)) if se_events else None
    se_total_est = (se_mean * TOTAL_FILES["SingleElectron"]) if se_mean else None

    dm_g = runs["DoubleMuon_generic"]["sec_per_Mevent"]
    dm_m = runs["DoubleMuon_matched"]["sec_per_Mevent"]
    ratio = (dm_m / dm_g) if (dm_g and dm_m) else None

    events = {
        "DoubleEG": runs["DoubleEG_generic"]["n_events_read"],
        "MuonEG": runs["MuonEG_generic"]["n_events_read"],
        "SingleElectron": se_total_est,
    }

    # Two brackets. Upper: the dataset's own GENERIC seconds/Mevent, which
    # overestimates matched (matched keeps fewer events through the expensive
    # combinatorics). Lower: DoubleMuon's measured MATCHED rate.
    per_dataset = {}
    for ds in ("DoubleEG", "MuonEG", "SingleElectron"):
        ev = events[ds]
        gen_rate = runs.get(f"{ds}_generic", {}).get("sec_per_Mevent")
        if gen_rate is None:
            # SingleElectron: use the mean of the two measured generic rates.
            gen_rate = float(np.mean([runs["DoubleEG_generic"]["sec_per_Mevent"],
                                      runs["MuonEG_generic"]["sec_per_Mevent"]]))
            gen_rate_source = "mean of DoubleEG and MuonEG generic rates (no SingleElectron generic run exists)"
        else:
            gen_rate_source = "this dataset's own generic run"
        upper = (ev / 1e6) * gen_rate / 3600.0 if ev else None
        lower = (ev / 1e6) * dm_m / 3600.0 if ev else None
        per_dataset[ds] = {
            "n_files": TOTAL_FILES[ds], "n_jobs": TOTAL_FILES[ds],
            "n_events": int(ev) if ev else None,
            "n_events_is_estimate": ds == "SingleElectron",
            "generic_sec_per_Mevent": gen_rate,
            "generic_rate_source": gen_rate_source,
            "core_hours_upper_bound_generic_rate": upper,
            "core_hours_lower_bound_matched_rate": lower,
        }

    out = {
        "what": "cost estimate for a full matched production of the three "
                "electron datasets",
        "measured_runs": runs,
        "matched_vs_generic_cost_ratio_from_DoubleMuon": ratio,
        "note_on_ratio": (
            "DoubleMuon's matched run is CHEAPER per event than its generic run "
            f"(ratio {ratio:.3f} if not None) because the trigger-matching "
            "requirement removes events before the expensive combinatorics. So "
            "the generic-rate column is an UPPER bound for matched running."
        ) if ratio else None,
        "singleelectron_event_estimate": {
            "n_files_sampled": len(se_files),
            "mean_events_per_sampled_file": se_mean,
            "estimated_total_events": se_total_est,
            "status": "UNVERIFIED ESTIMATE -- no SingleElectron generic production "
                      "exists to read; scaled from the files this study sampled",
        },
        "per_dataset": per_dataset,
        "totals": {
            "n_files": sum(TOTAL_FILES.values()),
            "n_jobs": sum(TOTAL_FILES.values()),
            "core_hours_upper_bound": sum(
                v["core_hours_upper_bound_generic_rate"] or 0 for v in per_dataset.values()),
            "core_hours_lower_bound": sum(
                v["core_hours_lower_bound_matched_rate"] or 0 for v in per_dataset.values()),
        },
        "brief_expectation": {"files": 332, "core_hours": "25-35"},
    }
    t = out["totals"]
    out["totals"]["matches_brief_file_count"] = (t["n_files"] == 332)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"files/jobs: {t['n_files']}  core-hours: "
          f"{t['core_hours_lower_bound']:.1f} (matched rate) .. "
          f"{t['core_hours_upper_bound']:.1f} (generic rate)")
    for ds, v in per_dataset.items():
        print(f"  {ds:16s} {v['n_files']:3d} files  "
              f"{v['core_hours_lower_bound_matched_rate']:5.1f} .. "
              f"{v['core_hours_upper_bound_generic_rate']:5.1f} core-hours"
              + ("  (events ESTIMATED)" if v["n_events_is_estimate"] else ""))
    print(f"wrote {args.out}")


def part_yield(args):
    from services.storage.sqlite_shards import list_signatures
    from studies.cms_coverage.cluster.merge_and_count import (
        PRIMARY_MIN_EVENTS_PER_FS, MIN_BUMPNET_EVENTS, copy_shards,
        run_funnel_at_threshold,
    )
    from studies.m0m1j0_cms.histograms import make_fixed_grid_histogram
    from studies.cms_datasets.deliver.build_dataset_delivery import (
        build_sig_to_bumpnet, BINS_THRESHOLD_B,
    )

    shard_paths = []
    per_ds = {}
    for ds in ("DoubleEG", "MuonEG"):
        paths = sorted(glob.glob(f"{OUT_BASE}/runs/{ds}/job_*/dataset_shard_inclusive.sqlite"))
        per_ds[ds] = len(paths)
        shard_paths.extend(paths)
    print(f"pooling {len(shard_paths)} GENERIC inclusive shards: {per_ds}")

    sig_to_bumpnet = build_sig_to_bumpnet(shard_paths)
    print(f"distinct raw signatures: {len(sig_to_bumpnet)}")

    with tempfile.TemporaryDirectory(prefix="eprep_yield_") as tmp:
        scratch = copy_shards(shard_paths, Path(tmp))
        stage_b, stage_c, _stage_d, im_by_name = run_funnel_at_threshold(
            scratch, PRIMARY_MIN_EVENTS_PER_FS, sig_to_bumpnet)
    print(f"stage B: {len(stage_b)}   stage C: {len(stage_c)}")

    gt25 = set()
    for name, arr in stage_c.items():
        values, _edges = make_fixed_grid_histogram(arr)
        if int(np.count_nonzero(values)) > BINS_THRESHOLD_B and int(values.sum()) >= MIN_BUMPNET_EVENTS:
            gt25.add(name)

    def cat_of(n):
        return n.split("_cat_", 1)[1] if "_cat_" in n else "UNKNOWN"

    eg_cats = sorted({cat_of(n) for n in gt25})
    with uproot.open(DELIVERED_RARE4) as f:
        delivered = set()
        for k in sorted(set(k.split(";")[0] for k in f.keys())):
            n = k[len("ROI_"):] if k.startswith("ROI_") else k
            n = n.rsplit("_width_", 1)[0] if "_width_" in n else n
            delivered.add(n)
    delivered_cats = sorted({cat_of(n) for n in delivered})

    new_cats = sorted(set(eg_cats) - set(delivered_cats))
    shared_cats = sorted(set(eg_cats) & set(delivered_cats))
    per_cat = Counter(cat_of(n) for n in gt25)
    new_names = sorted(n for n in gt25 if cat_of(n) in set(new_cats))

    out = {
        "what": "APPROXIMATE, UNMATCHED projection of the electron-dataset gain",
        "STATUS": "NOT A RESULT. Built from the existing GENERIC (unmatched, older) "
                  "DoubleEG and MuonEG shards. A real matched production accepts FEWER "
                  "events, since trigger matching only ever removes events, so these "
                  "are an UPPER BOUND on the category reach and only a rough "
                  "indication of the histogram count. SingleElectron is NOT included "
                  "at all -- no generic SingleElectron production exists to read.",
        "datasets_pooled": per_ds,
        "n_shards": len(shard_paths),
        "post_processing": "the delivery's own funnel, imported unmodified "
                           "(>=100 events per final state, z-peak/max-mass cutoffs, "
                           "peak removal, first-empty-bin split, >25 filled bins, "
                           ">=100 entries)",
        "n_distinct_raw_signatures": len(sig_to_bumpnet),
        "funnel": {"b_after_min_events_per_final_state": len(stage_b),
                   "c_after_postprocessing": len(stage_c),
                   "d_gt25_bins": len(gt25)},
        "n_histograms_gt25bins": len(gt25),
        "n_categories_gt25bins": len(eg_cats),
        "delivered_rare4": {"root": DELIVERED_RARE4,
                            "n_histograms": len(delivered),
                            "n_categories": len(delivered_cats)},
        "categories_absent_from_delivered_rare4": new_cats,
        "n_categories_absent_from_delivered_rare4": len(new_cats),
        "categories_shared_with_delivered_rare4": shared_cats,
        "n_categories_shared": len(shared_cats),
        "n_histograms_in_new_categories": len(new_names),
        "histograms_per_new_category": {c: per_cat[c] for c in new_cats},
        "rough_additional_histograms_at_gt25bins": len(new_names),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"electron (generic) >25 bins: {len(gt25)} histograms in {len(eg_cats)} categories")
    print(f"delivered rare4: {len(delivered)} histograms in {len(delivered_cats)} categories")
    print(f"categories NOT in the delivered file: {len(new_cats)}")
    print(f"histograms living in those new categories: {len(new_names)}")
    print(f"wrote {args.out}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--part", required=True, choices=["cost", "yield"])
    p.add_argument("--out", required=True)
    p.add_argument("--measurements", default=MEASUREMENTS_DEFAULT)
    args = p.parse_args()
    (part_cost if args.part == "cost" else part_yield)(args)


if __name__ == "__main__":
    main()
