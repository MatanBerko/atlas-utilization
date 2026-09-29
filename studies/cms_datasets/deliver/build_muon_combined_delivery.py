#!/usr/bin/env python
"""
Build the combined DoubleMuon+SingleMuon matched-trigger BumpNet delivery
(top-4 task, Step 5). ONE version at a time (--version normal|top4).

Combination rule (Matan's decision, unchanged from the design task): per
signature, pool DoubleMuon's INCLUSIVE raw masses with SingleMuon's
EXCLUSIVE raw masses (DoubleMuon is veto priority 1 -- inclusive==
exclusive for it; SingleMuon is priority 2, so its own EXCLUSIVE shard is
already "not already covered by DoubleMuon's acceptance"), then run the
SAME unchanged post-processing chain as every earlier per-dataset
delivery in this study.

Reuses, unmodified (same imports as
studies/cms_datasets/deliver/build_dataset_delivery.py):
  - services.storage.sqlite_shards: list_signatures
  - studies.cms_coverage.cluster.merge_and_count: PRIMARY_MIN_EVENTS_PER_FS,
    MIN_BUMPNET_BINS, MIN_BUMPNET_EVENTS, copy_shards, run_funnel_at_threshold,
    object_content_category, object_count, SIG_PATTERN
  - studies.cms_coverage.deliver.crop_bumpnet_root: crop_arrays
  - studies.m0m1j0_cms.histograms: _convert_to_bumpnet_name,
    make_fixed_grid_histogram, to_writable_th1f, verify_written_th1f,
    BIN_WIDTH_GEV, FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV
  - build_dataset_delivery's own build_sig_to_bumpnet/write_root_file/
    write_cropped_root_file/manifest_entry (imported directly, not
    reimplemented, so this can never silently diverge from how the
    per-dataset deliveries build the same things).

The only genuinely new logic here is WHICH shard files get pooled
together (DoubleMuon inclusive across all 57 files + SingleMuon exclusive
across all 152 files, for one --version at a time) -- everything after
that point is the existing, shared funnel.

Usage:
    python build_muon_combined_delivery.py --version normal \
        --runs-matched-dir /storage/.../output/cms_datasets/runs_matched \
        --out-dir /storage/.../output/cms_datasets/deliver/muon_combined \
        --out-prefix muon_combined_matched
    python build_muon_combined_delivery.py --version top4 \
        --runs-matched-dir /storage/.../output/cms_datasets/runs_matched \
        --out-dir /storage/.../output/cms_datasets/deliver/muon_combined \
        --out-prefix muon_combined_matched_top4
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

from services.storage.sqlite_shards import list_signatures  # noqa: E402
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
from studies.cms_datasets.deliver.build_dataset_delivery import (  # noqa: E402
    build_sig_to_bumpnet,
    write_root_file,
    write_cropped_root_file,
    manifest_entry,
    BINS_THRESHOLD_A,
    BINS_THRESHOLD_B,
)

SHARD_NAMES_BY_VERSION = {
    "normal": {
        "doublemuon": "dataset_shard_inclusive.sqlite",
        "singlemuon": "dataset_shard_exclusive.sqlite",
    },
    "top4": {
        "doublemuon": "dataset_shard_top4_inclusive.sqlite",
        "singlemuon": "dataset_shard_top4_exclusive.sqlite",
    },
}


def gather_shard_paths(runs_matched_dir: Path, version: str):
    dm_index = json.loads((runs_matched_dir / "DoubleMuon_index.json").read_text())
    sm_index = json.loads((runs_matched_dir / "SingleMuon_index.json").read_text())
    shard_names = SHARD_NAMES_BY_VERSION[version]

    dm_paths = []
    for idx in dm_index:
        p = runs_matched_dir / "DoubleMuon" / f"job_{idx}" / shard_names["doublemuon"]
        if not p.exists():
            raise RuntimeError(f"missing DoubleMuon shard: {p}")
        dm_paths.append(str(p))

    sm_paths = []
    for idx in sm_index:
        p = runs_matched_dir / "SingleMuon" / f"job_{idx}" / shard_names["singlemuon"]
        if not p.exists():
            raise RuntimeError(f"missing SingleMuon shard: {p}")
        sm_paths.append(str(p))

    return dm_paths, sm_paths


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--version", required=True, choices=["normal", "top4"])
    p.add_argument("--runs-matched-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--out-prefix", required=True)
    args = p.parse_args()

    runs_matched_dir = Path(args.runs_matched_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    assert BIN_WIDTH_GEV == 10.0 and FIXED_MASS_MIN_GEV == 0.0 and FIXED_MASS_MAX_GEV == 10000.0, (
        "fixed-grid constants have drifted from the expected 0-10000 GeV / 10 GeV grid"
    )

    print(f"=== Combined muon delivery, version={args.version} ===")
    dm_paths, sm_paths = gather_shard_paths(runs_matched_dir, args.version)
    print(f"DoubleMuon shards (inclusive): {len(dm_paths)}")
    print(f"SingleMuon shards (exclusive): {len(sm_paths)}")
    shard_paths = dm_paths + sm_paths

    print("\n=== Funnel (real, shared post-processing chain) ===")
    sig_to_bumpnet = build_sig_to_bumpnet(shard_paths)
    print(f"total distinct raw signatures across all {len(shard_paths)} shards: {len(sig_to_bumpnet)}")
    with tempfile.TemporaryDirectory(prefix=f"muon_combined_{args.version}_funnel_") as tmp:
        scratch_shards = copy_shards(shard_paths, Path(tmp))
        stage_b_names, stage_c_survivors, stage_d_survivors, im_str_by_name = run_funnel_at_threshold(
            scratch_shards, PRIMARY_MIN_EVENTS_PER_FS, sig_to_bumpnet
        )
    print(f"stage_b(>=100 events per final state)={len(stage_b_names)} "
          f"stage_c(post-processed, >=100 main events)={len(stage_c_survivors)} "
          f"stage_d(>{MIN_BUMPNET_BINS} bins, merge_and_count's own threshold)={len(stage_d_survivors)}")

    print("\n=== Classify every stage-c survivor against both bin thresholds ===")
    all_hists = {}
    n_nonempty_by_name = {}
    n_events_by_name = {}
    for name, main_arr in stage_c_survivors.items():
        values, edges = make_fixed_grid_histogram(main_arr)
        all_hists[name] = (values, edges)
        n_nonempty_by_name[name] = int(np.count_nonzero(values))
        n_events_by_name[name] = int(values.sum())

    set_a = {n for n in stage_c_survivors
             if n_nonempty_by_name[n] > BINS_THRESHOLD_A and n_events_by_name[n] >= MIN_BUMPNET_EVENTS}
    set_b = {n for n in stage_c_survivors
             if n_nonempty_by_name[n] > BINS_THRESHOLD_B and n_events_by_name[n] >= MIN_BUMPNET_EVENTS}
    print(f"set_a (>{BINS_THRESHOLD_A} bins, min31bins): {len(set_a)} names")
    print(f"set_b (>{BINS_THRESHOLD_B} bins, min26bins): {len(set_b)} names")
    if not set_a.issubset(set_b):
        print("STOP: >25-bin set is not a superset of the >30-bin set (should be impossible).",
              file=sys.stderr)
        sys.exit(1)

    print("\n=== Writing ROOT files ===")
    hists_a = {name: all_hists[name] for name in set_a}
    hists_b = {name: all_hists[name] for name in set_b}
    path_a = out_dir / f"{args.out_prefix}_bumpnet_min31bins.root"
    path_b = out_dir / f"{args.out_prefix}_bumpnet_min26bins.root"
    path_a_cropped = out_dir / f"{args.out_prefix}_bumpnet_min31bins_cropped.root"
    path_b_cropped = out_dir / f"{args.out_prefix}_bumpnet_min26bins_cropped.root"

    write_root_file(path_a, hists_a)
    write_root_file(path_b, hists_b)
    write_cropped_root_file(path_a_cropped, hists_a)
    write_cropped_root_file(path_b_cropped, hists_b)
    print(f"wrote {path_a} ({len(hists_a)} histograms)")
    print(f"wrote {path_b} ({len(hists_b)} histograms)")
    print(f"wrote {path_a_cropped} ({len(hists_a)} histograms, cropped)")
    print(f"wrote {path_b_cropped} ({len(hists_b)} histograms, cropped)")

    print("\n=== Writing manifests ===")
    manifest_a = [manifest_entry(n, im_str_by_name[n], *all_hists[n]) for n in sorted(set_a)]
    manifest_b = [manifest_entry(n, im_str_by_name[n], *all_hists[n]) for n in sorted(set_b)]
    (out_dir / f"manifest_{args.out_prefix}_min31bins.json").write_text(json.dumps(manifest_a, indent=2))
    (out_dir / f"manifest_{args.out_prefix}_min26bins.json").write_text(json.dumps(manifest_b, indent=2))

    summary = {
        "version": args.version,
        "n_doublemuon_shards": len(dm_paths),
        "n_singlemuon_shards": len(sm_paths),
        "n_distinct_raw_signatures": len(sig_to_bumpnet),
        "funnel": {
            "b_after_min_events_per_fs_100": len(stage_b_names),
            "c_after_postprocessing_ge100_main": len(stage_c_survivors),
            "d_bumpnet_usable_gt30bins_ge100events": len(stage_d_survivors),
        },
        "n_histograms_min31bins": len(set_a),
        "n_histograms_min26bins": len(set_b),
        "output_files": {
            path_a.name: str(path_a), path_b.name: str(path_b),
            path_a_cropped.name: str(path_a_cropped), path_b_cropped.name: str(path_b_cropped),
        },
    }
    (out_dir / f"build_summary_{args.version}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nAll mandatory build-time checks PASSED (per-histogram TH1F verification already run "
          "inside write_root_file/write_cropped_root_file via verify_written_th1f).")


if __name__ == "__main__":
    main()
