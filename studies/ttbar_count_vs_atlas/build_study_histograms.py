#!/usr/bin/env python
"""
Step 6 (ttbar_count_vs_atlas): build the study histograms for ONE
--population notrigger variant, using the SAME post-processing as our
delivery builder.

Every post-processing decision is made by code imported unmodified from
the delivery path -- nothing is reimplemented here, and nothing in the
delivery path is changed:

  services.storage.sqlite_shards.list_signatures
  studies.cms_coverage.cluster.merge_and_count
      PRIMARY_MIN_EVENTS_PER_FS (100, per FINAL STATE, globally)
      MIN_BUMPNET_EVENTS        (100, per HISTOGRAM)
      copy_shards, run_funnel_at_threshold
         -> prune_final_states_below_min_events
         -> _apply_z_peak_cut (115 GeV, same-flavour dilepton channels)
         -> max-mass cutoff (10 TeV)
         -> _find_rightmost_highest_peak + peak removal
         -> _split_by_first_empty_bin
      object_content_category, object_count
  studies.m0m1j0_cms.histograms.make_fixed_grid_histogram
      (fixed 10 GeV bins, 0-10000 GeV)
  studies.cms_datasets.deliver.build_dataset_delivery
      build_sig_to_bumpnet, write_root_file, write_cropped_root_file,
      manifest_entry, BINS_THRESHOLD_A (>30), BINS_THRESHOLD_B (>25)

The only thing this script adds over build_muon_combined_delivery.py is
(a) WHICH shards get pooled -- one notrigger variant across every file of
one MC record, inclusive only, no DoubleMuon/SingleMuon pooling, since
notrigger mode does no de-duplication -- and (b) a third bin threshold,
">= 25 filled bins", which the delivery does not use but which is the
threshold Maryna quoted for the ATLAS count. That third threshold is
computed here from the same (values, edges) pairs; it changes nothing
about how a histogram is built.

Histograms are RAW counts. No weight is applied anywhere: the notrigger
shards carry no weights at all, and the ATLAS numbers being compared
against are raw too.

Usage:
    python build_study_histograms.py --jobs-dir <notrigger output base> \
        --variant rare4 --out-dir <dir> --out-prefix ttbar_notrigger_rare4
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    PRIMARY_MIN_EVENTS_PER_FS,
    MIN_BUMPNET_EVENTS,
    copy_shards,
    run_funnel_at_threshold,
    object_content_category,
    object_count,
)
from studies.m0m1j0_cms.histograms import (  # noqa: E402
    make_fixed_grid_histogram,
    BIN_WIDTH_GEV,
    FIXED_MASS_MIN_GEV,
    FIXED_MASS_MAX_GEV,
)
from studies.cms_datasets.deliver.build_dataset_delivery import (  # noqa: E402
    build_sig_to_bumpnet,
    write_root_file,
    write_cropped_root_file,
    manifest_entry,
    BINS_THRESHOLD_A,
    BINS_THRESHOLD_B,
)

VARIANTS = ("rare4", "pr31", "pr31_noOR")

# The third threshold, ">= 25 filled bins", is the one Maryna quoted for
# the ATLAS side (">=25 bins, >=100 events"). BINS_THRESHOLD_B is ">25",
# i.e. ">=26", so the two are NOT the same cut and both are reported.
BINS_THRESHOLD_ATLAS_GE25 = 25


def category_of(name: str) -> str:
    """`mass_<combo>_cat_<fs>` -> the `<fs>` part (our 1ex_0mx_... form)."""
    return name.split("_cat_", 1)[1] if "_cat_" in name else "UNKNOWN"


def lepton_content_of_category(category: str) -> str:
    """Classify a FINAL STATE by its lepton content.

    Our CMS delivery is muon-triggered, so the interesting split is
    whether a category can appear in it at all: categories with at least
    one muon can, categories with electrons but no muon essentially
    cannot, and categories with no lepton at all cannot.
    """
    counts = {}
    for token in category.split("_"):
        token = token[:-1] if token.endswith("x") else token
        if len(token) >= 2 and token[:-1].isdigit():
            counts[token[-1]] = int(token[:-1])
    n_m = counts.get("m", 0)
    n_e = counts.get("e", 0)
    if n_m >= 1:
        return "at_least_one_muon"
    if n_e >= 1:
        return "electrons_but_no_muon"
    return "no_lepton"


def breakdown(names) -> dict:
    cats = sorted({category_of(n) for n in names})
    by_content = defaultdict(list)
    for c in cats:
        by_content[lepton_content_of_category(c)].append(c)
    per_cat = defaultdict(int)
    for n in names:
        per_cat[category_of(n)] += 1
    return {
        "n_histograms": len(names),
        "n_categories": len(cats),
        "categories": cats,
        "categories_by_lepton_content": {k: sorted(v) for k, v in by_content.items()},
        "n_categories_by_lepton_content": {k: len(v) for k, v in by_content.items()},
        "n_histograms_by_lepton_content": {
            k: sum(per_cat[c] for c in v) for k, v in by_content.items()
        },
        "n_histograms_per_category": dict(sorted(per_cat.items())),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-dir", required=True,
                   help="notrigger output base containing job_<index>/ directories")
    p.add_argument("--variant", required=True, choices=list(VARIANTS))
    p.add_argument("--out-dir", required=True)
    p.add_argument("--out-prefix", required=True)
    p.add_argument("--expected-n-files", type=int, default=None,
                   help="fail unless exactly this many job directories are found")
    args = p.parse_args()

    jobs_dir = Path(args.jobs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    assert BIN_WIDTH_GEV == 10.0 and FIXED_MASS_MIN_GEV == 0.0 and FIXED_MASS_MAX_GEV == 10000.0, (
        "fixed-grid constants have drifted from the expected 0-10000 GeV / 10 GeV grid"
    )

    shard_name = f"dataset_shard_notrigger_{args.variant}_inclusive.sqlite"
    job_dirs = sorted(jobs_dir.glob("job_*"), key=lambda p: int(p.name.split("_")[1]))
    shard_paths = []
    missing = []
    for d in job_dirs:
        p_shard = d / shard_name
        if p_shard.exists():
            shard_paths.append(str(p_shard))
        else:
            missing.append(str(p_shard))
    if missing:
        raise RuntimeError(f"{len(missing)} job dir(s) have no {shard_name}: {missing[:5]}")
    if args.expected_n_files is not None and len(shard_paths) != args.expected_n_files:
        raise RuntimeError(f"expected {args.expected_n_files} shards, found {len(shard_paths)}")

    print(f"=== notrigger study histograms, variant={args.variant} ===")
    print(f"shards: {len(shard_paths)} (one per input file, inclusive only)")

    # Per-file event counters, straight out of each job's own metadata.
    totals = {"n_events_read": 0, "n_events_passing_gate": 0,
              "n_rejected_e_mu_b_gt4": 0, "n_dropped_ge5_light_jets": 0,
              "n_events_into_combinations": 0}
    sum_genweight_all = 0.0
    sum_genweight_gate = 0.0
    for d in job_dirs:
        meta = json.loads((d / "job_metadata.json").read_text())
        nt = meta["notrigger_diagnostics"]
        v = nt["variants"][args.variant]
        totals["n_events_read"] += v["n_events_read_this_file"]
        totals["n_events_passing_gate"] += v["n_events_passing_gate"]
        totals["n_rejected_e_mu_b_gt4"] += v["n_rejected_e_mu_b_gt4"]
        totals["n_dropped_ge5_light_jets"] += v["n_dropped_ge5_light_jets"]
        totals["n_events_into_combinations"] += v["n_events_into_combinations"]
        sum_genweight_all += nt["sum_genweight_all_events_this_file"]
        sum_genweight_gate += nt["sum_genweight_gate_passing_events"]
    print(f"events read:               {totals['n_events_read']}")
    print(f"events passing >=2 gate:   {totals['n_events_passing_gate']}")
    print(f"rejected e+mu+b > 4:       {totals['n_rejected_e_mu_b_gt4']}")
    print(f"dropped >= 5 light jets:   {totals['n_dropped_ge5_light_jets']}")
    print(f"events into combinations:  {totals['n_events_into_combinations']}")
    print(f"sum genWeight (all events, INFORMATION ONLY -- histograms are raw): {sum_genweight_all:.6g}")

    print("\n=== Funnel (the shared, unmodified post-processing chain) ===")
    sig_to_bumpnet = build_sig_to_bumpnet(shard_paths)
    names_with_any_event = sorted({v[0] for v in sig_to_bumpnet.values()})
    print(f"distinct raw signatures: {len(sig_to_bumpnet)}")
    print(f"stage A -- BumpNet names with >= 1 event: {len(names_with_any_event)}")

    with tempfile.TemporaryDirectory(prefix=f"ttbar_{args.variant}_funnel_") as tmp:
        scratch_shards = copy_shards(shard_paths, Path(tmp))
        stage_b_names, stage_c_survivors, _stage_d, im_str_by_name = run_funnel_at_threshold(
            scratch_shards, PRIMARY_MIN_EVENTS_PER_FS, sig_to_bumpnet
        )
    print(f"stage B -- after >= {PRIMARY_MIN_EVENTS_PER_FS} events per FINAL STATE "
          f"(global, across all files): {len(stage_b_names)}")
    print(f"stage C -- after post-processing, >= {PRIMARY_MIN_EVENTS_PER_FS} main events: "
          f"{len(stage_c_survivors)}")

    all_hists = {}
    n_nonempty_by_name = {}
    n_events_by_name = {}
    for name, main_arr in stage_c_survivors.items():
        values, edges = make_fixed_grid_histogram(main_arr)
        all_hists[name] = (values, edges)
        n_nonempty_by_name[name] = int(np.count_nonzero(values))
        n_events_by_name[name] = int(values.sum())

    def select(min_bins_strictly_greater=None, min_bins_at_least=None):
        out = set()
        for n in stage_c_survivors:
            if n_events_by_name[n] < MIN_BUMPNET_EVENTS:
                continue
            nb = n_nonempty_by_name[n]
            if min_bins_strictly_greater is not None and nb > min_bins_strictly_greater:
                out.add(n)
            elif min_bins_at_least is not None and nb >= min_bins_at_least:
                out.add(n)
        return out

    set_ge25 = select(min_bins_at_least=BINS_THRESHOLD_ATLAS_GE25)   # >= 25 bins (ATLAS wording)
    set_gt25 = select(min_bins_strictly_greater=BINS_THRESHOLD_B)    # > 25 bins (min26bins)
    set_gt30 = select(min_bins_strictly_greater=BINS_THRESHOLD_A)    # > 30 bins (min31bins)
    print(f"stage D -- >= {BINS_THRESHOLD_ATLAS_GE25} filled bins and >= {MIN_BUMPNET_EVENTS} events: "
          f"{len(set_ge25)}")
    print(f"stage D -- >  {BINS_THRESHOLD_B} filled bins (min26bins): {len(set_gt25)}")
    print(f"stage D -- >  {BINS_THRESHOLD_A} filled bins (min31bins): {len(set_gt30)}")
    if not (set_gt30 <= set_gt25 <= set_ge25):
        print("STOP: the three bin-threshold sets are not nested (should be impossible).",
              file=sys.stderr)
        sys.exit(1)

    print("\n=== Writing ROOT files + manifests ===")
    outputs = {}
    for tag, nameset in (("ge25bins", set_ge25), ("min26bins", set_gt25), ("min31bins", set_gt30)):
        hists = {n: all_hists[n] for n in nameset}
        path = out_dir / f"{args.out_prefix}_{tag}.root"
        path_cropped = out_dir / f"{args.out_prefix}_{tag}_cropped.root"
        write_root_file(path, hists)
        write_cropped_root_file(path_cropped, hists)
        manifest = [manifest_entry(n, im_str_by_name[n], *all_hists[n]) for n in sorted(nameset)]
        manifest_path = out_dir / f"manifest_{args.out_prefix}_{tag}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        outputs[tag] = {
            "root": str(path), "root_cropped": str(path_cropped),
            "manifest": str(manifest_path), "n_histograms": len(hists),
        }
        print(f"{tag}: {len(hists)} histograms -> {path.name}, {path_cropped.name}")

    summary = {
        "variant": args.variant,
        "jobs_dir": str(jobs_dir),
        "n_input_files": len(shard_paths),
        "weighting": "raw unweighted counts",
        "event_counts": totals,
        "sum_genweight_all_events": sum_genweight_all,
        "sum_genweight_gate_passing_events": sum_genweight_gate,
        "post_processing": {
            "bin_width_gev": BIN_WIDTH_GEV,
            "fixed_range_gev": [FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV],
            "min_events_per_final_state": PRIMARY_MIN_EVENTS_PER_FS,
            "min_events_per_histogram": MIN_BUMPNET_EVENTS,
            "z_peak_cutoff_gev": 115.0,
            "max_mass_cutoff_gev": 10000.0,
            "peak_removal": "rightmost highest peak, then keep mass >= peak",
            "outlier_split": "first empty bin",
        },
        "funnel": {
            "a_names_with_at_least_1_event": len(names_with_any_event),
            "b_after_min_events_per_final_state_100": len(stage_b_names),
            "c_after_postprocessing_ge100_main_events": len(stage_c_survivors),
            "d_ge25_bins": len(set_ge25),
            "d_gt25_bins_min26bins": len(set_gt25),
            "d_gt30_bins_min31bins": len(set_gt30),
        },
        "breakdown": {
            "a_names_with_at_least_1_event": breakdown(names_with_any_event),
            "b_after_min_events_per_final_state_100": breakdown(stage_b_names),
            "c_after_postprocessing": breakdown(list(stage_c_survivors)),
            "d_ge25_bins": breakdown(sorted(set_ge25)),
            "d_gt25_bins_min26bins": breakdown(sorted(set_gt25)),
            "d_gt30_bins_min31bins": breakdown(sorted(set_gt30)),
        },
        "object_content_categories_ge25": {
            k: v for k, v in sorted(
                Counter(
                    object_content_category(im_str_by_name[n]) for n in set_ge25
                ).items())
        },
        "object_count_histogram_ge25": {
            str(k): v for k, v in sorted(
                Counter(
                    object_count(im_str_by_name[n]) for n in set_ge25
                ).items())
        },
        "outputs": outputs,
    }
    (out_dir / f"build_summary_{args.variant}.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nwrote {out_dir}/build_summary_{args.variant}.json")
    print("All build-time TH1F readback checks passed (verify_written_th1f, inside "
          "write_root_file/write_cropped_root_file).")


if __name__ == "__main__":
    main()
