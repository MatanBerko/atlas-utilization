#!/usr/bin/env python
"""
Local, no-cluster-needed union/overlap analysis over the full stage-(d)
(and stage-(b)) histogram name lists saved by
cluster/measure_ceiling_funnel.py, for ONE configuration (C1-C5) at a time
-- run once per config, pointed at that config's own --names-dir.

Same computation as
studies/cms_coverage/per_dataset/triggered/compute_union.py (distinct
union for data/MC/combined, overlap-count histogram, per-dataset unique vs
shared, 20 most-shared names, object-content split, data-vs-MC name
matching, same at stage b) -- generalized for this task's 8 data labels
(the original 6 plus Tau and MET) and its own object-content categories
(via cluster/measure_ceiling_funnel.py's object_content_category, which is
photon/tau/MET-aware; the shared merge_and_count.object_content_category is
not, see that module's own comment for why).

Usage:
    python compute_union.py --config-label C1 \
        --names-dir /storage/.../ceiling_names/C1 \
        --out /storage/.../union_C1.json
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_coverage.ceiling.cluster.measure_ceiling_funnel import (  # noqa: E402
    object_content_category,
)

DATA_LABELS = [
    "SingleMuon", "DoubleMuon", "SingleElectron", "DoubleEG", "MuonEG", "JetHT",
    "Tau", "MET",
]
MC_LABELS = [
    "mc_ttbar", "mc_drell_yan", "mc_wjets", "mc_diboson",
    "mc_single_top", "mc_qcd_multijet_170to300", "mc_signals_hgg",
]

IM_FROM_BUMPNET = re.compile(r"^mass_([a-z0-9]+)_cat_")


def im_str_from_name(name: str) -> str:
    m = IM_FROM_BUMPNET.match(name)
    return m.group(1) if m else ""


def load_names(names_dir: Path, stage_key: str, data_labels, mc_labels):
    names_by_dataset = {}
    for label in data_labels + mc_labels:
        f = names_dir / f"names_{label}.json"
        if not f.exists():
            print(f"WARNING: {f} not found -- treating {label} as having 0 names "
                  f"at this stage (e.g. Tau/MET file may not have produced any "
                  f"surviving names, or the job hasn't been run for this config yet)")
            names_by_dataset[label] = set()
            continue
        d = json.loads(f.read_text())
        names_dict = d[stage_key]
        names_by_dataset[label] = set(names_dict.keys())
    return names_by_dataset


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
    p.add_argument("--config-label", required=True)
    p.add_argument("--names-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--data-labels", default=",".join(DATA_LABELS),
                    help="Comma-separated. Default: the 8 real datasets this task uses.")
    p.add_argument("--mc-labels", default=",".join(MC_LABELS))
    args = p.parse_args()
    names_dir = Path(args.names_dir)
    data_labels = [s for s in args.data_labels.split(",") if s]
    mc_labels = [s for s in args.mc_labels.split(",") if s]

    result = {"config_label": args.config_label}
    for stage_key, stage_label in [("stage_d_unscaled_names", "d"), ("stage_b_unscaled_names", "b")]:
        names_by_dataset = load_names(names_dir, stage_key, data_labels, mc_labels)

        data_union, data_membership, data_by_n, data_unique, data_shared, data_most_shared = \
            union_and_overlap(names_by_dataset, data_labels)
        mc_union, mc_membership, mc_by_n, mc_unique, mc_shared, mc_most_shared = \
            union_and_overlap(names_by_dataset, mc_labels)
        all_union, all_membership, all_by_n, all_unique, all_shared, all_most_shared = \
            union_and_overlap(names_by_dataset, data_labels + mc_labels)

        data_vs_mc_matching = len(data_union & mc_union)

        stage_result = {
            "per_dataset_counts": {label: len(names_by_dataset[label]) for label in data_labels + mc_labels},
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
                       for k, v in result.items() if k in ("b", "d")}, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
