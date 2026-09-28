#!/usr/bin/env python
"""
Dataset-parameterized manifest breakdown: lepton-content (0/1/>=2 selected
leptons), object-content category (jet-only/lepton-only/lepton+jet/
b-jet-containing, via merge_and_count's own object_content_category,
imported unmodified), zero-lepton count, and a count of final states with
>=2 selected leptons of a given flavor letter ('e' or 'm') -- the
conventional subset for a dilepton-triggered dataset.

Optionally compares against a second manifest (e.g. the DoubleMuon
generic delivery's own) to report shared vs. dataset-only histogram
NAMES.

Usage:
    python compute_manifest_breakdown.py \
        --manifest-min31 <manifest_..._min31bins.json> \
        --manifest-min26 <manifest_..._min26bins.json> \
        --lepton-letter e \
        --compare-manifest-min31 <other delivery's manifest_min31bins.json> \
        --compare-manifest-min26 <other delivery's manifest_min26bins.json> \
        --compare-label DoubleMuon_generic \
        --out-json <breakdown.json>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_coverage.cluster.merge_and_count import object_content_category  # noqa: E402

FS_CAT_PATTERN = re.compile(r"(\d+)ex_(\d+)mx_(\d+)jx_(\d+)gx(?:_(\d+)tx)?(?:_(\d+)bx)?")


def parse_fs_category(final_state_category: str):
    m = FS_CAT_PATTERN.search(final_state_category or "")
    if not m:
        return None
    n_e, n_m, n_j = int(m.group(1)), int(m.group(2)), int(m.group(3))
    n_b = int(m.group(6)) if m.group(6) else 0
    return n_e, n_m, n_j, n_b


def lepton_content_bucket(n_e: int, n_m: int) -> str:
    n_lep = n_e + n_m
    if n_lep == 0:
        return "0"
    if n_lep == 1:
        return "1"
    return ">=2"


def breakdown_one(manifest: list, lepton_letter: str) -> dict:
    by_object_content = Counter(e["object_content_category"] for e in manifest)
    lepton_content = Counter()
    n_zero_lepton = 0
    n_ge2_own_flavor = 0
    for e in manifest:
        c = parse_fs_category(e.get("final_state_category", ""))
        if c is None:
            continue
        n_e, n_m, n_j, n_b = c
        lepton_content[lepton_content_bucket(n_e, n_m)] += 1
        if n_e == 0 and n_m == 0:
            n_zero_lepton += 1
        n_own = n_e if lepton_letter == "e" else n_m
        if n_own >= 2:
            n_ge2_own_flavor += 1
    return {
        "n_total": len(manifest),
        "by_object_content_category": dict(by_object_content),
        "by_lepton_content": dict(lepton_content),
        "n_zero_lepton": n_zero_lepton,
        f"n_ge2_selected_{lepton_letter}": n_ge2_own_flavor,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest-min31", required=True)
    p.add_argument("--manifest-min26", required=True)
    p.add_argument("--lepton-letter", required=True, choices=["e", "m"])
    p.add_argument("--compare-manifest-min31", default=None)
    p.add_argument("--compare-manifest-min26", default=None)
    p.add_argument("--compare-label", default="other")
    p.add_argument("--out-json", required=True)
    args = p.parse_args()

    manifest_a = json.loads(Path(args.manifest_min31).read_text())
    manifest_b = json.loads(Path(args.manifest_min26).read_text())

    result = {
        "lepton_letter": args.lepton_letter,
        "min31bins": breakdown_one(manifest_a, args.lepton_letter),
        "min26bins": breakdown_one(manifest_b, args.lepton_letter),
    }

    if args.compare_manifest_min31 and args.compare_manifest_min26:
        cmp_a = json.loads(Path(args.compare_manifest_min31).read_text())
        cmp_b = json.loads(Path(args.compare_manifest_min26).read_text())
        names_a = set(e["name"] for e in manifest_a)
        names_b = set(e["name"] for e in manifest_b)
        cmp_names_a = set(e["name"] for e in cmp_a)
        cmp_names_b = set(e["name"] for e in cmp_b)
        result["comparison_vs"] = {
            "label": args.compare_label,
            "min31bins": {
                "n_this": len(names_a), "n_other": len(cmp_names_a),
                "n_shared": len(names_a & cmp_names_a),
                "n_only_in_this": len(names_a - cmp_names_a),
                "n_only_in_other": len(cmp_names_a - names_a),
            },
            "min26bins": {
                "n_this": len(names_b), "n_other": len(cmp_names_b),
                "n_shared": len(names_b & cmp_names_b),
                "n_only_in_this": len(names_b - cmp_names_b),
                "n_only_in_other": len(cmp_names_b - names_b),
            },
        }

    Path(args.out_json).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
