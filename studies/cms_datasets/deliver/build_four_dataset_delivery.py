#!/usr/bin/env python
"""
Build the combined FOUR-dataset matched BumpNet delivery
(electron-datasets task, B3): DoubleMuon + SingleMuon + DoubleEG + MuonEG.

This is the generalisation of
studies/cms_datasets/deliver/build_muon_combined_delivery.py from two
datasets to N, with the electron-datasets task's decisions as the
DEFAULTS instead of opt-in flags. That file is deliberately left
byte-for-byte unchanged, so every pre-existing muon-delivery invocation
keeps producing exactly what it produced before (Step C, check C8); this
module imports its primitives rather than copying them, so the two can
never diverge in what they actually compute.

POOLING RULE (the same rule as the muon delivery, extended):
per signature, pool the HIGHEST-priority dataset's INCLUSIVE raw masses
with every lower-priority dataset's EXCLUSIVE raw masses. With
DELIVERY_VETO_ORDER_4 = DoubleMuon > SingleMuon > DoubleEG > MuonEG that
is DoubleMuon inclusive + SingleMuon exclusive + DoubleEG exclusive +
MuonEG exclusive. Because the per-file jobs computed each dataset's
exclusive shard as "my acceptance AND not any higher dataset's
acceptance", pooling this way counts every accepted collision exactly
once.

DEFAULTS, with NO extra flags (the electron-datasets task's own
requirements):
  * upstream-exact histogram names, ending `_width_10.0`;
  * NO per-histogram minimum entry count (upstream's own behaviour: a
    histogram is written whenever it has at least one entry);
  * NO filled-bin cut (the >=25-filled-bins requirement is applied on the
    BumpNet side during smoothing);
  * the >=100-events-per-final-state rule applied ONCE, on the combined
    shards of all files.
Each of those can be turned back off with an explicit flag, for
cross-checks only.

Everything after the pooling step is the existing, shared post-processing
chain, imported unmodified:
  services.storage.sqlite_shards
  studies.cms_coverage.cluster.merge_and_count: PRIMARY_MIN_EVENTS_PER_FS,
      MIN_BUMPNET_EVENTS, BINS thresholds, copy_shards,
      run_funnel_at_threshold
  studies.m0m1j0_cms.histograms: make_fixed_grid_histogram, the fixed grid
  studies.cms_datasets.deliver.build_dataset_delivery: build_sig_to_bumpnet,
      width_suffix, write_root_file, write_cropped_root_file, manifest_entry
  studies.cms_datasets.deliver.build_muon_combined_delivery:
      UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM, convert_legacy_fs_label

prune_final_states_below_min_events deletes rows in place, so (exactly as
in the muon builder) the funnel runs only on scratch COPIES made by
copy_shards; the production shards are never modified.

Usage:
    python build_four_dataset_delivery.py \
        --runs-dir   /storage/.../output/cms_datasets/runs_matched4_<date> \
        --out-dir    /storage/.../output/cms_datasets/deliver/four_<date> \
        --out-prefix four_dataset_matched_vB
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    PRIMARY_MIN_EVENTS_PER_FS,
    MIN_BUMPNET_BINS,
    MIN_BUMPNET_EVENTS,
    copy_shards,
    run_funnel_at_threshold,
)
from studies.m0m1j0_cms.histograms import (  # noqa: E402
    make_fixed_grid_histogram,
    BIN_WIDTH_GEV,
    FIXED_MASS_MIN_GEV,
    FIXED_MASS_MAX_GEV,
)
from studies.cms_datasets.cluster.run_dataset_on_file import DELIVERY_VETO_ORDER_4  # noqa: E402
from studies.cms_datasets.deliver.build_dataset_delivery import (  # noqa: E402
    build_sig_to_bumpnet,
    width_suffix,
    write_root_file,
    write_cropped_root_file,
    manifest_entry,
    BINS_THRESHOLD_A,
    BINS_THRESHOLD_B,
)
from studies.cms_datasets.deliver.build_muon_combined_delivery import (  # noqa: E402
    UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM,
    convert_legacy_fs_label,
    assert_no_name_collisions,
)

SHARD_NAMES_BY_VERSION = {
    "normal": ("dataset_shard_inclusive.sqlite", "dataset_shard_exclusive.sqlite"),
    "top4": ("dataset_shard_top4_inclusive.sqlite", "dataset_shard_top4_exclusive.sqlite"),
    "nonjet4": ("dataset_shard_nonjet4_inclusive.sqlite", "dataset_shard_nonjet4_exclusive.sqlite"),
    "rare4": ("dataset_shard_rare4_inclusive.sqlite", "dataset_shard_rare4_exclusive.sqlite"),
}

README_TEMPLATE = """BumpNet delivery -- FOUR datasets, Version B (rare4)
====================================================

WHICH FILE TO USE
-----------------
    {cropped}

That is the file for BumpNet. It is the CROPPED one: every histogram has
been trimmed to its first..last filled bin, so the first bin is never
empty, which is what BumpNet requires.

    {uncropped}

is the same {n_delivered} histograms UNCROPPED, on the full fixed
0-10000 GeV grid. For cross-checking and plotting only.

WHAT IS IN IT
-------------
{n_delivered} histograms over {n_final_states} distinct final-state
categories, on the unchanged fixed grid: 0-10000 GeV in 10 GeV bins.
Every histogram is named ROI_mass_<combination>_cat_<final state>{suffix},
e.g. ROI_mass_m0m1_cat_0ex_2mx_5jx_1bx{suffix}.

WHICH DATA
----------
Run2016G+H, four primary datasets, de-duplicated so every accepted
collision is counted exactly once:

{pooling_table}

De-duplication priority, highest first: {order}. An event belongs to a
dataset's exclusive set if that dataset's own acceptance (its trigger
path(s) fired AND its own trigger-matching/threshold rule passes) holds
and no higher-priority dataset's acceptance does.

Electrons within dR < 0.05 of a selected muon are removed, in all four
datasets, before trigger matching and before the final state is decided.

THRESHOLDS APPLIED
------------------
* >= 100 events per final state, applied ONCE over the combined shards of
  all {n_shards} per-file jobs.
* per-histogram minimum entries: {min_entries}
* filled-bin cut: {bin_cut}

For information only, of the {n_delivered} delivered histograms:
  - {n_ge25} have 25 or more filled bins (what BumpNet's own cut keeps)
  - {n_gt25} have more than 25 filled bins
  - {n_gt30} have more than 30 filled bins

WHAT IS UNCHANGED FROM THE MUON DELIVERY
----------------------------------------
Object definitions, the b-tag working point, the golden-JSON run filter,
the Version B reject rule (reject an event if electrons + muons + b-jets
> 4, otherwise keep ALL selected light jets), exact light-jet final
states, the 186 combinations, the fixed 10 GeV binning, the Z-peak cut at
110 GeV, the bin-aligned outlier split, the max-mass cut and peak removal.
"""


def gather_shard_paths(runs_dir: Path, version: str, datasets: list[str]) -> dict:
    """{dataset: [shard path, ...]} -- the highest-priority dataset
    contributes its INCLUSIVE shards, every other its EXCLUSIVE ones."""
    incl_name, excl_name = SHARD_NAMES_BY_VERSION[version]
    out = {}
    for i, label in enumerate(datasets):
        index_path = runs_dir / f"{label}_index.json"
        if not index_path.exists():
            raise RuntimeError(f"missing per-file index: {index_path}")
        index = json.loads(index_path.read_text())
        shard_name = incl_name if i == 0 else excl_name
        paths = []
        for idx in index:
            p = runs_dir / label / f"job_{idx}" / shard_name
            if not p.exists():
                raise RuntimeError(f"missing {label} shard: {p}")
            paths.append(str(p))
        out[label] = paths
        print(f"{label:12s} {'inclusive' if i == 0 else 'exclusive'}: {len(paths)} shards")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs-dir", required=True,
                   help="per-file output root: <dataset>/job_<idx>/<shard>.sqlite "
                        "plus <dataset>_index.json")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--out-prefix", required=True)
    p.add_argument("--version", default="rare4", choices=list(SHARD_NAMES_BY_VERSION))
    p.add_argument("--datasets", default=",".join(DELIVERY_VETO_ORDER_4),
                   help="comma-separated, HIGHEST PRIORITY FIRST. The first one "
                        "contributes its inclusive shards, the rest their exclusive "
                        f"ones. Default: {','.join(DELIVERY_VETO_ORDER_4)}")
    p.add_argument("--min-events-per-fs", type=int, default=PRIMARY_MIN_EVENTS_PER_FS,
                   help="the >=N-events-per-final-state rule, applied ONCE on the "
                        f"combined shards. Default {PRIMARY_MIN_EVENTS_PER_FS}.")
    p.add_argument("--hist-min-entries", type=int, default=UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM,
                   help="per-histogram minimum entries. Default "
                        f"{UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM} = upstream behaviour "
                        "(no minimum; a histogram is written whenever it has data). "
                        f"Pass {MIN_BUMPNET_EVENTS} for the old per-histogram rule.")
    p.add_argument("--filled-bin-cut", action="store_true",
                   help="cross-check only: ALSO require more than "
                        f"{BINS_THRESHOLD_B} filled bins. Off by default, because "
                        "that cut is applied on the BumpNet side during smoothing.")
    p.add_argument("--legacy-width-suffix", action="store_true",
                   help="cross-check only: end names with _width_10 instead of "
                        "upstream's _width_10.0. Off by default.")
    p.add_argument("--legacy-gt-labels", action="store_true",
                   help="cross-check only: the shards carry pre-upstream-names "
                        "six-field labels (0e_2m_5j_0g_0t_1b); convert them as they "
                        "are read. matched4 shards never need this.")
    p.add_argument("--allow-overwrite", action="store_true",
                   help="allow writing into an output directory that already has "
                        "these ROOT files. Off by default: existing outputs are "
                        "read-only.")
    args = p.parse_args()

    datasets = [d.strip() for d in args.datasets.split(",") if d.strip()]
    runs_dir = Path(args.runs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    assert BIN_WIDTH_GEV == 10.0 and FIXED_MASS_MIN_GEV == 0.0 and FIXED_MASS_MAX_GEV == 10000.0, (
        "fixed-grid constants have drifted from the expected 0-10000 GeV / 10 GeV grid")

    upstream_suffix = not args.legacy_width_suffix
    print(f"=== Four-dataset delivery, version={args.version} ===")
    print(f"priority order (highest first): {datasets}")
    print(f"width suffix: {width_suffix(upstream=upstream_suffix)}")
    print(f"per-histogram minimum entries: {args.hist_min_entries}")
    print(f"filled-bin cut: {'>' + str(BINS_THRESHOLD_B) if args.filled_bin_cut else 'NONE'}")
    print(f"events per final state: >= {args.min_events_per_fs} (applied once, combined)")

    paths_by_dataset = gather_shard_paths(runs_dir, args.version, datasets)
    shard_paths = [p for label in datasets for p in paths_by_dataset[label]]
    print(f"total shards pooled: {len(shard_paths)}")

    print("\n=== Funnel (the shared post-processing chain) ===")
    if args.legacy_gt_labels:
        sig_to_bumpnet_legacy = build_sig_to_bumpnet(shard_paths)
        sig_to_bumpnet = build_sig_to_bumpnet(shard_paths, fs_converter=convert_legacy_fs_label)
        n_names = assert_no_name_collisions(sig_to_bumpnet_legacy, sig_to_bumpnet)
        print(f"  legacy labels converted: {len(sig_to_bumpnet)} signatures onto "
              f"{n_names} names, no collisions")
    else:
        sig_to_bumpnet = build_sig_to_bumpnet(shard_paths)
    print(f"distinct raw signatures across all {len(shard_paths)} shards: {len(sig_to_bumpnet)}")

    funnel_diagnostics: dict = {}
    # copy_shards makes scratch COPIES: prune_final_states_below_min_events
    # deletes rows in place, so it must never touch the originals.
    with tempfile.TemporaryDirectory(prefix=f"four_dataset_{args.version}_funnel_") as tmp:
        scratch_shards = copy_shards(shard_paths, Path(tmp))
        stage_b_names, stage_c_survivors, stage_d_survivors, im_str_by_name = run_funnel_at_threshold(
            scratch_shards, args.min_events_per_fs, sig_to_bumpnet,
            diagnostics=funnel_diagnostics, min_main_entries=args.hist_min_entries,
        )
    print(f"stage_b(>={args.min_events_per_fs} events per final state)={len(stage_b_names)} "
          f"stage_c(post-processed)={len(stage_c_survivors)} "
          f"stage_d(>{MIN_BUMPNET_BINS} bins, informational)={len(stage_d_survivors)}")

    all_hists = {}
    n_nonempty_by_name = {}
    n_events_by_name = {}
    for name, main_arr in stage_c_survivors.items():
        values, edges = make_fixed_grid_histogram(main_arr)
        all_hists[name] = (values, edges)
        n_nonempty_by_name[name] = int(np.count_nonzero(values))
        n_events_by_name[name] = int(values.sum())

    delivered = sorted(n for n in stage_c_survivors
                       if n_events_by_name[n] >= args.hist_min_entries
                       and (not args.filled_bin_cut or n_nonempty_by_name[n] > BINS_THRESHOLD_B))
    excluded_by_hist_min = sorted((n, n_events_by_name[n]) for n in stage_c_survivors
                                  if n_events_by_name[n] < args.hist_min_entries)
    n_ge25 = sum(1 for n in delivered if n_nonempty_by_name[n] >= 25)
    n_gt25 = sum(1 for n in delivered if n_nonempty_by_name[n] > BINS_THRESHOLD_B)
    n_gt30 = sum(1 for n in delivered if n_nonempty_by_name[n] > BINS_THRESHOLD_A)

    print(f"\ndelivered histograms: {len(delivered)}")
    print(f"  of which >=25 filled bins (BumpNet's own cut, informational): {n_ge25}")

    hists = {name: all_hists[name] for name in delivered}
    path_main = out_dir / f"{args.out_prefix}_bumpnet.root"
    path_cropped = out_dir / f"{args.out_prefix}_bumpnet_cropped.root"
    for path in (path_main, path_cropped):
        if path.exists() and not args.allow_overwrite:
            print(f"STOP: refusing to overwrite an existing file: {path}", file=sys.stderr)
            sys.exit(1)

    print("\n=== Writing ROOT files ===")
    write_root_file(path_main, hists, upstream_width_suffix=upstream_suffix)
    write_cropped_root_file(path_cropped, hists, upstream_width_suffix=upstream_suffix)
    print(f"wrote {path_main} ({len(hists)} histograms, uncropped)")
    print(f"wrote {path_cropped} ({len(hists)} histograms, cropped <- BumpNet uses this one)")

    manifest = [manifest_entry(n, im_str_by_name[n], *all_hists[n],
                               upstream_width_suffix=upstream_suffix) for n in delivered]
    (out_dir / f"manifest_{args.out_prefix}.json").write_text(json.dumps(manifest, indent=2))

    n_final_states = len({n.split("_cat_", 1)[1] for n in delivered if "_cat_" in n})
    pooling = {label: {"shards": len(paths_by_dataset[label]),
                       "contribution": "inclusive" if i == 0 else "exclusive"}
               for i, label in enumerate(datasets)}
    summary = {
        "what": "combined four-dataset matched BumpNet delivery (electron-datasets task B3)",
        "version": args.version,
        "priority_order_highest_first": datasets,
        "pooling": pooling,
        "n_shards_total": len(shard_paths),
        "n_distinct_raw_signatures": len(sig_to_bumpnet),
        "min_events_per_final_state": args.min_events_per_fs,
        "min_events_per_final_state_applied": "once, on the combined shards of all files",
        "per_histogram_min_entries": args.hist_min_entries,
        "per_histogram_min_entries_source": (
            "upstream: no minimum, a histogram is written whenever it has >=1 entry"
            if args.hist_min_entries <= UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM
            else "explicit --hist-min-entries"),
        "filled_bin_cut": (f">{BINS_THRESHOLD_B} filled bins" if args.filled_bin_cut
                           else "NONE (applied on the BumpNet side during smoothing)"),
        "width_suffix": width_suffix(upstream=upstream_suffix),
        "width_suffix_matches_upstream": bool(upstream_suffix),
        "legacy_gt_label_conversion_applied": bool(args.legacy_gt_labels),
        "funnel": {
            "b_after_min_events_per_fs": len(stage_b_names),
            "c_after_postprocessing": len(stage_c_survivors),
            "d_gt30bins_informational": len(stage_d_survivors),
        },
        "n_delivered_histograms": len(delivered),
        "n_distinct_final_state_categories_delivered": n_final_states,
        "informational_bin_counts": {
            "n_with_ge_25_filled_bins": n_ge25,
            "n_with_gt_25_filled_bins": n_gt25,
            "n_with_gt_30_filled_bins": n_gt30,
        },
        "n_excluded_at_histogram_step": len(excluded_by_hist_min),
        "n_excluded_at_postprocessing_step": funnel_diagnostics.get(
            "n_excluded_by_min_main_entries"),
        "funnel_diagnostics": {k: v for k, v in funnel_diagnostics.items()
                               if not k.startswith("names_")},
        "output_files": {path_main.name: str(path_main), path_cropped.name: str(path_cropped)},
        "file_for_bumpnet": path_cropped.name,
    }
    (out_dir / f"build_summary_{args.version}_four_dataset.json").write_text(
        json.dumps(summary, indent=2))

    pooling_table = "\n".join(
        f"  {label:12s} {pooling[label]['contribution']:9s} "
        f"({pooling[label]['shards']} per-file shards)" for label in datasets)
    (out_dir / "README.txt").write_text(README_TEMPLATE.format(
        cropped=path_cropped.name, uncropped=path_main.name,
        n_delivered=len(delivered), n_final_states=n_final_states,
        suffix=width_suffix(upstream=upstream_suffix),
        pooling_table=pooling_table, order=" > ".join(datasets),
        n_shards=len(shard_paths),
        min_entries=("NONE (upstream behaviour: >= 1 entry)"
                     if args.hist_min_entries <= UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM
                     else f">= {args.hist_min_entries} entries"),
        bin_cut=(f"> {BINS_THRESHOLD_B} filled bins" if args.filled_bin_cut
                 else "NONE (applied on the BumpNet side during smoothing)"),
        n_ge25=n_ge25, n_gt25=n_gt25, n_gt30=n_gt30,
    ))
    print(f"\nwrote {out_dir / 'README.txt'}")
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("funnel_diagnostics",)}, indent=2))
    print("\nAll mandatory build-time checks PASSED (per-histogram TH1F verification "
          "already run inside write_root_file/write_cropped_root_file via "
          "verify_written_th1f).")


if __name__ == "__main__":
    main()
