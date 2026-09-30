"""
rare4 task, Step 6: bin-count summary table for all FOUR versions
(normal, top4, nonjet4, rare4) and both thresholds (min31bins >30,
min26bins >25), for:
  1. Combined (DM inclusive + SM exclusive) -- the delivered numbers
  2. DoubleMuon alone (inclusive)
  3. SingleMuon alone (inclusive)
  4. Each record alone (inclusive): 30522, 30555, 30530, 30563
Counts only -- no ROOT files written for rows 2-5.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/rare4_delivery/repo")

import numpy as np  # noqa: E402

from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    PRIMARY_MIN_EVENTS_PER_FS,
    MIN_BUMPNET_EVENTS,
    copy_shards,
    run_funnel_at_threshold,
)
from studies.m0m1j0_cms.histograms import make_fixed_grid_histogram  # noqa: E402
from studies.cms_datasets.deliver.build_dataset_delivery import build_sig_to_bumpnet, BINS_THRESHOLD_A, BINS_THRESHOLD_B  # noqa: E402

RUNS_BASE_NORMAL = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched")
RUNS_BASE_NONJET4 = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_nonjet4")
RUNS_BASE_RARE4 = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_rare4")
OUT_DIR = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_rare4")
FS_RE = re.compile(r"^(\d+)ex_(\d+)mx_(\d+)jx_(\d+)gx_(\d+)tx_(\d+)bx$")

SHARD_NAMES = {
    "normal": {"incl": "dataset_shard_inclusive.sqlite", "excl": "dataset_shard_exclusive.sqlite"},
    "top4": {"incl": "dataset_shard_top4_inclusive.sqlite", "excl": "dataset_shard_top4_exclusive.sqlite"},
    "nonjet4": {"incl": "dataset_shard_nonjet4_inclusive.sqlite", "excl": "dataset_shard_nonjet4_exclusive.sqlite"},
    "rare4": {"incl": "dataset_shard_rare4_inclusive.sqlite", "excl": "dataset_shard_rare4_exclusive.sqlite"},
}
RUNS_BASE_BY_VERSION = {
    "normal": RUNS_BASE_NORMAL, "top4": RUNS_BASE_NORMAL,
    "nonjet4": RUNS_BASE_NONJET4, "rare4": RUNS_BASE_RARE4,
}

dm_index = json.loads((RUNS_BASE_NORMAL / "DoubleMuon_index.json").read_text())
sm_index = json.loads((RUNS_BASE_NORMAL / "SingleMuon_index.json").read_text())


def paths_for(dataset, idx_filter, which, version):
    index = dm_index if dataset == "DoubleMuon" else sm_index
    runs_base = RUNS_BASE_BY_VERSION[version]
    shard_name = SHARD_NAMES[version][which]
    out = []
    for idx, entry in index.items():
        if idx_filter is not None and entry["record_id"] != idx_filter:
            continue
        out.append(str(runs_base / dataset / f"job_{idx}" / shard_name))
    return out


ROW_DEFS = [
    ("combined", lambda version: paths_for("DoubleMuon", None, "incl", version) + paths_for("SingleMuon", None, "excl", version)),
    ("doublemuon_alone_inclusive", lambda version: paths_for("DoubleMuon", None, "incl", version)),
    ("singlemuon_alone_inclusive", lambda version: paths_for("SingleMuon", None, "incl", version)),
    ("record_30522_alone_inclusive", lambda version: paths_for("DoubleMuon", 30522, "incl", version)),
    ("record_30555_alone_inclusive", lambda version: paths_for("DoubleMuon", 30555, "incl", version)),
    ("record_30530_alone_inclusive", lambda version: paths_for("SingleMuon", 30530, "incl", version)),
    ("record_30563_alone_inclusive", lambda version: paths_for("SingleMuon", 30563, "incl", version)),
]


def classify(stage_c_survivors):
    n_nonempty = {}
    n_events = {}
    for name, main_arr in stage_c_survivors.items():
        values, edges = make_fixed_grid_histogram(main_arr)
        n_nonempty[name] = int(np.count_nonzero(values))
        n_events[name] = int(values.sum())
    min31 = {n for n in stage_c_survivors if n_nonempty[n] > BINS_THRESHOLD_A and n_events[n] >= MIN_BUMPNET_EVENTS}
    min26 = {n for n in stage_c_survivors if n_nonempty[n] > BINS_THRESHOLD_B and n_events[n] >= MIN_BUMPNET_EVENTS}
    return {"min31": min31, "min26": min26}


results = {}
for row_name, path_fn in ROW_DEFS:
    results[row_name] = {}
    for version in ["normal", "top4", "nonjet4", "rare4"]:
        shard_paths = path_fn(version)
        print(f"=== {row_name} / {version}: {len(shard_paths)} shards ===", flush=True)
        sig_to_bumpnet = build_sig_to_bumpnet(shard_paths)
        with tempfile.TemporaryDirectory(prefix=f"summary4_{row_name}_{version}_") as tmp:
            scratch = copy_shards(shard_paths, Path(tmp))
            _, stage_c_survivors, _, im_str_by_name = run_funnel_at_threshold(
                scratch, PRIMARY_MIN_EVENTS_PER_FS, sig_to_bumpnet
            )
        cls = classify(stage_c_survivors)
        results[row_name][version] = {"min31": len(cls["min31"]), "min26": len(cls["min26"])}
        print(f"  min31: {len(cls['min31'])}   min26: {len(cls['min26'])}", flush=True)

out = {"rows": results}
with open(OUT_DIR / "summary_table_4versions.json", "w") as f:
    json.dump(out, f, indent=2)
print("\nwrote summary_table_4versions.json")
