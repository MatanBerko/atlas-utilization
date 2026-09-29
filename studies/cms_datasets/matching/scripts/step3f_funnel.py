"""
Step 3f: per-file post-processing funnel (existing, unmodified functions:
services.storage.sqlite_shards.list_signatures,
studies.cms_coverage.cluster.merge_and_count.{copy_shards,run_funnel_at_threshold,
PRIMARY_MIN_EVENTS_PER_FS,MIN_BUMPNET_BINS,MIN_BUMPNET_EVENTS},
studies.cms_datasets.deliver.build_dataset_delivery.build_sig_to_bumpnet),
run per pilot file, in BOTH --population generic and --population matched,
for like-for-like comparison. Uses the SAME shard each dataset would
actually contribute to a future combined delivery: DoubleMuon (veto
priority 1) -> inclusive shard; SingleMuon (priority 2, behind DoubleMuon
only in this combination) -> exclusive shard. One-file counts are FLOORS
on the eventual full-dataset (57/152-file) delivery, not predictions --
stated explicitly in the report, not implied here.
"""
import sys
import json
import tempfile
from pathlib import Path

REPO_ROOT = "/storage/agrp/berkom/atlas-utilization/work/matching_validation_pinned/repo"
sys.path.insert(0, REPO_ROOT)

from services.storage.sqlite_shards import list_signatures  # noqa: E402
from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    PRIMARY_MIN_EVENTS_PER_FS,
    MIN_BUMPNET_BINS,
    MIN_BUMPNET_EVENTS,
    copy_shards,
    run_funnel_at_threshold,
)
from studies.cms_datasets.deliver.build_dataset_delivery import build_sig_to_bumpnet  # noqa: E402

BASE = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/matching_validation")

RUNS = [
    ("DoubleMuon_30522_0_generic", "inclusive"),
    ("DoubleMuon_30522_0_matched", "inclusive"),
    ("DoubleMuon_30555_0_generic", "inclusive"),
    ("DoubleMuon_30555_0_matched", "inclusive"),
    ("SingleMuon_30530_0_generic", "exclusive"),
    ("SingleMuon_30530_0_matched", "exclusive"),
    ("SingleMuon_30563_0_generic", "exclusive"),
    ("SingleMuon_30563_0_matched", "exclusive"),
]

print(f"PRIMARY_MIN_EVENTS_PER_FS={PRIMARY_MIN_EVENTS_PER_FS} MIN_BUMPNET_BINS={MIN_BUMPNET_BINS} "
      f"MIN_BUMPNET_EVENTS={MIN_BUMPNET_EVENTS}")

summary = {}
for run_dir, which_shard in RUNS:
    shard_name = f"dataset_shard_{which_shard}.sqlite"
    src_path = str(BASE / run_dir / shard_name)
    sig_to_bumpnet = build_sig_to_bumpnet([src_path])
    with tempfile.TemporaryDirectory() as scratch:
        scratch_paths = copy_shards([src_path], Path(scratch))
        stage_b_names, stage_c_survivors, stage_d_survivors, im_str_by_name = run_funnel_at_threshold(
            scratch_paths, PRIMARY_MIN_EVENTS_PER_FS, sig_to_bumpnet
        )
    n_stage_a_signatures = len(sig_to_bumpnet)
    n_stage_b = len(stage_b_names)
    n_stage_c = len(stage_c_survivors)
    n_stage_d = len(stage_d_survivors)  # >30 non-empty bins AND >=100 events (MIN_BUMPNET_BINS/EVENTS) -- equals n_min31 below, cross-check
    from studies.m0m1j0_cms.histograms import make_fixed_grid_histogram
    import numpy as np
    n_min26 = 0
    n_min31 = 0
    for name, main_arr in stage_c_survivors.items():
        values, edges = make_fixed_grid_histogram(main_arr)
        n_nonempty = int(np.count_nonzero(values))
        n_events = int(values.sum())
        if n_events < MIN_BUMPNET_EVENTS:
            continue
        if n_nonempty > 25:
            n_min26 += 1
        if n_nonempty > 30:
            n_min31 += 1

    assert n_min31 == n_stage_d, f"cross-check failed: recomputed min31={n_min31} != stage_d survivors={n_stage_d}"
    print(f"{run_dir} (shard={which_shard}): "
          f"stage_a_signatures={n_stage_a_signatures} stage_b(>=100/sig)={n_stage_b} "
          f"stage_c(z-peak+mass+peak+split)={n_stage_c} min26bins={n_min26} min31bins={n_min31}")
    summary[run_dir] = {
        "shard_used": which_shard,
        "n_stage_a_signatures": n_stage_a_signatures,
        "n_stage_b_after_min_events_per_signature": n_stage_b,
        "n_stage_c_after_zpeak_mass_peak_split": n_stage_c,
        "n_min26bins_histograms": n_min26,
        "n_min31bins_histograms": n_min31,
    }

with open(BASE / "step3f_funnel_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print("wrote", BASE / "step3f_funnel_summary.json")
