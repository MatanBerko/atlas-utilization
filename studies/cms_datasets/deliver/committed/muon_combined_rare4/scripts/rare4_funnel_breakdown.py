"""
rare4 task, Step 6: full funnel breakdown (a, a2, b, c, d, d'), same
methodology as the nonjet4 task's own FUNNEL_BREAKDOWN.md. Computed
directly from the full-run shards (DoubleMuon rare4 inclusive, 57 files +
SingleMuon rare4 exclusive, 152 files). Read-only: the per-final-state
prune runs only on scratch copies in a temp dir.
"""
import json
import sys
import sqlite3
import tempfile
from pathlib import Path
from collections import Counter

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/rare4_delivery/repo")

import numpy as np  # noqa: E402

from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    PRIMARY_MIN_EVENTS_PER_FS,
    MIN_BUMPNET_EVENTS,
    copy_shards,
    run_funnel_at_threshold,
)
from studies.m0m1j0_cms.histograms import make_fixed_grid_histogram  # noqa: E402
from studies.cms_datasets.deliver.build_dataset_delivery import (  # noqa: E402
    build_sig_to_bumpnet, BINS_THRESHOLD_A, BINS_THRESHOLD_B,
)

RUNS_BASE = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_rare4")
OUT_DIR = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_rare4")

dm_index = json.loads((RUNS_BASE / "DoubleMuon_index.json").read_text())
sm_index = json.loads((RUNS_BASE / "SingleMuon_index.json").read_text())

dm_incl_paths = [str(RUNS_BASE / "DoubleMuon" / f"job_{idx}" / "dataset_shard_rare4_inclusive.sqlite") for idx in dm_index]
sm_excl_paths = [str(RUNS_BASE / "SingleMuon" / f"job_{idx}" / "dataset_shard_rare4_exclusive.sqlite") for idx in sm_index]
sm_incl_paths = [str(RUNS_BASE / "SingleMuon" / f"job_{idx}" / "dataset_shard_rare4_inclusive.sqlite") for idx in sm_index]

combined_paths = dm_incl_paths + sm_excl_paths
print(f"DoubleMuon inclusive shards: {len(dm_incl_paths)}")
print(f"SingleMuon exclusive shards: {len(sm_excl_paths)}")
print(f"Combined (delivery-pooled) shards: {len(combined_paths)}")


def stage_a_names(shard_paths):
    sig_to_bumpnet = build_sig_to_bumpnet(shard_paths)
    names = set(bn for bn, _fs, _im in sig_to_bumpnet.values())
    return names, sig_to_bumpnet


combined_names_a, combined_sig_to_bumpnet = stage_a_names(combined_paths)
dm_alone_names_a, _ = stage_a_names(dm_incl_paths)
sm_alone_names_a, _ = stage_a_names(sm_incl_paths)

print(f"\n(a) combined distinct names (>=1 event): {len(combined_names_a)}")
print(f"(a) DoubleMuon alone (inclusive) distinct names: {len(dm_alone_names_a)}")
print(f"(a) SingleMuon alone (inclusive) distinct names: {len(sm_alone_names_a)}")


def read_entry_counts(shard_path):
    con = sqlite3.connect(f"file:{shard_path}?mode=ro&immutable=1", uri=True)
    cur = con.cursor()
    cur.execute("SELECT signature, SUM(n_entries) FROM array_chunks GROUP BY signature")
    rows = cur.fetchall()
    con.close()
    return rows


per_name_entries = Counter()
for i, shard_path in enumerate(combined_paths):
    for sig, n in read_entry_counts(shard_path):
        entry = combined_sig_to_bumpnet.get(sig)
        if entry is None:
            continue
        bn, _fs, _im = entry
        per_name_entries[bn] += int(n)
    if (i + 1) % 40 == 0:
        print(f"  (a2) scanned {i + 1}/{len(combined_paths)} shards")

assert set(per_name_entries.keys()) == combined_names_a
a2_count = sum(1 for v in per_name_entries.values() if v >= 100)
print(f"\n(a2) combined distinct names with pooled raw entries >=100: {a2_count}")

with tempfile.TemporaryDirectory(prefix="rare4_funnel_check_") as tmp:
    scratch = copy_shards(combined_paths, Path(tmp))
    stage_b_names, stage_c_survivors, stage_d_survivors, im_str_by_name = run_funnel_at_threshold(
        scratch, PRIMARY_MIN_EVENTS_PER_FS, combined_sig_to_bumpnet
    )
print(f"\n(b) after >=100-events-per-final-state prune: {len(stage_b_names)}")
print(f"(c) after post-processing (>=100 main events): {len(stage_c_survivors)}")

n_nonempty_by_name = {}
n_events_by_name = {}
for name, main_arr in stage_c_survivors.items():
    values, edges = make_fixed_grid_histogram(main_arr)
    n_nonempty_by_name[name] = int(np.count_nonzero(values))
    n_events_by_name[name] = int(values.sum())

set_d = {n for n in stage_c_survivors
         if n_nonempty_by_name[n] > BINS_THRESHOLD_B and n_events_by_name[n] >= MIN_BUMPNET_EVENTS}
set_dprime = {n for n in stage_c_survivors
              if n_nonempty_by_name[n] > BINS_THRESHOLD_A and n_events_by_name[n] >= MIN_BUMPNET_EVENTS}

print(f"(d)  >25 filled bins (min26bins): {len(set_d)}")
print(f"(d') >30 filled bins (min31bins): {len(set_dprime)}")

build_summary = json.loads((OUT_DIR / "build_summary_rare4.json").read_text())
expected_b = build_summary["funnel"]["b_after_min_events_per_fs_100"]
expected_c = build_summary["funnel"]["c_after_postprocessing_ge100_main"]
expected_dprime = build_summary["n_histograms_min31bins"]
expected_d = build_summary["n_histograms_min26bins"]

results = {
    "a_combined_ge1_event": len(combined_names_a),
    "a_doublemuon_alone_inclusive_ge1_event": len(dm_alone_names_a),
    "a_singlemuon_alone_inclusive_ge1_event": len(sm_alone_names_a),
    "a2_combined_names_with_ge100_pooled_entries": a2_count,
    "b_after_min_events_per_fs_100": len(stage_b_names),
    "c_after_postprocessing_ge100_main": len(stage_c_survivors),
    "d_gt25_bins_min26": len(set_d),
    "dprime_gt30_bins_min31": len(set_dprime),
    "confirm_vs_build_summary_rare4_json": {
        "b": {"computed": len(stage_b_names), "expected": expected_b, "match": len(stage_b_names) == expected_b},
        "c": {"computed": len(stage_c_survivors), "expected": expected_c, "match": len(stage_c_survivors) == expected_c},
        "d_min26": {"computed": len(set_d), "expected": expected_d, "match": len(set_d) == expected_d},
        "dprime_min31": {"computed": len(set_dprime), "expected": expected_dprime, "match": len(set_dprime) == expected_dprime},
    },
}
print("\n" + json.dumps(results, indent=2))

all_match = all(v["match"] for v in results["confirm_vs_build_summary_rare4_json"].values())
results["all_confirmed_match"] = all_match
print(f"\nALL CONFIRMED MATCH: {all_match}")

out_path = OUT_DIR / "funnel_breakdown_readonly.json"
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nwrote {out_path}")
