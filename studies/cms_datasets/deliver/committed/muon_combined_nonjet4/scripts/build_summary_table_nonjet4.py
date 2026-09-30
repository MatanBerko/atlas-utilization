"""
nonjet4 task, Step 6: bin-count summary table for all three versions
(normal, top4, nonjet4) and both thresholds (min31bins >30, min26bins
>25), for:
  1. Combined (DM inclusive + SM exclusive) -- the delivered numbers
  2. DoubleMuon alone (inclusive)
  3. SingleMuon alone (inclusive)
  4. SingleMuon exclusive part alone
  5. Each record alone (inclusive): 30522, 30555, 30530, 30563
Counts only -- no ROOT files written for rows 2-5.

Adapted from the top-4 task's own scripts/build_summary_table.py: same
funnel, same rows, extended with a third `nonjet4` version reading from
runs_matched_nonjet4/ instead of runs_matched/.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/nonjet4_delivery/repo")

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
OUT_DIR = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_nonjet4")
FS_RE = re.compile(r"^(\d+)ex_(\d+)mx_(\d+)jx_(\d+)gx_(\d+)tx_(\d+)bx$")

SHARD_NAMES = {
    "normal": {"incl": "dataset_shard_inclusive.sqlite", "excl": "dataset_shard_exclusive.sqlite"},
    "top4": {"incl": "dataset_shard_top4_inclusive.sqlite", "excl": "dataset_shard_top4_exclusive.sqlite"},
    "nonjet4": {"incl": "dataset_shard_nonjet4_inclusive.sqlite", "excl": "dataset_shard_nonjet4_exclusive.sqlite"},
}
RUNS_BASE_BY_VERSION = {"normal": RUNS_BASE_NORMAL, "top4": RUNS_BASE_NORMAL, "nonjet4": RUNS_BASE_NONJET4}

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
    ("singlemuon_exclusive_alone", lambda version: paths_for("SingleMuon", None, "excl", version)),
    ("record_30522_alone_inclusive", lambda version: paths_for("DoubleMuon", 30522, "incl", version)),
    ("record_30555_alone_inclusive", lambda version: paths_for("DoubleMuon", 30555, "incl", version)),
    ("record_30530_alone_inclusive", lambda version: paths_for("SingleMuon", 30530, "incl", version)),
    ("record_30563_alone_inclusive", lambda version: paths_for("SingleMuon", 30563, "incl", version)),
]


def fs_total_and_content(fs_label):
    m = FS_RE.match(fs_label)
    if not m:
        return None
    e, mu, j, g, t, b = (int(x) for x in m.groups())
    return {"total": e + mu + j + g + t + b, "e": e, "m": mu, "j": j, "g": g, "t": t, "b": b}


def classify(stage_c_survivors):
    n_nonempty = {}
    n_events = {}
    fs_info = {}
    for name, main_arr in stage_c_survivors.items():
        values, edges = make_fixed_grid_histogram(main_arr)
        n_nonempty[name] = int(np.count_nonzero(values))
        n_events[name] = int(values.sum())
        fs_label = name.split("_cat_", 1)[1] if "_cat_" in name else None
        fs_info[name] = fs_total_and_content(fs_label) if fs_label else None

    min31 = {n for n in stage_c_survivors if n_nonempty[n] > BINS_THRESHOLD_A and n_events[n] >= MIN_BUMPNET_EVENTS}
    min26 = {n for n in stage_c_survivors if n_nonempty[n] > BINS_THRESHOLD_B and n_events[n] >= MIN_BUMPNET_EVENTS}

    def lepton_breakdown(names):
        one_mu = sum(1 for n in names if fs_info.get(n) and fs_info[n]["m"] == 1)
        two_plus_mu = sum(1 for n in names if fs_info.get(n) and fs_info[n]["m"] >= 2)
        with_e = sum(1 for n in names if fs_info.get(n) and fs_info[n]["e"] >= 1)
        return {"one_muon": one_mu, "two_or_more_muons": two_plus_mu, "with_electrons": with_e}

    return {
        "min31": {"n": len(min31), "names": min31, "lepton_breakdown": lepton_breakdown(min31)},
        "min26": {"n": len(min26), "names": min26, "lepton_breakdown": lepton_breakdown(min26)},
    }


results = {}
for row_name, path_fn in ROW_DEFS:
    results[row_name] = {}
    for version in ["normal", "top4", "nonjet4"]:
        shard_paths = path_fn(version)
        print(f"=== {row_name} / {version}: {len(shard_paths)} shards ===")
        sig_to_bumpnet = build_sig_to_bumpnet(shard_paths)
        with tempfile.TemporaryDirectory(prefix=f"summary_{row_name}_{version}_") as tmp:
            scratch = copy_shards(shard_paths, Path(tmp))
            _, stage_c_survivors, _, im_str_by_name = run_funnel_at_threshold(
                scratch, PRIMARY_MIN_EVENTS_PER_FS, sig_to_bumpnet
            )
        cls = classify(stage_c_survivors)
        results[row_name][version] = {
            "min31": cls["min31"]["n"],
            "min26": cls["min26"]["n"],
            "min31_lepton_breakdown": cls["min31"]["lepton_breakdown"],
            "min26_lepton_breakdown": cls["min26"]["lepton_breakdown"],
            "min31_names": sorted(cls["min31"]["names"]),
            "min26_names": sorted(cls["min26"]["names"]),
        }
        print(f"  min31: {cls['min31']['n']}   min26: {cls['min26']['n']}")

# --- which names differ between top4 and nonjet4 (combined row, both thresholds) ---
diffs = {}
for threshold in ["min31", "min26"]:
    t4_names = set(results["combined"]["top4"][f"{threshold}_names"])
    nj4_names = set(results["combined"]["nonjet4"][f"{threshold}_names"])
    diffs[threshold] = {
        "in_top4_not_nonjet4": sorted(t4_names - nj4_names),
        "in_nonjet4_not_top4": sorted(nj4_names - t4_names),
    }
    print(f"\n{threshold}: top4-only={len(diffs[threshold]['in_top4_not_nonjet4'])} "
          f"nonjet4-only={len(diffs[threshold]['in_nonjet4_not_top4'])}")

names_out = {}
for row_name, by_version in results.items():
    names_out[row_name] = {}
    for version, d in by_version.items():
        names_out[row_name][version] = {"min31_names": d.pop("min31_names"), "min26_names": d.pop("min26_names")}

out = {"rows": results, "top4_vs_nonjet4_combined_diffs": diffs}
with open(OUT_DIR / "summary_table.json", "w") as f:
    json.dump(out, f, indent=2)
with open(OUT_DIR / "summary_table_names.json", "w") as f:
    json.dump(names_out, f, indent=2)
print("\nwrote summary_table.json and summary_table_names.json")
