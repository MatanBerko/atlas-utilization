"""
Top-4 task, Step 6: build the full bin-count summary table (required
table + Matan's mid-task addition) for both versions (normal, top4) and
both thresholds (min31bins >30, min26bins >25), for:
  1. Combined (DM inclusive + SM exclusive) -- the delivered numbers
  2. DoubleMuon alone (inclusive, both records)
  3. SingleMuon alone (inclusive, both records)
  4. SingleMuon exclusive part alone
  5. Each record alone (inclusive): 30522, 30555, 30530, 30563
Plus a "discard >4 objects" counts-only variant of each row (normal
version's own categories restricted to total object count <=4 -- no
separate production, just a post-hoc filter on the same funnel output).

Also computes, for the COMBINED delivery: how many surviving histograms
would still survive from DoubleMuon's own contribution alone, from
SingleMuon-exclusive's own contribution alone, from both, or from
neither alone (i.e. only survives once pooled) -- using each shard-set's
own independently-run funnel (rows 2 and 4 above), compared by NAME
against the combined delivery's own surviving names.

Counts only -- no ROOT files written for rows 2-5 (Hard instruction).
"""
import json
import re
import sys
import tempfile
from pathlib import Path
from collections import Counter

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/muon_combined_delivery/repo")

import numpy as np  # noqa: E402

from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    PRIMARY_MIN_EVENTS_PER_FS,
    MIN_BUMPNET_EVENTS,
    copy_shards,
    run_funnel_at_threshold,
)
from studies.m0m1j0_cms.histograms import make_fixed_grid_histogram  # noqa: E402
from studies.cms_datasets.deliver.build_dataset_delivery import build_sig_to_bumpnet, BINS_THRESHOLD_A, BINS_THRESHOLD_B  # noqa: E402

RUNS_BASE = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched")
FS_RE = re.compile(r"^(\d+)ex_(\d+)mx_(\d+)jx_(\d+)gx_(\d+)tx_(\d+)bx$")

SHARD_NAMES = {
    "normal": {"incl": "dataset_shard_inclusive.sqlite", "excl": "dataset_shard_exclusive.sqlite"},
    "top4": {"incl": "dataset_shard_top4_inclusive.sqlite", "excl": "dataset_shard_top4_exclusive.sqlite"},
}

dm_index = json.loads((RUNS_BASE / "DoubleMuon_index.json").read_text())
sm_index = json.loads((RUNS_BASE / "SingleMuon_index.json").read_text())


def paths_for(dataset, idx_filter, which, version):
    index = dm_index if dataset == "DoubleMuon" else sm_index
    shard_name = SHARD_NAMES[version][which]
    out = []
    for idx, entry in index.items():
        if idx_filter is not None and entry["record_id"] != idx_filter:
            continue
        out.append(str(RUNS_BASE / dataset / f"job_{idx}" / shard_name))
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


def classify(stage_c_survivors, im_str_by_name):
    """Returns dict with keys 'all' and 'discard' (<=4 objects), each
    holding {'min31': set(names), 'min26': set(names)} plus per-name
    metadata (fs label components) for lepton-content breakdowns."""
    all_hists = {}
    n_nonempty = {}
    n_events = {}
    fs_info = {}
    for name, main_arr in stage_c_survivors.items():
        values, edges = make_fixed_grid_histogram(main_arr)
        n_nonempty[name] = int(np.count_nonzero(values))
        n_events[name] = int(values.sum())
        # name format: "FS_<label>_cat_<final_state_category>" from _convert_to_bumpnet_name -- but
        # object_content_category/object_count already know how to parse -- easier: derive fs label
        # from im_str_by_name's own combination naming isn't fs -- instead parse from `name` itself.
        # _convert_to_bumpnet_name produces "mass_<im>_cat_<fs>" (see histograms.py) -- extract fs after "_cat_".
        fs_label = name.split("_cat_", 1)[1] if "_cat_" in name else None
        fs_info[name] = fs_total_and_content(fs_label) if fs_label else None

    min31 = {n for n in stage_c_survivors if n_nonempty[n] > BINS_THRESHOLD_A and n_events[n] >= MIN_BUMPNET_EVENTS}
    min26 = {n for n in stage_c_survivors if n_nonempty[n] > BINS_THRESHOLD_B and n_events[n] >= MIN_BUMPNET_EVENTS}

    def discard_filter(names):
        return {n for n in names if fs_info.get(n) and fs_info[n]["total"] <= 4}

    def lepton_breakdown(names):
        one_mu = sum(1 for n in names if fs_info.get(n) and fs_info[n]["m"] == 1)
        two_plus_mu = sum(1 for n in names if fs_info.get(n) and fs_info[n]["m"] >= 2)
        with_e = sum(1 for n in names if fs_info.get(n) and fs_info[n]["e"] >= 1)
        return {"one_muon": one_mu, "two_or_more_muons": two_plus_mu, "with_electrons": with_e}

    return {
        "all": {
            "min31": {"n": len(min31), "names": min31, "lepton_breakdown": lepton_breakdown(min31)},
            "min26": {"n": len(min26), "names": min26, "lepton_breakdown": lepton_breakdown(min26)},
        },
        "discard_gt4": {
            "min31": {"n": len(discard_filter(min31)), "lepton_breakdown": lepton_breakdown(discard_filter(min31))},
            "min26": {"n": len(discard_filter(min26)), "lepton_breakdown": lepton_breakdown(discard_filter(min26))},
        },
    }


results = {}
for row_name, path_fn in ROW_DEFS:
    results[row_name] = {}
    for version in ["normal", "top4"]:
        shard_paths = path_fn(version)
        print(f"=== {row_name} / {version}: {len(shard_paths)} shards ===")
        sig_to_bumpnet = build_sig_to_bumpnet(shard_paths)
        with tempfile.TemporaryDirectory(prefix=f"summary_{row_name}_{version}_") as tmp:
            scratch = copy_shards(shard_paths, Path(tmp))
            _, stage_c_survivors, _, im_str_by_name = run_funnel_at_threshold(
                scratch, PRIMARY_MIN_EVENTS_PER_FS, sig_to_bumpnet
            )
        cls = classify(stage_c_survivors, im_str_by_name)
        results[row_name][version] = {
            "min31_all": cls["all"]["min31"]["n"],
            "min26_all": cls["all"]["min26"]["n"],
            "min31_discard_gt4": cls["discard_gt4"]["min31"]["n"],
            "min26_discard_gt4": cls["discard_gt4"]["min26"]["n"],
            "min31_lepton_breakdown": cls["all"]["min31"]["lepton_breakdown"],
            "min26_lepton_breakdown": cls["all"]["min26"]["lepton_breakdown"],
            "min31_names": sorted(cls["all"]["min31"]["names"]),
            "min26_names": sorted(cls["all"]["min26"]["names"]),
        }
        print(f"  min31: all={cls['all']['min31']['n']} discard>4={cls['discard_gt4']['min31']['n']}")
        print(f"  min26: all={cls['all']['min26']['n']} discard>4={cls['discard_gt4']['min26']['n']}")

# --- purely-from-one-dataset-vs-both, for the combined delivery (normal version only, both thresholds) ---
origin = {}
for threshold in ["min31", "min26"]:
    combined_names = set(results["combined"]["normal"][f"{threshold}_names"])
    dm_names = set(results["doublemuon_alone_inclusive"]["normal"][f"{threshold}_names"])
    sm_names = set(results["singlemuon_exclusive_alone"]["normal"][f"{threshold}_names"])
    only_dm = combined_names & dm_names - sm_names
    only_sm = combined_names & sm_names - dm_names
    both = combined_names & dm_names & sm_names
    neither_alone = combined_names - dm_names - sm_names
    origin[threshold] = {
        "n_combined_total": len(combined_names),
        "n_survives_from_doublemuon_alone_only": len(only_dm),
        "n_survives_from_singlemuon_exclusive_alone_only": len(only_sm),
        "n_survives_from_both_alone": len(both),
        "n_survives_only_when_pooled": len(neither_alone),
    }
    print(f"\n{threshold}: combined={len(combined_names)} DM-alone-only={len(only_dm)} "
          f"SM-alone-only={len(only_sm)} both-alone={len(both)} only-when-pooled={len(neither_alone)}")

# Strip the large name-sets before dumping (keep counts only in the main JSON; names -> separate file)
names_out = {}
for row_name, by_version in results.items():
    names_out[row_name] = {}
    for version, d in by_version.items():
        names_out[row_name][version] = {"min31_names": d.pop("min31_names"), "min26_names": d.pop("min26_names")}

out = {"rows": results, "origin_breakdown": origin}
with open(RUNS_BASE.parent / "deliver" / "muon_combined" / "summary_table.json", "w") as f:
    json.dump(out, f, indent=2)
with open(RUNS_BASE.parent / "deliver" / "muon_combined" / "summary_table_names.json", "w") as f:
    json.dump(names_out, f, indent=2)
print("\nwrote summary_table.json and summary_table_names.json")
