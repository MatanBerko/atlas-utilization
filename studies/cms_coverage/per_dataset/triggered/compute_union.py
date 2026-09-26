#!/usr/bin/env python
"""
Local, no-cluster-needed union/overlap analysis over the full stage-(d)
(and stage-(b)) histogram name lists saved by
triggered/cluster/measure_per_dataset_funnel.py.

Reads names_<dataset>.json for every dataset, computes:
  1. Distinct union at stage (d), separately for data and MC, and combined.
  2. Overlap histogram (how many names in exactly 1, 2, ... datasets).
  3. Per-dataset unique vs shared counts.
  4. The 20 most-shared names.
  5. Split by object content (lepton-only, lepton+jet, jet-only, b-jet-containing).
  6. Data-vs-MC name matching.
  7. Same at stage (b), for the sensitivity comparison.

No shared-code calls needed here -- this is pure post-hoc aggregation of
already-committed JSON, using the same object_content_category/object_count
helpers already committed (imported, not reimplemented).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_coverage.cluster.merge_and_count import object_count, object_content_category  # noqa: E402

DATA_LABELS = ["SingleMuon", "DoubleMuon", "SingleElectron", "DoubleEG", "MuonEG", "JetHT"]
MC_LABELS = [
    "mc_ttbar", "mc_drell_yan", "mc_wjets", "mc_diboson",
    "mc_single_top", "mc_qcd_multijet_170to300", "mc_signals_hgg",
]

IM_FROM_BUMPNET = re.compile(r"^mass_([a-z0-9]+)_cat_")


def im_str_from_name(name: str) -> str:
    m = IM_FROM_BUMPNET.match(name)
    return m.group(1) if m else ""


def load_names(names_dir: Path, stage_key: str):
    """Returns {dataset_label: set(names)} and {dataset_label: {name: info}}."""
    names_by_dataset = {}
    info_by_dataset = {}
    for label in DATA_LABELS + MC_LABELS:
        f = names_dir / f"names_{label}.json"
        d = json.loads(f.read_text())
        names_dict = d[stage_key]
        names_by_dataset[label] = set(names_dict.keys())
        info_by_dataset[label] = names_dict
    return names_by_dataset, info_by_dataset


def union_and_overlap(names_by_dataset: dict, labels: list):
    union = set()
    for label in labels:
        union |= names_by_dataset[label]
    membership_count = Counter()
    for name in union:
        n = sum(1 for label in labels if name in names_by_dataset[label])
        membership_count[name] = n
    by_n_datasets = Counter(membership_count.values())
    per_dataset_unique = {}
    per_dataset_shared = {}
    for label in labels:
        unique = sum(1 for name in names_by_dataset[label] if membership_count[name] == 1)
        shared = len(names_by_dataset[label]) - unique
        per_dataset_unique[label] = unique
        per_dataset_shared[label] = shared
    most_shared = sorted(membership_count.items(), key=lambda kv: -kv[1])[:20]
    return union, membership_count, by_n_datasets, per_dataset_unique, per_dataset_shared, most_shared


def content_split(names: set):
    by_content = Counter()
    for name in names:
        im_str = im_str_from_name(name)
        by_content[object_content_category(im_str)] += 1
    return dict(by_content)


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--names-dir", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    names_dir = Path(args.names_dir)

    result = {}
    for stage_key, stage_label in [("stage_d_unscaled_names", "d"), ("stage_b_unscaled_names", "b")]:
        names_by_dataset, info_by_dataset = load_names(names_dir, stage_key)

        data_union, data_membership, data_by_n, data_unique, data_shared, data_most_shared = \
            union_and_overlap(names_by_dataset, DATA_LABELS)
        mc_union, mc_membership, mc_by_n, mc_unique, mc_shared, mc_most_shared = \
            union_and_overlap(names_by_dataset, MC_LABELS)
        all_union, all_membership, all_by_n, all_unique, all_shared, all_most_shared = \
            union_and_overlap(names_by_dataset, DATA_LABELS + MC_LABELS)

        data_vs_mc_matching = len(data_union & mc_union)

        stage_result = {
            "per_dataset_counts": {label: len(names_by_dataset[label]) for label in DATA_LABELS + MC_LABELS},
            "data_union": len(data_union),
            "mc_union": len(mc_union),
            "combined_union": len(all_union),
            "data_by_n_datasets": dict(sorted(data_by_n.items())),
            "mc_by_n_datasets": dict(sorted(mc_by_n.items())),
            "combined_by_n_datasets": dict(sorted(all_by_n.items())),
            "data_per_dataset_unique": data_unique,
            "data_per_dataset_shared": data_shared,
            "mc_per_dataset_unique": mc_unique,
            "mc_per_dataset_shared": mc_shared,
            "data_20_most_shared": data_most_shared,
            "combined_20_most_shared": all_most_shared,
            "data_union_by_content": content_split(data_union),
            "mc_union_by_content": content_split(mc_union),
            "combined_union_by_content": content_split(all_union),
            "data_names_also_in_mc_union": data_vs_mc_matching,
        }
        result[stage_label] = stage_result

    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in
                           ("data_union", "mc_union", "combined_union", "data_names_also_in_mc_union")}
                       for k, v in result.items()}, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
